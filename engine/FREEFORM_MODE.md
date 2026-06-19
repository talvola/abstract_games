# Freeform (unenforced) game mode — spike

Status: **engine foundation built + tested; server/web wiring pending.**

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

## What remains (separate PRs — touch server + web, can't verify headless here)

1. **Manifest/SPEC.** Document the `"mode": "freeform"` key (added a short note to
   `SPEC.md`). `mode` defaults to `"enforced"`.
2. **Server** (`server/`): for a match whose game `mode == "freeform"`:
   - accept a move if it is *structurally* valid — an action token, or a
     `from>to`(`=X`)/`@cell` whose cells lie on the board — instead of checking
     membership in `legal_moves`;
   - end the match only on an explicit result action; add a **draw-agreement**
     action pair (offer/accept) — `FreeformGame` currently handles `resign`;
     mutual-draw is a server-mediated handshake (or extend `apply_move` with
     `offer-draw`/`accept-draw` once the turn/seat model for it is decided);
   - **disable the bot opponent** (no MCTS enqueue) for freeform matches.
3. **Web** (`web/src/`): a freeform input mode on the generic `Board` — drag any
   piece to any cell (don't restrict to legal continuations), plus action buttons
   (pass / resign / offer-draw) and a small "set result" control; show an
   "Unenforced — honor system" badge. The renderer already draws the RenderSpec;
   this is an input-layer addition.
4. **Importer.** Wire the `gamecourier-to-platform` freeform path (§7 of the skill)
   to emit a `FreeformGame` subclass from a Game Courier settings file alone
   (board geometry + setup, no GAME-Code interpretation).

## Open sub-questions for the server/web pass

- **Turn model:** strict alternation (current `FreeformGame` flips `to_move` each
  move) vs. Game Courier's looser "side to move may make several piece moves."
  Strict alternation is simplest; revisit if it feels wrong in play.
- **Setup edits / piece drops:** Game Courier lets you add/remove pieces freely
  (`@`/place). `FreeformGame` supports remove + retype; a generic "place piece X on
  cell" move can be added when the web UI needs it.
- **Result entry trust:** honor-system result-setting (either player can declare)
  vs. requiring agreement. Start with resign + draw-agreement; defer free
  result-declaration.
