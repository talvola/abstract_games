# Superstar

*By Christian Freeling (mid-1980s). A connection / scoring game — the "missing
link" between Craige Schensted's **Star** and Freeling's later **Starweb**, with
a strong **Havannah** flavour.*

Superstar grew out of Freeling's dissatisfaction with *Star*: it keeps Star's
idea of rewarding connections that touch the border, but adds two more scoring
ideas — **superstars** (connecting the board's *sides*) and **loops**
(surrounding territory) — so the game has three simultaneous goals at once.

## The board

The playing area is a six-fold-symmetric **star** of hexagonal cells, identical
to the Starweb board:

- a hexagon-of-hexes of side 7 (a *hexhex-7*, 127 cells), plus
- a triangular **chunk of 15 cells** (rows of width 6, 5, 4) grown outward from
  the middle of each of the six sides,
- **217 playable cells** in total.

Cells use axial coordinates `q,r` (with `s = -q-r`); neighbours are the six
adjacent hexes.

### The edge

Surrounding the star is a **ring of exactly 60 cells called the *edge*.** *"The
edge is not part of the playing area"* — you never place a stone there. It exists
only to define **stars** (below). Each **outward corner** of the star (an arm
tip) is adjacent to exactly **3 edge cells**; each **inward corner** (a notch)
touches **1**; deep interior cells touch none. The edge is tinted gold.

### Corners and the twelve sides

- **12 outward corners** — the convex arm tips (cells with 3 on-board
  neighbours), tinted warm brown.
- **6 inward corners** — the concave notches between adjacent arms (cells with 5
  on-board neighbours), tinted violet.

Freeling: *"The board has twelve sides. A side is formed by 5 cells: an inward
corner, an outward corner and the 3 cells in between. Thus the six inward corners
each belong to two sides."* Concretely each **side** is the boundary arc

> `[inward corner, slant cell, slant cell, outward corner, flat-top cell]`

and the two sides of an arm split at the arm's flat top. The 12 sides exactly
partition the star's 54 boundary cells (the 6 inward corners counted in two sides
each).

## Play

- **White (player 0) moves first.**
- On your turn, **place one stone** of your colour on any vacant cell, **or
  pass**. Passing is legal and **not compulsory**. Stones never move and are
  never captured.
- The game **ends when both players pass in succession**, after which the score
  is counted. (Safety nets: a completely full board, or a hard 500-ply cap, also
  end the game.)

## Scoring

All scoring is done at the end. A **chain** is a connected component of one
colour. A single chain can score in **all three** capacities at once, and *"of
course separate counts are made in each capacity."* Your total is the sum over
**all** your chains of all three values:

### Star

> A **star** is a chain touching **at least 3 edge cells**. Its value is *"two
> less than the number of cells of the edge it touches"*: **value = (edge cells
> touched) − 2**.

"Touching" means hex-adjacent to that edge cell. A lone stone on an **outward
corner** touches 3 edge cells → a **1-point star**. Connecting two separate stars
adds 2 bonus points, so connections pay off.

### Superstar

> A **superstar** is a chain connecting **at least 3 sides**. **Value = 5 × (S −
> 2)**, where **S** = the number of distinct sides it connects.

A chain "connects" a side when it occupies **any of that side's 5 cells**. A lone
stone on an **inward corner** already connects **2 sides**, so reaching a third
side yields a 5-point superstar. Connecting two separate superstars that share no
side adds 10 bonus points. (Example from Freeling: a seven-stone chain joining
two inward corners through the interior connects 4 sides — a **10-point
superstar** — while touching only 2 edge cells, so it is *not* a star.)

### Loop

> A **loop** is a chain surrounding **at least one cell**. **Value = 1 point per
> enclosed vacant cell + 5 points per enclosed opponent stone.**

Enclosure is Havannah-style: a cell is *surrounded* when it cannot reach the
board boundary without crossing this chain. Enclosed **friendly** stones score
nothing.

## Komi

*"The player moving second gets a number of points beforehand to compensate for
the disadvantage of not moving first. Accurate komi have not yet been
established."* Accordingly **komi** is an integer option added to **Black's**
(the second player's) final score, **defaulting to 0**. It is kept integer so a
genuine tie remains possible.

## Winning

The player with the **highest total wins.** A **genuine tie** (equal totals) is
an honest **draw**.

## Implementation notes

- The board (217 cells, 60-cell edge, 12 outward + 6 inward corners, 12 sides)
  was reconstructed from the official MindSports diagram and verified
  cell-for-cell (see `selftest.py`): the edge is exactly 60 cells, an outward
  corner touches exactly 3 of them, and the 12 five-cell sides partition the 54
  boundary cells with each inward corner in exactly 2 sides.
- Player 0 is **White** (first); player 1 is **Black** (second, receives komi).
- A move is a single cell id `q,r`; `pass` appears as an action button.
- There is no swap/pie rule in Superstar (komi is the balancing mechanism).

## Source

Official rules: <https://mindsports.nl/index.php/the-pit/552-superstar>
