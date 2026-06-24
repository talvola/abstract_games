"""Modern Chess / Ajedrez Moderno (Gabriel Vicente Maura, Puerto Rico, 1968),
played on a 9x9 board, built on the shared chess-like core.

Adds one compound piece per side: the **Prime Minister** (a.k.a. Minister, or
"princess") "M" = bishop + knight (the same compound as Capablanca's Archbishop /
Cardinal). The back rank (files a..i) is ``R N B M K Q B N R``: the King sits on
the middle file (e), the Queen to its right (f) and the Prime Minister to its
left (d). The nine pawns start on the 2nd / 8th ranks with the orthodox pawn
(double-step, en passant) and promote to Q/R/B/N/M on the last rank.

Castling is Maura's two-square king slide toward either rook (see
:class:`ModernCastling`):

* Ministerside (0-M-0):  K e1->g1 (4->6), R i1->h1 (8->7)
* Queenside   (0-Q-0):  K e1->c1 (4->2), R a1->d1 (0->3)

White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, Castling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# Files a..i (0..8) on the back rank. King on e (4), Queen on f (5, right of
# king), Prime Minister on d (3, left of king).
BACK_RANK = ["R", "N", "B", "M", "K", "Q", "B", "N", "R"]


class ModernCastling(Castling):
    """Modern Chess castling on the 9-wide board.

    King starts on e1/e9 (file index 4), rooks in the corners a/i (0 and 8).
    The king slides **two** squares toward the chosen rook, and the rook jumps
    to the square the king passed over:

    * Ministerside (0-M-0): K e1->g1 (4->6), R i1->h1 (8->7)
    * Queenside    (0-Q-0): K e1->c1 (4->2), R a1->d1 (0->3)

    As in orthodox chess: neither piece may have moved, the squares between king
    and rook must be empty, and the king may not start in, pass through, or land
    in check. ``flag`` letters are K/Q (White) and k/q (Black) -- K = the
    ministerside (toward the i-file rook), Q = the queenside (toward the a-file
    rook).
    """

    # flag -> (king_from, king_to, rook_from, rook_to, empties_between,
    #          king_path_squares_that_must_be_safe)
    CASTLES = {
        # Ministerside: king slides toward the i1 rook (rights flag "K").
        "K": ((4, 0), (6, 0), (8, 0), (7, 0), [(5, 0), (6, 0), (7, 0)],
              [(4, 0), (5, 0), (6, 0)]),
        # Queenside: king slides toward the a1 rook (rights flag "Q").
        "Q": ((4, 0), (2, 0), (0, 0), (3, 0), [(1, 0), (2, 0), (3, 0)],
              [(4, 0), (3, 0), (2, 0)]),
        "k": ((4, 8), (6, 8), (8, 8), (7, 8), [(5, 8), (6, 8), (7, 8)],
              [(4, 8), (5, 8), (6, 8)]),
        "q": ((4, 8), (2, 8), (0, 8), (3, 8), [(1, 8), (2, 8), (3, 8)],
              [(4, 8), (3, 8), (2, 8)]),
    }
    BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
    ROOK_HOME = {(8, 0): "K", (0, 0): "Q", (8, 8): "k", (0, 8): "q"}
    KING_HOME = {(4, 0): WHITE, (4, 8): BLACK}

    def initial_rights(self):
        return frozenset("KQkq")

    def moves(self, core, state):
        player = state.to_move
        enemy = 1 - player
        if core.in_check(state.board, player):
            return
        for flag in self.BY_COLOR[player]:
            if flag not in state.castling:
                continue
            kfrom, kto, rfrom, rto, empties, path = self.CASTLES[flag]
            if (state.board.get(kfrom) != (player, "K")
                    or state.board.get(rfrom) != (player, "R")):
                continue
            if any(sq in state.board for sq in empties):
                continue
            if any(core.attacked(state.board, c, r, enemy) for (c, r) in path):
                continue
            yield kfrom, kto

    def rook_move(self, frm, to, player):
        if abs(to[0] - frm[0]) != 2:
            return None
        flag = self.BY_COLOR[player][0] if to[0] > frm[0] else self.BY_COLOR[player][1]
        _, _, rfrom, rto, _, _ = self.CASTLES[flag]
        return rfrom, rto

    def update_rights(self, rights, frm, to, board):
        rights = set(rights)
        pl, t = board[frm]
        if t == "K" and frm in self.KING_HOME:
            rights -= set(self.BY_COLOR[pl])
        if frm in self.ROOK_HOME:
            rights.discard(self.ROOK_HOME[frm])
        if to in self.ROOK_HOME:                 # a rook captured on its home square
            rights.discard(self.ROOK_HOME[to])
        return frozenset(rights)


class ModernChess(ChessLike):
    uid = "modern_chess"
    name = "Modern Chess"

    WIDTH = 9
    HEIGHT = 9
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
        "M": (DIAG, KNIGHT),   # Prime Minister / Minister = bishop + knight
    }
    HEAVY = ("P", "R", "Q", "M")
    PAWN = StandardPawn(white_start=1, black_start=7)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N", "M"))
    CASTLING = ModernCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(self.WIDTH):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 7)] = (BLACK, "P")
            b[(c, 8)] = (BLACK, BACK_RANK[c])
        return b
