# Achi

Achi is a traditional two-player **alignment game from Ghana**, played on a
**3x3 grid of 9 points**. It belongs to the Three Men's Morris family but is
distinguished by one thing: each player has **four pieces, not three**. The rules
**as implemented** here are described below; they follow Wikipedia's "Achi
(game)" entry.

## The board

The nine points sit on a 3x3 grid, addressed by their coordinate `x,y` on a
0..2 layout (so `0,0` is top-left, `1,1` the centre, `2,2` bottom-right).

The eight **lines** are the three rows, the three columns, and the two main
diagonals. These same eight lines define both how you win and how pieces may
move.

**Adjacency for sliding:** two points are adjacent when they are *consecutive*
along one of those eight lines. As a result:

- the **centre** (`1,1`) is adjacent to all eight outer points;
- each **corner** (`0,0`, `2,0`, `0,2`, `2,2`) is adjacent to its two
  edge-midpoint neighbours and the centre (three points), including the diagonal
  link to the centre;
- each **edge-midpoint** (`1,0`, `0,1`, `2,1`, `1,2`) is adjacent to its two
  corner neighbours and the centre (three points).

(In particular, corners are **not** adjacent to each other, and the two edge
points on opposite sides of the board are not adjacent.)

## Pieces

Each player has **four pieces** (one plays the white/red pieces, the other the
black pieces). This is the key difference from Three Men's Morris / Tapatan,
where each player has only three.

## Phase 1 — placing

Players alternate **placing** one piece on any empty point. White/red places
first. Placing continues until all **eight** pieces are on the board — four for
each player. Because the board has **nine** points, exactly **one point is left
empty** when placement ends.

If completing a placement puts your three pieces onto one of the eight lines, you
**win immediately** — placement does not have to finish first.

## Phase 2 — moving

Once all eight pieces are on the board, players alternate **moving**: slide one
of your pieces along a line into the (single) **adjacent empty point** (see
adjacency above). There is **no capture or removal** — pieces are never taken off
the board. Because only one point is empty at a time, the empty point migrates
around the board as the game develops.

## Winning

You **win** the instant **three of your pieces** occupy one of the eight lines (a
row, column, or diagonal). This can happen during placement or during movement.

In addition, following the standard rule, **a player who cannot move on their
turn loses** (equivalently, the player who leaves the opponent with no legal
slide wins). This is reachable in Achi because there is only one empty point: if
the side to move has no piece adjacent to it, they are stuck.

## Drawing (no-progress rule)

Because the movement phase can otherwise shuffle pieces forever, this package
declares a **draw after 80 movement plies** (40 moves per player) with no win.
Placement plies are not counted toward this cap; the clock only runs during the
movement phase. This is a generous, purely practical bound to guarantee the game
terminates — real games are decided far sooner.

## Ruleset choices made in this implementation

- **Diagonal wins count.** Wikipedia notes a variant in which only horizontal and
  vertical 3-in-a-rows win; this package uses the **standard rule where diagonals
  also win** (and the two diagonals are also legal sliding lines).
- **No-move loss is enforced** (per the standard rule). The side that leaves the
  opponent unable to move is credited with the win.
- **No opening restriction** — the first player may place anywhere, including the
  centre, on move one.

## Notation

During placing, a move is a single point like `1,1` (shown as `@1,1` in the move
log). During moving, it is `from>to`, e.g. `0,0>1,0` (shown as `0,0-1,0`). Points
are named by their `x,y` coordinate on the board diagram.
