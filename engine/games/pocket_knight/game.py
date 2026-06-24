"""Pocket Knight Chess (a.k.a. Tombola / Pocket Knight) -- standard chess where
each player holds ONE extra knight "in pocket" that may be dropped onto any
empty square, once, instead of a normal move.

Everything is ordinary chess (standard setup, castling, en passant, pawn
double-step and promotion, check / checkmate / stalemate, the fifty-move,
threefold-repetition draws) -- all supplied by ``agp.chesslike``. The only
addition is the pocket knight: each side starts with exactly one knight in its
reserve ("N": 1). On any turn a player may, instead of moving a board piece,
*drop* that knight onto any empty square with the move notation "N@c,r". The
drop is the whole turn, the player's own king may not be left in check, and the
reserve then empties -- each side gets exactly one pocket-knight drop for the
whole game.

This is NOT Crazyhouse: captured pieces are NEVER banked into the reserve. The
pocket knight is a one-time resource that is never replenished. The difference
from Crazyhouse is entirely in the ``DROPS`` strategy below
(``PocketKnightDrops``): it seeds one knight per side and its ``captured_to_hand``
returns ``None`` so nothing is ever added to a hand.

Drop-to-mate: a pocket-knight drop MAY deliver check and MAY deliver checkmate.
This follows the standard published rule (chessvariants.com "Pocket Knight",
where the only restriction is that the knight drops on a vacant square and the
mover's king is not left in check); the dropped knight is an ordinary piece, so
the move is legal exactly when any other check/mate-giving move would be. Some
casual variants forbid mate-by-drop; we follow the standard permissive rule.

White = player 0. The reserve is shown in trays above and below the board.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling, DropRules,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class PocketKnightDrops(DropRules):
    """One-time pocket knight per side. Each player starts with a single knight
    in hand; it may be dropped on ANY empty square (subject only to the shared
    rule that the mover's king is not left in check, enforced by the core's
    legal-move filter). Captures are NEVER banked, so a hand only ever holds the
    original knight, and once dropped it is gone for good (unlike Crazyhouse,
    where ``captured_to_hand`` recycles captured material)."""

    enabled = True

    def initial_hands(self, core) -> dict:
        return {WHITE: {"N": 1}, BLACK: {"N": 1}}

    def can_drop_on(self, core, state, letter, to, player) -> bool:
        # A knight may drop on any empty square (no rank restriction). The
        # target's emptiness and the not-in-check rule are handled by the core.
        return True

    def captured_to_hand(self, core, letter, was_promoted):
        # Never bank captured material -- the pocket knight is one-time only.
        return None


class PocketKnight(ChessLike):
    uid = "pocket_knight"
    name = "Pocket Knight Chess"

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
    DROPS = PocketKnightDrops()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b
