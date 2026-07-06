"""Ayu — "Attach Your Units" (Luis Bolaños Mures, 2011).

Played on the points of an odd-sized square grid (default 11x11), which starts
filled with an interleaved pattern of Black and White singleton stones (30
each on 11x11). Adjacency is ORTHOGONAL throughout.

On your turn you MUST move: either step a singleton to an adjacent empty
point, or take a stone from one of your groups and re-place it on a different
empty point adjacent to that same group (minus the moved stone) — all stones
that formed one group before the move must still be joined afterwards (the
group may be split *during* the move, but not after).

Distance rule: every move must reduce the distance between the moved unit and
its closest friendly unit, where the distance between two units is the length
of the shortest path of adjacent EMPTY points between them (the number of
moves needed to join them). Following the official Dagaz implementation on
mindsports.nl, this is enforced as "new closest distance < old closest
distance", and a move that JOINS the moved unit to another friendly unit is
always legal (distance became 0). These readings are equivalent to "approach
a (tied-)closest unit": a move changes any unit-pair distance by at most 1,
so the closest distance can only drop via a unit that was already closest.

A player who CANNOT MOVE on their turn WINS — normally because all their
stones form a single group (a one-group player has no legal move, since there
is no friendly unit left to approach).

Draw: a repeated position with the same player to move is a draw (tracked via
position keys), plus a hard ply cap as a termination backstop. Optional pie
rule: after Black's first move, White may play "swap" to change sides.

Moves are "from>to" cell paths; "swap" is an action button.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # stone colours (seat 0 plays Black unless swapped)
ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))
FILES = "abcdefghijklmno"


@dataclass
class AyuState:
    n: int = 11
    board: dict = field(default_factory=dict)  # (c, r) -> colour (BLACK/WHITE)
    to_move: int = 0                           # seat index
    swapped: bool = False                      # pie swap taken (seat<->colour flip)
    pie: bool = True
    ply: int = 0
    drawn: bool = False
    draw_kind: str = ""                        # "repetition" | "ply-cap"
    history: list = field(default_factory=list)  # position keys incl. initial
    last: Optional[list] = None                # [from_id, to_id] of last move
    _moves: Optional[list] = field(default=None, repr=False, compare=False)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _cid(p) -> str:
    return f"{p[0]},{p[1]}"


def _setup(n: int) -> dict:
    """Interleaved singletons: Black on even rows / odd columns, White on odd
    rows / even columns (rows counted from 0 at the bottom; corners empty; no
    two same-colour stones orthogonally adjacent; (n*n-1)//4 stones each).
    Matches the official mindsports/Dagaz 11x11 setup."""
    b = {}
    for r in range(n):
        for c in range(n):
            if r % 2 == 0 and c % 2 == 1:
                b[(c, r)] = BLACK
            elif r % 2 == 1 and c % 2 == 0:
                b[(c, r)] = WHITE
    return b


def _groups(board: dict, colour: int) -> list:
    """Orthogonally-connected groups of `colour`, each a list of cells."""
    seen, groups = set(), []
    for p, col in board.items():
        if col != colour or p in seen:
            continue
        comp = [p]
        seen.add(p)
        i = 0
        while i < len(comp):
            c, r = comp[i]
            i += 1
            for dc, dr in ORTH:
                q = (c + dc, r + dr)
                if q not in seen and board.get(q) == colour:
                    seen.add(q)
                    comp.append(q)
        groups.append(comp)
    return groups


def _component(board: dict, start, colour: int) -> set:
    """The connected group of `colour` stones containing `start`."""
    comp = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for dc, dr in ORTH:
            q = (c + dc, r + dr)
            if q not in comp and board.get(q) == colour:
                comp.add(q)
                stack.append(q)
    return comp


def _closest_dist(board: dict, n: int, unit, colour: int, limit=None):
    """Distance from `unit` to the nearest other friendly unit: the length of
    the shortest chain of adjacent EMPTY points between them (enemy stones
    block). Returns None if no friendly stone outside `unit` is reachable, or
    if the distance would exceed `limit`."""
    unit_set = unit if isinstance(unit, set) else set(unit)
    seen = set()
    frontier = []
    for (c, r) in unit_set:
        for dc, dr in ORTH:
            q = (c + dc, r + dr)
            if 0 <= q[0] < n and 0 <= q[1] < n and q not in seen and q not in board:
                seen.add(q)
                frontier.append(q)
    d = 0
    while frontier:
        d += 1
        if limit is not None and d > limit:
            return None
        nxt = []
        for (c, r) in frontier:
            for dc, dr in ORTH:
                q = (c + dc, r + dr)
                if not (0 <= q[0] < n and 0 <= q[1] < n):
                    continue
                occ = board.get(q)
                if occ is None:
                    if q not in seen:
                        seen.add(q)
                        nxt.append(q)
                elif occ == colour and q not in unit_set:
                    return d
        frontier = nxt
    return None


def _poskey(board: dict, colour_to_move: int) -> str:
    s = ";".join(f"{c},{r},{col}" for (c, r), col in sorted(board.items()))
    return hashlib.md5(f"{s}|{colour_to_move}".encode()).hexdigest()[:16]


class Ayu(Game):
    uid = "ayu"
    name = "Ayu"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AyuState:
        opts = options or {}
        n = int(opts.get("size", 11))
        if n % 2 == 0 or n < 5:
            raise ValueError("board size must be odd and >= 5")
        pie = opts.get("pie", True)
        if isinstance(pie, str):
            pie = pie.lower() not in ("false", "off", "0", "no")
        board = _setup(n)
        return AyuState(n=n, board=board, pie=bool(pie),
                        history=[_poskey(board, BLACK)])

    def current_player(self, s: AyuState) -> int:
        return s.to_move

    # ---- move generation ----------------------------------------------------

    def _colour(self, s: AyuState, seat: int) -> int:
        return seat ^ (1 if s.swapped else 0)

    def _raw_moves(self, s: AyuState) -> list:
        board, n = s.board, s.n
        mc = self._colour(s, s.to_move)
        groups = _groups(board, mc)
        moves = []
        if len(groups) < 2:
            # single (or no) unit: no friendly unit to approach -> no moves.
            return moves
        for unit in groups:
            uset = set(unit)
            old_d = _closest_dist(board, n, uset, mc)
            work = dict(board)
            for stone in unit:
                if len(unit) == 1:
                    rem = set()
                    cands = []
                    for dc, dr in ORTH:
                        q = (stone[0] + dc, stone[1] + dr)
                        if 0 <= q[0] < n and 0 <= q[1] < n and q not in board:
                            cands.append(q)
                else:
                    rem = uset - {stone}
                    seenc = set()
                    cands = []
                    for (c, r) in rem:
                        for dc, dr in ORTH:
                            q = (c + dc, r + dr)
                            if (0 <= q[0] < n and 0 <= q[1] < n
                                    and q not in seenc and q not in board):
                                seenc.add(q)
                                cands.append(q)
                if not cands:
                    continue
                del work[stone]
                for t in cands:
                    work[t] = mc
                    comp = _component(work, t, mc)
                    if rem <= comp:  # former group still joined (no split)
                        if len(comp) > len(unit):
                            # joined another friendly unit: always legal
                            moves.append(f"{_cid(stone)}>{_cid(t)}")
                        elif old_d is not None and _closest_dist(
                                work, n, comp, mc, limit=old_d - 1) is not None:
                            moves.append(f"{_cid(stone)}>{_cid(t)}")
                    del work[t]
                work[stone] = mc
        return moves

    def _moves_cached(self, s: AyuState) -> list:
        if s._moves is None:
            moves = self._raw_moves(s)
            if s.pie and s.ply == 1 and not s.swapped:
                moves.append("swap")
            s._moves = moves
        return s._moves

    def is_terminal(self, s: AyuState) -> bool:
        return s.drawn or not self._moves_cached(s)

    def legal_moves(self, s: AyuState) -> list:
        return [] if s.drawn else self._moves_cached(s)

    # ---- apply ---------------------------------------------------------------

    def apply_move(self, s: AyuState, move: str, rng=None) -> AyuState:
        if move == "swap":
            if not (s.pie and s.ply == 1 and not s.swapped):
                raise ValueError("swap not available")
            # White changes sides: seats swap colours; the position (and the
            # colour to move) is unchanged, so no new repetition key is added.
            return AyuState(n=s.n, board=dict(s.board), to_move=1 - s.to_move,
                            swapped=True, pie=s.pie, ply=s.ply + 1,
                            history=list(s.history), last=None)
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        mc = self._colour(s, s.to_move)
        if s.board.get(frm) != mc or to in s.board:
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        del board[frm]
        board[to] = mc
        ply = s.ply + 1
        key = _poskey(board, 1 - mc)
        drawn, kind = False, ""
        if key in s.history:
            drawn, kind = True, "repetition"
        elif ply >= self._ply_cap(s.n):
            drawn, kind = True, "ply-cap"
        return AyuState(n=s.n, board=board, to_move=1 - s.to_move,
                        swapped=s.swapped, pie=s.pie, ply=ply, drawn=drawn,
                        draw_kind=kind, history=s.history + [key],
                        last=[fs, ts])

    @staticmethod
    def _ply_cap(n: int) -> int:
        return 8 * n * n  # generous backstop; real games are far shorter

    def returns(self, s: AyuState) -> list:
        if s.drawn:
            return [0.0, 0.0]
        # terminal because the player to move cannot move: they WIN.
        return [1.0, -1.0] if s.to_move == 0 else [-1.0, 1.0]

    # ---- heuristic (MCTS rollout cutoff) --------------------------------------

    def heuristic(self, s: AyuState) -> list:
        g = [len(_groups(s.board, BLACK)), len(_groups(s.board, WHITE))]
        score_black = math.tanh((g[WHITE] - g[BLACK]) / 4.0)  # fewer units = better
        out = [0.0, 0.0]
        for seat in (0, 1):
            out[seat] = score_black if self._colour(s, seat) == BLACK else -score_black
        return out

    # ---- serialize -------------------------------------------------------------

    def serialize(self, s: AyuState) -> dict:
        return {
            "n": s.n,
            "board": {_cid(p): col for p, col in s.board.items()},
            "to_move": s.to_move,
            "swapped": s.swapped,
            "pie": s.pie,
            "ply": s.ply,
            "drawn": s.drawn,
            "draw_kind": s.draw_kind,
            "history": list(s.history),
            "last": list(s.last) if s.last else None,
        }

    def deserialize(self, d: dict) -> AyuState:
        return AyuState(
            n=d["n"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            swapped=d.get("swapped", False),
            pie=d.get("pie", True),
            ply=d.get("ply", 0),
            drawn=d.get("drawn", False),
            draw_kind=d.get("draw_kind", ""),
            history=list(d.get("history", [])),
            last=list(d["last"]) if d.get("last") else None,
        )

    # ---- presentation ------------------------------------------------------------

    def describe_move(self, s: AyuState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        alg = lambda p: f"{FILES[p[0]]}{p[1] + 1}"  # noqa: E731
        mc = self._colour(s, s.to_move)
        # a join attaches the moved unit to a friendly stone OUTSIDE its own unit
        unit = _component(s.board, frm, mc) if s.board.get(frm) == mc else {frm}
        joined = False
        for dc, dr in ORTH:
            q = (to[0] + dc, to[1] + dr)
            if q not in unit and s.board.get(q) == mc:
                joined = True
                break
        return f"{alg(frm)}-{alg(to)}" + (" (join)" if joined else "")

    def _seat_name(self, s: AyuState, seat: int) -> str:
        return "Black" if self._colour(s, seat) == BLACK else "White"

    def render(self, s: AyuState, perspective=None) -> dict:
        pieces = [
            {"cell": _cid(p), "owner": col ^ (1 if s.swapped else 0), "label": ""}
            for p, col in s.board.items()
        ]
        highlights = []
        if s.last:
            highlights.append({"cell": s.last[1], "kind": "last-move"})
            highlights.append({"cell": s.last[0], "kind": "last-move"})
        if s.drawn:
            caption = f"Draw ({s.draw_kind})"
        elif self.is_terminal(s):
            caption = f"{self._seat_name(s, s.to_move)} cannot move — {self._seat_name(s, s.to_move)} wins"
        else:
            caption = f"{self._seat_name(s, s.to_move)} to move"
        return {
            "board": {"type": "square", "width": s.n, "height": s.n},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
