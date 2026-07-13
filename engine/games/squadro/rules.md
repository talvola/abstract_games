# Squadro

*Adrián Jiménez Pascual — Gigamic, 2018. 2 players.* Rules **as implemented** in
this package (verified against the Gigamic rulebook).

## Goal

Be the first to complete a full **round trip** (across the board and back to your
start line) with **four of your five pieces**.

## Board and setup

A 7×7 board. Cells are written `col,row` (columns `0..6` left→right, rows `0..6`
bottom→top).

- **White** (seat 0) places one piece on each of **rows 1–5**, on the **left**
  start line (column 0). White moves **horizontally**, outbound **left→right**.
- **Black** (seat 1) places one piece on each of **columns 1–5**, on the
  **bottom** start line (row 0). Black moves **vertically**, outbound
  **bottom→top**.

The two players move on perpendicular tracks. White moves first.

## Speeds

Every piece has a fixed speed — the number of dots on its starting cell. The
patterns for the two players are **complementary**: a piece that is slow going
out is fast coming back, because *outbound speed + return speed = 4*.

| Line (1–5) | White (by row) out / return | Black (by col) out / return |
|:---:|:---:|:---:|
| 1 | 3 / 1 | 1 / 3 |
| 2 | 1 / 3 | 3 / 1 |
| 3 | 2 / 2 | 2 / 2 |
| 4 | 1 / 3 | 3 / 1 |
| 5 | 3 / 1 | 1 / 3 |

So each player has two pieces that move 3, two that move 1, and one that moves 2
on the way out (and the reverse on the way back).

## Moving

On your turn, pick one of your pieces (click its cell — the destination is
forced). It advances **exactly its current speed** in a straight line along its
own line, with two things that can cut the move short:

1. **Turning around.** When a piece reaches the far edge it immediately turns
   around (now pointing home) and **stops there**, even if it had movement left.
   From then on it moves at its **return** speed.
2. **Finishing.** When a returning piece reaches its own start line it completes
   the round trip and is **removed** from the board.

A piece always makes its full move unless (1), (2), or a jump (below) stops it.

## Jumping

If, during its advance, a piece would move onto — or pass over — one or more
**opponent** pieces, it **leaps the entire contiguous group** and lands on the
first free cell just beyond them, then **stops immediately** (forfeiting any
remaining movement).

Every opponent piece that was jumped is sent back to its base:

- to its **start line**, if it had **not yet turned around**;
- to its **turnaround (far) line**, if it was already on its return trip.

Because each player's pieces sit on separate lines, a moving piece only ever
meets *opponent* pieces, and the base lines are never occupied by the opponent —
so a piece resting on a base is safe.

## Winning

The first player to bring **four of their five pieces** home on the full round
trip wins.

## Draws (backstop only)

Squadro has no draw in normal play. To guarantee termination this package
declares an honest **draw** if the exact position repeats three times or a hard
move cap is reached.
