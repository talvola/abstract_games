"""Berolina Chess (Edmund Hebermann, Berlin 1926), built on the shared core.

Standard chess except the pawn is a *Berolina pawn*: it MOVES one square
diagonally forward (two on its first move) and CAPTURES one square straight
ahead -- so it also attacks (and checks) straight ahead, not on the diagonals.
En passant applies to the diagonal double-step. Everything else (pieces,
castling, draws) is ordinary chess.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, BerolinaPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class Berolina(ChessLike):
    uid = "berolina"
    name = "Berolina Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = BerolinaPawn(white_start=1, black_start=6)
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
