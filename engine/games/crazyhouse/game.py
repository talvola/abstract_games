"""Crazyhouse (8x8) -- chess where captured pieces switch sides and return to
play as drops, built on the shared chess-like core.

All ordinary chess rules apply (castling, en passant, double-step, promotion to
Q/R/B/N, check/checkmate/stalemate). In addition, every piece you capture is
flipped to your colour and added to your reserve; on your turn you may instead
*drop* a reserved piece onto any empty square (pawns may not be dropped on the
first or last rank). A piece that was promoted reverts to a pawn when captured.
There is no draw by insufficient material -- material can always re-enter the
board -- so draws come from threefold repetition, the fifty-move rule, or
stalemate. White = player 0. Drops use the notation "L@c,r"; the reserve is shown
in trays above and below the board.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling, CrazyhouseDrops,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class Crazyhouse(ChessLike):
    uid = "crazyhouse"
    name = "Crazyhouse"

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
    DROPS = CrazyhouseDrops()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b
