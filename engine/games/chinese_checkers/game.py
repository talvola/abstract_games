"""Chinese Checkers (Sternhalma) -- the six-player classic on the 121-point star.

The board is the hexagram of cube coordinates ``(a, b, c)`` with ``a + b + c = 0``,
``max|coord| <= 8`` and ``median|coord| <= 4``: a central hexagon of 61 points and
six triangular points of 10. Each of the six players starts with ten marbles in
one point and races them to the **opposite** point; the first to fill it wins.
A marble steps to an adjacent empty point, or makes a chain of jumps -- hopping
over a single adjacent marble (anyone's) to the empty point directly beyond, as
many times as it can in one move. Nothing is ever captured.

Points are addressed ``"a,b"`` (c = -a-b is implied). This is the platform's
first six-seat game; the engine already cycles ``num_players`` and the web UI
seats all six.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# 6 cube directions (a, b); c follows.
DIRS = [(1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1)]
PLY_CAP = 600


def _build():
    cells = []
    for a in range(-8, 9):
        for b in range(-8, 9):
            c = -a - b
            if abs(c) > 8:
                continue
            ms = sorted((abs(a), abs(b), abs(c)))
            if ms[2] <= 8 and ms[1] <= 4:
                cells.append((a, b))
    cellset = set(cells)
    # camp of an outer point: which coord is the extreme (|.|>4) and its sign
    def camp_of(a, b):
        c = -a - b
        for i, v in enumerate((a, b, c)):
            if abs(v) > 4:
                return (i, 1 if v > 0 else -1)
        return None
    # six camps in cyclic order around the star; OPP[i] is i's opposite camp
    order = [(0, 1), (2, -1), (1, 1), (0, -1), (2, 1), (1, -1)]
    camps = [[(a, b) for (a, b) in cells if camp_of(a, b) == key] for key in order]
    opp = {key: order.index((key[0], -key[1])) for key in order}
    OPP = [opp[order[i]] for i in range(6)]
    return cells, cellset, camps, OPP


CELLS, CELLSET, CAMPS, OPP = _build()


def _cell(s):
    a, b = s.split(",")
    return int(a), int(b)


def _neighbors(a, b):
    for da, db in DIRS:
        nb = (a + da, b + db)
        if nb in CELLSET:
            yield nb


@dataclass
class CCState:
    nplayers: int = 6
    board: dict = field(default_factory=dict)        # (a,b) -> player
    to_move: int = 0
    ply: int = 0
    winner: object = None


class ChineseCheckers(Game):
    uid = "chinese_checkers"
    name = "Chinese Checkers"
    NPLAYERS = 6

    @property
    def num_players(self):
        return self.NPLAYERS

    def initial_state(self, options=None, rng=None):
        board = {}
        for p in range(self.NPLAYERS):
            for sq in CAMPS[p]:
                board[sq] = p
        return CCState(nplayers=self.NPLAYERS, board=board, to_move=0)

    def current_player(self, s):
        return s.to_move

    # ---- moves -------------------------------------------------------------
    def _jump_targets(self, board, start):
        """All cells reachable from `start` by one or more jumps (the start cell
        must be treated as vacated)."""
        seen = {start}
        out = []
        stack = [start]
        while stack:
            a, b = stack.pop()
            for da, db in DIRS:
                over = (a + da, b + db)
                land = (a + 2 * da, b + 2 * db)
                if over in board and land in CELLSET and land not in board and land not in seen:
                    seen.add(land)
                    out.append(land)
                    stack.append(land)
        return out

    def legal_moves(self, s):
        if s.winner is not None or s.ply >= PLY_CAP:
            return []
        pl = s.to_move
        out = []
        for (a, b), who in s.board.items():
            if who != pl:
                continue
            for nb in _neighbors(a, b):
                if nb not in s.board:
                    out.append(f"{a},{b}>{nb[0]},{nb[1]}")
            for land in self._jump_targets(s.board, (a, b)):
                out.append(f"{a},{b}>{land[0]},{land[1]}")
        return out

    def apply_move(self, s, move, rng=None):
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        board[to] = board.pop(frm)
        pl = s.to_move
        winner = pl if all(board.get(sq) == pl for sq in CAMPS[OPP[pl]]) else None
        return CCState(nplayers=s.nplayers, board=board,
                       to_move=(pl + 1) % self.NPLAYERS, ply=s.ply + 1, winner=winner)

    def is_terminal(self, s):
        return s.winner is not None or s.ply >= PLY_CAP

    def returns(self, s):
        if s.winner is None:
            return [0.0] * self.NPLAYERS
        return [1.0 if i == s.winner else -1.0 for i in range(self.NPLAYERS)]

    def serialize(self, s):
        return {"nplayers": s.nplayers,
                "board": {f"{a},{b}": p for (a, b), p in s.board.items()},
                "to_move": s.to_move, "ply": s.ply, "winner": s.winner}

    def deserialize(self, d):
        return CCState(nplayers=d.get("nplayers", 6),
                       board={_cell(k): v for k, v in d["board"].items()},
                       to_move=d["to_move"], ply=d.get("ply", 0), winner=d.get("winner"))

    def describe_move(self, s, move):
        return move

    # ---- presentation ------------------------------------------------------
    def render(self, s, perspective=None):
        import math
        S = 1.0
        cells = []
        rad = 0.56
        for (a, b) in CELLS:
            cx = S * math.sqrt(3) * (a + b / 2.0)
            cy = S * 1.5 * b
            pts = [[round(cx + rad * math.cos(math.radians(60 * k + 30)), 3),
                    round(cy + rad * math.sin(math.radians(60 * k + 30)), 3)] for k in range(6)]
            cells.append({"id": f"{a},{b}", "points": pts})
        pieces = [{"cell": f"{a},{b}", "owner": p} for (a, b), p in s.board.items()]
        if s.winner is not None:
            cap = f"Player {s.winner + 1} wins (filled the far point)"
        elif s.ply >= PLY_CAP:
            cap = "Draw (move cap)"
        else:
            cap = f"Player {s.to_move + 1} to move"
        return {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
