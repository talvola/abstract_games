"""Backgammon -- the classic race-and-block dice game (single-game version).

Two players (White & Black) each race 15 checkers around a 24-point board into
their own home quadrant and then bear them off; first to bear off all 15 wins.

Standard rules (Wikipedia "Backgammon" / USBGF). Implemented faithfully EXCEPT:

  * NO DOUBLING CUBE. The cube is a stake-betting layer, not board movement, so
    it is omitted; gammon/backgammon multipliers are meaningless without stakes,
    so a win is simply a win (+1 / -1).
  * OPENING SIMPLIFIED. Real backgammon decides the first move by each player
    rolling a single die (higher goes first, playing both). Here White (player 0)
    simply moves first with a freshly rolled pair. (Documented in rules.md.)

Randomness WITHOUT a chance node (the platform's standard pattern, as in the
Royal Game of Ur / Daldøs / Pachisi): the dice for the player to move are stored
in the state. ``initial_state`` rolls White's first pair with the supplied rng.
A TURN is consumed ONE DIE AT A TIME -- each ``apply_move`` plays a single die as
one sub-move (move one checker) and keeps the SAME player to move until the dice
are spent OR no remaining die can be legally played; then the next player's pair
is rolled and stored. A double (e.g. 3-3) yields FOUR moves of that value.
``has_randomness`` is true.

The "MUST USE BOTH DICE IF POSSIBLE" rule is enforced exactly per the official
ruleset: legal sub-moves are restricted to those that lie on a turn-sequence
using the MAXIMUM possible number of dice (and, when exactly one die can be
played, the larger if only one of the two is playable). This is computed by a
small recursive search over the remaining dice at each ply (``_max_usable``).

POINT NUMBERING (absolute, 1..24). White moves from high points toward point 1
and bears off past point 1 (White home = points 1..6). Black moves from low
points toward point 24 and bears off past point 24 (Black home = points 19..24).
A checker on the BAR must re-enter into the opponent's home quadrant before any
other move; it cannot be borne off until all 15 are home.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
NCHK = 15
PLY_CAP = 4000   # hard draw cap; random play always terminates (see note below)


# Starting positions, as absolute point -> count, for White.  White moves
# 24 -> 1.  Black is the 25-p mirror (Black moves 1 -> 24).  Each layout has 15
# checkers a side except Hypergammon (3 a side).
WHITE_START = {24: 2, 13: 5, 8: 3, 6: 5}                 # standard backgammon
SETUPS = {
    "standard":   {24: 2, 13: 5, 8: 3, 6: 5},            # 15 checkers
    "nackgammon": {24: 2, 23: 2, 13: 4, 8: 3, 6: 4},     # 15 checkers (Nack Ballard)
    "hypergammon": {24: 1, 23: 1, 22: 1},                # 3 checkers (Hyper-backgammon)
}


def _mirror(p):
    """Absolute point seen from the other player's direction."""
    return 25 - p


def _start_points(setup="standard"):
    """Return {point: (owner, count)} for the chosen opening setup.

    White and Black occupy mirror points, which never coincide, so each point
    holds at most one owner."""
    pts = {}
    for p, n in SETUPS[setup].items():
        pts[p] = (WHITE, n)
        pts[_mirror(p)] = (BLACK, n)
    return pts


@dataclass
class BgState:
    # board[point] = (owner, count) for points 1..24 that are occupied.
    board: dict = field(default_factory=dict)
    bar: dict = field(default_factory=lambda: {WHITE: 0, BLACK: 0})
    off: dict = field(default_factory=lambda: {WHITE: 0, BLACK: 0})
    roll: tuple = ()        # the FULL pair rolled this turn (for display)
    dice: tuple = ()        # the UNUSED die values still to play this turn
    to_move: int = WHITE
    ply: int = 0
    winner: object = None


class Backgammon(Game):
    uid = "backgammon"
    name = "Backgammon"

    @property
    def num_players(self):
        return 2

    # -- dice ---------------------------------------------------------------
    @staticmethod
    def _roll(rng):
        return (rng.randint(1, 6), rng.randint(1, 6))

    @staticmethod
    def _expand(roll):
        """Dice list to play this turn: doubles give four of that value."""
        a, b = roll
        return (a, a, a, a) if a == b else (a, b)

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        setup = (options or {}).get("setup", "standard")
        if setup not in SETUPS:
            setup = "standard"
        roll = self._roll(rng)
        return BgState(
            board=_start_points(setup),
            bar={WHITE: 0, BLACK: 0},
            off={WHITE: 0, BLACK: 0},
            roll=roll,
            dice=self._expand(roll),
            to_move=WHITE,
            ply=0,
            winner=None,
        )

    def current_player(self, s):
        return s.to_move

    # -- direction helpers --------------------------------------------------
    @staticmethod
    def _home_index(pl, p):
        """Pip distance of point p from bearing off (1..6 inside home)."""
        return p if pl == WHITE else _mirror(p)

    @staticmethod
    def _entry_point(pl, die):
        """Where a bar checker lands when entering with `die`."""
        return _mirror(die) if pl == WHITE else die   # White: 25-die; Black: die

    @staticmethod
    def _dest_point(pl, p, die):
        """Absolute point reached moving a checker from p by `die` (no bounds)."""
        return p - die if pl == WHITE else p + die

    # -- board queries ------------------------------------------------------
    @staticmethod
    def _owner_count(board, p):
        return board.get(p, (None, 0))

    def _blocked(self, board, pl, p):
        """True if point p is held by 2+ enemy checkers (cannot land)."""
        o, n = self._owner_count(board, p)
        return o == (1 - pl) and n >= 2

    def _total(self, s, pl):
        """This player's total checker count (board + bar + off). Invariant over a
        game; 15 for standard/nackgammon, 3 for hypergammon."""
        return (s.off[pl] + s.bar[pl]
                + sum(n for (o, n) in s.board.values() if o == pl))

    def _all_home(self, s, pl):
        """All of pl's checkers are in the home quadrant (none on bar/outside)."""
        if s.bar[pl]:
            return False
        for p, (o, n) in s.board.items():
            if o == pl and not (1 <= self._home_index(pl, p) <= 6):
                return False
        return True

    def _highest_home_index(self, s, pl):
        """Largest occupied home-index for pl (for the bear-off 'overshoot' rule)."""
        hi = 0
        for p, (o, n) in s.board.items():
            if o == pl:
                hi = max(hi, self._home_index(pl, p))
        return hi

    # -- single-die sub-move generation -------------------------------------
    def _submoves_for_die(self, s, pl, die):
        """All legal sub-moves (move strings) using ONE die value, on state s.

        If pl has checkers on the bar, ONLY entering moves are produced (the bar
        must be cleared first). Encodings:
          ``"bar>P"``  enter from the bar onto point P
          ``"F>T"``    advance a checker from point F to point T
          ``"F>off"``  bear off the checker on point F
        """
        board = s.board
        out = {}   # move-string -> ("enter"/"move"/"off", from, to)

        if s.bar[pl]:
            p = self._entry_point(pl, die)
            if not self._blocked(board, pl, p):
                out[f"bar>{p}"] = ("enter", None, p)
            return out

        home = self._all_home(s, pl)
        hi = self._highest_home_index(s, pl) if home else 0

        for p, (o, n) in board.items():
            if o != pl or n <= 0:
                continue
            dest = self._dest_point(pl, p, die)
            if 1 <= dest <= 24:
                if not self._blocked(board, pl, dest):
                    out[f"{p}>{dest}"] = ("move", p, dest)
            elif home:
                # dest is past the edge -> a bear-off candidate.
                hidx = self._home_index(pl, p)
                if hidx == die:
                    out[f"{p}>off"] = ("off", p, None)   # exact bear-off
                elif die > hidx and hidx == hi:
                    # overshoot allowed ONLY from the highest occupied point.
                    out[f"{p}>off"] = ("off", p, None)
        return out

    # -- max-dice usage (the "must use both if possible" rule) --------------
    def _max_usable(self, s, pl, dice):
        """Maximum number of the given dice playable over the rest of the turn.

        Recursive: try each distinct die, apply the resulting sub-move, recurse
        on the remaining dice, and take the best. Pure look-ahead (no winner /
        roll bookkeeping). Cheap: depth <= 4, branching small."""
        if not dice:
            return 0
        best = 0
        for die in set(dice):
            subs = self._submoves_for_die(s, pl, die)
            if not subs:
                continue
            rest = list(dice)
            rest.remove(die)
            for kind, frm, to in subs.values():
                ns = self._apply_sub(s, pl, kind, frm, to)
                got = 1 + self._max_usable(ns, pl, tuple(rest))
                if got > best:
                    best = got
                    if best == len(dice):
                        return best   # cannot do better
        return best

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        pl = s.to_move
        target = self._max_usable(s, pl, s.dice)
        if target == 0:
            return ["pass"]   # no remaining die can be legally played
        # Offer only sub-moves that PRESERVE the maximum dice usage: after
        # playing this sub-move, the rest of the turn must still reach target-1.
        moves = set()
        for die in set(s.dice):
            subs = self._submoves_for_die(s, pl, die)
            if not subs:
                continue
            rest = list(s.dice)
            rest.remove(die)
            for mv, (kind, frm, to) in subs.items():
                ns = self._apply_sub(s, pl, kind, frm, to)
                if 1 + self._max_usable(ns, pl, tuple(rest)) == target:
                    moves.add(mv)
        return sorted(moves)

    # -- apply a single sub-move (no turn/roll logic) -----------------------
    def _apply_sub(self, s, pl, kind, frm, to):
        """Return a new BgState with one checker moved; pure board update.

        Handles hitting an enemy blot (sent to the bar). Does NOT touch dice,
        to_move, winner, or ply -- callers manage those."""
        board = {p: (o, n) for p, (o, n) in s.board.items()}
        bar = dict(s.bar)
        off = dict(s.off)
        opp = 1 - pl

        def remove(p):
            o, n = board[p]
            if n == 1:
                del board[p]
            else:
                board[p] = (o, n - 1)

        def add(p):
            o, n = board.get(p, (pl, 0))
            if o == opp and n == 1:        # hit a blot
                del board[p]
                bar[opp] += 1
                board[p] = (pl, 1)
            elif p in board and board[p][0] == pl:
                board[p] = (pl, board[p][1] + 1)
            else:
                board[p] = (pl, 1)

        if kind == "enter":
            bar[pl] -= 1
            add(to)
        elif kind == "move":
            remove(frm)
            add(to)
        elif kind == "off":
            remove(frm)
            off[pl] += 1

        return BgState(board=board, bar=bar, off=off, roll=s.roll,
                       dice=s.dice, to_move=pl, ply=s.ply, winner=None)

    # -- parse a move string into a sub-move tuple --------------------------
    def _parse(self, s, pl, move):
        frm_s, to_s = move.split(">")
        if frm_s == "bar":
            return ("enter", None, int(to_s))
        if to_s == "off":
            return ("off", int(frm_s), None)
        return ("move", int(frm_s), int(to_s))

    # -- apply --------------------------------------------------------------
    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        pl = s.to_move

        if move == "pass":
            remaining = ()
            ns_board = {p: (o, n) for p, (o, n) in s.board.items()}
            ns = BgState(board=ns_board, bar=dict(s.bar), off=dict(s.off),
                         roll=s.roll, dice=s.dice, to_move=pl, ply=s.ply)
        else:
            if move not in self.legal_moves(s):
                raise ValueError(f"illegal move {move} for {NAMES[pl]}")
            kind, frm, to = self._parse(s, pl, move)
            ns = self._apply_sub(s, pl, kind, frm, to)
            # consume the die that produced this move. For a bear-off via
            # overshoot the same move can be produced by several dice; prefer the
            # smallest valid one (so the larger die is kept for another checker).
            die = self._consuming_die(s, pl, move)
            rest = list(s.dice)
            rest.remove(die)
            remaining = tuple(rest)
            ns.dice = remaining

        # win check: a player wins when ALL their checkers are borne off. The
        # total per side is 15 in standard/nackgammon but 3 in hypergammon, so
        # compare against that player's actual checker total, not a constant.
        winner = pl if ns.off[pl] >= self._total(ns, pl) else None

        ply = s.ply + 1
        if winner is None and ply >= PLY_CAP:
            winner = self._leader(ns)

        if winner is not None:
            return BgState(board=ns.board, bar=ns.bar, off=ns.off,
                           roll=(), dice=(), to_move=pl, ply=ply, winner=winner)

        # same player keeps moving while a remaining die is playable.
        probe = BgState(board=ns.board, bar=ns.bar, off=ns.off,
                        roll=s.roll, dice=remaining, to_move=pl, ply=ply)
        if remaining and self._max_usable(probe, pl, remaining) > 0:
            return probe

        # turn ends -> roll for the opponent.
        nxt = 1 - pl
        new_roll = self._roll(rng)
        return BgState(board=ns.board, bar=ns.bar, off=ns.off,
                       roll=new_roll, dice=self._expand(new_roll),
                       to_move=nxt, ply=ply, winner=None)

    def _consuming_die(self, s, pl, move):
        """Which UNUSED die value produces `move`. Prefer the smallest such die
        (keeps a larger die available for another checker -- the overshoot case)."""
        cands = []
        for die in set(s.dice):
            if move in self._submoves_for_die(s, pl, die):
                cands.append(die)
        if not cands:
            raise ValueError(f"no die produces {move}")
        return min(cands)

    # -- terminal / returns -------------------------------------------------
    def _leader(self, s):
        # pip-count leader (fewer pips = ahead); off counts as 0, bar far away.
        def pips(pl):
            tot = 25 * s.bar[pl]
            for p, (o, n) in s.board.items():
                if o == pl:
                    tot += self._home_index(pl, p) * n
            return tot
        return WHITE if pips(WHITE) <= pips(BLACK) else BLACK

    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s):
        return {
            "board": {str(p): [o, n] for p, (o, n) in s.board.items()},
            "bar": {str(k): v for k, v in s.bar.items()},
            "off": {str(k): v for k, v in s.off.items()},
            "roll": list(s.roll),
            "dice": list(s.dice),
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d):
        return BgState(
            board={int(p): (v[0], v[1]) for p, v in d["board"].items()},
            bar={int(k): v for k, v in d["bar"].items()},
            off={int(k): v for k, v in d["off"].items()},
            roll=tuple(d["roll"]),
            dice=tuple(d["dice"]),
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    # -- move log -----------------------------------------------------------
    def describe_move(self, s, move):
        pl = s.to_move
        if move == "pass":
            return (f"{NAMES[pl]} (dice {','.join(map(str, s.dice))}) "
                    f"— no legal move, forfeits")
        kind, frm, to = self._parse(s, pl, move)
        if kind == "enter":
            hit = self._owner_count(s.board, to)[0] == (1 - pl)
            return f"{NAMES[pl]} enters from bar → {to}" + (" *hit*" if hit else "")
        if kind == "off":
            return f"{NAMES[pl]} bears off from {frm}"
        hit = self._owner_count(s.board, to)[0] == (1 - pl)
        return f"{NAMES[pl]} {frm}→{to}" + (" *hit*" if hit else "")

    # -- render -------------------------------------------------------------
    def _layout(self):
        """Polygon triangles for the 24 points + bar + two off-trays.

        Classic layout: points 13..24 along the top (left→right is 13..18, then
        the bar, then 19..24), points 12..1 along the bottom. White (seat 0) home
        is the bottom-right (points 1..6); Black home is the top-right.
        Coordinate units are arbitrary; y grows downward.
        """
        cells = []
        W = 14.0           # total width units (12 point-columns + bar + tray)
        TOP_Y0, TOP_TIP = 0.0, 4.5
        BOT_Y0, BOT_TIP = 11.0, 6.5

        def col_x(slot):
            # slot 0..11 maps to a column; bar sits between slots 5 and 6.
            x = slot + (1.0 if slot >= 6 else 0.0)  # gap for the bar
            return x

        # top row: points 13..24 left-to-right
        for slot, p in enumerate(range(13, 25)):
            x = col_x(slot)
            cells.append({"id": str(p), "points": [
                [x, TOP_Y0], [x + 1, TOP_Y0], [x + 0.5, TOP_TIP]]})
        # bottom row: points 12..1 left-to-right
        for slot, p in enumerate(range(12, 0, -1)):
            x = col_x(slot)
            cells.append({"id": str(p), "points": [
                [x, BOT_Y0], [x + 1, BOT_Y0], [x + 0.5, BOT_TIP]]})

        # The bar: a tall rectangle down the centre (between slot 5 and 6).
        bx = 6.0
        cells.append({"id": "bar", "points": [
            [bx, 0.0], [bx + 1, 0.0], [bx + 1, 11.0], [bx, 11.0]]})
        # Off-trays at the far right.
        ox = W
        cells.append({"id": "off", "points": [
            [ox, 6.0], [ox + 1.0, 6.0], [ox + 1.0, 11.0], [ox, 11.0]]})
        return cells

    def render(self, s, perspective=None):
        cells = self._layout()

        # A point shows a STACK of checkers (all one owner). Render via piece.stack
        # so the generic tower glyph + a height badge appear on the triangle.
        pieces = []
        for p, (o, n) in s.board.items():
            pieces.append({
                "cell": str(p),
                "owner": o,
                "stack": [o] * n,
                "label": str(n) if n > 2 else "",
            })

        # Bar: show whichever side has checkers there (caption carries counts).
        bar_owner = None
        if s.bar[WHITE] and s.bar[BLACK]:
            bar_owner = s.to_move
        elif s.bar[WHITE]:
            bar_owner = WHITE
        elif s.bar[BLACK]:
            bar_owner = BLACK
        if bar_owner is not None:
            tot = s.bar[WHITE] + s.bar[BLACK]
            pieces.append({"cell": "bar", "owner": bar_owner,
                           "stack": [bar_owner] * max(1, s.bar[bar_owner]),
                           "label": f"{s.bar[WHITE]}/{s.bar[BLACK]}"})

        # Off-tray: show the player whose borne-off count is larger, labelled.
        off_owner = WHITE if s.off[WHITE] >= s.off[BLACK] else BLACK
        if s.off[WHITE] or s.off[BLACK]:
            pieces.append({"cell": "off", "owner": off_owner,
                           "stack": [off_owner],
                           "label": f"{s.off[WHITE]}/{s.off[BLACK]}"})

        tints = {"bar": "#3a3027", "off": "#2f3a27"}

        tally = (f"{NAMES[WHITE]}: {s.off[WHITE]} off, {s.bar[WHITE]} on bar  ·  "
                 f"{NAMES[BLACK]}: {s.off[BLACK]} off, {s.bar[BLACK]} on bar")
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins!  ·  {tally}"
        else:
            dice_s = ", ".join(map(str, s.dice)) if s.dice else "—"
            dbl = " (double!)" if len(set(s.roll)) == 1 else ""
            stuck = "" if self.legal_moves(s) != ["pass"] else " — no move, forfeits"
            caption = (f"{NAMES[s.to_move]} to move · rolled {s.roll[0]}-{s.roll[1]}"
                       f"{dbl} · dice left [{dice_s}]{stuck}  ·  {tally}")

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
