"""Side Stitch, by Craig Duncan, 2017 (BGG 223388).

A two-player connection/scoring game on a hexhex-8 board (hexagon of hexagonal
cells, side length 8 = 169 cells) whose perimeter (the 42 cells at radius 7) is
divided into seven coloured "sides" (colour-sides). It is the parent of Duncan's
Exo-Hex (2019): instead of owned stones sitting outside the board, the board's
own edge is painted in seven colours, and a group scores the number of distinct
colour-sides it touches.

PLAY.  Black (seat 0) moves first. On a turn, place one stone of your colour on
any empty cell (the whole 169-cell board is playable), or pass. Stones never
move and are never removed. Pie rule: on the second player's first turn they may
"swap" (take over the opener's stone as their own colour) instead of placing.
The game ends when both players pass in succession, or when the board is full.

SCORING.  A player's stones form connected groups under hex adjacency. Each
group's value is the number of DISTINCT colour-sides it TOUCHES: a group touches
a colour-side if any of its stones sits on a perimeter cell adjacent to that
side. Seven perimeter cells are BOUNDARY cells that lie where two colour-sides
meet — such a cell counts as touching BOTH of its colours. The owner of the
single highest-valued group wins; ties recurse (set the tied best groups aside
and compare the next-best, i.e. compare the two players' descending value lists
lexicographically, missing entries counting 0). The designer states a tie "all
the way down" is impossible on a played-out board, but a genuine tie IS reachable
via an early symmetric double pass (e.g. an immediate double pass on the empty
board), and such a total tie is scored as a DRAW (winner None), never a
fabricated tiebreak.

Coordinates are axial (q, r); cells satisfy max(|q|,|r|,|q+r|) <= 7. Move strings
are "q,r"; "swap" and "pass" are the two non-cell actions.

Sources: designer's rules in the BGG description (objectid 223388); Eric
Silverman, "Connection Games V: Side Stitch"
(https://drericsilverman.com/2020/03/12/connection-games-v-side-stitch/). The
per-cell colour map was extracted from Duncan's reference board image.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # seat 0 = Black, places first

SIDE = 8              # hexhex side length; interior radius = SIDE - 1 = 7
RAD = SIDE - 1        # 7

_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

# Hex colour of each of the seven colour-sides (for rendering only).
SIDE_COLORS = {
    "orange": "#F29200",
    "yellow": "#FFF200",
    "green": "#22B14C",
    "blue": "#0020F0",
    "purple": "#A300E8",
    "pink": "#FF80C8",
    "red": "#ED1C24",
}

# The 42 perimeter cells (radius 7) partitioned into 7 colour-sides. 35 cells
# touch a single side; the 7 BOUNDARY cells (where two sides meet) touch both.
# Extracted verbatim from Duncan's reference board image (each of the 7 colours
# is touched by exactly 7 cells). A group's value = number of distinct sides its
# stones touch.
PERIM_COLORS = {
    (-1, -6): frozenset({"orange", "red"}),
    (-1, 7): frozenset({"blue"}),
    (-2, -5): frozenset({"red"}),
    (-2, 7): frozenset({"blue", "purple"}),
    (-3, -4): frozenset({"red"}),
    (-3, 7): frozenset({"purple"}),
    (-4, -3): frozenset({"red"}),
    (-4, 7): frozenset({"purple"}),
    (-5, -2): frozenset({"red"}),
    (-5, 7): frozenset({"purple"}),
    (-6, -1): frozenset({"red"}),
    (-6, 7): frozenset({"purple"}),
    (-7, 0): frozenset({"pink", "red"}),
    (-7, 1): frozenset({"pink"}),
    (-7, 2): frozenset({"pink"}),
    (-7, 3): frozenset({"pink"}),
    (-7, 4): frozenset({"pink"}),
    (-7, 5): frozenset({"pink"}),
    (-7, 6): frozenset({"pink", "purple"}),
    (-7, 7): frozenset({"purple"}),
    (0, -7): frozenset({"orange"}),
    (0, 7): frozenset({"blue"}),
    (1, -7): frozenset({"orange"}),
    (1, 6): frozenset({"blue"}),
    (2, -7): frozenset({"orange"}),
    (2, 5): frozenset({"blue"}),
    (3, -7): frozenset({"orange"}),
    (3, 4): frozenset({"blue"}),
    (4, -7): frozenset({"orange"}),
    (4, 3): frozenset({"blue", "green"}),
    (5, -7): frozenset({"orange", "yellow"}),
    (5, 2): frozenset({"green"}),
    (6, -7): frozenset({"yellow"}),
    (6, 1): frozenset({"green"}),
    (7, -1): frozenset({"green"}),
    (7, -2): frozenset({"green"}),
    (7, -3): frozenset({"green", "yellow"}),
    (7, -4): frozenset({"yellow"}),
    (7, -5): frozenset({"yellow"}),
    (7, -6): frozenset({"yellow"}),
    (7, -7): frozenset({"yellow"}),
    (7, 0): frozenset({"green"}),
}


def _radius(q: int, r: int) -> int:
    return max(abs(q), abs(r), abs(q + r))


@lru_cache(maxsize=None)
def _cells() -> tuple:
    """All 169 playable cells of the hexhex-8 board: radius <= 7."""
    out = [
        (q, r)
        for q in range(-RAD, RAD + 1)
        for r in range(-RAD, RAD + 1)
        if _radius(q, r) <= RAD
    ]
    return tuple(sorted(out))


@lru_cache(maxsize=None)
def _cell_set() -> frozenset:
    return frozenset(_cells())


def _cell(t: str) -> tuple[int, int]:
    q, r = t.split(",")
    return int(q), int(r)


def _groups(board: dict, player: int) -> list[set]:
    """Connected components of ``player``'s stones under plain hex adjacency."""
    owned = {c for c, p in board.items() if p == player}
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


def _group_value(group: set) -> int:
    """Number of distinct colour-sides a group touches (boundary cells count for
    both of their sides)."""
    touched: set = set()
    for c in group:
        cs = PERIM_COLORS.get(c)
        if cs:
            touched |= cs
    return len(touched)


def _score_list(board: dict, player: int) -> list[int]:
    """The player's group values (distinct colour-sides touched), sorted
    descending. Groups touching no side score 0 and are dropped (0 compares the
    same as a missing entry)."""
    scores = [_group_value(g) for g in _groups(board, player)]
    return sorted((x for x in scores if x > 0), reverse=True)


def _compare(a: list[int], b: list[int]) -> int:
    """Recursive-tiebreak comparison: best group, then next-best, etc. Missing
    entries count 0. Returns +1 if a wins, -1 if b wins, 0 on a full tie."""
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x != y:
            return 1 if x > y else -1
    return 0


@dataclass
class SideStitchState:
    board: dict = field(default_factory=dict)   # (q, r) -> 0/1
    to_move: int = BLACK
    passes: int = 0                             # consecutive passes
    ply: int = 0
    last: Optional[tuple] = None
    winner: Optional[int] = None
    over: bool = False
    pie: bool = True


class SideStitch(Game):
    name = "Side Stitch"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SideStitchState:
        opts = options or {}
        pie = str(opts.get("pie", True)).lower() != "false"
        return SideStitchState(pie=pie)

    def current_player(self, s: SideStitchState) -> int:
        return s.to_move

    def legal_moves(self, s: SideStitchState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = [f"{q},{r}" for (q, r) in _cells() if (q, r) not in s.board]
        if s.pie and s.ply == 1 and len(s.board) == 1:
            moves.append("swap")
        moves.append("pass")
        return moves

    def apply_move(self, s: SideStitchState, move: str, rng=None) -> SideStitchState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move

        if move == "swap":
            if not (s.pie and s.ply == 1 and len(s.board) == 1):
                raise ValueError("swap not available")
            (cell, _), = list(s.board.items())
            return SideStitchState(
                board={cell: mover}, to_move=1 - mover, passes=0,
                ply=s.ply + 1, last=cell, pie=s.pie,
            )

        if move == "pass":
            ns = SideStitchState(
                board=dict(s.board), to_move=1 - mover,
                passes=s.passes + 1, ply=s.ply + 1, last=None, pie=s.pie,
            )
            self._maybe_finish(ns, force=(ns.passes >= 2))
            return ns

        cell = _cell(move)
        if cell not in _cell_set() or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        board[cell] = mover
        ns = SideStitchState(
            board=board, to_move=1 - mover, passes=0,
            ply=s.ply + 1, last=cell, pie=s.pie,
        )
        # A full board also ends the game.
        self._maybe_finish(ns, force=(len(board) >= len(_cells())))
        return ns

    def _maybe_finish(self, ns: SideStitchState, force: bool = False):
        if not force:
            return
        cmp = _compare(_score_list(ns.board, BLACK),
                       _score_list(ns.board, WHITE))
        # Recursive tiebreak. A played-out board is decisive, but an early
        # double pass in a symmetric position CAN tie all the way down; a genuine
        # total tie is a DRAW (winner None) — documented in rules.md.
        ns.winner = BLACK if cmp > 0 else (WHITE if cmp < 0 else None)
        ns.over = True

    def is_terminal(self, s: SideStitchState) -> bool:
        return s.over

    def returns(self, s: SideStitchState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: SideStitchState) -> list[float]:
        """Rollout-cutoff eval: depth-weighted difference of the two players'
        descending group-value lists, squashed to (-1, 1). Positive = Black."""
        a = _score_list(s.board, BLACK)
        b = _score_list(s.board, WHITE)
        diff = 0.0
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else 0
            y = b[i] if i < len(b) else 0
            diff += (x - y) * (0.5 ** i)
        v = math.tanh(diff / 4.0)
        return [v, -v]

    def serialize(self, s: SideStitchState) -> dict:
        return {
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "passes": s.passes,
            "ply": s.ply,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "winner": s.winner,
            "over": s.over,
            "pie": s.pie,
        }

    def deserialize(self, d: dict) -> SideStitchState:
        last = d.get("last")
        return SideStitchState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            passes=d.get("passes", 0),
            ply=d.get("ply", len(d["board"])),
            last=(_cell(last) if last else None),
            winner=d.get("winner"),
            over=d.get("over", False),
            pie=d.get("pie", True),
        )

    def describe_move(self, s: SideStitchState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        return move

    def render(self, s: SideStitchState, perspective=None) -> dict:
        tints = {}
        for (q, r), cs in PERIM_COLORS.items():
            # A boundary cell has two colours; a single tint is fine (scoring
            # still uses both). Pick a stable one for the fill.
            name = sorted(cs)[0]
            tints[f"{q},{r}"] = SIDE_COLORS[name]

        pieces = [
            {"cell": f"{q},{r}", "owner": p, "label": ""}
            for (q, r), p in s.board.items()
        ]

        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})

        names = {BLACK: "Black", WHITE: "White"}
        bl = _score_list(s.board, BLACK)
        wh = _score_list(s.board, WHITE)

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
            "board": {"type": "hex", "shape": "hexagon", "size": SIDE,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
