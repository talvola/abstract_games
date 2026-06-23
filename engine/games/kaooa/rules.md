# Kaooa (Vultures and Crows)

Kaooa (also spelled *Kowwa*; "vultures and crows") is a traditional hunt game
from India. It is **asymmetric**: one player controls a single **Vulture**, the
other controls seven **Crows**. These are the rules **as implemented** here.

## The board

The board is a **five-pointed star (pentagram)** with **10 points**:

- **5 outer points** — the tips of the star (`T0`–`T4`).
- **5 inner points** — the vertices of the pentagon where the star's lines
  cross (`I0`–`I4`).

The star is drawn as five straight strokes. Each stroke runs
**tip → inner → inner → tip**, so it passes through four points in a line. **Two
points are adjacent if and only if a single straight star segment joins them
directly** (with no other point between). The connecting lines shown on the board
are cosmetic; the adjacency that governs play lives in code and is exactly:

- each **outer tip** is adjacent to **2 inner points** (degree 2);
- each **inner point** is adjacent to **2 tips and 2 other inner points**
  (degree 4).

There are 15 adjacency edges in all. A *jump* (capture) must follow one of the
five straight strokes — three consecutive collinear points on a stroke form the
`from → over → land` line of a jump.

## Pieces

- **1 Vulture** (player 2 / seat 1).
- **7 Crows** (player 1 / seat 0).

## Setup and turn order — the placement phase

The board starts empty. **The Crow player moves first.**

1. On each Crow turn during placement, the Crow player **drops one crow** on any
   empty point. The crows are placed one at a time over (up to) seven turns.
2. **After the first crow has been placed**, on the Vulture's first turn the
   Vulture is **dropped onto any empty point**.
3. From then on the Vulture may **step or jump-capture** on its turns **even
   while crows are still being placed** — the vulture is active as soon as it is
   on the board. The Crow player keeps dropping crows until all seven are down,
   and only afterwards may crows move.

## Movement

- A **Crow** may move (one step along a star segment to an adjacent empty point)
  **only after all seven crows have been placed**. Crows never capture.
- The **Vulture** may, on its turn, either
  - **step** one point along a segment to an adjacent empty point, or
  - **jump-capture**: leap over a **single adjacent crow**, in a straight line
    along a star segment, landing on the empty point immediately beyond, and
    **remove** that crow. Only one crow is captured per move — **no
    multi-jumps**, and the jump must follow a drawn star line.

## Winning

- **The Vulture wins** as soon as it has **captured 4 crows.** (With three or
  fewer crows left the crows can no longer trap it — this is the standard
  threshold cited by Wikipedia and traditional-games references.)
- **The Crows win** when the **Vulture is trapped** — it has no legal step and
  no legal jump on its turn.
- More generally, the side to move with **no legal move loses**; this is how the
  trapped-Vulture win is detected.

## Draws / termination

For safety (to guarantee the game always terminates), if **300 plies** pass
without a result the game is scored a **draw**. In normal play this is never
reached.

## Notation

A placement/drop is a single point id like `T0` or `I2` (`crow@T0` /
`vulture@I2` in the move log). A step or jump is `from>to`, e.g. `I0-T1` for a
step or `I0xT2` for a capturing jump. Points are named `T0`–`T4` (tips) and
`I0`–`I4` (inner).

## Notes on ruleset choices

- **Capture threshold = 4 crows.** Sources are consistent that the vulture wins
  by capturing crows until the crows can no longer trap it; the commonly
  documented count is **four**. (Some variants instead say "reduce the crows to
  three," which is the same boundary.) This is the implemented, flagged choice.
- **Seat assignment:** seat 0 = Crows (move first), seat 1 = Vulture. This
  mirrors the platform's other hunt game (Bagh-Chal: seat 0 = the many small
  pieces that place first, seat 1 = the hunter).
- **Vulture entry timing:** the vulture enters on its first turn, i.e. after the
  first crow is placed, and is immediately active. This is the standard sequence
  described by Wikipedia and the "Board and Pieces" reference.
