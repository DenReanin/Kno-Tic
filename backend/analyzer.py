from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

load_dotenv()

_PLACEHOLDER_KEYS = {"", "your_gemini_api_key_here", "your_groq_api_key_here"}

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
RISKY_TLDS = {".xyz", ".top", ".click", ".tk", ".ml", ".gq", ".cf", ".ga", ".zip", ".mov"}

CLOUD_STORAGE_HOSTS = {
    "storage.googleapis.com",
    "firebasestorage.googleapis.com",
    "s3.amazonaws.com",
    "blob.core.windows.net",
    "raw.githubusercontent.com",
    "cdn.discordapp.com",
}


def _get_gemini_client():
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if key in _PLACEHOLDER_KEYS:
        return None
    from google import genai

    return genai.Client(api_key=key)


def _get_groq_client():
    key = (os.getenv("GROQ_API_KEY") or "").strip()
    if key in _PLACEHOLDER_KEYS:
        return None
    from groq import Groq

    return Groq(api_key=key)


def _is_blocked_ip(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def _is_safe_public_url(url: str) -> bool:
    """Valida que la URL use http/https y no apunte a direcciones internas/loopback."""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    if parsed.scheme.lower() not in ("http", "https"):
        return False

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False

    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        return False

    try:
        ip_literal = ipaddress.ip_address(hostname)
        return not _is_blocked_ip(ip_literal)
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        for _fam, _type, _proto, _canon, sockaddr in infos:
            ip_str = sockaddr[0].split("%")[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if _is_blocked_ip(ip_obj):
                return False
    except socket.gaierror:
        # Si estamos offline sin DNS, permitimos que continúe para evaluar heurísticas de string
        return True
    except Exception:
        return False

    return True


def _url_heuristics(original_url: str, final_url: str) -> list[str]:
    patterns = []
    try:
        parsed_orig = urlparse(original_url)
        parsed_final = urlparse(final_url)
        hostname = (parsed_orig.hostname or "").lower()

        if parsed_orig.scheme.lower() == "http":
            patterns.append("conexión sin cifrar (HTTP)")

        if "@" in parsed_orig.netloc:
            patterns.append("ofuscación con '@' en la URL para engañar sobre el dominio real")

        if "xn--" in hostname:
            patterns.append("dominio internacionalizado Punycode (posible ataque homográfico)")

        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
            patterns.append("dominio es dirección IP")

        if hostname in URL_SHORTENERS:
            patterns.append("acortador de URL conocido")

        if any(hostname.endswith(tld) for tld in RISKY_TLDS):
            patterns.append("TLD frecuentemente utilizado en campañas de phishing")

        if hostname.count(".") >= 4:
            patterns.append("exceso de subdominios")

        if parsed_orig.hostname != parsed_final.hostname and parsed_final.hostname:
            patterns.append(f"redirección a dominio diferente ({parsed_final.hostname})")

        if any(hostname == cs or hostname.endswith("." + cs) for cs in CLOUD_STORAGE_HOSTS):
            if parsed_orig.path.lower().endswith(".html"):
                patterns.append("archivo HTML alojado en almacenamiento cloud público (técnica blob phishing)")

        fragment = parsed_orig.fragment
        if len(fragment) > 30:
            patterns.append(
                f"hash fragment largo ({len(fragment)} caracteres) — patrón de kit de phishing para pasar datos de víctima"
            )

        if len(original_url) > 200:
            patterns.append("URL inusualmente larga")

        filename = parsed_orig.path.split("/")[-1].split(".")[0]
        if filename and len(filename) >= 5:
            vowels = sum(1 for c in filename.lower() if c in "aeiou")
            if vowels / len(filename) < 0.15:
                patterns.append("nombre de archivo con patrón aleatorio (generado automáticamente)")

    except Exception:
        pass
    return patterns


_HEURISTIC_RULES: list[tuple[str, int, str, str]] = [
    (
        "urgencia",
        24,
        r"\b(urgente|inmediato|inmediata|24\s*horas|48\s*horas|último aviso|ultimo aviso|caduca|expira|hoy mismo|suspendid[ao]|bloquead[ao]|urgent|immediately|expires today)\b",
        "Crea sensación de urgencia artificial para que actúes sin comprobar la autenticidad.",
    ),
    (
        "autoridad",
        22,
        r"\b(bbva|santander|caixabank|sabadell|bankinter|ing|unicaja|correos|dgt|agencia tributaria|hacienda|seguridad social|polic[ií]a|paypal|amazon|netflix|apple|microsoft|soporte t[eé]cnico|banco|entidad bancaria)\b",
        "Menciona una entidad oficial, bancaria o marca conocida (posible suplantación de autoridad).",
    ),
    (
        "miedo",
        22,
        r"\b(cargo no autorizado|actividad sospechosa|acceso no autorizado|multa|embargo|sanci[oó]n|cancelaci[oó]n|penalizaci[oó]n|unauthorized|security alert|account locked)\b",
        "Apela al miedo o a consecuencias económicas/legales para forzar una respuesta rápida.",
    ),
    (
        "datos_personales",
        26,
        r"\b(dni|nie|iban|tarjeta|cvv|pin|contrase[nñ]a|clave de acceso|c[oó]digo sms|otp|verificar datos|actualizar datos|password|credit card)\b",
        "Solicita credenciales, códigos de verificación o datos bancarios/personales sensibles.",
    ),
    (
        "suplantacion",
        18,
        r"\b(estimado cliente|querido usuario|verifique su cuenta|confirme su identidad|restablecer acceso|haga clic|pinche aqu[ií]|click here|verify your account)\b",
        "Utiliza fórmulas impersonales o llamadas directas a validar la cuenta mediante un enlace.",
    ),
]


def _analyze_with_local_heuristics(
    content: str,
    suspicious_patterns: list[str] | None = None,
) -> dict:
    """Motor heurístico offline de respaldo cuando no hay API keys de Gemini/Groq."""
    text = content or ""
    indicators: list[dict[str, str]] = []
    score = 0

    for ind_type, weight, pattern, description in _HEURISTIC_RULES:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            unique = sorted({str(m).lower() for m in matches})[:3]
            score += weight + min(8, (len(unique) - 1) * 4)
            indicators.append({
                "type": ind_type,
                "description": f"{description} (Detectado: {', '.join(unique)})",
            })

    urls = re.findall(r"https?://[^\s<>\"']+", text, flags=re.IGNORECASE)
    url_patterns = list(suspicious_patterns or [])
    for u in urls:
        url_patterns.extend(_url_heuristics(u, u))

    if url_patterns:
        unique_pat = list(dict.fromkeys(url_patterns))
        score += min(35, 14 + len(unique_pat) * 8)
        indicators.append({
            "type": "enlace",
            "description": "Señales técnicas en el enlace: " + "; ".join(unique_pat[:4]) + ".",
        })
    elif urls and score > 0:
        score += 12
        indicators.append({
            "type": "enlace",
            "description": "Combina lenguaje de presión con un enlace externo para redirigir a la víctima.",
        })

    score = max(0, min(100, score))

    if score >= 60:
        is_sms = len(text) < 280 and bool(urls)
        category = "smishing" if is_sms else "phishing"
        summary = (
            "Análisis offline: el contenido reúne múltiples tácticas típicas de ingeniería social "
            "(riesgo alto). No pulses enlaces ni introduzcas credenciales."
        )
    elif score >= 30:
        category = "sospechoso"
        summary = (
            "Análisis offline: se detectaron señales de alerta moderadas. Verifica el remitente por "
            "un canal oficial antes de responder."
        )
    else:
        category = "seguro"
        summary = (
            "Análisis offline: no se detectaron patrones evidentes de phishing o ingeniería social."
        )

    return {
        "risk_score": score,
        "category": category,
        "indicators": indicators,
        "summary": summary,
        "provider": "heuristic_offline",
    }


_LOCAL_LEARNING_GUIDES: dict[str, str] = {
    "urgencia": (
        "La táctica de urgencia busca impedir que pienses con calma imponiendo plazos falsos "
        "(por ejemplo, 24 horas o bloqueo inmediato).\n"
        "• Plazos límite exagerados o cuentas regresivas\n"
        "• Amenazas de pérdida de acceso si no actúas hoy\n"
        "• Tono imperativo para que pulses un enlace de inmediato\n\n"
        "Detente y comprueba la situación entrando directamente en la web o app oficial sin usar el enlace."
    ),
    "autoridad": (
        "La suplantación de autoridad imita bancos, organismos públicos o servicios conocidos para "
        "ganar obediencia automática.\n"
        "• Uso de logos o nombres oficiales desde remitentes extraños\n"
        "• Notificaciones de multas, impuestos o bloqueos bancarios\n"
        "• Mensajes genéricos sin tu nombre real\n\n"
        "Contacta con la entidad a través de su teléfono o web oficial guardada en tus marcadores."
    ),
    "miedo": (
        "El miedo aprovecha el pánico ante un supuesto fraude, multa o robo de cuenta para forzar "
        "errores rápidos.\n"
        "• Avisos de cargos bancarios falsos o accesos desde otro país\n"
        "• Amenazas legales o sanciones económicas\n"
        "• Solicitud de acción inmediata para 'cancelar' el problema\n\n"
        "Revisa tus movimientos desde la aplicación oficial; nunca desde enlaces recibidos por SMS o correo."
    ),
    "suplantacion": (
        "La suplantación intenta hacerse pasar por soporte técnico, compañeros o empresas legítimas.\n"
        "• Dominios parecidos con letras cambiadas o subdominios largos\n"
        "• Saludos genéricos como 'Estimado cliente'\n"
        "• Enlaces a formularios externos de inicio de sesión\n\n"
        "Inspecciona siempre el dominio real de la dirección web antes de escribir ningún dato."
    ),
    "datos_personales": (
        "La petición directa de credenciales, códigos OTP o tarjetas es el objetivo final del phishing.\n"
        "• Solicita PIN, CVV, contraseñas o códigos de un solo uso\n"
        "• Formularios inesperados tras un enlace externo\n"
        "• Excusas de 'verificación de identidad'\n\n"
        "Ningún banco ni organismo legítimo te pedirá tu clave completa ni tus códigos SMS por enlace."
    ),
    "enlace": (
        "Los enlaces maliciosos ocultan su destino real usando acortadores, IPs o dominios recién creados.\n"
        "• URLs acortadas (bit.ly, tinyurl) o con muchos subdominios\n"
        "• Conexiones HTTP sin cifrado o caracteres '@' / Punycode\n"
        "• Archivos HTML alojados en nubes públicas\n\n"
        "No hagas clic en enlaces sospechosos; escribe tú mismo la dirección oficial en el navegador."
    ),
}


async def analyze_message(content: str) -> dict:
    gemini = _get_gemini_client()
    if gemini is not None:
        try:
            res = _analyze_with_gemini(gemini, content)
            res.setdefault("provider", "gemini")
            return res
        except Exception:
            pass

    groq = _get_groq_client()
    if groq is not None:
        try:
            res = _analyze_with_groq(groq, content)
            res.setdefault("provider", "groq")
            return res
        except Exception:
            pass

    return _analyze_with_local_heuristics(content)


async def analyze_image_content(image_bytes: bytes, mime_type: str) -> dict:
    gemini = _get_gemini_client()
    if gemini is None:
        raise RuntimeError(
            "El análisis de imágenes requiere configurar GEMINI_API_KEY en backend/.env"
        )
    from google.genai import types

    response = gemini.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(
                text=SYSTEM_PROMPT
                + "\n\nAnaliza el texto que aparece en esta captura de pantalla de un mensaje."
            ),
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    if response.text is None:
        raise ValueError("Gemini devolvió una respuesta vacía al analizar la imagen")
    res = json.loads(response.text)
    res.setdefault("provider", "gemini")
    return res


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
        if not _is_safe_public_url(str(resp.url)):
            raise ValueError("Redirección bloqueada hacia dirección privada o local")
        html = resp.text[:4000]
        html = re.sub(r"\s+", " ", html).strip()
        return html


async def analyze_url(url: str) -> dict:
    if not _is_safe_public_url(url):
        raise ValueError(
            "URL bloqueada por protección anti-SSRF: solo se permiten URLs públicas http/https."
        )

    redirect_chain = [url]
    final_url = url
    html_content = ""

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.head(url)
            final_url = str(resp.url)
            if not _is_safe_public_url(final_url):
                raise ValueError("La URL redirige a una dirección interna no permitida")
            redirect_chain = [str(r.url) for r in resp.history] + [final_url]
    except ValueError:
        raise
    except Exception:
        pass

    try:
        html_content = await _fetch_page_content(url)
    except ValueError:
        raise
    except Exception:
        pass

    suspicious_patterns = _url_heuristics(url, final_url)

    gemini = _get_gemini_client()
    groq = _get_groq_client()
    if gemini is not None or groq is not None:
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
    else:
        result = _analyze_with_local_heuristics(
            f"{url} {final_url} {html_content}",
            suspicious_patterns=suspicious_patterns,
        )

    result["redirect_chain"] = redirect_chain
    result["final_url"] = final_url
    result["suspicious_patterns"] = suspicious_patterns
    return result


async def learn_indicator(indicator_type: str, description: str, summary: str) -> dict:
    gemini = _get_gemini_client()
    if gemini is not None:
        try:
            from google.genai import types

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
            response = gemini.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            if response.text is not None:
                return json.loads(response.text)
        except Exception:
            pass

    guide = _LOCAL_LEARNING_GUIDES.get(
        indicator_type,
        "Este indicador refleja un patrón habitual en mensajes engañosos.\n"
        "• Desconfía de solicitudes inesperadas o enlaces externos\n"
        "• Verifica siempre el dominio real y la identidad del remitente\n"
        "• No compartas contraseñas ni códigos por enlace\n\n"
        "Ante la duda, contacta directamente con la entidad por sus canales oficiales.",
    )
    return {"explanation": guide}


def _analyze_with_gemini(gemini_client, content: str) -> dict:
    from google.genai import types

    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=f"{SYSTEM_PROMPT}\n\nMensaje a analizar:\n{content}",
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    if response.text is None:
        raise ValueError("Gemini devolvió una respuesta vacía")
    return json.loads(response.text)


def _analyze_with_groq(groq_client, content: str) -> dict:
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
