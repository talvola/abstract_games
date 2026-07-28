"""Brusky's Hexagonal Chess (Yakov Brusky, USSR, 1966).

Chess on an irregular hexagonal board of 84 cells with HORIZONTAL ranks and
slanting files -- the other orientation family from Gliński's (whose files are
vertical).  Each side has the orthodox army plus one extra bishop (three, one
per hex colour) and one extra pawn, and the two kings sit on OPPOSITE wings so
that the position has 180-degree rotational symmetry.

Board & coordinates
-------------------
Brusky's own notation names a cell by a *left-leaning* file letter a..l and a
horizontal rank 1..8::

    a1-a5   b1-b6   c1-c7   d1-d8 ... i1-i8   j2-j8   k3-k8   l4-l8   = 84 cells

Internally a cell is an axial hex coordinate ``"q,r"`` with::

    q = file index (a=0 .. l=11)        r = -rank (rank 1 = -1 .. rank 8 = -8)

so a cell exists iff ``0 <= q <= 11``, ``-8 <= r <= -1`` and ``-5 <= q+r <= 7``
(``q+r`` is the index of the *right*-leaning file, which is why the two cut
corners are exactly the ``q+r < -5`` and ``q+r > 7`` triangles).  The web
renderer draws pointy-top hexes at ``x = sqrt(3)(q + r/2), y = 1.5r``, so
constant ``r`` is a horizontal row and rank 1 (r = -1) sits at the bottom for
White -- the board's natural orientation.

Because the axial frame is just Gliński's rotated, the direction TABLES are
identical to the rest of the family's, so they (and the sliders, leapers,
check/mate, the draw counters, serialisation, rendering and the MCTS heuristic)
come from ``agp.hexchesslike``; only which vector is "forward" for a pawn
differs -- a Brusky pawn has TWO forward orthogonals.

Rules implemented (chessvariants.com/rules/bruskyshexagonalchess, which follows
Pritchard's *Encyclopedia of Chess Variants*; see rules.md)
------------------------------------------------------------------------------
* Rook 6 orthogonals, bishop 6 diagonals (colourbound; three bishops on the
  three colours), queen = both, knight = the 12-target hex leap, king one step
  in any of the 12 directions -- exactly as in Gliński's.
* Castling: the king moves TWO cells toward the rook on the king's side
  (O-O) or THREE toward the rook on the queen's side (O-O-O); the rook hops to
  the cell on the king's far side.  All orthodox castling conditions apply.
* Pawn (the variant's distinctive part):
  - two orthogonally forward directions;
  - a double step from the pawn's own starting rank may not change direction;
  - an ENEMY piece adjacent in one forward direction blocks the other forward
    direction too (a friendly piece blocks only its own direction);
  - captures on the two slanted forward diagonals always, and additionally on
    the fully vertical forward diagonal while the pawn stands on its starting
    rank;
  - en passant; promotion to Q/R/B/N on the far rank.
* Stalemate is a DRAW and the rest of orthodox chess applies (checkmate, 50-move
  rule, threefold repetition, bare kings).  A hard ply cap is a defensive
  backstop only -- see PLY_CAP.

Move strings: "q1,r1>q2,r2" plus an "=Q/=R/=B/=N" suffix on promotions;
castling is written as the king's two- or three-cell move.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# The names re-exported / defined here (BState, WHITE/BLACK, FILES, CELLS,
# ORTHO/DIAG/KNIGHT, on_board, cell_name, name_to_cell, HOME_RANK, pawn_caps,
# PLY_CAP, _cell, _poskey, _attacked, _king_cell, _in_check) are this module's
# PUBLIC SURFACE: ``selftest.py`` imports them and the selftest is the
# regression net for this refactor, so it is deliberately not rewritten.
from agp.hexchesslike import (BLACK, DIAG, KNIGHT, ORTHO, WHITE,  # noqa: F401
                              HexChessLike, HState, cell_str, parse_cell)

NAMES = {WHITE: "White", BLACK: "Black"}
FILES = "abcdefghijkl"          # 12 left-leaning files; Brusky's notation uses "j"

# The 50-move rule always fires first: a pawn advances at most 6 ranks and there
# are 10 pawns a side (<= 120 pawn moves) and at most 36 capturable units, so a
# game contains at most 156 irreversible plies and therefore at most
# 156 + 157*100 = 15,856 plies before "halfmove >= 100" ends it.  PLY_CAP is set
# above that bound, so it is dead code that can only fire if a rule above it is
# broken -- it is NEVER outcome-load-bearing.
PLY_CAP = 20000

# ORTHO / DIAG / KNIGHT come from the shared core (identical in axial space for
# the whole hex-chess family).  Here the orthogonals read NW, NE, E, SE, SW, W;
# the diagonals are the sums of adjacent orthogonals, with (1,-2) "straight up
# the board" and (-1,2) straight down.

# Pawns: two forward orthogonals, two slanted forward diagonals, and the fully
# vertical forward diagonal (a capture direction only from the starting rank).
PAWN_FWD = {WHITE: [(0, -1), (1, -1)], BLACK: [(0, 1), (-1, 1)]}
PAWN_SLANT = {WHITE: [(-1, -1), (2, -1)], BLACK: [(1, 1), (-2, 1)]}
PAWN_VERT = {WHITE: (1, -2), BLACK: (-1, 2)}
HOME_RANK = {WHITE: -2, BLACK: -7}      # r of the pawns' starting rank
PROMO_RANK = {WHITE: -8, BLACK: -1}     # r of the far rank
PROMO_PIECES = ("Q", "R", "B", "N")

# --- castling (king's side = the rook next to the king; queen's side = the
# rook beyond the queen).  Each entry: king from/to, rook from/to, the cells
# between king and rook that must be empty, and the king's transit path that
# must not be attacked. -------------------------------------------------------
CASTLES = {
    "K": {"player": WHITE, "kfrom": (5, -1), "kto": (7, -1),
          "rfrom": (8, -1), "rto": (6, -1),
          "empty": [(6, -1), (7, -1)],
          "path": [(5, -1), (6, -1), (7, -1)], "name": "O-O"},
    "Q": {"player": WHITE, "kfrom": (5, -1), "kto": (2, -1),
          "rfrom": (0, -1), "rto": (3, -1),
          "empty": [(1, -1), (2, -1), (3, -1), (4, -1)],
          "path": [(5, -1), (4, -1), (3, -1), (2, -1)], "name": "O-O-O"},
    "k": {"player": BLACK, "kfrom": (6, -8), "kto": (4, -8),
          "rfrom": (3, -8), "rto": (5, -8),
          "empty": [(4, -8), (5, -8)],
          "path": [(6, -8), (5, -8), (4, -8)], "name": "O-O"},
    "q": {"player": BLACK, "kfrom": (6, -8), "kto": (9, -8),
          "rfrom": (11, -8), "rto": (8, -8),
          "empty": [(7, -8), (8, -8), (9, -8), (10, -8)],
          "path": [(6, -8), (7, -8), (8, -8), (9, -8)], "name": "O-O-O"},
}
FLAGS_BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
ROOK_HOME = {c["rfrom"]: f for f, c in CASTLES.items()}
KING_HOME = {(5, -1): WHITE, (6, -8): BLACK}
ALL_RIGHTS = frozenset("KQkq")


def on_board(q: int, r: int) -> bool:
    return 0 <= q <= 11 and -8 <= r <= -1 and -5 <= q + r <= 7


CELLS = frozenset((q, r) for q in range(12) for r in range(-8, 0) if on_board(q, r))


def cell_name(cell) -> str:
    """Axial (q,r) -> Brusky notation, e.g. (2,-4) -> 'c4'."""
    q, r = cell
    return f"{FILES[q]}{-r}"


def name_to_cell(name: str):
    """Brusky notation -> axial, e.g. 'c4' -> (2,-4)."""
    return (FILES.index(name[0]), -int(name[1:]))


def _cell(sstr: str):
    return parse_cell(sstr)


def _setup_board() -> dict:
    """White R a1 N b1 B c1 Q d1 B e1 K f1 B g1 N h1 R i1, pawns a2-j2;
    Black the 180-degree rotation: R d8 N e8 B f8 K g8 B h8 Q i8 B j8 N k8 R l8,
    pawns c7-l7.  (The kings really do stand on opposite wings.)"""
    b = {}
    back = "RNBQBKBNR"
    for i, t in enumerate(back):
        b[(i, -1)] = (WHITE, t)                 # a1 .. i1
        b[(11 - i, -8)] = (BLACK, t)            # l8 .. d8
    for q in range(0, 10):
        b[(q, -2)] = (WHITE, "P")               # a2 .. j2
    for q in range(2, 12):
        b[(q, -7)] = (BLACK, "P")               # c7 .. l7
    return b


def pawn_caps(player: int, cell) -> list:
    """The directions this pawn captures in: the two slants always, plus the
    fully vertical diagonal while it stands on its own starting rank."""
    caps = list(PAWN_SLANT[player])
    if cell[1] == HOME_RANK[player]:
        caps.append(PAWN_VERT[player])
    return caps


@dataclass
class BState(HState):
    """The shared hex-chess state with Brusky's own defaults.

    ``castling`` is a set of "KQkq" flag characters and ``ep`` is
    ``(target_cell, pawn_cell)`` -- the ORDER the shipped package used, kept
    because ``selftest.py`` reads ``s.ep[0]``/``s.ep[1]`` and because the
    serialized form goes to the production DB.
    """
    board: dict = field(default_factory=_setup_board)  # (q,r) -> (owner, letter)
    castling: frozenset = ALL_RIGHTS


def _poskey(board: dict, to_move: int, castling, ep) -> str:
    """Repetition key.  Kept verbatim (rather than using the core's) so that a
    match already stored in the DB keeps counting its own repetitions."""
    items = sorted((q, r, o, t) for (q, r), (o, t) in board.items())
    ep_s = f"{ep[0][0]},{ep[0][1]}" if ep else "-"
    return (f"{to_move}|{''.join(sorted(castling))}|{ep_s}|"
            + ";".join(f"{q},{r},{o},{t}" for q, r, o, t in items))


def _ep_right(letter: str, player: int, frm, to):
    """The en-passant right created by a move, or None.

    It must be recognised by the DIRECTION of the step, not by |dr| == 2: the
    vertical-diagonal capture (1,-2)/(-1,2) also spans two ranks but is not a
    double step.  The right records both the skipped cell (the capture target)
    and the double-stepper's cell (the pawn to remove) -- with two forward
    directions the victim is not at a fixed offset from the target."""
    if letter != "P":
        return None
    d = (to[0] - frm[0], to[1] - frm[1])
    for dq, dr in PAWN_FWD[player]:
        if d == (2 * dq, 2 * dr):
            return ((frm[0] + dq, frm[1] + dr), to)
    return None


def _castle_flag(board: dict, frm, to):
    """If this king move is a castling, return its flag, else None."""
    piece = board.get(frm)
    if piece is None or piece[1] != "K":
        return None
    if frm[1] != to[1] or abs(to[0] - frm[0]) < 2:
        return None
    for flag in FLAGS_BY_COLOR[piece[0]]:
        c = CASTLES[flag]
        if c["kfrom"] == frm and c["kto"] == to:
            return flag
    return None


class BruskyChess(HexChessLike):
    CELLS = CELLS
    FILES = FILES
    NAME_OF = NAMES
    PLY_CAP = PLY_CAP
    STATE = BState
    # STALEMATE_SCORED stays False: stalemate is an ordinary draw.

    # ---- notation ---------------------------------------------------------
    def cell_name(self, cell) -> str:
        return cell_name(cell)

    # ---- setup ------------------------------------------------------------
    def setup_board(self) -> dict:
        return _setup_board()

    def initial_castling(self) -> frozenset:
        return ALL_RIGHTS

    # ---- pawns ------------------------------------------------------------
    def is_promo(self, player: int, cell) -> bool:
        return cell[1] == PROMO_RANK[player]

    def pawn_attackers(self, player: int, cell):
        """Reverse of ``pawn_caps``: the cells a pawn of `player` attacks `cell`
        from.  The vertical diagonal counts only when the pawn would be standing
        on its OWN starting rank, so the source cell -- not the target -- is what
        gates it.  Getting this wrong changes check detection without changing
        move generation."""
        q, r = cell
        srcs = [(q - dq, r - dr) for dq, dr in PAWN_SLANT[player]]
        dq, dr = PAWN_VERT[player]
        src = (q - dq, r - dr)
        if src[1] == HOME_RANK[player]:
            srcs.append(src)
        return srcs

    def pawn_moves(self, s, cell, out) -> None:
        board, me = s.board, s.to_move
        q, r = cell
        # --- non-capturing advances.  An ENEMY piece adjacent in EITHER forward
        # direction blocks BOTH; a friendly one blocks only its own direction.
        blocked = False
        for dq, dr in PAWN_FWD[me]:
            occ = board.get((q + dq, r + dr))
            if occ is not None and occ[0] != me:
                blocked = True
                break
        if not blocked:
            home = (r == HOME_RANK[me])
            for dq, dr in PAWN_FWD[me]:
                one = (q + dq, r + dr)
                if one not in CELLS or one in board:
                    continue
                if self.is_promo(me, one):
                    for pc in PROMO_PIECES:
                        out.append((cell, one, pc, None, None))
                else:
                    out.append((cell, one, None, None, None))
                if home:                       # double step, same direction
                    two = (q + 2 * dq, r + 2 * dr)
                    if two in CELLS and two not in board:
                        out.append((cell, two, None, None, None))
        # --- captures (and en passant)
        for dq, dr in pawn_caps(me, cell):
            tgt = (q + dq, r + dr)
            if tgt not in CELLS:
                continue
            occ = board.get(tgt)
            if occ is not None:
                if occ[0] != me:
                    if self.is_promo(me, tgt):
                        for pc in PROMO_PIECES:
                            out.append((cell, tgt, pc, None, None))
                    else:
                        out.append((cell, tgt, None, None, None))
            elif s.ep is not None and tgt == s.ep[0]:
                # s.ep = (target, victim); the victim cell is carried explicitly
                # because with two forward directions BOTH cells behind the
                # target can hold an enemy pawn.
                out.append((cell, tgt, None, s.ep[1], None))

    def ep_after(self, s, frm, to, piece: str):
        return _ep_right(piece, s.to_move, frm, to)

    # ---- castling ---------------------------------------------------------
    def castle_moves(self, s, out) -> None:
        me = s.to_move
        board = s.board
        if self.in_check(board, me):
            return
        for flag in FLAGS_BY_COLOR[me]:
            if flag not in s.castling:
                continue
            c = CASTLES[flag]
            if board.get(c["kfrom"]) != (me, "K") or board.get(c["rfrom"]) != (me, "R"):
                continue
            if any(x in board for x in c["empty"]):
                continue
            if any(self.attacked(board, x, 1 - me) for x in c["path"]):
                continue
            out.append((c["kfrom"], c["kto"], None, None, (c["rfrom"], c["rto"])))

    def update_castling(self, rights: frozenset, frm, to, board,
                        new_board=None) -> frozenset:
        pl, t = board[frm]
        out = set(rights)
        if t == "K" and frm in KING_HOME:
            out -= set(FLAGS_BY_COLOR[pl])
        if frm in ROOK_HOME:
            out.discard(ROOK_HOME[frm])
        if to in ROOK_HOME:                      # a rook captured on its home cell
            out.discard(ROOK_HOME[to])
        return frozenset(out)

    # ---- draws -------------------------------------------------------------
    def _draw_reason(self, s) -> Optional[str]:
        """The shared counters, plus Brusky's one material rule.

        Bare kings is the ONLY insufficient-material case: unlike orthodox
        chess, K+B vs K and K+N vs K are not dead positions here (a corner has
        just five king-neighbours, so a lone minor really can mate -- e.g.
        Kc5+Nb3 vs Ka5#), so auto-drawing them would be a rule error.

        It needs no "a decisive result outranks the draw" guard of its own (the
        guard the core applies to the counters): with only the two kings left
        neither checkmate nor stalemate is reachable.
        """
        reason = super()._draw_reason(s)
        if reason is not None:
            return reason
        if len(s.board) == 2:                  # bare kings: mate is impossible
            return "insufficient material"
        return None

    # ---- applying a move ----------------------------------------------------
    def apply_move(self, s, move: str, rng=None):
        """The core's move application, with Brusky's repetition-table policy.

        The core clears ``reps`` when a castling RIGHT is lost as well as on an
        irreversible move; this package never did, and the serialized ``reps``
        goes to the production DB, so the stale entries are kept.  They are
        inert either way: their positions carry the old rights, so they can
        never recur and can never be the entry that reaches three.
        """
        ns = super().apply_move(s, move, rng)
        if ns.halfmove and ns.castling != s.castling:
            merged = dict(s.reps)
            for k, v in ns.reps.items():
                merged[k] = merged.get(k, 0) + v
            ns.reps = merged
        return ns

    def _apply_flagged(self, board: dict, frm, to, promo, ep_victim, mover: int) -> dict:
        """Apply a move whose castling is INFERRED from the king's step (used by
        ``describe_move``, which is handed a bare move string).  Tolerant of a
        missing rook, as the shipped version was."""
        flag = _castle_flag(board, frm, to)
        nb = dict(board)
        owner, t = nb.pop(frm)
        if ep_victim is not None:
            nb.pop(ep_victim, None)
        nb[to] = (owner, promo if promo else t)
        if flag is not None:
            c = CASTLES[flag]
            nb.pop(c["rfrom"], None)
            nb[c["rto"]] = (mover, "R")
        return nb

    # ---- state encoding (DO NOT CHANGE: async matches are stored serialized) --
    def poskey(self, board: dict, to_move: int, ep, castling) -> str:
        return _poskey(board, to_move, castling, ep)

    def ep_to_json(self, ep):
        return None if ep is None else [cell_str(ep[0]), cell_str(ep[1])]

    def ep_from_json(self, v):
        return (parse_cell(v[0]), parse_cell(v[1])) if v else None

    def castling_to_json(self, rights):
        return "".join(sorted(rights))

    def castling_from_json(self, v):
        return frozenset(v or "")

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s, move: str) -> str:
        promo = None
        body = move
        if "=" in move:
            body, promo = move.split("=")
        frm_s, to_s = body.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        piece = s.board.get(frm)
        flag = _castle_flag(s.board, frm, to)
        is_ep = (piece is not None and piece[1] == "P" and s.ep is not None
                 and to == s.ep[0] and to not in s.board)
        if flag is not None:
            out = CASTLES[flag]["name"]
        else:
            letter = "" if piece is None or piece[1] == "P" else piece[1]
            cap = "x" if (to in s.board or is_ep) else "-"
            out = f"{letter}{cell_name(frm)}{cap}{cell_name(to)}"
            if promo:
                out += f"={promo}"
            if is_ep:
                out += " e.p."
        if piece is not None:
            victim = s.ep[1] if is_ep else None
            nb = self._apply_flagged(s.board, frm, to, promo, victim, piece[0])
            foe = 1 - piece[0]
            if self.in_check(nb, foe):
                nxt = BState(board=nb, to_move=foe,
                             ep=_ep_right(piece[1], piece[0], frm, to),
                             castling=self.update_castling(s.castling, frm, to,
                                                           s.board))
                out += "#" if not self._legal(nxt) else "+"
        return out

    def board_spec(self, s) -> dict:
        # The three hex colours (the bishop colour classes): (q - r) mod 3.
        shades = {0: "#e8ab6f", 1: "#ffce9e", 2: "#d18b47"}   # mid, light, dark
        cells = sorted(CELLS, key=lambda c: (-c[1], c[0]))
        return {
            "type": "hex",
            "cells": [f"{q},{r}" for q, r in cells],
            "tints": {f"{q},{r}": shades[(q - r) % 3] for q, r in cells},
        }


# --- module-level helpers kept for selftest.py / callers ---------------------
_G = BruskyChess()


def _attacked(board: dict, cell, by: int) -> bool:
    """Is `cell` attacked by any piece of player `by`?  (Pawn attacks use the
    same starting-rank rule as pawn captures.)"""
    return _G.attacked(board, cell, by)


def _king_cell(board: dict, player: int):
    return _G.king_cell(board, player)


def _in_check(board: dict, player: int) -> bool:
    return _G.in_check(board, player)
