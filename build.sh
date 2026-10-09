#!/usr/bin/env bash
# Render build script — single web service.
# Installs the FastAPI backend deps and builds the React/Vite frontend into
# web/dist, which server/app.py serves in production (one origin → no CORS).
set -o errexit

pip install -r server/requirements.txt

# Board thumbnails for the landing page's "Start here" shelf (static JSON in
# web/public, regenerated every deploy so it can't drift from the games).
python3 engine/tools/gen_featured_previews.py

# Build the SPA. Render's native build environment includes Node + npm.
cd web
npm ci
npm run build
cd ..

echo "build.sh: backend deps installed + web/dist built"
