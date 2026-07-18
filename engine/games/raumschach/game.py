"""Raumschach — Dr. Ferdinand Maack, 1907. The classic 5x5x5 three-dimensional
chess and a Recognized Chess Variant.

Five stacked 5x5 levels A (bottom, White's home) .. E (top, Black's home). A
cell is identified by (level, file, rank): levels A-E, files a-e, ranks 1-5.
Coordinates in this module are (x=file 0..4, y=rank 0..4, z=level 0..4); the
cell-id STRING is "level,col,row" == f"{z},{x},{y}" (mirrors alice_chess's
3-component ids so the generic click-to-move UI works). A move string is
"z,x,y>z2,x2,y2" (+ "=Q/R/B/N/U" for a promotion).

PIECES & MOVES (chessvariants.com/3d.dir/3d5.html + Wikipedia "Three-dimensional
chess", Raumschach section; sources agree):
  * Rook (R)    — slides through the 6 FACES: exactly one coordinate changes.
  * Bishop (B)  — slides through the 12 EDGES: exactly two coordinates change
                  by +/-1 (a 2-D diagonal in one of the three coordinal planes).
  * Unicorn (U) — slides through the 8 CORNERS: all three coordinates change by
                  +/-1 (a pure 3-D space diagonal / triagonal). No 2-D move.
  * Queen (Q)   — Rook + Bishop + Unicorn = 26 directions.
                  (CVP: "The Queen has the combined moves of Rook, Bishop and
                  Unicorn.")
  * King (K)    — as the Queen but one step (any of the 26 adjacent cells).
  * Knight (N)  — a (0,1,2) leap: one coordinate 0, the other two are 1 and 2
                  (in magnitude), any signs -> 24 destinations; leaps over
                  pieces.
  * Pawn (P)    — NON-capturing: one step straight FORWARD (toward the enemy
                  side, +rank for White / -rank for Black) OR one step straight
                  UP for White / DOWN for Black (absolute z). CAPTURING: one
                  step diagonally, either forward-in-level (+/-file, +rank) or
                  sideways-and-up/down (+/-file, +/-level toward the enemy).
                  These are exactly CVP's worked example squares (a White pawn
                  on Ac2 captures Ab3, Ad3, Bb2, Bd2). NO 2-step first move, NO
                  en passant, NO castling. Promotes on the far rank (rank 5 for
                  White, rank 1 for Black) to Q/R/B/N/U.

WIN: checkmate. Stalemate = draw. Threefold repetition / 50-move no-progress /
a hard ply cap = draw (termination guarantee).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZE = 5
WHITE, BLACK = 0, 1
PLY_CAP = 400
NOPROGRESS_CAP = 100  # 50 full moves without a capture or pawn move -> draw

PIECE_VALUE = {"P": 1.0, "N": 3.0, "B": 3.0, "U": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}


# --------------------------------------------------------------- direction sets
def _build_dirs():
    rook, bishop, unicorn = [], [], []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                nz = (dx != 0) + (dy != 0) + (dz != 0)
                if nz == 1:
                    rook.append((dx, dy, dz))
                elif nz == 2:
                    bishop.append((dx, dy, dz))
                elif nz == 3:
                    unicorn.append((dx, dy, dz))
    return rook, bishop, unicorn


ROOK_DIRS, BISHOP_DIRS, UNICORN_DIRS = _build_dirs()   # 6, 12, 8
QUEEN_DIRS = ROOK_DIRS + BISHOP_DIRS + UNICORN_DIRS     # 26


def _build_knight():
    offs = set()
    for zero in range(3):
        axes = [i for i in range(3) if i != zero]
        for a in (1, -1, 2, -2):
            for b in (1, -1, 2, -2):
                if {abs(a), abs(b)} == {1, 2}:
                    v = [0, 0, 0]
                    v[axes[0]] = a
                    v[axes[1]] = b
                    offs.add(tuple(v))
    return sorted(offs)


KNIGHT_OFFS = _build_knight()   # 24

SLIDERS = {"R": ROOK_DIRS, "B": BISHOP_DIRS, "U": UNICORN_DIRS, "Q": QUEEN_DIRS}

# Pawn vectors (x=file, y=rank, z=level).  White forward = +y, White up = +z.
PAWN = {
    WHITE: {
        "push": [(0, 1, 0), (0, 0, 1)],
        "cap": [(1, 1, 0), (-1, 1, 0), (1, 0, 1), (-1, 0, 1)],
        "promo_row": SIZE - 1,   # rank 5
    },
    BLACK: {
        "push": [(0, -1, 0), (0, 0, -1)],
        "cap": [(1, -1, 0), (-1, -1, 0), (1, 0, -1), (-1, 0, -1)],
        "promo_row": 0,          # rank 1
    },
}
PROMO = ("Q", "R", "B", "N", "U")


def _inb(x, y, z):
    return 0 <= x < SIZE and 0 <= y < SIZE and 0 <= z < SIZE


def _key(x, y, z):
    return f"{z},{x},{y}"          # "level,col,row"


def _parse(s):
    z, x, y = (int(v) for v in s.split(","))
    return x, y, z


def _enemy(p):
    return 1 - p


# ------------------------------------------------------------------- setup ----
BACK_A = ["R", "N", "K", "N", "R"]   # levels A / E outer levels
BACK_B = ["B", "U", "Q", "B", "U"]   # levels B / D inner levels


def _setup():
    p = {}
    # White: level A (z=0) and level B (z=1); back rank on row 0, pawns row 1.
    for x in range(SIZE):
        p[(x, 0, 0)] = (WHITE, BACK_A[x])
        p[(x, 1, 0)] = (WHITE, "P")
        p[(x, 0, 1)] = (WHITE, BACK_B[x])
        p[(x, 1, 1)] = (WHITE, "P")
    # Black: level D (z=3) and level E (z=4); back rank on row 4, pawns row 3.
    for x in range(SIZE):
        p[(x, 4, 3)] = (BLACK, BACK_B[x])
        p[(x, 3, 3)] = (BLACK, "P")
        p[(x, 4, 4)] = (BLACK, BACK_A[x])
        p[(x, 3, 4)] = (BLACK, "P")
    return p


# ------------------------------------------------------------------ attacks ---
def _attacked(pieces, tx, ty, tz, by):
    """Is cell (tx,ty,tz) attacked by side ``by``?"""
    # Pawn: a `by` pawn attacks this cell iff it stands at cell - capvec.
    for dx, dy, dz in PAWN[by]["cap"]:
        occ = pieces.get((tx - dx, ty - dy, tz - dz))
        if occ is not None and occ[0] == by and occ[1] == "P":
            return True
    # Knight.
    for dx, dy, dz in KNIGHT_OFFS:
        occ = pieces.get((tx + dx, ty + dy, tz + dz))
        if occ is not None and occ[0] == by and occ[1] == "N":
            return True
    # King (adjacent, 26 dirs).
    for dx, dy, dz in QUEEN_DIRS:
        occ = pieces.get((tx + dx, ty + dy, tz + dz))
        if occ is not None and occ[0] == by and occ[1] == "K":
            return True
    # Sliders.
    for dirs, letters in ((ROOK_DIRS, ("R", "Q")),
                          (BISHOP_DIRS, ("B", "Q")),
                          (UNICORN_DIRS, ("U", "Q"))):
        for dx, dy, dz in dirs:
            sx, sy, sz = tx + dx, ty + dy, tz + dz
            while _inb(sx, sy, sz):
                occ = pieces.get((sx, sy, sz))
                if occ is not None:
                    if occ[0] == by and occ[1] in letters:
                        return True
                    break
                sx, sy, sz = sx + dx, sy + dy, sz + dz
    return False


def _king_pos(pieces, player):
    for pos, (o, l) in pieces.items():
        if o == player and l == "K":
            return pos
    return None


def _in_check(pieces, player):
    kp = _king_pos(pieces, player)
    if kp is None:
        return False
    return _attacked(pieces, kp[0], kp[1], kp[2], _enemy(player))


# ---------------------------------------------------------- pseudo / legal ----
def _pseudo(pieces, player):
    for (x, y, z), (o, l) in list(pieces.items()):
        if o != player:
            continue
        if l in SLIDERS:
            for dx, dy, dz in SLIDERS[l]:
                sx, sy, sz = x + dx, y + dy, z + dz
                while _inb(sx, sy, sz):
                    occ = pieces.get((sx, sy, sz))
                    if occ is None:
                        yield (x, y, z, sx, sy, sz, None)
                    else:
                        if occ[0] != player:
                            yield (x, y, z, sx, sy, sz, None)
                        break
                    sx, sy, sz = sx + dx, sy + dy, sz + dz
        elif l == "K":
            for dx, dy, dz in QUEEN_DIRS:
                sx, sy, sz = x + dx, y + dy, z + dz
                if not _inb(sx, sy, sz):
                    continue
                occ = pieces.get((sx, sy, sz))
                if occ is None or occ[0] != player:
                    yield (x, y, z, sx, sy, sz, None)
        elif l == "N":
            for dx, dy, dz in KNIGHT_OFFS:
                sx, sy, sz = x + dx, y + dy, z + dz
                if not _inb(sx, sy, sz):
                    continue
                occ = pieces.get((sx, sy, sz))
                if occ is None or occ[0] != player:
                    yield (x, y, z, sx, sy, sz, None)
        elif l == "P":
            spec = PAWN[player]
            pr = spec["promo_row"]
            for dx, dy, dz in spec["push"]:
                sx, sy, sz = x + dx, y + dy, z + dz
                if _inb(sx, sy, sz) and pieces.get((sx, sy, sz)) is None:
                    if sy == pr:
                        for pc in PROMO:
                            yield (x, y, z, sx, sy, sz, pc)
                    else:
                        yield (x, y, z, sx, sy, sz, None)
            for dx, dy, dz in spec["cap"]:
                sx, sy, sz = x + dx, y + dy, z + dz
                if not _inb(sx, sy, sz):
                    continue
                occ = pieces.get((sx, sy, sz))
                if occ is not None and occ[0] != player:
                    if sy == pr:
                        for pc in PROMO:
                            yield (x, y, z, sx, sy, sz, pc)
                    else:
                        yield (x, y, z, sx, sy, sz, None)


def _apply_pseudo(pieces, mv):
    fx, fy, fz, tx, ty, tz, promo = mv
    np = dict(pieces)
    o, l = np.pop((fx, fy, fz))
    if promo is not None:
        l = promo
    np[(tx, ty, tz)] = (o, l)
    return np


def _legal(pieces, player):
    out = []
    for mv in _pseudo(pieces, player):
        np = _apply_pseudo(pieces, mv)
        if not _in_check(np, player):
            out.append(mv)
    return out


def _mstr(mv):
    fx, fy, fz, tx, ty, tz, promo = mv
    s = f"{_key(fx, fy, fz)}>{_key(tx, ty, tz)}"
    if promo is not None:
        s += f"={promo}"
    return s


def _perft(pieces, player, depth):
    """Pure move-count perft (ignores draw bookkeeping) — the frozen anchor."""
    if depth == 0:
        return 1
    total = 0
    for mv in _legal(pieces, player):
        total += _perft(_apply_pseudo(pieces, mv), _enemy(player), depth - 1)
    return total


def _pos_key(pieces, to_move):
    parts = [f"{z}{x}{y}{o}{l}" for (x, y, z), (o, l) in sorted(pieces.items())]
    return "|".join(parts) + f"#{to_move}"


def _material(pieces):
    w = b = 0.0
    for (o, l) in pieces.values():
        if o == WHITE:
            w += PIECE_VALUE[l]
        else:
            b += PIECE_VALUE[l]
    return w, b


# --------------------------------------------------------------------- state --
@dataclass
class RaumState:
    pieces: dict = field(default_factory=dict)   # (x,y,z) -> (owner, letter)
    to_move: int = WHITE
    winner: Optional[int] = None
    draw: bool = False
    ply: int = 0
    noprog: int = 0                               # plies since capture/pawn move
    seen: dict = field(default_factory=dict)
    last: Optional[tuple] = None                  # (x,y,z) landing cell


class Raumschach(Game):
    uid = "raumschach"
    name = "Raumschach"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        pieces = _setup()
        s = RaumState(pieces=pieces, to_move=WHITE, ply=0, noprog=0)
        s.seen = {_pos_key(pieces, WHITE): 1}
        return s

    def current_player(self, s):
        return s.to_move

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        return [_mstr(mv) for mv in _legal(s.pieces, s.to_move)]

    def apply_move(self, s, move, rng=None):
        if self.is_terminal(s):
            raise ValueError("game over")
        player = s.to_move
        chosen = None
        for mv in _legal(s.pieces, player):
            if _mstr(mv) == move:
                chosen = mv
                break
        if chosen is None:
            raise ValueError(f"illegal move {move!r}")
        fx, fy, fz, tx, ty, tz, promo = chosen
        was_capture = (tx, ty, tz) in s.pieces
        moved_letter = s.pieces[(fx, fy, fz)][1]
        new_pieces = _apply_pseudo(s.pieces, chosen)
        opp = _enemy(player)

        noprog = 0 if (was_capture or moved_letter == "P") else s.noprog + 1
        ply = s.ply + 1
        seen = dict(s.seen)
        pk = _pos_key(new_pieces, opp)
        rep = seen.get(pk, 0) + 1
        seen[pk] = rep

        ns = RaumState(pieces=new_pieces, to_move=opp, ply=ply, noprog=noprog,
                       seen=seen, last=(tx, ty, tz))

        opp_moves = _legal(new_pieces, opp)
        if not opp_moves:
            if _in_check(new_pieces, opp):
                ns.winner = player            # checkmate
            else:
                ns.draw = True                # stalemate
            return ns
        if rep >= 3 or noprog >= NOPROGRESS_CAP or ply >= PLY_CAP:
            ns.draw = True
        return ns

    def is_terminal(self, s):
        return s.winner is not None or s.draw

    def returns(self, s):
        if s.winner == WHITE:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s):
        import math
        w, b = _material(s.pieces)
        v = math.tanh((w - b) / 8.0)
        return [v, -v]

    # ----------------------------------------------------------- serialize ----
    def serialize(self, s):
        return {
            "pieces": {_key(x, y, z): [o, l]
                       for (x, y, z), (o, l) in s.pieces.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
            "noprog": s.noprog,
            "seen": dict(s.seen),
            "last": (list(s.last) if s.last is not None else None),
        }

    def deserialize(self, d):
        pieces = {}
        for k, v in d["pieces"].items():
            pieces[_parse(k)] = (int(v[0]), v[1])
        last = d.get("last")
        return RaumState(
            pieces=pieces,
            to_move=d["to_move"],
            winner=d.get("winner"),
            draw=d.get("draw", False),
            ply=d.get("ply", 0),
            noprog=d.get("noprog", 0),
            seen=dict(d.get("seen", {})),
            last=(tuple(last) if last is not None else None),
        )

    # ------------------------------------------------------------- notation ---
    def describe_move(self, s, move):
        head = move.split("=")
        promo = head[1] if len(head) > 1 else None
        frm, to = head[0].split(">")
        fx, fy, fz = _parse(frm)
        tx, ty, tz = _parse(to)
        occ = s.pieces.get((fx, fy, fz))
        letter = occ[1] if occ else "?"

        def sq(x, y, z):
            return f"{'ABCDE'[z]}{'abcde'[x]}{y + 1}"

        cap = "x" if (tx, ty, tz) in s.pieces else "-"
        prefix = "" if letter == "P" else letter
        out = f"{prefix}{sq(fx, fy, fz)}{cap}{sq(tx, ty, tz)}"
        if promo:
            out += f"={promo}"
        return out

    # ---------------------------------------------------------- presentation --
    def render(self, s, perspective=None):
        GAP = 1.5
        light = "#ecdab9"
        dark = "#b58863"
        cells = []
        tints = {}
        for z in range(SIZE):
            bx = z * (SIZE + GAP)
            for x in range(SIZE):
                for y in range(SIZE):
                    ox = bx + x
                    oy = (SIZE - 1 - y)
                    pts = [
                        [round(ox, 3), round(oy, 3)],
                        [round(ox + 1, 3), round(oy, 3)],
                        [round(ox + 1, 3), round(oy + 1, 3)],
                        [round(ox, 3), round(oy + 1, 3)],
                    ]
                    cid = _key(x, y, z)
                    cells.append({"id": cid, "points": pts})
                    tints[cid] = light if (x + y + z) % 2 == 0 else dark

        pieces = []
        for (x, y, z), (o, l) in s.pieces.items():
            pc = {"cell": _key(x, y, z), "owner": o, "label": l}
            if l == "U":
                pc["icon"] = "unicorn"
            pieces.append(pc)

        highlights = []
        if s.last is not None:
            highlights.append({"cell": _key(*s.last), "kind": "last-move"})

        names = {WHITE: "White", BLACK: "Black"}
        if s.winner is not None:
            caption = f"{names[s.winner]} wins by checkmate"
        elif s.draw:
            caption = "Draw"
        else:
            caption = (f"{names[s.to_move]} to move  "
                       "(levels A-E, left to right)")
            if _in_check(s.pieces, s.to_move):
                caption += " — CHECK"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieceset": "chess",
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
