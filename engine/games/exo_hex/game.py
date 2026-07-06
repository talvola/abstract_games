"""Exo-Hex, by Craig Duncan, 2019 (BGG 291638).

A two-player connection/scoring game on a hexhex-n board (hexagon of hexagonal
cells, side length n, n ODD). It is the "distilled" sibling of Duncan's Side
Stitch (2017): instead of coloured board sides, actual stones of both colours
sit OUTSIDE the board and are both the scoring targets and connectors.

SETUP (the "exo-stones").  Just outside each of the six sides of the board lies
an exterior row of n-1 pre-placed stones, occupying the off-board hex positions
of the ring at radius n (one hex further out than the board's edge). Each
side's exterior row is split into one black string and one white string of
(n-1)/2 stones each, and the 12 strings ALTERNATE in colour all the way around
the perimeter (6 strings per player). The 6 exterior CORNER positions of the
ring are EMPTY GAPS — no exo-stone sits on a corner.

This matches the designer's photographed hexhex-7 board (Silverman, "Connection
Games V"): every side, traversed in a consistent rotational direction, reads
(n-1)/2 stones of one colour then (n-1)/2 of the other, giving the alternating
12-string perimeter with a gap at each corner. Which colour comes "first" is a
pure orientation/reflection choice (any 60-degree rotation maps the arrangement
onto itself); we fix black-first and document it in rules.md.

ADJACENCY MODEL (derived from the ring geometry + the board photo):
  * Exo-stones occupy real hex positions, so ordinary hex adjacency applies to
    the union of interior cells and exo positions.
  * Consecutive exo-stones of a string are hex-adjacent — a string is
    CONNECTIVE (Silverman: "a chain of stones coming in one end of a given side
    is still connected to a chain coming out the other end").
  * Each exo-stone is adjacent to exactly two interior edge cells.
  * The two exo-stones flanking a corner gap are NOT adjacent to each other
    (they are two ring steps apart) — the gap breaks the perimeter there.
  * An interior CORNER cell is adjacent to the last exo-stone of one side and
    the first exo-stone of the next (which are opposite colours).

PLAY.  Black (seat 0) moves first. On a turn, place one stone of your colour on
any empty INTERIOR cell (exo positions are never playable), or pass. Stones
never move. Pie rule: on the second player's first turn they may "swap" (take
over the first stone as their own colour) instead of placing. The game ends
when both players pass in succession, or when the board is full.

SCORING.  A player's stones — interior placements plus their own exo-stones —
form connected groups under hex adjacency. A group scores the number of
EXO-STONES it contains. The owner of the single highest-scoring group wins.
Ties recurse: set the tied groups aside and compare the next-best groups, i.e.
compare the two players' descending lists of group scores lexicographically
(missing entries count 0). The designer states a tie "all the way down" is
impossible; that holds for played-out boards (extensive full-board fuzzing
found none), but a genuine tie IS reachable when both players pass early in a
symmetric position (e.g. an immediate double pass on the untouched start).
Such an all-the-way tie is scored as a DRAW (documented in rules.md).

Coordinates are axial (q, r); interior = max(|q|,|r|,|q+r|) <= n-1, exo ring at
radius n. Interior move strings are "q,r"; exo render-cell ids are "x:q,r".

Sources: designer's rules in the BGG description (objectid 291638);
https://drericsilverman.com/2020/03/12/connection-games-v-side-stitch/
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # seat 0 = Black, places first

_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

# Ring corners of the exo ring (radius n), in rotational order.
_CORNER_UNITS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]


def _radius(q: int, r: int) -> int:
    return max(abs(q), abs(r), abs(q + r))


@lru_cache(maxsize=None)
def _cells(n: int) -> tuple:
    """All interior (playable) cells of the hexhex-n board: radius <= n-1."""
    rad = n - 1
    out = [
        (q, r)
        for q in range(-rad, rad + 1)
        for r in range(-rad, rad + 1)
        if _radius(q, r) <= rad
    ]
    return tuple(sorted(out))


@lru_cache(maxsize=None)
def _cell_set(n: int) -> frozenset:
    return frozenset(_cells(n))


@lru_cache(maxsize=None)
def _exo(n: int) -> dict:
    """(q, r) -> owner for the 6(n-1) pre-placed exo-stones.

    They occupy the non-corner positions of the hex ring at radius n. Each of
    the 6 sides (corner-to-corner run of n-1 positions) is half black then half
    white in a consistent rotational direction, so the 12 strings alternate
    B, W, B, W, ... around the perimeter and the ring corners stay empty.
    Treat the returned dict as immutable.
    """
    half = (n - 1) // 2
    out = {}
    for i in range(6):
        cq, cr = _CORNER_UNITS[i][0] * n, _CORNER_UNITS[i][1] * n
        nq, nr = _CORNER_UNITS[(i + 1) % 6][0] * n, _CORNER_UNITS[(i + 1) % 6][1] * n
        dq, dr = (nq - cq) // n, (nr - cr) // n
        for k in range(1, n):  # k = 0 and k = n are the (empty) ring corners
            out[(cq + dq * k, cr + dr * k)] = BLACK if k <= half else WHITE
    return out


@lru_cache(maxsize=None)
def _ring_corners(n: int) -> frozenset:
    return frozenset((u * n, v * n) for (u, v) in _CORNER_UNITS)


def _cell(t: str) -> tuple[int, int]:
    q, r = t.split(",")
    return int(q), int(r)


def _groups(board: dict, player: int, n: int) -> list[set]:
    """Connected components of ``player``'s stones (interior placements plus
    the player's exo-stones) under plain hex adjacency."""
    exo = _exo(n)
    owned = {c for c, p in board.items() if p == player}
    owned |= {c for c, p in exo.items() if p == player}
    out, seen = [], set()
    for cell in owned:
        if cell in seen:
            continue
        comp, stack = {cell}, [cell]
        seen.add(cell)
        while stack:
            cq, cr = stack.pop()
            for dq, dr in _DIRS:
                nb = (cq + dq, cr + dr)
                if nb in owned and nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    stack.append(nb)
        out.append(comp)
    return out


def _score_list(board: dict, player: int, n: int) -> list[int]:
    """The player's group scores (exo-stones contained), sorted descending.
    Groups containing no exo-stone score 0 and are dropped (a 0 compares the
    same as a missing entry)."""
    exo = _exo(n)
    scores = [sum(1 for c in g if c in exo) for g in _groups(board, player, n)]
    return sorted((x for x in scores if x > 0), reverse=True)


def _compare(a: list[int], b: list[int]) -> int:
    """Recursive-tiebreak comparison: best group, then next-best, etc.
    (equivalently: set tied groups aside and compare the remainder). Missing
    entries count 0. Returns +1 if a wins, -1 if b wins, 0 on a full tie."""
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x != y:
            return 1 if x > y else -1
    return 0


@dataclass
class ExoHexState:
    n: int = 7
    board: dict = field(default_factory=dict)   # (q, r) -> 0/1 (interior only)
    to_move: int = BLACK
    passes: int = 0                             # consecutive passes
    ply: int = 0
    last: Optional[tuple] = None
    winner: Optional[int] = None
    over: bool = False
    pie: bool = True


class ExoHex(Game):
    name = "Exo-Hex"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ExoHexState:
        opts = options or {}
        n = int(str(opts.get("size", 7)))
        if n < 3 or n % 2 == 0:
            raise ValueError("Exo-Hex needs an odd hexhex side >= 3")
        pie = str(opts.get("pie", True)).lower() != "false"
        return ExoHexState(n=n, pie=pie)

    def current_player(self, s: ExoHexState) -> int:
        return s.to_move

    def legal_moves(self, s: ExoHexState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = [f"{q},{r}" for (q, r) in _cells(s.n) if (q, r) not in s.board]
        if s.pie and s.ply == 1 and len(s.board) == 1:
            moves.append("swap")
        moves.append("pass")
        return moves

    def apply_move(self, s: ExoHexState, move: str, rng=None) -> ExoHexState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move

        if move == "swap":
            if not (s.pie and s.ply == 1 and len(s.board) == 1):
                raise ValueError("swap not available")
            (cell, _), = list(s.board.items())
            return ExoHexState(
                n=s.n, board={cell: mover}, to_move=1 - mover, passes=0,
                ply=s.ply + 1, last=cell, pie=s.pie,
            )

        if move == "pass":
            ns = ExoHexState(
                n=s.n, board=dict(s.board), to_move=1 - mover,
                passes=s.passes + 1, ply=s.ply + 1, last=None, pie=s.pie,
            )
            self._maybe_finish(ns, force=(ns.passes >= 2))
            return ns

        cell = _cell(move)
        if cell not in _cell_set(s.n) or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        board[cell] = mover
        ns = ExoHexState(
            n=s.n, board=board, to_move=1 - mover, passes=0,
            ply=s.ply + 1, last=cell, pie=s.pie,
        )
        # Hard safety net: a full board also ends the game.
        self._maybe_finish(ns, force=(len(board) >= len(_cells(s.n))))
        return ns

    def _maybe_finish(self, ns: ExoHexState, force: bool = False):
        if not force:
            return
        cmp = _compare(_score_list(ns.board, BLACK, ns.n),
                       _score_list(ns.board, WHITE, ns.n))
        # Recursive tiebreak. The designer states a full-board tie is
        # impossible (full-board fuzzing agrees), but early double-passes in
        # symmetric positions CAN tie all the way down; a genuine total tie is
        # a draw (winner None) — documented in rules.md.
        ns.winner = BLACK if cmp > 0 else (WHITE if cmp < 0 else None)
        ns.over = True

    def is_terminal(self, s: ExoHexState) -> bool:
        return s.over

    def returns(self, s: ExoHexState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: ExoHexState) -> list[float]:
        """Rollout-cutoff eval: depth-weighted difference of the two players'
        descending group-score lists, squashed to (-1, 1). Positive = Black."""
        a = _score_list(s.board, BLACK, s.n)
        b = _score_list(s.board, WHITE, s.n)
        diff = 0.0
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else 0
            y = b[i] if i < len(b) else 0
            diff += (x - y) * (0.5 ** i)
        v = math.tanh(diff / 4.0)
        return [v, -v]

    def serialize(self, s: ExoHexState) -> dict:
        return {
            "n": s.n,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "passes": s.passes,
            "ply": s.ply,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "winner": s.winner,
            "over": s.over,
            "pie": s.pie,
        }

    def deserialize(self, d: dict) -> ExoHexState:
        last = d.get("last")
        return ExoHexState(
            n=d.get("n", 7),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            passes=d.get("passes", 0),
            ply=d.get("ply", len(d["board"])),
            last=(_cell(last) if last else None),
            winner=d.get("winner"),
            over=d.get("over", False),
            pie=d.get("pie", True),
        )

    def describe_move(self, s: ExoHexState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        return move

    def render(self, s: ExoHexState, perspective=None) -> dict:
        n = s.n
        rad = 0.58
        exo = _exo(n)

        def hexpts(q, r):
            cx = math.sqrt(3) * (q + r / 2.0)
            cy = 1.5 * r
            return [[round(cx + rad * math.cos(math.radians(60 * k + 30)), 3),
                     round(cy + rad * math.sin(math.radians(60 * k + 30)), 3)]
                    for k in range(6)]

        cells = []
        tints = {}
        for (q, r) in _cells(n):                 # playable interior
            cells.append({"id": f"{q},{r}", "points": hexpts(q, r)})
        for (q, r) in sorted(exo):               # exo positions (never playable)
            cid = f"x:{q},{r}"
            cells.append({"id": cid, "points": hexpts(q, r)})
            tints[cid] = "#6b6350"               # dim warm: exterior row
        # The 6 ring-corner gaps are deliberately NOT rendered: the missing hex
        # shows the break in the perimeter.

        pieces = [
            {"cell": f"{q},{r}", "owner": p, "label": ""}
            for (q, r), p in s.board.items()
        ] + [
            {"cell": f"x:{q},{r}", "owner": p, "label": ""}
            for (q, r), p in sorted(exo.items())
        ]

        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})

        names = {BLACK: "Black", WHITE: "White"}
        bl = _score_list(s.board, BLACK, n)
        wh = _score_list(s.board, WHITE, n)

        def top(xs):
            return xs[0] if xs else 0

        if s.over:
            result = "Draw" if s.winner is None else f"{names[s.winner]} wins"
            caption = (f"{result} — best group: "
                       f"Black {top(bl)}, White {top(wh)}")
        else:
            caption = (f"{names[s.to_move]} to move — best group: "
                       f"Black {top(bl)}, White {top(wh)}")

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
