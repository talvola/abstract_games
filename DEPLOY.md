# Deploying a hosted instance

> **Live:** https://abstract-games.onrender.com — a Render web service
> (`srv-d8un5a7lk1mc7385c73g`, free plan) created via the Render API, **auto-deploys
> on every push to `main`**. Persistence is a **Neon** Postgres (`DATABASE_URL` set in
> the Render env, not in git; the `neon-*.txt` credential files are gitignored).
> Accounts + async matches now survive redeploys. To rotate/replace the DB, update the
> `DATABASE_URL` env var on the service.


This hosts the platform as **one Render web service** that serves both the API and
the built React/Vite frontend from a single origin (so no CORS and same-site session
cookies). It mirrors the `generic_poker` Render setup (`render.yaml` + `build.sh`).

## Why Render (not Vercel)
The backend is a long-running, stateful FastAPI app: it loads the ~205-game registry
once at startup, holds it in memory, and uses a SQL database + signed-cookie sessions.
That fits Render's **Web Service** model. Vercel's strength is static/SPA hosting and
short-lived serverless functions — a poor fit for this backend (cold starts would
re-load the whole registry per invocation, and SQLite/in-memory state don't survive
serverless). `gamefinder` uses Vercel only because it's a Next.js app.
A single Render service serving the SPA too is the simplest thing that lets others test.

## One-time setup (Render dashboard)
1. Make sure this repo is pushed to GitHub (it is: `talvola/abstract_games`).
2. In the [Render dashboard](https://dashboard.render.com): **New → Blueprint**, pick this
   repo, and Render reads `render.yaml` and creates the `abstract-games` web service.
   (Or **New → Web Service** → connect the repo; it auto-detects `render.yaml`.)
3. First build runs `./build.sh` (pip install + `npm run build`) and starts
   `uvicorn server.app:app`. When it's live you get a URL like
   `https://abstract-games.onrender.com` — share that.

That's it. **Hotseat** and **vs-bot** play work immediately (they're stateless — the
client holds the game state, the server just computes moves).

## What the env vars do (set automatically by `render.yaml`)
- `AGP_SECRET_KEY` — generated once; signs session cookies.
- `AGP_COOKIE_SECURE=true` — required for cookies over Render's HTTPS.
- `PYTHON_VERSION` / `NODE_VERSION` — build toolchain.
- `DATABASE_URL` — unset by default ⇒ ephemeral SQLite (see below).

## Security (important)
The game-upload endpoint runs uploaded game code **in-process (RCE)**. It is **closed by
default** and must stay that way on a public instance: do **not** set
`AGP_ALLOW_OPEN_UPLOADS` or `AGP_ADMIN_EMAILS`. New games are added by committing
packages to `engine/games/` and redeploying — never via the public upload endpoint.

## Free-tier caveats
- The service **spins down after ~15 min idle**; the next request cold-starts it
  (~1 min, incl. loading the 205-game registry). Fine for casual testing.
- The free filesystem is **ephemeral** — the SQLite DB (accounts + async/correspondence
  matches) resets on every redeploy/spin-down. Hotseat + vs-bot are unaffected.

## Persistent database (optional — to keep accounts & async matches)
1. Render dashboard: **New → PostgreSQL** (free tier available), same region as the service.
2. Copy its **Internal Database URL** and set it as `DATABASE_URL` on the web service
   (Environment tab). The app auto-creates tables on startup and already rewrites
   `postgres://` → `postgresql://`.

   Or wire it in `render.yaml` instead of the manual step:
   ```yaml
   databases:
     - name: abstract-games-db
       plan: free
   services:
     - type: web
       # ...
       envVars:
         - key: DATABASE_URL
           fromDatabase:
             name: abstract-games-db
             property: connectionString
   ```

## Updating the live site
Push to `main` → Render auto-deploys (rebuilds the frontend + restarts). To pick up
newly added games, a redeploy is all that's needed (the registry loads at startup).

## Local sanity check (optional, mimics production)
```bash
cd web && npm run build && cd ..        # build the SPA into web/dist
.venv/bin/uvicorn server.app:app --port 8000   # one server, no Vite
# open http://localhost:8000  →  the app + /api both served from one origin
```
