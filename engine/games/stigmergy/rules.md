# Stigmergy

By **Luis Bolaños Mures & Steven Metzger** (2021). A drawless territory game on
an initially empty hexagonal board of hexagons (side length 8 by default; a
manifest option). Based on Mike Zapawa's *Tumbleweed* — but where Tumbleweed
grows **stacks** whose height must beat what's on the hex, Stigmergy plays
single **flippable stones**: legality and captures hinge on line-of-sight
*control* of cells, and captured stones flip colour in place.

## Seeing and control

- Two stones, or a stone and an empty cell, **see** each other if they lie on
  the same straight line of adjacent cells with **no other stones between
  them**. From a cell, along each of the 6 directions, only the *first* stone
  is seen. A cell's own occupant is not seen by it and doesn't block its rays.
- You **control** a cell if the number of stones of your colour it sees is
  **more than half the number of cells adjacent to it** (empty or occupied):
  interior cells have 6 neighbours (you need 4+), board-edge cells 4 (need 3+),
  corner cells 3 (need 2+). At most one player can control a given cell.
- The faint red/blue cell shading in the UI shows who currently controls each
  empty cell.

## Play

Black (seat 0, rendered red) moves first; turns alternate. On your turn do **exactly
one** of:

1. **Place** a stone of your colour on an empty cell **not controlled by your
   opponent** (uncontrolled or self-controlled cells are fine).
2. **Flip** an enemy stone on a cell **you control** — it becomes your colour.
3. **Pass** — allowed only when there are no empty cells, or every empty cell
   is controlled by some player (and, with an odd komi, only after the button
   has been taken).

## End and scoring

The game ends when **both players pass in succession**. Your score is your
**stones on the board** plus the **empty cells you control**, plus **komi**
for White (and half a point for the button holder). Higher score wins.

## Komi and the button

- **Komi** is a whole number of points added to White's score (a game option
  here, default 0). The official rules set it by negotiation — the first
  player names the komi and the second chooses sides — which is out of scope
  for this implementation; pick a value from the dropdown instead.
- With an **odd** komi the **button** is in play: until someone takes it,
  nobody may pass, and on your turn you may take the button *instead of* a
  board play. It adds **half a point** to its holder's final score.

At a genuine double-pass ending every empty cell is controlled by exactly one
player, so the two base scores always sum to the board's odd cell total —
with an even komi the game is drawless, and an odd komi's half-point button
keeps it so.

## Implementation notes

- **Termination backstop:** placements only ever add stones, but flips alone
  could in principle cycle, so a long stretch of plies with no placement (or
  a hard ply cap) ends the game with the position scored as-is. Only on that
  backstop path can uncontrolled empty cells (scored for nobody) make a tie
  possible — an honest **draw**.
- Source: the designer's revised rules from Zillions of Games submission
  id 3126 (updated 2021-07-03), which match the bundled ReadMe. The Zillions
  program's own restrictions ("pass only with no moves available", komi and
  button unenforced) were coding simplifications there and are *not* followed
  here — the written rules are.

## How it differs from Tumbleweed

Tumbleweed (also in this library) is the parent game: hexhex board, six-ray
line of sight, area scoring. Stigmergy has **no stacks and no heights** — one
stone per cell, ever. Placement is barred only from *opponent-controlled*
cells (not tied to a LoS-vs-height count), captures are **flips in place** on
cells you control, the control threshold scales with each cell's neighbour
count (corners and edges are easier to control), and scoring counts your
stones plus controlled empty cells, with komi/button instead of Tumbleweed's
neutral start stack.
