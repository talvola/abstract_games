"""Lines of Action (Claude Soucie, 1969).

8x8 board. Each player has 12 pieces: player 0 (Red, moves first) starts on the
top and bottom rows (excluding corners); player 1 (Blue) on the left and right
columns. A piece moves in a straight line (orthogonal or diagonal) EXACTLY as
many squares as there are pieces (of both colours) on that whole line. It may
jump over friendly pieces but not over enemy pieces, and may capture by landing
on an enemy piece (not on a friendly one).

You win by bringing ALL your pieces into a single group connected orthogonally
or diagonally (8-connectivity); a lone piece counts as connected. The win is
checked after every move, so reducing your opponent to a connected group makes
THEM win. If a move connects both players at once, it's a draw (modern rule).

Moves are "from>to" cell paths (click a piece, then its destination). A ply cap
guarantees termination for random play (declared a draw).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 8
PLY_CAP = 200
AXES = [(1, 0), (0, 1), (1, 1), (1, -1)]  # horizontal, vertical, two diagonals


@dataclass
class LOAState:
    board: dict = field(default_factory=dict)  # (c, r) -> 0/1
    to_move: int = 0
    winner: Optional[int] = None
    drawn: bool = False
    ply: int = 0
    sim_win: bool = False  # option: simultaneous connection is a win for the mover (else a draw)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _line_count(board: dict, c: int, r: int, dc: int, dr: int) -> int:
    """Pieces on the whole line through (c,r) along axis (dc,dr), including it."""
    count = 1
    for sgn in (1, -1):
        cc, rr = c + sgn * dc, r + sgn * dr
        while _on(cc, rr):
            if (cc, rr) in board:
                count += 1
            cc += sgn * dc
            rr += sgn * dr
    return count


def _connected(board: dict, player: int) -> bool:
    cells = [pos for pos, pl in board.items() if pl == player]
    if len(cells) <= 1:
        return True
    seen = {cells[0]}
    stack = [cells[0]]
    while stack:
        c, r = stack.pop()
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc or dr:
                    nb = (c + dc, r + dr)
                    if nb not in seen and board.get(nb) == player:
                        seen.add(nb)
                        stack.append(nb)
    return len(seen) == len(cells)


def _start_board() -> dict:
    b = {}
    for c in range(1, N - 1):
        b[(c, 0)] = 0
        b[(c, N - 1)] = 0
    for r in range(1, N - 1):
        b[(0, r)] = 1
        b[(N - 1, r)] = 1
    return b


class LinesOfAction(Game):
    uid = "lines_of_action"
    name = "Lines of Action"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> LOAState:
        sim_win = (options or {}).get("sim_connection") == "win"
        return LOAState(board=_start_board(), sim_win=sim_win)

    def current_player(self, s: LOAState) -> int:
        return s.to_move

    def _raw_moves(self, s: LOAState) -> list[str]:
        board, player, out = s.board, s.to_move, []
        for (c, r), pl in list(board.items()):
            if pl != player:
                continue
            for dc, dr in AXES:
                d = _line_count(board, c, r, dc, dr)
                for sgn in (1, -1):
                    sdc, sdr = sgn * dc, sgn * dr
                    tc, tr = c + sdc * d, r + sdr * d
                    if not _on(tc, tr):
                        continue
                    blocked = any(
                        board.get((c + sdc * k, r + sdr * k)) not in (None, player)
                        for k in range(1, d)
                    )
                    if blocked or board.get((tc, tr)) == player:
                        continue
                    out.append(f"{c},{r}>{tc},{tr}")
        return out

    def is_terminal(self, s: LOAState) -> bool:
        return s.winner is not None or s.drawn or not self._raw_moves(s)

    def legal_moves(self, s: LOAState) -> list[str]:
        return [] if self.is_terminal(s) else self._raw_moves(s)

    def apply_move(self, s: LOAState, move: str, rng=None) -> LOAState:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        mover = s.to_move
        board = dict(s.board)
        del board[frm]
        board[to] = mover  # captures any enemy on `to`

        p = _connected(board, mover)
        o = _connected(board, 1 - mover)
        winner, drawn = None, False
        if p and o:
            winner, drawn = (mover, False) if s.sim_win else (None, True)
        elif p:
            winner = mover
        elif o:
            winner = 1 - mover
        ply = s.ply + 1
        if winner is None and not drawn and ply >= PLY_CAP:
            drawn = True
        return LOAState(board=board, to_move=1 - mover, winner=winner, drawn=drawn,
                        ply=ply, sim_win=s.sim_win)

    def returns(self, s: LOAState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        if s.drawn:
            return [0.0, 0.0]
        # terminal because the player to move has no move: they lose
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: LOAState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "drawn": s.drawn,
            "ply": s.ply,
            "sim_win": s.sim_win,
        }

    def deserialize(self, d: dict) -> LOAState:
        return LOAState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], winner=d["winner"],
            drawn=d.get("drawn", False), ply=d.get("ply", 0),
            sim_win=d.get("sim_win", False),
        )

    def describe_move(self, s: LOAState, move: str) -> str:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        cap = to in s.board
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{alg(frm)}{'x' if cap else '-'}{alg(to)}"

    def render(self, s: LOAState, perspective=None) -> dict:
        names = {0: "Red", 1: "Blue"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""} for (c, r), p in s.board.items()]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.drawn:
            caption = "Draw"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
