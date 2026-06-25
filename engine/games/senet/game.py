"""Senet -- the ancient Egyptian race game (~3100 BCE onward), here in the
widely-used **Timothy Kendall** reconstruction (Kendall 1978/2007, as summarised
on Wikipedia "Senet").

Two players race **5 pawns** each along a 30-square boustrophedon (S-shaped)
track and off the far end. Movement is by **four two-sided throw sticks**: the
roll is the number of white (marked) sides up, 1-4, with the special case that
**all-black counts as 5**. A throw of **1, 4 or 5 grants another throw** (an
extra turn).

Randomness is modelled WITHOUT a chance node (the platform's standard pattern,
as in EinStein / Royal Game of Ur / Daldøs): the throw for the player to move is
stored in the state. ``initial_state`` makes the first throw with the supplied
rng; every ``apply_move`` makes the throw for whoever moves next and stores it,
so the throw is always known when the move is chosen. ``has_randomness`` is true.

THE BOARD (boustrophedon, linear track index 0..29 -> a 10-wide x 3-tall grid):
  - houses 1..10  = TOP row, left to right    (col 0..9, row 0)
  - houses 11..20 = MIDDLE row, right to left  (col 9..0, row 1)
  - houses 21..30 = BOTTOM row, left to right   (col 0..9, row 2)
A pawn at the end of house 10 continues to house 11 (directly below house 10),
giving the S-shaped path.

SPECIAL HOUSES (Kendall):
  - House 15 "House of Rebirth" (the Ankh): a plain house, but the destination
    of pawns sent back from house 27.
  - House 26 "House of Happiness/Beauty": a **mandatory stop** -- a pawn may not
    pass it; every pawn must land exactly on house 26 before continuing.
  - House 27 "House of Water": a pawn that lands here is sent back to house 15
    (or, if 15 is occupied by a friendly pawn, to the first empty house before
    it).
  - House 28 "House of the Three Truths": a pawn here bears off only on an exact
    throw of 3.
  - House 29 "House of Re-Atoum": a pawn here bears off only on an exact throw
    of 2.
  - House 30 "House of Horus": a pawn here bears off on a throw of 1 (or any
    overshoot that reaches/passes the end -- it is the last house).

MOVEMENT, SWAP, BLOCKADE:
  - Move one pawn forward by the throw. You may not land on your OWN pawn.
  - Landing on an opponent's SINGLE pawn SWAPS them: your pawn takes the square,
    the opponent's pawn goes back to the square you came from.
  - A pawn is PROTECTED if it has a friendly pawn on an immediately adjacent
    track square (a "pair"): it cannot be swapped/landed on.
  - THREE or more consecutive friendly pawns form an impassable BLOCK: an enemy
    pawn may not move past it (any move that would cross such a block is illegal).
  - If a player has no legal move for the throw, the turn passes ("pass").

First player to bear ALL 5 pawns off wins.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

NAMES = {0: "White", 1: "Black"}
NPIECES = 5
TRACK = 30                 # houses 1..30 -> indices 0..29
OFF = TRACK                # a pawn index of 30 means "borne off"
PLY_CAP = 4000             # hard draw cap (safety; a race always progresses)

# Special houses, expressed as 0-based track indices (house N -> index N-1).
HOUSE_REBIRTH = 14         # house 15
HOUSE_HAPPINESS = 25       # house 26 -- mandatory stop
HOUSE_WATER = 26           # house 27 -- sent back to rebirth
HOUSE_THREE_TRUTHS = 27    # house 28 -- bears off on exact 3
HOUSE_RE_ATOUM = 28        # house 29 -- bears off on exact 2
HOUSE_HORUS = 29           # house 30 -- bears off on a 1 / overshoot


# ---------------------------------------------------------------------------
# Boustrophedon geometry: linear track index 0..29 -> (col, row) on a 10x3 grid.
# ---------------------------------------------------------------------------
def track_to_cell(idx):
    """Map a 0-based track index (0..29) to a (col, row) grid cell."""
    row = idx // 10
    pos = idx % 10
    col = pos if row != 1 else (9 - pos)  # middle row runs right-to-left
    return col, row


CELLS = [track_to_cell(i) for i in range(TRACK)]
CELL_TO_TRACK = {cell: i for i, cell in enumerate(CELLS)}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class SenetState:
    # positions[pl] = sorted list of track indices for that player's 5 pawns.
    #   0..29 = on the board at that track index
    #   OFF (30) = borne off
    positions: dict = field(default_factory=dict)
    throw: int = 0
    to_move: int = 0
    ply: int = 0
    winner: object = None


class Senet(Game):
    uid = "senet"
    name = "Senet"

    @property
    def num_players(self):
        return 2

    # -- throw sticks -------------------------------------------------------
    @staticmethod
    def _throw(rng):
        """Four 2-sided sticks: number of white sides up, all-black counts as 5."""
        whites = sum(rng.randint(0, 1) for _ in range(4))
        return whites if whites >= 1 else 5

    @staticmethod
    def _bonus(throw):
        """A throw of 1, 4 or 5 grants an extra turn."""
        return throw in (1, 4, 5)

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        # Standard start: pawns interleaved on houses 1..10.
        #   White (0) on houses 1,3,5,7,9   -> indices 0,2,4,6,8
        #   Black (1) on houses 2,4,6,8,10  -> indices 1,3,5,7,9
        positions = {0: [0, 2, 4, 6, 8], 1: [1, 3, 5, 7, 9]}
        return SenetState(positions=positions, throw=self._throw(rng),
                          to_move=0, ply=0, winner=None)

    def current_player(self, s):
        return s.to_move

    # -- board occupancy helpers -------------------------------------------
    @staticmethod
    def _occ_map(positions):
        """track index -> owner, for every on-board pawn (off-board excluded)."""
        m = {}
        for pl in (0, 1):
            for idx in positions[pl]:
                if 0 <= idx < TRACK:
                    m[idx] = pl
        return m

    @staticmethod
    def _is_protected(positions, owner, idx):
        """A pawn is protected if a friendly pawn sits on an adjacent track sq."""
        own = positions[owner]
        return (idx - 1) in own or (idx + 1) in own

    @staticmethod
    def _blocked_span(positions, enemy):
        """Set of track indices an enemy may NOT cross: any square that is part
        of a run of 3+ consecutive enemy pawns."""
        own = sorted(i for i in positions[enemy] if 0 <= i < TRACK)
        blocked = set()
        i = 0
        n = len(own)
        while i < n:
            j = i
            while j + 1 < n and own[j + 1] == own[j] + 1:
                j += 1
            if j - i + 1 >= 3:
                blocked.update(own[i:j + 1])
            i = j + 1
        return blocked

    # -- move generation ----------------------------------------------------
    def _legal_dests(self, s, pl):
        """Map src_idx -> dest_idx for the current throw. dest == OFF = bear off.

        Honours: mandatory stop at house 26, exact-bear-off houses (28/29/30),
        no-land-on-own, swap-vs-protected, and the 3-in-a-row block.
        """
        throw = s.throw
        out = {}
        positions = s.positions
        opp = 1 - pl
        occ = self._occ_map(positions)
        block = self._blocked_span(positions, opp)

        for src in sorted(set(i for i in positions[pl] if i < TRACK)):
            # --- bear-off houses (28/29/30) require an exact throw ----------
            if src == HOUSE_THREE_TRUTHS:
                if throw == 3:
                    out[src] = OFF
                continue
            if src == HOUSE_RE_ATOUM:
                if throw == 2:
                    out[src] = OFF
                continue
            if src == HOUSE_HORUS:
                if throw == 1:
                    out[src] = OFF
                continue

            dest = src + throw

            # --- mandatory stop at house 26 (index 25): may not pass it -----
            if src < HOUSE_HAPPINESS and dest > HOUSE_HAPPINESS:
                continue  # would jump over the House of Happiness -> illegal

            # --- bear off past the end (houses <=27 reaching 30+) -----------
            if dest >= TRACK:
                # A pawn at/after house 28 uses the exact-throw rule above; here
                # src <= index 26 (house 27). It must land exactly on the end
                # houses or pass off only via the bear-off houses, so overshoot
                # of the board is NOT a legal bear-off for these -- it must land
                # on a real house. Disallow overshoot.
                continue

            # --- 3-in-a-row block: cannot cross / land within an enemy block -
            if any(b in block for b in range(src + 1, dest + 1)):
                continue

            # --- destination occupancy --------------------------------------
            who = occ.get(dest)
            if who == pl:
                continue  # cannot land on own pawn
            if who == opp:
                # swap only if the enemy pawn is NOT protected by a pair
                if self._is_protected(positions, opp, dest):
                    continue

            out[src] = dest
        return out

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        dests = self._legal_dests(s, s.to_move)
        if not dests:
            return ["pass"]
        moves = []
        for src, dest in dests.items():
            fc = CELLS[src]
            if dest == OFF:
                moves.append(f"{fc[0]},{fc[1]}>off")
            else:
                dc = CELLS[dest]
                moves.append(f"{fc[0]},{fc[1]}>{dc[0]},{dc[1]}")
        return sorted(moves)

    # -- apply --------------------------------------------------------------
    def _parse(self, move):
        frm_s, to_s = move.split(">")
        src = CELL_TO_TRACK[_cell(frm_s)]
        dest = OFF if to_s == "off" else CELL_TO_TRACK[_cell(to_s)]
        return src, dest

    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        pl = s.to_move
        positions = {0: list(s.positions[0]), 1: list(s.positions[1])}
        opp = 1 - pl

        extra = False
        if move != "pass":
            src, dest = self._parse(move)
            extra = self._bonus(s.throw)

            # remove the moving pawn from src
            positions[pl].remove(src)

            if dest == OFF:
                positions[pl].append(OFF)
            else:
                # swap: an opponent pawn on dest goes back to src
                if dest in positions[opp]:
                    positions[opp].remove(dest)
                    positions[opp].append(src)
                # House of Water (27): sent back to house 15 / first empty before
                if dest == HOUSE_WATER:
                    dest = self._rebirth_target(positions, pl)
                positions[pl].append(dest)

            positions[pl].sort()
            positions[opp].sort()
        else:
            # a forced pass still consumes the throw; bonus does NOT re-grant a
            # turn on a pass (no move was made).
            extra = False

        winner = pl if all(p == OFF for p in positions[pl]) else None

        ply = s.ply + 1
        if winner is None and ply >= PLY_CAP:
            winner = self._leader(positions)

        next_player = pl if (extra and winner is None) else opp
        new_throw = 0 if winner is not None else self._throw(rng)
        return SenetState(positions=positions, throw=new_throw,
                          to_move=next_player, ply=ply, winner=winner)

    @staticmethod
    def _rebirth_target(positions, pl):
        """House of Water target: house 15, or the first empty house before it
        if 15 is occupied (by either player)."""
        occupied = set(positions[0]) | set(positions[1])
        idx = HOUSE_REBIRTH
        while idx >= 0 and idx in occupied:
            idx -= 1
        if idx < 0:
            # extremely unlikely (whole start blocked); fall back to rebirth.
            return HOUSE_REBIRTH
        return idx

    @staticmethod
    def _borne_off(positions, pl):
        return sum(1 for p in positions[pl] if p == OFF)

    def _leader(self, positions):
        a = sum(p for p in positions[0])
        b = sum(p for p in positions[1])
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
            "throw": s.throw,
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d):
        return SenetState(
            positions={int(pl): list(v) for pl, v in d["positions"].items()},
            throw=d["throw"],
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    # -- move log -----------------------------------------------------------
    def describe_move(self, s, move):
        pl = s.to_move
        if move == "pass":
            return f"{NAMES[pl]} (threw {s.throw}) — no move, passes"
        src, dest = self._parse(move)
        if dest == OFF:
            return f"{NAMES[pl]} bears off from house {src + 1} (threw {s.throw})"
        opp = 1 - pl
        swap = dest in s.positions[opp]
        note = ""
        if dest == HOUSE_WATER:
            note = " → House of Water, sent back to House of Rebirth"
        elif dest == HOUSE_HAPPINESS:
            note = " (House of Happiness)"
        verb = "swaps onto" if swap else "to"
        return (f"{NAMES[pl]} {verb} house {dest + 1} from house {src + 1} "
                f"(threw {s.throw}){note}")

    # -- render -------------------------------------------------------------
    def render(self, s, perspective=None):
        # Square 10-wide x 3-tall board.
        tints = {}
        special = {
            HOUSE_REBIRTH: "#7fbf7f",     # House of Rebirth (green)
            HOUSE_HAPPINESS: "#e8c84a",   # House of Happiness (gold)
            HOUSE_WATER: "#5b8fd6",       # House of Water (blue)
            HOUSE_THREE_TRUTHS: "#c98fd6",  # Three Truths (purple)
            HOUSE_RE_ATOUM: "#d68f8f",    # Re-Atoum (red)
            HOUSE_HORUS: "#d6b35b",       # Horus (amber)
        }
        for idx, colour in special.items():
            c, r = CELLS[idx]
            tints[f"{c},{r}"] = colour

        pieces = []
        for pl in (0, 1):
            for idx in s.positions[pl]:
                if 0 <= idx < TRACK:
                    c, r = CELLS[idx]
                    pieces.append({"cell": f"{c},{r}", "owner": pl})

        done0 = self._borne_off(s.positions, 0)
        done1 = self._borne_off(s.positions, 1)
        tally = (f"{NAMES[0]}: {done0}/{NPIECES} off  ·  "
                 f"{NAMES[1]}: {done1}/{NPIECES} off")

        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins!  ·  {tally}"
        else:
            no_move = "" if self._legal_dests(s, s.to_move) else " (no move — pass)"
            bonus = " (extra turn on 1/4/5)" if self._bonus(s.throw) else ""
            caption = (f"{NAMES[s.to_move]} threw {s.throw}{bonus}{no_move}  ·  "
                       f"{tally}")

        return {
            "board": {"type": "square", "width": 10, "height": 3, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
