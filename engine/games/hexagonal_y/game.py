"""Hexagonal Y — Mark Steere, September 2023.

A regular hexagonal board (a "hexhex") of hexagonal cells, initially empty.
Red and Blue alternately place a stone on an empty cell, Red first.  A
placement on a **perimeter** cell obliges you to place a second stone on the
diametrically opposite perimeter cell (180 degrees about the board's centre),
which concludes your turn; an interior placement places one stone.

You win when one connected group of your stones occupies at least two perimeter
cells **and** the shortest perimeter path containing all of that group's
perimeter cells is longer than half of the perimeter.

Coordinates are axial ``"q,r"`` with the hexhex of side ``n`` being
``max(|q|, |r|, |q+r|) <= n-1``; the perimeter is the ring at distance
``n-1``.  The rendering is pointy-top (rows horizontal), exactly as the rule
sheet draws every figure, and the antipode of ``(q, r)`` is ``(-q, -r)``.

The double placement gives the game its key structural invariant:

    a perimeter cell and its antipode are ALWAYS either both empty, or both
    occupied by stones of the SAME colour.

They start empty together and only ever change together.  So the prose's one
gap — "what if the opposite perimeter cell is already taken?" — describes a
position that cannot arise (see ``rules.md``); ``selftest.py`` asserts the
invariant over whole random games on every board size.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# Board side lengths offered in the manifest.  4 is the size every figure of
# the rule sheet uses; 7 is AbstractPlay's default (127 cells); 8/9/11 are its
# other variants.
SIZES = (4, 5, 6, 7, 8, 9, 11)

SEAT_NAMES = ("Red", "Blue")

# Axial neighbour offsets.  Pointy-top: E, NE, NW, W, SW, SE — a *row*
# (constant r) is horizontal, which is how the rule sheet draws the board.
DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def neighbors(q: int, r: int):
    return [(q + dq, r + dr) for dq, dr in DIRS]


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def hex_dist(q: int, r: int) -> int:
    """Distance from the centre cell (0, 0)."""
    return (abs(q) + abs(r) + abs(q + r)) // 2


@dataclass(frozen=True)
class BoardSpec:
    """Per-size geometry, built once and cached."""

    size: int                 # side length n
    cells: tuple              # every cell, deterministic order
    cellset: frozenset
    ring: tuple               # perimeter cells in CYCLIC order
    ring_index: dict          # perimeter cell -> its index in `ring`
    perimeter: int            # len(ring) == 6 * (n - 1)


_SPECS: dict = {}


def _build(size: int) -> BoardSpec:
    n = int(size)
    if n < 2:
        raise ValueError(f"unsupported Hexagonal Y board size {size!r}")
    R = n - 1
    cells = tuple(sorted(
        (q, r)
        for q in range(-R, R + 1)
        for r in range(-R, R + 1)
        if abs(q + r) <= R
    ))
    # Walk the ring at radius R: start one full step along direction 4 (SW) and
    # then take R steps in each of the six directions in turn.
    ring = []
    q, r = -R, R
    for d in range(6):
        dq, dr = DIRS[d]
        for _ in range(R):
            ring.append((q, r))
            q, r = q + dq, r + dr
    assert (q, r) == (-R, R)
    assert len(ring) == len(set(ring)) == 6 * R
    assert all(hex_dist(*c) == R for c in ring)
    return BoardSpec(size=n, cells=cells, cellset=frozenset(cells),
                     ring=tuple(ring),
                     ring_index={c: i for i, c in enumerate(ring)},
                     perimeter=6 * R)


def spec_for(size: int) -> BoardSpec:
    s = _SPECS.get(int(size))
    if s is None:
        s = _SPECS[int(size)] = _build(size)
    return s


def antipode(cell):
    """The cell diametrically opposite `cell` about the board's centre."""
    return (-cell[0], -cell[1])


def cell_name(size: int, cell) -> str:
    """Algebraic name: row letter counted UP from the bottom row, then the
    1-based index of the cell within its row from the left.  This is also
    AbstractPlay's notation for the same board (`a1` is the bottom-left cell)."""
    q, r = cell
    R = size - 1
    q_min = max(-R, -R - r)
    return f"{chr(ord('a') + R - r)}{q - q_min + 1}"


# --------------------------------------------------------------------------
#  The win predicate.
#
#  The perimeter is a cycle of P = 6(n-1) cells.  A group occupies a subset S
#  of it.  "The shortest perimeter path that includes all of S" is the
#  complement of the LARGEST gap between cyclically consecutive members of S,
#  so its length is P - max_gap.  The group wins when that is > P/2.
# --------------------------------------------------------------------------

def covering_arc(sp: BoardSpec, idxs) -> Optional[tuple]:
    """The shortest perimeter arc containing every index in `idxs`, as a tuple
    of ring indices in cyclic order.  ``None`` when fewer than two are given
    (rule 1 needs at least two perimeter stones)."""
    s = sorted(set(idxs))
    if len(s) < 2:
        return None
    P = sp.perimeter
    k = len(s)
    best_gap, best_i = -1, 0
    for i in range(k):
        gap = (s[(i + 1) % k] - s[i] - 1) % P
        if gap > best_gap:
            best_gap, best_i = gap, i
    start = s[(best_i + 1) % k]
    length = P - best_gap
    return tuple((start + j) % P for j in range(length))


def arc_wins(sp: BoardSpec, arc) -> bool:
    """Rule 2: the arc must comprise MORE THAN half of the perimeter."""
    return arc is not None and 2 * len(arc) > sp.perimeter


@dataclass
class HexYState:
    size: int = 7
    stones: dict = field(default_factory=dict)   # (q, r) -> seat
    to_move: int = 0
    winner: Optional[int] = None
    last: tuple = ()             # cells placed/affected by the last move
    pie: bool = False            # optional swap rule (off = Steere's sheet)
    plies: int = 0               # completed turns, for swap eligibility


class HexagonalY(Game):
    name = "Hexagonal Y"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ core

    def initial_state(self, options=None, rng=None) -> HexYState:
        o = options or {}
        size = int(o.get("size", 7))
        if size not in SIZES:
            raise ValueError(f"unsupported board size {size!r}")
        spec_for(size)
        pie = o.get("pie", False)
        if isinstance(pie, str):
            pie = pie.lower() == "true"
        return HexYState(size=size, pie=bool(pie))

    def current_player(self, s: HexYState) -> int:
        return s.to_move

    def legal_moves(self, s: HexYState) -> list[str]:
        if s.winner is not None:
            return []
        sp = spec_for(s.size)
        moves = [f"{q},{r}" for (q, r) in sp.cells if (q, r) not in s.stones]
        if s.pie and s.plies == 1:
            moves.append("swap")
        return moves

    def apply_move(self, s: HexYState, move: str, rng=None) -> HexYState:
        if s.winner is not None:
            raise ValueError("the game is over")
        sp = spec_for(s.size)
        seat = s.to_move

        if move == "swap":
            if not (s.pie and s.plies == 1):
                raise ValueError("swap is not available")
            stones = {c: seat for c in s.stones}
            last = tuple(sorted(stones))
            # Cannot actually win (the opening is one stone, or an antipodal
            # pair that is never adjacent on a board of side >= 3) — but the
            # check costs nothing and keeps the branch honest.
            winner = seat if self._winning_arc(sp, stones, seat, last) else None
            return HexYState(size=s.size, stones=stones, to_move=1 - seat,
                             winner=winner, last=last,
                             pie=s.pie, plies=s.plies + 1)

        cell = _cell(move)
        if cell not in sp.cellset:
            raise ValueError(f"{move} is not a cell of this board")
        if cell in s.stones:
            raise ValueError(f"{move} is already occupied")

        stones = dict(s.stones)
        stones[cell] = seat
        placed = [cell]
        if hex_dist(*cell) == sp.size - 1:
            opp = antipode(cell)
            # Unreachable from a real game (a perimeter cell and its antipode
            # are always both empty or both filled) — but never overwrite.
            if opp not in stones:
                stones[opp] = seat
                placed.append(opp)

        winner = seat if self._winning_arc(sp, stones, seat, placed) else None
        return HexYState(size=s.size, stones=stones, to_move=1 - seat,
                         winner=winner, last=tuple(placed), pie=s.pie,
                         plies=s.plies + 1)

    def is_terminal(self, s: HexYState) -> bool:
        return s.winner is not None or not self.legal_moves(s)

    def returns(self, s: HexYState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        # A full board with no winning group is believed impossible (rules.md);
        # a genuine tie is scored as an honest draw rather than a fake win.
        return [0.0, 0.0]

    # ---------------------------------------------------------- win detection

    @staticmethod
    def group_of(stones: dict, cell) -> set:
        """The connected group of like-coloured stones containing `cell`."""
        seat = stones.get(cell)
        if seat is None:
            return set()
        seen = {cell}
        stack = [cell]
        while stack:
            cur = stack.pop()
            for nb in neighbors(*cur):
                if nb not in seen and stones.get(nb) == seat:
                    seen.add(nb)
                    stack.append(nb)
        return seen

    @classmethod
    def group_arc(cls, sp: BoardSpec, stones: dict, cell) -> Optional[tuple]:
        """The shortest covering perimeter arc of the group containing `cell`,
        or ``None`` if that group has fewer than two perimeter stones."""
        group = cls.group_of(stones, cell)
        idxs = [sp.ring_index[c] for c in group if c in sp.ring_index]
        return covering_arc(sp, idxs)

    @classmethod
    def _winning_arc(cls, sp: BoardSpec, stones: dict, seat: int,
                     starts) -> Optional[tuple]:
        """The winning arc of a group of `seat` touched by one of `starts`."""
        seen: set = set()
        for start in starts:
            if stones.get(start) != seat or start in seen:
                continue
            group = cls.group_of(stones, start)
            seen |= group
            arc = covering_arc(sp, [sp.ring_index[c] for c in group
                                    if c in sp.ring_index])
            if arc_wins(sp, arc):
                return arc
        return None

    def winning_group(self, s: HexYState) -> set:
        """Cells of the group that won, for highlighting/inspection."""
        if s.winner is None:
            return set()
        sp = spec_for(s.size)
        for start in s.last:
            if s.stones.get(start) != s.winner:
                continue
            group = self.group_of(s.stones, start)
            arc = covering_arc(sp, [sp.ring_index[c] for c in group
                                    if c in sp.ring_index])
            if arc_wins(sp, arc):
                return group
        return set()

    def winning_arc(self, s: HexYState) -> tuple:
        """Perimeter cells of the shortest covering path of the winning group."""
        if s.winner is None:
            return ()
        sp = spec_for(s.size)
        for start in s.last:
            if s.stones.get(start) != s.winner:
                continue
            arc = self.group_arc(sp, s.stones, start)
            if arc_wins(sp, arc):
                return tuple(sp.ring[i] for i in arc)
        return ()

    def has_won(self, s: HexYState, seat: int) -> bool:
        """Does `seat` currently hold a winning group?  (Board predicate — the
        match result itself lives in ``state.winner``.)"""
        sp = spec_for(s.size)
        seen: set = set()
        for cell, owner in s.stones.items():
            if owner != seat or cell in seen:
                continue
            group = self.group_of(s.stones, cell)
            seen |= group
            arc = covering_arc(sp, [sp.ring_index[c] for c in group
                                    if c in sp.ring_index])
            if arc_wins(sp, arc):
                return True
        return False

    # ------------------------------------------------------------- bot eval

    def _rim_reach(self, sp: BoardSpec, stones: dict, seat: int) -> float:
        """How far round the rim `seat`'s best single group already reaches,
        plus a small credit for rim stones that are not yet joined up.

        One O(cells) pass: flood-fill every group once, take the longest
        covering arc (the quantity the win condition is measured in), and add
        1/6 of a cell per owned rim cell as a tie-break so that grabbing rim
        pairs early still registers.  A group needs an arc of more than half
        the rim to win, so a longer arc is strictly closer to winning.
        """
        seen: set = set()
        best = 0
        rim = 0
        for cell, owner in stones.items():
            if owner != seat:
                continue
            if cell in sp.ring_index:
                rim += 1
            if cell in seen:
                continue
            group = self.group_of(stones, cell)
            seen |= group
            arc = covering_arc(sp, [c for c in
                                    (sp.ring_index.get(x) for x in group)
                                    if c is not None])
            if arc is not None and len(arc) > best:
                best = len(arc)
        return best + rim / 6.0

    def heuristic(self, s: HexYState) -> list[float]:
        """Positive for seat 0.  Returns a LIST of `num_players` payoffs, the
        same convention as ``returns`` — MCTS indexes it per player."""
        if s.winner is not None:
            return self.returns(s)
        sp = spec_for(s.size)
        a = self._rim_reach(sp, s.stones, 0)
        b = self._rim_reach(sp, s.stones, 1)
        v = math.tanh(6.0 * (a - b) / sp.perimeter)
        return [v, -v]

    # ----------------------------------------------------------- (de)serialize

    def serialize(self, s: HexYState) -> dict:
        return {
            "size": s.size,
            "stones": {f"{q},{r}": p for (q, r), p in s.stones.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "last": [f"{q},{r}" for (q, r) in s.last],
            "pie": s.pie,
            "plies": s.plies,
        }

    def deserialize(self, d: dict) -> HexYState:
        return HexYState(
            size=int(d["size"]),
            stones={_cell(k): int(v) for k, v in d["stones"].items()},
            to_move=int(d["to_move"]),
            winner=None if d["winner"] is None else int(d["winner"]),
            last=tuple(_cell(c) for c in d["last"]),
            pie=bool(d["pie"]),
            plies=int(d["plies"]),
        )

    # ------------------------------------------------------------------- UI

    def describe_move(self, s: HexYState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        try:
            cell = _cell(move)
            name = cell_name(s.size, cell)
            if hex_dist(*cell) == s.size - 1:
                opp = antipode(cell)
                if opp not in s.stones:
                    return f"{name}+{cell_name(s.size, opp)}"
            return name
        except Exception:
            return move

    def render(self, s: HexYState, perspective=None) -> dict:
        sp = spec_for(s.size)
        pieces = [{"cell": f"{q},{r}", "owner": p} for (q, r), p in s.stones.items()]
        tints = {f"{q},{r}": "#463c2b" for (q, r) in sp.ring}
        highlights = []
        if s.winner is not None:
            for (q, r) in self.winning_arc(s):
                highlights.append({"cell": f"{q},{r}", "kind": "goal"})
            caption = (f"{SEAT_NAMES[s.winner]} wins — the marked arc is more "
                       f"than half the perimeter")
        else:
            for (q, r) in s.last:
                highlights.append({"cell": f"{q},{r}", "kind": "last-move"})
            if not self.legal_moves(s):
                caption = "Board full — draw"
            else:
                caption = (f"{SEAT_NAMES[s.to_move]} to move — a placement on "
                           f"the ring also fills the opposite ring cell")
        return {
            "board": {
                "type": "hex",
                "shape": "hexagon",
                "size": s.size,
                "tints": tints,
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
