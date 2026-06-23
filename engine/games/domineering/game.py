"""Domineering — the classic combinatorial domino game (Göran Andersson;
popularised by Berlekamp, Conway & Guy in *Winning Ways*).

Two players place dominoes on a rectangular grid (default 8x8). The board starts
empty. On a turn a player covers two adjacent empty on-board cells with one
domino:

* **Player 0 — Vertical**: a domino covering (c, r) and (c, r+1).
* **Player 1 — Horizontal**: a domino covering (c, r) and (c+1, r).

There are no captures and pieces never move. **Normal play**: the player who
cannot place a domino on their turn LOSES (equivalently, the last player to place
a domino wins). Vertical (player 0) moves first.

Each placement fills two cells, so the game is strictly bounded and always
terminates. A move is written as the two covered cells as a path,
``"c,r>c2,r2"`` (click the two cells).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

VERTICAL, HORIZONTAL = 0, 1


@dataclass
class DomState:
    width: int = 8
    height: int = 8
    board: dict = field(default_factory=dict)   # (c, r) -> owner (0 vertical / 1 horizontal)
    to_move: int = VERTICAL
    last: tuple = ()                              # cells covered by the last domino (for highlight)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


# Accepted size option choices -> (width, height). Keys are option values.
SIZES = {
    "6x6": (6, 6),
    "7x7": (7, 7),
    "8x8": (8, 8),
    "9x9": (9, 9),
    "10x10": (10, 10),
    "8x6": (8, 6),
    "6x8": (6, 8),
}


class Domineering(Game):
    uid = "domineering"
    name = "Domineering"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DomState:
        opts = options or {}
        size = opts.get("size", "8x8")
        w, h = SIZES.get(size, (8, 8))
        return DomState(width=w, height=h)

    def current_player(self, s: DomState) -> int:
        return s.to_move

    def _domino_cells(self, s: DomState, c: int, r: int, who: int):
        """The pair of cells a player `who` covers anchored at (c, r), or None
        if it runs off the board."""
        if who == VERTICAL:
            other = (c, r + 1)
            if r + 1 >= s.height:
                return None
        else:
            other = (c + 1, r)
            if c + 1 >= s.width:
                return None
        return (c, r), other

    def legal_moves(self, s: DomState) -> list[str]:
        moves = []
        who = s.to_move
        for r in range(s.height):
            for c in range(s.width):
                if (c, r) in s.board:
                    continue
                pair = self._domino_cells(s, c, r, who)
                if pair is None:
                    continue
                a, b = pair
                if b in s.board:
                    continue
                moves.append(f"{a[0]},{a[1]}>{b[0]},{b[1]}")
        return moves

    def apply_move(self, s: DomState, move: str, rng=None) -> DomState:
        a_s, b_s = move.split(">")
        a, b = _cell(a_s), _cell(b_s)
        who = s.to_move
        # Validate: both cells on-board, empty, and form this player's orientation.
        if not self._on_board(s, a) or not self._on_board(s, b):
            raise ValueError(f"off-board domino: {move}")
        if a in s.board or b in s.board:
            raise ValueError(f"overlapping domino: {move}")
        pair = self._domino_cells(s, a[0], a[1], who)
        if pair is None or set(pair) != {a, b}:
            raise ValueError(f"illegal orientation for player {who}: {move}")
        board = dict(s.board)
        board[a] = who
        board[b] = who
        return DomState(
            width=s.width,
            height=s.height,
            board=board,
            to_move=1 - who,
            last=(a, b),
        )

    def _on_board(self, s: DomState, cell) -> bool:
        c, r = cell
        return 0 <= c < s.width and 0 <= r < s.height

    def is_terminal(self, s: DomState) -> bool:
        return len(self.legal_moves(s)) == 0

    def returns(self, s: DomState) -> list[float]:
        # Normal play: the player to move (who has no legal move) loses.
        loser = s.to_move
        winner = 1 - loser
        out = [0.0, 0.0]
        out[winner] = 1.0
        out[loser] = -1.0
        return out

    def serialize(self, s: DomState) -> dict:
        return {
            "width": s.width,
            "height": s.height,
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "to_move": s.to_move,
            "last": [f"{c},{r}" for (c, r) in s.last],
        }

    def deserialize(self, d: dict) -> DomState:
        return DomState(
            width=d["width"],
            height=d["height"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            last=tuple(_cell(x) for x in d.get("last", [])),
        )

    def describe_move(self, s: DomState, move: str) -> str:
        a_s, b_s = move.split(">")
        a, b = _cell(a_s), _cell(b_s)
        who = "V" if s.to_move == VERTICAL else "H"
        return f"{who}:{a[0] + 1},{a[1] + 1}-{b[0] + 1},{b[1] + 1}"

    def render(self, s: DomState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": v} for (c, r), v in s.board.items()]
        last_cells = {f"{c},{r}" for (c, r) in s.last}
        highlights = [{"cell": cid, "kind": "last-move"} for cid in last_cells]
        if self.is_terminal(s):
            winner = "Vertical" if (1 - s.to_move) == VERTICAL else "Horizontal"
            caption = f"{winner} wins (opponent cannot place a domino)"
        else:
            who = "Vertical" if s.to_move == VERTICAL else "Horizontal"
            caption = f"{who} to move"
        return {
            "board": {"type": "square", "width": s.width, "height": s.height},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
