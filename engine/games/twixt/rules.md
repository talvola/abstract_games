# TwixT

TwixT (Alex Randolph, 1962) is a connection game played with **pegs and bridges**.
These are the rules **as implemented** here.

## The board

A square grid of holes (size 12, 18, or 24 a side). **Red** owns the **top and
bottom** rows and tries to connect them; **Black** owns the **left and right**
columns and tries to connect those. The two goal edges are tinted in each
player's colour. The four corner holes belong to no one and are never playable.
A player may not place in the opponent's two border lines (Red avoids the left/
right columns, Black avoids the top/bottom rows). Red moves first.

## Placing pegs and bridges

On your turn you place **one peg** of your colour in an empty hole. The new peg
**automatically links** by a **bridge** to each of your pegs a **knight's-move**
away (the eight (±1,±2)/(±2,±1) holes), **except** any link that would **cross a
bridge already on the board** — a bridge of *either* colour. Two bridges that
merely meet at a shared peg do not count as crossing.

(For simplicity this package always adds every non-crossing knight link
automatically; it does not offer the optional manual bridge removal of the
physical game.)

## Winning

You win the moment a chain of your pegs and bridges **connects your two border
edges**. Unlike Hex, TwixT **can be drawn**: if every non-corner hole is filled
with no side connected, the game is a draw. (A player who has no legal peg to
place simply passes until the board fills.)

## Notation

A move is the hole `c,r` (or `pass`). Pegs are drawn in each player's colour and
bridges as lines between them.
