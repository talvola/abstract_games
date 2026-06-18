# Yodd

A parity placement game by Luis Bolaños Mures, on a hexagonal board.

## Objective
Finish the game with **fewer groups of your own colour** than your opponent.

## Board & setup
An empty hexhex board (the **size** option; sides 6–9 are recommended). Red is player 1, Blue player 2; Red moves first. A *group* is a set of connected, like-coloured stones.

## Play
- On your turn you place **one or two stones of either colour** on empty cells (on the opening turn, Red places only one).
- **The odd rule:** at the end of every turn, the **total** number of groups on the board (both colours together) must be **odd**.
- You may **pass** instead of placing, but only if it keeps the total odd (so Red cannot pass first). Two passes in a row end the game.

## Winning & draws
Whoever has **fewer groups of their own colour** wins. Because the total is always odd, the two counts can never be equal — so **draws are impossible**.

## In this implementation
- The board **size** (6–9) is selectable.
- Source: <https://mindsports.nl/index.php/the-pit/623-yodd>
