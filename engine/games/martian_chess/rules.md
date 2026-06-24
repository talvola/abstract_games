# Martian Chess

**Martian Chess** is an abstract game by **Andrew Looney** (Looney Labs), played
with Icehouse / Looney Pyramids. Its signature idea: **color means nothing — you
control whatever pieces are currently sitting in *your* half of the board.**

This page documents the rules **as implemented** in this package.

## Board

A **4-wide × 8-tall** grid (cells `c,r`, with `c` 0..3 and `r` 0..7), split by a
**canal** between rows 3 and 4 into two **4×4 zones**:

- **rows 0–3** — **Red**'s zone (player 0, bottom)
- **rows 4–7** — **Blue**'s zone (player 1, top)

(This is the standard 2-player half-board; the full 8×8 four-player game is not
implemented here.)

## Pieces

Each player starts with **nine** pieces — the three Looney-pyramid sizes,
distinguished here by their **label** and **movement** (color is irrelevant):

| Label | Piece | Value | Movement |
|---|---|---|---|
| **P** | Pawn (size 1) | 1 | one square **diagonally** (any of the 4 diagonals) |
| **D** | Drone (size 2) | 2 | **1 or 2** squares **orthogonally** in a straight line; cannot jump |
| **Q** | Queen (size 3) | 3 | **any distance** orthogonally **or** diagonally; cannot jump |

## Starting setup

Each player's nine pieces form a **triangular block in the corner** of their
zone: three Queens in the very corner (an L), a diagonal of three Drones sharing
sides with the Queens, then three Pawns. The two blocks are **180°-rotationally
symmetric** (not mirror images).

```
Q Q D P      row 3 .. row 0 are Red's zone
Q D P .      (corner at 0,0)
D P . .
. . . .   <- canal
. . . .
. . P D
. P D Q      Blue's zone, corner at (3,7)
P D Q Q
```

Exact cells — **Red** (player 0): Queens `0,0 1,0 0,1`; Drones `2,0 1,1 0,2`;
Pawns `3,0 2,1 1,2`. **Blue** (player 1) is the 180° rotation: Queens
`3,7 2,7 3,6`; Drones `1,7 2,6 3,5`; Pawns `0,7 1,6 2,5`.

## Ownership by zone (the signature rule)

On your turn you move **any one piece that is currently in your own zone** — not
a piece of "your color" (there are no colors). A piece you move may slide or step
**across the canal** into the opponent's zone; once it lands there it is **theirs**
to move on a later turn. Likewise, a piece an opponent pushes into your zone
becomes yours.

## Capture & scoring

Moving onto a square occupied by **any** piece **captures** it: the piece is
removed from the board and **its point value is added to the mover's score**
(Pawn 1, Drone 2, Queen 3). Because you only move pieces in your own zone, a
capture is always your piece landing on a piece across the canal. Your running
scores are shown in the caption (e.g. `score 0-0`).

## Field promotion (merging)

This is a **base-game rule** and is implemented:

- If you control **no Queens**, you may move a **Drone onto one of your Pawns**
  (or a Pawn onto a Drone) **in your own zone**, removing both and replacing them
  with a **Queen**.
- If you control **no Drones**, you may move one of your **Pawns onto another
  Pawn** in your own zone, replacing both with a **Drone**.

A merge happens entirely within your zone and **scores nothing**. (Moving onto
your own piece is otherwise illegal.)

## No-take-back

In the 2-player game you may **not "reject" the opponent's immediately preceding
move**: if the opponent just moved a piece from one square to another, you may
not move that same piece **straight back to the square it just left** on your
very next turn. (Any other move of that piece, or returning to it later, is
fine.)

## Game end & winner

The game ends the **instant one zone is completely empty**. The player with the
**higher score wins**. On a **tie**, the player who made the move that ended the
game wins (the official tie-break). Result: **+1 / −1** for win/loss, **0 / 0**
for a draw.

A player who somehow has **no legal move** likewise ends the game and it is
scored as above (a well-formedness convention; this is essentially unreachable in
normal play).

### Termination safety (non-original)

To guarantee the engine always terminates, a **hard draw is declared at 400 plies**.
This is **not part of the published rules** — a real game empties a zone far
sooner (random self-play here averages ~185 plies, max observed 359) — but it is a
required safety net for the platform's conformance checks.

## Notation

Moves are cell paths `from>to` (two `c,r` cells), so the board is fully
click-to-move. The move log uses readable algebraic notation, e.g. `Q a1-c3`
(move), `Q a4xa6` (capture, `x`), `D a1+a2=Q` (merge).

## Sources

- Official rules: [Looney Labs — Martian Chess](https://www.looneylabs.com/rules/martian-chess)
- [Wikipedia — Martian Chess](https://en.wikipedia.org/wiki/Martian_Chess)
- [The Rules of Martian Chess (wunderland.com)](http://wunderland.com/icehouse/MartianChess.html)
