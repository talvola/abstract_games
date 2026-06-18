"""FoxSox — Fox and Geese on triangular cells (Bob Henderson, faithfully ported
from his Zillions rules file).

The board is a rhombus of triangular cells, n per side (n = 4..9 → 2*n^2 cells),
encoded on a (row, col) grid as in the ZRF. The six directions connect each
triangle to its neighbours; the "killed" grid points (both coords ≡ 1 mod 3) are
the tiling's vertices, not cells.

* GEESE (player 0, move first): several pieces, each moves to an empty neighbour
  in a "rightward" direction only (se / s / sw).
* FOX (player 1): one piece, moves to any empty neighbour (all 6 directions —
  i.e. any of its 3 triangle edges).
No captures or jumps.

Win: the Fox wins by reaching the far corner (cell B2). The Geese win by
stalemating the Fox (no move). If the Geese run out of moves first it's a draw
(the fox can't be caught but hasn't escaped). Geese only ever advance, so the
game terminates.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

GEESE, FOX = 0, 1
PLY_CAP = 400

# (drow, dcol) for each direction, and their pixel offsets in the ZRF basis
# row -> (26,-15), col -> (26,15). Directions sit at 60° intervals.
DIRS = {"n": (-1, -1), "ne": (-2, 1), "se": (-1, 2), "s": (1, 1), "sw": (2, -1), "nw": (1, -2)}
GEESE_DIRS = ("se", "s", "sw")  # "rightward"
GEESE_START = {
    4: [(5, 2), (3, 3), (2, 5)],
    5: [(2, 2), (5, 2), (3, 3), (2, 5)],
    6: [(2, 2), (5, 2), (3, 3), (2, 5)],
    7: [(5, 2), (2, 5), (6, 3), (5, 5), (3, 6)],
    8: [(5, 2), (2, 5), (6, 3), (5, 5), (3, 6)],
    9: [(5, 2), (2, 5), (6, 3), (5, 5), (3, 6)],
}
GOAL = (2, 2)


def _kill(r, c):
    return (r - 1) % 3 == 0 and (c - 1) % 3 == 0


def _board_cells(n: int) -> set:
    """The set of (row, col) triangle cells for size n, by BFS over the 6 dirs."""
    M = 3 * n + 1
    fox = (3 * n, 3 * n)

    def valid(p):
        r, c = p
        return 1 <= r <= M and 1 <= c <= M and not _kill(r, c)

    seen = {fox}
    q = deque([fox])
    while q:
        p = q.popleft()
        for dr, dc in DIRS.values():
            np = (p[0] + dr, p[1] + dc)
            if valid(np) and np not in seen:
                seen.add(np)
                q.append(np)
    return seen


def _cid(p):  # cell id
    return f"{p[0]},{p[1]}"


def _cell(s: str):
    r, c = s.split(",")
    return int(r), int(c)


def _rowname(r: int) -> str:
    return chr(ord("A") + r - 1) if r <= 26 else chr(ord("A") + (r - 27)) * 2


@dataclass
class FoxSoxState:
    size: int = 4
    board: dict = field(default_factory=dict)  # (r, c) -> 0 (goose) / 1 (fox)
    to_move: int = GEESE
    winner: Optional[int] = None
    drawn: bool = False
    ply: int = 0


class FoxSox(Game):
    uid = "foxsox"
    name = "FoxSox"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> FoxSoxState:
        n = int((options or {}).get("size", 4))
        cells = _board_cells(n)  # validates the size is buildable
        board = {(3 * n, 3 * n): FOX}
        for g in GEESE_START[n]:
            board[g] = GEESE
        # sanity: every starting piece must be on a real cell
        assert all(p in cells for p in board), "bad FoxSox setup"
        return FoxSoxState(size=n, board=board)

    def _cells(self, s: FoxSoxState) -> set:
        return _board_cells(s.size)

    def current_player(self, s: FoxSoxState) -> int:
        return s.to_move

    def _raw_moves(self, s: FoxSoxState) -> list[str]:
        cells = self._cells(s)
        dirs = list(DIRS.values()) if s.to_move == FOX else [DIRS[k] for k in GEESE_DIRS]
        out = []
        for (r, c), pl in s.board.items():
            if pl != s.to_move:
                continue
            for dr, dc in dirs:
                t = (r + dr, c + dc)
                if t in cells and t not in s.board:
                    out.append(f"{r},{c}>{t[0]},{t[1]}")
        return out

    def is_terminal(self, s: FoxSoxState) -> bool:
        return s.winner is not None or s.drawn or not self._raw_moves(s)

    def legal_moves(self, s: FoxSoxState) -> list[str]:
        return [] if self.is_terminal(s) else self._raw_moves(s)

    def apply_move(self, s: FoxSoxState, move: str, rng=None) -> FoxSoxState:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        mover = s.to_move
        board = dict(s.board)
        del board[frm]
        board[to] = mover
        winner = FOX if (mover == FOX and to == GOAL) else None
        ply = s.ply + 1
        drawn = winner is None and ply >= PLY_CAP
        return FoxSoxState(size=s.size, board=board, to_move=1 - mover,
                           winner=winner, drawn=drawn, ply=ply)

    def returns(self, s: FoxSoxState) -> list[float]:
        if s.winner == FOX:
            return [-1.0, 1.0]   # geese lose, fox wins
        if s.drawn:
            return [0.0, 0.0]
        # terminal because the player to move is stuck:
        #   fox stuck -> geese win; geese stuck -> draw (fox uncatchable, not escaped)
        if s.to_move == FOX:
            return [1.0, -1.0]   # geese win
        return [0.0, 0.0]        # geese stuck -> draw

    def serialize(self, s: FoxSoxState) -> dict:
        return {
            "size": s.size,
            "board": {_cid(p): v for p, v in s.board.items()},
            "to_move": s.to_move, "winner": s.winner, "drawn": s.drawn, "ply": s.ply,
        }

    def deserialize(self, d: dict) -> FoxSoxState:
        return FoxSoxState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], winner=d["winner"],
            drawn=d.get("drawn", False), ply=d.get("ply", 0),
        )

    def describe_move(self, s: FoxSoxState, move: str) -> str:
        fs, ts = move.split(">")
        (fr, fc), (tr, tc) = _cell(fs), _cell(ts)
        who = "F" if s.board.get((fr, fc)) == FOX else "G"
        return f"{who} {_rowname(fr)}{fc}-{_rowname(tr)}{tc}"

    # ---- rendering: triangular cells as polygons ----
    @staticmethod
    def _center(r, c):
        return (26 * (r + c), 15 * (c - r))

    @staticmethod
    def _triangle(r, c):
        cx, cy = FoxSox._center(r, c)
        # type A cells (vertices toward 0/120/240°) vs type B (180/60/300°)
        angles = (0, 120, 240) if (2 * c - r) % 3 == 0 else (180, 60, 300)
        return [[round(cx + 52 * math.cos(math.radians(a)), 1),
                 round(cy + 52 * math.sin(math.radians(a)), 1)] for a in angles]

    def render(self, s: FoxSoxState, perspective=None) -> dict:
        cells = self._cells(s)
        cell_specs = [{"id": _cid(p), "points": self._triangle(*p)} for p in sorted(cells)]
        pieces = [
            {"cell": _cid(p), "owner": v, "label": "F" if v == FOX else ""}
            for p, v in s.board.items()
        ]
        highlights = [{"cell": _cid(GOAL), "kind": "goal"}]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret == [0.0, 0.0] else ("Fox wins" if ret[1] > 0 else "Geese win")
        else:
            caption = "Geese to move" if s.to_move == GEESE else "Fox to move"
        return {
            "board": {"type": "polygons", "cells": cell_specs},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
