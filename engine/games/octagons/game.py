"""Octagons — R. Wayne Schmittberger's connection game with a double move (1992).

Sources of truth:
  * Kerry Handscomb, "Octagons", Abstract Games magazine #7 (Autumn 2001),
    pp. 12-13 — a full restatement of the rules from Schmittberger's book
    "New Rules for Classic Games" (John Wiley & Sons, 1992), with Diagram 1
    (the original spaces board) and Diagram 2 (the equivalent points board).
  * BGG 69697 (metadata: designer/year/publisher).

BOARD (read from Diagram 1 at 600-1200 dpi).  An 8x8 array of octagons in the
truncated-square tiling.  Every octagon is cut into two congruent half-octagon
pentagons by a chord joining the midpoints of two opposite orthogonal sides;
the cut orientation alternates checkerboard-fashion (with column a..h = c 0..7
and row 1..8 = r 0..7 from the South edge: (c+r) even => VERTICAL cut, halves
'w'/'e'; (c+r) odd => HORIZONTAL cut, halves 'n'/'s'; matches the diagram's
top-left octagon being horizontally cut).  The 7x7 interior interstices are
small tilted SQUARES; the interstices along the borders are filled by the
frame (teeth), so there are no edge squares.  Total spaces: 128 half-octagons
+ 49 squares = 177.

Two spaces sharing a common SIDE (positive-length contact) are connected.
Except on the edges, exactly three spaces meet at every intersection of the
board's lines — the article's stated reason draws are impossible (as in Hex).

CELL IDS.  Half-octagons: octagon coordinate + half letter ("a1w", "b1n"...).
Squares: SW octagon coordinate + "x" ("a1x" = the square NE of octagon a1).

MOVES.  Red (seat 0, first) vs Blue (seat 1).  A turn colours EITHER one
half-octagon (move = its id) OR two distinct empty squares (move =
"sq1>sq2"; both orderings are legal and equivalent).  Red aims to join the
North and South board sides with a chain of connected red spaces, Blue West
and East.  A corner space touches both adjacent sides (this falls out of the
geometry; the article states it explicitly).  The game ends the moment a
chain connects ("win as event": winner stored in state).

Edge-case ruling (not addressed by the article; the 1992 book has no
searchable text to check): when exactly ONE empty square remains, a player
choosing the two-squares option may colour just that single square (move =
its id).  The permissive reading avoids an artificial dead option; documented
in rules.md.

PIE.  After Red's first move Blue may "swap" instead of moving.  The goals
are N-S vs E-W, so the swap must transform the board through an automorphism
exchanging the goals: a 90-degree ROTATION of the board (the split-parity
checkerboard maps onto itself; proven computationally at build time and in
selftest.py).  Stone at p -> opposite colour at rot(p), exactly as Onyx's
transpose-swap.

TERMINATION.  Every move fills at least one space; 177 spaces bound the game.
The no-draw property means a winner exists by the full board at the latest;
a full board without a winner would be a bug but is still reported as an
honest draw.
"""

from __future__ import annotations

import heapq
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1          # Red connects North-South, Blue connects West-East
N = 8                     # octagons per side
PITCH = 4                 # lattice pitch (logic coords, y up, South = y 0)
SIZE = N * PITCH          # 32
LETTERS = "abcdefgh"

_SEAT0_COL, _SEAT1_COL = "#d23b3b", "#3b6fd2"   # web/src/colors.js seat fills


def _oct(c: int, r: int) -> str:
    return f"{LETTERS[c]}{r + 1}"


def _split(c: int, r: int) -> str:
    """'V' (halves w/e) or 'H' (halves n/s)."""
    return "V" if (c + r) % 2 == 0 else "H"


# ---------------------------------------------------------------------------
# Board construction (module-level, immutable).  All adjacency and goal
# contact is DERIVED from exact integer polygon geometry: two cells are
# adjacent iff they share a positive-length boundary segment; a cell touches
# a board side iff it has a boundary segment on that border line.
# ---------------------------------------------------------------------------

_POLY: dict[str, tuple] = {}       # cell id -> polygon vertices (logic, y up)
_KIND: dict[str, str] = {}         # cell id -> "half" | "square"
_ADJ: dict[str, frozenset] = {}
_SIDES: dict[str, frozenset] = {}  # "N"/"S"/"W"/"E" -> cells touching it
_ROT: dict[str, str] = {}          # 90-degree CW rotation cell automorphism
_TWIN: dict[str, str] = {}         # half-octagon -> other half of its octagon

# local half polygons (octagon spans [0,4]x[0,4], corner cut 1)
_LOCAL = {
    "H": {"s": ((0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (0, 2)),
          "n": ((0, 2), (4, 2), (4, 3), (3, 4), (1, 4), (0, 3))},
    "V": {"w": ((1, 0), (2, 0), (2, 4), (1, 4), (0, 3), (0, 1)),
          "e": ((2, 0), (3, 0), (4, 1), (4, 3), (3, 4), (2, 4))},
}


def _elem_segments(poly) -> list:
    """Decompose the polygon boundary into unit lattice segments."""
    segs = []
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        g = math.gcd(abs(x2 - x1), abs(y2 - y1))
        sx, sy = (x2 - x1) // g, (y2 - y1) // g
        for k in range(g):
            a = (x1 + k * sx, y1 + k * sy)
            b = (x1 + (k + 1) * sx, y1 + (k + 1) * sy)
            segs.append((a, b) if a < b else (b, a))
    return segs


def _build() -> None:
    for c in range(N):
        for r in range(N):
            for half, local in _LOCAL[_split(c, r)].items():
                cid = _oct(c, r) + half
                _POLY[cid] = tuple((x + PITCH * c, y + PITCH * r)
                                   for x, y in local)
                _KIND[cid] = "half"
    for c in range(N - 1):
        for r in range(N - 1):
            jx, jy = PITCH * (c + 1), PITCH * (r + 1)
            cid = _oct(c, r) + "x"
            _POLY[cid] = ((jx - 1, jy), (jx, jy - 1), (jx + 1, jy), (jx, jy + 1))
            _KIND[cid] = "square"

    seg_cells: dict[tuple, list] = {}
    for cid, poly in _POLY.items():
        for seg in _elem_segments(poly):
            seg_cells.setdefault(seg, []).append(cid)
    adj: dict[str, set] = {cid: set() for cid in _POLY}
    for seg, cells in seg_cells.items():
        if len(cells) == 2:
            a, b = cells
            adj[a].add(b)
            adj[b].add(a)
        elif len(cells) > 2:                       # pragma: no cover
            raise AssertionError(f"segment {seg} shared by {cells}")
    for cid, nbs in adj.items():
        _ADJ[cid] = frozenset(nbs)

    def _on_border(cid: str, coord: int, value: int) -> bool:
        return any(a[coord] == value and b[coord] == value
                   for a, b in _elem_segments(_POLY[cid]))

    _SIDES["S"] = frozenset(c for c in _POLY if _on_border(c, 1, 0))
    _SIDES["N"] = frozenset(c for c in _POLY if _on_border(c, 1, SIZE))
    _SIDES["W"] = frozenset(c for c in _POLY if _on_border(c, 0, 0))
    _SIDES["E"] = frozenset(c for c in _POLY if _on_border(c, 0, SIZE))

    # 90-degree CW rotation (y up): (x, y) -> (y, SIZE - x).  Match each
    # cell's rotated vertex set to the cell occupying that polygon.
    by_points = {frozenset(p): cid for cid, p in _POLY.items()}
    for cid, poly in _POLY.items():
        target = frozenset((y, SIZE - x) for x, y in poly)
        _ROT[cid] = by_points[target]              # KeyError = no automorphism

    for c in range(N):
        for r in range(N):
            halves = [_oct(c, r) + h for h in _LOCAL[_split(c, r)]]
            _TWIN[halves[0]] = halves[1]
            _TWIN[halves[1]] = halves[0]


_build()

_ORDER = tuple(sorted(_POLY))
_HALVES = tuple(c for c in _ORDER if _KIND[c] == "half")
_SQUARES = tuple(c for c in _ORDER if _KIND[c] == "square")
_GOALS = {RED: ("N", "S"), BLUE: ("W", "E")}


def _connects(stones: dict, player: int) -> tuple:
    """A winning chain of `player` stones linking their two sides, or ()."""
    a, b = _GOALS[player]
    srcs, tgts = _SIDES[a], _SIDES[b]
    start = [p for p in srcs if stones.get(p) == player]
    goal = {p for p in tgts if stones.get(p) == player}
    if not start or not goal:
        return ()
    parent: dict[str, Optional[str]] = {p: None for p in start}
    dq = deque(start)
    end = None
    while dq:
        cur = dq.popleft()
        if cur in goal:
            end = cur
            break
        for nb in _ADJ[cur]:
            if nb not in parent and stones.get(nb) == player:
                parent[nb] = cur
                dq.append(nb)
    if end is None:
        return ()
    path = []
    node: Optional[str] = end
    while node is not None:
        path.append(node)
        node = parent[node]
    return tuple(reversed(path))


def _distance(stones: dict, player: int) -> float:
    """Cheapest remaining cost to connect: own stones free, empty
    half-octagons cost 1 move, empty squares 0.5 (two per move); enemy
    stones block.  inf if cut off."""
    a, b = _GOALS[player]
    tgts = _SIDES[b]
    cost = {}
    heap = []
    for p in _SIDES[a]:
        o = stones.get(p)
        if o == 1 - player:
            continue
        d = 0.0 if o == player else (0.5 if _KIND[p] == "square" else 1.0)
        if d < cost.get(p, math.inf):
            cost[p] = d
            heapq.heappush(heap, (d, p))
    while heap:
        d, p = heapq.heappop(heap)
        if d > cost.get(p, math.inf):
            continue
        if p in tgts:
            return d
        for nb in _ADJ[p]:
            o = stones.get(nb)
            if o == 1 - player:
                continue
            nd = d + (0.0 if o == player
                      else (0.5 if _KIND[nb] == "square" else 1.0))
            if nd < cost.get(nb, math.inf):
                cost[nb] = nd
                heapq.heappush(heap, (nd, nb))
    return math.inf


# ---------------------------------------------------------------------------
# Static render geometry (render space: y down, North at the top).
# ---------------------------------------------------------------------------

_CELLS_STATIC = tuple(
    {"id": cid, "points": [[x, SIZE - y] for x, y in _POLY[cid]]}
    for cid in _ORDER
)
_CENTER = {cid: (sum(x for x, _ in _POLY[cid]) / len(_POLY[cid]),
                 SIZE - sum(y for _, y in _POLY[cid]) / len(_POLY[cid]))
           for cid in _ORDER}
_M = 0.9
_LINES_STATIC = (
    [[-_M, -_M], [SIZE + _M, -_M], _SEAT0_COL],          # North (Red)
    [[-_M, SIZE + _M], [SIZE + _M, SIZE + _M], _SEAT0_COL],  # South (Red)
    [[-_M, -_M], [-_M, SIZE + _M], _SEAT1_COL],          # West (Blue)
    [[SIZE + _M, -_M], [SIZE + _M, SIZE + _M], _SEAT1_COL],  # East (Blue)
)


# ---------------------------------------------------------------------------
# State + game.
# ---------------------------------------------------------------------------

@dataclass
class OctagonsState:
    stones: dict = field(default_factory=dict)   # cell id -> RED/BLUE
    to_move: int = RED
    winner: Optional[int] = None
    ply: int = 0
    last: tuple = ()                             # cells coloured by last move
    conn_path: tuple = ()                        # winning chain (render)


class Octagons(Game):
    name = "Octagons"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options: Optional[dict] = None,
                      rng=None) -> OctagonsState:
        return OctagonsState()

    def current_player(self, s: OctagonsState) -> int:
        return s.to_move

    def legal_moves(self, s: OctagonsState) -> list[str]:
        if s.winner is not None:
            return []
        halves = [h for h in _HALVES if h not in s.stones]
        squares = [q for q in _SQUARES if q not in s.stones]
        moves = halves
        if len(squares) >= 2:
            moves += [f"{a}>{b}" for a in squares for b in squares if a != b]
        elif len(squares) == 1:
            moves.append(squares[0])   # ruling: lone last square colourable
        if s.ply == 1:
            moves.append("swap")
        return moves

    def apply_move(self, s: OctagonsState, move: str, rng=None) -> OctagonsState:
        if s.winner is not None:
            raise ValueError("game over")
        mover = s.to_move
        if move == "swap":
            if s.ply != 1:
                raise ValueError("swap only available on move 2")
            # Goals are N-S vs E-W: recolour + rotate the board 90 degrees
            # (a proven automorphism exchanging the goals) to preserve the
            # position's value for the new colour assignment.
            stones = {_ROT[p]: 1 - o for p, o in s.stones.items()}
            return OctagonsState(stones=stones, to_move=1 - mover,
                                 ply=s.ply + 1, last=("swap",))
        cells = move.split(">")
        if len(cells) == 1:
            c = cells[0]
            if c not in _POLY or c in s.stones:
                raise ValueError(f"illegal move {move!r}")
            if _KIND[c] == "square":
                empties = [q for q in _SQUARES if q not in s.stones]
                if empties != [c]:
                    raise ValueError(
                        "a single square may only be coloured when it is "
                        "the last empty square")
        elif len(cells) == 2:
            a, b = cells
            if (a == b or any(c not in _POLY or _KIND[c] != "square"
                              or c in s.stones for c in (a, b))):
                raise ValueError(f"illegal move {move!r}")
        else:
            raise ValueError(f"illegal move {move!r}")
        stones = dict(s.stones)
        for c in cells:
            stones[c] = mover
        path = _connects(stones, mover)
        return OctagonsState(stones=stones, to_move=1 - mover,
                             winner=mover if path else None, ply=s.ply + 1,
                             last=tuple(sorted(cells)), conn_path=path)

    def is_terminal(self, s: OctagonsState) -> bool:
        return s.winner is not None or len(s.stones) == len(_POLY)

    def returns(self, s: OctagonsState) -> list[float]:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]   # unreachable in theory (no-draw); honest if hit

    def heuristic(self, s: OctagonsState) -> list[float]:
        if s.winner is not None:
            return self.returns(s)
        dr = _distance(s.stones, RED)
        db = _distance(s.stones, BLUE)
        dr = min(dr, 99.0)
        db = min(db, 99.0)
        v = math.tanh((db - dr) / 3.0)
        return [v, -v]

    def serialize(self, s: OctagonsState) -> dict:
        return {
            "stones": dict(s.stones),
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "last": list(s.last),
            "conn_path": list(s.conn_path),
        }

    def deserialize(self, d: dict) -> OctagonsState:
        return OctagonsState(
            stones={k: int(v) for k, v in d.get("stones", {}).items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            last=tuple(d.get("last", [])),
            conn_path=tuple(d.get("conn_path", [])),
        )

    def describe_move(self, s: OctagonsState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        cells = move.split(">")
        if len(cells) == 2:
            return "+".join(cells)
        if _KIND.get(move) == "square":
            return f"{move} (last square)"
        return move

    def render(self, s: OctagonsState, perspective=None) -> dict:
        cells = [{"id": c["id"], "points": [list(p) for p in c["points"]]}
                 for c in _CELLS_STATIC]
        lines = [list(seg) for seg in _LINES_STATIC]
        overlay = []
        if s.conn_path:
            overlay.append([[round(x, 2), round(y, 2)]
                            for x, y in (_CENTER[p] for p in s.conn_path)]
                           + ["#f0b429"])
        pieces = [{"cell": p, "owner": o, "shape": "fill"}
                  for p, o in s.stones.items()]
        highlights = [{"cell": c, "kind": "last-move"}
                      for c in s.last if c != "swap"]
        names = {RED: "Red", BLUE: "Blue"}
        goals = {RED: "North–South", BLUE: "West–East"}
        if s.winner is not None:
            caption = f"{names[s.winner]} wins (connected {goals[s.winner]})"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            caption = (f"{names[s.to_move]} to move (connect "
                       f"{goals[s.to_move]}): one half-octagon or two squares")
        spec = {
            "board": {"type": "polygons", "cells": cells, "lines": lines},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "actionNames": {"swap": "Swap (pie rule)"},
        }
        if overlay:
            spec["board"]["overlay"] = overlay
        return spec
