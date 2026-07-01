# Ponte del Diavolo ("Devil's Bridge")

A territory and connection game by **Martin Ebel** (Hans im Glück / Rio Grande
Games, 2007), an homage to Alex Randolph's *TwixT*. Two players place coloured
**island squares** ("tiles") and gray **bridges** on a plain **10×10** grid.
Player 1 = **Light**, player 2 = **Dark**. The goal is to build many islands and
link them into large bridge-connected groups.

## Your turn

On your turn you do **exactly one** of the following:

- **Place two tiles** of your colour on any two empty, un-blocked squares. The
  two tiles need not be next to each other. *(In this implementation you place
  them one at a time — two clicks — as a single turn.)*
- **Place one bridge** connecting two of your own tiles.

## Islands and sandbanks

- **Island** — exactly **four** orthogonally-connected tiles of one colour
  (touching along their sides, forming any tetromino shape). An island is *never*
  more and never fewer than four tiles.
- **Sandbank** — an incomplete group of **1, 2, or 3** orthogonally-connected
  tiles of one colour.

Placement rules (all enforced — illegal placements are simply not offered):

1. You may **never** create a group of **five or more** orthogonally-connected
   same-colour tiles.
2. An **island** may **never** touch another island *or* a sandbank of the **same
   colour — not even diagonally** (the "touching rule"). Equivalently: no island
   may have any other same-colour tile among its eight neighbours.
3. **Sandbanks** of the same colour **may** touch each other diagonally, and may
   be joined into an island as long as the result is a legal island (≤ 4 tiles
   and not touching another same-colour island/sandbank).
4. Tiles of **different** colours may touch freely.
5. You may not place a tile on an occupied square, nor under a bridge.

## Bridges

A **bridge** connects two of your own tiles that lie a **straight orthogonal
step, a straight diagonal step, or a knight's-move apart** — spanning **one**
empty water square (orthogonal/diagonal) or **two** empty water squares (knight).

- The square(s) the bridge spans must be **empty water** (no tile of either
  colour, and not already spanned by another bridge).
- A bridge may **not cross** a tile or another bridge.
- Each tile may support **at most one** bridge.
- Bridges may connect islands *or* sandbanks; only islands score, but a sandbank
  can act as a stepping-stone that links two islands into one group.

The physical game supplies **15 bridges** (a shared pool) and **40 tiles per
colour**; both limits are enforced here.

## End of the game

A player may **pass** only when they **cannot legally place two tiles**. When
**Light** passes, **Dark** takes **one final turn** and the game then ends. When
**Dark** passes, the game ends **immediately**. (A hard ply cap also bounds the
game as a safety net.)

## Scoring

Each maximal **group** of islands connected by bridges scores the **triangular
number** of the islands it contains:

| Islands in group | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Points | 1 | 3 | 6 | 10 | 15 | 21 | 28 | 36 |

(the formula is *n·(n+1)/2*). A lone island scores **1**. Sandbanks score
**nothing** on their own. Sum each player's groups.

The higher total **wins**. Ties break in order: **(1)** most islands, **(2)**
most bridges, **(3)** a **shared victory** (a draw).

## Notation (as implemented)

- A tile placement is a single cell, e.g. `4,5` (col,row, each 0–9). A full
  turn = two such placements by the same player.
- A bridge is the path `a>b` between two of your tiles, e.g. `2,1>2,3`.
- `pass` ends your turn (offered only when you cannot place two tiles).

## Deviation from the published rules

The optional **Alex Randolph pie / colour-swap start rule** (the first player
places two Light tiles and the opponent then chooses a colour) is **omitted**
for simplicity: Light always moves first. All other rules follow the official
Hans im Glück / Rio Grande rulebook.
