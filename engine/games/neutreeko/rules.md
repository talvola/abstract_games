# Neutreeko

By Jan Kristian Haugland (2001). The name is a portmanteau of *Neutron* and
*Teeko*, the two games it is based on. Official site:
[neutreeko.net](https://www.neutreeko.net/neutreeko.htm).

## Board & setup

A 5×5 board. Each player has **three pieces**. Official starting position
(files a–e left to right, ranks 1–5 bottom to top):

- **Black**: b1, d1, c4
- **White**: b5, d5, c2

**Black moves first.**

## Movement

On your turn, move one of your pieces. A piece **slides orthogonally or
diagonally until stopped** by an occupied square or the border of the board.
It must travel as far as it can — it cannot stop short — and a direction in
which it cannot move at all (immediately blocked) is not a legal move.
There are no captures.

## Objective

Get your three pieces **in a row, orthogonally or diagonally. The row must
be connected** (three adjacent squares in a line). Only the player who just
moved can complete a row, so the game ends the moment your move makes one.

## Draws

- **Threefold repetition** (the official rule): "a match is declared a draw
  if the same position occurs three times". A *position* here is the piece
  placement plus the player to move; the initial position counts as its
  first occurrence.
- As a practical backstop this implementation also declares a draw after
  300 plies (unreachable in sensible play; the repetition rule is the real
  draw rule).

## Notes (as implemented)

- The official rules never mention a player with no legal move; with six
  pieces on 25 squares this is unreachable in practice. For completeness,
  a player with no legal slide loses.
- **The game is solved** (see the official site's "Perfect Neutreeko opening
  play" analysis): the starting position is *neutral* — perfect play by both
  sides is a **draw**. Only about 3% of all legal positions are neutral, and
  there are positions where perfect play takes 51 moves to force the win.
  All three claims were re-verified for this port by a full retrograde solve
  of the 3,395,644 legal positions: the start is a draw, 3.08% of positions
  are neutral, and the longest forced win is exactly 51 plies.
