"""Crazy 38's — Ben Good (1998), an entry in Hans Bodlaender's "38 square" challenge.

A chess/shogi hybrid played on a 38-square knotted board with drops.

Board / notation
----------------
The board is drawn as a Celtic knot of diamonds. Rows are lettered a-h down one
side and numbered 1-8 up the other; each square is a (letter, number) pair and
only 38 of the 64 combinations exist. Internally a cell is the tuple
``(n, l)`` with n = number (1-8, the render column) and l = letter index
(1 = a ... 8 = h, the render row; a is at the top, h at the bottom).

The diamonds tile a 45-degree-rotated square lattice, so all pieces move by
ordinary chess geometry ON THE (letter, number) GRID:

* ORTHOGONAL neighbours (rook / king / pawn / silver / gold steps) are the
  next EXISTING cell along the file (same letter, vary number) or rank (same
  number, vary letter). The six curved "tip" cells (a8, a3, f8, c1, h6, h1)
  bridge the six gaps in the knot, so e.g. a6 and a8 are orthogonally adjacent
  even though a7 does not exist — this is the "loop-effect" the rook exploits.
* DIAGONAL neighbours (bishop slides, silver/gold/king diagonal steps) are the
  direct (l+-1, n+-1) cells (no bridging).

See rules.md for the full ruleset as implemented.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
PLY_CAP = 300               # hard draw cap (drops recycle material -> guarantee termination)
REP_LIMIT = 4              # 4-fold repetition -> draw (shogi sennichite)

LETTERS = "abcdefgh"

# Existing numbers per letter (l = 1..8). Transcribed cell-by-cell from the CVP
# board diagram (38.dir/crazy/38squares.notation.gif).
FILE_NUMS = {
    1: [3, 5, 6, 8],              # a3 a5 a6 a8
    2: [5, 6],                    # b5 b6
    3: [1, 3, 4, 5, 6, 7, 8],     # c1 c3 c4 c5 c6 c7 c8
    4: [3, 4, 5, 6, 7, 8],        # d3 d4 d5 d6 d7 d8
    5: [1, 2, 3, 4, 5, 6],        # e1 e2 e3 e4 e5 e6
    6: [1, 2, 3, 4, 5, 6, 8],     # f1 f2 f3 f4 f5 f6 f8
    7: [3, 4],                    # g3 g4
    8: [1, 3, 4, 6],              # h1 h3 h4 h6
}
CELLS = frozenset((n, l) for l, nums in FILE_NUMS.items() for n in nums)
assert len(CELLS) == 38, len(CELLS)

# Ranks: letters present for each number.
RANK_LETTERS = {n: sorted(l for l in range(1, 9) if n in FILE_NUMS[l]) for n in range(1, 9)}


def _next(seq, cur, up):
    """Next value in sorted list `seq` strictly above (up) / below cur, or None."""
    cand = [v for v in seq if (v > cur if up else v < cur)]
    if not cand:
        return None
    return min(cand) if up else max(cand)


# Orthogonal neighbour maps (bridged along file / rank).
FILE_UP, FILE_DOWN, RANK_RIGHT, RANK_LEFT = {}, {}, {}, {}
for (n, l) in CELLS:
    nu = _next(FILE_NUMS[l], n, True)
    nd = _next(FILE_NUMS[l], n, False)
    lr = _next(RANK_LETTERS[n], l, True)
    ll = _next(RANK_LETTERS[n], l, False)
    FILE_UP[(n, l)] = (nu, l) if nu else None
    FILE_DOWN[(n, l)] = (nd, l) if nd else None
    RANK_RIGHT[(n, l)] = (n, lr) if lr else None
    RANK_LEFT[(n, l)] = (n, ll) if ll else None

ORTH_MAPS = (FILE_UP, FILE_DOWN, RANK_RIGHT, RANK_LEFT)

# Diagonal steps as (dl, dn); silver/gold pick subsets, king/bishop use all.
DIAG_SIDE = [(1, 1), (-1, -1)]     # silver's two diagonals
DIAG_FRONT = [(1, -1), (-1, 1)]    # gold's two diagonals (ahead/behind)
DIAG_ALL = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

# Home / promotion squares.
HOME = {WHITE: (1, 8), BLACK: (8, 1)}        # h1 (White king start) / a8 (Black king start)
def enemy_home(o):
    return HOME[1 - o]

VALUE = {"P": 1, "S": 3, "G": 4, "N": 3, "B": 4, "R": 5, "Q": 9, "K": 0}
DROP_TYPES = ("R", "B", "G", "S", "N", "P")


def _diag(n, l, dl, dn):
    c = (n + dn, l + dl)
    return c if c in CELLS else None


@dataclass
class CState:
    board: dict = field(default_factory=dict)   # (n,l) -> (owner, ptype)
    hands: dict = field(default_factory=lambda: {WHITE: {}, BLACK: {}})
    to_move: int = WHITE
    winner: Optional[int] = None                # 0/1 winner, else None
    draw: bool = False
    reps: dict = field(default_factory=dict)    # poskey -> count
    ply: int = 0
    last: list = field(default_factory=list)    # cell strings for highlight


def _cid(c):
    return f"{c[0]},{c[1]}"


def _label(c):
    return f"{LETTERS[c[1] - 1]}{c[0]}"


# --------------------------------------------------------------------------- #
#  Pseudo-move generation (geometry only; no check filtering)
# --------------------------------------------------------------------------- #
def _pawn_targets(n, l, owner):
    if owner == WHITE:                      # forward = toward a8 = +number / -letter
        cands = [FILE_UP.get((n, l)), RANK_LEFT.get((n, l))]
    else:                                   # Black forward = toward h1 = -number / +letter
        cands = [FILE_DOWN.get((n, l)), RANK_RIGHT.get((n, l))]
    return [c for c in cands if c]


def _step_targets(n, l, orth, diags):
    out = []
    if orth:
        for m in ORTH_MAPS:
            c = m.get((n, l))
            if c:
                out.append(c)
    for (dl, dn) in diags:
        c = _diag(n, l, dl, dn)
        if c:
            out.append(c)
    return out


def _slide(board, start, stepmap, owner):
    """Follow a neighbour map (dict cell->cell) from start; yield reachable cells."""
    out = []
    cur = stepmap.get(start)
    while cur is not None:
        occ = board.get(cur)
        if occ is None:
            out.append(cur)
            cur = stepmap.get(cur)
        else:
            if occ[0] != owner:
                out.append(cur)     # capture
            break
    return out


def _diag_step_map(dl, dn):
    return {c: _diag(c[0], c[1], dl, dn) for c in CELLS}


DIAG_MAPS = {(dl, dn): _diag_step_map(dl, dn) for (dl, dn) in DIAG_ALL}


# --------------------------------------------------------------------------- #
#  Geometry-derived Knight table
# --------------------------------------------------------------------------- #
# The Knight is "one square diagonally, then one orthogonally away" — an L of 2
# steps along one direction and 1 along the perpendicular. On a flat board that
# is the ordinary (+-1,+-2)/(+-2,+-1) leap, but on this KNOTTED board the L must
# follow the board's CURVED files/ranks (the six tip-bridged gaps), so a raw
# lattice offset is wrong near the tips (it invents non-knight bridge moves and
# misses the over-the-tip leaps). We therefore derive the target set for every
# cell from the geometry: two steps along one curved orthogonal line + one step
# along the crossing line, taken in EVERY interleaving (short step first / middle
# / last, since order changes the landing cell around a curve), deduped, origin
# excluded. This is validated below (selftest) against the two knight.gif ground
# truths — a8 -> {b5,c6,d7} and f3 -> {d4,e1,e5,h4,h1} — reproduced exactly, and
# the resulting relation is symmetric (x attacks y iff y attacks x).
# The six "tip" cells — each is joined to the rest of the board ONLY by its two
# curved bridge-caps (one file, one rank). A knight leap must never *pass
# through* a tip as an intermediate square: routing through a tip walks around
# the loop and overshoots to a cell ~2x the true leap distance (e.g. the naive
# a5->a6->a8->c8 lands on the far side of the top loop, which is not a knight's
# move — the piece diagram shows the a8 knight reaching only its three short
# neighbours). Landing ON a tip as the destination is fine (e.g. f3->h1).
TIP_CELLS = frozenset({(8, 1), (3, 1), (8, 6), (1, 3), (6, 8), (1, 8)})  # a8 a3 f8 c1 h6 h1


def _build_knight_table():
    table = {}
    for c in CELLS:
        res = set()
        for long_map in (FILE_UP, FILE_DOWN, RANK_LEFT, RANK_RIGHT):
            cross = (RANK_LEFT, RANK_RIGHT) if long_map in (FILE_UP, FILE_DOWN) \
                else (FILE_UP, FILE_DOWN)
            for short_map in cross:
                for seq in ((short_map, long_map, long_map),
                            (long_map, short_map, long_map),
                            (long_map, long_map, short_map)):
                    cur = c
                    path = []
                    for m in seq:
                        cur = m.get(cur)
                        if cur is None:
                            break
                        path.append(cur)
                    if cur is None or cur == c:
                        continue
                    if any(step in TIP_CELLS for step in path[:2]):  # tip as intermediate
                        continue
                    res.add(cur)
        table[c] = frozenset(res)
    return table


KNIGHT_TABLE = _build_knight_table()


def _piece_moves(board, cell, owner, ptype):
    """Return list of (to_cell, flag). flag in '', 'promo', 'homewin'."""
    n, l = cell
    tgt = []
    if ptype == "P":
        tgt = _pawn_targets(n, l, owner)
    elif ptype == "S":
        tgt = _step_targets(n, l, True, DIAG_SIDE)
    elif ptype == "G":
        tgt = _step_targets(n, l, True, DIAG_FRONT)
    elif ptype == "K":
        tgt = _step_targets(n, l, True, DIAG_ALL)
    elif ptype == "N":
        tgt = list(KNIGHT_TABLE[cell])
    elif ptype == "R":
        for m in ORTH_MAPS:
            tgt += _slide(board, cell, m, owner)
    elif ptype == "B":
        for d in DIAG_ALL:
            tgt += _slide(board, cell, DIAG_MAPS[d], owner)
        # special: one NON-capturing orthogonal step to an empty cell, iff the
        # bishop is orthogonally adjacent to a friendly piece.
        orth_nb = [m.get(cell) for m in ORTH_MAPS]
        orth_nb = [c for c in orth_nb if c]
        if any(board.get(c) and board[c][0] == owner for c in orth_nb):
            for c in orth_nb:
                if board.get(c) is None:
                    tgt.append(c)
    elif ptype == "Q":
        for m in ORTH_MAPS:
            tgt += _slide(board, cell, m, owner)
        for d in DIAG_ALL:
            tgt += _slide(board, cell, DIAG_MAPS[d], owner)

    moves = []
    ehome = enemy_home(owner)
    seen = set()
    for c in tgt:
        occ = board.get(c)
        if occ is not None and occ[0] == owner:
            continue
        if c in seen:
            continue
        seen.add(c)
        if ptype == "K" and c == ehome and not (occ is not None and occ[1] == "K"):
            moves.append((c, "homewin"))
        elif ptype == "P" and c == ehome:
            moves.append((c, "promo"))
        else:
            moves.append((c, ""))
    return moves


# --------------------------------------------------------------------------- #
#  Attacks & check
# --------------------------------------------------------------------------- #
def _attacks(board, owner):
    """Set of cells attacked by `owner` (captures; bishop's quiet step excluded)."""
    hit = set()
    for cell, (o, pt) in board.items():
        if o != owner:
            continue
        n, l = cell
        if pt == "P":
            for c in _pawn_targets(n, l, owner):
                hit.add(c)
        elif pt == "S":
            hit.update(_step_targets(n, l, True, DIAG_SIDE))
        elif pt == "G":
            hit.update(_step_targets(n, l, True, DIAG_FRONT))
        elif pt == "K":
            hit.update(_step_targets(n, l, True, DIAG_ALL))
        elif pt == "N":
            hit.update(KNIGHT_TABLE[cell])
        elif pt == "R":
            for m in ORTH_MAPS:
                hit.update(_slide(board, cell, m, owner))
        elif pt == "B":
            for d in DIAG_ALL:
                hit.update(_slide(board, cell, DIAG_MAPS[d], owner))
        elif pt == "Q":
            for m in ORTH_MAPS:
                hit.update(_slide(board, cell, m, owner))
            for d in DIAG_ALL:
                hit.update(_slide(board, cell, DIAG_MAPS[d], owner))
    return hit


def _king_cell(board, owner):
    for c, (o, pt) in board.items():
        if o == owner and pt == "K":
            return c
    return None


def _in_check(board, owner):
    kc = _king_cell(board, owner)
    if kc is None:
        return False
    return kc in _attacks(board, 1 - owner)


def _demote(pt):
    return "P" if pt == "Q" else pt


def _do_move(board, owner, move):
    """Apply a move string to a COPY of board; return (nb, info)."""
    nb = dict(board)
    info = {"capture": None, "promo": False, "homewin": False, "drop": None,
            "from": None, "to": None, "ptype": None}
    if "@" in move:
        pt, cell = move.split("@")
        c = _cell(cell)
        nb[c] = (owner, pt)
        info.update(drop=pt, to=c, ptype=pt)
        return nb, info
    frm_s, to_s = move.split(">")
    frm, to = _cell(frm_s), _cell(to_s)
    owner_p, pt = nb.pop(frm)
    occ = nb.get(to)
    if occ is not None:
        info["capture"] = _demote(occ[1])
    if pt == "K" and to == enemy_home(owner):
        info["homewin"] = True
    if pt == "P" and to == enemy_home(owner):
        pt = "Q"
        info["promo"] = True
    nb[to] = (owner, pt)
    info.update({"from": frm, "to": to, "ptype": pt})
    return nb, info


def _cell(s):
    n, l = s.split(",")
    return (int(n), int(l))


def _all_legal(board, hands, owner, pawn_mate=True):
    """All legal move strings for `owner` (king-safe + king-home wins + drops)."""
    out = []
    # piece moves
    for cell, (o, pt) in list(board.items()):
        if o != owner:
            continue
        for (to, flag) in _piece_moves(board, cell, owner, pt):
            mv = f"{_cid(cell)}>{_cid(to)}"
            if flag == "homewin":
                out.append(mv)
                continue
            nb, _ = _do_move(board, owner, mv)
            if not _in_check(nb, owner):
                out.append(mv)
    # drops
    hand = hands.get(owner, {})
    empties = [c for c in CELLS if c not in board]
    ehome = enemy_home(owner)
    for pt in DROP_TYPES:
        if hand.get(pt, 0) <= 0:
            continue
        for c in empties:
            if pt == "P" and c == ehome:
                continue
            mv = f"{pt}@{_cid(c)}"
            nb, _ = _do_move(board, owner, mv)
            if _in_check(nb, owner):
                continue
            if pt == "P" and pawn_mate:
                opp = 1 - owner
                if _in_check(nb, opp) and not _all_legal(nb, hands, opp, pawn_mate=False):
                    continue    # illegal: pawn drop delivers checkmate
            out.append(mv)
    return out


# --------------------------------------------------------------------------- #
class Crazy38s(Game):
    name = "Crazy 38's"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None) -> CState:
        board = {}
        # Black (seat 1, top). Transcribed from 38squares.setup.gif.
        black = {(8, 1): "K", (5, 1): "P", (6, 2): "S", (5, 2): "B", (7, 3): "G",
                 (6, 3): "R", (5, 3): "P", (8, 4): "P", (7, 4): "N", (6, 4): "P"}
        for c, pt in black.items():
            board[c] = (BLACK, pt)
        # White (seat 0, bottom) = 180-degree rotation (n,l)->(9-n,9-l).
        for (n, l), pt in black.items():
            board[(9 - n, 9 - l)] = (WHITE, pt)
        return CState(board=board, hands={WHITE: {}, BLACK: {}}, to_move=WHITE)

    def current_player(self, state):
        return state.to_move

    def is_terminal(self, state):
        return state.winner is not None or state.draw

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        return _all_legal(state.board, state.hands, state.to_move)

    def apply_move(self, state, move, rng=None):
        owner = state.to_move
        nb, info = _do_move(state.board, owner, move)
        # hands: capture banks to mover; drop removes from mover's hand
        nh = {WHITE: dict(state.hands.get(WHITE, {})), BLACK: dict(state.hands.get(BLACK, {}))}
        if info["capture"]:
            cp = info["capture"]
            nh[owner][cp] = nh[owner].get(cp, 0) + 1
        if info["drop"]:
            dp = info["drop"]
            nh[owner][dp] = nh[owner].get(dp, 0) - 1
            if nh[owner][dp] <= 0:
                del nh[owner][dp]

        opp = 1 - owner
        ns = CState(board=nb, hands=nh, to_move=opp,
                    reps=dict(state.reps), ply=state.ply + 1)
        if info["from"] is not None:
            ns.last = [_cid(info["from"]), _cid(info["to"])]
        else:
            ns.last = [_cid(info["to"])]

        # 1) immediate king-to-enemy-home win
        if info["homewin"]:
            ns.winner = owner
            return ns
        # 2) repetition / ply cap
        key = _poskey(nb, nh, opp)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        if ns.reps[key] >= REP_LIMIT or ns.ply >= PLY_CAP:
            ns.draw = True
            return ns
        # 3) checkmate / stalemate for the side to move
        if not _all_legal(nb, nh, opp):
            if _in_check(nb, opp):
                ns.winner = owner          # checkmate
            else:
                ns.draw = True             # stalemate -> honest draw
        return ns

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if p == state.winner else -1.0 for p in (WHITE, BLACK)]

    def heuristic(self, state):
        if state.winner is not None:
            return [1.0 if p == state.winner else -1.0 for p in (WHITE, BLACK)]
        if state.draw:
            return [0.0, 0.0]
        m = 0
        for (o, pt) in state.board.values():
            v = VALUE[pt]
            m += v if o == WHITE else -v
        for o in (WHITE, BLACK):
            for pt, cnt in state.hands.get(o, {}).items():
                v = VALUE[_demote(pt)] * cnt
                m += v if o == WHITE else -v
        h = math.tanh(m / 8.0)
        return [h, -h]

    # ---- notation --------------------------------------------------------
    def describe_move(self, state, move):
        owner = state.to_move
        if "@" in move:
            pt, cell = move.split("@")
            return f"{pt}@{_label(_cell(cell))}"
        frm, to = move.split(">")
        fc, tc = _cell(frm), _cell(to)
        pt = state.board.get(fc, (owner, "?"))[1]
        cap = "x" if to_occupied(state.board, tc) else "-"
        s = f"{pt}{_label(fc)}{cap}{_label(tc)}"
        if pt == "P" and tc == enemy_home(owner):
            s += "=Q"
        if pt == "K" and tc == enemy_home(owner):
            s += "#"
        return s

    # ---- persistence -----------------------------------------------------
    def serialize(self, state):
        return {
            "board": {_cid(c): [o, pt] for c, (o, pt) in state.board.items()},
            "hands": {str(o): dict(h) for o, h in state.hands.items()},
            "to_move": state.to_move,
            "winner": state.winner,
            "draw": state.draw,
            "reps": dict(state.reps),
            "ply": state.ply,
            "last": list(state.last),
        }

    def deserialize(self, data):
        board = {_cell(k): (v[0], v[1]) for k, v in data["board"].items()}
        hands = {WHITE: dict(data["hands"].get("0", {})),
                 BLACK: dict(data["hands"].get("1", {}))}
        return CState(board=board, hands=hands, to_move=data["to_move"],
                      winner=data["winner"], draw=data["draw"],
                      reps=dict(data.get("reps", {})), ply=data.get("ply", 0),
                      last=list(data.get("last", [])))

    # ---- render ----------------------------------------------------------
    def render(self, state, perspective=None):
        cells = []
        for (n, l) in sorted(CELLS):
            ix = l + n - 5
            iy = l - n + 6
            cells.append({"id": _cid((n, l)),
                          "points": [[ix, iy - 1], [ix + 1, iy], [ix, iy + 1], [ix - 1, iy]]})
        pieces = [{"cell": _cid(c), "owner": o, "label": pt} for c, (o, pt) in state.board.items()]
        reserve = {}
        for o in (WHITE, BLACK):
            h = {k: v for k, v in state.hands.get(o, {}).items() if v > 0}
            if h:
                reserve[str(o)] = h
        names = {WHITE: "White", BLACK: "Black"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif state.draw:
            cap = "Draw"
        else:
            chk = " (check)" if _in_check(state.board, state.to_move) else ""
            cap = f"{names[state.to_move]} to move{chk}"
        spec = {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "pieceset": "chess",
            "highlights": [{"cell": c, "kind": "last-move"} for c in state.last],
            "caption": cap,
        }
        if reserve:
            spec["reserve"] = reserve
        return spec


def to_occupied(board, c):
    return c in board


def _poskey(board, hands, to_move):
    b = ";".join(f"{_cid(c)}:{o}{pt}" for c, (o, pt) in sorted(board.items()))
    hh = "|".join(f"{o}:" + ",".join(f"{k}{v}" for k, v in sorted(hands.get(o, {}).items()))
                  for o in (WHITE, BLACK))
    return f"{b}#{hh}#{to_move}"
