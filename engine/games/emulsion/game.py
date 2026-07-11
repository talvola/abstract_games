"""Emulsion (Luis Bolanos Mures, 2020).

An n x n board starts completely full of black and white pieces in a checkered
pattern (on odd-sized boards the centre square -- and hence every square of the
centre's colour-parity, including the corners -- is White). Black moves first.

VALUE. A piece's value is the number of pieces of its own colour orthogonally
adjacent to it, plus HALF the number of board edges adjacent to its square
(corner squares add 1, non-corner rim squares add 1/2).

MOVE. On your turn, swap two orthogonally or diagonally adjacent pieces of
different colours such that the value of YOUR piece in the pair increases.
(Because the board is always full, a swap changes both pieces' values by
exactly the same amount, so both players always have the same set of available
swaps -- the designer notes this and it is provable; the selftest checks it.)

END + SCORING. The game ends when no swaps are available (which happens for
both players at once). Your score is the size of your largest orthogonally
connected group of your colour. If tied, second-largest groups are added, and
so on down the (multiset of) group sizes. On even-sized boards, if the tie
persists all the way down, whoever made the LAST move wins. On odd boards a
full tie is impossible (the piece counts differ).

TERMINATION. Every legal swap strictly increases the total "friendliness"
potential (monochromatic orthogonal adjacencies plus the half-edge bonuses),
which is bounded, so the game is finite (at most ~2*n^2 moves). A generous ply
cap is kept as a pure safety backstop (an honest draw, in practice
unreachable).

Move notation: "c1,r1>c2,r2" -- the mover's own piece first, then the adjacent
enemy piece it swaps with.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1          # Black moves first (per the designer's ZRF turn order)
DEFAULT_SIZE = 9

ORTH = ((0, 1), (0, -1), (1, 0), (-1, 0))
DIRS8 = ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1))


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _checkered(n: int) -> dict:
    """Full checkered board. White occupies the (c+r)-even squares -- on odd
    boards that puts White on the centre (and corners), per the rules."""
    return {(c, r): (WHITE if (c + r) % 2 == 0 else BLACK)
            for c in range(n) for r in range(n)}


def _edges(n: int, c: int, r: int) -> int:
    """Number of board edges adjacent to square (c, r): 2 at a corner, 1 on a
    rim square, 0 in the interior."""
    return (c == 0) + (c == n - 1) + (r == 0) + (r == n - 1)


def _delta2(board: dict, n: int, a, b) -> int:
    """Twice the change in value of the piece at `a` if it swaps with the
    (opposite-coloured) piece at `b`. Doubled so everything stays integer.

    Derivation (board is always full): moving the colour-`col` piece from a to
    b changes its value from  cn(a) + e(a)/2  to  cn(b) - [a orth-adj b] + e(b)/2,
    where cn(x) counts colour-`col` orthogonal neighbours of x on the CURRENT
    board (the piece at a is `col`, so it is included in cn(b) when orth-adjacent
    but no longer adjacent to itself after the swap). Because the board is full,
    the same expression (with colours exchanged) equals the change for the other
    piece, so the swap is legal for both players or neither.
    """
    col = board[a]

    def cn(x):
        cnt = 0
        for dc, dr in ORTH:
            nb = (x[0] + dc, x[1] + dr)
            if board.get(nb) == col:
                cnt += 1
        return cnt

    orth_adj = 1 if (abs(a[0] - b[0]) + abs(a[1] - b[1])) == 1 else 0
    return (2 * (cn(b) - orth_adj - cn(a))
            + _edges(n, b[0], b[1]) - _edges(n, a[0], a[1]))


def _group_sizes(board: dict, colour: int) -> list:
    """Sizes of the orthogonally connected groups of `colour`, sorted desc."""
    cells = {pos for pos, pl in board.items() if pl == colour}
    sizes = []
    seen = set()
    for start in cells:
        if start in seen:
            continue
        seen.add(start)
        stack = [start]
        size = 0
        while stack:
            c, r = stack.pop()
            size += 1
            for dc, dr in ORTH:
                nb = (c + dc, r + dr)
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        sizes.append(size)
    sizes.sort(reverse=True)
    return sizes


def _compare_scores(black_sizes: list, white_sizes: list) -> int:
    """Rules tiebreak: compare largest groups, then second-largest, etc.
    Returns >0 if Black leads, <0 if White leads, 0 on a full tie."""
    m = max(len(black_sizes), len(white_sizes))
    for i in range(m):
        b = black_sizes[i] if i < len(black_sizes) else 0
        w = white_sizes[i] if i < len(white_sizes) else 0
        if b != w:
            return 1 if b > w else -1
    return 0


@dataclass
class EmulsionState:
    n: int = DEFAULT_SIZE
    board: dict = field(default_factory=dict)   # (c, r) -> BLACK/WHITE
    to_move: int = BLACK
    ply: int = 0
    drawn: bool = False
    last: Optional[list] = None                  # the two swapped cell strings


class Emulsion(Game):
    name = "Emulsion"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> EmulsionState:
        n = int((options or {}).get("size", DEFAULT_SIZE))
        return EmulsionState(n=n, board=_checkered(n))

    def current_player(self, s: EmulsionState) -> int:
        return s.to_move

    # ---- moves -------------------------------------------------------------
    def _raw_moves(self, board: dict, n: int, p: int) -> list:
        out = []
        for (c, r), pl in board.items():
            if pl != p:
                continue
            for dc, dr in DIRS8:
                b = (c + dc, r + dr)
                if board.get(b) == 1 - p and _delta2(board, n, (c, r), b) > 0:
                    out.append(f"{c},{r}>{b[0]},{b[1]}")
        return out

    def legal_moves(self, s: EmulsionState) -> list:
        if s.drawn:
            return []
        return self._raw_moves(s.board, s.n, s.to_move)

    def is_terminal(self, s: EmulsionState) -> bool:
        return s.drawn or not self._raw_moves(s.board, s.n, s.to_move)

    def apply_move(self, s: EmulsionState, move: str, rng=None) -> EmulsionState:
        a_s, b_s = move.split(">")
        a, b = _cell(a_s), _cell(b_s)
        board = dict(s.board)
        board[a], board[b] = board[b], board[a]
        ply = s.ply + 1
        drawn = ply >= 4 * s.n * s.n + 100       # safety backstop; unreachable
        return EmulsionState(n=s.n, board=board, to_move=1 - s.to_move,
                             ply=ply, drawn=drawn, last=[a_s, b_s])

    # ---- result ------------------------------------------------------------
    def returns(self, s: EmulsionState) -> list:
        if s.drawn:
            return [0.0, 0.0]                    # ply-cap backstop only
        cmp = _compare_scores(_group_sizes(s.board, BLACK),
                              _group_sizes(s.board, WHITE))
        if cmp == 0:
            # Full tie. Rules: on even-sized boards the player who made the
            # LAST move wins. (On odd boards a full tie is impossible -- the
            # colours have different piece counts.) If no move was ever made
            # there is no "last mover": honest draw (unreachable in practice --
            # the initial position always has moves).
            if s.n % 2 == 0 and s.ply > 0:
                last_mover = 1 - s.to_move
                return [1.0, -1.0] if last_mover == BLACK else [-1.0, 1.0]
            return [0.0, 0.0]
        return [1.0, -1.0] if cmp > 0 else [-1.0, 1.0]

    # ---- MCTS rollout-cutoff heuristic --------------------------------------
    def heuristic(self, s: EmulsionState) -> list:
        import math
        bs = _group_sizes(s.board, BLACK)
        ws = _group_sizes(s.board, WHITE)
        score = ((bs[0] if bs else 0) + 0.1 * (bs[1] if len(bs) > 1 else 0)
                 - (ws[0] if ws else 0) - 0.1 * (ws[1] if len(ws) > 1 else 0))
        val = math.tanh(4.0 * score / (s.n * s.n))
        return [val, -val]

    # ---- serialize ----------------------------------------------------------
    def serialize(self, s: EmulsionState) -> dict:
        return {
            "n": s.n,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "drawn": s.drawn,
            "last": s.last,
        }

    def deserialize(self, d: dict) -> EmulsionState:
        return EmulsionState(
            n=d["n"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], ply=d.get("ply", 0),
            drawn=d.get("drawn", False), last=d.get("last"),
        )

    # ---- notation -----------------------------------------------------------
    def _alg(self, s: EmulsionState, cell_str: str) -> str:
        c, r = _cell(cell_str)
        return f"{chr(ord('a') + c)}{r + 1}"

    def describe_move(self, s: EmulsionState, move: str) -> str:
        a, b = move.split(">")
        return f"{self._alg(s, a)}↔{self._alg(s, b)}"

    # ---- render -------------------------------------------------------------
    def render(self, s: EmulsionState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        highlights = [{"cell": cell, "kind": "last-move"} for cell in (s.last or [])]
        bs = _group_sizes(s.board, BLACK)
        ws = _group_sizes(s.board, WHITE)
        groups = f"largest group B {bs[0] if bs else 0} / W {ws[0] if ws else 0}"
        if s.drawn:
            caption = f"Draw (ply cap) · {groups}"
        elif self.is_terminal(s):
            ret = self.returns(s)
            if ret[0] == ret[1]:
                caption = f"Draw · {groups}"
            else:
                caption = f"{names[BLACK] if ret[0] > 0 else names[WHITE]} wins · {groups}"
        else:
            caption = f"{names[s.to_move]} to move · {groups}"
        return {
            "board": {"type": "square", "width": s.n, "height": s.n},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
