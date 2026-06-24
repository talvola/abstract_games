"""Sim -- the Ramsey graph game (Gustavus Simmons, 1969).

The board is the complete graph K6: 6 vertices (dots) laid out as a regular
hexagon, with all 15 edges between every pair of vertices. Two players take
turns; on a turn a player COLORS one uncolored edge in their own colour
(player 0 / Red, player 1 / Blue).

MISERE / AVOIDANCE: a player LOSES the instant they form a triangle of THEIR
OWN colour -- three edges of the player's colour joining some 3 of the 6
vertices. The opponent then wins.

By Ramsey's theorem (R(3,3) = 6) any 2-colouring of K6 contains a monochromatic
triangle, so the game can NEVER end in a draw: a decisive result always arrives
within at most 15 plies. (Sim is a second-player win with perfect play; no
swap/pie rule is part of the game.)

EDGE / MOVE ENCODING -- mirrors Dots and Boxes: each edge is its OWN thin
clickable cell on a `polygons` board whose id IS the move string, so an
uncoloured edge is a legal 1-cell move and the generic renderer makes it
click-to-place. An edge between vertices i<j (vertices 0..5) is:

    "e{i}-{j}"      e.g. "e0-3", "e2-5"

`legal_moves` returns exactly those strings for the uncoloured edges; a coloured
edge is tinted in its owner's seat colour via `board.tints`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N_VERTS = 6

# All 15 unordered vertex pairs (i < j) of K6.
ALL_EDGES = [(i, j) for i in range(N_VERTS) for j in range(i + 1, N_VERTS)]


def edge_id(i: int, j: int) -> str:
    if i > j:
        i, j = j, i
    return f"e{i}-{j}"


def parse_edge(s: str):
    a, b = s[1:].split("-")
    i, j = int(a), int(b)
    if i > j:
        i, j = j, i
    return i, j


@dataclass
class SimState:
    # edge (i,j) i<j -> owner (0 or 1); absent => uncoloured
    colors: dict = field(default_factory=dict)
    to_move: int = 0
    loser: Optional[int] = None        # set the instant a mono-triangle is formed
    last_move: Optional[str] = None


class Sim(Game):
    uid = "sim"
    name = "Sim"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SimState:
        return SimState()

    def current_player(self, s: SimState) -> int:
        return s.to_move

    def legal_moves(self, s: SimState):
        if self.is_terminal(s):
            return []
        return [edge_id(i, j) for (i, j) in ALL_EDGES if (i, j) not in s.colors]

    def _forms_triangle(self, colors, i, j, player) -> bool:
        """Does colouring edge (i,j) for `player` complete a same-colour
        triangle?  True iff some third vertex k has both (i,k) and (j,k)
        already owned by `player`."""
        for k in range(N_VERTS):
            if k == i or k == j:
                continue
            e1 = (min(i, k), max(i, k))
            e2 = (min(j, k), max(j, k))
            if colors.get(e1) == player and colors.get(e2) == player:
                return True
        return False

    def apply_move(self, s: SimState, move: str, rng=None) -> SimState:
        i, j = parse_edge(move)
        colors = dict(s.colors)
        player = s.to_move
        colors[(i, j)] = player
        loser = None
        if self._forms_triangle(s.colors, i, j, player):
            # The mover just completed a triangle in their OWN colour -> loses.
            loser = player
        return SimState(
            colors=colors,
            to_move=1 - player,
            loser=loser,
            last_move=move,
        )

    def is_terminal(self, s: SimState) -> bool:
        # Decisive the moment someone forms a mono-triangle. By Ramsey this MUST
        # happen by the time all 15 edges are coloured, so a full board with no
        # loser is impossible; we still treat a full board as terminal defensively.
        return s.loser is not None or len(s.colors) >= len(ALL_EDGES)

    def returns(self, s: SimState):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        if s.loser is None:
            # Unreachable under correct play (Ramsey guarantees a loser), but be
            # well-formed if a full board is ever reached without one.
            return [0.0, 0.0]
        # Loser gets -1, the other player wins.
        return [1.0, -1.0] if s.loser == 1 else [-1.0, 1.0]

    # ---- (de)serialise -----------------------------------------------------
    def serialize(self, s: SimState) -> dict:
        return {
            "colors": [[i, j, p] for (i, j), p in sorted(s.colors.items())],
            "to_move": s.to_move,
            "loser": s.loser,
            "last_move": s.last_move,
        }

    def deserialize(self, d: dict) -> SimState:
        return SimState(
            colors={(i, j): p for i, j, p in d.get("colors", [])},
            to_move=d["to_move"],
            loser=d.get("loser"),
            last_move=d.get("last_move"),
        )

    def describe_move(self, s: SimState, move: str) -> str:
        names = {0: "Red", 1: "Blue"}
        i, j = parse_edge(move)
        return f"{names[s.to_move]} {i}-{j}"

    # ---- render ------------------------------------------------------------
    # Regular hexagon vertex layout: vertex 0 at top, going clockwise.
    @staticmethod
    def _vertex_xy():
        pts = []
        for i in range(N_VERTS):
            a = math.pi / 2 - i * math.pi / 3
            pts.append((math.cos(a), -math.sin(a)))
        return pts

    def render(self, s: SimState, perspective=None) -> dict:
        # A `polygons` board: each of the 15 edges is its OWN thin quadrilateral
        # cell (id = the move string "ei-j"), so an uncoloured edge is a legal
        # 1-cell move and the generic renderer makes it click-to-place. The 6
        # vertices are tiny diamond cells with no legal move (not clickable).
        verts = self._vertex_xy()
        cells = []
        tints = {}
        # Seat colours (Red = player 0, Blue = player 1).
        seat_color = {0: "#d2473a", 1: "#3a6bd2"}

        ET = 0.045          # half-thickness of an edge bar
        INSET = 0.12        # pull each edge end back from the vertex dot

        # Vertices first (drawn under edges). Small diamonds.
        DOT = 0.06
        for v, (x, y) in enumerate(verts):
            cells.append({
                "id": f"v{v}",
                "points": [
                    [x, y - DOT], [x + DOT, y], [x, y + DOT], [x - DOT, y],
                ],
            })

        # Edges: a thin rectangle oriented along the segment between its vertices.
        for (i, j) in ALL_EDGES:
            x1, y1 = verts[i]
            x2, y2 = verts[j]
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            ux, uy = dx / length, dy / length          # unit along edge
            nx, ny = -uy, ux                           # unit normal
            # inset endpoints so bars don't overlap the dots
            ax, ay = x1 + ux * INSET, y1 + uy * INSET
            bx, by = x2 - ux * INSET, y2 - uy * INSET
            cid = edge_id(i, j)
            cells.append({
                "id": cid,
                "points": [
                    [ax + nx * ET, ay + ny * ET],
                    [bx + nx * ET, by + ny * ET],
                    [bx - nx * ET, by - ny * ET],
                    [ax - nx * ET, ay - ny * ET],
                ],
            })
            owner = s.colors.get((i, j))
            if owner is not None:
                tints[cid] = seat_color[owner]

        names = {0: "Red", 1: "Blue"}
        if self.is_terminal(s) and s.loser is not None:
            w = 1 - s.loser
            cap = (f"{names[w]} wins  ·  {names[s.loser]} completed a "
                   f"{names[s.loser]} triangle")
        elif self.is_terminal(s):
            cap = "Game over"
        else:
            cap = f"{names[s.to_move]} to move  ·  avoid making a triangle of your colour"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": [],
            "highlights": [],
            "caption": cap,
        }
