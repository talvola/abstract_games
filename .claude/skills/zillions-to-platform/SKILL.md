---
name: zillions-to-platform
description: Convert a Zillions of Games game (a .zrf rules file, e.g. a download from zillions-of-games.com) into an Abstract Games Platform game module. Use when the user wants to port/add a Zillions game, references a .zrf/.zsg file, a zillions-of-games.com submission, or asks to "convert this Zillions game".
---

# Zillions (.zrf) → Abstract Games Platform

Port a Zillions of Games game into a platform game module. The platform's game
contract is the target — **read `engine/SPEC.md` first** (the authority on the
`Game` interface, move notation, board types, and options). This skill is the
*procedure* for translating a ZRF into that contract. Iterate on it as you port
more games.

## 1. Get the game

Zillions submission pages have a download link `...submissions.cgi?do=download;id=N`
that **302-redirects** to `https://zillions-of-games.com/ftp/games/<Name>.zip` — you
can fetch that path directly (with `-L` to follow the redirect):
```bash
cd /tmp && curl -sL -A "Mozilla/5.0" "https://www.zillions-of-games.com/cgi-bin/zilligames/submissions.cgi?do=download;id=N" -o g.zip
unzip -o g.zip -d game && ls -R game
```
You get: a **`.zrf`** (plain-text rules), `.zsg` (saved games; the numbers in their
names are *solution move counts*, not cell counts), board **`.bmp`** images, and
`ReadMe`/`intro` text. View a board to ground-truth geometry:
```bash
python3 -c "from PIL import Image; Image.open('game/.../Wide4.bmp').save('/tmp/b.png')"
```
then Read `/tmp/b.png`. If you can't download, ask the user to paste the `.zrf`.

**The `.zrf` is NOT always the best source of truth.** For classic single-board
games it is. But many *modern* designer games on Zillions (e.g. the Luis Bolaños
Mures / Dieter Stein connection family) ship a **machine-generated, multi-board
`.zrf`** whose scoring/win logic is deliberately incomplete ("omitted for coding
simplicity" — komi, largest-group scoring, and even the win check are often not
wired up), while the bundled **`ReadMe` carries the complete, authoritative
ruleset**. And some bundles have only a boilerplate ReadMe with NO rules, plus a
Zillions catalog **blurb that is often wrong** (seen: Konobi's blurb says "like
Sokoban" — false). So: **prefer the designer's own published rules** (BGG,
spielstein.com, mindsports.nl, nestorgames PDFs) as the authority, cross-check the
ReadMe, and treat the `.zrf` as the tie-breaker for exact move geometry — NOT as
gospel. When the designer's site and the `.zrf` port disagree (e.g. Ordo's ordo-move
directions), **follow the designer and document the deviation in `rules.md`**.

## 2. Map ZRF sections → the contract

| ZRF | Platform |
|---|---|
| `(game (title ..)(description ..))` | manifest `name` / `description` |
| `(players A B)` `(turn-order A B)` | seat order — **first player listed/ordered = `to_move` 0** |
| `(board (grid (dimensions ..)(directions ..)) (kill-positions ..))` | the cell graph + geometry (see §3) |
| `(piece (name ..)(moves ..))` | per-piece move generation in `legal_moves`/`apply_move` (see §4) |
| `(board-setup (Player (Piece pos ..)))` | `initial_state` starting positions |
| `(zone (name z)(positions ..))` + `(win-condition (P)(absolute-config Pc (z)))` | win = piece `Pc` reaches a cell in zone `z` |
| `(loss-condition (P) stalemated)` | that player loses if they have no legal move |
| `(variant (title ..) (board ..)(board-setup ..))` | a manifest **option** (board size / rule toggle), not a separate game |

**Zillions defaults that are easy to miss:** with `(pass-turn false)`, a player
with **no legal move LOSES by default** (stalemate = loss), even if only one
side has an explicit `loss-condition`. Decide each side's no-move outcome
deliberately (win/lose/draw) and confirm against the readme's flavor text.

## 3. Decode the board geometry (the hard part)

A ZRF `grid` defines positions by dimensions; each cell id is the concatenation
of its dimension labels (e.g. row `"L"` + col `"12"` → `"L12"`). `directions`
give per-dimension integer offsets, e.g. `(n -1 -1)` = (row−1, col−1).
`kill-positions` removes grid points — **for triangular/exotic boards the killed
points are usually the tiling's vertices, not playable cells.**

Reconstruct cells and adjacency by BFS over the direction vectors, then map to a
RenderSpec board type (`square`, `hex` with `shape` hexagon/rhombus, or the
generic **`polygons`** type where the game supplies each cell's vertices). The
`(dimensions ...)` pixel deltas give cell centers for `polygons` rendering.

Reusable decode pattern (adapt offsets/bounds/kill-rule per game):
```python
DIRS = {"n":(-1,-1),"ne":(-2,1),"se":(-1,2),"s":(1,1),"sw":(2,-1),"nw":(1,-2)}
def kill(r,c): return (r-1)%3==0 and (c-1)%3==0          # from the ZRF kill pattern
def cells(maxR, maxC, start):
    from collections import deque
    ok=lambda p: 1<=p[0]<=maxR and 1<=p[1]<=maxC and not kill(*p)
    seen={start}; q=deque([start])
    while q:
        p=q.popleft()
        for dr,dc in DIRS.values():
            n=(p[0]+dr,p[1]+dc)
            if ok(n) and n not in seen: seen.add(n); q.append(n)
    return seen
```
Sanity-check the cell count and shape against the board image before proceeding
(e.g. FoxSox = a rhombus of triangles, 2·n² cells). For `polygons`, compute each
cell center from the dimension pixel deltas and its vertices from the direction
geometry; cell **orientation** (which of the paired directions are real edges)
follows a coordinate parity — derive it and verify against the BFS adjacency.

## 4. Translate piece moves

Each `(piece (moves ...))` is a cursor-based move generator (often via a `define`
macro). The mini-language:
- a bare **`<direction>`** steps the cursor one cell that way;
- **`add`** emits a move ending at the cursor's current cell (→ a legal move);
  `add q r b n` = promotion *choice*; `add-copy` = drop a new piece;
- **`(verify <pred>)`** aborts this branch unless the predicate holds at the cursor;
- **`(while <pred> ... )`** loops; **`cascade`** moves several pieces in one game
  move (castling), **`from`/`mark`/`back`** control the cursor;
- predicates test the cursor cell: `empty?`, `enemy?`, `friend?`, `not`, …

Note: during generation the move is **not yet applied** — predicates see the
*pre-move* board. Canonical patterns:
```
step    (dir add)                                   ; king/man one square
slide   (dir (while empty? add dir))                ; rook (+ (verify enemy?) add to capture)
cannon  ($1 (while empty? add $1) $1 (while empty? $1) (verify enemy?) add)  ; hop then capture
```
Also: **only directions landing on a real cell are legal** (a triangular cell's
orientation makes some invalid); a piece may list a **restricted** subset (e.g.
geese "rightward"); read **distance rules** carefully (Lines of Action moves *as
many cells as pieces on the line*); jumps/hops (checkers) leap an enemy to the
empty cell beyond, often chained and mandatory (see `move-priorities`).

**`symmetry`** remaps directions per player — moves/goals are written once and
mirrored for the opponent; expand both sides when porting.

In our move notation a move is a `>`-separated **path of cell ids**; emit the
visited cells (`"a>b"` for from-to, `"a>b>c"` for chains). A move needing a
choice uses a `=X` suffix (promotion); a non-cell action (pie swap, pass) is its
own token and renders as a button. See `engine/SPEC.md`.

**Cell ids must be numeric `"col,row"`/`"q,r"`** — the generic Board renderer only
treats a move as a click-to-move path when *every* `>`-segment matches
`^-?\d+,-?\d+$` (that's how it tells cell paths from action tokens like `swap`).
A ZRF uses alphanumeric labels (`E11`, `H8`); if you pass those through as cell
ids, every move is misclassified as an *action* and dumps into a button row
instead of click-to-move. Use numeric grid coordinates as the id (e.g. map the
label to `"colindex,rowindex"`) and keep the ZRF label only for `describe_move`.

## 5. Implement, validate, wire

1. Write `engine/games/<uid>/{manifest.json, game.py, rules.md, selftest.py}`
   against the contract. Pick a `category` (reuse an existing one if it fits); put
   variants/sizes in `options`; set `bgg_url` to the source page. Add a
   `describe_move` for readable move-log notation. **`rules.md`** is a one-page
   writeup of the rules *as implemented* (note any interpretation you had to make
   when the ZRF/source was ambiguous) — the UI shows it via a "Rules" button.
   Ship a **`selftest.py`** too (see §6).
2. **Guarantee termination** — if random play could loop, add a no-progress /
   ply-cap draw (conformance plays random games to a terminal).
3. **Scoring/win logic is usually the real porting work.** The territory/group
   games' `.zrf` ports don't enforce the win condition, so you implement it: a
   largest-connected-group flood-fill, an area count, a line-of-sight control test.
   Write these in plain Python from the ReadMe/designer rules. **A genuine tie must
   resolve to an honest DRAW** (`winner=None`, `returns [0,0]`) — NEVER invent a
   winner via a fallback tiebreak "that should be unreachable" (it usually isn't:
   an early symmetric double-pass ties, and a fake winner is an exploitable rule
   bug). If the designer says "draws are impossible," that's a claim about *full*
   boards — still implement the honest draw for the reachable tie.
4. `cd engine && PYTHONPATH=. python3 -m agp.cli validate games/<uid>` until
   `RESULT: OK`; then `playtest`/`render` to sanity-check.
5. Restart the backend (the registry caches game code at startup; kill by PORT
   only) and **browser-verify** the board (a RenderSpec bug is invisible to
   validate/selftest but white-screens the board): pinchtab → QuickPlay → click the
   game card → START → screenshot; confirm the board renders and a signature move
   works.

## 6. Anchor with a `selftest.py` + independent QA

- **`selftest.py` (pure stdlib — import only `agp` + your own game; no PIL/numpy):**
  a fast standalone script asserting the port's correctness anchors — board
  construction (cell count/adjacency/degrees), the signature move rules, win/score
  on hand-built positions, and a random-playout-terminates check. It runs under
  `tests/test_games.py::test_package_selftests` on system `python3`, so pip-only
  deps are forbidden. If you needed an image/library to *build* a static board,
  do that ONCE offline and ship the result as a `board.json` data file loaded at
  runtime (see `games/pex`) — runtime stays pure-stdlib.
- **Independent adversarial QA is worth it** for any non-trivial port: a *separate*
  agent re-fetches the sources, writes its OWN reference move-generator / scorer,
  and differential-fuzzes it against your `legal_moves`/`returns` over thousands of
  positions (exact set-equality is the gold standard). For connection games the
  **no-draw oracle** is decisive — 2-color the full board tens of thousands of
  times and assert exactly one player connects every time; a draw or double-win
  means the adjacency/edge graph is wrong (this is how `pex`'s reconstructed
  pentagon board was proven genuine).

## 7. Render primitives available (you rarely need a new one)

`polygons` covers almost any board (supply each cell's `points` — a LIST of
`{id, points}`, NOT a dict; vertex key is `points`). On top of the base
`square`/`hex`/`polygons` types the renderer already supports (see `SPEC.md` +
`GAME_STATUS.md` for the live menu): `board.tints` (per-cell colours — terrain,
goal edges, ownership), `board.lines` (under-cell grooves, e.g. a vertex board's
graph edges), `board.overlay` (over-cell lines, e.g. bridges), `board.walls`,
`board.tiles`/`board.tokens`/`board.tracks` (path/track tiles), `board.cards`
(movement-pattern strips), a per-seat `reserve` tray with click-to-drop (drop move
`"L@c,r"`), `piece.stack`/`piece.prongs`/`piece.label`. Vertex-played boards (Go on
a graph, honeycomb) render as small `polygons` cells at each vertex + `board.lines`
for the edges (see `games/{rosette,lotus,kensington}`). If a game genuinely needs a
NEW primitive, that's an orchestrator-owned change to `web/src/Board.jsx` (a render
bug white-screens EVERY game) — flag it, don't hack it into one game.

## Gotchas (from real ports)

- **Per-piece direction lists must be lists, not generators** — a generator is
  exhausted after the first piece, silently dropping moves.
- **Killed grid points = tiling vertices** for triangular boards; cells are the
  BFS-reachable sublattice, far fewer than (grid − kills).
- **Direction vectors come in opposite pairs**; each cell uses ~half (its edges),
  determined by an orientation parity.
- **`.zsg` filename numbers are solution lengths**, not board sizes.
- **Stalemate defaults to a loss** for the side to move unless the ZRF/readme
  says otherwise.
- Verify geometry against the **board image** (convert BMP→PNG with PIL), not
  just the ZRF text.

## ZRF construct index

The full keyword set (from `Langref.chm`). Recognise these in a `.zrf`:

- **Structure:** `game` `variant`(→ a manifest *option*) `option`(engine flags, e.g. pass-turn) `define`(macro) `include` `players` `turn-order` `board-setup` `piece` `image` `title`/`description`/`history`/`strategy`/`version`.
- **Board/geometry:** `board` `grid` `dimensions` `directions` `links`(explicit adjacency) `kill-positions` `zone` `positions` `symmetry`(see below) `opposite`.
- **Move generators** (inside `(moves ...)`): `add`(drop the moving piece & end the move) `cascade`(keep moving this turn — chains/multi-step) `from`/`to` `go`/`mark`/`back`(cursor control) `verify`(guard) `if`/`else` `while`(loop → slides) `not` `capture`(remove enemy) `create`(drop a new piece) `change-type`(promotion) `change-owner`/`flip` `set-flag`/`set-position-flag`/`position-flag`(special-right state) `move-type` `move-priorities`(ordering / **mandatory** moves) `drops`/`moves`.
- **Predicates/queries:** `empty?` `enemy?`/`friend?`/`any-owner` `attacked?`/`defended?` `captured?` `last-from`/`last-to` `attribute`/`set-attribute`.
- **Win/loss/draw** (`win_loss_draw-condition`): `absolute-config`(your piece(s) on named cells) `relative-config`(a piece pattern) `pieces-remaining`/`total-piece-count`/`count-condition`(material) `stalemated` `checkmated` `repetition` `goal`.
- **Presentation (ignore):** `sound` `music` `graphics` `notation` `comment`.

Important ones that change a port:
- **`symmetry`** — a piece's moves are often defined for ONE player and auto-mirrored for the opponent. Expand both directions when porting (don't give both players identical raw directions).
- **`move-priorities`** — forced moves (e.g. mandatory capture): higher-priority move types must be played if available. Mirror this in `legal_moves`.
- **flags** (`set-flag`/`position-flag`) — encode special rights: castling, en passant, ko. Track them in your state and serialize.

`Langref.chm` (repo root, gitignored — proprietary) has the full prose; from a
non-Windows shell only the topic index above is recoverable (bodies are
LZX-compressed). Open it in a CHM viewer for a primitive's exact semantics.

## When to pause and ask

Stop and confirm with the user if the ZRF uses: randomness/dice, hidden
information, simultaneous moves, piece drops from off-board (`create`/`drops`),
complex cascading move generators, or win conditions you can't cleanly express.
Better to ask than to ship a subtly-wrong port.
