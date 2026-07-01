# Opulent Chess

Greg Strong's 10×10 chess variant (2005) — Grand Chess with a stronger Knight and two new leapers, giving 10 piece types on a 10×10 board.

## Objective
Checkmate the opponent's King.

## Board & setup (10×10, files a–j, ranks 1–10)
- **Rank 1 / 10:** Rooks on a1, j1; **Wizards** on b1, i1 (mirrored for Black on rank 10).
- **Rank 2 / 9:** **C L N B Q K B N L A** (a→j): Chancellor, Lion, Knight, Bishop, Queen, King, Bishop, Knight, Lion, Archbishop.
- **Rank 3 / 8:** ten Pawns each.

## Pieces
- **King (K), Queen (Q), Rook (R), Bishop (B), Pawn (P)** — as in orthodox chess.
- **Knight (N)** — orthodox knight **plus** a single step horizontally or vertically (a knight + wazir). Still changes square colour every move.
- **Wizard (W)** — leaps like a **camel** (1,3) *or* steps one square diagonally (ferz). Colorbound.
- **Lion (L)** — Betza's *Half-Duck*: leaps **2 or 3 squares horizontally or vertically** (jumping over any pieces in between), or steps one square diagonally.
- **Chancellor (C)** — rook + orthodox knight.
- **Archbishop (A)** — bishop + orthodox knight (it does **not** get the Knight's extra step).

## Play
White moves first. Pawns step one square forward, may step **one or two** from their starting (third) rank, capture diagonally, and may capture **en passant**. **There is no castling.**

### Promotion (Grand Chess rule)
A pawn may promote **only to a piece type its owner has lost** (you can never field more of a type than you started with: 1×Q/C/A, 2×R/B/N/L/W). Promotion is **optional** on the 8th and 9th ranks and **compulsory** on the 10th. If no captured piece is available, the pawn **may not move onto the 10th rank** and is stuck on the 9th (where it still attacks and can give check).

## Winning & draws
Checkmate wins. Stalemate, threefold repetition, the fifty-move rule, and insufficient material (bare kings or a lone bishop) are draws; a long game is adjudicated a draw at 800 plies.

## Notes / as implemented
- Piece letters follow the author's notation (W = Wizard; the Chancellor is C and the Archbishop A — unlike this site's Grand Chess port, which uses Freeling's names Marshall/Cardinal for the same two compounds).
- Source (rules as published by the inventor): <https://www.chessvariants.com/rules/opulent-chess>
