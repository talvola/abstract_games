"""Pente — five-in-a-row with custodial pair captures (Gary Gabrel, 1977).

Players alternately place a stone on an empty intersection (13x13, 15x15, or 19x19
via the size option). Black (player 0) moves first. Two ways to win:

* make an unbroken line of FIVE OR MORE of your own stones (any direction), or
* capture FIVE PAIRS of enemy stones (ten stones total).

Custodial pair capture: when your placed stone makes the pattern
  YOU - enemy - enemy - YOU
in a straight line (exactly two enemy stones bracketed by your stones), those two
enemy stones are removed. Only pairs are taken — never a single stone or three in a
row — and capture is active: placing your own pair *between* two enemy stones is
safe.

Cells are "col,row"; a move is a single empty cell. A hard ply cap draws the rare
game that would otherwise cycle through repeated captures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

CONNECT = 5
PAIRS_TO_WIN = 5
NAMES = {0: "Black", 1: "White"}
LINE_DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
DIRS8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


@dataclass
class PenteState:
    size: int = 19
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    captures: dict = field(default_factory=lambda: {0: 0, 1: 0})  # pairs taken
    winner: Optional[int] = None
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


class Pente(Game):
    uid = "pente"
    name = "Pente"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> PenteState:
        return PenteState(size=int((options or {}).get("size", 19)))

    def _cap(self, s: PenteState) -> int:
        return 2 * s.size * s.size      # generous; only a cycling game ever hits it

    def current_player(self, s: PenteState) -> int:
        return s.to_move

    def legal_moves(self, s: PenteState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for c in range(s.size) for r in range(s.size)
                if (c, r) not in s.board]

    def _five(self, board: dict, cell, player: int) -> bool:
        c, r = cell
        for dc, dr in LINE_DIRS:
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

    def apply_move(self, s: PenteState, move: str, rng=None) -> PenteState:
        c, r = _cell(move)
        player = s.to_move
        board = dict(s.board)
        board[(c, r)] = player
        captures = dict(s.captures)
        # custodial pair capture in each of the 8 directions
        for dc, dr in DIRS8:
            a = (c + dc, r + dr)
            b = (c + 2 * dc, r + 2 * dr)
            cap = (c + 3 * dc, r + 3 * dr)
            if (board.get(a) == 1 - player and board.get(b) == 1 - player
                    and board.get(cap) == player):
                del board[a]
                del board[b]
                captures[player] += 1
        winner = None
        if self._five(board, (c, r), player) or captures[player] >= PAIRS_TO_WIN:
            winner = player
        return PenteState(size=s.size, board=board, to_move=1 - player,
                          captures=captures, winner=winner, ply=s.ply + 1)

    def is_terminal(self, s: PenteState) -> bool:
        return (s.winner is not None or len(s.board) == s.size * s.size
                or s.ply >= self._cap(s))

    def returns(self, s: PenteState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: PenteState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "captures": {str(k): v for k, v in s.captures.items()},
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> PenteState:
        return PenteState(
            size=d.get("size", 19),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            captures={int(k): v for k, v in d.get("captures", {"0": 0, "1": 0}).items()},
            winner=d.get("winner"),
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: PenteState, move: str) -> str:
        c, r = _cell(move)
        return f"{NAMES[s.to_move][0]}:{c + 1},{r + 1}"

    def render(self, s: PenteState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        cap = f"  [pairs {s.captures[0]}-{s.captures[1]}]"
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins" + cap
        elif self.is_terminal(s):
            caption = "Draw" + cap
        else:
            caption = f"{NAMES[s.to_move]} to move" + cap
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
