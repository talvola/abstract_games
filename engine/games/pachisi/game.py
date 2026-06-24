"""Pachisi (पचीसी) -- the classic Indian cross-and-circle race game, the
ancestor of Ludo / Parcheesi / Parchís.

Four players each race FOUR pieces. A piece starts in the central Charkoni,
travels OUT down the middle column of its own arm to the arm's tip, then
ANTICLOCKWISE around the periphery of the cross (the two outer columns of every
arm -- the shared "main track" where captures happen), and finally back UP the
middle column of its own arm to finish on the Charkoni. The middle column of
each arm is that player's PRIVATE home column (only its owner travels it, and it
is safe from capture).

Movement is by SIX COWRIE SHELLS. The throw value = a function of how many fall
mouth-up (Wikipedia / Masters of Games):

    mouths-up : value : grace (extra turn)?
        0     :  25   : yes
        1     :  10   : yes
        2     :   2   : no
        3     :   3   : no
        4     :   4   : no
        5     :   5   : no
        6     :   6   : yes

The grace throws (6, 10, 25) grant an EXTRA TURN and let the player introduce a
new piece from the Charkoni onto the board (a fresh piece can ONLY enter on a
grace throw). The name "pachisi" is Hindi for 25, the largest throw.

CASTLE (safe) SQUARES: twelve crossed squares -- the middle square at each arm's
tip, plus the squares four in from the end on each outer column of each arm. A
piece on a castle square cannot be captured. CAPTURE: landing exactly on an
opponent's piece on a NON-castle main-track square sends that piece back to the
Charkoni (it must re-enter via a future grace throw). EXACT FINISH: a piece
enters the Charkoni (finishes) only on the exact count.

PLAYER COUNT / PARTNERSHIPS: implemented as FOUR INDEPENDENT players (num_players
= 4). Traditional Pachisi is often played as two partnerships (yellow+black vs
red+green); we implement the simpler, fully general free-for-all -- every seat
races for itself and the first to bring all four pieces home wins (returns =
+1 winner, -1 to each of the other three). This keeps the generic MCTS bot /
per-player payoff vector well-defined.

RANDOMNESS WITHOUT A CHANCE NODE (the platform's standard pattern, as in the
Royal Game of Ur / Daldøs): the current mover's throw is STORED in the state.
``initial_state`` sets the first throw with the supplied rng; every turn-ending
``apply_move`` rolls the next mover's throw. ``legal_moves`` is computed against
the stored throw; a grace throw keeps the same player (re-throw). ``has_randomness``
is true and ``apply_move(state, move, rng)`` is deterministic given ``rng``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

# ---------------------------------------------------------------------------
# Geometry.  Coordinates (x=col, y=row), y downward.  The cross:
#   central 3x3 = cols 8,9,10  rows 8,9,10 ; Charkoni = (9,9).
#   TOP    arm: cols 8,9,10  rows 0..7   (middle col 9)
#   BOTTOM arm: cols 8,9,10  rows 11..18 (middle col 9)
#   LEFT   arm: rows 8,9,10  cols 0..7   (middle row 9)
#   RIGHT  arm: rows 8,9,10  cols 11..18 (middle row 9)
# ---------------------------------------------------------------------------
CHARKONI = (9, 9)


def _rotccw(c, k):
    """Rotate cell c about the centre (9,9) by k quarter-turns (maps arm->arm,
    anticlockwise player order BOTTOM->RIGHT->TOP->LEFT)."""
    x, y = c
    x -= 9
    y -= 9
    for _ in range(k % 4):
        x, y = y, -x
    return (x + 9, y + 9)


def _board_cells():
    cells = set()
    for x in (8, 9, 10):
        for y in range(0, 8):
            cells.add((x, y))      # top
        for y in range(11, 19):
            cells.add((x, y))      # bottom
    for y in (8, 9, 10):
        for x in range(0, 8):
            cells.add((x, y))      # left
        for x in range(11, 19):
            cells.add((x, y))      # right
    for x in (8, 9, 10):
        for y in (8, 9, 10):
            cells.add((x, y))      # centre
    return cells


ALL_CELLS = _board_cells()

# The 68-cell anticlockwise OUTER LOOP (shared main track -- the two outer
# columns of every arm + the tips).  Built once for the bottom arm orientation.
def _build_loop():
    loop = []
    for y in range(11, 19):
        loop.append((10, y))            # bottom right col, out
    loop.append((9, 18))
    loop.append((8, 18))                # bottom tip
    for y in range(17, 10, -1):
        loop.append((8, y))             # bottom left col, in
    for x in range(7, -1, -1):
        loop.append((x, 10))            # left lower row, out
    loop.append((0, 9))
    loop.append((0, 8))                 # left tip
    for x in range(1, 8):
        loop.append((x, 8))             # left upper row, in
    for y in range(7, -1, -1):
        loop.append((8, y))             # top left col, out
    loop.append((9, 0))
    loop.append((10, 0))                # top tip
    for y in range(1, 8):
        loop.append((10, y))            # top right col, in
    for x in range(11, 19):
        loop.append((x, 8))             # right upper row, out
    loop.append((18, 9))
    loop.append((18, 10))               # right tip
    for x in range(17, 10, -1):
        loop.append((x, 10))            # right lower row, in
    return loop


LOOP = _build_loop()
assert len(LOOP) == 68 and len(set(LOOP)) == 68

# Each player's full path: OUT own middle col (7 cells) -> the 68-loop CCW
# (entered at the player's own arm tip) -> IN own middle col (7 cells) ->
# Charkoni.  Length = 7 + 68 + 7 + 1 = 83 (index 0 = entry square just outside
# Charkoni; index 82 = Charkoni = finished).  This realises the documented
# circuit (down the middle, anticlockwise around the outside, back up the
# middle); a full lap is ~84 squares.
def _build_path(arm_k):
    # bottom orientation, then rotate.
    mid = [(9, y) for y in range(11, 18)]          # (9,11)..(9,17)  OUT (7)
    i_tip = LOOP.index((9, 18))                     # bottom-tip middle on loop
    loop_b = LOOP[i_tip:] + LOOP[:i_tip]            # loop starting at the tip
    path = mid + loop_b + list(reversed(mid)) + [CHARKONI]
    return [_rotccw(c, arm_k) for c in path]


# Player p (0..3) owns arm p in CCW order (0=BOTTOM,1=RIGHT,2=TOP,3=LEFT).
PATH = {p: _build_path(p) for p in range(4)}
PATH_LEN = len(PATH[0])                              # 83
FINISH = PATH_LEN - 1                                # index of the Charkoni cell
assert all(len(PATH[p]) == PATH_LEN for p in range(4))
assert all(PATH[p][FINISH] == CHARKONI for p in range(4))

# The private "home column" of each player = its arm's middle column.  Pieces on
# their own home column are safe and never captured.  These are the OUT/IN middle
# cells (the same physical cells traversed twice).
HOME_COL = {p: set(_rotccw((9, y), p) for y in range(11, 18)) for p in range(4)}

# Cells on the SHARED main track (the outer loop) -- captures happen only here.
MAIN_TRACK = set(LOOP)

# Castle (safe) squares: 12.  Per arm: the tip-middle square, plus the square 4
# in from the tip on each outer column.  (Bottom arm: tip (9,18); 4th-from-tip on
# x=8 and x=10 = row 15.)
def _build_castles():
    castles = set()
    base = [(9, 18), (8, 15), (10, 15)]
    for k in range(4):
        for c in base:
            castles.add(_rotccw(c, k))
    return castles


CASTLES = _build_castles()
assert len(CASTLES) == 12

NPLAYERS = 4
NPIECES = 4
PLY_CAP = 1500   # hard resolution cap (see rules.md / selftest): the exact-
# finish rule makes the *last-piece* tail heavy under purely random play (most
# games finish in well under a thousand plies, but a tail can drag), so at the
# cap the current LEADER (pieces-home, then total progress) is declared the
# winner.  Real play (human / MCTS) finishes far below this; the cap only bounds
# pathological random playouts so conformance always terminates.
NAMES = {0: "Red", 1: "Blue", 2: "Green", 3: "Yellow"}

# Cowrie throw: how many of 6 shells land mouth-up -> (value, grace?).
COWRIE = {
    0: (25, True),
    1: (10, True),
    2: (2, False),
    3: (3, False),
    4: (4, False),
    5: (5, False),
    6: (6, True),
}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class PachisiState:
    # positions[p] = list of NPIECES path indices for player p:
    #   -1          = in the Charkoni, off the track (not yet introduced / sent home)
    #   0..FINISH-1 = on the board at PATH[p][idx]
    #   FINISH      = finished (home on the Charkoni)
    positions: dict = field(default_factory=dict)
    roll: int = 0
    to_move: int = 0
    ply: int = 0
    winner: object = None


class Pachisi(Game):
    uid = "pachisi"
    name = "Pachisi"

    @property
    def num_players(self):
        return NPLAYERS

    # -- cowrie dice --------------------------------------------------------
    @staticmethod
    def _throw(rng):
        """Throw six cowrie shells -> the move value (and whether it's a grace).
        Each shell is mouth-up with p=1/2."""
        up = sum(rng.randint(0, 1) for _ in range(6))
        value, _grace = COWRIE[up]
        return value

    @staticmethod
    def _is_grace(value):
        return value in (25, 10, 6)

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        positions = {p: [-1] * NPIECES for p in range(NPLAYERS)}
        return PachisiState(positions=positions, roll=self._throw(rng),
                            to_move=0, ply=0, winner=None)

    def current_player(self, s):
        return s.to_move

    # -- geometry helpers ---------------------------------------------------
    @staticmethod
    def _cell_at(p, idx):
        if 0 <= idx < FINISH:
            return PATH[p][idx]
        return None  # -1 (Charkoni) or FINISH (home) have no distinct track cell

    def _occupied_by_self(self, s, p, idx):
        """True if player p already has a piece sitting at path index idx (used
        to forbid landing two of your own on one square on the main track)."""
        cell = self._cell_at(p, idx)
        if cell is None:
            return False
        for j in s.positions[p]:
            if j == idx:
                return True
        return False

    # -- move generation ----------------------------------------------------
    def _piece_dests(self, s, p):
        """Map src_idx -> dest_idx of legal moves for the stored throw.

        src_idx == -1 is an off-board entry (only on a grace throw); a piece on
        the board advances by the throw, must reach FINISH by the exact count
        (overshoot is illegal), and may not land on its own piece on the main
        track (own private home column may stack/pass freely)."""
        roll = s.roll
        out = {}
        grace = self._is_grace(roll)
        seen_src = set()
        for src in s.positions[p]:
            if src == FINISH:
                continue                       # already home
            if src in seen_src:
                continue
            seen_src.add(src)
            if src == -1:
                # Entry from the Charkoni: only on a grace throw, onto path[0].
                if not grace:
                    continue
                dest = 0
                if self._occupied_by_self(s, p, dest):
                    continue
                out[src] = dest
                continue
            dest = src + roll
            if dest > FINISH:
                continue                       # overshoot -> need exact to finish
            if dest < FINISH:
                # may not land on your own piece on the SHARED main track
                cell = PATH[p][dest]
                if cell in MAIN_TRACK and self._occupied_by_self(s, p, dest):
                    continue
            out[src] = dest
        return out

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        dests = self._piece_dests(s, s.to_move)
        if not dests:
            return ["pass"]                    # no legal move for this throw
        p = s.to_move
        moves = []
        for src, dest in dests.items():
            if src == -1:
                # entry -> a single-cell (placement) move = one click on path[0]
                d = PATH[p][0]
                moves.append(f"{d[0]},{d[1]}")
            elif dest == FINISH:
                f = PATH[p][src]
                moves.append(f"{f[0]},{f[1]}>home")
            else:
                f = PATH[p][src]
                d = PATH[p][dest]
                moves.append(f"{f[0]},{f[1]}>{d[0]},{d[1]}")
        return sorted(moves)

    # -- apply --------------------------------------------------------------
    def _parse(self, s, move):
        """Return (src_idx, dest_idx) for a non-pass move of the mover.

        Resolved against the authoritative ``_piece_dests`` map (NOT a raw
        ``PATH.index`` lookup): a private home-column cell appears at two path
        indices [the OUT pass and the IN pass], so we must match the move string
        to the actual legal (src -> dest) the player has on the board."""
        p = s.to_move
        if ">" not in move:
            return -1, 0                       # entry from the Charkoni
        for src, dest in self._piece_dests(s, p).items():
            if src == -1:
                continue
            f = PATH[p][src]
            if dest == FINISH:
                cand = f"{f[0]},{f[1]}>home"
            else:
                d = PATH[p][dest]
                cand = f"{f[0]},{f[1]}>{d[0]},{d[1]}"
            if cand == move:
                return src, dest
        raise ValueError(f"illegal/ambiguous move {move} for {NAMES[p]}")

    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        p = s.to_move
        positions = {q: list(s.positions[q]) for q in range(NPLAYERS)}
        grace = self._is_grace(s.roll)

        if move != "pass":
            src, dest = self._parse(s, move)
            # advance a piece sitting at src (entry: the first -1)
            positions[p][positions[p].index(src)] = dest

            if dest < FINISH:
                cell = PATH[p][dest]
                # capture: only on the shared main track AND not a castle square
                if cell in MAIN_TRACK and cell not in CASTLES:
                    for q in range(NPLAYERS):
                        if q == p:
                            continue
                        for i, oidx in enumerate(positions[q]):
                            ocell = self._cell_at(q, oidx)
                            if ocell == cell:
                                positions[q][i] = -1   # sent home to the Charkoni

        # win check: all of mover's pieces home
        winner = p if all(j == FINISH for j in positions[p]) else None

        ply = s.ply + 1
        if winner is None and ply >= PLY_CAP:
            winner = self._leader(positions)

        # grace throws (and a pass on a grace -- a grace still grants the extra
        # turn) keep the SAME player, who re-throws.
        next_player = p if (grace and winner is None) else (p + 1) % NPLAYERS
        new_roll = 0 if winner is not None else self._throw(rng)
        return PachisiState(positions=positions, roll=new_roll,
                            to_move=next_player, ply=ply, winner=winner)

    @staticmethod
    def _progress(positions, p):
        """Total forward progress for tie-breaking (off-board counts as 0)."""
        return sum(j if j >= 0 else 0 for j in positions[p])

    def _leader(self, positions):
        best, who = -1, 0
        for p in range(NPLAYERS):
            home = sum(1 for j in positions[p] if j == FINISH)
            score = home * 10_000 + self._progress(positions, p)
            if score > best:
                best, who = score, p
        return who

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None:
            return [0.0] * NPLAYERS
        return [1.0 if i == s.winner else -1.0 for i in range(NPLAYERS)]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s):
        return {
            "positions": {str(p): list(v) for p, v in s.positions.items()},
            "roll": s.roll,
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d):
        return PachisiState(
            positions={int(p): list(v) for p, v in d["positions"].items()},
            roll=d["roll"],
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    # -- move log -----------------------------------------------------------
    def describe_move(self, s, move):
        p = s.to_move
        grace = " (grace, extra turn)" if self._is_grace(s.roll) else ""
        if move == "pass":
            return f"{NAMES[p]} threw {s.roll} — no move, passes{grace}"
        src, dest = self._parse(s, move)
        if src == -1:
            return f"{NAMES[p]} enters a piece (threw {s.roll}){grace}"
        if dest == FINISH:
            return f"{NAMES[p]} brings a piece home (threw {s.roll}){grace}"
        cell = PATH[p][dest]
        captured = (cell in MAIN_TRACK and cell not in CASTLES and any(
            self._cell_at(q, oidx) == cell
            for q in range(NPLAYERS) if q != p for oidx in s.positions[q]))
        verb = "captures at" if captured else "to"
        safe = " ✚" if cell in CASTLES else ""
        return (f"{NAMES[p]} {verb} {cell[0]},{cell[1]}{safe} "
                f"(threw {s.roll}){grace}")

    # -- render -------------------------------------------------------------
    def render(self, s, perspective=None):
        cells = []
        for (c, r) in sorted(ALL_CELLS):
            pts = [[c, r], [c + 1, r], [c + 1, r + 1], [c, r + 1]]
            cells.append({"id": f"{c},{r}", "points": pts})

        tints = {}
        # each player's private home column, tinted in a pale seat colour
        home_tint = {0: "#f6d6d6", 1: "#d6e0f6", 2: "#d6f0da", 3: "#f6eccf"}
        for p in range(NPLAYERS):
            for (c, r) in HOME_COL[p]:
                tints[f"{c},{r}"] = home_tint[p]
        tints[f"{CHARKONI[0]},{CHARKONI[1]}"] = "#e8e2d0"   # Charkoni
        for (c, r) in CASTLES:                              # castle squares
            tints[f"{c},{r}"] = "#caa53d"

        pieces = []
        for p in range(NPLAYERS):
            for idx in s.positions[p]:
                if 0 <= idx < FINISH:
                    c, r = PATH[p][idx]
                    pieces.append({"cell": f"{c},{r}", "owner": p})

        def tally(p):
            waiting = sum(1 for j in s.positions[p] if j == -1)
            home = sum(1 for j in s.positions[p] if j == FINISH)
            return f"{NAMES[p]}: {waiting} wait, {home} home"

        line = "  ·  ".join(tally(p) for p in range(NPLAYERS))
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins!  ·  {line}"
        else:
            grace = " (grace!)" if self._is_grace(s.roll) else ""
            no_move = "" if self._piece_dests(s, s.to_move) else " — no move, pass"
            caption = (f"{NAMES[s.to_move]} threw {s.roll}{grace}{no_move}"
                       f"  ·  {line}")

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
