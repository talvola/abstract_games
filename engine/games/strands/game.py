"""Strands, by Nick Bentley (2022).

A largest-group placement game on a pre-numbered hexhex board.

RULES (as implemented — verified against the authoritative sources; see
rules.md for the full write-up and the noted source conflict):

  * The board is a hexagon of N cells per side (N = 5, 6 or 7). Every cell is
    pre-labelled with a number 1..6. The centre is a single "1"; the numbers
    grow outward, with the six geometric corners the highest ("6"). The exact
    fixed layouts are AbstractPlay's `size-{5,6,7}-fixed` boards (the same
    boards igGameCenter / Board Game Arena serve). Default N = 6 (91 cells),
    the "six cells per side" board igGameCenter calls canonical.

  * Black (seat 0) opens by covering exactly ONE cell marked "2".

  * From then on, starting with White (seat 1), players alternate. On your
    turn you pick a number X (by covering any empty cell marked X) and then
    cover UP TO X empty cells all marked X (you may cover as few as one; if
    fewer than X empty "X" cells remain you simply cover what is left). Every
    covered cell holds one of your stones.

  * The game ends when the board is FULL (every cell covered — it always
    fills, so termination is automatic; no captures ever remove a stone).

  * Winner = the player whose single LARGEST connected group of stones (hex
    6-adjacency) is bigger. If the two largest groups tie, whoever has MORE
    groups of that size wins; failing that, compare the second-largest groups,
    and so on. If the two players' full sorted lists of group sizes are
    identical, the game is an honest DRAW (winner = None / returns [0, 0]).

TURN ENCODING (multi-move pattern, the platform's sanctioned way to model a
several-placement turn — Blooms/Oust do the same): a turn is a sequence of
single-cell placements by the same player. Each sub-move is a cell id "q,r".
The first placement of a turn commits its number X; subsequent placements
must be on empty "X" cells and are offered in ascending cell order (so each
final set is reached exactly once, never a permutation blow-up). While a turn
is under way and more X cells could still be covered, the player may also play
"done" to stop early (the "up to X" rule). The turn ends automatically once X
cells are covered or no empty X cells remain. The opening covers exactly one
"2" and ends immediately. (This avoids enumerating whole-turn subsets, which
for a fresh 24-cell ring of "4"s would be ~13k moves per turn.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game


# --- Fixed number layouts (AbstractPlay size-{5,6,7}-fixed, rows top->bottom,
#     spaces stripped). Verified: centre "1", six corner "6"s, symmetric rings. -
FIXED_ROWS = {
    5: ["64446", "433334", "4222224", "43222234", "632212236",
        "43222234", "4222224", "433334", "64446"],
    6: ["644446", "4333334", "43222234", "432222234", "4322222234",
        "63222122236", "4322222234", "432222234", "43222234", "4333334",
        "644446"],
    7: ["6655566", "64333346", "533222335", "5322222235", "53222222235",
        "632222122246", "6432211122346", "642221222236", "53222222235",
        "5322222235", "533222335", "64333346", "6655566"],
}


def _neighbors(q: int, r: int):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1),
            (q + 1, r - 1), (q - 1, r + 1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    """All on-board axial cells of a hexhex of side ``size`` (sorted)."""
    n = size - 1
    out = []
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            if abs(q) <= n and abs(r) <= n and abs(q + r) <= n:
                out.append((q, r))
    return tuple(sorted(out))


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


@lru_cache(maxsize=None)
def _setup(size: int) -> dict:
    """Map (q, r) -> the number printed on that cell, from the fixed grid.

    Row ``ri`` (top->bottom) is the axial line r = ri-(N); the k-th character
    is q = qmin+k, where qmin = max(-N, -N-r). Widths are asserted so a typo in
    a layout string fails loudly rather than silently mis-mapping the board.
    """
    rows = FIXED_ROWS[size]
    n = size - 1
    if len(rows) != 2 * size - 1:
        raise ValueError(f"strands size {size}: expected {2*size-1} rows")
    setup: dict = {}
    for ri, row in enumerate(rows):
        r = ri - n
        qmin = max(-n, -n - r)
        qmax = min(n, n - r)
        if len(row) != qmax - qmin + 1:
            raise ValueError(f"strands size {size} row {ri}: width {len(row)} "
                             f"!= {qmax - qmin + 1}")
        for k, ch in enumerate(row):
            setup[(qmin + k, r)] = int(ch)
    if set(setup) != _cell_set(size):
        raise ValueError(f"strands size {size}: layout != hexhex cell set")
    return setup


def _cell(s: str) -> tuple:
    q, r = s.split(",")
    return int(q), int(r)


def _cid(c: tuple) -> str:
    return f"{c[0]},{c[1]}"


def _group_sizes(board: dict, size: int, player: int) -> list:
    """Sorted-descending sizes of ``player``'s connected stone groups."""
    on = _cell_set(size)
    own = {c for c, o in board.items() if o == player}
    seen: set = set()
    sizes: list = []
    for cell in own:
        if cell in seen:
            continue
        n = 0
        stack = [cell]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            n += 1
            cq, cr = cur
            for nb in _neighbors(cq, cr):
                if nb in on and nb in own and nb not in seen:
                    stack.append(nb)
        sizes.append(n)
    sizes.sort(reverse=True)
    return sizes


def compute_winner(board: dict, size: int) -> Optional[int]:
    """The Strands end-of-game comparison. Returns 0, 1, or None (draw).

    Compare the players' descending group-size lists element by element; the
    first difference decides. If one list is a strict prefix of the other, the
    longer (more groups) wins. Identical lists = honest draw.
    """
    a = _group_sizes(board, size, 0)
    b = _group_sizes(board, size, 1)
    for x, y in zip(a, b):
        if x > y:
            return 0
        if x < y:
            return 1
    if len(a) > len(b):
        return 0
    if len(a) < len(b):
        return 1
    return None


@dataclass
class StrandsState:
    size: int = 6
    board: dict = field(default_factory=dict)     # (q, r) -> owner 0/1
    to_move: int = 0
    turn_cells: list = field(default_factory=list)  # cells placed so far THIS turn
    last: list = field(default_factory=list)        # cells placed on the previous turn
    winner: Optional[int] = None
    over: bool = False


class Strands(Game):
    name = "Strands"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> StrandsState:
        opts = options or {}
        size = int(opts.get("size", 6))
        if size not in FIXED_ROWS:
            size = 6
        _setup(size)  # validate the layout up front
        return StrandsState(size=size)

    def current_player(self, s: StrandsState) -> int:
        return s.to_move

    # -- move generation ---------------------------------------------------

    def legal_moves(self, s: StrandsState) -> list:
        if s.over:
            return []
        setup = _setup(s.size)
        empties = [c for c in _cells(s.size) if c not in s.board]
        opening = (not s.board) and (not s.turn_cells)
        if opening:
            # Black opens on exactly one "2".
            return [_cid(c) for c in empties if setup[c] == 2]
        if not s.turn_cells:
            # Start of a normal turn: covering any empty cell commits its number.
            return [_cid(c) for c in empties]
        # Mid-turn: continue with a higher-sorted empty cell of the same number,
        # or stop early ("up to X").
        num = setup[s.turn_cells[0]]
        last_cell = s.turn_cells[-1]
        cont = [_cid(c) for c in empties if setup[c] == num and c > last_cell]
        return cont + ["done"]

    # -- transition --------------------------------------------------------

    def apply_move(self, s: StrandsState, move: str, rng=None) -> StrandsState:
        if s.over:
            raise ValueError("game over")
        setup = _setup(s.size)

        if move == "done":
            if not s.turn_cells:
                raise ValueError("nothing placed yet this turn")
            return self._end_turn(s, dict(s.board), list(s.turn_cells))

        cell = _cell(move)
        if cell not in _cell_set(s.size):
            raise ValueError(f"off-board {move!r}")
        if cell in s.board:
            raise ValueError(f"occupied {move!r}")

        opening = (not s.board) and (not s.turn_cells)
        if opening:
            if setup[cell] != 2:
                raise ValueError("the opening must cover a cell marked 2")
            board = dict(s.board)
            board[cell] = s.to_move
            return self._end_turn(s, board, [cell])

        if s.turn_cells:
            num = setup[s.turn_cells[0]]
            if setup[cell] != num:
                raise ValueError(f"must keep covering cells marked {num}")
            if cell <= s.turn_cells[-1]:
                raise ValueError("cover cells in ascending order")
        else:
            num = setup[cell]

        board = dict(s.board)
        board[cell] = s.to_move
        placed = s.turn_cells + [cell]

        # May the same player continue? (fewer than X placed AND an empty
        # higher-sorted X cell still remains)
        more = [c for c in _cells(s.size)
                if c not in board and setup[c] == num and c > cell]
        if len(placed) < num and more:
            return StrandsState(size=s.size, board=board, to_move=s.to_move,
                                turn_cells=placed, last=list(s.last))
        # Otherwise the turn ends.
        return self._end_turn(s, board, placed)

    def _end_turn(self, s: StrandsState, board: dict, placed: list) -> StrandsState:
        ns = StrandsState(size=s.size, board=board, to_move=1 - s.to_move,
                          turn_cells=[], last=list(placed))
        if len(board) >= len(_cells(s.size)):
            ns.over = True
            ns.winner = compute_winner(board, s.size)
        return ns

    def is_terminal(self, s: StrandsState) -> bool:
        return s.over

    def returns(self, s: StrandsState) -> list:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: StrandsState) -> list:
        """Largest-group lead, for truncated MCTS rollouts."""
        a = _group_sizes(s.board, s.size, 0)
        b = _group_sizes(s.board, s.size, 1)
        la = a[0] if a else 0
        lb = b[0] if b else 0
        v = math.tanh((la - lb) / 6.0)
        return [v, -v]

    # -- serialization -----------------------------------------------------

    def serialize(self, s: StrandsState) -> dict:
        return {
            "size": s.size,
            "board": {_cid(c): o for c, o in s.board.items()},
            "to_move": s.to_move,
            "turn_cells": [_cid(c) for c in s.turn_cells],
            "last": [_cid(c) for c in s.last],
            "winner": s.winner,
            "over": s.over,
        }

    def deserialize(self, d: dict) -> StrandsState:
        return StrandsState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            turn_cells=[_cell(x) for x in d.get("turn_cells", [])],
            last=[_cell(x) for x in d.get("last", [])],
            winner=d.get("winner"),
            over=d.get("over", False),
        )

    # -- presentation ------------------------------------------------------

    def describe_move(self, s: StrandsState, move: str) -> str:
        if move == "done":
            return "done"
        setup = _setup(s.size)
        cell = _cell(move)
        num = setup.get(cell)
        return f"{num}: {move}" if num is not None else move

    def render(self, s: StrandsState, perspective=None) -> dict:
        setup = _setup(s.size)
        seat_names = {0: "Black", 1: "White"}
        pieces = []
        for c in _cells(s.size):
            if c in s.board:
                pieces.append({"cell": _cid(c), "owner": s.board[c]})
            else:
                # Empty numbered cell = neutral (owner-less) labelled disc.
                pieces.append({
                    "cell": _cid(c), "label": str(setup[c]),
                    "fill": "#e6d8ad", "stroke": "#5f4b23",
                })
        highlights = [{"cell": _cid(c), "kind": "last-move"} for c in s.last]
        highlights += [{"cell": _cid(c), "kind": "last-move"} for c in s.turn_cells]

        a = _group_sizes(s.board, s.size, 0)
        b = _group_sizes(s.board, s.size, 1)
        score = f"largest group  {a[0] if a else 0} : {b[0] if b else 0}"
        if s.over:
            if s.winner is None:
                caption = f"Draw — {score}"
            else:
                caption = f"{seat_names[s.winner]} wins — {score}"
        elif s.turn_cells:
            num = setup[s.turn_cells[0]]
            left = num - len(s.turn_cells)
            caption = (f"{seat_names[s.to_move]}: cover up to {left} more "
                       f"“{num}” or done — {score}")
        elif not s.board:
            caption = f"{seat_names[s.to_move]} opens on a “2” — {score}"
        else:
            caption = f"{seat_names[s.to_move]} to move — {score}"

        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
