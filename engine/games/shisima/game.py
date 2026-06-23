"""Shisima -- a traditional Kenyan three-in-a-row sliding game.

"Shisima" means "body of water" (the centre point); the pieces are the
*imbalavali* ("water bugs"). The board is an **octagon of 8 rim points plus a
central point** = 9 points in all.

Board / marked lines (see rules.md for the full discussion and sources):

* The 8 rim points sit at the corners of an octagon (indices ``0..7`` clockwise).
* The marked lines drawn on the board are (a) the OCTAGON RIM -- each rim point
  joined to its two ring-neighbours -- and (b) four DIAMETRICAL lines, each
  joining a rim point through the CENTRE to the diametrically opposite rim point.
* **Adjacency for sliding** therefore is: each rim point is adjacent to its two
  ring-neighbours (mod 8) and to the CENTRE (the next point along its diameter);
  the CENTRE is adjacent to all 8 rim points. A rim point is NOT adjacent to the
  opposite rim point, because the centre lies between them on the diameter.

Pieces: each player has THREE. Player 0 starts on three successive rim points
(0,1,2) and player 1 on the three opposite (4,5,6); rim points 3 and 7 and the
centre start empty, so there is a vacant point on both ends of each set.

A turn slides ONE of your pieces along a marked line to an ADJACENT EMPTY point.
There are NO captures and NO placement phase.

WIN: get your three pieces into a straight line **through the centre** -- i.e. a
diametrical line ``{rim i, centre, rim i+4}`` for i in 0..3 (4 such lines). A
"three-in-a-row" that does not pass through the centre is impossible here (no
three points are collinear except along a diameter through the centre).

Because sliding could otherwise repeat forever, a no-progress draw is declared
after a hard cap of plies with no win.

Points + cosmetic lines are supplied to the generic ``polygons`` renderer;
adjacency and the win lines live in code, mirroring tapatan / mu_torere.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

# Eight rim points on a circle (clockwise from the top) + the central "shisima".
CENTER_XY = (5.0, 5.0)
RADIUS = 4.0
CENTRE = "c"

RIM = [str(i) for i in range(8)]
POINTS = RIM + [CENTRE]

MEN = 3  # pieces per player


def _rim_xy(i):
    a = math.pi / 2 - i * (2 * math.pi / 8)   # top, going clockwise
    return (CENTER_XY[0] + math.cos(a) * RADIUS,
            CENTER_XY[1] - math.sin(a) * RADIUS)  # screen y grows downward


XY = {str(i): _rim_xy(i) for i in range(8)}
XY[CENTRE] = CENTER_XY


def _adjacency():
    """Adjacency along the marked lines: rim ring edges + rim<->centre spokes."""
    adj = {p: set() for p in POINTS}
    for i in range(8):
        a = str(i)
        adj[a].add(str((i + 1) % 8))   # ring neighbour
        adj[a].add(str((i - 1) % 8))   # ring neighbour
        adj[a].add(CENTRE)             # spoke (diameter through centre)
        adj[CENTRE].add(a)
    return {p: frozenset(s) for p, s in adj.items()}


ADJ = _adjacency()


def _win_lines():
    """The four diametrical winning lines: {rim i, centre, rim i+4}."""
    return [frozenset({str(i), CENTRE, str(i + 4)}) for i in range(4)]


WIN_LINES = _win_lines()


def _line_segments():
    """Cosmetic geometry: the 8 octagon rim edges + the 4 diameters."""
    segs = []
    for i in range(8):
        segs.append([list(XY[str(i)]), list(XY[str((i + 1) % 8)])])  # rim edge
    for i in range(4):                                               # diameter
        segs.append([list(XY[str(i)]), list(XY[str(i + 4)])])
    return segs


RENDER_LINES = _line_segments()


@dataclass
class SState:
    pos: dict = field(default_factory=dict)        # point -> player (0/1)
    to_move: int = 0
    ply: int = 0                                    # half-moves played (draw clock)
    winner: object = None                           # set when someone forms a line


class Shisima(Game):
    uid = "shisima"
    name = "Shisima"
    MEN = MEN
    # Hard cap of plies with no win -> draw (no-progress / termination guarantee).
    # The 9-point board has a tiny state space; 120 plies is far beyond any real
    # game and only guards against pathological non-progress under random play.
    PLY_CAP = 120

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        pos = {str(i): 0 for i in range(3)}        # player 0 on rim 0,1,2
        pos.update({str(i): 1 for i in range(4, 7)})  # player 1 on rim 4,5,6
        # rim points 3 and 7 and the centre start empty
        return SState(pos=pos, to_move=0, ply=0, winner=None)

    def current_player(self, state):
        return state.to_move

    # ---- helpers -----------------------------------------------------------
    def _is_line(self, pos, pl):
        return any(all(pos.get(q) == pl for q in ln) for ln in WIN_LINES)

    def _draw(self, state):
        return state.winner is None and state.ply >= self.PLY_CAP

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        pl = state.to_move
        out = []
        for src, owner in state.pos.items():
            if owner != pl:
                continue
            for dst in ADJ[src]:
                if dst not in state.pos:            # adjacent and empty
                    out.append(f"{src}>{dst}")
        return out

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        src, dst = move.split(">")
        pos = dict(state.pos)
        pos[dst] = pos.pop(src)
        winner = pl if self._is_line(pos, pl) else None
        return SState(pos=pos, to_move=1 - pl, ply=state.ply + 1, winner=winner)

    # ---- terminal ----------------------------------------------------------
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
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return SState(pos=dict(d["pos"]), to_move=d["to_move"],
                      ply=d.get("ply", 0), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        src, dst = move.split(">")
        name = lambda p: "shisima" if p == CENTRE else f"point {p}"
        return f"{name(src)}->{name(dst)}"

    def render(self, state, perspective=None):
        cells = []
        s = 0.5
        for p in POINTS:
            x, y = XY[p]
            cells.append({"id": p,
                          "points": [[x - s, y - s], [x + s, y - s],
                                     [x + s, y + s], [x - s, y + s]]})
        pieces = [{"cell": p, "owner": v} for p, v in state.pos.items()]
        names = {0: "Black", 1: "White"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw (ply cap)"
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": RENDER_LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
