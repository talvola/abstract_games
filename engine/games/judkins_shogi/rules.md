# Judkins Shogi (6×6)

Judkins Shogi is Shogi compressed onto a **6×6** board, a little larger than
Mini Shogi and — unlike Mini Shogi — it includes a **Knight**. All the Shogi
rules apply, including **drops**, so see the Shogi rules for the full detail;
this page lists only what differs.

## Pieces

Each side has **seven** pieces, one of each:

- King (K), Rook (R), Bishop (B), Knight (N), Gold general (G), Silver general
  (S), and one Pawn (P).

The pieces move exactly as in Shogi:

- **Rook** slides orthogonally, **Bishop** slides diagonally.
- **Knight** jumps two squares forward and one to the side — *forward only*, and
  it may leap over intervening pieces (the shogi knight, not the chess knight).
- **Gold**, **Silver**, **King** and **Pawn** move as in Shogi (the Pawn is a
  single forward step).

## Setup

```
R B N S G k     ← White (Gote), top
. . . . . p
. . . . . .
. . . . . .
P . . . . .
k G S N B R     ← Black (Sente), bottom
```

Each side's King starts in the **left corner** of its back rank, which runs
**King–Gold–Silver–Knight–Bishop–Rook** from that player's view (the corner
holds the King and the far corner the Rook). The two armies are rotated 180°
from each other, with one Pawn directly in front of each King.
**Black (Sente) moves first.**

## Promotion

The **promotion zone is the far two ranks** (ranks 5 and 6 from your side — "the
original line of the opponent's Pawn and beyond"). A piece that moves into, out
of, or within the zone may promote; a Pawn reaching the last rank, or a Knight
reaching the last two ranks, *must* promote. Promotions: R→Dragon (+R, rook +
king diagonal steps), B→Horse (+B, bishop + king orthogonal steps), and
N/S/P→+piece (each moves like a Gold). King and Gold never promote.

## Drops, captures, winning, draws

Identical to Shogi: a captured piece switches colour and goes to your hand, to be
dropped (unpromoted) on a later turn, subject to the two-pawns (*nifu*),
last-rank and drop-mate (*uchifuzume*) rules. **Checkmate wins.** Repetition (the
same position four times) is a **draw**, and a ply cap guarantees termination.

## Notation

As in Shogi: board moves are `from>to` (append `=+` to promote), drops are
`L@c,r`.
