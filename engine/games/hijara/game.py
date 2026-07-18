"""Hijara — Martin H. Samuel's 3-D alignment-scoring game on a 2-D board.

First printed as "Excel" in American Airlines' American Way magazine (1985),
sold commercially as "Eclipse" (1994) and as "Hijara" (Great American Trading
Company 1995; Games Above Board / Sterling Games 2003, 2006). Reviewed by
Kerry Handscomb in Abstract Games magazine issue 5 (2001).

BOARD. A 4x4 array of LARGE squares, each divided into four small squares
numbered 1-4. Per the physical board (Wikipedia "Hijara layout" photo) the
numbers run clockwise from the bottom-left in every large square:
1 = bottom-left, 2 = top-left, 3 = top-right, 4 = bottom-right.

PLAY. Two players (seat 0 "Sun", seat 1 "Moon"; 32 stones each) alternate
placing one stone on any large square that still has an empty small square.
The single rule: within each large square the small squares must be filled in
numerical order 1 -> 2 -> 3 -> 4, so the small square filled is always the
lowest-numbered open one (<= 16 legal placements at any time). The game ends
when all 64 small squares are filled; the higher score wins, equal scores are
an honest draw.

SCORING (awarded as soon as a formation is completed; stones never move, so
formations persist and a final-board rescore gives identical totals):
  * 10 pts - a line of 4 large squares (4 rows + 4 columns + 2 main diagonals
    of the 4x4 array) in which one player's stones occupy the SAME number in
    all four large squares.
  * 15 pts - such a line in which the player's stones occupy the numbers
    1,2,3,4 IN ORDER along the line — in EITHER direction (1-2-3-4 read one
    way = 4-3-2-1 read the other; both count, and the ascending and
    descending patterns on one line are disjoint cell sets, so both can in
    principle score).
  * 20 pts - all four small squares of one large square occupied by one
    player.
  * OPTIONAL rule (manifest option "corners", off by default — BGG's
    designer-sourced description lists these as "two additional optional ways
    to score"): the 4 corner large squares acting as a line — same number in
    all four corners = 10 pts; the numbers 1,2,3,4 one in each corner (any
    arrangement) = 15 pts.
One placement can complete several formations at once; all of them score.

EQUIVALENCE (Handscomb, AG#5): the base game is exactly 4x4x4 Qubic with
gravity plus scoring. Map small square (X, Y, number n) to 3-D cell
(X, Y, z = n-1): the fill-order rule is gravity, and the 76 base formations
are exactly Qubic's 76 lines — 40 horizontal lines (10 pts), 20 z-varying
face/space diagonals (15 pts), 16 pillars (20 pts). The selftest asserts this
correspondence formation-by-formation.

MOVES. A move is the small-square cell id "c,r" on the 8x8 grid (c = 2X+dx,
r = 2Y+dy, row 0 at the bottom). Only the forced (lowest open) small square
of each non-full large square is legal — click it directly in the UI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import permutations
from typing import List, Optional

from agp.game import Game

SIZE = 4
NAMES = ("Sun", "Moon")

# Small-square position (dx, dy) within a large square, dy = 1 is the TOP row
# on screen (the renderer draws row 0 at the bottom). Matches the physical
# board: 1 bottom-left, 2 top-left, 3 top-right, 4 bottom-right.
NUM_POS = {1: (0, 0), 2: (0, 1), 3: (1, 1), 4: (1, 0)}
POS_NUM = {v: k for k, v in NUM_POS.items()}

CORNERS = ((0, 0), (3, 0), (0, 3), (3, 3))


def _cell_id(x: int, y: int, n: int) -> str:
    dx, dy = NUM_POS[n]
    return f"{2 * x + dx},{2 * y + dy}"


def _parse_cell(move: str):
    """Cell id "c,r" -> (X, Y, n) or None if malformed/off-board."""
    try:
        c, r = (int(v) for v in move.split(","))
    except ValueError:
        return None
    if not (0 <= c < 8 and 0 <= r < 8):
        return None
    x, y = c // 2, r // 2
    n = POS_NUM[(c % 2, r % 2)]
    return x, y, n


@lru_cache(maxsize=None)
def _lines() -> tuple:
    """The 10 lines of large squares, each an ORDERED 4-tuple of (X, Y)."""
    out = []
    for y in range(SIZE):
        out.append(tuple((x, y) for x in range(SIZE)))
    for x in range(SIZE):
        out.append(tuple((x, y) for y in range(SIZE)))
    out.append(tuple((i, i) for i in range(SIZE)))
    out.append(tuple((i, SIZE - 1 - i) for i in range(SIZE)))
    return tuple(out)


@lru_cache(maxsize=None)
def _formations(corners: bool) -> tuple:
    """All scoring formations as (frozenset of (X, Y, n) cells, points)."""
    forms = []
    for line in _lines():
        for k in range(1, 5):                       # 10 pts: same number
            forms.append((frozenset((x, y, k) for (x, y) in line), 10))
        # 15 pts: 1-2-3-4 in order, both traversal directions (disjoint sets)
        forms.append((frozenset((line[i][0], line[i][1], i + 1) for i in range(4)), 15))
        forms.append((frozenset((line[i][0], line[i][1], 4 - i) for i in range(4)), 15))
    for x in range(SIZE):                           # 20 pts: a full square
        for y in range(SIZE):
            forms.append((frozenset((x, y, n) for n in range(1, 5)), 20))
    if corners:
        for k in range(1, 5):                       # optional: corners, same number
            forms.append((frozenset((x, y, k) for (x, y) in CORNERS), 10))
        # optional: 1,2,3,4 one per corner, any arrangement (documented
        # interpretation — the corners have no canonical reading order)
        for perm in permutations((1, 2, 3, 4)):
            forms.append((frozenset((CORNERS[i][0], CORNERS[i][1], perm[i])
                                    for i in range(4)), 15))
    return tuple(forms)


@lru_cache(maxsize=None)
def _forms_through(corners: bool) -> dict:
    """(X, Y, n) -> tuple of formations (cells, points) containing that cell."""
    out: dict = {}
    for cells, pts in _formations(corners):
        for c in cells:
            out.setdefault(c, []).append((cells, pts))
    return {c: tuple(v) for c, v in out.items()}


@dataclass
class HijaraState:
    # squares[Y*4+X] = owners of that large square's stones in fill order
    # (index j = number j+1)
    squares: List[List[int]] = field(default_factory=lambda: [[] for _ in range(16)])
    scores: List[int] = field(default_factory=lambda: [0, 0])
    to_move: int = 0
    last: Optional[str] = None      # last-placed cell id
    corners: bool = False


def _owner(squares, x: int, y: int, n: int) -> Optional[int]:
    col = squares[y * SIZE + x]
    return col[n - 1] if len(col) >= n else None


def _points_after(squares, x: int, y: int, n: int, player: int, corners: bool) -> int:
    """Points the stone just placed at (x, y, n) by ``player`` scores
    (``squares`` already contains it)."""
    pts = 0
    for cells, value in _forms_through(corners).get((x, y, n), ()):
        if all(_owner(squares, cx, cy, cn) == player for (cx, cy, cn) in cells):
            pts += value
    return pts


class Hijara(Game):
    name = "Hijara"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HijaraState:
        opts = options or {}
        corners = opts.get("corners", False)
        if isinstance(corners, str):
            corners = corners.lower() == "true"
        return HijaraState(corners=bool(corners))

    def current_player(self, s: HijaraState) -> int:
        return s.to_move

    def legal_moves(self, s: HijaraState):
        moves = []
        for idx, col in enumerate(s.squares):
            if len(col) < 4:
                x, y = idx % SIZE, idx // SIZE
                moves.append(_cell_id(x, y, len(col) + 1))
        return moves

    def apply_move(self, s: HijaraState, move: str, rng=None) -> HijaraState:
        parsed = _parse_cell(move)
        if parsed is None:
            raise ValueError(f"malformed move {move!r}")
        x, y, n = parsed
        col = s.squares[y * SIZE + x]
        if len(col) >= 4 or n != len(col) + 1:
            raise ValueError(
                f"illegal move {move!r}: square ({x},{y}) must fill number "
                f"{len(col) + 1} next"
            )
        mover = s.to_move
        squares = [list(c) for c in s.squares]
        squares[y * SIZE + x].append(mover)
        scores = list(s.scores)
        scores[mover] += _points_after(squares, x, y, n, mover, s.corners)
        return HijaraState(
            squares=squares,
            scores=scores,
            to_move=1 - mover,
            last=move,
            corners=s.corners,
        )

    def is_terminal(self, s: HijaraState) -> bool:
        return all(len(col) == 4 for col in s.squares)

    def returns(self, s: HijaraState):
        a, b = s.scores
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]           # genuine tie: honest draw

    def heuristic(self, s: HijaraState):
        v = math.tanh((s.scores[0] - s.scores[1]) / 25.0)
        return [v, -v]

    def serialize(self, s: HijaraState) -> dict:
        return {
            "squares": [list(c) for c in s.squares],
            "scores": list(s.scores),
            "to_move": s.to_move,
            "last": s.last,
            "corners": s.corners,
        }

    def deserialize(self, d: dict) -> HijaraState:
        return HijaraState(
            squares=[list(c) for c in d["squares"]],
            scores=list(d["scores"]),
            to_move=d["to_move"],
            last=d.get("last"),
            corners=bool(d.get("corners", False)),
        )

    def describe_move(self, s: HijaraState, move: str) -> str:
        parsed = _parse_cell(move)
        if parsed is None:
            return move
        x, y, n = parsed
        label = f"{NAMES[s.to_move]} {'abcd'[x]}{y + 1} slot {n}"
        col = s.squares[y * SIZE + x]
        if len(col) < 4 and n == len(col) + 1:
            squares = [list(c) for c in s.squares]
            squares[y * SIZE + x].append(s.to_move)
            pts = _points_after(squares, x, y, n, s.to_move, s.corners)
            if pts:
                label += f" +{pts}"
        return label

    # ---- presentation ------------------------------------------------------
    def render(self, s: HijaraState, perspective=None) -> dict:
        # Large squares distinguished by a 2x2 checker of subtle tints.
        tints = {}
        for x in range(SIZE):
            for y in range(SIZE):
                shade = "#332e27" if (x + y) % 2 == 0 else "#27292f"
                for n in range(1, 5):
                    tints[_cell_id(x, y, n)] = shade

        pieces = []
        for x in range(SIZE):
            for y in range(SIZE):
                col = s.squares[y * SIZE + x]
                for n in range(1, 5):
                    cid = _cell_id(x, y, n)
                    if len(col) >= n:
                        pieces.append({"cell": cid, "owner": col[n - 1]})
                    else:
                        # ownerless label -> faint grey number on the empty
                        # small square (the printed board numbering)
                        pieces.append({"cell": cid, "label": str(n)})

        highlights = []
        if s.last:
            highlights.append({"cell": s.last, "kind": "last-move"})

        a, b = s.scores
        tally = f"Sun {a} · Moon {b}"
        if self.is_terminal(s):
            if a == b:
                caption = f"Draw — {tally}"
            else:
                caption = f"{NAMES[0 if a > b else 1]} wins — {tally}"
        else:
            caption = f"{tally} — {NAMES[s.to_move]} to move"

        return {
            "board": {"type": "square", "width": 8, "height": 8, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
