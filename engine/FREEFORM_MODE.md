# Freeform (unenforced) game mode

Status: **shipped — engine + server + web, with a demo game, verified in-browser.**

Game Courier hosts hundreds of variants because a preset can be *unenforced* — it
defines a board + starting position and lets players move pieces freely on the
honor system, with no legality checking and the result set by an explicit action.
This is the complement to our strict, conformance-validated engine, and the cheap
on-ramp for porting the long tail (and the freeform path of the
`gamecourier-to-platform` skill). See PLATFORM_PLAN.md §8.

## The one design decision (resolved here, confirm if you disagree)

**Freeform is a first-class _mode_, not a degenerate strict game.** A game is
freeform when `manifest["mode"] == "freeform"` (equivalently its class sets
`enforced = False`). Consequences we accept:

- The **generic MCTS bot does not play freeform games** (there are no rules to
  search). Freeform is human-vs-human only; "vs bot" is hidden for these games.
- **Conformance is checked on a lighter path** (no random self-play to a terminal —
  a freeform game has no algorithmic terminal). The strict path is untouched.
- The **server is a move-relay** for freeform matches: it accepts any
  structurally-valid move and ends the match only on an explicit result action.

The alternative — forcing freeform into the strict `Game` contract (enumerate the
full move cross-product, fake a terminal) — is uglier and buys nothing, so it was
rejected.

## What's built (engine, in this repo)

- **`agp/freeform.py` — `FreeformGame(Game)`** base. An author subclasses it and
  supplies only `setup_board()` (+ `WIDTH`/`HEIGHT`, or `board_spec()` for hex).
  It implements the whole `Game` contract generically:
  - moves: `"fc,fr>tc,tr"` (free, no legality; optional `=X` retype),
    `"@fc,fr"` (remove), `"pass"`, `"resign"`;
  - `legal_moves` returns only the action tokens (`pass`/`resign`) — board moves
    are unrestricted free-drag, validated by *shape* elsewhere, not enumerated;
  - `is_terminal`/`returns` driven by an explicit `result`; `resign` loses for the
    mover; `serialize`/`deserialize` round-trip; `render` emits the standard
    RenderSpec with a "unenforced (honor system)" caption + last-move highlight;
  - marker attribute **`enforced = False`**.
- **`agp/conformance.py`** branches on `_is_freeform(game, manifest)` →
  `_check_freeform(...)`: initial state renders + is non-terminal, serialize
  round-trips (initial + after a free move), a free move is pure, and `resign`
  yields a well-formed terminal. No legal-move/termination requirement.
- **`agp/__init__.py`** exports `FreeformGame` / `FState`.
- **`tests/test_games.py::test_freeform_mode`** exercises it end-to-end
  (`agp validate`-equivalent `check()` passes; free capture, promotion-as-relabel,
  resign-terminal). Full suite green.

So an unenforced game package validates today:
`manifest.json` with `"mode": "freeform"` + a `game.py` subclassing `FreeformGame`.
Reference package: **`engine/games/freeform_chess`** ("Freeform Board (8×8)") — a
standard chess array with no rules, in the **Sandbox** category.

Draw-agreement is handled **inside the engine state** (no DB column): `offer-draw`
sets `draw_offer` and passes the turn; the opponent sees `accept-draw` (→ draw) /
`decline-draw`, and any ordinary move implicitly declines. Because the offer lives
in the serialized state, it survives correspondence polling with no schema change.

## What's built (server)

`server/games.py` + `server/app.py`:
- `is_freeform(game)` (reads `enforced`) and `freeform_move_ok(game, state, move)`
  — a **structural, topology-agnostic** validator: an action token, or a
  `from>to`(`=X`)/`@cell` whose source cell is currently occupied (occupancy read
  from `render()` so it works for any board type).
- The correspondence move route and the stateless quick-play route **branch**:
  enforced → `legal_moves` membership; freeform → `freeform_move_ok` (server is a
  move-relay, not a referee).
- `new_match` **rejects a bot opponent** for freeform games (400); the catalogue
  (`/api/games`) exposes `mode` + `freeform`, and `position_view` exposes
  `freeform` so the client can switch input modes.
- Resign uses the existing `/resign` endpoint; draws go through the engine moves.

## What's built (web)

`web/src/`:
- `Board.jsx` gains a **`freeform` input mode**: select any piece → click any
  square to submit `from>to` (no legal-move restriction); only the selected source
  is highlighted (no 64-target flood). Cells carry a `data-cell` attribute (stable
  selector for testing). Friendly labels for `offer-draw`/`accept-draw`/
  `decline-draw`/`resign`/`pass`.
- `MatchPlay.jsx` / `QuickPlay.jsx` pass `freeform`; `MatchPlay` routes resign
  through its dedicated button (filters it from the action row).
- `QuickPlay.jsx` + `Lobby.jsx` **disable "vs Computer"** for freeform games and
  show an "unenforced — honor system" note.

Verified in-browser (Quick Play hotseat): an illegal-in-chess move applies, the
Pass/Resign/Offer-draw actions show, and offer → Accept/Decline → "Draw" works.

## Still optional / future

- **Importer.** Wire the `gamecourier-to-platform` freeform path (§7 of the skill)
  to emit a `FreeformGame` subclass from a Game Courier settings file alone.
- **Setup edits / piece drops:** a generic "place piece X on cell" move (the
  engine already supports `@cell` removal + `=X` retype) once the UI needs it.
- **Turn model:** currently strict alternation; Game Courier allows a looser
  "side to move may make several piece moves" — revisit if it feels wrong in play.
