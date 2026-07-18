"""Smess (a.k.a. "Take the Brain"; the 1979 re-skin is "All the King's Men").

Reuben Klamer / Perry Grant, Parker Brothers 1970 — "The Ninny's Chess". A
7x8 chess variant in which every square carries printed ARROWS, and a piece may
leave a square only in a direction one of that square's arrows points. It is
always the arrows on the square a piece STARTS from that govern the move.

Three piece types per side (12 each = 1 Brain + 4 Numskulls + 7 Ninnies):
  * NINNY  — moves exactly one square along a start-square arrow.
  * NUMSKULL — rides any number of squares in a straight line along a
    start-square arrow direction; may not jump (stops at the first piece,
    capturing it if it is an enemy).
  * BRAIN  — moves exactly one square along a start-square arrow (like a Ninny).

Capture is by displacement (as in chess). The object is simply to CAPTURE the
enemy Brain: there is no check or checkmate — you win the instant you take it.
Arrows are ABSOLUTE board directions (identical for both players); you may even
move backward if an arrow points that way.

Promotion (official Parker Brothers rules): a Ninny that moves onto one of the
OPPONENT'S Numskull starting squares becomes a Numskull.

Draw: the official rulebook declares the position a tie once "the only two
pieces left in the game are the two Brains".

The arrow map (`ARROWS`) is transcribed from the official Smess board image
(chessvariants.com/other.dir/smess.html, rendered from Fergus Duniho's
implementation) and is provably 180deg point-symmetric — the selftest asserts
this. Moves are clickable cell paths "from>to" (single step for Ninny/Brain,
the landing square for a Numskull slide); promotion is automatic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

W, H = 7, 8
NAMES = {0: "Red", 1: "Blue"}          # seat 0 renders red, seat 1 blue
LETTER = {"ninny": "N", "numskull": "S", "brain": "B"}
VALUE = {"ninny": 1, "numskull": 3, "brain": 0}
ARROW_COLOR = "#33475b"

# Draw safety valves (guarantee termination under random play; arrow moves are
# largely reversible, so cap no-progress runs and total plies).
NOPROG_CAP = 60      # plies with no capture and no promotion -> draw
PLY_CAP = 400        # hard ply cap -> draw

DIRS = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0),
        "NE": (1, 1), "NW": (-1, 1), "SE": (1, -1), "SW": (-1, -1)}
REV = {"N": "S", "S": "N", "E": "W", "W": "E",
       "NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}
ALL8 = set(DIRS)

# Arrow map, one rank per row (file order a..g). Rank 8 = Black's back row,
# rank 1 = Red's back row. Transcribed from the official board diagram and
# cross-checked by full 180deg rotational symmetry.
_RANKS = {
    8: [{"S", "E"}, {"W", "E", "S"}, {"W", "E", "S"}, {"W", "E", "S"},
        {"W", "E", "S"}, {"W", "E", "S"}, {"S"}],
    7: [{"N", "S"}, {"NW", "E", "S"}, {"N", "E", "S", "W"}, {"E", "S", "W"},
        {"N", "E", "S", "W"}, {"NW", "S"}, {"N", "S"}],
    6: [{"N", "E", "S"}, {"N", "E", "S", "W"}, {"NE", "NW", "SE", "SW"},
        {"E", "W"}, {"NE", "NW", "SE", "SW"}, {"N", "E", "W"}, {"N", "W", "S"}],
    5: [{"NE", "E", "SE"}, {"E"}, {"N", "E", "S"}, set(ALL8),
        {"N", "E", "S"}, {"N", "E", "S", "W"}, {"N", "S"}],
    4: [{"N", "S"}, {"N", "E", "S", "W"}, {"N", "W", "S"}, set(ALL8),
        {"N", "W", "S"}, {"W"}, {"NW", "W", "SW"}],
    3: [{"N", "E", "S"}, {"E", "S", "W"}, {"NE", "NW", "SE", "SW"},
        {"E", "W"}, {"NE", "NW", "SE", "SW"}, {"N", "E", "S", "W"}, {"N", "W", "S"}],
    2: [{"N", "S"}, {"N", "SE"}, {"N", "E", "S", "W"}, {"N", "E", "W"},
        {"N", "E", "S", "W"}, {"N", "W", "SE"}, {"N", "S"}],
    1: [{"N"}, {"N", "E", "W"}, {"N", "E", "W"}, {"N", "E", "W"},
        {"N", "E", "W"}, {"N", "E", "W"}, {"N", "W"}],
}
ARROWS: dict = {}
for _rank, _row in _RANKS.items():
    for _col, _s in enumerate(_row):
        ARROWS[(_col, _rank - 1)] = frozenset(_s)

# Numskull starting squares. A Ninny promotes on the OPPONENT'S set.
NUMSKULL_START = {0: {(1, 0), (2, 0), (4, 0), (5, 0)},
                  1: {(1, 7), (2, 7), (4, 7), (5, 7)}}
PROMO = {0: NUMSKULL_START[1], 1: NUMSKULL_START[0]}


def _on(c, r):
    return 0 <= c < W and 0 <= r < H


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _sq(c, r):
    return f"{chr(97 + c)}{r + 1}"


def _start_board() -> dict:
    b = {}
    for c in range(W):
        b[(c, 1)] = (0, "ninny")
        b[(c, 6)] = (1, "ninny")
    for c in (1, 2, 4, 5):
        b[(c, 0)] = (0, "numskull")
        b[(c, 7)] = (1, "numskull")
    b[(3, 0)] = (0, "brain")
    b[(3, 7)] = (1, "brain")
    return b


def _build_overlay():
    """Per-cell arrow glyphs for board.overlay (cell-coord space). Each arrow is
    one open polyline [tail, tip, barb1, tip, barb2, colour] sitting near the
    cell edge in its allowed direction (5 points -> sharp polyline, not a Bezier)."""
    ov = []
    for (c, r), dirs in ARROWS.items():
        for d in dirs:
            dc, dr = DIRS[d]
            ln = math.hypot(dc, dr)
            ux, uy = dc / ln, dr / ln
            px, py = -uy, ux                       # perpendicular
            tail = [round(c + 0.24 * ux, 3), round(r + 0.24 * uy, 3)]
            tip = [round(c + 0.42 * ux, 3), round(r + 0.42 * uy, 3)]
            b1 = [round(tip[0] - 0.11 * ux + 0.075 * px, 3),
                  round(tip[1] - 0.11 * uy + 0.075 * py, 3)]
            b2 = [round(tip[0] - 0.11 * ux - 0.075 * px, 3),
                  round(tip[1] - 0.11 * uy - 0.075 * py, 3)]
            ov.append([tail, tip, b1, list(tip), b2, ARROW_COLOR])
    return ov


OVERLAY = _build_overlay()


@dataclass
class SState:
    board: dict = field(default_factory=dict)   # (c, r) -> (owner, ptype)
    to_move: int = 0
    no_progress: int = 0
    ply: int = 0


class Smess(Game):
    uid = "smess"
    name = "Smess"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options: Optional[dict] = None, rng=None) -> SState:
        return SState(board=_start_board(), to_move=0, no_progress=0, ply=0)

    def current_player(self, state: SState) -> int:
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _raw_moves(self, state: SState):
        b, player = state.board, state.to_move
        out = []
        for (c, r), (owner, ptype) in b.items():
            if owner != player:
                continue
            for d in ARROWS[(c, r)]:
                dc, dr = DIRS[d]
                if ptype == "numskull":
                    k = 1
                    while True:
                        nc, nr = c + k * dc, r + k * dr
                        if not _on(nc, nr):
                            break
                        t = b.get((nc, nr))
                        if t is None:
                            out.append(f"{c},{r}>{nc},{nr}")
                            k += 1
                            continue
                        if t[0] != player:
                            out.append(f"{c},{r}>{nc},{nr}")
                        break
                else:                                   # ninny / brain: one step
                    nc, nr = c + dc, r + dr
                    if _on(nc, nr):
                        t = b.get((nc, nr))
                        if t is None or t[0] != player:
                            out.append(f"{c},{r}>{nc},{nr}")
        return out

    def legal_moves(self, state: SState):
        if self.is_terminal(state):
            return []
        return self._raw_moves(state)

    def apply_move(self, state: SState, move: str, rng=None) -> SState:
        frm, to = move.split(">")
        fc, fr = _cell(frm)
        tc, tr = _cell(to)
        b = dict(state.board)
        owner, ptype = b.pop((fc, fr))
        captured = b.get((tc, tr))
        progress = captured is not None
        if ptype == "ninny" and (tc, tr) in PROMO[owner]:
            ptype = "numskull"
            progress = True
        b[(tc, tr)] = (owner, ptype)
        return SState(
            board=b,
            to_move=1 - state.to_move,
            no_progress=0 if progress else state.no_progress + 1,
            ply=state.ply + 1,
        )

    # ---- terminal (computed lazily from the board) -------------------------
    def _brains(self, board):
        w0 = any(v == (0, "brain") for v in board.values())
        w1 = any(v == (1, "brain") for v in board.values())
        return w0, w1

    def is_terminal(self, state: SState) -> bool:
        b = state.board
        w0, w1 = self._brains(b)
        if not w0 or not w1:            # a Brain has been captured -> decided
            return True
        if len(b) == 2:                 # only the two Brains remain -> draw
            return True
        if state.no_progress >= NOPROG_CAP or state.ply >= PLY_CAP:
            return True
        if not self._raw_moves(state):  # no legal move (deadlock) -> draw
            return True
        return False

    def returns(self, state: SState):
        w0, w1 = self._brains(state.board)
        if w0 and not w1:
            return [1.0, -1.0]          # Blue's Brain captured -> Red wins
        if w1 and not w0:
            return [-1.0, 1.0]
        return [0.0, 0.0]               # two-Brains / cap / deadlock -> draw

    # ---- eval --------------------------------------------------------------
    def heuristic(self, state: SState):
        m = [0, 0]
        for owner, ptype in state.board.values():
            m[owner] += VALUE[ptype]
        v = math.tanh((m[0] - m[1]) / 6.0)
        return [v, -v]

    # ---- persistence -------------------------------------------------------
    def serialize(self, state: SState) -> dict:
        return {
            "board": {f"{c},{r}": [o, p] for (c, r), (o, p) in state.board.items()},
            "to_move": state.to_move,
            "no_progress": state.no_progress,
            "ply": state.ply,
        }

    def deserialize(self, data: dict) -> SState:
        board = {_cell(k): (v[0], v[1]) for k, v in data["board"].items()}
        return SState(
            board=board,
            to_move=data["to_move"],
            no_progress=data.get("no_progress", 0),
            ply=data.get("ply", 0),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state: SState, move: str) -> str:
        frm, to = move.split(">")
        fc, fr = _cell(frm)
        tc, tr = _cell(to)
        p = state.board.get((fc, fr))
        letter = LETTER.get(p[1], "?") if p else "?"
        sep = "x" if state.board.get((tc, tr)) else "-"
        promo = ""
        if p and p[1] == "ninny" and (tc, tr) in PROMO[p[0]]:
            promo = "=S"
        return f"{letter}{_sq(fc, fr)}{sep}{_sq(tc, tr)}{promo}"

    def render(self, state: SState, perspective: Optional[int] = None):
        pieces = []
        for (c, r), (owner, ptype) in state.board.items():
            pc = {"cell": f"{c},{r}", "owner": owner, "label": LETTER[ptype]}
            if ptype == "brain":
                pc["icon"] = "mann"     # falls back to the "B" label if unknown
            pieces.append(pc)
        if self.is_terminal(state):
            ret = self.returns(state)
            if ret[0] > ret[1]:
                cap = f"{NAMES[0]} wins — captured the Brain"
            elif ret[1] > ret[0]:
                cap = f"{NAMES[1]} wins — captured the Brain"
            else:
                cap = "Draw"
        else:
            cap = f"{NAMES[state.to_move]} to move"
        return {
            "board": {"type": "square", "width": W, "height": H, "overlay": OVERLAY},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
