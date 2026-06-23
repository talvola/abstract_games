# Ataxx

Ataxx is a two-player expansion / infection game on a **7×7** board. The goal is
to own **more pieces than your opponent** when no more moves are possible.

## Setup

Cells are addressed `col,row`, both `0..6`.

- **Red (player 0)** starts with pieces at the **top-left** `0,0` and
  **bottom-right** `6,6` corners.
- **Blue (player 1)** starts with pieces at the **top-right** `6,0` and
  **bottom-left** `0,6` corners.

Red moves first.

## A turn: move one piece to an empty cell

On your turn you pick **one of your pieces** and move it to an **empty** target
cell. There are two kinds of move, distinguished by how far the target is
(Chebyshev / king distance):

- **Grow (clone)** — target is a **distance-1** neighbour (one of the 8
  surrounding cells). A **new** piece of your colour appears on the target and
  your **original piece stays put** — you go from *n* to *n+1* pieces.
- **Jump** — target is at **distance exactly 2**. The piece **relocates**: the
  source cell becomes empty and the piece appears on the target. Your piece
  count is unchanged.

A move is written as a path `src>dst`, e.g. `0,0>1,1` (a grow) or `0,0>2,0`
(a jump).

## Infection (the flip)

After your piece **lands on the destination**, every **opponent** piece in the
8 cells **orthogonally or diagonally adjacent** to that destination is
**infected** and flips to your colour. (Only the destination's neighbours flip;
the source's neighbours are unaffected.)

Infection only converts existing opponent pieces — it never creates or removes
pieces, it just changes their colour.

## Passing

If a player **has at least one legal move, they must move.** If a player has
**no legal move** (none of their pieces can reach any empty cell by a grow or a
jump), they **pass** and the turn goes to the opponent.

## Game end and winning

The game ends when **neither** player has a legal move, or when the **board is
full**. The player with **more pieces wins**; an equal count is a **draw**.

This implementation uses the simple **end-and-count** rule: when play stops, the
pieces are counted as they stand. (Some Ataxx rule sets instead award all empty
cells to the side that can still move when its opponent is stalled; this package
does **not** do that — it simply counts the final position. In the common case
where the board fills up completely the two rules give the same result.)

A defensive hard ply cap (2000 plies) also forces an end-and-count, so the game
always terminates; in normal play it is never reached because every grow adds a
piece and the board is bounded at 49 cells.
