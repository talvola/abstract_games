"""Daldøs (Daldøsa) -- a traditional Scandinavian "running-fight" dice-war game
from Denmark and Norway, here in the well-attested standard ruleset (Wikipedia
"Daldøs" + the St. Thomas Guild reconstruction + boardandpieces.com).

Two players race their pieces around a boat-shaped board of three rows of holes
(each player's own outer "home" row plus a shared middle row) trying to remove
ALL the opponent's pieces by landing exactly on them. Movement is by TWO
four-sided long dice marked 1 ("dal"), 2, 3, 4. The signature mechanic is the
*dal*: a piece is dead-in-its-hole until "dalled" (activated by a roll of 1),
after which it moves freely; only a dalled, moving piece may capture.

Randomness is modelled WITHOUT a chance node (the platform's standard pattern,
as in EinStein / Royal Game of Ur): the dice for the player to move are stored
in the state. ``initial_state`` rolls the first pair with the supplied rng. A
TURN consumes the two dice ONE AT A TIME (each is a separate ``apply_move`` ply
by the SAME player, mirroring "both dice must be used if possible"); when the
dice are spent (or none of the remaining dice can be used) the next mover's pair
is rolled and stored. ``has_randomness`` is true.

THE PATH (verified, see rules.md for source quotes). A piece traverses:
  1. its HOME row toward the STERN,
  2. the MIDDLE row toward the PROW,
  3. the ENEMY home row (entered "from behind", the prow end) toward the stern,
  4. then back into the middle row, repeating middle<->enemy forever, never
     returning to its own home row.
A piece is removed permanently when an enemy piece lands exactly on its cell.

VARIANTS via manifest option ``size``: Norwegian 12+13+12 with 12 pieces
(default) or Danish 16+17+16 with 16 pieces.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

NAMES = {0: "Red", 1: "Blue"}
PLY_CAP = 6000  # hard draw cap so a shuffling capture-race always terminates


# ---------------------------------------------------------------------------
# Board geometry, parameterised by H = holes per home row.
#   y = 0  -> player 0's home row (cols 1..H)
#   y = 1  -> the SHARED middle row (cols 0..H ; M = H+1 holes, extra at prow)
#   y = 2  -> player 1's home row (cols 1..H)
# Stern is at HIGH x (right), prow at x = 0 (left, the middle row's extra hole).
# ---------------------------------------------------------------------------
def _geometry(H):
    M = H + 1
    home0 = [(c, 0) for c in range(1, H + 1)]
    home1 = [(c, 2) for c in range(1, H + 1)]
    middle = [(c, 1) for c in range(0, H + 1)]  # cols 0..H

    def _path(home_y, enemy_y):
        home = [(c, home_y) for c in range(1, H + 1)]            # toward stern
        mid = [(c, 1) for c in range(H, -1, -1)]                 # toward prow
        enemy = [(c, enemy_y) for c in range(1, H + 1)]          # toward stern
        return home, mid, enemy

    h0, mid0, e0 = _path(0, 2)
    h1, mid1, e1 = _path(2, 0)
    circuit0 = mid0 + e0           # length M + H ; repeats forever
    circuit1 = mid1 + e1
    return {
        "H": H, "M": M,
        "home": {0: h0, 1: h1},
        "circuit": {0: circuit0, 1: circuit1},
        "all_cells": home0 + middle + home1,
    }


SIZES = {"norwegian": 12, "danish": 16}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class DaldosState:
    # pieces[pl] = list of {"idx": int, "dalled": bool}. A captured piece is
    # dropped entirely.  idx is the position along player pl's reference path:
    #   0..H-1 : home row (idx = home-column-1). Undalled pieces sit here; a
    #            dalled piece in [0,H-1] is mid-home-row.
    #   >= H   : shared circuit at circuit[(idx-H) % len(circuit)].
    pieces: dict = field(default_factory=dict)
    roll: tuple = ()        # the FULL pair rolled this turn, for display
    dice: tuple = ()        # the UNUSED dice still to play this turn
    to_move: int = 0
    ply: int = 0
    winner: object = None
    H: int = 12


class Daldos(Game):
    uid = "daldos"
    name = "Daldøs"

    @property
    def num_players(self):
        return 2

    # -- dice ---------------------------------------------------------------
    @staticmethod
    def _roll(rng):
        """Two four-sided long dice, each 1..4 (face 1 = the 'dal')."""
        return (rng.randint(1, 4), rng.randint(1, 4))

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        options = options or {}
        size = options.get("size", "norwegian")
        H = SIZES.get(size, 12)
        pieces = {
            0: [{"idx": c, "dalled": False} for c in range(H)],
            1: [{"idx": c, "dalled": False} for c in range(H)],
        }
        roll = self._roll(rng)
        return DaldosState(pieces=pieces, roll=roll, dice=roll,
                           to_move=0, ply=0, winner=None, H=H)

    def current_player(self, s):
        return s.to_move

    # -- geometry helpers ---------------------------------------------------
    def _geo(self, s):
        return _geometry(s.H)

    def _abs_cell(self, geo, pl, idx):
        H = geo["H"]
        if idx < H:
            return geo["home"][pl][idx]
        circ = geo["circuit"][pl]
        return circ[(idx - H) % len(circ)]

    def _occupied(self, geo, s, pl, cell):
        for p in s.pieces[pl]:
            if self._abs_cell(geo, pl, p["idx"]) == cell:
                return True
        return False

    # -- move generation ----------------------------------------------------
    def _stern_undalled_index(self, s, pl):
        """Path index of the ONLY piece dallable next: the undalled piece
        closest to the stern (highest home column). None if none undalled."""
        best = None
        for p in s.pieces[pl]:
            if not p["dalled"]:
                if best is None or p["idx"] > best:
                    best = p["idx"]
        return best

    def _piece_die_move(self, geo, s, pl, die, pi):
        """The legal new_idx for piece pi using a SINGLE die value, or None.

        die==1 on an undalled piece is the dal-activation (only for the
        stern-most undalled piece, advancing one hole). Any die on a dalled
        piece advances it by that many holes (cannot land on own piece)."""
        p = s.pieces[pl][pi]
        if not p["dalled"]:
            if die == 1 and p["idx"] == self._stern_undalled_index(s, pl):
                return p["idx"] + 1
            return None
        new_idx = p["idx"] + die
        if self._occupied(geo, s, pl, self._abs_cell(geo, pl, new_idx)):
            return None
        return new_idx

    def _moves_for_die(self, geo, s, pl, die):
        """All 'src>dst' move strings achievable with one die value."""
        out = {}
        for pi, p in enumerate(s.pieces[pl]):
            new_idx = self._piece_die_move(geo, s, pl, die, pi)
            if new_idx is None:
                continue
            src = self._abs_cell(geo, pl, p["idx"])
            dst = self._abs_cell(geo, pl, new_idx)
            out[f"{src[0]},{src[1]}>{dst[0]},{dst[1]}"] = (pi, new_idx, die)
        return out

    def _all_moves(self, geo, s, pl):
        """Map move-string -> (pi, new_idx, die) over all UNUSED dice."""
        out = {}
        for die in set(s.dice):
            out.update(self._moves_for_die(geo, s, pl, die))
        return out

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        geo = self._geo(s)
        moves = self._all_moves(geo, s, s.to_move)
        if not moves:
            return ["pass"]  # none of the remaining dice can be used this turn
        return sorted(moves)

    # -- apply --------------------------------------------------------------
    def _consume_die(self, dice, die):
        """Return the dice tuple with one occurrence of `die` removed."""
        d = list(dice)
        d.remove(die)
        return tuple(d)

    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        geo = self._geo(s)
        pl = s.to_move
        pieces = {
            0: [dict(p) for p in s.pieces[0]],
            1: [dict(p) for p in s.pieces[1]],
        }

        if move == "pass":
            # the remaining dice are forfeit; the turn ends.
            remaining = ()
        else:
            moves = self._all_moves(geo, s, pl)
            if move not in moves:
                raise ValueError(f"illegal move {move} for {NAMES[pl]}")
            pi, new_idx, die = moves[move]
            pieces[pl][pi]["idx"] = new_idx
            pieces[pl][pi]["dalled"] = True
            dst = self._abs_cell(geo, pl, new_idx)
            opp = 1 - pl
            pieces[opp] = [
                p for p in pieces[opp]
                if self._abs_cell(geo, opp, p["idx"]) != dst
            ]
            remaining = self._consume_die(s.dice, die)

        # win = opponent has no pieces left.
        opp = 1 - pl
        winner = None
        if not pieces[opp]:
            winner = pl
        elif not pieces[pl]:
            winner = opp

        ply = s.ply + 1
        if winner is None and ply >= PLY_CAP:
            winner = self._leader(pieces)

        # Does the SAME player keep moving (dice left and at least one usable)?
        if winner is not None:
            return DaldosState(pieces=pieces, roll=(), dice=(),
                               to_move=pl, ply=ply, winner=winner, H=s.H)

        same_turn = False
        if remaining:
            probe = DaldosState(pieces=pieces, roll=s.roll, dice=remaining,
                                to_move=pl, ply=ply, winner=None, H=s.H)
            if self._all_moves(geo, probe, pl):
                same_turn = True

        if same_turn:
            return DaldosState(pieces=pieces, roll=s.roll, dice=remaining,
                               to_move=pl, ply=ply, winner=None, H=s.H)

        # turn ends -> roll for the opponent.
        new_roll = self._roll(rng)
        return DaldosState(pieces=pieces, roll=new_roll, dice=new_roll,
                           to_move=1 - pl, ply=ply, winner=None, H=s.H)

    @staticmethod
    def _leader(pieces):
        a, b = len(pieces[0]), len(pieces[1])
        if a == b:
            return 0
        return 0 if a > b else 1

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
            "pieces": {
                str(pl): [{"idx": p["idx"], "dalled": p["dalled"]} for p in v]
                for pl, v in s.pieces.items()
            },
            "roll": list(s.roll),
            "dice": list(s.dice),
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
            "H": s.H,
        }

    def deserialize(self, d):
        return DaldosState(
            pieces={
                int(pl): [{"idx": p["idx"], "dalled": p["dalled"]} for p in v]
                for pl, v in d["pieces"].items()
            },
            roll=tuple(d["roll"]),
            dice=tuple(d["dice"]),
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
            H=d.get("H", 12),
        )

    # -- move log -----------------------------------------------------------
    def describe_move(self, s, move):
        if move == "pass":
            return (f"{NAMES[s.to_move]} (dice {','.join(map(str, s.dice))}) "
                    f"— no usable die, passes")
        geo = self._geo(s)
        pl = s.to_move
        moves = self._all_moves(geo, s, pl)
        pi, new_idx, die = moves[move]
        was_dalled = s.pieces[pl][pi]["dalled"]
        dst = self._abs_cell(geo, pl, new_idx)
        cap = self._occupied(geo, s, 1 - pl, dst)
        frm_s, to_s = move.split(">")
        if not was_dalled:
            return f"{NAMES[pl]} dals a piece → {to_s}"
        verb = "captures at" if cap else "to"
        return f"{NAMES[pl]} {frm_s} {verb} {to_s} (die {die})"

    # -- render -------------------------------------------------------------
    def render(self, s, perspective=None):
        geo = self._geo(s)
        H = geo["H"]
        cells = []
        for (c, r) in geo["all_cells"]:
            x0, y0 = c, r
            pts = [[x0, y0], [x0 + 1, y0], [x0 + 1, y0 + 1], [x0, y0 + 1]]
            cells.append({"id": f"{c},{r}", "points": pts})

        lines = []
        for r in (0, 1, 2):
            row = sorted(c for c in geo["all_cells"] if c[1] == r)
            pts = [[c[0] + 0.5, c[1] + 0.5] for c in row]
            lines.append(pts + ["#8a6d3b"])

        tints = {f"{c},1": "#f0e6c8" for c in range(0, H + 1)}

        pieces = []
        for pl in (0, 1):
            for p in s.pieces[pl]:
                c, r = self._abs_cell(geo, pl, p["idx"])
                entry = {"cell": f"{c},{r}", "owner": pl}
                if not p["dalled"]:
                    entry["label"] = "·"
                pieces.append(entry)

        n0, n1 = len(s.pieces[0]), len(s.pieces[1])
        tally = f"{NAMES[0]}: {n0} pieces  ·  {NAMES[1]}: {n1} pieces"
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins!  ·  {tally}"
        else:
            dice_s = ",".join(map(str, s.dice)) if s.dice else "—"
            has_move = self.legal_moves(s) != ["pass"]
            extra = "" if has_move else " (no usable die — pass)"
            caption = (f"{NAMES[s.to_move]} to move, dice [{dice_s}]{extra}"
                       f"  ·  {tally}")

        return {
            "board": {"type": "polygons", "cells": cells,
                      "lines": lines, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
