"""Connect Four — the classic vertical four-in-a-row.

A 7-wide, 6-tall grid. On your turn you drop a disc into a column; it falls to
the lowest empty cell of that column. First to get four of their own discs in a
line — horizontal, vertical, or diagonal — wins. If the board fills with no line,
the game is a draw.

Cells are "col,row" with row 0 at the BOTTOM. A move is the single landing cell
(the lowest empty cell of a column), so each non-full column contributes exactly
one legal move and the UI shows it as a placement target. Player 0 = Red,
1 = Yellow. Termination is automatic: at most width*height (42) moves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WIDTH, HEIGHT, CONNECT = 7, 6, 4
NAMES = {0: "Red", 1: "Yellow"}
# the four line directions (and their opposites are covered by scanning both ways)
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


@dataclass
class C4State:
    board: dict = field(default_factory=dict)   # (col, row) -> player
    to_move: int = 0
    winner: Optional[int] = None


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


class ConnectFour(Game):
    uid = "connect_four"
    name = "Connect Four"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> C4State:
        return C4State()

    def current_player(self, s: C4State) -> int:
        return s.to_move

    def _landing(self, board: dict, col: int) -> Optional[int]:
        """Lowest empty row in `col`, or None if the column is full."""
        for r in range(HEIGHT):
            if (col, r) not in board:
                return r
        return None

    def legal_moves(self, s: C4State) -> list[str]:
        if self.is_terminal(s):
            return []
        out = []
        for c in range(WIDTH):
            r = self._landing(s.board, c)
            if r is not None:
                out.append(f"{c},{r}")
        return out

    def _wins(self, board: dict, cell, player: int) -> bool:
        c, r = cell
        for dc, dr in DIRS:
            run = 1
            for sign in (1, -1):
                cc, rr = c + dc * sign, r + dr * sign
                while board.get((cc, rr)) == player:
                    run += 1
                    cc += dc * sign
                    rr += dr * sign
            if run >= CONNECT:
                return True
        return False

    def apply_move(self, s: C4State, move: str, rng=None) -> C4State:
        cell = _cell(move)
        board = dict(s.board)
        board[cell] = s.to_move
        winner = s.to_move if self._wins(board, cell, s.to_move) else None
        return C4State(board=board, to_move=1 - s.to_move, winner=winner)

    def is_terminal(self, s: C4State) -> bool:
        return s.winner is not None or len(s.board) == WIDTH * HEIGHT

    def returns(self, s: C4State) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: C4State) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> C4State:
        return C4State(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
        )

    def describe_move(self, s: C4State, move: str) -> str:
        c, _ = _cell(move)
        return f"{NAMES[s.to_move][0]}:col {c + 1}"

    def render(self, s: C4State, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": WIDTH, "height": HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
