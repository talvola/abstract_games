# Quoridor

Quoridor (Mirko Marchesi, 1997) is a race-and-block game: get your pawn to the
far side of the board while dropping walls to send your opponent the long way
round. These are the rules **as implemented** here.

## The board

A 9×9 grid of cells. Each player has a pawn and **ten walls**. Player 1 (red)
starts at the middle of the bottom row and must reach the **top** row; Player 2
(blue) starts at the top and must reach the **bottom**. The two goal rows are
tinted in each player's colour. Player 1 moves first.

## Your turn — move or wall

On your turn you do exactly one of:

- **Move your pawn** one cell up, down, left, or right — but not across a wall and
  not off the board.
- **Place a wall** in a groove between cells. A wall is **two cells long** and
  blocks movement across its whole length. Click the faint slot in the groove to
  place it.

### Jumping

If the opponent's pawn is in the cell you would step into, you **jump straight
over** it to the cell beyond. If that cell is off the board or blocked by a wall,
you may instead step **diagonally** to either side of the opponent (whichever
isn't itself walled off).

## Walls — the restrictions

- Walls may not **overlap** another wall or **cross** one (two walls can't share
  the same post).
- **A wall may never completely cut a pawn off from its goal row** — not yours and
  not your opponent's. If a placement would leave either pawn with no path at all,
  it is illegal. (You may freely *lengthen* a path; you just can't seal it.)

## Winning

The first player to move their pawn onto **any cell of their goal row** wins.
Quoridor cannot end in a draw; a hard move cap only exists as a safety net against
pathological play.

## Notation

A pawn move is `from>to` (e.g. `4,0-4,1` in the log); a wall is `H c,r` or `V c,r`
for a horizontal or vertical wall at the post `(c,r)` (the shared corner of four
cells, with `c,r` in 0..7). Cells are named by their `col,row` coordinate.
