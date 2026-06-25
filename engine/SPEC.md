# Authoring a game module (engine_api 1)

This is the contract a Claude Code session generates against. **Goal: make
`agp validate <yourgame>` pass**, then sanity-check with `agp render` / `agp playtest`.

## Package layout

```
yourgame/
  manifest.json     # metadata (required)
  game.py           # one subclass of agp.game.Game (required)
  rules.md          # human rules (recommended) — shown in-app via a "Rules" button
  assets/           # optional images
```

Distribute as that folder or a `.zip` of it (flat, or a single top-level folder).

**`rules.md`** is a one-page Markdown writeup of the rules **as implemented** — the
local source of truth (variants/draw rules differ between sources, so document
what *this* package actually does). The server serves it at
`GET /api/games/<uid>/rules` and the web UI renders it in a "Rules" dialog, with
a link to the official rules if `manifest.bgg_url` is set. Supported Markdown:
headings (`#`/`##`/`###`), `**bold**`, `*italic*`, `` `code` ``, `-`/`1.` lists,
`[links](url)`, and paragraphs.

## manifest.json

```jsonc
{
  "uid": "yourgame",            // unique, stable, lowercase_snake
  "name": "Your Game",
  "version": "1.0.0",
  "engine_api": "1",            // must match the engine
  "author": "...",
  "players": { "min": 2, "max": 2 },
  "has_randomness": false,      // true if apply_move/initial_state use rng
  "hidden_info": false,         // true if you implement player_view
  "category": "N-in-a-row",     // groups the game in the lobby; see below
  "tags": ["square"],
  "bgg_url": "https://boardgamegeek.com/...",   // optional
  "options": {                  // optional rule/variant selectors (shown as dropdowns)
    "size": { "choices": [4,5,6], "default": 5, "label": "Board size" },
    "sim_connection": { "choices": ["draw","win"], "default": "draw",
                        "label": "Simultaneous connection",
                        "labels": { "draw": "Draw", "win": "Win for mover" } }
  },
  "description": "..."
}
```

`options` reach `initial_state(options=...)`; branch on them and store anything
the rest of the game needs in the state. **Small rule variations belong in an
`option`** (e.g. board size, a tie-break rule, a rule toggle) — the lobby shows
each as a dropdown. Make a **separate game package** only when the variant is a
distinct game with its own identity/name/strategy.

**`mode`** (optional, default `"enforced"`). Set `"mode": "freeform"` for an
*unenforced / honor-system* game: a board + starting position with no movement or
win rules (players move freely; the result is set by resign/agreement). Such a
game subclasses **`agp.FreeformGame`** and implements only `setup_board()` (+
board geometry) — see `agp/freeform.py` and `FREEFORM_MODE.md`. Conformance checks
freeform games on a lighter path (no self-play); the generic MCTS bot does not
apply to them.

## The Game interface (`agp.game.Game`)

Implement these. See `games/tic_tac_toe/game.py` (minimal) and `games/oust/game.py`
(captures, multi-placement turns, pass handling, event-based win) as references.

| Method | Contract |
|---|---|
| `num_players` (property) | how many players |
| `initial_state(options=None, rng=None)` | starting state; `options` = variant settings, `rng` = `random.Random` |
| `current_player(state)` | 0-based index to move (or `agp.CHANCE` for a pending random event) |
| `legal_moves(state)` | list of move strings; **non-empty unless terminal** |
| `apply_move(state, move, rng=None)` | return a **new** state; **must not mutate** `state` |
| `is_terminal(state)` | bool |
| `returns(state)` | per-player payoff list at terminal (e.g. `+1/0/-1`), length `num_players` |
| `serialize(state)` | JSON-able dict; **must round-trip** with `deserialize` |
| `deserialize(data)` | inverse of `serialize` |
| `render(state, perspective=None)` | JSON-able RenderSpec (see below); never pixels |
| `move_to_str` / `parse_move` | optional; default to identity on strings |
| `describe_move(state, move)` | optional; short label for the move log (state is *before* the move). Default = the raw move string; override for nicer notation (e.g. chess `Nb1-c3`) |
| `player_view(state, player)` | only for hidden-info games; default = full info |

### Hard invariants (checked by `agp validate`)

1. **Moves are strings** in your own notation (e.g. `"1,2"`).
2. **`apply_move` is pure** — never mutate the input state; return a fresh one.
3. **`serialize` round-trips** — `deserialize(serialize(s))` serializes identically and is JSON-able.
4. **Non-empty `legal_moves`** on every non-terminal state. If the player to move
   has no action, advance past them (a *pass*) inside `apply_move`, don't return `[]`.
5. **The game terminates.** No infinite play under random move selection.
6. **`returns` is well-formed** at terminal: length `num_players`, finite numbers.

### Modelling notes

* **A "turn" can be several moves by the same player.** Just keep
  `current_player` returning the same index until the turn ends (see Oust's
  capture chains). The engine and MCTS handle this automatically.
* **Win as an event, not a board predicate?** Store it in the state (Oust keeps
  a `winner` field) rather than recomputing from the board, when the opening
  position would otherwise look terminal.
* **Randomness** (dice/decks): use the passed `rng` in `apply_move` /
  `initial_state` and set `has_randomness: true`. (Generic MCTS plays these but
  isn't yet specialised for them — ISMCTS is future work.)

## RenderSpec

A JSON-able dict the generic renderer draws. Phase-0 shape:

```jsonc
{
  "board": { "type": "square", "width": 3, "height": 3 }
        // or { "type": "hex", "shape": "hexagon", "size": 7 },
  "pieces":     [ { "cell": "1,2", "owner": 0, "label": "X" } ],
  "highlights": [ { "cell": "0,0", "kind": "last-move" } ],   // optional
  "caption": "Red to move"                                     // optional
}
```

Cell ids are your move-notation cell strings: `"col,row"` for square, `"q,r"`
(axial) for hex. The CLI's ASCII previewer understands `square` and `hex`.

**Optional per-piece fields** (the generic renderer honours these; all default off):
- `"label": "X"` — centre text glyph.
- `"stack": [owner, …]` — an ordered tower of owners (bottom→top); drawn as
  layered bands with a height badge (draughts towers — Lasca/Bashni/Focus/Lasca).
- `"shape": "ring"` — a hollow ring in the owner's colour (YINSH/GIPF rings).
  Add `"inner": <seat>` to draw a marker *inside* the ring, and/or `"label"`.
- `"shape": "marker"` — a small filled disc (a YINSH marker / flippable stone;
  flip = just emit the other `owner`).
- `"size": <1..~5>` — a "nesting" piece (Gobblet): the disc scales with size so a
  bigger piece visibly covers (gobbles) a smaller one. Emit ONLY the TOP piece of
  a nested cell (what's underneath is hidden, as in the physical game). Pair with
  the `reserve` tray for the off-board nested stacks (use the size digit as the
  reserve "letter"; drop move `"<size>@c,r"`).
- `"fill": "#rrggbb"` (and optional `"stroke"`) — override the seat colour for
  this piece (e.g. ZÈRTZ's neutral white/grey/black marbles, which aren't owned
  by a player).
- `"prongs": [0, 2, 5, …]` — **directional prongs** (Octi): a list of directions
  `0..7` (`0`=N/up, clockwise: NE, E, SE, S, SW, W, NW), each drawn as a short
  arrow radiating from the piece so you can read which way the pod can move/jump.
  (Directions are SCREEN-oriented: `0` points up. On a square board the renderer
  draws row 0 at the bottom, so up = the +row direction — the engine should emit
  prongs in this screen convention and map `0`→+row when moving.)
- (default, none of the above) — a normal filled disc.

`board.extent: [minX, minY, w, h]` pins the SVG viewBox to a fixed window
instead of fitting the current cells — use it for a **shrinking board** (ZÈRTZ:
emit only the rings that still exist as `cells`; removed rings then leave a gap
rather than the whole board rescaling between moves).

Board-level optional fields: `board.lines` (cosmetic connecting lines/arcs — 2pt
line, 3pt quadratic-Bézier arc, or N-pt polyline, each `[[x,y],…,"#colour"?]`),
`board.overlay` (same format, drawn *over* cells — TwixT bridges, Surakarta
loops), `board.tints` (`{cellId: "#colour"}` terrain fills),
`board.levels` (`{cellId: <int 1..4>}` per-cell **build height** — drawn as
stacked "wedding-cake" tiers for levels 1-3 with a blue **dome** cap at level 4
and a small height badge, *under* any worker piece on that cell; the
two-things-per-cell primitive for **Santorini** [building level + worker]; omit
ground/level-0 cells), `board.walls`,
`reserve` (off-board drop trays), `board.cards`,
`board.tiles` + `board.tokens` (the **path-tile** primitive for **Tsuro**: a
square board where each placed tile shows painted paths joining its 8 edge-notches,
and player markers sit on those notches). `board.tiles` = `{cellId: [[a,b]×4]}` —
four notch-pairs per placed tile, each drawn as a smooth path-arc joining notch
`a` to notch `b`. `board.tokens` = `[{cell, notch, owner}]` — a marker disc on a
cell's edge-notch in the owner's seat colour. **Notch numbering** (clockwise from
the top-left of the rendered cell): `0,1`=top side, `2,3`=right, `4,5`=bottom,
`6,7`=left, each at the side's third-points. For path-following across cells,
bordering notches align as: top↔bottom `0↔5 / 1↔4`, right↔left `2↔7 / 3↔6` (a
token exiting one cell's notch enters the neighbour at the matching notch).
`board.tracks` = `{cellId: [[a, b, "#colour"], …]}` — the **colour-track tile**
primitive for **Trax**: each segment joins two of the cell's 4 EDGE-MIDPOINTS
(`0`=top, `1`=right, `2`=bottom, `3`=left) in `colour` (a straight track for
opposite mids, a corner curve for adjacent ones). Use a growing board (emit only
the occupied + legal cells as `cells`, plus `board.extent` if you want stability). For a points-and-lines board
(Morris/alquerque/YINSH) use `"type": "polygons"` with explicit cell vertices +
`board.lines`. **`polygons` cells format (exact — the renderer crashes otherwise):**
`board.cells` MUST be a **list** of `{"id": "<cellId>", "points": [[x,y], …]}`
objects — NOT a dict keyed by id, and the vertex key is `points` (not `polygon`).
`board.lines`/`board.overlay` are lists of point-lists (each an N-point polyline)
in the same coordinate space as the cell vertices. (Renderer-format bugs are NOT
caught by `validate`/selftest — only by opening the game in the browser.)

### Move notation & click-to-move

A move is a **`>`-separated path of cell ids** (cell ids use `,`, so they never
clash with `>`). The web UI derives click-to-move from this:

- **Placement** games: a move is a single cell, e.g. `"2,3"` — one click.
- **From–to** games (chess-like): a move is `"from>to"`, e.g. `"2,1>2,3"` — click
  the source, then the destination. The UI offers only legal continuations.
- Multi-step paths (`"a>b>c"`) are supported too (e.g. chained captures).
- **Non-cell action moves** (a legal move that isn't a cell path, e.g. `"swap"`
  for the pie rule, or `"pass"`) render as a labelled button below the board.
- **Moves needing a choice** (e.g. pawn promotion): append `"=CHOICE"` to the
  move, e.g. `"2,4>2,5=Q"` / `"=R"` / `"=N"`. When a clicked destination matches
  several moves differing only by that suffix, the UI shows a small picker of
  the choices. (`CHOICE` is shown via a friendly name for `Q/R/N/B/K/P`.)

Use this convention for any game you want clickable. Other notations still
validate and play via the API.

### Categories

`category` groups your game in the lobby. Prefer an existing bucket so games
cluster well; common ones: **"N-in-a-row"**, **"Chess & chess-like"**,
**"Capture / annihilation"**, **"Connection"**. Anything else is fine and is
shown under its own heading (no category → "Other").

## The authoring loop

```
agp validate games/yourgame          # must print RESULT: OK
agp render   games/yourgame --moves 8 # eyeball the board + a few random moves
agp playtest games/yourgame --bot     # MCTS self-play; check results look sane
```
