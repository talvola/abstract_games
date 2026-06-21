"""Capablanca Chess (José Raúl Capablanca, c. 1920), 10x8, built on the shared
chess-like core.

Adds two compound pieces: the **Archbishop** (a.k.a. Cardinal) "A" = bishop +
knight, and the **Chancellor** (a.k.a. Marshall / Empress) "C" = rook + knight.
The back rank (files a..j) is ``R N A B Q K B C N R``: the Archbishop sits next
to the queen's bishop and the Chancellor next to the king's bishop. Pawns start
on the 2nd / 7th ranks with the orthodox pawn (double-step, en passant) and
promote to Q/R/B/N/A/C on the last rank. Castling is Capablanca's three-square
king move toward a rook (see :class:`CapablancaCastling`). White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, Castling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# Files a..j (0..9) on the back rank.
BACK_RANK = ["R", "N", "A", "B", "Q", "K", "B", "C", "N", "R"]


class CapablancaCastling(Castling):
    """Capablanca castling on the 10-wide board.

    King starts on f1/f8 (file index 5), rooks in the corners a/j (0 and 9).
    The king moves **three** squares toward the chosen rook and the rook jumps
    to the square the king passed over:

    * Kingside  (O-O):   K f1->i1 (5->8), R j1->h1 (9->7)
    * Queenside (O-O-O): K f1->c1 (5->2), R a1->d1 (0->3)

    As in orthodox chess: neither piece may have moved, the squares between king
    and rook must be empty, and the king may not start in, pass through, or land
    in check. ``flag`` letters are K/Q (White) and k/q (Black).
    """

    # flag -> (king_from, king_to, rook_from, rook_to, empties_between,
    #          king_path_squares_that_must_be_safe)
    CASTLES = {
        "K": ((5, 0), (8, 0), (9, 0), (7, 0), [(6, 0), (7, 0), (8, 0)],
              [(5, 0), (6, 0), (7, 0), (8, 0)]),
        "Q": ((5, 0), (2, 0), (0, 0), (3, 0), [(1, 0), (2, 0), (3, 0), (4, 0)],
              [(5, 0), (4, 0), (3, 0), (2, 0)]),
        "k": ((5, 7), (8, 7), (9, 7), (7, 7), [(6, 7), (7, 7), (8, 7)],
              [(5, 7), (6, 7), (7, 7), (8, 7)]),
        "q": ((5, 7), (2, 7), (0, 7), (3, 7), [(1, 7), (2, 7), (3, 7), (4, 7)],
              [(5, 7), (4, 7), (3, 7), (2, 7)]),
    }
    BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
    ROOK_HOME = {(9, 0): "K", (0, 0): "Q", (9, 7): "k", (0, 7): "q"}
    KING_HOME = {(5, 0): WHITE, (5, 7): BLACK}

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
        if abs(to[0] - frm[0]) != 3:
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


class CapablancaChess(ChessLike):
    uid = "capablanca_chess"
    name = "Capablanca Chess"

    WIDTH = 10
    HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
        "A": (DIAG, KNIGHT),   # Archbishop / Cardinal = bishop + knight
        "C": (ORTHO, KNIGHT),  # Chancellor / Marshall = rook + knight
    }
    HEAVY = ("P", "R", "Q", "A", "C")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N", "A", "C"))
    CASTLING = CapablancaCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(self.WIDTH):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b
