# Chess

Standard chess on an 8×8 board, with the full FIDE rules.

## Objective
Checkmate the opponent's king — attack it so that it cannot escape capture.

## Board & setup
The usual array: pawns on the second rank, and R N B Q K B N R behind them. White is player 1 and moves first; Black is player 2.

## Play
Pieces move as in standard chess (king, queen, rook, bishop, knight, pawn). The implementation includes all the special rules:
- **Castling**, king- and queen-side (with the usual rights and "not through, into, or out of check" restrictions).
- **En passant** capture.
- **Pawn double-step** from the starting rank, and **promotion** to Q/R/B/N on the last rank.

## Winning & draws
- **Checkmate** wins. **Stalemate** (no legal move while not in check) is a draw.
- Also drawn by the **fifty-move rule**, **threefold repetition**, and **insufficient material**.

## In this implementation
- Castling is entered as the king's two-square move; the rook follows automatically. Promotion shows a Q/R/B/N picker.
