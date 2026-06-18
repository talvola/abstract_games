# Abstract Games Platform

Generic platform for abstract board games (async-vs-human + vs-bot), games added as modular packages.
See PLATFORM_PLAN.md (roadmap) and engine/SPEC.md (game authoring contract).

## Layout
- `engine/` — Python SDK (pure stdlib): `agp/` package, `games/<uid>/` packages, `SPEC.md`, `tests/`.
- `server/` — FastAPI backend (SQLAlchemy, sqlite default). `web/` — React+Vite frontend.
- `gamedev-kit/` — distributable SDK; build with `python3 tools/build_devkit.py` → `dist/gamedev-kit.zip`.
- Legacy (superseded): `oust.jsx`, `yodd.jsx`, `src/`, root `index.html`/`vite.config.js`.

## Run / dev
- `./dev.sh` — backend :8000 + frontend :5173 (Vite proxies `/api`); sources gitignored `dev.env` (e.g. `AGP_ADMIN_EMAILS`).
- **Restart the backend after any engine/game change** — the game registry loads game code at startup and is cached (uvicorn runs without --reload).
- Frontend `web/src` edits are live via Vite HMR on :5173 — **no `npm run build` needed in dev** (build only for production/`dist`).
- Stop a server by PORT, never `pkill -f vite|uvicorn` (the pattern matches the bash command itself → exit 144): `kill $(ss -ltnp | grep ':8000 ' | grep -oP 'pid=\K[0-9]+')`.
- Start long-lived servers via the Bash tool's `run_in_background`, not `nohup ... &` in a foreground call.

## Engine / authoring a game
- A game = `engine/games/<uid>/{manifest.json, game.py}` (game.py = one `agp.game.Game` subclass; uid comes from manifest — don't hardcode it in the class).
- Validate/iterate: `cd engine && PYTHONPATH=. python3 -m agp.cli validate|playtest|render|pack games/<uid>`.
- Moves are strings: `>`-separated cell-id path (`"2,1>3,4>5,6"`), optional `=CHOICE` suffix (promotion). Cells: `"col,row"` square, `"q,r"` axial hex.
- **Guarantee termination** (conformance plays random games to a terminal): add no-progress + hard-ply-cap draw rules for games that could loop.
- Optional hooks: `describe_move` (move-log notation), manifest `category` (lobby grouping). "Win as event" games store the result in state (e.g. Oust/chess `winner`), not inferred from the board.
- Rule variants / board sizes → manifest `options` (auto-rendered as dropdowns); make a separate package only for a genuinely distinct game.
- Non-cell legal moves (e.g. `"swap"`, `"pass"`) auto-render as action buttons; `=CHOICE` moves show a picker.

## Server
- `DATABASE_URL` (default `sqlite:///./agp.db`). Uploads run game code IN-PROCESS (RCE) → gated, closed by default: `AGP_ADMIN_EMAILS` allowlist or `AGP_ALLOW_OPEN_UPLOADS=true`. Real sandbox is deferred.
- Game registry caches at startup; `POST /api/games/upload` hot-reloads it.

## Testing
- Engine: `cd engine && PYTHONPATH=. python3 tests/test_games.py`.
- Backend via `TestClient`: call `server.db.init_db()` first (bare TestClient skips the startup lifespan → no tables). Use `httpx` in `.venv` (not `requests`).
- Browser checks use pinchtab: click custom buttons by **ref** (text:/CSS clicks are unreliable); coordinate clicks are flaky (first click often misses) — verify with a screenshot/snap; screenshots occasionally capture a stale tab, re-run in a fresh session.

## Conventions
- Frontend: one generic `Board` renderer; all board types (`square`/`hex`/`polygons`) go through a unified polygon shape model — `polygons` games supply each cell's vertices. No per-game UI. Seat colors in `web/src/colors.js`.
- Porting a Zillions of Games (.zrf) game: use the `zillions-to-platform` skill (`.claude/skills/`).
- Git: solo project, commit directly to `main`.
