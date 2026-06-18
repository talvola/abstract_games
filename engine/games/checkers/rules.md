# Checkers

Standard 8×8 checkers (American / English draughts).

## Objective
Capture all of the opponent's pieces, or leave them with no legal move.

## Board & setup
Played on the dark squares of an 8×8 board. Each side starts with 12 men on the three ranks nearest them. Player 1 moves first.

## Play
- **Men** move one square diagonally **forward** to an empty square.
- **Capturing** ("jumping") leaps diagonally over an adjacent enemy piece to the empty square beyond; the jumped piece is removed. Multiple jumps chain in a single turn.
- **Captures are mandatory:** if any jump is available you must jump, and you must continue a multi-jump until no further jump is possible.
- A man reaching the far rank is **promoted to a king**, which moves and jumps diagonally both forward and backward.

## Winning & draws
You **win** when the opponent has no pieces left, or cannot move on their turn.
The game is drawn by a **50-ply no-progress rule** (no capture and no man move — only kings shuffling) and by a hard 400-ply cap.
