# Dodo

Mark Steere, May 2021. Two players: **Red** (moves first) and **Blue**.
Official rules: [marksteeregames.com/Dodo_rules.pdf](https://www.marksteeregames.com/Dodo_rules.pdf).

## Board & setup

A hexagon of hexagons, side 4 by default (37 cells). Each player starts with
**13 checkers** filling their home-corner region, with an empty three-file band
between the flocks (the rule sheet's Figure 1). In this port the board is shown
rotated a quarter turn from the PDF's diagram: **Red starts in the left corner
and moves rightward; Blue starts in the right corner and moves leftward** —
otherwise identical.

Other board sides (3, 5, 6) extend the same pattern: every cell beyond the
central three-file band starts filled. (The PDF says "a hexagonal grid of any
size" but only diagrams side 4, which is the standard size.)

## Moving

- Players alternate turns, moving exactly **one** of their own checkers.
  **Passing is not allowed.**
- A checker moves **one cell directly forward or diagonally forward** — the
  three adjacent cells on the opponent's side. For Red these point right
  (→, ↗, ↘); for Blue they point left (←, ↖, ↙). Forward is fixed for the
  whole game, wherever the checker stands.
- **All moves are to unoccupied cells.** There are no captures, no jumps, and
  never any backward or sideways movement.

## Object of the game

**If at the beginning of your turn you have no moves available, you win.**
Getting your flock stuck first is the whole game — hem your own birds in while
keeping the opponent's birds free to move.

## Notes

- Because checkers only ever move forward, progress is strictly monotone: the
  game always ends with one player stuck (and victorious). **Draws cannot
  occur.** (A hard ply-cap draw exists in the implementation purely as an
  engine-mandated backstop; it is provably unreachable.)
