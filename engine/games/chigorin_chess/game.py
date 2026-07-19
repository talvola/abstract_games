"""Chigorin Chess (Ralph Betza, 2002) -- Knights army vs Bishops army.

Standard 8x8 chess with unequal armies, named for Mikhail Chigorin's supposed
fondness for Knights over Bishops:

* **White** (the "Chigorin" side): Rooks a1/h1, four Knights b1/c1/f1/g1, a
  **Chancellor** (Rook + Knight compound) on d1, King e1, eight Pawns.
* **Black**: Rooks a8/h8, four Bishops b8/c8/f8/g8, an orthodox Queen d8,
  King e8, eight Pawns.

All other FIDE rules apply: castling both wings, en passant, check/checkmate,
stalemate and the usual draws.  Pawn promotion is to a piece of the *owner's
own army* (Betza's stated preference for this game, and exactly the
Fairy-Stockfish ``chigorin`` built-in ruleset): White promotes to Chancellor,
Rook or Knight; Black promotes to Queen, Rook or Bishop.

Sources: Betza's page https://www.chessvariants.com/diffsetup.dir/chigorin.html,
the Fairy-Stockfish built-in variant ``chigorin`` (perft-anchored via pyffish;
see ``_diff_pyffish.py``), and John Vehre's article in Abstract Games #24.
White = player 0 (advances toward higher rows).  See ``rules.md``.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, PromotionRules, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

WHITE_RANK = ["R", "N", "N", "C", "K", "N", "N", "R"]
BLACK_RANK = ["R", "B", "B", "Q", "K", "B", "B", "R"]


class OwnArmyPromotion(PromotionRules):
    """Mandatory last-rank promotion, to a piece of the mover's OWN army only
    (Betza's rule for this game; matches the Fairy-Stockfish ``chigorin``
    built-in): White -> Chancellor/Rook/Knight, Black -> Queen/Rook/Bishop."""

    TARGETS = {WHITE: ("C", "R", "N"), BLACK: ("Q", "R", "B")}

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        last = (to[1] == core.HEIGHT - 1 and pl == WHITE) or (to[1] == 0 and pl == BLACK)
        return list(self.TARGETS[pl]) if last else [None]

    def safety_piece(self) -> str:
        # Only used for occupancy when probing the mover's OWN king safety;
        # the promoted piece's movement is never queried there.
        return "Q"


class ChigorinChess(ChessLike):
    uid = "chigorin_chess"
    name = "Chigorin Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT),
        "C": (ORTHO, KNIGHT),      # Chancellor = Rook + Knight (icon auto-derived)
        "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q", "C")   # B/N keep the base lone-minor draw handling

    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = OwnArmyPromotion()
    CASTLING = StandardCastling()

    PIECE_VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "C": 8.5,
                    "Q": 9.0, "K": 0.0}

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, WHITE_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BLACK_RANK[c])
        return b

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        spec["choiceNames"] = {"C": "Chancellor"}   # Q/R/B/N have built-in names
        return spec
