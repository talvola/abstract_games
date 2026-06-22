# Tapatan (Three Men's Morris)

Tapatan is a classic two-player game played on a **3x3 grid of 9 points**. It is
known across many cultures (Three Men's Morris, Tant Fant, Marelle, etc.). Each
player has **three men**. The rules **as implemented** here are described below.

## The board

The nine points sit on a 3x3 grid, addressed by their coordinate `x,y` on a
0..2 layout (so `0,0` is top-left, `1,1` the centre, `2,2` bottom-right).

The eight **lines** are the three rows, the three columns, and the two main
diagonals. These same eight lines define both how you win and how men may move.

**Adjacency for sliding:** two points are adjacent when they are *consecutive*
along one of those eight lines. As a result:

- the **centre** (`1,1`) is adjacent to all eight outer points;
- each **corner** (`0,0`, `2,0`, `0,2`, `2,2`) is adjacent to its two
  edge-midpoint neighbours and the centre (three points);
- each **edge-midpoint** (`1,0`, `0,1`, `2,1`, `1,2`) is adjacent to its two
  corner neighbours and the centre (three points).

(In particular, corners are **not** adjacent to each other, and the two edge
points on opposite sides of the board are not adjacent.)

## Phase 1 — placing

Players alternate **placing** one man on any empty point. White/red places first.
Placing continues until each player has placed all **three** men (six placements
total).

If completing a placement puts your three men onto one of the eight lines, you
**win immediately** — placement does not have to finish first.

## Phase 2 — moving

Once all six men are on the board, players alternate **moving**: slide one of
your men along a line to an **adjacent empty point** (see adjacency above). There
is **no capture or removal** — unlike Nine Men's Morris, men are never taken off
the board.

## Winning

You **win** the instant your three men occupy one of the eight lines (a row,
column, or diagonal). This can happen during placement or during movement.

## Drawing (no-progress rule)

Because the movement phase can otherwise shuffle men forever, this package
declares a **draw after 60 movement plies** (30 moves per player) with no win.
Placement plies are not counted toward this cap; the clock only runs during the
movement phase. This is a generous, purely practical bound to guarantee the game
terminates — real games are decided (or seen to be drawn) far sooner.

## Strategy note — first-player advantage

With perfect play, standard Tapatan is a **win or draw for the first player and
never a loss for them**; under the most common analysis the second player can
hold a draw, so the game is generally considered a **draw with best play** while
giving the first mover the initiative. A frequent house rule forbids the first
player from opening on the **centre point** (and sometimes any opening that
immediately threatens too strongly) to reduce this advantage.

**This package does NOT implement any opening restriction** — the first player
may place anywhere, including the centre, on move one. The restriction is noted
here only for context; add it as a manifest option if a balanced variant is
desired.

## Notation

During placing, a move is a single point like `1,1` (shown as `@1,1` in the move
log). During moving, it is `from>to`, e.g. `0,0>1,0` (shown as `0,0-1,0`). Points
are named by their `x,y` coordinate on the board diagram.
