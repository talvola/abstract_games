"""Fox and Hounds — a traditional asymmetric hunt game.

Played on the dark squares of an 8x8 board. Player 0 is the lone FOX (moves one
square diagonally in ANY direction). Player 1 is the four HOUNDS (each moves one
square diagonally FORWARD only — toward the fox's edge). No captures. The fox
moves first.

* The fox wins by reaching the hounds' starting edge (row 0), or if the hounds
  ever have no legal move.
* The hounds win by trapping the fox so it has no legal move.

The hounds can only advance, so the game always terminates (a ply cap guards
random play regardless). Moves are "from>to" cell paths (click a piece, then a
diagonally adjacent empty dark square).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 8
FOX, HOUND = 0, 1
PLY_CAP = 300
FOX_DIRS = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
HOUND_DIRS = [(1, 1), (-1, 1)]  # forward = toward higher r (the fox's edge)


@dataclass
class FHState:
    board: dict = field(default_factory=dict)  # (c, r) -> 0 (fox) / 1 (hound)
    to_move: int = FOX
    winner: Optional[int] = None  # only ever set to FOX (hounds win via no-move)
    drawn: bool = False
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {(c, 0): HOUND for c in (1, 3, 5, 7)}  # hounds on row-0 dark squares
    b[(4, 7)] = FOX                            # fox on a far-edge dark square
    return b


class FoxAndHounds(Game):
    uid = "fox_and_hounds"
    name = "Fox and Hounds"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> FHState:
        return FHState(board=_start_board())

    def current_player(self, s: FHState) -> int:
        return s.to_move

    def _raw_moves(self, s: FHState) -> list[str]:
        dirs = FOX_DIRS if s.to_move == FOX else HOUND_DIRS
        out = []
        for (c, r), pl in s.board.items():
            if pl != s.to_move:
                continue
            for dc, dr in dirs:
                tc, tr = c + dc, r + dr
                if _on(tc, tr) and (tc, tr) not in s.board:
                    out.append(f"{c},{r}>{tc},{tr}")
        return out

    def is_terminal(self, s: FHState) -> bool:
        return s.winner is not None or s.drawn or not self._raw_moves(s)

    def legal_moves(self, s: FHState) -> list[str]:
        return [] if self.is_terminal(s) else self._raw_moves(s)

    def apply_move(self, s: FHState, move: str, rng=None) -> FHState:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        mover = s.to_move
        board = dict(s.board)
        del board[frm]
        board[to] = mover
        winner = FOX if (mover == FOX and to[1] == 0) else None
        ply = s.ply + 1
        drawn = winner is None and ply >= PLY_CAP
        return FHState(board=board, to_move=1 - mover, winner=winner, drawn=drawn, ply=ply)

    def returns(self, s: FHState) -> list[float]:
        if s.winner == FOX:
            return [1.0, -1.0]
        if s.drawn:
            return [0.0, 0.0]
        # terminal because the player to move is stuck: they lose
        return [-1.0, 1.0] if s.to_move == FOX else [1.0, -1.0]

    def serialize(self, s: FHState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "drawn": s.drawn,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> FHState:
        return FHState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], winner=d["winner"],
            drawn=d.get("drawn", False), ply=d.get("ply", 0),
        )

    def describe_move(self, s: FHState, move: str) -> str:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        who = "F" if s.board.get(frm) == FOX else "H"
        return f"{who} {alg(frm)}-{alg(to)}"

    def render(self, s: FHState, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": "F" if p == FOX else ""}
            for (c, r), p in s.board.items()
        ]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret == [0.0, 0.0] else ("Fox wins" if ret[0] > 0 else "Hounds win")
        else:
            caption = "Fox to move" if s.to_move == FOX else "Hounds to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
