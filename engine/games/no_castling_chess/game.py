"""No-Castling Chess (8x8), built on the shared chess-like core.

Standard chess in every respect *except* that castling is not permitted for
either side -- the rule popularised by Vladimir Kramnik (2019) as a way to
reduce opening theory and force kings to work harder for safety.

Because castling can never occur regardless, the opening perft is identical to
standard chess at shallow depths (20 / 400 / 8902 at depths 1/2/3): the earliest
a king or rook could castle is well beyond depth 3, so no node is removed until a
king has both castling rights and a clear, unattacked path -- which first arises
only in deeper lines. All piece movement, en passant, promotion, and the ordinary
chess draws are unchanged. White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, NoCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class NoCastlingChess(ChessLike):
    uid = "no_castling_chess"
    name = "No-Castling Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = NoCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b
