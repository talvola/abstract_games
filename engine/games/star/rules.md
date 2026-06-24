# Star

**Star**, by Craige Schensted (later **Ea Ea**) and Ea Ea — first published in
*Games* magazine, 1983. A two-player connection / scoring game in the Y / Poly-Y
family, and the direct ancestor of *Star (board game)*'s relatives and of
Christian Freeling's *Starweb*.

## The board

Star is played on a **hexagon of hexagonal cells** whose six sides **alternate in
length** between two values `A` and `B` (default **A = 5, B = 6**, giving **106
playing cells**). The alternating sides make the perimeter **odd**, which is what
guarantees the game is **drawless**.

Hugging the outside of the playing area are the **"partial hexagons"** — the
**border cells** (drawn as half/edge hexes around the rim). **These are not
playable**; they exist only for scoring. By the geometry:

- each of the **6 corner** playing cells touches exactly **3** border cells,
- each non-corner **edge** playing cell touches exactly **2** border cells,
- every **interior** playing cell touches **0**.

The default board has **39 border cells** (odd).

Coordinates are axial `q,r` (cube `s = -q-r`). The playing cells are those with
`-B ≤ q, r, s ≤ A`. Adjacency is the six hex neighbours.

| Option `size` | Playing cells | Border cells |
|---|---|---|
| `4x5` | 73 | 33 |
| `5x6` (default) | 106 | 39 |
| `6x7` | 145 | 45 |

## Play

- **Black** (player 1) and **White** (player 2) alternately place one stone of
  their colour on any **empty playing cell**. Stones never move and are never
  captured.
- A player may **pass** at any time.
- **Pie / swap rule** (option, on by default): on the second player's very first
  turn they may play **swap** instead of placing — they take over the opening
  stone as their own and pass the move back.
- The game **ends** when **both players pass in succession** (hard safety net:
  it also ends when every playing cell is full).

## Scoring — the heart of the game

Like-coloured connected stones form a **group**. A group that touches at least
**three distinct border cells** is a **"star"**, worth

> **(number of distinct border cells the group touches) − 2**

A group touching **fewer than three** border cells scores **0** (such groups are
still useful for cutting the opponent). A border cell is **shared**: if groups of
both colours are adjacent to the same partial hexagon, it counts toward **each**
of their touch-counts.

Worked examples (on the default board):

- a **lone stone on a corner** touches 3 border cells → `3 − 2 = 1` point;
- a **lone stone on an edge** touches 2 → not a star → `0`;
- a group touching **5** border cells → `5 − 2 = 3` points.

A player's **total** is the sum over their stars. The **combined** two-player
score is bounded by `(#border cells) − 2` by Schensted's constant-sum structure.

## Winner

The player with the **higher total** wins. Star is **drawless** by design (the
perimeter is odd). In the implementation, a tie — only reachable on a
near-empty pass-out — is awarded to the player who placed the **second** stone
(White), mirroring the convention used for Starweb.

## Implementation notes / interpretations

- **Corner scoring.** We use the **original** rule: a corner touches **3**
  border cells (so a lone corner stone scores **1**). Schensted later proposed a
  variant making each corner worth **2** (by turning corners into five-sided
  cells); we do **not** apply that variant — it would change the constant-sum
  total and is not the canonical published ruleset.
- **Termination** is guaranteed: each placement fills a cell, the playing board
  is finite, and two passes (or a full board) end the game.

## Source

- *Star (board game)* — Wikipedia: <https://en.wikipedia.org/wiki/Star_(board_game)>
- BGG entry: <https://boardgamegeek.com/boardgame/194969/star>
