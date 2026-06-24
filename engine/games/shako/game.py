"""Shako (Jean-Louis Cazaux, 1990) -- a 10x10 chess variant on the shared core.

The full FIDE army plus two extra piece types per side:

* **Cannon (C)** -- the Xiangqi cannon: moves like a rook along EMPTY lines, but
  CAPTURES only by jumping over exactly one intervening piece (a "screen", of
  either colour) and landing on the enemy beyond it.
* **Elephant (E)** -- the medieval (shatranj) elephant = Ferz + Alfil: it moves
  ONE or TWO squares diagonally; the two-square move LEAPS (the intermediate
  square's occupancy is irrelevant). It is purely diagonal and always stays on
  its own colour.

Starting position (White; Black mirrors), files a..j:

    rank 1 :  C . . . . . . . . C
    rank 2 :  E R N B Q K B N R E      (Queen on e2, King on f2)
    rank 3 :  P P P P P P P P P P

Everything else is orthodox chess: pawns step one or two from their home (rank 3 /
rank 8), capture diagonally, and play en passant; pawns promote on the far rank to
Q/R/B/N/Cannon/Elephant (player's choice); the king castles "as in orthodox chess"
(with the king on the f-file: kingside K f2->h2 & rook i2->g2, queenside K f2->d2 &
rook b2->e2; Black mirrors on rank 9). Checkmate wins; stalemate, the fifty-move
rule, threefold repetition and a hard ply cap draw. White = player 0.

Implementation notes:
  * "C" is registered in PIECES with EMPTY slide/leap lists; its move-gen is custom
    (``_cannon_targets``), modelled on the xiangqi cannon screen-scan (slide like a
    rook to empties; to capture, skip exactly one screen and take the first enemy
    beyond it). ``_pseudo`` and ``attacked`` are overridden so cannon moves and
    cannon checks are generated/detected.
  * "E" (Elephant) is a plain leaper -- DIAG (Ferz) + the four (2,2) Alfil offsets --
    so the base slider/leaper machinery handles it (leaps never test the
    intermediate square, which is exactly the Alfil's leap-over rule).
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, Castling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# Elephant = Ferz (1 diagonal step) + Alfil (2 diagonal leap).
ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
ELEPHANT_LEAPS = DIAG + ALFIL

# Back rank (rank 2 / rank 9), files a..j. Queen on e (index 4), King on f (index 5).
BACK_RANK = ["E", "R", "N", "B", "Q", "K", "B", "N", "R", "E"]


class ShakoCastling(Castling):
    """Orthodox castling for the f-file king on a 10-wide board.

    King home f2 (5,0) / f9 (5,9); kingside rook i (8), queenside rook b (1).
    King moves two squares toward the rook; the rook jumps to the square the king
    crossed. Same legality as FIDE: king & rook unmoved, squares between empty, and
    the king is not in check / does not pass through or land on an attacked square.
    """

    # flag -> (king_from, king_to, rook_from, rook_to, empties_between, king_path)
    CASTLES = {
        "K": ((5, 0), (7, 0), (8, 0), (6, 0), [(6, 0), (7, 0)], [(5, 0), (6, 0), (7, 0)]),
        "Q": ((5, 0), (3, 0), (1, 0), (4, 0), [(2, 0), (3, 0), (4, 0)], [(5, 0), (4, 0), (3, 0)]),
        "k": ((5, 9), (7, 9), (8, 9), (6, 9), [(6, 9), (7, 9)], [(5, 9), (6, 9), (7, 9)]),
        "q": ((5, 9), (3, 9), (1, 9), (4, 9), [(2, 9), (3, 9), (4, 9)], [(5, 9), (4, 9), (3, 9)]),
    }
    BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
    ROOK_HOME = {(8, 0): "K", (1, 0): "Q", (8, 9): "k", (1, 9): "q"}
    KING_HOME = {(5, 0): WHITE, (5, 9): BLACK}

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
            if state.board.get(kfrom) != (player, "K") or state.board.get(rfrom) != (player, "R"):
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


class Shako(ChessLike):
    uid = "shako"
    name = "Shako"

    WIDTH = HEIGHT = 10
    PLY_CAP = 800
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
        "E": ([], ELEPHANT_LEAPS),   # Elephant = Ferz + Alfil (plain leaper)
        "C": ([], []),               # Cannon: hop move-gen is custom (see below)
    }
    HEAVY = ("P", "R", "Q", "C")
    PAWN = StandardPawn(white_start=2, black_start=7)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N", "C", "E"))
    CASTLING = ShakoCastling()

    def setup_board(self) -> dict:
        b = {}
        b[(0, 0)] = b[(9, 0)] = (WHITE, "C")     # cannons in the rank-1 corners
        b[(0, 9)] = b[(9, 9)] = (BLACK, "C")
        for i, t in enumerate(BACK_RANK):
            b[(i, 1)] = (WHITE, t)               # rank 2 back rank
            b[(i, 8)] = (BLACK, t)               # rank 9 back rank
        for c in range(10):
            b[(c, 2)] = (WHITE, "P")             # pawns on rank 3
            b[(c, 7)] = (BLACK, "P")             # pawns on rank 8
        return b

    # ---- cannon (Xiangqi-cannon) move-gen -----------------------------------
    def _cannon_targets(self, board, c, r, player):
        """Squares the cannon at (c, r) can reach: rook-slide along empty lines for
        non-captures; a capture jumps exactly one screen (any colour) and lands on
        the first enemy beyond it."""
        for dc, dr in ORTHO:
            cc, rr = c + dc, r + dr
            while self.on(cc, rr) and (cc, rr) not in board:   # non-capture slide
                yield (c, r), (cc, rr)
                cc += dc
                rr += dr
            if not self.on(cc, rr):
                continue                                       # ran off the board
            cc += dc                                           # skip the screen
            rr += dr
            while self.on(cc, rr) and (cc, rr) not in board:   # find first piece beyond
                cc += dc
                rr += dr
            if self.on(cc, rr) and board[(cc, rr)][0] != player:
                yield (c, r), (cc, rr)                          # capture beyond the screen

    def _pseudo(self, state):
        board, player = state.board, state.to_move
        for (c, r), (pl, t) in list(board.items()):
            if pl == player and t == "C":
                yield from self._cannon_targets(board, c, r, player)
        yield from super()._pseudo(state)

    # ---- attack detection (check) must include cannon captures --------------
    def attacked(self, board, c, r, by) -> bool:
        if super().attacked(board, c, r, by):
            return True
        # An enemy cannon attacks (c, r) if, along some orthogonal ray, there is
        # exactly one screen between it and (c, r): scan past the first occupied
        # square (the screen) to the next piece -- if that is an enemy cannon, it
        # attacks (c, r).
        for dc, dr in ORTHO:
            cc, rr = c + dc, r + dr
            while self.on(cc, rr) and (cc, rr) not in board:   # to the screen
                cc += dc
                rr += dr
            if not self.on(cc, rr):
                continue
            cc += dc                                           # past the screen
            rr += dr
            while self.on(cc, rr) and (cc, rr) not in board:   # to the next piece
                cc += dc
                rr += dr
            if self.on(cc, rr):
                occ = board[(cc, rr)]
                if occ[0] == by and occ[1] == "C":
                    return True
        return False

    # ---- fairy material: the base lone-minor draw logic only understands B/N,
    # so don't let it fire while a Cannon or Elephant is on the board (their
    # mating value is non-standard). The hard ply cap still guarantees
    # termination; ordinary K+minor / bare-king draws are unaffected.
    def _insufficient(self, board) -> bool:
        if any(t in ("C", "E") for (_, t) in board.values()):
            return False
        return super()._insufficient(board)
