"""Catchup (a.k.a. Catch-Up), by Nick Bentley (2010).

A group-building game on a hexagon of hexagons ("hexhex") of side 5 = 61 cells.
Two players alternately place stones of their colour on empty cells; stones
never move and are never captured. The board fills completely and then the
player whose LARGEST connected (same-colour, 6-adjacency) group is biggest
wins, with ties broken by comparing 2nd-largest groups, then 3rd, etc.

The self-balancing CATCH-UP rule governs how many stones a turn places:

  * The very FIRST move of the game places exactly ONE stone.
  * On every later turn a player normally places 1 OR 2 stones.
  * A player MAY place up to 3 stones if, on the OPPONENT's immediately
    preceding turn, the opponent's score INCREASED and is, at the start of
    this player's turn, GREATER THAN OR EQUAL TO this player's score.

(A player's "score" = the number of stones in their current largest group;
both scores start at 1 once a stone of each colour is on the board, and 0
before that.) This is the canonical wording from Nick Bentley / Little Golem:
"you may place 1 or 2 stones, or up to 3 if your opponent's score increased on
their last turn and is, at the beginning of your turn, greater than or equal to
your score." A turn always places the chosen number of stones on DISTINCT empty
cells (fewer only if the board cannot fit more).

Coordinates are axial (q, r); the third cube coordinate is s = -q-r. A cell is
on the board iff max(|q|, |r|, |s|) <= N-1 (N = 5). Adjacency is the 6 hex
neighbours. A turn's placement is encoded as a '>'-separated path of the placed
cell ids (e.g. "0,0>1,-1"); a single-stone turn is just "q,r".

The game always terminates: every turn strictly fills >=1 empty cell, so the
board is full after a bounded number of plies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
from typing import Optional

from agp.game import Game

P0, P1 = 0, 1
BOARD_SIDE = 5  # hexhex side length -> 61 cells


def _neighbors(q: int, r: int):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1), (q + 1, r - 1), (q - 1, r + 1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    """All on-board axial cells of a hexhex of side ``size`` (size = N)."""
    out = []
    n = size - 1
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            s = -q - r
            if abs(q) <= n and abs(r) <= n and abs(s) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


def _group_sizes(board: dict, player: int) -> list[int]:
    """Sizes of all connected same-colour components owned by ``player``,
    sorted descending."""
    seen = set()
    sizes = []
    for cell, p in board.items():
        if p != player or cell in seen:
            continue
        # BFS this component
        comp = {cell}
        stack = [cell]
        while stack:
            cq, cr = stack.pop()
            for nb in _neighbors(cq, cr):
                if nb not in comp and board.get(nb) == player:
                    comp.add(nb)
                    stack.append(nb)
        seen |= comp
        sizes.append(len(comp))
    sizes.sort(reverse=True)
    return sizes


def _score(board: dict, player: int) -> int:
    """A player's score = size of their largest group (0 if no stones)."""
    sizes = _group_sizes(board, player)
    return sizes[0] if sizes else 0


def _compare(sizes_a: list[int], sizes_b: list[int]) -> int:
    """Catchup result comparison: compare largest, then 2nd, etc. Returns
    +1 if a wins, -1 if b wins. (Ties are impossible at game end on a full
    board, but we handle the degenerate equal case by returning 0.)"""
    for x, y in zip(sizes_a, sizes_b):
        if x != y:
            return 1 if x > y else -1
    # one list is a prefix of the other (different group counts)
    if len(sizes_a) != len(sizes_b):
        return 1 if len(sizes_a) > len(sizes_b) else -1
    return 0


@dataclass
class CatchupState:
    size: int = BOARD_SIDE
    board: dict = field(default_factory=dict)   # (q, r) -> 0/1
    to_move: int = P0
    ply: int = 0                                 # number of completed turns
    allow3: bool = False                         # may current player place 3?
    last: tuple = ()                             # last placed cells (this/previous turn)
    winner: Optional[int] = None


class Catchup(Game):
    uid = "catchup"
    name = "Catchup"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CatchupState:
        return CatchupState(size=BOARD_SIDE)

    def current_player(self, s: CatchupState) -> int:
        return s.to_move

    def _max_place(self, s: CatchupState) -> int:
        """How many stones the current player may place this turn (the cap)."""
        if s.ply == 0:
            return 1  # the very first move places exactly one stone
        return 3 if s.allow3 else 2

    def legal_moves(self, s: CatchupState) -> list[str]:
        if self.is_terminal(s):
            return []
        empties = [(q, r) for (q, r) in _cells(s.size) if (q, r) not in s.board]
        cap = self._max_place(s)
        cap = min(cap, len(empties))  # can't place more than fit
        if s.ply == 0:
            counts = [1]
        else:
            counts = list(range(1, cap + 1))  # may place 1..cap
        moves = []
        for k in counts:
            for combo in combinations(empties, k):
                moves.append(">".join(f"{q},{r}" for (q, r) in combo))
        return moves

    def apply_move(self, s: CatchupState, move: str, rng=None) -> CatchupState:
        cells = [_cell(part) for part in move.split(">")]
        if len(cells) != len(set(cells)):
            raise ValueError(f"duplicate cell in move {move!r}")
        cap = self._max_place(s)
        empties = sum(1 for c in _cells(s.size) if c not in s.board)
        allowed_max = min(cap, empties) if s.ply > 0 else 1
        if not (1 <= len(cells) <= allowed_max):
            raise ValueError(f"placed {len(cells)} stones, allowed 1..{allowed_max}")
        on = _cell_set(s.size)
        for c in cells:
            if c not in on or c in s.board:
                raise ValueError(f"illegal placement at {c}")

        mover = s.to_move
        opp = 1 - mover

        # score of the mover BEFORE this turn
        score_before = _score(s.board, mover)

        board = dict(s.board)
        for c in cells:
            board[c] = mover

        # score of the mover AFTER this turn
        score_after = _score(board, mover)
        opp_score = _score(board, opp)

        # Catch-up rule (evaluated for the OPPONENT's upcoming turn):
        # opponent may place up to 3 iff the mover's score INCREASED this turn
        # AND, at the start of the opponent's turn, the mover's score is
        # >= the opponent's score.
        opp_allow3 = (score_after > score_before) and (score_after >= opp_score)

        new_ply = s.ply + 1
        winner = None
        full = len(board) >= len(_cells(s.size))
        if full:
            cmp = _compare(_group_sizes(board, P0), _group_sizes(board, P1))
            winner = P0 if cmp > 0 else (P1 if cmp < 0 else None)

        return CatchupState(
            size=s.size,
            board=board,
            to_move=opp,
            ply=new_ply,
            allow3=opp_allow3,
            last=tuple(cells),
            winner=winner,
        )

    def is_terminal(self, s: CatchupState) -> bool:
        return len(s.board) >= len(_cells(s.size))

    def returns(self, s: CatchupState) -> list[float]:
        if not self.is_terminal(s):
            return [0.0, 0.0]
        cmp = _compare(_group_sizes(s.board, P0), _group_sizes(s.board, P1))
        if cmp > 0:
            return [1.0, -1.0]
        if cmp < 0:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # only the empty-board degenerate case; not reachable

    def serialize(self, s: CatchupState) -> dict:
        return {
            "size": s.size,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "allow3": s.allow3,
            "last": [f"{q},{r}" for (q, r) in s.last],
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> CatchupState:
        return CatchupState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            allow3=d.get("allow3", False),
            last=tuple(_cell(x) for x in d.get("last", [])),
            winner=d.get("winner"),
        )

    def describe_move(self, s: CatchupState, move: str) -> str:
        n = len(move.split(">"))
        return f"{move} ({n} stone{'s' if n != 1 else ''})"

    def render(self, s: CatchupState, perspective=None) -> dict:
        names = {P0: "Black", P1: "White"}
        pieces = [
            {"cell": f"{q},{r}", "owner": p, "label": ""}
            for (q, r), p in s.board.items()
        ]
        highlights = [
            {"cell": f"{q},{r}", "kind": "last-move"} for (q, r) in s.last
        ]
        if self.is_terminal(s):
            sz0 = _group_sizes(s.board, P0)
            sz1 = _group_sizes(s.board, P1)
            top0 = sz0[0] if sz0 else 0
            top1 = sz1[0] if sz1 else 0
            if s.winner is not None:
                caption = f"{names[s.winner]} wins ({top0} vs {top1})"
            else:
                caption = f"Draw ({top0} vs {top1})"
        else:
            cap = self._max_place(s)
            sc0 = _score(s.board, P0)
            sc1 = _score(s.board, P1)
            caption = (
                f"{names[s.to_move]} to move "
                f"(place 1–{cap}; scores {sc0}–{sc1})"
            )
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
