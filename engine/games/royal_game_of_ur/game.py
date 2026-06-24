"""The Royal Game of Ur (the Game of Twenty Squares) -- the ~4500-year-old
Mesopotamian race game, in Irving Finkel's (British Museum) reconstructed
ruleset.

Two players each race 7 pieces from off-board, up their private start arm,
along a shared central lane, then down their private exit arm and off the far
end. Movement is by FOUR tetrahedral dice (each lands "marked" with p=1/2), so a
roll is the number of marked corners up = 0..4, distributed binomial(4, 1/2):
P(0)=P(4)=1/16, P(1)=P(3)=4/16, P(2)=6/16.

Randomness is modelled WITHOUT a chance node (the platform's standard pattern,
as in EinStein): the roll for the player to move is stored in the state. The
first roll is set in ``initial_state`` with the supplied rng; every ``apply_move``
rolls the dice for the player who will move next and stores that value, so the
roll is always known when the move is chosen. ``has_randomness`` is true.

Special squares: 5 rosettes. Landing on a rosette (a) is SAFE -- an enemy can
never land on / capture a piece there -- and (b) grants the SAME player an EXTRA
TURN (a fresh roll, same player to move). On a SHARED middle-lane square, landing
on an enemy piece CAPTURES it (sends it back off-board to restart). Bearing a
piece off requires an EXACT roll past the last square. First to bear all 7 off
wins.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

# ---------------------------------------------------------------------------
# Geometry.  Columns c in 0..7, rows r in {0,1,2}.
#   r = 0  -> player 0's private arms (start cols 0..3, exit cols 6..7)
#   r = 1  -> the SHARED central lane (cols 0..7)
#   r = 2  -> player 1's private arms (start cols 0..3, exit cols 6..7)
# The 4 cells r in {0,2} at cols {4,5} do not exist (the board's narrow bridge),
# giving the classic 20-square H/dumbbell shape.
# ---------------------------------------------------------------------------
SHARED_ROW = 1

BOARD_CELLS = []  # the 20 squares that exist
for c in range(8):
    BOARD_CELLS.append((c, SHARED_ROW))  # full middle lane
for r in (0, 2):
    for c in (0, 1, 2, 3, 6, 7):
        BOARD_CELLS.append((c, r))
BOARD_CELLS = sorted(set(BOARD_CELLS))

# Each player's path of 14 squares, off-board -> ... -> off the far end.
# Standard Finkel path: up the private start column (4), along the shared lane
# (8), down the private exit column (2).  Player 0 uses row 0 for private arms,
# player 1 uses row 2; they share row 1.
def _path(home_row):
    start = [(3, home_row), (2, home_row), (1, home_row), (0, home_row)]
    shared = [(c, SHARED_ROW) for c in range(8)]
    exit_arm = [(7, home_row), (6, home_row)]
    return start + shared + exit_arm


PATH = {0: _path(0), 1: _path(2)}
PATH_LEN = 14  # squares on a path; an index of PATH_LEN means "borne off"
assert all(len(p) == PATH_LEN for p in PATH.values())

# Rosettes: the standard 5.  Along a path (0-indexed) they are at index 3 (the
# private start-corner, path square 4), index 7 (centre of the shared lane,
# square 8) and index 13 (the private exit square, square 14).
ROSETTE_PATH_IDX = {3, 7, 13}
ROSETTES = set()
for pl in (0, 1):
    for i in ROSETTE_PATH_IDX:
        ROSETTES.add(PATH[pl][i])
# (3,1) is shared and is the same cell for both players -> 5 distinct rosettes.
assert len(ROSETTES) == 5, ROSETTES

# A cell is "shared" (capture happens) iff it is in the central lane.
def _is_shared(cell):
    return cell[1] == SHARED_ROW


NPIECES = 7
PLY_CAP = 2000  # safety: random play always terminates (pieces only advance)
NAMES = {0: "White", 1: "Black"}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class UrState:
    # positions[pl] = list of path indices for that player's 7 pieces.
    #   -1  = off-board, not yet started
    #   0..13 = on the board at PATH[pl][idx]
    #   PATH_LEN (14) = borne off
    positions: dict = field(default_factory=dict)
    roll: int = 0
    to_move: int = 0
    ply: int = 0
    winner: object = None


class RoyalGameOfUr(Game):
    uid = "royal_game_of_ur"
    name = "The Royal Game of Ur"

    @property
    def num_players(self):
        return 2

    # -- dice ---------------------------------------------------------------
    @staticmethod
    def _roll(rng):
        """Four tetrahedral dice -> number of marked corners up, 0..4."""
        return sum(rng.randint(0, 1) for _ in range(4))

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        positions = {0: [-1] * NPIECES, 1: [-1] * NPIECES}
        return UrState(positions=positions, roll=self._roll(rng),
                       to_move=0, ply=0, winner=None)

    def current_player(self, s):
        return s.to_move

    # -- move helpers -------------------------------------------------------
    @staticmethod
    def _cell_at(pl, idx):
        return PATH[pl][idx] if 0 <= idx < PATH_LEN else None

    def _occupied_by(self, s, pl, cell):
        """True if player pl has a piece on this board cell."""
        for idx in s.positions[pl]:
            if 0 <= idx < PATH_LEN and PATH[pl][idx] == cell:
                return True
        return False

    def _piece_dests(self, s, pl):
        """Map of legal moves for the current roll: dict src_idx -> dest_idx.

        src_idx is the piece's current path index (-1 for off-board entry).
        dest_idx == PATH_LEN means "bear off".  A roll of 0 yields no moves.
        """
        roll = s.roll
        out = {}
        if roll == 0:
            return out
        seen_src = set()
        for src in s.positions[pl]:
            if src == PATH_LEN:
                continue  # already borne off
            if src in seen_src:
                continue  # multiple pieces share a source (e.g. several off-board)
            seen_src.add(src)
            dest = src + roll
            if dest > PATH_LEN:
                continue  # overshoot -> must be exact to bear off
            if dest == PATH_LEN:
                out[src] = dest  # exact bear-off
                continue
            cell = PATH[pl][dest]
            if self._occupied_by(s, pl, cell):
                continue  # cannot land on your own piece
            # Rosette safety: an enemy piece on a rosette cannot be landed on.
            opp = 1 - pl
            if cell in ROSETTES and self._occupied_by(s, opp, cell):
                continue
            out[src] = dest
        return out

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        dests = self._piece_dests(s, s.to_move)
        if not dests:
            return ["pass"]  # roll of 0, or genuinely no legal move
        moves = []
        for src, dest in dests.items():
            if src == -1:
                # Entry from off-board -> a single-cell (placement) move = one
                # click on the destination square.
                d = PATH[s.to_move][dest]
                moves.append(f"{d[0]},{d[1]}")
            elif dest == PATH_LEN:
                # Bear off -> an action button "from>off".
                f = PATH[s.to_move][src]
                moves.append(f"{f[0]},{f[1]}>off")
            else:
                f = PATH[s.to_move][src]
                d = PATH[s.to_move][dest]
                moves.append(f"{f[0]},{f[1]}>{d[0]},{d[1]}")
        return sorted(moves)

    # -- apply --------------------------------------------------------------
    def _parse(self, s, move):
        """Return (src_idx, dest_idx) for a non-pass move of the player to move.

        Encodings: ``"c,r"`` (single cell) = entry from off-board onto that
        square; ``"c,r>off"`` = bear off from that square; ``"c,r>c,r"`` = a
        normal on-board advance.
        """
        pl = s.to_move
        if ">" not in move:
            # entry: destination square -> src is off-board (-1)
            dest = PATH[pl].index(_cell(move))
            return -1, dest
        frm_s, to_s = move.split(">")
        src = PATH[pl].index(_cell(frm_s))
        dest = PATH_LEN if to_s == "off" else PATH[pl].index(_cell(to_s))
        return src, dest

    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        pl = s.to_move
        positions = {0: list(s.positions[0]), 1: list(s.positions[1])}

        extra_turn = False
        if move != "pass":
            src, dest = self._parse(s, move)
            # advance one piece sitting at src (off-board entry: the first -1)
            positions[pl][positions[pl].index(src)] = dest

            if dest < PATH_LEN:
                cell = PATH[pl][dest]
                # capture on a shared square (rosettes are safe; legal_moves
                # already forbade landing on an enemy rosette).
                if _is_shared(cell):
                    opp = 1 - pl
                    for i, oidx in enumerate(positions[opp]):
                        if 0 <= oidx < PATH_LEN and PATH[opp][oidx] == cell:
                            positions[opp][i] = -1  # sent back off-board
                if cell in ROSETTES:
                    extra_turn = True

        # win check
        winner = pl if all(p == PATH_LEN for p in positions[pl]) else None

        ply = s.ply + 1
        if winner is None and ply >= PLY_CAP:
            # Safety net (unreachable in practice -- pieces only advance and a
            # capture is bounded).  Declare the leader the winner.
            winner = self._leader(positions)

        next_player = pl if extra_turn else 1 - pl
        new_roll = 0 if winner is not None else self._roll(rng)
        return UrState(positions=positions, roll=new_roll,
                       to_move=next_player, ply=ply, winner=winner)

    @staticmethod
    def _borne_off(positions, pl):
        return sum(1 for p in positions[pl] if p == PATH_LEN)

    def _leader(self, positions):
        a = sum(p if p >= 0 else 0 for p in positions[0])
        b = sum(p if p >= 0 else 0 for p in positions[1])
        return 0 if a >= b else 1

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s):
        return {
            "positions": {str(pl): list(v) for pl, v in s.positions.items()},
            "roll": s.roll,
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d):
        return UrState(
            positions={int(pl): list(v) for pl, v in d["positions"].items()},
            roll=d["roll"],
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    # -- move log -----------------------------------------------------------
    def describe_move(self, s, move):
        if move == "pass":
            return f"{NAMES[s.to_move]} rolled 0 — passes" if s.roll == 0 \
                else f"{NAMES[s.to_move]} (rolled {s.roll}) — no move, passes"
        pl = s.to_move
        src, dest = self._parse(s, move)
        opp = 1 - pl
        frm = "entry" if src == -1 else "{},{}".format(*PATH[pl][src])
        if dest == PATH_LEN:
            return f"{NAMES[pl]} bears off (from {frm})"
        cell = PATH[pl][dest]
        cap = _is_shared(cell) and self._occupied_by(s, opp, cell)
        ros = " ★" if cell in ROSETTES else ""
        verb = "captures at" if cap else "to"
        return f"{NAMES[pl]} {frm} {verb} {cell[0]},{cell[1]}{ros}"

    # -- render -------------------------------------------------------------
    def render(self, s, perspective=None):
        # Polygons board: only the 20 real squares (gives the H shape; the
        # bridge gaps simply have no cell).  y grows downward.
        cells = []
        for (c, r) in BOARD_CELLS:
            x0, y0 = c, r
            pts = [[x0, y0], [x0 + 1, y0], [x0 + 1, y0 + 1], [x0, y0 + 1]]
            cells.append({"id": f"{c},{r}", "points": pts})

        tints = {f"{c},{r}": "#caa53d" for (c, r) in ROSETTES}  # rosette gold

        pieces = []
        for pl in (0, 1):
            for idx in s.positions[pl]:
                if 0 <= idx < PATH_LEN:
                    c, r = PATH[pl][idx]
                    pieces.append({"cell": f"{c},{r}", "owner": pl})

        off0 = sum(1 for p in s.positions[0] if p == -1)
        off1 = sum(1 for p in s.positions[1] if p == -1)
        done0 = self._borne_off(s.positions, 0)
        done1 = self._borne_off(s.positions, 1)
        tally = (f"{NAMES[0]}: {off0} waiting, {done0} home  ·  "
                 f"{NAMES[1]}: {off1} waiting, {done1} home")

        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins!  ·  {tally}"
        else:
            extra = "" if self._piece_dests(s, s.to_move) else " (no move — pass)"
            caption = (f"{NAMES[s.to_move]} rolled {s.roll}{extra}  ·  {tally}")

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
