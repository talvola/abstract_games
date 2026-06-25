"""Kensington — Brian Taylor & Peter Forbes (1979).

A two-phase placement/movement game on the *vertices* of a 7-hexagon
rhombitrihexagonal (3.4.6.4) tessellation: 72 vertices, 30 squares, 24
triangles and 7 hexagons (3 white down the middle, 2 red, 2 blue).

PLACEMENT.  Red and Blue alternately drop one of their 15 counters on any empty
vertex until both have placed all 15.

MOVEMENT.  Players then alternate, sliding one of their counters along a line
to an adjacent empty vertex.

MILLS (both phases).  Completing all 3 vertices of a *triangle* with your move
lets you relocate one enemy counter to any vacant vertex; completing all 4
vertices of a *square* lets you relocate two — but no more than two relocations
per turn even if several mills form at once.

WIN.  Occupy all 6 vertices of any **white** hexagon, or of a hexagon of your
**own** colour (Red owns the red hexagons, Blue the blue). Achievable in either
phase.

TERMINATION.  The movement phase can shuffle forever, so a no-progress ply cap
forces a draw (see ``DRAW_PLIES``).

Moves (strings):
  * placement   — a vertex id, e.g. ``"v17"``.
  * slide       — ``"from>to"``, e.g. ``"v17>v25"``.
  * relocation  — ``"from>to"`` (enemy vertex -> any vacant vertex); the engine
    knows it is a relocation because ``state.relo`` > 0.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

from agp.game import Game

# ===========================================================================
# Board geometry — the 7-hexagon rhombitrihexagonal (3.4.6.4) tiling.
# Generated deterministically (pure stdlib) at import time so the data is
# self-documenting and auditable. Produces exactly the published Kensington
# board: 72 vertices, 7 hexagons (3 WHITE down the vertical middle, 2 RED on
# one side, 2 BLUE on the other), 30 squares, 24 triangles, 132 edges.
# Vertices are numbered v0..v71 top-to-bottom, then left-to-right.
# ===========================================================================

# Hexagon edge length = 1. Flat-vertex hexagons (vertices at 0,60,...,300 deg).
# In the 3.4.6.4 tiling a unit square sits on every hexagon edge, so neighbouring
# hexagon centres are 2*apothem + 1 = sqrt(3)+1 apart.
_D = math.sqrt(3) + 1.0
# 1 central hexagon + 6 around it (a "flower"). White = the vertical pillar
# (centre + top + bottom), Red = the two on the +x side, Blue = the two on -x.
_NEIGHBOR_DIRS = [30, 90, 150, 210, 270, 330]
_CENTERS = [(0.0, 0.0)] + [
    (_D * math.cos(math.radians(a)), _D * math.sin(math.radians(a)))
    for a in _NEIGHBOR_DIRS
]
# index into _CENTERS -> colour. centre=0; 1..6 = dirs 30,90,150,210,270,330.
_HEXCOLOR = {0: "white", 2: "white", 5: "white",   # x=0 vertical pillar
             1: "red", 6: "red",                    # +x side
             3: "blue", 4: "blue"}                   # -x side


def _hex_vertices(cx, cy, r=1.0):
    return [(cx + r * math.cos(math.radians(60 * k)),
             cy + r * math.sin(math.radians(60 * k))) for k in range(6)]


def _rk(x, y):
    return (round(x, 4), round(y, 4))


def _build():
    coords = {}            # rounded-key -> (x, y)

    def add(x, y):
        k = _rk(x, y)
        coords.setdefault(k, (x, y))
        return k

    hex_keys = []
    for (cx, cy) in _CENTERS:
        hex_keys.append([add(*p) for p in _hex_vertices(cx, cy)])

    # Squares: one on each hexagon edge, pushed outward by 1 (the square's far
    # side). Adding their outer corners completes the vertex set.
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

    # Edges = every pair of vertices at distance 1 (the tiling's unit edges).
    keys = list(coords)
    adj = {k: set() for k in keys}
    for a, b in itertools.combinations(keys, 2):
        pa, pb = coords[a], coords[b]
        if abs(math.hypot(pa[0] - pb[0], pa[1] - pb[1]) - 1.0) < 1e-3:
            adj[a].add(b)
            adj[b].add(a)

    # Squares (dedup): rebuild each hex-edge square and canonicalise by vertex set.
    squares = {}
    for hi, (cx, cy) in enumerate(_CENTERS):
        vs = [coords[k] for k in hex_keys[hi]]
        for i in range(6):
            p1, p2 = vs[i], vs[(i + 1) % 6]
            mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            dx, dy = mx - cx, my - cy
            L = math.hypot(dx, dy)
            nx, ny = dx / L, dy / L
            sq = frozenset([_rk(p1[0], p1[1]), _rk(p2[0], p2[1]),
                            _rk(p2[0] + nx, p2[1] + ny), _rk(p1[0] + nx, p1[1] + ny)])
            squares[sq] = sq

    # Triangles = 3-cliques in the adjacency (all edges unit length).
    tris = set()
    for a in keys:
        for b in adj[a]:
            for c in adj[b]:
                if c in adj[a] and len({a, b, c}) == 3:
                    tris.add(frozenset((a, b, c)))

    # Stable ids: top-to-bottom (y desc), then left-to-right (x asc).
    order = sorted(keys, key=lambda k: (-round(coords[k][1], 3), round(coords[k][0], 3)))
    vid = {k: f"v{i}" for i, k in enumerate(order)}

    verts = {vid[k]: (round(coords[k][0], 4), round(coords[k][1], 4)) for k in keys}
    adj_out = {vid[k]: tuple(sorted((vid[x] for x in adj[k]), key=lambda s: int(s[1:])))
               for k in keys}
    hexes = [{"color": _HEXCOLOR[hi],
              "verts": tuple(sorted((vid[k] for k in hex_keys[hi]), key=lambda s: int(s[1:])))}
             for hi in range(7)]
    square_sets = [frozenset(vid[k] for k in sq) for sq in squares]
    tri_sets = [frozenset(vid[k] for k in t) for t in tris]
    return verts, adj_out, hexes, square_sets, tri_sets


VERTS, ADJ, HEXES, SQUARES, TRIANGLES = _build()
POINTS = list(VERTS.keys())

# Mills indexed by the polygons each vertex belongs to (for fast newly-formed checks).
TRIANGLES_AT = {p: [t for t in TRIANGLES if p in t] for p in POINTS}
SQUARES_AT = {p: [s for s in SQUARES if p in s] for p in POINTS}
HEXES_AT = {p: [h for h in HEXES if p in h["verts"]] for p in POINTS}

# Cosmetic geometry for the renderer.
# Tessellation edges (deduped): list of [[x,y],[x,y]] segments in vertex-coord space.
_seen = set()
EDGE_SEGMENTS = []
for _p, _nbrs in ADJ.items():
    for _q in _nbrs:
        _key = tuple(sorted((_p, _q)))
        if _key in _seen:
            continue
        _seen.add(_key)
        EDGE_SEGMENTS.append([list(VERTS[_p]), list(VERTS[_q])])

# Coloured hexagon outlines: a closed 7-point polyline per hex, trailing colour.
_HEXFILL = {"white": "#d8d8d8", "red": "#d8463c", "blue": "#3a6fd8"}


def hex_outline_lines():
    """Closed coloured polylines tracing each hexagon (for ``board.lines``)."""
    out = []
    for h in HEXES:
        vs = list(h["verts"])
        cx = sum(VERTS[v][0] for v in vs) / 6
        cy = sum(VERTS[v][1] for v in vs) / 6
        vs.sort(key=lambda v: math.atan2(VERTS[v][1] - cy, VERTS[v][0] - cx))
        loop = [list(VERTS[v]) for v in vs]
        loop.append(loop[0])
        loop.append(_HEXFILL[h["color"]])
        out.append(loop)
    return out


# ===========================================================================
# Game
# ===========================================================================

RED, BLUE = 0, 1
COUNTERS = 15
_OWN_COLOR = {RED: "red", BLUE: "blue"}


@dataclass
class KState:
    pos: dict = field(default_factory=dict)        # vertex -> player
    to_move: int = RED
    placed: list = field(default_factory=lambda: [0, 0])  # counters placed per player
    relo: int = 0                                   # pending enemy relocations this turn
    since_progress: int = 0                         # plies since a placement/mill (draw clock)
    winner: object = None                           # set when a hexagon is captured


class Kensington(Game):
    uid = "kensington"
    name = "Kensington"
    COUNTERS = COUNTERS
    DRAW_PLIES = 60        # movement plies with no placement/mill -> draw

    @property
    def num_players(self):
        return 2

    # ---- lifecycle ---------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        return KState()

    def current_player(self, state):
        return state.to_move

    # ---- phase helpers -----------------------------------------------------
    def _placing(self, state):
        """True while either player still has counters to place."""
        return state.placed[RED] < self.COUNTERS or state.placed[BLUE] < self.COUNTERS

    def _color_owns(self, pl, hexcolor):
        return hexcolor == "white" or hexcolor == _OWN_COLOR[pl]

    def _winning_hex(self, pos, pl):
        """A hexagon the given player has fully occupied and is allowed to win on."""
        for h in HEXES:
            if self._color_owns(pl, h["color"]) and all(pos.get(v) == pl for v in h["verts"]):
                return True
        return False

    def _newly_completed(self, pos, vertex, pl):
        """How many relocations the move that just landed on ``vertex`` earns.

        A triangle the player now fully owns (and that contains ``vertex``)
        scores 1; a square scores 2. Capped at 2 total per turn.
        """
        gained = 0
        for t in TRIANGLES_AT[vertex]:
            if all(pos.get(v) == pl for v in t):
                gained += 1
        for s in SQUARES_AT[vertex]:
            if all(pos.get(v) == pl for v in s):
                gained += 2
        return min(2, gained)

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        pl = state.to_move

        if state.relo > 0:
            # relocate an enemy counter to any vacant vertex
            enemies = [p for p, v in state.pos.items() if v != pl]
            empties = [p for p in POINTS if p not in state.pos]
            return [f"{e}>{t}" for e in enemies for t in empties]

        if self._placing(state):
            return [p for p in POINTS if p not in state.pos]

        # movement phase: slide along an edge to an empty adjacent vertex
        out = []
        for p, v in state.pos.items():
            if v != pl:
                continue
            for q in ADJ[p]:
                if q not in state.pos:
                    out.append(f"{p}>{q}")
        return out

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        pos = dict(state.pos)
        placed = list(state.placed)
        since = state.since_progress

        if state.relo > 0:
            frm, to = move.split(">")
            pos[to] = pos.pop(frm)                 # move the enemy counter
            relo = state.relo - 1
            # relocating an enemy might itself complete one of MY hexagons? No — it
            # only moves an ENEMY counter, so check the enemy doesn't auto-win and I
            # may have freed a square... we re-check wins for both sides below.
            return self._settle(pos, pl, placed, relo, since, state)

        if ">" in move:                            # slide
            frm, to = move.split(">")
            pos[to] = pos.pop(frm)
            landed = to
            since = since + 1
        else:                                      # placement
            pos[move] = pl
            placed[pl] += 1
            landed = move
            since = 0

        gained = self._newly_completed(pos, landed, pl)
        # progress resets on a mill (a capture is progress)
        if gained > 0:
            since = 0
        # only relocate if there is at least one enemy counter and a vacant vertex
        enemies = any(v != pl for v in pos.values())
        empties = any(p not in pos for p in POINTS)
        relo = gained if (gained > 0 and enemies and empties) else 0
        return self._settle(pos, pl, placed, relo, since, state)

    def _settle(self, pos, mover, placed, relo, since, state):
        """Build the next state, checking the win and whether the turn continues."""
        # Win check: did the move give *anyone* a completed eligible hexagon?
        # The mover is the natural winner, but a relocation could in principle
        # complete the enemy's hexagon (they'd then win) — check mover first.
        winner = state.winner
        if winner is None:
            if self._winning_hex(pos, mover):
                winner = mover
            elif self._winning_hex(pos, 1 - mover):
                winner = 1 - mover

        if winner is not None:
            ns = KState(pos=pos, to_move=mover, placed=placed, relo=0,
                        since_progress=since, winner=winner)
            return ns

        if relo > 0:
            # same player keeps the turn to perform the relocation(s)
            return KState(pos=pos, to_move=mover, placed=placed, relo=relo,
                          since_progress=since, winner=None)

        # turn passes. If the next player has no legal move (movement phase),
        # the rule is: the opponent keeps moving until they can move again.
        nxt = 1 - mover
        ns = KState(pos=pos, to_move=nxt, placed=placed, relo=0,
                    since_progress=since, winner=None)
        if not self._placing(ns) and not self._draw(ns):
            if not self._has_slide(ns, nxt):
                if self._has_slide(ns, mover):
                    ns.to_move = mover            # blocked player is skipped
                # else: neither can move -> stalemate handled by is_terminal/draw
        return ns

    def _has_slide(self, state, pl):
        for p, v in state.pos.items():
            if v == pl and any(q not in state.pos for q in ADJ[p]):
                return True
        return False

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        if state.winner is not None:
            return False
        if self._placing(state):
            return False
        # no-progress cap
        if state.since_progress >= self.DRAW_PLIES:
            return True
        # total stalemate: nobody can slide
        if not self._has_slide(state, RED) and not self._has_slide(state, BLUE):
            return True
        return False

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialize ---------------------------------------------------------
    def serialize(self, state):
        return {
            "pos": dict(state.pos),
            "to_move": state.to_move,
            "placed": list(state.placed),
            "relo": state.relo,
            "since_progress": state.since_progress,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return KState(pos=dict(d["pos"]), to_move=d["to_move"],
                      placed=list(d["placed"]), relo=d.get("relo", 0),
                      since_progress=d.get("since_progress", 0),
                      winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if state.relo > 0:
            return f"reloc {move.replace('>', '->')}"
        if ">" in move:
            return move.replace(">", "-")
        return f"@{move}"

    def render(self, state, perspective=None):
        s = 0.16   # vertex-marker half-size
        cells = []
        for p in POINTS:
            x, y = VERTS[p]
            cells.append({"id": p, "points": [
                [x - s, y - s], [x + s, y - s], [x + s, y + s], [x - s, y + s]]})
        pieces = [{"cell": p, "owner": v} for p, v in state.pos.items()]
        # coloured hexagon outlines first, then the thin grid edges
        lines = hex_outline_lines() + [seg for seg in EDGE_SEGMENTS]

        names = {RED: "Red", BLUE: "Blue"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        elif state.relo > 0:
            cap = f"{names[state.to_move]}: relocate enemy counter ({state.relo} left)"
        elif self._placing(state):
            left = self.COUNTERS - state.placed[state.to_move]
            cap = f"{names[state.to_move]} to place ({left} in hand)"
        else:
            cap = f"{names[state.to_move]} to move"

        return {
            "board": {"type": "polygons", "cells": cells, "lines": lines},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
