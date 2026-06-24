"""Three Musketeers — an asymmetric hunt game by Haar Hoolim.

Played on a 5x5 grid. Player 0 is the three MUSKETEERS (seat 0); player 1 is the
22 ENEMY pieces (Cardinal Richelieu's men, seat 1). Every one of the 25 squares is
occupied at the start: the three Musketeers sit on two opposite corners + the
centre, the enemy fills the rest.

Movement (players alternate, MUSKETEERS move first):
* A Musketeer move MUST capture: move a Musketeer one square orthogonally onto an
  adjacent square occupied by an enemy, removing that enemy (the Musketeer takes
  its place). A Musketeer can NEVER move to an empty square.
* An enemy move: move one enemy piece one square orthogonally onto an adjacent
  EMPTY square (no captures).

Win conditions (asymmetric):
* The ENEMY wins if the three Musketeers ever come to lie in the same row or the
  same column (a line). Because the Musketeer player must capture on their turn,
  if every legal capture would line up the three Musketeers, they are forced into
  a losing line — the enemy still wins.
* The MUSKETEERS win if, on their turn, they cannot move because no Musketeer has
  an adjacent enemy to capture (and they are not in a line).

Termination: every Musketeer move removes one enemy (<=22 captures), so the
Musketeer side is monotone. The enemy can shuffle empty squares forever without
progress, so a hard ply cap (PLY_CAP) declares a draw if neither win fires. In
practice the line/no-move condition fires quickly in random play.

Moves are "from>to" cell paths ("c,r>c,r"): click a piece, then an adjacent
square (an enemy for a Musketeer, an empty square for the enemy).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 5
MUSK, ENEMY = 0, 1
PLY_CAP = 400
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


@dataclass
class TMState:
    board: dict = field(default_factory=dict)  # (c, r) -> 0 (musketeer) / 1 (enemy)
    to_move: int = MUSK
    winner: Optional[int] = None  # 0 musketeers / 1 enemy
    drawn: bool = False
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {}
    musk = {(0, 0), (N - 1, N - 1), (N // 2, N // 2)}  # two opposite corners + centre
    for r in range(N):
        for c in range(N):
            b[(c, r)] = MUSK if (c, r) in musk else ENEMY
    return b


def _musketeers_in_line(board: dict) -> bool:
    cells = [(c, r) for (c, r), p in board.items() if p == MUSK]
    if len(cells) != 3:
        return False
    cols = {c for c, _ in cells}
    rows = {r for _, r in cells}
    return len(cols) == 1 or len(rows) == 1


class ThreeMusketeers(Game):
    uid = "three_musketeers"
    name = "Three Musketeers"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> TMState:
        return TMState(board=_start_board())

    def current_player(self, s: TMState) -> int:
        return s.to_move

    def _raw_moves(self, s: TMState) -> list[str]:
        out = []
        if s.to_move == MUSK:
            # Musketeers move only by capturing an orthogonally adjacent enemy.
            for (c, r), p in s.board.items():
                if p != MUSK:
                    continue
                for dc, dr in DIRS:
                    tc, tr = c + dc, r + dr
                    if _on(tc, tr) and s.board.get((tc, tr)) == ENEMY:
                        out.append(f"{c},{r}>{tc},{tr}")
        else:
            # Enemy moves to an orthogonally adjacent empty square.
            for (c, r), p in s.board.items():
                if p != ENEMY:
                    continue
                for dc, dr in DIRS:
                    tc, tr = c + dc, r + dr
                    if _on(tc, tr) and (tc, tr) not in s.board:
                        out.append(f"{c},{r}>{tc},{tr}")
        return out

    def is_terminal(self, s: TMState) -> bool:
        if s.winner is not None or s.drawn:
            return True
        # Musketeers win if on their turn they have no capture available.
        if s.to_move == MUSK and not self._raw_moves(s):
            return True
        # Enemy with no move (cannot actually happen — there is always an empty
        # square once a capture has occurred, but guard defensively).
        if s.to_move == ENEMY and not self._raw_moves(s):
            return True
        return False

    def legal_moves(self, s: TMState) -> list[str]:
        return [] if self.is_terminal(s) else self._raw_moves(s)

    def apply_move(self, s: TMState, move: str, rng=None) -> TMState:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        mover = s.to_move
        board = dict(s.board)
        del board[frm]
        board[to] = mover  # capture for Musketeer (target removed), step for enemy
        ply = s.ply + 1

        winner = None
        if _musketeers_in_line(board):
            winner = ENEMY  # enemy wins the moment the three line up (either side's move)
        drawn = winner is None and ply >= PLY_CAP
        return TMState(board=board, to_move=1 - mover, winner=winner, drawn=drawn, ply=ply)

    def returns(self, s: TMState) -> list[float]:
        if s.winner == ENEMY:
            return [-1.0, 1.0]
        if s.winner == MUSK:
            return [1.0, -1.0]
        if s.drawn:
            return [0.0, 0.0]
        # Terminal because the player to move is stuck.
        if s.to_move == MUSK:
            # Musketeers cannot capture and are not in a line -> Musketeers WIN.
            return [1.0, -1.0]
        # Enemy stuck (defensive) -> enemy loses.
        return [1.0, -1.0]

    def serialize(self, s: TMState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "drawn": s.drawn,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> TMState:
        return TMState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            drawn=d.get("drawn", False),
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: TMState, move: str) -> str:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        alg = lambda c: f"{'abcde'[c[0]]}{c[1] + 1}"  # noqa: E731
        if s.board.get(frm) == MUSK:
            return f"M {alg(frm)}x{alg(to)}"  # capture
        return f"E {alg(frm)}-{alg(to)}"

    def render(self, s: TMState, perspective=None) -> dict:
        pieces = []
        tints = {}
        for (c, r), p in s.board.items():
            cell = f"{c},{r}"
            if p == MUSK:
                pieces.append({"cell": cell, "owner": MUSK, "label": "M"})
                tints[cell] = "#f6d6c8"  # subtle highlight under the three Musketeers
            else:
                pieces.append({"cell": cell, "owner": ENEMY})

        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = "Draw (move cap reached)"
            elif ret[0] > 0:
                caption = "Musketeers win"
            else:
                caption = "Enemy (Cardinal) wins"
        else:
            caption = "Musketeers to move" if s.to_move == MUSK else "Enemy to move"

        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
