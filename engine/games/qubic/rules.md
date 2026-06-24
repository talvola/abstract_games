# Qubic

**Qubic** is three-dimensional tic-tac-toe, played on a **4×4×4 cube** (Parker
Brothers, 1953). It is famously **solved**: with perfect play the first player
wins (Oren Patashnik, 1980).

## The board

The cube has **64 cells**, each addressed by coordinates `(x, y, z)` with `x`,
`y`, `z` each in **0..3**. There is **no gravity** (unlike Score Four): every
empty cell is a legal placement, regardless of whether the cells "below" it are
filled.

This package lays the cube out as **four side-by-side 4×4 grids** — one grid per
layer `z = 0, 1, 2, 3`, drawn left → right with a small gap. Within each grid,
`x` runs left→right (0..3) and `y` runs top→bottom (0..3). A faint tint band
distinguishes the four layers.

## How to play

- Player **0 plays X**, player **1 plays O**. X moves first.
- On your turn, **place one of your marks on any empty cell**.
- The move string is the cell id **`"x,y,z"`** (e.g. `"1,2,0"`). In the web UI
  each empty cell is directly clickable (click-to-place).

## Winning — the 76 lines

You **win immediately** by getting **four of your marks in a straight line**.
A straight line is any of the cube's **76 winning lines**:

- **48 axis lines** — straight rows, columns, and pillars
  (4×4 lines per axis × 3 axes).
- **24 face diagonals** — the two diagonals of each 4×4 plane, across all 12
  axis-aligned planes.
- **4 space diagonals** — the corner-to-corner diagonals through the cube,
  e.g. `(0,0,0)–(1,1,1)–(2,2,2)–(3,3,3)`.

`48 + 24 + 4 = 76`. The package enumerates these lines programmatically and its
selftest asserts the count is exactly **76**.

## Draw

If all 64 cells are filled and no one has completed a line, the game is a
**draw**. (Possible in principle; with perfect play the first player wins, but
ordinary play can draw.)

## Source

Official / reference: [Qubic on BoardGameGeek](https://boardgamegeek.com/boardgame/1958/qubic)
and Wikipedia, *3D tic-tac-toe*.
