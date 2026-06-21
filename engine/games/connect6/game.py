"""Connect6 — a fair six-in-a-row (Professor I-Chen Wu, 2005).

Played on a Go-style square grid (13x13 or 19x19 via the board-size option).
Black (player 0) moves first and on the FIRST move of the game places exactly
ONE stone. After that, players alternate and EACH turn (both colours) places
exactly TWO stones, on any two distinct empty intersections. A player WINS
immediately upon getting SIX OR MORE of their own stones in an unbroken line —
horizontal, vertical, or diagonal. The two-stones-per-turn rule is what makes
Connect6 fair/balanced. A full board with no six-line is a draw.

Move encoding (`>`-separated cell-id path, cells "col,row"):
  - opening single-stone move:  "9,9"
  - normal two-stone move:      "3,3>10,10"  (two placements, order irrelevant)

legal_moves practicality
------------------------
The full set of unordered two-empty-cell pairs is enormous (~64k on 19x19), so
`legal_moves` returns a PRUNED but legal list: for normal turns it forms pairs
only among candidate cells (empty cells within Chebyshev distance 3 of an
existing stone, plus the board centre on an empty board). `apply_move` accepts
ANY move that places stones on two distinct empty cells, so a representative
move list never blocks a legal play. See rules.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

CONNECT = 6
NAMES = {0: "Black", 1: "White"}
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
NEAR = 3  # candidate radius (Chebyshev) for the pruned move list


@dataclass
class Connect6State:
    size: int = 19
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    ply: int = 0                                 # number of turns already taken
    winner: Optional[int] = None


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


class Connect6(Game):
    uid = "connect6"
    name = "Connect6"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> Connect6State:
        size = int((options or {}).get("size", 19))
        return Connect6State(size=size)

    def current_player(self, s: Connect6State) -> int:
        return s.to_move

    def _stones_this_turn(self, s: Connect6State) -> int:
        # The very first turn of the game (ply 0, Black) places one stone;
        # every turn thereafter places two.
        return 1 if s.ply == 0 else 2

    def _empties(self, s: Connect6State):
        return [(c, r) for c in range(s.size) for r in range(s.size)
                if (c, r) not in s.board]

    def _candidates(self, s: Connect6State):
        """Empty cells near an existing stone (pruned move-list support)."""
        if not s.board:
            mid = s.size // 2
            return [(mid, mid)]
        cands = set()
        for (c, r) in s.board:
            for dc in range(-NEAR, NEAR + 1):
                for dr in range(-NEAR, NEAR + 1):
                    cc, rr = c + dc, r + dr
                    if 0 <= cc < s.size and 0 <= rr < s.size and (cc, rr) not in s.board:
                        cands.add((cc, rr))
        return sorted(cands)

    def legal_moves(self, s: Connect6State) -> list[str]:
        if self.is_terminal(s):
            return []
        if self._stones_this_turn(s) == 1:
            return [f"{c},{r}" for (c, r) in self._empties(s)]
        cands = self._candidates(s)
        moves = []
        for i in range(len(cands)):
            ci, ri = cands[i]
            for j in range(i + 1, len(cands)):
                cj, rj = cands[j]
                moves.append(f"{ci},{ri}>{cj},{rj}")
        return moves

    def _parse(self, move: str):
        return [_cell(p) for p in move.split(">")]

    def _wins(self, board: dict, cell, player: int) -> bool:
        c, r = cell
        for dc, dr in DIRS:
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

    def apply_move(self, s: Connect6State, move: str, rng=None) -> Connect6State:
        cells = self._parse(move)
        expected = self._stones_this_turn(s)
        if len(cells) != expected:
            raise ValueError(
                f"turn {s.ply} ({NAMES[s.to_move]}) must place {expected} "
                f"stone(s), got {len(cells)}")
        if len(set(cells)) != len(cells):
            raise ValueError("two placements must be on distinct cells")
        board = dict(s.board)
        for cell in cells:
            c, r = cell
            if not (0 <= c < s.size and 0 <= r < s.size):
                raise ValueError(f"cell {cell} off board")
            if cell in board:
                raise ValueError(f"cell {cell} is occupied")
            board[cell] = s.to_move
        winner = None
        for cell in cells:
            if self._wins(board, cell, s.to_move):
                winner = s.to_move
                break
        return Connect6State(
            size=s.size, board=board, to_move=1 - s.to_move,
            ply=s.ply + 1, winner=winner,
        )

    def is_terminal(self, s: Connect6State) -> bool:
        return s.winner is not None or len(s.board) == s.size * s.size

    def returns(self, s: Connect6State) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: Connect6State) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> Connect6State:
        return Connect6State(
            size=d.get("size", 19),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d["winner"],
        )

    def describe_move(self, s: Connect6State, move: str) -> str:
        cells = self._parse(move)
        tag = NAMES[s.to_move][0]
        parts = [f"{c + 1},{r + 1}" for (c, r) in cells]
        return f"{tag}:" + "+".join(parts)

    def render(self, s: Connect6State, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            n = self._stones_this_turn(s)
            stones = "one stone" if n == 1 else "two stones"
            caption = f"{NAMES[s.to_move]} to move ({stones})"
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
