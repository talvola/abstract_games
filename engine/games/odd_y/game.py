"""Odd-Y, by Bill Taylor (2015) — the connection game Y generalised to any
equilateral board with an ODD number of sides (BGG 223551).

Players alternately place a stone of their colour on any empty cell; stones
never move and are never captured. A CORNER cell belongs to BOTH sides that
meet there. The pie (swap) rule applies on the second player's first turn.

WINNING.  A player wins by owning one connected group that touches a set of
three sides such that the triangle drawn between the midpoints of those three
sides CONTAINS THE BOARD'S CENTRE. For side midpoints on a circle this holds
exactly when no cyclic gap between consecutive chosen sides exceeds half the
perimeter, i.e. every gap is at most (m-1)/2 sides (m odd, so a gap can never
be exactly half):

  * Pentagon (m=5, the game "5-Y", independently found by Ea Ea as "Star Y"):
    any 3 of the 5 sides EXCEPT 3 consecutive ones — 5 winning triples of the
    10, the 5 losing ones being the rotations of {k, k+1, k+2}.
  * Heptagon (m=7, "7-Y"): a triple wins iff no gap exceeds 3, i.e. exactly the
    triples that do NOT fit within 4 consecutive sides — 14 winning of the 35.

The 3-sided case is the classic Game of Y (shipped separately as ``y``).

DRAWLESS.  By the generalised Y ("mudcrack") theorem, on a full board exactly
one player has a winning group, so the game cannot end in a draw. Placement on
a finite board also guarantees termination.

THE BOARD.  The same pentagon-of-hexes "mudcrack" pie construction as our
``poly_y`` package, generalised to m sides: m rhombic sectors of (n+1)x(n+1)
hex cells meet at a central cell; the shared spoke edges and the centre are
merged. Result: ``m*n*n + m*n + 1`` cells, m corners, m equal sides of
``2n + 1`` boundary cells each (corners shared between adjacent sides).

  * Cell ids: ``"c"`` (centre), ``"s,k,i"`` (i-th cell out along spoke k;
    spoke k is the boundary between sectors k-1 and k; ``"s,k,n"`` is corner
    k), ``"f,k,i,j"`` (interior face cell of sector k, 1 <= i,j <= n).
  * Side k runs from corner k to corner k+1 (the ``i == n`` / ``j == n`` outer
    boundary of sector k); corner cells lie on both adjacent sides.

Sources: BGG 223551 (Wayback 2021-06-06 snapshot of the description);
Dr Eric Silverman, "Quick Picks: interesting abstract games in brief" (2021).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # player 0 (Black) places first

# Hex neighbours within a sector's rhombus (axial-style).
_RHOMB_NB = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


def _canon(m: int, k: int, i: int, j: int) -> tuple:
    """Map a sector-local (k,i,j) to its canonical merged cell key."""
    k %= m
    if i == 0 and j == 0:
        return ("c",)
    if j == 0:                       # spoke between sector k-1 and k
        return ("s", k, i)
    if i == 0:                       # spoke between sector k and k+1
        return ("s", (k + 1) % m, j)
    return ("f", k, i, j)


@lru_cache(maxsize=None)
def _cells(m: int, n: int) -> tuple:
    out = set()
    for k in range(m):
        for i in range(n + 1):
            for j in range(n + 1):
                out.add(_canon(m, k, i, j))
    return tuple(sorted(out, key=lambda c: (c[0],) + c[1:]))


@lru_cache(maxsize=None)
def _cell_set(m: int, n: int) -> frozenset:
    return frozenset(_cells(m, n))


@lru_cache(maxsize=None)
def _preimages(m: int, n: int) -> dict:
    """canonical cell -> list of (k,i,j) sector-local coordinates."""
    out: dict = {}
    for k in range(m):
        for i in range(n + 1):
            for j in range(n + 1):
                out.setdefault(_canon(m, k, i, j), []).append((k, i, j))
    return out


@lru_cache(maxsize=None)
def _adj(m: int, n: int) -> dict:
    """canonical cell -> frozenset of neighbouring canonical cells."""
    pre = _preimages(m, n)
    out: dict = {}
    for cell, coords in pre.items():
        s = set()
        for (k, i, j) in coords:
            for di, dj in _RHOMB_NB:
                ni, nj = i + di, j + dj
                if 0 <= ni <= n and 0 <= nj <= n:
                    c2 = _canon(m, k, ni, nj)
                    if c2 != cell:
                        s.add(c2)
        out[cell] = frozenset(s)
    return out


@lru_cache(maxsize=None)
def _corners(m: int, n: int) -> tuple:
    """The m corner cells (outer tip of each spoke)."""
    return tuple(("s", k, n) for k in range(m))


@lru_cache(maxsize=None)
def _sides(m: int, n: int) -> tuple:
    """side k -> frozenset of its boundary cells (i==n or j==n edge of sector k).
    Corner cells belong to the two sides that meet there."""
    out = []
    for k in range(m):
        s = set()
        for j in range(n + 1):
            s.add(_canon(m, k, n, j))      # i == n edge (anchored at corner k)
        for i in range(n + 1):
            s.add(_canon(m, k, i, n))      # j == n edge (anchored at corner k+1)
        out.append(frozenset(s))
    return tuple(out)


@lru_cache(maxsize=None)
def _winning_triples(m: int) -> frozenset:
    """All 3-subsets of the m sides whose midpoint triangle contains the centre.

    Side midpoints sit on a circle; the triangle contains the centre iff no
    cyclic gap between consecutive chosen sides exceeds half the circle, i.e.
    every gap is <= (m-1)//2 (m is odd, so exactly half is impossible).
    Pentagon: 5 winning of C(5,3)=10 (excluded = 3 consecutive sides).
    Heptagon: 14 winning of C(7,3)=35 (excluded = triples within 4 consecutive).
    """
    half = (m - 1) // 2
    win = set()
    for a, b, c in combinations(range(m), 3):
        gaps = (b - a, c - b, m - c + a)
        if max(gaps) <= half:
            win.add(frozenset((a, b, c)))
    return frozenset(win)


def _group_sides(board: dict, adj: dict, sides: tuple, start: tuple) -> set:
    """Side indices touched by the group (of start's owner) containing start."""
    p = board[start]
    seen = {start}
    stack = [start]
    touched = set()
    while stack:
        x = stack.pop()
        for k, side in enumerate(sides):
            if x in side:
                touched.add(k)
        for nb in adj[x]:
            if nb not in seen and board.get(nb) == p:
                seen.add(nb)
                stack.append(nb)
    return touched


def _winning_triple_from(touched: set, triples: frozenset):
    """A winning triple among the touched sides, or None."""
    if len(touched) < 3:
        return None
    for tri in combinations(sorted(touched), 3):
        if frozenset(tri) in triples:
            return tri
    return None


def _key(cell: tuple) -> str:
    return ",".join(str(x) for x in cell)


def _cell(s: str) -> tuple:
    parts = s.split(",")
    if parts[0] == "c":
        return ("c",)
    head = parts[0]
    return (head,) + tuple(int(x) for x in parts[1:])


def _corner_dir(m: int, k: int):
    th = math.radians(90 + k * 360.0 / m)
    return (math.cos(th), math.sin(th))


@lru_cache(maxsize=None)
def _positions(m: int, n: int) -> dict:
    """canonical cell -> (x, y) layout point (m-fold symmetric)."""
    pre = _preimages(m, n)
    out = {}
    for cell, coords in pre.items():
        k, i, j = coords[0]
        ux, uy = _corner_dir(m, k)
        vx, vy = _corner_dir(m, (k + 1) % m)
        out[cell] = (i * ux + j * vx, i * uy + j * vy)
    return out


@dataclass
class OddYState:
    m: int = 5                                  # number of sides (odd)
    n: int = 4                                  # cells per spoke
    board: dict = field(default_factory=dict)   # canonical cell -> 0/1
    to_move: int = BLACK
    ply: int = 0
    last: Optional[tuple] = None
    winner: Optional[int] = None
    win_triple: Optional[tuple] = None          # the connected winning sides
    over: bool = False
    pie: bool = True


class OddY(Game):
    name = "Odd-Y"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> OddYState:
        opts = options or {}
        m = int(opts.get("sides", 5))
        n = int(opts.get("size", 4))
        pie = bool(opts.get("pie", True))
        return OddYState(m=m, n=n, pie=pie)

    def current_player(self, s: OddYState) -> int:
        return s.to_move

    def legal_moves(self, s: OddYState):
        if self.is_terminal(s):
            return []
        moves = [_key(c) for c in _cells(s.m, s.n) if c not in s.board]
        if s.pie and s.ply == 1:                 # second player's first turn
            moves.append("swap")
        return moves

    def apply_move(self, s: OddYState, move: str, rng=None) -> OddYState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move

        if move == "swap":
            if not (s.pie and s.ply == 1):
                raise ValueError("swap not available")
            (cell, _), = list(s.board.items())
            return OddYState(
                m=s.m, n=s.n, board={cell: mover}, to_move=1 - mover,
                ply=s.ply + 1, last=cell, pie=s.pie,
            )

        cell = _cell(move)
        if cell not in _cell_set(s.m, s.n) or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        board[cell] = mover
        ns = OddYState(
            m=s.m, n=s.n, board=board, to_move=1 - mover,
            ply=s.ply + 1, last=cell, pie=s.pie,
        )
        # Only the mover's group containing the new stone can newly win.
        touched = _group_sides(board, _adj(s.m, s.n), _sides(s.m, s.n), cell)
        tri = _winning_triple_from(touched, _winning_triples(s.m))
        if tri is not None:
            ns.winner = mover
            ns.win_triple = tri
            ns.over = True
        elif len(board) >= len(_cells(s.m, s.n)):
            # Unreachable by the generalised Y theorem (a full board always has
            # a winning group, detected on the move that completed it) — kept
            # as a termination guard.
            ns.over = True
        return ns

    def is_terminal(self, s: OddYState) -> bool:
        return s.over

    def returns(self, s: OddYState):
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: OddYState):
        """MCTS rollout-cutoff eval: best progress (0..3 sides of some winning
        triple touched by one group) for each player, squashed to (-1, 1)."""
        if s.over:
            return self.returns(s)
        adj = _adj(s.m, s.n)
        sides = _sides(s.m, s.n)
        triples = _winning_triples(s.m)
        best = [0, 0]
        seen = set()
        for cell, p in s.board.items():
            if cell in seen:
                continue
            stack = [cell]
            seen.add(cell)
            touched = set()
            while stack:
                x = stack.pop()
                for k, side in enumerate(sides):
                    if x in side:
                        touched.add(k)
                for nb in adj[x]:
                    if nb not in seen and s.board.get(nb) == p:
                        seen.add(nb)
                        stack.append(nb)
            prog = max((len(tri & touched) for tri in triples), default=0)
            best[p] = max(best[p], prog)
        d = 0.25 * (best[BLACK] - best[WHITE])
        return [d, -d]

    def serialize(self, s: OddYState) -> dict:
        return {
            "m": s.m,
            "n": s.n,
            "board": {_key(c): p for c, p in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "last": (_key(s.last) if s.last is not None else None),
            "winner": s.winner,
            "win_triple": (list(s.win_triple) if s.win_triple else None),
            "over": s.over,
            "pie": s.pie,
        }

    def deserialize(self, d: dict) -> OddYState:
        last = d.get("last")
        wt = d.get("win_triple")
        return OddYState(
            m=d.get("m", 5),
            n=d.get("n", 4),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", len(d["board"])),
            last=(_cell(last) if last else None),
            winner=d.get("winner"),
            win_triple=(tuple(wt) if wt else None),
            over=d.get("over", False),
            pie=d.get("pie", True),
        )

    def describe_move(self, s: OddYState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if _cell(move) in _corners(s.m, s.n):
            return f"{move}*"                    # placing on a corner cell
        return move

    # ---- presentation ------------------------------------------------------
    def render(self, s: OddYState, perspective=None) -> dict:
        m, n = s.m, s.n
        pos = _positions(m, n)
        # Nearest distinct cells are 2*sin(pi/m) apart; scale the hex so
        # neighbours just touch (0.56 was tuned for the pentagon).
        rad = 0.56 * math.sin(math.pi / m) / math.sin(math.pi / 5)

        def hexpts(cx, cy):
            return [[round(cx + rad * math.cos(math.radians(60 * t + 30)), 3),
                     round(cy + rad * math.sin(math.radians(60 * t + 30)), 3)]
                    for t in range(6)]

        corners = set(_corners(m, n))
        sides = _sides(m, n)
        # which single side a non-corner boundary cell belongs to (for tinting)
        side_of = {}
        for k in range(m):
            for c in sides[k]:
                if c in corners:
                    continue
                side_of.setdefault(c, k)

        side_tint = ["#3a4a6a", "#3a5a4a", "#5a4a3a", "#5a3a55",
                     "#4a4a2a", "#2a5a5a", "#5a3a3a"]

        cells = []
        tints = {}
        for c in _cells(m, n):
            cx, cy = pos[c]
            cells.append({"id": _key(c), "points": hexpts(cx, cy)})
            if c in corners:
                tints[_key(c)] = "#caa75a"             # gold corner cells
            elif c in side_of:
                tints[_key(c)] = side_tint[side_of[c] % len(side_tint)]

        pieces = [
            {"cell": _key(c), "owner": p, "label": ""}
            for c, p in s.board.items()
        ]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": _key(s.last), "kind": "last-move"})

        names = {BLACK: "Black", WHITE: "White"}
        if s.over:
            if s.winner is not None:
                tri = "-".join(str(t) for t in (s.win_triple or ()))
                caption = f"{names[s.winner]} wins (sides {tri} connected)"
            else:
                caption = "Board full"
        else:
            caption = f"{names[s.to_move]} to move"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
