# Bridg-It (David Gale's "Game of Gale")

Bridg-It is a **connection game** and a textbook **Shannon switching game**,
invented by mathematician David Gale around 1958 and marketed by Hasbro. Two
players race to build a chain across the board; **Bridg-It can never end in a
draw** — exactly one player always connects.

## The board: two interleaved dot lattices

The board is two square grids of dots, one per player, offset half a step from
each other. This implementation lays both grids on a single combined integer
grid with coordinates `(x, y)`, with `0 ≤ x, y ≤ 2N` (the default board uses
`N = 5`, the classic Hasbro size).

- **Red (player 0)** owns the dots where **x is odd and y is even** — an
  `N` × `(N+1)` lattice (5 columns × 6 rows by default).
- **Blue (player 1)** owns the dots where **x is even and y is odd** — an
  `(N+1)` × `N` lattice (6 columns × 5 rows by default).

So Red's dots and Blue's dots interleave in a brick pattern; neither colour's
dot ever sits on the other's spot.

## Goal (the two sides)

- **Red connects TOP to BOTTOM** — Red wins by linking the top edge (`y = 0`) to
  the bottom edge (`y = 2N`) with a connected chain of Red edges.
- **Blue connects LEFT to RIGHT** — Blue wins by linking the left edge (`x = 0`)
  to the right edge (`x = 2N`) with a connected chain of Blue edges.

Red plays first.

## The move: draw one edge

On your turn you draw a single **unit edge** between two **orthogonally-adjacent
dots of your own colour**. On the combined grid two same-colour dots are adjacent
when they differ by exactly 2 in one axis (the small gap of one cell between
them). A move is written as the pair of endpoint dot-ids joined by `>`, e.g.
`1,0>1,2` (a Red vertical edge) or `0,1>2,1` (a Blue horizontal edge). You may
not redraw an edge you already own.

## The no-crossing rule

The two colours' potential edges interleave so that **a Red edge and the Blue
edge that would cross it pass through the same point**. You may **not** draw an
edge if the perpendicular opponent edge that crosses it has already been drawn
(and vice-versa). Each interior edge crosses exactly one opponent edge; edges
that run along the outer rim of the board cross nothing and are never blocked.

This mutual exclusion is the heart of the game: every blocking move you make to
cut your opponent's path also builds (or fails to build) your own.

## Winning

After each move we check whether the mover has connected their two sides: we walk
the graph whose nodes are the mover's dots and whose links are the mover's drawn
edges (breadth-first), starting from the dots on one target side and seeking the
opposite side. The first player to connect wins immediately. Because the board's
edges are dual, when no further edges can be placed exactly one player has
connected — **there are no draws.**

## Ruleset choices (flagged)

- **Board size.** The standard physical Bridg-It board is the 5×6 / 6×5
  interleave used here as the default (`N = 5`). Sources vary on the exact size,
  so `size` is a selectable option (`N = 4, 5, 6`); the geometry and rules are
  identical for every `N`. This is **flagged** as the one place sources differ.
- **Coordinates.** Endpoints use a single combined integer lattice `(x, y)` with
  `0..2N` per axis (Red dots at odd-x/even-y, Blue at even-x/odd-y) rather than
  two separate grid numberings. This makes the crossing rule exact: a Red edge
  and its crossing Blue edge share an identical midpoint.
- **No passing.** A player always has a legal move until the game is decided;
  there is no pass and no draw.
