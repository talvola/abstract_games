"""Clobber — Albert, Grossman, Nowakowski & Wolfe (2001), a combinatorial game.

The board is a rectangular grid that starts COMPLETELY FILLED in a checkerboard:
cell (c, r) with (c + r) even holds player 0's stone, (c + r) odd holds player 1's.

A MOVE picks one of your own stones and moves it onto an orthogonally adjacent
cell that holds an OPPONENT's stone; that opponent stone is removed ("clobbered")
and yours occupies the cell. There are NO non-capturing moves — stones only ever
move onto an adjacent enemy.

NORMAL PLAY convention: the player to move who has no legal move LOSES (equivalently,
last to move wins). There are no draws. Termination is structural: every move removes
exactly one stone, so play lasts at most (#cells - 1) moves and cannot cycle.

Moves are clickable cell paths "c,r>c2,r2". Player 0 / player 1 stones render in
the two seat colours with a last-move highlight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

NAMES = {0: "Player 1", 1: "Player 2"}

# Board dimensions per `size` option, as (width, height).
SIZES = {
    "5x6": (5, 6),
    "6x5": (6, 5),
    "4x5": (4, 5),
    "8x8": (8, 8),
}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class CLState:
    board: dict = field(default_factory=dict)   # (c, r) -> player (0/1)
    to_move: int = 0
    width: int = 5
    height: int = 6
    last_move: Optional[tuple] = None           # ((c,r),(c2,r2)) or None


def _start_board(w: int, h: int) -> dict:
    # Every cell filled in a checkerboard: (c+r) even = player 0, odd = player 1.
    return {(c, r): (c + r) % 2 for c in range(w) for r in range(h)}


class Clobber(Game):
    uid = "clobber"
    name = "Clobber"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CLState:
        options = options or {}
        size = options.get("size", "5x6")
        w, h = SIZES.get(size, SIZES["5x6"])
        return CLState(board=_start_board(w, h), to_move=0, width=w, height=h)

    def current_player(self, s: CLState) -> int:
        return s.to_move

    def _moves(self, s: CLState) -> list:
        out = []
        opp = 1 - s.to_move
        for (c, r), pl in s.board.items():
            if pl != s.to_move:
                continue
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (c + dc, r + dr)
                if s.board.get(nb) == opp:          # adjacent enemy stone
                    out.append(((c, r), nb))
        return out

    def legal_moves(self, s: CLState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    def apply_move(self, s: CLState, move: str, rng=None) -> CLState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        pl = board.pop(frm)
        board[to] = pl                              # clobber: overwrite the enemy
        return CLState(board=board, to_move=1 - pl, width=s.width,
                       height=s.height, last_move=(frm, to))

    def is_terminal(self, s: CLState) -> bool:
        return not self._moves(s)

    def returns(self, s: CLState) -> list[float]:
        # No legal move for the player to move -> they lose (last to move wins).
        loser = s.to_move
        return [-1.0, 1.0] if loser == 0 else [1.0, -1.0]

    def serialize(self, s: CLState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "width": s.width,
            "height": s.height,
            "last_move": ([list(s.last_move[0]), list(s.last_move[1])]
                          if s.last_move else None),
        }

    def deserialize(self, d: dict) -> CLState:
        lm = d.get("last_move")
        return CLState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            width=d["width"],
            height=d["height"],
            last_move=((tuple(lm[0]), tuple(lm[1])) if lm else None),
        )

    def describe_move(self, s: CLState, move: str) -> str:
        frm, to = move.split(">")
        return f"{frm}x{to}"

    def render(self, s: CLState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p} for (c, r), p in s.board.items()]
        highlights = []
        if s.last_move:
            (fc, fr), (tc, tr) = s.last_move
            highlights = [
                {"cell": f"{fc},{fr}", "kind": "last-move"},
                {"cell": f"{tc},{tr}", "kind": "last-move"},
            ]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": s.width, "height": s.height},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
