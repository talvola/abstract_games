"""Starter template — a COMPLETE, working game you edit into your own.

As shipped this is "get N in a row" on a square board (like Gomoku): players
alternate placing a stone on an empty cell; first to line up `IN_A_ROW` wins; a
full board with no line is a draw. It already passes `agp validate`.

Replace the rules with your game. Keep the method signatures and the five
invariants in AGENTS.md / SPEC.md. The two things to change are usually:
`legal_moves` (what moves exist) and `apply_move` (what a move does + when the
game ends).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

IN_A_ROW = 4               # how many in a line wins
MARKS = {0: "X", 1: "O"}
DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]


@dataclass
class GameState:
    size: int = 5
    board: dict = field(default_factory=dict)  # (col, row) -> player index
    to_move: int = 0
    winner: Optional[int] = None               # set the moment someone wins


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


class MyGame(Game):
    # Identity (uid, name) comes from manifest.json — no need to repeat it here.
    # (You may set `uid`/`name` class attributes, but then keep them in sync.)

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> GameState:
        size = int((options or {}).get("size", 5))
        return GameState(size=size)

    def current_player(self, s: GameState) -> int:
        return s.to_move

    def legal_moves(self, s: GameState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [
            f"{c},{r}"
            for c in range(s.size)
            for r in range(s.size)
            if (c, r) not in s.board
        ]

    def apply_move(self, s: GameState, move: str, rng=None) -> GameState:
        c, r = _cell(move)
        board = dict(s.board)              # copy — never mutate the input
        board[(c, r)] = s.to_move
        winner = s.to_move if self._wins(board, c, r, s.to_move, s.size) else None
        return GameState(size=s.size, board=board, to_move=1 - s.to_move, winner=winner)

    def _wins(self, board, c, r, player, size) -> bool:
        for dc, dr in DIRECTIONS:
            count = 1
            for sign in (1, -1):
                cc, rr = c + dc * sign, r + dr * sign
                while board.get((cc, rr)) == player:
                    count += 1
                    cc += dc * sign
                    rr += dr * sign
            if count >= IN_A_ROW:
                return True
        return False

    def is_terminal(self, s: GameState) -> bool:
        return s.winner is not None or len(s.board) == s.size * s.size

    def returns(self, s: GameState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: GameState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> GameState:
        return GameState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
        )

    def render(self, s: GameState, perspective=None) -> dict:
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
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
