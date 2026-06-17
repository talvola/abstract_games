# Abstract Games Platform — Requirements & Design

> A web platform for playing abstract board games **asynchronously against humans**
> (correspondence-style) or **against a computer opponent**, where new games are added as
> **drop-in packages** — ideally authored by a Claude Code session against a documented spec,
> then uploaded and registered with no redeploy.

## 1. Why build vs. adopt (research summary)

We evaluated the existing landscape (June 2026):

| Platform | Async vs humans | Computer opponent | Add games | Stack | Self-host | License |
|---|---|---|---|---|---|---|
| **AbstractPlay** | ✅ proven | ⚠️ hooks only (AiAi bridge) | code a TS class + **rebuild/redeploy** | React + TS Lambda + DynamoDB | AWS-locked | MIT |
| **boardgame.io** | ✅ (server + DB adapter) | ⚠️ built-in MCTS, basic | code JS/TS object, **compiled in** | JS/TS (Node) | ✅ Render | MIT (near-dormant) |
| **OpenSpiel** | ❌ no platform | ✅✅ strong | code C++/Python class | Python+C++ | container | Apache-2.0 |
| **Ludii** | ❌ desktop | ✅✅ best general AI | `.lud` DSL (best authoring) | Java | ❌ | ❌ non-commercial |
| **Zillions/Polygamo/Axiom** | ❌ | ✅ | ZRF DSL | Win/C#/Forth | dormant | mixed |
| **Board Game Arena** | ✅ | ❌ | PHP+JS "BGA Studio" | PHP/JS | ❌ closed | closed |
| **GGP/GDL-II, RBG/RG** | ❌ | ✅ general (mediocre/game) | declarative DSL | academic | research | open/unclear |
| **Little Golem / Yucata / MindSports** | ✅ | ❌ | owner hand-codes | bespoke | ❌ | closed |

**Decisive finding:** *no* platform supports a runtime-loadable game **package** (drop a ZIP, it
appears, no redeploy). Every one bakes games into the source tree and redeploys. So the drop-in
authoring loop is custom work **regardless** of base — which removes the main reason to adopt a
heavy foundation. Combined with the Python preference and "Claude Code generates the module" being
the real game-creation engine (so we don't need an inherited game library), the choice is:

**Build a thin, server-authoritative Python platform**, borrowing two ideas:
- **AbstractPlay's render-spec** (`APRenderRep`): games emit a JSON *description* of the board; one
  generic frontend renderer draws SVG for **all** games → authors never touch UI.
- **OpenSpiel's game API shape** (`legal_moves`/`apply`/`is_terminal`/`returns` + optional chance
  nodes) for the module contract and to make a single generic MCTS work on any game.

## 2. Locked decisions

- **Foundation:** custom, Python.
- **Trust model:** trusted authors only (you + Claude Code + a few). Modules load in-process / via
  subprocess; **no heavy sandboxing now**. Keep the loader behind an interface so a WASM/container
  sandbox can be added later for public uploads. *Don't spend build time on sandboxing — spend it on
  gameplay.*
- **AI:** one **generic MCTS** (UCT) that plays any conforming module; **ISMCTS** variant for
  stochastic/hidden-info games. Honest expectation: *decent, not strong*; per-game tuning is future.

## 3. The game-module contract (the heart of the system)

A game is a **package** (directory, distributed as a ZIP):

```
oust/
  manifest.json        # metadata (see below)
  game.py              # implements the Game interface
  rules.md             # optional human rules text
  assets/              # optional images/icons
```

### manifest.json
```jsonc
{
  "uid": "oust",                  // unique, stable id
  "name": "Oust",
  "version": "1.0.0",
  "engine_api": "1",              // contract version for forward-compat
  "author": "Erik / Claude Code",
  "players": { "min": 2, "max": 2 },
  "has_randomness": false,        // chance nodes used?
  "hidden_info": false,           // player-specific views?
  "tags": ["connection", "hex", "placement"],
  "bgg_url": "https://boardgamegeek.com/...",
  "description": "Capture-by-placement on a hex board."
}
```

### Game interface (Python ABC)
```python
class Game(ABC):
    # --- setup ---
    def initial_state(self, num_players: int, options: dict, rng) -> State: ...

    # --- core loop ---
    def current_player(self, s: State) -> int        # or CHANCE for stochastic resolution
    def legal_moves(self, s: State) -> list[Move]
    def apply_move(self, s: State, m: Move, rng) -> State   # rng only used by stochastic games
    def is_terminal(self, s: State) -> bool
    def returns(self, s: State) -> list[float]        # per-player: +1/0/-1 or scores

    # --- persistence & notation ---
    def serialize(self, s: State) -> dict             # JSON-able; round-trips
    def deserialize(self, d: dict) -> State
    def move_to_str(self, m: Move) -> str
    def parse_move(self, text: str) -> Move

    # --- presentation (no pixels) ---
    def render(self, s: State, perspective: int | None) -> RenderSpec

    # --- optional, only for hidden-info games ---
    def player_view(self, s: State, player: int) -> State   # default: identity
```

- **Default games are deterministic + perfect-info** — `has_randomness`/`hidden_info` false, ignore
  `rng`/`player_view`. Randomness/hidden info are opt-in to keep the common case trivial.
- **RenderSpec** is JSON describing geometry (board type: square/hex/graph), pieces, highlights, and
  legal-move targets. A single SVG renderer interprets it for every game.
  - **Strong option: adopt AbstractPlay's `@abstractplay/renderer`** (MIT, JS) on the frontend and
    emit a compatible spec from Python — it already renders hex/square/stacking boards from JSON and
    would save the bulk of frontend work. Decide in Phase 1.

### Conformance harness (cheap, high-leverage)
A validator that, given a package: imports it, plays **N random self-play games** to terminal, and
checks — legal_moves non-empty until terminal, apply produces valid states, terminal reached within
a move cap, `returns` well-formed, `serialize`→`deserialize` round-trips, `render` returns a valid
spec. **This doubles as the target Claude Code generates against** ("make it pass `validate`").

## 4. Architecture

```
                React SPA (Vite)  ──────────────┐  Vercel or Render static
                  generic SVG renderer          │
                          │ REST/WS             ▼
   FastAPI app (Render web service) ── Postgres (matches, users, move history, game registry)
        │                    │
        │ enqueue            │ import & run modules (in-process / subprocess)
        ▼                    ▼
   Worker (Render)       Module registry on disk / object storage
   - bot moves (MCTS)        (uid → version → package path)
   - notifications
```

- **Backend:** FastAPI + SQLAlchemy + Postgres. Async-friendly, Pythonic.
- **Worker:** background queue (Arq/RQ/Celery) for (a) computing bot moves off the request path and
  (b) sending "your turn" notifications. A persistent worker is also why we host on **Render, not
  Vercel serverless** (the game/bot engine is stateful and long-running).
- **Frontend:** React + Vite (consistent with your current Yodd/Oust). Generic renderer + a move
  input layer driven by the RenderSpec's legal-move targets (click a target → submit move).
- **Auth:** simple — email magic-link or email/password. Keep minimal.
- **Match model:** `(game_uid, players[], state stack/history, current_player, status, deadlines)`.
  Store full move history → enables replay, undo-request, and ISMCTS determinization.
- **Bot as opponent:** a bot is just a "player" whose turns the worker fills via generic MCTS with a
  configurable iteration/time budget; works identically in correspondence and live play.

### Module registration flow
1. Admin uploads a ZIP.
2. Server validates manifest + runs the **conformance harness** (in a subprocess).
3. On pass → store package, insert/upgrade registry row keyed by `uid` + `engine_api`.
4. Game appears in the lobby. No redeploy.

## 5. The Claude Code authoring loop (the headline workflow)

Deliver a small local toolkit so a Claude Code session can build a game end-to-end:
- `SPEC.md` — the precise `Game` contract + RenderSpec schema (Claude reads this).
- A **template package** (`cookiecutter` or a copy-me folder).
- A CLI:
  - `agp validate ./oust` — run conformance harness
  - `agp playtest ./oust [--bot]` — random or MCTS self-play, prints result stats
  - `agp render ./oust` — open a local preview of the board
- Loop: *Claude reads SPEC.md → writes `game.py` + `manifest.json` → runs `agp validate`/`playtest`
  until green → you upload the ZIP → it's live.*

## 6. Phased plan

- **Phase 0 — Contract & proof (local only).** Define `Game` interface + RenderSpec + conformance
  harness + CLI. **Port Yodd or Oust** to the contract as the first module. No server. *Validates the
  abstraction before any infra.*
- **Phase 1 — Single-player web.** React app + generic renderer; pick a registered game, play
  **hotseat or vs generic MCTS bot**. No accounts. Decide renderer (adopt AbstractPlay's vs custom).
- **Phase 2 — Async humans.** FastAPI + Postgres + accounts + correspondence matches + "your turn"
  notifications + lobby/challenges.
- **Phase 3 — Drop-in packages.** ZIP upload + validation pipeline + registry UI. Bot-as-opponent in
  correspondence via worker.
- **Phase 4 — Polish.** Ratings/Elo, move clocks/timeouts, spectating, replay viewer, rules modals
  (you already have BGG links + rules in Yodd/Oust).
- **Future.** Sandboxing for untrusted public uploads (WASM/container) · stronger/per-game AI
  (heuristics or AlphaZero-style) · tournaments.

## 7. Risks & honest caveats

- **Generic AI is mediocre per-game.** Set expectations; plan per-game tuning later. (Confirmed
  across boardgame.io MCTS and GGP players.)
- **RenderSpec generality is the hardest design problem** — one renderer for hex/square/graph/
  stacking/cards is real work. Mitigate by reusing AbstractPlay's renderer and/or scoping to the
  board families you care about first.
- **Stochastic/hidden-info** (ISMCTS, `player_view`, chance nodes) adds real complexity — kept
  **opt-in** so it never taxes the common deterministic case.
- **Engine API versioning from day 1** (`engine_api` in manifest) so old modules keep working as the
  contract evolves.

## 8. Open questions to resolve before/at Phase 1

- Adopt `@abstractplay/renderer` (fast, MIT, but couples your spec to theirs) vs. roll your own
  RenderSpec + renderer (full control, more work)?
- First game to port (Yodd vs Oust) and exact board-geometry primitives needed.
- Notification channel for "your turn" (email vs web push) and whether move clocks are in v1.
