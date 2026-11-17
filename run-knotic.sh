#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

KNOTIC_PORT="${KNOTIC_PORT:-8000}"
export KNOTIC_PORT

if [ ! -x ".venv/bin/python" ]; then
  echo "[Kno-Tic] Creando entorno virtual .venv..."
  python3 -m venv --system-site-packages .venv
  echo "[Kno-Tic] Instalando dependencias backend..."
  ./.venv/bin/pip install --upgrade pip >/dev/null || true
  ./.venv/bin/pip install -r backend/requirements.txt httpx
fi

if [ ! -d "frontend/dist" ] && [ -d "frontend" ]; then
  echo "[Kno-Tic] Compilando frontend React..."
  (cd frontend && npm install && npm run build)
fi

if [ "${1:-}" = "--setup-only" ]; then
  echo "[Kno-Tic] Entorno y build listos."
  exit 0
fi

(
  for _ in $(seq 1 30); do
    if "$ROOT/.venv/bin/python" -c "import os, socket; s=socket.socket(); s.settimeout(0.2); s.connect(('127.0.0.1', int(os.environ.get('KNOTIC_PORT', '8000')))); s.close()" 2>/dev/null; then
      if command -v xdg-open >/dev/null 2>&1 && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
        xdg-open "http://127.0.0.1:${KNOTIC_PORT}" >/dev/null 2>&1 || true
      fi
      break
    fi
    sleep 0.5
  done
) >/dev/null 2>&1 &

cd "$ROOT/backend"
exec "$ROOT/.venv/bin/python" -u -m uvicorn main:app --host 127.0.0.1 --port "$KNOTIC_PORT"
