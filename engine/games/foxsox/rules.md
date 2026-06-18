# FoxSox

Fox and Geese on a rhombus of **triangular** cells, by Bob Henderson.

## Objective
- **Fox** (one piece): reach the far corner cell.
- **Geese** (several pieces): block the fox so it cannot move.

## Board & setup
A rhombus of triangular cells, *n* per side (the **size** option, 4–9). The fox starts in one corner, the geese spread across the board. Geese move first. There are no captures or jumps.

## Play
- The **Fox** moves to any empty neighbouring cell (any of its three triangle edges).
- Each **Goose** moves to an empty neighbour, but only in a "rightward" direction (toward the fox's far corner) — never back the way it came.

## Winning & draws
- The **Fox wins** by reaching the far corner.
- The **Geese win** if the fox is stalemated (no legal move).
- If the **geese** run out of moves first, it is a **draw** (the fox can't be caught but hasn't escaped). Geese only ever advance, so the game terminates.

## In this implementation
- Six board **sizes** (4–9), from easy to fiendish.
- Source: <https://www.zillions-of-games.com/cgi-bin/zilligames/submissions.cgi?do=show;id=3332>
