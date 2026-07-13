"""Pool Checkers — American Pool draughts (the same rules as Russian Draughts,
but with NO promotion during a capture chain).

Pool checkers is played on the 8x8 board, 12 men per side on the dark squares.
Men move one square diagonally FORWARD to an empty square, but CAPTURE both
forward and backward. Kings are FLYING: they slide any distance along a clear
diagonal, and capture by leaping a single enemy piece (any number of empty
squares before it) and landing on any empty square beyond, then optionally
continuing the chain.

Capture is MANDATORY but ANY (not maximum): when a capture exists a player must
capture, but may choose ANY available capture sequence — they are NOT forced to
take the longest / most pieces. Once a chain has started it must be finished.
Captured pieces are removed only at the END of the sequence and a piece may not
be jumped twice.

DEFINING RULE — deferred promotion. A man that reaches the king row DURING a
capture sequence does NOT become a king until the sequence is complete. It keeps
jumping as a MAN for the rest of that turn (so mid-sequence it can only make
man-style short jumps — never a king's flying/long jump) and promotes only at
the end if it finishes on the last rank. This is the ONLY difference from
Russian draughts, where such a man promotes IMMEDIATELY and continues the chain
as a flying king. (It also differs from Brazilian draughts, which forces the
MAXIMUM capture; Pool allows ANY capture.)

You lose if you have no legal move (all captured or blocked). Draw by a 50-ply
no-progress rule (no capture and no man move) and a hard 400-ply cap.

Moves are the platform's clickable cell-path notation: the squares the piece
visits, e.g. "1,2>2,3" (simple) or "3,4>5,2>3,0" (a man double-jump).

Player 0 (White, rows 0-2) moves toward row 7; player 1 (Black, rows 5-7)
toward row 0.
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


def _man_dirs(player: int):
    return [(1, 1), (-1, 1)] if player == 0 else [(1, -1), (-1, -1)]


def _start_board() -> dict:
    """12 men per side on the dark squares ((c+r) odd) of the three nearest
    ranks: White on rows 0-2, Black on rows 5-7."""
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


def _man_capture_paths(board, pos, origin, player, captured):
    """Capture sequences for a MAN at `pos`. board is the ORIGINAL board (pieces
    only removed at end), `origin` = the moving piece's true start square (now
    vacated, so treated as empty), `captured` = set of enemy squares already
    jumped this sequence (a piece may not be jumped twice). Men capture in all 4
    diagonals, landing exactly two squares beyond an adjacent enemy.

    DEFERRED PROMOTION: a man that reaches the king row mid-capture keeps
    jumping AS A MAN (short jumps only). It does NOT become a flying king, so
    this function is never asked for king-style continuations mid-sequence.
    Promotion happens only in apply_move when the man ENDS on the king row."""
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


class PoolCheckers(Game):
    uid = "pool_checkers"
    name = "Pool Checkers"

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
        """Legal move paths. Capture is MANDATORY but ANY: if any capture
        exists, ALL complete capture sequences are legal (the player is NOT
        forced to the maximum — this is the Pool/Russian 'choice of capture',
        the difference from Brazilian's majority rule). Otherwise, quiet moves.
        Every returned capture path is a COMPLETE chain (the recursion only
        stops a branch when no further capture is possible), so 'you must finish
        a started chain' is enforced."""
        mine = [(pos, k) for pos, k in s.board.items() if k[0] == s.to_move]
        captures = []
        for pos, (pl, kind) in mine:
            if kind == "k":
                captures += _king_capture_paths(s.board, pos, pos, pl, frozenset())
            else:
                captures += _man_capture_paths(s.board, pos, pos, pl, frozenset())
        if captures:
            return captures
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
        # DEFERRED promotion: a man promotes only if it ENDS the whole sequence
        # on the king row. Passing over / reaching it mid-capture does NOT
        # promote (the man kept jumping as a man; see _man_capture_paths).
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
