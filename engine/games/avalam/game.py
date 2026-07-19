"""Avalam (Avalam Bitaka) -- Philippe Deweys, Belgium 1996 (SC.JP Fils.Fils /
Filsfils International; 1998 Mensa Select).

A pure stacking game on an irregular board of 49 depressions (an orthogonal
9x9 array with the corners shaved off).  48 pieces -- 24 Light, 24 Dark --
start one per depression in a strict checkerboard, the central depression
empty.  On your turn you MUST move any one stack (either colour on top --
ownership does not matter) exactly one cell in any of the 8 directions, onto
an adjacent occupied cell; the whole stack moves and lands on top.  No stack
may ever exceed 5 pieces, and you may never move onto an empty depression
(empty cells stay empty forever).  When no legal move remains, each stack
scores one point for the player whose colour is on top -- regardless of
height.  Most tops wins; an equal count is a draw (the published rules give
no tiebreak).

Every move merges two stacks into one, so the stack count strictly
decreases: the game always ends within 47 plies.

Board geometry pinned from the publisher's rulebook photo (SC.JP Fils.Fils,
"Le 49eme trou"), the Abstract Games #18 cover essay ("49 depressions"), and
the UCLouvain reference implementation (Vianney le Clement, 2010), which all
agree.

Cells are "c,r" (col 0-8, row 0-8) on the 49-cell footprint.  Moves are
"c1,r1>c2,r2".
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from agp.game import Game

LIGHT, DARK = 0, 1
NAMES = {LIGHT: "Light", DARK: "Dark"}
MAX_HEIGHT = 5
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]

# The board footprint: matrix[r][c] = 1 for a depression, 0 for off-board.
# Row r=0 is rendered at the TOP (matching the publisher's board photo).
# 49 depressions: rows of 2/4/6/8/9/8/6/4/2 holes; the central hole (4,4)
# is a real cell that starts (and therefore stays) empty.
FOOTPRINT = [
    [0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 1, 0, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 0],
]
CELLS = frozenset((c, r) for r in range(9) for c in range(9) if FOOTPRINT[r][c])
CENTER = (4, 4)


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _s(cell):
    return f"{cell[0]},{cell[1]}"


@dataclass
class AvState:
    board: dict = field(default_factory=dict)   # (c,r) -> tuple of owners, bottom->top
    to_move: int = LIGHT
    last: object = None                          # (src, dst) of the previous move
    ply: int = 0


class Avalam(Game):

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {}
        for (c, r) in CELLS:
            if (c, r) == CENTER:
                continue                         # the central depression starts empty
            board[(c, r)] = (LIGHT if (c + r) % 2 == 0 else DARK,)
        return AvState(board=board)

    def current_player(self, state):
        return state.to_move

    # ---- moves -------------------------------------------------------------
    def _moves(self, state):
        board = state.board
        out = []
        for (c, r), col in board.items():
            h = len(col)
            for (dc, dr) in DIRS:
                dst = (c + dc, r + dr)
                tgt = board.get(dst)
                if tgt is not None and h + len(tgt) <= MAX_HEIGHT:
                    out.append(((c, r), dst))
        return out

    def legal_moves(self, state):
        return [f"{_s(src)}>{_s(dst)}" for (src, dst) in self._moves(state)]

    def apply_move(self, state, move, rng=None):
        frm, _, to = move.partition(">")
        src, dst = _cell(frm), _cell(to)
        board = dict(state.board)
        moved = board.pop(src)
        board[dst] = board[dst] + moved          # the whole stack lands on top
        return AvState(board=board, to_move=1 - state.to_move,
                       last=(src, dst), ply=state.ply + 1)

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        return not self._moves(state)

    def _tops(self, state):
        t = [0, 0]
        for col in state.board.values():
            t[col[-1]] += 1
        return t

    def returns(self, state):
        t = self._tops(state)
        if t[LIGHT] > t[DARK]:
            return [1.0, -1.0]
        if t[DARK] > t[LIGHT]:
            return [-1.0, 1.0]
        return [0.0, 0.0]                        # honest draw: no official tiebreak

    def heuristic(self, state):
        """Top-count difference; a settled (isolated) tower counts full weight,
        a still-contested one half."""
        board = state.board
        bal = 0.0
        for (c, r), col in board.items():
            settled = not any((c + dc, r + dr) in board for (dc, dr) in DIRS)
            w = 1.0 if settled else 0.5
            bal += w if col[-1] == LIGHT else -w
        t = math.tanh(0.25 * bal)
        return [t, -t]

    # ---- serialise ---------------------------------------------------------
    def serialize(self, state):
        return {
            "board": {_s(cell): "".join(str(o) for o in col)
                      for cell, col in state.board.items()},
            "to_move": state.to_move,
            "last": None if state.last is None else [list(state.last[0]),
                                                     list(state.last[1])],
            "ply": state.ply,
        }

    def deserialize(self, d):
        last = d.get("last")
        return AvState(
            board={_cell(k): tuple(int(ch) for ch in v)
                   for k, v in d["board"].items()},
            to_move=d["to_move"],
            last=None if last is None else (tuple(last[0]), tuple(last[1])),
            ply=d.get("ply", 0))

    # ---- presentation ------------------------------------------------------
    @staticmethod
    def _alg(cell):
        return "abcdefghi"[cell[0]] + str(9 - cell[1])   # row 0 = rank 9 (top)

    def describe_move(self, state, move):
        frm, _, to = move.partition(">")
        src, dst = _cell(frm), _cell(to)
        h = len(state.board[src]) + len(state.board[dst])
        return f"{self._alg(src)}>{self._alg(dst)} (={h})"

    @staticmethod
    def _square_poly(c, r):
        y = 8 - r                                # row 0 at the top of the SVG
        return [[c, y], [c + 1, y], [c + 1, y + 1], [c, y + 1]]

    def render(self, state, perspective=None):
        cell_specs = [{"id": _s(cell), "points": self._square_poly(*cell)}
                      for cell in sorted(CELLS)]
        pieces = []
        for cell, col in state.board.items():
            pieces.append({"cell": _s(cell), "owner": col[-1],
                           "stack": list(col)})
        highlights = []
        if state.last is not None:
            highlights = [{"cell": _s(state.last[1]), "kind": "last-move"},
                          {"cell": _s(state.last[0]), "kind": "last-move"}]
        t = self._tops(state)
        if self.is_terminal(state):
            if t[LIGHT] > t[DARK]:
                cap = f"Light wins {t[LIGHT]}–{t[DARK]}"
            elif t[DARK] > t[LIGHT]:
                cap = f"Dark wins {t[DARK]}–{t[LIGHT]}"
            else:
                cap = f"Draw {t[LIGHT]}–{t[DARK]}"
        else:
            cap = (f"{NAMES[state.to_move]} to move · tops "
                   f"L {t[LIGHT]} / D {t[DARK]}")
        return {
            "board": {"type": "polygons", "cells": cell_specs},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
