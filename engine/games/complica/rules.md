# Complica

**Designer:** Reiner Knizia (1991) · **Players:** 2 · A Connect-4 variant with a
column-push twist. Rules below are *as implemented*, faithful to AbstractPlay's
open-source `gameslib` implementation.

## Board

A grid **4 columns wide × 7 rows tall** (28 cells). Row 0 is the bottom, row 6 the
top; columns are numbered **1–4** from the left. Player 0 = **Red**, Player 1 =
**Yellow**. Red moves first.

## Your move: drop into a column

On your turn choose one of the four columns. Every column is *always* playable:

- **Non-full column** — your disc **stacks on top**: it falls to the lowest empty
  cell of that column, exactly like Connect Four.
- **Full column** — the whole column is **pushed down by one row**: the disc at the
  **bottom (row 0) falls off the board**, every remaining disc drops one row, and
  your new disc **enters at the very top (row 6)**.

Because full columns cycle, the board can change dramatically each move and discs
of either colour can be pushed into — or out of — a winning line.

## Winning

A line of **four of your own discs** — horizontal, vertical, or either diagonal —
wins.

The end-of-game check is **symmetric**, evaluated after every move (it does not
care who moved): count four-in-a-rows for **both** players.

- If **exactly one** player has a four-in-a-row, that player **wins** — even if the
  winning line was created by the *opponent's* push move.
- If **both** players have a four-in-a-row at the same time (a push can complete
  lines for both colours at once), **nobody wins** and play simply continues.
- If neither player has four, play continues.

## Draws / termination

There is no natural draw: a full column just cycles, so there are always four legal
moves and the board never "fills up" into a stalemate. To guarantee the game ends,
a hard **ply cap of 300 half-moves** declares an honest **draw** if reached. In
practice games finish long before this.

## Move notation

A move is the single **column number** (`"1"`–`"4"`), shown in the interface as
four column buttons. The move log distinguishes a `drop col N` (stacking) from a
`push col N` (the column was full and got pushed down).
