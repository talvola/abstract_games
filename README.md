# Abstract Games Platform

A generic platform for playing abstract board games — asynchronously against
humans (planned) or against a computer opponent — where new games are added as
**modular packages** authored against a documented contract, not hard-coded into
the app.

See **[PLATFORM_PLAN.md](PLATFORM_PLAN.md)** for the full requirements, research,
and phased roadmap.

## Repository layout

| Path | What it is |
|---|---|
| `engine/` | **Phase 0** — the Python engine: game contract, package loader, conformance harness, generic MCTS opponent, `agp` CLI. No web, no deps. See `engine/README.md` and `engine/SPEC.md`. |
| `server/` | **Phase 1** — FastAPI backend exposing the engine over HTTP (stateless; the client holds game state). |
| `web/` | **Phase 1** — React + Vite frontend with a *generic* SVG renderer driven by each game's RenderSpec. Knows no game rules. |
| `engine/games/` | Game packages: `tic_tac_toe` (minimal), `oust` (Mark Steere — hex, captures). |
| `legacy/` | The original standalone per-game React prototypes of Oust & Yodd, archived (both now run as platform engine modules). See `legacy/README.md`. |

## Run it (Phase 1)

```bash
./dev.sh                      # starts backend :8000 + frontend :5173
# then open http://localhost:5173
```

Or manually:

```bash
python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt
.venv/bin/uvicorn server.app:app --port 8000 --reload      # backend
cd web && npm install && npm run dev                        # frontend (proxies /api)
```

You can pick a game, choose a board size, and play **two-player hotseat** or
**vs the computer** (generic MCTS — no per-game AI code).

## Author / test a game offline (Phase 0)

```bash
cd engine && export PYTHONPATH=.
python3 -m agp.cli validate games/oust          # conformance: RESULT: OK
python3 -m agp.cli render   games/oust --moves 8
python3 -m agp.cli playtest games/oust --bot --size 4
```

To add a game, follow **`engine/SPEC.md`**: write `manifest.json` + a `game.py`
implementing `agp.game.Game`, drop it in `engine/games/<uid>/`, make
`agp validate` pass — it then appears in the web UI automatically.

## Accounts & correspondence (Phase 2)

Signing in unlocks asynchronous play. The backend persists matches (SQLAlchemy;
SQLite locally via `DATABASE_URL`, Postgres in production), enforces turn order,
and stores move history. You can:

- **Post an open challenge** (a *seek*) for another person to accept, or play the
  **computer** (generic MCTS) — for any game.
- Track ongoing games in a **lobby** with whose-turn badges; the match view polls
  so an opponent's move appears without a manual refresh.

Auth is email + password with a signed-cookie session (`AGP_SECRET_KEY` to set the
signing key; `AGP_COOKIE_SECURE=true` behind HTTPS). Quick-play still needs no account.

## Add a game without the platform source (Phase 3)

Anyone can build a game with the **dev kit** and drop it into a running
platform — no access to the platform's source, no redeploy:

1. Download the kit from a running site (`/api/devkit`, or the "Add a game"
   panel) — or build it locally with `python3 tools/build_devkit.py`
   (→ `dist/gamedev-kit.zip`). The kit is self-contained: the `agp` SDK,
   `SPEC.md`, a starter `template/`, a worked example, an `AGENTS.md` guide, and
   a ready-to-use **Claude Code skill** (`build-abstract-game`).
2. Implement the game against the contract until `agp validate` passes, then
   `agp pack` it into a `.zip`.
3. Upload the `.zip` via the **Add a game** panel (signed in). The server
   re-validates it (conformance harness in a subprocess) and **hot-registers**
   it — it's immediately playable against people or the AI.

`gamedev-kit/` holds the kit's hand-written sources; `tools/build_devkit.py`
assembles the full kit (copying the SDK from `engine/` so it never drifts).

> **⚠️ Security — uploads are remote code execution.** A registered game's
> `game.py` is imported and run **in-process** by the server (validation runs in
> a subprocess, but accepted games then execute in the API process). There is no
> sandbox yet, so uploading a package is equivalent to running arbitrary code on
> the host. Uploads are therefore **closed by default** and gated:
> - `AGP_ADMIN_EMAILS="you@x,friend@y"` — only those signed-in users may upload (recommended).
> - `AGP_ALLOW_OPEN_UPLOADS=true` — any signed-in user may upload; **knowingly unsafe**, trusted/local instances only (`dev.sh` sets this for local use).
>
> With neither set, uploads are denied. Real isolation (subprocess/WASM/container
> per game) is the prerequisite for opening uploads to untrusted users — see
> `PLATFORM_PLAN.md`.

## Status

- **Phase 0 ✅** game contract + conformance + generic MCTS, proven on Tic-Tac-Toe and Oust.
- **Phase 1 ✅** web UI: generic renderer (hex + square), hotseat & vs-bot play.
- **Phase 2 ✅** accounts, persistent matches, lobby, async correspondence (human & bot).
- **Phase 3 ✅** dev kit (SDK + spec + template + agent guide + Claude Code skill) and drop-in `.zip` upload, validation, and hot-registration.
- **Later** real sandboxing for untrusted uploads · bot on a background worker · "your turn" email/push · stronger per-game AI.

See the roadmap in [PLATFORM_PLAN.md](PLATFORM_PLAN.md).
