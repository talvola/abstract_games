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

## 8. Features to borrow from Game Courier (chessvariants.com)

[Game Courier](https://www.chessvariants.com/play/pbm/) (Fergus Duniho's play-by-mail system) is
the closest existing thing to what we're building: a correspondence platform hosting *hundreds* of
abstract/chess-variant games, where new games are added as data rather than redeployed code. It's
worth mining for features and one big design idea. (Note: the site 403s automated fetchers — use a
real browser / the `pinchtab` skill to read its pages.)

| Capability | Game Courier | Us (today) | Action |
|---|---|---|---|
| Async correspondence vs. humans | ✅ core | planned (Phase 2) | build as planned |
| "Your turn" notifications | ✅ email + "Your Games" dashboard | — | Phase 2 |
| Invitations | ✅ **open** challenges + **personal** invites by email/link | — | Phase 2 lobby/challenges |
| Correspondence time controls | ✅ Grace (per-move) + Reserve bank (Spare/Min/Extra/Bonus/Max) | — | Phase 4 (model on theirs) |
| Per-game ratings | ✅ | — | Phase 4 |
| Move entry by **typed notation** | ✅ (notation + Preview) *and* click/touch | click-to-move only | add: our moves are already strings → expose a notation input |
| Move log + **replay** of finished games | ✅ | partial (full history stored) | Phase 4 replay viewer |
| Public game browsing / ranking | ✅ sortable, ranked by popularity | — | Phase 4 spectating + index |
| In-game **comments / kibbitzing** | ✅ per-move comments + site-wide feed | — | new: per-move comment thread (great for correspondence) |
| **Unenforced (honor-system) games** | ✅ — play any variant with *no* rule code | ✗ engine always enforces | **design idea, see below** |
| Rule enforcement | GAME Code (Turing-complete server lang) | Python `Game` module | ours is stronger-typed; keep |
| Authoring barrier | wizard generates GAME Code for simple variants | Claude Code writes the module against `SPEC.md` | our Claude-authoring loop is the analog; see import skill |
| User-generated content | anyone authors presets in Edit mode | trusted-author uploads (Phase 3) | already covered |

**Prioritized additions** (slot into existing phases):
- **Phase 2:** open + personal invitations (personal = locked to a user id; open = appears in a
  public list + "what's new" feed); "your turn" email + a "Your Games" dashboard showing whose turn
  it is. **Resign by a reserved move token** and a draw-offer/agreement action (Game Courier types
  literal `resign`; we already model non-cell actions like `"pass"`/`"swap"` as buttons, so
  `"resign"`/`"offer-draw"`/`"accept-draw"` are the same mechanism).
- **Phase 4:** correspondence time controls — copy Game Courier's **two-axis model**: *Grace Time*
  (a per-move grace period that doesn't touch the bank) + *Reserve Time* (a whole-game bank with
  Spare/Min/Extra/Bonus+BonusPeriod/Max knobs). Pure days-per-move = Grace alone; accumulating bank =
  Spare+Extra. Also: per-game ratings, replay viewer, public game index ranked by activity — all
  already on the roadmap; Game Courier is the reference implementation to copy behavior from.
- **New, small, high-value:** **per-move comment threads / annotations** (kibbitzing). Correspondence
  play is social; a comment box attached to each move/match is cheap and a big engagement lever.
  Game Courier even has a *Record/annotate* mode with branching variation lines (`|`-prefixed) — a
  nice later target for a replay/analysis viewer. And a **typed-notation move input** alongside
  click-to-move — nearly free since our moves are already canonical strings (`"2,1>3,4"`, `"swap"`).
  Note Game Courier's move syntax is a useful precedent: it knows *no* game's rules and relies on
  **full algebraic notation** (`P e2-e4`, `;`-chained sub-moves, promotion `q-e8`, drop `b*5e`,
  removal `e4-`) — structurally the same idea as our `>`-separated paths with `=CHOICE` suffixes.

**Big design idea — an "unenforced" / freeform game mode.** Game Courier's reach (hundreds of games)
comes from *not requiring* rule code: a preset can just define a board + pieces and let players move
freely on the honor system, with no legality checking. That's the opposite of our strict, conformance-
validated engine — and it's a complementary mode, not a replacement. A freeform module type (board
geometry + piece set + initial setup, **no `legal_moves`/`is_terminal` logic**) would let us host a
long tail of variants in minutes, with the bot disabled and "anything goes" move entry, then graduate
the popular ones to fully-enforced engine modules. **Shipped** — `agp.FreeformGame` + a manifest
`"mode": "freeform"`, a conformance branch, server move-relay + draw-agreement + bot-disable, and a web
free-drag input mode, with a demo game (**Freeform Board (8×8)**, the "Sandbox" category) verified
in-browser (see `engine/FREEFORM_MODE.md`). The import skill's freeform path is also wired: a
`parse_fen` helper + a `freeform_from_settings.py` converter turn a Game Courier settings file
(declarative `code`/`cols` only — no GAME-Code) straight into a `FreeformGame` package.

### Importing games from Game Courier / chessvariants.com
Erik's ask: given a URL like `…/play/pbm/play.php?game=Univers+Chess&settings=default` *or* just
"import N Chess from Game Courier," locate the rules, board, and piece movements and emit an engine
module. Feasible as a **`gamecourier-to-platform` skill**, sibling to `zillions-to-platform`. The
mechanics line up better than expected:

- **How a game is addressed.** A preset is `play.php?game=<Name>&settings=<basename>`. The `game`
  name → a game id (lowercase, spaces→`_`) that locates logs/settings/rules; `settings` is the
  basename of a **PHP settings file**. That file's raw source is retrievable programmatically:
  **`/play/pbmsettings/showsource.php?game=<Name>&settings=<basename>`**. So "import 123456 Chess"
  resolves to: hit `showsource.php` for its settings + fetch its rules page. (Both 403 bots → fetch
  via a real browser / the `pinchtab` skill, which Erik is logged into.)
- **What's mechanically parseable (the easy 60%).** The settings file is just `$default[...]`
  assignments. Board **geometry and starting position are fully declarative**: `code` (an *extended
  FEN* — digits = N empty squares, `/` = end-of-rank, `-` = non-cell/hole, `{NB}` = multi-char piece
  label, lowercase/uppercase = Black/White), `cols`, `files`/`ranks` (coordinate labels), `board`
  (checker pattern), `shape` (square / hex / circular / custom-grid / custom pixel-mapped), `sides`.
  This maps almost 1:1 onto our board model + `setup_board()` and tells us immediately whether a game
  is square/hex (we support both) or an exotic topology (defer). Piece **set/graphics** (`set` or an
  inline JSON custom set) we ignore — we have our own renderer.
- **What is NOT declarative (the hard 40%): movement + rules.** These live as imperative **GAME Code**
  in seven fields (Pre-Game / Pre-Move{1,2} / Post-Move{1,2} / Post-Game{1,2}) plus shared include
  files (`chess`, `chess2`, `fairychess`, `xiangqi`, `shogi`). Two sub-cases:
  - *Slider/leaper pieces* are written as `def X = or`-chains of `checkleap from to Δf Δr` (leaper)
    and `checkride from to Δf Δr` (rider). **Those `(Δfile,Δrank)` pairs ARE our `(slide_dirs,
    leap_offsets)`** — a near-mechanical translation into a `ChessLike` `PIECES` table. Same for
    games authored in **Betza/"funny" notation** via the fairychess include / the GAME-Code wizard
    (Betza atoms → offsets for the rider/leaper subset).
  - *Everything else needs a human/Claude in the loop:* pawns (divergent move≠capture, double-step,
    en-passant, promotion — but our `StandardPawn`/`PROMOTION`/`CASTLING` strategies already cover the
    common cases), and genuinely out-of-model pieces — **hoppers/Cannons, locust/long-leaper capture,
    bent/lame leapers (Xiangqi horse), drops, swaps, multi-move turns**. These fall back to a generic
    `Game` with hand-written `legal_moves`.
- **Translation strategy** (mirrors the Zillions skill — Claude *reads* the source and writes the
  module; not a literal transpiler): parse `code`+`cols`+`shape`+`files`/`ranks` → board + setup
  mechanically; read movement from the **human rules page** (prose is clearer than reverse-engineering
  GAME Code) cross-checked against the `def` lines for the slider/leaper offsets; emit a `ChessLike`
  subclass when the game fits the chess family (most do — ~40 lines), else a generic `Game`. Produce
  `manifest.json` (+ `bgg_url`/source-credit link), `game.py`, and `rules.md` written from the rules
  page. Validate with `agp validate`; for chess variants add a **perft check** against known counts.
- **The unenforced mode is the cheap on-ramp.** A freeform import (board + pieces + setup only, *skip*
  movement logic) is automatable **from the settings file alone** — no GAME Code interpretation — so
  we can stand up the long tail of variants in minutes and selectively graduate popular ones to
  fully-enforced modules. This is the single highest-leverage reason to add the freeform mode.
- **Etiquette:** chessvariants.com is a volunteer hobbyist site with clear content ownership. Import
  for personal/playtest use, credit the author + link the source, and don't bulk-scrape.

## 9. Open questions to resolve before/at Phase 1

- Adopt `@abstractplay/renderer` (fast, MIT, but couples your spec to theirs) vs. roll your own
  RenderSpec + renderer (full control, more work)?
- First game to port (Yodd vs Oust) and exact board-geometry primitives needed.
- Notification channel for "your turn" (email vs web push) and whether move clocks are in v1.
