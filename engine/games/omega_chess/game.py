"""Omega Chess (Daniel MacDonald, 1992), built on the shared chess core.

10x10 board plus four extra "wizard" squares attached diagonally beyond each
corner (104 squares total), modelled as a 12x12 embedding: core squares are
(c, r) with 1 <= c, r <= 10 and the wizard squares are (0,0), (11,0), (0,11),
(11,11). White = player 0 on ranks r=1 (pieces) / r=2 (pawns).

New pieces (both leapers, so they jump over anything in between):

* **Champion "C"** (Betza WAD) -- steps one square orthogonally, or leaps two
  squares orthogonally or diagonally. No single diagonal step.
* **Wizard "W"** (Betza FC) -- steps one square diagonally, or makes a (1,3)
  camel leap. Colour-bound, like the bishop.

Setup (files a..j = c 1..10): Champion, Rook, Knight, Bishop, Queen, King,
Bishop, Knight, Rook, Champion on the first rank, ten pawns on the second,
and a Wizard on each corner wizard square. Pawns may advance one, TWO or
THREE squares on their first move; a pawn that made a multi-step move may be
captured en passant on ANY passed square (a 3-step pawn leaves two e.p.
targets, for one move). Castling is orthodox in form: the king (f-file)
moves two squares toward either rook (b/i files) and that rook lands on the
square the king crossed. Pawns promote on the far rank of the 10x10 field
(r=10 for White, r=1 for Black) to any piece except a king (Q/C/W/R/B/N).
Checkmate wins; stalemate, threefold repetition, the 50-move rule and bare
kings draw. Pawns and rooks can never reach the wizard squares (emergent
from their movement); every other piece can.

Sources: https://www.chessvariants.com/large.dir/omega/rules.html (official
rules, used with the inventor's permission) and
https://en.wikipedia.org/wiki/Omega_Chess.
"""

from __future__ import annotations

import dataclasses

from agp.chesslike import (
    ChessLike, CState, PawnRules, PromotionRules, Castling, cell,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

CAMEL = [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]
DABBABA = [(2, 0), (-2, 0), (0, 2), (0, -2)]
ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]

BACK = ["C", "R", "N", "B", "Q", "K", "B", "N", "R", "C"]   # files a..j = c 1..10

WIZARD_SQ = ((0, 0), (11, 0), (11, 11), (0, 11))            # w1, w2, w3, w4
_WNAMES = {(0, 0): "w1", (11, 0): "w2", (11, 11): "w3", (0, 11): "w4"}
_FILES = "abcdefghij"                                       # c 1..10


class OmegaPawn(PawnRules):
    """Orthodox pawn, but the first move may be 1, 2 or 3 squares, and a
    multi-step pawn can be captured en passant on ANY passed square. The e.p.
    state value is ``((passed, ...), moved_pawn_square)`` -- a tuple of one or
    two target squares plus the square of the pawn that gets removed."""

    def pseudo(self, core, board, c, r, player, ep_targets):
        fwd = self.fwd(player)
        if core.on(c, r + fwd) and (c, r + fwd) not in board:
            yield (c, r), (c, r + fwd)
            if r == self.start(player):
                for n in (2, 3):
                    t = (c, r + n * fwd)
                    if not core.on(*t) or t in board:
                        break
                    yield (c, r), t
        for dc in (-1, 1):
            t = (c + dc, r + fwd)
            if not core.on(*t):
                continue
            occ = board.get(t)
            if (occ is not None and occ[0] != player) or (ep_targets and t in ep_targets):
                yield (c, r), t

    def attacks(self, core, board, c, r, by) -> bool:
        pr = r - self.fwd(by)
        return any(board.get((c + dc, pr)) == (by, "P") for dc in (-1, 1))

    def ep_after(self, frm, to):
        d = to[1] - frm[1]
        n = abs(d)
        if n < 2:
            return None
        step = 1 if d > 0 else -1
        passed = tuple((frm[0], frm[1] + step * i) for i in range(1, n))
        return (passed, to)


class OmegaPromotion(PromotionRules):
    """Mandatory promotion on the far rank of the 10x10 field (r=10 White,
    r=1 Black -- NOT the 12x12 embedding edge) to any piece except a king."""

    TARGETS = ("Q", "C", "W", "R", "B", "N")

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        last = (pl == WHITE and to[1] == 10) or (pl == BLACK and to[1] == 1)
        return list(self.TARGETS) if last else [None]


class OmegaCastling(Castling):
    """Orthodox-style castling on the first rank of the 10x10 field: king on
    the f-file (c=6) moves two squares toward the b- or i-file rook, which
    lands on the square the king crossed."""

    # flag: (king_from, king_to, rook_from, rook_to, must_be_empty, king_path)
    CASTLES = {
        "K": ((6, 1), (8, 1), (9, 1), (7, 1),
              [(7, 1), (8, 1)], [(6, 1), (7, 1), (8, 1)]),
        "Q": ((6, 1), (4, 1), (2, 1), (5, 1),
              [(3, 1), (4, 1), (5, 1)], [(6, 1), (5, 1), (4, 1)]),
        "k": ((6, 10), (8, 10), (9, 10), (7, 10),
              [(7, 10), (8, 10)], [(6, 10), (7, 10), (8, 10)]),
        "q": ((6, 10), (4, 10), (2, 10), (5, 10),
              [(3, 10), (4, 10), (5, 10)], [(6, 10), (5, 10), (4, 10)]),
    }
    BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
    ROOK_HOME = {(9, 1): "K", (2, 1): "Q", (9, 10): "k", (2, 10): "q"}
    KING_HOME = {(6, 1): WHITE, (6, 10): BLACK}

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
            # Unlike on the 8x8 board, Omega rooks do NOT start in the rank's
            # last square: an enemy slider on a0/j0 (behind the castling rook)
            # attacks the king's landing square only once the rook vacates.
            # So also verify king safety on the actual post-castle board.
            b2 = dict(state.board)
            del b2[kfrom], b2[rfrom]
            b2[kto] = (player, "K")
            b2[rto] = (player, "R")
            if core.in_check(b2, player):
                continue
            yield kfrom, kto

    def rook_move(self, frm, to, player):
        if abs(to[0] - frm[0]) != 2 or frm not in self.KING_HOME:
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


class OmegaChess(ChessLike):
    name = "Omega Chess"

    WIDTH = HEIGHT = 12          # embedding; only 104 cells are on the board
    PLY_CAP = 800
    PIECES = {
        "R": (ORTHO, []),
        "B": (DIAG, []),
        "Q": (ALL8, []),
        "N": ([], KNIGHT),
        "C": ([], ORTHO + DABBABA + ALFIL),   # Champion: wazir + dabbaba + alfil
        "W": ([], DIAG + CAMEL),              # Wizard: ferz + camel (colour-bound)
        "K": ([], ALL8),
    }
    # Many small-material mates exist here (2N, 2C, B+W, ...) -- only bare
    # kings auto-draw; everything else runs into the 50-move rule instead.
    HEAVY = ("P", "R", "Q", "B", "N", "C", "W")
    PIECE_VALUES = {"P": 1.0, "N": 3.0, "B": 3.5, "W": 3.5, "C": 4.0,
                    "R": 5.0, "Q": 9.5, "K": 0.0}
    PAWN = OmegaPawn(white_start=2, black_start=9)
    PROMOTION = OmegaPromotion()
    CASTLING = OmegaCastling()

    CELLS = tuple((c, r) for r in range(1, 11) for c in range(1, 11)) + WIZARD_SQ
    _CELLSET = frozenset(CELLS)

    # ---- geometry -----------------------------------------------------------
    def on(self, c, r) -> bool:
        return (c, r) in self._CELLSET

    def setup_board(self) -> dict:
        b = {}
        b[(0, 0)] = b[(11, 0)] = (WHITE, "W")
        b[(0, 11)] = b[(11, 11)] = (BLACK, "W")
        for i, t in enumerate(BACK):
            b[(i + 1, 1)] = (WHITE, t)
            b[(i + 1, 10)] = (BLACK, t)
        for c in range(1, 11):
            b[(c, 2)] = (WHITE, "P")
            b[(c, 9)] = (BLACK, "P")
        return b

    # ---- promotion happens on r=10/r=1, not the 12x12 edge -------------------
    def _apply_board(self, board, frm, to, ep):
        b = dict(board)
        pl, t = b.pop(frm)
        if t == "P" and ep is not None and to in ep[0] and to not in board:
            b.pop(ep[1], None)
        if t == "P" and ((pl == WHITE and to[1] == 10) or (pl == BLACK and to[1] == 1)):
            t = self.PROMOTION.safety_piece()
        b[to] = (pl, t)
        return b

    # ---- apply (multi-target e.p.; otherwise mirrors the base) ---------------
    def apply_move(self, state, move, rng=None):
        promo = None
        if "=" in move:
            move, promo = move.split("=")
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)

        capture = to in state.board
        ep_new = None
        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
        elif t == "P":
            if state.ep is not None and to in state.ep[0] and to not in state.board:
                b.pop(state.ep[1], None)
                capture = True
            else:
                ep_new = self.PAWN.ep_after(frm, to)

        if t == "P" and promo:
            t = promo
        b[to] = (pl, t)

        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        reset = capture or state.board[frm][1] == "P"
        key = self._poskey(b, 1 - pl, castling, ep_new)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps)

    # ---- (de)serialize: ep may hold two target squares ------------------------
    def serialize(self, state) -> dict:
        d = ChessLike.serialize(self, dataclasses.replace(state, ep=None))
        if state.ep is not None:
            targets, cap = state.ep
            d["ep"] = (";".join(f"{c},{r}" for c, r in targets)
                       + "|" + f"{cap[0]},{cap[1]}")
        return d

    def deserialize(self, d: dict):
        d2 = dict(d)
        ep_s = d2.pop("ep", None)
        d2["ep"] = None
        st = ChessLike.deserialize(self, d2)
        if ep_s:
            tpart, cpart = ep_s.split("|")
            st.ep = (tuple(cell(x) for x in tpart.split(";")), cell(cpart))
        return st

    # ---- presentation ---------------------------------------------------------
    @staticmethod
    def _alg(sq) -> str:
        if sq in _WNAMES:
            return _WNAMES[sq]
        return f"{_FILES[sq[0] - 1]}{sq[1] - 1}"   # official notation: ranks 0-9

    def describe_move(self, state, move) -> str:
        raw, promo = (move.split("=") + [None])[:2]
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board.get(frm, (None, "?"))
        if t == "K" and self.CASTLING.rook_move(frm, to, pl) is not None:
            return "O-O" if to[0] > frm[0] else "O-O-O"
        capture = to in state.board or (
            t == "P" and state.ep is not None and to in state.ep[0])
        text = f"{t}{self._alg(frm)}{'x' if capture else '-'}{self._alg(to)}"
        return text + (f"={promo}" if promo else "")

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        cells = []
        tints = {}
        for (c, r) in self.CELLS:
            y = self.HEIGHT - 1 - r          # flip: White (r=1) at the bottom
            cells.append({"id": f"{c},{r}",
                          "points": [[c, y], [c + 1, y], [c + 1, y + 1], [c, y + 1]]})
            if (c, r) in _WNAMES:
                tints[f"{c},{r}"] = "#3a2e45"          # wizard squares (accent)
            elif (c + r) % 2 == 1:
                tints[f"{c},{r}"] = "#332e27"          # dark squares
            else:
                tints[f"{c},{r}"] = "#2a2620"          # light squares
        spec["board"] = {"type": "polygons", "cells": cells, "tints": tints}
        return spec
