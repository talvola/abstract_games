# McCooey's Hexagonal Chess

Developed in **1978–79 by Dave McCooey and Richard Honeycutt**, independently of
Gliński, with the explicit goal of being "the closest hexagonal equivalent to the
real game of chess". Same regular hexagon of **91 hexes** (side 6, three colours)
as Gliński's game, and the same piece moves — but a different starting array with
**seven pawns** per side (all exactly seven hexes from promotion, none of the array's
cells behind the pawns unoccupied), orthodox-style **diagonal pawn captures**, no
double step for the centre pawn, and **stalemate is an ordinary draw**.

## Board & setup

Files `a`–`k` (**including `j`**, unlike Gliński's notation); ranks bend 60° at the
central f-file. White's corner is f1, the centre f6, Black's corner f11.
Starting position (White / Black mirrored):

- **King** g1 / g10 - **Queen** e1 / e10
- **Bishops** f1, f2, f3 / f9, f10, f11 (one on each of the three hex colours)
- **Knights** e2, g2 / e9, g9 - **Rooks** d1, h1 / d9, h9
- **Pawns** c1, d2, e3, f4, g3, h2, i1 / c8, d8, e8, f8, g8, h8, i8

*(The generic renderer draws the hexagons point-up, so the whole board appears rotated
~30° from the traditional vertical diagram. The three background shades are the three
hex colours — the centre hex is the lightest, per McCooey's own convention — and each
bishop is bound to one.)*

## Moves

- **Rook**: any distance in the 6 *orthogonal* directions (through cell edges).
- **Bishop**: any distance in the 6 *diagonal* directions (through cell vertices);
  colourbound. A diagonal move passes between — never through — the two cells
  flanking the line, so a one-step diagonal move can never be blocked.
- **Queen**: rook + bishop (12 directions). **King**: one step in any of the 12.
  **There is no castling.**
- **Knight**: two hexes orthogonally, then one more at 60° (12 possible targets),
  jumping over anything in between. It never lands on its own colour.
- **Pawn**: one vacant hex straight forward. It **captures one hex along the two
  forward *diagonal* (bishop-wise) directions** — exactly like an orthodox pawn, and
  McCooey's deliberate difference from Gliński's orthogonal-capturing pawns. Every
  pawn **except the centre pawn (f4 / f8)** may advance two vacant hexes straight
  forward on its first move; the centre pawn is denied the double step so that White
  cannot seize the centre hex on move one. **En passant**: a pawn double-stepping
  across an enemy pawn's attack hex may be captured on that crossed hex on the
  immediately following move. A pawn **promotes** to Q, R, B or N (free choice,
  regardless of pieces on the board) on reaching the end of any file — the 11
  far-edge hexes (a6, b7, c8, d9, e10, f11, g10, h9, i8, j7, k6 for White).
  Promotion is forced.

## Ending the game

- **Checkmate** wins (+1 / −1).
- **Stalemate is a DRAW** (½–½). McCooey chose the orthodox outcome, explicitly
  rejecting Gliński's ¾–¼ stalemate rule.
- **Draws**: 50-move rule (50 full moves without a pawn move or capture), threefold
  repetition (same position, side to move and en-passant rights), plus a defensive
  1000-ply cap as a termination backstop.

## Interpretations documented (rules as implemented)

- **"First move" double step = standing on its own starting hex.** In this array no
  pawn can ever capture onto a friendly pawn's starting hex (they are mutually
  unreachable by forward motion), so the two readings coincide — there is no
  Gliński-style "regained double step".
- **No "insufficient material" auto-draw.** Bare-king and other dead endings finish
  via the 50-move rule; K+2N genuinely mates on this board (McCooey's own endgame
  databases), so material rules would be delicate — and unnecessary.
- The repetition key always includes the en-passant target when one exists (a
  conservative reading; it can only delay, never fabricate, a repetition draw).

## Correctness anchors

No open-source McCooey engine was found (the hexchess.club engine used to verify our
Gliński package is Gliński-only), so this package is anchored three ways:

1. **The starting array is verified against three independent sources**: McCooey's
   own chessvariants.com page (Interactive Diagram), his published sample games, and
   the Markmann Zillions ZRF for hexagonal chess — all agree.
2. **Perft, hand-derived at depth 1**: from the start exactly **31** moves —
   13 pawn (7 singles + 6 doubles; the centre pawn has no double), 10 knight
   (e2→b1,c3,d4,f5,g4; g2→e4,f5,h4,i3,j1), 8 bishop (all by f3: g4,h5,i6,j7 and
   e4,d5,c6,b7; f1/f2 are boxed in), and **0** rook/queen/king moves (the array has
   no empty cells behind the pawn chain). Frozen self-perft: **31 / 947 / 33,307 /
   1,157,856** (depths 1–4).
3. **Full replay of seven of McCooey's published sample games** (~340 plies played
   by McCooey, Billy Haynie and Tim O'Lena, from the chessvariants.com sample-games
   page) through a strict SAN reader: every move must resolve to exactly one legal
   move, every `+` must be a real check, every unannotated move must give no check,
   and the four decisive games must end in genuine checkmate for the annotated
   winner. One informally-ambiguous rook move (game 7, 15…Re8) is disambiguated in
   the test with a note; the continuation proves which rook moved.

`selftest.py` re-asserts all of the above plus: both diagonal pawn-capture
directions (and that Gliński's orthogonal captures are illegal), the Wikipedia
en-passant example (e8–e6 answered by d5×e7 e.p.), forced promotion, McCooey's
"a knight landing on the unprotected centre pawn's hex at the start is checkmate
and a triple fork" remark, stalemate scoring 0/0, repetition, the 50-move rule and
bishop colour invariance.

## Sources

- [chessvariants.com — Hexagonal Chess (McCooey's variant)](https://www.chessvariants.com/hexagonal.dir/hexchess2.html) — Dave McCooey's own rules page.
- [chessvariants.com — Sample games](https://www.chessvariants.com/hexagonal.dir/sample1.html) — the replayed games.
- [Wikipedia — Hexagonal chess (McCooey's variant)](https://en.wikipedia.org/wiki/Hexagonal_chess)
- Jens Markmann's Zillions ZRF *Hexagonal Chess* v1.01 (setup & zone cross-check).
