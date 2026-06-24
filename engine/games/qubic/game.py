"""Qubic — 4x4x4 three-dimensional tic-tac-toe (Parker Brothers, 1953).

Two players (0 = X, 1 = O) alternately place one mark on any empty cell of a
4x4x4 cube (coordinates (x, y, z), each 0..3 — 64 cells). There is NO gravity
(unlike Score Four): any empty cell is legal. The first player to get FOUR of
their own marks in a straight line wins. A straight line is any of the 76
winning lines of the cube: the axis-parallel rows/columns/pillars, the 2D
face diagonals, and the 3D space (corner-to-corner) diagonals. A full board
with no completed line is a draw (rare in practice; with perfect play the first
player wins — Patashnik 1980).

THE 76 LINES are enumerated programmatically (see ``WIN_LINES``): for every
cell and every of the 26 unit directions, the four collinear cells
(c, c+d, c+2d, c+3d) form a line if they all stay inside the cube; collecting
these as unordered sets de-duplicates to exactly 76. Breakdown (standard
published result): 48 axis lines (4*4 per axis * 3 axes), 24 face diagonals
(2 per 4x4 face plane * 12 planes), 4 space diagonals.

RENDERING. The cube is drawn on a ``polygons`` board as four side-by-side
4x4 grids, one per layer z = 0..3, laid out left→right with a gap between
layers. Each of the 64 cells is a square whose ``id`` is its move string
``"x,y,z"``. Because the cell id equals the (single-cell) legal move, the
generic renderer's labelled-id click-to-place makes every empty cell clickable
(Board.jsx: a polygons cell whose id is a legal move is click-to-place). Marks
render as seat-coloured discs with an X / O label; a faint per-layer tint band
distinguishes the four grids.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

SIZE = 4
MARKS = {0: "X", 1: "O"}


@lru_cache(maxsize=1)
def _win_lines() -> tuple:
    """All 76 winning lines, each a frozenset of 4 (x,y,z) cells."""
    dirs = [
        (dx, dy, dz)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        for dz in (-1, 0, 1)
        if (dx, dy, dz) != (0, 0, 0)
    ]
    lines = set()
    for x in range(SIZE):
        for y in range(SIZE):
            for z in range(SIZE):
                for dx, dy, dz in dirs:
                    cells = []
                    ok = True
                    for k in range(SIZE):
                        nx, ny, nz = x + k * dx, y + k * dy, z + k * dz
                        if not (0 <= nx < SIZE and 0 <= ny < SIZE and 0 <= nz < SIZE):
                            ok = False
                            break
                        cells.append((nx, ny, nz))
                    if ok:
                        lines.add(frozenset(cells))
    return tuple(lines)


@lru_cache(maxsize=1)
def _lines_through() -> dict:
    """cell -> tuple of the win-lines passing through it (for fast win checks)."""
    out: dict = {}
    for line in _win_lines():
        for c in line:
            out.setdefault(c, []).append(line)
    return {c: tuple(v) for c, v in out.items()}


@lru_cache(maxsize=1)
def _all_cells() -> tuple:
    return tuple(
        (x, y, z)
        for z in range(SIZE)
        for y in range(SIZE)
        for x in range(SIZE)
    )


def _key(c: tuple) -> str:
    return f"{c[0]},{c[1]},{c[2]}"


def _cell(s: str) -> tuple:
    x, y, z = s.split(",")
    return int(x), int(y), int(z)


@dataclass
class QubicState:
    board: dict = field(default_factory=dict)   # (x,y,z) -> 0 or 1
    to_move: int = 0
    winner: Optional[int] = None                # 0, 1, or None
    last: Optional[tuple] = None


class Qubic(Game):
    uid = "qubic"
    name = "Qubic"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> QubicState:
        return QubicState()

    def current_player(self, s: QubicState) -> int:
        return s.to_move

    def legal_moves(self, s: QubicState):
        if self.is_terminal(s):
            return []
        return [_key(c) for c in _all_cells() if c not in s.board]

    def apply_move(self, s: QubicState, move: str, rng=None) -> QubicState:
        if self.is_terminal(s):
            raise ValueError("game over")
        cell = _cell(move)
        if cell not in _lines_through() or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        mover = s.to_move
        board = dict(s.board)
        board[cell] = mover
        winner = None
        for line in _lines_through()[cell]:
            if all(board.get(c) == mover for c in line):
                winner = mover
                break
        return QubicState(board=board, to_move=1 - mover, winner=winner, last=cell)

    def is_terminal(self, s: QubicState) -> bool:
        return s.winner is not None or len(s.board) == SIZE ** 3

    def returns(self, s: QubicState):
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: QubicState) -> dict:
        return {
            "board": {_key(c): p for c, p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "last": (_key(s.last) if s.last is not None else None),
        }

    def deserialize(self, d: dict) -> QubicState:
        last = d.get("last")
        return QubicState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            last=(_cell(last) if last else None),
        )

    def describe_move(self, s: QubicState, move: str) -> str:
        x, y, z = _cell(move)
        return f"{MARKS[s.to_move]} ({x},{y},{z})"

    # ---- presentation ------------------------------------------------------
    def render(self, s: QubicState, perspective=None) -> dict:
        # Four 4x4 grids side by side: layer z occupies x-columns
        # [z*(SIZE+GAP) .. z*(SIZE+GAP)+SIZE]. One unit = one cell.
        GAP = 1.5
        layer_tint = ["#26303f", "#2a3a2c", "#3a302a", "#382a3a"]
        cells = []
        tints = {}
        for (x, y, z) in _all_cells():
            ox = z * (SIZE + GAP) + x
            # y grows downward (row 0 at top)
            oy = y
            pts = [
                [round(ox, 3), round(oy, 3)],
                [round(ox + 1, 3), round(oy, 3)],
                [round(ox + 1, 3), round(oy + 1, 3)],
                [round(ox, 3), round(oy + 1, 3)],
            ]
            cid = _key((x, y, z))
            cells.append({"id": cid, "points": pts})
            tints[cid] = layer_tint[z]

        # Layer captions as cosmetic text are not supported; we distinguish
        # layers by the tint band above plus the cell ids (x,y,z) themselves.
        pieces = [
            {"cell": _key(c), "owner": p, "label": MARKS[p]}
            for c, p in s.board.items()
        ]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": _key(s.last), "kind": "last-move"})

        if s.winner is not None:
            caption = f"{MARKS[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            caption = (
                f"{MARKS[s.to_move]} to move  —  layers z=0..3 left→right"
            )

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
