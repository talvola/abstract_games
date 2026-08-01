"""Churn — Mark Steere, December 2024.

A hexagonal board of hexagonal cells ("hexhex"), initially empty.  Red and Blue
alternately place one stone of their own colour on an empty cell, Red first, and
the game uses the **pie rule**.  A *group* is a monocoloured connected set of at
least one stone.

**Placement (mandatory, in strict priority order)** — rule sheet, PLAY:

    "If you can place a stone in isolation (not adjacent to any friendly
     groups), you must do so.  If you can only place adjacent to a friendly
     group, you must select a placement that forms the smallest friendly group
     possible."

so the legal set is:

  * every empty cell with **no friendly neighbour**, if there is one;
  * otherwise every empty cell minimising the size of the group the placement
    **would form** — i.e. ``1 + (total size of all friendly groups the cell
    touches)``, counting the new stone and every group the placement merges.

Enemy stones are irrelevant to legality.  **Figure 1 settles the isolation
branch** (its three green cells are exactly the cells with no red neighbour, and
ALL THREE touch blue stones, so "adjacent to any group" is not the reading).
**Figure 2 settles the minimisation**: its four empty cells form groups of sizes
3, 3, 5 and 6 after the placement, and exactly the two 3s are printed green —
which kills "minimise the smallest adjacent group" (that would pick a different
pair), "minimise the largest adjacent group" and "minimise the number of groups
merged" (each would print a single cell).  See ``rules.md``.

**Removals** — rule sheet, REMOVALS:

    "Having placed adjacent to a friendly group, thereby forming a larger group,
     you must immediately remove all friendly groups smaller than the group so
     formed, concluding your turn."

Strictly smaller: **Figure 3 settles ``<`` versus ``<=``** — the placement forms
a group of 3, another red group of exactly 3 is on the board, and it is *not*
dotted for removal (only the red 2-group and the red singleton are).  The new
group is never removed (it is not smaller than itself).

**Object** — rule sheet, OBJECT OF THE GAME:

    "Once the board has filled, at the conclusion of a turn, the player having
     the majority of on-board stones wins.  (If your placement causes the board
     to be filled, you still have to finish your turn by removing all friendly
     groups smaller than your newly formed group.)"

The check is at the CONCLUSION of the turn, *after* the removals, and **Figure 4
proves it**: Red's placement fills the board 10-9 in Red's favour, but the
mandatory removal of Red's singleton leaves 9-9 with one hole, so nobody has won;
Blue's forced reply into that hole forms a blue 5-group, removes nothing (Blue's
other group is also 5), fills the board and wins it 10-9.  "Figure 4 is a win for
Blue" is only true under this ordering.  Counting before the removals would make
it a win for RED.

Every state in this module is at a turn boundary, so ``is_terminal`` is simply
"the board is full" and the result is read off the board — nothing is cached.

**Termination — proved, so this game ships with NO ply cap and NO repetition
rule.**  Take the multiset of the mover's OWN group sizes, sorted descending, and
order such vectors lexicographically (a proper prefix is smaller than its
extension).  A player's stones are never touched by the opponent, so this vector
changes only on that player's own turns, and on every one of them it strictly
increases:

  * *isolated placement* — the vector gains one extra ``1`` at its very end,
    which is a proper prefix-extension, hence larger;
  * *adjacent placement* — let ``s`` be the size of the group formed.  Every
    group that was merged had size ``< s``, and at least one group WAS merged, so
    the old vector is ``A ++ rest`` with ``A`` = the groups of size ``>= s`` and
    ``rest`` non-empty with ``rest[0] < s``; the new vector is ``A ++ [s]``
    (the removals delete exactly the groups smaller than ``s``).  Common prefix
    ``A``, then ``s > rest[0]``, hence larger.

The vectors are partitions of integers in ``0 .. len(cells)``, a finite totally
ordered set, so each player makes at most ``sum(p(k) for k in 0..N) - 1`` turns.
With the single pie-swap ply (which places no stone and is available once) that
gives ``max_plies()`` below — derived from the board's own cell count, never
pinned.  In practice random play finishes far sooner: measured means are 8.1
turns on side 2, 69.9 on side 3 and 203.7 on the limping 27-cell board.

Coordinates are axial ``"q,r"``; the boards are drawn pointy-top (rows
horizontal), exactly as the rule sheet's figures draw them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SEAT_NAMES = ("Red", "Blue")

# Axial neighbour offsets.  Pointy-top: E, NE, NW, W, SW, SE — a *row* (constant
# r) is horizontal, which is how the rule sheet draws the board.
DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


# --------------------------------------------------------------------------
#  Boards
# --------------------------------------------------------------------------
#
# "Churn is a two-player game played on a hexagonal board of any size ...
#  Size 3 (side length 3) is recommended", plus "Irregular hexagonal boards can
# be used, such as one having side lengths 3,4,3,4,3,4 (27 cells).  Only boards
# with an odd number of cells should be used, to prevent ties."
#
# A hexagon with sides (a, b, a, b, a, b) is the axial region
#     -A <= q <= B,  -C <= r <= D,  -E <= q + r <= F
# The regular hexhex of side n is A=B=C=D=E=F=n-1 and has 3n^2-3n+1 cells, which
# is ALWAYS odd (3n(n-1) is a product of consecutive integers, hence even).  The
# limping 3,4 board below has 27 cells — also odd.  So no shipped board can tie.
#
# Only the SHORT boards are shipped.  Churn is deliberately slow ("designed to
# have an extreme churn rate"), and measured random-play means are 8.1 turns on
# side 2, 69.9 on side 3, 203.7 on the limping 27, 657.7 on side 4 and 7,385 on
# side 5 (the designer's own figure for side 5 is "about 7,400").  Sides 4 and up
# are not playable as an async match; see rules.md for the full table.
BOARD_PARAMS = {
    # key:        (A, B, C, D, E, F)
    "hex2":       (1, 1, 1, 1, 1, 1),   # regular hexhex, side 2 —  7 cells
    "hex3":       (2, 2, 2, 2, 2, 2),   # regular hexhex, side 3 — 19 cells
    "limping34":  (2, 3, 3, 2, 2, 3),   # sides 3,4,3,4,3,4      — 27 cells
}
BOARD_KEYS = tuple(BOARD_PARAMS)
DEFAULT_BOARD = "hex3"
# The regular hexhex boards also declare a `size`, which lets render() use the
# compact {"shape": "hexagon", "size": n} board spec Board.jsx already knows.
HEXHEX_SIDE = {"hex2": 2, "hex3": 3}


@dataclass(frozen=True)
class BoardSpec:
    key: str
    cells: tuple          # every cell, deterministic (sorted) order
    cellset: frozenset
    nbrs: dict            # cell -> tuple of on-board neighbours
    rows: tuple           # (r, q_min, width) top row first
    side: Optional[int]   # side length if a regular hexhex, else None


_SPECS: dict = {}


def _build(key: str) -> BoardSpec:
    A, B, C, D, E, F = BOARD_PARAMS[key]
    cells = tuple(sorted(
        (q, r)
        for q in range(-A, B + 1)
        for r in range(-C, D + 1)
        if -E <= q + r <= F
    ))
    cellset = frozenset(cells)
    nbrs = {c: tuple(nb for nb in
                     ((c[0] + dq, c[1] + dr) for dq, dr in DIRS)
                     if nb in cellset)
            for c in cells}
    rows = []
    for r in range(-C, D + 1):
        qs = [q for (q, rr) in cells if rr == r]
        if qs:
            rows.append((r, min(qs), len(qs)))
    return BoardSpec(key=key, cells=cells, cellset=cellset, nbrs=nbrs,
                     rows=tuple(rows), side=HEXHEX_SIDE.get(key))


def spec_for(key: str) -> BoardSpec:
    sp = _SPECS.get(key)
    if sp is None:
        if key not in BOARD_PARAMS:
            raise ValueError(f"unsupported Churn board {key!r}")
        sp = _SPECS[key] = _build(key)
    return sp


def cell_name(sp: BoardSpec, cell) -> str:
    """Algebraic name: row letter counted UP from the bottom row, then the
    1-based index of the cell within its row from the left.  ``a1`` is the
    bottom-left cell — the same notation AbstractPlay uses for these boards."""
    q, r = cell
    r_max = sp.rows[-1][0]
    for rr, q_min, _w in sp.rows:
        if rr == r:
            return f"{chr(ord('a') + r_max - r)}{q - q_min + 1}"
    raise ValueError(f"{cell!r} is not on this board")


def _partition_counts(n: int) -> int:
    """sum(p(k) for k in 0..n) — the number of distinct sorted-descending group
    vectors a player can ever hold on a board of n cells."""
    p = [0] * (n + 1)
    p[0] = 1
    for k in range(1, n + 1):
        for total in range(k, n + 1):
            p[total] += p[total - k]
    return sum(p)


def max_plies(key: str) -> int:
    """A rigorous upper bound on the length of a game, derived from the board.

    Each player's sorted-descending group-size vector strictly increases on each
    of that player's own turns (see the module docstring) and lives in the finite
    totally ordered set of partitions of 0..N, so each player has at most
    ``_partition_counts(N) - 1`` turns.  The pie swap is ONE extra ply that
    places no stone.  Nothing here is a pinned constant."""
    n = len(spec_for(key).cells)
    return 2 * (_partition_counts(n) - 1) + 1


# --------------------------------------------------------------------------
#  Groups
# --------------------------------------------------------------------------

def label_groups(sp: BoardSpec, stones: dict, seat: int):
    """One flood-fill pass: (cell -> group id, [group size, ...])."""
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


def group_of(sp: BoardSpec, stones: dict, cell) -> set:
    """The connected like-coloured group containing `cell` (empty if empty)."""
    seat = stones.get(cell)
    if seat is None:
        return set()
    seen = {cell}
    stack = [cell]
    while stack:
        cur = stack.pop()
        for nb in sp.nbrs[cur]:
            if nb not in seen and stones.get(nb) == seat:
                seen.add(nb)
                stack.append(nb)
    return seen


@dataclass
class ChurnState:
    board: str = DEFAULT_BOARD
    stones: dict = field(default_factory=dict)     # (q, r) -> seat
    to_move: int = 0
    ply: int = 0                                   # completed plies
    swapped: bool = False                          # was the pie exercised?
    last: Optional[tuple] = None                   # the cell just played
    removed: tuple = ()                            # cells cleared by that turn


class Churn(Game):
    name = "Churn"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ core

    def initial_state(self, options=None, rng=None) -> ChurnState:
        o = options or {}
        key = str(o.get("board", DEFAULT_BOARD))
        if key not in BOARD_PARAMS:
            raise ValueError(f"unsupported Churn board {key!r}")
        spec_for(key)
        return ChurnState(board=key)

    def current_player(self, s: ChurnState) -> int:
        return s.to_move

    # ------------------------------------------------------------ placements

    def placement_sizes(self, s: ChurnState, seat: Optional[int] = None) -> dict:
        """``empty cell -> size of the friendly group placing there would form``
        (1 + the total size of every friendly group the cell touches, so a cell
        that merges three groups of 2 maps to 7).  Diagnostic + move-gen core."""
        if seat is None:
            seat = s.to_move
        sp = spec_for(s.board)
        lab, sizes = label_groups(sp, s.stones, seat)
        out = {}
        for c in sp.cells:
            if c in s.stones:
                continue
            adj = set()
            for nb in sp.nbrs[c]:
                gid = lab.get(nb)
                if gid is not None:
                    adj.add(gid)
            out[c] = 1 + sum(sizes[g] for g in adj)
        return out

    def placements(self, s: ChurnState, seat: Optional[int] = None) -> list:
        """Every cell `seat` (default: the player to move) may legally occupy,
        as (q, r) tuples in board order.

        PLAY, in priority order: an isolated placement (resulting group size 1)
        if one exists, otherwise every placement minimising the resulting group
        size.  Both branches are "minimise the resulting size" — 1 is the
        smallest achievable value — but they are kept explicit because the sheet
        states them as two clauses and Figure 1 pins the first.
        """
        sizes = self.placement_sizes(s, seat)
        if not sizes:
            return []
        iso = [c for c, n in sizes.items() if n == 1]
        if iso:
            return sorted(iso)
        best = min(sizes.values())
        return sorted(c for c, n in sizes.items() if n == best)

    def legal_moves(self, s: ChurnState) -> list:
        if self.is_terminal(s):
            return []
        moves = [f"{q},{r}" for (q, r) in self.placements(s)]
        # Pie rule: the second player, on their first turn only, may instead
        # adopt the opening stone as their own and hand the move back.
        if s.ply == 1 and not s.swapped and len(s.stones) == 1:
            moves.append("swap")
        return moves

    # ------------------------------------------------------------ move application

    def _removals(self, sp: BoardSpec, stones: dict, seat: int, cell) -> list:
        """The mover's stones that must come off after placing on `cell`:
        every friendly group STRICTLY smaller than the group just formed."""
        lab, sizes = label_groups(sp, stones, seat)
        new_size = sizes[lab[cell]]
        return sorted(c for c, gid in lab.items() if sizes[gid] < new_size)

    def apply_move(self, s: ChurnState, move: str, rng=None) -> ChurnState:
        if self.is_terminal(s):
            raise ValueError("the game is over")
        sp = spec_for(s.board)

        if move == "swap":
            if not (s.ply == 1 and not s.swapped and len(s.stones) == 1):
                raise ValueError("the pie swap is only available to the second "
                                 "player, on their first turn")
            # The swapper adopts the opening stone as their own and passes the
            # move back.  Churn is fully symmetric under exchanging the colours
            # (both players want the majority of THEIR OWN stones and the rules
            # are identical), so recolouring in place is exactly value
            # preserving — no reflection is needed.  Seat 0 stays "Red" and
            # seat 1 stays "Blue" throughout; after a swap the board simply
            # holds Blue's opening stone with Red to move.
            (cell, _owner), = s.stones.items()
            return ChurnState(board=s.board, stones={cell: s.to_move},
                              to_move=1 - s.to_move, ply=s.ply + 1,
                              swapped=True, last=cell, removed=())

        cell = _cell(move)
        if cell not in sp.cellset:
            raise ValueError(f"{move} is not a cell of this board")
        if cell in s.stones:
            raise ValueError(f"{move} is already occupied")
        seat = s.to_move
        if cell not in set(self.placements(s)):
            raise ValueError(
                f"{move} is not a legal placement for {SEAT_NAMES[seat]} "
                f"(isolation first, then the smallest group possible)")

        stones = dict(s.stones)
        stones[cell] = seat
        dead = self._removals(sp, stones, seat, cell)
        for c in dead:
            del stones[c]
        return ChurnState(board=s.board, stones=stones, to_move=1 - seat,
                          ply=s.ply + 1, swapped=s.swapped, last=cell,
                          removed=tuple(dead))

    # -------------------------------------------------------- terminal / score

    def is_terminal(self, s: ChurnState) -> bool:
        """"Once the board has filled, at the conclusion of a turn ..." — every
        state here IS a turn conclusion (apply_move performs the removals before
        returning), so a full board is exactly a finished game."""
        return len(s.stones) == len(spec_for(s.board).cells)

    def counts(self, s: ChurnState) -> tuple:
        a = sum(1 for v in s.stones.values() if v == 0)
        return a, len(s.stones) - a

    def winner(self, s: ChurnState) -> Optional[int]:
        if not self.is_terminal(s):
            return None
        a, b = self.counts(s)
        if a == b:
            return None          # honest draw; unreachable on an odd board
        return 0 if a > b else 1

    def returns(self, s: ChurnState) -> list:
        w = self.winner(s)
        if w is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    # ----------------------------------------------------------- (de)serialize

    def serialize(self, s: ChurnState) -> dict:
        return {
            "board": s.board,
            "stones": {f"{q},{r}": p for (q, r), p in s.stones.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "swapped": s.swapped,
            "last": None if s.last is None else f"{s.last[0]},{s.last[1]}",
            "removed": [f"{q},{r}" for (q, r) in s.removed],
        }

    def deserialize(self, d: dict) -> ChurnState:
        return ChurnState(
            board=str(d["board"]),
            stones={_cell(k): int(v) for k, v in d["stones"].items()},
            to_move=int(d["to_move"]),
            ply=int(d["ply"]),
            swapped=bool(d["swapped"]),
            last=None if d.get("last") is None else _cell(d["last"]),
            removed=tuple(_cell(x) for x in d.get("removed", ())),
        )

    # ------------------------------------------------------------------- UI

    def describe_move(self, s: ChurnState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        try:
            sp = spec_for(s.board)
            cell = _cell(move)
            name = cell_name(sp, cell)
            stones = dict(s.stones)
            stones[cell] = s.to_move
            n = len(self._removals(sp, stones, s.to_move, cell))
            return f"{name} -{n}" if n else name
        except Exception:
            return move

    def render(self, s: ChurnState, perspective=None) -> dict:
        sp = spec_for(s.board)
        pieces = [{"cell": f"{q},{r}", "owner": p}
                  for (q, r), p in s.stones.items()]
        highlights = []
        if s.last is not None and s.last in s.stones:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}",
                               "kind": "last-move"})
        red, blue = self.counts(s)
        score = f"Red {red}, Blue {blue}"
        if self.is_terminal(s):
            w = self.winner(s)
            caption = (f"Draw — {score} on a full board" if w is None
                       else f"{SEAT_NAMES[w]} wins — {score}")
        else:
            caption = f"{SEAT_NAMES[s.to_move]} to move ({score})"
            if s.removed:
                caption += f" — {len(s.removed)} removed"
            if s.ply == 1 and not s.swapped and len(s.stones) == 1:
                caption += " — or swap (pie rule)"
        if sp.side is not None:
            board = {"type": "hex", "shape": "hexagon", "size": sp.side}
        else:
            board = {"type": "hex",
                     "cells": [f"{q},{r}" for (q, r) in sp.cells]}
        return {
            "board": board,
            "pieces": pieces,
            "highlights": highlights,
            "actionNames": {"swap": "Swap colours (pie rule)"},
            "caption": caption,
        }
