"""Reversi / Othello — 8x8 flipping game.

Black (player 0) moves first. A legal move places one of your discs on an empty
cell so that it brackets a straight line (in any of the 8 directions) of one or
more opponent discs capped by one of your own; every bracketed opponent disc in
those lines flips to your colour. You must move if you can; if you have no legal
placement you pass. The game ends when neither player can move (typically a full
board); the player with more discs wins, equal counts draw.

Cells are "col,row", 0..7. A move is a single cell (the placement) or "pass".
Termination is automatic: every placement fills a cell (<=60), and a pass is only
offered when the opponent has a move, so passes can't repeat forever.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 8
NAMES = {0: "Black", 1: "White"}
DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


@dataclass
class ReversiState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    return {(3, 3): 1, (4, 4): 1, (3, 4): 0, (4, 3): 0}


def _flips(board: dict, cell, player: int) -> list:
    """Cells that would flip if `player` places at `cell` (empty assumed)."""
    c, r = cell
    flipped = []
    for dc, dr in DIRS:
        line = []
        cc, rr = c + dc, r + dr
        while _on(cc, rr) and board.get((cc, rr)) == 1 - player:
            line.append((cc, rr))
            cc += dc
            rr += dr
        if line and _on(cc, rr) and board.get((cc, rr)) == player:
            flipped += line
    return flipped


def _placements(board: dict, player: int) -> list:
    return [(c, r) for c in range(N) for r in range(N)
            if (c, r) not in board and _flips(board, (c, r), player)]


class Reversi(Game):
    uid = "reversi"
    name = "Reversi"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ReversiState:
        return ReversiState(board=_start_board())

    def current_player(self, s: ReversiState) -> int:
        return s.to_move

    def is_terminal(self, s: ReversiState) -> bool:
        return not _placements(s.board, 0) and not _placements(s.board, 1)

    def legal_moves(self, s: ReversiState) -> list[str]:
        if self.is_terminal(s):
            return []
        mine = _placements(s.board, s.to_move)
        if mine:
            return [f"{c},{r}" for c, r in mine]
        return ["pass"]   # opponent has a move (else terminal); we must pass

    def apply_move(self, s: ReversiState, move: str, rng=None) -> ReversiState:
        if move == "pass":
            return ReversiState(board=dict(s.board), to_move=1 - s.to_move)
        cell = _cell(move)
        board = dict(s.board)
        for fc in _flips(board, cell, s.to_move):
            board[fc] = s.to_move
        board[cell] = s.to_move
        return ReversiState(board=board, to_move=1 - s.to_move)

    def _counts(self, s: ReversiState):
        b = sum(1 for p in s.board.values() if p == 0)
        w = sum(1 for p in s.board.values() if p == 1)
        return b, w

    def returns(self, s: ReversiState) -> list[float]:
        b, w = self._counts(s)
        if b > w:
            return [1.0, -1.0]
        if w > b:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: ReversiState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
        }

    def deserialize(self, d: dict) -> ReversiState:
        return ReversiState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
        )

    def describe_move(self, s: ReversiState, move: str) -> str:
        if move == "pass":
            return f"{NAMES[s.to_move][0]}:pass"
        c, r = _cell(move)
        return f"{NAMES[s.to_move][0]}:{'abcdefgh'[c]}{r + 1}"

    def render(self, s: ReversiState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        b, w = self._counts(s)
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = (f"Draw {b}-{w}" if ret == [0.0, 0.0]
                       else f"{NAMES[0 if ret[0] > 0 else 1]} wins {max(b, w)}-{min(b, w)}")
        else:
            caption = f"{NAMES[s.to_move]} to move  ({b}-{w})"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
