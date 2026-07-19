# Shape Chess (Xingqi, 形棋)

By 日出 "Richu" of Guangzhou, China (2022 rules; first version 2010). The pattern
game where the winning pattern is a geometric *property*: **mirror symmetry**.
Rules as implemented follow David Ploog's article in *Abstract Games* magazine
issue 24 (Winter 2022).

## Board and stones

- A square grid of points, **12×12** by default (13×13, 15×15 and 19×19 are
  offered as options — any Go or Renju board works). Stones sit on the points.
- Both players have an unlimited supply of stones. **Black moves first.**

## Shapes and symmetry

- A **shape** is a stone together with all same-coloured stones reachable by
  orthogonal *or diagonal* steps (8-way connectivity).
- A shape is **symmetric** if it is preserved by reflection along some line:
  a vertical or horizontal line **through the points or between them**
  (half-grid lines count), or a **diagonal** line. **Rotational symmetry does
  NOT count** — a shape with only 180° symmetry is not symmetric.

## A turn

Play exactly one of the three actions:

1. **Drop** — place an own stone on any empty point.
2. **Jump** — move an own stone to any empty point, *anywhere* on the board.
3. **Push** — move an **enemy** stone to an adjacent empty point (any of its 8
   neighbours — *you* choose which) and place an **own** stone on the point it
   left.

Drops and pushes add one of your stones to the board; jumps do not.

## Scoring

If **after your turn** there are symmetric shapes of **6 or more stones of
your own colour**:

1. every such shape is **removed** from the board,
2. each removed shape of n stones scores you **n − 5 points**,
3. you immediately take **another turn** (and this can chain).

Only the mover's colour is ever checked — you never score or remove on the
opponent's turn.

## Winning

The first player to reach **4 points** (adjustable via the *Winning score*
option) wins immediately.

## End-of-game additions (this implementation)

The article assumes play continues until someone reaches the target. For a
guaranteed finish this implementation adds:

- If the **board fills completely** there is no legal move: the game ends and
  the **higher score wins**; equal scores are a draw.
- **No-progress rule:** if no scoring happens for max(120, n×n) consecutive
  turns, or after 6×n×n total turns, the game ends the same way (higher score
  wins; a genuine tie is an honest draw).

## Notation

Cells are shown in algebraic coordinates (a1 = bottom-left; file letters
include "i"). The move log writes `Drop e5`, `Jump f6-d9`, `Push e5:e4`
(pushed stone's origin : its destination), with `(+n)` marking points scored.
Click an empty point to drop; click one of your stones then an empty point to
jump; click an enemy stone then an adjacent empty point to push.
