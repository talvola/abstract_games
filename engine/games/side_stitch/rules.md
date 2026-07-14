# Side Stitch

By **Craig Duncan, 2017**. A connection/scoring game on a hexagonal board whose
edge is divided into seven coloured "sides". It is the parent of Duncan's
*Exo-Hex* (2019), which replaces the coloured sides with owned stones sitting
outside the board.

## Board

- Played on a **hexhex-8** board (hexagon of hexagons, side length 8 =
  **169 cells**). All cells start empty and the whole board is playable.
- The **perimeter** is the ring of **42 cells** at the board's edge. It is
  partitioned into **seven colour-sides**: orange, yellow, green, blue, purple,
  pink and red. Each colour is touched by exactly **7 perimeter cells**.
- **Boundary cells:** the seven cells where two colour-sides meet (one at each of
  the six corners plus the seventh join) belong to **both** of their neighbouring
  colours — such a cell counts as touching **both** sides.

## Play

- **Black moves first.** On your turn, place one stone of your colour on any
  empty cell, or **pass**. Stones never move and are never removed.
- **Pie rule** (on by default): on the second player's first turn they may
  **swap** — take over the opener's stone as their own colour — instead of
  placing.
- The game ends when **both players pass in succession**, or when the board is
  full.

## Scoring

- Your stones form connected groups under hex adjacency. **A group's value is
  the number of distinct colour-sides it touches.** A group touches a colour-side
  if any of its stones sits on a perimeter cell adjacent to that side; a boundary
  cell counts for **both** of its colours.
- **The owner of the single highest-valued group wins.**
- **Recursive tiebreak:** if the best groups tie, set them aside and compare the
  next-best groups, and so on (i.e. compare the two players' descending lists of
  group values; a missing entry counts 0). The designer notes it is impossible
  for the values to tie "all the way down" on a played-out board.
- *Implementation note:* the impossibility claim holds for played-out boards, but
  if both players pass early in a symmetric position — e.g. an immediate double
  pass on the empty board — the group values really do tie all the way down. Such
  a genuine total tie is scored as an honest **draw** (no fabricated tiebreak).

## Notes

- Maximum value for one group: touching all **7** colour-sides.
- Sources: the designer's rules in the
  [BGG description](https://boardgamegeek.com/boardgame/223388/side-stitch), plus
  Eric Silverman's
  [*Connection Games V: Side Stitch*](https://drericsilverman.com/2020/03/12/connection-games-v-side-stitch/).
  The per-cell colour map was extracted from Duncan's reference board image.
