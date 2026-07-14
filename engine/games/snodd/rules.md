# Snodd

A parity placement game by **Dr Eric Silverman** (2021): Luis Bolaños Mures' **Xodd/Yodd** ported to the **snub square tiling**.

## Objective
Finish the game with **fewer groups of your own colour** than your opponent.

## Board & setup
An empty board whose cells are the **vertices of the snub square tiling** (vertex configuration 3.3.4.3.4). Every interior point has **degree 5** — halfway between Xodd's square grid (degree 4) and Yodd's hexagonal grid (degree 6). Red is player 1, Blue player 2; Red moves first. A *group* is a set of connected, like-coloured stones (connected through the board's adjacency).

Each playable point is drawn as one cell of the **Cairo pentagonal tiling** — the dual of the snub square tiling, so two pentagons share an edge exactly when their two points are adjacent.

## Play
- On your turn you place **one or two stones of either colour** on empty cells (on the opening turn, Red places only one).
- **The odd rule:** at the end of every turn, the **total** number of groups on the board (both colours together) must be **odd**.
- You may **pass** instead of placing, but only if it keeps the total odd (so Red cannot pass first — an empty board has zero groups). Two passes in a row end the game.

## Winning & draws
Whoever has **fewer groups of their own colour** wins. Because the total is always odd, the two counts can never be equal — so **draws are impossible**.

## In this implementation
- The board is a fixed patch of **84 snub-square points** (56 of them fully interior, degree 5).
- A turn is entered as up to two placements: `<cell>=red` / `<cell>=blue`; after one stone you may `end` the turn (if the total is already odd) or place a second stone to fix the parity. `pass` passes the whole turn.
- Source: <https://drericsilverman.com/2021/10/23/reviewing-almost-all-the-games-on-mindsports/> (Snodd); rules follow Yodd/Xodd, <https://mindsports.nl/index.php/the-pit/623-yodd>.
