# Conspirateurs

**Conspirateurs** is a traditional board game from France, probably invented
before 1800 (after the French Revolution of 1789). It plays like *Halma* /
*Chinese Checkers*: there is **no capturing**, and you win by getting **all** of
your men ("conspirateurs") safely into the **sanctuaries** ("shelter holes") on
the rim of the board. This package follows the **nestorgames 2-player edition**
(Néstor Romeral Andrés, 2018).

## Board

- **17 × 17 square cells**, columns/rows `0..16`.
- A **9-wide × 5-tall** block of cells in the dead centre (cols 4–12, rows 6–10)
  is the **"secret meeting place"** — the drop zone (shown pale blue).
- A ring of **sanctuary** cells sits on the perimeter (shown gold). A sanctuary
  holds at most one man.

## Pieces

- Player 0 = **Black** (moves first); Player 1 = **White**.
- Each player has **20 men** in play. (The physical box supplies 21 cones per
  colour — one spare; only 20 are used.)

## How to play

The game has two phases.

### 1. Drop phase

Players alternate **placing one man per turn** on any vacant cell of the central
9×5 area, until each side has placed all 20 men. **No man may move until both
sides have finished dropping.** (If one side finishes first, the other simply
keeps placing its remaining men.)

### 2. Move phase

On your turn you move **one** man, choosing either:

- **Step** — move to one of the 8 adjacent cells (orthogonal or diagonal) that is
  **empty**; or
- **Jump** — hop over exactly one **adjacent occupied** cell (friend *or* foe,
  whether or not the jumped man is on a sanctuary) and land on the **empty** cell
  immediately beyond. From the landing cell you **may continue jumping** (each hop
  may change direction). The whole chain is **one move**, and you may **stop after
  any hop** (jumping is never compulsory).

A **jumped man is never captured** — there is no capturing in Conspirateurs.

A man that **begins your turn already on a sanctuary may not move.** Moves may
never leave the 17×17 board.

### Movement notation

- A **drop** is a single cell, e.g. `8,8` (one click).
- A **step** is `from>to`, e.g. `8,7>8,6`.
- A **jump chain** is `from>land>land>…`, listing every cell the man lands on,
  e.g. `8,7>8,5>10,5`.

## Goal

> The first player to have **all 20 of their men resting on sanctuary cells** wins.

## Termination / draws

The move phase is a pure no-capture race, and a man can never leave a sanctuary
once it arrives, so men only ever flow toward the rim. As a defensive guarantee
of termination (the platform plays random games to a terminal state), the game is
a **draw** if a hard ply cap is reached or if a long stretch of move-phase turns
passes with the mover gaining no new shelter. Real games end far below these caps.

## Ruleset choices & notes (flagged for review)

- **Men per player: 20.** The nestorgames rulebook says "In two-player games, each
  side has **20 men**, and players take all the **21 cones** of that colour" — i.e.
  20 men *in play*, 21 physical cones supplied (one spare). Wikipedia and Ludii also
  state 20. So **20 men per side** are dropped and must be sheltered to win; the 21st
  cone is just a spare.
- **Sanctuary layout — RECONSTRUCTED.** The published board marks **39** perimeter
  cells as shelters, but the exact cell-by-cell map of those 39 is not recoverable
  from the available text sources (Wikipedia, the nestorgames rulebook text, Ludii,
  and the di.fc.ul.pt diagram all state "39 shelters on the perimeter, clustered at
  the corners and edges" without listing coordinates). This package therefore uses
  a clean, **fully symmetric reconstruction of 40 shelter cells**: an L-shaped
  cluster of 7 in each of the four corners (the corner cell plus 3 cells inward
  along each border) **plus** a 3-cell cluster at the midpoint of each of the four
  edges. This is faithful in spirit — shelters cluster at the corners and
  edge-midpoints of the rim, and capacity (40) comfortably exceeds the 20 men a
  side must shelter — and differs from the published board only by one decorative
  cell in the count. **The rules of play (drop, step/jump, no-capture,
  all-men-home win) are exact.** If a precise published shelter map is obtained,
  only `_sanctuaries()` in `game.py` needs to change.
- **3- and 4-player variants** exist (15 and 11 men; partnership play) but are not
  implemented here — this package is the standard 2-player game.

## Differences from the prompt's summary

The brief described queen-like (chess-queen) movement with a "may not land
adjacent to another piece" constraint. That is **not** how Conspirateurs is
actually played. The real game (verified against Wikipedia, the nestorgames 2018
rulebook, and Ludii) is a **Halma-style step-and-jump race with no adjacency
constraint and no capturing**, implemented faithfully above.

## Sources

- Wikipedia, "Conspirateurs".
- nestorgames, *Conspirateurs* rulebook (EN), © 2018 Néstor Romeral Andrés.
- Ludii Games — "Conspirateurs".
- BoardGameGeek #60707.
