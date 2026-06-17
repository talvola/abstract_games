#!/usr/bin/env bash
# Run the Phase-1 stack locally: FastAPI backend (:8000) + Vite frontend (:5173).
# The Vite dev server proxies /api to the backend, so just open http://localhost:5173
set -euo pipefail
cd "$(dirname "$0")"

# --- backend ---
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r server/requirements.txt
fi
.venv/bin/uvicorn server.app:app --port 8000 --reload &
BACK=$!

# --- frontend ---
if [ ! -d web/node_modules ]; then (cd web && npm install); fi
(cd web && npm run dev -- --port 5173) &
FRONT=$!

trap 'kill $BACK $FRONT 2>/dev/null' EXIT
echo "Backend  : http://localhost:8000/api/health"
echo "Frontend : http://localhost:5173"
wait
