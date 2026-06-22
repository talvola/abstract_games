# Alquerque

Alquerque is one of the oldest board games still played — a capture game from the
ancient Near East that is the direct ancestor of draughts/checkers and of
Fanorona. These are the rules **as implemented** here.

## The board

A 5×5 grid of 25 points joined by lines: every point connects orthogonally to its
neighbours, and the "strong" points (where the coordinate sum `c + r` is even)
also connect diagonally. Pieces move and capture only along these drawn lines.

## Setup

Each player has **12 pieces**. White fills the bottom two rows and the two
left-of-centre points of the middle row; Black fills the top two rows and the two
right-of-centre points. The **centre point starts empty**. White moves first.

## Moving and capturing

- **Step:** move one piece one point along a line to an adjacent empty point.
- **Capture:** jump one piece over an adjacent enemy, along a line, to the empty
  point immediately beyond — removing the jumped piece (exactly as in draughts).

**Capturing is compulsory:** if any capture is available you must capture, and a
multi-jump is played to its end as a single move (you keep jumping as long as the
same piece can). When several captures are possible you may choose which to make.

## Winning and draws

You win by **capturing all of the enemy's pieces**, or by **leaving the opponent
with no legal move** on their turn. To guarantee termination the game is drawn
after 40 plies with no capture, by threefold repetition, or at a hard ply cap.

## Notation

A move is a `>`-path of points, shown as `a-b` for a step and `a x b x c…` for a
jump chain. Points are named by their `c,r` coordinate.
