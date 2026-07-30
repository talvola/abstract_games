"""Atoll — Mark Steere, January 2008.

Eight "islands" of stones ring an empty hexagonal grid.  The islands alternate
in colour around the perimeter, four per player, so each player owns two
diametrically **opposite** pairs.  Players add one stone per turn to any empty
cell; you win the moment one connected group of your stones (island stones
count) contains stones of two of your islands that are exactly opposite each
other.

Board (Fig. 1 of the rule sheet, verified cell-for-cell against the vector art
in ``Atoll_rules.pdf``).  Working in an offset "column, half-row" system
``(c, row)`` with ``N`` playable columns ``c = 1..N`` and the two island
columns ``c = 0`` and ``c = N+1``:

* playable cells: odd ``c`` carries rows ``3, 5, … 2N-3``; even ``c`` carries
  rows ``2, 4, … 2N-2``  (N=11 → 104 cells, N=15 → 202, N=19 → 332);
* the top islands sit on rows 0/1 and the bottom islands on rows 2N-1/2N, each
  pair split left/right of the middle column ``m = (N+1)/2`` — the row-0 cell
  above ``m`` is *absent*, which is the notch that separates them;
* the side islands sit in columns 0 and N+1 on rows ``4 … 2N-4``, split above
  and below the middle row ``N``.

``m`` must be even for that notch to exist, i.e. ``N ≡ 3 (mod 4)`` — hence the
board sizes 11 / 15 / 19.

Cell ids are axial ``"q,r"`` with ``q = c`` and ``r = (row - c) / 2``, rendered
flat-top so that a column is vertical, exactly as the rule sheet draws it.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZES = (11, 15, 19)

# Seat 0 moves first (the rule sheet's Black); the UI paints it red.
SEAT_NAMES = ("Red", "Blue")

# Axial neighbour offsets.  With the flat-top orientation these are
# N/S/NE/NW/SE/SW, so a file (constant q) is vertical.
DIRS = ((0, -1), (0, 1), (1, -1), (1, 0), (-1, 0), (-1, 1))

# The eight islands in cyclic order around the perimeter, clockwise from the
# top-left one.  Keys are "<seat><compass>".  Note the strict alternation of
# owners, and that opposite islands (four apart in this list) always share an
# owner — that is what makes the goal well defined.
PERIMETER_ORDER = ("1N", "0N", "1E", "0E", "1S", "0S", "1W", "0W")

# Each seat's two goals: North<->South and West<->East.
OPPOSITE_PAIRS = (("0N", "0S"), ("0W", "0E"), ("1N", "1S"), ("1W", "1E"))


def neighbors(q: int, r: int):
    return [(q + dq, r + dr) for dq, dr in DIRS]


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def _ax(c: int, row: int):
    """Offset (column, half-row) -> axial (q, r)."""
    return (c, (row - c) // 2)


@dataclass(frozen=True)
class BoardSpec:
    """Immutable per-size board geometry."""

    size: int
    playable: frozenset          # axial cells a stone may be placed on
    islands: dict                # island key -> frozenset of axial cells
    island_of: dict              # axial cell -> island key
    owner_of: dict               # axial cell -> seat, for island cells only
    order: tuple                 # deterministic placement order
    all_cells: tuple             # every cell on the board (playable + islands)


_SPECS: dict = {}


def _build(size: int) -> BoardSpec:
    n = int(size)
    if n not in SIZES:
        raise ValueError(f"unsupported Atoll board size {size!r}")
    m = (n + 1) // 2                       # middle playable column (always even)
    playable = set()
    for c in range(1, n + 1):
        lo, hi = (3, 2 * n - 3) if c % 2 else (2, 2 * n - 2)
        for row in range(lo, hi + 1, 2):
            playable.add(_ax(c, row))
    raw = {
        # top row pair: seat 1 to the left of the notch, seat 0 to the right
        "1N": [(c, 1) for c in range(1, m, 2)] + [(c, 0) for c in range(2, m, 2)],
        "0N": [(c, 1) for c in range(m + 1, n + 1, 2)] + [(c, 0) for c in range(m + 2, n, 2)],
        # bottom row pair: mirrored, so each seat's N and S islands are opposite
        "0S": [(c, 2 * n - 1) for c in range(1, m, 2)] + [(c, 2 * n) for c in range(2, m, 2)],
        "1S": [(c, 2 * n - 1) for c in range(m + 1, n + 1, 2)] + [(c, 2 * n) for c in range(m + 2, n, 2)],
        # side columns, split at the middle row
        "0W": [(0, row) for row in range(4, n, 2)],
        "1W": [(0, row) for row in range(n + 1, 2 * n - 3, 2)],
        "1E": [(n + 1, row) for row in range(4, n, 2)],
        "0E": [(n + 1, row) for row in range(n + 1, 2 * n - 3, 2)],
    }
    islands = {k: frozenset(_ax(*cell) for cell in v) for k, v in raw.items()}
    island_of, owner_of = {}, {}
    for k, cells in islands.items():
        for cell in cells:
            island_of[cell] = k
            owner_of[cell] = int(k[0])
    order = tuple(sorted(playable))
    all_cells = tuple(sorted(playable | set(island_of)))
    return BoardSpec(size=n, playable=frozenset(playable), islands=islands,
                     island_of=island_of, owner_of=owner_of, order=order,
                     all_cells=all_cells)


def spec_for(size: int) -> BoardSpec:
    s = _SPECS.get(int(size))
    if s is None:
        s = _SPECS[int(size)] = _build(size)
    return s


def cell_name(size: int, cell) -> str:
    """Algebraic name of a playable cell — file letter + rank counted up from
    the bottom of that file (a1 = foot of the leftmost playable column).  This
    is also AbstractPlay's notation for the same cell."""
    q, r = cell
    row = 2 * r + q
    y = (row - 1) // 2 if q % 2 else (row - 2) // 2
    return f"{chr(ord('a') + q - 1)}{size - 1 - y}"


@dataclass
class AtollState:
    size: int = 11
    stones: dict = field(default_factory=dict)   # axial cell -> seat (PLACED stones only)
    to_move: int = 0
    winner: Optional[int] = None
    last: Optional[tuple] = None


class Atoll(Game):
    name = "Atoll"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ core

    def initial_state(self, options=None, rng=None) -> AtollState:
        size = int((options or {}).get("size", 11))
        spec_for(size)                      # validate / warm the cache
        return AtollState(size=size)

    def current_player(self, s: AtollState) -> int:
        return s.to_move

    def legal_moves(self, s: AtollState) -> list[str]:
        if s.winner is not None:
            return []
        sp = spec_for(s.size)
        return [f"{q},{r}" for (q, r) in sp.order if (q, r) not in s.stones]

    def apply_move(self, s: AtollState, move: str, rng=None) -> AtollState:
        sp = spec_for(s.size)
        cell = _cell(move)
        if cell not in sp.playable:
            raise ValueError(f"{move} is not a playable cell")
        if cell in s.stones:
            raise ValueError(f"{move} is already occupied")
        if s.winner is not None:
            raise ValueError("the game is over")
        seat = s.to_move
        stones = dict(s.stones)
        stones[cell] = seat
        winner = seat if self._wins(sp, stones, seat, cell) else None
        return AtollState(size=s.size, stones=stones, to_move=1 - seat,
                          winner=winner, last=cell)

    def is_terminal(self, s: AtollState) -> bool:
        return s.winner is not None or not self.legal_moves(s)

    def returns(self, s: AtollState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        # A full board with no connection is impossible (see rules.md), but a
        # genuine tie is an honest draw rather than a fabricated tie-break.
        return [0.0, 0.0]

    # ---------------------------------------------------------- win detection

    @staticmethod
    def _owner(sp: BoardSpec, stones: dict, cell) -> Optional[int]:
        o = stones.get(cell)
        if o is not None:
            return o
        return sp.owner_of.get(cell)

    @classmethod
    def _group_islands(cls, sp: BoardSpec, stones: dict, seat: int, start) -> set:
        """Islands touched by `seat`'s connected group containing `start`."""
        seen = {start}
        stack = [start]
        found = set()
        k = sp.island_of.get(start)
        if k is not None and int(k[0]) == seat:
            found.add(k)
        while stack:
            cur = stack.pop()
            for nb in neighbors(*cur):
                if nb in seen or cls._owner(sp, stones, nb) != seat:
                    continue
                seen.add(nb)
                stack.append(nb)
                k = sp.island_of.get(nb)
                if k is not None:
                    found.add(k)
        return found

    @classmethod
    def _wins(cls, sp: BoardSpec, stones: dict, seat: int, start) -> bool:
        found = cls._group_islands(sp, stones, seat, start)
        for a, b in OPPOSITE_PAIRS:
            if int(a[0]) == seat and a in found and b in found:
                return True
        return False

    def winning_group(self, s: AtollState) -> set:
        """The cells of the group that won, for highlighting/inspection."""
        if s.winner is None:
            return set()
        sp = spec_for(s.size)
        seat = s.winner
        start = s.last
        if start is None or self._owner(sp, s.stones, start) != seat:
            return set()
        seen = {start}
        stack = [start]
        while stack:
            cur = stack.pop()
            for nb in neighbors(*cur):
                if nb not in seen and self._owner(sp, s.stones, nb) == seat:
                    seen.add(nb)
                    stack.append(nb)
        return seen

    def connected_islands(self, s: AtollState, seat: int) -> set:
        """All (a, b) island pairs of `seat` linked by one group — diagnostics.

        Each pair comes back as a tuple sorted ALPHABETICALLY, so ``("0E", "0W")``
        and never ``("0W", "0E")``.  Compare pairs as sets/frozensets, or against
        ``tuple(sorted(...))`` — testing membership of a literal ``("0W", "0E")``
        silently never matches.  ``_wins`` does not use this method; it checks
        both members of each pair explicitly and so is order-free.
        """
        sp = spec_for(s.size)
        pairs = set()
        done = set()
        for cell in sp.all_cells:
            if cell in done or self._owner(sp, s.stones, cell) != seat:
                continue
            found = self._group_islands(sp, s.stones, seat, cell)
            seen = {cell}
            stack = [cell]
            while stack:
                cur = stack.pop()
                for nb in neighbors(*cur):
                    if nb not in seen and self._owner(sp, s.stones, nb) == seat:
                        seen.add(nb)
                        stack.append(nb)
            done |= seen
            ks = sorted(found)
            for i, a in enumerate(ks):
                for b in ks[i + 1:]:
                    pairs.add((a, b))
        return pairs

    # ------------------------------------------------------------- bot eval

    def _link_cost(self, sp: BoardSpec, stones: dict, seat: int, a: str, b: str) -> int:
        """Fewest additional empty cells `seat` must fill to join islands a, b
        (0-1 BFS: own/island cells free, empty cost 1, opponent impassable)."""
        inf = 1 << 30
        dist = {}
        dq = deque()
        for cell in sp.islands[a]:
            dist[cell] = 0
            dq.append(cell)
        target = sp.islands[b]
        best = inf
        while dq:
            cur = dq.popleft()
            d = dist[cur]
            if d >= best:
                continue
            if cur in target:
                best = d
                continue
            for nb in neighbors(*cur):
                if nb not in sp.playable and nb not in sp.island_of:
                    continue
                own = self._owner(sp, stones, nb)
                if own is None:
                    w = 1
                elif own == seat:
                    w = 0
                else:
                    continue
                nd = d + w
                if nd < dist.get(nb, inf):
                    dist[nb] = nd
                    (dq.appendleft if w == 0 else dq.append)(nb)
        return best

    def heuristic(self, s: AtollState) -> list[float]:
        if s.winner is not None:
            return self.returns(s)
        sp = spec_for(s.size)
        need = []
        for seat in (0, 1):
            d = min(self._link_cost(sp, s.stones, seat, a, b)
                    for a, b in OPPOSITE_PAIRS if int(a[0]) == seat)
            need.append(d - (0.5 if s.to_move == seat else 0.0))
        v = math.tanh(0.4 * (need[1] - need[0]))
        return [v, -v]

    # ----------------------------------------------------------- (de)serialize

    def serialize(self, s: AtollState) -> dict:
        return {
            "size": s.size,
            "stones": {f"{q},{r}": p for (q, r), p in s.stones.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "last": None if s.last is None else f"{s.last[0]},{s.last[1]}",
        }

    def deserialize(self, d: dict) -> AtollState:
        return AtollState(
            size=int(d["size"]),
            stones={_cell(k): int(v) for k, v in d["stones"].items()},
            to_move=int(d["to_move"]),
            winner=d["winner"],
            last=None if d["last"] is None else _cell(d["last"]),
        )

    # ------------------------------------------------------------------- UI

    def describe_move(self, s: AtollState, move: str) -> str:
        try:
            return cell_name(s.size, _cell(move))
        except Exception:
            return move

    def render(self, s: AtollState, perspective=None) -> dict:
        sp = spec_for(s.size)
        tint = ("#f0d6d6", "#d6dcf0")
        pieces = []
        tints = {}
        for cell, seat in sp.owner_of.items():
            pieces.append({"cell": f"{cell[0]},{cell[1]}", "owner": seat})
            tints[f"{cell[0]},{cell[1]}"] = tint[seat]
        for (q, r), seat in s.stones.items():
            pieces.append({"cell": f"{q},{r}", "owner": seat})
        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})
        if s.winner is not None:
            caption = f"{SEAT_NAMES[s.winner]} wins"
        elif not self.legal_moves(s):
            caption = "Board full — draw"
        else:
            caption = (f"{SEAT_NAMES[s.to_move]} to move — link your North–South "
                       f"or West–East islands")
        return {
            "board": {
                "type": "hex",
                "cells": [f"{q},{r}" for (q, r) in sp.all_cells],
                "orientation": "flat",
                "tints": tints,
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
