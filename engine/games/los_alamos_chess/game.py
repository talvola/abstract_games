"""Los Alamos chess -- simplified 6x6 chess (Stein & Wells, MANIAC I, 1956),
built on the shared chess-like core.

Differences from orthodox chess: 6x6 board, no bishops (the queen still moves in
all eight directions), no castling, no double pawn step, no en passant. Pawns
promote on the far rank to Queen, Rook, or Knight. White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, NoCastling,
    ORTHO, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "Q", "K", "N", "R"]


class LosAlamosChess(ChessLike):
    uid = "los_alamos_chess"
    name = "Los Alamos Chess"

    WIDTH = HEIGHT = 6
    PLY_CAP = 200
    PIECES = {
        "R": (ORTHO, []), "Q": (ALL8, []), "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=4, double=False)
    PROMOTION = LastRankPromotion(("Q", "R", "N"))
    CASTLING = NoCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(6):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 4)] = (BLACK, "P")
            b[(c, 5)] = (BLACK, BACK_RANK[c])
        return b
