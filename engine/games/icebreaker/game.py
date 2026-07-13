"""Icebreaker, by Mark Steere (November 2021).

A two-player capture game on a hexagonal (hexhex) grid. There are three red
ships and three black ships, initially placed at the six corners of the board
(Fig. 1). Every other cell holds a white *iceberg*. Red and Black take turns
moving one of their own ships one cell per turn, starting with Red; passing is
not allowed.

Rules as implemented (from the designer's one-page rules sheet,
marksteeregames.com/Icebreaker.pdf):

  * MOVE: you must move one of your ships to an adjacent cell which doesn't
    contain another ship. Moving onto a cell that contains an iceberg captures
    the iceberg and increases your score by 1 (the iceberg is removed, the
    ship takes its place).
  * MOVE DIRECTION (the crux): the ship you select must move *closer to its
    closest iceberg*. Distance is the number of cells along the shortest path
    of cells connecting the ship to an iceberg, routing AROUND other ships
    (a BFS over empty/iceberg cells that treats the other five ships as
    blockers; icebergs are passable floor and also valid endpoints). A legal
    destination for a chosen ship is an adjacent non-ship cell whose own
    distance-to-nearest-iceberg is exactly one less than the ship's. If the
    ship has an iceberg adjacent (distance 1), the only such destinations are
    icebergs, so "you must capture one of them" falls out automatically.
  * OBJECT: capture the majority of the icebergs. On the size-5 board there
    are 55 icebergs at the start, so 28 captures win. In general
    majority = floor(total / 2) + 1.

Termination: each non-capturing move strictly reduces the moving ship's
distance to its nearest iceberg, and captures monotonically drain a finite
supply of icebergs, so real play converges. A hard ply-cap draw backstop is
kept defensively. A player with NO legal move (all their ships walled off
from every iceberg by the other ships) cannot pass, so the game ends and is
scored by icebergs captured: more captures wins, an equal count is an honest
draw. (This is rare and never fabricates a winner from a genuine tie.)
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

RED, BLACK = 0, 1
SHIP_FILL = ["#d23b3b", "#2b2b2b"]
SHIP_STROKE = ["#7a1414", "#000000"]
ICE_FILL = "#eaf6ff"
ICE_STROKE = "#8fb8d0"
SEAT_NAME = {RED: "Red", BLACK: "Black"}

INF = float("inf")


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
            if abs(q + r) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


def _corners(size: int):
    """The six corner cells, in angular order (matching Fig. 1's layout).

    With the web renderer's axial->pixel map (x = √3·q + (√3/2)·r, y = 1.5·r),
    these are: top-left, top-right, right, bottom-right, bottom-left, left.
    Fig. 1 places Red on the 1st/3rd/5th and Black on the 2nd/4th/6th.
    """
    n = size - 1
    return [
        (0, -n),   # top-left     -> Red
        (n, -n),   # top-right    -> Black
        (n, 0),    # right        -> Red
        (0, n),    # bottom-right -> Black
        (-n, n),   # bottom-left  -> Red
        (-n, 0),   # left         -> Black
    ]


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


def _key(c: tuple[int, int]) -> str:
    return f"{c[0]},{c[1]}"


def _dist_field(size: int, icebergs: frozenset, blockers: frozenset) -> dict:
    """Multi-source BFS: distance from every reachable cell to the nearest
    iceberg, moving over on-board cells that are NOT blockers (icebergs and
    empties are passable; icebergs are the sources at distance 0)."""
    on = _cell_set(size)
    dist: dict = {}
    dq = deque()
    for c in icebergs:
        dist[c] = 0
        dq.append(c)
    while dq:
        cur = dq.popleft()
        d = dist[cur]
        for nb in _neighbors(*cur):
            if nb not in on or nb in blockers or nb in dist:
                continue
            dist[nb] = d + 1
            dq.append(nb)
    return dist


@dataclass
class IceState:
    size: int = 5
    total: int = 55                       # icebergs at the start
    ships: dict = field(default_factory=dict)     # (q, r) -> seat
    icebergs: frozenset = frozenset()             # cells holding an iceberg
    to_move: int = RED
    captures: list = field(default_factory=lambda: [0, 0])
    ply: int = 0
    last: tuple = ()                              # (from, to) of the last move
    winner: Optional[int] = None
    over: bool = False


class Icebreaker(Game):
    name = "Icebreaker"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup -------------------------------------------------------------

    def initial_state(self, options=None, rng=None) -> IceState:
        opts = options or {}
        size = int(opts.get("size", 5))
        corners = _corners(size)
        ships = {}
        for i, c in enumerate(corners):
            ships[c] = RED if i % 2 == 0 else BLACK
        icebergs = frozenset(c for c in _cells(size) if c not in ships)
        return IceState(size=size, total=len(icebergs), ships=ships,
                        icebergs=icebergs)

    def current_player(self, s: IceState) -> int:
        return s.to_move

    def _majority(self, s: IceState) -> int:
        return s.total // 2 + 1

    # -- move generation ---------------------------------------------------

    def _moves_for_ship(self, s: IceState, ship: tuple) -> list:
        """Legal destinations for one ship, as (from, to) cell pairs."""
        others = frozenset(c for c in s.ships if c != ship)
        field_ = _dist_field(s.size, s.icebergs, others)
        d_here = field_.get(ship, INF)
        if d_here is INF or d_here == 0:
            return []
        out = []
        for nb in _neighbors(*ship):
            if nb not in _cell_set(s.size):
                continue
            if nb in s.ships:                 # can't move onto another ship
                continue
            if field_.get(nb, INF) == d_here - 1:
                out.append((ship, nb))
        return out

    def _all_moves(self, s: IceState) -> list:
        moves = []
        for ship, seat in s.ships.items():
            if seat != s.to_move:
                continue
            moves.extend(self._moves_for_ship(s, ship))
        return moves

    def legal_moves(self, s: IceState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{_key(a)}>{_key(b)}" for (a, b) in self._all_moves(s)]

    # -- transition --------------------------------------------------------

    def _ply_cap(self, size: int) -> int:
        # Defensive only: non-capturing moves strictly reduce a ship's distance
        # and captures drain a finite iceberg supply, so real play converges.
        return 60 * len(_cells(size))

    def apply_move(self, s: IceState, move: str, rng=None) -> IceState:
        if self.is_terminal(s):
            raise ValueError("game over")
        if move not in self.legal_moves(s):
            raise ValueError(f"illegal move {move!r}")
        src_s, dst_s = move.split(">")
        src, dst = _cell(src_s), _cell(dst_s)
        mover = s.to_move

        ships = dict(s.ships)
        del ships[src]
        ships[dst] = mover
        icebergs = s.icebergs
        captures = list(s.captures)
        if dst in icebergs:
            icebergs = icebergs - {dst}
            captures[mover] += 1

        ns = IceState(
            size=s.size, total=s.total, ships=ships, icebergs=icebergs,
            to_move=1 - mover, captures=captures, ply=s.ply + 1,
            last=(src, dst),
        )

        if captures[mover] >= self._majority(s):
            ns.winner = mover
            ns.over = True
        elif ns.ply >= self._ply_cap(s.size):
            ns.winner = None          # hard-cap honest draw (defensive backstop)
            ns.over = True
        elif not self._all_moves(ns):
            # The player to move cannot move and may not pass: end the game and
            # score by captures. More icebergs wins; an equal count is an honest
            # draw (never a fabricated winner).
            ns.over = True
            if captures[0] > captures[1]:
                ns.winner = 0
            elif captures[1] > captures[0]:
                ns.winner = 1
            else:
                ns.winner = None
        return ns

    def is_terminal(self, s: IceState) -> bool:
        return s.over

    def returns(self, s: IceState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: IceState) -> list:
        """Capture-race progress for truncated MCTS rollouts."""
        d = (s.captures[0] - s.captures[1]) / max(1, self._majority(s))
        v = math.tanh(1.2 * d)
        return [v, -v]

    # -- serialization -----------------------------------------------------

    def serialize(self, s: IceState) -> dict:
        return {
            "size": s.size,
            "total": s.total,
            "ships": {_key(c): seat for c, seat in s.ships.items()},
            "icebergs": [_key(c) for c in sorted(s.icebergs)],
            "to_move": s.to_move,
            "captures": list(s.captures),
            "ply": s.ply,
            "last": [_key(c) for c in s.last],
            "winner": s.winner,
            "over": s.over,
        }

    def deserialize(self, d: dict) -> IceState:
        return IceState(
            size=d["size"],
            total=d["total"],
            ships={_cell(k): v for k, v in d["ships"].items()},
            icebergs=frozenset(_cell(k) for k in d["icebergs"]),
            to_move=d["to_move"],
            captures=list(d.get("captures", [0, 0])),
            ply=d.get("ply", 0),
            last=tuple(_cell(k) for k in d.get("last", [])),
            winner=d.get("winner"),
            over=d.get("over", False),
        )

    # -- presentation ------------------------------------------------------

    def describe_move(self, s: IceState, move: str) -> str:
        src_s, dst_s = move.split(">")
        cap = " (capture)" if _cell(dst_s) in s.icebergs else ""
        return f"{SEAT_NAME[s.to_move]} {src_s}→{dst_s}{cap}"

    def render(self, s: IceState, perspective=None) -> dict:
        pieces = []
        for c in s.icebergs:
            pieces.append({"cell": _key(c), "fill": ICE_FILL, "stroke": ICE_STROKE})
        for c, seat in s.ships.items():
            pieces.append({
                "cell": _key(c), "owner": seat,
                "fill": SHIP_FILL[seat], "stroke": SHIP_STROKE[seat],
            })
        highlights = [{"cell": _key(c), "kind": "last-move"} for c in s.last]

        maj = self._majority(s)
        score = (f"captures {s.captures[0]}/{maj} : {s.captures[1]}/{maj} "
                 f"({len(s.icebergs)} icebergs left)")
        if s.over:
            if s.winner is None:
                caption = f"Draw — {score}"
            else:
                caption = f"{SEAT_NAME[s.winner]} wins — {score}"
        else:
            caption = f"{SEAT_NAME[s.to_move]} to move — {score}"

        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
