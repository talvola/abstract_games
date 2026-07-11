"""Dodo — Mark Steere (May 2021).

Two players, Red and Blue, on a hexagonal grid of hexagons (a "hexhex" board,
side 4 by default = 37 cells, per the official rule sheet's Figure 1: 13
checkers each). Red moves first; players alternate moving ONE of their own
checkers per turn; passing is not allowed.

MOVES (from the PDF, marksteeregames.com/Dodo_rules.pdf): "All moves are to
unoccupied cells. Players can move their checkers one cell directly forward or
diagonally forward." There are no captures and no jumps; the three forward
directions are fixed per player (toward the opponent's home corner) and never
depend on where the checker stands.

OBJECT: "If at the beginning of your turn you have no moves available, you
win." (Misere blocking — being stuck is VICTORY.)

Orientation: the platform's hex renderer draws pointy-top hexes with corner
cells at the left/right extremes, so this port shows the rule sheet's figure
rotated a quarter turn: Red's flock starts in the LEFT corner region and flies
rightward (screen E / NE / SE = axial (1,0), (1,-1), (0,1)); Blue starts in
the RIGHT corner and flies leftward (W / NW / SW). Game-logically identical
to the PDF's vertical diagram (hex-grid graph isomorphism).

Setup (transcribed from Figure 1): every cell strictly beyond the central
three "pixel columns" is filled — with x = 2q + r, Red occupies all cells with
x <= -2, Blue all cells with x >= +2, and the 11-cell band x in {-1, 0, +1}
starts empty. On side 4 this reproduces the figure exactly (13 checkers each,
per-row counts 1,2,2,3,2,2,1 from each player's corner). Other board sizes
extend the same pattern (the PDF says "a hexagonal grid of any size" but
diagrams only side 4; BGA plays side 4).

Termination: every move strictly increases the mover's sum of forward
progress (2q+r moves by +1 or +2 for Red, mirrored for Blue), which is
bounded, so play cannot loop and repetition is impossible; someone is
eventually stuck and wins. A genuine draw is therefore unreachable; the
ply-cap draw below is only the platform-mandated backstop and is set ABOVE
the provable maximum game length.

Moves are "q,r>q,r" axial cell paths (click source, then destination).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import tanh
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1  # Red = seat 0, moves first (per the PDF)

# Renderer geometry: x = sqrt3*(q + r/2), y = 1.5*r (pointy-top axial).
# Red flies toward +x: E, NE, SE. Blue mirrors: W, NW, SW.
DIRS = {
    RED: ((1, 0), (1, -1), (0, 1)),
    BLUE: ((-1, 0), (0, -1), (-1, 1)),
}
SEAT_NAMES = ("Red", "Blue")


def _cells(size: int) -> list:
    n = size - 1
    return [(q, r) for q in range(-n, n + 1) for r in range(-n, n + 1)
            if abs(q + r) <= n]


def _setup(size: int) -> dict:
    """Figure-1 setup: fill everything outside the central 3-half-column band."""
    board = {}
    for (q, r) in _cells(size):
        x = 2 * q + r
        if x <= -2:
            board[(q, r)] = RED
        elif x >= 2:
            board[(q, r)] = BLUE
    return board


def _ply_cap(size: int) -> int:
    """A provable upper bound on game length + slack.

    Each move raises the mover's progress sum P = sum over their checkers of
    sgn*(2q+r) (sgn=+1 Red, -1 Blue) by exactly +1 or +2, and P can never
    exceed the sum of its checker-count largest cell values. Total moves is
    therefore at most the two players' combined headroom (185 on side 4);
    real games end far earlier. We add slack and use it only as a backstop.
    """
    if size in _PLY_CAP_CACHE:
        return _PLY_CAP_CACHE[size]
    vals = sorted((2 * q + r for (q, r) in _cells(size)), reverse=True)
    board = _setup(size)
    cap = 1
    for seat, sgn in ((RED, 1), (BLUE, -1)):
        init = sum(sgn * (2 * q + r) for (q, r), c in board.items() if c == seat)
        count = sum(1 for c in board.values() if c == seat)
        cap += sum(vals[:count]) - init  # vals are symmetric under negation
    _PLY_CAP_CACHE[size] = cap + 16
    return _PLY_CAP_CACHE[size]


_PLY_CAP_CACHE: dict = {}


def _cell(sid: str):
    q, r = sid.split(",")
    return int(q), int(r)


def _cid(p) -> str:
    return f"{p[0]},{p[1]}"


@dataclass
class DodoState:
    size: int = 4
    board: dict = field(default_factory=dict)  # (q, r) -> seat
    to_move: int = RED
    ply: int = 0
    drawn: bool = False                        # ply-cap backstop (unreachable)
    last: Optional[list] = None                # [from_id, to_id]
    _moves: Optional[list] = field(default=None, repr=False, compare=False)


class Dodo(Game):
    name = "Dodo"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DodoState:
        opts = options or {}
        size = int(opts.get("size", 4))
        if size < 2:
            raise ValueError("board side must be >= 2")
        return DodoState(size=size, board=_setup(size))

    def current_player(self, s: DodoState) -> int:
        return s.to_move

    # ---- move generation -----------------------------------------------------

    def _on_board(self, s: DodoState, p) -> bool:
        n = s.size - 1
        return abs(p[0]) <= n and abs(p[1]) <= n and abs(p[0] + p[1]) <= n

    def _moves_cached(self, s: DodoState) -> list:
        if s._moves is None:
            moves = []
            for (q, r), seat in s.board.items():
                if seat != s.to_move:
                    continue
                for dq, dr in DIRS[seat]:
                    t = (q + dq, r + dr)
                    if self._on_board(s, t) and t not in s.board:
                        moves.append(f"{q},{r}>{t[0]},{t[1]}")
            s._moves = sorted(moves)
        return s._moves

    def legal_moves(self, s: DodoState) -> list:
        return [] if s.drawn else self._moves_cached(s)

    def is_terminal(self, s: DodoState) -> bool:
        # No moves at the start of your turn => YOU win (computed live, so
        # hand-built stuck positions are terminal too).
        return s.drawn or not self._moves_cached(s)

    # ---- apply -----------------------------------------------------------------

    def apply_move(self, s: DodoState, move: str, rng=None) -> DodoState:
        try:
            fs, ts = move.split(">")
            frm, to = _cell(fs), _cell(ts)
        except ValueError:
            raise ValueError(f"bad move syntax {move!r}")
        if s.drawn:
            raise ValueError("game is over")
        if s.board.get(frm) != s.to_move:
            raise ValueError(f"{move!r}: no {SEAT_NAMES[s.to_move]} checker on {fs}")
        if (to[0] - frm[0], to[1] - frm[1]) not in DIRS[s.to_move]:
            raise ValueError(f"{move!r}: not a forward step")
        if not self._on_board(s, to):
            raise ValueError(f"{move!r}: off the board")
        if to in s.board:
            raise ValueError(f"{move!r}: destination occupied (no captures/jumps)")
        board = dict(s.board)
        del board[frm]
        board[to] = s.to_move
        ply = s.ply + 1
        return DodoState(size=s.size, board=board, to_move=1 - s.to_move,
                         ply=ply, drawn=ply >= _ply_cap(s.size),
                         last=[fs, ts])

    def returns(self, s: DodoState) -> list:
        if s.drawn:
            return [0.0, 0.0]  # backstop only; a real draw is unreachable
        # terminal because the player to move has no moves: they WIN.
        return [1.0, -1.0] if s.to_move == RED else [-1.0, 1.0]

    # ---- heuristic (MCTS rollout cutoff) ----------------------------------------

    def heuristic(self, s: DodoState) -> list:
        """Misere mobility: you want FEW moves for yourself, many for them."""
        mob = [0, 0]
        for (q, r), seat in s.board.items():
            for dq, dr in DIRS[seat]:
                t = (q + dq, r + dr)
                if self._on_board(s, t) and t not in s.board:
                    mob[seat] += 1
        score_red = tanh((mob[BLUE] - mob[RED]) / 6.0)
        return [score_red, -score_red]

    # ---- serialize ----------------------------------------------------------------

    def serialize(self, s: DodoState) -> dict:
        return {
            "size": s.size,
            "board": {_cid(p): seat for p, seat in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "drawn": s.drawn,
            "last": list(s.last) if s.last else None,
        }

    def deserialize(self, d: dict) -> DodoState:
        return DodoState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            drawn=d.get("drawn", False),
            last=list(d["last"]) if d.get("last") else None,
        )

    # ---- presentation ---------------------------------------------------------------

    def describe_move(self, s: DodoState, move: str) -> str:
        return move.replace(">", " > ")

    def render(self, s: DodoState, perspective=None) -> dict:
        pieces = [{"cell": _cid(p), "owner": seat} for p, seat in s.board.items()]
        highlights = []
        if s.last:
            highlights.append({"cell": s.last[0], "kind": "last-move"})
            highlights.append({"cell": s.last[1], "kind": "last-move"})
        if s.drawn:
            caption = "Draw (ply-cap backstop)"
        elif self.is_terminal(s):
            w = SEAT_NAMES[s.to_move]
            caption = f"{w} cannot move — {w} wins!"
        else:
            caption = f"{SEAT_NAMES[s.to_move]} to move ({'→' if s.to_move == RED else '←'})"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
