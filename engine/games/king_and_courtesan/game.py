"""King & Courtesan — Mark Steere, May 2022.

A checkerboard turned 45 degrees, so the first "row" is a single square: the
**home square**. Each side owns the triangle of squares within Manhattan
distance `size - 2` of its own home corner (15 pieces on 6x6, 21 on 7x7, 28 on
8x8); the long middle diagonal starts empty. The home square holds the **king**
(physically a stack of two like-coloured checkers); every other piece is a
**courtesan** (a singleton).

Three move types, one per turn:

* **Non-capturing** — any piece steps to an adjacent EMPTY square in one of the
  three FORWARD directions. Red's forward set is `(+1,0) (0,+1) (+1,+1)`;
  Blue's is the mirror. (On the rotated board those are "forward-left",
  "forward-right" and "straight ahead".)
* **Capturing** — any piece steps onto an adjacent ENEMY-occupied square in any
  of the EIGHT directions, capturing by replacement. Backward captures are
  legal; backward non-captures are not.
* **Exchange** — the king transfers its top checker onto an adjacent FRIENDLY
  COURTESAN in one of the three forward directions; king and courtesan swap
  roles. The set of occupied squares is unchanged.

You win by moving your king onto the enemy home square (by step, by capture or
by exchange), or by capturing the enemy king.

Termination is structural, and hard (no cycle is possible even by mutual
consent) — see `rules.md` for the proof and `PLY_CAP` below for the derived,
provably-unreachable backstop. A player is likewise never stuck: the KING alone
always has a move unless it already stands on the enemy home square, in which
case the game is already over.

Moves are clickable cell paths `"from>to"`; the destination's contents decide
which of the three move types it is, so the notation is unambiguous.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

NAMES = {0: "Red", 1: "Blue"}
SIZES = (6, 7, 8)

# Red (seat 0) advances away from (0,0); Blue (seat 1) away from (size-1,size-1).
FORWARD = {0: ((1, 0), (0, 1), (1, 1)), 1: ((-1, 0), (0, -1), (-1, -1))}
ALL8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))

KING, COURTESAN = "K", "C"


def home(player: int, size: int) -> tuple:
    """The player's own home square (the corner their king starts on)."""
    return (0, 0) if player == 0 else (size - 1, size - 1)


def ply_cap(size: int) -> int:
    """A rigorous upper bound on the number of plies a game can last.

    Write ``n`` for the number of pieces on the board, ``A`` for the sum over
    all pieces of that piece's *advancement* (distance travelled from its
    owner's home corner, `c+r` for Red and the mirror for Blue), and ``K`` for
    the sum of the two kings' advancements. Then:

    * a **capture** lowers ``n`` by exactly 1 (at most `t-1` of these, where `t`
      is the starting piece count, since the board never gains a piece);
    * a **non-capturing step** leaves ``n`` alone and raises ``A`` by 1 or 2;
    * an **exchange** leaves ``n`` and ``A`` alone and raises ``K`` by 1 or 2.

    So `(-n, A, K)` increases lexicographically on EVERY move over a finite
    domain: the game is hard-finite. Counting each kind against the range it
    consumes gives the bound below (`A <= t*(2*size-2)`; a capture can cost `A`
    at most `(2*size-2) + 2`; a king's advancement falls at most 2 per capture
    it makes, so `size` bounds the exchanges between captures).

    The bound is deliberately loose and is DEAD CODE — `selftest.py` measures
    the longest random game and asserts it is nowhere near this. It exists only
    so that a future termination regression ends the game instead of hanging.
    """
    t = size * (size - 1)                 # pieces on the board at the start
    captures = t - 1                      # each removes one piece; n never grows
    a_max = t * (2 * size - 2)            # largest possible advancement sum
    non_capturing = a_max + 2 * size * captures
    exchanges = 2 * (2 * size - 2) + 2 * captures
    return captures + non_capturing + exchanges


@dataclass
class KCState:
    size: int = 6
    board: dict = field(default_factory=dict)   # (c, r) -> (owner, KING|COURTESAN)
    to_move: int = 0
    ply: int = 0
    winner: Optional[int] = None


def _cell(s: str) -> tuple:
    c, r = s.split(",")
    return int(c), int(r)


def _cid(cell: tuple) -> str:
    return f"{cell[0]},{cell[1]}"


def _alg(cell: tuple) -> str:
    return f"{'abcdefgh'[cell[0]]}{cell[1] + 1}"


def _start_board(size: int) -> dict:
    b = {}
    for c in range(size):
        for r in range(size):
            if c + r <= size - 2:
                owner = 0
            elif (size - 1 - c) + (size - 1 - r) <= size - 2:
                owner = 1
            else:
                continue
            kind = KING if (c, r) == home(owner, size) else COURTESAN
            b[(c, r)] = (owner, kind)
    return b


class KingAndCourtesan(Game):
    name = "King & Courtesan"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> KCState:
        options = options or {}
        size = int(options.get("size", 6))
        if size not in SIZES:
            raise ValueError(f"unsupported board size {size!r}")
        return KCState(size=size, board=_start_board(size))

    def current_player(self, s: KCState) -> int:
        return s.to_move

    # ---- move generation -------------------------------------------------

    def _moves(self, s: KCState) -> list:
        """(from, to) pairs. The destination's contents fix the move type:
        empty => non-capturing step, enemy => capture, own courtesan =>
        exchange. Those are mutually exclusive, so no (from, to) is ambiguous."""
        n = s.size
        me = s.to_move
        out = []
        for frm, (owner, kind) in s.board.items():
            if owner != me:
                continue
            c, r = frm
            for dc, dr in FORWARD[me]:
                to = (c + dc, r + dr)
                if not (0 <= to[0] < n and 0 <= to[1] < n):
                    continue
                occ = s.board.get(to)
                if occ is None:                                 # step
                    out.append((frm, to))
                elif occ[0] == me and kind == KING and occ[1] == COURTESAN:
                    out.append((frm, to))                       # exchange
            for dc, dr in ALL8:
                to = (c + dc, r + dr)
                if not (0 <= to[0] < n and 0 <= to[1] < n):
                    continue
                occ = s.board.get(to)
                if occ is not None and occ[0] != me:            # capture
                    out.append((frm, to))
        return out

    def legal_moves(self, s: KCState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{_cid(a)}>{_cid(b)}" for a, b in self._moves(s)]

    # ---- transition ------------------------------------------------------

    def apply_move(self, s: KCState, move: str, rng=None) -> KCState:
        frm, to = (_cell(x) for x in move.split(">"))
        me = s.to_move
        board = dict(s.board)                    # fresh dict: never alias
        mover = board[frm]
        dest = board.get(to)

        if dest is not None and dest[0] == me:   # exchange: swap the two roles
            board[frm] = (me, COURTESAN)
            board[to] = (me, KING)
        else:                                    # step or capture-by-replacement
            del board[frm]
            board[to] = mover

        winner = None
        if board.get(home(1 - me, s.size)) == (me, KING):
            winner = me                          # king reached the enemy home
        elif not any(o == 1 - me and k == KING for o, k in board.values()):
            winner = me                          # enemy king captured
        return KCState(size=s.size, board=board, to_move=1 - me,
                       ply=s.ply + 1, winner=winner)

    # ---- terminal --------------------------------------------------------

    def is_terminal(self, s: KCState) -> bool:
        # A decisive result is checked FIRST and needs no counter.
        return s.winner is not None or s.ply >= ply_cap(s.size)

    def returns(self, s: KCState) -> list[float]:
        # A decisive result OUTRANKS the ply cap: a win delivered on the very
        # ply the (provably dead) backstop trips is still a win.
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        return [0.0, 0.0]                        # cap draw — proven unreachable

    # ---- persistence -----------------------------------------------------

    def serialize(self, s: KCState) -> dict:
        return {
            "size": s.size,
            "board": {_cid(k): f"{o}{kind}" for k, (o, kind) in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> KCState:
        return KCState(
            size=d["size"],
            board={_cell(k): (int(v[0]), v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d["ply"],
            winner=d["winner"],
        )

    # ---- presentation ----------------------------------------------------

    def describe_move(self, s: KCState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        mover = s.board.get(frm)
        dest = s.board.get(to)
        pfx = "K" if mover is not None and mover[1] == KING else ""
        if dest is None:
            op = "-"
        elif mover is not None and dest[0] == mover[0]:
            op = "/"                              # exchange
        else:
            op = "x"
        return f"{pfx}{_alg(frm)}{op}{_alg(to)}"

    def heuristic(self, s: KCState) -> list[float]:
        """Material plus king race progress, squashed to (-1, 1).

        Returns ONE PAYOFF PER SEAT (the `returns` convention) — the MCTS bot
        indexes it as `payoffs[p]`."""
        if s.winner is not None:
            return self.returns(s)
        n = s.size
        counts = [0, 0]
        kings: list = [None, None]
        for (c, r), (o, kind) in s.board.items():
            counts[o] += 1
            if kind == KING:
                kings[o] = (c, r)
        dist = [0.0, 0.0]
        for p in (0, 1):
            if kings[p] is None:
                return [1.0, -1.0] if p == 1 else [-1.0, 1.0]
            tc, tr = home(1 - p, n)
            dist[p] = max(abs(tc - kings[p][0]), abs(tr - kings[p][1]))
        v = math.tanh(0.10 * (counts[0] - counts[1]) + 0.35 * (dist[1] - dist[0]))
        return [v, -v]

    def render(self, s: KCState, perspective=None) -> dict:
        pieces = []
        for (c, r), (o, kind) in s.board.items():
            p = {"cell": f"{c},{r}", "owner": o}
            if kind == KING:
                p["stack"] = [o, o]              # the physical stack of two checkers
            pieces.append(p)
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw (ply cap)"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {
                "type": "square", "width": s.size, "height": s.size,
                "tints": {_cid(home(0, s.size)): "#4a2a28",
                          _cid(home(1, s.size)): "#26304a"},
            },
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
