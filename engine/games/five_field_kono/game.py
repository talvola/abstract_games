"""Five Field Kono (오밭고누) — a traditional Korean racing game.

Played on a 5x5 grid of points (the "five fields"). Each player has 7 pieces.
Pieces move one step DIAGONALLY (any of the four diagonal directions) to an
adjacent EMPTY point. There are NO captures and no jumps. The first player to
move ALL of their pieces onto the exact set of points the OPPONENT started on
wins (a race to exchange home territories).

Coordinates are "c,r" with c the column (0..4) and r the row (0..4).

START (the standard documented layout):
  Player 0 (bottom, rows 0-1): the whole back row r=0 (5 points) plus the two
  OUTER points of the second row r=1 — i.e. (0,1) and (4,1). 7 pieces.
  Player 1 (top, rows 4-3): mirror — the whole row r=4 (5 points) plus (0,3)
  and (4,3). 7 pieces.

WIN: occupy the opponent's 7 starting points. The race is parity-feasible: the
two home sets contain the same multiset of diagonal-colour parities.

Termination: a piece can move forward or backward, so play could in principle
cycle. We add a no-progress / hard-ply cap that yields a DRAW. A player with no
legal move is passed (so we never return an empty move list); if neither side can
move the position is a stalemate draw via the ply cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 5
NAMES = {0: "Bottom", 1: "Top"}
DIAGS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

# Hard cap on plies with no decisive result -> draw (guarantees termination).
PLY_CAP = 200


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _home(player: int) -> set:
    """The 7 starting points of `player`."""
    if player == 0:
        cells = {(c, 0) for c in range(N)} | {(0, 1), (N - 1, 1)}
    else:
        cells = {(c, N - 1) for c in range(N)} | {(0, N - 2), (N - 1, N - 2)}
    return cells


def _start_board() -> dict:
    b = {}
    for c, r in _home(0):
        b[(c, r)] = 0
    for c, r in _home(1):
        b[(c, r)] = 1
    return b


@dataclass
class KonoState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None                 # 0/1 winner, or None
    draw: bool = False
    plies: int = 0


class FiveFieldKono(Game):
    name = "Five Field Kono"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> KonoState:
        return KonoState(board=_start_board())

    def current_player(self, s: KonoState) -> int:
        return s.to_move

    def _moves(self, s: KonoState, player: int) -> list:
        out = []
        for (c, r), pl in s.board.items():
            if pl != player:
                continue
            for dc, dr in DIAGS:
                nc, nr = c + dc, r + dr
                if _on(nc, nr) and (nc, nr) not in s.board:
                    out.append(((c, r), (nc, nr)))
        return out

    def _check_winner(self, board: dict, player: int) -> bool:
        """True if all of `player`'s pieces sit on the opponent's home set."""
        target = _home(1 - player)
        own = {cell for cell, pl in board.items() if pl == player}
        return own == target

    def legal_moves(self, s: KonoState) -> list[str]:
        if self.is_terminal(s):
            return []
        mv = self._moves(s, s.to_move)
        if not mv:
            # No move for the side to move -> they pass (never return []).
            return ["pass"]
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in mv]

    def apply_move(self, s: KonoState, move: str, rng=None) -> KonoState:
        plies = s.plies + 1
        if move == "pass":
            draw = plies >= PLY_CAP
            return KonoState(board=dict(s.board), to_move=1 - s.to_move,
                             winner=None, draw=draw, plies=plies)
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        pl = board.pop(frm)
        board[to] = pl
        winner = pl if self._check_winner(board, pl) else None
        draw = winner is None and plies >= PLY_CAP
        return KonoState(board=board, to_move=1 - pl, winner=winner,
                         draw=draw, plies=plies)

    def is_terminal(self, s: KonoState) -> bool:
        return s.winner is not None or s.draw

    def returns(self, s: KonoState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    def serialize(self, s: KonoState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "plies": s.plies,
        }

    def deserialize(self, d: dict) -> KonoState:
        return KonoState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            draw=d.get("draw", False),
            plies=d.get("plies", 0),
        )

    def describe_move(self, s: KonoState, move: str) -> str:
        if move == "pass":
            return "pass"
        frm, to = move.split(">")
        return f"{frm}→{to}"

    def render(self, s: KonoState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p}
                  for (c, r), p in s.board.items()]
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif s.draw:
            caption = "Draw"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        # Tint each player's target (the opponent's home) faintly.
        tints = {}
        for c, r in _home(1):
            tints[f"{c},{r}"] = "#ffe7e7"   # bottom player's goal
        for c, r in _home(0):
            tints[f"{c},{r}"] = "#e7ecff"   # top player's goal
        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
