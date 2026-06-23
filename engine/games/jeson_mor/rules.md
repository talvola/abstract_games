# Jeson Mor (Mongolian "Running Horses")

Jeson Mor (Зон мөр, "Running Horses") is a traditional Mongolian abstract game
from the chess family. It is played entirely with **knights** — there are no
other piece types.

## Board

- A **9×9** square board (81 cells). Cells are addressed `col,row` with
  `0,0` in a corner.
- The **central square** is `(4,4)` — the dead centre of the board. The renderer
  tints it so it is easy to see.

## Pieces and setup

- Each player has **9 knights**.
- **White (player 0)** fills the bottom back rank — row `0`, columns `0`–`8`.
- **Black (player 1)** fills the top back rank — row `8`, columns `0`–`8`.
- White moves first.

## Movement

- **Every piece is a chess knight.** A knight moves in an "L": exactly the
  `(1,2)` / `(2,1)` leaper, giving up to **8 target squares**. From an open
  central square a knight has all 8; from an edge or corner it has fewer.
- A knight **may jump over** any intervening pieces (its own or the enemy's) —
  only the landing square matters.
- A knight **captures an enemy knight by landing on it** (the captured knight is
  removed). A knight may not land on a square occupied by a friendly knight.
- There is **no king, no check, no pawns, and no promotion.** Knights are
  captured like any piece; king-safety / check rules do not apply.

A move is written as the path `from>to`, e.g. `4,0>5,2`.

## How to win — the centre rule (as implemented)

This package implements the standard **"occupy-then-vacate the centre"** win:

> A player wins by moving one of their knights **onto** the central square
> `(4,4)` and then, on a **subsequent turn**, moving a knight **off** the central
> square.

In other words you must **occupy** the centre and then **leave** it:

- **Merely passing through** the centre does not count — a single move that lands
  on `(4,4)` is not a win, and a move that does not *start* on `(4,4)` never wins
  by the centre rule.
- **Merely sitting** on the centre is not yet a win — occupying `(4,4)` is safe
  but does not end the game.
- You **win the instant you vacate** the centre, having occupied it. Mechanically:
  **any move whose source square is `(4,4)` wins immediately for the mover** — a
  knight can only be standing on `(4,4)` because it arrived there on an earlier
  turn, so leaving it now is exactly "occupied, then vacated."

A knight sitting on `(4,4)` may of course be **captured** by the opponent before
it gets the chance to leave; in that case no win occurs and play continues.

## Other ways the game ends

- A player who has **no knights left** loses (after a capture removes the
  opponent's last knight, the mover wins).
- A player who has **no legal move** on their turn loses.
- **Defensive draw cap:** to guarantee termination (knight games can shuffle
  indefinitely), if neither side has won after **400 plies** the game is a draw.
  This is a platform safety cap, not a traditional rule.

## Ruleset note

Some sources describe a simpler variant — *first to occupy the centre wins*. This
package deliberately implements the more common and more interesting
**occupy-then-vacate** rule (a knight on the centre is exposed and must survive a
turn before it can claim victory by leaving). Only one rule is implemented; it is
the occupy-then-vacate rule described above.
