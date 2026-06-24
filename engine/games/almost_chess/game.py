"""Almost Chess (Ralph Betza, 1977), 8x8, built on the shared chess-like core.

Standard chess in every respect EXCEPT that each player's queen is replaced by a
**Chancellor** "M" -- a compound piece moving as a Rook OR a Knight (also called
a Marshall or Empress). It has NO bishop (diagonal) move. The Chancellor starts
on the queen's square (d1 / d8). Castling, en passant, the pawn double-step, and
all the draw rules are standard; pawns promote to a Chancellor / R / B / N (the
Chancellor is this game's most powerful piece, taking the queen's promotion slot).
White = player 0.

The Chancellor reuses Grand Chess's Marshall: letter "M", movement
``(ORTHO, KNIGHT)`` -- rook rays plus knight leaps. "M" is already rendered as
"Marshall" by the web Board, so no UI change is needed.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "M", "K", "B", "N", "R"]   # Chancellor "M" on the d-file


class AlmostChess(ChessLike):
    uid = "almost_chess"
    name = "Almost Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "N": ([], KNIGHT),
        "K": ([], ALL8), "M": (ORTHO, KNIGHT),   # Chancellor = Rook + Knight
    }
    HEAVY = ("P", "R", "M")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("M", "R", "B", "N"))
    CASTLING = StandardCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b
