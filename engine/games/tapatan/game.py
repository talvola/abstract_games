"""Tapatan -- Three Men's Morris on a 3x3 grid of 9 points.

A two-phase game with NO capture (unlike Nine Men's Morris):

* PHASE 1 (placement): players alternate placing one man on any empty point
  until each has placed three.
* PHASE 2 (movement): a player slides one of their men along a board line to an
  adjacent empty point.

The eight winning lines are the three rows, three columns, and two main
diagonals. Sliding adjacency = two points are adjacent iff they are consecutive
along one of those eight lines, so the centre is adjacent to all eight outer
points, a corner is adjacent to its two edge-midpoints and the centre, and an
edge-midpoint is adjacent to its two corners and the centre.

A player WINS the instant their three men occupy one of the eight lines -- which
can happen during placement or during movement. Because the movement phase could
otherwise repeat forever, a no-progress draw is declared after a hard cap of
movement plies with no win.

Points are addressed by their grid coordinate ``"x,y"`` on a 0..2 layout, and
the points + the cosmetic lines are supplied to the generic ``polygons``
renderer (adjacency and the win lines live in code).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# 9 points on a 0..2 grid (x right, y down).
COORDS = [(x, y) for y in range(3) for x in range(3)]
POINTS = [f"{x},{y}" for (x, y) in COORDS]

MEN = 3  # men per player


def _lines():
    """The eight winning lines: 3 rows, 3 columns, 2 main diagonals."""
    lines = []
    for y in range(3):                       # rows
        lines.append(tuple(f"{x},{y}" for x in range(3)))
    for x in range(3):                       # columns
        lines.append(tuple(f"{x},{y}" for y in range(3)))
    lines.append(tuple(f"{i},{i}" for i in range(3)))          # main diagonal
    lines.append(tuple(f"{i},{2 - i}" for i in range(3)))      # anti-diagonal
    return lines


LINES = _lines()                              # 8 winning lines
LINES_AT = {p: [ln for ln in LINES if p in ln] for p in POINTS}


def _adjacency():
    """Two points are adjacent iff consecutive along one of the eight lines."""
    adj = {p: set() for p in POINTS}
    for ln in LINES:
        for i in range(len(ln) - 1):
            a, b = ln[i], ln[i + 1]
            adj[a].add(b)
            adj[b].add(a)
    return {p: frozenset(s) for p, s in adj.items()}


ADJ = _adjacency()


# Cosmetic line segments for the renderer (the eight winning lines as strokes).
def _line_segments():
    segs = []
    for ln in LINES:
        a = tuple(int(v) for v in ln[0].split(","))
        c = tuple(int(v) for v in ln[-1].split(","))
        segs.append([list(a), list(c)])
    return segs


RENDER_LINES = _line_segments()


@dataclass
class TState:
    pos: dict = field(default_factory=dict)            # point -> player
    to_move: int = 0
    placed: list = field(default_factory=lambda: [0, 0])   # men placed per player
    move_plies: int = 0                                 # movement-phase plies so far
    winner: object = None                               # set when someone forms a line


class Tapatan(Game):
    uid = "tapatan"
    name = "Tapatan"
    MEN = MEN
    # Hard cap of movement plies with no win -> draw (no-progress / termination
    # guarantee). 60 movement plies (30 full moves) is far beyond any sensible
    # game on a 9-point board.
    DRAW_MOVE_PLIES = 60

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return TState()

    def current_player(self, state):
        return state.to_move

    # ---- helpers -----------------------------------------------------------
    def _phase_placing(self, state, pl):
        return state.placed[pl] < self.MEN

    def _both_placed(self, state):
        return state.placed[0] >= self.MEN and state.placed[1] >= self.MEN

    def _is_line(self, pos, pl):
        return any(all(pos.get(q) == pl for q in ln) for ln in LINES)

    def _draw(self, state):
        return state.winner is None and state.move_plies >= self.DRAW_MOVE_PLIES

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        pl = state.to_move
        if self._phase_placing(state, pl):
            return [p for p in POINTS if p not in state.pos]
        # movement phase: slide a man to an adjacent empty point
        out = []
        for p, v in state.pos.items():
            if v != pl:
                continue
            for q in ADJ[p]:
                if q not in state.pos:
                    out.append(f"{p}>{q}")
        return out

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        pos = dict(state.pos)
        placed = list(state.placed)
        move_plies = state.move_plies

        if ">" in move:                              # movement
            frm, to = move.split(">")
            pos[to] = pos.pop(frm)
            move_plies += 1
        else:                                        # placement
            pos[move] = pl
            placed[pl] += 1

        winner = pl if self._is_line(pos, pl) else None
        ns = TState(pos=pos, to_move=1 - pl, placed=placed,
                    move_plies=move_plies, winner=winner)
        return ns

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
            "pos": {p: v for p, v in state.pos.items()},
            "to_move": state.to_move,
            "placed": list(state.placed),
            "move_plies": state.move_plies,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return TState(pos=dict(d["pos"]), to_move=d["to_move"],
                      placed=list(d["placed"]),
                      move_plies=d.get("move_plies", 0),
                      winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if ">" in move:
            return move.replace(">", "-")
        return f"@{move}"

    def render(self, state, perspective=None):
        cells = []
        for (x, y) in COORDS:
            s = 0.42
            cells.append({"id": f"{x},{y}",
                          "points": [[x - s, y - s], [x + s, y - s],
                                     [x + s, y + s], [x - s, y + s]]})
        pieces = [{"cell": p, "owner": v} for p, v in state.pos.items()]
        names = {0: "White", 1: "Black"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        elif self._phase_placing(state, state.to_move):
            left = self.MEN - state.placed[state.to_move]
            cap = f"{names[state.to_move]} to place ({left} in hand)"
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": RENDER_LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
