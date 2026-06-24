"""ConHex — Michail Antonow's two-layer connection game (2002).

ConHex is played on a square board carrying TWO overlaid structures:

  * a lattice of **69 placement points** ("holes" / vertices) sitting on an
    11x11 integer grid, and
  * a set of **41 cells** ("spaces"), each bordered by a small set of those
    points. The cells form concentric octagonal rings (16 cells on the outer
    rim, then 12, 8, 4, and a single diamond CENTRE cell).

PLAY.  Red moves first; on Yellow's (player 1's) very first turn it may instead
``swap`` colours (pie rule) to neutralise a strong opening. A move places one
PEG on an empty lattice point. When a player owns at least **half** of the
points bordering a cell, they immediately CLAIM that cell in their colour
(the claim is permanent — pegs and claims never move or change owner). The
threshold is ``ceil(n/2)`` of the cell's ``n`` border points: 2 of 3 for the
rim/corner cells, 3 of 5 for the centre cell, 3 of 6 for the interior cells.

WIN.  A player wins by forming a contiguous chain of cells THEY OWN linking
their two opposite sides:

  * RED (player 0) links the TOP edge to the BOTTOM edge;
  * YELLOW (player 1) links the LEFT edge to the RIGHT edge.

The four CORNER cells each touch both of their adjacent sides (e.g. the NE
corner cell counts for both the top side and the right side). Draws are
impossible — exactly one player connects.

BOARD STRUCTURE.  The 69 points, the 41 cells and their border-point sets, the
cell-adjacency graph and the side-membership lines are generated procedurally
from the same algorithm used by AbstractPlay's reference implementation
(https://github.com/AbstractPlay/gameslib, src/games/conhex.ts), so the board
is faithful to the published ConHex board (41 cells / 69 holes).

Moves are point ids ``"x,y"`` (x, y in 0..10), plus the pie action ``"swap"``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

RED, YELLOW = 0, 1
SIZE = 11  # 11x11 lattice; the standard (and only) ConHex board


# ---------------------------------------------------------------------------
# Board generators (ported from the AbstractPlay reference implementation).
# ``v(x, y)`` is a lattice-point id; ``sp(x, y)`` is a cell ("space") id.
# ---------------------------------------------------------------------------

def _v(x: int, y: int) -> str:
    return f"{x},{y}"


def _sp(x: int, y: int) -> str:
    return f"s{x},{y}"  # 's' prefix keeps cell ids distinct from point ids


def _sp_xy(space: str) -> tuple[int, int]:
    x, y = space[1:].split(",")
    return int(x), int(y)


@lru_cache(maxsize=None)
def _all_points() -> tuple:
    """The 69 lattice points (point ids), in the reference order."""
    n = SIZE
    pts = [_v(0, 0), _v(0, n - 1), _v(n - 1, 0), _v(n - 1, n - 1),
           _v((n - 1) // 2, (n - 1) // 2)]
    row_count = (n - 1) // 2 - 2
    col_start = n - 4
    for j in range(row_count + 1):
        rn, rs = j + 1, n - 2 - j
        cw, ce = j + 1, n - 2 - j
        for i in range(col_start - 2 * j):
            c = 2 + j + i
            pts.append(_v(c, rn))
            pts.append(_v(c, rs))
            pts.append(_v(cw, c))
            pts.append(_v(ce, c))
    return tuple(pts)


@lru_cache(maxsize=None)
def _space_points() -> dict:
    """Map each cell id -> tuple of its bordering point ids."""
    n = SIZE
    m: dict[str, list] = {}
    rc = (n - 1) // 2
    # corners
    m[_sp(0, 0)] = [_v(0, 0), _v(1, 2), _v(2, 1)]
    m[_sp(rc - 1, 0)] = [_v(n - 1, 0), _v(n - 2, 2), _v(n - 3, 1)]
    m[_sp(2 * (rc - 1), 0)] = [_v(n - 1, n - 1), _v(n - 3, n - 2), _v(n - 2, n - 3)]
    m[_sp(3 * (rc - 1), 0)] = [_v(0, n - 1), _v(2, n - 2), _v(1, n - 3)]
    # outer edges
    for i in range(rc - 2):
        m[_sp(i + 1, 0)] = [_v(2 + 2 * i, 1), _v(3 + 2 * i, 1), _v(4 + 2 * i, 1)]
        m[_sp(i + rc, 0)] = [_v(n - 2, 2 + 2 * i), _v(n - 2, 3 + 2 * i), _v(n - 2, 4 + 2 * i)]
        m[_sp(i + 2 * (rc - 1) + 1, 0)] = [_v(n - 3 - 2 * i, n - 2), _v(n - 4 - 2 * i, n - 2), _v(n - 5 - 2 * i, n - 2)]
        m[_sp(i + 3 * (rc - 1) + 1, 0)] = [_v(1, n - 3 - 2 * i), _v(1, n - 4 - 2 * i), _v(1, n - 5 - 2 * i)]
    # inner corners (6 points each)
    for j in range(rc - 2):
        m[_sp(0, 1 + j)] = [_v(2 + j, 1 + j), _v(3 + j, 1 + j), _v(1 + j, 2 + j), _v(3 + j, 2 + j), _v(1 + j, 3 + j), _v(2 + j, 3 + j)]
        m[_sp(rc - 2 - j, 1 + j)] = [_v(n - 4 - j, 1 + j), _v(n - 3 - j, 1 + j), _v(n - 2 - j, 2 + j), _v(n - 4 - j, 2 + j), _v(n - 2 - j, 3 + j), _v(n - 3 - j, 3 + j)]
        m[_sp(2 * (rc - 2 - j), 1 + j)] = [_v(n - 3 - j, n - 4 - j), _v(n - 2 - j, n - 4 - j), _v(n - 4 - j, n - 3 - j), _v(n - 2 - j, n - 3 - j), _v(n - 4 - j, n - 2 - j), _v(n - 3 - j, n - 2 - j)]
        m[_sp(3 * (rc - 2 - j), 1 + j)] = [_v(1 + j, n - 4 - j), _v(2 + j, n - 4 - j), _v(1 + j, n - 3 - j), _v(3 + j, n - 3 - j), _v(2 + j, n - 2 - j), _v(3 + j, n - 2 - j)]
    # inner edges (6 points each)
    for j in range(rc - 2):
        for i in range(rc - 3 - j):
            m[_sp(i + 1, 1 + j)] = [_v(3 + j + 2 * i, 1 + j), _v(4 + j + 2 * i, 1 + j), _v(5 + j + 2 * i, 1 + j), _v(3 + j + 2 * i, 2 + j), _v(4 + j + 2 * i, 2 + j), _v(5 + j + 2 * i, 2 + j)]
            m[_sp(rc - 1 - j + i, 1 + j)] = [_v(n - 3 - j, 3 + j + 2 * i), _v(n - 3 - j, 4 + j + 2 * i), _v(n - 3 - j, 5 + j + 2 * i), _v(n - 2 - j, 3 + j + 2 * i), _v(n - 2 - j, 4 + j + 2 * i), _v(n - 2 - j, 5 + j + 2 * i)]
            m[_sp(2 * (rc - 2 - j) + 1 + i, 1 + j)] = [_v(n - 4 - j - 2 * i, n - 3 - j), _v(n - 5 - j - 2 * i, n - 3 - j), _v(n - 6 - j - 2 * i, n - 3 - j), _v(n - 4 - j - 2 * i, n - 2 - j), _v(n - 5 - j - 2 * i, n - 2 - j), _v(n - 6 - j - 2 * i, n - 2 - j)]
            m[_sp(3 * (rc - 2 - j) + 1 + i, 1 + j)] = [_v(1 + j, n - 4 - j - 2 * i), _v(1 + j, n - 5 - j - 2 * i), _v(1 + j, n - 6 - j - 2 * i), _v(2 + j, n - 4 - j - 2 * i), _v(2 + j, n - 5 - j - 2 * i), _v(2 + j, n - 6 - j - 2 * i)]
    # centre (5 points)
    c = (n - 1) // 2
    m[_sp(0, rc - 1)] = [_v(c, c - 1), _v(c, c + 1), _v(c - 1, c), _v(c + 1, c), _v(c, c)]
    return {k: tuple(vs) for k, vs in m.items()}


@lru_cache(maxsize=None)
def _point_spaces() -> dict:
    """Inverse: point id -> tuple of cell ids it borders."""
    out: dict[str, list] = {}
    for sp, pts in _space_points().items():
        for p in pts:
            out.setdefault(p, []).append(sp)
    return {k: tuple(vs) for k, vs in out.items()}


def _space_type(x: int, y: int) -> str:
    rc = (SIZE - 1) // 2
    if y == rc - 1:
        return "centre"
    if x % (rc - 1 - y) == 0:
        return "corner"
    return "edge"


@lru_cache(maxsize=None)
def _neighbours(space: str) -> tuple:
    """Cells adjacent to ``space`` in the cell-connection graph."""
    x, y = _sp_xy(space)
    rc = (SIZE - 1) // 2
    st = _space_type(x, y)
    if st == "centre":
        return (_sp(0, rc - 2), _sp(1, rc - 2), _sp(2, rc - 2), _sp(3, rc - 2))
    ns = []
    ns.append(_sp(4 * (rc - 1 - y) - 1 if x == 0 else x - 1, y))
    ns.append(_sp(0 if x + 1 == 4 * (rc - 1 - y) else x + 1, y))
    quad = x // (rc - 1 - y)
    if st == "corner":
        ns.append(_sp(x - quad, y + 1))
        if y > 0:
            ns.append(_sp(x + quad, y - 1))
            ns.append(_sp(x + quad + 1, y - 1))
            ns.append(_sp(4 * (rc - y) - 1 if x == 0 else x + quad - 1, y - 1))
    else:
        ns.append(_sp(0 if x - quad == 4 * (rc - 2 - y) else x - quad, y + 1))
        ns.append(_sp(x - quad - 1, y + 1))
        if y > 0:
            ns.append(_sp(x + quad, y - 1))
            ns.append(_sp(x + quad + 1, y - 1))
    return tuple(ns)


@lru_cache(maxsize=None)
def _lines() -> tuple:
    """((red_top, red_bottom), (yellow_left, yellow_right)) cell-id side lists."""
    rc = (SIZE - 1) // 2
    line_n = [_sp(x, 0) for x in range(rc)]
    line_s = [_sp(2 * (rc - 1) + x, 0) for x in range(rc)]
    line_e = [_sp(rc - 1 + y, 0) for y in range(rc)]
    line_w = [_sp(0 if y == rc - 1 else 3 * (rc - 1) + y, 0) for y in range(rc)]
    # RED links top<->bottom; YELLOW links left<->right.
    return ((tuple(line_n), tuple(line_s)), (tuple(line_w), tuple(line_e)))


def _threshold(space: str) -> int:
    return math.ceil(len(_space_points()[space]) / 2)


# ---------------------------------------------------------------------------
# Polygon geometry for rendering (lattice points live on the 11x11 grid).
# ---------------------------------------------------------------------------

_CENTRE_PT = ((SIZE - 1) // 2, (SIZE - 1) // 2)


def _pt_xy(pid: str) -> tuple[int, int]:
    x, y = pid.split(",")
    return int(x), int(y)


def _order(pts: list) -> list:
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


@lru_cache(maxsize=None)
def _cell_polygon(space: str) -> tuple:
    """Outline (list of [x,y]) for a cell, drawn on the lattice grid."""
    pts = [_pt_xy(p) for p in _space_points()[space]]
    x, y = _sp_xy(space)
    st = _space_type(x, y)
    n = SIZE - 1
    if st == "centre":
        outer = [p for p in pts if p != _CENTRE_PT]
        return tuple([list(p) for p in _order(outer)])
    if len(pts) == 6:
        return tuple([list(p) for p in _order(pts)])
    # 3-point outer-ring cell: extend to the board rim.
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if st == "edge":
        if len(set(ys)) == 1:  # horizontal run (top y=1 or bottom y=9)
            yc = ys[0]
            rim = 0 if yc == 1 else n
            x0, x1 = min(xs), max(xs)
            mid = sorted(pts)[1][0]
            poly = [(x0, rim), (x0, yc), (mid, yc), (x1, yc), (x1, rim)]
        else:  # vertical run (right x=9 or left x=1)
            xc = xs[0]
            rim = n if xc == n - 2 else 0
            y0, y1 = min(ys), max(ys)
            mid = sorted(pts, key=lambda p: p[1])[1][1]
            poly = [(rim, y0), (xc, y0), (xc, mid), (xc, y1), (rim, y1)]
        return tuple([list(p) for p in poly])
    # corner cell: board-corner point + two inner points projected to the rims
    corner = next(p for p in pts if p in [(0, 0), (n, 0), (n, n), (0, n)])
    rx, ry = (0 if corner[0] == 0 else n), (0 if corner[1] == 0 else n)
    others = [p for p in pts if p != corner]
    proj = []
    for p in others:
        if abs(p[1] - ry) < abs(p[0] - rx):
            proj.append((p[0], ry))
        else:
            proj.append((rx, p[1]))
    poly = _order([corner] + others + proj)
    return tuple([list(p) for p in poly])


# ---------------------------------------------------------------------------
# State + game
# ---------------------------------------------------------------------------

@dataclass
class ConHexState:
    points: dict = field(default_factory=dict)   # point id -> 0/1 (peg owner)
    spaces: dict = field(default_factory=dict)   # cell id  -> 0/1 (claim owner)
    to_move: int = RED
    winner: Optional[int] = None
    ply: int = 0
    last: Optional[str] = None
    conn_path: tuple = ()


def _connects(spaces: dict, player: int) -> tuple:
    """Return a winning chain of `player`'s cells linking their two sides, or ()."""
    (red_a, red_b), (yel_a, yel_b) = _lines()
    sources, targets = (red_a, red_b) if player == RED else (yel_a, yel_b)
    owned = {c for c, p in spaces.items() if p == player}
    src = [c for c in sources if c in owned]
    tgt = set(t for t in targets if t in owned)
    if not src or not tgt:
        return ()
    # BFS from any source cell to any target cell over the owned-cell subgraph.
    parent = {c: None for c in src}
    from collections import deque
    dq = deque(src)
    goal = None
    while dq:
        cur = dq.popleft()
        if cur in tgt:
            goal = cur
            break
        for nb in _neighbours(cur):
            if nb in owned and nb not in parent:
                parent[nb] = cur
                dq.append(nb)
    if goal is None:
        return ()
    path = []
    c = goal
    while c is not None:
        path.append(c)
        c = parent[c]
    return tuple(reversed(path))


class ConHex(Game):
    uid = "conhex"
    name = "ConHex"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ConHexState:
        return ConHexState()

    def current_player(self, s: ConHexState) -> int:
        return s.to_move

    def legal_moves(self, s: ConHexState) -> list[str]:
        if s.winner is not None:
            return []
        moves = [p for p in _all_points() if p not in s.points]
        if s.ply == 1:  # second player's first turn -> pie option
            moves.append("swap")
        return moves

    def apply_move(self, s: ConHexState, move: str, rng=None) -> ConHexState:
        if s.winner is not None:
            raise ValueError("game over")
        mover = s.to_move
        if move == "swap":
            if s.ply != 1:
                raise ValueError("swap not available")
            # Pie: the second player takes the opening peg by recolouring it.
            ((pid, _),) = list(s.points.items())
            return ConHexState(points={pid: mover}, spaces={}, to_move=1 - mover,
                               winner=None, ply=s.ply + 1, last="swap")
        if move not in _all_points() or move in s.points:
            raise ValueError(f"illegal move {move!r}")
        points = dict(s.points)
        points[move] = mover
        spaces = dict(s.spaces)
        # A peg may claim one or more of the cells it borders.
        for sp in _point_spaces()[move]:
            if sp in spaces:
                continue
            owned = sum(1 for p in _space_points()[sp]
                        if points.get(p) == mover)
            if owned >= _threshold(sp):
                spaces[sp] = mover
        path = _connects(spaces, mover)
        winner = mover if path else None
        return ConHexState(points=points, spaces=spaces, to_move=1 - mover,
                           winner=winner, ply=s.ply + 1, last=move,
                           conn_path=path)

    def is_terminal(self, s: ConHexState) -> bool:
        return s.winner is not None

    def returns(self, s: ConHexState) -> list[float]:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == YELLOW:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # unreachable: ConHex is drawless

    def serialize(self, s: ConHexState) -> dict:
        return {
            "points": dict(s.points),
            "spaces": dict(s.spaces),
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "last": s.last,
            "conn_path": list(s.conn_path),
        }

    def deserialize(self, d: dict) -> ConHexState:
        return ConHexState(
            points=dict(d.get("points", {})),
            spaces=dict(d.get("spaces", {})),
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", len(d.get("points", {}))),
            last=d.get("last"),
            conn_path=tuple(d.get("conn_path", [])),
        )

    def describe_move(self, s: ConHexState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        return move

    def render(self, s: ConHexState, perspective=None) -> dict:
        cells = []
        # 1) the 41 cells (drawn first, under the dots)
        for sp in _space_points():
            cells.append({"id": sp, "points": [list(p) for p in _cell_polygon(sp)]})
        # 2) the 69 lattice points as small diamond cells (drawn on top, clickable)
        d = 0.32
        for pid in _all_points():
            x, y = _pt_xy(pid)
            cells.append({
                "id": pid,
                "points": [[x, y - d], [x + d, y], [x, y + d], [x - d, y]],
            })
        # claimed cells -> tinted in the owner's (muted) colour
        claim_fill = {RED: "#7a2828", YELLOW: "#274a86"}
        tints = {sp: claim_fill[p] for sp, p in s.spaces.items()}
        # winning chain stands out
        for sp in s.conn_path:
            tints[sp] = "#caa05a"
        # pegs on the lattice points
        pieces = [{"cell": pid, "owner": p} for pid, p in s.points.items()]
        highlights = []
        if s.last and s.last != "swap":
            highlights.append({"cell": s.last, "kind": "last-move"})
        names = {RED: "Red", YELLOW: "Yellow"}
        if s.winner is not None:
            edge = "top–bottom" if s.winner == RED else "left–right"
            caption = f"{names[s.winner]} wins (connected {edge})"
        else:
            edge = "top–bottom" if s.to_move == RED else "left–right"
            caption = f"{names[s.to_move]} to move (connect {edge})"
        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
