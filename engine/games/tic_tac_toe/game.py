"""Tic-Tac-Toe -- the minimal reference game module.

The smallest complete example of the Game contract: deterministic, perfect
information, square board, fixed two players. Read this first when authoring a
new game; see SPEC.md for the full contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# Cells are addressed "col,row" with col,row in 0..2. Player 0 = X, 1 = O.
LINES = [
    [(0, 0), (1, 0), (2, 0)], [(0, 1), (1, 1), (2, 1)], [(0, 2), (1, 2), (2, 2)],
    [(0, 0), (0, 1), (0, 2)], [(1, 0), (1, 1), (1, 2)], [(2, 0), (2, 1), (2, 2)],
    [(0, 0), (1, 1), (2, 2)], [(2, 0), (1, 1), (0, 2)],
]
MARKS = {0: "X", 1: "O"}


@dataclass
class TTTState:
    # board[(col, row)] -> 0 or 1
    board: dict = field(default_factory=dict)
    to_move: int = 0
    winner: Optional[int] = None  # 0, 1, or None (None + full board = draw)


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


class TicTacToe(Game):
    uid = "tic_tac_toe"
    name = "Tic-Tac-Toe"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> TTTState:
        return TTTState()

    def current_player(self, s: TTTState) -> int:
        return s.to_move

    def legal_moves(self, s: TTTState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for c in range(3) for r in range(3) if (c, r) not in s.board]

    def apply_move(self, s: TTTState, move: str, rng=None) -> TTTState:
        cell = _cell(move)
        board = dict(s.board)
        board[cell] = s.to_move
        winner = None
        for line in LINES:
            if all(board.get(c) == s.to_move for c in line):
                winner = s.to_move
                break
        return TTTState(board=board, to_move=1 - s.to_move, winner=winner)

    def is_terminal(self, s: TTTState) -> bool:
        return s.winner is not None or len(s.board) == 9

    def returns(self, s: TTTState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: TTTState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> TTTState:
        return TTTState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
        )

    def render(self, s: TTTState, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": MARKS[p]}
            for (c, r), p in s.board.items()
        ]
        if s.winner is not None:
            caption = f"{MARKS[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            caption = f"{MARKS[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": 3, "height": 3},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
