"""Sáhkku -- the Sámi "running-fight" board game (the "Devil's game").

This package implements the **Vuovdaguoika / Gávkevuotna ruleset** as primary
(per Wikipedia "Sáhkku" it is the branch with unbroken living transmission),
verified against Wikipedia's per-ruleset writeup, Alan Borvo's Board Game
Studies 4 (2001) article and the Ludii DLP entry. See rules.md for source
quotes and every documented interpretation.

Sáhkku is kin to Daldøs (both are Nordic running-fight dice games) but a
DIFFERENT game: a 3x15 board of lines (sárgát) instead of a boat of holes, a
shared neutral KING (gonagas) that is recruited -- never captured -- and pushed
("cadjat") when landed on, THREE stick dice faced X("sáhkku")-III-II-blank
(blank = move FOUR, not zero), un-activated soldiers CAN be captured, and the
two armies run MIRRORED tracks so they meet head-on ("vuosttut").

Randomness is modelled WITHOUT a chance node (platform standard, exactly as in
daldos): the three dice for the player to move are rolled in
``initial_state``/``apply_move`` and stored in the state; each die is spent as
a separate ``apply_move`` ply by the SAME player, in any order (Vuovdaguoika:
"You may use the dice in any order you like"). ``has_randomness`` is true.

Die faces and values (Vuovdaguoika):
  X ("sáhkku")  -> activate a soldier (frontmost-first) OR move an activated
                   piece 1 sárggis; activation itself advances the soldier one
                   sárggis (general rule: "When activated, a soldier is moved
                   one sárggis ahead").
  II            -> move 2      III -> move 3
  blank         -> move 4 ("Blank signifies 'move four' instead of 'no move'")
A fresh throw of THREE X may optionally be rethrown ("Dice may only be
rethrown if a player gets 3*X") -- offered as the action move ``rethrow``.

The track (vuosttut): rightward along your own home row, leftward along the
middle row, rightward along the enemy home row, then looping middle <-> enemy
row forever -- soldiers NEVER return to their own home row. The optional
``miedut`` pattern reverses player 1's directions so the armies chase instead
of meeting head-on.

The king starts neutral on the Castle (centre of the middle row). Landing a
soldier on it RECRUITS it (it becomes your piece, moving like your soldiers --
except that, unlike a soldier, "it may pass (jump) soldiers of its own army")
and pushes it one sárggis ahead along your track; an enemy soldier on that
sárggis is "rammed" and captured. The king can never be captured, only
recruited back.

Win = remove ALL enemy soldiers. A hard ply cap declares an honest DRAW.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from agp.game import Game

NAMES = {0: "Red", 1: "Blue"}
W = 15                    # sárgát per row
CASTLE = (7, 1)           # centre of the middle row
PLY_CAP = 6000            # hard cap -> honest draw [0,0]
FACES = ("X", "2", "3", "B")          # the four faces of one stick die
DIE_STEPS = {"X": 1, "2": 2, "3": 3, "B": 4}
STEP_DIE = {1: "X", 2: "2", 3: "3", 4: "B"}
DIE_SHOW = {"X": "X", "2": "II", "3": "III", "B": "blank"}


@dataclass
class SahkkuState:
    # soldiers[pl] = list of {"cell": (c, r), "active": bool}; captured
    # soldiers are dropped entirely. Un-activated soldiers have never moved,
    # so they always stand on their original home-row cell.
    soldiers: dict = field(default_factory=dict)
    # king = {"cell": (c, r), "owner": None | 0 | 1}; owner None = neutral.
    king: dict = field(default_factory=dict)
    roll: tuple = ()      # the full triple rolled this turn (for display)
    dice: tuple = ()      # the UNUSED dice still to play this turn
    to_move: int = 0
    ply: int = 0
    winner: object = None  # None (ongoing) | 0 | 1 | "draw"
    pattern: str = "vuosttut"
    blocking: bool = True


class Sahkku(Game):
    name = "Sáhkku"

    @property
    def num_players(self):
        return 2

    # -- dice ---------------------------------------------------------------
    @staticmethod
    def _roll(rng):
        """Three four-sided stick dice, faces X / II / III / blank."""
        return tuple(FACES[rng.randint(0, 3)] for _ in range(3))

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        options = options or {}
        pattern = options.get("pattern", "vuosttut")
        blocking = options.get("blocking", "on") != "off"
        soldiers = {
            0: [{"cell": (c, 0), "active": False} for c in range(W)],
            1: [{"cell": (c, 2), "active": False} for c in range(W)],
        }
        roll = self._roll(rng)
        return SahkkuState(
            soldiers=soldiers,
            king={"cell": CASTLE, "owner": None},
            roll=roll, dice=roll, to_move=0, ply=0, winner=None,
            pattern=pattern, blocking=blocking,
        )

    def current_player(self, s):
        return s.to_move

    # -- track geometry -----------------------------------------------------
    @staticmethod
    def _home_row(pl):
        return 0 if pl == 0 else 2

    def _dirs(self, s, pl):
        """Column direction per row for player pl's directed track."""
        if pl == 0:
            return {0: 1, 1: -1, 2: 1}
        if s.pattern == "miedut":
            # player 1 reversed: same absolute circulation as player 0 (chase)
            return {2: 1, 1: -1, 0: 1}
        # vuosttut (default): mirrored -- the armies meet head-on
        return {2: -1, 1: 1, 0: -1}

    def _next_cell(self, s, pl, cell):
        """The next sárggis along player pl's directed track from `cell`.

        Row ends connect to the adjacent row at the SAME column: own home row
        end -> middle; middle end -> ENEMY home row; enemy row end -> middle.
        A soldier's own home row is only ever exited, never re-entered."""
        c, r = cell
        nc = c + self._dirs(s, pl)[r]
        if 0 <= nc < W:
            return (nc, r)
        if r == 1:
            return (c, 2 - self._home_row(pl))   # into the ENEMY home row
        return (c, 1)                            # any home-row end -> middle

    # -- helpers ------------------------------------------------------------
    def _own_soldier_cells(self, s, pl):
        return {x["cell"] for x in s.soldiers[pl]}

    def _frontmost_inactive(self, s, pl):
        """Index of the only soldier that may be activated next: the
        un-activated soldier furthest along the home-row marching direction.
        None if every surviving soldier is active."""
        hd = self._dirs(s, pl)[self._home_row(pl)]
        best, best_key = None, None
        for i, x in enumerate(s.soldiers[pl]):
            if x["active"]:
                continue
            key = hd * x["cell"][0]
            if best is None or key > best_key:
                best, best_key = i, key
        return best

    # -- move generation ----------------------------------------------------
    def _try(self, s, pl, kind, idx, d):
        """Return (src, dst) if this piece may move d steps, else None.

        kind: "s" = active soldier idx, "a" = activate inactive soldier idx
        (d is always 1), "k" = the king (owned by pl)."""
        if kind == "k":
            src = s.king["cell"]
        else:
            src = s.soldiers[pl][idx]["cell"]
        cells = []
        cur = src
        for _ in range(d):
            cur = self._next_cell(s, pl, cur)
            cells.append(cur)
        dst = cells[-1]
        own = self._own_soldier_cells(s, pl)
        # blocking rule: "a soldier may not jump (move past) a soldier of its
        # own army" (optional -- players may agree to waive it). The KING is
        # explicitly exempt: "unlike a normal soldier, it may pass (jump)
        # soldiers of its own army".
        if s.blocking and kind != "k" and any(c in own for c in cells[:-1]):
            return None
        if dst in own:
            return None      # never onto a sárggis occupied by your own army
        if kind != "k" and dst == s.king["cell"]:
            # recruit + push: the king goes one sárggis ahead along OUR track;
            # if our own soldier stands there the move is illegal (the king,
            # now ours, may not land on our own soldier).
            if self._next_cell(s, pl, dst) in own:
                return None
        return (src, dst)

    def _all_moves(self, s, pl):
        """Map move-string 'src>dst' -> (kind, idx, d, die) for unused dice."""
        out = {}
        movers = [("s", i) for i, x in enumerate(s.soldiers[pl]) if x["active"]]
        if s.king["owner"] == pl:
            movers.append(("k", None))
        for die in set(s.dice):
            d = DIE_STEPS[die]
            for kind, idx in movers:
                res = self._try(s, pl, kind, idx, d)
                if res:
                    src, dst = res
                    out[f"{src[0]},{src[1]}>{dst[0]},{dst[1]}"] = (kind, idx, d, die)
            if die == "X":
                fi = self._frontmost_inactive(s, pl)
                if fi is not None:
                    res = self._try(s, pl, "a", fi, 1)
                    if res:
                        src, dst = res
                        out[f"{src[0]},{src[1]}>{dst[0]},{dst[1]}"] = ("a", fi, 1, "X")
        return out

    def _can_rethrow(self, s):
        """A FRESH throw of three sáhkku (X,X,X) may be rethrown."""
        return (len(s.dice) == 3 and s.dice == s.roll
                and all(t == "X" for t in s.dice))

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        moves = sorted(self._all_moves(s, s.to_move))
        if self._can_rethrow(s):
            moves.append("rethrow")
        if not moves:
            return ["pass"]   # none of the remaining dice can be used
        return moves

    # -- apply --------------------------------------------------------------
    @staticmethod
    def _consume(dice, die):
        d = list(dice)
        d.remove(die)
        return tuple(d)

    def _copy(self, s):
        soldiers = {
            p: [{"cell": tuple(x["cell"]), "active": x["active"]}
                for x in s.soldiers[p]]
            for p in (0, 1)
        }
        king = {"cell": tuple(s.king["cell"]), "owner": s.king["owner"]}
        return soldiers, king

    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        pl = s.to_move
        opp = 1 - pl
        soldiers, king = self._copy(s)
        ply = s.ply + 1

        if move == "rethrow":
            if not self._can_rethrow(s):
                raise ValueError(f"illegal move {move} for {NAMES[pl]}")
            winner = "draw" if ply >= PLY_CAP else None
            new_roll = () if winner else self._roll(rng)
            return SahkkuState(soldiers=soldiers, king=king,
                               roll=new_roll, dice=new_roll,
                               to_move=pl, ply=ply, winner=winner,
                               pattern=s.pattern, blocking=s.blocking)

        if move == "pass":
            if self.legal_moves(s) != ["pass"]:
                raise ValueError(f"illegal move {move} for {NAMES[pl]}")
            remaining = ()   # the unused dice are forfeit; the turn ends
        else:
            moves = self._all_moves(s, pl)
            if move not in moves:
                raise ValueError(f"illegal move {move} for {NAMES[pl]}")
            kind, idx, d, die = moves[move]
            # recompute the destination
            cur = king["cell"] if kind == "k" else soldiers[pl][idx]["cell"]
            for _ in range(d):
                cur = self._next_cell(s, pl, cur)
            dst = cur
            if kind == "a":
                soldiers[pl][idx]["active"] = True
            if kind != "k" and dst == king["cell"]:
                # RECRUIT the king; push it one sárggis ahead; RAM any enemy
                # soldier standing there.
                pt = self._next_cell(s, pl, dst)
                soldiers[opp] = [x for x in soldiers[opp] if x["cell"] != pt]
                king = {"cell": pt, "owner": pl}
                soldiers[pl][idx]["cell"] = dst
            else:
                # exact landing on an enemy soldier captures it (un-activated
                # soldiers included -- Vuovdaguoika allows that).
                soldiers[opp] = [x for x in soldiers[opp] if x["cell"] != dst]
                if kind == "k":
                    king = {"cell": dst, "owner": king["owner"]}
                else:
                    soldiers[pl][idx]["cell"] = dst
            remaining = self._consume(s.dice, die)

        winner = None
        if not soldiers[opp]:
            winner = pl
        elif not soldiers[pl]:
            winner = opp
        if winner is None and ply >= PLY_CAP:
            winner = "draw"

        if winner is not None:
            return SahkkuState(soldiers=soldiers, king=king, roll=(), dice=(),
                               to_move=pl, ply=ply, winner=winner,
                               pattern=s.pattern, blocking=s.blocking)

        # same player continues while a remaining die is usable
        if remaining:
            probe = SahkkuState(soldiers=soldiers, king=king, roll=s.roll,
                                dice=remaining, to_move=pl, ply=ply,
                                winner=None, pattern=s.pattern,
                                blocking=s.blocking)
            if self._all_moves(probe, pl):
                return probe

        new_roll = self._roll(rng)
        return SahkkuState(soldiers=soldiers, king=king,
                           roll=new_roll, dice=new_roll,
                           to_move=opp, ply=ply, winner=None,
                           pattern=s.pattern, blocking=s.blocking)

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None or s.winner == "draw":
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    def heuristic(self, s):
        n0, n1 = len(s.soldiers[0]), len(s.soldiers[1])
        a0 = sum(1 for x in s.soldiers[0] if x["active"])
        a1 = sum(1 for x in s.soldiers[1] if x["active"])
        k = {0: 1, 1: -1}.get(s.king["owner"], 0)
        v = math.tanh(0.30 * (n0 - n1) + 0.04 * (a0 - a1) + 0.10 * k)
        return [v, -v]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s):
        return {
            "soldiers": {
                str(pl): [{"cell": f"{x['cell'][0]},{x['cell'][1]}",
                           "active": x["active"]} for x in v]
                for pl, v in s.soldiers.items()
            },
            "king": {"cell": f"{s.king['cell'][0]},{s.king['cell'][1]}",
                     "owner": s.king["owner"]},
            "roll": list(s.roll),
            "dice": list(s.dice),
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
            "pattern": s.pattern,
            "blocking": s.blocking,
        }

    @staticmethod
    def _cell(t):
        c, r = t.split(",")
        return (int(c), int(r))

    def deserialize(self, d):
        return SahkkuState(
            soldiers={
                int(pl): [{"cell": self._cell(x["cell"]),
                           "active": x["active"]} for x in v]
                for pl, v in d["soldiers"].items()
            },
            king={"cell": self._cell(d["king"]["cell"]),
                  "owner": d["king"]["owner"]},
            roll=tuple(d["roll"]),
            dice=tuple(d["dice"]),
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
            pattern=d.get("pattern", "vuosttut"),
            blocking=d.get("blocking", True),
        )

    # -- move log -----------------------------------------------------------
    def describe_move(self, s, move):
        pl = s.to_move
        if move == "pass":
            dice_s = ",".join(DIE_SHOW[t] for t in s.dice)
            return f"{NAMES[pl]} (dice {dice_s}) — no usable die, passes"
        if move == "rethrow":
            return f"{NAMES[pl]} rethrows the triple sáhkku (X,X,X)"
        moves = self._all_moves(s, pl)
        kind, idx, d, die = moves[move]
        frm_s, to_s = move.split(">")
        dst = self._cell(to_s)
        die_s = DIE_SHOW[die]
        who = "the king" if kind == "k" else f"{frm_s}"
        if kind != "k" and dst == s.king["cell"]:
            pt = self._next_cell(s, pl, dst)
            ram = any(x["cell"] == pt for x in s.soldiers[1 - pl])
            tail = " — the king RAMS a soldier!" if ram else ""
            verb = "activates and recruits" if kind == "a" else "recruits"
            return (f"{NAMES[pl]} {frm_s} {verb} the king at {to_s} "
                    f"({die_s}){tail}")
        cap = any(x["cell"] == dst for x in s.soldiers[1 - pl])
        if kind == "a":
            verb = "activates a soldier →" if not cap \
                else "activates a soldier, capturing at"
            return f"{NAMES[pl]} {verb} {to_s} (sáhkku)"
        verb = "captures at" if cap else "to"
        return f"{NAMES[pl]} {who} {verb} {to_s} ({die_s})"

    # -- render -------------------------------------------------------------
    def render(self, s, perspective=None):
        tints = {f"{c},1": "#f0e6c8" for c in range(W)}
        tints["7,1"] = "#e8c96b"   # the Castle

        pieces = []
        for pl in (0, 1):
            for x in s.soldiers[pl]:
                c, r = x["cell"]
                entry = {"cell": f"{c},{r}", "owner": pl}
                if not x["active"]:
                    entry["label"] = "·"
                pieces.append(entry)
        kc, kr = s.king["cell"]
        kentry = {"cell": f"{kc},{kr}", "glyph": "♚"}
        if s.king["owner"] is None:
            kentry["owner"] = 0
            kentry["fill"] = "#9e9e9e"
            kentry["stroke"] = "#5f6368"
        else:
            kentry["owner"] = s.king["owner"]
        pieces.append(kentry)

        n0, n1 = len(s.soldiers[0]), len(s.soldiers[1])
        kown = "neutral" if s.king["owner"] is None else NAMES[s.king["owner"]]
        tally = f"{NAMES[0]}: {n0} · {NAMES[1]}: {n1} · King: {kown}"
        if s.winner == "draw":
            caption = f"Draw (ply cap) · {tally}"
        elif s.winner is not None:
            caption = f"{NAMES[s.winner]} wins! · {tally}"
        else:
            dice_s = ",".join(DIE_SHOW[t] for t in s.dice) if s.dice else "—"
            caption = f"{NAMES[s.to_move]} to move, dice [{dice_s}] · {tally}"

        return {
            "board": {"type": "square", "width": W, "height": 3,
                      "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
