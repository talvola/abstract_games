"""Dao — Jeff Pickering & Ben van Buskirk (~1999), a 4x4 abstract.

Each player has four pieces. Black starts on one main diagonal,
White on the other. Players alternate. A piece moves like a queen
(any of the 8 directions) but MUST slide as far as it can: it travels
in the chosen direction until it hits the board edge or another piece,
stopping on the last empty square before the obstacle. It cannot stop
short, and cannot pick a direction in which it is already blocked
(immediately against the edge or another piece). There are no captures —
pieces never leave the board.

Win by arranging YOUR four pieces into any one of:
  1. a 2x2 square,
  2. a full straight line of four (a complete row or column — diagonals
     do NOT count),
  3. all four board corners,
  4. (corner trap) one of YOUR pieces sitting in a board corner with the
     three cells adjacent to that corner all occupied by the OPPONENT —
     the trapped player wins.

Because the corner-trap condition can be created by either player, every
win condition is checked for BOTH players after each move. (If both reach
a winning shape simultaneously, the player who just moved is credited.)

Ruleset choices (see rules.md): "line" means a full row/column only.
A player with no legal move loses (the published rules are silent; this
is the natural convention and is needed for a well-formed terminal). A
PLY_CAP draw guarantees termination since Dao positions can cycle.

Moves are clickable cell paths "from>to". Player 0 = Black, player 1 = White.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 4
NAMES = {0: "Black", 1: "White"}
PLY_CAP = 200  # hard draw cap; Dao can cycle

DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
CORNERS = [(0, 0), (0, N - 1), (N - 1, 0), (N - 1, N - 1)]


@dataclass
class DaoState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None                 # set on a win
    draw: bool = False                           # set when PLY_CAP hit
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {}
    for i in range(N):
        b[(i, i)] = 0                 # Black on the (0,0)..(3,3) diagonal
        b[(i, N - 1 - i)] = 1         # White on the (0,3)..(3,0) diagonal
    return b


def _slide_dest(board: dict, c: int, r: int, dc: int, dr: int):
    """Final empty cell sliding from (c,r) along (dc,dr), or None if blocked
    immediately (already against the edge or a piece)."""
    nc, nr = c + dc, r + dr
    if not _on(nc, nr) or (nc, nr) in board:
        return None
    # advance until the next step would leave the board or hit a piece
    while _on(nc + dc, nr + dr) and (nc + dc, nr + dr) not in board:
        nc, nr = nc + dc, nr + dr
    return (nc, nr)


def _moves(board: dict, player: int) -> list:
    out = []
    for (c, r), pl in board.items():
        if pl != player:
            continue
        for dc, dr in DIRS:
            dest = _slide_dest(board, c, r, dc, dr)
            if dest is not None:
                out.append(((c, r), dest))
    return out


def _cells_of(board: dict, player: int):
    return frozenset(cell for cell, pl in board.items() if pl == player)


def _is_square(cells) -> bool:
    """The four cells form a 2x2 block."""
    cs = sorted(c for c, _ in cells)
    rs = sorted(r for _, r in cells)
    if cs[0] == cs[1] and cs[2] == cs[3] and cs[1] + 1 == cs[2] \
            and rs[0] == rs[1] and rs[2] == rs[3] and rs[1] + 1 == rs[2]:
        c0, r0 = cs[0], rs[0]
        want = {(c0, r0), (c0 + 1, r0), (c0, r0 + 1), (c0 + 1, r0 + 1)}
        return set(cells) == want
    return False


def _is_line(cells) -> bool:
    """All four in one full row or one full column (diagonals excluded)."""
    cols = {c for c, _ in cells}
    rows = {r for _, r in cells}
    return len(cols) == 1 or len(rows) == 1


def _is_corners(cells) -> bool:
    return set(cells) == set(CORNERS)


def _is_corner_trapped(board: dict, player: int) -> bool:
    """One of `player`'s pieces sits in a board corner and the three cells
    adjacent to that corner are all occupied by the opponent."""
    opp = 1 - player
    for (cc, cr) in CORNERS:
        if board.get((cc, cr)) != player:
            continue
        nbrs = [(cc + dc, cr + dr) for dc, dr in DIRS if _on(cc + dc, cr + dr)]
        # an interior board corner has exactly 3 neighbours
        if all(board.get(n) == opp for n in nbrs):
            return True
    return False


def _has_won(board: dict, player: int) -> bool:
    cells = _cells_of(board, player)
    if len(cells) == N and (_is_square(cells) or _is_line(cells)
                            or _is_corners(cells)):
        return True
    return _is_corner_trapped(board, player)


class Dao(Game):
    uid = "dao"
    name = "Dao"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DaoState:
        return DaoState(board=_start_board())

    def current_player(self, s: DaoState) -> int:
        return s.to_move

    def legal_moves(self, s: DaoState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}"
                for a, b in _moves(s.board, s.to_move)]

    def apply_move(self, s: DaoState, move: str, rng=None) -> DaoState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        pl = board.pop(frm)
        board[to] = pl
        ply = s.ply + 1

        winner = None
        # the mover gets priority if both shapes appear at once
        if _has_won(board, pl):
            winner = pl
        elif _has_won(board, 1 - pl):
            winner = 1 - pl

        draw = False
        if winner is None and ply >= PLY_CAP:
            draw = True

        return DaoState(board=board, to_move=1 - pl,
                        winner=winner, draw=draw, ply=ply)

    def is_terminal(self, s: DaoState) -> bool:
        if s.winner is not None or s.draw:
            return True
        # player to move with no legal move loses (handled in returns)
        return not _moves(s.board, s.to_move)

    def returns(self, s: DaoState) -> list[float]:
        if s.draw:
            return [0.0, 0.0]
        if s.winner is not None:
            w = s.winner
        else:
            # to_move has no legal move -> to_move loses
            w = 1 - s.to_move
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def serialize(self, s: DaoState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> DaoState:
        return DaoState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            draw=d["draw"],
            ply=d["ply"],
        )

    def describe_move(self, s: DaoState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcd'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{alg(frm)}-{alg(to)}"

    def render(self, s: DaoState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if self.is_terminal(s):
            if s.draw:
                caption = "Draw (move cap reached)"
            else:
                ret = self.returns(s)
                caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
