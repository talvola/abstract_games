"""PÜNCT — Kris Burm, 2005 (GIPF project game #6).

A CONNECTION game with STACKING. Each player has 18 flat pieces, every piece
covering THREE adjacent hexagonal fields. One of a piece's three dots is the
coloured *PÜNCT*; the other two are *minor dots*. On a turn you either ADD a new
piece flat on three empty fields, or MOVE one of your pieces — sliding its PÜNCT
in a straight line and optionally rotating it, possibly jumping on top of other
pieces. The colour showing on TOP of a field is what counts. You win by linking
any one pair of opposite sides of the hexagonal board with a contiguous chain of
fields your colour tops (Hex-style BFS over "visible from above").

See rules.md for the verified board, the exact piece shapes/counts, the
placement + stacking/support/bridging rule, and the connection win — plus the
ruleset choices made here (the PÜNCT-piece, the standard-rules central-hexagon
restriction and central-control tie-break are documented as out of scope of this
BASE implementation, and a no-progress ply cap guarantees termination).

Coordinates are axial cube hexes ``q,r`` (s = -q-r). The board is a regular
hexagon of side 9 with the 6 single corner fields clipped → 211 fields.

Rendering: there is no multi-cell-piece primitive, so we render PER FIELD — each
covered field emits a disc in the TOP piece's owner colour (a 3-field piece thus
shows as 3 adjacent same-colour discs) and carries a height label when stacked.
A shape-overlay primitive (drawing the three-field triomino outline) would make
piece identity clearer; flagged for review.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}

# The six axial neighbour directions (q, r).
DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]

RADIUS = 8          # side-9 hexagon -> max(|q|,|r|,|s|) <= 8
PLY_CAP = 200       # hard draw cap (termination guarantee); see rules.md


# --------------------------------------------------------------------------- #
# Board geometry
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=None)
def board_cells() -> frozenset:
    """The 211 on-board fields: a side-9 hexagon minus its 6 corner fields."""
    cells = set()
    for q in range(-RADIUS, RADIUS + 1):
        for r in range(-RADIUS, RADIUS + 1):
            s = -q - r
            if max(abs(q), abs(r), abs(s)) > RADIUS:
                continue
            # A corner field is one where two of |q|,|r|,|s| equal RADIUS.
            if sum(1 for v in (q, r, s) if abs(v) == RADIUS) >= 2:
                continue
            cells.add((q, r))
    return frozenset(cells)


def on_board(c) -> bool:
    return c in board_cells()


@lru_cache(maxsize=None)
def _central_set() -> frozenset:
    """The central hexagon: the centre field plus its six neighbours."""
    return frozenset({(0, 0)} | set(neighbors((0, 0))))


def neighbors(c):
    q, r = c
    return [(q + dq, r + dr) for dq, dr in DIRS]


# The hexagon has six edges; opposite edges are paired by the three cube axes.
# Edge "+q" = fields with q == RADIUS (after clipping, q can reach 8 on a full
# row), etc. A field belongs to an edge if its corresponding coord == ±RADIUS.
def edge_of(c, axis: int, sign: int) -> bool:
    q, r = c
    s = -q - r
    val = (q, r, s)[axis]
    return val == sign * RADIUS


# Three pairs of opposite sides (cube axes q, r, s). A player wins by connecting
# ANY one pair.
AXES = [0, 1, 2]


# --------------------------------------------------------------------------- #
# Piece shapes — the three PÜNCT triominoes, anchored at the PÜNCT.
# Each orientation is described by the two OFFSETS of the minor dots relative to
# the PÜNCT field. Because a physical piece's PÜNCT may be centred OR at an end,
# we enumerate the PÜNCT at every position of the triomino: 9 straight, 18
# angular and 6 triangular oriented placements. Anchoring the move generator at
# the PÜNCT then covers every (shape, PÜNCT-position, rotation) a physical piece
# can take — and the end-anchored straight/angular orientations are exactly what
# make BRIDGING (an unsupported MIDDLE minor) possible.
# --------------------------------------------------------------------------- #
_DIRSET = set(DIRS)


def _classify(c0, c1, c2):
    """Classify a triomino {c0,c1,c2} and return (kind, middle_field).

    The *middle* is the field adjacent to BOTH others. straight/angular pieces
    have a clear middle (and 2 ends); a triangular piece is mutually adjacent
    (no unique middle → middle is None). kind ∈ {straight, angular, triangular}.
    """
    cells = (c0, c1, c2)
    # triangular: every cell adjacent to both others (a tight triangle).
    def adj(x, y):
        return (y[0] - x[0], y[1] - x[1]) in _DIRSET
    if adj(c0, c1) and adj(c0, c2) and adj(c1, c2):
        return "triangular", None
    # otherwise find the unique field adjacent to both others = the middle.
    for i in range(3):
        mid = cells[i]
        ends = [cells[j] for j in range(3) if j != i]
        if adj(mid, ends[0]) and adj(mid, ends[1]):
            # straight iff the two ends are collinear through the middle.
            e0, e1 = ends
            if (e0[0] + e1[0] == 2 * mid[0]) and (e0[1] + e1[1] == 2 * mid[1]):
                return "straight", mid
            return "angular", mid
    return "angular", None  # unreachable for a connected triomino


@lru_cache(maxsize=None)
def shape_offsets():
    """Return {'straight':[...], 'angular':[...], 'triangular':[...]} where each
    entry is a tuple (minor_a, minor_b) of axial offsets from the PÜNCT.

    The PÜNCT may sit at ANY of a triomino's three positions (physical pieces
    are made with the coloured dot centred or at an end), so straight/angular
    shapes appear both middle-anchored and end-anchored — an end-anchored
    straight has a minor two steps away. This full enumeration is what makes
    bridging (an unsupported MIDDLE minor) possible.
    """
    straight, angular, triangular = [], [], []
    # candidate offsets: every cell within axial distance 2 of the PÜNCT.
    cand = set()
    for d in DIRS:
        cand.add(d)
        for e in DIRS:
            cand.add((d[0] + e[0], d[1] + e[1]))
    cand.discard((0, 0))
    cand = sorted(cand)
    seen = set()
    O = (0, 0)
    for ai in range(len(cand)):
        for bi in range(ai + 1, len(cand)):
            a, b = cand[ai], cand[bi]
            if not _connected3(O, a, b):
                continue
            kind, _mid = _classify(O, a, b)
            key = (kind, frozenset((a, b)))
            if key in seen:
                continue
            seen.add(key)
            (straight if kind == "straight"
             else triangular if kind == "triangular" else angular).append((a, b))
    return {"straight": straight, "angular": angular, "triangular": triangular}


def _connected3(c0, c1, c2):
    cells = {c0, c1, c2}
    seen = {c0}
    stack = [c0]
    while stack:
        x = stack.pop()
        for d in DIRS:
            n = (x[0] + d[0], x[1] + d[1])
            if n in cells and n not in seen:
                seen.add(n)
                stack.append(n)
    return seen == cells


@lru_cache(maxsize=None)
def all_placements():
    """Every geometrically on-board (punct, (a, b)) triomino placement, as a
    tuple ((punct, a, b), kind, move_string). Precomputed once."""
    cells = board_cells()
    forms = shape_offsets()
    out = []
    for kind in ("straight", "angular", "triangular"):
        for (ma, mb) in forms[kind]:
            for punct in cells:
                a = (punct[0] + ma[0], punct[1] + ma[1])
                b = (punct[0] + mb[0], punct[1] + mb[1])
                if a in cells and b in cells:
                    out.append(((punct, a, b), kind, add_move(punct, (a, b))))
    return tuple(out)


def shape_of(minor_a, minor_b) -> str:
    """Shape of a piece whose PÜNCT is at the origin and minors at the offsets."""
    kind, _ = _classify((0, 0), minor_a, minor_b)
    return kind


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
@dataclass
class Piece:
    owner: int
    punct: tuple            # (q, r) of the PÜNCT (the coloured dot)
    minors: tuple           # ((q,r),(q,r)) of the two minor dots
    level: int              # 0 = flat on the board; >0 = stacked height

    def cells(self):
        return (self.punct,) + tuple(self.minors)

    def shape(self) -> str:
        ma = (self.minors[0][0] - self.punct[0], self.minors[0][1] - self.punct[1])
        mb = (self.minors[1][0] - self.punct[0], self.minors[1][1] - self.punct[1])
        return shape_of(ma, mb)


@dataclass
class PunctState:
    pieces: list = field(default_factory=list)   # all physical Piece objects
    reserve: tuple = (18, 18)                     # pieces left to add per seat
    to_move: int = WHITE
    winner: Optional[int] = None
    ply: int = 0


# --------------------------------------------------------------------------- #
# Stack model derived from the piece list
# --------------------------------------------------------------------------- #
def field_stacks(pieces):
    """field -> ordered list of (level, piece_index) covering it, bottom→top."""
    stacks = {}
    for idx, p in enumerate(pieces):
        for c in p.cells():
            stacks.setdefault(c, []).append((p.level, idx))
    for c in stacks:
        stacks[c].sort()
    return stacks


def top_owner(pieces, stacks=None):
    """field -> owner of the topmost piece (what counts for connection)."""
    if stacks is None:
        stacks = field_stacks(pieces)
    out = {}
    for c, lst in stacks.items():
        out[c] = pieces[lst[-1][1]].owner
    return out


def height_at(stacks, c) -> int:
    """How many pieces currently cover field c (its top level + 1, or 0)."""
    return len(stacks.get(c, []))


def piece_immobile(pieces, idx, stacks) -> bool:
    """A piece is immobile if any of its dots is covered by a higher piece."""
    p = pieces[idx]
    for c in p.cells():
        lst = stacks.get(c, [])
        # find this piece's level in the stack; if anything sits above it here,
        # the dot is covered -> the piece is blocked.
        for lvl, j in lst:
            if j == idx:
                if lvl < lst[-1][0]:
                    return True
                break
    return False


# --------------------------------------------------------------------------- #
# Connection (Hex-style BFS over top-colour, "visible from above")
# --------------------------------------------------------------------------- #
def connects(top, player: int) -> Optional[int]:
    """Return the axis index (0/1/2) on which `player` links a pair of opposite
    sides, else None. Adjacency ignores level (visible-from-above)."""
    owned = {c for c, o in top.items() if o == player}
    for axis in AXES:
        starts = [c for c in owned if edge_of(c, axis, +1)]
        if not starts:
            continue
        seen = set(starts)
        stack = list(starts)
        ok = False
        while stack:
            cur = stack.pop()
            if edge_of(cur, axis, -1):
                ok = True
                break
            for nb in neighbors(cur):
                if nb in owned and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        if ok:
            return axis
    return None


# --------------------------------------------------------------------------- #
# Move notation
#   ADD  :  "Pq,r>Aq,r>Bq,r"          (PÜNCT field, then the two minor fields)
#   MOVE :  "q0,r0>Pq,r>Aq,r>Bq,r"    (source PÜNCT field, then the new
#                                       PÜNCT/minor fields it lands on)
# All three covered fields are listed explicitly so the move is fully clickable
# as a >-separated cell path. The leading token is tagged 'P'/'A'/'B' (or a bare
# source cell for the move's origin) so parsing is unambiguous and the order of
# the dots — i.e. the orientation / which field is the PÜNCT — is preserved.
# --------------------------------------------------------------------------- #
def _c(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def _fmt_cell(c) -> str:
    return f"{c[0]},{c[1]}"


def add_move(punct, minors) -> str:
    return ">".join(["P" + _fmt_cell(punct)]
                    + ["A" + _fmt_cell(minors[0]), "B" + _fmt_cell(minors[1])])


def move_move(src_punct, punct, minors) -> str:
    return ">".join([_fmt_cell(src_punct), "P" + _fmt_cell(punct),
                     "A" + _fmt_cell(minors[0]), "B" + _fmt_cell(minors[1])])


def parse(move: str):
    parts = move.split(">")
    if parts[0].startswith("P"):
        punct = _c(parts[0][1:])
        a = _c(parts[1][1:])
        b = _c(parts[2][1:])
        return ("add", None, punct, (a, b))
    src = _c(parts[0])
    punct = _c(parts[1][1:])
    a = _c(parts[2][1:])
    b = _c(parts[3][1:])
    return ("move", src, punct, (a, b))


# --------------------------------------------------------------------------- #
# Game
# --------------------------------------------------------------------------- #
class Punct(Game):
    uid = "punct"
    name = "PÜNCT"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> PunctState:
        return PunctState()

    def current_player(self, s: PunctState) -> int:
        return s.to_move

    # ---- placement / movement legality helpers --------------------------- #
    def _central(self):
        """The central hexagon (centre + its 6 neighbours = 7 fields)."""
        return _central_set()

    def _add_moves(self, s: PunctState, stacks):
        """Every legal flat placement on three empty fields."""
        out = []
        occupied = stacks  # field -> stack list; presence means non-empty
        central = self._central()
        # BASE rule: only the FIRST player's FIRST piece may not touch the centre.
        restrict_centre = (s.ply == 0 and s.to_move == WHITE)
        for cells, _kind, mv in all_placements():
            p0, a, b = cells
            if p0 in occupied or a in occupied or b in occupied:
                continue
            if restrict_centre and (p0 in central or a in central or b in central):
                continue
            out.append(mv)
        return out

    def _move_moves(self, s: PunctState, stacks):
        """Every legal move of one of the mover's (mobile) pieces."""
        out = []
        owner = s.to_move
        for idx, p in enumerate(s.pieces):
            if p.owner != owner:
                continue
            if piece_immobile(s.pieces, idx, stacks):
                continue
            out.extend(self._moves_for_piece(s, stacks, idx))
        return out

    def _moves_for_piece(self, s, stacks, idx):
        p = s.pieces[idx]
        out = []
        # Build the stacks as they'd look with this piece LIFTED off the board.
        lifted = self._stacks_without(s.pieces, idx, stacks)
        cells_set = board_cells()
        kind = p.shape()                       # a physical piece keeps its shape
        orientations = shape_offsets()[kind]
        src = p.punct
        sq, sr = src
        # The PÜNCT slides in a straight line over any number of fields, in any
        # of the 6 directions, then the piece may be rotated about the PÜNCT.
        for dq, dr in DIRS:
            step = 1
            while True:
                dest = (sq + dq * step, sr + dr * step)
                if dest not in cells_set:
                    break
                dq0, dr0 = dest
                for (ma, mb) in orientations:
                    a = (dq0 + ma[0], dr0 + ma[1])
                    if a not in cells_set:
                        continue
                    b = (dq0 + mb[0], dr0 + mb[1])
                    if b not in cells_set:
                        continue
                    if self._landing_ok(s, lifted, p, dest, (a, b), kind):
                        out.append(move_move(src, dest, (a, b)))
                step += 1
        return out

    def _stacks_without(self, pieces, idx, stacks):
        lifted = {}
        for c, lst in stacks.items():
            kept = [(lvl, j) for (lvl, j) in lst if j != idx]
            if kept:
                lifted[c] = kept
        return lifted

    def _landing_ok(self, s, lifted, p, punct, minors, kind):
        """Is landing `p` (now `kind`) with its PÜNCT at `punct` and minors at
        `minors` legal, given the board `lifted` (this piece removed)?"""
        ma, mb = minors
        hp = len(lifted.get(punct, ()))
        ha = len(lifted.get(ma, ()))
        hb = len(lifted.get(mb, ()))
        new_level = hp

        if new_level == 0:
            # Sliding flat: all three fields must be empty (a flat piece can
            # slide/rotate across empty ground but cannot overlap anything).
            return ha == 0 and hb == 0

        # Stacking. The PÜNCT must land ON one of the mover's OWN pieces, i.e.
        # the field it lands on must currently be topped by the mover.
        ptop = lifted.get(punct)
        if not ptop or s.pieces[ptop[-1][1]].owner != p.owner:
            return False

        # Each minor dot must be supported at new_level (a piece directly below)
        # OR be the bridged middle dot of a straight/angular piece. The bridged
        # dot must hang over a GAP (strictly lower than new_level).
        bridged = self._bridged_middle(kind, punct, minors)
        if ma == bridged:
            if ha >= new_level:
                return False
        elif ha != new_level:
            return False
        if mb == bridged:
            if hb >= new_level:
                return False
        elif hb != new_level:
            return False
        return True

    def _bridged_middle(self, kind, punct, minors):
        """For a straight/angular piece used as a bridge, return the field of
        the unsupported MIDDLE dot, else None. The middle dot is the one whose
        field lies BETWEEN the two ends; for these shapes the PÜNCT or a minor
        can be the middle. We only allow bridging when the middle is a minor dot
        (the PÜNCT must always be supported, since it must land on a piece)."""
        if kind == "triangular":
            return None
        a, b = minors
        _kind, mid = _classify(punct, a, b)
        if mid is None or mid == punct:
            return None  # PÜNCT is the middle → can't bridge (must land on a piece)
        return mid

    # ---- public API ------------------------------------------------------ #
    def legal_moves(self, s: PunctState) -> list[str]:
        if s.winner is not None or s.ply >= PLY_CAP:
            return []
        stacks = field_stacks(s.pieces)
        moves = []
        if s.reserve[s.to_move] > 0:
            moves.extend(self._add_moves(s, stacks))
        moves.extend(self._move_moves(s, stacks))
        # A player with no legal action passes (advance the turn).
        if not moves:
            moves = ["pass"]
        return moves

    def apply_move(self, s: PunctState, move: str, rng=None) -> PunctState:
        if move == "pass":
            return PunctState(pieces=list(s.pieces), reserve=s.reserve,
                              to_move=1 - s.to_move, winner=s.winner,
                              ply=s.ply + 1)
        kind, src, punct, minors = parse(move)
        pieces = list(s.pieces)
        reserve = list(s.reserve)
        owner = s.to_move
        if kind == "add":
            level = 0
            pieces.append(Piece(owner, punct, minors, level))
            reserve[owner] -= 1
        else:
            stacks = field_stacks(s.pieces)
            # locate the moving piece by its current PÜNCT field + owner + top
            idx = self._find_piece(s.pieces, stacks, owner, src)
            lifted = self._stacks_without(s.pieces, idx, stacks)
            level = len(lifted.get(punct, []))
            pieces[idx] = Piece(owner, punct, minors, level)
        new_state = PunctState(pieces=pieces, reserve=tuple(reserve),
                               to_move=1 - owner, winner=None, ply=s.ply + 1)
        # Check connection for the player who just moved (and, defensively, both).
        top = top_owner(new_state.pieces)
        if connects(top, owner) is not None:
            new_state.winner = owner
        elif connects(top, 1 - owner) is not None:
            new_state.winner = 1 - owner
        return new_state

    def _find_piece(self, pieces, stacks, owner, src):
        """Find the mover's piece whose PÜNCT is at field `src` and is on top
        there (the clickable, movable one)."""
        for idx, p in enumerate(pieces):
            if p.owner == owner and p.punct == src:
                lst = stacks.get(src, [])
                if lst and lst[-1][1] == idx:
                    return idx
        # fallback: any of the mover's pieces with that PÜNCT
        for idx, p in enumerate(pieces):
            if p.owner == owner and p.punct == src:
                return idx
        raise ValueError(f"no movable piece with PÜNCT at {src}")

    def is_terminal(self, s: PunctState) -> bool:
        return s.winner is not None or s.ply >= PLY_CAP

    def returns(self, s: PunctState) -> list[float]:
        if s.winner == WHITE:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # ply-cap draw

    # ---- serialization --------------------------------------------------- #
    def serialize(self, s: PunctState) -> dict:
        return {
            "pieces": [
                {
                    "owner": p.owner,
                    "punct": _fmt_cell(p.punct),
                    "minors": [_fmt_cell(p.minors[0]), _fmt_cell(p.minors[1])],
                    "level": p.level,
                }
                for p in s.pieces
            ],
            "reserve": list(s.reserve),
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> PunctState:
        pieces = [
            Piece(
                owner=pd["owner"],
                punct=_c(pd["punct"]),
                minors=(_c(pd["minors"][0]), _c(pd["minors"][1])),
                level=pd["level"],
            )
            for pd in d["pieces"]
        ]
        return PunctState(
            pieces=pieces,
            reserve=tuple(d["reserve"]),
            to_move=d["to_move"],
            winner=d["winner"],
            ply=d.get("ply", 0),
        )

    # ---- move log -------------------------------------------------------- #
    def describe_move(self, s: PunctState, move: str) -> str:
        if move == "pass":
            return "pass"
        kind, src, punct, minors = parse(move)
        if kind == "add":
            return f"add {_fmt_cell(punct)} ({_fmt_cell(minors[0])},{_fmt_cell(minors[1])})"
        return f"move {_fmt_cell(src)}→{_fmt_cell(punct)}"

    # ---- rendering ------------------------------------------------------- #
    def render(self, s: PunctState, perspective=None) -> dict:
        stacks = field_stacks(s.pieces)
        top = top_owner(s.pieces, stacks)

        # polygon board: emit every on-board field as a hex cell.
        SQRT3 = math.sqrt(3)

        def hexpoly(q, r):
            cx = SQRT3 * (q + r / 2)
            cy = 1.5 * r
            pts = []
            for k in range(6):
                ang = math.radians(60 * k - 30)
                pts.append([round(cx + math.cos(ang), 4),
                            round(cy + math.sin(ang), 4)])
            return pts

        cells = [{"id": _fmt_cell(c), "points": hexpoly(*c)} for c in sorted(board_cells())]

        pieces = []
        for c, owner in top.items():
            h = height_at(stacks, c)
            piece = {"cell": _fmt_cell(c), "owner": owner}
            if h > 1:
                piece["label"] = str(h)        # stack height glyph
            pieces.append(piece)

        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins (connection)"
        elif s.ply >= PLY_CAP:
            caption = "Draw (move cap)"
        else:
            caption = (f"{NAMES[s.to_move]} to move "
                       f"(reserve {s.reserve[s.to_move]})")

        return {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
