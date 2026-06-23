"""Squava — a 5x5 misère/positive hybrid n-in-a-row.

Two players alternately place a stone on an empty cell of a 5x5 square grid.
Stones never move or get captured (exactly like Gomoku). Player 0 (Black) moves
first.

After a player places a stone, the lines through that stone are evaluated:

- If the placer now has **four or more** of their stones in an unbroken row —
  horizontally, vertically, or diagonally — the placer **WINS** immediately.
- Otherwise, if the placer now has **exactly three** in a row (and no four), the
  placer **LOSES** immediately (the misère twist: making three is forbidden
  unless it is part of a four).
- **Four takes precedence**: if a placement simultaneously creates a three and a
  four, it is a WIN.

If the board fills (25 stones) with no four and no decisive three, the game is a
DRAW. There are no captures or movement, so the game always terminates in at most
25 placements.

Cells are "col,row"; a move is a single empty cell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZE = 5
WIN_LEN = 4
LOSE_LEN = 3
NAMES = {0: "Black", 1: "White"}
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


@dataclass
class SquavaState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None                # seat index that won, or None


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _max_run(board: dict, cell, player: int) -> int:
    """Longest unbroken run of `player`'s stones through `cell` over all 4 axes."""
    c, r = cell
    best = 1
    for dc, dr in DIRS:
        run = 1
        for sign in (1, -1):
            cc, rr = c + dc * sign, r + dr * sign
            while board.get((cc, rr)) == player:
                run += 1
                cc += dc * sign
                rr += dr * sign
        if run > best:
            best = run
    return best


class Squava(Game):
    uid = "squava"
    name = "Squava"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SquavaState:
        return SquavaState()

    def current_player(self, s: SquavaState) -> int:
        return s.to_move

    def legal_moves(self, s: SquavaState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for c in range(SIZE) for r in range(SIZE)
                if (c, r) not in s.board]

    def _outcome(self, board: dict, cell, player: int) -> Optional[int]:
        """Winner after `player` placed at `cell`, or None if game continues.

        Four-or-more in a row  -> placer wins (returns player).
        Exactly three (no four) -> placer loses (returns opponent).
        Otherwise               -> None.
        """
        run = _max_run(board, cell, player)
        if run >= WIN_LEN:
            return player
        if run == LOSE_LEN:
            return 1 - player
        return None

    def apply_move(self, s: SquavaState, move: str, rng=None) -> SquavaState:
        cell = _cell(move)
        board = dict(s.board)
        board[cell] = s.to_move
        winner = self._outcome(board, cell, s.to_move)
        return SquavaState(board=board, to_move=1 - s.to_move, winner=winner)

    def is_terminal(self, s: SquavaState) -> bool:
        return s.winner is not None or len(s.board) == SIZE * SIZE

    def returns(self, s: SquavaState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: SquavaState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> SquavaState:
        return SquavaState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
        )

    def describe_move(self, s: SquavaState, move: str) -> str:
        c, r = _cell(move)
        return f"{NAMES[s.to_move][0]}:{c + 1},{r + 1}"

    def render(self, s: SquavaState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
