"""Rolit -- a four-player Reversi (Goliath, 1990s) on a standard 8x8 board.

Four players (each a colour) take turns dropping a ball next to a ball already on
the board (8 directions). Any straight line of *other* players' balls bracketed
between the new ball and another of your own flips to your colour, exactly as in
Reversi -- but unlike Reversi you may also place adjacent **without** flipping
anything (the only requirement is that the cell touch an existing ball). The board
fills after 60 placements; whoever then owns the most balls wins.

This is the platform's first **>2-player** game; the engine already supports any
``num_players`` and the web UI now seats four. Player order is 0->1->2->3->0.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 8
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _flips(board, c, r, player):
    """Cells that flip to `player` if they place at (c,r) (Reversi brackets)."""
    out = []
    for dc, dr in DIRS:
        line = []
        cc, rr = c + dc, r + dr
        while 0 <= cc < SIZE and 0 <= rr < SIZE and (cc, rr) in board and board[(cc, rr)] != player:
            line.append((cc, rr))
            cc, rr = cc + dc, rr + dr
        if line and 0 <= cc < SIZE and 0 <= rr < SIZE and board.get((cc, rr)) == player:
            out.extend(line)
    return out


def _adjacent_to_any(board, c, r):
    for dc, dr in DIRS:
        if (c + dc, r + dr) in board:
            return True
    return False


@dataclass
class RolitState:
    board: dict = field(default_factory=dict)        # (c,r) -> player 0..3
    to_move: int = 0
    nplayers: int = 4


class Rolit(Game):
    uid = "rolit"
    name = "Rolit"

    @property
    def num_players(self):
        return 4

    def initial_state(self, options=None, rng=None):
        # Four balls in the centre, one per player, arranged as a pinwheel.
        board = {(3, 3): 0, (4, 3): 1, (4, 4): 2, (3, 4): 3}
        return RolitState(board=board, to_move=0)

    def current_player(self, s):
        return s.to_move

    def _legal(self, board):
        return [(c, r) for r in range(SIZE) for c in range(SIZE)
                if (c, r) not in board and _adjacent_to_any(board, c, r)]

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in self._legal(s.board)]

    def _next_with_move(self, board, after):
        """The next player (cyclically after `after`) who has a legal move, or
        None if nobody does."""
        if not self._legal(board):
            return None
        return (after + 1) % 4        # every live turn has a move until the board fills

    def apply_move(self, s, move, rng=None):
        c, r = _cell(move)
        board = dict(s.board)
        for sq in _flips(board, c, r, s.to_move):
            board[sq] = s.to_move
        board[(c, r)] = s.to_move
        nxt = self._next_with_move(board, s.to_move)
        return RolitState(board=board, to_move=(s.to_move if nxt is None else nxt))

    def is_terminal(self, s):
        return len(s.board) == SIZE * SIZE or not self._legal(s.board)

    def _scores(self, board):
        sc = [0, 0, 0, 0]
        for p in board.values():
            sc[p] += 1
        return sc

    def returns(self, s):
        if not self.is_terminal(s):
            return [0.0, 0.0, 0.0, 0.0]
        sc = self._scores(s.board)
        best = max(sc)
        winners = [i for i, v in enumerate(sc) if v == best]
        # +1 to the sole leader, -1 to everyone else; a tie for first is a draw (0).
        if len(winners) == 1:
            return [1.0 if i == winners[0] else -1.0 for i in range(4)]
        return [0.0, 0.0, 0.0, 0.0]

    def serialize(self, s):
        return {"board": {f"{c},{r}": p for (c, r), p in s.board.items()},
                "to_move": s.to_move}

    def deserialize(self, d):
        return RolitState(board={_cell(k): v for k, v in d["board"].items()},
                          to_move=d["to_move"])

    def describe_move(self, s, move):
        c, r = _cell(move)
        n = len(_flips(s.board, c, r, s.to_move))
        letters = "ABCDEFGH"
        return f"{letters[c]}{r + 1}" + (f" (+{n})" if n else "")

    def render(self, s, perspective=None):
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        sc = self._scores(s.board)
        score_str = " · ".join(f"P{i + 1} {sc[i]}" for i in range(4))
        if self.is_terminal(s):
            best = max(sc)
            lead = [i for i, v in enumerate(sc) if v == best]
            cap = (f"P{lead[0] + 1} wins" if len(lead) == 1 else "Draw") + f"  ·  {score_str}"
        else:
            cap = f"P{s.to_move + 1} to move  ·  {score_str}"
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
