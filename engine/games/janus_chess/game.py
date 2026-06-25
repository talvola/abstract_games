"""Janus Chess (Janus-Schach, Werner Schöndorf, 1978), 10x8, built on the shared
chess-like core.

Adds the **Janus** "J" -- a bishop + knight compound (the same piece as
Capablanca's Archbishop / Cardinal). Each side has **two** Januses, flanking the
knights on the b- and i-files. The back rank (files a..j) is
``R J N B K Q B N J R``: note the King is on the **e-file** and the Queen on the
**f-file** (reversed from orthodox chess).

Pawns start on the 2nd / 7th ranks with the orthodox pawn (double-step, en
passant) and promote to Q/R/B/N/J on the last rank. Castling is asymmetric on
the 10-wide board: the king moves toward a rook, ending on the b- or i-file with
the rook on the adjacent c- or h-file (see :class:`JanusCastling`). White =
player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, Castling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# Files a..j (0..9) on the back rank.  King on e (4), Queen on f (5).
BACK_RANK = ["R", "J", "N", "B", "K", "Q", "B", "N", "J", "R"]


class JanusCastling(Castling):
    """Janus Chess castling on the 10-wide board.

    King starts on e1/e8 (file index 4), rooks in the corners a/j (0 and 9).
    Castling is **asymmetric** -- the king always ends on the b- or i-file and
    the rook on the adjacent c- or h-file:

    * Queenside (O-O-O): K e1->b1 (4->1, three squares), R a1->c1 (0->2)
    * Kingside  (O-O):   K e1->i1 (4->8, four  squares), R j1->h1 (9->7)

    As in orthodox chess: neither piece may have moved, every square between king
    and rook must be empty, and the king may not start in, pass through, or land
    in check. ``flag`` letters are K/Q (White) and k/q (Black).
    """

    # flag -> (king_from, king_to, rook_from, rook_to, empties_between,
    #          king_path_squares_that_must_be_safe)
    CASTLES = {
        # Kingside: king e1->i1 crosses f,g,h; rook j1->h1.
        "K": ((4, 0), (8, 0), (9, 0), (7, 0), [(5, 0), (6, 0), (7, 0), (8, 0)],
              [(4, 0), (5, 0), (6, 0), (7, 0), (8, 0)]),
        # Queenside: king e1->b1 crosses d,c; rook a1->c1.
        "Q": ((4, 0), (1, 0), (0, 0), (2, 0), [(1, 0), (2, 0), (3, 0)],
              [(4, 0), (3, 0), (2, 0), (1, 0)]),
        "k": ((4, 7), (8, 7), (9, 7), (7, 7), [(5, 7), (6, 7), (7, 7), (8, 7)],
              [(4, 7), (5, 7), (6, 7), (7, 7), (8, 7)]),
        "q": ((4, 7), (1, 7), (0, 7), (2, 7), [(1, 7), (2, 7), (3, 7)],
              [(4, 7), (3, 7), (2, 7), (1, 7)]),
    }
    BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
    ROOK_HOME = {(9, 0): "K", (0, 0): "Q", (9, 7): "k", (0, 7): "q"}
    KING_HOME = {(4, 0): WHITE, (4, 7): BLACK}

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
        # A king move is a castle iff it lands on the b-file (queenside) or the
        # i-file (kingside) -- i.e. moves more than one square horizontally.
        dx = to[0] - frm[0]
        if dx == -3:                         # e -> b (queenside)
            flag = self.BY_COLOR[player][1]
        elif dx == 4:                        # e -> i (kingside)
            flag = self.BY_COLOR[player][0]
        else:
            return None
        if to[1] != frm[1]:
            return None
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


class JanusChess(ChessLike):
    uid = "janus_chess"
    name = "Janus Chess"

    WIDTH = 10
    HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
        "J": (DIAG, KNIGHT),   # Janus = bishop + knight (an Archbishop / Cardinal)
    }
    HEAVY = ("P", "R", "Q", "J")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N", "J"))
    CASTLING = JanusCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(self.WIDTH):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b
