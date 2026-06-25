# Gardner's Minichess

The classic 5×5 minichess, designed by **Martin Gardner** and published in his
*Scientific American* "Mathematical Games" column in 1969. It packs every chess
piece onto the smallest board on which all of them retain their normal moves.

## Objective
Checkmate the opponent's king.

## Board & setup (5×5)
Files a–e, ranks 1–5. White occupies ranks 1–2, Black ranks 4–5:

```
5  r n b q k     (Black back rank)
4  p p p p p     (Black pawns)
3  . . . . .
2  P P P P P     (White pawns)
1  R N B Q K     (White back rank)
   a b c d e
```

Each side has a Rook, Knight, Bishop, Queen, King and five pawns (10 men).
The back rank reads **R N B Q K** for both sides (a→e), so the kings start on
the e-file facing each other. **White moves first.**

## How the pieces move
Exactly as in orthodox chess — rook orthogonally, bishop diagonally, queen in
all eight directions, knight in its L, king one step, pawn one step forward and
captures diagonally.

## Differences from standard chess
- **No castling.**
- **No double pawn step** (a pawn always advances exactly one square), and
  therefore **no en passant**.
- Pawns **promote** on reaching the far rank. Promotion is to **Queen, Rook,
  Bishop, or Knight** (any non-king back-rank piece), chosen by the player.

## Winning & draws
Checkmate wins. **Stalemate** is a draw, as is **insufficient material**. A
no-progress (50-move) rule and a hard ply cap also force a draw, guaranteeing
the game terminates.
