"""Rosette -- Go transposed to the triple contacts (vertices) of a honeycomb.

Invented by Mark Berger (pen name of Richard Kramberger) in 1975, published in
*Games & Puzzles*, and revived/hosted by Christian Freeling on MindSports.

The board is the set of vertices ("triple contacts") of a hexagonal patch of
hexagons with ``n`` hexes on each side; there are exactly ``6 * n**2`` vertices
(base-5 = 150, base-6 = 216, base-7 = 294). Every interior vertex has exactly
three neighbours (along the honeycomb edges); boundary vertices have two.

All the usual Go rules apply -- alternating single placement (Black first),
passing allowed, double-pass ends, standard liberty capture, illegal suicide
unless it captures, and situational **superko** (a move may not recreate a prior
position with the same player to move). Scoring is **Chinese / area** (stones +
single-colour territory), with White receiving the **komi**.

**The one new rule -- the rosette.** A group also lives, unconditionally and
permanently, if it contains a *rosette*: six like-coloured stones surrounding one
small hexagon (all six vertices of a honeycomb cell occupied by one colour). A
group that contains a rosette is immune from capture -- it is skipped in capture
checks and can never be self-atari/suicide.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

BLACK, WHITE = 0, 1


# --------------------------------------------------------------------------- #
#  Honeycomb-vertex geometry (built + cached per board size)
# --------------------------------------------------------------------------- #
class _Geo:
    """The vertex graph of a hexagonal honeycomb patch with ``n`` hexes/side.

    Vertices are indexed ``0..N-1``; a move string is ``str(vertex_id)``.
    """

    __slots__ = ("n", "N", "coords", "neigh", "hexes", "hex_at")

    def __init__(self, n: int):
        self.n = n
        R = n - 1
        # Hex centres of a hexagon-shaped patch (cube-coordinate constraint).
        centers = []
        for q in range(-R, R + 1):
            for r in range(-R, R + 1):
                if max(abs(q), abs(r), abs(q + r)) <= R:
                    centers.append((q, r))

        def cpix(q, r):
            return (1.5 * q, math.sqrt(3.0) * (r + q / 2.0))

        def corner(cx, cy, i):
            a = math.radians(60.0 * i)
            return (cx + math.cos(a), cy + math.sin(a))

        vid: dict = {}
        coords: list = []
        raw_hexes: list = []

        def getv(x, y):
            k = (round(x, 4), round(y, 4))
            j = vid.get(k)
            if j is None:
                j = len(coords)
                vid[k] = j
                coords.append((x, y))
            return j

        for (q, r) in centers:
            cx, cy = cpix(q, r)
            raw_hexes.append(tuple(getv(*corner(cx, cy, i)) for i in range(6)))

        # Re-index vertices top-to-bottom (stable, tidy ids) and remap.
        order = sorted(range(len(coords)),
                       key=lambda j: (round(coords[j][1], 4), round(coords[j][0], 4)))
        remap = {old: new for new, old in enumerate(order)}
        self.N = len(coords)
        self.coords = [coords[order[new]] for new in range(self.N)]
        self.hexes = [tuple(remap[v] for v in h) for h in raw_hexes]

        neigh = [set() for _ in range(self.N)]
        for h in self.hexes:
            for i in range(6):
                a, b = h[i], h[(i + 1) % 6]
                neigh[a].add(b)
                neigh[b].add(a)
        self.neigh = [tuple(sorted(s)) for s in neigh]

        # Hex faces incident to each vertex (for cheap rosette tests).
        hex_at = [[] for _ in range(self.N)]
        for hi, h in enumerate(self.hexes):
            for v in h:
                hex_at[v].append(hi)
        self.hex_at = [tuple(x) for x in hex_at]


_GEO: dict = {}


def _geo(n: int) -> _Geo:
    g = _GEO.get(n)
    if g is None:
        g = _Geo(n)
        _GEO[n] = g
    return g


# --------------------------------------------------------------------------- #
#  Group / liberty / rosette / capture core
# --------------------------------------------------------------------------- #
def _group(board, start, geo):
    color = board[start]
    seen = {start}
    stack = [start]
    while stack:
        v = stack.pop()
        for nb in geo.neigh[v]:
            if nb not in seen and board.get(nb) == color:
                seen.add(nb)
                stack.append(nb)
    return seen


def _has_liberty(board, group, geo):
    for v in group:
        for nb in geo.neigh[v]:
            if nb not in board:
                return True
    return False


def _has_rosette(group, geo):
    """True iff the group contains all six vertices of some honeycomb cell."""
    for v in group:
        for hi in geo.hex_at[v]:
            if all(w in group for w in geo.hexes[hi]):
                return True
    return False


def _board_key(board, geo):
    return "".join("." if i not in board else "bw"[board[i]] for i in range(geo.N))


def _resolve(board, v, mover, geo):
    """Board after ``mover`` plays at vertex ``v``: capture enemy groups that have
    lost their last liberty and hold no rosette, then (if nothing was captured)
    remove the mover's own group if it is dead and rosette-less (=> suicide).
    Returns (new_board, captured_count). If ``v`` is absent from new_board the
    placement was suicide."""
    nb = dict(board)
    nb[v] = mover
    captured = 0
    enemy = 1 - mover
    done = set()
    for ec in geo.neigh[v]:
        if nb.get(ec) == enemy and ec not in done:
            grp = _group(nb, ec, geo)
            done |= grp
            if not _has_liberty(nb, grp, geo) and not _has_rosette(grp, geo):
                for sq in grp:
                    del nb[sq]
                captured += len(grp)
    if captured == 0:
        own = _group(nb, v, geo)
        if not _has_liberty(nb, own, geo) and not _has_rosette(own, geo):
            for sq in own:
                del nb[sq]
    return nb, captured


def _score(board, geo, komi):
    """Chinese / area score -> (black, white). White includes komi."""
    black = sum(1 for c in board.values() if c == BLACK)
    white = sum(1 for c in board.values() if c == WHITE)
    seen = set()
    for start in range(geo.N):
        if start in board or start in seen:
            continue
        region, border = 0, set()
        stack = [start]
        seen.add(start)
        while stack:
            v = stack.pop()
            region += 1
            for nb in geo.neigh[v]:
                if nb in board:
                    border.add(board[nb])
                elif nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        if border == {BLACK}:
            black += region
        elif border == {WHITE}:
            white += region
    return black, white + komi


# --------------------------------------------------------------------------- #
#  State
# --------------------------------------------------------------------------- #
@dataclass
class RosetteState:
    size: int = 5
    komi: float = 4.5
    board: dict = field(default_factory=dict)      # vertex_id(int) -> player
    to_move: int = BLACK
    passes: int = 0
    ply: int = 0
    last_move: object = None                        # int, "pass", or None
    history: frozenset = field(default_factory=frozenset)   # (board_key, to_move)


class Rosette(Game):
    uid = "rosette"
    name = "Rosette"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        size = int(opts.get("size", 5))
        komi = float(opts.get("komi", 4.5))
        geo = _geo(size)
        s = RosetteState(size=size, komi=komi)
        s.history = frozenset({(_board_key(s.board, geo), BLACK)})
        return s

    def current_player(self, s):
        return s.to_move

    def _ply_cap(self, s):
        return _geo(s.size).N * 2

    def _legal_placements(self, s):
        geo = _geo(s.size)
        opp = 1 - s.to_move
        for v in range(geo.N):
            if v in s.board:
                continue
            nb, captured = _resolve(s.board, v, s.to_move, geo)
            if captured == 0 and v not in nb:
                continue                                    # suicide
            if (_board_key(nb, geo), opp) in s.history:
                continue                                    # situational superko
            yield v, nb

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        return [str(v) for v, _ in self._legal_placements(s)] + ["pass"]

    def apply_move(self, s, move, rng=None):
        geo = _geo(s.size)
        if move == "pass":
            return RosetteState(
                size=s.size, komi=s.komi, board=dict(s.board),
                to_move=1 - s.to_move, passes=s.passes + 1, ply=s.ply + 1,
                last_move="pass", history=s.history)
        v = int(move)
        nb, _cap = _resolve(s.board, v, s.to_move, geo)
        opp = 1 - s.to_move
        return RosetteState(
            size=s.size, komi=s.komi, board=nb, to_move=opp, passes=0,
            ply=s.ply + 1, last_move=v,
            history=s.history | {(_board_key(nb, geo), opp)})

    def is_terminal(self, s):
        return s.passes >= 2 or s.ply >= self._ply_cap(s)

    def returns(self, s):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        b, w = _score(s.board, _geo(s.size), s.komi)
        if b > w:
            return [1.0, -1.0]
        if w > b:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s):
        """Area-balance eval squashed to (-1, 1), as [black, white] payoffs."""
        b, w = _score(s.board, _geo(s.size), s.komi)
        score = math.tanh((b - w) / 8.0)
        return [score, -score]

    # ---- serialization ------------------------------------------------------
    def serialize(self, s):
        lm = s.last_move
        return {
            "size": s.size, "komi": s.komi,
            "board": {str(v): p for v, p in s.board.items()},
            "to_move": s.to_move, "passes": s.passes, "ply": s.ply,
            "last_move": ("pass" if lm == "pass" else (int(lm) if lm is not None else None)),
            "history": sorted([k, tm] for (k, tm) in s.history),
        }

    def deserialize(self, d):
        lm = d.get("last_move")
        return RosetteState(
            size=d["size"], komi=d.get("komi", 4.5),
            board={int(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], passes=d.get("passes", 0), ply=d.get("ply", 0),
            last_move=("pass" if lm == "pass" else (int(lm) if lm is not None else None)),
            history=frozenset((k, tm) for k, tm in d.get("history", [])))

    # ---- presentation -------------------------------------------------------
    def describe_move(self, s, move):
        return "pass" if move == "pass" else f"@{move}"

    def render(self, s, perspective=None):
        geo = _geo(s.size)
        hw = 0.34                                   # vertex-marker half-size
        cells = []
        for v in range(geo.N):
            x, y = geo.coords[v]
            cells.append({"id": str(v), "points": [
                [x - hw, y - hw], [x + hw, y - hw],
                [x + hw, y + hw], [x - hw, y + hw]]})
        # honeycomb edges as under-cell grooves (each edge once)
        lines = []
        for a in range(geo.N):
            ax, ay = geo.coords[a]
            for b in geo.neigh[a]:
                if b > a:
                    bx, by = geo.coords[b]
                    lines.append([[ax, ay], [bx, by]])

        pieces = [{"cell": str(v), "owner": p} for v, p in s.board.items()]
        highlights = []
        if isinstance(s.last_move, int):
            highlights.append({"cell": str(s.last_move), "kind": "last-move"})

        names = {BLACK: "Black", WHITE: "White"}
        b, w = _score(s.board, geo, s.komi)
        if self.is_terminal(s):
            res = "Draw" if b == w else f"{names[BLACK] if b > w else names[WHITE]} wins"
            caption = f"{res} — Black {b:g}, White {w:g} (komi {s.komi:g})"
        else:
            passed = "  ·  opponent passed" if s.last_move == "pass" else ""
            caption = (f"{names[s.to_move]} to move{passed}  ·  "
                       f"score B {b:g} / W {w:g} (komi {s.komi:g})")

        return {
            "board": {"type": "polygons", "cells": cells, "lines": lines},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
