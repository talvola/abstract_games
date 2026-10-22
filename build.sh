#!/usr/bin/env bash
# Render build script — single web service.
# Installs the FastAPI backend deps and builds the React/Vite frontend into
# web/dist, which server/app.py serves in production (one origin → no CORS).
set -o errexit

# emSign ECC Root CA - G3 compromise (2026-10-20): upgrade pip hash-verified, then make
# every later TLS handshake use only pip's fixed bundle (Render's Debian 12 store is
# unverified). Node's roots are compiled in, so the guard checks the node binary too
# (NODE_VERSION must be a release that dropped G3: 22.23.4 / 24.22.1 / 26.12.1 or later).
pip install --require-hashes -r server/requirements-bootstrap.txt
export SSL_CERT_FILE="$(python -c 'from pip._vendor import certifi; print(certifi.where())')"
export SSL_CERT_DIR=/nonexistent
python - <<'EOF'
import os, ssl, subprocess, sys, pip
from pip._vendor import certifi
G3 = "emSign ECC Root CA - G3"
bad = [p for p in {certifi.where(), os.environ["SSL_CERT_FILE"]} if G3 in open(p).read()]
if os.path.exists(os.environ["SSL_CERT_DIR"]):
    bad.append(os.environ["SSL_CERT_DIR"])
if tuple(int(x) for x in pip.__version__.split(".")[:3]) < (26, 2, 2):
    bad.append(f"pip {pip.__version__}")
node = subprocess.run(
    ["node", "-p", "process.version + ' ' + require('tls').rootCertificates.some(p => "
     f"new (require('crypto').X509Certificate)(p).subject.includes('{G3}'))"],
    capture_output=True, text=True).stdout.split()
if node[-1:] != ["false"]:
    bad.append(f"node {node}")
# Informational only: the running app no longer relies on the OS store (db.py and
# notify.py pass certifi's bundle explicitly), but record what Render's image holds.
os_store = "/etc/ssl/certs/ca-certificates.crt"
os_g3 = G3 in open(os_store).read() if os.path.exists(os_store) else "missing"
os_pkg = subprocess.run(["dpkg-query", "-W", "-f=${Version}", "ca-certificates"],
                        capture_output=True, text=True).stdout or "?"
print(f"emsign-guard: pip {pip.__version__} node {node[0] if node else '?'} "
      f"paths={ssl.get_default_verify_paths()} os_store=ca-certificates {os_pkg} g3={os_g3} bad={bad}")
sys.exit(1 if bad else 0)
EOF

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
