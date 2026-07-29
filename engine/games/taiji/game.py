"""Taiji -- Néstor Romeral Andrés, 2007 (nestorgames / Blue Panther).

Implemented from the designer's own rulebooks
(https://nestorgames.com/rulebooks/TAIJI_EN.pdf, "2007 - 2020 (c) Néstor
Romeral Andrés", and the DELUXE EDITION sheet TAIJIDELUXE_EN.pdf, 2007) and
differentialled move-for-move against the AbstractPlay `gameslib` reference
implementation (see `_diff_ap.py`).

The board starts EMPTY.  A turn is always the same thing: place one TAIJITU --
a domino with one LIGHT half and one DARK half -- on two empty orthogonally
adjacent squares, in either orientation.  You place BOTH colours every turn,
so every move helps your opponent too; that is the whole game.

Seat 0 is Light and moves first ("Light player starts"); seat 1 is Dark.  A
player scores only their OWN colour.

The game ends when no TAIJITU can be placed, i.e. when no two orthogonally
adjacent empty squares remain.  On an odd board (7x7 / 9x9 / 11x11 all have an
odd number of squares) the board can never fill exactly, so at least one empty
square always survives; several isolated empties may survive.  Leftover empty
squares score nothing.

Score = the sum of the sizes of your N largest groups of your colour, where N
is the "scoring type" chosen at setup (1, 2 or 3) and a group is a set of
same-coloured squares connected ORTHOGONALLY ("horizontally or vertically
adjacent (not diagonally)" -- rulebook).  Highest score wins; "In case of a
tie, the 'Dark' player wins" (rulebook).  See rules.md.

Cells are "c,r" (col 0..size-1 left->right, row 0..size-1 BOTTOM->top), printed
as algebraic "a1".."i9" (== AbstractPlay's naming).  A move is

    "c1,r1>c2,r2"   place the LIGHT half on the first cell and the DARK half
                    on the second; the two cells must be empty and orthogonally
                    adjacent.  Both orientations of every domino are offered,
                    so the mover chooses which square gets which colour.

TERMINATION (no ply cap needed, and none is used): every legal move fills
exactly two empty squares and nothing ever empties a square, so the number of
empty squares strictly decreases by 2 each ply.  A game is therefore at most
floor(size^2 / 2) plies long (24 / 40 / 60), whatever the players do.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from agp.game import Game

EMPTY = -1
LIGHT, DARK = 0, 1
NAMES = {LIGHT: "Light", DARK: "Dark"}

SIZES = (7, 9, 11)
GROUPS = (1, 2, 3)
TIES = ("dark", "draw")

# Orthogonal only -- both for what counts as "a free space of 2 connected
# squares" and for what counts as a group when scoring.
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _idx(size, c, r):
    return r * size + c


def _cr(size, i):
    return i % size, i // size


def cell_id(size, i):
    c, r = _cr(size, i)
    return f"{c},{r}"


def parse_cell(size, s):
    c, r = (int(x) for x in s.split(","))
    if not (0 <= c < size and 0 <= r < size):
        raise ValueError(f"cell off the board: {s}")
    return _idx(size, c, r)


def cell_name(size, i):
    """Board-printed algebraic name, 'a1' bottom-left (== AbstractPlay)."""
    c, r = _cr(size, i)
    return chr(ord("a") + c) + str(r + 1)


def _neighbours(size):
    """neighbours[i] = tuple of orthogonally adjacent cell indices."""
    out = []
    for i in range(size * size):
        c, r = _cr(size, i)
        out.append(tuple(_idx(size, c + dc, r + dr) for dc, dr in DIRS
                         if 0 <= c + dc < size and 0 <= r + dr < size))
    return tuple(out)


class _NbCache(dict):
    """neighbour tables, precomputed for the three published board sizes and
    built on demand for any other (test positions use small boards)."""

    def __missing__(self, size):
        self[size] = _neighbours(size)
        return self[size]


NEIGHBOURS = _NbCache({n: _neighbours(n) for n in SIZES})


@dataclass(frozen=True)
class TState:
    size: int = 9
    groups: int = 2                 # how many largest groups score (1/2/3)
    tie: str = "dark"               # "dark" = official tie-break, "draw"
    board: tuple = ()               # size*size ints: EMPTY / LIGHT / DARK
    to_move: int = LIGHT
    last: object = None             # (light_idx, dark_idx) of the last move


class Taiji(Game):

    @property
    def num_players(self):
        return 2

    # ---- setup ---------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        opts = options or {}
        size = int(opts.get("size", 9))
        if size not in SIZES:
            size = 9
        groups = int(opts.get("groups", 2))
        if groups not in GROUPS:
            groups = 2
        tie = str(opts.get("tie", "dark"))
        if tie not in TIES:
            tie = "dark"
        return TState(size=size, groups=groups, tie=tie,
                      board=(EMPTY,) * (size * size), to_move=LIGHT, last=None)

    def current_player(self, state):
        return state.to_move

    # ---- rules ---------------------------------------------------------
    def legal_moves(self, state):
        size, board = state.size, state.board
        nb = NEIGHBOURS[size]
        out = []
        for i, v in enumerate(board):
            if v != EMPTY:
                continue
            for j in nb[i]:
                if board[j] == EMPTY:
                    # ORDERED pair: light on i, dark on j.  Both orientations
                    # of every domino appear, since (j, i) is generated too.
                    out.append(f"{cell_id(size, i)}>{cell_id(size, j)}")
        return out

    def _parse(self, state, move):
        a, _, b = move.partition(">")
        if not b:
            raise ValueError(f"malformed move: {move}")
        i, j = parse_cell(state.size, a), parse_cell(state.size, b)
        if i == j:
            raise ValueError(f"a TAIJITU needs two different squares: {move}")
        if state.board[i] != EMPTY or state.board[j] != EMPTY:
            raise ValueError(f"square already occupied: {move}")
        if j not in NEIGHBOURS[state.size][i]:
            raise ValueError(f"squares are not orthogonally adjacent: {move}")
        return i, j

    def apply_move(self, state, move, rng=None):
        i, j = self._parse(state, move)
        board = list(state.board)
        board[i] = LIGHT
        board[j] = DARK
        return TState(size=state.size, groups=state.groups, tie=state.tie,
                      board=tuple(board), to_move=1 - state.to_move,
                      last=(i, j))

    def is_terminal(self, state):
        """True once no TAIJITU fits: no two orthogonally adjacent empties."""
        board, nb = state.board, NEIGHBOURS[state.size]
        for i, v in enumerate(board):
            if v != EMPTY:
                continue
            for j in nb[i]:
                if board[j] == EMPTY:
                    return False
        return True

    # ---- scoring -------------------------------------------------------
    @staticmethod
    def group_sizes(state, colour):
        """Sizes of every orthogonally-connected group of `colour`, descending."""
        board, nb = state.board, NEIGHBOURS[state.size]
        seen = [False] * len(board)
        sizes = []
        for start, v in enumerate(board):
            if v != colour or seen[start]:
                continue
            seen[start] = True
            todo = [start]
            n = 0
            while todo:
                cur = todo.pop()
                n += 1
                for j in nb[cur]:
                    if board[j] == colour and not seen[j]:
                        seen[j] = True
                        todo.append(j)
            sizes.append(n)
        sizes.sort(reverse=True)
        return sizes

    @classmethod
    def score(cls, state, colour):
        """Sum of the sizes of the `groups` largest groups of that colour."""
        return sum(cls.group_sizes(state, colour)[:state.groups])

    @classmethod
    def scores(cls, state):
        return (cls.score(state, LIGHT), cls.score(state, DARK))

    def returns(self, state):
        lt, dk = self.scores(state)
        if lt > dk:
            return [1.0, -1.0]
        if dk > lt:
            return [-1.0, 1.0]
        # Equal scores.  The designer's rulebook says "In case of a tie, the
        # 'Dark' player wins", which is the default; the "draw" option scores
        # an equal game as an honest draw instead (AbstractPlay's reading).
        if state.tie == "dark":
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, state):
        lt, dk = self.scores(state)
        v = math.tanh((lt - dk) / float(state.size))
        return [v, -v]

    # ---- persistence ---------------------------------------------------
    def serialize(self, state):
        sym = {EMPTY: ".", LIGHT: "L", DARK: "D"}
        return {
            "size": state.size,
            "groups": state.groups,
            "tie": state.tie,
            "board": "".join(sym[v] for v in state.board),
            "to_move": state.to_move,
            "last": (None if state.last is None
                     else [cell_id(state.size, state.last[0]),
                           cell_id(state.size, state.last[1])]),
        }

    def deserialize(self, data):
        val = {".": EMPTY, "L": LIGHT, "D": DARK}
        size = int(data["size"])
        last = data.get("last")
        return TState(
            size=size,
            groups=int(data["groups"]),
            tie=data.get("tie", "dark"),
            board=tuple(val[ch] for ch in data["board"]),
            to_move=int(data["to_move"]),
            last=(None if last is None
                  else (parse_cell(size, last[0]), parse_cell(size, last[1]))),
        )

    # ---- notation ------------------------------------------------------
    def describe_move(self, state, move):
        i, j = self._parse(state, move)
        size = state.size
        return f"{cell_name(size, i)}(L)-{cell_name(size, j)}(D)"

    # ---- presentation --------------------------------------------------
    def render(self, state, perspective=None):
        size = state.size
        pieces = [{"cell": cell_id(size, i), "owner": v}
                  for i, v in enumerate(state.board) if v != EMPTY]
        spec = {
            "board": {"type": "square", "width": size, "height": size},
            "pieces": pieces,
            "caption": self._caption(state),
        }
        if state.last is not None:
            spec["highlights"] = [{"cell": cell_id(size, i), "kind": "last-move"}
                                  for i in state.last]
        return spec

    def _caption(self, state):
        lt, dk = self.scores(state)
        n = state.groups
        head = (f"Light {lt} - Dark {dk} "
                f"(largest {n} group{'s' if n != 1 else ''})")
        if not self.is_terminal(state):
            # Choosing the orientation IS the move, and a move is "light>dark",
            # so the player has to be told which click picks which half.
            return (f"{NAMES[state.to_move]} to place - click the LIGHT square, "
                    f"then the DARK - {head}")
        if lt > dk:
            return f"Light wins - {head}"
        if dk > lt:
            return f"Dark wins - {head}"
        if state.tie == "dark":
            return f"Tie - Dark wins the tie-break - {head}"
        return f"Draw - {head}"
