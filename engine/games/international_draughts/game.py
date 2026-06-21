"""International Draughts (Polish draughts) — 10x10, played on dark squares.

20 men each. Men move one square diagonally FORWARD to an empty square, but
CAPTURE both forward and backward. Kings are FLYING: they slide any distance
along a diagonal over empty squares, and capture by leaping a single enemy
piece (with any number of empty squares before it) and landing on any empty
square beyond, then optionally continuing the chain.

Captures are MANDATORY and you must play a sequence that captures the MAXIMUM
number of pieces (the "majority" rule); among maximal sequences any may be
chosen. Captured pieces are removed only at the END of the move, and a piece
may not be jumped twice in one sequence. A man promotes to king only if it ENDS
its move on the last rank (merely passing over the last rank mid-capture does
NOT promote).

You lose if you have no legal move (all captured or blocked). Draw by a 50-ply
no-progress rule (no capture and no man move) and a hard 400-ply cap.

Moves are the platform's clickable cell-path notation: the squares the piece
visits, e.g. "1,2>2,3" (simple) or "3,6>5,4>7,6" (a man double-jump). Because
only maximal capture sequences are legal, the UI forces a chain to completion.

Player 0 (White, rows 0-3) moves toward row 9; player 1 (Black, rows 6-9)
toward row 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 10
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


def _man_dirs(player: int):
    return [(1, 1), (-1, 1)] if player == 0 else [(1, -1), (-1, -1)]


def _start_board() -> dict:
    b = {}
    for r in (0, 1, 2, 3):
        for c in range(N):
            if (c + r) % 2 == 1:
                b[(c, r)] = (0, "m")
    for r in (6, 7, 8, 9):
        for c in range(N):
            if (c + r) % 2 == 1:
                b[(c, r)] = (1, "m")
    return b


def _man_capture_paths(board, pos, origin, player, captured):
    """Capture sequences for a MAN at `pos`. board is the ORIGINAL board (pieces
    only removed at end), `origin` = the moving piece's true start square (now
    vacated, so treated as empty), `captured` = set of enemy squares already
    jumped this sequence (a piece may not be jumped twice). Men capture in all 4
    diagonals, landing exactly two squares beyond an adjacent enemy. A man
    promotes (and must stop) only by ENDING on the king row — passing over it
    mid-capture does not promote, so the capture may continue."""
    c, r = pos
    paths = []
    for dc, dr in DIAGS:
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
        if not _on(*land):
            continue
        occ = board.get(over)
        # The jumped square must hold an uncaptured enemy; the landing square
        # must be empty (or be the now-vacated origin of the moving piece).
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
    """Capture sequences for a FLYING KING at `pos`. Slide along a diagonal over
    empty squares until reaching exactly one enemy piece not yet captured; then
    land on any empty square beyond it (along the same diagonal) before the next
    obstruction, and optionally continue. `origin` is the now-vacated true start
    square (treated as empty when sliding)."""
    c, r = pos
    paths = []
    for dc, dr in DIAGS:
        # advance over empties to find the first piece on this diagonal
        i = 1
        over = None
        while True:
            sq = (c + i * dc, r + i * dr)
            if not _on(*sq):
                break
            occ = board.get(sq)
            free = occ is None or sq == origin
            if free:
                i += 1
                continue
            over = sq
            break
        if over is None:
            continue
        occ = board.get(over)
        # must be an enemy piece not already jumped
        if occ[0] == player or over in captured:
            continue
        # land squares: empties beyond `over` until next obstruction/edge
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


def _count_captures(path) -> int:
    """Number of enemy pieces jumped along a visited-square path. For a king the
    captured squares aren't midpoints, so recompute geometrically: between each
    consecutive pair there is exactly one enemy on the diagonal."""
    return len(path) - 1


class InternationalDraughts(Game):
    uid = "international_draughts"
    name = "International Draughts"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DraughtsState:
        return DraughtsState(board=_start_board())

    def current_player(self, s: DraughtsState) -> int:
        return s.to_move

    def _draw(self, s: DraughtsState) -> bool:
        return s.halfmove >= DRAW_HALFMOVE or s.ply >= PLY_CAP

    def _captured_squares(self, board, path):
        """Enemy squares jumped along a visited-square path (handles flying king
        gaps): the single enemy piece strictly between consecutive vertices."""
        caps = []
        for a, b in zip(path, path[1:]):
            dc = (b[0] > a[0]) - (b[0] < a[0])
            dr = (b[1] > a[1]) - (b[1] < a[1])
            step = (a[0] + dc, a[1] + dr)
            while step != b:
                if board.get(step) is not None:
                    caps.append(step)
                    break
                step = (step[0] + dc, step[1] + dr)
        return caps

    def _all_moves(self, s: DraughtsState) -> list[list]:
        """Legal move paths. Mandatory MAXIMUM capture (majority rule): if any
        capture exists, only sequences capturing the maximum number are legal."""
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
        # quiet moves
        simples = []
        for pos, (pl, kind) in mine:
            c, r = pos
            if kind == "k":
                for dc, dr in DIAGS:
                    i = 1
                    while True:
                        t = (c + i * dc, r + i * dr)
                        if not _on(*t) or s.board.get(t) is not None:
                            break
                        simples.append([pos, t])
                        i += 1
            else:
                for dc, dr in _man_dirs(pl):
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
        caps = self._captured_squares(s.board, cells)
        for sq in caps:
            board.pop(sq, None)
        final = cells[-1]
        # promote only if ENDING on the king row
        if kind == "m" and final[1] == _king_row(pl):
            kind = "k"
        board[final] = (pl, kind)
        captured = bool(caps)
        progress = captured or s.board[cells[0]][1] == "m"
        return DraughtsState(
            board=board, to_move=1 - pl,
            halfmove=0 if progress else s.halfmove + 1, ply=s.ply + 1,
        )

    def is_terminal(self, s: DraughtsState) -> bool:
        return self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: DraughtsState) -> list[float]:
        if self._draw(s):
            return [0.0, 0.0]
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
        caps = self._captured_squares(s.board, cells)
        sep = "x" if caps else "-"
        return sep.join(f"{c},{r}" for c, r in cells)

    def render(self, s: DraughtsState, perspective=None) -> dict:
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
