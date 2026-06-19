"""Gomoku — Five in a Row (freestyle).

Players alternately place a stone on an empty intersection of a square grid
(13x13, 15x15, or 19x19 via the board-size option). Black (player 0) moves first.
The first player to get FIVE OR MORE of their own stones in an unbroken line —
horizontal, vertical, or diagonal — wins. A completely full board with no line is
a draw (vanishingly rare on the larger boards, but it bounds the game).

This is the freestyle variant: there are no restrictions on the first player and
overlines (six or more) also win. Cells are "col,row"; a move is a single empty
cell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

CONNECT = 5
NAMES = {0: "Black", 1: "White"}
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


@dataclass
class GomokuState:
    size: int = 15
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


class Gomoku(Game):
    uid = "gomoku"
    name = "Gomoku"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> GomokuState:
        size = int((options or {}).get("size", 15))
        return GomokuState(size=size)

    def current_player(self, s: GomokuState) -> int:
        return s.to_move

    def legal_moves(self, s: GomokuState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for c in range(s.size) for r in range(s.size)
                if (c, r) not in s.board]

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

    def apply_move(self, s: GomokuState, move: str, rng=None) -> GomokuState:
        cell = _cell(move)
        board = dict(s.board)
        board[cell] = s.to_move
        winner = s.to_move if self._wins(board, cell, s.to_move) else None
        return GomokuState(size=s.size, board=board, to_move=1 - s.to_move, winner=winner)

    def is_terminal(self, s: GomokuState) -> bool:
        return s.winner is not None or len(s.board) == s.size * s.size

    def returns(self, s: GomokuState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: GomokuState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> GomokuState:
        return GomokuState(
            size=d.get("size", 15),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
        )

    def describe_move(self, s: GomokuState, move: str) -> str:
        c, r = _cell(move)
        return f"{NAMES[s.to_move][0]}:{c + 1},{r + 1}"

    def render(self, s: GomokuState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
