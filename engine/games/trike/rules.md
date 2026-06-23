# Trike

*Alek Erickson, 2020. A two-player, draw-free combinatorial abstract game.*

## Board

An equilateral **triangle of hexagons**, `size` hexes on a side. The published game
uses sides of 6–12; this package offers **7, 9, 11, 13** (default **11**). Cells are
addressed `row,col` with `row` from `0` (apex) to `size-1` and `col` from `0` to
`row`. Each cell touches up to six neighbours — the six hex directions. The board is
drawn as hexagonal `polygons`.

## Pieces

- **One shared, neutral pawn.** It belongs to no player; either player moves it on
  their turn.
- **Stones** in each player's colour (White = player 1 / host, Blue = player 2 / guest).

## A turn

Passing is **not allowed**. On your turn:

1. **Slide the pawn** in a straight line along one of the six hex directions, **any
   number of cells**, over **empty cells only**. The pawn may **not jump over** an
   occupied cell and may **not land on** an occupied cell — it stops on an empty cell.
2. **Drop a stone of your own colour** on that landing cell. The pawn then rests on
   top of your new stone.

Because every move places one stone on a previously empty cell, the board strictly
fills up around the pawn and the game always terminates.

## Opening and the pie (swap) rule

- The **host (White)** opens by placing a white stone on **any cell** and the pawn on
  top of it. (In this implementation that is just a normal "destination cell" move
  played from the empty board.)
- The **guest (Blue)** then either plays a normal turn as Blue, **or** uses the
  **`swap`** move (the pie rule): the lone opening stone is recoloured to the guest
  and the turn passes back, so the guest effectively adopts the host's opening. This
  balances the first-move advantage.

After the opening (and any swap), play strictly alternates.

## End and scoring

The game ends the instant the **pawn is trapped** — every one of the six lines out of
its cell is immediately blocked (by an occupied neighbour or the board edge), so there
is no empty cell to move to.

**Score** = the number of stones **you own** among the pawn's **final cell** (the stone
directly under the pawn always counts for its owner) **plus its up-to-six adjacent
cells**. The **higher score wins**. Trike is provably **draw-free** — a draw cannot
occur in legal play; the engine still resolves an (impossible) tie as a draw
defensively.

## Implementation notes / choices flagged

- **Board sizes** offered are 7/9/11/13 (the BGG/Kanare rulebook ships front/back board
  faces; 11 is a common competitive size). Picked one clean default (11) and exposed a
  `size` option.
- **Triangular geometry** reuses the platform's hex-triangle layout (same as the Game
  of Y): `row,col` with six-direction adjacency, rendered as hexagons.
- **Pie rule** is modelled exactly as the Game of Y's `swap`: recolour the single
  opening stone to the swapper and pass the turn. This is faithful to the rulebook's
  "the guest decides whether to be responsible for white or blue."
- **Move notation:** the pawn's destination cell `row,col` (a single cell — one click),
  plus `swap` for the pie rule on the guest's first turn.

Official rules: see the BGG page linked in-app.
