"""Zola — Mark Steere (February 2021).

Two players, Red and Blue, on a 6x6 (or 8x8...) checkerboard that starts
COMPLETELY FILLED with a checkered pattern of red and blue checkers (the rule
sheet's Figure 1). Red moves first; players alternate moving ONE of their own
checkers per turn. "If a player has a move available, he must make one. If he
has no moves available, he must sit the game out and wait until he does have a
move available." (Sitting out is the explicit "pass" move here, legal ONLY
when a player has no other move.)

MOVES (from the PDF, marksteeregames.com/Zola.pdf):

* Non-capturing: "a king-like move to an adjacent (horizontally, vertically,
  or diagonally), unoccupied square. A non-capturing move must INCREASE the
  straight line distance to the center point of the board." (Strict.)
* Capturing: "a queen-like move along a straight (horizontal, vertical or
  diagonal) sequence of zero or more unoccupied squares terminating with an
  enemy occupied square. The enemy checker is removed and replaced with the
  capturing checker. A capturing move must MAINTAIN OR DECREASE the straight
  line distance to the center point of the board."

Captures are NOT compulsory — any legal move may be chosen.

OBJECT: capture all enemy checkers.

Distance metric: the center POINT of the board sits between squares (the board
side is even), at ((n-1)/2, (n-1)/2) in cell coordinates. We compare squared
Euclidean distances scaled by 4 to stay in integers:
    d2(c, r) = (2c - (n-1))^2 + (2r - (n-1))^2.
On 6x6 this yields exactly the PDF sidebar's 6 "levels" of distance
(d2 = 2, 10, 18, 26, 34, 50 with 4, 8, 4, 8, 8, 4 squares respectively).

Termination: the PDF states "Draws cannot occur in Zola" and "At least one of
the two players will always have a move available." Finiteness is provable:
every capture reduces the checker count (bounded), and between captures every
non-pass move strictly increases the integer sum of d2 over all checkers,
which is bounded above — so play cannot cycle. A pass never changes the board,
and two passes in a row would mean NEITHER player has a move; per the rule
sheet that is impossible (an exhaustive ≤4-checker search plus millions of
random positions found no such position), but as the platform-mandated honest
backstop this implementation treats a mutually-stuck position as a terminal
DRAW rather than looping.

Moves are "c,r>c,r" square cell paths (capture iff the destination is
occupied), plus the forced "pass".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import tanh
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1  # Red = seat 0, moves first (per the PDF)
SEAT_NAMES = ("Red", "Blue")
DIRS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def _d2(c: int, r: int, n: int) -> int:
    """4x the squared Euclidean distance from square (c,r) to the board center."""
    return (2 * c - (n - 1)) ** 2 + (2 * r - (n - 1)) ** 2


def _setup(n: int) -> dict:
    """Figure-1 setup: the full checkered fill. Red on (c+r)-even squares —
    with the renderer drawing row 0 at the bottom, this reproduces Figure 1
    exactly (bottom-left square red, colors alternating)."""
    return {(c, r): (RED if (c + r) % 2 == 0 else BLUE)
            for c in range(n) for r in range(n)}


def _cell(sid: str):
    c, r = sid.split(",")
    return int(c), int(r)


def _cid(p) -> str:
    return f"{p[0]},{p[1]}"


@dataclass
class ZolaState:
    size: int = 6
    board: dict = field(default_factory=dict)  # (c, r) -> seat
    to_move: int = RED
    ply: int = 0
    last: Optional[list] = None                # [from_id, to_id]
    _moves: Optional[list] = field(default=None, repr=False, compare=False)


class Zola(Game):
    name = "Zola"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ZolaState:
        opts = options or {}
        size = int(opts.get("size", 6))
        if size < 2 or size % 2:
            raise ValueError("board side must be an even number >= 2")
        return ZolaState(size=size, board=_setup(size))

    def current_player(self, s: ZolaState) -> int:
        return s.to_move

    # ---- move generation -----------------------------------------------------

    def _seat_moves(self, s: ZolaState, seat: int) -> list:
        """All non-pass moves for `seat` (regardless of whose turn it is)."""
        n = s.size
        board = s.board
        out = []
        for (c, r), owner in board.items():
            if owner != seat:
                continue
            src = _d2(c, r, n)
            for dc, dr in DIRS:
                x, y = c + dc, r + dr
                first = True
                while 0 <= x < n and 0 <= y < n:
                    occ = board.get((x, y))
                    if occ is None:
                        # king-step non-capture: strictly AWAY from center
                        if first and _d2(x, y, n) > src:
                            out.append(f"{c},{r}>{x},{y}")
                    else:
                        # queen-slide capture: maintain or decrease distance
                        if occ != seat and _d2(x, y, n) <= src:
                            out.append(f"{c},{r}>{x},{y}")
                        break  # any checker ends the slide
                    x += dc
                    y += dr
                    first = False
        return sorted(out)

    def _moves_cached(self, s: ZolaState) -> list:
        if s._moves is None:
            s._moves = self._seat_moves(s, s.to_move)
        return s._moves

    def _counts(self, s: ZolaState) -> list:
        counts = [0, 0]
        for owner in s.board.values():
            counts[owner] += 1
        return counts

    def legal_moves(self, s: ZolaState) -> list:
        if self.is_terminal(s):
            return []
        moves = self._moves_cached(s)
        # "If he has no moves available, he must sit the game out": forced pass.
        return moves if moves else ["pass"]

    def is_terminal(self, s: ZolaState) -> bool:
        counts = self._counts(s)
        if counts[RED] == 0 or counts[BLUE] == 0:
            return True  # all of somebody's checkers captured
        if self._moves_cached(s):
            return False
        # Mover is stuck; if the opponent is stuck too, nothing can ever change
        # (draw backstop — per the rule sheet this position cannot occur).
        return not self._seat_moves(s, 1 - s.to_move)

    # ---- apply -----------------------------------------------------------------

    def apply_move(self, s: ZolaState, move: str, rng=None) -> ZolaState:
        if self.is_terminal(s):
            raise ValueError("game is over")
        if move == "pass":
            if self._moves_cached(s):
                raise ValueError("pass is only allowed when you have no moves")
            return ZolaState(size=s.size, board=dict(s.board),
                             to_move=1 - s.to_move, ply=s.ply + 1, last=None)
        if move not in self._moves_cached(s):
            self._explain_illegal(s, move)  # raises ValueError with a reason
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        board = dict(s.board)
        del board[frm]
        board[to] = s.to_move  # a capture replaces the enemy checker
        return ZolaState(size=s.size, board=board, to_move=1 - s.to_move,
                         ply=s.ply + 1, last=[fs, ts])

    def _explain_illegal(self, s: ZolaState, move: str):
        """Raise a ValueError explaining why `move` is not legal."""
        try:
            fs, ts = move.split(">")
            frm, to = _cell(fs), _cell(ts)
        except ValueError:
            raise ValueError(f"bad move syntax {move!r}")
        n = s.size
        if not (0 <= frm[0] < n and 0 <= frm[1] < n and 0 <= to[0] < n and 0 <= to[1] < n):
            raise ValueError(f"{move!r}: off the board")
        if s.board.get(frm) != s.to_move:
            raise ValueError(f"{move!r}: no {SEAT_NAMES[s.to_move]} checker on {fs}")
        dc, dr = to[0] - frm[0], to[1] - frm[1]
        if not (dc == 0 or dr == 0 or abs(dc) == abs(dr)) or (dc, dr) == (0, 0):
            raise ValueError(f"{move!r}: not a straight (rook/bishop) line")
        src, dst = _d2(*frm, n), _d2(*to, n)
        if to in s.board:
            if s.board[to] == s.to_move:
                raise ValueError(f"{move!r}: cannot capture your own checker")
            if dst > src:
                raise ValueError(f"{move!r}: a capture must maintain or decrease "
                                 "the distance to the center")
            raise ValueError(f"{move!r}: capture path is blocked")
        if max(abs(dc), abs(dr)) > 1:
            raise ValueError(f"{move!r}: non-capturing moves are a single king step")
        if dst <= src:
            raise ValueError(f"{move!r}: a non-capturing move must increase "
                             "the distance to the center")
        raise ValueError(f"{move!r}: illegal move")

    def returns(self, s: ZolaState) -> list:
        counts = self._counts(s)
        if counts[BLUE] == 0:
            return [1.0, -1.0]
        if counts[RED] == 0:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # mutually-stuck backstop; unreachable per the PDF

    # ---- heuristic (MCTS rollout cutoff) ----------------------------------------

    def heuristic(self, s: ZolaState) -> list:
        """Material balance — the object is to capture ALL enemy checkers."""
        counts = self._counts(s)
        score_red = tanh((counts[RED] - counts[BLUE]) / 4.0)
        return [score_red, -score_red]

    # ---- serialize ----------------------------------------------------------------

    def serialize(self, s: ZolaState) -> dict:
        return {
            "size": s.size,
            "board": {_cid(p): seat for p, seat in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "last": list(s.last) if s.last else None,
        }

    def deserialize(self, d: dict) -> ZolaState:
        return ZolaState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            last=list(d["last"]) if d.get("last") else None,
        )

    # ---- presentation ---------------------------------------------------------------

    def describe_move(self, s: ZolaState, move: str) -> str:
        if move == "pass":
            return "pass (no moves available)"
        fs, ts = move.split(">")
        if _cell(ts) in s.board:
            return f"{fs} x {ts}"
        return f"{fs} > {ts}"

    def render(self, s: ZolaState, perspective=None) -> dict:
        pieces = [{"cell": _cid(p), "owner": seat} for p, seat in s.board.items()]
        highlights = []
        if s.last:
            highlights.append({"cell": s.last[0], "kind": "last-move"})
            highlights.append({"cell": s.last[1], "kind": "last-move"})
        counts = self._counts(s)
        if counts[RED] == 0 or counts[BLUE] == 0:
            w = RED if counts[BLUE] == 0 else BLUE
            caption = f"{SEAT_NAMES[w]} captured every enemy checker — {SEAT_NAMES[w]} wins!"
        elif self.is_terminal(s):
            caption = "Neither player can move — draw (backstop; per the rules unreachable)"
        else:
            caption = (f"{SEAT_NAMES[s.to_move]} to move "
                       f"(Red {counts[RED]}, Blue {counts[BLUE]})")
            if not self._moves_cached(s):
                caption = f"{SEAT_NAMES[s.to_move]} has no moves and must pass"
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
