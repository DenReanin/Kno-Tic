from google import genai
from google.genai import types
from groq import Groq
from dotenv import load_dotenv
import httpx
import json
import os
import re

load_dotenv()

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

SYSTEM_PROMPT = """Eres un experto en ciberseguridad especializado en detección
de phishing e ingeniería social. Analiza el texto proporcionado y devuelve
ÚNICAMENTE un JSON válido con exactamente esta estructura:

{
  "risk_score": <número entero entre 0 y 100>,
  "category": "<uno de: seguro | sospechoso | phishing | smishing | fraude>",
  "indicators": [
    {
      "type": "<uno de: urgencia | autoridad | miedo | suplantacion | datos_personales | enlace | otro>",
      "description": "<explicación breve en español de por qué es sospechoso>"
    }
  ],
  "summary": "<resumen de 1-2 frases en español explicando el resultado>"
}

Criterios de puntuación:
- 0-29: Mensaje legítimo, sin señales de alerta
- 30-59: Sospechoso, requiere precaución
- 60-79: Probable phishing o smishing
- 80-100: Phishing/fraude confirmado con alta confianza

Si el mensaje es seguro, devuelve indicators como lista vacía []."""

URL_SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "short.to", "buff.ly", "rb.gy"}

CLOUD_STORAGE_HOSTS = {
    "storage.googleapis.com",
    "firebasestorage.googleapis.com",
    "s3.amazonaws.com",
    "blob.core.windows.net",
    "raw.githubusercontent.com",
    "cdn.discordapp.com",
}


async def analyze_message(content: str) -> dict:
    try:
        return _analyze_with_gemini(content)
    except Exception:
        pass

    if groq_client:
        return _analyze_with_groq(content)

    raise RuntimeError("Ningún proveedor de IA disponible")


async def analyze_image_content(image_bytes: bytes, mime_type: str) -> dict:
    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(
                text=SYSTEM_PROMPT + "\n\nAnaliza el texto que aparece en esta captura de pantalla de un mensaje."
            ),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )
    if response.text is None:
        raise ValueError("Gemini devolvió una respuesta vacía al analizar la imagen")
    return json.loads(response.text)


def _url_heuristics(original_url: str, final_url: str) -> list[str]:
    patterns = []
    try:
        from urllib.parse import urlparse
        parsed_orig = urlparse(original_url)
        parsed_final = urlparse(final_url)
        hostname = parsed_orig.hostname or ''

        if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', hostname):
            patterns.append("dominio es dirección IP")

        if hostname in URL_SHORTENERS:
            patterns.append("acortador de URL conocido")

        if hostname.count('.') >= 4:
            patterns.append("exceso de subdominios")

        if parsed_orig.hostname != parsed_final.hostname and parsed_final.hostname:
            patterns.append(f"redirección a dominio diferente ({parsed_final.hostname})")

        if any(hostname == cs or hostname.endswith('.' + cs) for cs in CLOUD_STORAGE_HOSTS):
            if parsed_orig.path.lower().endswith('.html'):
                patterns.append("archivo HTML alojado en almacenamiento cloud público (técnica blob phishing)")

        fragment = parsed_orig.fragment
        if len(fragment) > 30:
            patterns.append(f"hash fragment largo ({len(fragment)} caracteres) — patrón de kit de phishing para pasar datos de víctima")

        if len(original_url) > 200:
            patterns.append("URL inusualmente larga")

        filename = parsed_orig.path.split('/')[-1].split('.')[0]
        if filename and len(filename) >= 5:
            vowels = sum(1 for c in filename.lower() if c in 'aeiou')
            if vowels / len(filename) < 0.15:
                patterns.append("nombre de archivo con patrón aleatorio (generado automáticamente)")

    except Exception:
        pass
    return patterns


async def _fetch_page_content(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=8.0) as client:
        resp = await client.get(url, headers=headers)
        html = resp.text[:4000]
        html = re.sub(r'\s+', ' ', html).strip()
        return html


async def analyze_url(url: str) -> dict:
    redirect_chain = [url]
    final_url = url
    html_content = ""

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.head(url)
            final_url = str(resp.url)
            redirect_chain = [str(r.url) for r in resp.history] + [final_url]
    except Exception:
        pass

    try:
        html_content = await _fetch_page_content(url)
    except Exception:
        pass

    suspicious_patterns = _url_heuristics(url, final_url)

    context = (
        f"URL original: {url}\n"
        f"URL final tras redirecciones: {final_url}\n"
        f"Número de redirecciones: {len(redirect_chain) - 1}\n"
        f"Cadena de redirecciones: {' -> '.join(redirect_chain)}\n"
        f"Patrones sospechosos detectados: {', '.join(suspicious_patterns) if suspicious_patterns else 'ninguno'}\n"
    )

    if html_content:
        context += (
            f"\nContenido HTML de la página (primeros 4000 caracteres):\n{html_content}\n\n"
            "Analiza el HTML en busca de: formularios de login falsos, campos de contraseña, "
            "logos de marcas conocidas embebidos en base64, scripts que leen window.location.hash, "
            "redirecciones JavaScript, o cualquier contenido de ingeniería social."
        )
    else:
        context += "\n(No se pudo obtener el contenido de la página)"

    context += "\n\nDetermina si esta URL es parte de un intento de phishing, fraude o ingeniería social."

    result = await analyze_message(context)
    result["redirect_chain"] = redirect_chain
    result["final_url"] = final_url
    result["suspicious_patterns"] = suspicious_patterns
    return result


async def learn_indicator(indicator_type: str, description: str, summary: str) -> dict:
    prompt = (
        f"Eres un experto en ciberseguridad que enseña a usuarios a protegerse.\n\n"
        f"El usuario analizó un mensaje que contiene este indicador de riesgo:\n"
        f"- Tipo: {indicator_type.replace('_', ' ')}\n"
        f"- Descripción: {description}\n"
        f"- Contexto del mensaje: {summary}\n\n"
        f"Responde ÚNICAMENTE con un JSON válido: {{\"explanation\": \"<texto>\"}}\n\n"
        f"El texto debe tener máximo 200 palabras y seguir esta estructura:\n"
        f"1) Qué es la táctica '{indicator_type.replace('_', ' ')}' (2-3 frases)\n"
        f"2) 3 señales para identificarla (formato lista con •)\n"
        f"3) Qué hacer si la encuentras (1-2 frases)\n\n"
        f"Responde en español, tono didáctico y directo."
    )
    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    if response.text is None:
        raise ValueError("Gemini devolvió una respuesta vacía")
    return json.loads(response.text)


def _analyze_with_gemini(content: str) -> dict:
    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=f"{SYSTEM_PROMPT}\n\nMensaje a analizar:\n{content}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )
    if response.text is None:
        raise ValueError("Gemini devolvió una respuesta vacía")
    return json.loads(response.text)


def _analyze_with_groq(content: str) -> dict:
    assert groq_client is not None, "Groq client no está configurado"
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Mensaje a analizar:\n{content}"},
        ],
    )
    raw = response.choices[0].message.content
    if raw is None:
        raise ValueError("Groq devolvió una respuesta vacía")
    return json.loads(raw)
