"""Star, by Craige Schensted (later Ea Ea) and Ea Ea, first published 1983.

A two-player connection / scoring game on an irregular hexagon of hexagonal
cells. The signature of Star is the SCORING: it is played on a board whose six
sides ALTERNATE in length (so the perimeter is odd, making draws impossible),
and the cells around the OUTSIDE of the playing area are "partial hexagons"
(half/edge hexes drawn hugging the border) that are NOT playable -- they exist
only for scoring.

GEOMETRY.  The board is a hexagon-of-hexes whose six sides alternate between
length A and length B (A=5, B=6 by default -> 106 playable cells). Around the
outer ring sit the "border cells" (partial hexagons), one per exposed outer
face. By the geometry:

  * each of the 6 CORNER playing cells touches exactly 3 border cells,
  * each non-corner EDGE playing cell touches exactly 2 border cells,
  * every INTERIOR cell touches 0.

The default board has 39 border cells (odd -> drawless).

PLAY.  Black and White alternately place one stone of their colour on any empty
PLAYING cell (border cells are never playable). Stones never move and are never
captured. A player may PASS. The game ends when both players pass in succession
(hard safety net: when the board's playing cells are all full).

SCORING (the whole game).  Like-coloured connected stones form a group. A group
that touches at least THREE distinct border cells is a "STAR"; it scores

        (number of distinct border cells the group touches)  -  2.

A group touching fewer than three border cells scores 0. A lone stone on a
corner therefore touches 3 border cells and scores 3 - 2 = 1; a lone stone on
an edge touches 2 and scores 0. A player's total is the sum over their stars.
The combined two-player score is bounded by (#border cells) - 2 per the
constant-sum structure Schensted designed. Highest total wins.

A border cell is shared: if groups of BOTH colours are adjacent to the same
border cell, it counts toward each of their touch-counts independently (this is
the published rule -- the partial hex is "split" between them).

Coordinates are axial (q, r); the third cube coordinate is s = -q - r. The
board is the set of cells satisfying  -B <= q,r,s <= A  (with A,B the two side
parameters). Border cells use the same axial coords but lie just OFF the board.

Source: https://en.wikipedia.org/wiki/Star_(board_game)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # player 0 places first

_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


def _s(q: int, r: int) -> int:
    return -q - r


@lru_cache(maxsize=None)
def _cells(a: int, b: int) -> tuple:
    """All playing cells of the alternating-side hexagon: -b <= q,r,s <= a."""
    out = []
    lo, hi = -b, a
    for q in range(lo, hi + 1):
        for r in range(lo, hi + 1):
            if lo <= _s(q, r) <= hi:
                out.append((q, r))
    return tuple(sorted(out))


@lru_cache(maxsize=None)
def _cell_set(a: int, b: int) -> frozenset:
    return frozenset(_cells(a, b))


@lru_cache(maxsize=None)
def _borders(a: int, b: int) -> frozenset:
    """The off-board 'partial hexagon' border cells: off-board cells that are a
    hex-neighbour of at least one playing cell."""
    on = _cell_set(a, b)
    out = set()
    for (q, r) in on:
        for dq, dr in _DIRS:
            nb = (q + dq, r + dr)
            if nb not in on:
                out.add(nb)
    return frozenset(out)


@lru_cache(maxsize=None)
def _border_touch(a: int, b: int) -> dict:
    """playing cell -> frozenset of border cells it is adjacent to (0, 2, or 3)."""
    on = _cell_set(a, b)
    borders = _borders(a, b)
    out = {}
    for (q, r) in on:
        ts = frozenset(
            (q + dq, r + dr) for dq, dr in _DIRS if (q + dq, r + dr) in borders
        )
        out[(q, r)] = ts
    return out


@lru_cache(maxsize=None)
def _corners(a: int, b: int) -> frozenset:
    """Playing cells touching exactly 3 border cells (the 6 corners)."""
    bt = _border_touch(a, b)
    return frozenset(c for c, ts in bt.items() if len(ts) == 3)


def _cell(t: str) -> tuple[int, int]:
    q, r = t.split(",")
    return int(q), int(r)


@dataclass
class StarState:
    a: int = 5
    b: int = 6
    board: dict = field(default_factory=dict)   # (q, r) -> 0/1
    to_move: int = BLACK
    passes: int = 0                             # consecutive passes
    ply: int = 0
    last: Optional[tuple] = None
    winner: Optional[int] = None
    over: bool = False
    pie: bool = True


def _groups(board: dict, player: int) -> list[set]:
    """All connected components of ``player``'s stones."""
    out, seen = [], set()
    for cell, p in board.items():
        if p != player or cell in seen:
            continue
        comp, stack = {cell}, [cell]
        seen.add(cell)
        while stack:
            cq, cr = stack.pop()
            for dq, dr in _DIRS:
                nb = (cq + dq, cr + dr)
                if nb not in seen and board.get(nb) == player:
                    seen.add(nb)
                    comp.add(nb)
                    stack.append(nb)
        out.append(comp)
    return out


def _score(board: dict, player: int, a: int, b: int) -> int:
    """Sum over the player's stars of (border cells touched - 2); a group must
    touch >= 3 distinct border cells to count as a star (else 0)."""
    bt = _border_touch(a, b)
    total = 0
    for g in _groups(board, player):
        touched = set()
        for c in g:
            touched |= bt[c]
        n = len(touched)
        if n >= 3:
            total += n - 2
    return total


class Star(Game):
    uid = "star"
    name = "Star"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> StarState:
        opts = options or {}
        size = str(opts.get("size", "5x6"))
        a, b = (int(x) for x in size.split("x"))
        pie = bool(opts.get("pie", True))
        return StarState(a=a, b=b, pie=pie)

    def current_player(self, s: StarState) -> int:
        return s.to_move

    def legal_moves(self, s: StarState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = [f"{q},{r}" for (q, r) in _cells(s.a, s.b) if (q, r) not in s.board]
        if s.pie and s.ply == 1:  # second player's first turn
            moves.append("swap")
        moves.append("pass")
        return moves

    def apply_move(self, s: StarState, move: str, rng=None) -> StarState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move

        if move == "swap":
            if not (s.pie and s.ply == 1):
                raise ValueError("swap not available")
            (cell, _), = list(s.board.items())
            return StarState(
                a=s.a, b=s.b, board={cell: mover}, to_move=1 - mover, passes=0,
                ply=s.ply + 1, last=cell, pie=s.pie,
            )

        if move == "pass":
            ns = StarState(
                a=s.a, b=s.b, board=dict(s.board), to_move=1 - mover,
                passes=s.passes + 1, ply=s.ply + 1, last=None, pie=s.pie,
            )
            self._maybe_finish(ns, force=(ns.passes >= 2))
            return ns

        cell = _cell(move)
        if cell not in _cell_set(s.a, s.b) or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        board[cell] = mover
        ns = StarState(
            a=s.a, b=s.b, board=board, to_move=1 - mover, passes=0,
            ply=s.ply + 1, last=cell, pie=s.pie,
        )
        # Hard safety net: a full playing board also ends the game.
        self._maybe_finish(ns, force=(len(board) >= len(_cells(s.a, s.b))))
        return ns

    def _maybe_finish(self, ns: StarState, force: bool = False):
        if not force:
            return
        bl = _score(ns.board, BLACK, ns.a, ns.b)
        wh = _score(ns.board, WHITE, ns.a, ns.b)
        # Highest score wins. Drawless by design (odd border count); a tie (only
        # possible on a near-empty board / pathological pass-out) goes to the
        # player who placed the second stone (WHITE).
        ns.winner = BLACK if bl > wh else WHITE
        ns.over = True

    def is_terminal(self, s: StarState) -> bool:
        return s.over

    def returns(self, s: StarState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: StarState) -> dict:
        return {
            "a": s.a, "b": s.b,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "passes": s.passes,
            "ply": s.ply,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "winner": s.winner,
            "over": s.over,
            "pie": s.pie,
        }

    def deserialize(self, d: dict) -> StarState:
        last = d.get("last")
        return StarState(
            a=d.get("a", 5), b=d.get("b", 6),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            passes=d.get("passes", 0),
            ply=d.get("ply", len(d["board"])),
            last=(_cell(last) if last else None),
            winner=d.get("winner"),
            over=d.get("over", False),
            pie=d.get("pie", True),
        )

    def describe_move(self, s: StarState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if move == "pass":
            return "pass"
        cell = _cell(move)
        if cell in _corners(s.a, s.b):
            return f"{move}*"  # corner cell
        return move

    def render(self, s: StarState, perspective=None) -> dict:
        a, b = s.a, s.b
        rad = 0.58
        corners = _corners(a, b)
        borders = _borders(a, b)

        def hexpts(q, r):
            cx = math.sqrt(3) * (q + r / 2.0)
            cy = 1.5 * r
            return [[round(cx + rad * math.cos(math.radians(60 * k + 30)), 3),
                     round(cy + rad * math.sin(math.radians(60 * k + 30)), 3)]
                    for k in range(6)]

        cells = []
        tints = {}
        # playing cells
        for (q, r) in _cells(a, b):
            cid = f"{q},{r}"
            cells.append({"id": cid, "points": hexpts(q, r)})
            if (q, r) in corners:
                tints[cid] = "#8a5a2a"   # corner edge cell (warm)
            elif len(_border_touch(a, b)[(q, r)]) == 2:
                tints[cid] = "#5a4a2a"   # non-corner edge cell (dim warm)
        # off-board partial-hex border (scoring) cells -- not playable
        for (q, r) in borders:
            cid = f"b:{q},{r}"
            cells.append({"id": cid, "points": hexpts(q, r)})
            tints[cid] = "#caa75a"       # gold partial-hex border

        pieces = [
            {"cell": f"{q},{r}", "owner": p, "label": ""}
            for (q, r), p in s.board.items()
        ]

        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})

        names = {BLACK: "Black", WHITE: "White"}
        bl = _score(s.board, BLACK, a, b)
        wh = _score(s.board, WHITE, a, b)
        if s.over:
            caption = f"{names[s.winner]} wins — Black {bl}, White {wh}"
        else:
            caption = f"{names[s.to_move]} to move — Black {bl}, White {wh}"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
