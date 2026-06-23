"""Quixo (Gigamic, designer Thierry Chapeau) on a 5x5 grid of cubes.

Each cube shows a blank face, a cross (X = player 0) or a circle (O = player 1);
all 25 start blank. On your turn you:

  1. TAKE a cube from the BORDER (the 16 outer cells) that is blank OR already
     shows YOUR symbol -- you may never take a cube showing the opponent's symbol;
  2. stamp it with YOUR symbol;
  3. push it back into the SAME row or column from one edge, so it re-enters at
     that edge and the cubes between the edge and the gap all shift one step. The
     cube must actually move (you cannot put it straight back where it came from).

A move is written ``"c,r=DIR"`` -- the taken border cell plus the EDGE the cube
re-enters from: ``L`` (left, x!=0), ``R`` (right, x!=4), ``U`` (top, y!=0),
``D`` (bottom, y!=4). The web UI offers the legal directions as a picker when you
click a border cube.

WIN: a straight line of five of your symbol (row, column or diagonal), checked
after the slide. Because a slide can complete a line for either colour, if the
move forms a five of the OPPONENT's symbol (and not yours) the OPPONENT wins; if
it forms both, the mover wins. A defensive ply cap makes a stalled game a draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 5
BLANK = -1
SYM = {0: "X", 1: "O"}
PLY_CAP = 400                       # defensive no-progress draw cap

# The 16 border cells (outer ring of a 5x5 grid).
BORDER = [(c, r) for r in range(N) for c in range(N)
          if c == 0 or c == N - 1 or r == 0 or r == N - 1]

# All winning lines: 5 rows, 5 columns, 2 diagonals.
LINES = (
    [[(c, r) for c in range(N)] for r in range(N)] +
    [[(c, r) for r in range(N)] for c in range(N)] +
    [[(i, i) for i in range(N)], [(i, N - 1 - i) for i in range(N)]]
)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class QState:
    # board[(c, r)] -> BLANK / 0 / 1 ; every cell present.
    board: dict = field(default_factory=lambda: {(c, r): BLANK
                                                 for r in range(N) for c in range(N)})
    to_move: int = 0
    winner: object = None          # 0, 1, or "draw"; None while playing
    ply: int = 0


class Quixo(Game):
    uid = "quixo"
    name = "Quixo"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return QState()

    def current_player(self, state):
        return state.to_move

    # -------------------------------------------------------- move generation
    def _dirs_for(self, c, r):
        """The legal re-insert edges for a taken border cube at (c, r): a cube can
        slide along its row (L/R) or column (U/D), excluding the direction that
        would just return it to its own cell (no movement)."""
        out = []
        if c != 0:
            out.append("L")        # re-enter at left edge, shift the left part right
        if c != N - 1:
            out.append("R")
        if r != 0:
            out.append("U")
        if r != N - 1:
            out.append("D")
        return out

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        pl = state.to_move
        out = []
        for (c, r) in BORDER:
            if state.board[(c, r)] in (BLANK, pl):     # blank or your own symbol
                for d in self._dirs_for(c, r):
                    out.append(f"{c},{r}={d}")
        return out

    # -------------------------------------------------------------- transition
    def _slide(self, board, c, r, d, v):
        """Stamp the taken cube as `v` and push it back from edge `d`, shifting the
        intervening cubes one step. Mutates `board`."""
        if d == "L":               # re-enter at col 0; cols 0..c-1 shift right
            for i in range(c, 0, -1):
                board[(i, r)] = board[(i - 1, r)]
            board[(0, r)] = v
        elif d == "R":             # re-enter at col N-1; cols c+1..N-1 shift left
            for i in range(c, N - 1):
                board[(i, r)] = board[(i + 1, r)]
            board[(N - 1, r)] = v
        elif d == "U":             # re-enter at row 0; rows 0..r-1 shift down
            for i in range(r, 0, -1):
                board[(c, i)] = board[(c, i - 1)]
            board[(c, 0)] = v
        elif d == "D":             # re-enter at row N-1; rows r+1..N-1 shift up
            for i in range(r, N - 1):
                board[(c, i)] = board[(c, i + 1)]
            board[(c, N - 1)] = v
        else:
            raise ValueError(f"bad direction {d}")

    def apply_move(self, state, move, rng=None):
        path, _, d = move.partition("=")
        c, r = _cell(path)
        pl = state.to_move
        if (c, r) not in BORDER:
            raise ValueError(f"{path} is not a border cell")
        if state.board[(c, r)] not in (BLANK, pl):
            raise ValueError(f"cannot take the opponent's cube at {path}")
        if d not in self._dirs_for(c, r):
            raise ValueError(f"illegal slide {move}")

        board = dict(state.board)
        self._slide(board, c, r, d, pl)               # stamp as pl + push

        ns = QState(board=board, to_move=1 - pl, ply=state.ply + 1)
        # Evaluate lines after the slide. A move may complete a line for either
        # colour; the mover's own line takes precedence over the opponent's.
        mover_line = self._has_line(board, pl)
        opp_line = self._has_line(board, 1 - pl)
        if mover_line:
            ns.winner = pl
        elif opp_line:
            ns.winner = 1 - pl
        elif ns.ply >= PLY_CAP:
            ns.winner = "draw"
        return ns

    def _has_line(self, board, pl):
        for line in LINES:
            if all(board[cell] == pl for cell in line):
                return True
        return False

    # ------------------------------------------------------------------- ends
    def is_terminal(self, state):
        return state.winner is not None

    def returns(self, state):
        if state.winner is None or state.winner == "draw":
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ------------------------------------------------------------ serialization
    def serialize(self, state):
        return {
            "board": {f"{c},{r}": v for (c, r), v in state.board.items()},
            "to_move": state.to_move,
            "winner": state.winner,
            "ply": state.ply,
        }

    def deserialize(self, d):
        return QState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
        )

    def describe_move(self, state, move):
        path, _, d = move.partition("=")
        c, r = _cell(path)
        # NB: the board renders with row 0 at the BOTTOM, so the engine's "U"
        # edge (re-enter at row 0) is the player's visual bottom, and vice versa.
        edge = {"L": "from left", "R": "from right", "U": "from bottom", "D": "from top"}[d]
        alg = f"{'abcde'[c]}{r + 1}"
        return f"{SYM[state.to_move]}: {alg} {edge}"

    # ------------------------------------------------------------- presentation
    # Row 0 renders at the BOTTOM, so U (re-enter at row 0) is the visual bottom.
    CHOICE_NAMES = {"L": "From left", "R": "From right", "U": "From bottom", "D": "From top"}

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), v in state.board.items():
            if v != BLANK:
                pieces.append({"cell": f"{c},{r}", "owner": v, "label": SYM[v]})

        if state.winner == "draw":
            cap = "Draw"
        elif state.winner is not None:
            cap = f"{SYM[state.winner]} wins"
        else:
            cap = f"{SYM[state.to_move]} to move (take a border cube)"

        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
            "choiceTitle": "Slide in from",
            "choiceNames": self.CHOICE_NAMES,
        }
