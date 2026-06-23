# Domineering

Domineering (also called Stop-Gate or Crosscram) is a two-player combinatorial
game invented by Göran Andersson and popularised by Berlekamp, Conway and Guy in
*Winning Ways for Your Mathematical Plays*. It is a staple example in
combinatorial game theory (CGT).

## Board

A rectangular grid, **default 8x8**. The `size` option offers a few boards
written as *columns x rows*: `6x6`, `7x7`, `8x8` (default), `9x9`, `10x10`, plus
the asymmetric `8x6` and `6x8`. Cells are addressed `c,r` with `c` the column and
`r` the row, both zero-based. The board starts **empty**.

## Placement

On each turn the player places **one domino** covering **two adjacent empty
on-board cells**:

- **Player 0 — Vertical** covers a cell `(c, r)` and the cell directly below it
  `(c, r+1)`.
- **Player 1 — Horizontal** covers a cell `(c, r)` and the cell to its right
  `(c+1, r)`.

Both covered cells must be empty and on the board. There are **no captures** and
placed dominoes **never move**. Each player can only place dominoes in their own
orientation, so as the board fills the two players are competing for the same
shrinking space.

**Vertical (player 0) moves first.**

## Winning — normal play

This package uses **normal play**: the player who **cannot place a domino on
their turn loses**. Equivalently, the **last player able to place a domino
wins**. There are no draws.

Because every move fills exactly two cells, the game is strictly bounded and
always terminates.

## Move notation

A move is the two covered cells written as a path: `c,r>c2,r2`. In the web UI
click the two cells of the domino (the interface offers only legal second cells).
A placed domino shows as two cells filled in the placer's colour, with the most
recent domino highlighted.

## Ruleset notes

- **Normal play only** (last to move wins). The misère variant (last to move
  loses) is *not* offered.
- The standard game is played on an empty rectangular board; this package does
  not implement pre-removed cells or non-rectangular regions.
