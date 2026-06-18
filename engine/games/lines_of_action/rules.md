# Lines of Action

A positional game by Claude Soucie: gather your pieces into one connected group.

## Objective
Bring **all** your pieces into a single connected group (counting all eight directions as connections).

## Board & setup
An 8×8 board. One player's pieces start on the top and bottom edges, the other's on the left and right edges. Player 1 moves first.

## Play
- A piece moves in a straight line (orthogonally or diagonally) a distance **exactly equal to the number of pieces (of either colour) standing on that line**.
- It may **jump over friendly pieces** but **not over enemy pieces**.
- It may **capture** by landing on an enemy piece (removing it); it may not land on a friendly piece.

## Winning & draws
You **win** the moment all your pieces form one connected group. Note: if your capture reduces the **opponent** to a single connected group, **they** win. If a move connects both players at once, it is a **draw** (modern rule) — or, with the **simultaneous-connection** option set to "win", the mover wins. A ply cap declares a draw if play drags on.

## In this implementation
- The **simultaneous-connection** outcome is selectable (draw or win-for-mover).
