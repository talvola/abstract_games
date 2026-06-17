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
| `oust.jsx`, `yodd.jsx`, `src/` | The original standalone per-game React apps (being superseded by the platform). |

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

## Status

- **Phase 0 ✅** game contract + conformance + generic MCTS, proven on Tic-Tac-Toe and Oust.
- **Phase 1 ✅** web UI: generic renderer (hex + square), hotseat & vs-bot play.
- **Phase 2 (next)** accounts + Postgres + asynchronous correspondence play between humans.
- **Phase 3** drop-in ZIP upload & registration; bot-as-opponent in correspondence.

See the roadmap in [PLATFORM_PLAN.md](PLATFORM_PLAN.md).
