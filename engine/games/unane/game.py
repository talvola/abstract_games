"""Ūnane — Mark Steere, April 2026.

A Kōnane board: a rectangular grid of pits, one stone per pit, initially filled
with a checkerboard pattern of black and white stones.  The grid may be any size
**with at least one even dimension**; this package offers the ``W x (W-1)``
family (``W`` even) that AbstractPlay's reference implementation uses.

Black moves first; passing is not allowed.  Ūnane uses the **pie rule**: on his
first turn White may instead switch colours and become Black, claiming the first
move as his own.

TURN.  Each turn you do exactly one of two things with exactly one stone of your
own colour (never both):

* **CAPTURE** — move one of your stones onto an ORTHOGONALLY ADJACENT enemy
  stone, in any direction, capturing it by replacement.  There is no
  non-capturing move, and no long-range move: the rule sheet says "adjacent"
  (its sibling Narrows, whose move really is a rook slide, says "separated from
  your stone by empty points only" instead).  Sheet Figure 2 confirms the
  diagonal reading is wrong — the one white stone it marks in RED is the one
  that is only DIAGONALLY adjacent to the black stone.
* **REMOVAL** — take one of your own stones off the board, provided it has no
  orthogonal adjacency with an enemy stone.  Sheet Figure 3 prints the legal
  (green) and illegal (red) removals; the green ones include stones that touch
  FRIENDLY stones and stones that touch an enemy only DIAGONALLY, which is what
  pins "orthogonal adjacency with enemy stones" as the exact predicate.

OBJECT.  You want your stones to form exactly ONE orthogonally connected group
(which may be a single stone).  "You can win on your turn or on your opponent's
turn.  If, after your turn, there is only one friendly group and only one enemy
group, you win."  So after EVERY turn both players' group counts are examined:

* if the mover has exactly one group, the mover wins (this also settles the tie
  — the sheet's third sentence is exactly the both-at-once case);
* otherwise, if the player who did not move has exactly one group, HE wins.

The sheet's stated test is symmetric in the two colours, so a literal "one
friendly AND one enemy group" reading would make the second sentence dead prose;
Figure 4 kills it outright — it is captioned "Black wins" and shows Black with
one group and White with TWO.  (AbstractPlay's ``unane.ts`` ``checkEOG``
independently agrees with the reading implemented here.)

TERMINATION (no ply cap, no repetition rule — the game cannot loop).
Every non-swap turn removes exactly one stone from the board: a capture by
replacement removes the captured enemy stone and relocates the mover's own; a
removal takes one friendly stone off.  Nothing is ever added, so no position can
repeat and the total stone count strictly decreases.  A player holding exactly
one stone trivially has exactly one group, so the game is over the moment either
count reaches 1; both counts therefore stay >= 2 while play continues, which
needs a total of >= 4 stones.  Starting from ``W*H`` stones, at most ``W*H - 4``
turns can leave both counts >= 2, and one further turn ends the game, so a game
lasts at most ``W*H - 3`` stone-removing plies plus the single optional swap ply
(which removes NOTHING): ``max_plies(w, h) = W*H - 2``.  Derived from the board
dimensions in code — never a pinned constant.

NO-MOVE IS IMPOSSIBLE (proved, not defended).  Take any stone you own.  Either
it has an orthogonally adjacent enemy stone — then you can capture it — or it
has none, and then you may remove it.  So a player with at least one stone
always has a legal move, and a player with zero stones is unreachable: reaching
zero requires passing through one, and one stone is one group, which ends the
game.  ``selftest.py`` verifies both halves exhaustively on constructed boards.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# Board widths offered in the manifest.  The board is WIDTH columns x
# (WIDTH - 1) rows, so the width is the even dimension the rule sheet requires.
# 8 (= 8x7) is AbstractPlay's default; 4 (= 4x3) is small enough to solve
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

    ``w*h - 3`` stone-removing plies (the count argument in the module
    docstring) plus the one optional swap ply, which removes nothing.  Derived
    from the board dimensions alone — never a pinned constant.
    """
    return w * h - 2


# --------------------------------------------------------------------------
#  Pure board helpers.  ``board`` is a sparse dict {(c, r): seat}; a cell that
#  is absent from the dict is empty.  These are used by the game, the selftest
#  and the exhaustive solver alike.
# --------------------------------------------------------------------------

def neighbours(w: int, h: int, cell: tuple) -> list:
    """The orthogonally adjacent cells of `cell` that are on the board."""
    c0, r0 = cell
    return [(c0 + dc, r0 + dr) for dc, dr in ORTHO
            if 0 <= c0 + dc < w and 0 <= r0 + dr < h]


def capture_targets(board: dict, w: int, h: int, cell: tuple) -> list:
    """Every enemy stone the stone on `cell` can capture: the ORTHOGONALLY
    ADJACENT enemy stones, in any direction (Figure 2)."""
    seat = board.get(cell)
    if seat is None:
        return []
    return [nb for nb in neighbours(w, h, cell)
            if board.get(nb) not in (None, seat)]


def can_remove(board: dict, w: int, h: int, cell: tuple) -> bool:
    """May the stone on `cell` be taken off the board?  Only if it is yours and
    has NO orthogonal adjacency with an enemy stone (Figure 3).  Friendly and
    diagonal neighbours are irrelevant."""
    seat = board.get(cell)
    if seat is None:
        return False
    return not any(board.get(nb) not in (None, seat)
                   for nb in neighbours(w, h, cell))


def all_turns(board: dict, w: int, h: int, seat: int) -> list:
    """Every (from, to) turn available to `seat`, in deterministic order.
    A capture has ``to != from``; a REMOVAL is encoded as ``to == from``."""
    out = []
    for cell in sorted(c for c, p in board.items() if p == seat):
        if can_remove(board, w, h, cell):
            out.append((cell, cell))
        for tgt in capture_targets(board, w, h, cell):
            out.append((cell, tgt))
    return out


def groups(board: dict, w: int, h: int, seat: int) -> list:
    """The orthogonally connected groups of `seat`'s stones.  Only stones of
    that colour connect — empty points do not link anything (unlike the
    designer's Narrows)."""
    own = {c for c, p in board.items() if p == seat}
    seen: set = set()
    comps: list = []
    for start in sorted(own):
        if start in seen:
            continue
        comp = {start}
        seen.add(start)
        stack = [start]
        while stack:
            cur = stack.pop()
            for nb in neighbours(w, h, cur):
                if nb in own and nb not in comp:
                    comp.add(nb)
                    seen.add(nb)
                    stack.append(nb)
        comps.append(comp)
    return comps


def is_unified(board: dict, w: int, h: int, seat: int) -> bool:
    """Has `seat` met the object of the game — exactly ONE group?  A seat with
    NO stones has no groups at all and has *not* won (matching AbstractPlay);
    that case is in any event unreachable — see ``selftest.py``."""
    return len(groups(board, w, h, seat)) == 1


# --------------------------------------------------------------------------


@dataclass
class UnaneState:
    w: int = 8
    h: int = 7
    board: dict = field(default_factory=dict)   # (c, r) -> seat
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0                 # completed plies (swap is legal iff ply == 1)
    last: tuple = ()             # (from, to) of the last turn, () otherwise
    swapped: bool = False        # was the pie rule exercised?


class Unane(Game):
    name = "Ūnane"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ core

    def initial_state(self, options=None, rng=None) -> UnaneState:
        o = options or {}
        size = int(o.get("size", 8))
        if size not in SIZES:
            raise ValueError(f"unsupported board size {size!r}")
        w, h = board_dims(size)
        # Checkerboard: Black (seat 0) on the even-parity cells.  The height is
        # ODD, so this puts a black stone on the TOP-LEFT pit, exactly as
        # Figure 1 of the rule sheet draws it.
        board = {(c, r): (0 if (c + r) % 2 == 0 else 1)
                 for c in range(w) for r in range(h)}
        return UnaneState(w=w, h=h, board=board)

    def current_player(self, s: UnaneState) -> int:
        return s.to_move

    def legal_moves(self, s: UnaneState) -> list:
        if s.winner is not None:
            return []
        moves = [f"{f[0]},{f[1]}>{t[0]},{t[1]}"
                 for f, t in all_turns(s.board, s.w, s.h, s.to_move)]
        if s.ply == 1:
            moves.append("swap")
        return moves

    def apply_move(self, s: UnaneState, move: str, rng=None) -> UnaneState:
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
            new = UnaneState(w=s.w, h=s.h, board=board, to_move=1 - seat,
                             ply=s.ply + 1, last=(), swapped=True)
        else:
            frm, to = (_cell(x) for x in move.split(">"))
            if s.board.get(frm) != seat:
                raise ValueError(f"{move}: no stone of yours on {cell_name(frm)}")
            board = dict(s.board)
            if to == frm:
                if not can_remove(s.board, s.w, s.h, frm):
                    raise ValueError(f"{move}: {cell_name(frm)} is orthogonally "
                                     f"adjacent to an enemy stone")
                del board[frm]
            else:
                if to not in capture_targets(s.board, s.w, s.h, frm):
                    raise ValueError(f"{move}: not an orthogonally adjacent "
                                     f"enemy stone")
                del board[frm]
                board[to] = seat            # capture by replacement
            new = UnaneState(w=s.w, h=s.h, board=board, to_move=1 - seat,
                             ply=s.ply + 1, last=(frm, to), swapped=s.swapped)

        # You can win on your turn or on your opponent's turn; if the move
        # unifies both players, the mover wins.
        mover_ok = is_unified(new.board, new.w, new.h, seat)
        other_ok = is_unified(new.board, new.w, new.h, 1 - seat)
        if mover_ok:
            new.winner = seat
        elif other_ok:
            new.winner = 1 - seat
        return new

    def is_terminal(self, s: UnaneState) -> bool:
        return s.winner is not None or not self.legal_moves(s)

    def returns(self, s: UnaneState) -> list:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        # Provably unreachable (see the module docstring and selftest.py): every
        # stone you own offers you either a capture or a removal, so only a
        # player with no stones at all could be stuck — and being reduced to one
        # stone already ends the game.  Scored as an honest draw rather than a
        # fabricated winner.
        return [0.0, 0.0]

    # ------------------------------------------------------------- bot eval

    def heuristic(self, s: UnaneState) -> list:
        """Rollout-cutoff evaluation for ``MCTSBot`` — a LIST of per-seat
        payoffs, as the bot's back-propagation requires.

        The object of the game is to get down to ONE group, so the natural
        signal is the difference in group counts, squashed into (-1, 1).

        MEASURED THROUGH THE CONSUMER, not by 1-ply greedy play: ``MCTSBot``
        (120 iterations, ``max_rollout=4`` so the cutoff — and therefore this
        function — is always reached) on the 6x5 board, seats alternated.

        * vs this same eval SIGN-FLIPPED: **10-0 over 10 games** (two-sided
          p ~= 0.002).  This is what pins the DIRECTION rather than merely the
          shape, and it REPLICATED EXACTLY (10-0) in an independent QA re-run.
        * vs a constant-zero eval the gain is real but MODEST, and the exact
          margin is seed-dependent: 29-11 (0.725) on the seeds used here, but
          25-15 (0.625, two-sided p ~= 0.15 — not significant on its own) on an
          independent QA re-run of the same 40-game protocol.  Pooled over both
          runs: 54-26 of 80 (p ~= 0.002).  Read this as "better than no eval,
          by a modest
          amount", NOT as a stable 0.725 win rate.

        ``MCTSBot`` only calls this on a NON-terminal state (it uses
        ``returns`` when a rollout reaches a terminal), so there is deliberately
        no terminal branch here — this is exactly the function that was
        measured.
        """
        a = len(groups(s.board, s.w, s.h, 0))
        b = len(groups(s.board, s.w, s.h, 1))
        v = math.tanh((b - a) / 3.0)
        return [v, -v]

    # ----------------------------------------------------------- (de)serialize

    def serialize(self, s: UnaneState) -> dict:
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

    def deserialize(self, d: dict) -> UnaneState:
        return UnaneState(
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

    def describe_move(self, s: UnaneState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        try:
            frm, to = (_cell(x) for x in move.split(">"))
            if frm == to:
                return f"-{cell_name(frm)}"          # removal
            return f"{cell_name(frm)}x{cell_name(to)}"
        except Exception:
            return move

    @staticmethod
    def seat_colour(s: UnaneState, seat: int) -> str:
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

    def render(self, s: UnaneState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p}
                  for (c, r), p in s.board.items()]
        highlights = []
        if s.winner is not None:
            for cell in sorted(groups(s.board, s.w, s.h, s.winner)[0]):
                highlights.append({"cell": f"{cell[0]},{cell[1]}",
                                   "kind": "goal"})
            name = self.seat_colour(s, s.winner)
            caption = (f"{name} wins — every {name} stone is in one "
                       f"orthogonally connected group")
        elif not self.legal_moves(s):
            caption = "No legal turn — draw"
        else:
            for cell in s.last:
                highlights.append({"cell": f"{cell[0]},{cell[1]}",
                                   "kind": "last-move"})
            caption = (f"{self.seat_colour(s, s.to_move)} to move — capture an "
                       f"adjacent enemy stone, or click one of your own stones "
                       f"twice to remove it")
            if s.ply == 1:
                caption += " (or take the pie swap)"
        return {
            "board": {"type": "square", "width": s.w, "height": s.h},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "actionNames": {"swap": "Swap colours (pie rule)"},
        }
