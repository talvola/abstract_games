# Trax

**Trax** (David Smith, New Zealand, 1980) is a two-player game of *loops and
lines*. Both players place the same two-coloured tiles on an unbounded square
grid; one player owns **White**, the other **Red**, and each tries to complete a
closed loop or a long line in their colour.

## The tiles

Every Trax tile is a square. Its four edges are coloured so that **two are white
and two are red**, with a **white track joining the two white edges** and a **red
track joining the two red edges**. Up to rotation there are exactly **two tile
types**:

- **Straight tile** — white joins one pair of *opposite* edges, red joins the
  other opposite pair (two parallel straight lines).
- **Curved tile** — white joins two *adjacent* edges, red joins the remaining
  two adjacent edges (two corner curves).

Edges/midpoints are numbered **0 = top, 1 = right, 2 = bottom, 3 = left**. The
distinct **orientations** (and the move token used for each) are:

| Token | Type | White edges | Red edges | Edge colours (T,R,B,L) |
|-------|------|-------------|-----------|------------------------|
| `\|`  | straight | 0–2 (top–bottom) | 1–3 (left–right) | W R W R |
| `-`   | straight | 1–3 (left–right) | 0–2 (top–bottom) | R W R W |
| `TL`  | curve | 0–3 (top+left)   | 1–2 (right+bottom) | W R R W |
| `TR`  | curve | 0–1 (top+right)  | 2–3 (bottom+left)  | W W R R |
| `BR`  | curve | 1–2 (right+bottom) | 0–3 (top+left)   | R W W R |
| `BL`  | curve | 2–3 (bottom+left) | 0–1 (top+right)  | R R W W |

So a placed tile is fully described by which of these **6 orientations** it is.

## Setup and first move

**White moves first.** By board symmetry every opening is equivalent, so the
first tile is fixed: a **curved tile** placed at the centre with white running
top-left (`TL`). All later play radiates from it.

## Placing a tile (the matching rule)

Each tile after the first is placed on an **empty cell adjacent to at least one
tile already in play**. The placement is legal only if the colour on **every
shared edge matches** the neighbour it touches (white meets white, red meets
red). A tile + orientation that violates any touching edge is illegal.

## Forced / mandatory moves (the heart of Trax)

After a tile is placed, look at every empty cell on the frontier. **If two (or
more) of an empty cell's edges are forced by placed neighbours to the *same*
colour, a tile MUST be added there** — the matching rule then determines its
orientation uniquely (the doubled colour joins those two edges; the other two
edges and the other colour are fixed). The same player adds every such forced
tile as part of the same turn. A forced placement can create further forced
cells, so this **repeats to a fixed point**.

A configuration where **three or more** of an empty cell's edges would be the
same colour is **illegal**; a move (or a forced chain) that would create one is
not allowed, and such candidate placements are filtered out of the legal-move
list. The turn is complete when every remaining empty frontier cell has at most
one forced edge, or two forced edges of *different* colours.

## Winning

Immediately after a placement **and all its forced moves resolve**, a player
**wins** if their colour forms either:

- a **LOOP** — a closed, continuous path of that colour's track that connects
  back to itself; or
- a **winning LINE** — a continuous path of that colour that touches **two
  opposite outermost edges** of the tiles in play and spans **at least 8 rows or
  8 columns** (across or down). (Here: the path's connected component reaches
  both the leftmost and rightmost occupied columns with the board spanning ≥ 8
  columns, or both the topmost and bottommost occupied rows with span ≥ 8 rows.)

**Loops always win.** If a single turn (including its forced moves) completes a
winning configuration for **both** colours at once, the **player who moved
wins** (the simultaneous-win rule).

## Move encoding

A move is the target cell id plus the chosen orientation token as a `=CHOICE`
suffix, e.g. `3,4=TL`, `2,1=|`, `0,0=BR`. Clicking an empty legal cell offers
the legal orientations for that cell. The board grows in all directions; cell
ids may be negative.

## Termination

Trax has no fixed board and in principle could grow without bound, but real
games end in a handful of placements. As a safety net this implementation
declares a **draw** if play reaches **300 plies** or the played area spans **64
cells** in either direction — neither is reachable in normal play; they exist
only to guarantee the engine terminates under random self-play.

## Interpretations / notes

- The two players never have distinct pieces; both place identical two-coloured
  tiles. Ownership is only of a *colour* (White = seat 0, Red = seat 1).
- The opening tile is fixed to `TL` at the centre because every legal opening is
  equivalent up to rotation/reflection and colour relabelling.
- The winning-line definition follows the official rules ("connects opposite and
  outermost edges of the tiles in play, over at least 8 rows of tiles, across or
  down").
