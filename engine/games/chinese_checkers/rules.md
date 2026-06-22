# Chinese Checkers (Sternhalma)

Despite the name, Chinese Checkers is a German game (Sternhalma) and a descendant
of Halma. It is a **six-player** race across a six-pointed star. These are the
rules **as implemented** here.

## The board

The board is a star of **121 points**: a central hexagon plus six triangular
points of ten. Each of the six players owns one point, filled with their **ten
marbles**, and aims for the point **directly opposite** (where an opponent
started). Players move in turn, 1 → 2 → 3 → 4 → 5 → 6.

## Moving

On your turn you move **one marble**, in one of two ways:

- **Step** it to an adjacent empty point (six directions), or
- **Jump** it over a single adjacent marble — anyone's — to the empty point
  **directly beyond**, and you may keep jumping in a **chain** for as long as the
  marble can hop. A move is either one step *or* a sequence of jumps.

**Nothing is ever captured** — jumped marbles stay exactly where they are.

## Winning

The first player to get **all ten of their marbles into the opposite point** wins.
(A hard move cap forces a draw in the rare event that no one ever finishes — for
example under random play.)

## Notes

This package implements the classic **six-player** game. Two- and three-player
Chinese Checkers use the same star with fewer points occupied; they would be
separate games here. The traditional anti-spoiling conventions (a marble may not
permanently block an opponent's home) are not enforced beyond the move cap.

## Notation

A move is `from>to`, e.g. `0,0>4,-4` for a two-hop chain; points are named by
their cube coordinate `a,b` (the third coordinate is `-a-b`). Each player's
marbles are shown in their seat colour.
