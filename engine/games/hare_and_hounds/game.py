"""Hare and Hounds -- the classic asymmetric hunt (a.k.a. the Soldier's Game /
Le Jeu Militaire / the French Military Game) on the 11-point board.

Player 0 is the three HOUNDS; player 1 is the lone HARE. The Hounds try to
corner the Hare so it cannot move; the Hare tries to slip past the Hounds to
their starting end (or wins if the Hounds dawdle -- the stalling rule).

Board: the standard 11-point board -- a 3x3 grid of points with one extra point
off the left-middle and one off the right-middle (a horizontally-stretched
cross / two-ended spearhead). Coordinates (x right, y down):

        1,0   2,0   3,0
    0,1 1,1   2,1   3,1 4,1
        1,2   2,2   3,2

Lines: every grid row and column is a line, the long middle row runs through
both apex points, and the centre point 2,1 is joined by a diagonal to each of
the four grid corners (the classic central X). There are NO diagonals in the
outer cells -- only the four through the centre. Adjacency/lines live in code;
the renderer draws the lines cosmetically (mirrors Nine Men's Morris).

Movement: a piece steps one point along a board line to an adjacent EMPTY point.
* HOUNDS may move forward (toward the Hare's / open right end, greater x) or
  sideways (vertical, same x) but NEVER back toward their own starting (left)
  end -- the no-retreat rule that makes the hunt finite.
* The HARE may move along any line in any direction.

Win conditions:
* The HOUNDS win by trapping the Hare so it has no legal move (or, defensively,
  if the Hounds themselves are ever left with no move, the Hare wins).
* The HARE wins by reaching the Hounds' starting end -- the left apex 0,1
  (slipping past all the Hounds).
* The HARE also wins by the STALLING rule: if the Hounds make 10 CONSECUTIVE
  non-advancing (sideways/vertical) moves -- counted across the turn alternation
  and NOT reset by the Hare's intervening moves -- they are deemed to be stalling.
  Any advancing (forward, x-increasing) Hound move resets the counter.

The Hounds move first (the traditional turn order). Moves are "from>to" cell
paths: click a piece, then an adjacent empty point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

HOUNDS, HARE = 0, 1
STALL_LIMIT = 10          # consecutive non-advancing Hound moves -> Hare wins (stalling)
PLY_CAP = 400             # hard safety cap (random play); should never bind in real play

# --- the 11-point board -----------------------------------------------------
LEFT_APEX = (0, 1)
RIGHT_APEX = (4, 1)
GRID = [(x, y) for x in (1, 2, 3) for y in (0, 1, 2)]
POINTS = [LEFT_APEX] + GRID + [RIGHT_APEX]
CENTER = (2, 1)
CORNERS = [(1, 0), (3, 0), (1, 2), (3, 2)]

# The Hare's escape goal: the Hounds' starting (left) end.
ESCAPE = LEFT_APEX


def _line_pairs():
    """Undirected adjacency pairs implied by the drawn board lines."""
    pairs = set()

    def add(a, b):
        pairs.add((a, b))
        pairs.add((b, a))

    # Three horizontal rows. The middle row runs through both apexes.
    add((1, 0), (2, 0)); add((2, 0), (3, 0))
    add(LEFT_APEX, (1, 1)); add((1, 1), (2, 1)); add((2, 1), (3, 1)); add((3, 1), RIGHT_APEX)
    add((1, 2), (2, 2)); add((2, 2), (3, 2))
    # Three vertical columns.
    for x in (1, 2, 3):
        add((x, 0), (x, 1)); add((x, 1), (x, 2))
    # The central X: centre joined to each grid corner.
    for c in CORNERS:
        add(CENTER, c)
    return pairs


_PAIRS = _line_pairs()
ADJ = {p: frozenset(b for (a, b) in _PAIRS if a == p) for p in POINTS}

# Cosmetic line segments for the renderer (each a 2-point polyline).
LINES = [[list(a), list(b)] for (a, b) in _PAIRS if a < b]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _str(p) -> str:
    return f"{p[0]},{p[1]}"


@dataclass
class HHState:
    board: dict = field(default_factory=dict)   # (x, y) -> HOUNDS / HARE
    to_move: int = HOUNDS
    winner: Optional[int] = None                # set when the Hare escapes / stalls
    vstalls: int = 0                            # consecutive non-advancing Hound moves (not reset by the Hare)
    ply: int = 0


def _start_board() -> dict:
    # Hounds on the three left-most grid points (the closed left end); the Hare
    # at the open right apex.
    b = {(1, 0): HOUNDS, (1, 1): HOUNDS, (1, 2): HOUNDS}
    b[RIGHT_APEX] = HARE
    return b


class HareAndHounds(Game):
    uid = "hare_and_hounds"
    name = "Hare and Hounds"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HHState:
        return HHState(board=_start_board())

    def current_player(self, s: HHState) -> int:
        return s.to_move

    # ---- moves -------------------------------------------------------------
    def _raw_moves(self, s: HHState) -> list[str]:
        out = []
        for (x, y), pl in s.board.items():
            if pl != s.to_move:
                continue
            for (tx, ty) in ADJ[(x, y)]:
                if (tx, ty) in s.board:
                    continue
                if s.to_move == HOUNDS and tx < x:
                    continue  # no-retreat: Hounds may not move toward their own (left) end
                out.append(f"{x},{y}>{tx},{ty}")
        return out

    def is_terminal(self, s: HHState) -> bool:
        return s.winner is not None or not self._raw_moves(s)

    def legal_moves(self, s: HHState) -> list[str]:
        return [] if self.is_terminal(s) else self._raw_moves(s)

    def apply_move(self, s: HHState, move: str, rng=None) -> HHState:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        mover = s.to_move
        board = dict(s.board)
        del board[frm]
        board[to] = mover

        winner = None
        vstalls = s.vstalls
        if mover == HOUNDS:
            # Stalling counts CONSECUTIVE non-advancing Hound moves. "Advancing"
            # = the Hound increased its x (moved toward the Hare's / open right
            # end -- the same forward direction the no-retreat rule is based on:
            # a Hound may never decrease x, so x can only stay equal or grow).
            # A move that keeps x the same (vertical/sideways shuffle) does NOT
            # advance and increments the counter; any forward move resets it.
            # The counter is NOT reset by the Hare's intervening move (see below),
            # so it accumulates across the alternation as the rule intends.
            if to[0] > frm[0]:
                vstalls = 0          # advanced -> reset
            else:
                vstalls += 1         # same x: non-advancing shuffle
            if vstalls >= STALL_LIMIT:
                winner = HARE
        else:  # HARE
            # Leave vstalls UNCHANGED: the stall streak tracks the Hounds across
            # the (hound, hare, hound, hare, ...) alternation and must survive the
            # Hare's intervening turn, or the threshold could never be reached.
            if to == ESCAPE:
                winner = HARE

        ply = s.ply + 1
        if winner is None and ply >= PLY_CAP:
            winner = HARE  # safety: a non-terminating random game favours the Hare (Hounds dawdled)
        return HHState(board=board, to_move=1 - mover, winner=winner,
                       vstalls=vstalls, ply=ply)

    def returns(self, s: HHState) -> list[float]:
        if s.winner == HARE:
            return [-1.0, 1.0]
        if s.winner == HOUNDS:
            return [1.0, -1.0]
        # terminal because the player to move has no legal move:
        #  Hare stuck  -> Hounds win;  Hounds stuck -> Hare wins.
        return [1.0, -1.0] if s.to_move == HARE else [-1.0, 1.0]

    # ---- serialize ---------------------------------------------------------
    def serialize(self, s: HHState) -> dict:
        return {
            "board": {_str(p): v for p, v in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "vstalls": s.vstalls,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> HHState:
        return HHState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], winner=d["winner"],
            vstalls=d.get("vstalls", 0), ply=d.get("ply", 0),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s: HHState, move: str) -> str:
        fs, ts = move.split(">")
        frm = _cell(fs)
        who = "Ho" if s.board.get(frm) == HOUNDS else "Ha"
        return f"{who} {fs}-{ts}"

    def render(self, s: HHState, perspective=None) -> dict:
        sz = 0.30
        cells = []
        for (x, y) in POINTS:
            cells.append({"id": _str((x, y)),
                          "points": [[x - sz, y - sz], [x + sz, y - sz],
                                     [x + sz, y + sz], [x - sz, y + sz]]})
        pieces = [{"cell": _str(p), "owner": v,
                   "label": "Ha" if v == HARE else ""}
                  for p, v in s.board.items()]

        if self.is_terminal(s):
            ret = self.returns(s)
            cap = "Hare wins" if ret[HARE] > 0 else "Hounds win"
        else:
            cap = "Hounds to move" if s.to_move == HOUNDS else "Hare to move"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
