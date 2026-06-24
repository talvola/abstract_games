# Almost Chess

**Almost Chess** (Ralph Betza, 1977) is standard chess with a single change: each
player's **queen is replaced by a Chancellor**. It plays "almost" like chess, but the
Chancellor's rook-plus-knight power changes the dynamics — the two pieces are of
roughly equal value, yet behave very differently.

## Equipment & setup

A standard 8×8 board with the usual chess army, except the queen on **d1** (White) and
**d8** (Black) is a **Chancellor** instead. White (player 0) moves first.

```
Black:  r n b M k b n r      (M = Chancellor)
        p p p p p p p p
        . . . . . . . .
        . . . . . . . .
        . . . . . . . .
        . . . . . . . .
        p p p p p p p p
White:  R N B M K B N R
```

## The Chancellor (M)

The **Chancellor** (also called a Marshall or Empress) moves as a **Rook OR a Knight**:

- like a **rook**, any number of empty squares horizontally or vertically; and
- like a **knight**, an L-shaped leap (it jumps, ignoring intervening pieces).

It does **not** move diagonally — it has no bishop component (that is the only thing
that makes it "almost" a queen). It captures the same way it moves.

## Everything else is standard chess

- **Pawns:** one square forward, two from their home rank, capture one square
  diagonally, including **en passant**.
- **Castling:** standard king- and queen-side, with all the usual conditions (king and
  rook unmoved, no pieces between, king not in/through/into check). Move the king two
  squares; the rook jumps over automatically.
- **King, Rook, Bishop, Knight:** move exactly as in standard chess.
- **Check, checkmate, stalemate:** standard. Checkmate wins; stalemate is a draw.
- **Draws:** stalemate, the fifty-move rule, threefold repetition, and insufficient
  material.

## Promotion

A pawn reaching the far rank promotes (mandatory) to a **Chancellor, Rook, Bishop, or
Knight** — the Chancellor takes the queen's slot as the strongest promotion choice.
(*Implementation note:* the original sources don't spell the promotion set out; this
follows the standard chess convention of promoting to this game's most powerful piece
plus R/B/N.)

## Notation

Moves are entered by clicking the piece and its destination. Castling is the king's
two-square move. A promotion appends the chosen piece, e.g. `b7>b8=M` for a Chancellor.
