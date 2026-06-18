# Oust

A capture-by-placement game by Mark Steere (2007), played on a hexagonal board.

## Objective
Remove **all** of your opponent's stones from the board.

## Board & setup
A hexagonal board (side length set by the **size** option), empty to start. Red is player 1, Blue player 2; Red moves first.

## Play
On your turn you place one stone of your colour on an empty cell. A *group* is a set of connected same-coloured stones.

- **Non-capturing placement** — the stone connects to no stones, or only to enemy stones. Always legal, and it **ends your turn**.
- **Capturing placement** — the stone connects to one or more of your own groups, forming a larger group. It is legal **only if** that new group touches at least one enemy group and **every** touched enemy group is strictly smaller than your new group. All those enemy groups are removed, and you **must keep placing** until you make a non-capturing placement.
- If you have no legal placement, you pass. The rules guarantee at least one player always has a move, so the game never deadlocks.

## Winning & draws
You **win** by making a capture that removes the opponent's last stone. **Draws cannot occur.**

## In this implementation
- The board **size** is selectable.
- Source: <https://www.marksteeregames.com/>
