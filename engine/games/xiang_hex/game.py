"""Xiang Hex (L. Lynn Smith, 2008) -- Chinese Chess on a 79-cell elongated hexagon.

The first hexagonal Xiangqi: the palace, the river, the screen-capturing Cannon,
the lame Horse and the river-bound Elephant all transplanted onto a hex grid,
with three of the six hex directions "forward" for a Soldier instead of one.

Board & coordinates
-------------------
Nine VERTICAL files ``a``-``i``; the two outer files are 7 cells long and the
centre file 11 (7, 8, 9, 10, 11, 10, 9, 8, 7 = 79 cells) -- an elongated
hexagon whose six sides are 7, 5, 5, 7, 5, 5.  Every file is numbered from the
Red end: ``a1``-``a7``, ``e1``-``e11``, ``i1``-``i7``.  (This per-file numbering
is the one used by the rules page and by every diagram on it; the Game Courier
preset instead uses a *global* rank 1-11, so its ``a5`` is this ``a1``.)

Cells are axial hex coordinates ``"q,r"`` (cube ``s = -q-r``) with

    q = file index - 4        (a = -4 ... i = +4)
    r = 6 - q - n  for q >= 0,   6 - n  for q < 0     (n = the cell's number)

so the board is exactly ``|q| <= 4``, ``|r| <= 5``, ``|q+r| <= 5`` (79 cells).
Red (seat 0) starts at the bottom and moves in the ``-r`` direction ("north", up
a file); the axial direction tables are byte-identical to ``shafran_chess`` /
``glinski_chess``, and the board is drawn flat-top (``orientation: "flat"``)
because ``q`` IS the printed board's vertical file.

The **river** is the line of five cells ``a4, c5, e6, g5, i4`` (the 4th cell of
the outer files, the 5th of the c/g files, the 6th of the centre file), which is
the horizontal mid-line of the board.  Writing

    D(q, r) = q + 2r          (D = 0 exactly on the river line)

Red's own side is ``D > 0``, Blue's is ``D < 0``, and the five river cells are
``D = 0``.  D never changes along the river direction and drops by 2 for each
step "north", so it is the natural river coordinate.

The **palace** of each player is a radius-1 hexagon of seven cells: Red's is
``{e1, e2, e3, d1, d2, f1, f2}`` centred on ``e2``; Blue's is the 180 deg
rotation ``{e11, e10, e9, d10, d9, f10, f9}`` centred on ``e10``.  (The rules
page: "the first three cells of the center file and the first two cells which
flank".)

Rules implemented -- all seven pieces verified cell-for-cell against Fergus
Duniho's movement diagrams on the rules page AND against the rule-enforcing
GAME code of his Game Courier preset; see rules.md
------------------------------------------------------------------------------
* SOLDIER  one step straight forward while on its own side of the river; on and
  beyond the river also the two other forward orthogonals and the two sideways
  hex-diagonals (5 destinations).  Never promotes, never retreats.
* HORSE    one orthogonal step to a VACANT cell, then one hex-diagonal step
  continuing in the same direction -- 12 destinations, lamed exactly like the
  Xiangqi horse.
* CHARIOT  slides any distance in the 6 orthogonal (edge) directions.
* CANNON   slides like the Chariot when not capturing; captures by leaping
  exactly one screen (of either colour) along one of those 6 lines.
* ELEPHANT two hex-diagonal steps in the same direction (6 destinations); the
  intermediate cell must be vacant, and it may never cross the river.
* MANDARIN one hex-diagonal step, never leaving the palace.  A hex diagonal is
  two cells long, so the palace's seven cells split into TWO disjoint mandarin
  triangles ({d1,f1,e3} and {e1,f2,d2}) plus the unusable centre e2 -- both of
  a player's mandarins start in the same triangle and can never leave it.
* GENERAL  one orthogonal step, never leaving the palace, and never on an
  otherwise-empty file with the enemy General (the "flying general" rule: it is
  implemented as the General attacking the enemy General along the file).

Ending the game (rules page, "Rules")
-------------------------------------
* Checkmate wins.  **Stalemate LOSES** -- so, uniformly, a player with no legal
  move loses.
* **Repetition of position LOSES**: the player whose move recreates a position
  (board + side to move) that has already occurred in the game loses at once.
  This also makes the game provably finite -- see rules.md.
* If NEITHER side still has a piece that can cross the river (no Soldier, Horse,
  Chariot or Cannon anywhere on the board) the game is an honest DRAW.

Move strings: ``"q1,r1>q2,r2"``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1
NAMES = {RED: "Red", BLUE: "Blue"}
FILES = "abcdefghi"

# --- board -----------------------------------------------------------------
QMIN, QMAX = -4, 4
RMIN, RMAX = -5, 5
SMAX = 5                                  # |q + r| <= 5


def on_board(q: int, r: int) -> bool:
    return (QMIN <= q <= QMAX and RMIN <= r <= RMAX and -SMAX <= q + r <= SMAX)


CELLS = tuple(sorted((q, r) for q in range(QMIN, QMAX + 1)
                     for r in range(RMIN, RMAX + 1) if on_board(q, r)))

# --- directions (axial q,r; cube s = -q-r) ---------------------------------
# Orthogonal = through cell EDGES, listed N, NE, SE, S, SW, NW; "N" (0,-1) is
# Red's forward direction (up a file).
ORTHO = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
# Diagonal = through cell VERTICES = the sum of two adjacent orthogonals, in the
# same cyclic order (DIAG[i] = ORTHO[i] + ORTHO[i+1]).  A hex diagonal spans two
# cells, which is why the Elephant/Mandarin behave as they do.
DIAG = [(1, -2), (2, -1), (1, 1), (-1, 2), (-2, 1), (-1, -1)]

# Horse: one orthogonal step then one diagonal step "in the same direction" --
# (step_delta, destination_delta) so the lame-leg cell is explicit.
HORSE = tuple((ORTHO[i], (ORTHO[i][0] + d[0], ORTHO[i][1] + d[1]))
              for i in range(6) for d in (DIAG[i], DIAG[i - 1]))
# Elephant: two diagonal steps in one direction -- (eye_delta, destination).
ELEPHANT = tuple((d, (2 * d[0], 2 * d[1])) for d in DIAG)

# Soldier: (delta, needs_river) per seat.  Red's plain forward is N; the two
# other forward orthogonals (NE, NW) and the two sideways diagonals (E, W) open
# up on and beyond the river.  Blue's set is the exact negation.
SOLDIER = {
    RED:  (((0, -1), False), ((1, -1), True), ((-1, 0), True),
           ((2, -1), True), ((-2, 1), True)),
    BLUE: (((0, 1), False), ((-1, 1), True), ((1, 0), True),
           ((-2, 1), True), ((2, -1), True)),
}

# --- river & palace ---------------------------------------------------------


def river_coord(cell) -> int:
    """D = q + 2r: > 0 on Red's side, 0 on the river line, < 0 on Blue's."""
    return cell[0] + 2 * cell[1]


RIVER = frozenset(c for c in CELLS if river_coord(c) == 0)   # a4 c5 e6 g5 i4


def _crossed(seat: int, cell) -> bool:
    """Is `cell` on or beyond the river, from `seat`'s point of view?"""
    d = river_coord(cell)
    return d <= 0 if seat == RED else d >= 0


def _elephant_ok(seat: int, cell) -> bool:
    """An Elephant may never cross the river (its own side, river included)."""
    d = river_coord(cell)
    return d >= 0 if seat == RED else d <= 0


PALACE_CENTRE = {RED: (0, 4), BLUE: (0, -4)}
PALACE = {p: frozenset([c] + [(c[0] + dq, c[1] + dr) for dq, dr in ORTHO])
          for p, c in PALACE_CENTRE.items()}

# Pieces that are able to cross the river; if neither side has one the game is
# drawn.  Elephant/Mandarin/General are the three that never can.
CROSSERS = frozenset("SHCA")
PIECE_NAMES = {"S": "Soldier", "H": "Horse", "C": "Chariot", "A": "Cannon",
               "E": "Elephant", "M": "Mandarin", "G": "General"}

# Defensive termination backstop only -- a hang guard, not a game rule.
# "Repetition loses" makes a repeated position impossible, so every game is
# finite by construction; this cap is unreachable in practice (longest of 8000
# random games: 1572 plies, and no game came within a factor of 12 of the cap).
# See rules.md; a draw is the honest verdict if it ever did fire.
PLY_CAP = 20000


# --- notation ---------------------------------------------------------------
def cell_name(cell) -> str:
    """Axial (q,r) -> the rules page's per-file notation, e.g. (0,5) -> 'e1'."""
    q, r = cell
    n = (6 - q - r) if q >= 0 else (6 - r)
    return f"{FILES[q - QMIN]}{n}"


def parse_name(name: str):
    """'e1' -> (0, 5).  Inverse of cell_name."""
    q = FILES.index(name[0]) + QMIN
    n = int(name[1:])
    r = (6 - q - n) if q >= 0 else (6 - n)
    return (q, r)


def _cell(sstr: str):
    q, r = sstr.split(",")
    return int(q), int(r)


# --- setup ------------------------------------------------------------------
_RED_ARRAY = {
    "a1": "C", "i1": "C", "b1": "H", "h1": "H", "b2": "A", "h2": "A",
    "c1": "E", "g1": "E", "d1": "M", "f1": "M", "e1": "G",
    "a2": "S", "c3": "S", "e4": "S", "g3": "S", "i2": "S",
}


def _setup_board() -> dict:
    """Red's array plus Blue's exact 180 deg rotation (q,r) -> (-q,-r)."""
    b = {}
    for name, letter in _RED_ARRAY.items():
        q, r = parse_name(name)
        b[(q, r)] = (RED, letter)
        b[(-q, -r)] = (BLUE, letter)
    return b


# --- attack detection -------------------------------------------------------
def _attacked(board: dict, cell, by: int) -> bool:
    """Is `cell` attacked by a piece of player `by`?  (Flying general is handled
    separately in `_in_check` because it is a mutual restriction.)"""
    q, r = cell
    # Soldier -- run its move deltas backwards; the river gate is on the
    # DESTINATION, i.e. on `cell` itself.
    for (dq, dr), gated in SOLDIER[by]:
        if gated and not _crossed(by, cell):
            continue
        if board.get((q - dq, r - dr)) == (by, "S"):
            return True
    # Horse -- the lame leg must be vacant.
    for (sq, sr), (tq, tr) in HORSE:
        oq, or_ = q - tq, r - tr
        if board.get((oq, or_)) == (by, "H"):
            leg = (oq + sq, or_ + sr)
            if on_board(*leg) and leg not in board:
                return True
    # Elephant -- two diagonals, vacant eye, may not cross the river.
    if _elephant_ok(by, cell):
        for (vq, vr), (tq, tr) in ELEPHANT:
            oq, or_ = q - tq, r - tr
            if board.get((oq, or_)) == (by, "E"):
                eye = (oq + vq, or_ + vr)
                if on_board(*eye) and eye not in board:
                    return True
    # Mandarin / General -- both palace-bound, so only palace cells qualify.
    if cell in PALACE[by]:
        for dq, dr in DIAG:
            if board.get((q - dq, r - dr)) == (by, "M"):
                return True
        for dq, dr in ORTHO:
            if board.get((q - dq, r - dr)) == (by, "G"):
                return True
    # Chariot (first piece along a line) and Cannon (second piece along a line).
    for dq, dr in ORTHO:
        cq, cr = q + dq, r + dr
        while on_board(cq, cr) and (cq, cr) not in board:
            cq, cr = cq + dq, cr + dr
        if not on_board(cq, cr):
            continue
        if board[(cq, cr)] == (by, "C"):
            return True
        cq, cr = cq + dq, cr + dr                     # leap that screen
        while on_board(cq, cr) and (cq, cr) not in board:
            cq, cr = cq + dq, cr + dr
        if on_board(cq, cr) and board[(cq, cr)] == (by, "A"):
            return True
    return False


def _general_cell(board: dict, seat: int):
    for cell, (o, t) in board.items():
        if o == seat and t == "G":
            return cell
    return None


def _facing(board: dict) -> bool:
    """Do the two Generals stand on one file with nothing in between?

    The flying-general line is the FILE only.  Red's palace cells all have
    r in {3,4,5} and q+r in {3,4,5}; Blue's have r in {-5,-4,-3} and q+r in
    {-5,-4,-3}; so the SE (constant r) and NE (constant q+r) lines can never
    join the two palaces and only the file (constant q) can.  (selftest)
    """
    g0, g1 = _general_cell(board, RED), _general_cell(board, BLUE)
    if g0 is None or g1 is None or g0[0] != g1[0]:
        return False
    q = g0[0]
    lo, hi = sorted((g0[1], g1[1]))
    return all((q, r) not in board for r in range(lo + 1, hi))


def _in_check(board: dict, seat: int) -> bool:
    g = _general_cell(board, seat)
    if g is None:
        return False
    return _attacked(board, g, 1 - seat) or _facing(board)


# --- state ------------------------------------------------------------------
def _poskey(board: dict, to_move: int) -> str:
    out = [str(to_move)]
    for c in CELLS:
        p = board.get(c)
        out.append("." if p is None else
                   (p[1] if p[0] == RED else p[1].lower()))
    return "".join(out)


@dataclass
class GState:
    board: dict = field(default_factory=_setup_board)
    to_move: int = RED
    ply: int = 0
    # Every position seen since the last irreversible move, current one LAST.
    hist: tuple = ()
    last: Optional[tuple] = None            # (from, to) for highlighting


class XiangHex(Game):

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> GState:
        s = GState()
        s.hist = (_poskey(s.board, s.to_move),)
        return s

    def current_player(self, s: GState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def _pseudo(self, board: dict, me: int) -> list:
        out = []
        add = out.append
        for (q, r), (owner, t) in board.items():
            if owner != me:
                continue
            if t == "S":
                for (dq, dr), gated in SOLDIER[me]:
                    tgt = (q + dq, r + dr)
                    if not on_board(*tgt):
                        continue
                    if gated and not _crossed(me, tgt):
                        continue
                    occ = board.get(tgt)
                    if occ is None or occ[0] != me:
                        add(((q, r), tgt))
            elif t == "H":
                for (sq, sr), (tq, tr) in HORSE:
                    leg = (q + sq, r + sr)
                    if not on_board(*leg) or leg in board:
                        continue            # the horse's leg is hobbled
                    tgt = (q + tq, r + tr)
                    if not on_board(*tgt):
                        continue
                    occ = board.get(tgt)
                    if occ is None or occ[0] != me:
                        add(((q, r), tgt))
            elif t == "E":
                for (vq, vr), (tq, tr) in ELEPHANT:
                    eye = (q + vq, r + vr)
                    if not on_board(*eye) or eye in board:
                        continue            # the elephant's eye is blocked
                    tgt = (q + tq, r + tr)
                    if not on_board(*tgt) or not _elephant_ok(me, tgt):
                        continue
                    occ = board.get(tgt)
                    if occ is None or occ[0] != me:
                        add(((q, r), tgt))
            elif t == "M":
                for dq, dr in DIAG:
                    tgt = (q + dq, r + dr)
                    if tgt not in PALACE[me]:
                        continue
                    occ = board.get(tgt)
                    if occ is None or occ[0] != me:
                        add(((q, r), tgt))
            elif t == "G":
                for dq, dr in ORTHO:
                    tgt = (q + dq, r + dr)
                    if tgt not in PALACE[me]:
                        continue
                    occ = board.get(tgt)
                    if occ is None or occ[0] != me:
                        add(((q, r), tgt))
                # "Flying general": capturing the enemy General down an empty
                # file, exactly as the preset's `def g` admits.  It is NOT what
                # makes facing illegal -- `_in_check` calls `_facing` directly,
                # so a facing position is check for BOTH sides however this move
                # is generated -- and it is unreachable in play, because a
                # facing position could only follow a move that was itself
                # illegal.  It is emitted purely so the move list matches the
                # Game Courier oracle cell-for-cell even in such a position.
                foe = _general_cell(board, 1 - me)
                if foe is not None and foe[0] == q:
                    lo, hi = sorted((r, foe[1]))
                    if all((q, rr) not in board for rr in range(lo + 1, hi)):
                        add(((q, r), foe))
            else:                                    # C = Chariot, A = Cannon
                for dq, dr in ORTHO:
                    cq, cr = q + dq, r + dr
                    while on_board(cq, cr) and (cq, cr) not in board:
                        add(((q, r), (cq, cr)))      # quiet slide (both)
                        cq, cr = cq + dq, cr + dr
                    if not on_board(cq, cr):
                        continue
                    if t == "C":
                        if board[(cq, cr)][0] != me:
                            add(((q, r), (cq, cr)))  # chariot takes the first
                        continue
                    cq, cr = cq + dq, cr + dr        # cannon leaps that screen
                    while on_board(cq, cr) and (cq, cr) not in board:
                        cq, cr = cq + dq, cr + dr
                    if on_board(cq, cr) and board[(cq, cr)][0] != me:
                        add(((q, r), (cq, cr)))
        return out

    def _legal(self, s: GState) -> list:
        cached = getattr(s, "_legal_cache", None)
        if cached is not None:
            return cached
        me = s.to_move
        out = []
        for frm, to in self._pseudo(s.board, me):
            nb = dict(s.board)
            nb[to] = nb.pop(frm)
            if not _in_check(nb, me):
                out.append((frm, to))
        out.sort()
        object.__setattr__(s, "_legal_cache", out)
        return out

    # ---- endings -----------------------------------------------------------
    def _over(self, s: GState):
        """Non-move-based endings: (reason, winner or None) or None."""
        if len(s.hist) >= 2 and s.hist[-1] in s.hist[:-1]:
            # The player who just moved (1 - to_move) recreated an earlier
            # position and LOSES, so the winner is the player to move.
            return ("repetition", s.to_move)
        if not any(t in CROSSERS for (_o, t) in s.board.values()):
            return ("no river-crossers", None)
        if s.ply >= PLY_CAP:
            return ("move limit", None)
        return None

    # ---- Game interface ----------------------------------------------------
    def legal_moves(self, s: GState) -> list:
        if self._over(s) is not None:
            return []
        return [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for f, t in self._legal(s)]

    def apply_move(self, s: GState, move: str, rng=None) -> GState:
        frm_s, to_s = move.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        if self._over(s) is not None or (frm, to) not in self._legal(s):
            raise ValueError(f"illegal move {move!r}")
        me = s.to_move
        letter = s.board[frm][1]
        capture = to in s.board
        nb = dict(s.board)
        nb[to] = nb.pop(frm)
        # A position can only recur while material and every Soldier's river
        # coordinate are unchanged: D never increases for a Red Soldier nor
        # decreases for a Blue one, so any Soldier move that changes D -- and
        # any capture -- is irreversible and clears the history.
        soldier_progress = letter == "S" and river_coord(to) != river_coord(frm)
        hist = () if (capture or soldier_progress) else s.hist
        return GState(board=nb, to_move=1 - me, ply=s.ply + 1,
                      hist=hist + (_poskey(nb, 1 - me),), last=(frm, to))

    def is_terminal(self, s: GState) -> bool:
        return self._over(s) is not None or not self._legal(s)

    def returns(self, s: GState) -> list:
        # No legal move = checkmate OR stalemate, and BOTH lose; that is
        # decisive and takes precedence over the drawing conditions.
        if not self._legal(s):
            return [-1.0, 1.0] if s.to_move == RED else [1.0, -1.0]
        over = self._over(s)
        if over is not None and over[1] is not None:
            return [1.0, -1.0] if over[1] == RED else [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: GState) -> dict:
        return {
            "board": {f"{q},{r}": [o, t] for (q, r), (o, t) in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "hist": list(s.hist),
            "last": ([f"{s.last[0][0]},{s.last[0][1]}",
                      f"{s.last[1][0]},{s.last[1][1]}"] if s.last else None),
        }

    def deserialize(self, d: dict) -> GState:
        last = d.get("last")
        board = {_cell(k): (v[0], v[1]) for k, v in d["board"].items()}
        hist = tuple(d.get("hist") or ())
        if not hist:
            hist = (_poskey(board, d["to_move"]),)
        return GState(board=board, to_move=d["to_move"], ply=d.get("ply", 0),
                      hist=hist,
                      last=(_cell(last[0]), _cell(last[1])) if last else None)

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s: GState, move: str) -> str:
        frm_s, to_s = move.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        piece = s.board.get(frm)
        letter = piece[1] if piece else ""
        sep = "x" if to in s.board else "-"
        out = f"{letter}{cell_name(frm)}{sep}{cell_name(to)}"
        if piece is not None:
            nb = dict(s.board)
            nb[to] = nb.pop(frm)
            if _in_check(nb, 1 - piece[0]):
                out += "+"
        return out

    def render(self, s: GState, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": o, "label": t}
                  for (q, r), (o, t) in s.board.items()]
        highlights = [{"cell": f"{c[0]},{c[1]}", "kind": "last-move"}
                      for c in (s.last or ())]
        # The three hex colours, then the palaces (gold) and the river (blue)
        # painted over them, exactly as the rules page's board is coloured.
        shades = {0: "#e8ab6f", 1: "#ffce9e", 2: "#d18b47"}
        tints = {f"{q},{r}": shades[(q - r) % 3] for q, r in CELLS}
        for seat in (RED, BLUE):
            for q, r in PALACE[seat]:
                tints[f"{q},{r}"] = "#e8c86a"
        for q, r in RIVER:
            tints[f"{q},{r}"] = "#b8d9ea"
        # The river as a line right across the board, and the two mandarin
        # triangles inside each palace (the hex analogue of Xiangqi's palace
        # cross -- a Mandarin really does walk only those triangles).
        overlay = [[[-14.0 / 3, 7.0 / 3], [14.0 / 3, -7.0 / 3], "#3f7fb0"]]
        for seat in (RED, BLUE):
            cq, cr = PALACE_CENTRE[seat]
            for start in (0, 1):
                tri = [(cq + ORTHO[i][0], cr + ORTHO[i][1])
                       for i in (start, start + 2, start + 4)]
                overlay.append([[float(a), float(b)] for a, b in tri + tri[:1]]
                               + ["#b08a3f"])
        over = self._over(s)
        if not self._legal(s):
            why = "checkmate" if _in_check(s.board, s.to_move) else "stalemate"
            caption = f"{NAMES[1 - s.to_move]} wins ({why})"
        elif over is not None:
            caption = (f"Draw ({over[0]})" if over[1] is None
                       else f"{NAMES[over[1]]} wins ({over[0]})")
        else:
            check = " (check)" if _in_check(s.board, s.to_move) else ""
            caption = f"{NAMES[s.to_move]} to move{check}"
        return {
            "board": {"type": "hex",
                      "cells": [f"{q},{r}" for q, r in CELLS],
                      # q IS the printed board's file and the files are drawn
                      # VERTICAL, so the hexes are flat-top (see SPEC.md).
                      "orientation": "flat",
                      "tints": tints,
                      "overlay": overlay},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }

    # ---- bot eval ----------------------------------------------------------
    VALUES = {"S": 1.0, "H": 4.0, "C": 9.0, "A": 4.5,
              "E": 2.0, "M": 2.0, "G": 0.0}

    def heuristic(self, s: GState) -> list:
        import math
        bal = 0.0
        for cell, (o, t) in s.board.items():
            v = self.VALUES[t]
            if t == "S" and _crossed(o, cell):
                v = 2.0                      # a Soldier past the river is worth more
            bal += v if o == RED else -v
        v = math.tanh(bal / 8.0)
        return [v, -v]
