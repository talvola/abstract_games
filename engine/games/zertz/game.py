"""ZERTZ (Kris Burm, GIPF project #2) -- the shrinking-board game.

The board is a hexagon of 37 rings (hexhex, four rings to a side). Both players
draw from ONE shared pool of neutral marbles: 6 white, 8 grey, 10 black. Marbles
are NOT owned by a player; you score by *capturing* them into your own reserve.

Each turn is one of two kinds:

  PLACEMENT -- put a marble of any colour from the pool onto any vacant ring,
  THEN remove one "free" ring (a vacant ring at the edge that can be slid off
  without disturbing the others). Modelled as a two-step turn: the place move is
  "W@q,r" / "G@q,r" / "B@q,r"; the engine then keeps the turn with the same
  player to pick the ring to remove, "x q,r". If no ring is free, the removal
  step is skipped automatically.

  CAPTURE -- a marble jumps an orthogonally-adjacent marble of ANY colour (one of
  the 6 hex directions) to the vacant ring immediately beyond; the jumped marble
  is removed and added to the MOVING player's reserve. Captures are MANDATORY
  (if any jump exists you must jump, you may not place) and CHAIN (you keep
  jumping with the same marble while a jump remains; you choose the path). A
  capture move is the jumping marble's path of cell ids, e.g. "q,r>q2,r2>...".

ISOLATION -- if removing a ring cuts a group of rings completely off from the
rest of the board AND every ring in that group carries a marble, those marbles
are captured by the player who just moved and the rings are removed.

WIN -- the first player whose captured reserve contains a winning set wins:
3 white + 3 grey + 3 black, OR 4 white, OR 5 grey, OR 6 black. If the pool and
board are exhausted with nobody at a winning set the game is a draw (with a
defensive ply cap).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

# --- board geometry: hexhex side 4 (37 rings), axial (q, r) ----------------
RADIUS = 3  # max(|q|, |r|, |q+r|) <= 3  ->  37 cells
ALL_RINGS = frozenset(
    (q, r)
    for q in range(-RADIUS, RADIUS + 1)
    for r in range(-RADIUS, RADIUS + 1)
    if max(abs(q), abs(r), abs(q + r)) <= RADIUS
)
assert len(ALL_RINGS) == 37

# the 6 axial hex directions (consecutive around the cell)
DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]

# marble pool: colour -> count
POOL = {"W": 6, "G": 8, "B": 10}
COLOURS = ("W", "G", "B")

# winning sets
WIN_SINGLE = {"W": 4, "G": 5, "B": 6}
WIN_TRIPLE = 3  # 3 of every colour


# Pointy-top hex pixel layout matching the web renderer (R=30, axial->pixel:
# x = SQRT3*(q + r/2)*R, y = 1.5*r*R; vertices at 60*i-30 degrees).
HEX_R = 30.0
_SQRT3 = math.sqrt(3.0)


def _hex_center(q, r):
    return (_SQRT3 * (q + r / 2.0) * HEX_R, 1.5 * r * HEX_R)


def _hex_poly(q, r):
    cx, cy = _hex_center(q, r)
    pts = []
    for i in range(6):
        a = math.radians(60 * i - 30)
        pts.append([round(cx + HEX_R * math.cos(a), 3),
                    round(cy + HEX_R * math.sin(a), 3)])
    return pts


def _cid(c):
    return f"{c[0]},{c[1]}"


def _cell(s):
    q, r = s.split(",")
    return (int(q), int(r))


@dataclass
class ZState:
    rings: frozenset = ALL_RINGS         # rings still on the board
    marbles: dict = field(default_factory=dict)   # cell -> colour ("W"/"G"/"B")
    pool: dict = field(default_factory=lambda: dict(POOL))  # shared supply
    reserve: list = field(default_factory=lambda: [{"W": 0, "G": 0, "B": 0},
                                                   {"W": 0, "G": 0, "B": 0}])
    to_move: int = 0
    # two-step placement: after placing a marble we keep the turn to remove a ring
    pending_removal: bool = False
    # the marble currently mid-capture-chain (cell id) or None
    chain_from: object = None
    winner: object = None
    plies: int = 0


class Zertz(Game):
    uid = "zertz"
    name = "ZERTZ"
    PLY_CAP = 400  # defensive: nobody can win -> draw

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        return ZState()

    def current_player(self, state):
        return state.to_move

    # ---- adjacency / capture helpers --------------------------------------
    def _neighbours(self, cell):
        return [(cell[0] + d[0], cell[1] + d[1]) for d in DIRS]

    def _jumps_from(self, state, cell):
        """All single jumps available from a marble at `cell`."""
        out = []
        if cell not in state.marbles:
            return out
        for d in DIRS:
            over = (cell[0] + d[0], cell[1] + d[1])
            land = (cell[0] + 2 * d[0], cell[1] + 2 * d[1])
            if over in state.marbles and land in state.rings and land not in state.marbles:
                out.append((over, land))
        return out

    def _any_capture(self, state):
        return any(self._jumps_from(state, c) for c in state.marbles)

    def _free_rings(self, state):
        """A ring is free iff it is vacant AND it can be slid off the edge --
        i.e. it has two CONSECUTIVE neighbour directions that are not occupied by
        a present ring (a gap wide enough to pass it out)."""
        free = []
        for cell in state.rings:
            if cell in state.marbles:
                continue
            present = [(_n in state.rings) for _n in self._neighbours(cell)]
            # two consecutive missing neighbours (cyclic over the 6 directions)
            if any((not present[i]) and (not present[(i + 1) % 6]) for i in range(6)):
                free.append(cell)
        return free

    # ---- isolation ---------------------------------------------------------
    def _components(self, rings):
        rings = set(rings)
        seen = set()
        comps = []
        for start in rings:
            if start in seen:
                continue
            stack = [start]
            comp = set()
            while stack:
                c = stack.pop()
                if c in comp:
                    continue
                comp.add(c)
                seen.add(c)
                for n in self._neighbours(c):
                    if n in rings and n not in comp:
                        stack.append(n)
            comps.append(comp)
        return comps

    def _resolve_isolation(self, rings, marbles, reserve, mover, prev=None):
        """Any connected component of rings that is FULLY occupied is claimed by
        `mover`: its marbles go to the mover's reserve and its rings are removed.
        Returns (new_rings, new_marbles). Mutates `reserve[mover]` in place.

        `prev`, when given, is the (rings, marbles) of the position BEFORE this
        move; a component that was ALREADY a fully-occupied isolated component in
        that position is left untouched (it was not cut off / completed by this
        move, so it stays as part of the standing board)."""
        rings = set(rings)
        marbles = dict(marbles)
        comps = self._components(rings)
        if len(comps) <= 1:
            return frozenset(rings), marbles
        prev_full = set()
        if prev is not None:
            prev_rings, prev_marbles = prev
            for pc in self._components(prev_rings):
                if all(c in prev_marbles for c in pc):
                    prev_full.add(frozenset(pc))
        for comp in comps:
            if all(c in marbles for c in comp):  # every ring occupied
                if frozenset(comp) in prev_full:
                    continue  # already isolated+full before the move -> leave it
                for c in comp:
                    reserve[mover][marbles[c]] += 1
                    del marbles[c]
                    rings.discard(c)
        return frozenset(rings), marbles

    # ---- legal moves -------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        # mid-capture chain: must continue jumping with chain_from (if possible)
        if state.chain_from is not None:
            cont = self._chain_moves(state, _cell(state.chain_from))
            # chain_from is only set while another jump remains; defensive:
            return cont if cont else []
        # pending ring removal after a placement
        if state.pending_removal:
            free = self._free_rings(state)
            return [f"x{_cid(c)}" for c in free]
        # captures are mandatory
        caps = self._all_captures(state)
        if caps:
            return caps
        # placement: any pooled colour onto any vacant ring
        vacant = [c for c in state.rings if c not in state.marbles]
        out = []
        for col in COLOURS:
            if state.pool[col] > 0:
                for c in vacant:
                    out.append(f"{col}@{_cid(c)}")
        return out

    def _all_captures(self, state):
        """Single-jump capture moves available this turn (start of a chain)."""
        out = []
        for c in state.marbles:
            for over, land in self._jumps_from(state, c):
                out.append(f"{_cid(c)}>{_cid(land)}")
        return out

    def _chain_moves(self, state, cell):
        """Continuation jumps for the marble at `cell` mid-chain."""
        out = []
        for over, land in self._jumps_from(state, cell):
            out.append(f"{_cid(cell)}>{_cid(land)}")
        return out

    # ---- apply -------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        rings = set(state.rings)
        marbles = dict(state.marbles)
        pool = dict(state.pool)
        reserve = [dict(state.reserve[0]), dict(state.reserve[1])]
        pl = state.to_move
        plies = state.plies + 1

        # --- ring removal step of a placement turn ---
        if move.startswith("x"):
            cell = _cell(move[1:])
            prev = (frozenset(rings), dict(marbles))  # board before this removal
            rings.discard(cell)
            rings, marbles = self._resolve_isolation(rings, marbles, reserve, pl,
                                                     prev=prev)
            ns = ZState(rings=frozenset(rings), marbles=marbles, pool=pool,
                        reserve=reserve, to_move=1 - pl, plies=plies)
            return self._settle(ns)

        # --- placement: colour@cell ---
        if "@" in move:
            col, cell_s = move.split("@")
            cell = _cell(cell_s)
            prev = (frozenset(rings), dict(marbles))  # board before this placement
            marbles[cell] = col
            pool[col] -= 1
            # A placement can FILL the last vacant ring of an already cut-off
            # group; that group is now fully occupied and must be claimed by the
            # mover immediately (the official rule), even if no ring is removed
            # this turn. Resolve isolation right after the placement. `prev` keeps
            # a group that was ALREADY isolated+fully-occupied from being claimed.
            rings_fz, marbles = self._resolve_isolation(rings, marbles, reserve, pl,
                                                        prev=prev)
            rings = set(rings_fz)
            free = self._free_rings_raw(rings, marbles)
            if free:
                ns = ZState(rings=frozenset(rings), marbles=marbles, pool=pool,
                            reserve=reserve, to_move=pl, pending_removal=True,
                            plies=plies)
                # a placement-triggered isolation may already be a win;
                # _settle only sets `winner` (it does not pass the turn), so the
                # pending ring-removal step is preserved unless the game is over.
                return self._settle(ns)
            # no free ring -> turn ends without a removal
            ns = ZState(rings=frozenset(rings), marbles=marbles, pool=pool,
                        reserve=reserve, to_move=1 - pl, plies=plies)
            return self._settle(ns)

        # --- capture: a>b (single jump; chain continues if more jumps remain) ---
        frm_s, to_s = move.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        # the jumped marble is the midpoint
        over = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
        captured_col = marbles[over]
        reserve[pl][captured_col] += 1
        del marbles[over]
        marbles[to] = marbles.pop(frm)
        ns = ZState(rings=frozenset(rings), marbles=marbles, pool=pool,
                    reserve=reserve, to_move=pl, plies=plies)
        # chain: if the marble can jump again, keep the turn
        if self._jumps_from(ns, to):
            ns.chain_from = _cid(to)
            return ns
        # chain over -> pass turn
        ns.to_move = 1 - pl
        ns.chain_from = None
        return self._settle(ns)

    def _free_rings_raw(self, rings, marbles):
        rings = set(rings)
        free = []
        for cell in rings:
            if cell in marbles:
                continue
            present = [((cell[0] + d[0], cell[1] + d[1]) in rings) for d in DIRS]
            if any((not present[i]) and (not present[(i + 1) % 6]) for i in range(6)):
                free.append(cell)
        return free

    def _settle(self, ns):
        """Decide a win from captured reserves; else defensive draw checks."""
        for pl in (0, 1):
            r = ns.reserve[pl]
            if (any(r[c] >= WIN_SINGLE[c] for c in COLOURS)
                    or (r["W"] >= WIN_TRIPLE and r["G"] >= WIN_TRIPLE
                        and r["B"] >= WIN_TRIPLE)):
                ns.winner = pl
                return ns
        return ns

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        if state.winner is not None:
            return True
        if state.plies >= self.PLY_CAP:
            return True
        # no marbles can be placed and no captures: dead position -> draw
        if state.chain_from is None and not state.pending_removal:
            if not self._all_captures(state):
                vacant = any(c not in state.marbles for c in state.rings)
                pooled = any(state.pool[c] > 0 for c in COLOURS)
                if not (vacant and pooled):
                    return True
        return False

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialize ---------------------------------------------------------
    def serialize(self, state):
        return {
            "rings": sorted([list(c) for c in state.rings]),
            "marbles": {_cid(c): v for c, v in state.marbles.items()},
            "pool": dict(state.pool),
            "reserve": [dict(state.reserve[0]), dict(state.reserve[1])],
            "to_move": state.to_move,
            "pending_removal": state.pending_removal,
            "chain_from": state.chain_from,
            "winner": state.winner,
            "plies": state.plies,
        }

    def deserialize(self, d):
        return ZState(
            rings=frozenset((c[0], c[1]) for c in d["rings"]),
            marbles={_cell(k): v for k, v in d["marbles"].items()},
            pool=dict(d["pool"]),
            reserve=[dict(d["reserve"][0]), dict(d["reserve"][1])],
            to_move=d["to_move"],
            pending_removal=d.get("pending_removal", False),
            chain_from=d.get("chain_from"),
            winner=d.get("winner"),
            plies=d.get("plies", 0),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if move.startswith("x"):
            return f"-{move[1:]}"
        if "@" in move:
            col, cell = move.split("@")
            names = {"W": "white", "G": "grey", "B": "black"}
            return f"{names[col]}@{cell}"
        return move.replace(">", "x")  # a jump

    def render(self, state, perspective=None):
        # We render as `polygons` so removed rings actually vanish (the generic
        # hex renderer always draws the full hexagon and ignores a cell list).
        # Each EXISTING ring becomes a hexagon polygon laid out exactly like the
        # web hex layout; `board.extent` is pinned to the FULL 37-ring bounds so
        # the viewBox never rescales/recentres as rings disappear.
        cells = [{"id": f"{q},{r}", "points": _hex_poly(q, r)}
                 for (q, r) in sorted(state.rings)]
        ext = self._full_extent()

        fill = {"W": "#f5f5f0", "G": "#9aa0a6", "B": "#2b2b2b"}
        stroke = {"W": "#333333", "G": "#444444", "B": "#dddddd"}
        pieces = []
        for c, col in state.marbles.items():
            pieces.append({"cell": _cid(c), "fill": fill[col], "stroke": stroke[col]})

        names = {0: "White", 1: "Black"}
        # The win is about CAPTURED marbles, so the two reserve trays are used to
        # arm the shared POOL for placement: during the mover's placement step the
        # pool (W/G/B) is shown under the mover's tray so they can click-a-colour-
        # then-click-a-ring (the standard drop flow), and captured-marble progress
        # for both sides rides the caption. In any non-placement step the trays
        # are empty (no marble to place that step).
        placing = (state.winner is None and not self.is_terminal(state)
                   and state.chain_from is None and not state.pending_removal
                   and not self._all_captures(state))
        if placing:
            pool_nz = {c: state.pool[c] for c in COLOURS if state.pool[c]}
            reserve = {str(state.to_move): pool_nz, str(1 - state.to_move): {}}
        else:
            reserve = {"0": {}, "1": {}}

        def _cap_str(i):
            r = state.reserve[i]
            s = " ".join(f"{r[c]}{c}" for c in COLOURS if r[c])
            return s or "—"
        captured = f"  ·  captured — {names[0]}: {_cap_str(0)} / {names[1]}: {_cap_str(1)}"

        if state.winner is not None:
            cap = f"{names[state.winner]} wins" + captured
        elif self.is_terminal(state):
            cap = "Draw" + captured
        elif state.chain_from is not None:
            cap = f"{names[state.to_move]}: continue jumping" + captured
        elif state.pending_removal:
            cap = f"{names[state.to_move]}: remove a free ring" + captured
        elif self._all_captures(state):
            cap = f"{names[state.to_move]}: must capture" + captured
        else:
            cap = f"{names[state.to_move]} to place (pick a pool marble)" + captured

        return {
            "board": {"type": "polygons", "cells": cells, "extent": ext},
            "pieces": pieces,
            "reserve": reserve,
            "highlights": [],
            "caption": cap,
        }

    def _full_extent(self):
        # Bounds (in the same pixel space as the polygon vertices) over ALL 37
        # original rings, so the viewBox stays fixed as the board shrinks.
        xs, ys = [], []
        for (q, r) in ALL_RINGS:
            for (x, y) in _hex_poly(q, r):
                xs.append(x); ys.append(y)
        pad = HEX_R * 0.6
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        return [minx - pad, miny - pad,
                (maxx - minx) + 2 * pad, (maxy - miny) + 2 * pad]
