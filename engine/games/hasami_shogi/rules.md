# Hasami Shogi (Dai Hasami Shogi)

Hasami Shogi (挟み将棋, "sandwiching chess") is a traditional Japanese
two-player game played with shogi pawns on a board. This package implements the
well-known **Dai Hasami Shogi** combination: a custodial (Tafl-like)
sandwich-capture together with the **five-in-a-row** goal.

## Equipment & setup

- Board: **9x9**, cells addressed `col,row` with `0,0` at the bottom-left.
- Pieces: **9 identical men per player**. There is a single piece type — no
  promotion, no king.
- **Player 0** fills **row 0** (its home row); **Player 1** fills **row 8**.
- Player 0 moves first.

## Movement

A man moves like a **rook**: any number of empty squares **orthogonally**
(along a rank or file). It may **not** move diagonally and may **not** jump over
any piece (friendly or enemy). There is no capture by displacement — you never
land on an occupied square.

## Capture — custodial / sandwich (active)

Capture happens **only as a result of your own move**, never passively. After
you move a man to its destination, look outward from that destination in each of
the four orthogonal directions:

- If you find one or more **contiguous enemy men** in a straight line, with
  **no gap** and no friendly man among them, and the square **just beyond** the
  run holds one of **your** men, then **every enemy man in that run is captured**
  (removed from the board).
- Because the bracket must be unbroken, a single sandwiched enemy man is the
  common case, but a whole line of two, three, … enemy men is captured at once.

A man that simply **moves into** a square that happens to be between two enemy
men is **safe** — capture is *active* and resolves only on the mover's turn.
This is identical to the flanking rule used in the Tafl family (see Brandub).

### Corner capture

A man standing on one of the four **board corners** is captured if the moving
player occupies **both** edge-adjacent squares of that corner (the two cells
along the two board edges that meet at the corner). This is the standard Dai
Hasami Shogi corner rule and is evaluated as part of resolving your move.

## Winning

Both standard win conditions are implemented; achieving **either** on your move
wins immediately:

1. **Decimation** — reduce your opponent to a **single man** (i.e. capture all
   but one of their nine). When the opponent has 1 or fewer men left after your
   move, you win.

2. **Five-in-a-row** — form an **unbroken line of 5 (or more) of your own men**,
   **orthogonally or diagonally**, where **no** square of that line lies on your
   **own home row** (row 0 for Player 0, row 8 for Player 1). The home-row
   exclusion prevents winning trivially from the starting array; you must
   advance your men off the back rank to score the line.

## Draws / termination

Custodial games can shuffle indefinitely, so a **300-ply cap** ends the game as
a **draw**. If a player to move has no legal move, that player **loses**.

## Notes on the ruleset choice

Hasami Shogi has several documented variants:

- A simpler "jumping" / replacement-capture variant exists, and some rulesets
  use only the decimation goal while others use only the five-in-a-row goal.
- This package implements the **Dai Hasami Shogi** combination most commonly
  described: **rook movement**, **custodial (sandwich) capture** including the
  corner rule, and **both** the decimation and the off-home-row five-in-a-row
  win conditions. The exact thresholds used here (reduce to one man; line length
  five; whole line off the home row) are stated above and are the values
  enforced by the engine.
