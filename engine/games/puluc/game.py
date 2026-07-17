"""Puluc (Bul / Boolik) -- the Maya / Q'eqchi' running-fight game of Guatemala.

A single track of spaces (the gaps between a row of corn kernels) is shared by
both players, whose pieces enter from OPPOSITE ends and run toward each other.
Movement is by four corn-kernel dice, blackened on one side: the number of
black faces up is the move value, except that all-plain (0 black) counts FIVE
(Verbeeck 1998 / Wikipedia "Bul (game)"; see rules.md for the Sapper 1906
divergence).

The signature mechanic is capture-and-carry: landing EXACTLY on an
enemy-controlled piece or stack captures the whole stack -- it is placed
beneath the mover, which immediately REVERSES direction and carries its
prisoners back toward its own end. Passing off the board at its own end kills
the enemy prisoners permanently, frees any friendly pieces in the pile back to
the owner's hand, and returns the carrier to hand for re-entry. An enemy piece
landing exactly on a carrier captures the whole pile in turn (ownership flips
to the new top piece; your own former prisoners now ride home with you). A
free piece that runs the whole track without capturing returns to its owner's
hand and may re-enter later.

Randomness is modelled WITHOUT a chance node (platform standard, exactly as
daldos/sahkku): the throw for the player to move is rolled in
``initial_state``/``apply_move`` and STORED in the state; one throw = one move
= one turn. ``has_randomness`` is true.

Win: kill ALL five enemy pieces. A hard ply cap declares an honest DRAW.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from agp.game import Game

NAMES = {0: "Red", 1: "Blue"}
PIECES = 5
PLY_CAP = 3000           # hard cap -> honest draw [0, 0]
TRACKS = (9, 14, 21)     # documented board sizes (see rules.md)


@dataclass
class PulucState:
    # track[i] = [] (empty) or a list of piece-owners BOTTOM -> TOP. The TOP
    # piece's owner controls the pile. A pile of length 1 is a "free" piece
    # moving toward the enemy end; length > 1 is a CARRIER moving back toward
    # its controller's own end (a captured pile always contains an enemy).
    track: list = field(default_factory=list)
    hand: list = field(default_factory=lambda: [PIECES, PIECES])
    roll: int = 0            # the stored throw for the player to move
    to_move: int = 0
    ply: int = 0
    winner: object = None    # None (ongoing) | 0 | 1 | "draw"
    n: int = 9               # number of track spaces


class Puluc(Game):
    name = "Puluc"

    @property
    def num_players(self):
        return 2

    # -- dice ---------------------------------------------------------------
    @staticmethod
    def _roll(rng):
        """Four binary corn-kernel dice: value = number of black faces up,
        except 0 black (all plain) = 5 (Verbeeck 1998)."""
        blacks = sum(rng.randint(0, 1) for _ in range(4))
        return blacks if blacks > 0 else 5

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        options = options or {}
        n = int(options.get("track", 9))
        if n not in TRACKS:
            n = 9
        return PulucState(track=[[] for _ in range(n)],
                          hand=[PIECES, PIECES],
                          roll=self._roll(rng),
                          to_move=0, ply=0, winner=None, n=n)

    def current_player(self, s):
        return s.to_move

    # -- geometry helpers ---------------------------------------------------
    # Render cells: x = 0 is player 0's home (entry/bear-off), x = 1..n are
    # the track spaces (track index i -> cell x = i + 1), x = n + 1 is player
    # 1's home. Player 0 runs left->right (+1), player 1 right->left (-1).
    @staticmethod
    def _cell(i):
        return f"{i + 1},0"

    @staticmethod
    def _home_cell(pl, n):
        return "0,0" if pl == 0 else f"{n + 1},0"

    @staticmethod
    def _controls(track, pl, j):
        return bool(track[j]) and track[j][-1] == pl

    # -- move generation ----------------------------------------------------
    def _all_moves(self, s, pl):
        """Map move-string 'src>dst' -> (kind, i, j).

        kind: "enter" (from hand; j = landing index), "move" (i -> j on the
        track, capturing if an enemy pile is at j), "off" (i -> off the board:
        a free piece completing its run at the FAR end, or a carrier bearing
        off at its OWN end)."""
        out = {}
        r = s.roll
        n = s.n
        fwd = 1 if pl == 0 else -1
        if s.hand[pl] > 0:
            j = (r - 1) if pl == 0 else (n - r)
            if not self._controls(s.track, pl, j):
                out[f"{self._home_cell(pl, n)}>{self._cell(j)}"] = ("enter", None, j)
        for i, pile in enumerate(s.track):
            if not pile or pile[-1] != pl:
                continue
            carrying = len(pile) > 1
            d = -fwd if carrying else fwd     # a carrier heads back home
            j = i + d * r
            if 0 <= j < n:
                if self._controls(s.track, pl, j):
                    continue                  # never onto your own pile
                out[f"{self._cell(i)}>{self._cell(j)}"] = ("move", i, j)
            else:
                # off the board: a carrier exits at its OWN home end; a free
                # piece exits at the FAR (enemy) end. Reaching or passing the
                # end suffices -- no exact throw needed.
                edge = self._home_cell(pl if carrying else 1 - pl, n)
                out[f"{self._cell(i)}>{edge}"] = ("off", i, None)
        return out

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        moves = sorted(self._all_moves(s, s.to_move))
        if not moves:
            return ["pass"]   # nothing usable this throw; the turn is forfeit
        return moves

    # -- apply --------------------------------------------------------------
    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        pl = s.to_move
        opp = 1 - pl
        track = [list(pile) for pile in s.track]
        hand = list(s.hand)
        ply = s.ply + 1

        if move == "pass":
            if self.legal_moves(s) != ["pass"]:
                raise ValueError(f"illegal move {move} for {NAMES[pl]}")
        else:
            moves = self._all_moves(s, pl)
            if move not in moves:
                raise ValueError(f"illegal move {move} for {NAMES[pl]}")
            kind, i, j = moves[move]
            if kind == "enter":
                hand[pl] -= 1
                track[j] = track[j] + [pl]     # captures on entry if enemy
            elif kind == "move":
                track[j] = track[j] + track[i]  # enemy pile goes BENEATH
                track[i] = []
            else:  # "off"
                for owner in track[i]:
                    if owner == pl:
                        hand[pl] += 1          # carrier + freed friends
                    # enemy prisoners are killed: simply not returned
                track[i] = []

        winner = None
        alive_opp = hand[opp] + sum(pile.count(opp) for pile in track)
        if alive_opp == 0:
            winner = pl
        elif ply >= PLY_CAP:
            winner = "draw"

        if winner is not None:
            return PulucState(track=track, hand=hand, roll=0,
                              to_move=pl, ply=ply, winner=winner, n=s.n)
        return PulucState(track=track, hand=hand, roll=self._roll(rng),
                          to_move=opp, ply=ply, winner=None, n=s.n)

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None or s.winner == "draw":
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    def heuristic(self, s):
        alive = [s.hand[0], s.hand[1]]
        held = [0, 0]         # enemy pieces currently held prisoner
        for pile in s.track:
            for o in pile:
                alive[o] += 1
            if len(pile) > 1:
                top = pile[-1]
                held[top] += sum(1 for o in pile if o != top)
        v = math.tanh(0.45 * (alive[0] - alive[1]) + 0.2 * (held[0] - held[1]))
        return [v, -v]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s):
        return {
            "track": [list(pile) for pile in s.track],
            "hand": list(s.hand),
            "roll": s.roll,
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
            "n": s.n,
        }

    def deserialize(self, d):
        return PulucState(
            track=[list(pile) for pile in d["track"]],
            hand=list(d["hand"]),
            roll=d["roll"],
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
            n=d.get("n", 9),
        )

    # -- move log -----------------------------------------------------------
    def describe_move(self, s, move):
        pl = s.to_move
        if move == "pass":
            return f"{NAMES[pl]} (roll {s.roll}) — no legal move, passes"
        moves = self._all_moves(s, pl)
        kind, i, j = moves[move]
        frm_s, to_s = move.split(">")
        if kind == "enter":
            cap = bool(s.track[j])
            verb = "enters and captures at" if cap else "enters at"
            return f"{NAMES[pl]} {verb} {to_s} (roll {s.roll})"
        if kind == "move":
            if s.track[j]:
                total = len(s.track[j]) + len(s.track[i]) - 1
                return (f"{NAMES[pl]} {frm_s} captures at {to_s} — carries "
                        f"{total} prisoner(s) homeward (roll {s.roll})")
            verb = "carries prisoners to" if len(s.track[i]) > 1 else "to"
            return f"{NAMES[pl]} {frm_s} {verb} {to_s} (roll {s.roll})"
        # off
        pile = s.track[i]
        kills = sum(1 for o in pile if o != pl)
        if kills:
            mine = len(pile) - kills
            return (f"{NAMES[pl]} bears off at {frm_s}: kills {kills} "
                    f"prisoner(s), {mine} piece(s) return to hand "
                    f"(roll {s.roll})")
        return (f"{NAMES[pl]} {frm_s} completes the run and returns to hand "
                f"(roll {s.roll})")

    # -- render -------------------------------------------------------------
    def render(self, s, perspective=None):
        n = s.n
        tints = {self._home_cell(0, n): "#f3d7cf",
                 self._home_cell(1, n): "#cfdcf3"}
        for i in range(n):
            tints.setdefault(self._cell(i), "#f0e6c8")

        pieces = []
        for pl in (0, 1):
            h = s.hand[pl]
            if h > 1:
                pieces.append({"cell": self._home_cell(pl, n), "owner": pl,
                               "stack": [pl] * h})
            elif h == 1:
                pieces.append({"cell": self._home_cell(pl, n), "owner": pl})
        for i, pile in enumerate(s.track):
            if not pile:
                continue
            entry = {"cell": self._cell(i), "owner": pile[-1]}
            if len(pile) > 1:
                entry["stack"] = list(pile)
            pieces.append(entry)

        alive = [s.hand[0], s.hand[1]]
        for pile in s.track:
            for o in pile:
                alive[o] += 1
        tally = (f"{NAMES[0]}: {alive[0]} alive ({s.hand[0]} in hand) · "
                 f"{NAMES[1]}: {alive[1]} alive ({s.hand[1]} in hand)")
        if s.winner == "draw":
            caption = f"Draw (ply cap) · {tally}"
        elif s.winner is not None:
            caption = f"{NAMES[s.winner]} wins! · {tally}"
        else:
            caption = f"{NAMES[s.to_move]} to move, roll {s.roll} · {tally}"

        return {
            "board": {"type": "square", "width": n + 2, "height": 1,
                      "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
