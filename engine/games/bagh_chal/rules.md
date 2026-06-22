# Bagh-Chal (Tigers and Goats)

Bagh-Chal is a traditional hunt game from Nepal. It is **asymmetric**: one player
controls four **Tigers**, the other twenty **Goats**. These are the rules **as
implemented** here.

## The board

The board is a 5×5 grid of 25 points joined by lines: every point connects
orthogonally to its neighbours, and the "strong" points — where the coordinate
sum `c + r` is even — also connect diagonally. Pieces move and capture only along
these drawn lines.

## Setup and turn order

- The four **Tigers** start on the four **corner** points.
- The twenty **Goats** start **off the board, in hand**.
- **Goats move first**, then the sides alternate.

## Goats

- **Placing phase:** while any Goats remain in hand, a Goat turn must **place** one
  Goat on any empty point. (Goats may not move during this phase.)
- **Moving phase:** once all twenty Goats have been placed, a Goat turn **moves**
  one Goat one step along a line to an adjacent empty point. Goats never jump and
  never capture.

## Tigers

On a Tiger turn you either:

- **Step** a Tiger one point along a line to an adjacent empty point, or
- **Jump** a Tiger over an adjacent Goat, along a straight line, to the empty
  point immediately beyond — **capturing** that Goat. Only a single goat is jumped
  per move (no multi-jumps), and the jump must follow a real board line
  (diagonal jumps only from strong points).

## Winning

- **Tigers win** as soon as they have captured **five Goats**.
- **Goats win** when **every Tiger is trapped** — no Tiger has any legal step or
  jump.
- More generally, a side that has **no legal move on its turn loses** (this is how
  the Tigers-are-trapped win is detected; a fully blocked Goat side likewise
  loses, though that is very rare).

## Draws / termination

The same position recurring three times, or 400 plies passing, ends the game in a
**draw** (a no-progress safeguard that also guarantees termination).

## Notation

A placement is a single point like `2,2` (`goat@2,2` in the log). A step or jump
is `from>to`, e.g. `0,0-1,1` for a step or `0,0x2,2` for a capturing jump. Points
are named by their `c,r` coordinate.
