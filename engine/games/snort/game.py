"""Snort — Simon Norton's combinatorial game, the dual of Col, on a square grid.

Two players each own a colour (player 0 / player 1). On your turn you colour one
EMPTY cell with YOUR colour, subject to the single placement restriction:

    the cell must NOT be orthogonally adjacent to a cell already holding the
    OPPONENT's colour.

It MAY be orthogonally adjacent to your OWN colour (same colours may sit side by
side), and diagonal adjacency is never restricted. Stones never move and are
never captured.

NORMAL PLAY convention: the player who cannot move (has no legal placement)
LOSES — equivalently, the last player able to place a stone WINS. Play is finite
(every move fills a cell; at most width*height placements), so termination is
automatic.

A move is a single cell id "c,r". This game is the exact DUAL of Col: Col forbids
placing next to your OWN colour; Snort forbids placing next to the OPPONENT's
colour. Only the adjacency test differs between the two packages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]


@dataclass
class SnortState:
    width: int = 5
    height: int = 5
    board: dict = field(default_factory=dict)   # (c, r) -> 0 | 1 (owner)
    to_move: int = 0
    winner: Optional[int] = None                 # set when the game ends


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


class Snort(Game):
    uid = "snort"
    name = "Snort"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SnortState:
        options = options or {}
        size = int(options.get("size", 5))
        return SnortState(width=size, height=size)

    def current_player(self, s: SnortState) -> int:
        return s.to_move

    def _legal_cells(self, s: SnortState, player: int):
        opponent = 1 - player
        cells = []
        for c in range(s.width):
            for r in range(s.height):
                if (c, r) in s.board:
                    continue
                # Forbidden if orthogonally adjacent to one of the OPPONENT's stones.
                bad = False
                for dc, dr in ORTHO:
                    if s.board.get((c + dc, r + dr)) == opponent:
                        bad = True
                        break
                if not bad:
                    cells.append((c, r))
        return cells

    def legal_moves(self, s: SnortState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in self._legal_cells(s, s.to_move)]

    def apply_move(self, s: SnortState, move: str, rng=None) -> SnortState:
        cell = _cell(move)
        board = dict(s.board)
        board[cell] = s.to_move
        nxt = 1 - s.to_move
        ns = SnortState(width=s.width, height=s.height, board=board,
                        to_move=nxt, winner=s.winner)
        # If the next player has no legal move, the mover (s.to_move) wins.
        if ns.winner is None and not self._legal_cells(ns, nxt):
            ns.winner = s.to_move
        return ns

    def is_terminal(self, s: SnortState) -> bool:
        return s.winner is not None

    def returns(self, s: SnortState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: SnortState) -> dict:
        return {
            "width": s.width,
            "height": s.height,
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> SnortState:
        return SnortState(
            width=d["width"],
            height=d["height"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
        )

    def describe_move(self, s: SnortState, move: str) -> str:
        c, r = _cell(move)
        who = "P1" if s.to_move == 0 else "P2"
        return f"{who}:{c + 1},{r + 1}"

    def render(self, s: SnortState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": v}
                  for (c, r), v in s.board.items()]
        if s.winner is not None:
            caption = f"{'Player 1' if s.winner == 0 else 'Player 2'} wins (last to move)"
        else:
            caption = f"{'Player 1' if s.to_move == 0 else 'Player 2'} to move"
        return {
            "board": {"type": "square", "width": s.width, "height": s.height},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
