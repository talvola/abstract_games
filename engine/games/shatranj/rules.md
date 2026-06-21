# Shatranj

Shatranj is medieval Persian/Arabic chess, the direct ancestor of the modern
game. It is played on an ordinary 8x8 board with the same array of pieces as
chess, but several pieces are much shorter-ranged, and the way you *win* is
different. White (player 0) moves first; players alternate, one move per turn.

These are the rules **as implemented** in this package. Where historical sources
disagree, the choice made here is noted explicitly.

## The pieces

| Piece | Name | How it moves |
|-------|------|--------------|
| Shah | King (`K`) | One square in any direction, exactly like a chess king. **No castling.** |
| Firzan / Ferz | "Counsellor", ancestor of the queen (`F`) | Exactly **one square diagonally**. Nothing more. |
| Alfil | Elephant, ancestor of the bishop (`A`) | **Leaps exactly two squares diagonally**, jumping over any piece on the square in between. |
| Rukh | Rook (`R`) | Any distance orthogonally, exactly like a chess rook. |
| Asp / Faras | Knight (`N`) | The chess knight's leap. |
| Baidaq | Pawn (`P`) | One square straight forward (**never two**); captures one square diagonally forward. |

The Alfil is a *leaper*: pieces between it and its destination do not block it,
and it can only ever reach 8 of the 64 squares (its colour-bound triangle).

The Firzan is also a leaper in the technical sense (it only ever moves to an
adjacent diagonal square), and like the Alfil it is colour-bound.

## Setup

The opening array is the same files as chess, with the counsellor/elephant
replacing the queen/bishops:

```
R N A F K A N R     (Black, rank 8)
P P P P P P P P
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
P P P P P P P P
R N A F K A N R     (White, rank 1)
```

The Firzan starts on the d-file beside the Shah, as in historic Shatranj
(king on e, counsellor on d). The two players' counsellors therefore start on
opposite-coloured squares (kings face each other; this package does not "mirror"
the array).

## Pawns

* A Baidaq moves **one square straight forward** only. There is **no two-square
  first move**, and consequently **no en passant**.
* It captures one square diagonally forward, like a chess pawn.
* On reaching the far rank it **promotes, and only to a Firzan** (`=F`). There is
  no choice of promotion piece.

## Check and the royal Shah

The Shah may not move into check, you must escape check, and you may not leave
your own Shah in check — all exactly as in chess.

## Winning

A game ends, and is decided, in one of these ways:

1. **Checkmate.** The side to move is in check and has no legal move. That side
   loses.
2. **Stalemate — a WIN for the stalemating side.** If the side to move is *not*
   in check but has no legal move, in Shatranj this is **not** a draw: the
   stalemated player **loses** (the opponent who produced the position wins).
3. **Baring the king (bare-king).** If you capture so that your opponent is
   reduced to a **lone king** (no other pieces), you win — *unless* on the
   **immediately following move** that opponent can capture your last non-king
   piece and so bare your king in return. If they can bare you back, the game is
   a **draw**. If both kings end up bare at the same time, it is likewise a draw.

   In this implementation the bare-king decision is evaluated the moment a side
   is reduced to a lone king: if that side (now to move) has any legal move that
   leaves the opponent also with a lone king, the result is an immediate draw;
   otherwise the side that did the baring wins immediately.

## Ruleset choices / interpretations

* **No medieval draw rules.** Shatranj historically had no fifty-move,
  threefold-repetition or insufficient-material draw. This package omits them:
  material that modern chess would call "insufficient" is decided by the
  bare-king rule instead. The **only** automatic draw is a ply cap (600 plies),
  kept purely so the engine's termination requirement is met; it is far beyond
  any realistic game length.
* **Promotion to Firzan only**, matching historic Shatranj (no promotion to
  Rukh/Asp/Alfil).
* **No castling** and **no pawn double step / en passant**, as in the historic
  game.
* **Starting placement of the Firzan** is beside the Shah (king on e, counsellor
  on d) for both sides, with no left/right mirroring between the two armies.

## Notation

Moves are the platform's clickable cell-path strings, e.g. `4,1>4,2`
(from–to). Pawn promotion appends `=F`, e.g. `0,6>0,7=F`. Piece letters in the
move log are `K` (Shah), `F` (Firzan), `A` (Alfil), `R` (Rukh), `N` (Asp),
`P` (Baidaq).
