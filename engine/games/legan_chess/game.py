"""Legan Chess (L. Legan, 1913): a corner-to-corner chess variant.

The whole game is rotated to a diagonal orientation: White attacks toward the
a8 corner (up-left), Black toward the h1 corner (down-right). Every army sits
along the two board edges adjacent to its own corner, behind a diagonal pawn
wall.

The signature is the **Legan pawn**, which advances toward the enemy corner:

* A WHITE pawn MOVES one step diagonally up-left, direction ``(-1, +1)`` (e.g.
  f3->e4), and CAPTURES one step orthogonally in the direction of that advance,
  i.e. left ``(-1, 0)`` or up ``(0, +1)`` (e.g. a pawn on f3 captures on e3 / f4).
* A BLACK pawn MOVES one step diagonally down-right, direction ``(+1, -1)``, and
  CAPTURES right ``(+1, 0)`` or down ``(0, -1)``.

There is no double step, no en passant, and no castling. A pawn promotes when it
reaches the enemy corner -- i.e. either of the two far edges by that corner:
White on the a-file (col 0) or the 8th rank (row 7); Black on the h-file
(col 7) or the 1st rank (row 0). All other pieces, check, mate, stalemate and the
draw rules are exactly as in standard chess.

Source: https://en.wikipedia.org/wiki/Legan_chess
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, PawnRules, PromotionRules, NoCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)


class LeganPawn(PawnRules):
    """A pawn that advances toward the enemy corner: moves one step diagonally,
    captures one step orthogonally (the two orthogonal steps that share the
    advance's direction). No double step and no en passant."""

    # move direction (dc, dr) toward the enemy corner, per colour
    MOVE = {WHITE: (-1, 1), BLACK: (1, -1)}
    # the two orthogonal capture steps, per colour
    CAPS = {WHITE: ((-1, 0), (0, 1)), BLACK: ((1, 0), (0, -1))}

    def __init__(self):
        # No home rank / double step; en passant never arises.
        super().__init__(white_start=-1, black_start=-1, double=False)

    def ep_after(self, frm, to):
        return None

    def pseudo(self, core, board, c, r, player, ep_target):
        mdc, mdr = self.MOVE[player]
        step = (c + mdc, r + mdr)
        if core.on(*step) and step not in board:
            yield (c, r), step
        for ddc, ddr in self.CAPS[player]:
            t = (c + ddc, r + ddr)
            if not core.on(*t):
                continue
            occ = board.get(t)
            if occ is not None and occ[0] != player:
                yield (c, r), t

    def attacks(self, core, board, c, r, by) -> bool:
        # An enemy pawn attacks (c, r) if it sits one orthogonal capture step
        # away, on the square it would capture FROM.
        for ddc, ddr in self.CAPS[by]:
            if board.get((c - ddc, r - ddr)) == (by, "P"):
                return True
        return False


class LeganPromotion(PromotionRules):
    """Promote (mandatory) on reaching the enemy corner -- either of the two far
    edges by that corner. White: a-file (col 0) or 8th rank (row 7). Black:
    h-file (col WIDTH-1) or 1st rank (row 0)."""

    def __init__(self, targets):
        self.targets = tuple(targets)

    def _is_zone(self, core, player, to):
        if player == WHITE:
            return to[0] == 0 or to[1] == core.HEIGHT - 1
        return to[0] == core.WIDTH - 1 or to[1] == 0

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        return list(self.targets) if self._is_zone(core, pl, to) else [None]


class LeganChess(ChessLike):
    name = "Legan Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = LeganPawn()
    PROMOTION = LeganPromotion(("Q", "R", "B", "N"))
    CASTLING = NoCastling()

    # Canonical Legan starting position (Wikipedia). Black is the 180-degree
    # rotation of White through the board centre.
    WHITE_PIECES = {
        (7, 0): "K", (6, 1): "Q",
        (5, 0): "B", (7, 1): "B",
        (6, 0): "N", (7, 2): "N",
        (4, 0): "R", (7, 3): "R",
    }
    WHITE_PAWNS = [(3, 0), (4, 1), (4, 3), (5, 1), (5, 2), (6, 2), (6, 3), (7, 4)]

    def setup_board(self) -> dict:
        b = {}
        for (c, r), t in self.WHITE_PIECES.items():
            b[(c, r)] = (WHITE, t)
            b[(7 - c, 7 - r)] = (BLACK, t)
        for (c, r) in self.WHITE_PAWNS:
            b[(c, r)] = (WHITE, "P")
            b[(7 - c, 7 - r)] = (BLACK, "P")
        return b

    def _is_promo_zone(self, player, to):
        return self.PROMOTION._is_zone(self, player, to)

    def _apply_board(self, board, frm, to, ep):
        """Override only the promotion test: Legan promotes on the corner edges,
        not on the last rank. Everything else is the base behaviour."""
        b = dict(board)
        pl, t = b.pop(frm)
        if t == "P" and self._is_promo_zone(pl, to):
            t = self.PROMOTION.safety_piece()
        b[to] = (pl, t)
        return b
