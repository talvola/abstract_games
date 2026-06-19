"""Breakthrough — Dan Troyka's 2000 race game (8x8).

Each side starts with two full rows of identical pawns (White on rows 0-1, Black
on rows 6-7). A pawn moves one square straight or diagonally FORWARD to an empty
square, or captures one square DIAGONALLY forward onto an enemy pawn (no straight
capture, never sideways or backward). You win the instant one of your pawns
reaches the opponent's home row; a player with no legal move loses.

Moves are clickable cell paths "from>to". Player 0 = White (advances toward row 7),
player 1 = Black (toward row 0). Termination is structural: every move advances a
pawn one row forward (and captures also remove material), so play strictly
progresses and cannot cycle — no draws.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 8
NAMES = {0: "White", 1: "Black"}


@dataclass
class BTState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {}
    for c in range(N):
        b[(c, 0)] = b[(c, 1)] = 0
        b[(c, 6)] = b[(c, 7)] = 1
    return b


def _fwd(player: int) -> int:
    return 1 if player == 0 else -1


def _far_row(player: int) -> int:
    return N - 1 if player == 0 else 0


class Breakthrough(Game):
    uid = "breakthrough"
    name = "Breakthrough"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> BTState:
        return BTState(board=_start_board())

    def current_player(self, s: BTState) -> int:
        return s.to_move

    def _moves(self, s: BTState) -> list:
        out = []
        dr = _fwd(s.to_move)
        for (c, r), pl in s.board.items():
            if pl != s.to_move:
                continue
            nr = r + dr
            # straight forward: only to an empty square
            if _on(c, nr) and (c, nr) not in s.board:
                out.append(((c, r), (c, nr)))
            # diagonals: to empty, or capture an enemy
            for dc in (-1, 1):
                nc = c + dc
                if not _on(nc, nr):
                    continue
                occ = s.board.get((nc, nr))
                if occ is None or occ != s.to_move:
                    out.append(((c, r), (nc, nr)))
        return out

    def legal_moves(self, s: BTState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    def apply_move(self, s: BTState, move: str, rng=None) -> BTState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        pl = board.pop(frm)
        board[to] = pl                                  # capture overwrites the dest
        winner = pl if to[1] == _far_row(pl) else None
        return BTState(board=board, to_move=1 - pl, winner=winner)

    def is_terminal(self, s: BTState) -> bool:
        return s.winner is not None or not self._moves(s)

    def returns(self, s: BTState) -> list[float]:
        w = s.winner if s.winner is not None else 1 - s.to_move  # no move -> to_move loses
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def serialize(self, s: BTState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> BTState:
        return BTState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
        )

    def describe_move(self, s: BTState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        cap = to in s.board
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{alg(frm)}{'x' if cap else '-'}{alg(to)}"

    def render(self, s: BTState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
