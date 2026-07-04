# Decimaka

H. G. Muller's 10x10 chess variant (2018), built to emulate the promotion
dynamics of Maka Dai Dai Shogi: **pieces promote by making a capture** —
anywhere on the board. There is no promotion zone.

Source: [chessvariants.com/rules/decimaka](https://www.chessvariants.com/rules/decimaka)
(this implements the original 2018 page, not Muller's later revision).

## Board and setup

10x10 board. White's army (Black mirrors it by 180-degree rotation, so the
Black King sits on e10 next to the Fiancee on f10):

- **Rank 1:** Rook a1, Y d1, Fiancee e1, King f1, Y g1, Rook j1
- **Rank 2:** Cross a2, Tee b2, Knight c2, Bishop d2, Lion e2, Star f2, Bishop g2, Knight h2, Tee i2, Cross j2
- **Rank 3:** ten Pawns

## The pieces

- **King (K)** — orthodox King. Castles by moving **three** squares toward
  either Rook (rook lands on the square the King crossed last); usual
  conditions: neither piece has moved, the squares between are empty, the King
  is not in check and does not pass through or land on an attacked square.
- **Rook (R)**, **Bishop (B)**, **Knight (N)** — orthodox.
- **Pawn (P)** — orthodox: single step forward, double step from its home
  (3rd/8th) rank, diagonal captures, en passant.
- **Fiancee (F)** — moves like a King but is not royal.
- **Tee (T)** — steps one square straight forward or backward, or diagonally
  forward.
- **Cross (C)** — steps one or jumps two squares in the four orthogonal
  directions.
- **Y (Y)** — leaps one, two or three squares diagonally forward or straight
  backward.
- **Star (S)** — jumps one, two or three squares in any of the eight
  directions.
- **Lion (L)** — moves as King or Knight, or jumps two squares orthogonally or
  diagonally.

### Promoted pieces (only ever created by capture-promotion)

- **Queen (Q)** — promoted Fiancee; orthodox Queen.
- **Trident (+T)** — promoted Tee; slides along the file (both ways) or
  diagonally forward.
- **Nightrider (+N)** — promoted Knight; makes repeated Knight moves in the
  same direction until blocked.
- **Omni (O)** — promoted Pawn, Cross, Y, Star or Lion; **moves** (without
  capturing) one step orthogonally and **captures** one step diagonally.

## Promotion (the signature rule)

Promotion happens only on a move that captures, and takes effect immediately
(the piece lands as its promoted type):

1. **Capturing a Queen** promotes the capturer to **Queen**, mandatorily —
   this applies to every piece except the King, including already-promoted
   pieces and pieces that normally cannot promote.
2. Otherwise, **capturing a promoted piece** (Q, O, +T, +N) makes the
   capturer's promotion **mandatory** (Rooks, Bishops and the promoted types
   have no promotion and simply stay what they are).
3. Any **other capture** makes promotion **optional** — you may decline (for
   Cross/Y/Star/Lion, becoming an Omni is usually a demotion!).
4. Kings never promote. Pawns do **not** promote on the last rank — a pawn
   that walks there becomes immobile "dead wood" (it can still be worth it if
   the capture that got it there was, or it may promote to Omni *on* that
   capture).

## Winning and draws

- **Checkmate wins.** Stalemate is a draw.
- Draws: 50 moves without a capture or pawn move, threefold repetition,
  insufficient material, and a hard 800-ply cap (platform termination
  guarantee).

## Notation / interpretations

- Promotion choices appear as a `=X` suffix on the capture move (e.g. `=O`,
  `=+T`, `=Q`); when promotion is mandatory only the promoted move is offered.
- The Queen-capture rule is read as fully forced: a piece with a promotion of
  its own (e.g. a Tee) that captures a Queen becomes a Queen, not its normal
  promotion.
- En passant is a capture of an (unpromoted) Pawn, so the capturing pawn may
  optionally promote to Omni on it.
- Castling geometry (from Muller's Interactive Diagram, `KisO3`): White
  f1→i1 with Rook j1→h1, or f1→c1 with Rook a1→d1; Black e10→h10 with Rook
  j10→g10, or e10→b10 with Rook a10→c10.
