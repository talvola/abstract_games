# Tumbleweed

**Designer:** Mike Zapawa (2020). A modern two-player abstract influence /
area game on a hexagonal board of hexagons. *Rules as implemented in this
package.*

## Board

A **hexhex** of side length *N* (axial coordinates `q,r`; a cell is on the
board iff `max(|q|,|r|,|q+r|) <= N-1`). Default **N = 8** (the most common
competitive size, "hexhex-8"); an `N = 6` option is provided for a faster
game. Each hex holds **at most one stack** — a pile of 1..K tokens of a single
colour. The colour on a hex's stack is said to *control* that hex.

## Setup

- A **neutral** stack of **height 2** sits on the centre hex `0,0`.
- Each player gets **one starting stack of height 1**.

This package uses a **simple fixed opening**: White starts on `(N-1, -1)` and
Black on the point-reflected hex `(-(N-1), 1)` — two opposite border hexes, both
height 1, each already able to see the centre.

> **Ruleset choice (flagged):** The official game uses a host/guest
> **"settlement" opening** in which the two starting hexes are *chosen* (with a
> pie-style swap), creating an asymmetric meta-phase. We deliberately omit that
> and use a fixed symmetric opening so the package is self-contained and
> deterministic. The core influence/stacking mechanics below are faithful.

## Line of sight

For the player to move and a given target hex, look outward along each of the
**6 straight hex directions**. Along a direction, the **first stack** you reach
is the only one that matters: it contributes **+1** to the target's
line-of-sight (LOS) count **iff it is your colour**, and in every case it
**blocks** sight further along that direction. So a hex's LOS for you is an
integer **0..6** (at most one per direction). Your own, the enemy's, and the
neutral stack all block sight equally.

## Placing a stack (the move)

Choose **any** hex (empty, yours, the enemy's, or the neutral centre) and let
**L** be its LOS count for you. You may place a stack of **your colour and
height exactly L** on that hex **iff**:

1. **L ≥ 1** (at least one of your stacks sees it), and
2. **L is strictly greater than the height currently on the target.**

Placing **replaces** whatever stack was there. Therefore L lets you:

- **settle** an empty hex (current height 0, so any L ≥ 1 works),
- **grow** one of your own shorter stacks, or
- **capture** a shorter enemy stack or the neutral centre stack.

The move notation is the single target cell, e.g. `3,4`.

## Pass

A player may **pass** (move `pass`) instead of placing.

## End of game

The game ends when **both players pass in succession** (two consecutive
passes), or when the board is fully locked (neither player has any legal
placement). A hard ply cap also forces an end as a safety net; because every
placement strictly changes the board, normal play cannot loop.

## Winning — owned + controlled territory

At the end, **every cell on the board is scored** ("owned + controlled"):

- An **occupied** cell counts for the player whose colour **tops** it. The
  **neutral** stack counts for **nobody**.
- An **empty** cell counts for the player with **strictly greater line of
  sight** to it (the same LOS rule used for placing). If both players have
  **equal** LOS — including **0–0** (neither sees it) — the cell is **neutral**
  and counts for neither.

Each player's score is therefore *(their occupied cells) + (empty cells they
control by majority LOS)*. The player with the **most total cells wins**;
**equal totals is a draw**. Both players' scores plus the neutral cells always
sum to the whole board (e.g. a finished hexhex-8 totals 169 cells, scoring like
White 89 : Black 80).

## Official source

See the [BoardGameGeek Tumbleweed page](https://boardgamegeek.com/boardgame/318702/tumbleweed).
