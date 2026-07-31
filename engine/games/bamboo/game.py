"""Bamboo — Mark Steere, March 2021.

A hexagon-of-hexagons ("hexhex"), initially empty.  Red and Blue alternately
place one stone of their own colour on an empty cell; passing is not allowed.

The single restriction, quoted verbatim from the rule sheet:

    "A player's group can't contain more stones than the number of groups he
     has."

A *group* is one or more interconnected like-coloured stones.  The clause is a
**position invariant on the mover**, checked after the placement and over **all**
of that player's groups — not merely the group the new stone joins.  A placement
may simultaneously grow one group and merge several others (lowering the group
count), so the two readings genuinely differ, and **Figure 2 of the rule sheet
settles it**: under the all-groups reading its printed green set is exactly the
4 cells drawn; under the placed-group-only reading it would be 8.  (AbstractPlay
`gameslib` implements the placed-group-only reading and is wrong here — see
``rules.md``.)

The opponent's groups never matter.

**Object:** the last player to place a stone wins.  Equivalently, the player who
cannot place loses; passing being illegal, that is the only way the game ends.

Termination is immediate and needs no ply cap or repetition rule: every move
places exactly one stone and no stone is ever removed or moved, so the number of
empty cells strictly decreases and the game lasts at most ``len(spec.cells)``
plies (= ``3n^2 - 3n + 1`` on side ``n``).

Drawlessness is likewise structural: the empty board always admits a move (a
lone stone is a group of 1 with a group count of 1), so at least one stone is
always placed and "the last player to place a stone" is always defined.

Coordinates are axial ``"q,r"`` with the hexhex of side ``n`` being
``max(|q|, |r|, |q+r|) <= n-1``; the board is drawn pointy-top (rows
horizontal), exactly as both rule-sheet figures draw it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# Board side lengths offered in the manifest.  5 is the size BOTH rule-sheet
# figures use (61 cells) and is the default; 6 and 7 are AbstractPlay's two
# board variants; 4 is offered as a quick game.
SIZES = (4, 5, 6, 7)

SEAT_NAMES = ("Red", "Blue")

# Axial neighbour offsets.  Pointy-top: E, NE, NW, W, SW, SE — a *row*
# (constant r) is horizontal, which is how the rule sheet draws the board.
DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def neighbors(q: int, r: int):
    return [(q + dq, r + dr) for dq, dr in DIRS]


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


@dataclass(frozen=True)
class BoardSpec:
    """Per-size geometry, built once and cached."""

    size: int          # side length n
    cells: tuple       # every cell, deterministic (sorted) order
    cellset: frozenset
    nbrs: dict         # cell -> tuple of on-board neighbours


_SPECS: dict = {}


def _build(size: int) -> BoardSpec:
    n = int(size)
    if n < 2:
        raise ValueError(f"unsupported Bamboo board size {size!r}")
    R = n - 1
    cells = tuple(sorted(
        (q, r)
        for q in range(-R, R + 1)
        for r in range(-R, R + 1)
        if abs(q + r) <= R
    ))
    cellset = frozenset(cells)
    nbrs = {c: tuple(nb for nb in neighbors(*c) if nb in cellset) for c in cells}
    return BoardSpec(size=n, cells=cells, cellset=cellset, nbrs=nbrs)


def spec_for(size: int) -> BoardSpec:
    s = _SPECS.get(int(size))
    if s is None:
        s = _SPECS[int(size)] = _build(size)
    return s


def cell_count(size: int) -> int:
    """3n^2 - 3n + 1, the number of cells of a hexhex of side n."""
    n = int(size)
    return 3 * n * n - 3 * n + 1


def cell_name(size: int, cell) -> str:
    """Algebraic name: row letter counted UP from the bottom row, then the
    1-based index of the cell within its row from the left.  This is also
    AbstractPlay's notation for the same board (``a1`` is the bottom-left cell)."""
    q, r = cell
    R = size - 1
    q_min = max(-R, -R - r)
    return f"{chr(ord('a') + R - r)}{q - q_min + 1}"


# --------------------------------------------------------------------------
#  Groups
# --------------------------------------------------------------------------

def groups_of(sp: BoardSpec, stones: dict, seat: int) -> list:
    """Every connected group of `seat`'s stones, as a list of sets."""
    mine = {c for c, p in stones.items() if p == seat}
    out = []
    seen: set = set()
    for c in mine:
        if c in seen:
            continue
        comp = {c}
        seen.add(c)
        stack = [c]
        while stack:
            cur = stack.pop()
            for nb in sp.nbrs[cur]:
                if nb in mine and nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    stack.append(nb)
        out.append(comp)
    return out


def invariant_holds(sp: BoardSpec, stones: dict, seat: int) -> bool:
    """The rule sheet's clause as a position predicate: no group of `seat`
    contains more stones than `seat`'s number of groups."""
    g = groups_of(sp, stones, seat)
    return not g or max(len(x) for x in g) <= len(g)


def _label_groups(sp: BoardSpec, stones: dict, seat: int):
    """One flood-fill pass: (cell -> group id, group id -> size)."""
    lab: dict = {}
    sizes: list = []
    for c, p in stones.items():
        if p != seat or c in lab:
            continue
        gid = len(sizes)
        lab[c] = gid
        n = 1
        stack = [c]
        while stack:
            cur = stack.pop()
            for nb in sp.nbrs[cur]:
                if nb not in lab and stones.get(nb) == seat:
                    lab[nb] = gid
                    n += 1
                    stack.append(nb)
        sizes.append(n)
    return lab, sizes


@dataclass
class BambooState:
    size: int = 5
    stones: dict = field(default_factory=dict)   # (q, r) -> seat
    to_move: int = 0
    winner: Optional[int] = None
    last: Optional[tuple] = None                 # the cell just played


class Bamboo(Game):
    name = "Bamboo"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ core

    def initial_state(self, options=None, rng=None) -> BambooState:
        o = options or {}
        size = int(o.get("size", 5))
        if size not in SIZES:
            raise ValueError(f"unsupported board size {size!r}")
        spec_for(size)
        return BambooState(size=size)

    def current_player(self, s: BambooState) -> int:
        return s.to_move

    # ------------------------------------------------------------ placements

    def placements(self, s: BambooState, seat: Optional[int] = None) -> list:
        """Every cell `seat` (default: the player to move) may legally occupy,
        as (q, r) tuples in board order.

        One flood-fill of the mover's stones, then O(1) work per empty cell:
        placing on `c` merges the k distinct groups adjacent to `c` into one of
        size ``total + 1`` and leaves ``count - k + 1`` groups, so the position
        after the placement satisfies the invariant iff

            max(total + 1, largest group NOT adjacent to c) <= count - k + 1
        """
        if seat is None:
            seat = s.to_move
        sp = spec_for(s.size)
        lab, sizes = _label_groups(sp, s.stones, seat)
        count = len(sizes)
        desc = sorted(sizes, reverse=True)
        out = []
        for c in sp.cells:
            if c in s.stones:
                continue
            adj = set()
            for nb in sp.nbrs[c]:
                gid = lab.get(nb)
                if gid is not None:
                    adj.add(gid)
            placed = 1 + sum(sizes[g] for g in adj)
            new_count = count - len(adj) + 1
            if placed > new_count:
                continue
            # largest group of `seat` that the placement does NOT absorb
            rem = {}
            for g in adj:
                rem[sizes[g]] = rem.get(sizes[g], 0) + 1
            other_max = 0
            for sz in desc:
                if rem.get(sz):
                    rem[sz] -= 1
                    continue
                other_max = sz
                break
            if other_max <= new_count:
                out.append(c)
        return out

    def legal_moves(self, s: BambooState) -> list[str]:
        if s.winner is not None:
            return []
        return [f"{q},{r}" for (q, r) in self.placements(s)]

    def apply_move(self, s: BambooState, move: str, rng=None) -> BambooState:
        if s.winner is not None:
            raise ValueError("the game is over")
        sp = spec_for(s.size)
        cell = _cell(move)
        if cell not in sp.cellset:
            raise ValueError(f"{move} is not a cell of this board")
        if cell in s.stones:
            raise ValueError(f"{move} is already occupied")
        seat = s.to_move
        stones = dict(s.stones)
        stones[cell] = seat
        if not invariant_holds(sp, stones, seat):
            raise ValueError(
                f"{move} would leave {SEAT_NAMES[seat]} with a group larger "
                f"than his number of groups")
        nxt = BambooState(size=s.size, stones=stones, to_move=1 - seat,
                          winner=None, last=cell)
        # "The last player to place a stone wins" — so the mover wins as soon as
        # the opponent has no placement (passing is illegal).
        if not self.placements(nxt):
            nxt.winner = seat
        return nxt

    def is_terminal(self, s: BambooState) -> bool:
        return s.winner is not None or not self.placements(s)

    def returns(self, s: BambooState) -> list[float]:
        # The player to move is the one who cannot place; the previous player
        # placed the last stone and wins.  `winner` (set in apply_move) always
        # equals 1 - to_move, so the two agree — see selftest.
        w = s.winner if s.winner is not None else 1 - s.to_move
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    # -------------------------------------------------------------- helpers

    def group_count(self, s: BambooState, seat: int) -> int:
        return len(_label_groups(spec_for(s.size), s.stones, seat)[1])

    def largest_group(self, s: BambooState, seat: int) -> int:
        sizes = _label_groups(spec_for(s.size), s.stones, seat)[1]
        return max(sizes) if sizes else 0

    def group_of(self, s: BambooState, cell) -> set:
        """The connected like-coloured group containing `cell` (empty if the
        cell is empty)."""
        seat = s.stones.get(cell)
        if seat is None:
            return set()
        sp = spec_for(s.size)
        seen = {cell}
        stack = [cell]
        while stack:
            cur = stack.pop()
            for nb in sp.nbrs[cur]:
                if nb not in seen and s.stones.get(nb) == seat:
                    seen.add(nb)
                    stack.append(nb)
        return seen

    # ------------------------------------------------------------- bot eval

    def heuristic(self, s: BambooState) -> list[float]:
        """Mobility balance, as a LIST of `num_players` payoffs (the same
        convention as ``returns`` — MCTS indexes it per player).

        The loser is exactly the player who runs out of legal placements first,
        so "how many cells may I still occupy, compared with my opponent" is a
        direct measure of the goal.

        **What it is worth depends entirely on the board size**, because MCTS
        only ever consults a ``heuristic`` when a rollout is TRUNCATED.  At the
        shipped ``max_rollout=50`` the cutoff fires 0% of the time on side 4,
        ~1/3 of the time on side 5, and 100% on sides 6 and 7 — so on the two
        small boards this eval is worth literally nothing (on side 4 it is never
        called at all), while on sides 6-7 it is the *only* signal the search
        has: without it every rollout scores as a draw and the root children all
        end up at exactly 0.  Do NOT read the 0.925 win rate in ``rules.md`` as
        general bot strength: it is measured with the cutoff FORCED
        (``max_rollout=4``); at the shipped default on the default board the
        eval is statistically indistinguishable from none.  See ``rules.md``
        for all three measurements.
        """
        a = self.placements(s, 0)
        b = self.placements(s, 1)
        if s.winner is not None or not (a if s.to_move == 0 else b):
            return self.returns(s)
        v = math.tanh(0.08 * (len(a) - len(b)))
        return [v, -v]

    # ----------------------------------------------------------- (de)serialize

    def serialize(self, s: BambooState) -> dict:
        return {
            "size": s.size,
            "stones": {f"{q},{r}": p for (q, r), p in s.stones.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "last": None if s.last is None else f"{s.last[0]},{s.last[1]}",
        }

    def deserialize(self, d: dict) -> BambooState:
        return BambooState(
            size=int(d["size"]),
            stones={_cell(k): int(v) for k, v in d["stones"].items()},
            to_move=int(d["to_move"]),
            winner=None if d["winner"] is None else int(d["winner"]),
            last=None if d.get("last") is None else _cell(d["last"]),
        )

    # ------------------------------------------------------------------- UI

    def describe_move(self, s: BambooState, move: str) -> str:
        try:
            return cell_name(s.size, _cell(move))
        except Exception:
            return move

    def render(self, s: BambooState, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": p}
                  for (q, r), p in s.stones.items()]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}",
                               "kind": "last-move"})
        stats = ", ".join(
            f"{SEAT_NAMES[p]} {self.largest_group(s, p)}/{self.group_count(s, p)}"
            for p in (0, 1))
        if self.is_terminal(s):
            w = s.winner if s.winner is not None else 1 - s.to_move
            caption = (f"{SEAT_NAMES[w]} wins — {SEAT_NAMES[1 - w]} has no "
                       f"legal placement (largest group/groups: {stats})")
        else:
            caption = (f"{SEAT_NAMES[s.to_move]} to move "
                       f"(largest group/groups: {stats})")
        return {
            "board": {
                "type": "hex",
                "shape": "hexagon",
                "size": s.size,
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
