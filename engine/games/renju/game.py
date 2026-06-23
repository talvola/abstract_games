"""Renju — professional Gomoku with Black-handicap (forbidden-move) rules.

Renju is Gomoku (five in a row on a 15x15 board, Black/player 0 moves first,
placement only) with handicaps imposed on Black to offset the first-move
advantage:

* WHITE wins with FIVE OR MORE in a row (overlines win for White).
* BLACK wins ONLY with an EXACT FIVE; a Black overline (six or more) is NOT a
  win.
* BLACK is FORBIDDEN from making a move that creates any of:
    (a) a DOUBLE-THREE  — two or more "open threes",
    (b) a DOUBLE-FOUR   — two or more "fours",
    (c) an OVERLINE      — six or more in a row.
  Black LOSES immediately if its move makes a forbidden shape, UNLESS that same
  move also makes an exact five-in-a-row, in which case the five-win takes
  precedence (an exact five is always a win for Black, even when the move would
  otherwise be forbidden).
* WHITE is never restricted.

This package implements the BASE Renju forbidden-move ruleset only. It does NOT
implement opening rules (no swap, no opening-move restrictions). See rules.md.

The forbidden-move detector follows the standard Renju International Federation
(RIF) recursive definitions of three/four/open-three. See the long comment on
`RenjuRules` below for the exact algorithm and the documented interpretation
points.

Cells are "col,row"; a move is a single empty cell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZE = 15
BLACK = 0
WHITE = 1
EMPTY = None
NAMES = {0: "Black", 1: "White"}

# The four line directions (each is one of a +/- pair, handled symmetrically).
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _in_bounds(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE


# ---------------------------------------------------------------------------
# Forbidden-move / line analysis
# ---------------------------------------------------------------------------
#
# All analysis is done on a board dict mapping (c, r) -> player. EMPTY squares
# are simply absent. Black is player 0.
#
# Terminology (RIF):
#   * "five"          : exactly five black stones in an unbroken row.
#   * "overline"      : six or more black stones in an unbroken row.
#   * "four"          : a line of black stones from which a *single* black move
#                       completes an (exact) five. There may be more than one
#                       completing point (a "straight four"/open four) or just
#                       one (a "simple four"). A move "makes a four" once for
#                       each distinct four-shape it creates along a direction;
#                       a straight four counts as ONE four (the standard rule:
#                       the open four "_BBBB_" is a single four, not two).
#   * "open three"    : a line of black stones from which a single black move
#                       makes a *straight four* (open four "_BBBB_"). The point
#                       that develops the three into the straight four must be a
#                       point where placing a black stone is itself NOT a
#                       forbidden / illegal point that destroys the four (the
#                       recursive part: a three is only a real three if it can
#                       actually be developed into a four legally).
#
# DOUBLE-THREE  = the move creates >= 2 open threes.
# DOUBLE-FOUR   = the move creates >= 2 fours.
# OVERLINE      = the move creates a black row of length >= 6.
#
# Recursion / nesting (the crux): determining whether a black point is
# forbidden can require knowing whether *other* black points are forbidden
# (because an open three only counts if it can legally be developed into a
# straight four, and a four only counts if it can legally complete a five —
# but a five always overrides forbiddenness, so a completing point of a four is
# never blocked by forbiddenness). RIF resolves this recursively with the rule
# that a five ALWAYS overrides forbidden status. We implement that recursion
# with a depth guard; in practice nesting is shallow.
#
# This is a faithful implementation of the widely used RIF recursive algorithm
# (the same approach as e.g. the renjuoffline / Wikipedia "Renju" description).
# The one documented interpretation point is the standard one: when testing
# whether a "three" can be developed into a "straight four", the developing
# black stone's own forbiddenness is checked recursively (a three developed
# only via a forbidden point is not a valid three). See rules.md.


class RenjuRules:
    """Stateless analysis helpers over a board dict (Black = player 0)."""

    @staticmethod
    def run_length(board, c, r, dc, dr, player):
        """Length of the unbroken run of `player` through (c,r) along axis."""
        if board.get((c, r)) != player:
            return 0
        run = 1
        for sign in (1, -1):
            cc, rr = c + dc * sign, r + dr * sign
            while board.get((cc, rr)) == player:
                run += 1
                cc += dc * sign
                rr += dr * sign
        return run

    @staticmethod
    def max_run_through(board, cell, player):
        c, r = cell
        return max(RenjuRules.run_length(board, c, r, dc, dr, player)
                   for dc, dr in DIRS)

    @staticmethod
    def makes_exact_five(board, cell, player):
        """True if (cell), occupied by player, lies in an EXACT-five run.

        For black this is the win test. We require *some* direction to have a
        run of exactly five (an overline run of >=6 is not an exact five, but if
        a separate direction is exactly five that still wins)."""
        c, r = cell
        for dc, dr in DIRS:
            if RenjuRules.run_length(board, c, r, dc, dr, player) == 5:
                return True
        return False

    @staticmethod
    def makes_five_or_more(board, cell, player):
        """White win test: any run of length >= 5 through cell."""
        return RenjuRules.max_run_through(board, cell, player) >= 5

    @staticmethod
    def makes_overline(board, cell, player):
        """True if any run through cell has length >= 6."""
        return RenjuRules.max_run_through(board, cell, player) >= 6

    # --- four / three detection along a single direction ------------------

    @staticmethod
    def _line_cells(board, c, r, dc, dr, player, span=5):
        """Return the window of states along a direction centered loosely.

        Helper not used directly; analysis below scans explicit windows."""
        raise NotImplementedError

    @staticmethod
    def empties_completing_five(board, c, r, dc, dr):
        """For the BLACK stone just placed at (c,r), find empty points along
        the (dc,dr) axis whose addition (as black) would create an EXACT five
        run that includes (c,r). Returns the set of such empty points.

        We scan every empty point within distance 4 of (c,r) along the axis,
        tentatively place a black stone, and check for an exact-five run that
        passes through both (c,r) and the candidate point."""
        results = set()
        for k in range(-5, 6):
            if k == 0:
                continue
            pc, pr = c + dc * k, r + dr * k
            if not _in_bounds(pc, pr):
                continue
            if board.get((pc, pr)) is not None:
                continue
            nb = dict(board)
            nb[(pc, pr)] = BLACK
            # The new five must include the original stone (c,r): require the
            # run through (c,r) along this axis to be exactly five AND include
            # (pc,pr).
            run = RenjuRules.run_length(nb, c, r, dc, dr, BLACK)
            if run == 5:
                # verify (pc,pr) is part of that run
                # the run through (c,r) spans contiguous black stones; (pc,pr)
                # being black and adjacent in-run is guaranteed by run inclusion
                results.add((pc, pr))
        return results

    @staticmethod
    def is_four_in_dir(board, c, r, dc, dr):
        """True if the black stone at (c,r) forms a FOUR along (dc,dr):
        i.e. there exists an empty point on this axis that would complete an
        exact five. Returns the set of completing empty points (a "straight
        four" has two, a simple four has one)."""
        return RenjuRules.empties_completing_five(board, c, r, dc, dr)

    @staticmethod
    def count_fours(board, cell):
        """Number of distinct FOURS the black stone at `cell` participates in.

        One per direction that has at least one completing point. A straight
        four (two completing points) along one direction counts as a single
        four (standard RIF: the open four _BBBB_ is one four)."""
        c, r = cell
        n = 0
        for dc, dr in DIRS:
            # only count if there is already a 4-in-a-window potential, i.e.
            # a completing point exists AND the move is not already a five/
            # overline along this direction (a made five is not a "four").
            run = RenjuRules.run_length(board, c, r, dc, dr, BLACK)
            if run >= 5:
                continue  # this direction is already a five+/overline, not a four
            comps = RenjuRules.empties_completing_five(board, c, r, dc, dr)
            if comps:
                n += 1
        return n

    @staticmethod
    def is_open_three_in_dir(board, c, r, dc, dr, depth=0):
        """True if the black stone at (c,r) forms an OPEN THREE along (dc,dr).

        An open three is a shape that can be developed, by a single black move
        at an empty point on this axis, into a STRAIGHT (open) FOUR — that is a
        four with TWO distinct completing points (the _BBBB_ shape). The
        developing point must itself be a legal black point (placing there must
        not be a forbidden move that would prevent the straight four). We check
        the developing point's forbiddenness recursively (bounded depth).

        A three is, by definition, a THREE: the placed stone must NOT already be
        part of a four-or-more along this direction. A run of 4 (a straight or
        simple four) is a FOUR, never a three, so we exclude run >= 4 here. (The
        prior bug counted a straight four `_BBBB_` as an open three because it
        only excluded run >= 5, then accepted a development point that merely
        recompleted the *pre-existing* four's two empties rather than extending
        an actual three.)"""
        # A three has at most three stones in the run through (c,r) along this
        # axis. Any run of FOUR or more is a four/five/overline, NOT a three.
        run = RenjuRules.run_length(board, c, r, dc, dr, BLACK)
        if run >= 4:
            return False
        for k in range(-5, 6):
            if k == 0:
                continue
            pc, pr = c + dc * k, r + dr * k
            if not _in_bounds(pc, pr):
                continue
            if board.get((pc, pr)) is not None:
                continue
            nb = dict(board)
            nb[(pc, pr)] = BLACK
            # The developing stone must actually EXTEND this three: after
            # placing it, the run through (c,r) along this axis must grow to
            # exactly FOUR (an open four `_BBBB_`). This rules out a development
            # point that lies off the placed stone's line of three (e.g. a
            # disconnected stone that, together with a pre-existing four, would
            # spuriously yield two completing points).
            run2 = RenjuRules.run_length(nb, c, r, dc, dr, BLACK)
            if run2 != 4:
                continue  # not an extension of THIS three into an open four
            comps = RenjuRules.empties_completing_five(nb, c, r, dc, dr)
            if len(comps) >= 2:
                # Straight four exists. Now the developing point (pc,pr) must
                # be a legal black point (not forbidden in a way that destroys
                # the shape). Check recursively with depth guard.
                if depth >= 3:
                    return True  # assume legal at deep nesting
                if not RenjuRules.is_forbidden_point(board, (pc, pr),
                                                     depth=depth + 1):
                    return True
        return False

    @staticmethod
    def count_open_threes(board, cell, depth=0):
        c, r = cell
        n = 0
        for dc, dr in DIRS:
            if RenjuRules.is_open_three_in_dir(board, c, r, dc, dr, depth):
                n += 1
        return n

    @staticmethod
    def is_forbidden_point(board, cell, depth=0):
        """True if placing a BLACK stone at `cell` (currently empty) is a
        forbidden move (double-three / double-four / overline) AND does not
        simultaneously make an exact five.

        A move that makes an exact five is NEVER forbidden (five overrides)."""
        if board.get(cell) is not None:
            return False
        nb = dict(board)
        nb[cell] = BLACK

        # Five always overrides — never forbidden.
        if RenjuRules.makes_exact_five(nb, cell, BLACK):
            return False

        # Overline.
        if RenjuRules.makes_overline(nb, cell, BLACK):
            return True

        # Double-four.
        if RenjuRules.count_fours(nb, cell) >= 2:
            return True

        # Double-three.
        if RenjuRules.count_open_threes(nb, cell, depth) >= 2:
            return True

        return False


@dataclass
class RenjuState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None    # 0/1 = that player wins; None = no result yet
    # last move (for highlight / move log)
    last: Optional[tuple] = None


class Renju(Game):
    uid = "renju"
    name = "Renju"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> RenjuState:
        return RenjuState()

    def current_player(self, s: RenjuState) -> int:
        return s.to_move

    def legal_moves(self, s: RenjuState) -> list[str]:
        if self.is_terminal(s):
            return []
        # All empty cells are legal moves. A Black forbidden move is *legal to
        # play* but loses the game immediately (it is a rule of Renju that the
        # forbidden move ends the game as a loss for Black, not an illegal /
        # unplayable move). Modelling it as a legal-but-losing move keeps the
        # game tree well-formed and matches how Renju is scored.
        return [f"{c},{r}" for c in range(SIZE) for r in range(SIZE)
                if (c, r) not in s.board]

    def apply_move(self, s: RenjuState, move: str, rng=None) -> RenjuState:
        cell = _cell(move)
        board = dict(s.board)
        player = s.to_move
        board[cell] = player

        winner = None
        if player == WHITE:
            if RenjuRules.makes_five_or_more(board, cell, WHITE):
                winner = WHITE
        else:  # BLACK
            if RenjuRules.makes_exact_five(board, cell, BLACK):
                # Exact five always wins for Black — overrides any forbidden
                # shape the same move might also create.
                winner = BLACK
            else:
                # No exact five. Check forbidden shapes.
                forbidden = (
                    RenjuRules.makes_overline(board, cell, BLACK)
                    or RenjuRules.count_fours(board, cell) >= 2
                    or RenjuRules.count_open_threes(board, cell) >= 2
                )
                if forbidden:
                    winner = WHITE  # Black loses immediately
        return RenjuState(board=board, to_move=1 - player, winner=winner,
                          last=cell)

    def is_terminal(self, s: RenjuState) -> bool:
        return s.winner is not None or len(s.board) == SIZE * SIZE

    def returns(self, s: RenjuState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: RenjuState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
        }

    def deserialize(self, d: dict) -> RenjuState:
        return RenjuState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            last=(_cell(d["last"]) if d.get("last") else None),
        )

    def describe_move(self, s: RenjuState, move: str) -> str:
        c, r = _cell(move)
        return f"{NAMES[s.to_move][0]}:{c + 1},{r + 1}"

    def render(self, s: RenjuState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}",
                               "kind": "last-move"})
        if s.winner is not None:
            if s.winner == WHITE and s.last is not None and \
                    s.board.get(s.last) == BLACK:
                caption = "White wins (Black played a forbidden move)"
            else:
                caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
