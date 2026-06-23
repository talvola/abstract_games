# Cram

Cram is a two-player **impartial** combinatorial game — the impartial cousin of
Domineering. It is also known as **plugg** and was popularised by Martin Gardner
in his *Scientific American* "Mathematical Games" column (and is sometimes
credited to Geoffrey Mott-Smith). It is a standard example in combinatorial game
theory (CGT).

## Board

A rectangular grid, **default 6x6**. The `size` option offers a few boards
written as *columns x rows*: `4x4`, `5x5`, `6x6` (default), plus the asymmetric
`4x6` and `6x4`. Cells are addressed `c,r` with `c` the column and `r` the row,
both zero-based. The board starts **empty**.

## Placement — the key difference from Domineering

On each turn the player places **one domino** covering **two empty
orthogonally-adjacent on-board cells**. Unlike Domineering, **either player may
place a domino in either orientation** — horizontal *or* vertical. The two
players therefore share the **same set of legal moves** from any position; this
makes Cram an **impartial** game (in Domineering, by contrast, one player plays
only vertical dominoes and the other only horizontal).

Both covered cells must be empty and on the board. There are **no captures** and
placed dominoes **never move**.

**Player 1 moves first.**

## Winning — normal play

This package uses **normal play**: the player who **cannot place a domino on
their turn loses**. Equivalently, the **last player able to place a domino
wins**. There are no draws.

Because every move fills exactly two cells, the game is strictly bounded and
always terminates.

## The parity result (mirror strategy)

The one **rigorously proven** result for Cram under normal play is the
even-by-even theorem:

- **Both dimensions even → the SECOND player wins.** The second player uses a
  *mirror (symmetry) strategy*: whatever domino the first player places, the
  second player places the domino obtained by reflecting it through the centre
  of the board (a 180° point reflection). On an even-by-even board this reflected
  pair of cells is always distinct from the first player's and still empty, so
  the second player can always reply — and thus makes the last move.

Beyond that, **Cram does not have a simple closed-form winner.** The commonly
quoted shortcut "both even → 2nd player, otherwise 1st player" is *incomplete*:
it is wrong for some odd-by-odd boards — for example the **3×3 board is a
SECOND-player win**, not a first-player win. (The trivial too-small case `1x1`
has no legal move at all, so the player to move loses immediately.)

For the offered and adjacent small boards the exact outcomes are determined by
exhaustive game-tree search. Illustrative cases:

- `2×2` (both even) — **second player wins** (mirror).
- `2×3` — **first player wins**.
- `3×3` (both odd) — **second player wins** (the formula's exception).
- `4×4` (both even) — **second player wins**.

This package's `selftest.py` verifies these by exhaustive search and bakes the
searched outcomes as plain assertions (and asserts the even-by-even mirror
theorem for `2×2`, `2×4`, `4×2`, `4×4`).

## Move notation

A move is the two covered cells written as a path: `c,r>c2,r2`, where the second
cell is orthogonally adjacent to the first. In the web UI click the two cells of
the domino (the interface offers only legal second cells). A placed domino shows
as two cells filled in the placer's colour, with the most recent domino
highlighted.

## Ruleset notes

- **Normal play only** (last to move wins). The misère variant (last to move
  loses) is *not* offered.
- The standard game is played on an empty rectangular board; this package does
  not implement pre-removed cells or non-rectangular regions.
- Because the game is impartial, the two players' pieces are coloured only to
  show who placed each domino; it has no effect on legality.
