"""Croda — Ljuban Dedić's orthogonal draughts (1995).

8x8 board using ALL 64 squares. 24 men each, filling the player's first three
ranks. White moves first.

A MAN moves one square forward — straight OR diagonally forward (the diagonal
step is the only diagonal motion in the game). A man CAPTURES by the short
leap ORTHOGONALLY only, in all four directions (forward, backward, sideways);
never diagonally. A KING moves like a chess rook and captures by the long
leap along ranks and files: fly over empty squares to a single enemy piece
and land on any empty square beyond it, optionally turning to continue.

Capture is compulsory, with the MAJORITY rule: among all capture sequences of
all pieces you must play one removing the maximum number of enemy pieces
(kings and men count equally); with several maximal options the choice is
free. Captured pieces are removed only at the END of the sequence, a piece
may not be jumped twice, and empty squares may be crossed repeatedly — an
already-jumped piece therefore still BLOCKS further jumps (the "Coup Turc").
A man promotes only by ENDING its move on the far rank; jumping on and off
the far rank mid-capture does not promote.

A player with no legal move (eliminated or blocked) loses. Draws (as
implemented): 50 consecutive plies without a capture or a man move, or a
hard 400-ply cap (approximating the official 3-fold repetition / mutual
impotence draws — kings are the only pieces that can shuffle).

Moves are the platform's clickable cell-path notation: the squares the piece
visits, e.g. "5,0>4,1" (man step), "3,4>3,0>7,0>7,2>4,2" (a king's chain).
Player 0 (White, rows 0-2) moves toward row 7; player 1 (Black, rows 5-7)
toward row 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 8
DRAW_HALFMOVE = 50
PLY_CAP = 400
ORTHO = [(0, 1), (0, -1), (-1, 0), (1, 0)]


@dataclass
class CrodaState:
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


def _man_move_dirs(player: int):
    """Men move one square straight or diagonally FORWARD (never sideways or
    backward). These are movement directions only — capture is orthogonal."""
    f = 1 if player == 0 else -1
    return [(0, f), (-1, f), (1, f)]


def _start_board() -> dict:
    b = {}
    for r in (0, 1, 2):
        for c in range(N):
            b[(c, r)] = (0, "m")
    for r in (5, 6, 7):
        for c in range(N):
            b[(c, r)] = (1, "m")
    return b


def _man_capture_paths(board, pos, origin, player, captured):
    """Capture sequences for a MAN at `pos`. `board` is the ORIGINAL board
    (captured pieces are removed only at the end of the move, so they still
    block); `origin` = the mover's true start square (vacated, treated as
    empty); `captured` = enemy squares already jumped (no piece may be jumped
    twice). Men short-leap in all 4 ORTHOGONAL directions. A man does NOT
    promote mid-sequence — it keeps capturing as a man even from the far
    rank — so the recursion never stops early for promotion."""
    c, r = pos
    paths = []
    for dc, dr in ORTHO:
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
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
    """Capture sequences for a FLYING KING at `pos`: slide along a rank/file
    over empty squares to exactly one not-yet-captured enemy piece, land on
    any empty square beyond it before the next obstruction, optionally
    continue. Already-captured pieces still occupy their squares and block."""
    c, r = pos
    paths = []
    for dc, dr in ORTHO:
        i = 1
        over = None
        while True:
            sq = (c + i * dc, r + i * dr)
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
            land = (over[0] + j * dc, over[1] + j * dr)
            if not _on(*land):
                break
            lc = board.get(land)
            if lc is not None and land != origin:
                break
            cont = _king_capture_paths(board, land, origin, player, captured | {over})
            if cont:
                paths += [[pos] + p for p in cont]
            else:
                paths.append([pos, land])
            j += 1
    return paths


class Croda(Game):
    uid = "croda"
    name = "Croda"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CrodaState:
        return CrodaState(board=_start_board())

    def current_player(self, s: CrodaState) -> int:
        return s.to_move

    def _draw(self, s: CrodaState) -> bool:
        return s.halfmove >= DRAW_HALFMOVE or s.ply >= PLY_CAP

    def _captured_squares(self, board, path):
        """Enemy squares jumped along a visited-square path: the single piece
        strictly between consecutive vertices. The mover's origin square is
        treated as empty (the piece is in flight), so a later segment crossing
        it is scanned correctly."""
        caps = []
        origin = path[0]
        for a, b in zip(path, path[1:]):
            dc = (b[0] > a[0]) - (b[0] < a[0])
            dr = (b[1] > a[1]) - (b[1] < a[1])
            step = (a[0] + dc, a[1] + dr)
            while step != b:
                if step != origin and board.get(step) is not None:
                    caps.append(step)
                    break
                step = (step[0] + dc, step[1] + dr)
        return caps

    def _all_moves(self, s: CrodaState) -> list[list]:
        """Legal move paths. Mandatory MAXIMUM capture (majority rule): if any
        capture exists, only sequences capturing the maximum number of pieces
        are legal (each jump captures exactly one piece)."""
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
            c, r = pos
            if kind == "k":
                for dc, dr in ORTHO:
                    i = 1
                    while True:
                        t = (c + i * dc, r + i * dr)
                        if not _on(*t) or s.board.get(t) is not None:
                            break
                        simples.append([pos, t])
                        i += 1
            else:
                for dc, dr in _man_move_dirs(pl):
                    t = (c + dc, r + dr)
                    if _on(*t) and t not in s.board:
                        simples.append([pos, t])
        return simples

    def legal_moves(self, s: CrodaState) -> list[str]:
        if self._draw(s):
            return []
        return [">".join(f"{c},{r}" for c, r in path) for path in self._all_moves(s)]

    def apply_move(self, s: CrodaState, move: str, rng=None) -> CrodaState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        pl, kind = board.pop(cells[0])
        caps = self._captured_squares(s.board, cells)
        for sq in caps:
            board.pop(sq, None)
        final = cells[-1]
        # promote only if ENDING the move on the far rank
        if kind == "m" and final[1] == _king_row(pl):
            kind = "k"
        board[final] = (pl, kind)
        progress = bool(caps) or s.board[cells[0]][1] == "m"
        return CrodaState(
            board=board, to_move=1 - pl,
            halfmove=0 if progress else s.halfmove + 1, ply=s.ply + 1,
        )

    def is_terminal(self, s: CrodaState) -> bool:
        return self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: CrodaState) -> list[float]:
        if self._draw(s):
            return [0.0, 0.0]
        # no legal move: the player to move loses
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: CrodaState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, k] for (c, r), (pl, k) in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> CrodaState:
        return CrodaState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"], halfmove=d["halfmove"], ply=d["ply"],
        )

    def describe_move(self, s: CrodaState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        caps = self._captured_squares(s.board, cells)
        sep = "x" if caps else "-"
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        return sep.join(alg(c) for c in cells)

    def render(self, s: CrodaState, perspective=None) -> dict:
        names = {0: "White", 1: "Black"}
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
