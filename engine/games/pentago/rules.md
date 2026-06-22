# Pentago

Pentago (Tomas Florén, 2005) is five-in-a-row with a twist — literally. The 6×6
board is divided into four 3×3 **quadrants**. These are the rules **as
implemented** here.

## A turn has two parts

On your turn you:

1. **Place** one marble of your colour on any empty cell, then
2. **Rotate** one of the four quadrants **90°**, clockwise or counter-clockwise.

You must do both — the rotation is mandatory (there is no "no twist" option).

In the app this is a single move: click an empty cell, then pick the rotation
from the menu (the four quadrants `BL`/`BR`/`TL`/`TR` — bottom-/top-, left/right —
each `cw` or `ccw`).

## Winning

A win is **five of your marbles in a row** — horizontally, vertically, or
diagonally — and it is judged **after the rotation**. Because the twist moves
marbles, the rotation itself can create (or break) a five.

- If, after your rotation, **only you** have a five, **you win**.
- If the rotation leaves **only your opponent** with a five, **they win**.
- If it makes a five for **both** players at once, the game is a **draw**.
- If the board fills up with no five, it is a **draw**.

## Notation

A move is written `c,r=QUAD-DIR`, e.g. `2,3=TL-cw` (place at column 2 row 3, then
rotate the top-left quadrant clockwise); the move log shows it as `2,3 ↻TL-cw`.
