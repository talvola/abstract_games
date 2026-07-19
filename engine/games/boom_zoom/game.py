"""Boom & Zoom -- Ty Bomba's abstract wargame of laser-tower stacks (2012,
Victory Point Games; definitive 2nd edition 2018, Hollandspiele).

Ruleset implemented: the Hollandspiele 2nd edition, as given in full by David
Ploog's article in Abstract Games magazine #21 (Spring 2021), pp. 21-25, and
cross-checked against Ploog's abstractgames.org/boomzoom.html page and BGG.

* 8x8 board. Each side has 12 counters, starting as four 3-high stacks on the
  four central squares of its home row (White c1/d1/e1/f1, Black c8/d8/e8/f8).
* A turn is exactly one action with ONE whole stack (stacks never split or
  merge; a stack is always a single colour):
  - ZOOM: move the stack in a straight line (any of the 8 directions, backwards
    allowed) over FREE squares; distance 1..height.
  - BOOM: instead of moving, shoot a square the stack could otherwise move to
    (straight line, clear path, distance <= height) that holds an enemy stack:
    remove ONE counter from it. Removed counters are gone (nobody scores them).
* Bearing off: beyond the OPPONENT's home row lies a virtual goal row of TEN
  squares (the 8 files plus one diagonal corner square past each edge -- AG#21
  clarification diagram: a piece may escape diagonally through the corner).
  A stack landing there leaves the board and scores 1 point per counter.
  Only that one row: a path may never leave the board sideways, and you may
  never enter your OWN side's virtual row.
* The game ends the moment one side has no counters left on the board (its
  last stack borne off, or its last counter shot). Higher score wins; an equal
  score is an honest draw.

Engine backstops (documented in rules.md): if 100 consecutive plies pass with
no counter leaving the board (no boom, no bear-off), the game is adjudicated
by the current score (equal = draw). A player with no legal action passes
(believed unreachable: a stack on the far rank can always bear off, and full
self-blocking needs more friendly stacks than the game provides).

Anchors (selftest.py): the AG#21 worked diagrams -- opening position, the
boom-range example, the corner bear-off clarification, the shoot-out
asymmetry, the White-timer table (24 entries), and BOTH end-game problems
(p. 25) played out move-by-move to the article's solutions (p. 29): a 9:8
White race win after the key capture f4:f5 and the 9:9 draw line, plus the
b4:b6 keystone of Problem 2.  NOTE: the magazine printed the two problem
diagrams with their captions/scores swapped; the positions used here are the
ones consistent with the printed solutions AND with counter accounting
(both checked exactly -- see selftest).

Cells are "c,r": files a..h = c 1..8, ranks r 1..8; White's goal row is r=9
(c 0..9), Black's is r=0 (c 0..9). Moves are "c1,r1>c2,r2" -- a move onto an
enemy-held square is a Boom (the shooter stays put), onto a free square a
Zoom, onto a goal-row square a bear-off.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
START_HEIGHT = 3
NO_PROGRESS_CAP = 100    # plies without a counter leaving the board -> adjudicate

# goal row rank per player (the row BEYOND the opponent's home row)
GOAL_ROW = {WHITE: 9, BLACK: 0}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _s(c, r):
    return f"{c},{r}"


def _interior(c, r):
    return 1 <= c <= 8 and 1 <= r <= 8


@dataclass
class BZState:
    board: dict = field(default_factory=dict)   # (c,r) -> (owner, height)
    scores: list = field(default_factory=lambda: [0, 0])
    to_move: int = WHITE
    since: int = 0        # plies since a counter last left the board
    ply: int = 0
    winner: object = None  # set when over and not a draw
    over: bool = False
    last: list = field(default_factory=list)    # last move's cells (highlights)


class BoomZoom(Game):

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        st = BZState()
        for c in (3, 4, 5, 6):
            st.board[(c, 1)] = (WHITE, START_HEIGHT)
            st.board[(c, 8)] = (BLACK, START_HEIGHT)
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------

    def _stack_moves(self, board, c, r, p, h):
        """All moves for the stack at (c,r): zooms, booms and bear-offs."""
        out = []
        src = _s(c, r)
        goal = GOAL_ROW[p]
        for dx, dy in DIRS:
            for d in range(1, h + 1):
                x, y = c + dx * d, r + dy * d
                if _interior(x, y):
                    occ = board.get((x, y))
                    if occ is None:
                        out.append(f"{src}>{_s(x, y)}")      # zoom
                        continue
                    if occ[0] != p:
                        out.append(f"{src}>{_s(x, y)}")      # boom
                    break                                     # line blocked
                # left the interior: only the mover's own goal row is legal,
                # and only its 10 squares (files a..h + the two corners)
                if y == goal and 0 <= x <= 9:
                    out.append(f"{src}>{_s(x, y)}")          # bear off
                break
        return out

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        p = state.to_move
        out = []
        for (c, r), (owner, h) in sorted(state.board.items()):
            if owner == p:
                out.extend(self._stack_moves(state.board, c, r, p, h))
        return out if out else ["pass"]

    # ---- applying moves ----------------------------------------------------

    def apply_move(self, state, move, rng=None):
        st = BZState(
            board=dict(state.board),
            scores=list(state.scores),
            to_move=state.to_move,
            since=state.since,
            ply=state.ply,
            winner=state.winner,
            over=state.over,
            last=list(state.last),
        )
        p = st.to_move
        removal = False
        if move == "pass":
            st.last = []
        else:
            frm, to = move.split(">")
            fc, fr = _cell(frm)
            tc, tr = _cell(to)
            owner, h = st.board[(fc, fr)]
            assert owner == p
            target = st.board.get((tc, tr)) if _interior(tc, tr) else None
            if target is not None:                    # BOOM: shooter stays put
                to_owner, th = target
                if th == 1:
                    del st.board[(tc, tr)]
                else:
                    st.board[(tc, tr)] = (to_owner, th - 1)
                removal = True
            elif _interior(tc, tr):                   # ZOOM
                del st.board[(fc, fr)]
                st.board[(tc, tr)] = (owner, h)
            else:                                     # bear off
                del st.board[(fc, fr)]
                st.scores[p] += h
                removal = True
            st.last = [frm, to]

        st.ply += 1
        st.since = 0 if removal else st.since + 1
        st.to_move = 1 - p

        on = [0, 0]
        for (owner, h) in st.board.values():
            on[owner] += h
        if on[WHITE] == 0 or on[BLACK] == 0 or st.since >= NO_PROGRESS_CAP:
            st.over = True
            if st.scores[WHITE] > st.scores[BLACK]:
                st.winner = WHITE
            elif st.scores[BLACK] > st.scores[WHITE]:
                st.winner = BLACK
            else:
                st.winner = None                      # honest draw
        return st

    def is_terminal(self, state):
        return state.over

    def returns(self, state):
        if state.winner is None:
            return [0, 0]
        return [1, -1] if state.winner == WHITE else [-1, 1]

    # ---- notation ----------------------------------------------------------

    @staticmethod
    def _alg(c, r):
        if 1 <= c <= 8 and 1 <= r <= 8:
            return "abcdefgh"[c - 1] + str(r)
        return "off"

    def describe_move(self, state, move):
        if move == "pass":
            return "pass"
        frm, to = move.split(">")
        fc, fr = _cell(frm)
        tc, tr = _cell(to)
        owner, h = state.board.get((fc, fr), (state.to_move, 0))
        a = self._alg(fc, fr)
        if not _interior(tc, tr):
            return f"{a}-off (+{h})"
        target = state.board.get((tc, tr))
        if target is not None and target[0] != owner:
            return f"{a}:{self._alg(tc, tr)} ({target[1]}→{target[1] - 1})"
        return f"{a}-{self._alg(tc, tr)}"

    # ---- serialization -----------------------------------------------------

    def serialize(self, state):
        return {
            "board": {_s(c, r): [o, h] for (c, r), (o, h) in sorted(state.board.items())},
            "scores": list(state.scores),
            "to_move": state.to_move,
            "since": state.since,
            "ply": state.ply,
            "winner": state.winner,
            "over": state.over,
            "last": list(state.last),
        }

    def deserialize(self, data):
        return BZState(
            board={_cell(k): (v[0], v[1]) for k, v in data["board"].items()},
            scores=list(data["scores"]),
            to_move=data["to_move"],
            since=data["since"],
            ply=data["ply"],
            winner=data["winner"],
            over=data["over"],
            last=list(data.get("last", [])),
        )

    # ---- bot eval ----------------------------------------------------------

    def heuristic(self, state):
        """Score + discounted bear-off potential per side. Returns [w, b]."""
        e = [float(state.scores[WHITE]), float(state.scores[BLACK])]
        for (c, r), (owner, h) in state.board.items():
            prog = (r - 1) if owner == WHITE else (8 - r)
            e[owner] += h * (0.70 + 0.04 * prog)
        v = math.tanh((e[WHITE] - e[BLACK]) / 3.0)
        return [v, -v]

    # ---- rendering ---------------------------------------------------------

    @staticmethod
    def _poly(c, r):
        y = 9 - r                       # rank 9 (White's goal) at the top
        return [[c, y], [c + 1, y], [c + 1, y + 1], [c, y + 1]]

    def render(self, state, perspective=None):
        cells = []
        tints = {}
        for r in range(1, 9):
            for c in range(1, 9):
                cells.append({"id": _s(c, r), "points": self._poly(c, r)})
                if (c + r) % 2 == 0:
                    tints[_s(c, r)] = "#ccd2db"
        for c in range(0, 10):          # the two 10-square virtual goal rows
            for r in (0, 9):
                cells.append({"id": _s(c, r), "points": self._poly(c, r)})
                tints[_s(c, r)] = "#f3d9e2" if (c % 2 == 0) else "#f9e9ef"
        pieces = [
            {"cell": _s(c, r), "owner": o, "stack": [o] * h}
            for (c, r), (o, h) in state.board.items()
        ]
        score = f"{NAMES[WHITE]} {state.scores[WHITE]} : {NAMES[BLACK]} {state.scores[BLACK]}"
        if state.over:
            if state.winner is None:
                cap = f"Draw — {score}"
            else:
                cap = f"{NAMES[state.winner]} wins — {score}"
        else:
            cap = f"{NAMES[state.to_move]} to move — {score}"
        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": [{"cell": cid, "kind": "last-move"} for cid in state.last],
            "caption": cap,
        }
