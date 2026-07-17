# Dablot Prejjesne

A Sámi battle game from Frostviken in Swedish Lapland, recorded by Nils Keyland
(1921). A Sámi army — king, prince and 28 warriors — fights a settler army —
landlord, his son and 28 tenant farmers. It is an Alquerque-family game with one
defining twist: **rank** decides who may capture whom.

## Board

Pieces stand on the **points** of a 6×7 grid with every line drawn: horizontal
and vertical lines join the 42 grid vertices, and both diagonals are drawn
through each of the 30 small squares, adding a point where they cross —
**72 points** joined by **191 line segments**. Movement is only along drawn
lines: vertices connect orthogonally to neighbouring vertices and diagonally to
the centres of adjacent squares; each centre connects to its four corners.

```
*---*---*---*---*---*      * grid vertex
| x | x | x | x | x |      x square centre (diagonals cross here;
*---*---*---*---*---*        the diagonals themselves are drawn
| x | x | x | x | x |        lines: corner - centre - corner)
*---*---*---*---*---*
        ... (7 vertex rows in all)
```

## Setup

Counting the 13 ranks of points from your own edge (vertex and centre rows
alternate): your **28 commoners** fill ranks 1–5 (6+5+6+5+6 points), your
**prince** stands on the diagonal-crossing point at your far right of rank 6,
and your **king** on your right-hand end of rank 7 — the middle line of the
board, so the two kings start facing each other from its opposite ends. The two
armies are 180° rotations of each other. The Sámi side moves first.

## Moving and capturing

- All pieces move alike: **one point along any drawn line** to an empty point,
  in any direction.
- **Capture** by a draughts-style short jump: over an adjacent enemy, along the
  same straight drawn line, landing on the empty point directly beyond. Chains
  are allowed and may change direction; jumped pieces are removed as you go.
- **The rank rule:** a piece may only jump an enemy of **equal or lower rank**
  (king > prince > commoner). The king captures anything; the prince captures
  princes and commoners; a commoner captures only commoners. No piece is ever
  promoted.
- **Captures are optional** (Keyland's rules, the default): you may decline a
  capture, and you may stop a chain at any point. The `Captures` option
  switches to the compulsory rule used in some modern accounts: if a capture
  exists you must capture, and a chain must continue while a further jump is
  available (you need not choose the longest chain).

## Ending the game

- **Win** by capturing all enemy pieces, or by leaving your opponent with no
  legal move (a trapped player loses).
- **Two lone kings** — one piece each, both kings — is an immediate **draw**
  (neither can ever safely approach the other).
- **Single combat:** if both players are reduced to one piece each of *equal*
  rank (both commoners or both princes), the pieces must fight: each must
  capture if it can, and otherwise must step so as to close the distance to the
  enemy. Whoever lands the jump wins.
- Draw backstops (as implemented): 60 consecutive plies without a capture,
  threefold repetition of the position with the same player to move, or 1000
  plies in total end the game as an honest draw.

## Sources & interpretations

Implemented from Keyland, *Dablot prejjesne och dablot duoljesne* (1921,
Frostviken) as transmitted by the Ludii project's ruleset, cross-checked
against Wikipedia's "Dablot Prejjesne" article; both agree on the 72-point
lattice (6×7 vertices + 30 diagonal crossings), the 28+prince+king armies, the
right-hand prince/king placement, all-pieces-alike movement, the
equal-or-lower-rank capture rule and the absence of promotion. Documented
interpretations:

- **Capture compulsion** is the one genuine source conflict: Keyland/Ludii say
  captures are *not* compulsory; Wikipedia says modern play makes them
  compulsory. Both are offered via the `Captures` option; the primary source's
  optional rule is the default. No huffing in either mode.
- **Trapped = loss** generalises the sources' block rules: Wikipedia calls
  stalemating the opponent "a common secondary winning condition"; Ludii
  awards the mover a win when the opponent's last piece is a blocked
  higher-ranking piece. This implementation makes any player with no legal
  move lose, which subsumes both.
- **Single combat** is forced (as in Ludii's implementation) rather than
  declared; approach distance is measured along the drawn lines. In rare
  blocked corner cases where neither a capture nor an approach step exists,
  any normal move is allowed and the draw backstops decide.
- Which army moves first is not specified by the sources; here the Sámi side
  (bottom) moves first. Left/right chirality of the setup is mirror-symmetric
  and does not affect play.
