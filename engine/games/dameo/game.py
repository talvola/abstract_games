"""Dameo (Christian Freeling, 2000) — a modern 8x8 draughts variant on ALL squares.

Each player starts with 18 men in a trapezoidal "phalanx" formation (full back
rank, then progressively shorter centred rows). Three movement ideas:

  (A) MAN STEP — a single man moves one square FORWARD: straight-forward
      (orthogonal) OR diagonally-forward. (White, rows up, steps (0,+1),
      (+1,+1), (-1,+1); Black mirrors downward.) Men do NOT step sideways or
      backward.

  (B) LINEAR MOVEMENT (the Dameo signature) — a straight UNBROKEN line of two
      or more of your OWN adjacent men, oriented along one of the three forward
      axes (a column, or either forward diagonal), moves ONE square forward
      along that axis when the cell at the front of the line is empty. The whole
      file shifts forward one: the rear man vacates, the empty square just past
      the front fills (equivalently, the rear man "jumps over" the file to the
      empty square in front). Lines oriented sideways (a horizontal row) cannot
      move, because sideways is not a forward man-direction; kings never take
      part in a linear move.

  (C) CAPTURE — a man captures ORTHOGONALLY only (forward, backward or
      sideways: (+/-1,0),(0,+/-1)) by jumping a single adjacent enemy to the
      empty square just beyond. Captures are MANDATORY, CHAINED and MAXIMAL
      (you must play a sequence taking the greatest number of enemy pieces).
      Jumped pieces stay on the board (blocking re-jump) until the whole move
      completes, then are all removed at once; a piece may not be jumped twice.

A man that ENDS its move on the far rank becomes a flying KING: it moves
queen-wise (any distance in all 8 directions over empty squares) but captures
rook-wise (orthogonally) by the long leap — sliding over empty squares to a
single enemy, then landing on any empty square beyond it, optionally chaining.

WIN: a player with no men/kings, or with no legal move, loses. A 50-ply
no-progress rule (no capture, no man step / no man advancing) and a 400-ply hard
cap force a draw to guarantee termination.

Moves use the platform's clickable cell-path notation:
  - man step / king quiet move:  "c,r>c,r"
  - linear move:                 "rear>front_dest"  (the rear man's square to
                                  the empty square just past the front of the
                                  line; spans >=2 squares so it never collides
                                  with a 1-square man step)
  - capture (man or king):       the visited squares, e.g. "2,2>2,4>4,4".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 8
DRAW_HALFMOVE = 50
PLY_CAP = 400

# Orthogonal directions (capture directions for men, and king ortho captures).
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
# All eight directions (king quiet move).
DIRS8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


@dataclass
class DameoState:
    board: dict = field(default_factory=dict)  # (c, r) -> (player, "m"|"k")
    to_move: int = 0
    halfmove: int = 0   # plies since last capture or man advance (no-progress)
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _king_row(player: int) -> int:
    return N - 1 if player == 0 else 0


def _forward_dirs(player: int):
    """The three forward man-step directions (also the linear-move axes)."""
    f = 1 if player == 0 else -1
    return [(0, f), (1, f), (-1, f)]


def _start_board() -> dict:
    """Trapezoidal Dameo opening: full back rank, then rows shrinking by one cell
    on each side. White on rows 0,1,2; Black mirrored on rows 7,6,5. 18 men each:
      White: row0 c=0..7 (8), row1 c=1..6 (6), row2 c=2..5 (4).
      Black: row7 c=0..7 (8), row6 c=1..6 (6), row5 c=2..5 (4).
    """
    b = {}
    rows_white = {0: range(0, 8), 1: range(1, 7), 2: range(2, 6)}
    for r, cols in rows_white.items():
        for c in cols:
            b[(c, r)] = (0, "m")
    rows_black = {7: range(0, 8), 6: range(1, 7), 5: range(2, 6)}
    for r, cols in rows_black.items():
        for c in cols:
            b[(c, r)] = (1, "m")
    return b


# ---------------------------------------------------------------------------
# Capture generation (orthogonal short leaps for men; long leaps for kings)
# ---------------------------------------------------------------------------

def _man_capture_paths(board, pos, origin, player, captured):
    """Capture sequences for a MAN at `pos`. `board` is the ORIGINAL board
    (captured pieces are not removed until the move ends), `origin` is the
    moving piece's true start square (treated as empty, since it is vacated),
    `captured` is the set of enemy squares already jumped this sequence (no
    piece may be jumped twice). Men capture in the four ORTHOGONAL directions,
    landing exactly two squares beyond an adjacent enemy."""
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
    """Capture sequences for a flying KING at `pos`. Kings capture ROOK-wise
    (orthogonally): slide over empty squares along an orthogonal line to the
    first piece; if it is an uncaptured enemy, land on any empty square beyond
    it (before the next obstruction) and optionally continue."""
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
            free = occ is None or sq == origin
            if free:
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


# ---------------------------------------------------------------------------
# Quiet (non-capturing) move generation
# ---------------------------------------------------------------------------

def _linear_moves(board, player):
    """All LINEAR moves for `player`: maximal unbroken lines of own men along a
    forward axis that can shift one square forward (front cell empty). Returns a
    list of (rear_square, front_dest_square) pairs. Single-man "lines" along a
    forward axis are exactly the diagonal/straight man steps and are emitted
    here too (so all quiet man movement flows through one generator)."""
    own = {pos for pos, (pl, k) in board.items() if pl == player and k == "m"}
    moves = []
    for dc, dr in _forward_dirs(player):
        seen_rear = set()
        for pos in own:
            # Only start a line at its REAR (no own man behind it on this axis).
            behind = (pos[0] - dc, pos[1] - dr)
            if behind in own:
                continue
            if pos in seen_rear:
                continue
            seen_rear.add(pos)
            # Walk forward collecting the unbroken run of own men.
            front = pos
            length = 1
            while True:
                nxt = (front[0] + dc, front[1] + dr)
                if nxt in own:
                    front = nxt
                    length += 1
                else:
                    break
            dest = (front[0] + dc, front[1] + dr)
            if _on(*dest) and board.get(dest) is None:
                moves.append((pos, dest))
    return moves


def _king_quiet_moves(board, pos):
    """Queen-wise slides for a king over empty squares in all eight directions."""
    c, r = pos
    out = []
    for dc, dr in DIRS8:
        i = 1
        while True:
            t = (c + i * dc, r + i * dr)
            if not _on(*t) or board.get(t) is not None:
                break
            out.append([pos, t])
            i += 1
    return out


class Dameo(Game):
    uid = "dameo"
    name = "Dameo"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DameoState:
        return DameoState(board=_start_board())

    def current_player(self, s: DameoState) -> int:
        return s.to_move

    def _draw(self, s: DameoState) -> bool:
        return s.halfmove >= DRAW_HALFMOVE or s.ply >= PLY_CAP

    def _captured_squares(self, board, path):
        """ENEMY squares jumped along a visited-square capture path (handles the
        flying-king gaps): the single ENEMY piece strictly between consecutive
        vertices on the orthogonal line. Only enemy pieces count, so a LINEAR
        move (own men between rear and dest) yields no captures and is not
        mistaken for a jump. `path[0]` holds the mover, fixing whose enemies."""
        mover = board.get(path[0])
        player = mover[0] if mover is not None else None
        caps = []
        for a, b in zip(path, path[1:]):
            dc = (b[0] > a[0]) - (b[0] < a[0])
            dr = (b[1] > a[1]) - (b[1] < a[1])
            step = (a[0] + dc, a[1] + dr)
            while step != b:
                occ = board.get(step)
                if occ is not None:
                    if player is None or occ[0] != player:
                        caps.append(step)
                    break
                step = (step[0] + dc, step[1] + dr)
        return caps

    def _all_capture_paths(self, s: DameoState):
        mine = [(pos, k) for pos, k in s.board.items() if k[0] == s.to_move]
        captures = []
        for pos, (pl, kind) in mine:
            if kind == "k":
                captures += _king_capture_paths(s.board, pos, pos, pl, frozenset())
            else:
                captures += _man_capture_paths(s.board, pos, pos, pl, frozenset())
        return captures

    def _all_moves(self, s: DameoState):
        """Legal move paths. Mandatory MAXIMUM capture (majority rule): if any
        capture exists, only the longest sequences are legal; otherwise quiet
        man steps + linear moves + king slides."""
        captures = self._all_capture_paths(s)
        if captures:
            best = max(self._num_caps(s.board, p) for p in captures)
            return [p for p in captures if self._num_caps(s.board, p) == best]
        moves = []
        # Linear moves (length-1 lines are the ordinary man steps).
        for rear, dest in _linear_moves(s.board, s.to_move):
            moves.append([rear, dest])
        # King quiet slides.
        for pos, (pl, kind) in s.board.items():
            if pl == s.to_move and kind == "k":
                moves += _king_quiet_moves(s.board, pos)
        return moves

    def _num_caps(self, board, path):
        return len(self._captured_squares(board, path))

    def legal_moves(self, s: DameoState) -> list[str]:
        if self._draw(s):
            return []
        return [">".join(f"{c},{r}" for c, r in path) for path in self._all_moves(s)]

    def apply_move(self, s: DameoState, move: str, rng=None) -> DameoState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        first = cells[0]
        pl, kind = board[first]
        caps = self._captured_squares(s.board, cells)

        if caps:
            # Capture move (man short leaps or king long leaps): remove the
            # mover from its start, drop all captured at the end, place the
            # mover on the final square.
            del board[first]
            for sq in caps:
                board.pop(sq, None)
            final = cells[-1]
            if kind == "m" and final[1] == _king_row(pl):
                kind = "k"
            board[final] = (pl, kind)
            progress = True
        elif kind == "k":
            # King quiet slide.
            del board[first]
            board[cells[-1]] = (pl, kind)
            progress = False
        else:
            # Quiet MAN move: a linear file-shift (length 1 == ordinary step).
            rear, dest = cells
            ddc = (dest[0] > rear[0]) - (dest[0] < rear[0])
            ddr = (dest[1] > rear[1]) - (dest[1] < rear[1])
            # Gather the file from rear forward to (but not including) dest.
            file_cells = []
            cur = rear
            while cur != dest:
                file_cells.append(cur)
                cur = (cur[0] + ddc, cur[1] + ddr)
            # Shift every man one square forward along the axis; the rear vacates
            # and dest fills. Promote any man that lands on the king row.
            for sq in file_cells:
                del board[sq]
            for sq in file_cells:
                nxt = (sq[0] + ddc, sq[1] + ddr)
                k = "k" if nxt[1] == _king_row(pl) else "m"
                board[nxt] = (pl, k)
            progress = True

        return DameoState(
            board=board,
            to_move=1 - pl,
            halfmove=0 if progress else s.halfmove + 1,
            ply=s.ply + 1,
        )

    def is_terminal(self, s: DameoState) -> bool:
        return self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: DameoState) -> list[float]:
        if self._draw(s):
            return [0.0, 0.0]
        # Side to move has no legal move -> it loses.
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: DameoState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, k] for (c, r), (pl, k) in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> DameoState:
        return DameoState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"], halfmove=d["halfmove"], ply=d["ply"],
        )

    def describe_move(self, s: DameoState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        caps = self._captured_squares(s.board, cells)
        sep = "x" if caps else "-"
        return sep.join(f"{c},{r}" for c, r in cells)

    def render(self, s: DameoState, perspective=None) -> dict:
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
