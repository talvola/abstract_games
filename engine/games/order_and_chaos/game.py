"""Order and Chaos — a 6x6 asymmetric tic-tac-toe variant (Stephen Sniderman).

On every turn the player to move places EITHER an X or an O on any empty cell —
both players may use both symbols. Player 0 is **Order**, who wins by making a
line of exactly **five** like symbols (horizontal, vertical, or diagonal). Player
1 is **Chaos**, who wins by **filling the board** with no such line. A run of six
does NOT count as a win for Order. Order moves first.

Each move is a cell plus a symbol choice, written with the platform's choice
suffix: "c,r=X" or "c,r=O" — clicking an empty cell pops a small X/O picker.
Termination is automatic: at most 36 placements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 6
WIN = 5
ORDER, CHAOS = 0, 1
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
SYMBOL_OWNER = {"X": 0, "O": 1}      # only for piece colour in the renderer


@dataclass
class OCState:
    board: dict = field(default_factory=dict)   # (c, r) -> "X" | "O"
    to_move: int = ORDER
    winner: Optional[int] = None                  # set to ORDER when a 5-line appears


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


class OrderAndChaos(Game):
    uid = "order_and_chaos"
    name = "Order and Chaos"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> OCState:
        return OCState()

    def current_player(self, s: OCState) -> int:
        return s.to_move

    def legal_moves(self, s: OCState) -> list[str]:
        if self.is_terminal(s):
            return []
        empties = [(c, r) for c in range(N) for r in range(N) if (c, r) not in s.board]
        return [f"{c},{r}={sym}" for (c, r) in empties for sym in ("X", "O")]

    def _makes_five(self, board: dict, cell, sym: str) -> bool:
        """True if `sym` at `cell` completes a run of EXACTLY five (six doesn't win)."""
        c, r = cell
        for dc, dr in DIRS:
            run = 1
            for sign in (1, -1):
                cc, rr = c + dc * sign, r + dr * sign
                while board.get((cc, rr)) == sym:
                    run += 1
                    cc += dc * sign
                    rr += dr * sign
            if run == WIN:
                return True
        return False

    def apply_move(self, s: OCState, move: str, rng=None) -> OCState:
        cs, sym = move.split("=")
        cell = _cell(cs)
        board = dict(s.board)
        board[cell] = sym
        winner = s.winner if s.winner is not None else (
            ORDER if self._makes_five(board, cell, sym) else None)
        return OCState(board=board, to_move=1 - s.to_move, winner=winner)

    def is_terminal(self, s: OCState) -> bool:
        return s.winner is not None or len(s.board) == N * N

    def returns(self, s: OCState) -> list[float]:
        # Order wins on a five-line; otherwise a full board is a Chaos win.
        if s.winner == ORDER:
            return [1.0, -1.0]
        return [-1.0, 1.0]

    def serialize(self, s: OCState) -> dict:
        return {
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> OCState:
        return OCState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
        )

    def describe_move(self, s: OCState, move: str) -> str:
        cs, sym = move.split("=")
        c, r = _cell(cs)
        who = "Order" if s.to_move == ORDER else "Chaos"
        return f"{who}:{sym}@{c + 1},{r + 1}"

    def render(self, s: OCState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": SYMBOL_OWNER[v], "label": v}
                  for (c, r), v in s.board.items()]
        if s.winner == ORDER:
            caption = "Order wins (five in a row)"
        elif self.is_terminal(s):
            caption = "Chaos wins (board full)"
        else:
            caption = f"{'Order' if s.to_move == ORDER else 'Chaos'} to move (place X or O)"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
