# Surakarta

Surakarta (also called *Roundabouts*) is a traditional capturing game from the
Indonesian city of Surakarta. Its hallmark is the looping capture: the grid
lines curl back at the corners, and a piece captures by sliding around at least
one of those loops.

## Board

A grid of **6 × 6 intersections**, rendered as a 6-wide × 6-tall square board.
Cells use the platform `col,row` notation, columns `0–5` and rows `0–5`. The
six horizontal lines (rows) and six vertical lines (columns) are drawn as
cosmetic grooves; the eight **corner loops** are drawn as arcs over the board's
edges.

## Setup

Each player has **12 pieces**.

- **White** (player 0, moves first) fills the two rows nearest it: **rows 0 and 1**.
- **Black** (player 1) fills **rows 4 and 5**.
- The **middle two rows (2 and 3) start empty.**

## Moves

On your turn you make exactly one move, of one of two kinds.

### (A) Non-capturing step

Move one of your pieces to **any one of the up-to-8 adjacent intersections**
(orthogonal **or** diagonal) that is **empty**. A step never captures, and may
go in any of the eight directions.

### (B) Capturing move

A capturing piece **slides along the straight orthogonal lines** (its current
row or column — **never a diagonal**). To capture, the slide **must pass around
at least one corner loop.** It travels through empty intersections, follows a
loop arc at a board edge (which turns it 90° onto the perpendicular line),
continues, and **captures the first piece it meets** — which **must be an
enemy.**

- The slide **may not jump over any piece.** The first piece it reaches ends the
  slide: if that piece is an enemy it is captured (the slider takes its square);
  if it is your own piece, that line of capture is **illegal.**
- A slide that reaches an enemy **without traversing a loop is not a capture**
  (an ordinary orthogonal line with no loop can only be used for a step, and a
  step is a single space). Capturing therefore *requires* a loop.
- Diagonals are for stepping only — you can never capture along a diagonal.

Captures are **not mandatory** in this implementation (see *Ruleset choices*).

## The loop topology (exactly as implemented)

The board's lines extend at the edges into curved tracks that connect each
line's end into a perpendicular line. **Only the inner four lines on each axis
loop; the outermost lines (row/column `0` and `5`) do not.** The loops form
**two concentric rings**, eight corner arcs in all (4 corners × 2 rings):

- **Inner ring (depth 1):** rows **r = 1** and **r = 4**, columns **c = 1** and
  **c = 4**. At each corner a small three-quarter arc joins the end of the inner
  row line to the end of the inner column line (e.g. the left end of row 1,
  `(0,1)`, curves down and around to the bottom end of column 1, `(1,0)`).
- **Outer ring (depth 2):** rows **r = 2** and **r = 3**, columns **c = 2** and
  **c = 3**, joined by a larger arc concentrically outside the inner one (e.g.
  `(0,2)` ↔ `(2,0)`).

Each ring is a **single closed cyclic track.** A capturing slide stays on one
ring (it never switches rings): it runs straight along a line, passing straight
through the interior crossings, and **only at a board edge does an arc bend it**
onto the perpendicular line. It must cross **≥ 1 arc** before reaching the
captured piece. The four true board corners `(0,0)`, `(0,5)`, `(5,0)`, `(5,5)`
lie on no looping line and so can never give or take a loop capture.

Internally each ring is a precomputed cyclic sequence of cells (the four interior
crossing cells appear twice, once per line through them); a capturing slide is a
walk along that cycle in either direction until it meets a piece or returns to
its origin.

## Winning

You **win** by capturing **all** of the opponent's pieces.

## No-progress draw (termination guarantee)

Captures strictly reduce the number of pieces, so a game cannot loop forever
through captures — but non-capturing **steps** could shuffle indefinitely. To
guarantee the platform's random self-play always terminates, after **60
consecutive non-capturing plies** (any capture resets the count) the game is
declared a **draw**. (Real games end by annihilation long before this.)

## Move notation

A move is the platform's `>`-separated cell path `frm>to`:

- A **step** is `frm>to` where `to` is an **adjacent empty** intersection,
  e.g. `0,1>0,2`.
- A **capture** is `frm>to` where `to` is the **captured enemy's cell**, reached
  by the loop slide (the intermediate path is implicit), e.g. `2,1>2,4`.

These never collide: a step destination is adjacent and empty, while a capture
destination holds the captured enemy piece.

## Ruleset choices (as implemented)

- **6 × 6 board, 12 pieces each**, White on rows 0–1, Black on rows 4–5, middle
  two rows empty — the standard Surakarta array.
- **Two loop rings** (inner = the second line in from each corner, outer = the
  third), eight corner arcs total, as described above. This is the standard
  Surakarta topology; the precise arc connectivity (which line-end joins which)
  is the conventional one — each line's end joins the *perpendicular* line's end
  at the same corner and same depth.
- **Captures are optional**, not forced. Sources differ on whether capture is
  mandatory in Surakarta; the common modern ruleset treats it as optional, and
  this package follows that. (If you prefer mandatory capture, that would be a
  one-line change but a genuinely different game feel — flagged here as a choice.)
- **No published perft/move counts** exist for Surakarta, so the bundled
  `selftest.py` asserts the rule mechanics directly on hand-built positions
  (loop capture legal, the same slide without a loop rejected, no jumping, the
  8-direction step, capture-all win) plus an engine conformance pass.
- A **60-ply no-capture draw cap** guarantees termination (documented above).
