# Avalam

Avalam (originally **Avalam Bitaka**) — Philippe Deweys, Brussels, 1996.
First published by SC.JP Fils.Fils / Filsfils International (Belgium); later
editions by Piatnik, Oya, Art of Games and others. 1998 Mensa Select.

## Board & setup

The board is an irregular "orthogonal array of **49 depressions**" — a 9×9
grid with the corners shaved off, giving rows of 2/4/6/8/9/8/6/4/2 holes
(the shape is 180°-rotation symmetric). The **48 pieces** — 24 Light and 24
Dark — start one per hole in a strict checkerboard pattern; the **central
depression starts empty** (and, by the movement rule, stays empty forever).
Light moves first in this implementation (the published rules name no
starting player).

## Play

Players alternate turns. On your turn you **must** make exactly one move (a
move always exists until the game is over):

- Take **any one stack** — a single piece is a stack of one, and it does
  **not** matter which colour is on top: you may move your opponent's
  pieces.
- Move it **exactly one cell** in any of the 8 directions (orthogonal or
  diagonal) **onto an adjacent occupied cell**. The whole moving stack lands
  on top of the target stack.
- The **whole stack always moves** — stacks are never split.
- **No stack may ever exceed 5 pieces**: a move whose combined height would
  be 6 or more is illegal.
- You may **never move onto an empty depression** — once a hole is empty it
  stays empty, so a stack with no occupied neighbours is frozen for good and
  can no longer change owner.

## End & scoring

The game ends when **no legal move remains** (every stack is isolated or
every merge would exceed 5). Each remaining stack is worth **one point** to
the player whose colour is **on top** — a 1-stack and a 5-tower both count
exactly one. Most points wins. **An equal count is a draw** — the published
rules (publisher rulebook and the Abstract Games #18 essay) give no
tiebreak. (Some later retail blurbs suggest breaking ties by 5-towers; that
is not in the primary rules and is not implemented.)

Termination is structural: every move merges two stacks into one, so the
stack count falls by exactly one per move and the game ends within 47 moves.

## Notation

Cells are `col,row` on the 9×9 footprint; a move is `from>to`. The move log
shows algebraic squares (a–i, ranks 9 at the top) with the resulting stack
height, e.g. `d5>e4 (=3)`.

## Sources

- Abstract Games magazine #18 (Winter/Spring 2020), front-cover essay by
  Kerry Handscomb (complete ruleset, "49 depressions").
- Publisher rulebook (SC.JP Fils.Fils, French; board photo pins the exact
  layout; the free-placement variant text confirms "le 49ème trou").
- UCLouvain reference implementation (Vianney le Clément, 2010) — its
  standard `initial_board` matrix matches this package cell-for-cell.
- [BoardGameGeek](https://boardgamegeek.com/boardgame/9092/avalam).
