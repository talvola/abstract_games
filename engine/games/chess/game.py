"""Standard chess (8x8), full rules, built on the shared chess-like core.

Castling, en passant, pawn double-step and promotion to Q/R/B/N, check /
checkmate / stalemate, and draws by the fifty-move rule, threefold repetition and
insufficient material -- all supplied by ``agp.chesslike``. White = player 0.
Moves use the clickable cell-path notation; castling is the king's two-square
move (the rook follows automatically) and promotion appends "=Q/R/B/N".
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class Chess(ChessLike):
    uid = "chess"
    name = "Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = StandardCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b
