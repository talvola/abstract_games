"""Tsoro Yematatu -- a traditional Shona (Zimbabwean) three-in-a-row game.

Played on a SEVEN-point board: an isosceles triangle with a horizontal line
across its breadth and a vertical line down its central axis. That figure gives
seven intersection points wired by five straight lines of three.

Each player has three men. In **phase 1** players alternately place their three
men on empty points. In **phase 2** a turn is moving one man along a board line
to an adjacent empty point, OR **jumping** over an adjacent man (friend or enemy)
along a line to the empty point beyond -- jumps do NOT capture. A player wins by
getting their three men on one of the board's five lines of three; in the
standard rule a line completed during placement does NOT win (see ``rules.md``).

Points are addressed by their grid coordinate ``"x,y"`` on the diagram and fed,
with the cosmetic line segments, to the generic ``polygons`` renderer; adjacency
and the win-lines live in code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# Seven points of the triangular figure, on a grid (x right, y down):
#
#                 0  (apex)
#               / | \
#             1 - 2 - 3      (horizontal midline)
#           /     |     \
#         4 ----- 5 ----- 6  (base)
#
#   left side : 0-1-4   |  right side : 0-3-6
#   midline   : 1-2-3   |  base       : 4-5-6   |  central axis : 0-2-5
COORDS = {
    "0": (3, 0),   # apex
    "1": (1, 2),   # mid-left
    "2": (3, 2),   # centre
    "3": (5, 2),   # mid-right
    "4": (0, 4),   # base-left
    "5": (3, 4),   # base-centre
    "6": (6, 4),   # base-right
}
POINTS = list(COORDS)

# The five straight lines of the board (each an ordered triple of collinear,
# pairwise-adjacent points). These are simultaneously the win-lines and the
# source of both the adjacency graph and the legal jumps.
LINES = [
    ("0", "1", "4"),   # left side
    ("0", "3", "6"),   # right side
    ("1", "2", "3"),   # horizontal midline
    ("4", "5", "6"),   # base
    ("0", "2", "5"),   # central axis
]


def _adjacency():
    adj = {p: set() for p in POINTS}
    for a, b, c in LINES:
        adj[a].add(b); adj[b].add(a)
        adj[b].add(c); adj[c].add(b)
    return {p: frozenset(s) for p, s in adj.items()}


ADJ = _adjacency()


def _jumps():
    """point -> {over: landing} for every aligned (a, over, b) triple."""
    jmp = {p: {} for p in POINTS}
    for a, b, c in LINES:
        jmp[a][b] = c          # a jumps over b, lands on c
        jmp[c][b] = a          # and the reverse
    return jmp


JUMPS = _jumps()


def _cosmetic_lines():
    """Line segments (in cell-coordinate space) for the renderer to draw."""
    segs = []
    for a, b, c in LINES:
        segs.append([list(COORDS[a]), list(COORDS[c])])
    return segs


COSMETIC_LINES = _cosmetic_lines()


@dataclass
class TState:
    pos: dict = field(default_factory=dict)              # point -> player (0/1)
    to_move: int = 0
    placed: list = field(default_factory=lambda: [0, 0])  # men placed per player
    plies: int = 0                                        # total plies played
    no_progress: int = 0                                  # moves since a placement (draw clock)
    winner: object = None                                 # set when a line is completed


class TsoroYematatu(Game):
    uid = "tsoro_yematatu"
    name = "Tsoro Yematatu"
    MEN = 3
    DRAW_PLIES = 60        # movement plies with no placement -> draw (termination guard)
    PLACEMENT_WIN = False  # default; overridden by initial_state from options

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        self.PLACEMENT_WIN = opts.get("placement_win", "no") == "yes"
        return TState()

    def current_player(self, state):
        return state.to_move

    # ---- helpers -----------------------------------------------------------
    def _phase_placing(self, state, pl):
        return state.placed[pl] < self.MEN

    def _both_placed(self, state):
        return state.placed[0] >= self.MEN and state.placed[1] >= self.MEN

    def _has_line(self, pos, pl):
        return any(all(pos.get(p) == pl for p in line) for line in LINES)

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        pl = state.to_move
        if self._phase_placing(state, pl):
            return [p for p in POINTS if p not in state.pos]
        # movement phase: slides and jumps
        out = []
        for p, v in state.pos.items():
            if v != pl:
                continue
            for q in ADJ[p]:                       # slide to an adjacent empty point
                if q not in state.pos:
                    out.append(f"{p}>{q}")
            for over, land in JUMPS[p].items():    # jump an occupied neighbour
                if over in state.pos and land not in state.pos:
                    out.append(f"{p}>{land}")
        return out

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        pos = dict(state.pos)
        placed = list(state.placed)
        plies = state.plies + 1
        no_progress = state.no_progress

        if ">" in move:                            # movement (slide or jump)
            frm, to = move.split(">")
            pos[to] = pos.pop(frm)
            no_progress += 1
        else:                                      # placement
            pos[move] = pl
            placed[pl] += 1
            no_progress = 0

        winner = None
        # A line wins, except (standard rule) one completed during the placement
        # phase: a three-in-a-row only counts once both players have placed all
        # their men. Toggle with the placement_win option.
        scoring = self.PLACEMENT_WIN or (placed[0] >= self.MEN and placed[1] >= self.MEN)
        if scoring and self._has_line(pos, pl):
            winner = pl

        ns = TState(pos=pos, to_move=1 - pl, placed=placed, plies=plies,
                    no_progress=no_progress, winner=winner)
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return state.winner is None and state.no_progress >= self.DRAW_PLIES

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
            "plies": state.plies,
            "no_progress": state.no_progress,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return TState(pos=dict(d["pos"]), to_move=d["to_move"],
                      placed=list(d["placed"]), plies=d.get("plies", 0),
                      no_progress=d.get("no_progress", 0), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if ">" in move:
            frm, to = move.split(">")
            # mark a jump (non-adjacent landing) distinctly from a slide
            if to in ADJ[frm]:
                return move.replace(">", "-")
            return move.replace(">", "^")     # jump
        return f"@{move}"

    def render(self, state, perspective=None):
        cells = []
        s = 0.42
        for p, (x, y) in COORDS.items():
            cells.append({"id": p,
                          "points": [[x - s, y - s], [x + s, y - s],
                                     [x + s, y + s], [x - s, y + s]]})
        pieces = [{"cell": p, "owner": v} for p, v in state.pos.items()]
        names = {0: "White", 1: "Black"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins (three in a row)"
        elif self._draw(state):
            cap = "Draw"
        elif self._phase_placing(state, state.to_move):
            left = self.MEN - state.placed[state.to_move]
            cap = f"{names[state.to_move]} to place ({left} in hand)"
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": COSMETIC_LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
