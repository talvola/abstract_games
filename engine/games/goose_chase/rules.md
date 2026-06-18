# Goose Chase

Fox & Geese on a board of pentagonal "paver" (Cairo-tiling) cells, by Bob Henderson.

## Objective
- **Fox** (one piece): reach the goal cell at the far end.
- **Geese** (several pieces): wall the fox in so it cannot move.

## Board & setup
A Cairo pentagonal tiling; eight board sizes are offered via the **board** option. The fox starts at one end, the geese in front of the goal. There are no captures or jumps, so few geese can trap the fox.

## Play
- The **Fox** moves to any empty neighbouring cell (any of its up-to-five pentagon edges).
- The **Geese** move to an empty neighbour but only sideways or away from the goal — never toward it.

## Winning & draws
- The **Fox wins** by reaching the goal cell.
- The **Geese win** by stalemating the fox.
- Per the Zillions rules a side with no move loses; a hard ply cap otherwise declares a draw (the original uses a geese repetition-loss).

## In this implementation
- Eight board **sizes** (2×2 … 6×5), from easy to fiendish.
- Source: <https://www.zillions-of-games.com/cgi-bin/zilligames/submissions.cgi?do=show;id=3331>
