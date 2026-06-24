"""Quantik (Nouri Khalifa / Gigamic, 2019) -- the shape-placement logic duel.

Board: 4x4 (cell ids "c,r", c/r in 0..3), partitioned into four 2x2 ZONES
(quadrants): the cells {(c,r): c in 0..1, r in 0..1} is the top-left zone, etc.

Each player owns EIGHT pieces in their own colour: two each of four SHAPES.
We label the four shapes A, B, C, D (cube/sphere/cylinder/cone in the physical
game). Pieces are held off-board in a per-seat reserve.

TURN.  Place one of your own reserved pieces (a shape) onto an empty cell,
SUBJECT to the placement restriction:

  * You may NOT place a shape into a row, column, or 2x2 zone in which the
    OPPONENT has already placed that SAME shape.
  * You MAY place a shape that matches one of YOUR OWN pieces already in that
    line/zone -- the restriction is only against the opponent's same shape.

(Verified against the official Gigamic rules / Wikipedia / BGG: "you are not
allowed to place a shape in a row, column or region in which your opponent has
a piece of the same shape".)

WIN.  The player who places the piece that COMPLETES any row, column, or 2x2
zone so that it contains all FOUR DIFFERENT shapes wins IMMEDIATELY -- the
piece COLOURS do not matter, only that the line/zone holds one of each shape
A,B,C,D. (Verified: "the first player to place the fourth different shape in a
row, column or region wins".)

LOSS.  A player who cannot make any legal placement on their turn LOSES (there
is no pass). (Verified: "if a player cannot make a valid move, they lose".)

Termination is bounded: at most 16 placements; a win or a no-legal-move loss
always ends the game, so random playouts terminate.

Move encoding (reserve-tray drop, mirroring Gobblet/Crazyhouse):
    "<shape>@c,r"  -- e.g. "A@1,2" drops shape A on cell (1,2).
The reserve key is the single shape letter, matching Board.jsx's DROP regex
``/^([A-Za-z0-9])@(-?\\d+,-?\\d+)$/`` and its click-to-drop reserve tray.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 4
SHAPES = ["A", "B", "C", "D"]
# A glyph per shape so the four read distinctly on the board.
SHAPE_GLYPH = {"A": "■", "B": "●", "C": "▮", "D": "▲"}
#                 A = filled square   B = filled circle  C = bar  D = triangle
SHAPE_NAME = {"A": "cube", "B": "sphere", "C": "cylinder", "D": "cone"}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _rows():
    return [[(c, r) for c in range(N)] for r in range(N)]


def _cols():
    return [[(c, r) for r in range(N)] for c in range(N)]


def _zones():
    out = []
    for zc in (0, 1):
        for zr in (0, 1):
            out.append([(zc * 2 + dc, zr * 2 + dr)
                        for dc in (0, 1) for dr in (0, 1)])
    return out


# Every line/zone group (rows, columns, four 2x2 quadrants).
GROUPS = _rows() + _cols() + _zones()


def _zone_of(c: int, r: int) -> int:
    """Index 0..3 of the 2x2 quadrant containing (c, r)."""
    return (r // 2) * 2 + (c // 2)


@dataclass
class QState:
    # board[(c, r)] -> (owner, shape)
    board: dict = field(default_factory=dict)
    # hands[owner] -> {shape: count} remaining off-board
    hands: dict = field(default_factory=dict)
    to_move: int = 0
    winner: Optional[int] = None  # set inside apply_move; None = ongoing/draw


class Quantik(Game):
    uid = "quantik"
    name = "Quantik"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> QState:
        hands = {0: {s: 2 for s in SHAPES}, 1: {s: 2 for s in SHAPES}}
        return QState(board={}, hands=hands, to_move=0, winner=None)

    def current_player(self, s: QState) -> int:
        return s.to_move

    # --- placement legality ----------------------------------------------
    def _opponent_has_shape(self, s: QState, opp: int, shape: str,
                            c: int, r: int) -> bool:
        """True iff the opponent already placed `shape` somewhere sharing the
        row, column, or 2x2 zone of cell (c, r)."""
        z = _zone_of(c, r)
        for (bc, br), (owner, sh) in s.board.items():
            if owner != opp or sh != shape:
                continue
            if bc == c or br == r or _zone_of(bc, br) == z:
                return True
        return False

    def _can_place(self, s: QState, shape: str, c: int, r: int) -> bool:
        if (c, r) in s.board:
            return False
        opp = 1 - s.to_move
        return not self._opponent_has_shape(s, opp, shape, c, r)

    def legal_moves(self, s: QState):
        if self.is_terminal(s):
            return []
        me = s.to_move
        avail = [sh for sh in SHAPES if s.hands[me].get(sh, 0) > 0]
        moves = []
        for c in range(N):
            for r in range(N):
                if (c, r) in s.board:
                    continue
                for sh in avail:
                    if self._can_place(s, sh, c, r):
                        moves.append(f"{sh}@{c},{r}")
        return moves

    # --- win detection ----------------------------------------------------
    @staticmethod
    def _group_complete(board: dict, group) -> bool:
        """True iff every cell of `group` is filled and the four shapes are all
        distinct (one each of A,B,C,D). Colours are irrelevant."""
        shapes = set()
        for cell in group:
            if cell not in board:
                return False
            shapes.add(board[cell][1])
        return len(shapes) == N

    def _is_win(self, board: dict) -> bool:
        return any(self._group_complete(board, g) for g in GROUPS)

    def apply_move(self, s: QState, move: str, rng=None) -> QState:
        shape, cell_s = move.split("@")
        cell = _cell(cell_s)
        me = s.to_move
        board = dict(s.board)
        hands = {p: dict(h) for p, h in s.hands.items()}

        board[cell] = (me, shape)
        hands[me][shape] -= 1

        winner = me if self._is_win(board) else None
        ns = QState(board=board, hands=hands,
                    to_move=me if winner is not None else 1 - me,
                    winner=winner)
        # Loss-on-no-move: if the next player to act has no legal placement,
        # they lose -> the player who just moved wins.
        if ns.winner is None and not self.legal_moves(ns):
            ns.winner = me
        return ns

    def is_terminal(self, s: QState) -> bool:
        return s.winner is not None or len(s.board) == N * N

    def returns(self, s: QState):
        if s.winner is None:
            return [0.0, 0.0]  # full board with no completed group: draw
        return [1.0 if i == s.winner else -1.0 for i in range(self.num_players)]

    # --- serialization ----------------------------------------------------
    def serialize(self, s: QState) -> dict:
        return {
            "board": {f"{c},{r}": [o, sh] for (c, r), (o, sh) in s.board.items()},
            "hands": {str(p): dict(h) for p, h in s.hands.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> QState:
        return QState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            hands={int(p): dict(h) for p, h in d["hands"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
        )

    def describe_move(self, s: QState, move: str) -> str:
        shape, cell_s = move.split("@")
        c, r = _cell(cell_s)
        return f"{SHAPE_NAME[shape]} ({shape}) @ {c + 1},{r + 1}"

    # --- rendering --------------------------------------------------------
    def render(self, s: QState, perspective=None) -> dict:
        pieces = []
        for (c, r), (owner, sh) in s.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": owner,
                "label": SHAPE_GLYPH[sh],
            })

        # Tint the four 2x2 quadrants in two alternating shades so the zones read.
        zone_tint = {0: "#2e2a33", 3: "#2e2a33", 1: "#262420", 2: "#262420"}
        tints = {}
        for c in range(N):
            for r in range(N):
                tints[f"{c},{r}"] = zone_tint[_zone_of(c, r)]

        # Heavy dividers between the four quadrants (cell-coordinate space).
        lines = [
            [[2.0, -0.5], [2.0, 3.5], "#000000"],   # vertical split
            [[-0.5, 2.0], [3.5, 2.0], "#000000"],   # horizontal split
        ]

        reserve = {str(p): {sh: n for sh, n in s.hands[p].items() if n > 0}
                   for p in (0, 1)}

        names = {0: "Red", 1: "Blue"}
        if s.winner is not None:
            cap = f"{names[s.winner]} wins (completed a line/zone with all 4 shapes)"
        elif self.is_terminal(s):
            cap = "Draw (board full)"
        else:
            cap = f"{names[s.to_move]} to move"

        return {
            "board": {"type": "square", "width": N, "height": N,
                      "tints": tints, "lines": lines},
            "pieces": pieces,
            "reserve": reserve,
            "highlights": [],
            "caption": cap,
        }
