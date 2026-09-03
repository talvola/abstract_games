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

## Email (turn / pairing / result / reminder notifications)

Correspondence play depends on email: the side to move has **7 days** per move
(`AGP_MOVE_DEADLINE_DAYS`) and is auto-forfeited after that, so without mail a
game dies silently. `server/events.py` decides who is told what (pairing,
your turn, game over by move/resignation/timeout, a reminder at <24h —
`AGP_REMINDER_HOURS`), records every send in the `notifications` table
(reminders go out once per turn), and `server/notify.py` sends via **any SMTP
relay**. Nothing is sent until these env vars exist on the Render service:

| var | value |
|---|---|
| `AGP_SMTP_HOST` | e.g. `smtp-relay.brevo.com` |
| `AGP_SMTP_PORT` | `587` (STARTTLS) |
| `AGP_SMTP_USER` | relay login |
| `AGP_SMTP_PASS` | relay password / SMTP key (**Render env only, never git**) |
| `AGP_EMAIL_FROM` | `Abstract Games <you@example.com>` — must be a sender the relay has verified |
| `AGP_BASE_URL` | `https://abstract-games.onrender.com` — used for the links in every email |

**⚠ Render's FREE tier blocks outbound SMTP (ports 25/465/587) since
2025-09** — `[notify] … OSError(101, 'Network is unreachable')` in the logs is
that block, not a credential problem. So on the free instance the SMTP vars
above can never work. Two ways out:

1. **Upgrade the web service to a paid instance** (Starter, ~$7/mo). SMTP
   ports 465/587 open (25 stays blocked everywhere), and the instance no longer
   sleeps, which also removes the cold start. Then Gmail SMTP with an **App
   Password** is the simplest sender: dedicated Gmail account → 2-Step
   Verification → myaccount.google.com/apppasswords → `AGP_SMTP_HOST=smtp.gmail.com`,
   `AGP_SMTP_PORT=587`, `AGP_SMTP_USER=<the gmail>`, `AGP_SMTP_PASS=<app password>`,
   `AGP_EMAIL_FROM=Abstract Games <the gmail>` (~500/day). Yahoo works the same
   way (`smtp.mail.yahoo.com`) once the account is old enough to issue app
   passwords.
2. **Stay free and send over HTTPS**: set `AGP_RESEND_API_KEY` (Resend, free
   3,000/mo; takes precedence over SMTP). Resend needs a **verified domain** to
   send to arbitrary recipients — buy a cheap domain, add its DNS records, and
   set `AGP_EMAIL_FROM=Abstract Games <notify@yourdomain>`. (The domain can
   also be attached to Render for a nicer URL.) Brevo's HTTP API would work too
   but requires a postal address in every mail.

**Verify:** `curl https://abstract-games.onrender.com/api/cron/tick` returns
`email:true`, `email_transport`, `email_sent_ok` (count) and `email_last_error`
(the last delivery failure, or null). Trigger a send (accept a seek between two
accounts, or "Forgot password?"), then re-check: `email_sent_ok` should go up
and `email_last_error` stay null; if it shows `Network is unreachable` you are
on the free tier's SMTP block.
Locally, unset vars = the message is printed to the uvicorn log instead.

**Scheduler:** there is no worker on the free tier. Forfeits and reminders run
on every lobby load *and* on `GET /api/cron/tick` — point a free uptime pinger
(UptimeRobot, cron-job.org) at that URL every 5–10 min. It is idempotent and
unauthenticated on purpose, and as a bonus it keeps the instance warm (see the
cold-start issue). Tests: `.venv/bin/python -m unittest server.tests.test_notify -v`.

## Accounts: reset, rename, delete

- Users can change their display name and password from the **Account** panel
  (signed-in box on the home page) and request a reset link with **Forgot
  password?** — the link (`#/reset/<token>`, 1 hour, single-use, no table)
  needs the mailer above; without it the UI says to contact the admin.
- **Deleting an account** has no UI. From the Neon SQL editor (or `psql`), with
  the user's id from `select id, email from users where email = '…'`:

  ```sql
  begin;
  delete from notifications where user_id = :id;
  delete from match_rating_changes where user_id = :id;
  delete from user_game_ratings where user_id = :id;
  delete from messages where user_id = :id;
  delete from seeks where creator_id = :id;
  -- matches keep a JSON seat with the name; resign/finish them first if active:
  update matches set status = 'finished' where status = 'active'
     and players::text like '%"user_id": ' || :id || '%';
  delete from users where id = :id;
  commit;
  ```
  (Column names: check `server/models.py` if this drifts.)
