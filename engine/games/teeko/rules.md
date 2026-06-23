# Teeko

**Teeko** was invented by John Scarne in 1937 (and refined into the early 1950s).
It is a two-player game on a **5x5 board** of 25 cells. Each player has **four
markers**. The rules **as implemented** here are described below.

## The board

The 25 cells sit on a 5x5 grid, addressed by their coordinate `c,r` on a 0..4
layout (so `0,0` is top-left, `4,4` is bottom-right). It is a plain square board.

## Phase 1 — dropping

Players alternate **dropping** one marker on any empty cell. The first player
(Red) drops first. Dropping continues, strictly alternating, until each player
has placed all **four** markers — **eight drops total**.

If completing a drop already puts your four markers into a winning shape (see
**Winning**), you **win immediately** — the dropping phase does not have to
finish first.

## Phase 2 — moving

Once all eight markers are on the board, players alternate **moving**: slide
**one** of your markers to an **adjacent empty cell**. Adjacency is the **eight
surrounding cells** — the four orthogonal *and* the four diagonal neighbours
(i.e. one chess **king's step**). You may not move onto an occupied cell, and you
may not move off the board.

There is **no capture or removal** — markers are never taken off the board.

## Winning

You **win** the instant your four markers form **one** of these shapes:

1. **Four-in-a-row** — four consecutive cells in a straight line, in any of the
   four directions: **horizontal**, **vertical**, or **either diagonal**.
2. **A 2x2 square** — four cells forming a solid 2-by-2 block.

The win condition is checked **after every drop and after every move**, and the
win is attributed to the player who just moved. A win can therefore occur during
the dropping phase or during the movement phase.

## Drawing (no-progress rule)

Because the movement phase can otherwise shuffle markers forever, this package
declares a **draw after 80 movement plies** (40 moves per player) with no win.
Drop plies are not counted toward this cap; the clock only runs during the
movement phase. This is a generous, purely practical bound that guarantees the
game terminates — real games are decided (or seen to be drawn) far sooner.

## Ruleset choice — base Teeko only

This package implements **base Teeko**. Scarne later promoted an **"advanced
Teeko"** with extra rules (notably allowing a marker to **jump** an adjacent
marker, and other tournament refinements). Those advanced rules are **NOT
implemented here** — movement is strictly a single king-step slide to an empty
cell, and there are no jumps or captures.

## Strategy note — a known draw

Teeko has been **completely solved**. With perfect play by both sides the base
game is a **draw**: neither player can force a win against correct defence. (This
was established by exhaustive computer analysis; Scarne himself long believed the
game might be a first-player win, which the solution disproved.) The implication
for play is that mistakes, not the opening, decide real games.

## Notation

During dropping, a move is a single cell like `2,2` (shown as `@2,2` in the move
log). During moving, it is `from>to`, e.g. `2,2>2,3` (shown as `2,2-2,3`). Cells
are named by their `c,r` coordinate on the board diagram.
