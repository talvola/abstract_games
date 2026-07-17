"""Hobak Gonu (호박고누, "pumpkin gonu") — traditional Korean blockade game.

BOARD (11 points, 14 edges — Ludii "Ho-Bag Gonu.lud" board graph, confirmed
against the figures of Ludii's cited source, nol2i.com):

        0,0 ---- 2,0 ---- 4,0        top home row (seat 1)
                  |
                 2,1                 circle: north
               /  |  \\
        1,2 --- 2,2 --- 3,2          circle: west - centre - east
               \\  |  /
                 2,3                 circle: south
                  |
        0,4 ---- 2,4 ---- 4,4        bottom home row (seat 0)

The four "diagonal" strokes above are the circle arcs: n-w, n-e, s-w, s-e
(the ring), and the centre 2,2 connects by the internal cross to all four
ring points.  14 edges total: 2 per home row, 2 connectors (home middle to
the nearest ring point), 4 ring arcs, 4 cross spokes.

RULES AS IMPLEMENTED (consensus of nol2i / namu.wiki / lflank; see rules.md
for sources and the documented interpretation points):

* 3 pieces each, starting on the player's home row.  Seat 0 (Black, bottom)
  moves first.  A move steps along one line to an adjacent EMPTY point.

* Home rows are ONE-WAY FUNNELS (all positional, no history needed):
    - no move may ever end on a home-row ENDPOINT (they are exit-only);
    - a home-row MIDDLE may only be entered from ITS OWN row's endpoints;
    - hence a piece that has reached the circle can never re-enter its own
      home row (nol2i rule 3), and a home piece beside an empty endpoint
      still counts as blocked (namu.wiki footnote; nol2i's own win diagram
      requires this).

* The five circle points (ring + centre) are free: any adjacent empty point
  that is not barred above.

* Opponent's home row — manifest option `invasion`:
    - "closed" (default): may never be entered (namu.wiki, lflank);
    - "trap": a piece may step from the circle onto the OPPONENT's home
      middle and may then move within the opponent's row (middle <->
      endpoints) but can never leave it (nol2i rule 4 / Ludii).

* A player with no legal move on their turn LOSES (blockade).

* TERMINATION: the first repetition of a position (occupancy + side to
  move) is an immediate honest DRAW, plus a PLY_CAP hard backstop.  The
  full solve (selftest.py re-runs it) shows BOTH variants are a DRAW under
  perfect play with cycle-as-draw semantics — matching namu.wiki's claim
  that the game has no forced win.

Cells are "c,r" strings on a virtual 5x5 grid; moves are "c1,r1>c2,r2".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# ---- board graph -----------------------------------------------------------

H0 = [(0, 4), (2, 4), (4, 4)]           # seat 0 home (bottom): end, mid, end
H1 = [(0, 0), (2, 0), (4, 0)]           # seat 1 home (top)
MID = {0: (2, 4), 1: (2, 0)}
ENDS = {0: frozenset({(0, 4), (4, 4)}), 1: frozenset({(0, 0), (4, 0)})}
HOME = {0: frozenset(H0), 1: frozenset(H1)}
CIRCLE = frozenset({(2, 3), (1, 2), (2, 2), (3, 2), (2, 1)})
POINTS = H0 + [(2, 3), (1, 2), (2, 2), (3, 2), (2, 1)] + H1

EDGES = [
    ((0, 4), (2, 4)), ((2, 4), (4, 4)),          # bottom home row
    ((0, 0), (2, 0)), ((2, 0), (4, 0)),          # top home row
    ((2, 4), (2, 3)), ((2, 0), (2, 1)),          # connectors
    ((2, 3), (1, 2)), ((1, 2), (2, 1)),          # ring arcs (SW, NW)
    ((2, 1), (3, 2)), ((3, 2), (2, 3)),          # ring arcs (NE, SE)
    ((2, 2), (2, 3)), ((2, 2), (1, 2)),          # cross spokes
    ((2, 2), (3, 2)), ((2, 2), (2, 1)),
]

ADJ = {p: [] for p in POINTS}
for _a, _b in EDGES:
    ADJ[_a].append(_b)
    ADJ[_b].append(_a)

NAMES = {0: "Black", 1: "White"}
# short point names for move-log notation
PT_NAME = {
    (0, 4): "bL", (2, 4): "bM", (4, 4): "bR",
    (0, 0): "tL", (2, 0): "tM", (4, 0): "tR",
    (2, 1): "n", (1, 2): "w", (2, 2): "c", (3, 2): "e", (2, 3): "s",
}

PLY_CAP = 200      # hard backstop; max forced-win depth in the solve is 22


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _key(pos: dict, to_move: int) -> str:
    return ";".join(f"{c},{r}:{o}" for (c, r), o in sorted(pos.items())) + f"|{to_move}"


@dataclass
class HGState:
    pos: dict = field(default_factory=dict)       # (c, r) -> 0 | 1
    to_move: int = 0
    variant: str = "closed"                       # "closed" | "trap"
    winner: Optional[int] = None                  # blockade winner
    drawn: bool = False                           # repetition draw
    ply: int = 0
    history: list = field(default_factory=list)   # position keys seen (incl. current)


class HobakGonu(Game):
    name = "Hobak Gonu"

    @property
    def num_players(self):
        return 2

    # ---- lifecycle ---------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        variant = (options or {}).get("invasion", "closed")
        if variant not in ("closed", "trap"):
            variant = "closed"
        pos = {p: 0 for p in H0}
        pos.update({p: 1 for p in H1})
        st = HGState(pos=pos, to_move=0, variant=variant)
        st.history = [_key(pos, 0)]
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _dst_ok(self, pl, src, dst, variant):
        """May player pl move src -> dst (dst known adjacent + empty)?"""
        opp = 1 - pl
        if dst in CIRCLE:
            # trap variant: once inside the opponent's row, never leave
            return src not in HOME[opp]
        if dst == MID[pl]:
            return src in ENDS[pl]                # funnel: own middle from own ends
        if dst in ENDS[pl]:
            return False                          # own endpoints are exit-only
        # dst is in the opponent's row
        if variant == "closed":
            return False
        if src in HOME[opp]:
            return True                           # move within the opponent's row
        return dst == MID[opp] and src in CIRCLE  # enter at the middle only

    def _moves_for(self, state, pl):
        out = []
        for src, owner in state.pos.items():
            if owner != pl:
                continue
            for dst in ADJ[src]:
                if dst not in state.pos and self._dst_ok(pl, src, dst, state.variant):
                    out.append(f"{src[0]},{src[1]}>{dst[0]},{dst[1]}")
        return sorted(out)

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        return self._moves_for(state, state.to_move)

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        a, b = move.split(">")
        src, dst = _cell(a), _cell(b)
        pos = dict(state.pos)
        pos[dst] = pos.pop(src)
        ns = HGState(pos=pos, to_move=1 - pl, variant=state.variant,
                     ply=state.ply + 1, history=list(state.history))
        # blockade: the player now on the move has no legal move -> mover wins
        if not self._moves_for(ns, ns.to_move):
            ns.winner = pl
            return ns
        # first repetition of a position (occupancy + side to move) -> draw
        k = _key(pos, ns.to_move)
        if k in ns.history:
            ns.drawn = True
        ns.history.append(k)
        return ns

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        return (state.winner is not None or state.drawn
                or state.ply >= PLY_CAP)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- bot helper --------------------------------------------------------
    def heuristic(self, state):
        """Mobility differential (one payoff per seat, like returns)."""
        m0 = len(self._moves_for(state, 0))
        m1 = len(self._moves_for(state, 1))
        v = max(-1.0, min(1.0, 0.15 * (m0 - m1)))
        return [v, -v]

    # ---- serialize ---------------------------------------------------------
    def serialize(self, state):
        return {
            "pos": {f"{c},{r}": o for (c, r), o in state.pos.items()},
            "to_move": state.to_move,
            "variant": state.variant,
            "winner": state.winner,
            "drawn": state.drawn,
            "ply": state.ply,
            "history": list(state.history),
        }

    def deserialize(self, d):
        return HGState(
            pos={_cell(k): v for k, v in d["pos"].items()},
            to_move=d["to_move"],
            variant=d.get("variant", "closed"),
            winner=d.get("winner"),
            drawn=d.get("drawn", False),
            ply=d.get("ply", 0),
            history=list(d.get("history", [])),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        a, b = move.split(">")
        return f"{PT_NAME[_cell(a)]}>{PT_NAME[_cell(b)]}"

    def render(self, state, perspective=None):
        import math
        s = 0.36
        cells = []
        for (c, r) in POINTS:
            cells.append({"id": f"{c},{r}",
                          "points": [[c - s, r - s], [c + s, r - s],
                                     [c + s, r + s], [c - s, r + s]]})
        lines = [
            [[0, 4], [4, 4]],            # bottom home row
            [[0, 0], [4, 0]],            # top home row
            [[2, 0], [2, 1]],            # top connector
            [[2, 3], [2, 4]],            # bottom connector
            [[2, 1], [2, 3]],            # cross: vertical
            [[1, 2], [3, 2]],            # cross: horizontal
        ]
        # the pumpkin: a circle of radius 1 about the centre (2,2), as a
        # closed polyline through the four ring points
        circle = [[2 + math.cos(t * math.pi / 18), 2 + math.sin(t * math.pi / 18)]
                  for t in range(37)]
        lines.append(circle)
        pieces = [{"cell": f"{c},{r}", "owner": o} for (c, r), o in state.pos.items()]
        if state.winner is not None:
            cap = f"{NAMES[state.winner]} wins (blockade)"
        elif state.drawn:
            cap = "Draw (repetition)"
        elif state.ply >= PLY_CAP:
            cap = "Draw (ply cap)"
        else:
            cap = f"{NAMES[state.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": lines},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
