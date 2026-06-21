"""Turkish Draughts (Dama).

8x8 board using ALL squares. 16 men each, on the 2nd and 3rd ranks.
Men move one square ORTHOGONALLY forward or sideways (never diagonally,
never backward) to an empty square. Kings move any distance orthogonally
(a flying rook).

Captures: a man jumps an adjacent enemy orthogonally (forward or sideways)
to the empty square immediately beyond, removing it. A king captures by
sliding along a rank/file over empty squares to exactly one enemy piece,
then landing on any empty square beyond it (still in line), removing the
enemy. Captured pieces are removed IMMEDIATELY during the sequence (the
Turkish rule), so a freed square may be flown over later in the same chain
and an already-captured piece blocks no further than its now-empty square.

Capture is MANDATORY and the MAXIMUM-capture rule applies: you must play a
sequence that removes the greatest possible number of enemy pieces. A man
promotes to king on reaching the last rank; promotion ends the turn.

Moves are the platform's clickable cell-path notation: the squares the
moving piece visits, e.g. "1,2>1,3" (simple), "1,2>1,4" (man jump),
"0,0>0,5" (king jump). Only maximal capture sequences are legal, so the
UI naturally forces a chain to completion.

Player 0 (rows 0-1 at start) moves toward row 7; player 1 (rows 5-6)
toward row 0. Termination: a 60-ply no-progress rule (no capture and no
man move) and a hard 400-ply cap both end the game in a draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 8
DRAW_HALFMOVE = 60
PLY_CAP = 400

# Orthogonal unit directions.
UP = (0, 1)
DOWN = (0, -1)
LEFT = (-1, 0)
RIGHT = (1, 0)
ORTHO = [UP, DOWN, LEFT, RIGHT]


@dataclass
class DamaState:
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
    """Men move forward or sideways, never backward."""
    fwd = UP if player == 0 else DOWN
    return [fwd, LEFT, RIGHT]


def _start_board() -> dict:
    b = {}
    # White (player 0) on rows 1-2; row 0 (its 1st rank) stays empty.
    for r in (1, 2):
        for c in range(N):
            b[(c, r)] = (0, "m")
    # Black (player 1) on rows 5-6; row 7 (its 1st rank) stays empty.
    for r in (5, 6):
        for c in range(N):
            b[(c, r)] = (1, "m")
    return b


def _man_jumps(board: dict, pos, player: int):
    """All maximal man-jump sequences from `pos`. Returns paths [pos, land, ...].

    Captured pieces are removed immediately, so a square cleared earlier in the
    chain may be landed on / passed later. A man may jump forward or sideways
    (not backward). Promotion on the last rank ends the chain.
    """
    c, r = pos
    paths = []
    for dc, dr in _man_move_dirs(player):
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
        occ = board.get(over)
        if _on(*land) and occ is not None and occ[0] != player and board.get(land) is None:
            nb = dict(board)
            del nb[over]
            del nb[pos]
            promoted = land[1] == _king_row(player)
            if promoted:
                # Promotion ends the turn; no king continuation.
                paths.append([pos, land])
                continue
            nb[land] = (player, "m")
            cont = _man_jumps(nb, land, player)
            if cont:
                paths += [[pos] + p for p in cont]
            else:
                paths.append([pos, land])
    return paths


def _king_jumps(board: dict, pos, player: int):
    """All maximal king-jump sequences from `pos`. Returns paths [pos, land, ...].

    Along each orthogonal ray: skip empty squares, find exactly one enemy
    (an own piece or a second enemy blocks the ray), then each empty square
    beyond it (before any further piece) is a possible landing square.
    """
    c, r = pos
    paths = []
    for dc, dr in ORTHO:
        # advance over empty squares to the first occupied square
        x, y = c + dc, r + dr
        while _on(x, y) and board.get((x, y)) is None:
            x, y = x + dc, y + dr
        if not _on(x, y):
            continue
        target = board.get((x, y))
        if target is None or target[0] == player:
            continue  # blocked by own piece, or ran off board
        captured = (x, y)
        # landing squares: empties strictly beyond the captured piece
        lx, ly = x + dc, y + dr
        while _on(lx, ly) and board.get((lx, ly)) is None:
            land = (lx, ly)
            nb = dict(board)
            del nb[captured]
            del nb[pos]
            nb[land] = (player, "k")
            cont = _king_jumps(nb, land, player)
            if cont:
                paths += [[pos] + p for p in cont]
            else:
                paths.append([pos, land])
            lx, ly = lx + dc, ly + dr
    return paths


class TurkishDraughts(Game):
    uid = "turkish_draughts"
    name = "Turkish Draughts"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DamaState:
        return DamaState(board=_start_board())

    def current_player(self, s: DamaState) -> int:
        return s.to_move

    def _draw(self, s: DamaState) -> bool:
        return s.halfmove >= DRAW_HALFMOVE or s.ply >= PLY_CAP

    def _all_jumps(self, s: DamaState) -> list[list]:
        mine = [(pos, k) for pos, k in s.board.items() if k[0] == s.to_move]
        jumps = []
        for pos, (pl, kind) in mine:
            if kind == "k":
                jumps += _king_jumps(s.board, pos, pl)
            else:
                jumps += _man_jumps(s.board, pos, pl)
        return jumps

    def _count_captures(self, path) -> int:
        # number of pieces removed = number of jump steps in the path
        return len(path) - 1

    def _all_moves(self, s: DamaState) -> list[list]:
        """Legal move paths. Mandatory MAXIMUM capture: if any jump exists, only
        jump sequences removing the maximum number of pieces are legal."""
        jumps = self._all_jumps(s)
        if jumps:
            best = max(self._count_captures(p) for p in jumps)
            return [p for p in jumps if self._count_captures(p) == best]
        simples = []
        for pos, (pl, kind) in [(p, k) for p, k in s.board.items() if k[0] == s.to_move]:
            c, r = pos
            if kind == "k":
                for dc, dr in ORTHO:
                    x, y = c + dc, r + dr
                    while _on(x, y) and s.board.get((x, y)) is None:
                        simples.append([pos, (x, y)])
                        x, y = x + dc, y + dr
            else:
                for dc, dr in _man_move_dirs(pl):
                    t = (c + dc, r + dr)
                    if _on(*t) and t not in s.board:
                        simples.append([pos, t])
        return simples

    def legal_moves(self, s: DamaState) -> list[str]:
        if self._draw(s):
            return []
        return [">".join(f"{c},{r}" for c, r in path) for path in self._all_moves(s)]

    def apply_move(self, s: DamaState, move: str, rng=None) -> DamaState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        pl, kind = board.pop(cells[0])
        captured = False
        for a, b in zip(cells, cells[1:]):
            dc = (b[0] > a[0]) - (b[0] < a[0])
            dr = (b[1] > a[1]) - (b[1] < a[1])
            dist = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
            if dist >= 2:
                # capture step: find the (single) enemy piece between a and b
                x, y = a[0] + dc, a[1] + dr
                while (x, y) != b:
                    if board.get((x, y)) is not None:
                        board.pop((x, y), None)
                        captured = True
                        break
                    x, y = x + dc, y + dr
        final = cells[-1]
        if kind == "m" and final[1] == _king_row(pl):
            kind = "k"
        board[final] = (pl, kind)
        man_move = s.board[cells[0]][1] == "m"
        progress = captured or man_move
        return DamaState(
            board=board, to_move=1 - pl,
            halfmove=0 if progress else s.halfmove + 1, ply=s.ply + 1,
        )

    def is_terminal(self, s: DamaState) -> bool:
        return self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: DamaState) -> list[float]:
        if self._draw(s):
            return [0.0, 0.0]
        # no legal move: the player to move loses
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: DamaState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, k] for (c, r), (pl, k) in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> DamaState:
        return DamaState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"], halfmove=d["halfmove"], ply=d["ply"],
        )

    def describe_move(self, s: DamaState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        jump = any(
            max(abs(b[0] - a[0]), abs(b[1] - a[1])) >= 2
            for a, b in zip(cells, cells[1:])
        )
        sep = "x" if jump else "-"
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        return sep.join(alg(c) for c in cells)

    def render(self, s: DamaState, perspective=None) -> dict:
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
