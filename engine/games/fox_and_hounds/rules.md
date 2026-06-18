# Fox and Hounds

An asymmetric hunt game on the dark squares of an 8×8 board.

## Objective
- **Fox** (one piece): reach the far edge (the hounds' home rank).
- **Hounds** (four pieces): trap the fox so it cannot move.

## Board & setup
The four hounds start on the dark squares of one edge; the lone fox starts on the opposite side. The **Fox moves first**. There are no captures.

## Play
- The **Fox** moves one square diagonally in **any** of the four directions.
- Each **Hound** moves one square diagonally **forward only** (toward the fox's goal edge), never backward.

## Winning & draws
- The **Fox wins** by reaching the far edge.
- The **Hounds win** if the fox has no legal move on its turn.
- Because the hounds can only advance, the game always terminates; a ply cap declares a draw in the rare event play stalls.
