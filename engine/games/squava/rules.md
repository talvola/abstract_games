# Squava

A two-player game on a **5×5** square grid. Player 0 is **Black** and moves
first; player 1 is **White**. Squava is a *misère/positive hybrid* n-in-a-row:
one length of line wins, a shorter one loses.

## How to play

- On your turn, place one stone on any **empty** cell.
- Stones never move and are never captured or removed (exactly like Gomoku) —
  the game is **placement only**.
- Players alternate, one stone per turn.

## Winning and losing

After you place a stone, the lines running through it (horizontal, vertical, and
both diagonals) are evaluated:

- If you now have **four or more** of your own stones in an unbroken row, you
  **WIN** immediately.
- Otherwise, if you now have **exactly three** of your own stones in an unbroken
  row (and no four), you **LOSE** immediately. This is the misère twist: you are
  forbidden from making three-in-a-row **unless** it is part of a four.

### Four takes precedence

If a single placement creates a three **and** a four at the same time (for
example, completing a line of four also contains a sub-run of three), it counts
as a **four — and therefore a WIN**. A four always beats a three; you are only
punished for a three that is *not* part of a four.

## Draw

If the board fills with all **25** stones placed and no four was ever made and no
losing three ever decided the game, the result is a **draw**. Because there is no
movement and no capture, the game always ends within 25 placements.

## Ruleset notes (as implemented)

- "Three" and "four" are measured as the **longest unbroken run** of the placer's
  stones through the just-placed cell along each of the four axes. A run of length
  ≥ 4 is a win; a run of length exactly 3 (with no run of 4 anywhere through that
  stone) is a loss.
- Only the **player who just moved** can win or lose on that placement — the
  outcome is always evaluated from the perspective of the stone just placed. You
  cannot lose because of a three formed by your opponent's stone.
- Overlines (five in a row, only possible by filling a full rank/file/diagonal of
  the 5×5 board) are treated like any other four-or-more and **win**.
