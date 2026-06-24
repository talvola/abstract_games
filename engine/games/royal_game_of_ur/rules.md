# The Royal Game of Ur

The **Royal Game of Ur** (the *Game of Twenty Squares*) is a ~4500-year-old
Mesopotamian race game, excavated by Leonard Woolley at the Royal Cemetery of
Ur. These rules follow **Irving Finkel's** (British Museum) widely accepted
reconstruction. Two players race seven pieces each from off-board, around a
shared track, and off the far end; first to bear all seven off wins.

## The board

Twenty squares in the classic H / dumbbell shape: two blocks (a 3×4 and a 3×2)
joined by a narrow 1×2 bridge. In this implementation the board is three rows of
eight columns, with the four corner cells of the bridge removed:

- **Top row** — `White`'s private arms.
- **Middle row** — the **shared** central lane (all eight squares).
- **Bottom row** — `Black`'s private arms.

Five squares carry a **rosette** (shown in gold). They are: each player's
start-arm corner, the **centre of the shared lane**, and each player's exit-arm
square — at path squares 4, 8 and 14.

## The path

Each piece travels **14 squares**, then off:

1. **Up your private start arm** — 4 squares.
2. **Along the shared central lane** — 8 squares.
3. **Down your private exit arm** — 2 squares, then **off** the far end.

Your private squares can never hold an enemy piece; only the shared lane is
contested.

## The dice

You roll **four tetrahedral (4-sided) dice**. Two of each die's corners are
marked; the roll is the **number of marked corners up = 0–4**. Because each die
is marked with probability ½, the roll is binomial(4, ½):

| Roll | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Probability | 1/16 | 4/16 | 6/16 | 4/16 | 1/16 |

The roll is the number of squares you move one piece. A roll of **0** is no move
— your turn passes.

## A turn

Advance **one** of your pieces exactly `roll` squares along your path. Entering
from off-board counts as moving onto path-square `roll`. You may not land on a
square already holding **your own** piece. If you have **no legal move** for your
roll (including a roll of 0), your turn passes.

- **Capture** — landing on an **enemy** piece on a **shared** (central-lane)
  square sends it back **off-board**, to restart its journey. Captures only
  happen on the shared lane.
- **Rosette safety** — a piece standing on a rosette **cannot be captured**: an
  enemy may not land on an occupied rosette.
- **Rosette extra turn** — landing on **any** rosette grants the **same player**
  another roll-and-move (chainable).
- **Bearing off** — a piece must roll the **exact** number to move off the far
  end (overshooting is illegal; you must move a different piece or pass).

## Winning

The first player to **bear all seven pieces off** the board wins.

## Move encoding & UI

Moves are `from>to` cell paths. An entering piece uses the source token `off`
(e.g. `off>3,0`); bearing off uses the destination token `off` (e.g.
`7,0>off`). When the roll yields no legal move, the only move is the **`pass`**
action button. The current roll, each side's waiting and borne-off counts, and
whose turn it is are shown in the caption (there is no separate dice prompt — the
roll is part of the position).

## Notes / interpretations

The ancient ruleset is partly reconstructed; the choices above are the standard
Finkel reconstruction (corroborated by Wikipedia and RoyalUr.net): four binary
tetrahedral dice (0–4), the 4-then-8-then-2 path, the five-rosette set, rosette
safety + extra turn, capture only on the shared lane, and exact bear-off.
