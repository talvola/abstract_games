"""Maharajah and the Sepoys -- a classic asymmetric chess variant.

One player ("the Maharajah") has a SINGLE super-piece, the Maharajah/Amazon,
which moves as a queen *or* a knight combined. The other player ("the Sepoys")
has a FULL standard chess army (8 pawns + R N B Q K B N R). The Sepoys move by
normal chess rules, with TWO differences from orthodox chess:

* the Maharajah is the lone royal piece for its side (it is "checkmated" exactly
  like a king -- if it is attacked and cannot escape capture, the Sepoys win),
  and
* **Sepoy pawns may NOT promote** -- a sepoy pawn reaching the last rank simply
  stays a pawn. (This is the rule that makes the lone Maharajah a fair fight: an
  unrestricted promoting army would trivially overwhelm it.)

Seat assignment (documented):

* **Seat 0 = the Maharajah = White** -- a single piece "M" starting on **e1**
  (cell ``4,0``), moving as queen + knight (an Amazon). It is royal.
* **Seat 1 = the Sepoys = Black** -- the standard 16-piece army on ranks 7 & 8
  (rows 6 & 7), pawns advancing toward row 0. The king "K" is royal.

**The Sepoys (Black) move first** (per the Wikipedia ruleset). White wins by
checkmating the Sepoy king; Black wins by checkmating (capturing/trapping) the
Maharajah. Both royals obey the usual check rules on their own turn.

Wiring vs. ``ChessLike``:

* The Amazon is a new ``PIECES`` entry ``"M": (ALL8, KNIGHT)`` (queen slides +
  knight leaps).
* ChessLike hard-codes the king letter "K" as *the* royal. Here each side has a
  *different* royal letter, so ``_royal_sq`` is overridden to return the M for
  White and the K for Black, and ``in_check`` routes through it. Everything that
  used ``_king`` (check / mate / stalemate / ``returns``) now respects the
  per-side royal.
* No promotion: ``PROMOTION = NoPromotion()`` always returns ``[None]`` (a sepoy
  pawn reaching the last rank just stays a pawn), and ``_apply_board`` / safety
  testing never auto-queens.
* No castling, no drops (the Maharajah side has no king or rook to castle).
* The Sepoys move first: ``initial_state`` sets ``to_move = BLACK``.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, StandardPawn, PromotionRules, NoCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# Sepoy (Black) back rank, standard.
SEPOY_BACK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class NoPromotion(PromotionRules):
    """Sepoy pawns never promote: a pawn reaching the last rank stays a pawn."""

    def options(self, core, state, frm, to):
        return [None]

    def safety_piece(self) -> str:
        # Used only by ChessLike's king-safety preview, which only promotes a
        # pawn that reaches the last rank. Since we never promote, this value is
        # effectively unused, but a pawn is the honest answer.
        return "P"


class Maharajah(ChessLike):
    uid = "maharajah"
    name = "Maharajah and the Sepoys"

    WIDTH = HEIGHT = 8
    PLY_CAP = 400

    PIECES = {
        # Sepoy pieces (standard).
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
        # The Maharajah / Amazon: queen slides + knight leaps.
        "M": (ALL8, KNIGHT),
    }
    # Mating material: the lone Maharajah ("M") is always able to deliver mate,
    # and the Sepoy army is heavy. We never want an insufficient-material draw
    # here, so list everything that can appear.
    HEAVY = ("P", "R", "Q", "N", "B", "M")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = NoPromotion()
    CASTLING = NoCastling()

    # ---- per-side royal -----------------------------------------------------
    def _royal_sq(self, board, player):
        """The royal square for ``player``: the Maharajah "M" for White (seat 0),
        the king "K" for Black (seat 1)."""
        want = "M" if player == WHITE else "K"
        for (c, r), (pl, t) in board.items():
            if pl == player and t == want:
                return c, r
        return None

    # Keep ChessLike's helpers (used by castling etc.) consistent.
    def _king(self, board, player):
        return self._royal_sq(board, player)

    def in_check(self, board, player) -> bool:
        royal = self._royal_sq(board, player)
        return royal is not None and self.attacked(board, royal[0], royal[1], 1 - player)

    # ---- setup / move order -------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        # Seat 0 / White: the lone Maharajah on e1 (4,0).
        b[(4, 0)] = (WHITE, "M")
        # Seat 1 / Black: the full Sepoy army on ranks 7 & 8 (rows 6 & 7).
        for c in range(8):
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, SEPOY_BACK[c])
        return b

    def initial_state(self, options=None, rng=None):
        st = super().initial_state(options, rng)
        # The Sepoys (Black) move first.
        st.to_move = BLACK
        st.reps = {self._poskey_state(st): 1}
        return st

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "Maharajah", BLACK: "Sepoys"}
        if self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                spec["caption"] = "Draw"
            else:
                winner = 0 if ret[0] > 0 else 1
                spec["caption"] = f"{names[winner]} win (checkmate)"
        elif self.in_check(state.board, state.to_move):
            spec["caption"] = f"{names[state.to_move]} to move (check)"
        else:
            spec["caption"] = f"{names[state.to_move]} to move"
        return spec
