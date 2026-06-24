# Quantik

*Nouri Khalifa — Gigamic, 2019.* A two-player abstract logic game. Rules below
are **as implemented** in this package.

## Equipment

- A **4×4** board, partitioned into **four 2×2 zones** (quadrants):
  top-left, top-right, bottom-left, bottom-right.
- **Four shapes**, labelled here **A**, **B**, **C**, **D** (the physical game's
  cube / sphere / cylinder / cone). On the board they are drawn as distinct
  glyphs: A = ■ (square), B = ● (circle), C = ▮ (bar), D = ▲ (triangle).
- Each player has **8 pieces in their own colour** (Red = player 1, Blue =
  player 2): **two of each of the four shapes**, held off-board in a reserve tray.

## Turn

On your turn you **place one of your reserved pieces** (any shape you still
have) onto an **empty cell** — subject to the placement restriction below.

### Placement restriction (the crux)

> You may **not** place a shape in a row, column, or 2×2 zone in which the
> **OPPONENT** has already placed that **same shape**.

You **may** place a shape that matches one of **your own** pieces already in
that row, column, or zone — the restriction only blocks matching the
**opponent's** shape. (So a row may legally end up holding two of the same shape
as long as they are both yours.)

## Winning

The player who **places the fourth different shape** that completes any **row,
column, or 2×2 zone** — so the line/zone contains **all four distinct shapes**
(one each of A, B, C, D) — **wins immediately**. The pieces' **colours do not
matter** for the win; either player's pieces can fill the line, and whoever
places the completing piece wins.

## Losing (no legal move)

There is no passing. If, on your turn, you **cannot make any legal placement**
(every empty cell is blocked for every shape you still hold), **you lose**.

A completely full board with no all-four-shapes line/zone is scored as a draw,
but this is essentially unreachable in normal play.

## Move encoding

A move is a reserve-tray **drop**: `"<shape>@c,r"`, e.g. `"A@1,2"` places shape
A on the cell at column 1, row 2 (0-indexed). In the web UI, click your shape
chip in the reserve tray, then click a highlighted empty cell.
