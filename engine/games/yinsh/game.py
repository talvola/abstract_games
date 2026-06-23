"""YINSH -- Kris Burm's GIPF project #5: a rings-and-markers game.

Board: the 85-point YINSH lattice. A point is a lattice coordinate ``(x, y)``
with ``x, y in [-5, 5]`` satisfying ``(0.5*sqrt(3)*x)^2 + (0.5*x - y)^2 <= 4.6^2``
(this is the authoritative geometry used by published implementations -- it
yields exactly 85 intersections in columns of length 4,7,8,9,10,9,10,9,8,7,4).
Points are connected along THREE line families:

  * constant x      -- step (0, +-1)
  * constant y      -- step (+-1, 0)
  * constant (x-y)  -- step (+-1, +-1)   [i.e. (1,1)/(-1,-1)]

Each player has 5 RINGS; the markers are a shared, flippable supply (51 in the
physical game -- here effectively unbounded but bounded by board size and a
defensive ply cap).

Setup phase: players alternate placing their 5 rings on empty points; White
(player 0) first; 10 placements total.

Play phase, each turn:
  1. place a MARKER of your colour on the point inside one of YOUR rings;
  2. MOVE that ring in a straight line: it slides over empty points and, on
     reaching the first occupied point, must JUMP the contiguous run of MARKERS
     (either colour) and land on the first EMPTY point beyond. A ring may never
     pass over or land on another RING (rings block). Every jumped marker is
     FLIPPED. A ring must move at least one point.

Forming a ROW of FIVE+ consecutive markers of one colour: the OWNER removes
exactly five of them and then removes ONE of their own rings (set aside). The
MOVER resolves their own row(s) first, then the opponent resolves any row(s)
the move created for them.

WIN: first player to remove THREE of their own rings wins. If the move-step
budget (ply cap) is hit with nobody at 3, the player who has removed more rings
wins (tie -> draw).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

# ---- board geometry --------------------------------------------------------

_SQRT3 = math.sqrt(3.0)
_R2 = 4.6 * 4.6


def _inside(x, y):
    return (0.5 * _SQRT3 * x) ** 2 + (0.5 * x - y) ** 2 <= _R2


POINTS = [(x, y) for x in range(-5, 6) for y in range(-5, 6) if _inside(x, y)]
POINT_SET = set(POINTS)
ID = {p: f"{p[0]},{p[1]}" for p in POINTS}            # (x,y) -> "x,y"
PT = {v: k for k, v in ID.items()}                    # "x,y" -> (x,y)
POINT_IDS = [ID[p] for p in POINTS]

# Three line direction axes (each a +/- pair). A "direction" is a unit step.
AXES = [(0, 1), (1, 0), (1, 1)]
DIRS = [(dx, dy) for (dx, dy) in AXES] + [(-dx, -dy) for (dx, dy) in AXES]


def _screen(x, y):
    """Orthogonal screen coords from the board's own validity metric.

    u = 0.5*sqrt3*x (horizontal), v = 0.5*x - y (vertical). Used for the
    polygons renderer so the triangular lattice draws correctly.
    """
    return 0.5 * _SQRT3 * x, 0.5 * x - y


# Cosmetic grid lines: for each of the three axes, draw the maximal segment of
# every line that has >= 2 points, in screen space.
def _grid_lines():
    segs = []
    for (dx, dy) in AXES:
        seen = set()
        for p in POINTS:
            if p in seen:
                continue
            # walk back to the start of this line
            sx, sy = p
            while (sx - dx, sy - dy) in POINT_SET:
                sx, sy = sx - dx, sy - dy
            line = []
            cx, cy = sx, sy
            while (cx, cy) in POINT_SET:
                seen.add((cx, cy))
                line.append((cx, cy))
                cx, cy = cx + dx, cy + dy
            if len(line) >= 2:
                a = _screen(*line[0])
                b = _screen(*line[-1])
                segs.append([[a[0], a[1]], [b[0], b[1]]])
    return segs


LINES = _grid_lines()


# ---- state -----------------------------------------------------------------

@dataclass
class YState:
    rings: dict = field(default_factory=dict)       # "x,y" -> owner (0/1)
    markers: dict = field(default_factory=dict)     # "x,y" -> owner (0/1)
    to_move: int = 0
    phase: str = "setup"                            # "setup" | "play"
    placed: list = field(default_factory=lambda: [0, 0])   # rings placed (setup)
    removed: list = field(default_factory=lambda: [0, 0])  # rings removed (score)
    # row-resolution queue: when non-empty, `resolver` must remove a row.
    resolver: object = None                         # player who must resolve, or None
    next_player: int = 0                            # whose normal turn after resolution
    winner: object = None
    plies: int = 0


# ---- helpers ---------------------------------------------------------------

def _ray(src, d):
    """Points from src (exclusive) stepping by d until off-board."""
    x, y = PT[src]
    dx, dy = d
    out = []
    x, y = x + dx, y + dy
    while (x, y) in POINT_SET:
        out.append(ID[(x, y)])
        x, y = x + dx, y + dy
    return out


def _ring_moves(state, src):
    """Legal destinations for the ring at src under YINSH sliding rules."""
    dests = []
    rings = state.rings
    markers = state.markers
    for d in DIRS:
        jumped = False
        for cell in _ray(src, d):
            if cell in rings:
                break                       # rings block: cannot pass/land
            if cell in markers:
                jumped = True               # entering / continuing a marker run
                continue
            # empty cell
            dests.append(cell)
            if jumped:
                break                       # after a jump, must land here
            # not yet jumped: may keep sliding over empties
    return dests


def _markers_between(src, dst):
    """The marker-run cells strictly between src and dst (the jumped run)."""
    sx, sy = PT[src]
    dx2, dy2 = PT[dst]
    ddx = (dx2 > sx) - (dx2 < sx)
    ddy = (dy2 > sy) - (dy2 < sy)
    out = []
    x, y = sx + ddx, sy + ddy
    while (x, y) != (dx2, dy2):
        out.append(ID[(x, y)])
        x, y = x + ddx, y + ddy
    return out


def _find_rows(markers, owner):
    """All maximal runs of >=5 consecutive `owner` markers, as lists of cell ids.

    Returned as the set of distinct 5+ runs (one per maximal segment); the
    caller turns each into concrete removable rows.
    """
    rows = []
    for (dx, dy) in AXES:
        seen = set()
        for p in POINTS:
            cid = ID[p]
            if (p, (dx, dy)) in seen:
                continue
            # start of this line
            sx, sy = p
            while (sx - dx, sy - dy) in POINT_SET:
                sx, sy = sx - dx, sy - dy
            line = []
            cx, cy = sx, sy
            while (cx, cy) in POINT_SET:
                seen.add(((cx, cy), (dx, dy)))
                line.append(ID[(cx, cy)])
                cx, cy = cx + dx, cy + dy
            # scan for maximal runs of owner's markers
            run = []
            for c in line + [None]:
                if c is not None and markers.get(c) == owner:
                    run.append(c)
                else:
                    if len(run) >= 5:
                        rows.append(list(run))
                    run = []
    return rows


def _has_row(markers, owner):
    return bool(_find_rows(markers, owner))


# ---- game ------------------------------------------------------------------

class Yinsh(Game):
    uid = "yinsh"
    name = "YINSH"
    RINGS = 5
    WIN_RINGS = 3
    PLY_CAP = 800        # defensive termination bound (markers are finite)

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return YState()

    def current_player(self, state):
        if state.resolver is not None:
            return state.resolver
        return state.to_move

    # ---- legal moves -------------------------------------------------------
    def legal_moves(self, state):
        if state.winner is not None or state.plies >= self.PLY_CAP:
            return []

        if state.resolver is not None:
            return self._removal_moves(state, state.resolver)

        if state.phase == "setup":
            return [c for c in POINT_IDS
                    if c not in state.rings and c not in state.markers]

        # play phase: place marker in one of your rings, then move that ring
        pl = state.to_move
        out = []
        for src, owner in state.rings.items():
            if owner != pl:
                continue
            if src in state.markers:        # ring's point must be empty of a marker
                continue
            for dst in _ring_moves(state, src):
                out.append(f"{src}>{dst}")
        return out

    def _removal_moves(self, state, pl):
        """Moves of the form 'R:c1,c2,c3,c4,c5|ringPoint' for player pl."""
        rows = _find_rows(state.markers, pl)
        my_rings = [c for c, o in state.rings.items() if o == pl]
        moves = []
        seen = set()
        for row in rows:
            # choose any 5 consecutive within this run (handles 6+ in a line)
            for i in range(0, len(row) - 4):
                five = tuple(row[i:i + 5])
                for ring in my_rings:
                    key = (five, ring)
                    if key in seen:
                        continue
                    seen.add(key)
                    moves.append("R:" + ">".join(five) + "|" + ring)
        return moves

    # ---- apply -------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        if state.resolver is not None:
            return self._apply_removal(state, move)
        if state.phase == "setup":
            return self._apply_setup(state, move)
        return self._apply_play(state, move)

    def _clone(self, state):
        return YState(
            rings=dict(state.rings), markers=dict(state.markers),
            to_move=state.to_move, phase=state.phase,
            placed=list(state.placed), removed=list(state.removed),
            resolver=state.resolver, next_player=state.next_player,
            winner=state.winner, plies=state.plies + 1,
        )

    def _apply_setup(self, state, move):
        ns = self._clone(state)
        pl = ns.to_move
        ns.rings[move] = pl
        ns.placed[pl] += 1
        if ns.placed[0] >= self.RINGS and ns.placed[1] >= self.RINGS:
            ns.phase = "play"
            ns.to_move = 0
        else:
            ns.to_move = 1 - pl
        return ns

    def _apply_play(self, state, move):
        ns = self._clone(state)
        pl = ns.to_move
        src, dst = move.split(">")
        # 1) drop a marker of pl on the ring's point
        ns.markers[src] = pl
        # 2) move the ring
        del ns.rings[src]
        ns.rings[dst] = pl
        # 3) flip every jumped marker (intervening cells that hold a marker)
        for c in _markers_between(src, dst):
            if c in ns.markers:
                ns.markers[c] = 1 - ns.markers[c]

        # Resolution: mover first, then opponent. Set up the resolver queue.
        ns.next_player = 1 - pl
        if _has_row(ns.markers, pl):
            ns.resolver = pl
        elif _has_row(ns.markers, 1 - pl):
            ns.resolver = 1 - pl
        else:
            ns.resolver = None
            ns.to_move = 1 - pl
        return ns

    def _apply_removal(self, state, move):
        ns = self._clone(state)
        pl = ns.resolver
        body, ring = move.split("|")
        cells = body[2:].split(">")          # strip "R:"
        for c in cells:
            del ns.markers[c]
        del ns.rings[ring]
        ns.removed[pl] += 1

        if ns.removed[pl] >= self.WIN_RINGS:
            ns.winner = pl
            ns.resolver = None
            return ns

        # more rows for the same player? they resolve all of theirs first.
        if _has_row(ns.markers, pl):
            ns.resolver = pl
            return ns
        # then the OTHER player resolves any rows the move created for them.
        other = 1 - pl
        if _has_row(ns.markers, other):
            ns.resolver = other
            return ns
        # done resolving -> normal turn passes
        ns.resolver = None
        ns.to_move = ns.next_player
        return ns

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        if state.winner is not None:
            return True
        return state.plies >= self.PLY_CAP

    def returns(self, state):
        if state.winner is not None:
            return [1.0 if i == state.winner else -1.0 for i in range(2)]
        # ply cap reached: more removed rings wins; tie -> draw
        if state.removed[0] > state.removed[1]:
            return [1.0, -1.0]
        if state.removed[1] > state.removed[0]:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- serialize ---------------------------------------------------------
    def serialize(self, state):
        return {
            "rings": dict(state.rings),
            "markers": dict(state.markers),
            "to_move": state.to_move,
            "phase": state.phase,
            "placed": list(state.placed),
            "removed": list(state.removed),
            "resolver": state.resolver,
            "next_player": state.next_player,
            "winner": state.winner,
            "plies": state.plies,
        }

    def deserialize(self, d):
        return YState(
            rings=dict(d["rings"]), markers=dict(d["markers"]),
            to_move=d["to_move"], phase=d["phase"],
            placed=list(d["placed"]), removed=list(d["removed"]),
            resolver=d.get("resolver"), next_player=d.get("next_player", 0),
            winner=d.get("winner"), plies=d.get("plies", 0),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if move.startswith("R:"):
            body, ring = move.split("|")
            cells = body[2:].split(">")
            return f"row {cells[0]}-{cells[-1]} x-ring {ring}"
        if ">" in move:
            return move.replace(">", "-")
        return f"ring@{move}"

    def render(self, state, perspective=None):
        cells = []
        s = 0.34
        for p in POINTS:
            u, v = _screen(*p)
            cells.append({
                "id": ID[p],
                "points": [[u - s, v - s], [u + s, v - s],
                           [u + s, v + s], [u - s, v + s]],
            })
        pieces = []
        # markers (small filled discs in owner colour)
        for c, o in state.markers.items():
            # a marker sitting inside a ring is rendered via the ring's "inner"
            if c in state.rings:
                continue
            pieces.append({"cell": c, "owner": o, "shape": "marker"})
        # rings (hollow ring in owner colour; show inner marker if present)
        for c, o in state.rings.items():
            pc = {"cell": c, "owner": o, "shape": "ring"}
            if c in state.markers:
                pc["inner"] = state.markers[c]
            pieces.append(pc)

        names = {0: "White", 1: "Black"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif state.plies >= self.PLY_CAP:
            cap = "Draw (move cap)"
        elif state.resolver is not None:
            cap = f"{names[state.resolver]}: remove a row of 5 + one ring"
        elif state.phase == "setup":
            left = self.RINGS - state.placed[state.to_move]
            cap = f"{names[state.to_move]} to place a ring ({left} left)"
        else:
            cap = (f"{names[state.to_move]} to move "
                   f"(rings removed {state.removed[0]}-{state.removed[1]})")
        return {
            "board": {"type": "polygons", "cells": cells, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
