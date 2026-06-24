"""Dots and Boxes -- the classic paper-and-pencil game (Edouard Lucas, 1889,
"La Pipopipette").

An m x n grid of BOXES is bounded by (m+1) x (n+1) dots. On a turn a player draws
one undrawn unit line (edge) between two orthogonally-adjacent dots. Completing the
fourth side of a box scores that box AND grants the SAME player another move (one
extra move, even if a single edge completed TWO boxes -- the chain of boxes is all
scored, then the player simply moves again once). A move that completes no box
passes the turn. The game ends when every edge is drawn; the player with the most
boxes wins (equal boxes => draw).

EDGE / MOVE ENCODING -- each edge is its OWN thin clickable cell on a `polygons`
board, whose id IS the move string, so the generic renderer makes an undrawn edge
(a legal 1-cell move) click-to-place:

  * Horizontal edge between dots (c,r) and (c+1,r):
        "H{c},{r}"  with c in 0..m-1, r in 0..n
  * Vertical edge between dots (c,r) and (c,r+1):
        "V{c},{r}"  with c in 0..m, r in 0..n-1

(The Quoridor `board.walls` primitive can't represent D&B edges -- its groove
segments are 2 cells long and never address the outer border -- so we render
edges as polygon cells instead; see render() below.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game


def _cr(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class DBState:
    m: int = 5                                  # boxes wide
    n: int = 5                                  # boxes tall
    h_edges: frozenset = field(default_factory=frozenset)   # drawn "Hc,r" keys (c,r)
    v_edges: frozenset = field(default_factory=frozenset)   # drawn "Vc,r" keys (c,r)
    owners: dict = field(default_factory=dict)  # (c,r) box -> player who closed it
    scores: list = field(default_factory=lambda: [0, 0])
    to_move: int = 0
    last_move: Optional[str] = None


class DotsAndBoxes(Game):
    uid = "dots_and_boxes"
    name = "Dots and Boxes"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DBState:
        opts = options or {}
        size = str(opts.get("size", "5x5"))
        m_s, n_s = size.lower().split("x")
        return DBState(m=int(m_s), n=int(n_s))

    def current_player(self, s: DBState) -> int:
        return s.to_move

    # ---- edges of a box ----------------------------------------------------
    @staticmethod
    def _box_edges(c, r):
        """The four edge-keys (kind, c, r) bounding box (c, r)."""
        return [
            ("H", c, r),       # bottom of box  (top gridline of box-row r-1 == r here)
            ("H", c, r + 1),   # top of box
            ("V", c, r),       # left of box    (right gridline of box-col c-1 == c here)
            ("V", c + 1, r),   # right of box
        ]

    def _drawn(self, s, kind, c, r):
        return (c, r) in (s.h_edges if kind == "H" else s.v_edges)

    def _all_edges(self, s):
        out = []
        for r in range(s.n + 1):
            for c in range(s.m):
                out.append(("H", c, r))
        for r in range(s.n):
            for c in range(s.m + 1):
                out.append(("V", c, r))
        return out

    def legal_moves(self, s: DBState):
        if self.is_terminal(s):
            return []
        out = []
        for kind, c, r in self._all_edges(s):
            if not self._drawn(s, kind, c, r):
                out.append(f"{kind}{c},{r}")
        return out

    # ---- which boxes does drawing (kind,c,r) complete? ---------------------
    def _boxes_touched(self, kind, c, r, m, n):
        """The (<=2) boxes that border edge (kind,c,r)."""
        boxes = []
        if kind == "H":
            # edge is the gridline at height r: borders box-row r (above) and r-1 (below)
            if r < n:
                boxes.append((c, r))          # box whose BOTTOM this edge is
            if r - 1 >= 0:
                boxes.append((c, r - 1))      # box whose TOP this edge is
        else:  # V: gridline at column c, borders box-col c (right) and c-1 (left)
            if c < m:
                boxes.append((c, r))          # box whose LEFT this edge is
            if c - 1 >= 0:
                boxes.append((c - 1, r))      # box whose RIGHT this edge is
        return boxes

    def _box_complete(self, h_edges, v_edges, c, r):
        for kind, ec, er in self._box_edges(c, r):
            store = h_edges if kind == "H" else v_edges
            if (ec, er) not in store:
                return False
        return True

    def apply_move(self, s: DBState, move: str, rng=None) -> DBState:
        kind = move[0]
        c, r = _cr(move[1:])
        h = set(s.h_edges)
        v = set(s.v_edges)
        if kind == "H":
            h.add((c, r))
        else:
            v.add((c, r))
        owners = dict(s.owners)
        scores = list(s.scores)
        closed = 0
        for bc, br in self._boxes_touched(kind, c, r, s.m, s.n):
            if (bc, br) not in owners and self._box_complete(h, v, bc, br):
                owners[(bc, br)] = s.to_move
                scores[s.to_move] += 1
                closed += 1
        # completing >=1 box => SAME player moves again (exactly one extra move,
        # regardless of how many boxes closed); else the turn passes.
        to_move = s.to_move if closed > 0 else 1 - s.to_move
        return DBState(
            m=s.m, n=s.n,
            h_edges=frozenset(h), v_edges=frozenset(v),
            owners=owners, scores=scores, to_move=to_move, last_move=move,
        )

    def is_terminal(self, s: DBState) -> bool:
        total = s.m * (s.n + 1) + s.n * (s.m + 1)
        return len(s.h_edges) + len(s.v_edges) >= total

    def returns(self, s: DBState):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        a, b = s.scores
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- (de)serialise -----------------------------------------------------
    def serialize(self, s: DBState) -> dict:
        return {
            "m": s.m, "n": s.n,
            "h_edges": sorted([list(e) for e in s.h_edges]),
            "v_edges": sorted([list(e) for e in s.v_edges]),
            "owners": [[c, r, p] for (c, r), p in sorted(s.owners.items())],
            "scores": list(s.scores),
            "to_move": s.to_move,
            "last_move": s.last_move,
        }

    def deserialize(self, d: dict) -> DBState:
        return DBState(
            m=d["m"], n=d["n"],
            h_edges=frozenset(tuple(e) for e in d.get("h_edges", [])),
            v_edges=frozenset(tuple(e) for e in d.get("v_edges", [])),
            owners={(c, r): p for c, r, p in d.get("owners", [])},
            scores=list(d.get("scores", [0, 0])),
            to_move=d["to_move"],
            last_move=d.get("last_move"),
        )

    def describe_move(self, s: DBState, move: str) -> str:
        names = {0: "P1", 1: "P2"}
        kind = move[0]
        c, r = _cr(move[1:])
        glyph = "─" if kind == "H" else "│"
        return f"{names[s.to_move]} {glyph} {kind}{c},{r}"

    # ---- render ------------------------------------------------------------
    def render(self, s: DBState, perspective=None) -> dict:
        # A `polygons` board: every edge is its OWN thin clickable cell (id =
        # the move string "Hc,r"/"Vc,r"), so an undrawn edge is a legal move and
        # the generic renderer makes it click-to-place. Dots are tiny square
        # cells (no legal move starts there -> not clickable). Boxes are square
        # cells, tinted in the owner's seat colour once closed and labelled.
        cells = []
        pieces = []
        tints = {}
        marks = {0: "1", 1: "2"}
        # Owner seat colours (faint box fills) so the board reads at a glance.
        box_fill = {0: "#4a2f24", 1: "#243149"}

        DOT = 0.10          # half-size of a dot square
        ET = 0.085          # half-thickness of an edge bar
        EL = 0.42           # half-length of an edge bar (slightly inset from dots)
        BX = 0.36           # half-size of a box square

        def rect(cx, cy, hx, hy):
            return [[cx - hx, cy - hy], [cx + hx, cy - hy],
                    [cx + hx, cy + hy], [cx - hx, cy + hy]]

        # Dots
        for dr in range(s.n + 1):
            for dc in range(s.m + 1):
                cells.append({"id": f"dot{dc},{dr}", "points": rect(dc, dr, DOT, DOT)})

        # Horizontal edges H c,r : between dots (c,r) and (c+1,r)
        for r in range(s.n + 1):
            for c in range(s.m):
                cid = f"H{c},{r}"
                cells.append({"id": cid, "points": rect(c + 0.5, r, EL, ET)})
                if (c, r) in s.h_edges:
                    tints[cid] = "#c9a96e"
        # Vertical edges V c,r : between dots (c,r) and (c,r+1)
        for r in range(s.n):
            for c in range(s.m + 1):
                cid = f"V{c},{r}"
                cells.append({"id": cid, "points": rect(c, r + 0.5, ET, EL)})
                if (c, r) in s.v_edges:
                    tints[cid] = "#c9a96e"

        # Boxes
        for r in range(s.n):
            for c in range(s.m):
                cid = f"box{c},{r}"
                cells.append({"id": cid, "points": rect(c + 0.5, r + 0.5, BX, BX)})
                if (c, r) in s.owners:
                    p = s.owners[(c, r)]
                    tints[cid] = box_fill[p]
                    pieces.append({"cell": cid, "owner": p, "label": marks[p]})

        names = {0: "Player 1", 1: "Player 2"}
        if self.is_terminal(s):
            a, b = s.scores
            if a == b:
                cap = f"Draw  ·  {a}–{b}"
            else:
                w = 0 if a > b else 1
                cap = f"{names[w]} wins  ·  {a}–{b}"
        else:
            cap = (f"{names[s.to_move]} to move  ·  "
                   f"P1 {s.scores[0]} – P2 {s.scores[1]}")

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
