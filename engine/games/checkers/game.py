"""Checkers — standard American/English draughts.

8x8 board, play on dark squares only. 12 men each. Men move one square
diagonally forward to an empty square; kings move diagonally in any direction.
Captures (jumps) leap over an adjacent enemy piece to the empty square beyond
and remove it. Captures are MANDATORY, and a jump must continue while the same
piece can jump again — the whole chain is one move. A man reaching the far rank
becomes a king, and that ends the turn (no further jumping that move). You lose
if you have no legal move (all pieces captured or blocked).

Moves are the platform's clickable cell-path notation: the squares the piece
visits, e.g. "1,2>2,3" (simple) or "1,2>3,4>5,6" (double jump). Because only
maximal jump sequences are legal, the UI naturally forces a chain to completion.

Player 0 (rows 0-2) moves toward row 7; player 1 (rows 5-7) toward row 0.
Draw rules (and termination guarantee): a 50-ply no-progress rule (no capture or
man move = only kings shuffling) and a hard 400-ply cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 8
DRAW_HALFMOVE = 50
PLY_CAP = 400
DIAGS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


@dataclass
class DraughtsState:
    board: dict = field(default_factory=dict)  # (c, r) -> (player, "m"|"k")
    to_move: int = 0
    halfmove: int = 0   # plies since last capture or man move
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _king_row(player: int) -> int:
    return N - 1 if player == 0 else 0


def _move_dirs(player: int, kind: str):
    if kind == "k":
        return DIAGS
    return [(1, 1), (-1, 1)] if player == 0 else [(1, -1), (-1, -1)]


def _start_board() -> dict:
    b = {}
    for r in (0, 1, 2):
        for c in range(N):
            if (c + r) % 2 == 1:
                b[(c, r)] = (0, "m")
    for r in (5, 6, 7):
        for c in range(N):
            if (c + r) % 2 == 1:
                b[(c, r)] = (1, "m")
    return b


def _jump_paths(board: dict, pos, player: int, kind: str):
    """All maximal jump sequences from `pos` (board already has the piece at pos,
    earlier captures removed). Returns list of paths [pos, land, ...]."""
    c, r = pos
    paths = []
    for dc, dr in _move_dirs(player, kind):
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
        occ = board.get(over)
        if _on(*land) and occ is not None and occ[0] != player and board.get(land) is None:
            nb = dict(board)
            del nb[over]
            del nb[pos]
            promoted = kind == "m" and land[1] == _king_row(player)
            nk = "k" if promoted else kind
            nb[land] = (player, nk)
            cont = [] if promoted else _jump_paths(nb, land, player, nk)
            if cont:
                paths += [[pos] + p for p in cont]
            else:
                paths.append([pos, land])
    return paths


class Checkers(Game):
    uid = "checkers"
    name = "Checkers"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DraughtsState:
        return DraughtsState(board=_start_board())

    def current_player(self, s: DraughtsState) -> int:
        return s.to_move

    def _draw(self, s: DraughtsState) -> bool:
        return s.halfmove >= DRAW_HALFMOVE or s.ply >= PLY_CAP

    def _all_moves(self, s: DraughtsState) -> list[list]:
        """Legal move paths. Mandatory capture: if any jump exists, only jumps."""
        mine = [(pos, k) for pos, k in s.board.items() if k[0] == s.to_move]
        jumps = []
        for pos, (pl, kind) in mine:
            jumps += _jump_paths(s.board, pos, pl, kind)
        if jumps:
            return jumps
        simples = []
        for pos, (pl, kind) in mine:
            c, r = pos
            for dc, dr in _move_dirs(pl, kind):
                t = (c + dc, r + dr)
                if _on(*t) and t not in s.board:
                    simples.append([pos, t])
        return simples

    def legal_moves(self, s: DraughtsState) -> list[str]:
        if self._draw(s):
            return []
        return [">".join(f"{c},{r}" for c, r in path) for path in self._all_moves(s)]

    def apply_move(self, s: DraughtsState, move: str, rng=None) -> DraughtsState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        pl, kind = board.pop(cells[0])
        captured = False
        for a, b in zip(cells, cells[1:]):
            if abs(b[0] - a[0]) == 2:
                mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
                board.pop(mid, None)
                captured = True
        final = cells[-1]
        if kind == "m" and final[1] == _king_row(pl):
            kind = "k"
        board[final] = (pl, kind)
        progress = captured or kind == "m" or s.board[cells[0]][1] == "m"
        return DraughtsState(
            board=board, to_move=1 - pl,
            halfmove=0 if progress else s.halfmove + 1, ply=s.ply + 1,
        )

    def is_terminal(self, s: DraughtsState) -> bool:
        return self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: DraughtsState) -> list[float]:
        if self._draw(s):
            return [0.0, 0.0]
        # no legal move: the player to move loses
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: DraughtsState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, k] for (c, r), (pl, k) in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> DraughtsState:
        return DraughtsState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"], halfmove=d["halfmove"], ply=d["ply"],
        )

    def describe_move(self, s: DraughtsState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        jump = any(abs(b[0] - a[0]) == 2 for a, b in zip(cells, cells[1:]))
        sep = "x" if jump else "-"
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        return sep.join(alg(c) for c in cells)

    def render(self, s: DraughtsState, perspective=None) -> dict:
        names = {0: "Red", 1: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": "K" if k == "k" else ""}
            for (c, r), (pl, k) in s.board.items()
        ]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
