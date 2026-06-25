"""Gardner's Minichess -- the classic 5x5 minichess (Martin Gardner, 1969),
built on the shared chess-like core.

Pieces move exactly as in orthodox chess. Differences from standard chess: a
5x5 board, **no castling**, **no double pawn step** (and therefore no en
passant). Pawns promote on the far rank. White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, NoCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K"]


class GardnerMinichess(ChessLike):
    uid = "gardner_minichess"
    name = "Gardner's Minichess"

    WIDTH = HEIGHT = 5
    PLY_CAP = 200
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=3, double=False)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = NoCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(5):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 3)] = (BLACK, "P")
            b[(c, 4)] = (BLACK, BACK_RANK[c])
        return b
