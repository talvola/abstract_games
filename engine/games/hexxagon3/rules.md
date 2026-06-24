# Hexxagon (3-player)

**Hexxagon (3-player)** is the three-player variant of **Hexxagon** — the
hexagonal-board variant of **Ataxx** (a clone / jump / infection game). Spread
your colour across the board; whoever holds the most hexes at the end wins.

> **Designed extension.** Published Ataxx / Hexxagon sources focus on the
> **two-player** game. The exact three-player layout below — the alternating
> P0/P1/P2 corner setup, the turn order that skips eliminated players, and the
> three-way win — is **our designed extension**, chosen to be symmetric and fair.
> The board geometry and the per-move mechanics are identical to 2-player Hexxagon.

## Board

A **hexagon of hexagons** ("hexhex") of side length **5 = 61 cells**, with **3
blocked "holes"** near the center removed, leaving **58 playable hexes**.

- Cells use **axial coordinates** `q,r`. A cell is on the board when
  `max(|q|, |r|, |q+r|) <= 4`. Hex distance between two cells is
  `(|dq| + |dr| + |dq+dr|) / 2`.
- **Holes** are dark, blocked cells: you can never move onto one, no piece ever
  sits there, and they are *not* counted as neighbours for infection.

### Holes layout (interpretation)

We use a clean, **3-fold rotationally-symmetric** default: the 3 holes at `(1,0)`,
`(-1,1)`, `(0,-1)` — three of the six cells adjacent to the center, at alternating
120°-apart positions. This leaves the center `(0,0)` playable and the board
symmetric for all three players. You can turn holes off entirely with the **Center
holes** option (`none` → all 61 hexes playable).

## Players, pieces, and start

**Three players** — **Red (P0, moves first)**, **Blue (P1)**, and **Green (P2)** —
each start with **2 pieces** (6 total). The six corners of the hexagon, in cyclic
(angular) order, are
`(0,-4), (4,-4), (4,0), (0,4), (-4,4), (-4,0)`.
Going around the ring they are assigned **P0, P1, P2, P0, P1, P2** (`owner = i mod 3`):

- **Red (P0):** `(0,-4)`, `(0,4)`
- **Blue (P1):** `(4,-4)`, `(-4,4)`
- **Green (P2):** `(4,0)`, `(-4,0)`

So each player owns **two opposite corners** (3 apart in the cycle), and adjacent
corners always belong to **different** players. This is **3-fold rotationally
symmetric** and fair.

## A turn

On your turn you **move one of your pieces onto an empty (non-hole) cell**, in one
of two ways, by hex distance from the source:

- **Grow / clone — hex distance 1** (one of the **6 adjacent hexes**): a **new**
  piece of your colour appears on the destination; the **source stays** (you go
  from *n* to *n+1* pieces).
- **Jump — hex distance exactly 2** (the **12-hex second ring**): the piece
  **relocates** — the source becomes empty, your piece count is unchanged.

Moves are written `src>dst`, e.g. `0,-4>1,-4` (a grow) or `0,-4>2,-4` (a jump).

### Infection

After your piece lands (grow or jump), **every piece belonging to *either*
opponent in the 6 hexes adjacent to the destination flips to your colour.** Both
opponents are affected — a single landing can flip a Blue and a Green piece in the
same move. Only the immediate 6-neighbourhood of the landing cell is affected —
there is no chaining, and holes are never neighbours.

### Passing and elimination

Turn order cycles **P0 → P1 → P2 → P0**, but it **skips** any player who is
**eliminated** (has 0 pieces) or who currently has **no legal move** (they pass).
An eliminated player is permanently out. So the turn always advances to the next
player who still has pieces *and* a move.

## Ending and winner

- **Last survivor (auto-fill):** if, after a move, **only one player still has
  pieces** (both opponents are eliminated — e.g. their last pieces were infected
  away), the surviving player's colour **automatically fills every remaining empty
  (non-hole) cell** and that player **wins** immediately.
- Otherwise the game ends when:
  - the board is **full** (all playable hexes occupied), **or**
  - **no remaining player can move**.

  Then the **winner is the player with the most pieces** (a three-way count). A
  **sole leader wins**; a **tie for the most pieces is a draw**.

## Scoring (returns)

Matching the platform's multi-player convention (as used by Rolit): the **sole
leader scores +1** and **both other players score −1**; a **tie for the lead is a
draw** (all three score 0).

## Termination

Every grow adds a piece (the board is bounded at 58), and jumps and infections
never reduce the total piece count, so play cannot cycle indefinitely. A defensive
hard ply cap also forces an end-and-count.

## Notes / interpretations

- This is the **3-player hex Ataxx** variant; the per-move mechanics (clone, jump,
  infect, most-pieces wins, pass on no move, auto-fill on last survivor) mirror
  2-player Hexxagon exactly — only the player count, starting layout, turn order
  (skip eliminated/stuck), and three-way win/scoring differ.
- The **alternating-corner P0/P1/P2 setup** and the **holes layout** are our
  documented design choices (see above).
