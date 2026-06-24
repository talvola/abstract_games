# ConHex

**Designer:** Michail Antonow (2002). A two-player connection game played on a
distinctive board with two overlaid layers: a lattice of placement points and a
set of cells.

## The board

- **69 placement points** ("holes") sit on an 11×11 grid of intersections.
- **41 cells** ("spaces") overlay the points, arranged in concentric octagonal
  rings: 16 cells on the outer rim (4 corner cells + 12 edge cells), then rings
  of 12, 8 and 4 cells, and a single diamond **centre** cell in the middle.
- Each cell is bordered by a fixed set of points:
  - the **16 rim cells** (corners + edges) are bordered by **3** points each,
  - the **24 interior cells** by **6** points each,
  - the **centre cell** by **5** points (including the board's exact centre).

The top and bottom sides of the board belong to **Red**; the left and right
sides belong to **Yellow**.

## Play

- **Red moves first.** On **Yellow's first move only**, Yellow may instead play
  `swap` (the **pie rule**): it takes over Red's opening peg, recoloured to
  Yellow. This neutralises a too-strong opening.
- On your turn, place one **peg** of your colour on any **empty point**.
- **Claiming a cell:** the moment you own at least **half** of a cell's
  bordering points, you immediately **claim** that cell in your colour. The
  exact threshold is ⌈n⁄2⌉ of the cell's *n* border points:
  - **2 of 3** for a rim/corner cell,
  - **3 of 6** for an interior cell,
  - **3 of 5** for the centre cell.
  A single peg can complete the claim of more than one cell at once. Pegs and
  claims are **permanent** — they never move or change owner. A cell is claimed
  by whoever reaches its threshold **first**.

## Winning

- **Red** wins by connecting the **top and bottom** sides with a contiguous
  chain of cells **Red owns**.
- **Yellow** wins by connecting the **left and right** sides with a chain of
  cells **Yellow owns**.
- Two cells are connected if they are adjacent in the cell graph (cells that
  share a border on the board).
- Each of the four **corner cells touches both of its adjacent sides** (e.g. the
  top-right corner cell counts toward both the top side and the right side).
- **Draws are impossible** — exactly one player completes a connection.

## Notation

A move is a point id `x,y` (with `x`, `y` from 0 to 10), or `swap` for the pie
option on Yellow's first turn.

## Source

Rules © 2002 Michail Antonow; rulebook © 2011 Néstor Romeral Andrés
([nestorgames PDF](http://nestorgames.com/rulebooks/CONHEX_EN.pdf)). Board
geometry (the 41 cells, 69 points, their border-point sets, the cell-adjacency
graph and the side memberships) is generated procedurally from the same
algorithm used by the reference implementation at
[AbstractPlay/gameslib](https://github.com/AbstractPlay/gameslib)
(`src/games/conhex.ts`). Official source:
[BoardGameGeek #10989](https://boardgamegeek.com/boardgame/10989/conhex).
