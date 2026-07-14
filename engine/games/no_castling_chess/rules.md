# No-Castling Chess

Standard chess on an 8×8 board with **one rule removed: castling is not allowed** for either side.

Proposed by former World Champion Vladimir Kramnik in 2019 (with Google DeepMind's AlphaZero used to study its character), the idea is to reduce memorised opening theory and make king safety something a player has to earn by hand, since the king can no longer be tucked away in one move.

## Objective
Checkmate the opponent's king — attack it so that it cannot escape capture.

## Board & setup
The usual array: pawns on the second rank, and R N B Q K B N R behind them. White is player 1 and moves first; Black is player 2.

## Play
Every piece moves exactly as in standard chess (king, queen, rook, bishop, knight, pawn), including:
- **En passant** capture.
- **Pawn double-step** from the starting rank, and **promotion** to Q/R/B/N on the last rank.

The single difference from orthodox chess:
- **No castling.** Neither king- nor queen-side castling is ever offered, so the king must be moved one square at a time.

## Winning & draws
- **Checkmate** wins. **Stalemate** (no legal move while not in check) is a draw.
- Also drawn by the **fifty-move rule**, **threefold repetition**, and **insufficient material**.

## In this implementation
- Because castling is disabled, the king's only moves are the ordinary one-square king steps. Promotion shows a Q/R/B/N picker.
