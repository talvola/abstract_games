# Exo-Hex

By **Craig Duncan, 2019**. A connection/scoring game and the "distilled" sibling of
Duncan's *Side Stitch* (2017): Side Stitch's coloured board sides are replaced by
actual stones sitting outside the board, so the game plays with any plain hexhex
board and two colours of stones.

## Board and setup

- Played on a **hexhex** board (hexagon of hexagons) of odd side length *n*
  (options: 5, 7 — default, or 9). All interior cells start empty.
- **Exo-stones:** just outside each of the six sides lies an exterior row of
  *n−1* pre-placed stones, one hex further out than the board's edge. Each
  side's row is **one black string and one white string** of *(n−1)/2* stones
  each, and the 12 strings **alternate in colour** around the whole perimeter
  (6 strings per player). The 6 exterior **corner positions are empty gaps** —
  no exo-stone sits on a corner.
- Which colour comes first on a given side is a pure orientation choice (the
  arrangement is symmetric under 60° rotation); this implementation fixes the
  black half first in rotational order, matching the alternation shown on the
  designer's photographed board.

## Adjacency (as implemented)

Exo-stones occupy real hex positions, so ordinary hex adjacency applies to
interior cells and exo-stones alike:

- Consecutive exo-stones of a string touch each other — **strings are
  connective**: a chain entering one end of your string is connected to a chain
  leaving the other end.
- Each exo-stone touches exactly **two** interior edge cells.
- The two exo-stones flanking a corner gap are **not** adjacent to each other —
  the **gap breaks the perimeter** at every corner.
- An interior corner cell touches the last exo-stone of one side and the first
  of the next (always opposite colours).

## Play

- **Black moves first.** On your turn, place one stone of your colour on any
  empty interior cell (exo positions are never playable), or **pass**. Stones
  never move and are never captured.
- **Pie rule** (on by default): on the second player's first turn they may
  **swap** — take over the first stone as their own colour — instead of placing.
- The game ends when **both players pass in succession**, or when the board is
  full.

## Scoring

- Your stones — interior placements plus your own exo-stones — form connected
  groups. **A group scores the number of exo-stones it contains.**
- **The owner of the single highest-scoring group wins.**
- **Recursive tiebreak:** if the best groups tie, set them aside and compare the
  next-best groups, and so on (i.e. compare the two players' descending lists of
  group scores; a missing entry counts 0). The designer notes it is impossible
  for the scores to tie "all the way down."
- *Implementation note:* the impossibility claim holds for played-out boards,
  but if both players pass early in a symmetric position — e.g. an immediate
  double pass on the untouched starting position — the group scores really do
  tie all the way down. Such a genuine total tie is scored as a **draw**.

## Notes

- Maximum score for one group: connecting all 6 of your strings yields
  3(n−1) exo-stones (18 on the default hexhex-7).
- Source: the designer's rules in the
  [BGG description](https://boardgamegeek.com/boardgame/291638/exo-hex), plus
  Eric Silverman's
  [*Connection Games V: Side Stitch*](https://drericsilverman.com/2020/03/12/connection-games-v-side-stitch/)
  (confirms the connective sides and the board arrangement).
