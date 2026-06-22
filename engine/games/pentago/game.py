"""Pentago -- place a marble, then twist a quadrant. First to get five in a row
wins. A 6x6 board split into four 3x3 quadrants.

Each turn has two parts, encoded as one move ``"c,r=QUAD-DIR"``: place a marble on
an empty cell, then rotate one of the four quadrants 90 degrees clockwise (`cw`)
or counter-clockwise (`ccw`). The five-in-a-row is checked *after* the rotation;
if the twist makes a five for the opponent only, they win; if it makes five for
both, the game is a draw. A full board with no five is also a draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 6
BLACK, WHITE = 0, 1
# Quadrants: (col_offset, row_offset) of each 3x3 block, with a display label.
QUADS = {
    "BL": (0, 0), "BR": (3, 0), "TL": (0, 3), "TR": (3, 3),
}
DIRS = ("cw", "ccw")
LINES_DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _rotate(board, quad, direction):
    """Return a new board with the 3x3 `quad` rotated 90 degrees."""
    qc, qr = QUADS[quad]
    nb = dict(board)
    for i in range(3):
        for j in range(3):
            src = (qc + i, qr + j)
            # 90deg rotation within the 3x3 local frame
            ni, nj = (2 - j, i) if direction == "cw" else (j, 2 - i)
            dst = (qc + ni, qr + nj)
            if src in board:
                nb[dst] = board[src]
            elif dst in nb:
                del nb[dst]
    return nb


def _five(board, player):
    """True if `player` has five in a row anywhere (orthogonal or diagonal)."""
    for r in range(N):
        for c in range(N):
            if board.get((c, r)) != player:
                continue
            for dc, dr in LINES_DIRS:
                if all(board.get((c + k * dc, r + k * dr)) == player for k in range(5)):
                    return True
    return False


@dataclass
class PState:
    board: dict = field(default_factory=dict)
    to_move: int = BLACK
    winner: object = None            # None, 0, 1, or "draw"


class Pentago(Game):
    uid = "pentago"
    name = "Pentago"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return PState()

    def current_player(self, state):
        return state.to_move

    def legal_moves(self, state):
        if state.winner is not None:
            return []
        empties = [(c, r) for r in range(N) for c in range(N) if (c, r) not in state.board]
        if not empties:
            return []
        out = []
        for (c, r) in empties:
            for q in QUADS:
                for d in DIRS:
                    out.append(f"{c},{r}={q}-{d}")
        return out

    def apply_move(self, state, move, rng=None):
        cellpart, choice = move.split("=")
        quad, direction = choice.split("-")
        c, r = _cell(cellpart)
        board = dict(state.board)
        board[(c, r)] = state.to_move
        board = _rotate(board, quad, direction)
        mover, opp = state.to_move, 1 - state.to_move
        mover_five, opp_five = _five(board, mover), _five(board, opp)
        if mover_five and opp_five:
            winner = "draw"
        elif mover_five:
            winner = mover
        elif opp_five:
            winner = opp
        elif len(board) == N * N:
            winner = "draw"
        else:
            winner = None
        return PState(board=board, to_move=1 - state.to_move, winner=winner)

    def is_terminal(self, state):
        return state.winner is not None

    def returns(self, state):
        if state.winner in (None, "draw"):
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    def serialize(self, state):
        return {
            "board": {f"{c},{r}": p for (c, r), p in state.board.items()},
            "to_move": state.to_move, "winner": state.winner,
        }

    def deserialize(self, d):
        return PState(board={_cell(k): v for k, v in d["board"].items()},
                      to_move=d["to_move"], winner=d.get("winner"))

    def describe_move(self, state, move):
        cellpart, choice = move.split("=")
        return f"{cellpart} ↻{choice}"

    def render(self, state, perspective=None):
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in state.board.items()]
        # Draw the two quadrant dividers (boundaries sit between cells 2 and 3).
        lines = [[[2.5, -0.5], [2.5, 5.5], "#8a7a52"],
                 [[-0.5, 2.5], [5.5, 2.5], "#8a7a52"]]
        if state.winner == "draw":
            cap = "Draw"
        elif state.winner is not None:
            cap = f"{names[state.winner]} wins (five in a row)"
        else:
            cap = f"{names[state.to_move]} to move (place, then rotate a quadrant)"
        return {
            "board": {"type": "square", "width": N, "height": N, "lines": lines},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
