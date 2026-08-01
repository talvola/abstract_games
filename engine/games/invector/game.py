"""Invector — Mark Steere, April 2026.

A Kōnane board: a rectangular grid of pits, one stone per pit, initially filled
with a checkerboard pattern of black and white stones.  The rule sheet allows
any size "with one even dimension and one odd dimension"; this package offers
the ``W x (W-1)`` family (``W`` even), which is the family AbstractPlay's
reference implementation uses and which satisfies the parity requirement
structurally.

Black moves first.  Passing is not allowed, but a player with no legal move has
his turn SKIPPED.  Invector uses the **pie rule**: on his first turn White may
instead switch colours and become Black, claiming the first move as his own.

MOVES.  One stone per turn, to an orthogonally adjacent pit, in one of two ways:

* **capture by replacement** — the destination holds an enemy stone, which is
  removed and replaced by yours.  Direction is unrestricted (Figure 2 of the
  rule sheet marks captures that move *away* from the centre as legal), and
  diagonal neighbours are never capturable.
* **non-capturing move** — the destination is EMPTY and STRICTLY CLOSER to a
  centre pit, Manhattan distance.  There are exactly two centre pits: the two
  pits flanking the board's geometric centre along the EVEN dimension.  A stone
  standing on a centre pit therefore has no non-capturing move at all.

OBJECT.  Capture every enemy stone.

TERMINATION (no ply cap, no repetition rule — the game cannot loop).
Let ``N`` be the number of stones on the board and ``D`` the sum, over all
stones, of the distance from that stone to the nearest centre pit.

* A **capture** removes the victim (which stood on the destination) and moves
  the mover from ``f`` to ``t``: ``N`` drops by one and
  ``dD = d(t) - d(f) - d(t) = -d(f) <= 0`` — D can never increase.
* A **non-capturing move** leaves ``N`` alone and sets ``dD = d(t) - d(f) = -1``.

So the pair ``(N, D)`` strictly decreases lexicographically on every ply, and
both components are bounded below.  Counting: at most ``W*H - 1`` captures (the
game ends when one side reaches zero stones, so at least one stone survives),
at most ``D0`` non-capturing plies where ``D0`` is the initial (full-board) sum
of distances, plus the single optional pie ply — see ``max_plies()``, which
derives the bound from the board dimensions alone.

MUTUAL DEADLOCK IS IMPOSSIBLE (proved, not defended).  Suppose both players hold
at least one stone and NO capture is available anywhere.  Let ``m`` be the
smallest distance-to-centre over all stones on the board.
* If ``m > 0``: take a stone at distance ``m``.  Every non-centre pit has an
  orthogonal neighbour one step closer to a centre pit; that neighbour cannot
  hold a stone (its distance would be ``m-1 < m``), so it is empty and that
  stone has a legal non-capturing move.
* If ``m = 0``: some stone stands on a centre pit.  Let ``mw`` be the smallest
  distance over the OTHER player's stones.  If ``mw > 0``, that player's closest
  stone has a strictly-closer neighbour, which is either empty (a legal move) or
  holds a stone of distance ``< mw`` — necessarily an ENEMY stone, i.e. a legal
  capture.  Either way he is not stuck.  If ``mw = 0`` then both players stand
  on centre pits; the two centre pits are orthogonally adjacent, so each can
  capture the other.
In every case at least one player has a move, so the game can never sit in an
endless skip loop.  ``selftest.py`` verifies this exhaustively on every
constructed board of two small grids.  A single player CAN be stuck (the skip
rule is real and does fire), which is why ``apply_move`` implements it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

# Board widths offered in the manifest.  The board is WIDTH columns x
# (WIDTH - 1) rows, so the width is the even dimension and the height the odd
# one, exactly as the rule sheet requires.  8 (= 8x7) is AbstractPlay's default;
# 4 (= 4x3) is small enough to solve exhaustively (see selftest.py).
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


# --------------------------------------------------------------------------
#  The centre of the board, and distance to it.
#
#  "[There are two center pits.]"  With one even and one odd dimension the
#  board's geometric centre falls on the midpoint of an edge of the grid, so
#  exactly two pits are nearest to it: they share the middle coordinate of the
#  ODD dimension and flank the centre along the EVEN dimension.  The definition
#  below is written symmetrically in the two axes and makes no assumption about
#  which of them is the even one.
# --------------------------------------------------------------------------

@lru_cache(maxsize=None)
def centre_pits(w: int, h: int) -> tuple:
    """The centre pits of a ``w`` x ``h`` board, as a sorted tuple of cells.

    A pit is a centre pit iff it minimises the distance to the board's
    geometric centre ``((w-1)/2, (h-1)/2)``.  An odd dimension has one middle
    coordinate, an even dimension has two, so a board with one even and one odd
    dimension has exactly TWO centre pits (and they are orthogonally adjacent).
    """
    cols = [w // 2] if w % 2 else [w // 2 - 1, w // 2]
    rows = [h // 2] if h % 2 else [h // 2 - 1, h // 2]
    return tuple(sorted((c, r) for c in cols for r in rows))


@lru_cache(maxsize=None)
def dist_table(w: int, h: int) -> dict:
    """{cell: Manhattan distance to the NEAREST centre pit} for a w x h board."""
    cps = centre_pits(w, h)
    return {(c, r): min(abs(c - cc) + abs(r - rr) for cc, rr in cps)
            for c in range(w) for r in range(h)}


def dist_to_centre(w: int, h: int, cell: tuple) -> int:
    """Manhattan distance from ``cell`` to the nearest centre pit."""
    return dist_table(w, h)[cell]


def initial_distance_sum(w: int, h: int) -> int:
    """``D0`` — the sum of ``dist_to_centre`` over a completely full board."""
    return sum(dist_table(w, h).values())


def max_plies(w: int, h: int) -> int:
    """Provable upper bound on the number of plies of a game on a w x h board.

    ``w*h - 1`` captures (the game ends when one side has no stones left, so at
    least one stone is never captured) + ``D0`` non-capturing plies (each
    strictly reduces the total distance-to-centre, which no move can ever
    increase) + the one optional pie ply.  Derived from the board dimensions
    alone — never a pinned constant.
    """
    return 1 + (w * h - 1) + initial_distance_sum(w, h)


# --------------------------------------------------------------------------
#  Pure board helpers.  ``board`` is a sparse dict {(c, r): seat}; a cell absent
#  from the dict is empty.  Used by the game, the selftest and the solver alike.
# --------------------------------------------------------------------------

def captures_from(board: dict, w: int, h: int, cell: tuple) -> list:
    """Every enemy stone the stone on ``cell`` can capture by replacement: the
    orthogonally adjacent pits holding an enemy stone, in ANY direction."""
    seat = board.get(cell)
    if seat is None:
        return []
    c0, r0 = cell
    out = []
    for dc, dr in ORTHO:
        c, r = c0 + dc, r0 + dr
        if 0 <= c < w and 0 <= r < h:
            occ = board.get((c, r))
            if occ is not None and occ != seat:
                out.append((c, r))
    return out


def advances_from(board: dict, w: int, h: int, cell: tuple) -> list:
    """Every non-capturing destination for the stone on ``cell``: orthogonally
    adjacent, UNOCCUPIED, and strictly closer to a centre pit."""
    if board.get(cell) is None:
        return []
    tbl = dist_table(w, h)
    d0 = tbl[cell]
    c0, r0 = cell
    out = []
    for dc, dr in ORTHO:
        c, r = c0 + dc, r0 + dr
        if 0 <= c < w and 0 <= r < h:
            if (c, r) not in board and tbl[(c, r)] < d0:
                out.append((c, r))
    return out


def all_moves(board: dict, w: int, h: int, seat: int) -> list:
    """Every (from, to) move available to ``seat``, in deterministic order."""
    out = []
    for cell in sorted(c for c, p in board.items() if p == seat):
        for tgt in captures_from(board, w, h, cell):
            out.append((cell, tgt))
        for tgt in advances_from(board, w, h, cell):
            out.append((cell, tgt))
    return out


def has_move(board: dict, w: int, h: int, seat: int) -> bool:
    """Does ``seat`` have at least one stone move?  (The pie swap is not a stone
    move and is handled by ``legal_moves``.)"""
    tbl = dist_table(w, h)
    for cell, p in board.items():
        if p != seat:
            continue
        c0, r0 = cell
        d0 = tbl[cell]
        for dc, dr in ORTHO:
            nb = (c0 + dc, r0 + dr)
            if not (0 <= nb[0] < w and 0 <= nb[1] < h):
                continue
            occ = board.get(nb)
            if occ is None:
                if tbl[nb] < d0:
                    return True
            elif occ != seat:
                return True
    return False


def stone_count(board: dict, seat: int) -> int:
    return sum(1 for p in board.values() if p == seat)


# --------------------------------------------------------------------------


@dataclass
class InvectorState:
    w: int = 8
    h: int = 7
    board: dict = field(default_factory=dict)   # (c, r) -> seat
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0                 # completed plies (swap is legal iff ply == 1)
    last: tuple = ()             # (from, to) of the last stone move, () otherwise
    swapped: bool = False        # was the pie rule exercised?
    skipped: bool = False        # did the LAST ply skip the other player's turn?


class Invector(Game):
    name = "Invector"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ core

    def initial_state(self, options=None, rng=None) -> InvectorState:
        o = options or {}
        size = int(o.get("size", 8))
        if size not in SIZES:
            raise ValueError(f"unsupported board size {size!r}")
        w, h = board_dims(size)
        # Checkerboard: Black (seat 0) on the even-parity cells, so the top-left
        # pit holds a black stone as Figure 1 of the rule sheet draws it.  (The
        # height is odd, so the bottom-left pit is black too.)
        board = {(c, r): (0 if (c + r) % 2 == 0 else 1)
                 for c in range(w) for r in range(h)}
        return InvectorState(w=w, h=h, board=board)

    def current_player(self, s: InvectorState) -> int:
        return s.to_move

    def legal_moves(self, s: InvectorState) -> list:
        if s.winner is not None:
            return []
        moves = [f"{f[0]},{f[1]}>{t[0]},{t[1]}"
                 for f, t in all_moves(s.board, s.w, s.h, s.to_move)]
        if s.ply == 1:
            moves.append("swap")
        return moves

    def apply_move(self, s: InvectorState, move: str, rng=None) -> InvectorState:
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
            new = InvectorState(w=s.w, h=s.h, board=board, to_move=1 - seat,
                                ply=s.ply + 1, last=(), swapped=True)
        else:
            frm, to = (_cell(x) for x in move.split(">"))
            if s.board.get(frm) != seat:
                raise ValueError(f"{move}: no stone of yours on {cell_name(frm)}")
            if (to not in captures_from(s.board, s.w, s.h, frm)
                    and to not in advances_from(s.board, s.w, s.h, frm)):
                raise ValueError(f"{move}: not a legal Invector move")
            board = dict(s.board)
            del board[frm]
            board[to] = seat            # capture by replacement / quiet advance
            new = InvectorState(w=s.w, h=s.h, board=board, to_move=1 - seat,
                                ply=s.ply + 1, last=(frm, to), swapped=s.swapped)
            # OBJECT OF THE GAME: remove every enemy stone.
            if stone_count(board, 1 - seat) == 0:
                new.winner = seat

        # "Passing is not allowed, but if you don't have a legal move available,
        # your turn is skipped."  A skip is not a ply of its own: the turn simply
        # comes back to the player who just moved.  Both players being stuck at
        # once is impossible (see the module docstring), so one check suffices;
        # were it to happen anyway the position would be terminal and score as an
        # honest draw rather than inventing a winner.
        if (new.winner is None and new.ply != 1        # ply 1 always has the pie
                and not has_move(new.board, new.w, new.h, new.to_move)):
            new.to_move = seat
            new.skipped = True
        return new

    def is_terminal(self, s: InvectorState) -> bool:
        return s.winner is not None or not self.legal_moves(s)

    def returns(self, s: InvectorState) -> list:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        # Provably unreachable (see the module docstring and selftest.py): two
        # stuck players at once cannot happen.  Scored as an honest draw rather
        # than a fabricated winner.
        return [0.0, 0.0]

    # NO ``heuristic``.  The obvious eval for an annihilation game — the
    # normalised material balance ``(mine - yours) / (all stones)``, which even
    # agrees with the true payoff at a terminal position — was implemented and
    # measured THROUGH ``MCTSBot`` (the consumer that would use it) against the
    # generic constant-zero fallback, at the server's default settings on the
    # 8x7 board.  It is statistically indistinguishable from no eval at all, so
    # it is not shipped: see rules.md for the numbers.

    # ----------------------------------------------------------- (de)serialize

    def serialize(self, s: InvectorState) -> dict:
        return {
            "w": s.w,
            "h": s.h,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "last": [f"{c},{r}" for (c, r) in s.last],
            "swapped": s.swapped,
            "skipped": s.skipped,
        }

    def deserialize(self, d: dict) -> InvectorState:
        return InvectorState(
            w=int(d["w"]),
            h=int(d["h"]),
            board={_cell(k): int(v) for k, v in d["board"].items()},
            to_move=int(d["to_move"]),
            winner=None if d["winner"] is None else int(d["winner"]),
            ply=int(d["ply"]),
            last=tuple(_cell(c) for c in d["last"]),
            swapped=bool(d["swapped"]),
            skipped=bool(d["skipped"]),
        )

    # ------------------------------------------------------------------- UI

    def describe_move(self, s: InvectorState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        try:
            frm, to = (_cell(x) for x in move.split(">"))
        except Exception:
            return move
        sep = "x" if s.board.get(to) is not None else "-"
        return f"{cell_name(frm)}{sep}{cell_name(to)}"

    @staticmethod
    def seat_colour(s: InvectorState, seat: int) -> str:
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

    def render(self, s: InvectorState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p}
                  for (c, r), p in s.board.items()]
        # The two centre pits are marked: every non-capturing move must end up
        # closer to one of them, so they are the geometry the rule is about.
        tints = {f"{c},{r}": "#4a3c26" for (c, r) in centre_pits(s.w, s.h)}
        highlights = []
        if s.winner is not None:
            name = self.seat_colour(s, s.winner)
            loser = self.seat_colour(s, 1 - s.winner)
            caption = f"{name} wins — every {loser} stone has been captured"
        elif not self.legal_moves(s):
            caption = "Neither player has a legal move — draw"
        else:
            for cell in s.last:
                highlights.append({"cell": f"{cell[0]},{cell[1]}",
                                   "kind": "last-move"})
            mover = self.seat_colour(s, s.to_move)
            caption = f"{mover} to move — capture, or step closer to the centre"
            if s.skipped:
                other = self.seat_colour(s, 1 - s.to_move)
                caption = (f"{other} has no legal move — turn skipped. " + caption)
            if s.ply == 1:
                caption += " (or take the pie swap)"
        return {
            "board": {"type": "square", "width": s.w, "height": s.h,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "actionNames": {"swap": "Swap colours (pie rule)"},
        }
