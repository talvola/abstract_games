# Octagons

Connection game by **R. Wayne Schmittberger**, published in *New Rules for
Classic Games* (John Wiley & Sons, 1992) and his June 2000 *Games* magazine
connection-games article. Implemented from Kerry Handscomb's full rules
restatement in *Abstract Games* #7 (Autumn 2001), pp. 12-13.

## Board

An 8×8 array of octagons. Every octagon is cut into two **half-octagons** by
a line joining the midpoints of two opposite sides; the cut direction
alternates checkerboard-fashion (horizontal / vertical). The 7×7 interior
gaps between octagons are small tilted **squares**. Total: 128 half-octagons
+ 49 squares = 177 spaces. The notches along the board edges belong to the
frame (there are no edge squares).

The North and South edges are Red's; West and East are Blue's.

## Play

- Red moves first. The board starts empty.
- On your turn, colour EITHER **one half-octagon** OR **two distinct empty
  squares** with your colour (click one square, then the other).
- Two spaces of the same colour sharing a common **side** are connected.
- **Red wins** by joining the North and South edges with an unbroken chain of
  connected red spaces; **Blue wins** by joining West and East.
- A **corner space** connects to both edges that meet at that corner.
- **Pie rule:** after Red's first move, Blue may **swap** instead of moving
  (take over the first player's advantage). Because the two goals run in
  different directions, the swap rotates the position 90° and recolours it —
  a board symmetry that exactly exchanges the two players' goals, so the
  position's value is preserved (proven in this package's selftest).

As with Hex, **draws are impossible**: except on the edges, exactly three
spaces meet at every intersection of the board's lines, so a full board
always contains exactly one winning chain. The game ends the moment a chain
connects.

## Tactics (from the AG #7 article)

The double move is what sets Octagons apart. Colouring a square early is
almost always wasted — a square's four neighbouring half-octagons already
form a connected ring around it. Squares matter late: a double move on two
square centres can simultaneously threaten to break an enemy *semi-square*
connection and solidify one of your own.

## Implementation notes

- Cell names: octagons are `a1`–`h8` (a1 = southwest); a half-octagon is the
  octagon plus its half (`b3n`/`b3s` for horizontally cut, `a1w`/`a1e` for
  vertically cut); the square northeast of octagon `c4` is `c4x`.
- A two-square move may be entered in either order.
- **Ruling** (not addressed by the article; the 1992 book was not
  searchable): when exactly **one** empty square remains, a player choosing
  the squares option may colour just that single remaining square. The
  stricter reading (two-square moves become entirely unavailable) would
  merely dead-end the option; this permissive reading is the interpretation
  implemented.
- Handscomb's article also gives an equivalent "points" board (the Onyx grid
  rotated 45°); this implementation renders the original spaces board of
  Diagram 1.
