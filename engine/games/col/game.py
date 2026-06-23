"""Col — Colin Vout's map-colouring combinatorial game, on a square grid.

Two players each own a colour (player 0 / player 1). On your turn you colour one
EMPTY cell with YOUR colour, subject to the single placement restriction:

    the cell must NOT be orthogonally adjacent to a cell already holding YOUR
    OWN colour.

It MAY be orthogonally adjacent to the opponent's colour, and diagonal adjacency
is never restricted. Stones never move and are never captured.

NORMAL PLAY convention: the player who cannot move (has no legal placement)
LOSES — equivalently, the last player able to place a stone WINS. Play is finite
(every move fills a cell; at most width*height placements), so termination is
automatic.

A move is a single cell id "c,r". The dual game, Snort, instead forbids placing
next to the OPPONENT's colour; this package implements Col.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]


@dataclass
class ColState:
    width: int = 5
    height: int = 5
    board: dict = field(default_factory=dict)   # (c, r) -> 0 | 1 (owner)
    to_move: int = 0
    winner: Optional[int] = None                 # set when the game ends


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


class Col(Game):
    uid = "col"
    name = "Col"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ColState:
        options = options or {}
        size = int(options.get("size", 5))
        return ColState(width=size, height=size)

    def current_player(self, s: ColState) -> int:
        return s.to_move

    def _legal_cells(self, s: ColState, player: int):
        cells = []
        for c in range(s.width):
            for r in range(s.height):
                if (c, r) in s.board:
                    continue
                # Forbidden if orthogonally adjacent to one of player's own stones.
                bad = False
                for dc, dr in ORTHO:
                    if s.board.get((c + dc, r + dr)) == player:
                        bad = True
                        break
                if not bad:
                    cells.append((c, r))
        return cells

    def legal_moves(self, s: ColState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in self._legal_cells(s, s.to_move)]

    def apply_move(self, s: ColState, move: str, rng=None) -> ColState:
        cell = _cell(move)
        board = dict(s.board)
        board[cell] = s.to_move
        nxt = 1 - s.to_move
        ns = ColState(width=s.width, height=s.height, board=board,
                      to_move=nxt, winner=s.winner)
        # If the next player has no legal move, the mover (s.to_move) wins.
        if ns.winner is None and not self._legal_cells(ns, nxt):
            ns.winner = s.to_move
        return ns

    def is_terminal(self, s: ColState) -> bool:
        return s.winner is not None

    def returns(self, s: ColState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: ColState) -> dict:
        return {
            "width": s.width,
            "height": s.height,
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> ColState:
        return ColState(
            width=d["width"],
            height=d["height"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
        )

    def describe_move(self, s: ColState, move: str) -> str:
        c, r = _cell(move)
        who = "P1" if s.to_move == 0 else "P2"
        return f"{who}:{c + 1},{r + 1}"

    def render(self, s: ColState, perspective=None) -> dict:
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
