"""EinStein würfelt nicht! (Ingo Althöfer, 2004) -- "Einstein doesn't play dice",
a light race-and-capture game where, ironically, a die decides which stone you
move each turn.

On a 5x5 board each player has six stones numbered 1-6 in a home corner. You roll
a die and must move the stone of that number toward the far corner; if that stone
has been captured you move the next-higher or next-lower stone you still have.
Moving onto any stone (yours or the enemy's) removes it. You win by landing a
stone on the opposite corner, or by capturing all of the enemy's stones.

Randomness is modelled without a separate chance node: each move rolls the die for
the *next* turn and stores it in the state (so the value is known when you choose
your move, exactly as if you'd rolled first). ``has_randomness`` is true.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

N = 5
# player 0 starts top-left corner (0,0) and races to (4,4); player 1 the reverse.
HOME = {
    0: [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (0, 2)],
    1: [(4, 4), (3, 4), (2, 4), (4, 3), (3, 3), (4, 2)],
}
GOAL = {0: (4, 4), 1: (0, 0)}
DIRS = {0: [(1, 0), (0, 1), (1, 1)], 1: [(-1, 0), (0, -1), (-1, -1)]}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class EWNState:
    board: dict = field(default_factory=dict)        # (c,r) -> (player, number)
    die: int = 1
    to_move: int = 0
    ply: int = 0
    winner: object = None


class Einstein(Game):
    uid = "einstein"
    name = "EinStein würfelt nicht"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        board = {}
        for p in (0, 1):
            nums = list(range(1, 7))
            rng.shuffle(nums)                         # random legal setup (a known variant)
            for cell, num in zip(HOME[p], nums):
                board[cell] = (p, num)
        return EWNState(board=board, die=rng.randint(1, 6), to_move=0)

    def current_player(self, s):
        return s.to_move

    def _movable_numbers(self, s, pl):
        """Which stone numbers `pl` may move for the current die."""
        have = {num for (p, num) in s.board.values() if p == pl}
        if not have:
            return []
        if s.die in have:
            return [s.die]
        lower = max((n for n in have if n < s.die), default=None)
        higher = min((n for n in have if n > s.die), default=None)
        return [n for n in (lower, higher) if n is not None]

    def _stone_cell(self, s, pl, num):
        for cell, (p, k) in s.board.items():
            if p == pl and k == num:
                return cell
        return None

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        out = []
        for num in self._movable_numbers(s, s.to_move):
            c, r = self._stone_cell(s, s.to_move, num)
            for dc, dr in DIRS[s.to_move]:
                to = (c + dc, r + dr)
                if 0 <= to[0] < N and 0 <= to[1] < N:
                    out.append(f"{c},{r}>{to[0]},{to[1]}")
        return out

    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        stone = board.pop(frm)
        board[to] = stone                             # capture: overwrites any stone on `to`
        pl = s.to_move
        winner = None
        if to == GOAL[pl]:
            winner = pl                               # reached the far corner
        elif not any(p == 1 - pl for (p, _n) in board.values()):
            winner = pl                               # captured all enemy stones
        return EWNState(board=board, die=rng.randint(1, 6), to_move=1 - pl,
                        ply=s.ply + 1, winner=winner)

    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    def serialize(self, s):
        return {"board": {f"{c},{r}": list(v) for (c, r), v in s.board.items()},
                "die": s.die, "to_move": s.to_move, "ply": s.ply, "winner": s.winner}

    def deserialize(self, d):
        return EWNState(board={_cell(k): tuple(v) for k, v in d["board"].items()},
                        die=d["die"], to_move=d["to_move"], ply=d.get("ply", 0),
                        winner=d.get("winner"))

    def describe_move(self, s, move):
        frm, to = move.split(">")
        _p, num = s.board.get(_cell(frm), (None, "?"))
        cap = _cell(to) in s.board
        return f"#{num} {frm}{'x' if cap else '-'}{to}"

    def render(self, s, perspective=None):
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": str(n)}
                  for (c, r), (p, n) in s.board.items()]
        names = {0: "Player 1", 1: "Player 2"}
        if s.winner is not None:
            cap = f"{names[s.winner]} wins"
        else:
            movable = self._movable_numbers(s, s.to_move)
            which = (f"stone {movable[0]}" if len(movable) == 1
                     else "stone " + " or ".join(map(str, movable)) if movable else "—")
            cap = f"{names[s.to_move]} rolled {s.die} — move {which}"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
