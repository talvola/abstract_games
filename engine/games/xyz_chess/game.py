"""3D XYZ Chess — Rick Hewson (developed since 1988; ruleset stable since 2016).

Source: Abstract Games magazine issue 24 (Winter 2022), pp. 30-34 — rules
summary by Kerry Handscomb, annotated Hewson-Mandoshkin game by Jake
Mandoshkin.  (Successor of Hewson's "Exchequer", AG15; per AG19 the only
significant change is the edge-pawn two-space initial move.)

BOARD: a 4x4x4 array of cubes.  Article notation: levels A (top) .. D
(bottom); columns a (closest to White) .. d; rows 1 .. 4.  This module uses
(x=column a..d = 0..3, y=row 1..4 = 0..3, z=level A..D = 0..3); the cell-id
STRING is "z,x,y" ("level,col,row" — same 3-component convention as
raumschach so the generic layered-board UI works).  A move is
"z,x,y>z2,x2,y2".  White's army fills the 2x2x4 corner block at a1/b2 (all
levels), Black mirrors at d4/c3 (x,y -> 3-x,3-y, same level).

PIECES (the standard 32 chess pieces; movement per the AG24 diagrams):
  * King   (K) — ONE step orthogonally only (6 face-neighbours; explicitly NO
                 diagonal step).
  * Rook   (R) — orthogonal slider (6 directions; max 9 squares from centre,
                 an article-stated figure).
  * Bishop (B) — planar-diagonal slider: exactly two coordinates change by
                 +/-1 (12 directions; max 15 squares from centre, article
                 figure).  NO triagonal.
  * Queen  (Q) — Rook + Bishop (18 directions).  NO triagonal.
  * Knight (N) — ONE step "triagonally": all three coordinates change by +/-1
                 (8 directions; must change level).  Confined to a 16-cell
                 sub-lattice.
  * Pawn   (P) — cannot change level.  Moves one step orthogonally ON ITS
                 LEVEL towards its opposite corner (White: +x or +y; Black:
                 -x or -y).  Pawns CAPTURE EXACTLY AS THEY MOVE.  A pawn
                 still standing on one of its side's EDGE start squares (the
                 four starting pawns on the outer ring of their level: White
                 a2A, b1B, a2C, b1D; Black d3A, c4B, d3C, c4D) may move TWO
                 spaces in either of its directions provided the first space
                 is empty; the double-step may capture (the anchor game plays
                 three such captures: 7...Pc4BxNc2B, 9.Pb1BxBd1B,
                 16...Pd3AxPb3A).  No en passant.  On reaching the opposite
                 corner OF ITS LEVEL (d4 for White, a1 for Black) a pawn
                 promotes to a Queen (automatic; the article names no other
                 choice).
No castling.  WIN: checkmate.  Stalemate is a draw (explicit in the article).
Termination guarantees (conventions; the article is silent): threefold
repetition, 100 plies with no capture or pawn move, or a hard ply cap = draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZE = 4
WHITE, BLACK = 0, 1
PLY_CAP = 400
NOPROGRESS_CAP = 100  # 50 full moves without a capture or pawn move -> draw

# Article: Bishop (max 15 squares) outvalues Rook (max 9); Knight worth a
# little less than a Pawn.
PIECE_VALUE = {"P": 1.0, "N": 0.9, "B": 5.0, "R": 4.0, "Q": 9.0, "K": 0.0}


# --------------------------------------------------------------- direction sets
def _build_dirs():
    ortho, planar = [], []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                nz = (dx != 0) + (dy != 0) + (dz != 0)
                if nz == 1:
                    ortho.append((dx, dy, dz))
                elif nz == 2:
                    planar.append((dx, dy, dz))
    return ortho, planar


ORTHO_DIRS, PLANAR_DIRS = _build_dirs()          # 6, 12
QUEEN_DIRS = ORTHO_DIRS + PLANAR_DIRS             # 18 (no triagonal)
TRIAGONAL = [(dx, dy, dz) for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]

SLIDERS = {"R": ORTHO_DIRS, "B": PLANAR_DIRS, "Q": QUEEN_DIRS}

# Pawns: on-level orthogonal, towards the opposite corner of the level.
PAWN_DIRS = {WHITE: [(1, 0, 0), (0, 1, 0)], BLACK: [(-1, 0, 0), (0, -1, 0)]}
# Promotion corner of each level: d4 for White, a1 for Black.
PROMO_XY = {WHITE: (SIZE - 1, SIZE - 1), BLACK: (0, 0)}
# The four EDGE pawn start squares per side (outer ring of their level);
# the b2/c3-file pawns sit on the central 2x2 of their level and get no
# double-step.
EDGE_START = {
    WHITE: {(0, 1, 0), (1, 0, 1), (0, 1, 2), (1, 0, 3)},   # a2A b1B a2C b1D
    BLACK: {(3, 2, 0), (2, 3, 1), (3, 2, 2), (2, 3, 3)},   # d3A c4B d3C c4D
}


def _inb(x, y, z):
    return 0 <= x < SIZE and 0 <= y < SIZE and 0 <= z < SIZE


def _key(x, y, z):
    return f"{z},{x},{y}"          # "level,col,row"


def _parse(s):
    z, x, y = (int(v) for v in s.split(","))
    return x, y, z


def _enemy(p):
    return 1 - p


def _sq(x, y, z):
    """Article notation: column letter + row digit + level letter, e.g. c2B."""
    return f"{'abcd'[x]}{y + 1}{'ABCD'[z]}"


# ------------------------------------------------------------------- setup ----
def _setup():
    """AG24 setup diagram, cross-checked against every piece's first move in
    the annotated Hewson-Mandoshkin game.  White fills the 2x2x4 block at its
    a1 corner; Black mirrors (x,y -> 3-x,3-y) at d4."""
    white = {
        (0, 0, 0): "N", (1, 0, 0): "R", (0, 1, 0): "P", (1, 1, 0): "P",  # A
        (0, 0, 1): "K", (1, 0, 1): "P", (0, 1, 1): "B", (1, 1, 1): "P",  # B
        (0, 0, 2): "Q", (1, 0, 2): "N", (0, 1, 2): "P", (1, 1, 2): "P",  # C
        (0, 0, 3): "B", (1, 0, 3): "P", (0, 1, 3): "R", (1, 1, 3): "P",  # D
    }
    p = {}
    for (x, y, z), l in white.items():
        p[(x, y, z)] = (WHITE, l)
        p[(SIZE - 1 - x, SIZE - 1 - y, z)] = (BLACK, l)
    return p


# ------------------------------------------------------------------ attacks ---
def _pawn_attacks(pieces, tx, ty, tz, by):
    for dx, dy, dz in PAWN_DIRS[by]:
        occ = pieces.get((tx - dx, ty - dy, tz - dz))
        if occ is not None and occ == (by, "P"):
            return True
        # Double-step capture: a `by` pawn on one of its edge start squares,
        # two steps away with an empty intermediate, also attacks this cell.
        src = (tx - 2 * dx, ty - 2 * dy, tz - 2 * dz)
        occ2 = pieces.get(src)
        if (occ2 == (by, "P") and src in EDGE_START[by]
                and pieces.get((tx - dx, ty - dy, tz - dz)) is None):
            return True
    return False


def _attacked(pieces, tx, ty, tz, by):
    """Is cell (tx,ty,tz) attacked by side ``by``?"""
    if _pawn_attacks(pieces, tx, ty, tz, by):
        return True
    for dx, dy, dz in TRIAGONAL:
        occ = pieces.get((tx + dx, ty + dy, tz + dz))
        if occ == (by, "N"):
            return True
    for dx, dy, dz in ORTHO_DIRS:
        occ = pieces.get((tx + dx, ty + dy, tz + dz))
        if occ == (by, "K"):
            return True
    for dirs, letters in ((ORTHO_DIRS, ("R", "Q")), (PLANAR_DIRS, ("B", "Q"))):
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
    """Yield (fx,fy,fz,tx,ty,tz) pseudo-legal moves (promotion is automatic)."""
    for (x, y, z), (o, l) in list(pieces.items()):
        if o != player:
            continue
        if l in SLIDERS:
            for dx, dy, dz in SLIDERS[l]:
                sx, sy, sz = x + dx, y + dy, z + dz
                while _inb(sx, sy, sz):
                    occ = pieces.get((sx, sy, sz))
                    if occ is None:
                        yield (x, y, z, sx, sy, sz)
                    else:
                        if occ[0] != player:
                            yield (x, y, z, sx, sy, sz)
                        break
                    sx, sy, sz = sx + dx, sy + dy, sz + dz
        elif l == "K":
            for dx, dy, dz in ORTHO_DIRS:
                sx, sy, sz = x + dx, y + dy, z + dz
                if not _inb(sx, sy, sz):
                    continue
                occ = pieces.get((sx, sy, sz))
                if occ is None or occ[0] != player:
                    yield (x, y, z, sx, sy, sz)
        elif l == "N":
            for dx, dy, dz in TRIAGONAL:
                sx, sy, sz = x + dx, y + dy, z + dz
                if not _inb(sx, sy, sz):
                    continue
                occ = pieces.get((sx, sy, sz))
                if occ is None or occ[0] != player:
                    yield (x, y, z, sx, sy, sz)
        elif l == "P":
            can_double = (x, y, z) in EDGE_START[player]
            for dx, dy, dz in PAWN_DIRS[player]:
                sx, sy, sz = x + dx, y + dy, z + dz
                if _inb(sx, sy, sz):
                    occ = pieces.get((sx, sy, sz))
                    if occ is None or occ[0] != player:
                        yield (x, y, z, sx, sy, sz)
                    # Two-space initial move: first space must be EMPTY; the
                    # second may be empty or an enemy piece (capture-as-move).
                    if can_double and occ is None:
                        s2 = (x + 2 * dx, y + 2 * dy, z + 2 * dz)
                        if _inb(*s2):
                            occ2 = pieces.get(s2)
                            if occ2 is None or occ2[0] != player:
                                yield (x, y, z, s2[0], s2[1], s2[2])


def _apply_pseudo(pieces, mv):
    fx, fy, fz, tx, ty, tz = mv
    np = dict(pieces)
    o, l = np.pop((fx, fy, fz))
    if l == "P" and (tx, ty) == PROMO_XY[o]:
        l = "Q"                    # automatic promotion at the far corner
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
    fx, fy, fz, tx, ty, tz = mv
    return f"{_key(fx, fy, fz)}>{_key(tx, ty, tz)}"


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
class XyzState:
    pieces: dict = field(default_factory=dict)   # (x,y,z) -> (owner, letter)
    to_move: int = WHITE
    winner: Optional[int] = None
    draw: bool = False
    ply: int = 0
    noprog: int = 0                               # plies since capture/pawn move
    seen: dict = field(default_factory=dict)
    last: Optional[tuple] = None                  # (x,y,z) landing cell


class XyzChess(Game):
    name = "3D XYZ Chess"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        pieces = _setup()
        s = XyzState(pieces=pieces, to_move=WHITE, ply=0, noprog=0)
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
        fx, fy, fz, tx, ty, tz = chosen
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

        ns = XyzState(pieces=new_pieces, to_move=opp, ply=ply, noprog=noprog,
                      seen=seen, last=(tx, ty, tz))

        opp_moves = _legal(new_pieces, opp)
        if not opp_moves:
            if _in_check(new_pieces, opp):
                ns.winner = player            # checkmate
            else:
                ns.draw = True                # stalemate (explicit article rule)
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
        return XyzState(
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
        """Article notation, e.g. 'Rb1A-c1A', 'Nb1CxPc2B', with +/# suffix."""
        frm, to = move.split(">")
        fx, fy, fz = _parse(frm)
        tx, ty, tz = _parse(to)
        occ = s.pieces.get((fx, fy, fz))
        letter = occ[1] if occ else "?"
        victim = s.pieces.get((tx, ty, tz))
        mid = f"x{victim[1]}" if victim else "-"
        out = f"{letter}{_sq(fx, fy, fz)}{mid}{_sq(tx, ty, tz)}"
        if (occ is not None and letter == "P"
                and (tx, ty) == PROMO_XY[occ[0]]):
            out += "=Q"
        try:
            ns = self.apply_move(s, move)
            if ns.winner is not None:
                out += "#"
            elif _in_check(ns.pieces, ns.to_move):
                out += "+"
        except ValueError:
            pass
        return out

    # ---------------------------------------------------------- presentation --
    def render(self, s, perspective=None):
        GAP = 1.4
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

        pieces = [{"cell": _key(x, y, z), "owner": o, "label": l}
                  for (x, y, z), (o, l) in s.pieces.items()]

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
                       "(levels A-D left to right; White home = bottom-left "
                       "a1 corner, Black = top-right d4)")
            if _in_check(s.pieces, s.to_move):
                caption += " — CHECK"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieceset": "chess",
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
