#!/usr/bin/env python3
"""Suite de pruebas automatizadas de Kno-Tic (offline heuristics, SSRF, SQLite y API)."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BACKEND_DIR = RAIZ / "backend"
sys.path.insert(0, str(BACKEND_DIR))

TMP_DIR = Path(tempfile.mkdtemp(prefix="knotic_test_"))
os.environ["KNOTIC_DB_PATH"] = str(TMP_DIR / "test_kno_tic.db")
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("GROQ_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
import analyzer  # noqa: E402
import db  # noqa: E402
from main import app  # noqa: E402

fallos: list[str] = []


def comprobar(nombre: str, condicion: bool, detalle: str = "") -> None:
    if condicion:
        print(f"  [OK]    {nombre}")
    else:
        print(f"  [FALLO] {nombre}" + (f" — {detalle}" if detalle else ""))
        fallos.append(nombre)


def caso_heuristicas_y_ssrf() -> None:
    print("\n1. Motor heurístico offline y protección SSRF")
    seguro = analyzer._analyze_with_local_heuristics("Hola, nos vemos mañana a las 10 para tomar café.")
    comprobar("mensaje legítimo puntúa < 30 (seguro)",
              seguro["risk_score"] < 30 and seguro["category"] == "seguro", str(seguro))

    smishing = analyzer._analyze_with_local_heuristics(
        "BBVA URGENTE: su cuenta ha sido bloqueada por actividad sospechosa. "
        "Verifique su DNI y clave SMS en 24 horas en http://bit.ly/bbva-alerta"
    )
    comprobar("smishing bancario puntúa >= 60",
              smishing["risk_score"] >= 60 and smishing["category"] in ("smishing", "phishing"),
              str(smishing))
    tipos = {i["type"] for i in smishing["indicators"]}
    comprobar("detecta tácticas clave (urgencia, autoridad, datos_personales, enlace)",
              {"urgencia", "autoridad", "datos_personales", "enlace"}.issubset(tipos), str(tipos))

    comprobar("SSRF bloquea 127.0.0.1", not analyzer._is_safe_public_url("http://127.0.0.1:8000"))
    comprobar("SSRF bloquea localhost", not analyzer._is_safe_public_url("http://localhost:5000/admin"))
    comprobar("SSRF bloquea metadata AWS 169.254.169.254",
              not analyzer._is_safe_public_url("http://169.254.169.254/latest/meta-data/"))
    comprobar("SSRF bloquea file://", not analyzer._is_safe_public_url("file:///etc/passwd"))
    comprobar("SSRF permite https://example.com", analyzer._is_safe_public_url("https://example.com"))

    pat = analyzer._url_heuristics("http://xn--bbv-1la.xyz/login.html#token=" + ("a" * 35), "http://xn--bbv-1la.xyz")
    comprobar("heurísticas URL detectan http, punycode, TLD de riesgo y fragment largo",
              len(pat) >= 3, str(pat))


def caso_db_y_api() -> None:
    print("\n2. Base de datos SQLite y API FastAPI")
    db.init_db()
    with TestClient(app) as client:
        r_health = client.get("/api/health")
        comprobar("GET /api/health responde ok",
                  r_health.status_code == 200 and r_health.json().get("status") == "ok")

        r_an = client.post("/analyze", json={
            "content": "Agencia Tributaria: multa urgente. Introduzca su IBAN y contraseña en https://tinyurl.com/pago"
        })
        comprobar("POST /analyze funciona offline con heurísticas",
                  r_an.status_code == 200 and r_an.json().get("risk_score", 0) >= 60, r_an.text)
        aid = r_an.json().get("analysis_id")

        r_ssrf = client.post("/analyze-url", json={"url": "http://127.0.0.1:8000/history"})
        comprobar("POST /analyze-url bloquea SSRF con HTTP 400",
                  r_ssrf.status_code == 400, f"status={r_ssrf.status_code}")

        r_url = client.post("/analyze-url", json={"url": "http://bit.ly/prueba-phishing"})
        comprobar("POST /analyze-url analiza URL externa offline",
                  r_url.status_code == 200 and "acortador de URL conocido" in str(r_url.json().get("suspicious_patterns")),
                  r_url.text)

        r_fb = client.patch(f"/feedback/{aid}", json={"value": "correcto"})
        comprobar("PATCH /feedback actualiza SQLite", r_fb.status_code == 200)

        r_hist = client.get("/history?search=Tributaria")
        comprobar("GET /history filtra y devuelve registro guardado",
                  r_hist.status_code == 200 and len(r_hist.json()) >= 1 and r_hist.json()[0]["feedback"] == "correcto")

        r_stats = client.get("/stats")
        comprobar("GET /stats devuelve estadísticas",
                  r_stats.status_code == 200 and r_stats.json().get("total", 0) >= 2, r_stats.text)

        r_learn = client.post("/learn", json={
            "indicator_type": "urgencia",
            "description": "Plazo de 24h",
            "summary": "Mensaje fraudulento",
        })
        comprobar("POST /learn devuelve guía offline sin API key",
                  r_learn.status_code == 200 and len(r_learn.json().get("explanation", "")) > 30)


def main() -> int:
    try:
        caso_heuristicas_y_ssrf()
        caso_db_y_api()
    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)

    print()
    if fallos:
        print(f"RESULTADO: {len(fallos)} comprobación(es) fallida(s):")
        for f in fallos:
            print(f"  · {f}")
        return 1
    print("RESULTADO: todas las comprobaciones pasan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
