"""Poly-Y, by Craige Schensted & Charles Titus (c. 1970) — the polygonal
generalisation of the connection game Y.

Poly-Y is played on a board shaped like a polygon with an ODD number of sides
(and hence an odd number of corners). This package uses the smallest classic
shape: a PENTAGON (5 sides, 5 corners). Two players alternately place a stone of
their colour on any empty cell; stones never move and are never captured. The
board fills up.

THE BOARD (pentagon of hexagonal cells).  The pentagon is built as five
triangular/rhombic SECTORS meeting at a central cell — the "mudcrack" pie
construction. Concretely each sector ``k`` (k = 0..4) is an (n+1)x(n+1) grid of
cells with axes running toward two adjacent corners; the cell ``(k,i,j)`` sits at
``i`` steps toward corner ``k`` plus ``j`` steps toward corner ``k+1``. The
``j == 0`` edge of sector ``k`` (a "spoke") is the SAME line of cells as the
``i == 0`` edge of sector ``k-1``; those shared spoke cells, and the single
central cell ``(i=j=0)``, are merged so each is one physical cell. Result for
side parameter ``n``: ``5*n*n + 5*n + 1`` cells (101 at n=4), full 5-fold
symmetry, 5 corners, 5 equal sides.

  * Canonical cell ids: ``"c"`` (centre), ``"s,k,i"`` (the i-th cell out along
    spoke k, k = 0..4, i = 1..n; spoke k is the boundary between sectors k-1 and
    k), and ``"f,k,i,j"`` (an interior face cell of sector k, 1 <= i,j <= n).
  * Corner k is the outer tip of spoke k: ``"s,k,n"``.
  * Adjacency is the 6 hex neighbours within each sector's rhombus grid
    ``(di,dj) in {(±1,0),(0,±1),(+1,-1),(-1,+1)}``, unioned across the sector
    pre-images of every shared cell. (The graph is built once and cached.)

THE SIDES.  Side k (k = 0..4) runs between corner k and corner k+1 and consists
of the outer boundary cells of sector k's rhombus: the cells with ``i == n`` or
``j == n``. A CORNER cell lies on the two sides that meet there, so corner k is a
member of BOTH side k-1 and side k (the published "corner counts as part of both
adjacent sides" rule falls out of the geometry).

WINNING — CORNER OWNERSHIP (the signature of Poly-Y).  At the end (board full)
each corner is awarded to one player. Corner k is owned by the player who has a
single connected group that touches **the two sides adjacent to that corner
(k-1 and k) AND at least one of the OTHER three sides** — i.e. a "Y" linking the
two adjacent sides to a third side. Equivalently: split the pentagon's boundary
into three arcs — arc A = side k-1, arc B = side k, arc C = the remaining three
sides merged — and corner k goes to whoever connects all three arcs. By the
Hex/Y disk theorem exactly one player connects A, B and C on a full board, so
every corner has a unique owner and there are no draws. The player owning a
MAJORITY of the 5 corners (3+) wins; the odd corner count makes ties impossible.

A swap (pie) move is offered to the second player on their first turn to balance
the first-move advantage.

Sources: Schensted & Titus, *Mudcrack Y & Poly-Y* (1975);
Dr Eric Silverman, "Connection Games II: Y, Poly-Y, Star and *Star";
https://en.wikipedia.org/wiki/Y_(game) ; https://boardgamegeek.com/boardgame/179816/poly-y
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # player 0 (Black) places first
NSIDES = 5

# Hex neighbours within a sector's rhombus (axial-style).
_RHOMB_NB = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


def _canon(k: int, i: int, j: int) -> tuple:
    """Map a sector-local (k,i,j) to its canonical merged cell key."""
    k %= NSIDES
    if i == 0 and j == 0:
        return ("c",)
    if j == 0:                       # spoke between sector k-1 and k
        return ("s", k, i)
    if i == 0:                       # spoke between sector k and k+1
        return ("s", (k + 1) % NSIDES, j)
    return ("f", k, i, j)


@lru_cache(maxsize=None)
def _cells(n: int) -> tuple:
    out = set()
    for k in range(NSIDES):
        for i in range(n + 1):
            for j in range(n + 1):
                out.add(_canon(k, i, j))
    return tuple(sorted(out, key=lambda c: (c[0],) + c[1:]))


@lru_cache(maxsize=None)
def _cell_set(n: int) -> frozenset:
    return frozenset(_cells(n))


@lru_cache(maxsize=None)
def _preimages(n: int) -> dict:
    """canonical cell -> list of (k,i,j) sector-local coordinates."""
    out: dict = {}
    for k in range(NSIDES):
        for i in range(n + 1):
            for j in range(n + 1):
                out.setdefault(_canon(k, i, j), []).append((k, i, j))
    return out


@lru_cache(maxsize=None)
def _adj(n: int) -> dict:
    """canonical cell -> frozenset of neighbouring canonical cells."""
    pre = _preimages(n)
    out: dict = {}
    for cell, coords in pre.items():
        s = set()
        for (k, i, j) in coords:
            for di, dj in _RHOMB_NB:
                ni, nj = i + di, j + dj
                if 0 <= ni <= n and 0 <= nj <= n:
                    c2 = _canon(k, ni, nj)
                    if c2 != cell:
                        s.add(c2)
        out[cell] = frozenset(s)
    return out


@lru_cache(maxsize=None)
def _corners(n: int) -> tuple:
    """The 5 corner cells (outer tip of each spoke)."""
    return tuple(("s", k, n) for k in range(NSIDES))


@lru_cache(maxsize=None)
def _sides(n: int) -> tuple:
    """side k -> frozenset of its boundary cells (i==n or j==n edge of sector k).
    Corner cells belong to the two sides that meet there."""
    out = []
    for k in range(NSIDES):
        s = set()
        for j in range(n + 1):
            s.add(_canon(k, n, j))      # i == n edge (anchored at corner k)
        for i in range(n + 1):
            s.add(_canon(k, i, n))      # j == n edge (anchored at corner k+1)
        out.append(frozenset(s))
    return tuple(out)


@lru_cache(maxsize=None)
def _corner_arcs(n: int) -> tuple:
    """For each corner k return (A, B, C): A = side k-1, B = side k,
    C = the union of the other three sides (the 'third side')."""
    sides = _sides(n)
    arcs = []
    for k in range(NSIDES):
        A = sides[(k - 1) % NSIDES]
        B = sides[k]
        others = [sides[(k + d) % NSIDES] for d in (1, 2, 3)]
        C = frozenset().union(*others)
        arcs.append((A, B, C))
    return tuple(arcs)


def _connects_three(board: dict, adj: dict, p: int, A, B, C) -> bool:
    """Does player ``p`` have one connected group touching all of arcs A, B, C?"""
    seen = set()
    for start, owner in board.items():
        if owner != p or start in seen:
            continue
        stack = [start]
        seen.add(start)
        ta = tb = tc = False
        while stack:
            x = stack.pop()
            if x in A:
                ta = True
            if x in B:
                tb = True
            if x in C:
                tc = True
            for nb in adj[x]:
                if nb not in seen and board.get(nb) == p:
                    seen.add(nb)
                    stack.append(nb)
        if ta and tb and tc:
            return True
    return False


def _corner_dir(k: int):
    th = math.radians(90 + k * 72)
    return (math.cos(th), math.sin(th))


@lru_cache(maxsize=None)
def _positions(n: int) -> dict:
    """canonical cell -> (x, y) layout point (5-fold symmetric)."""
    pre = _preimages(n)
    out = {}
    for cell, coords in pre.items():
        k, i, j = coords[0]
        ux, uy = _corner_dir(k)
        vx, vy = _corner_dir((k + 1) % NSIDES)
        out[cell] = (i * ux + j * vx, i * uy + j * vy)
    return out


def _corner_owner(board: dict, n: int, k: int):
    """Owner of corner k (or None if not yet decided on a partial board)."""
    adj = _adj(n)
    A, B, C = _corner_arcs(n)[k]
    if _connects_three(board, adj, BLACK, A, B, C):
        return BLACK
    if _connects_three(board, adj, WHITE, A, B, C):
        return WHITE
    return None


def _corner_counts(board: dict, n: int):
    """(black_corners, white_corners, owners_list)."""
    owners = [_corner_owner(board, n, k) for k in range(NSIDES)]
    bl = sum(1 for o in owners if o == BLACK)
    wh = sum(1 for o in owners if o == WHITE)
    return bl, wh, owners


def _key(cell: tuple) -> str:
    return ",".join(str(x) for x in cell)


def _cell(s: str) -> tuple:
    parts = s.split(",")
    if parts[0] == "c":
        return ("c",)
    head = parts[0]
    return (head,) + tuple(int(x) for x in parts[1:])


@dataclass
class PolyYState:
    n: int = 4
    board: dict = field(default_factory=dict)   # canonical cell -> 0/1
    to_move: int = BLACK
    ply: int = 0
    last: Optional[tuple] = None
    winner: Optional[int] = None
    over: bool = False
    pie: bool = True


class PolyY(Game):
    uid = "poly_y"
    name = "Poly-Y"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> PolyYState:
        opts = options or {}
        n = int(opts.get("size", 4))
        pie = bool(opts.get("pie", True))
        return PolyYState(n=n, pie=pie)

    def current_player(self, s: PolyYState) -> int:
        return s.to_move

    def legal_moves(self, s: PolyYState):
        if self.is_terminal(s):
            return []
        moves = [_key(c) for c in _cells(s.n) if c not in s.board]
        if s.pie and s.ply == 1:                 # second player's first turn
            moves.append("swap")
        return moves

    def apply_move(self, s: PolyYState, move: str, rng=None) -> PolyYState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move

        if move == "swap":
            if not (s.pie and s.ply == 1):
                raise ValueError("swap not available")
            (cell, _), = list(s.board.items())
            return PolyYState(
                n=s.n, board={cell: mover}, to_move=1 - mover,
                ply=s.ply + 1, last=cell, pie=s.pie,
            )

        cell = _cell(move)
        if cell not in _cell_set(s.n) or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        board[cell] = mover
        ns = PolyYState(
            n=s.n, board=board, to_move=1 - mover,
            ply=s.ply + 1, last=cell, pie=s.pie,
        )
        if len(board) >= len(_cells(s.n)):       # board full -> score corners
            bl, wh, _ = _corner_counts(board, s.n)
            ns.winner = BLACK if bl > wh else WHITE  # odd corners -> no tie
            ns.over = True
        return ns

    def is_terminal(self, s: PolyYState) -> bool:
        return s.over

    def returns(self, s: PolyYState):
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: PolyYState) -> dict:
        return {
            "n": s.n,
            "board": {_key(c): p for c, p in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "last": (_key(s.last) if s.last is not None else None),
            "winner": s.winner,
            "over": s.over,
            "pie": s.pie,
        }

    def deserialize(self, d: dict) -> PolyYState:
        last = d.get("last")
        return PolyYState(
            n=d.get("n", 4),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", len(d["board"])),
            last=(_cell(last) if last else None),
            winner=d.get("winner"),
            over=d.get("over", False),
            pie=d.get("pie", True),
        )

    def describe_move(self, s: PolyYState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if _cell(move) in _corners(s.n):
            return f"{move}*"                    # placing on a corner cell
        return move

    # ---- presentation ------------------------------------------------------
    def render(self, s: PolyYState, perspective=None) -> dict:
        n = s.n
        pos = _positions(n)
        rad = 0.56
        # pointy-top hexagon at each cell centre
        def hexpts(cx, cy):
            return [[round(cx + rad * math.cos(math.radians(60 * t + 30)), 3),
                     round(cy + rad * math.sin(math.radians(60 * t + 30)), 3)]
                    for t in range(6)]

        corners = set(_corners(n))
        sides = _sides(n)
        # which single side a non-corner boundary cell belongs to (for tinting)
        side_of = {}
        for k in range(NSIDES):
            for c in sides[k]:
                if c in corners:
                    continue
                side_of.setdefault(c, k)

        side_tint = ["#3a4a6a", "#3a5a4a", "#5a4a3a", "#5a3a55", "#4a4a2a"]

        cells = []
        tints = {}
        for c in _cells(n):
            cx, cy = pos[c]
            cells.append({"id": _key(c), "points": hexpts(cx, cy)})
            if c in corners:
                tints[_key(c)] = "#caa75a"             # gold corner cells
            elif c in side_of:
                tints[_key(c)] = side_tint[side_of[c]]  # per-side edge colour

        pieces = [
            {"cell": _key(c), "owner": p, "label": ""}
            for c, p in s.board.items()
        ]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": _key(s.last), "kind": "last-move"})

        names = {BLACK: "Black", WHITE: "White"}
        bl, wh, _ = _corner_counts(s.board, n)
        if s.over:
            caption = f"{names[s.winner]} wins — corners Black {bl}, White {wh}"
        else:
            caption = f"{names[s.to_move]} to move — corners Black {bl}, White {wh}"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
