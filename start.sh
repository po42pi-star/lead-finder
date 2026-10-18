#!/usr/bin/env bash
# Запуск Lead Finder локально: бэкенд (порт 8000) + интерфейс (порт 5173).
# Остановить — Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Нет файла .env — скопируйте .env.example в .env и впишите ключи (OPENAI_API_KEY, DADATA_API_KEY)."
  exit 1
fi

if [ ! -d .venv ]; then
  echo "→ Первый запуск: ставлю зависимости Python…"
  python3 -m venv .venv
  .venv/bin/pip install -q -e ".[dev]"
fi

if [ ! -d frontend/node_modules ]; then
  echo "→ Первый запуск: ставлю зависимости интерфейса…"
  (cd frontend && npm install --silent)
fi

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "→ Бэкенд: http://localhost:8000/docs"
.venv/bin/uvicorn main:app --port 8000 --log-level warning &

if [ ! -f data/chroma/chroma.sqlite3 ]; then
  echo "→ База знаний не найдена — индексирую rag_docs (1–2 минуты)…"
  until curl -s localhost:8000/health >/dev/null; do sleep 1; done
  curl -s -X POST localhost:8000/rag/ingest -H 'Content-Type: application/json' \
    -d '{"path": "", "force_rebuild": false}' >/dev/null
fi

echo "→ Интерфейс: http://localhost:5173"
(cd frontend && npx vite --port 5173 --strictPort) &

until curl -s localhost:5173 >/dev/null; do sleep 1; done
if [ -z "${NO_BROWSER:-}" ]; then
  if [ -d /Applications/Firefox.app ]; then open -a Firefox http://localhost:5173; else open http://localhost:5173; fi
fi

wait
