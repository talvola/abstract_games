"""HexDame (Christian Freeling, 1979) — international draughts on a hexhex-5 board.

A literal adaptation of international (Polish) draughts to a hexagonal board of
61 cells (hexhex, 5 cells per side). Each player has 16 men filling a 4x4
rhombus in their home corner. Men move one cell in the THREE forward
directions; men CAPTURE by a short jump in ALL SIX directions. Kings are
FLYING: they slide any distance along one of the six lines, and capture a
single enemy piece at any distance, landing on any empty cell beyond it.

Captures are compulsory with the MAJORITY (maximum) rule: the mover must play
a sequence capturing the maximum NUMBER of pieces (a king counts as one piece,
same as a man); among equal-maximal sequences any may be chosen. Captured
pieces are removed only when the whole sequence is complete, so a "dead" piece
still blocks and may not be jumped a second time (Coup Turc); cells may be
revisited. A man promotes only by ENDING its move on the opponent's back rank
— the NINE cells of the two far sides of the hexagon; merely passing over a
back-rank cell mid-capture does not promote.

You lose when you have no legal move (all pieces captured, or blocked). Draw
by a 50-ply no-progress rule (no capture and no man move) plus a hard 400-ply
cap (the platform's termination guarantee; mindsports.nl uses 3-fold
repetition/agreement, which async play handles via the draw-offer buttons).

Coordinates: axial (q, y) cell ids "q,y" with max(|q|, |y|, |q+y|) <= 4.
Traditional HexDame notation (files a-i x ranks 1-9, |file-rank| <= 4) maps as
q = rank-5, y = 5-file; ``describe_move`` shows moves in that notation
(e.g. "c5-d6", "e7xc5xe5"). White's corner a1 = (-4,4) renders bottom-left,
Black's corner i9 = (4,-4) top-right.

Rules source: mindsports.nl (Freeling's own site) Arena > Hexdame > Rules;
cross-checked with Wikipedia "Hexdame" and Abstract Games #8 p.21 (Kok 2001).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

SIZE = 5
N = SIZE - 1  # 4
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
# White (player 0) moves from the a1 corner (-4,4) toward the i9 corner (4,-4).
FWD = {
    0: [(0, -1), (1, 0), (1, -1)],
    1: [(0, 1), (-1, 0), (-1, 1)],
}
DRAW_HALFMOVE = 50
PLY_CAP = 400
FILES = "abcdefghi"


@dataclass
class HexDameState:
    board: dict = field(default_factory=dict)  # (q, y) -> (player, "m"|"k")
    to_move: int = 0
    halfmove: int = 0  # plies since last capture or man move
    ply: int = 0


def _cell(s: str):
    q, y = s.split(",")
    return int(q), int(y)


def _on(q, y):
    return abs(q) <= N and abs(y) <= N and abs(q + y) <= N


def _promotes(player: int, cell) -> bool:
    """The 9-cell back rank: the two far sides of the hexagon (shared corner
    counted once). White: file i (y=-4) or rank 9 (q=4); Black: file a / rank 1."""
    q, y = cell
    return (y == -N or q == N) if player == 0 else (y == N or q == -N)


def _start_board() -> dict:
    """16 men each in a 4x4 rhombus: White files a-d x ranks 1-4 (incl. the a1
    corner), Black files f-i x ranks 6-9 — per the mindsports.nl diagram."""
    b = {}
    for q in range(-N, 0):
        for y in range(1, N + 1):
            b[(q, y)] = (0, "m")
            b[(-q, -y)] = (1, "m")
    return b


def _man_capture_paths(board, pos, origin, player, captured):
    """Capture sequences for a MAN at `pos`, in all 6 directions. `board` is the
    ORIGINAL board (pieces removed only at the end), `origin` the moving piece's
    vacated start cell (treated as empty), `captured` the enemy cells already
    jumped (a piece may not be jumped twice; still on the board, so it blocks).
    Promotion never interrupts a capture: a man passing over the back rank
    continues as a man."""
    q, y = pos
    paths = []
    for dq, dy in DIRS:
        over = (q + dq, y + dy)
        land = (q + 2 * dq, y + 2 * dy)
        if not _on(*land):
            continue
        occ = board.get(over)
        land_free = board.get(land) is None or land == origin
        if (occ is not None and occ[0] != player and over not in captured
                and over != origin and land_free):
            cont = _man_capture_paths(board, land, origin, player, captured | {over})
            if cont:
                paths += [[pos] + p for p in cont]
            else:
                paths.append([pos, land])
    return paths


def _king_capture_paths(board, pos, origin, player, captured):
    """Capture sequences for a FLYING KING at `pos`: slide over empties to the
    first piece on a line; if it is an uncaptured enemy, land on any empty cell
    beyond it (before the next obstruction) and optionally continue."""
    q, y = pos
    paths = []
    for dq, dy in DIRS:
        i = 1
        over = None
        while True:
            sq = (q + i * dq, y + i * dy)
            if not _on(*sq):
                break
            occ = board.get(sq)
            if occ is None or sq == origin:
                i += 1
                continue
            over = sq
            break
        if over is None:
            continue
        occ = board.get(over)
        if occ[0] == player or over in captured:
            continue
        j = 1
        while True:
            land = (over[0] + j * dq, over[1] + j * dy)
            if not _on(*land):
                break
            if board.get(land) is not None and land != origin:
                break
            cont = _king_capture_paths(board, land, origin, player, captured | {over})
            if cont:
                paths += [[pos] + p for p in cont]
            else:
                paths.append([pos, land])
            j += 1
    return paths


class HexDame(Game):
    name = "HexDame"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HexDameState:
        return HexDameState(board=_start_board())

    def current_player(self, s: HexDameState) -> int:
        return s.to_move

    def _draw(self, s: HexDameState) -> bool:
        return s.halfmove >= DRAW_HALFMOVE or s.ply >= PLY_CAP

    def _captured_squares(self, board, path):
        """Enemy cells jumped along a visited-cell path (handles flying-king
        gaps): the first occupied cell strictly between consecutive vertices.
        The mover's origin cell (path[0]) is vacated for the whole move, so a
        segment may slide straight over it — skip it when scanning."""
        origin = path[0]
        caps = []
        for a, b in zip(path, path[1:]):
            dq_t, dy_t = b[0] - a[0], b[1] - a[1]
            if dq_t == 0:
                dq, dy = 0, (1 if dy_t > 0 else -1)
            elif dy_t == 0:
                dq, dy = (1 if dq_t > 0 else -1), 0
            else:  # the (1,-1)/(-1,1) line
                dq, dy = (1 if dq_t > 0 else -1), (1 if dy_t > 0 else -1)
            step = (a[0] + dq, a[1] + dy)
            while step != b:
                if step != origin and board.get(step) is not None:
                    caps.append(step)
                    break
                step = (step[0] + dq, step[1] + dy)
        return caps

    def _all_moves(self, s: HexDameState) -> list[list]:
        """Legal move paths. Mandatory MAXIMUM capture (majority rule)."""
        mine = [(pos, k) for pos, k in s.board.items() if k[0] == s.to_move]
        captures = []
        for pos, (pl, kind) in mine:
            if kind == "k":
                captures += _king_capture_paths(s.board, pos, pos, pl, frozenset())
            else:
                captures += _man_capture_paths(s.board, pos, pos, pl, frozenset())
        if captures:
            best = max(len(p) for p in captures)
            return [p for p in captures if len(p) == best]
        simples = []
        for pos, (pl, kind) in mine:
            q, y = pos
            if kind == "k":
                for dq, dy in DIRS:
                    i = 1
                    while True:
                        t = (q + i * dq, y + i * dy)
                        if not _on(*t) or s.board.get(t) is not None:
                            break
                        simples.append([pos, t])
                        i += 1
            else:
                for dq, dy in FWD[pl]:
                    t = (q + dq, y + dy)
                    if _on(*t) and t not in s.board:
                        simples.append([pos, t])
        return simples

    def legal_moves(self, s: HexDameState) -> list[str]:
        if self._draw(s):
            return []
        moves = [">".join(f"{q},{y}" for q, y in p) for p in self._all_moves(s)]
        return list(dict.fromkeys(moves))

    def apply_move(self, s: HexDameState, move: str, rng=None) -> HexDameState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        pl, kind = board.pop(cells[0])
        caps = self._captured_squares(s.board, cells)
        for sq in caps:
            board.pop(sq, None)
        final = cells[-1]
        # promote only when ENDING the move on the back rank
        if kind == "m" and _promotes(pl, final):
            kind = "k"
        board[final] = (pl, kind)
        progress = bool(caps) or s.board[cells[0]][1] == "m"
        return HexDameState(
            board=board, to_move=1 - pl,
            halfmove=0 if progress else s.halfmove + 1, ply=s.ply + 1,
        )

    def is_terminal(self, s: HexDameState) -> bool:
        return self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: HexDameState) -> list[float]:
        if self._draw(s):
            return [0.0, 0.0]
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def heuristic(self, s: HexDameState) -> list[float]:
        mat = [0.0, 0.0]
        for (pl, kind) in s.board.values():
            mat[pl] += 3.0 if kind == "k" else 1.0
        v = math.tanh((mat[0] - mat[1]) / 8.0)
        return [v, -v]

    def serialize(self, s: HexDameState) -> dict:
        return {
            "board": {f"{q},{y}": [pl, k] for (q, y), (pl, k) in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> HexDameState:
        return HexDameState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"], halfmove=d["halfmove"], ply=d["ply"],
        )

    @staticmethod
    def _notation(cell) -> str:
        q, y = cell
        return f"{FILES[4 - y]}{q + 5}"

    def describe_move(self, s: HexDameState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        sep = "x" if self._captured_squares(s.board, cells) else "-"
        return sep.join(self._notation(c) for c in cells)

    def render(self, s: HexDameState, perspective=None) -> dict:
        names = {0: "White", 1: "Black"}
        pieces = [
            {"cell": f"{q},{y}", "owner": pl, "label": "K" if k == "k" else ""}
            for (q, y), (pl, k) in s.board.items()
        ]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
