"""King of the Hill -- standard chess plus a "reach the centre" win.

Identical to standard chess in every way (castling, en passant, pawn
double-step and promotion, check / checkmate / stalemate, and the fifty-move /
threefold-repetition / insufficient-material draws), all supplied by
``agp.chesslike`` -- EXCEPT a player ALSO wins immediately the moment their own
king reaches one of the four central squares d4/d5/e4/e5 (engine 0-based
``c,r``: cols 3-4, rows 3-4).

Because the king must arrive there by an ordinary *legal* move, it can never
step into check to do so, and the legal-move set is byte-for-byte identical to
standard chess -- so opening perft stays 20 / 400 / 8902. The only changes are
to terminal detection / the result / the caption: subclass the standard ``Chess``
configuration and layer the centre win on top.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]

# The four central squares d4/d5/e4/e5 in 0-based (col, row) coordinates.
HILL = frozenset({(3, 3), (3, 4), (4, 3), (4, 4)})


class KingOfTheHill(ChessLike):
    uid = "king_of_the_hill"
    name = "King of the Hill"

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

    # ---- centre-king win ----------------------------------------------------
    def _king_on_hill(self, board):
        """Return the player whose king sits on a central square, else None.

        Both kings can never legally be on the hill at once (only the side that
        just moved can have just arrived), so at most one player is returned.
        """
        for sq in HILL:
            occ = board.get(sq)
            if occ is not None and occ[1] == "K":
                return occ[0]
        return None

    def is_terminal(self, state) -> bool:
        if self._king_on_hill(state.board) is not None:
            return True
        return super().is_terminal(state)

    def returns(self, state) -> list:
        winner = self._king_on_hill(state.board)
        if winner is not None:
            return [1.0, -1.0] if winner == WHITE else [-1.0, 1.0]
        return super().returns(state)

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        spec["highlights"] = [{"cell": f"{c},{r}", "kind": "zone"} for (c, r) in sorted(HILL)]
        winner = self._king_on_hill(state.board)
        if winner is not None:
            names = {WHITE: "White", BLACK: "Black"}
            spec["caption"] = f"{names[winner]} wins (king on the hill)"
        return spec
