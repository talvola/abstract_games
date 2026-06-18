"""Grand Chess (Christian Freeling, 1984), 10x10, built on the shared core.

Adds the Marshall "M" (rook + knight) and Cardinal "C" (bishop + knight); pawns
start on the third rank; there is no castling; and promotion is restricted to a
piece type the owner has lost (optional on the 8th/9th ranks, compulsory on the
10th) -- see ``GrandPromotion``. White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, GrandPromotion, NoCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

MAJORS = ["N", "B", "Q", "K", "M", "C", "B", "N"]   # files b..i on the 2nd/9th rank


class GrandChess(ChessLike):
    uid = "grand_chess"
    name = "Grand Chess"

    WIDTH = HEIGHT = 10
    PLY_CAP = 800
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []), "N": ([], KNIGHT),
        "K": ([], ALL8), "M": (ORTHO, KNIGHT), "C": (DIAG, KNIGHT),
    }
    HEAVY = ("P", "R", "Q", "M", "C")
    PAWN = StandardPawn(white_start=2, black_start=7)
    PROMOTION = GrandPromotion({"Q": 1, "M": 1, "C": 1, "R": 2, "B": 2, "N": 2})
    CASTLING = NoCastling()

    def setup_board(self) -> dict:
        b = {}
        b[(0, 0)] = b[(9, 0)] = (WHITE, "R")
        b[(0, 9)] = b[(9, 9)] = (BLACK, "R")
        for i, t in enumerate(MAJORS):
            b[(i + 1, 1)] = (WHITE, t)
            b[(i + 1, 8)] = (BLACK, t)
        for c in range(10):
            b[(c, 2)] = (WHITE, "P")
            b[(c, 7)] = (BLACK, "P")
        return b
