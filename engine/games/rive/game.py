"""Rive, by Mark Steere (December 2010).

A hexagonal group-minimisation capture game. Rive is played on an odd-sized
(hence odd-celled -> draws impossible) hexhex board that starts empty. Black and
White alternate placing stones; the goal is a majority of stones on the FILLED
board.

Core mechanics (verified against Mark Steere's one-page rule sheet, Figs 1-3d,
marksteeregames.com/Rive.pdf):

  * A GROUP is a maximal connected component of stones of BOTH colours
    (mixed-colour adjacency merges into one group). (Fig 2.)

  * STONE PLACEMENT. If you can place a stone in ISOLATION (adjacent to no
    existing group) you MUST. (Fig 1 marks exactly the isolated cells.)
    Otherwise your stone must go on an empty cell that MINIMISES the size of the
    LARGEST group it touches (over every empty cell). Every empty cell achieving
    that minimum is legal — whether it touches one group (non-capturing) or two
    or three (capturing). (Fig 2 / Fig 3a: it is illegal to touch the size-3
    group when a cell touching only size-2 groups exists.)

    Geometry note: on a hexhex a placed stone can touch AT MOST 3 distinct
    groups — the 6 neighbours form a ring in which any two non-adjacent
    (independent) cells number at most 3 — which is exactly the rule sheet's
    "up to three groups".

  * CAPTURING PLACEMENT. When your stone connects 2 or 3 groups you MUST remove
    stones (of either/both colours) from the newly combined group to bring it
    down to exactly ONE larger than the LARGEST of the combined groups. The
    removal must NOT split the group into two or more pieces (the survivors must
    stay a single connected component). The mover CHOOSES which stones to remove,
    so each valid non-splitting removal set is a distinct legal move.
    (Fig 3b: White joins two size-2 groups with a placement, removes 2 -> a
    connected size-3 group. Fig 3d: Black joins two size-3 groups, removes 3 ->
    a connected size-4 group.)

  * MULTIPLE PLACEMENTS PER TURN. A capturing placement does NOT end your turn:
    you must place again, and keep placing until a NON-capturing placement, which
    ends the turn. (Figs 3c/3d — the same-player-continues pattern; the engine
    just keeps ``to_move`` fixed across a capturing placement.)

  * OBJECT. Majority of stones on a filled board. Odd cell count => the full
    board can never tie, so the winner is always decided.

MOVE ENCODING (a '>'-separated cell path, per the platform convention):
  * Non-capturing placement:  "q,r"                     (one cell)
  * Capturing placement:      "q,r>a,b>c,d>..."         (placement cell first,
    then the removed cells in a canonical (r-then-q) sorted order). One move per
    distinct removal SET.

INTERPRETATIONS (documented in rules.md):
  * The just-placed stone is never itself removed (it is the stone that
    performed the capture); removals come only from the pre-existing stones of
    the combined group. Every capture always has at least one valid removal
    (keep the largest combined group plus the placed stone, remove the rest),
    so a capturing placement is never a dead end.
  * Draws cannot occur in real Rive, but captures make the board non-monotonic,
    so a generous hard ply-cap draw is kept purely as an anti-loop backstop for
    the platform's termination guarantee (honest draw on the cap, never a
    fabricated winner).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
from typing import Optional

from agp.game import Game


def _neighbors(q: int, r: int):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1),
            (q + 1, r - 1), (q - 1, r + 1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    """All on-board axial cells of a hexhex of side ``size``."""
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


def _cs(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _cell(s: str) -> tuple:
    q, r = s.split(",")
    return int(q), int(r)


def _groups(board: dict, size: int):
    """Connected components of stones (BOTH colours merge). Returns
    (list_of_frozensets, cell->group_index map)."""
    on = _cell_set(size)
    seen: set = set()
    groups = []
    cell_to_gid = {}
    for cell in board:
        if cell in seen:
            continue
        comp = {cell}
        stack = [cell]
        seen.add(cell)
        while stack:
            c = stack.pop()
            for nb in _neighbors(*c):
                if nb in on and nb in board and nb not in comp:
                    comp.add(nb)
                    seen.add(nb)
                    stack.append(nb)
        gid = len(groups)
        for c in comp:
            cell_to_gid[c] = gid
        groups.append(frozenset(comp))
    return groups, cell_to_gid


def _connected(cells_set: set, size: int) -> bool:
    if not cells_set:
        return False
    start = next(iter(cells_set))
    seen = {start}
    stack = [start]
    while stack:
        c = stack.pop()
        for nb in _neighbors(*c):
            if nb in cells_set and nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return len(seen) == len(cells_set)


def _valid_removals(combined: set, placed, remove_count: int, size: int):
    """Yield every removal set (tuple of cells, canonically sorted) of size
    ``remove_count`` drawn from ``combined`` minus the placed stone, such that
    the survivors form a single connected component."""
    if remove_count <= 0:
        return
    removable = sorted(combined - {placed}, key=lambda c: (c[1], c[0]))
    for R in combinations(removable, remove_count):
        remaining = combined - set(R)
        if _connected(remaining, size):
            yield R


@dataclass
class RiveState:
    size: int = 3
    board: dict = field(default_factory=dict)   # (q, r) -> owner 0=Black / 1=White
    to_move: int = 0                            # 0 = Black (moves first)
    ply: int = 0
    chain: bool = False                         # mid-turn continuation (last was a capture)
    last: tuple = ()                            # cells touched by the previous move (for render)
    winner: Optional[int] = None
    over: bool = False


class Rive(Game):
    name = "Rive"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> RiveState:
        opts = options or {}
        size = int(opts.get("size", 3))
        return RiveState(size=size)

    def current_player(self, s: RiveState) -> int:
        return s.to_move

    # -- move generation ---------------------------------------------------

    def _ply_cap(self, size: int) -> int:
        # Anti-loop backstop only. Captures make the board non-monotonic, so we
        # cannot prove filling; this bound is generous enough that a genuine
        # game finishes far below it (honest draw if it is ever reached).
        return 60 * len(_cells(size))

    def legal_moves(self, s: RiveState) -> list:
        if self.is_terminal(s):
            return []
        size = s.size
        board = s.board
        empties = [c for c in _cells(size) if c not in board]
        if not empties:
            return []

        groups, cell_to_gid = _groups(board, size)

        # adjacency info per empty cell
        info = {}      # cell -> (frozenset of gids, largest adjacent size)
        isolated = []
        for e in empties:
            gids = set()
            for nb in _neighbors(*e):
                if nb in cell_to_gid:
                    gids.add(cell_to_gid[nb])
            largest = max((len(groups[g]) for g in gids), default=0)
            info[e] = (gids, largest)
            if not gids:
                isolated.append(e)

        # Rule 1: an isolated placement is available -> must play isolated.
        if isolated:
            return [_cs(e) for e in isolated]

        # Rule 2: minimise the largest touched group.
        minmax = min(largest for (_gids, largest) in info.values())
        moves: list = []
        for e in empties:
            gids, largest = info[e]
            if largest != minmax:
                continue
            if len(gids) <= 1:
                moves.append(_cs(e))                       # non-capturing
                continue
            # capturing placement: connects 2 or 3 groups
            combined = {e}
            for g in gids:
                combined |= groups[g]
            biggest = max(len(groups[g]) for g in gids)
            target = biggest + 1
            remove_count = len(combined) - target
            for R in _valid_removals(combined, e, remove_count, size):
                moves.append(_cs(e) + "".join(">" + _cs(c) for c in R))
        return moves

    # -- transition --------------------------------------------------------

    def apply_move(self, s: RiveState, move: str, rng=None) -> RiveState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move
        parts = move.split(">")
        place = _cell(parts[0])
        removals = [_cell(p) for p in parts[1:]]

        if place not in _cell_set(s.size):
            raise ValueError(f"off-board placement {move!r}")
        if place in s.board:
            raise ValueError(f"occupied cell {move!r}")

        board = dict(s.board)
        board[place] = mover
        for c in removals:
            if c not in board:
                raise ValueError(f"cannot remove empty cell {c} in {move!r}")
            del board[c]

        capturing = bool(removals)
        touched = tuple([place] + removals)
        ns = RiveState(
            size=s.size,
            board=board,
            to_move=mover if capturing else 1 - mover,
            ply=s.ply + 1,
            chain=capturing,
            last=touched,
        )

        total = len(_cells(s.size))
        if len(board) >= total:
            # Board filled -> majority decides (odd cell count => never a tie).
            black = sum(1 for v in board.values() if v == 0)
            white = len(board) - black
            ns.winner = 0 if black > white else 1
            ns.over = True
        elif ns.ply >= self._ply_cap(s.size):
            ns.winner = None          # hard-cap honest draw (anti-loop backstop)
            ns.over = True
        return ns

    def is_terminal(self, s: RiveState) -> bool:
        return s.over

    def returns(self, s: RiveState) -> list:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: RiveState) -> list:
        """Stone-majority lead, for truncated MCTS rollouts."""
        import math
        black = sum(1 for v in s.board.values() if v == 0)
        white = len(s.board) - black
        total = len(_cells(s.size))
        d = (black - white) / max(1, total)
        v = math.tanh(2.0 * d)
        return [v, -v]

    # -- serialization -----------------------------------------------------

    def serialize(self, s: RiveState) -> dict:
        return {
            "size": s.size,
            "board": {_cs(c): v for c, v in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "chain": s.chain,
            "last": [_cs(c) for c in s.last],
            "winner": s.winner,
            "over": s.over,
        }

    def deserialize(self, d: dict) -> RiveState:
        return RiveState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            chain=d.get("chain", False),
            last=tuple(_cell(x) for x in d.get("last", [])),
            winner=d.get("winner"),
            over=d.get("over", False),
        )

    # -- presentation ------------------------------------------------------

    def describe_move(self, s: RiveState, move: str) -> str:
        parts = move.split(">")
        colour = "Black" if s.to_move == 0 else "White"
        label = f"{colour} {parts[0]}"
        if len(parts) > 1:
            label += f" (-{len(parts) - 1})"
        return label

    def render(self, s: RiveState, perspective=None) -> dict:
        fills = ["#1a1a1a", "#f4f4ef"]
        strokes = ["#000000", "#555555"]
        pieces = []
        for c, owner in s.board.items():
            pieces.append({
                "cell": _cs(c),
                "owner": owner,
                "fill": fills[owner],
                "stroke": strokes[owner],
            })
        highlights = [{"cell": _cs(c), "kind": "last-move"} for c in s.last]

        black = sum(1 for v in s.board.values() if v == 0)
        white = len(s.board) - black
        score = f"Black {black} : {white} White"
        names = {0: "Black", 1: "White"}
        if s.over:
            caption = (f"Draw — {score}" if s.winner is None
                       else f"{names[s.winner]} wins — {score}")
        elif s.chain:
            caption = f"{names[s.to_move]} must place again — {score}"
        else:
            caption = f"{names[s.to_move]} to move — {score}"

        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
