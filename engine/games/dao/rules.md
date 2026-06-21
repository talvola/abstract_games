# Dao

A two-player abstract on a **4×4** board (Jeff Pickering & Ben van Buskirk,
~1999). Each player has **four pieces**. Player 0 is **Black**, player 1 is
**White**.

## Setup

The pieces start on the two main diagonals:

- **Black** on `(0,0) (1,1) (2,2) (3,3)`,
- **White** on `(0,3) (1,2) (2,1) (3,0)`.

(`(col,row)`, 0-indexed; in the move log, columns are `a–d` and rows `1–4`.)

## Moving

Players alternate. On your turn move **one** of your pieces in any of the
**8 directions** (orthogonal or diagonal), like a chess queen — **but** the
piece **must slide as far as it can**: it travels in the chosen direction
until it is stopped by the board edge or another piece, and **comes to rest on
the last empty square before that obstacle**.

- You **cannot stop part-way** along the line.
- You **cannot choose a direction in which you are already blocked** — i.e. the
  very next square is off the board or occupied. That direction yields no move.
- **There are no captures.** Pieces never leave the board, and you can never
  land on or jump over a piece.

## Winning

You win the instant **your four pieces** form any one of these patterns:

1. **2×2 square** — your pieces occupy a 2×2 block, e.g. `(1,1) (2,1) (1,2) (2,2)`.
2. **Line of four** — your pieces fill **one complete row or one complete
   column**. On a 4×4 board with exactly four pieces this is the only way four
   pieces can lie in a full straight line. **Diagonals do _not_ count** (so the
   starting position, with each side on a main diagonal, is not a win).
3. **Four corners** — your pieces occupy all four board corners
   `(0,0) (0,3) (3,0) (3,3)`.
4. **Corner trap** — one of **your** pieces sits in a **board corner** and the
   **three squares adjacent to that corner** (its two orthogonal neighbours and
   the one diagonal neighbour) are **all occupied by your opponent**. The player
   whose piece is trapped in the corner **wins**. (Yes — being boxed into a
   corner is a *win* for the trapped player, per the inventors' rules / patent.)

Because the corner-trap pattern can be completed by *either* player's move, all
win conditions are evaluated for **both** players after every move. If a single
move would complete winning shapes for both players at once, the player who just
moved is credited with the win.

## Ruleset choices

The published descriptions vary slightly; this package implements:

- **"Line" = a full row or column only.** The patent's broader "any straight
  line" wording reduces to exactly rows/columns when four pieces must fill the
  line on a 4×4 board; diagonals are excluded (matching the common Wikipedia
  statement and the fact that the diagonal starting layout must not be a win).
- **No legal move ⇒ loss.** The mandatory-maximum-slide rule means a player is
  almost always able to move, and the published rules do not define a "stuck"
  case. For a well-formed game we treat a player with **no legal move** as the
  **loser** (the standard convention). In practice this is essentially
  unreachable before a corner-trap win occurs.
- **Move cap.** Dao positions can repeat, so a hard cap of **200 plies** ends
  the game as a **draw** to guarantee termination. This is a technical
  safeguard, not a normal way for a real game to end.
