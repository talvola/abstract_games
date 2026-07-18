"""Onyx — Larry Back's connection game with a capture rule (1995).

Source of truth: Larry Back, "Onyx: An Original Connection Game", Abstract
Games magazine #4 (Winter 2000), which includes "The Official Rules of Onyx"
(the rules list itself is printed in AG#5, Spring 2001). Cross-checked against
Wikipedia "Onyx (game)" and BGG 11375.

BOARD.  A 12x12 grid of points (columns a..l, rows 1..12) in Back's "zig-zag
coordinate system": alternate points are displaced so the lattice forms
interlocking squares and triangles (combinatorially the snub square tiling).
Between the 144 grid points lie 11x11 = 121 unit cells:

  * cells whose 0-based (col + row) sum is ODD are SQUARES (60 of them, in a
    checkerboard pattern).  Each is subdivided by both diagonals, creating a
    playable MIDPOINT joined to exactly its 4 corner points.
  * the other 61 cells are split by ONE (short) diagonal into two triangles:
    the "/" diagonal (low-left to high-right corner) when the cell's 0-based
    column is even, the "\\" diagonal otherwise.  (Derived from Diagram 9 of
    the AG#4 article and confirmed by the article's Diagram-12 notation, whose
    White chain uses the a5-b6 edge = the "/" diagonal of cell a5/b6.)

Total 204 points and 565 line segments; adjacency = joined by a segment.

MOVES.  Players alternate placing one stone of their colour on any empty
point — EXCEPT that a midpoint may only be taken while ALL FOUR corner points
of its square are empty (official rule, Diagram 8).

CAPTURE (Diagrams 10/11).  If a placement on a CORNER point of a square
results in both players occupying two diagonally-opposite corner pairs of
that square while the square's midpoint is unoccupied, the two enemy stones
on that square are captured and removed.  One placement can do this on two
squares at once (double capture — all four enemy stones come off).  Captures
are automatic and mandatory; midpoint placements never capture.

GOAL.  Black (player 0) connects the TOP and BOTTOM board edges (rows 12/1)
with an unbroken chain of black stones; White (player 1) connects LEFT and
RIGHT (columns a/l).  The four corner points belong to both adjacent edges.
Midpoint stones link chains like any other stone.

SETUP.  Official (default): Black on a6,a7,l6,l7 and White on f1,g1,f12,g12
— the two outside corners of the middle square on each side (Diagram 9).
The article notes the game can also start empty: option ``setup = empty``.

PIE.  Black places the first stone, then the second player may "swap"
(choose Black).  Goals are transposed (rows vs columns), so the platform
swap TRANSPOSES every stone (c,r) -> (r,c) — an automorphism of the board
that maps squares to squares and each goal onto the other — and recolours
it, exactly as in Crossway/Cation.  The official setup is itself symmetric
under transpose + recolour, so only the opening stone visibly moves.

TERMINATION.  Back argues repetition needs both players' conspiracy, so the
official rules have no repetition clause.  For engine-guaranteed
termination: if the mover has no legal placement the game is a DRAW, and a
hard cap of 600 plies is also an honest draw.

Move strings: point ids ("f6"), midpoint ids ("d9m" = midpoint of the square
whose lower-left corner is d9), and "swap".  ``describe_move`` emits Back's
official notation ("F6", "DE910", trailing "*" per captured pair).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black connects top<->bottom, White connects left<->right
N = 12
LETTERS = "abcdefghijkl"
PLY_CAP = 600
# Zig-zag displacement. With e = 1 - sqrt(3)/2 every edge of the lattice has
# equal length and the board is the exact snub square tiling (squares tilted
# ~15 degrees, equilateral triangles) — visually matching Back's Diagram 9.
E_OFF = 1.0 - math.sqrt(3) / 2.0


def _pt(c: int, r: int) -> str:
    return f"{LETTERS[c]}{r + 1}"


def _pt_cr(pid: str) -> tuple[int, int]:
    return LETTERS.index(pid[0]), int(pid[1:]) - 1


# ---------------------------------------------------------------------------
# Board construction (module-level, immutable).
# ---------------------------------------------------------------------------

_XY: dict[str, tuple[float, float]] = {}     # id -> render coords (y down)
_ADJ: dict[str, frozenset] = {}
_SQUARES: list[tuple[tuple, str]] = []       # (corners cyclic 4-tuple, mid id)
_PT_SQUARES: dict[str, tuple] = {}           # corner point -> square indices
_MID_CORNERS: dict[str, tuple] = {}          # mid id -> its 4 corners
_TRANSPOSE: dict[str, str] = {}              # the (c,r)->(r,c) automorphism


def _build() -> None:
    adj: dict[str, set] = {}

    def link(a: str, b: str) -> None:
        adj[a].add(b)
        adj[b].add(a)

    for c in range(N):
        for r in range(N):
            p = _pt(c, r)
            _XY[p] = (c + E_OFF * (1 if r % 2 == 0 else -1),
                      (N - 1 - r) + E_OFF * (-1 if c % 2 == 0 else 1))
            adj[p] = set()
            _TRANSPOSE[p] = _pt(r, c)
    for c in range(N):
        for r in range(N):
            if c + 1 < N:
                link(_pt(c, r), _pt(c + 1, r))
            if r + 1 < N:
                link(_pt(c, r), _pt(c, r + 1))
    for c0 in range(N - 1):
        for r0 in range(N - 1):
            if (c0 + r0) % 2 == 1:
                # subdivided square: both diagonals meet at a new midpoint
                corners = (_pt(c0, r0), _pt(c0 + 1, r0),
                           _pt(c0 + 1, r0 + 1), _pt(c0, r0 + 1))
                mid = f"{LETTERS[c0]}{r0 + 1}m"
                _XY[mid] = (c0 + 0.5, (N - 1 - r0) - 0.5)
                adj[mid] = set()
                for cn in corners:
                    link(mid, cn)
                _SQUARES.append((corners, mid))
                _MID_CORNERS[mid] = corners
                _TRANSPOSE[mid] = f"{LETTERS[r0]}{c0 + 1}m"
            else:
                # triangle pair: one (short) diagonal
                if c0 % 2 == 0:
                    link(_pt(c0, r0), _pt(c0 + 1, r0 + 1))
                else:
                    link(_pt(c0 + 1, r0), _pt(c0, r0 + 1))
    for i, (corners, _mid) in enumerate(_SQUARES):
        for cn in corners:
            _PT_SQUARES.setdefault(cn, []).append(i)
    for k in list(_PT_SQUARES):
        _PT_SQUARES[k] = tuple(_PT_SQUARES[k])
    for k, v in adj.items():
        _ADJ[k] = frozenset(v)


_build()

_ORDER = tuple([_pt(c, r) for r in range(N) for c in range(N)]
               + sorted(_MID_CORNERS))
_TOP = frozenset(_pt(c, N - 1) for c in range(N))
_BOTTOM = frozenset(_pt(c, 0) for c in range(N))
_LEFT = frozenset(_pt(0, r) for r in range(N))
_RIGHT = frozenset(_pt(N - 1, r) for r in range(N))

# Official setup (AG#4 Diagram 9): each colour on the two outside corners of
# the middle square along both of the OPPONENT's sides.
_OFFICIAL = {"a6": BLACK, "a7": BLACK, "l6": BLACK, "l7": BLACK,
             "f1": WHITE, "g1": WHITE, "f12": WHITE, "g12": WHITE}


def _placements(stones: dict) -> list[str]:
    out = []
    for p in _ORDER:
        if p in stones:
            continue
        cs = _MID_CORNERS.get(p)
        if cs is not None and any(c in stones for c in cs):
            continue  # midpoint of a square with an occupied corner
        out.append(p)
    return out


def _captures(stones: dict, move: str, mover: int) -> set:
    """Enemy stones captured by `mover` having just placed on `move`
    (stones already includes the placed stone)."""
    caps: set = set()
    for si in _PT_SQUARES.get(move, ()):
        corners, mid = _SQUARES[si]
        if mid in stones:
            continue
        v = [stones.get(x) for x in corners]
        if None in v:
            continue
        if v[0] == v[2] and v[1] == v[3] and v[0] != v[1]:
            opp = 1 - mover
            caps.update(x for x, o in zip(corners, v) if o == opp)
    return caps


def _connects(stones: dict, player: int) -> tuple:
    """A winning chain of `player` stones linking their two edges, or ()."""
    srcs, tgts = ((_TOP, _BOTTOM) if player == BLACK else (_LEFT, _RIGHT))
    start = [p for p in srcs if stones.get(p) == player]
    goal = {p for p in tgts if stones.get(p) == player}
    if not start or not goal:
        return ()
    parent: dict[str, Optional[str]] = {p: None for p in start}
    dq = deque(start)
    end = None
    while dq:
        cur = dq.popleft()
        if cur in goal:
            end = cur
            break
        for nb in _ADJ[cur]:
            if nb not in parent and stones.get(nb) == player:
                parent[nb] = cur
                dq.append(nb)
    if end is None:
        return ()
    path = []
    node: Optional[str] = end
    while node is not None:
        path.append(node)
        node = parent[node]
    return tuple(reversed(path))


# ---------------------------------------------------------------------------
# Static render geometry.
# ---------------------------------------------------------------------------

def _octagon(x: float, y: float, rr: float) -> list:
    pts = []
    for k in range(8):
        a = math.radians(22.5 + 45.0 * k)
        pts.append([round(x + rr * math.cos(a), 3), round(y + rr * math.sin(a), 3)])
    return pts


_CELLS_STATIC = tuple(
    {"id": p, "points": _octagon(*_XY[p], 0.26 if p in _MID_CORNERS else 0.34)}
    for p in _ORDER
)
_SEAT0_COL, _SEAT1_COL = "#d23b3b", "#3b6fd2"  # web/src/colors.js seat fills


def _static_lines() -> tuple:
    segs = []
    seen = set()
    for a in _ORDER:
        xa, ya = _XY[a]
        for b in _ADJ[a]:
            if (b, a) in seen:
                continue
            seen.add((a, b))
            xb, yb = _XY[b]
            segs.append([[round(xa, 3), round(ya, 3)], [round(xb, 3), round(yb, 3)]])
    lo, hi = -0.75, 11.85
    segs.append([[lo, lo], [hi, lo], _SEAT0_COL])   # top edge    (Black)
    segs.append([[lo, hi], [hi, hi], _SEAT0_COL])   # bottom edge (Black)
    segs.append([[lo, lo], [lo, hi], _SEAT1_COL])   # left edge   (White)
    segs.append([[hi, lo], [hi, hi], _SEAT1_COL])   # right edge  (White)
    return tuple(segs)


_LINES_STATIC = _static_lines()


# ---------------------------------------------------------------------------
# State + game.
# ---------------------------------------------------------------------------

@dataclass
class OnyxState:
    stones: dict = field(default_factory=dict)   # point id -> BLACK/WHITE
    to_move: int = BLACK
    winner: Optional[int] = None
    ply: int = 0
    last: Optional[str] = None                   # last move ("swap" included)
    captured: tuple = ()                         # points emptied by last move
    conn_path: tuple = ()                        # winning chain (render)


class Onyx(Game):
    name = "Onyx"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options: Optional[dict] = None, rng=None) -> OnyxState:
        setup = (options or {}).get("setup", "official")
        stones = dict(_OFFICIAL) if setup == "official" else {}
        return OnyxState(stones=stones)

    def current_player(self, s: OnyxState) -> int:
        return s.to_move

    def legal_moves(self, s: OnyxState) -> list[str]:
        if s.winner is not None or s.ply >= PLY_CAP:
            return []
        moves = _placements(s.stones)
        if not moves:
            return []  # stuck: terminal draw
        if s.ply == 1:
            moves.append("swap")  # pie: second player may take Black
        return moves

    def apply_move(self, s: OnyxState, move: str, rng=None) -> OnyxState:
        if s.winner is not None:
            raise ValueError("game over")
        mover = s.to_move
        if move == "swap":
            if s.ply != 1:
                raise ValueError("swap only available on move 2")
            # Goals are transposed, so the colour swap must also transpose the
            # board: stone at (c,r) -> opposite colour at (r,c). The official
            # setup maps onto itself under this transform.
            stones = {_TRANSPOSE[p]: 1 - o for p, o in s.stones.items()}
            return OnyxState(stones=stones, to_move=1 - mover, winner=None,
                             ply=s.ply + 1, last="swap")
        if move in s.stones or move not in _ADJ:
            raise ValueError(f"illegal move {move!r}")
        cs = _MID_CORNERS.get(move)
        if cs is not None and any(c in s.stones for c in cs):
            raise ValueError(f"midpoint {move} blocked: a corner is occupied")
        stones = dict(s.stones)
        stones[move] = mover
        caps = _captures(stones, move, mover)
        for x in caps:
            del stones[x]
        path = _connects(stones, mover)
        return OnyxState(stones=stones, to_move=1 - mover,
                         winner=mover if path else None, ply=s.ply + 1,
                         last=move, captured=tuple(sorted(caps)),
                         conn_path=path)

    def is_terminal(self, s: OnyxState) -> bool:
        if s.winner is not None or s.ply >= PLY_CAP:
            return True
        return not _placements(s.stones)

    def returns(self, s: OnyxState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # ply cap / stuck board: honest draw

    def serialize(self, s: OnyxState) -> dict:
        return {
            "stones": dict(s.stones),
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "last": s.last,
            "captured": list(s.captured),
            "conn_path": list(s.conn_path),
        }

    def deserialize(self, d: dict) -> OnyxState:
        return OnyxState(
            stones={k: int(v) for k, v in d.get("stones", {}).items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            last=d.get("last"),
            captured=tuple(d.get("captured", [])),
            conn_path=tuple(d.get("conn_path", [])),
        )

    def describe_move(self, s: OnyxState, move: str) -> str:
        """Back's official notation: F6 / DE910, '*' per captured pair."""
        if move == "swap":
            return "swap (pie)"
        if move in _MID_CORNERS:
            c0 = LETTERS.index(move[0])
            r0 = int(move[1:-1]) - 1
            base = (f"{LETTERS[c0]}{LETTERS[c0 + 1]}".upper()
                    + f"{r0 + 1}{r0 + 2}")
            return base  # midpoint placements never capture
        stones = dict(s.stones)
        stones[move] = s.to_move
        pairs = len(_captures(stones, move, s.to_move)) // 2
        return move.upper() + "*" * pairs

    def render(self, s: OnyxState, perspective=None) -> dict:
        cells = [{"id": c["id"], "points": [list(p) for p in c["points"]]}
                 for c in _CELLS_STATIC]
        lines = [list(seg) for seg in _LINES_STATIC]
        tints = {}
        for p in s.captured:
            tints[p] = "#caa08a"           # where the last capture(s) happened
        for p in s.conn_path:
            tints[p] = "#caa05a"           # the winning chain
        pieces = [{"cell": p, "owner": o} for p, o in s.stones.items()]
        highlights = []
        if s.last and s.last != "swap":
            highlights.append({"cell": s.last, "kind": "last-move"})
        names = {BLACK: "Black", WHITE: "White"}
        if s.winner is not None:
            edge = "top–bottom" if s.winner == BLACK else "left–right"
            caption = f"{names[s.winner]} wins (connected {edge})"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            edge = "top–bottom" if s.to_move == BLACK else "left–right"
            caption = f"{names[s.to_move]} to move (connect {edge})"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": lines,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "actionNames": {"swap": "Swap (take Black)"},
        }
