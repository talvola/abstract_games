"""GIPF (Kris Burm, 1997) -- the namesake of the GIPF Project, basic game.

The board is a hexagon of 37 spots (a radius-3 hex of points joined by lines in
three directions) ringed by 24 entry dots (the radius-4 boundary). Each turn a
player INTRODUCES one piece from their reserve onto an entry dot and SHOVES it
one step inward along that dot's line: the new piece occupies the first interior
spot and any unbroken run of pieces ahead of it slides one spot further along the
line. The shove is illegal if that line is full all the way to the far edge
(there is nowhere for the front piece to go). After the shove, any line of FOUR
OR MORE same-colour pieces is removed by its owner -- the owner's pieces return
to their reserve, opponent pieces sitting in the contiguous extension of the run
are captured (lost). A player who must introduce a piece but has an empty reserve
loses.

Pieces start with three per player on the six corners of the board, colours
alternating. Each player has a reserve of 15 pieces (3 start on the board, 12 in
hand). Single-piece (basic) game only; see rules.md for the documented
interpretations (notably the entry-dot line geometry).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

R = 3  # board radius (37 spots)

# --- geometry ---------------------------------------------------------------
# Axial hex coordinates (q, r). The third cube coord is s = -q-r.
# Board spots: the radius-3 hexagon (37 points).
SPOTS = [(q, r) for q in range(-R, R + 1) for r in range(-R, R + 1)
         if abs(q + r) <= R]
SPOTSET = frozenset(SPOTS)

# Entry dots: the outer ring of the radius-4 hexagon (24 points), one just beyond
# each board-edge point.
_RING4 = [(q, r) for q in range(-(R + 1), R + 2) for r in range(-(R + 1), R + 2)
          if max(abs(q), abs(r), abs(q + r)) == R + 1]
DOTS = list(_RING4)
DOTSET = frozenset(DOTS)

# The six line directions (a piece slides along one of three line axes).
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

# Corner spots of the board (where the starting pieces sit).
CORNERS = [(q, r) for (q, r) in SPOTS
           if [abs(q), abs(r), abs(q + r)].count(R) == 2]


def _cell(qr) -> str:
    return f"{qr[0]},{qr[1]}"


def _qr(s: str):
    a, b = s.split(",")
    return (int(a), int(b))


def _line_from(spot, d):
    """The maximal run of board spots starting at `spot` and stepping by `d`."""
    line = []
    cur = spot
    while cur in SPOTSET:
        line.append(cur)
        cur = (cur[0] + d[0], cur[1] + d[1])
    return line


def _entries():
    """All legal introductions: dot -> (first interior spot, direction, full line).

    An entry is a (dot, first_spot) pair. The first_spot is a board spot adjacent
    to the dot; the direction continues away from the dot (dot -> first_spot ->
    deeper). A dot beyond a board edge can be adjacent to two board spots (two
    line directions); both are offered (see rules.md, "entry geometry").
    """
    out = {}
    for dot in DOTS:
        for d in DIRS:
            first = (dot[0] + d[0], dot[1] + d[1])
            if first in SPOTSET:
                # the inward line from `first` along d
                line = _line_from(first, d)
                out[(dot, first)] = (d, line)
    return out


ENTRIES = _entries()

# Cosmetic line segments for the renderer: each maximal board line drawn once.
def _line_segments():
    segs = []
    seen = set()
    for d in [(1, 0), (0, 1), (1, -1)]:
        for s in SPOTS:
            if (s[0] - d[0], s[1] - d[1]) in SPOTSET:
                continue  # not the start of a maximal line
            line = _line_from(s, d)
            if len(line) < 2:
                continue
            key = frozenset(line)
            if key in seen:
                continue
            seen.add(key)
            segs.append([list(line[0]), list(line[-1])])
    return segs


LINES = _line_segments()

# All maximal board lines (for run detection), as ordered tuples.
def _all_lines():
    out = []
    seen = set()
    for d in [(1, 0), (0, 1), (1, -1)]:
        for s in SPOTS:
            if (s[0] - d[0], s[1] - d[1]) in SPOTSET:
                continue
            line = _line_from(s, d)
            key = frozenset(line)
            if key in seen:
                continue
            seen.add(key)
            out.append(tuple(line))
    return out


ALL_LINES = _all_lines()

START_RESERVE = 15  # pieces per player; 3 start on the board, 12 in hand


@dataclass
class GState:
    board: dict = field(default_factory=dict)      # spot-cell-id -> owner (0/1)
    reserve: list = field(default_factory=lambda: [12, 12])  # in hand
    to_move: int = 0
    removing: object = None      # None, or seat that must remove a run now
    winner: object = None
    plies: int = 0               # introductions made (draw clock)
    last: object = None          # last introduced spot id (for highlight)


class Gipf(Game):
    uid = "gipf"
    name = "GIPF"
    PLY_CAP = 400  # defensive draw cap on introductions

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        st = GState()
        # three pieces per player on the six corners, colours alternating.
        # order the corners around the hexagon so alternation is geometric.
        ordered = sorted(CORNERS, key=lambda c: _angle(c))
        for i, c in enumerate(ordered):
            st.board[_cell(c)] = i % 2          # 0,1,0,1,0,1 around the ring
        # each colour placed 3 pieces from its reserve at setup
        st.reserve = [12, 12]
        return st

    def current_player(self, state):
        if state.removing is not None:
            return state.removing
        return state.to_move

    # ---- run detection -----------------------------------------------------
    def _runs(self, board, colour):
        """Maximal contiguous blocks (no gaps) on a board line that contain a
        run of >=4 of `colour`. Returns list of frozensets of spot-cell-ids
        (the whole removable segment incl. extension)."""
        out = []
        for line in ALL_LINES:
            ids = [_cell(c) for c in line]
            n = len(ids)
            i = 0
            while i < n:
                if board.get(ids[i]) is None:
                    i += 1
                    continue
                j = i
                while j < n and board.get(ids[j]) is not None:
                    j += 1
                seg = ids[i:j]            # maximal occupied block (no gaps)
                # does this block contain >=4 consecutive of `colour`?
                if self._has_four(board, seg, colour):
                    out.append(frozenset(seg))
                i = j
        return out

    @staticmethod
    def _has_four(board, seg, colour):
        run = 0
        for cid in seg:
            if board.get(cid) == colour:
                run += 1
                if run >= 4:
                    return True
            else:
                run = 0
        return False

    def _any_run(self, board):
        return bool(self._runs(board, 0)) or bool(self._runs(board, 1))

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        if state.removing is not None:
            # choose a run of your colour to remove; identify by its lowest cell.
            runs = self._runs(state.board, state.removing)
            return sorted(_run_id(r) for r in runs)
        pl = state.to_move
        if state.reserve[pl] <= 0:
            return []          # cannot introduce -> loss (handled in terminal)
        out = []
        for (dot, first), (d, line) in ENTRIES.items():
            if self._shove_ok(state.board, line):
                out.append(f"{_cell(dot)}>{_cell(first)}")
        return sorted(out)

    def _shove_ok(self, board, line):
        """A shove is legal unless the line is full all the way to the far edge
        (the front piece would be pushed off the board)."""
        # find first empty spot along the line from the entry end.
        for c in line:
            if board.get(_cell(c)) is None:
                return True
        return False

    def apply_move(self, state, move, rng=None):
        if state.removing is not None:
            return self._apply_removal(state, move)
        # introduce + shove
        dot_s, first_s = move.split(">")
        dot, first = _qr(dot_s), _qr(first_s)
        d, line = ENTRIES[(dot, first)]
        board = dict(state.board)
        reserve = list(state.reserve)
        pl = state.to_move
        # shove: find the first gap; slide everything from `first` up to the gap.
        idx_gap = None
        for k, c in enumerate(line):
            if board.get(_cell(c)) is None:
                idx_gap = k
                break
        assert idx_gap is not None, "illegal shove (line full)"
        # move pieces from idx_gap-1 .. 0 each one step toward idx_gap
        for k in range(idx_gap, 0, -1):
            board[_cell(line[k])] = board[_cell(line[k - 1])]
        board[_cell(line[0])] = pl
        reserve[pl] -= 1
        first_id = _cell(line[0])

        ns = GState(board=board, reserve=reserve, to_move=pl,
                    removing=None, winner=state.winner,
                    plies=state.plies + 1, last=first_id)
        # resolution phase: mover removes their runs first, then opponent.
        return self._begin_resolution(ns, mover=pl)

    def _begin_resolution(self, ns, mover):
        # mover's runs first
        if self._runs(ns.board, mover):
            ns.removing = mover
            return ns
        opp = 1 - mover
        if self._runs(ns.board, opp):
            ns.removing = opp
            return ns
        # no runs: pass the turn and settle a possible loss
        ns.to_move = opp
        ns.removing = None
        return self._settle(ns)

    def _apply_removal(self, state, move):
        seat = state.removing
        board = dict(state.board)
        reserve = list(state.reserve)
        # the run identified by `move` (its lowest cell id)
        runs = self._runs(board, seat)
        target = None
        for r in runs:
            if _run_id(r) == move:
                target = r
                break
        assert target is not None, f"no run {move}"
        for cid in target:
            owner = board[cid]
            if owner == seat:
                reserve[seat] += 1       # own pieces return to reserve
            # opponent pieces in the extension are captured (lost) -- not banked
            del board[cid]

        ns = GState(board=board, reserve=reserve, to_move=state.to_move,
                    removing=None, winner=state.winner,
                    plies=state.plies, last=state.last)
        # keep removing same seat's remaining runs, then hand to the other seat.
        if self._runs(ns.board, seat):
            ns.removing = seat
            return ns
        other = 1 - seat
        # the OTHER seat removes only if it is the original opponent of the mover;
        # but generally: continue resolution for whoever still has runs, with the
        # MOVER (to_move) resolved before the opponent.
        mover = ns.to_move
        if seat == mover and self._runs(ns.board, other):
            ns.removing = other
            return ns
        # resolution done -> pass the turn
        ns.removing = None
        ns.to_move = 1 - mover
        return self._settle(ns)

    def _settle(self, ns):
        """At the start of `ns.to_move`'s turn: if they cannot introduce a piece
        (empty reserve), they lose."""
        if ns.winner is None and ns.removing is None:
            if ns.reserve[ns.to_move] <= 0:
                ns.winner = 1 - ns.to_move
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return state.winner is None and state.plies >= self.PLY_CAP

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialize ---------------------------------------------------------
    def serialize(self, state):
        return {
            "board": dict(state.board),
            "reserve": list(state.reserve),
            "to_move": state.to_move,
            "removing": state.removing,
            "winner": state.winner,
            "plies": state.plies,
            "last": state.last,
        }

    def deserialize(self, d):
        return GState(board=dict(d["board"]), reserve=list(d["reserve"]),
                      to_move=d["to_move"], removing=d.get("removing"),
                      winner=d.get("winner"), plies=d.get("plies", 0),
                      last=d.get("last"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if state.removing is not None:
            return f"x{move}"
        return move.replace(">", "->")

    def render(self, state, perspective=None):
        cells = []
        for (q, r) in SPOTS:
            x, y = _xy(q, r)
            s = 0.42
            cells.append({"id": _cell((q, r)),
                          "points": [[x - s, y - s], [x + s, y - s],
                                     [x + s, y + s], [x - s, y + s]]})
        # entry dots as small cosmetic cells (so they're clickable for entry)
        for (q, r) in DOTS:
            x, y = _xy(q, r)
            s = 0.22
            cells.append({"id": _cell((q, r)),
                          "points": [[x - s, y - s], [x + s, y - s],
                                     [x + s, y + s], [x - s, y + s]]})
        pieces = [{"cell": cid, "owner": ow} for cid, ow in state.board.items()]
        names = {0: "White", 1: "Black"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw (ply cap)"
        elif state.removing is not None:
            cap = f"{names[state.removing]}: remove a row of four"
        else:
            cap = f"{names[state.to_move]} to move ({state.reserve[state.to_move]} in reserve)"
        # render lines in xy space
        line_xy = []
        for seg in LINES:
            (q0, r0), (q1, r1) = seg[0], seg[1]
            line_xy.append([list(_xy(q0, r0)), list(_xy(q1, r1))])
        hl = []
        if state.last:
            hl.append({"cell": state.last, "kind": "last-move"})
        return {
            "board": {"type": "polygons", "cells": cells, "lines": line_xy},
            "pieces": pieces,
            "reserve": {str(p): ({"P": state.reserve[p]} if state.reserve[p] else {})
                        for p in (0, 1)},
            "highlights": hl,
            "caption": cap,
        }


# --- helpers ---------------------------------------------------------------
def _angle(c):
    import math
    x, y = _xy(c[0], c[1])
    return math.atan2(y, x)


def _xy(q, r):
    """Axial -> pixel (pointy-top), y grows downward for the renderer."""
    x = q + r / 2.0
    y = r * 0.8660254037844386  # sqrt(3)/2
    return (x, y)


def _run_id(run_frozenset):
    """A stable id for a run: its lexicographically smallest cell id."""
    return min(run_frozenset, key=lambda s: _qr(s))
