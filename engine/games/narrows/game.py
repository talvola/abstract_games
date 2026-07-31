"""Narrows — Mark Steere, May 2026.

A Kōnane board: a rectangular grid of pits, one stone per pit, initially filled
with a checkerboard pattern of black and white stones.  The grid may be any size
**with at least one even dimension**; this package offers the ``W x (W-1)``
family (``W`` even) that AbstractPlay's reference implementation uses.

Black moves first; passing is not allowed.  Narrows uses the **pie rule**: on his
first turn White may instead switch colours and become Black, claiming the first
move as his own.

MOVE (rook capture by replacement).  Slide one of your stones orthogonally onto
the first enemy stone it sees — the enemy stone is either adjacent, or separated
from your stone by empty points only.  The enemy stone is removed and yours takes
its place.  Every move is therefore a capture, and every move removes exactly one
enemy stone.

OBJECT.  All of your stones must be linked to each other via orthogonally
connected paths of unoccupied points and/or friendly stones — i.e. in the
subgraph induced on ``(empty cells) ∪ (your stones)`` all of your stones lie in
ONE connected component.  You can win on your turn or on your opponent's turn; if
one move links both players, the mover wins.

TERMINATION (no ply cap, no repetition rule — the game cannot loop).
Each non-swap move removes exactly one enemy stone, so the total stone count
strictly decreases; the swap is available on exactly one ply (ply 1) and removes
nothing.  A player holding exactly one stone trivially has all his stones in one
component, so the game is over the moment either count reaches 1.  Starting from
``m = W*H/2`` stones each, the counts run
``(m,m) -> (m,m-1) -> (m-1,m-1) -> …``; the first count of 1 appears after
``2m-3 = W*H-3`` moves, so a game lasts at most ``W*H - 3`` capture plies plus
the single optional swap ply: ``MAX_PLIES = W*H - 2`` (see ``max_plies()``).
Nothing is ever added to the board, so no position can repeat.

NO-MOVE IS IMPOSSIBLE (proved, not defended).  You have no capture iff no row and
no column contains stones of both colours (a row/column containing both must
somewhere have two consecutive stones of opposite colour, and those two capture
each other).  But if every row and every column is monochromatic then each player
occupies a set of rows R and columns C disjoint from the other player's, so any
two of his stones ``(r1,c1)``, ``(r2,c2)`` are joined by going down column ``c1``
(which holds no enemy stone) and then along row ``r2`` (likewise) — every cell on
that path is empty or friendly.  Both players are therefore linked, and the game
already ended on the previous move.  ``selftest.py`` verifies this exhaustively
on constructed boards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# Board widths offered in the manifest.  The board is WIDTH columns x
# (WIDTH - 1) rows, so the width is the even dimension the rule sheet requires.
# 12 (= 12x11) is AbstractPlay's default; 4 (= 4x3) is small enough to solve
# exhaustively (see selftest.py).
SIZES = (4, 6, 8, 10, 12, 14, 16)

SEAT_NAMES = ("Black", "White")

ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))


def board_dims(size: int) -> tuple:
    """(width, height) for a size option.  Width is the even dimension."""
    return int(size), int(size) - 1


def _cell(s: str) -> tuple:
    c, r = s.split(",")
    return int(c), int(r)


def cell_name(cell: tuple) -> str:
    """Algebraic name: file letter from the column, 1-based rank from the row
    (row 0 is the bottom row, as the renderer draws it)."""
    c, r = cell
    return f"{chr(ord('a') + c)}{r + 1}"


def max_plies(w: int, h: int) -> int:
    """Provable upper bound on the number of plies in a game on a w x h board.

    ``w*h - 3`` capture plies (the count argument in the module docstring) plus
    the one optional swap ply.  Derived from the board dimensions alone — never
    a pinned constant.
    """
    return w * h - 2


# --------------------------------------------------------------------------
#  Pure board helpers.  ``board`` is a sparse dict {(c, r): seat}; a cell that
#  is absent from the dict is empty.  These are used by the game, the selftest
#  and the exhaustive solver alike.
# --------------------------------------------------------------------------

def captures_from(board: dict, w: int, h: int, cell: tuple) -> list:
    """Every enemy stone the stone on `cell` can capture (rook line of sight
    through empty points).  Returns a list of target cells."""
    seat = board.get(cell)
    if seat is None:
        return []
    out = []
    c0, r0 = cell
    for dc, dr in ORTHO:
        c, r = c0 + dc, r0 + dr
        while 0 <= c < w and 0 <= r < h:
            occ = board.get((c, r))
            if occ is not None:
                if occ != seat:
                    out.append((c, r))
                break
            c, r = c + dc, r + dr
    return out


def all_captures(board: dict, w: int, h: int, seat: int) -> list:
    """Every (from, to) capture available to `seat`, in deterministic order."""
    out = []
    for cell in sorted(c for c, p in board.items() if p == seat):
        for tgt in captures_from(board, w, h, cell):
            out.append((cell, tgt))
    return out


def linked_components(board: dict, w: int, h: int, seat: int) -> list:
    """Connected components of the subgraph induced on
    ``(empty cells) ∪ (seat's stones)`` that contain at least one of `seat`'s
    stones.  Each component is returned as a set of cells (stones AND the empty
    points that link them).  `seat` has met the object of the game iff exactly
    one such component exists."""
    seen: set = set()
    comps: list = []
    for start in sorted(c for c, p in board.items() if p == seat):
        if start in seen:
            continue
        comp = {start}
        seen.add(start)
        stack = [start]
        while stack:
            c0, r0 = stack.pop()
            for dc, dr in ORTHO:
                nb = (c0 + dc, r0 + dr)
                if not (0 <= nb[0] < w and 0 <= nb[1] < h) or nb in comp:
                    continue
                occ = board.get(nb)
                if occ is None or occ == seat:
                    comp.add(nb)
                    seen.add(nb)
                    stack.append(nb)
        comps.append(comp)
    return comps


def is_linked(board: dict, w: int, h: int, seat: int) -> bool:
    """Has `seat` met the object of the game?  A seat with NO stones has no
    groups at all and has *not* won (matching AbstractPlay); that case is in any
    event unreachable — see ``selftest.py``."""
    return len(linked_components(board, w, h, seat)) == 1


def narrows_cells(board: dict, w: int, h: int, seat: int) -> set:
    """Display aid, not a rule: the EMPTY points whose removal would split
    `seat`'s stones into more than one component — the "narrows" that do the
    linking.  On the rule sheet's Figure 3 this is exactly the set of points
    marked with blue dots.  Empty only when `seat` is not linked."""
    if not is_linked(board, w, h, seat):
        return set()
    comp = linked_components(board, w, h, seat)[0]
    out = set()
    for cell in comp:
        if board.get(cell) is not None:
            continue                       # a stone, not an empty point
        blocked = dict(board)
        blocked[cell] = 1 - seat           # pretend it is an enemy stone
        if not is_linked(blocked, w, h, seat):
            out.add(cell)
    return out


# --------------------------------------------------------------------------


@dataclass
class NarrowsState:
    w: int = 12
    h: int = 11
    board: dict = field(default_factory=dict)   # (c, r) -> seat
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0                 # completed plies (swap is legal iff ply == 1)
    last: tuple = ()             # (from, to) of the last capture, () otherwise
    swapped: bool = False        # was the pie rule exercised?


class Narrows(Game):
    name = "Narrows"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ core

    def initial_state(self, options=None, rng=None) -> NarrowsState:
        o = options or {}
        size = int(o.get("size", 12))
        if size not in SIZES:
            raise ValueError(f"unsupported board size {size!r}")
        w, h = board_dims(size)
        # Checkerboard: Black (seat 0) on the even-parity cells, so both the
        # top-left and the bottom-left corner hold a black stone, as Figure 1
        # of the rule sheet draws it.
        board = {(c, r): (0 if (c + r) % 2 == 0 else 1)
                 for c in range(w) for r in range(h)}
        return NarrowsState(w=w, h=h, board=board)

    def current_player(self, s: NarrowsState) -> int:
        return s.to_move

    def legal_moves(self, s: NarrowsState) -> list:
        if s.winner is not None:
            return []
        moves = [f"{f[0]},{f[1]}>{t[0]},{t[1]}"
                 for f, t in all_captures(s.board, s.w, s.h, s.to_move)]
        if s.ply == 1:
            moves.append("swap")
        return moves

    def apply_move(self, s: NarrowsState, move: str, rng=None) -> NarrowsState:
        if s.winner is not None:
            raise ValueError("the game is over")
        seat = s.to_move

        if move == "swap":
            if s.ply != 1:
                raise ValueError("the pie swap is only available on White's "
                                 "first turn")
            # The players exchange colours; the position is untouched.  White
            # becomes Black and keeps the move Black already made, so it is now
            # the other seat's turn, playing White.
            board = {c: 1 - p for c, p in s.board.items()}
            new = NarrowsState(w=s.w, h=s.h, board=board, to_move=1 - seat,
                               ply=s.ply + 1, last=(), swapped=True)
        else:
            frm, to = (_cell(x) for x in move.split(">"))
            if s.board.get(frm) != seat:
                raise ValueError(f"{move}: no stone of yours on {cell_name(frm)}")
            if to not in captures_from(s.board, s.w, s.h, frm):
                raise ValueError(f"{move}: not a legal rook capture")
            board = dict(s.board)
            del board[frm]
            board[to] = seat            # capture by replacement
            new = NarrowsState(w=s.w, h=s.h, board=board, to_move=1 - seat,
                               ply=s.ply + 1, last=(frm, to), swapped=s.swapped)

        # You can win on your turn or on your opponent's turn; if the move links
        # both players, the mover wins.
        mover_ok = is_linked(new.board, new.w, new.h, seat)
        other_ok = is_linked(new.board, new.w, new.h, 1 - seat)
        if mover_ok:
            new.winner = seat
        elif other_ok:
            new.winner = 1 - seat
        return new

    def is_terminal(self, s: NarrowsState) -> bool:
        return s.winner is not None or not self.legal_moves(s)

    def returns(self, s: NarrowsState) -> list:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        # Provably unreachable (see the module docstring and selftest.py): a
        # position with no capture available has both players already linked, so
        # the game ended on the previous move.  Scored as an honest draw rather
        # than a fabricated winner.
        return [0.0, 0.0]

    # ----------------------------------------------------------- (de)serialize

    def serialize(self, s: NarrowsState) -> dict:
        return {
            "w": s.w,
            "h": s.h,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "last": [f"{c},{r}" for (c, r) in s.last],
            "swapped": s.swapped,
        }

    def deserialize(self, d: dict) -> NarrowsState:
        return NarrowsState(
            w=int(d["w"]),
            h=int(d["h"]),
            board={_cell(k): int(v) for k, v in d["board"].items()},
            to_move=int(d["to_move"]),
            winner=None if d["winner"] is None else int(d["winner"]),
            ply=int(d["ply"]),
            last=tuple(_cell(c) for c in d["last"]),
            swapped=bool(d["swapped"]),
        )

    # ------------------------------------------------------------------- UI

    def describe_move(self, s: NarrowsState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        try:
            frm, to = (_cell(x) for x in move.split(">"))
            return f"{cell_name(frm)}x{cell_name(to)}"
        except Exception:
            return move

    @staticmethod
    def seat_colour(s: NarrowsState, seat: int) -> str:
        """The rule sheet's colour name for a seat.

        The pie swap EXCHANGES the colours ("White ... has the option of
        switching colors and becoming Black"), and it is implemented by flipping
        the ownership of every stone — so after a swap seat 1 holds the army that
        opened the game and is Black, and seat 0 is White.  Consulting
        ``s.swapped`` here is what keeps the caption's colour names in step with
        the board; naming seats unconditionally would invert every colour word
        for the whole rest of a game in which the pie was taken.
        """
        return SEAT_NAMES[seat ^ int(bool(s.swapped))]

    def render(self, s: NarrowsState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p}
                  for (c, r), p in s.board.items()]
        highlights = []
        if s.winner is not None:
            for (c, r) in sorted(narrows_cells(s.board, s.w, s.h, s.winner)):
                highlights.append({"cell": f"{c},{r}", "kind": "goal"})
            name = self.seat_colour(s, s.winner)
            caption = (f"{name} wins — every {name} "
                       f"stone is linked to every other")
        elif not self.legal_moves(s):
            caption = "No capture available — draw"
        else:
            for cell in s.last:
                highlights.append({"cell": f"{cell[0]},{cell[1]}",
                                   "kind": "last-move"})
            caption = (f"{self.seat_colour(s, s.to_move)} to move — "
                       f"capture by replacement")
            if s.ply == 1:
                caption += " (or take the pie swap)"
        return {
            "board": {"type": "square", "width": s.w, "height": s.h},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "actionNames": {"swap": "Swap colours (pie rule)"},
        }
