"""Lotus — Christian Freeling (1980s; in Schmittberger's *New Rules for Classic
Games*, 1992).

A Go-like territory game with **Othelloanian (flip) capture** played on the
*vertices* of the Kensington rhombitrihexagonal (3.4.6.4) board — exactly 72
points (each of degree 3 or 4) and 7 hexagons.  The 6 points around any one
hexagon are a **lotus**; a group holding a lotus lives permanently.

Stones are bi-coloured "flip" stones.  A move places a stone on a vacant point,
or passes.  Capture never removes stones: an enemy group with no liberties is
**reversed** (flipped) to the mover's colour, uniting with the adjacent friendly
groups.  If the resulting group *itself* has no liberties the capture was
suicidal and a **second reversal** flips it back.  Suicide is legal (your own
liberty-less group flips to the opponent).  Because stones are only ever added
or flipped — never removed — no ko rule is needed and the stone count strictly
increases, so the game provably terminates.

A **pass marker** on a 15-point track (centre = 0, up to 7 toward each side)
moves one point toward whoever passes; at game end the side it rests on adds
that many points to its score.

The game ends on two consecutive passes.  Score = own stones on the board +
empty points bordered only by own stones + the marker points on your side;
seki / neutral empty points count for neither.  Highest score wins; an exact
tie is a draw.

Board geometry is reproduced verbatim from the Kensington package so the two
share an identical vertex set / adjacency / hexagons (self-contained: pure
stdlib).

Moves (strings):
  * placement — a vertex id, e.g. ``"v17"``.
  * ``"pass"`` — pass (moves the marker toward the passer).
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

from agp.game import Game

# ===========================================================================
# Board geometry — the 7-hexagon rhombitrihexagonal (3.4.6.4) tiling.
# Reproduced (pure stdlib) from the Kensington board so both packages share the
# SAME 72 vertices (v0..v71), adjacency and 7 hexagons.  Lotus does not use the
# squares / triangles or the hexagon colours, so those are dropped here.
# ===========================================================================

_D = math.sqrt(3) + 1.0
_NEIGHBOR_DIRS = [30, 90, 150, 210, 270, 330]
_CENTERS = [(0.0, 0.0)] + [
    (_D * math.cos(math.radians(a)), _D * math.sin(math.radians(a)))
    for a in _NEIGHBOR_DIRS
]


def _hex_vertices(cx, cy, r=1.0):
    return [(cx + r * math.cos(math.radians(60 * k)),
             cy + r * math.sin(math.radians(60 * k))) for k in range(6)]


def _rk(x, y):
    return (round(x, 4), round(y, 4))


def _build():
    coords = {}                                        # rounded-key -> (x, y)

    def add(x, y):
        k = _rk(x, y)
        coords.setdefault(k, (x, y))
        return k

    hex_keys = []
    for (cx, cy) in _CENTERS:
        hex_keys.append([add(*p) for p in _hex_vertices(cx, cy)])

    # Squares: one on each hexagon edge, pushed outward by 1 — adding their outer
    # corners completes the vertex set (identical to Kensington's construction).
    for hi, (cx, cy) in enumerate(_CENTERS):
        vs = [coords[k] for k in hex_keys[hi]]
        for i in range(6):
            p1, p2 = vs[i], vs[(i + 1) % 6]
            mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            dx, dy = mx - cx, my - cy
            L = math.hypot(dx, dy)
            nx, ny = dx / L, dy / L
            add(p1[0] + nx, p1[1] + ny)
            add(p2[0] + nx, p2[1] + ny)

    keys = list(coords)
    adj = {k: set() for k in keys}
    for a, b in itertools.combinations(keys, 2):
        pa, pb = coords[a], coords[b]
        if abs(math.hypot(pa[0] - pb[0], pa[1] - pb[1]) - 1.0) < 1e-3:
            adj[a].add(b)
            adj[b].add(a)

    # Stable ids: top-to-bottom (y desc), then left-to-right (x asc).
    order = sorted(keys, key=lambda k: (-round(coords[k][1], 3), round(coords[k][0], 3)))
    vid = {k: f"v{i}" for i, k in enumerate(order)}

    verts = {vid[k]: (round(coords[k][0], 4), round(coords[k][1], 4)) for k in keys}
    adj_out = {vid[k]: tuple(sorted((vid[x] for x in adj[k]), key=lambda s: int(s[1:])))
               for k in keys}
    hexes = [frozenset(vid[k] for k in hex_keys[hi]) for hi in range(7)]
    return verts, adj_out, hexes


VERTS, ADJ, HEXES = _build()
POINTS = list(VERTS.keys())

# Cosmetic geometry for the renderer -----------------------------------------
_seen = set()
EDGE_SEGMENTS = []
for _p, _nbrs in ADJ.items():
    for _q in _nbrs:
        _key = tuple(sorted((_p, _q)))
        if _key in _seen:
            continue
        _seen.add(_key)
        EDGE_SEGMENTS.append([list(VERTS[_p]), list(VERTS[_q])])


def hex_outline_lines():
    """Closed neutral polylines tracing each hexagon (the 7 lotus sites)."""
    out = []
    for h in HEXES:
        vs = list(h)
        cx = sum(VERTS[v][0] for v in vs) / 6
        cy = sum(VERTS[v][1] for v in vs) / 6
        vs.sort(key=lambda v: math.atan2(VERTS[v][1] - cy, VERTS[v][0] - cx))
        loop = [list(VERTS[v]) for v in vs]
        loop.append(loop[0])
        loop.append("#cbb26b")                         # muted lotus-gold outline
        out.append(loop)
    return out


# ===========================================================================
# Game
# ===========================================================================

WHITE, BLACK = 0, 1                                    # White moves first
MARKER_CAP = 7                                         # 15-point track: 7 each side of centre


# ---- pure board helpers (operate on a {vertex: player} dict) ----------------

def _group(pos, start):
    """Connected same-colour component containing ``start``."""
    color = pos[start]
    seen = {start}
    stack = [start]
    while stack:
        p = stack.pop()
        for q in ADJ[p]:
            if q not in seen and pos.get(q) == color:
                seen.add(q)
                stack.append(q)
    return seen


def _has_liberty(pos, group):
    for p in group:
        for q in ADJ[p]:
            if q not in pos:
                return True
    return False


def _has_lotus(group):
    """A group lives unconditionally if it holds all 6 vertices of some hexagon."""
    for h in HEXES:
        if h <= group:
            return True
    return False


def _resolve(pos, p, mover):
    """Return the board after ``mover`` places a stone at vacant point ``p``.

    Othelloanian (flip) capture with cascade, lotus immunity and legal suicide:
      1. Enemy groups adjacent to ``p`` that now have no liberty (and hold no
         lotus) are reversed to ``mover`` and united with the capturing group.
         If that new group *itself* has no liberty (and no lotus) the capture
         was suicidal -> a second reversal flips the whole group back.
      2. If nothing was captured and ``mover``'s own group has no liberty (and
         no lotus) the move is suicide -> the group flips to the opponent.
    """
    pos = dict(pos)
    pos[p] = mover
    enemy = 1 - mover

    captured = False
    done = set()
    for q in ADJ[p]:
        if pos.get(q) == enemy and q not in done:
            grp = _group(pos, q)
            done |= grp
            if not _has_liberty(pos, grp) and not _has_lotus(grp):
                for v in grp:
                    pos[v] = mover                     # reverse (flip) to mover
                captured = True

    if captured:
        united = _group(pos, p)                        # the new mover-coloured group
        if not _has_liberty(pos, united) and not _has_lotus(united):
            for v in united:                           # second reversal (suicidal capture)
                pos[v] = enemy
        return pos

    own = _group(pos, p)
    if not _has_liberty(pos, own) and not _has_lotus(own):
        for v in own:                                  # legal suicide
            pos[v] = enemy
    return pos


def _score(pos, marker):
    """Area score -> (white, black): stones + solely-bordered empty points +
    the marker points for the side the marker rests on."""
    white = sum(1 for v in pos.values() if v == WHITE)
    black = sum(1 for v in pos.values() if v == BLACK)
    seen = set()
    for p in POINTS:
        if p in pos or p in seen:
            continue
        region, border = set(), set()
        stack = [p]
        seen.add(p)
        while stack:
            cur = stack.pop()
            region.add(cur)
            for q in ADJ[cur]:
                if q in pos:
                    border.add(pos[q])
                elif q not in seen:
                    seen.add(q)
                    stack.append(q)
        if border == {WHITE}:
            white += len(region)
        elif border == {BLACK}:
            black += len(region)
        # bordered by both, or by neither (empty board) -> neutral / seki
    if marker > 0:
        white += marker
    elif marker < 0:
        black += -marker
    return white, black


@dataclass
class LState:
    pos: dict = field(default_factory=dict)            # vertex -> player
    to_move: int = WHITE
    marker: int = 0                                    # >0 toward White, <0 toward Black
    passes: int = 0                                    # consecutive passes
    ply: int = 0
    last: object = None                                # vertex id, "pass", or None


class Lotus(Game):
    uid = "lotus"
    name = "Lotus"
    PLY_CAP = len(POINTS) * 4                           # safety net (game already terminates)

    @property
    def num_players(self):
        return 2

    # ---- lifecycle ---------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        return LState()

    def current_player(self, state):
        return state.to_move

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        # Suicide is legal and there is no ko, so EVERY empty point is playable.
        moves = [p for p in POINTS if p not in state.pos]
        moves.append("pass")
        return moves

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        if move == "pass":
            step = 1 if pl == WHITE else -1
            marker = max(-MARKER_CAP, min(MARKER_CAP, state.marker + step))
            return LState(pos=dict(state.pos), to_move=1 - pl, marker=marker,
                          passes=state.passes + 1, ply=state.ply + 1, last="pass")
        pos = _resolve(state.pos, move, pl)
        return LState(pos=pos, to_move=1 - pl, marker=state.marker,
                      passes=0, ply=state.ply + 1, last=move)

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        return state.passes >= 2 or state.ply >= self.PLY_CAP

    def returns(self, state):
        if not self.is_terminal(state):
            return [0.0, 0.0]
        w, b = _score(state.pos, state.marker)
        if w > b:
            return [1.0, -1.0]
        if b > w:
            return [-1.0, 1.0]
        return [0.0, 0.0]                               # honest draw

    # ---- MCTS rollout-cutoff heuristic -------------------------------------
    def heuristic(self, state):
        w = sum(1 for v in state.pos.values() if v == WHITE)
        b = sum(1 for v in state.pos.values() if v == BLACK)
        diff = (w - b) + state.marker
        s = math.tanh(diff / 12.0)
        return [s, -s]

    # ---- serialize ---------------------------------------------------------
    def serialize(self, state):
        return {
            "pos": dict(state.pos),
            "to_move": state.to_move,
            "marker": state.marker,
            "passes": state.passes,
            "ply": state.ply,
            "last": state.last,
        }

    def deserialize(self, d):
        return LState(pos=dict(d["pos"]), to_move=d["to_move"],
                      marker=d.get("marker", 0), passes=d.get("passes", 0),
                      ply=d.get("ply", 0), last=d.get("last"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if move == "pass":
            return "pass"
        return f"@{move}"

    def _marker_text(self, marker):
        if marker > 0:
            return f"marker: White +{marker}"
        if marker < 0:
            return f"marker: Black +{-marker}"
        return "marker: centred"

    def render(self, state, perspective=None):
        s = 0.16                                        # vertex-marker half-size
        cells = []
        for p in POINTS:
            x, y = VERTS[p]
            cells.append({"id": p, "points": [
                [x - s, y - s], [x + s, y - s], [x + s, y + s], [x - s, y + s]]})
        pieces = [{"cell": p, "owner": v} for p, v in state.pos.items()]
        lines = hex_outline_lines() + [seg for seg in EDGE_SEGMENTS]

        names = {WHITE: "White", BLACK: "Black"}
        highlights = []
        if isinstance(state.last, str) and state.last != "pass" and state.last in state.pos:
            highlights.append({"cell": state.last, "kind": "last-move"})

        w, b = _score(state.pos, state.marker)
        if self.is_terminal(state):
            if w == b:
                res = "Draw"
            else:
                res = f"{names[WHITE] if w > b else names[BLACK]} wins"
            cap = f"{res} — White {w}, Black {b} · {self._marker_text(state.marker)}"
        else:
            passed = "  ·  opponent passed" if state.last == "pass" else ""
            cap = (f"{names[state.to_move]} to move{passed}  ·  "
                   f"score W {w} / B {b} · {self._marker_text(state.marker)}")

        return {
            "board": {"type": "polygons", "cells": cells, "lines": lines},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
