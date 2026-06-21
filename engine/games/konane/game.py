"""Kōnane — Hawaiian checkers, a combinatorial-game-theory classic.

N×N board (N = 6/8/10, option). The board starts COMPLETELY FILLED with
alternating black and white stones in a checkerboard pattern: cell (c, r) holds
Black when (c + r) is even, White when (c + r) is odd. Black is player 0,
White is player 1; Black moves first.

OPENING (two single-stone removals, one per side):
  Move 1 — Black removes one black stone from a *corner* or one of the (one or
           four) *center* squares.
  Move 2 — White removes one white stone *orthogonally adjacent* to the square
           Black just emptied.
Each opening removal is encoded as a 1-cell path (just the cell id), so the UI
treats it as a single click.

NORMAL PLAY (orthogonal jump-captures):
A player moves one of their stones by jumping orthogonally over an
orthogonally-adjacent enemy stone into the empty square beyond, removing the
jumped enemy stone. The SAME stone may continue jumping in the SAME straight-
line direction over successive enemy stones (each jump removes the jumped
stone); the player may stop after any jump. No diagonal moves, no turning
within a multi-jump, no promotion.

Moves are the platform's clickable cell-path notation: the squares the stone
visits, e.g. "2,0>0,0" (single jump, landing two squares away) or
"6,0>4,0>2,0" (double jump in a straight line). The opening removals are the
emptied cell alone, e.g. "0,0".

WIN: the first player who cannot move (has no legal capture) LOSES — i.e. the
last player to move wins (normal-play convention). No draws are possible
(someone always runs out of moves first); a hard ply cap is a safety net only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

PLY_CAP = 4000
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]

# Phases
P_OPEN1 = 0   # Black removes a corner/center stone
P_OPEN2 = 1   # White removes a stone adjacent to the first empty square
P_PLAY = 2    # normal jump-capture play


@dataclass
class KonaneState:
    n: int = 8
    board: dict = field(default_factory=dict)  # (c, r) -> player (0 Black / 1 White)
    to_move: int = 0
    phase: int = P_OPEN1
    first_empty: tuple | None = None  # the cell Black emptied in move 1
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _start_board(n: int) -> dict:
    # (c + r) even -> Black (0), odd -> White (1)
    return {(c, r): (c + r) % 2 for c in range(n) for r in range(n)}


def _on(n, c, r):
    return 0 <= c < n and 0 <= r < n


def _corner_cells(n: int):
    return [(0, 0), (n - 1, 0), (0, n - 1), (n - 1, n - 1)]


def _center_cells(n: int):
    """The board's central square(s). For even N the center is the 2x2 block of
    the four innermost cells; for odd N it is the single middle cell."""
    if n % 2 == 1:
        m = n // 2
        return [(m, m)]
    a, b = n // 2 - 1, n // 2
    return [(a, a), (a, b), (b, a), (b, b)]


def _opening1_cells(s: KonaneState):
    """Black's legal first removals: a corner or center cell that holds a black
    stone (Black = even parity, so corners and the even-parity center cells)."""
    cands = set(_corner_cells(s.n)) | set(_center_cells(s.n))
    return sorted(c for c in cands if s.board.get(c) == 0)


def _opening2_cells(s: KonaneState):
    """White's legal second removals: a white stone orthogonally adjacent to the
    square Black emptied in move 1."""
    fc, fr = s.first_empty
    out = []
    for dc, dr in ORTHO:
        t = (fc + dc, fr + dr)
        if _on(s.n, *t) and s.board.get(t) == 1:
            out.append(t)
    return sorted(out)


def _jump_paths(board: dict, n: int, pos, player: int):
    """All legal jump sequences from `pos` for `player`. Each step jumps over an
    adjacent enemy into the empty square beyond, in a FIXED straight-line
    direction (no turns); the player may stop after any jump. Returns a list of
    paths [pos, land1, land2, ...]."""
    paths = []
    for dc, dr in ORTHO:
        seq = _jump_dir(board, n, pos, player, dc, dr)
        paths += seq
    return paths


def _jump_dir(board: dict, n: int, pos, player: int, dc: int, dr: int):
    """All prefixes of the maximal straight-line jump in direction (dc, dr)."""
    paths = []
    cur = pos
    b = board
    while True:
        c, r = cur
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
        occ = b.get(over)
        if not (_on(n, *land) and occ is not None and occ != player and b.get(land) is None):
            break
        # perform this jump on a copy so further jumps see the removed stone
        nb = dict(b)
        del nb[over]
        if cur in nb:
            del nb[cur]
        nb[land] = player
        # record path from original pos to this landing
        if not paths:
            paths.append([pos, land])
        else:
            paths.append(paths[-1] + [land])
        b = nb
        cur = land
    return paths


class Konane(Game):
    uid = "konane"
    name = "Kōnane"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> KonaneState:
        n = 8
        if options and "size" in options:
            n = int(options["size"])
        return KonaneState(n=n, board=_start_board(n))

    def current_player(self, s: KonaneState) -> int:
        return s.to_move

    def _capped(self, s: KonaneState) -> bool:
        return s.ply >= PLY_CAP

    def _all_play_moves(self, s: KonaneState):
        paths = []
        for pos, owner in s.board.items():
            if owner == s.to_move:
                paths += _jump_paths(s.board, s.n, pos, owner)
        return paths

    def legal_moves(self, s: KonaneState) -> list[str]:
        if self._capped(s):
            return []
        if s.phase == P_OPEN1:
            return [f"{c},{r}" for (c, r) in _opening1_cells(s)]
        if s.phase == P_OPEN2:
            return [f"{c},{r}" for (c, r) in _opening2_cells(s)]
        return [">".join(f"{c},{r}" for c, r in path) for path in self._all_play_moves(s)]

    def apply_move(self, s: KonaneState, move: str, rng=None) -> KonaneState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        if s.phase == P_OPEN1:
            board.pop(cells[0], None)
            return KonaneState(
                n=s.n, board=board, to_move=1, phase=P_OPEN2,
                first_empty=cells[0], ply=s.ply + 1,
            )
        if s.phase == P_OPEN2:
            board.pop(cells[0], None)
            return KonaneState(
                n=s.n, board=board, to_move=0, phase=P_PLAY,
                first_empty=s.first_empty, ply=s.ply + 1,
            )
        # normal play: a straight-line jump path; remove each jumped enemy stone
        player = board.pop(cells[0])
        for a, b in zip(cells, cells[1:]):
            mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
            board.pop(mid, None)
        board[cells[-1]] = player
        return KonaneState(
            n=s.n, board=board, to_move=1 - player, phase=P_PLAY,
            first_empty=s.first_empty, ply=s.ply + 1,
        )

    def is_terminal(self, s: KonaneState) -> bool:
        return self._capped(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: KonaneState) -> list[float]:
        if self._capped(s):
            return [0.0, 0.0]
        # player to move has no move -> they lose (last player to move wins)
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: KonaneState) -> dict:
        return {
            "n": s.n,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "phase": s.phase,
            "first_empty": (None if s.first_empty is None
                            else f"{s.first_empty[0]},{s.first_empty[1]}"),
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> KonaneState:
        fe = d.get("first_empty")
        return KonaneState(
            n=d["n"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            phase=d["phase"],
            first_empty=(None if fe is None else _cell(fe)),
            ply=d["ply"],
        )

    def describe_move(self, s: KonaneState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        alg = lambda c: f"{chr(ord('a') + c[0])}{c[1] + 1}"  # noqa: E731
        if s.phase in (P_OPEN1, P_OPEN2):
            return f"remove {alg(cells[0])}"
        return "x".join(alg(c) for c in cells)

    def render(self, s: KonaneState, perspective=None) -> dict:
        names = {0: "Black", 1: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = "Draw (ply cap)"
            else:
                caption = f"{names[0 if ret[0] > 0 else 1]} wins"
        elif s.phase == P_OPEN1:
            caption = "Black: remove a corner or center stone"
        elif s.phase == P_OPEN2:
            caption = "White: remove an adjacent stone"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": s.n, "height": s.n},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
