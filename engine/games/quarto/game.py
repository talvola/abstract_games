"""Quarto (Blaise Müller / Gigamic, 1991) — the attribute-matching game in which
you choose the piece your OPPONENT must place.

Board: 4×4 (cell ids "c,r", c/r in 0..3).

There are 16 UNIQUE pieces, one for every combination of four binary attributes:

    height : T (tall)   / S (short)
    colour : L (light)  / D (dark)
    shape  : R (round)  / Q (square)
    fill   : H (hollow) / F (solid)

A piece is a 4-letter code in the fixed order height-colour-shape-fill, e.g.
"TLRH" = tall light round hollow, "SDQF" = short dark square solid. Pieces are
SHARED — neither player owns them; you place whichever piece your opponent gave
you.

TURN STRUCTURE.  On your turn you (1) PLACE the piece your opponent handed you on
any empty cell, then (2) CHOOSE one of the remaining unused pieces and hand it to
the opponent for their turn. The VERY FIRST move of the game is just step (2): the
first player picks a piece for the second player, with no placement.

Move encoding (clean, clickable):
  * first move (no placement):  "give=<code>"   — 16 action buttons.
  * normal move:                "c,r=<code>"     — click the empty cell, then a
        picker chooses <code> (the piece to hand over). The piece being PLACED is
        the in-hand piece stored in the state. A final placement with no piece
        left to give is just "c,r".

WIN.  Immediately after a PLACEMENT, if any full line of four — a row, a column,
or one of the two main diagonals — consists of four pieces that ALL share at least
one of the four attributes (all tall, OR all light, OR all round, OR …), the
player who just placed WINS. A full board with no such line is a DRAW.

Option `square_win` (default off): the optional Gigamic advanced variant in which
any full 2×2 square of four cells that all share an attribute also wins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 4

# Attribute axes: each piece is a 4-bit value, bit i picks the value on axis i.
# Letter pair per axis: index 0 = bit 0, index 1 = bit 1.
AXES = [("S", "T"), ("D", "L"), ("Q", "R"), ("F", "H")]
#         height       colour      shape       fill
# Code order (left→right): height, colour, shape, fill.
AXIS_ORDER = [0, 1, 2, 3]


def code_of(bits: int) -> str:
    """4-bit piece value -> 4-letter code in height-colour-shape-fill order."""
    return "".join(AXES[ax][(bits >> ax) & 1] for ax in AXIS_ORDER)


def bits_of(code: str) -> int:
    bits = 0
    for pos, ax in enumerate(AXIS_ORDER):
        ch = code[pos]
        lo, hi = AXES[ax]
        if ch == hi:
            bits |= (1 << ax)
        elif ch != lo:
            raise ValueError(f"bad piece code {code!r}")
    return bits


ALL_PIECES = [code_of(b) for b in range(16)]          # 16 unique codes
ALL_BITS = list(range(16))

ATTR_NAME = {
    "T": "tall", "S": "short", "L": "light", "D": "dark",
    "R": "round", "Q": "square", "H": "hollow", "F": "solid",
}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


# Four-in-a-line groups: rows, columns, both main diagonals.
def _lines():
    lines = []
    for r in range(N):
        lines.append([(c, r) for c in range(N)])      # rows
    for c in range(N):
        lines.append([(c, r) for r in range(N)])      # columns
    lines.append([(i, i) for i in range(N)])           # main diagonal
    lines.append([(i, N - 1 - i) for i in range(N)])   # anti-diagonal
    return lines


LINES = _lines()


def _squares():
    sq = []
    for c in range(N - 1):
        for r in range(N - 1):
            sq.append([(c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)])
    return sq


SQUARES = _squares()


def _group_wins(board: dict, group) -> bool:
    """True if every cell of `group` is filled and the four pieces share an attribute."""
    vals = []
    for cell in group:
        if cell not in board:
            return False
        vals.append(bits_of(board[cell]))
    # Share a value on some axis iff AND of bits or AND of complements is nonzero.
    common_one = vals[0]
    common_zero = (~vals[0]) & 0b1111
    for v in vals[1:]:
        common_one &= v
        common_zero &= (~v) & 0b1111
    return (common_one | common_zero) != 0


@dataclass
class QState:
    board: dict = field(default_factory=dict)     # (c, r) -> 4-letter code
    in_hand: Optional[str] = None                  # piece this player must place (None = first move)
    to_move: int = 0
    winner: Optional[int] = None                   # player index who just placed a winning line
    started: bool = False                          # has the opening give happened?
    square_win: bool = False                        # 2x2-square win variant


class Quarto(Game):
    uid = "quarto"
    name = "Quarto"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> QState:
        opts = options or {}
        return QState(square_win=bool(opts.get("square_win", False)))

    def current_player(self, s: QState) -> int:
        return s.to_move

    def _used(self, s: QState) -> set:
        used = set(s.board.values())
        if s.in_hand is not None:
            used.add(s.in_hand)
        return used

    def _available_to_give(self, s: QState) -> list[str]:
        used = self._used(s)
        return [p for p in ALL_PIECES if p not in used]

    def legal_moves(self, s: QState) -> list[str]:
        if self.is_terminal(s):
            return []
        if not s.started:
            # Opening move: just give a piece to the opponent. No placement.
            return [f"give={p}" for p in ALL_PIECES]
        empties = [(c, r) for c in range(N) for r in range(N) if (c, r) not in s.board]
        giveable = self._available_to_give(s)
        moves = []
        for (c, r) in empties:
            if giveable:
                for g in giveable:
                    moves.append(f"{c},{r}={g}")
            else:
                # Last placement: no piece remains to hand over.
                moves.append(f"{c},{r}")
        return moves

    def _wins(self, board: dict, square_win: bool) -> bool:
        groups = LINES + (SQUARES if square_win else [])
        return any(_group_wins(board, g) for g in groups)

    def apply_move(self, s: QState, move: str, rng=None) -> QState:
        if not s.started:
            # Opening: first player gives a piece to the second player.
            assert move.startswith("give=")
            give = move.split("=", 1)[1]
            return QState(board=dict(s.board), in_hand=give,
                          to_move=1 - s.to_move, winner=None, started=True,
                          square_win=s.square_win)

        # Normal turn: place the in-hand piece, then optionally give one away.
        if "=" in move:
            cs, give = move.split("=", 1)
        else:
            cs, give = move, None
        cell = _cell(cs)
        board = dict(s.board)
        board[cell] = s.in_hand
        won = self._wins(board, s.square_win)
        winner = s.to_move if won else None
        return QState(
            board=board,
            in_hand=None if won else give,
            to_move=s.to_move if won else 1 - s.to_move,
            winner=winner,
            started=True,
            square_win=s.square_win,
        )

    def is_terminal(self, s: QState) -> bool:
        return s.winner is not None or len(s.board) == N * N

    def returns(self, s: QState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]                          # full board, no line: draw
        return [1.0 if i == s.winner else -1.0 for i in range(self.num_players)]

    def serialize(self, s: QState) -> dict:
        return {
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "in_hand": s.in_hand,
            "to_move": s.to_move,
            "winner": s.winner,
            "started": s.started,
            "square_win": s.square_win,
        }

    def deserialize(self, d: dict) -> QState:
        return QState(
            board={_cell(k): v for k, v in d["board"].items()},
            in_hand=d.get("in_hand"),
            to_move=d["to_move"],
            winner=d.get("winner"),
            started=d.get("started", False),
            square_win=bool(d.get("square_win", False)),
        )

    def describe_move(self, s: QState, move: str) -> str:
        if move.startswith("give="):
            return f"give {move.split('=', 1)[1]}"
        if "=" in move:
            cs, give = move.split("=", 1)
            c, r = _cell(cs)
            return f"place {s.in_hand} @{c + 1},{r + 1}, give {give}"
        c, r = _cell(move)
        return f"place {s.in_hand} @{c + 1},{r + 1}"

    def render(self, s: QState, perspective=None) -> dict:
        # Neutral pieces (no seat colour): light pieces drawn light, dark dark; the
        # 4-letter code is the label. The square/round + hollow/solid distinctions
        # are spelled out in the code text.
        pieces = []
        for (c, r), code in s.board.items():
            light = code[1] == "L"
            pieces.append({
                "cell": f"{c},{r}",
                "owner": 0,
                "label": code,
                "fill": "#f2e7c9" if light else "#5b4636",
                "stroke": "#7a6a48" if light else "#2c2118",
            })

        if s.winner is not None:
            caption = f"Player {s.winner + 1} wins (a line shares an attribute)"
        elif self.is_terminal(s):
            caption = "Draw (board full, no shared line)"
        elif not s.started:
            caption = f"Player {s.to_move + 1}: choose a piece to give your opponent"
        else:
            hand = s.in_hand or "?"
            caption = (f"Player {s.to_move + 1}: place {hand} "
                       f"({self._spell(hand)}), then give a piece")

        spec = {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
            # Friendly names for the give-piece picker.
            "choiceNames": {p: f"give {p}" for p in ALL_PIECES},
        }
        # Show the in-hand piece in a reserve tray so it is visible off-board.
        if s.started and s.in_hand is not None and s.winner is None and not self.is_terminal(s):
            spec["reserve"] = {str(s.to_move): {s.in_hand: 1}}
        return spec

    @staticmethod
    def _spell(code: str) -> str:
        return " ".join(ATTR_NAME[ch] for ch in code)
