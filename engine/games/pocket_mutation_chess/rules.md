# Pocket Mutation Chess

**Michael Nelson, 2003** — a Recognized Chess Variant. Standard chess with a
one-slot *pocket*: instead of moving, you may pull one of your own pieces off the
board into the pocket (where it may **mutate** into another piece of equivalent
value), and later **drop** it back onto an empty square.

Source: [chessvariants.com — Pocket Mutation Chess](https://www.chessvariants.com/large.dir/pocketmutation.html).
The rules below are the rules *as implemented*.

## Setup

Identical to FIDE chess. Each pocket starts empty. White = player 0.

## Value classes

Every piece belongs to one of eight value classes. Pieces with no movement note
below move as in FIDE chess.

1. **Pawn**
2. **Knight**, **Bishop**
3. **Rook**, **Nightrider**, **SuperBishop**
4. **Cardinal**, **SuperRook**
5. **Queen**, **Chancellor**, **CardinalRider**, **SuperCardinal**
6. **ChancellorRider**, **SuperChancellor**, **SuperCardinalRider**
7. **Amazon**, **SuperChancellorRider**
8. **AmazonRider**

Fairy-piece moves (Wazir = one step orthogonally, Ferz = one step diagonally,
Nightrider = repeated Knight steps in one direction, each intermediate square
empty):

| Piece | Code | Moves as |
|---|---|---|
| Nightrider | H | repeated Knight steps in a line |
| SuperBishop | S | Bishop + Wazir |
| Cardinal | C | Bishop + Knight |
| SuperRook | T | Rook + Ferz |
| Chancellor | M | Rook + Knight |
| CardinalRider | D | Bishop + Nightrider |
| SuperCardinal | E | Bishop + Knight + Wazir |
| ChancellorRider | G | Rook + Nightrider |
| SuperChancellor | J | Rook + Knight + Ferz |
| SuperCardinalRider | L | Bishop + Nightrider + Wazir |
| Amazon | A | Queen + Knight |
| SuperChancellorRider | U | Rook + Nightrider + Ferz |
| AmazonRider | Z | Queen + Nightrider |

(The single-letter codes are this implementation's labels. Cardinal, Chancellor
and Amazon show real piece images; the rider/super compounds show their letter.)

## Rules

All FIDE rules apply **except** as follows.

1. **Pocket.** Each player has a pocket holding at most one piece; it starts empty.
2. **Pocketing a piece** (a whole move; only when your pocket is empty): remove any
   of your own pieces **except the King** from the board into your pocket. **White
   may not pocket on the very first move of the game.** You may not pocket a piece
   whose removal would leave your own King in check (so a pinned piece cannot be
   pocketed, and you cannot pocket while in check).
   - **From your 1st–7th rank:** the piece keeps its value class but may
     **optionally mutate** into any (other) piece of that class. The choice is made
     immediately, at the moment of pocketing.
   - **From your 8th rank:** the piece **promotes to the next higher value class**;
     the exact piece is chosen immediately. The AmazonRider (top class) has no
     higher class and is unchanged. This is the **only** promotion in the game — a
     pawn that reaches the 8th rank simply stays a pawn until it is pocketed
     (whereupon it promotes to a class-2 piece).
3. **Dropping** (a whole move; only when your pocket holds a piece): place the
   pocketed piece on **any empty square except your own 8th rank**. A drop may give
   check or checkmate. Your King may not be left in check.
4. **No castling.**
5. **Pawns.** A pawn on the 1st rank cannot double-step; a pawn on the 2nd rank may
   double-step (whether it started there, was dropped there, or advanced from the
   1st rank). En passant is normal.
6. **Draws.** The game is drawn if **50 consecutive moves** pass with no capture and
   no promotion (a pocket-promotion from the 8th rank counts; ordinary pawn pushes
   do **not** reset the counter). FIDE **threefold repetition** also draws — and the
   contents of both pockets are part of the repetition position. A move/ply cap and
   stalemate round out the draw conditions.

Captured pieces are removed from play — they are **not** banked (this is not
Crazyhouse). The pocket is filled only by pocketing one of your own pieces.

## Move notation

- Ordinary move: `fc,fr>tc,tr` (e.g. `4,1>4,3`).
- **Pocket a piece:** click the piece's own square twice — `c,r>c,r=X`, where `X`
  is the chosen (possibly mutated / promoted) piece code. A picker offers the legal
  choices.
- **Drop from pocket:** `X@c,r`, placed via the reserve tray shown above/below the
  board.

## Correctness anchors

`selftest.py` freezes: **perft(1) = 20** (White's ordinary 20 opening moves — no
pocketing on move 1, no castling/promotion) and **perft(2) = 920** (chess's 400
ordinary two-ply lines, plus 26 first-move pocketing options for Black after each
of White's 20 moves: 8 pawns + 2 knights×2 + 2 bishops×2 + 2 rooks×3 + queen×4 =
26, so 400 + 20×26 = 920); the full value-class and movement table re-derived from
the source; and rule positions for the pin/in-check pocketing bans, the 8th-rank
drop ban, a mutation from every class, a drop-delivered checkmate, and the
pocket-sensitive repetition key.
