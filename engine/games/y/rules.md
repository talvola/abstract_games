# The Game of Y

Y is a connection game — a close cousin of Hex — invented independently by Claude
Shannon and by Craige Schensted & Charles Titus. These are the rules **as
implemented** here.

## The board

The board is a **triangle of hexagonal cells**, `size` cells along each edge
(choose 8, 11, or 14 with the *Board side* option). The three sides of the
triangle are the **left**, **right**, and **bottom** edges; the three corners
belong to two edges at once.

## Play

- Red moves first. On your turn, **place one stone** of your colour on any empty
  cell.
- **Swap (pie rule):** to offset the first-move advantage, the second player may,
  *as their first move only*, choose **Swap** instead of placing — taking over the
  opening stone (it becomes their colour) and handing the turn back.

## Winning

You win the moment **one connected group of your stones touches all three sides**
of the triangle (the classic "Y" shape). Stones are connected through the six
neighbours each cell has.

Like Hex, **Y can never end in a draw**: once the board is full, exactly one player
always has a winning group — so the game always reaches a decisive result.

## Notation

A move is the cell `row,col` (row 0 is the apex); `swap` is the pie move. Red and
Blue stones are shown in their seat colours.
