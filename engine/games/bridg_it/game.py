"""Bridg-It — David Gale's "Game of Gale" (a Shannon switching game on a grid).

Two interleaved square lattices of dots share one combined integer grid. Using
combined coordinates (x, y) over 0..2N in each axis (N = number of Red columns,
default 5 → the classic Hasbro Bridg-It board):

  * RED (player 0) owns the dots where x is ODD and y is EVEN — an N-column ×
    (N+1)-row lattice (5×6 by default). Red connects the TOP edge (y = 0) to the
    BOTTOM edge (y = 2N).
  * BLUE (player 1) owns the dots where x is EVEN and y is ODD — an (N+1)-column
    × N-row lattice (6×5 by default). Blue connects the LEFT edge (x = 0) to the
    RIGHT edge (x = 2N).

A MOVE draws a unit EDGE between two orthogonally-adjacent dots of the MOVER's
own colour. On the combined grid, two same-colour dots are "adjacent" when they
differ by 2 in exactly one axis (the gap between them spans one lattice cell). An
edge is written as the `>`-separated pair of its endpoint dot-ids, lower-left
endpoint first, e.g. "1,0>1,2" (a Red vertical edge) or "0,1>2,1" (a Blue
horizontal edge).

CROSSING (no-crossing) RULE: a Red edge and the Blue edge that would cross it
share the same midpoint. Drawing an edge is ILLEGAL if the perpendicular
opponent edge crossing that exact spot is already drawn (and vice-versa). Each
interior edge crosses exactly one opponent edge; rim edges (along the outer
border) cross nothing.

WIN: a player wins when their drawn edges form a connected path joining their two
target sides. We BFS over the graph whose nodes are that player's dots and whose
links are that player's drawn edges, starting from the dots on one target side
and seeking the opposite side. Bridg-It cannot draw — it is a Shannon switching
game, so exactly one player connects.

Moves are edge strings "x1,y1>x2,y2" over the combined lattice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1


def _cell(s: str) -> tuple[int, int]:
    x, y = s.split(",")
    return int(x), int(y)


def _edge_key(a: tuple[int, int], b: tuple[int, int]) -> str:
    """Canonical "x1,y1>x2,y2" with the lower endpoint first."""
    lo, hi = sorted((a, b))
    return f"{lo[0]},{lo[1]}>{hi[0]},{hi[1]}"


def _parse_edge(move: str) -> tuple[tuple[int, int], tuple[int, int]]:
    a_s, b_s = move.split(">")
    a, b = _cell(a_s), _cell(b_s)
    return tuple(min(a, b)), tuple(max(a, b))


def _is_dot(x: int, y: int, owner: int) -> bool:
    if owner == RED:
        return x % 2 == 1 and y % 2 == 0
    return x % 2 == 0 and y % 2 == 1


def _dots(n: int, owner: int):
    size = 2 * n
    return {
        (x, y)
        for x in range(size + 1)
        for y in range(size + 1)
        if _is_dot(x, y, owner)
    }


def _potential_edges(n: int, owner: int) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """All unit edges between two orthogonally-adjacent dots of `owner`.

    Two same-colour dots are adjacent when they differ by exactly 2 in one axis.
    """
    dots = _dots(n, owner)
    edges = []
    for (x, y) in dots:
        for (dx, dy) in ((2, 0), (0, 2)):
            other = (x + dx, y + dy)
            if other in dots:
                edges.append(((x, y), other))
    return edges


def _on_board(x: int, y: int, n: int) -> bool:
    return 0 <= x <= 2 * n and 0 <= y <= 2 * n


def _crossing_edge(e, owner: int, n: int):
    """The opponent edge that crosses `e`, or None if `e` is a rim edge.

    A Red vertical edge (ax==bx) is crossed by the Blue horizontal edge through
    the same midpoint; a horizontal edge by the perpendicular vertical opponent
    edge. The crossing edge connects the two opponent dots flanking the midpoint
    across the OTHER axis. Rim edges whose geometric partner falls off the board
    cross nothing and return None.
    """
    (ax, ay), (bx, by) = e
    mx, my = (ax + bx) // 2, (ay + by) // 2  # true midpoint (cell centre)
    if ax == bx:  # vertical edge -> crossed by a horizontal opponent edge
        p, q = (mx - 1, my), (mx + 1, my)
    else:  # horizontal edge -> crossed by a vertical opponent edge
        p, q = (mx, my - 1), (mx, my + 1)
    opp = 1 - owner
    if (
        _on_board(*p, n) and _on_board(*q, n)
        and _is_dot(*p, opp) and _is_dot(*q, opp)
    ):
        return (min(p, q), max(p, q))
    return None


def _connects(edges: set, n: int, owner: int) -> bool:
    """Does `owner` link their two target sides via their drawn edges?

    Red: TOP (y=0) -> BOTTOM (y=2N). Blue: LEFT (x=0) -> RIGHT (x=2N).
    BFS over the adjacency graph formed by the owner's drawn edges.
    """
    size = 2 * n
    adj: dict = {}
    for ek in edges:
        a, b = _parse_edge(ek)
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    if owner == RED:
        starts = [d for d in adj if d[1] == 0]
        at_goal = lambda d: d[1] == size  # noqa: E731
    else:
        starts = [d for d in adj if d[0] == 0]
        at_goal = lambda d: d[0] == size  # noqa: E731
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        for nb in adj.get(cur, ()):
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return False


@dataclass
class BridgItState:
    n: int = 5
    red_edges: frozenset = field(default_factory=frozenset)   # set of edge-keys
    blue_edges: frozenset = field(default_factory=frozenset)
    to_move: int = RED
    winner: Optional[int] = None
    last_move: Optional[str] = None

    def edges_of(self, owner: int) -> frozenset:
        return self.red_edges if owner == RED else self.blue_edges


class BridgIt(Game):
    name = "Bridg-It"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> BridgItState:
        n = int((options or {}).get("size", 5))
        return BridgItState(n=n)

    def current_player(self, s: BridgItState) -> int:
        return s.to_move

    def legal_moves(self, s: BridgItState) -> list[str]:
        if s.winner is not None:
            return []
        own = s.edges_of(s.to_move)
        opp = s.edges_of(1 - s.to_move)
        moves = []
        for e in _potential_edges(s.n, s.to_move):
            ek = _edge_key(*e)
            if ek in own:
                continue  # already drawn by me
            cross = _crossing_edge(e, s.to_move, s.n)
            if cross is not None and _edge_key(*cross) in opp:
                continue  # blocked: opponent already crosses this spot
            moves.append(ek)
        return moves

    def apply_move(self, s: BridgItState, move: str, rng=None) -> BridgItState:
        a, b = _parse_edge(move)
        ek = _edge_key(a, b)
        if s.to_move == RED:
            red = s.red_edges | {ek}
            blue = s.blue_edges
        else:
            red = s.red_edges
            blue = s.blue_edges | {ek}
        edges = red if s.to_move == RED else blue
        winner = s.to_move if _connects(set(edges), s.n, s.to_move) else None
        return BridgItState(
            n=s.n,
            red_edges=red,
            blue_edges=blue,
            to_move=1 - s.to_move,
            winner=winner,
            last_move=ek,
        )

    def is_terminal(self, s: BridgItState) -> bool:
        return s.winner is not None

    def returns(self, s: BridgItState) -> list[float]:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: BridgItState) -> dict:
        return {
            "n": s.n,
            "red_edges": sorted(s.red_edges),
            "blue_edges": sorted(s.blue_edges),
            "to_move": s.to_move,
            "winner": s.winner,
            "last_move": s.last_move,
        }

    def deserialize(self, d: dict) -> BridgItState:
        return BridgItState(
            n=d["n"],
            red_edges=frozenset(d.get("red_edges", [])),
            blue_edges=frozenset(d.get("blue_edges", [])),
            to_move=d["to_move"],
            winner=d.get("winner"),
            last_move=d.get("last_move"),
        )

    def describe_move(self, s: BridgItState, move: str) -> str:
        names = {RED: "Red", BLUE: "Blue"}
        a, b = _parse_edge(move)
        orient = "│" if a[0] == b[0] else "─"
        return f"{names[s.to_move]} {orient} {a[0]},{a[1]}-{b[0]},{b[1]}"

    def render(self, s: BridgItState, perspective=None) -> dict:
        red_fill, blue_fill = "#e06b6b", "#6b8fe0"
        # Dots as small square polygons on the combined lattice; pieces carry the
        # owner colour via `fill`.
        cells = []
        pieces = []
        for owner, fill in ((RED, red_fill), (BLUE, blue_fill)):
            for (x, y) in _dots(s.n, owner):
                cid = f"{x},{y}"
                hs = 0.30
                cells.append({
                    "id": cid,
                    "points": [[x - hs, y - hs], [x + hs, y - hs],
                               [x + hs, y + hs], [x - hs, y + hs]],
                })
                pieces.append({"cell": cid, "owner": owner, "fill": fill})
        # Drawn edges as overlay segments in the owner's colour.
        overlay = []
        for ek in sorted(s.red_edges):
            a, b = _parse_edge(ek)
            overlay.append([[a[0], a[1]], [b[0], b[1]], red_fill])
        for ek in sorted(s.blue_edges):
            a, b = _parse_edge(ek)
            overlay.append([[a[0], a[1]], [b[0], b[1]], blue_fill])
        names = {RED: "Red", BLUE: "Blue"}
        if s.winner is not None:
            edge = "top–bottom" if s.winner == RED else "left–right"
            cap = f"{names[s.winner]} wins (connected {edge})"
        else:
            edge = "top–bottom" if s.to_move == RED else "left–right"
            cap = f"{names[s.to_move]} to move (connect {edge})"
        return {
            "board": {"type": "polygons", "cells": cells, "overlay": overlay},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
