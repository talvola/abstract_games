"""Goose Chase — Fox & Geese on pentagonal "paver" cells (Bob Henderson),
faithfully ported from his Zillions rules file.

The board is the Cairo pentagonal tiling: every cell is a pentagon with up to 5
edges (neighbours). The ZRF encodes it on a (col, row) grid where the "killed"
grid points are the tiling's vertices and the surviving points are cell centres.
A cell's grid coordinate (X, Y) = (column index, row index); its 12 candidate
neighbour directions are the ZRF directions, and which of them land on a real
cell determines the pentagon's edges. Eight board sizes ship as the `board`
option (see _boards.py, generated from the ZRF).

* FOX (player 1, the "King"): one piece; moves to any empty neighbouring cell
  (any of its <=5 pentagon edges).
* GEESE (player 0, the "Pawns", move first): several pieces, each moves to an
  empty neighbour but only in the 7 directions that don't head toward the Fox's
  goal — i.e. sideways or away from the goal. They never retreat toward the goal.
No captures or jumps.

Win: the Fox wins by reaching the goal cell. The Geese win by stalemating the
Fox (no legal move) — that's the whole point of the hunt. Per the Zillions
`pass-turn false` default, a side with no move loses, so a (very rare) Geese
stalemate is a Fox win. Geese only ever move sideways/away from the goal, but
sideways shuffling could loop forever, so a hard ply cap ends a dragging game in
a draw (the ZRF instead makes the Geese lose by repetition).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# Board definitions ported from Bob Henderson's "Goose Chase.zrf" (8 variants).
# Each cell id is the original ZRF label (column letter + row number). "cols"/"rows"
# list the grid axes (rows high->low, as in the ZRF); a cell's grid coordinate is
# (col_index, row_index) and the playable cells are the non-killed grid points.
# "cells" is the space-separated list of playable cells; geometry is derived below.
BOARDS = {
    "2x2": {
        "cols": "A/B/C/D/E/F/G/H/J",
        "rows": "11 10 9 8 7 6 5 4 3 2 1",
        "fox": "E1", "goal": "E11", "geese": "B8 H8 D9 F9",
        "cells": "A6 B8 B4 C6 D9 D3 E11 E7 E5 E1 F9 F3 G6 H8 H4 J6",
    },
    "3x2": {
        "cols": "A/B/C/D/E/F/G/H/J",
        "rows": "17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1",
        "fox": "H1", "goal": "H17", "geese": "H11 H13 D12 F12",
        "cells": (
            "A9 B11 B7 C9 D12 D6 E14 E10 E8 E4 F12 F6 G15 G9 G3 H17 H13 H11 H7 H5 H1 "
            "J15 J9 J3"
        ),
    },
    "3x3": {
        "cols": "A/B/C/D/E/F/G/H/J/K/L/M/N/O/P",
        "rows": "17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1",
        "fox": "H5", "goal": "H17", "geese": "D12 F12 K12 M12 H13",
        "cells": (
            "A9 B11 B7 C9 D12 D6 E14 E10 E8 E4 F12 F6 G15 G9 G3 H17 H13 H11 H7 H5 H1 "
            "J15 J9 J3 K12 K6 L14 L10 L8 L4 M12 M6 N9 O11 O7 P9"
        ),
    },
    "4x3": {
        "cols": "A/B/C/D/E/F/G/H/J/K/L/M",
        "rows": "23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1",
        "fox": "L1", "goal": "L23", "geese": "L19 G18 J18 L17",
        "cells": (
            "A12 B14 B10 C12 D15 D9 E17 E13 E11 E7 F15 F9 G18 G12 G6 H20 H16 H14 H10 H8 "
            "H4 J18 J12 J6 K21 K15 K9 K3 L23 L19 L17 L13 L11 L7 L5 L1 M21 M15 M9 M3"
        ),
    },
    "4x4": {
        "cols": "A/B/C/D/E/F/G/H/J/K/L/M/N/O/P/Q/R/S/T/U/V",
        "rows": "23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1",
        "fox": "L1", "goal": "L23", "geese": "G18 J18 N18 P18 L19",
        "cells": (
            "A12 B14 B10 C12 D15 D9 E17 E13 E11 E7 F15 F9 G18 G12 G6 H20 H16 H14 H10 H8 "
            "H4 J18 J12 J6 K21 K15 K9 K3 L23 L19 L17 L13 L11 L7 L5 L1 M21 M15 M9 M3 N18 "
            "N12 N6 O20 O16 O14 O10 O8 O4 P18 P12 P6 Q15 Q9 R17 R13 R11 R7 S15 S9 T12 U14 "
            "U10 V12"
        ),
    },
    "5x4": {
        "cols": "A/B/C/D/E/F/G/H/J/K/L/M/N/O/P",
        "rows": "29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1",
        "fox": "O1", "goal": "O29", "geese": "O25 O23 H23 K24 M24",
        "cells": (
            "A15 B17 B13 C15 D18 D12 E20 E16 E14 E10 F18 F12 G21 G15 G9 H23 H19 H17 H13 "
            "H11 H7 J21 J15 J9 K24 K18 K12 K6 L26 L22 L20 L16 L14 L10 L8 L4 M24 M18 M12 "
            "M6 N27 N21 N15 N9 N3 O29 O25 O23 O19 O17 O13 O11 O7 O5 O1 P27 P21 P15 P9 P3"
        ),
    },
    "5x5": {
        "cols": "A/B/C/D/E/F/G/H/J/K/L/M/N/O/P/Q/R/S/T/U/V/W/X/Y/Z/AA/AB",
        "rows": "29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1",
        "fox": "O5", "goal": "O29", "geese": "H23 U23 K24 M24 Q24 S24",
        "cells": (
            "A15 B17 B13 C15 D18 D12 E20 E16 E14 E10 F18 F12 G21 G15 G9 H23 H19 H17 H13 "
            "H11 H7 J21 J15 J9 K24 K18 K12 K6 L26 L22 L20 L16 L14 L10 L8 L4 M24 M18 M12 "
            "M6 N27 N21 N15 N9 N3 O29 O25 O23 O19 O17 O13 O11 O7 O5 O1 P27 P21 P15 P9 P3 "
            "Q24 Q18 Q12 Q6 R26 R22 R20 R16 R14 R10 R8 R4 S24 S18 S12 S6 T21 T15 T9 U23 "
            "U19 U17 U13 U11 U7 V21 V15 V9 W18 W12 X20 X16 X14 X10 Y18 Y12 Z15 AA17 AA13 "
            "AB15"
        ),
    },
    "6x5": {
        "cols": "A/B/C/D/E/F/G/H/J/K/L/M/N/O/P/Q/R/S",
        "rows": "35 34 33 32 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1",
        "fox": "R1", "goal": "R35", "geese": "O28 L29 R29 N30 P30",
        "cells": (
            "A18 B20 B16 C18 D21 D15 E23 E19 E17 E13 F21 F15 G24 G18 G12 H26 H22 H20 H16 "
            "H14 H10 J24 J18 J12 K27 K21 K15 K9 L29 L25 L23 L19 L17 L13 L11 L7 M27 M21 "
            "M15 M9 N30 N24 N18 N12 N6 O32 O28 O26 O22 O20 O16 O14 O10 O8 O4 P30 P24 P18 "
            "P12 P6 Q33 Q27 Q21 Q15 Q9 Q3 R35 R31 R29 R25 R23 R19 R17 R13 R11 R7 R5 R1 "
            "S33 S27 S21 S15 S9 S3"
        ),
    },
}

GEESE, FOX = 0, 1
PLY_CAP = 300

# 12 ZRF directions as (dX, dY) = (dColIndex, dRowIndex). Rows are listed high->low
# so Y increases away from the goal; "north" (toward the goal) is dY < 0.
DIRS = {
    "n": (0, -2), "e": (2, 0), "s": (0, 2), "w": (-2, 0),
    "nne": (1, -2), "ene": (2, -1), "ese": (2, 1), "sse": (1, 2),
    "ssw": (-1, 2), "wsw": (-2, 1), "wnw": (-2, -1), "nnw": (-1, -2),
}
# Geese may move in 7 of the 12 directions: never the 5 with a northward (toward
# the goal) component {n, nne, nnw, ene, wnw}.
GEESE_DIRS = ("e", "w", "s", "ese", "sse", "ssw", "wsw")

# Each cell's pentagon orientation is fixed by (X % 3, Y % 3); these are the full
# 5-edge direction sets per orientation (a cell uses the subset landing on real
# cells). Used only for rendering the pentagon outline.
ORIENT = {
    (1, 1): ("ese", "nne", "nnw", "s", "wsw"),
    (1, 0): ("ene", "n", "sse", "ssw", "wnw"),
    (2, 2): ("ene", "ese", "nnw", "ssw", "w"),
    (0, 2): ("e", "nne", "sse", "wnw", "wsw"),
}


def _clip(poly, v):
    """Sutherland–Hodgman clip of poly to the half-plane p·v <= |v|^2/2."""
    vx, vy = v
    c = (vx * vx + vy * vy) / 2.0
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        da = a[0] * vx + a[1] * vy - c
        db = b[0] * vx + b[1] * vy - c
        if da <= 1e-9:
            out.append(a)
        if (da <= 1e-9) != (db <= 1e-9):
            t = da / (da - db)
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def _pentagon(orient_key):
    """Pentagon vertices (centred at origin, grid units) for an orientation."""
    poly = [(-3.0, -3.0), (3.0, -3.0), (3.0, 3.0), (-3.0, 3.0)]
    for name in ORIENT[orient_key]:
        poly = _clip(poly, DIRS[name])
    return poly


_SHAPES = {k: _pentagon(k) for k in ORIENT}


class _BoardGeom:
    """Cells, coordinates and adjacency for one board variant (cached)."""

    _cache: dict = {}

    def __init__(self, key: str):
        b = BOARDS[key]
        self.key = key
        self.cols = b["cols"].split("/")
        self.rows = [int(r) for r in b["rows"].split()]
        self.rowindex = {r: i for i, r in enumerate(self.rows)}
        # Canonical cell id is the numeric grid coordinate "X,Y" (X = column index,
        # Y = row index). Numeric "c,r" ids are what the generic board renderer
        # recognises as click-to-move paths; the original ZRF label is kept only
        # for the move log (see describe_move).
        self.coord = {}   # "X,Y" -> (X, Y)
        self.label = {}   # "X,Y" -> ZRF label, e.g. "E11"
        for lab in b["cells"].split():
            x, y = self._xy(lab)
            cid = f"{x},{y}"
            self.coord[cid] = (x, y)
            self.label[cid] = lab
        self.cells = list(self.coord)
        self.fox = self._id(b["fox"])
        self.goal = self._id(b["goal"])
        self.geese = [self._id(g) for g in b["geese"].split()]
        # adjacency: cell -> {dirname: neighbour cell}
        valid = set(self.coord)
        self.adj = {}
        for cid, (x, y) in self.coord.items():
            nb = {}
            for name, (dx, dy) in DIRS.items():
                t = f"{x + dx},{y + dy}"
                if t in valid:
                    nb[name] = t
            self.adj[cid] = nb

    def _xy(self, label: str):
        i = 0
        while not label[i].isdigit():
            i += 1
        col, row = label[:i], int(label[i:])
        return (self.cols.index(col), self.rowindex[row])

    def _id(self, label: str) -> str:
        x, y = self._xy(label)
        return f"{x},{y}"

    @classmethod
    def get(cls, key: str) -> "_BoardGeom":
        g = cls._cache.get(key)
        if g is None:
            g = cls._cache[key] = cls(key)
        return g


@dataclass
class GooseChaseState:
    board_key: str = "3x3"
    board: dict = field(default_factory=dict)  # cell -> 0 (goose) / 1 (fox)
    to_move: int = GEESE
    winner: Optional[int] = None
    drawn: bool = False
    ply: int = 0


class GooseChase(Game):
    uid = "goose_chase"
    name = "Goose Chase"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> GooseChaseState:
        key = str((options or {}).get("board", "3x3"))
        if key not in BOARDS:
            raise ValueError(f"unknown board {key!r}")
        g = _BoardGeom.get(key)
        board = {g.fox: FOX}
        for goose in g.geese:
            board[goose] = GEESE
        return GooseChaseState(board_key=key, board=board)

    def current_player(self, s: GooseChaseState) -> int:
        return s.to_move

    def _raw_moves(self, s: GooseChaseState) -> list[str]:
        g = _BoardGeom.get(s.board_key)
        out = []
        if s.to_move == FOX:
            for c, owner in s.board.items():
                if owner != FOX:
                    continue
                for t in g.adj[c].values():
                    if t not in s.board:
                        out.append(f"{c}>{t}")
        else:
            for c, owner in s.board.items():
                if owner != GEESE:
                    continue
                for name in GEESE_DIRS:
                    t = g.adj[c].get(name)
                    if t is not None and t not in s.board:
                        out.append(f"{c}>{t}")
        return out

    def is_terminal(self, s: GooseChaseState) -> bool:
        return s.winner is not None or s.drawn or not self._raw_moves(s)

    def legal_moves(self, s: GooseChaseState) -> list[str]:
        return [] if self.is_terminal(s) else self._raw_moves(s)

    def apply_move(self, s: GooseChaseState, move: str, rng=None) -> GooseChaseState:
        frm, to = move.split(">")
        mover = s.to_move
        if s.board.get(frm) != mover or to in s.board:
            raise ValueError(f"illegal move {move!r}")
        g = _BoardGeom.get(s.board_key)
        if to not in g.adj[frm].values():
            raise ValueError(f"non-adjacent move {move!r}")
        board = dict(s.board)
        del board[frm]
        board[to] = mover
        winner = FOX if (mover == FOX and to == g.goal) else None
        ply = s.ply + 1
        drawn = winner is None and ply >= PLY_CAP
        return GooseChaseState(board_key=s.board_key, board=board,
                               to_move=1 - mover, winner=winner,
                               drawn=drawn, ply=ply)

    def returns(self, s: GooseChaseState) -> list[float]:
        if s.winner == FOX:
            return [-1.0, 1.0]      # geese lose, fox escaped
        if s.drawn:
            return [0.0, 0.0]
        # terminal because the side to move is stalemated (pass-turn false -> loss):
        #   fox stuck   -> geese win (the goal of the hunt)
        #   geese stuck -> fox wins (geese boxed in, fox is free)
        if s.to_move == FOX:
            return [1.0, -1.0]
        return [-1.0, 1.0]

    def serialize(self, s: GooseChaseState) -> dict:
        return {
            "board_key": s.board_key,
            "board": dict(s.board),
            "to_move": s.to_move,
            "winner": s.winner,
            "drawn": s.drawn,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> GooseChaseState:
        return GooseChaseState(
            board_key=d["board_key"],
            board=dict(d["board"]),
            to_move=d["to_move"],
            winner=d["winner"],
            drawn=d.get("drawn", False),
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: GooseChaseState, move: str) -> str:
        frm, to = move.split(">")
        g = _BoardGeom.get(s.board_key)
        who = "F" if s.board.get(frm) == FOX else "G"
        return f"{who} {g.label.get(frm, frm)}-{g.label.get(to, to)}"

    # ---- rendering: pentagonal cells as polygons ----
    def render(self, s: GooseChaseState, perspective=None) -> dict:
        g = _BoardGeom.get(s.board_key)
        SC = 30.0
        cell_specs = []
        for c in g.cells:
            x, y = g.coord[c]
            shape = _SHAPES[(x % 3, y % 3)]
            # Transpose to screen space (horizontal = row index, vertical = column)
            # so the Fox's goal sits on the left and the Fox starts on the right,
            # matching the original Zillions board orientation.
            pts = [[round((y + vy) * SC, 1), round((x + vx) * SC, 1)] for vx, vy in shape]
            cell_specs.append({"id": c, "points": pts})
        pieces = [
            {"cell": c, "owner": owner, "label": "F" if owner == FOX else ""}
            for c, owner in s.board.items()
        ]
        highlights = [{"cell": g.goal, "kind": "goal"}]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = ("Draw" if ret == [0.0, 0.0]
                       else "Fox wins" if ret[FOX] > 0 else "Geese win")
        else:
            caption = "Geese to move" if s.to_move == GEESE else "Fox to move"
        return {
            "board": {"type": "polygons", "cells": cell_specs},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
