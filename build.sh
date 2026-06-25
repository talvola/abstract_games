#!/usr/bin/env bash
# Render build script — single web service.
# Installs the FastAPI backend deps and builds the React/Vite frontend into
# web/dist, which server/app.py serves in production (one origin → no CORS).
set -o errexit

pip install -r server/requirements.txt

# Build the SPA. Render's native build environment includes Node + npm.
cd web
npm ci
npm run build
cd ..

echo "build.sh: backend deps installed + web/dist built"
