"""Flipway — a drawless connection game by Luis Bolaños Mures (2020).

Played on the points of an initially empty square board. Black (player 0)
tries to connect the TOP and BOTTOM edges, White (player 1) the LEFT and
RIGHT edges, each with a chain of ORTHOGONALLY adjacent stones of their
colour.

To start, Black places a single black stone on any empty point. From then on,
starting with White, the players alternate; on your turn you must perform
exactly one of these actions:

- DROP: select a 2x2 area including one or more empty points, such that no
  other 2x2 area includes all those empty points as well as at least another
  empty point. Place a stone of your colour on each empty point in the
  selected area. (I.e. the set of points you fill must be the empty set of a
  2x2 window, MAXIMAL in the sense that no 2x2 window contains all of them
  plus a further empty point. Equivalently — the designer's alternative
  phrasing on BGG — keep extending: if all stones placed so far fit in
  another 2x2 area with an empty point, fill that too; at most four stones
  are placed per turn.)

- FLIP: replace the two enemy stones in a crosscut with stones of your
  colour. A crosscut is a 2x2 area containing two diagonally adjacent black
  stones and two diagonally adjacent white stones.

Draws are not possible: on a full board with no connection a crosscut always
exists, and flip cycles are impossible (a flip never decreases the number of
orthogonally adjacent same-colour pairs). A generous ply cap is kept as a
purely defensive backstop; hitting it scores an honest draw.

Sources: Zillions of Games submission id=3051 (ReadMe.txt by the designer,
authoritative), BGG game page 314559 + designer's announcement thread 2466735
(same rules; adds the iterative drop phrasing and the drawless discussion).
The Zillions bundle's "Checkered"/"Bicheckered" variants (start from a full
checkerboard / 2x2-block checkerboard, so the whole game is flips) are
offered via the `setup` option; in those, per the designer's BGG description,
Black's opening move is replacing any single white stone with a black stone
(the full-board analogue of the single-stone opening).

Move encoding: a `>`-separated path of the cells changed, canonically sorted
("c,r" cells, sorted by (c, r)). A drop lists the 1-4 empty points filled; a
flip lists the two enemy stones flipped (they are occupied, so the strings
can never collide with drops).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black: top<->bottom, White: left<->right. Black first.
NAMES = {BLACK: "Black", WHITE: "White"}
_ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def _cell(sq: str):
    c, r = sq.split(",")
    return int(c), int(r)


def _sq(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _encode(cells) -> str:
    return ">".join(_sq(c) for c in sorted(cells))


def _cap(n: int) -> int:
    # Defensive only: never reached in real play (see module docstring).
    return 10 * n * n + 100


@dataclass
class FlipwayState:
    size: int = 12
    board: dict = field(default_factory=dict)  # (c, r) -> BLACK/WHITE
    to_move: int = BLACK
    winner: Optional[int] = None
    ply: int = 0
    setup: str = "plain"
    last: list = field(default_factory=list)   # cells changed by the last move


def _legal_drop_sets(board: dict, n: int) -> list:
    """All legal DROP fill-sets: for each 2x2 window W its empty set E (if
    non-empty), kept iff NO 2x2 window containing all of E has an extra empty
    point. Deduplicated by E (two windows can share the same empty set)."""
    out = []
    seen = set()
    for x in range(n - 1):
        for y in range(n - 1):
            E = frozenset(
                (x + dc, y + dr)
                for dc in (0, 1) for dr in (0, 1)
                if (x + dc, y + dr) not in board
            )
            if not E or E in seen:
                continue
            seen.add(E)
            xs = [c for (c, _) in E]
            ys = [r for (_, r) in E]
            legal = True
            # every 2x2 window whose cells contain E:
            for wx in range(max(0, max(xs) - 1), min(n - 2, min(xs)) + 1):
                for wy in range(max(0, max(ys) - 1), min(n - 2, min(ys)) + 1):
                    cnt = sum(
                        1
                        for dc in (0, 1) for dr in (0, 1)
                        if (wx + dc, wy + dr) not in board
                    )
                    if cnt > len(E):  # strict superset of empties -> not maximal
                        legal = False
                        break
                if not legal:
                    break
            if legal:
                out.append(E)
    return out


def _crosscuts(board: dict, n: int) -> list:
    """All crosscut windows, as ((x,y) diagonal-pair-owner-a, pairs).
    Returns list of (pair_of_cells_owned_by_a, pair_of_cells_owned_by_b, a)
    reduced to what we need: the two diagonal pairs with their owners."""
    out = []
    for x in range(n - 1):
        for y in range(n - 1):
            a = board.get((x, y))
            if a is None:
                continue
            b = board.get((x + 1, y + 1))
            c = board.get((x + 1, y))
            d = board.get((x, y + 1))
            if b == a and c is not None and d == c and c != a:
                out.append((((x, y), (x + 1, y + 1)), ((x + 1, y), (x, y + 1)), a))
    return out


def _flip_pairs(board: dict, n: int, mover: int) -> list:
    """The enemy diagonal pair of every crosscut (the cells `mover` may flip)."""
    pairs = []
    for pair_a, pair_c, owner_a in _crosscuts(board, n):
        pairs.append(pair_c if owner_a == mover else pair_a)
    return pairs


def _connects(board: dict, player: int, n: int) -> bool:
    """Does `player` join their two opposite edges via an ORTHOGONAL chain?"""
    if player == BLACK:  # top (r=0) <-> bottom (r=n-1)
        starts = [(c, 0) for c in range(n) if board.get((c, 0)) == BLACK]
        at_goal = lambda cell: cell[1] == n - 1  # noqa: E731
    else:                # left (c=0) <-> right (c=n-1)
        starts = [(0, r) for r in range(n) if board.get((0, r)) == WHITE]
        at_goal = lambda cell: cell[0] == n - 1  # noqa: E731
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        cc, cr = cur
        for dc, dr in _ORTH:
            nb = (cc + dc, cr + dr)
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return False


def _setup_board(size: int, setup: str) -> dict:
    if setup == "checkered":
        # Full checkerboard (Zillions "Checkered Flipway": a1 = White).
        return {
            (c, r): (WHITE if (c + r) % 2 == 0 else BLACK)
            for c in range(size) for r in range(size)
        }
    if setup == "bicheckered":
        # Full 2x2-block checkerboard (Zillions "Bicheckered Flipway":
        # the a1 block = White).
        return {
            (c, r): (WHITE if (c // 2 + r // 2) % 2 == 0 else BLACK)
            for c in range(size) for r in range(size)
        }
    return {}


class Flipway(Game):
    name = "Flipway"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> FlipwayState:
        opts = options or {}
        size = int(opts.get("size", 12))
        setup = str(opts.get("setup", "plain"))
        return FlipwayState(size=size, board=_setup_board(size, setup),
                            setup=setup)

    def current_player(self, s: FlipwayState) -> int:
        return s.to_move

    def legal_moves(self, s: FlipwayState) -> list[str]:
        if self.is_terminal(s):
            return []
        n = s.size
        if s.ply == 0:
            if not s.board:
                # Opening: Black places exactly ONE stone on any empty point.
                return [f"{c},{r}" for r in range(n) for c in range(n)]
            # Checkered/bicheckered opening (designer's BGG description):
            # "Black starts by replacing any white stone with a black stone."
            enemy = 1 - s.to_move
            return [_sq(c) for c in sorted(c for c, p in s.board.items()
                                           if p == enemy)]
        moves = [_encode(E) for E in _legal_drop_sets(s.board, n)]
        moves += [_encode(p) for p in _flip_pairs(s.board, n, s.to_move)]
        return moves

    def apply_move(self, s: FlipwayState, move: str, rng=None) -> FlipwayState:
        cells = [_cell(p) for p in move.split(">")]
        board = dict(s.board)
        for c in cells:  # a drop fills empties; a flip recolours enemy stones
            board[c] = s.to_move
        winner = s.to_move if _connects(board, s.to_move, s.size) else None
        return FlipwayState(size=s.size, board=board, to_move=1 - s.to_move,
                            winner=winner, ply=s.ply + 1, setup=s.setup,
                            last=[_sq(c) for c in cells])

    def is_terminal(self, s: FlipwayState) -> bool:
        if s.winner is not None:
            return True
        if s.ply >= _cap(s.size):  # defensive backstop -> honest draw
            return True
        n = s.size
        if len(s.board) == n * n and not _crosscuts(s.board, n):
            # Full board, no winner, no crosscut: no legal move for anyone.
            # Unreachable per the designer's drawless argument; honest draw.
            return True
        return False

    def returns(self, s: FlipwayState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # honest draw (backstop only; see rules.md)

    def serialize(self, s: FlipwayState) -> dict:
        return {
            "size": s.size,
            "board": {_sq(c): p for c, p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "setup": s.setup,
            "last": list(s.last),
        }

    def deserialize(self, d: dict) -> FlipwayState:
        return FlipwayState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            ply=d["ply"],
            setup=d.get("setup", "plain"),
            last=list(d.get("last", [])),
        )

    def _alg(self, cell) -> str:
        letters = "abcdefghijklmnopqrstuvwxyz"
        c, r = cell
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def describe_move(self, s: FlipwayState, move: str) -> str:
        cells = [_cell(p) for p in move.split(">")]
        if s.ply == 0:
            return f"opening {self._alg(cells[0])}"
        if all(c not in s.board for c in cells):
            return "drop " + "+".join(self._alg(c) for c in cells)
        return "flip " + "+".join(self._alg(c) for c in cells)

    def render(self, s: FlipwayState, perspective=None) -> dict:
        pieces = [
            {"cell": _sq(c), "owner": p, "label": ""}
            for c, p in s.board.items()
        ]
        highlights = [{"cell": sq, "kind": "last-move"} for sq in s.last]
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            edge = "top–bottom" if s.to_move == BLACK else "left–right"
            caption = f"{NAMES[s.to_move]} to move ({edge})"
        return {
            "board": {
                "type": "square", "width": s.size, "height": s.size,
                # Black goal = N/S edges; White goal = W/E edges.
                "edges": {"top": BLACK, "bottom": BLACK,
                          "left": WHITE, "right": WHITE},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
