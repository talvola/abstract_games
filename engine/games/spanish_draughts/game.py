"""Spanish Draughts (Damas Españolas) — the traditional 8x8 Spanish ruleset.

Rules follow the standard Spanish/Portuguese "dama" as documented by ludoteka.com
and mindsports.nl (Ed van Zon, "On the evolution of draughts variants"). Played on
one colour of an 8x8 board, 12 men per side. White moves first.

Distinctive Spanish rules (see rules.md for the full diff vs the siblings):

* **Men move and capture FORWARD only** — a man jumps an adjacent enemy piece and
  lands on the empty square immediately beyond it, in a forward diagonal only
  (men never capture backward, unlike Brazilian/Russian).
* **Men CAN capture kings** — a man may jump ANY enemy piece, man or king (unlike
  Italian, where a man may never capture a king). This is the load-bearing
  difference from Italian.
* **Kings are FLYING ("long") kings** — a king slides any distance along a clear
  diagonal, and captures by leaping a single enemy piece (any number of empty
  squares before it) to land on any empty square beyond, forward OR backward
  (unlike Italian's short/non-flying king).
* **Capture is mandatory and MAXIMUM**, chosen by a two-level priority:
    1. **Quantity** — capture the greatest NUMBER of pieces;
    2. **Quality** — among those, capture the greatest number of KINGS.
  Any sequences still tied may be chosen freely. (Spanish has NO Italian-style
  "must capture with a king" or "earliest king" sub-rules.)
* Captured pieces are removed only at the END of the sequence, and a piece may
  not be jumped twice in one sequence (so jumped pieces stay on as blockers).
* A man promotes to king only if it ENDS its move on the last rank. A man that
  reaches the last rank during a capture stops there and promotes (it does not
  continue jumping as a king that turn). Because men capture forward only,
  reaching the last rank is always the end of a sequence.

Board orientation: the mirror of Italian. The playing squares are (col+row) EVEN,
which puts each player's near-right square on a LIGHT (non-playing) square and the
double corner on the player's LEFT — the traditional Spanish orientation.

Moves are the platform's clickable cell-path notation: the squares the moving
piece visits, e.g. "0,2>1,3" (simple) or "3,3>5,5>7,3" (a chain). Because only
maximal, highest-priority capture sequences are legal, clicking a chain forces it
to completion.

Player 0 (White, rows 0-2) moves toward row 7; player 1 (Black, rows 5-7) toward
row 0. Draw by a 50-ply no-progress rule (no capture and no man move) and a hard
400-ply cap.
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
    """12 men per side on the (c+r) EVEN squares of the three nearest ranks:
    White on rows 0-2, Black on rows 5-7. This parity places each player's
    near-RIGHT square on a light (non-playing) cell — the Spanish orientation
    (double corner on the left), the mirror of Italian."""
    b = {}
    for r in (0, 1, 2):
        for c in range(N):
            if (c + r) % 2 == 0:
                b[(c, r)] = (0, "m")
    for r in (5, 6, 7):
        for c in range(N):
            if (c + r) % 2 == 0:
                b[(c, r)] = (1, "m")
    return b


def _man_capture_paths(board, pos, origin, player, captured):
    """Capture sequences for a MAN at `pos`. `board` is the ORIGINAL board (pieces
    removed only at the end), `origin` = the moving man's true start square (now
    vacated, treated as empty), `captured` = enemy squares already jumped this
    sequence (a piece may not be jumped twice).

    A man captures FORWARD only, over an adjacent enemy of EITHER kind (man OR
    king — Spanish men may capture kings), landing exactly two squares beyond. A
    man that lands on its king row STOPS (it promotes and the sequence ends)."""
    c, r = pos
    paths = []
    for dc, dr in _man_dirs(player):
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
        if not _on(*land):
            continue
        occ = board.get(over)
        if occ is None or occ[0] == player:
            continue
        if over in captured or over == origin:
            continue
        land_free = board.get(land) is None or land == origin
        if not land_free:
            continue
        if land[1] == _king_row(player):
            # man reaches the last rank: it promotes and the sequence ends here
            paths.append([pos, land])
            continue
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
    obstruction, and optionally continue. Kings capture forward AND backward.
    `origin` is the now-vacated true start square (treated as empty when
    sliding)."""
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


class SpanishDraughts(Game):
    name = "Spanish Draughts"

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
        """Enemy squares jumped along a visited-square path (handles flying-king
        gaps): the single occupied square strictly between consecutive vertices,
        in capture order."""
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

    def _seq_key(self, board, path):
        """Priority key for a capture sequence, to be MAXIMISED:
        (number of pieces captured, number of KINGS captured). Quantity first,
        then quality (most kings). No 'capture with a king' or 'earliest king'
        sub-rule — those are Italian, not Spanish."""
        caps = self._captured_squares(board, path)
        kings = sum(1 for sq in caps if board[sq][1] == "k")
        return (len(caps), kings)

    def _all_moves(self, s: DraughtsState) -> list[list]:
        """Legal move paths. If any capture exists, only the sequences with the
        maximal (pieces, kings) priority key are legal."""
        mine = [(pos, k) for pos, k in s.board.items() if k[0] == s.to_move]
        captures = []
        for pos, (pl, kind) in mine:
            if kind == "k":
                captures += _king_capture_paths(s.board, pos, pos, pl, frozenset())
            else:
                captures += _man_capture_paths(s.board, pos, pos, pl, frozenset())
        if captures:
            best = max(self._seq_key(s.board, p) for p in captures)
            return [p for p in captures if self._seq_key(s.board, p) == best]
        # quiet moves: men one square forward, kings slide any distance
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
        started_as_man = s.board[cells[0]][1] == "m"
        progress = bool(caps) or started_as_man
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
