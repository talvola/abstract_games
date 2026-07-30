"""Flume -- Mark Steere (January 2010).

Implemented from the author's rule sheet, the "Go set" edition
(marksteeregames.com/Flume_Go_rules.pdf, revised 2022 -- see rules.md), whose
Figures 3 and 4 are the only published worked examples of the cascade rule and
are replayed verbatim in ``selftest.py``.

Board model
-----------
Flume is played on the intersections of an odd-sized square grid whose
*outermost ring* is pre-filled with permanent, ownerless GREEN stones (Fig. 1).
So the package models the **whole** grid: ``size`` = the odd playable side
``n``, the grid is ``(n+2) x (n+2)`` with cell ids ``"c,r"``, ``0 <= c,r <
n+2``, the perimeter (``c`` or ``r`` equal to ``0`` or ``n+1``) is green and the
interior ``1..n`` square is playable.  Modelling the ring explicitly (rather
than "an edge counts as one stone") keeps move notation and the rendered board
in the SAME coordinate system, and draws the board exactly as Steere does.

Rules as implemented
--------------------
* Red (seat 0) moves first.  A **turn** is a run of one or more placements.
* You may place a stone of your own colour on any empty playable point.
* Count the placed stone's *connections* = its occupied orthogonal neighbours,
  where **green ring stones count exactly like coloured stones**.  If the count
  is **3 or 4** you must immediately place again (same turn); the turn ends on a
  placement with **2 or fewer** connections.
* One placement = one ply.  ``current_player`` keeps returning the same seat
  through a cascade and ``cont`` records that the seat owes another stone, so
  ``legal_moves`` stays a flat list of empty points instead of an exponential
  enumeration of whole cascades.
* Anti-mirroring: on Red's *first turn* Red may not play the centre point.
  (Red's first turn is provably a single placement -- on an empty board a
  placement has at most 2 connections -- so "first turn" and "first placement"
  coincide; see rules.md.)
* Pie rule: instead of placing, Blue's first turn may be ``"swap"``, which
  recolours the stones on the board and hands the move back to seat 0.
* The board fills up; whoever ends with more stones wins.  ``n`` is odd so
  ``n*n`` is odd and a tie is arithmetically impossible; as soon as a seat holds
  ``(n*n+1)//2`` stones the result is decided and the game ends.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

SIZES = (5, 7, 9, 11, 17)
GO_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"      # Go convention: no "I"


def _cell(txt):
    c, r = txt.split(",")
    return int(c), int(r)


def grid_size(n):
    """Full grid side (playable ``n`` plus the green ring on both sides)."""
    return n + 2


def is_green(n, c, r):
    """The permanent ownerless ring stone at grid point ``(c, r)``?"""
    g = grid_size(n)
    return c == 0 or r == 0 or c == g - 1 or r == g - 1


def playable_cells(n):
    return [(c, r) for r in range(1, n + 1) for c in range(1, n + 1)]


def centre(n):
    """The banned first-turn point (unique because ``n`` is odd)."""
    h = grid_size(n) // 2
    return (h, h)


def connections(board, n, c, r):
    """Occupied orthogonal neighbours of ``(c, r)`` -- green ring included."""
    k = 0
    for nc, nr in ((c - 1, r), (c + 1, r), (c, r - 1), (c, r + 1)):
        if is_green(n, nc, nr) or (nc, nr) in board:
            k += 1
    return k


def majority_target(n):
    """Stones that settle the game (``n*n`` is odd, so this is a strict half)."""
    return (n * n + 1) // 2


@dataclass
class FState:
    size: int = 7                               # playable side n (odd)
    board: dict = field(default_factory=dict)   # {(c,r): 0|1} placed stones
    to_move: int = 0
    cont: bool = False                          # to_move owes another stone
    turns: int = 0                              # completed turns
    swapped: bool = False
    marks: tuple = ()                           # this run's placements (highlight)


class Flume(Game):
    name = "Flume"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        n = int((options or {}).get("size", 7))
        if n not in SIZES:
            raise ValueError(f"unsupported board size {n}; choose from {SIZES}")
        if n % 2 == 0 or n < 3:
            raise ValueError("Flume needs an odd playable side of at least 3")
        return FState(size=n)

    def current_player(self, s):
        return s.to_move

    # ---- terminal / result -------------------------------------------------

    def _scores(self, s):
        a = sum(1 for v in s.board.values() if v == 0)
        return [a, len(s.board) - a]

    def _winner(self, s):
        target = majority_target(s.size)
        a, b = self._scores(s)
        if a >= target:
            return 0
        if b >= target:
            return 1
        return None

    def is_terminal(self, s):
        return self._winner(s) is not None

    def returns(self, s):
        a, b = self._scores(s)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]       # honest draw; unreachable (n*n is odd, see rules.md)

    # ---- moves -------------------------------------------------------------

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        banned = centre(s.size) if s.turns == 0 else None
        moves = [f"{c},{r}" for (c, r) in playable_cells(s.size)
                 if (c, r) not in s.board and (c, r) != banned]
        if s.turns == 1 and s.to_move == 1 and not s.swapped and not s.cont:
            moves.append("swap")                # pie rule: Blue's first turn only
        return moves

    def apply_move(self, s, move, rng=None):
        if move == "swap":
            # Pie rule: Blue takes over Red's opening stone.  Recolouring every
            # stone and handing the move back to seat 0 reproduces the physical
            # act exactly (the position is otherwise symmetric).
            board = {p: 1 - v for p, v in s.board.items()}
            return FState(size=s.size, board=board, to_move=0, cont=False,
                          turns=s.turns + 1, swapped=True,
                          marks=tuple(sorted(board)))
        c, r = _cell(move)
        conn = connections(s.board, s.size, c, r)
        board = dict(s.board)
        board[(c, r)] = s.to_move
        marks = (s.marks + ((c, r),)) if s.cont else ((c, r),)
        nxt = FState(size=s.size, board=board, to_move=s.to_move, cont=False,
                     turns=s.turns, swapped=s.swapped, marks=marks)
        # 3 or 4 connections => place again, still your turn (unless it is over)
        if conn >= 3 and self._winner(nxt) is None:
            nxt.cont = True
        else:
            nxt.to_move = 1 - s.to_move
            nxt.turns = s.turns + 1
        return nxt

    # ---- bot eval ----------------------------------------------------------

    def heuristic(self, s):
        a, b = self._scores(s)
        if self.is_terminal(s):
            return self.returns(s)
        v = math.tanh(2.0 * (a - b) / s.size)
        return [v, -v]

    # ---- persistence -------------------------------------------------------

    def serialize(self, s):
        return {
            "size": s.size,
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "to_move": s.to_move,
            "cont": s.cont,
            "turns": s.turns,
            "swapped": s.swapped,
            "marks": [f"{c},{r}" for (c, r) in s.marks],
        }

    def deserialize(self, d):
        return FState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            cont=d.get("cont", False),
            turns=d.get("turns", 0),
            swapped=d.get("swapped", False),
            marks=tuple(_cell(k) for k in d.get("marks", ())),
        )

    # ---- presentation ------------------------------------------------------

    def describe_move(self, s, move):
        if move == "swap":
            return "swap (pie)"
        c, r = _cell(move)
        col = GO_LETTERS[c - 1] if c - 1 < len(GO_LETTERS) else str(c)
        tag = f"{col}{r}"
        if connections(s.board, s.size, c, r) >= 3:
            probe = FState(size=s.size, board=dict(s.board))
            probe.board[(c, r)] = s.to_move
            if self._winner(probe) is None:
                tag += "+"                      # 3-4 connections: place again
        return tag

    def render(self, s, perspective=None):
        n, g = s.size, grid_size(s.size)
        names = {0: "Red", 1: "Blue"}
        pieces, tints = [], {}
        for r in range(g):
            for c in range(g):
                if is_green(n, c, r):
                    cid = f"{c},{r}"
                    tints[cid] = "#1d2a1c"
                    pieces.append({"cell": cid, "owner": 0,
                                   "fill": "#3aa93f", "stroke": "#1b6b22"})
        for (c, r), v in s.board.items():
            pieces.append({"cell": f"{c},{r}", "owner": v})
        highlights = [{"cell": f"{c},{r}", "kind": "last-move"} for (c, r) in s.marks]
        a, b = self._scores(s)
        w = self._winner(s)
        if w is not None:
            # The game stops the instant a seat holds a strict majority, so the
            # two counts need NOT add up to n*n -- say so rather than printing a
            # bare "of 49 points" beside 22 + 25 = 47.
            left = n * n - (a + b)
            caption = f"{names[w]} wins  ·  Red {a} / Blue {b}"
            caption += (f"  ·  all {n * n} points played" if not left else
                        f"  ·  decided, {left} of {n * n} points unplayed")
        else:
            caption = f"{names[s.to_move]} to move  ·  Red {a} / Blue {b}"
            if s.cont:
                caption += "  ·  must place again (same turn)"
            if s.swapped:
                caption += "  ·  swapped"
        return {
            "board": {"type": "square", "width": g, "height": g, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
