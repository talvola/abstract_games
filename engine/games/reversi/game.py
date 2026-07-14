"""Reversi / Othello — flipping game on an 8x8 (or 10x10) board.

Black (player 0) moves first. A legal move places one of your discs on an empty
cell so that it brackets a straight line (in any of the 8 directions) of one or
more opponent discs capped by one of your own; every bracketed opponent disc in
those lines flips to your colour. You must move if you can; if you have no legal
placement you pass. The game ends when neither player can move (typically a full
board).

Options:
  * ``size`` — 8 (standard Othello/Reversi) or 10 (Grand Othello).
  * ``opening`` — "othello" (fixed centre diagonal) or "reversi" (open centre:
    the first four discs are placed into the four central squares with no
    captures).
  * ``goal`` — "most" (standard: the majority of discs wins) or "fewest"
    (Anti- / misère Othello: FEWER discs wins). Equal counts always draw.

Cells are "col,row", 0..size-1. A move is a single cell (the placement) or
"pass". Termination is automatic: every placement fills a cell, and a pass is
only offered when the opponent has a move, so passes can't repeat forever.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

NAMES = {0: "Black", 1: "White"}
DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
COLS = "abcdefghij"   # enough for size 10


@dataclass
class ReversiState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    opening: str = "othello"                      # "othello" | "reversi"
    size: int = 8                                 # 8 | 10
    goal: str = "most"                            # "most" | "fewest"


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r, n):
    return 0 <= c < n and 0 <= r < n


def _center(n):
    """The four central squares for an n×n board."""
    lo, hi = n // 2 - 1, n // 2
    return [(lo, lo), (lo, hi), (hi, lo), (hi, hi)]


def _start_board(n) -> dict:
    """Standard fixed-diagonal start: White on the two \\-diagonal centre cells,
    Black on the two /-diagonal centre cells."""
    lo, hi = n // 2 - 1, n // 2
    return {(lo, lo): 1, (hi, hi): 1, (lo, hi): 0, (hi, lo): 0}


def _flips(board: dict, cell, player: int, n: int) -> list:
    """Cells that would flip if `player` places at `cell` (empty assumed)."""
    c, r = cell
    flipped = []
    for dc, dr in DIRS:
        line = []
        cc, rr = c + dc, r + dr
        while _on(cc, rr, n) and board.get((cc, rr)) == 1 - player:
            line.append((cc, rr))
            cc += dc
            rr += dr
        if line and _on(cc, rr, n) and board.get((cc, rr)) == player:
            flipped += line
    return flipped


def _placements(board: dict, player: int, n: int) -> list:
    return [(c, r) for c in range(n) for r in range(n)
            if (c, r) not in board and _flips(board, (c, r), player, n)]


class Reversi(Game):
    uid = "reversi"
    name = "Reversi"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ReversiState:
        opts = options or {}
        opening = opts.get("opening", "othello")
        size = int(opts.get("size", 8))
        goal = opts.get("goal", "most")
        board = {} if opening == "reversi" else _start_board(size)
        return ReversiState(board=board, opening=opening, size=size, goal=goal)

    def current_player(self, s: ReversiState) -> int:
        return s.to_move

    def _in_opening(self, s: ReversiState) -> bool:
        """Original-Reversi opening phase: the four central squares are still
        being filled (alternating placements, no captures)."""
        return s.opening == "reversi" and len(s.board) < 4

    def is_terminal(self, s: ReversiState) -> bool:
        if self._in_opening(s):
            return False                      # centre not yet filled -> play continues
        n = s.size
        return not _placements(s.board, 0, n) and not _placements(s.board, 1, n)

    def legal_moves(self, s: ReversiState) -> list[str]:
        if self.is_terminal(s):
            return []
        n = s.size
        if self._in_opening(s):
            return [f"{c},{r}" for (c, r) in _center(n) if (c, r) not in s.board]
        mine = _placements(s.board, s.to_move, n)
        if mine:
            return [f"{c},{r}" for c, r in mine]
        return ["pass"]   # opponent has a move (else terminal); we must pass

    def apply_move(self, s: ReversiState, move: str, rng=None) -> ReversiState:
        if move == "pass":
            return ReversiState(board=dict(s.board), to_move=1 - s.to_move,
                                opening=s.opening, size=s.size, goal=s.goal)
        cell = _cell(move)
        board = dict(s.board)
        if not self._in_opening(s):           # no captures during the centre opening
            for fc in _flips(board, cell, s.to_move, s.size):
                board[fc] = s.to_move
        board[cell] = s.to_move
        return ReversiState(board=board, to_move=1 - s.to_move,
                            opening=s.opening, size=s.size, goal=s.goal)

    def _counts(self, s: ReversiState):
        b = sum(1 for p in s.board.values() if p == 0)
        w = sum(1 for p in s.board.values() if p == 1)
        return b, w

    def returns(self, s: ReversiState) -> list[float]:
        b, w = self._counts(s)
        if b == w:
            return [0.0, 0.0]
        black_ahead = b > w
        if s.goal == "fewest":                # Anti-Othello: FEWER discs wins
            black_ahead = b < w
        return [1.0, -1.0] if black_ahead else [-1.0, 1.0]

    def serialize(self, s: ReversiState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "opening": s.opening,
            "size": s.size,
            "goal": s.goal,
        }

    def deserialize(self, d: dict) -> ReversiState:
        return ReversiState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            opening=d.get("opening", "othello"),
            size=int(d.get("size", 8)),
            goal=d.get("goal", "most"),
        )

    def describe_move(self, s: ReversiState, move: str) -> str:
        if move == "pass":
            return f"{NAMES[s.to_move][0]}:pass"
        c, r = _cell(move)
        return f"{NAMES[s.to_move][0]}:{COLS[c]}{r + 1}"

    def render(self, s: ReversiState, perspective=None) -> dict:
        n = s.size
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        b, w = self._counts(s)
        goal_tag = " (fewest wins)" if s.goal == "fewest" else ""
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = (f"Draw {b}-{w}" if ret == [0.0, 0.0]
                       else f"{NAMES[0 if ret[0] > 0 else 1]} wins {b}-{w}{goal_tag}")
        elif self._in_opening(s):
            caption = f"{NAMES[s.to_move]} to move (place a disc in the centre)"
        else:
            caption = f"{NAMES[s.to_move]} to move  ({b}-{w}){goal_tag}"
        return {
            "board": {"type": "square", "width": n, "height": n},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
