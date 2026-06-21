"""Frisian Draughts (Frysk dammen) — 10x10, played on dark squares.

Same family as International Draughts, but with Frisian capture geometry:

* **Men capture in ALL 8 directions** — a man jumps an adjacent enemy in any
  orthogonal (horizontal/vertical) or diagonal direction, landing on the empty
  square immediately beyond. (Men still *move*, when not capturing, one square
  diagonally FORWARD only.)
* **Flying kings move and capture along ALL 8 lines** — the four diagonals and
  the four orthogonals. A king slides any distance over empty squares, jumps a
  single enemy with at least one empty square beyond, and lands on any empty
  square past it along that same line, then optionally continues.
* **Weighted maximum capture.** Among capture sequences you must play one of
  greatest VALUE. The tie-break implemented here (the common Frisian rule):
  first maximise the NUMBER of captured pieces; among those, maximise the
  number of captured KINGS (a king is worth more than a man). Any sequence that
  is maximal under that ordering is legal.

Captured pieces are removed only at the END of the move; a piece may not be
jumped twice in one sequence. A man promotes to king only if it ENDS its move on
the last rank (passing over it mid-capture does not promote).

You lose if you have no legal move on your turn. Draw by a no-progress rule and a
hard ply cap (for guaranteed termination).

Moves are the platform's clickable cell-path notation: the squares the piece
visits, e.g. "1,2>2,3" (a quiet diagonal move) or "4,4>6,4>6,6" (an orthogonal
then diagonal capture chain).

Player 0 (White, rows 0-3) moves toward row 9; player 1 (Black, rows 6-9) toward
row 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 10
DRAW_HALFMOVE = 50
PLY_CAP = 400

# Movement step vectors that keep a piece on the dark squares. Diagonal
# neighbours are one step away; orthogonal neighbours (same colour, same
# row/column) are TWO board squares away, skipping the intervening light square.
# So a Frisian orthogonal capture jumps the dark square two away and lands two
# beyond it (four squares total). Each vector below moves from one dark square to
# the next dark square along its line.
DIAGS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ORTHO = [(2, 0), (-2, 0), (0, 2), (0, -2)]
ALL8 = DIAGS + ORTHO


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


def _man_move_dirs(player: int):
    """Quiet-move directions for a man: diagonally forward only."""
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
    jumped this sequence (a piece may not be jumped twice). A man captures in all
    8 directions (orthogonal + diagonal), landing exactly two squares beyond an
    adjacent enemy. A man promotes (and must stop) only by ENDING on the king
    row -- passing over it mid-capture does not promote, so the capture
    continues as a man."""
    c, r = pos
    paths = []
    for dc, dr in ALL8:
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
    """Capture sequences for a FLYING KING at `pos`. Slide along any of the 8
    lines (diagonals + orthogonals) over empty squares until reaching exactly one
    enemy piece not yet captured; then land on any empty square beyond it (along
    the same line) before the next obstruction, and optionally continue.
    `origin` is the now-vacated true start square (treated as empty when
    sliding)."""
    c, r = pos
    paths = []
    for dc, dr in ALL8:
        # advance over empties to find the first piece on this line
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


class FrisianDraughts(Game):
    uid = "frisian_draughts"
    name = "Frisian Draughts"

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
        gaps): the single enemy piece strictly between consecutive vertices.
        Works for both diagonal and orthogonal segments."""
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

    def _value(self, board, path):
        """Official Frisian weighted value of a capture path: a king is worth
        **1.5 men** and the SUMMED value is maximised (not a lexicographic
        count-then-kings tie-break). With integer weights man=2, king=3 (ratio
        1:1.5), the value is ``2*men + 3*kings == 2*len(caps) + kings``. Larger is
        better. E.g. 2 kings (value 6) ties 3 men (value 6) — both legal; 3 kings
        (value 9) beats 4 men (value 8) — the 3-king capture is forced."""
        caps = self._captured_squares(board, path)
        kings = sum(1 for sq in caps if board[sq][1] == "k")
        return 2 * len(caps) + kings

    def _all_moves(self, s: DraughtsState) -> list[list]:
        """Legal move paths. Mandatory WEIGHTED-maximum capture: if any capture
        exists, only sequences of maximal summed value (king = 1.5 men) are
        legal."""
        mine = [(pos, k) for pos, k in s.board.items() if k[0] == s.to_move]
        captures = []
        for pos, (pl, kind) in mine:
            if kind == "k":
                captures += _king_capture_paths(s.board, pos, pos, pl, frozenset())
            else:
                captures += _man_capture_paths(s.board, pos, pos, pl, frozenset())
        if captures:
            best = max(self._value(s.board, p) for p in captures)
            return [p for p in captures if self._value(s.board, p) == best]
        # quiet moves
        simples = []
        for pos, (pl, kind) in mine:
            c, r = pos
            if kind == "k":
                for dc, dr in ALL8:
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
