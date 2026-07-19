# Boom & Zoom

Ty Bomba's abstract wargame of laser-tower stacks (Victory Point Games 2012;
definitive **2nd edition, Hollandspiele 2018** — the ruleset implemented here,
as published in full in *Abstract Games* magazine #21, pp. 21–25).

## Setup

8×8 board. Each side has 12 counters, stacked as **four 3-high stacks on the
four central squares of the home row**: White on c1–f1, Black on c8–f8.
White moves first. Stacks never split or merge — every stack stays one colour
and moves as a whole.

## A turn — one action with one of your stacks

- **Zoom (move):** move the stack in a straight line — any of the 8
  directions, backwards included — over **free** squares only, a distance of
  **1 up to the stack's height**.
- **Boom (shoot):** instead of moving, pick a square the stack *could
  otherwise move to* (straight line, clear path, distance ≤ height) that
  holds an **enemy** stack, and remove **one counter** from it. The shooter
  stays put. Shot counters are gone for good — nobody scores them.

## Bearing off (scoring)

Beyond your **opponent's** home row lies a virtual goal row of **ten**
squares — the eight files plus one corner square past each edge, so a stack
may also escape **diagonally through the corner**. A zoom that lands there
takes the stack off the board and scores **1 point per counter**. The path
must stay on the board until the final square; you may never leave the board
sideways, and never enter the goal row on your *own* side.

## End of the game

The game ends the instant one side has **no counters left on the board** —
its last stack borne off, or its last counter shot away. The player with the
**higher score wins**; an equal score is a **draw**.

## Engine backstops (this implementation)

- If **100 consecutive plies** pass in which no counter leaves the board
  (no boom, no bear-off), the game is adjudicated by the current score
  (equal = draw).
- A player with no legal action must pass (with whole-stack movement in all
  8 directions this is believed unreachable in practice).

## Notation

Squares a1–h8, White at the bottom. `c4-f7` zoom, `b4:b6 (3→2)` boom,
`d2-off (+3)` bear-off. On the board, click your stack, then the destination
square — enemy stacks in range are boom targets, tinted goal-row squares are
bear-off destinations.

## Sources

- David Ploog, "A game by Ty Bomba: Boom & Zoom", *Abstract Games* #21
  (Spring 2021), pp. 21–25 — complete rules, diagrams and two problems
  (solutions p. 29), all reproduced as this package's self-test anchors.
  (Note: the magazine printed the two problem diagrams with their
  captions swapped; this package uses the pairing consistent with the
  printed solutions and with exact counter accounting.)
- [BGG: Boom & Zoom (2nd edition)](https://boardgamegeek.com/boardgame/243927/boom-and-zoom-second-edition);
  1st edition: boardgamegeek.com/boardgame/126807.
- abstractgames.org/boomzoom.html (Ploog's site, same ruleset).
