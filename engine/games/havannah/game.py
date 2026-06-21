"""Havannah, by Christian Freeling (1979).

Played on a hexagonal board of hexagons (a "hexhex") of side length N.
Players alternate placing one stone of their colour on any empty cell; stones
never move and are never captured. A player WINS the instant their stones
complete any ONE of three structures:

  * RING   — a loop of connected friendly stones surrounding at least one cell.
             The surrounded cell(s) may be empty, friendly, or enemy; all that
             matters is that the friendly stones form a closed cycle enclosing
             an interior region.
  * BRIDGE — a connected chain of friendly stones joining any TWO of the six
             CORNER cells of the hexagon.
  * FORK   — a connected chain of friendly stones joining any THREE of the six
             EDGES (the six side segments, EXCLUDING the corner cells).

Coordinates are axial (q, r); the third cube coordinate is s = -q-r. A cell is
on the board iff max(|q|, |r|, |s|) <= N-1. Adjacency is the 6 hex neighbours.

Draws are essentially impossible in practice, but we add a full-board terminal
(scored as a draw) so the engine always terminates.

The pie / swap rule is offered to the second player on their first turn as the
action move ``"swap"`` (enabled by the ``pie`` option, default on): instead of
placing, they adopt the opening stone as their own and pass the move back.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1


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


@lru_cache(maxsize=None)
def _corners(size: int) -> tuple:
    """The six corner cells of the hexagon."""
    n = size - 1
    return (
        (n, 0), (n, -n), (0, -n), (-n, 0), (-n, n), (0, n),
    )


@lru_cache(maxsize=None)
def _edge_id(size: int) -> dict:
    """Map each non-corner border cell -> edge index 0..5.

    The six edges are the open side segments between consecutive corners. A
    border cell lies on the side where exactly one cube coordinate is pinned
    at +(N-1) or -(N-1) (a corner pins two, so corners are excluded). We label
    the side by which coordinate (q, r, or s) is extreme and its sign.
    """
    n = size - 1
    corners = set(_corners(size))
    sides = {
        ("q", n): 0, ("r", -n): 1, ("s", n): 2,
        ("q", -n): 3, ("r", n): 4, ("s", -n): 5,
    }
    out = {}
    for (q, r) in _cells(size):
        if (q, r) in corners:
            continue
        s = -q - r
        for name, val in (("q", q), ("r", r), ("s", s)):
            if val == n or val == -n:
                out[(q, r)] = sides[(name, val)]
                break
    return out


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


@dataclass
class HavannahState:
    size: int = 8
    board: dict = field(default_factory=dict)  # (q, r) -> 0/1
    to_move: int = RED
    winner: Optional[int] = None
    win_kind: Optional[str] = None  # "ring" | "bridge" | "fork"
    last: Optional[tuple] = None     # last placed cell
    ply: int = 0
    pie: bool = True


def _group(board: dict, start: tuple, player: int) -> set:
    """Connected friendly component containing ``start`` (start must be friendly)."""
    if board.get(start) != player:
        return set()
    seen, stack = {start}, [start]
    while stack:
        cq, cr = stack.pop()
        for nb in _neighbors(cq, cr):
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return seen


def _has_ring(board: dict, size: int, group: set) -> bool:
    """Does ``group`` (a friendly connected component) enclose at least one cell?

    Flood-fill the board's empty/enemy/off-region from the OUTSIDE through every
    cell that is NOT in ``group``. Any on-board cell not reached by that fill is
    enclosed by the group -> a ring exists. We seed the fill from a virtual
    outside that surrounds the whole hexagon (every border cell that is not part
    of the group touches the outside).
    """
    on = _cell_set(size)
    # Cells the outside can reach: any on-board cell not in the group, starting
    # from border cells, expanding through non-group cells.
    reached = set()
    stack = []
    n = size - 1
    for (q, r) in on:
        if (q, r) in group:
            continue
        s = -q - r
        if abs(q) == n or abs(r) == n or abs(s) == n:  # border cell
            if (q, r) not in reached:
                reached.add((q, r))
                stack.append((q, r))
    while stack:
        cq, cr = stack.pop()
        for nb in _neighbors(cq, cr):
            if nb in on and nb not in group and nb not in reached:
                reached.add(nb)
                stack.append(nb)
    # Any on-board, non-group cell not reached => enclosed.
    for cell in on:
        if cell not in group and cell not in reached:
            return True
    return False


def _win_for(board: dict, size: int, player: int, last: Optional[tuple]) -> Optional[str]:
    """If ``player`` has completed a structure (checking the component touching
    ``last`` when given, else all components), return its kind, else None."""
    corners = set(_corners(size))
    edge_of = _edge_id(size)

    if last is not None and board.get(last) == player:
        groups = [_group(board, last, player)]
    else:
        groups, seen = [], set()
        for cell, p in board.items():
            if p == player and cell not in seen:
                g = _group(board, cell, player)
                seen |= g
                groups.append(g)

    for g in groups:
        # BRIDGE: chain touches >= 2 corners.
        if len(g & corners) >= 2:
            return "bridge"
        # FORK: chain touches >= 3 distinct edges.
        edges = {edge_of[c] for c in g if c in edge_of}
        if len(edges) >= 3:
            return "fork"
        # RING: chain encloses a cell. (Needs >= 6 stones; cheap guard.)
        if len(g) >= 6 and _has_ring(board, size, g):
            return "ring"
    return None


class Havannah(Game):
    uid = "havannah"
    name = "Havannah"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HavannahState:
        opts = options or {}
        size = int(opts.get("size", 8))
        pie = bool(opts.get("pie", True))
        return HavannahState(size=size, pie=pie)

    def current_player(self, s: HavannahState) -> int:
        return s.to_move

    def legal_moves(self, s: HavannahState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = [f"{q},{r}" for (q, r) in _cells(s.size) if (q, r) not in s.board]
        if s.pie and s.ply == 1:  # second player's first turn
            moves.append("swap")
        return moves

    def apply_move(self, s: HavannahState, move: str, rng=None) -> HavannahState:
        if move == "swap":
            if not (s.pie and s.ply == 1):
                raise ValueError("swap not available")
            (cell, _), = list(s.board.items())
            board = {cell: s.to_move}
            return HavannahState(size=s.size, board=board, to_move=1 - s.to_move,
                                 last=cell, ply=s.ply + 1, pie=s.pie)
        q, r = _cell(move)
        if (q, r) not in _cell_set(s.size) or (q, r) in s.board:
            raise ValueError(f"illegal move {move!r}")
        mover = s.to_move
        board = dict(s.board)
        board[(q, r)] = mover
        kind = _win_for(board, s.size, mover, (q, r))
        winner = mover if kind else None
        return HavannahState(
            size=s.size, board=board, to_move=1 - mover,
            winner=winner, win_kind=kind, last=(q, r), ply=s.ply + 1, pie=s.pie,
        )

    def is_terminal(self, s: HavannahState) -> bool:
        if s.winner is not None:
            return True
        return len(s.board) >= len(_cells(s.size))  # full board (safety draw)

    def returns(self, s: HavannahState) -> list[float]:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # full-board draw (practically unreachable)

    def serialize(self, s: HavannahState) -> dict:
        return {
            "size": s.size,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "win_kind": s.win_kind,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "ply": s.ply,
            "pie": s.pie,
        }

    def deserialize(self, d: dict) -> HavannahState:
        last = d.get("last")
        return HavannahState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            win_kind=d.get("win_kind"),
            last=(_cell(last) if last else None),
            ply=d.get("ply", len(d["board"])),
            pie=d.get("pie", True),
        )

    def describe_move(self, s: HavannahState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        return move

    def render(self, s: HavannahState, perspective=None) -> dict:
        names = {RED: "Red", BLUE: "Blue"}
        pieces = [
            {"cell": f"{q},{r}", "owner": p, "label": ""}
            for (q, r), p in s.board.items()
        ]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})
        if s.winner is not None:
            caption = f"{names[s.winner]} wins by {s.win_kind}"
        elif self.is_terminal(s):
            caption = "Draw (full board)"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
