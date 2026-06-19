# Game of the Amazons

A two-player territory game on a **10×10** board (Walter Zamkauskas, 1988). Each
side has **four amazons**. Player 0 is **White** and moves first; player 1 is
**Black**.

## A turn (two steps, one amazon)

1. **Move** one of your amazons like a chess **queen** — any number of squares in
   a straight line (orthogonal or diagonal), without jumping over anything.
2. **Shoot** an arrow from the amazon's **new** square, again like a queen move,
   to any empty square. That square is **blocked** for the rest of the game.

The amazon's *old* square is empty by the time it shoots, so it may fire back
along the path it came from. Nothing is ever captured.

In this implementation a move is the three-cell path **`from > to > arrow`**:
click the amazon, then where it moves, then where the arrow lands.

## Winning

There are no captures and no draws. Each turn fires one arrow, so empty squares
steadily run out. The **first player who cannot complete a move loses** — i.e. the
player who walls in the most space for their amazons (and strangles the opponent's)
wins.

## Notes

- Standard 10×10 opening: White amazons on a4, d1, g1, j4; Black on a7, d10, g10,
  j7. The game is prized for its sharp endgame territory-counting.
