"""The Game of Y -- the classic connection game (Claude Shannon / Craige Schensted
& Charles Titus). Played on a triangular board of hexagonal cells: place a stone
each turn; the first player to link **all three sides** of the triangle with one
connected group wins. Like Hex, Y can never end in a draw, so the game always
terminates.

The board is a triangle of side ``size``: cell ``(row, col)`` with ``row`` in
``0..size-1`` and ``col`` in ``0..row`` (row 0 is the top apex). Each cell touches
up to six neighbours. The three edges are the left side (col == 0), the right side
(col == row) and the bottom side (row == size-1). A swap (pie) move on the second
turn balances the first-move advantage.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

RED, BLUE = 0, 1
NEI = [(0, -1), (0, 1), (-1, -1), (-1, 0), (1, 0), (1, 1)]


def _cell(s):
    r, c = s.split(",")
    return int(r), int(c)


@dataclass
class YState:
    size: int = 11
    board: dict = field(default_factory=dict)        # (row,col) -> player
    to_move: int = RED
    ply: int = 0
    winner: object = None


class Y(Game):
    uid = "y"
    name = "Y"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        size = int((options or {}).get("size", 11))
        return YState(size=size)

    def current_player(self, s):
        return s.to_move

    def _cells(self, size):
        return [(r, c) for r in range(size) for c in range(r + 1)]

    def _neighbors(self, r, c, size):
        for dr, dc in NEI:
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc <= nr:
                yield (nr, nc)

    def _wins(self, board, player, size):
        """Does `player` have a single group touching all three sides?"""
        seen = set()
        for start in board:
            if board[start] != player or start in seen:
                continue
            stack = [start]
            seen.add(start)
            edges = 0b000
            while stack:
                r, c = stack.pop()
                if c == 0:
                    edges |= 0b001            # left
                if c == r:
                    edges |= 0b010            # right
                if r == size - 1:
                    edges |= 0b100            # bottom
                for nb in self._neighbors(r, c, size):
                    if nb not in seen and board.get(nb) == player:
                        seen.add(nb)
                        stack.append(nb)
            if edges == 0b111:
                return True
        return False

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        out = [f"{r},{c}" for (r, c) in self._cells(s.size) if (r, c) not in s.board]
        if s.ply == 1 and len(s.board) == 1:
            out.append("swap")               # pie rule: take over the opening move
        return out

    def apply_move(self, s, move, rng=None):
        board = dict(s.board)
        if move == "swap":
            sq = next(iter(board))
            board[sq] = s.to_move            # recolour the lone stone to the mover
            return YState(size=s.size, board=board, to_move=1 - s.to_move, ply=s.ply + 1)
        r, c = _cell(move)
        board[(r, c)] = s.to_move
        winner = s.to_move if self._wins(board, s.to_move, s.size) else None
        return YState(size=s.size, board=board, to_move=1 - s.to_move,
                      ply=s.ply + 1, winner=winner)

    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    def serialize(self, s):
        return {"size": s.size, "board": {f"{r},{c}": p for (r, c), p in s.board.items()},
                "to_move": s.to_move, "ply": s.ply, "winner": s.winner}

    def deserialize(self, d):
        return YState(size=d["size"], board={_cell(k): v for k, v in d["board"].items()},
                      to_move=d["to_move"], ply=d.get("ply", 0), winner=d.get("winner"))

    def describe_move(self, s, move):
        return move

    # ---- presentation ------------------------------------------------------
    def _hex(self, cx, cy, rad):
        pts = []
        for k in range(6):
            a = math.radians(60 * k + 30)
            pts.append([round(cx + rad * math.cos(a), 3), round(cy + rad * math.sin(a), 3)])
        return pts

    def render(self, s, perspective=None):
        size, S = s.size, 10.0
        rad = S * 0.62
        cells = []
        for (r, c) in self._cells(size):
            cx = S * (c - r / 2.0) * math.sqrt(3)
            cy = S * 1.5 * r
            cells.append({"id": f"{r},{c}", "points": self._hex(cx, cy, rad)})
        pieces = [{"cell": f"{r},{c}", "owner": p} for (r, c), p in s.board.items()]
        names = {RED: "Red", BLUE: "Blue"}
        if s.winner is not None:
            cap = f"{names[s.winner]} wins (Y connected)"
        else:
            cap = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
