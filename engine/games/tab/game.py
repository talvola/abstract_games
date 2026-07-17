"""Tâb -- the Egyptian/Middle-Eastern "running-fight" dice-war game, root of the
tâb/sîg/tablan family, in the ruleset recorded by Edward William Lane in Cairo
in the 1820s (Lane, "An Account of the Manners and Customs of the Modern
Egyptians", 5th ed. 1860, pp. 346-349 -- the primary historical description),
cross-checked against Wikipedia "Tâb" and the Ludii DLP entry (DLP.Games.129,
evidence: Lane 1836; Murray 1951: 95). See rules.md for source quotes and every
documented interpretation.

Two players each fill their own outer row of a 4xN board (N odd, 7..15; Lane's
own worked diagram uses 9) with one piece ("kelb") per square. Four two-sided
stick dice give throws 1 ("tâb"), 2, 3, 4 and 6 ("sitteh", all-black); a throw
of 1, 4 or 6 earns another throw. A player throws a whole CHAIN first, banking
the values, then spends them in any order, each on any one piece -- Lane:
"[having] thrown tab (or one), and then four, and then two, he may take the
kelb in o by the throw of two; then, by the throw of four, take that in s; and,
by the throw of tab, pass into a".

A piece is a dead "Christian" until converted to a "Muslim" by a tâb throw
(one conversion per tâb, foremost piece first, advancing it one square). Pieces
run a boustrophedon track: own home row, then an endless loop of the two middle
rows, with a once-only optional detour through the ENEMY home row (allowed only
while enemy pieces remain there; a piece parked there is frozen while any own
piece remains in one's own home row). Landing on enemy pieces captures the
whole pile; landing on your own Muslims unites them into a stack ("'eggeh")
that moves as one, splits only with a tâb, and is cut down to a single kelb if
moved back into a row it has already passed through. Capture ALL enemy pieces
to win; a no-progress/hard ply cap declares an honest draw.

Randomness is modelled WITHOUT a chance node (platform standard, as daldos /
sahkku): the throw chain for the player to move is rolled inside
``initial_state``/``apply_move`` and stored in the state; each banked value is
spent as a separate ``apply_move`` ply by the SAME player.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from agp.game import Game

NAMES = {0: "Red", 1: "Blue"}
SIZES = (7, 9, 11, 13, 15)          # squares per row (Lane: "seven, nine,
DEFAULT_N = 9                        # eleven, thirteen, or fifteen"; his
                                     # illustrative board is 9)
# throw value by number of white (flat) faces up; 0 white = "sitteh" = 6.
THROW_VALUE = {0: 6, 1: 1, 2: 2, 3: 3, 4: 4}
EXTRA = {1, 4, 6}                    # these throws earn another throw
CHAIN_CAP = 40                       # safety bound on a throw chain (P~1e-17)
PLY_CAP = 8000                       # hard cap -> honest draw
NO_PROGRESS_CAP = 500                # plies without capture/conversion -> draw

HOME_ROW = {0: 3, 1: 0}              # seat -> its home row (r=0 top, r=3 bottom)


def _show(v):
    return "tâb" if v == 1 else str(v)


def _cell_s(cell):
    return f"{cell[0]},{cell[1]}"


def _cell_t(s):
    c, r = s.split(",")
    return (int(c), int(r))


@dataclass
class TabState:
    # groups[seat] = list of piece-groups:
    #   {"cell": (c, r), "count": int, "conv": bool,
    #    "visited": frozenset(rows), "entered": bool}
    # A Christian (conv=False) is always a count-1 group on its original square.
    # Captured pieces are removed entirely; a stack "reduction" also removes
    # pieces from the board (they are not captured by anyone).
    groups: dict = field(default_factory=dict)
    roll: tuple = ()      # the full throw chain of this turn (for display)
    bank: tuple = ()      # the UNSPENT values of the chain
    to_move: int = 0
    ply: int = 0
    np: int = 0           # plies since last capture/conversion (progress)
    winner: object = None  # None | 0 | 1 | "draw"
    N: int = DEFAULT_N


class Tab(Game):
    name = "Tâb"

    @property
    def num_players(self):
        return 2

    # -- dice ---------------------------------------------------------------
    @staticmethod
    def _throw(rng):
        """One throw of the four two-sided stick dice."""
        whites = sum(rng.randint(0, 1) for _ in range(4))
        return THROW_VALUE[whites]

    @classmethod
    def _chain(cls, rng):
        """A full throw chain: 1/4/6 earn another throw; a 2 or 3 ends it."""
        out = []
        while True:
            v = cls._throw(rng)
            out.append(v)
            if v not in EXTRA or len(out) >= CHAIN_CAP:
                return tuple(out)

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        options = options or {}
        N = int(options.get("size", DEFAULT_N))
        if N not in SIZES:
            N = DEFAULT_N
        groups = {
            seat: [{"cell": (c, HOME_ROW[seat]), "count": 1, "conv": False,
                    "visited": frozenset({HOME_ROW[seat]}), "entered": False}
                   for c in range(N)]
            for seat in (0, 1)
        }
        roll = self._chain(rng)
        return TabState(groups=groups, roll=roll, bank=roll,
                        to_move=0, ply=0, np=0, winner=None, N=N)

    def current_player(self, s):
        return s.to_move

    # -- track geometry -----------------------------------------------------
    # r=0 is the top row (seat 1's home), r=3 the bottom row (seat 0's home).
    # Both players circulate the SAME directed loop through the middle rows
    # (Lane: "from K to S, and from k to s"): r=2 right-to-left, up, r=1
    # left-to-right, down. Seat 0: home r=3 left-to-right, exit up into the
    # loop at (N-1,2); branch square (N-1,1) -> continue down to (N-1,2) or
    # enter the enemy home row at (N-1,0), traversing it right-to-left and
    # rejoining the loop at (0,1). Seat 1 is the 180-degree mirror.
    @staticmethod
    def _succ(N, seat, cell):
        """Successor squares of `cell` on `seat`'s directed track, as a list
        of (next_cell, is_enemy_home_entry). The branch square yields two."""
        c, r = cell
        if seat == 0:
            if r == 3:
                return [((c + 1, 3), False)] if c < N - 1 else [((N - 1, 2), False)]
            if r == 2:
                return [((c - 1, 2), False)] if c > 0 else [((0, 1), False)]
            if r == 1:
                if c < N - 1:
                    return [((c + 1, 1), False)]
                return [((N - 1, 2), False), ((N - 1, 0), True)]   # branch
            # r == 0: inside the enemy home row
            return [((c - 1, 0), False)] if c > 0 else [((0, 1), False)]
        else:
            if r == 0:
                return [((c - 1, 0), False)] if c > 0 else [((0, 1), False)]
            if r == 1:
                return [((c + 1, 1), False)] if c < N - 1 else [((N - 1, 2), False)]
            if r == 2:
                if c > 0:
                    return [((c - 1, 2), False)]
                return [((0, 1), False), ((0, 3), True)]           # branch
            # r == 3: inside the enemy home row
            return [((c + 1, 3), False)] if c < N - 1 else [((N - 1, 2), False)]

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _total(groups):
        return sum(g["count"] for g in groups)

    def _enemy_home_has_enemy(self, s, seat):
        """Any opponent piece still in the opponent's own home row? (entry
        into that row is only allowed while there is -- Lane/Ludii)."""
        opp = 1 - seat
        row = HOME_ROW[opp]
        return any(g["cell"][1] == row for g in s.groups[opp])

    def _frozen(self, s, seat, g):
        """A piece in the ENEMY home row may not move while any own piece
        remains in one's OWN home row -- unless the own-home-row force is a
        single united stack ('eggeh)."""
        if g["cell"][1] != HOME_ROW[1 - seat]:
            return False
        home = [x for x in s.groups[seat] if x["cell"][1] == HOME_ROW[seat]]
        if not home:
            return False
        if len(home) == 1 and home[0]["count"] >= 2:
            return False   # the 'eggeh exception (Lane / Ludii)
        return True

    def _foremost_christian(self, s, seat):
        """Index of the only piece convertible next: the unconverted piece
        nearest its home-row exit (Lane: 'must always commence with the kelb
        in beyt I'). None if all pieces are converted."""
        best, best_key = None, None
        for i, g in enumerate(s.groups[seat]):
            if g["conv"]:
                continue
            c = g["cell"][0]
            key = c if seat == 0 else -c
            if best is None or key > best_key:
                best, best_key = i, key
        return best

    def _own_at(self, s, seat, cell):
        for i, g in enumerate(s.groups[seat]):
            if g["cell"] == cell:
                return i
        return None

    # -- move generation ----------------------------------------------------
    def _walk(self, s, seat, g, v, converting=False):
        """All ways group `g` can move `v` steps. Returns a list of dicts
        {dst, path, red, entered}: `path` = the stepped cells, `red` = the move
        re-enters a row the group has already passed through (stack-reduction
        trigger if the moving pile has 2+ pieces), `entered` = the move steps
        into the enemy home row (spending the once-only entry)."""
        N = s.N
        allow_entry = (not g["entered"]) and self._enemy_home_has_enemy(s, seat)
        outs = []

        def step(cell, left, path, entered):
            if left == 0:
                # analyse the path for row re-entry
                visited = set(g["visited"])
                prev_r = g["cell"][1]
                red = False
                for pcell in path:
                    r = pcell[1]
                    if r != prev_r and r in visited:
                        red = True
                    visited.add(r)
                    prev_r = r
                outs.append({"dst": cell, "path": list(path), "red": red,
                             "entered": entered,
                             "visited": frozenset(visited)})
                return
            for nc, is_entry in self._succ(N, seat, cell):
                if is_entry and (entered or not allow_entry or converting):
                    continue
                path.append(nc)
                step(nc, left - 1, path, entered or is_entry)
                path.pop()

        step(g["cell"], v, [], False)
        return outs

    def _land_ok(self, s, seat, dst):
        """A move may finish on `dst` unless one's OWN CHRISTIAN sits there
        (Muslims unite, enemies are captured)."""
        i = self._own_at(s, seat, dst)
        return i is None or s.groups[seat][i]["conv"]

    def _all_moves(self, s, seat):
        """Map move-string -> descriptor for every unspent value.

        descriptor = (kind, gi, v, dst, red, entered)
          kind: "m" move whole group | "s" split one kelb off a stack (tâb
                only) | "c" convert the foremost Christian (tâb only)."""
        out = {}
        for v in set(s.bank):
            for gi, g in enumerate(s.groups[seat]):
                if not g["conv"]:
                    continue
                if self._frozen(s, seat, g):
                    continue
                for w in self._walk(s, seat, g, v):
                    if not self._land_ok(s, seat, w["dst"]):
                        continue
                    base = f"{_cell_s(g['cell'])}>{_cell_s(w['dst'])}"
                    if v == 1 and g["count"] >= 2:
                        # a tâb on a stack: move it whole, or split one off
                        out[base + "=ALL"] = ("m", gi, v, w["dst"],
                                              w["red"], w["entered"])
                        out[base + "=ONE"] = ("s", gi, v, w["dst"],
                                              False, w["entered"])
                    else:
                        out[base] = ("m", gi, v, w["dst"],
                                     w["red"] and g["count"] >= 2,
                                     w["entered"])
            if v == 1:
                fi = self._foremost_christian(s, seat)
                if fi is not None:
                    g = s.groups[seat][fi]
                    for w in self._walk(s, seat, g, 1, converting=True):
                        if not self._land_ok(s, seat, w["dst"]):
                            continue
                        base = f"{_cell_s(g['cell'])}>{_cell_s(w['dst'])}"
                        out[base] = ("c", fi, 1, w["dst"], False, w["entered"])
        return out

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        moves = self._all_moves(s, s.to_move)
        if not moves:
            return ["pass"]
        out = sorted(moves)
        if all(d[4] for d in moves.values()):
            # every available move would cut a stack down -- Lane: "he need
            # not avail himself of such a throw"; the player may decline.
            out.append("pass")
        return out

    # -- apply --------------------------------------------------------------
    @staticmethod
    def _consume(bank, v):
        b = list(bank)
        b.remove(v)
        return tuple(b)

    @staticmethod
    def _copy_groups(groups):
        return {
            seat: [{"cell": tuple(g["cell"]), "count": g["count"],
                    "conv": g["conv"], "visited": frozenset(g["visited"]),
                    "entered": g["entered"]} for g in v]
            for seat, v in groups.items()
        }

    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        seat = s.to_move
        opp = 1 - seat
        groups = self._copy_groups(s.groups)
        ply = s.ply + 1
        progress = False

        if move == "pass":
            if "pass" not in self.legal_moves(s):
                raise ValueError(f"illegal move {move} for {NAMES[seat]}")
            bank = ()   # the unused throws are forfeit; the turn ends
        else:
            moves = self._all_moves(s, seat)
            if move not in moves:
                raise ValueError(f"illegal move {move} for {NAMES[seat]}")
            kind, gi, v, dst, red, entered = moves[move]
            g = groups[seat][gi]
            w = next(x for x in self._walk(s, seat, s.groups[seat][gi], v,
                                           converting=(kind == "c"))
                     if x["dst"] == dst)

            if kind == "s":
                # split one kelb off the stack; the rest stay put
                g["count"] -= 1
                mover = {"cell": dst, "count": 1, "conv": True,
                         "visited": w["visited"],
                         "entered": g["entered"] or w["entered"]}
            else:
                if kind == "c":
                    g["conv"] = True
                    progress = True   # a conversion is progress
                mover = g
                groups[seat] = [x for i, x in enumerate(groups[seat]) if i != gi]
                mover["cell"] = dst
                mover["visited"] = w["visited"]
                mover["entered"] = mover["entered"] or w["entered"]
                if red and mover["count"] >= 2:
                    # the stack re-entered a row it had already passed
                    # through: it is reduced to a single kelb
                    mover["count"] = 1
                    progress = True

            # capture: the whole enemy pile on dst leaves the board
            before = self._total(groups[opp])
            groups[opp] = [x for x in groups[opp] if x["cell"] != dst]
            if self._total(groups[opp]) < before:
                progress = True

            # unite with an own Muslim pile on dst
            oi = self._own_at_g(groups[seat], dst, exclude=mover)
            if oi is not None:
                other = groups[seat][oi]
                other["count"] += mover["count"]
                other["visited"] = mover["visited"] | other["visited"]
                other["entered"] = mover["entered"] or other["entered"]
            else:
                groups[seat].append(mover)
            bank = self._consume(s.bank, v)

        np = 0 if progress else s.np + 1
        winner = None
        if not groups[opp]:
            winner = seat
        elif not groups[seat]:
            winner = opp
        if winner is None and (ply >= PLY_CAP or np >= NO_PROGRESS_CAP):
            winner = "draw"

        if winner is not None:
            return TabState(groups=groups, roll=(), bank=(), to_move=seat,
                            ply=ply, np=np, winner=winner, N=s.N)

        # same player continues while a banked value remains usable
        if bank:
            probe = TabState(groups=groups, roll=s.roll, bank=bank,
                             to_move=seat, ply=ply, np=np, winner=None, N=s.N)
            if self._all_moves(probe, seat):
                return probe

        new_roll = self._chain(rng)
        return TabState(groups=groups, roll=new_roll, bank=new_roll,
                        to_move=opp, ply=ply, np=np, winner=None, N=s.N)

    @staticmethod
    def _own_at_g(glist, cell, exclude=None):
        for i, g in enumerate(glist):
            if g is not exclude and g["cell"] == cell:
                return i
        return None

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None or s.winner == "draw":
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    def heuristic(self, s):
        n0, n1 = self._total(s.groups[0]), self._total(s.groups[1])
        c0 = sum(g["count"] for g in s.groups[0] if g["conv"])
        c1 = sum(g["count"] for g in s.groups[1] if g["conv"])
        v = math.tanh(0.30 * (n0 - n1) + 0.04 * (c0 - c1))
        return [v, -v]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s):
        return {
            "groups": {
                str(seat): [{"cell": _cell_s(g["cell"]), "count": g["count"],
                             "conv": g["conv"],
                             "visited": sorted(g["visited"]),
                             "entered": g["entered"]} for g in v]
                for seat, v in s.groups.items()
            },
            "roll": list(s.roll),
            "bank": list(s.bank),
            "to_move": s.to_move,
            "ply": s.ply,
            "np": s.np,
            "winner": s.winner,
            "N": s.N,
        }

    def deserialize(self, d):
        return TabState(
            groups={
                int(seat): [{"cell": _cell_t(g["cell"]), "count": g["count"],
                             "conv": g["conv"],
                             "visited": frozenset(g["visited"]),
                             "entered": g["entered"]} for g in v]
                for seat, v in d["groups"].items()
            },
            roll=tuple(d["roll"]),
            bank=tuple(d["bank"]),
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            np=d.get("np", 0),
            winner=d.get("winner"),
            N=d.get("N", DEFAULT_N),
        )

    # -- move log -----------------------------------------------------------
    def describe_move(self, s, move):
        seat = s.to_move
        if move == "pass":
            shown = ",".join(_show(v) for v in s.bank) if s.bank else "—"
            return f"{NAMES[seat]} (throws {shown}) — passes, forfeiting them"
        moves = self._all_moves(s, seat)
        kind, gi, v, dst, red, entered = moves[move]
        frm = _cell_s(s.groups[seat][gi]["cell"])
        to = _cell_s(dst)
        cap = self._own_at(s, 1 - seat, dst) is not None
        join = self._own_at(s, seat, dst) is not None
        tail = ""
        if entered:
            tail += " — enters the enemy row"
        if red:
            tail += " — the stack is cut down to one kelb"
        if kind == "c":
            verb = "converts a kelb (tâb) →"
            if cap:
                verb = "converts a kelb (tâb), capturing at"
            return f"{NAMES[seat]} {verb} {to}{tail}"
        if kind == "s":
            what = f"splits one kelb off {frm} → {to} (tâb)"
            if cap:
                what += ", capturing"
        else:
            verb = "captures at" if cap else ("joins the pile at" if join else "to")
            what = f"{frm} {verb} {to} ({_show(v)})"
        return f"{NAMES[seat]} {what}{tail}"

    # -- render -------------------------------------------------------------
    def render(self, s, perspective=None):
        N = s.N
        tints = {}
        for c in range(N):
            tints[f"{c},1"] = "#f0e6c8"
            tints[f"{c},2"] = "#f0e6c8"
        tints[f"{N-1},1"] = "#e8d49a"   # seat 0's branch square (Lane's "s")
        tints["0,2"] = "#e8d49a"        # seat 1's branch square (Lane's "S")

        pieces = []
        for seat in (0, 1):
            for g in s.groups[seat]:
                entry = {"cell": _cell_s(g["cell"]), "owner": seat}
                if not g["conv"]:
                    entry["label"] = "·"       # sleeper convention (daldos)
                elif g["count"] >= 2:
                    entry["stack"] = [seat] * g["count"]
                pieces.append(entry)

        n0, n1 = self._total(s.groups[0]), self._total(s.groups[1])
        tally = f"{NAMES[0]}: {n0} · {NAMES[1]}: {n1}"
        if s.winner == "draw":
            caption = f"Draw · {tally}"
        elif s.winner is not None:
            caption = f"{NAMES[s.winner]} wins! · {tally}"
        else:
            shown = ",".join(_show(v) for v in s.bank) if s.bank else "—"
            caption = f"{NAMES[s.to_move]} to move, throws [{shown}] · {tally}"

        return {
            "board": {"type": "square", "width": N, "height": 4,
                      "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
            "choiceTitle": "Stack",
            "choiceNames": {"ALL": "Move the whole stack",
                            "ONE": "Split off one kelb"},
        }
