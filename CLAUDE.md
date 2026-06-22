# Abstract Games Platform

Generic platform for abstract board games (async-vs-human + vs-bot), games added as modular packages.
See PLATFORM_PLAN.md (roadmap) and engine/SPEC.md (game authoring contract).

## Layout
- `engine/` — Python SDK (pure stdlib): `agp/` package, `games/<uid>/` packages, `SPEC.md`, `tests/`.
- `server/` — FastAPI backend (SQLAlchemy, sqlite default). `web/` — React+Vite frontend.
- `gamedev-kit/` — distributable SDK; build with `python3 tools/build_devkit.py` → `dist/gamedev-kit.zip`.
- `legacy/` — the original standalone React prototypes of Oust & Yodd (archived, not part of the live app; both now run as engine modules). See `legacy/README.md`.

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
- Ship a **`rules.md`** (one page, rules *as implemented* — the local source of truth) in each game package. The web UI shows it via a "Rules" button and serves it at `/api/games/<uid>/rules`; `manifest.bgg_url` becomes the "official source" link. Supported Markdown: headings, `**bold**`/`*italic*`/`` `code` ``, `-`/`1.` lists, `[links](url)`.
- The lobby/quick-play game selector is a searchable, category-grouped `GamePicker` (`web/src/`); `manifest.category` and `tags` feed grouping and search.
- Non-cell legal moves (e.g. `"swap"`, `"pass"`) auto-render as action buttons; `=CHOICE` moves show a picker.
- **Chess-family games subclass `agp.chesslike.ChessLike`** (board model, slider/leaper move-gen, attack/check, draws, serialize/render). A variant just sets `WIDTH/HEIGHT`, a `PIECES` movement table (`{letter: (slide_dirs, leap_offsets)}`), `HEAVY` material, `setup_board()`, and four strategies — `PAWN` (`StandardPawn`/`BerolinaPawn`), `PROMOTION` (`LastRankPromotion`/`GrandPromotion`), `CASTLING` (`StandardCastling`/`NoCastling`), and `DROPS` (`NoDrops` default / `CrazyhouseDrops`). See `games/{chess,berolina,grand_chess,los_alamos_chess}` (~40 lines each). Validate new variants with a perft check against known node counts.
- **Drops / off-board reserve** (the first UI capability investment, shipped via Crazyhouse): the `DROPS` strategy adds a per-seat `hands` reserve + a `promoted`-square set to `CState` (both no-op/absent unless `DROPS.enabled`, so the other ~20 variants are byte-identical). A drop move is the string `"L@c,r"`; captures bank into the reserve; `render()` emits `spec.reserve = {seat: {letter: count}}`. **No server change** — the enforced path is `move in legal_moves`. The web `Board.jsx` shows two reserve trays (seat 1 top / seat 0 bottom): click your chip → legal drop targets highlight → click to drop. Reuse this for Shogi (its own `DropRules` for drop-zone/nifu) and the Morris family (different board, custom adjacency). Anchor with python-chess `CrazyhouseBoard` (see `games/crazyhouse/_diff_pychess.py`, manual/one-time).
- **Randomness without a chance node:** roll/deal in `apply_move`/`initial_state` and STORE the outcome in state (the die / dealt cards); set manifest `has_randomness: true`. The generic UI/bot then need no CHANCE handling (EinStein, Onitama). `num_players` is a fixed property read before any state exists, so it can NOT be a manifest option — a variable-player game picks one count (Chinese Checkers is fixed 6-seat).

## Server
- `DATABASE_URL` (default `sqlite:///./agp.db`). Uploads run game code IN-PROCESS (RCE) → gated, closed by default: `AGP_ADMIN_EMAILS` allowlist or `AGP_ALLOW_OPEN_UPLOADS=true`. Real sandbox is deferred.
- Game registry caches at startup; `POST /api/games/upload` hot-reloads it.

## Adding games at scale (the "game factory")
- The bundled library (~54 games) was largely built by an autonomous loop. `GAME_BACKLOG.md` is the capability map (the abstract-game universe bucketed by the platform primitive each needs); `GAMES_QUEUE.md` is the live status + the merge gate + escalation digest. Read both before a bulk game effort.
- The factory is a reusable dynamic **Workflow** (script under the session's `workflows/scripts/game-factory-*.js`): per game, one agent implements the package and a *different* agent adversarially verifies it; the orchestrator owns a deterministic merge gate (auto-merge on a published anchor or a clean independent review; queue only genuine ruleset decisions / new board shapes). See the `game-factory-loop` memory.
- **Anchor chess-family games with perft**; for variants, **python-chess / shakmaty** (install in `.venv`) are gold-standard differential oracles — use them for one-time verification only.

## Testing
- Engine: `cd engine && PYTHONPATH=. python3 tests/test_games.py`.
- **Per-game `selftest.py`**: a game package may ship `games/<uid>/selftest.py` — a standalone script asserting its correctness anchor (perft / rule positions). `tests/test_games.py::test_package_selftests` runs every one. **Selftests MUST be pure-stdlib** (import only `agp` + their own game; no `python-chess`/numpy) and fast — the suite runs them under system `python3` where pip-only deps are absent.
- **Don't trust a piped suite exit code:** `python3 tests/test_games.py | tail` returns the pipe's (tail's) exit, always 0 — run it unpiped to a file with `echo SUITE_EXIT=$?`, or grep for `all tests passed`.
- **"Win as event" + selftests:** `winner` is set only inside `apply_move`, so `is_terminal` is False on a hand-built no-move/stuck position. Test stuck/annihilation wins by REACHING them via `apply_move`, not by constructing the dead state.
- **Restart the backend to pick up a NEW game** (don't trust auto-reload for new packages). Kill STRICTLY by port; do NOT `ps`/`grep`/`pkill` for `uvicorn server.app` — your own restart command's line contains that string, so the match kills your shell (exit 143/144). Then start uvicorn via `run_in_background` with no grep.
- Backend via `TestClient`: call `server.db.init_db()` first (bare TestClient skips the startup lifespan → no tables). Use `httpx` in `.venv` (not `requests`).
- Browser checks use pinchtab: click custom buttons by **ref**; click SVG board cells via `[data-cell="c,r"]` CSS and non-a11y SVG elements (wall ghosts, cards) via a class selector with `--mode dom`; coordinate clicks are flaky — verify with a screenshot. **Sessions expire on long runs** — recreate with `pinchtab session create` on a `401 bad_session`. **In Quick Play you must click the game CARD to select it BEFORE hotseat/START**, else it launches the default game (search by a unique term — e.g. "Baduk" for Go).

## Conventions
- Frontend: one generic `Board` renderer; all board types (`square`/`hex`/`polygons`) go through a unified polygon shape model — `polygons` games supply each cell's vertices. No per-game UI. Seat colors in `web/src/colors.js`.
- **RenderSpec capabilities (opt-in, generic; all 7 backlog UI gaps now shipped — see `GAME_STATUS.md`):** `reserve` trays + click-to-drop (move `"L@c,r"`); **>2-seat** (6 colours in `colors.js`; QuickPlay seats `view.num_players` — MCTS already backs up per-player payoffs, no engine change); `board.lines` (under-cell grooves) & `board.overlay` (over-cell lines, e.g. TwixT bridges), both in cell-coord space; `board.tints` (`{cellId: colour}` terrain/edges); `board.walls` (`{h,v}` groove slots → ghost-click placement, Quoridor); `piece.stack: [owner,…]` (tower glyph, Lasca); `board.cards` (movement-pattern strip, Onitama). `GAME_STATUS.md` (via `engine/tools/gen_game_status.py`) is the live per-game catalogue — regenerate after adding a game.
- Porting a Zillions of Games (.zrf) game: use the `zillions-to-platform` skill (`.claude/skills/`).
- Git: solo project, commit directly to `main`.
