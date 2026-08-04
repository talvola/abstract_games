"""Cairo Corridor — Markus Hagenauer (rules (c) 2012, nestorgames 2013).

A "non-disconnection-and-area-control" placement game on a CAIRO PENTAGONAL
TILING of 72 pentagons (a 6x6 grid of two-pentagon blocks).

Players alternate dropping one pentagon of their colour onto any empty cell,
subject to one restriction: after the placement there must still be at least
one CORRIDOR — a connected group of empty cells that touches all four sides of
the board.  The game ends when only one Corridor is left and no more pentagons
can be placed adjacent to it; whoever has more pentagons adjacent to that
Corridor wins.

Geometry
--------
The board is generated analytically (pure stdlib) as the "collinear" Cairo
tiling: block (j, r) of a size x size grid holds two pentagons, a West|East
pair when (j + r) is even and a North/South pair when it is odd.  **The cell
adjacency used by every rule is derived from SHARED POLYGON EDGES of the
generated pentagons**, not from a hand-written neighbour table, so the drawn
board and the rules can never disagree ("adjacent" = "sharing an edge, not just
a corner", per the rulebook).

Cell ids are "x,y": x = 0..2*size-1 numbers the half-columns left to right,
y = 0..size-1 numbers the block rows BOTTOM to top.  A move is one cell id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from agp.game import Game

# Seat 0 moves first.  The physical game ships black and red pentagons, but the
# platform paints seat 0 red and seat 1 blue, so the seats are NAMED after what
# a player actually sees on screen (a caption must never lie about the colour).
# `selftest.py` pins these names to the owner of a specific pentagon in the
# rulebook's Example 1 figure, which is ground truth outside this module.
SEAT_NAMES = ("Red", "Blue")
DEFAULT_SIZE = 6                       # the published board: 6*6*2 = 72 pentagons

# ---------------------------------------------------------------------------
# Geometry: the Cairo pentagonal tiling.
# ---------------------------------------------------------------------------
# Pentagon vertex offsets from the cell centre, in SVG space (y increases
# DOWNWARD, which is also how the web renderer reads `polygons` points).  Unit
# block = 1; the four orientations are the same pentagon rotated by 90 degrees.
_H, _Q, _W = 0.5, 0.25, 0.75
PENT_OFFSETS = {
    "N": ((0, -_H), (_W, -_Q), (_H, _H), (-_H, _H), (-_W, -_Q)),
    "S": ((0, _H), (-_W, _Q), (-_H, -_H), (_H, -_H), (_W, _Q)),
    "E": ((_H, 0), (_Q, _W), (-_H, _H), (-_H, -_H), (_Q, -_W)),
    "W": ((-_H, 0), (-_Q, -_W), (_H, -_H), (_H, _H), (-_Q, _W)),
}
SCALE = 40.0                           # render units per block


def _block(j: int, r: int) -> Tuple[float, float, str]:
    """Centre of a block's FIRST pentagon and the block's orientation.

    r counts block rows from the TOP of the drawing (r = size-1-y).
    "H" = a West|East pair (side by side), "V" = a North/South pair.
    """
    if r % 2 == 0:
        rsx, rsy, rso = 0.0, 1.5 * r, "H"
    else:
        rsx, rsy, rso = 0.5, 1.0 + (r // 2) * 3.0, "V"
    orient = rso if j % 2 == 0 else ("V" if rso == "H" else "H")
    if j % 2 == 0:
        cx, cy = rsx + 1.5 * j, rsy
    elif orient == "H":
        cx, cy = rsx + 1.0 + (j // 2) * 3.0, rsy + 0.5
    else:
        cx, cy = rsx + 2.0 + (j // 2) * 3.0, rsy - 0.5
    return cx, cy, orient


def _vkey(p: Tuple[float, float]) -> Tuple[int, int]:
    """Exact-ish vertex key (every coordinate is a multiple of 1/4)."""
    return (round(p[0] * 4), round(p[1] * 4))


class Boardography:
    """Static per-size board data: polygons, kinds, edge-sharing adjacency, sides."""

    __slots__ = ("size", "ids", "kind", "poly", "adj", "north", "south",
                 "west", "east", "index")

    def __init__(self, size: int):
        self.size = size
        ids: List[str] = []
        kind: Dict[str, str] = {}
        poly: Dict[str, Tuple[Tuple[float, float], ...]] = {}
        for r in range(size):
            y = size - 1 - r
            for j in range(size):
                cx, cy, orient = _block(j, r)
                pair = (("W", cx, cy), ("E", cx + 1.0, cy)) if orient == "H" \
                    else (("N", cx, cy), ("S", cx, cy + 1.0))
                for k, (letter, px, py) in enumerate(pair):
                    cid = "%d,%d" % (2 * j + k, y)
                    ids.append(cid)
                    kind[cid] = letter
                    poly[cid] = tuple((px + dx, py + dy)
                                      for dx, dy in PENT_OFFSETS[letter])
        self.ids = tuple(ids)
        self.kind = kind
        self.poly = poly
        self.index = {cid: i for i, cid in enumerate(ids)}

        # --- adjacency from SHARED POLYGON EDGES (never a hand-written table)
        owner: Dict[frozenset, List[str]] = {}
        for cid, pts in poly.items():
            for i in range(5):
                e = frozenset((_vkey(pts[i]), _vkey(pts[(i + 1) % 5])))
                owner.setdefault(e, []).append(cid)
        adj: Dict[str, set] = {cid: set() for cid in ids}
        for e, own in owner.items():
            if len(own) == 2:
                adj[own[0]].add(own[1])
                adj[own[1]].add(own[0])
            elif len(own) != 1:                       # pragma: no cover
                raise AssertionError("tiling is not edge-to-edge: %r" % (own,))
        self.adj = {cid: frozenset(v) for cid, v in adj.items()}

        # --- the four sides of the board.
        # A block row at the TOP contributes its W/E pentagons (both touch the
        # top border) or its N pentagon; its S pentagon is fully interior.
        top, bot = size - 1, 0
        self.north = frozenset(c for c in ids if c.endswith(",%d" % top)
                               and kind[c] != "S")
        self.south = frozenset(c for c in ids if c.endswith(",%d" % bot)
                               and kind[c] != "N")
        self.west = frozenset(c for c in ids if c.startswith("0,")) | \
            frozenset(c for c in ids if c.startswith("1,") and kind[c] == "S")
        last, prev = 2 * size - 1, 2 * size - 2
        self.east = frozenset(c for c in ids if c.startswith("%d," % last)) | \
            frozenset(c for c in ids
                      if c.startswith("%d," % prev) and kind[c] == "N")

    def sides(self):
        return (self.north, self.south, self.west, self.east)


_BOARDS: Dict[int, Boardography] = {}


def board_for(size: int) -> Boardography:
    b = _BOARDS.get(size)
    if b is None:
        b = _BOARDS[size] = Boardography(size)
    return b


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
@dataclass
class CCState:
    size: int
    tie: str                                  # "draw" | "mover_loses"
    board: Dict[str, int]                     # cell id -> seat
    to_move: int
    last_move: Optional[str] = None
    # Derived, never serialised, never part of equality: (region, critical).
    _cache: Optional[tuple] = field(default=None, compare=False, repr=False)


class CairoCorridor(Game):
    """Cairo Corridor."""

    # ---- board queries -------------------------------------------------
    @staticmethod
    def _region(bg: Boardography, pool):
        """The connected component of `pool` touching ALL FOUR sides, or None.

        At most one such component can exist (a component joining North to
        South separates West from East on a planar board, and the Cairo tiling
        has no diagonal crossings: two cells meeting only at a degree-4 vertex
        are not adjacent), so "the Corridor" is well defined.
        """
        adj = bg.adj
        north, south, west, east = bg.sides()
        seen = set()
        for start in pool:
            if start in seen or start not in north:
                continue
            comp, stack = set(), [start]
            while stack:
                c = stack.pop()
                if c in comp:
                    continue
                comp.add(c)
                for n in adj[c]:
                    if n in pool and n not in comp:
                        stack.append(n)
            seen |= comp
            if comp & south and comp & west and comp & east:
                return comp
        return None

    def _derive(self, s: CCState):
        """(corridor region, frozenset of cells whose placement kills it)."""
        if s._cache is not None:
            return s._cache
        bg = board_for(s.size)
        empty = frozenset(c for c in bg.ids if c not in s.board)
        region = self._region(bg, empty)
        if region is None:                                # pragma: no cover
            raise AssertionError("state has no Corridor")
        region = frozenset(region)
        # A candidate only has to be re-flooded WITHIN the old region: every
        # other component of empty cells is untouched by the placement and (by
        # the uniqueness argument above) does not reach all four sides, so the
        # new Corridor is always a subset of the old one.
        critical = frozenset(
            c for c in region if self._region(bg, region - {c}) is None)
        s._cache = (region, critical)
        return s._cache

    # ---- Game interface -------------------------------------------------
    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CCState:
        o = options or {}
        size = int(o.get("size", DEFAULT_SIZE))
        tie = str(o.get("tie", "draw"))
        if tie not in ("draw", "mover_loses"):
            raise ValueError("unknown tie rule: %r" % (tie,))
        board_for(size)
        return CCState(size=size, tie=tie, board={}, to_move=0)

    def current_player(self, s: CCState) -> int:
        return s.to_move

    def legal_moves(self, s: CCState) -> List[str]:
        bg = board_for(s.size)
        _region, critical = self._derive(s)
        # The rulebook's only restriction is "there must always be at least one
        # Corridor", so EVERY empty cell outside the critical set is legal —
        # including cells in a dead zone, which lie in a different component of
        # empty cells and so cannot touch the Corridor at all.
        return [c for c in bg.ids if c not in s.board and c not in critical]

    def apply_move(self, s: CCState, move: str, rng=None) -> CCState:
        bg = board_for(s.size)
        if move not in bg.index:
            raise ValueError("no such cell: %r" % (move,))
        if move in s.board:
            raise ValueError("cell is occupied: %r" % (move,))
        _region, critical = self._derive(s)
        if move in critical:
            raise ValueError("placement would destroy the last Corridor: %r"
                             % (move,))
        nb = dict(s.board)
        nb[move] = s.to_move
        return CCState(size=s.size, tie=s.tie, board=nb,
                       to_move=1 - s.to_move, last_move=move)

    def is_terminal(self, s: CCState) -> bool:
        region, critical = self._derive(s)
        return region == critical

    def scores(self, s: CCState) -> List[int]:
        """Pentagons of each seat adjacent to the CRITICAL corridor cells.

        At the end of the game the critical set IS the whole Corridor, so this
        is exactly the rulebook's "pentagons adjacent to the Corridor"; before
        then it is a natural running score (the cells that are already locked
        into the final Corridor).
        """
        bg = board_for(s.size)
        _region, critical = self._derive(s)
        sc = [0, 0]
        counted = set()
        for c in critical:
            for n in bg.adj[c]:
                if n in s.board and n not in counted:
                    counted.add(n)
                    sc[s.board[n]] += 1
        return sc

    def winner(self, s: CCState) -> Optional[int]:
        """None = draw."""
        if not self.is_terminal(s):
            return None
        a, b = self.scores(s)
        if a != b:
            return 0 if a > b else 1
        if s.tie == "mover_loses":
            # The player to move is the one who did NOT make the last placement.
            return s.to_move
        return None

    def returns(self, s: CCState) -> List[float]:
        if not self.is_terminal(s):
            return [0.0, 0.0]
        w = self.winner(s)
        if w is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    # ---- serialisation ---------------------------------------------------
    def serialize(self, s: CCState) -> dict:
        return {
            "size": s.size,
            "tie": s.tie,
            "board": dict(s.board),
            "to_move": s.to_move,
            "last_move": s.last_move,
        }

    def deserialize(self, d: dict) -> CCState:
        return CCState(
            size=int(d["size"]),
            tie=str(d["tie"]),
            board={str(k): int(v) for k, v in (d["board"] or {}).items()},
            to_move=int(d["to_move"]),
            last_move=d["last_move"],
        )

    # ---- no `heuristic` on purpose ---------------------------------------
    # The obvious eval, tanh((score0 - score1) / 4), was measured THROUGH
    # MCTSBot (iterations=60, colours swapped each game; the two totals on each
    # line sum to that line's game count):
    #
    #     vs. its own sign-flipped self, max_rollout=4 : 30.0 - 0.0  (1.000)
    #     vs. NO heuristic,             max_rollout=4  : 23.0 - 1.0  (0.958)
    #     vs. NO heuristic,             max_rollout=50 : 12.5 - 11.5 (0.521)
    #
    # Its direction is right and it dominates when the rollout cutoff fires --
    # but a whole game is only ~40-60 plies and gets shorter as it goes, so at
    # the platform's DEFAULT max_rollout=50 almost every rollout already
    # reaches a real terminal and the eval is never consulted. Measured over
    # complete games, only ~5% of rollouts reach the cutoff at max_rollout=50
    # (~93% at max_rollout=4). Adding it would buy nothing the bot does not
    # already have, so it is deliberately absent.
    #
    # NOTE the 0.521 line is 24 games (s.e. ~0.10): it shows no measurable
    # benefit, which is not the same as proving none. Shipping no heuristic is
    # the conservative reading of it.

    # ---- presentation ----------------------------------------------------
    def describe_move(self, s: CCState, move: str) -> str:
        bg = board_for(s.size)
        return "%s %s" % (move, bg.kind.get(move, "?"))

    def render(self, s: CCState, perspective=None) -> dict:
        bg = board_for(s.size)
        region, critical = self._derive(s)
        cells = [{"id": cid,
                  "points": [[round(x * SCALE, 3), round(y * SCALE, 3)]
                             for x, y in bg.poly[cid]]}
                 for cid in bg.ids]
        tints = {}
        for cid in bg.ids:
            if cid in s.board:
                continue
            if cid in critical:
                tints[cid] = "#f7f0a0"          # locked-in Corridor (illegal)
            elif cid in region:
                tints[cid] = "#c6efd2"          # Corridor, still placeable
            else:
                tints[cid] = "#e6e6e6"          # dead zone (scores nothing)
        pieces = [{"cell": cid, "owner": seat, "shape": "fill"}
                  for cid, seat in s.board.items()]
        highlights = []
        if s.last_move:
            highlights.append({"cell": s.last_move, "kind": "last-move"})
        a, b = self.scores(s)
        if self.is_terminal(s):
            w = self.winner(s)
            if w is None:
                caption = "Game over — draw %d-%d" % (a, b)
            else:
                caption = "Game over — %s wins %d-%d" % (
                    SEAT_NAMES[w], max(a, b), min(a, b))
        else:
            caption = "%s to move — Corridor %d-%d (%d cells, %d locked)" % (
                SEAT_NAMES[s.to_move], a, b, len(region), len(critical))
        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
