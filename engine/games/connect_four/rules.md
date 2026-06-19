# Connect Four

A two-player game on a **7-column, 6-row** vertical grid. Player 0 is **Red**,
player 1 is **Yellow**.

## How to play

- On your turn, **drop a disc into a column**. It falls to the lowest empty cell
  of that column.
- In this implementation a move is the **landing cell** — each non-full column
  shows one placement target, so you click where the disc will come to rest.

## Winning

The first player to get **four of their own discs in a row** wins — the line may
be:

- **horizontal** (along a row),
- **vertical** (up a column), or
- **diagonal** (either direction).

If all 42 cells fill with no four-in-a-row, the game is a **draw**.

## Notes

- Standard board and goal (7×6, connect 4). The first player (Red) has a known
  winning strategy with perfect play, but it is far from obvious over the board.
