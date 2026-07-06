# Xodd

A parity placement game by Luis Bolaños Mures (2011), on a square board — the square sibling of Yodd.

## Objective
Finish the game with **fewer groups of your own colour** than your opponent.

## Board & setup
An empty square board (the **size** option; base 9–13 is recommended). Black is player 1, White player 2; Black moves first. A *group* is a set of **orthogonally** connected, like-coloured stones (diagonal contact does NOT connect).

## Play
- On your turn you drop **one or two stones of either colour** on empty cells (on the opening turn, Black drops only one).
- **The odd rule:** at the end of every turn, the **total** number of groups on the board (both colours together) must be **odd**.
- You may **pass** instead of placing, but only if it keeps the total odd (so Black cannot pass first). Two passes in a row end the game.

## Winning & draws
Whoever has **fewer groups of their own colour** wins. Because the total is always odd, the two counts can never be equal — so **draws are impossible**.

## In this implementation
- The board **size** (9 / 11 / 13) is selectable.
- After placing a first stone that keeps the total odd you may **end** your turn or place a second stone; a first stone that leaves the total even is only allowed when a parity-restoring second stone exists.
- Source: <https://mindsports.nl/index.php/the-pit/624-xodd>
