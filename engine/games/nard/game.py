"""Nard (Long Nardy / Long Backgammon) -- the Persian tables race game.

Two players (White & Black) each race 15 checkers around a shared 24-point board
into their own home quadrant and then bear them off; first to bear off all 15
wins. Nard is in the tables/backgammon family but is a fundamentally DIFFERENT
game from Western backgammon:

  * NO HITTING, NO BLOTS, NO BAR. A checker may NEVER land on a point occupied by
    ANY opposing checker (even a single one). A lone checker therefore fully holds
    a point, and no checker is ever sent back -- so there is no bar and no
    re-entry. This turns the game into a pure race + blocking contest.
  * ALL-ON-THE-HEAD START. Each player begins with ALL 15 checkers stacked on a
    single point -- their "head" -- in diagonally opposite corners.
  * SAME ROTATIONAL DIRECTION. BOTH players move the same way around the loop
    (counter-clockwise), each toward their own home quadrant, unlike backgammon's
    mirrored directions.
  * ONE OFF THE HEAD PER TURN. At most one checker may leave the head each turn
    (two are allowed on a player's FIRST turn). See below.

Randomness WITHOUT a chance node (the platform's standard pattern, as in
Backgammon / Royal Game of Ur): the dice for the player to move are stored in the
state. ``initial_state`` rolls White's first pair with the supplied rng. A TURN is
consumed ONE DIE AT A TIME -- each ``apply_move`` plays a single die as one
sub-move and keeps the SAME player to move until the dice are spent OR no
remaining die can legally be played; then the next player's pair is rolled and
stored. A double (e.g. 3-3) yields FOUR moves of that value. ``has_randomness``
is true.

The "MUST USE BOTH DICE IF POSSIBLE" rule is enforced exactly as in backgammon:
legal sub-moves are restricted to those that lie on a turn-sequence using the
MAXIMUM possible number of dice (computed by a small recursive search), and the
head cap is honoured throughout that search.

BOARD MODEL. Physical points are numbered 1..24. Each player has a fixed PATH --
the ordered list of the 24 points from the head to the last home point -- and
moves by advancing along that path (both paths trace the SAME cyclic direction
around the board). White's path is 24,23,...,1 (home = points 1..6, head = 24).
Black's path is 12,11,...,1,24,23,...,13 (home = points 13..18, head = 12). The
two heads (24 and 12) are diagonally opposite and exactly half the loop apart --
which is why an opening double 3, 4 or 6 is naturally forced to bring two men off
the head (a single man is blocked at the opponent's full head before all four
dice are spent; see rules.md).

Documented simplifications:
  * NO DOUBLING CUBE / no gammon scoring -- a win is simply a win (+1 / -1), as in
    the backgammon package.
  * THE SIX-PRIME RULE IS OMITTED. Long Nardy forbids building a full 6-point
    prime that traps ALL of the opponent's checkers behind it. Detecting that
    correctly (which men are "ahead" of a prime, across the wrap) is fiddly and it
    almost never binds in ordinary play, so the clean core is shipped without it
    (documented in rules.md).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
NCHK = 15
PLY_CAP = 4000   # hard draw cap; random play always terminates

HEAD = {WHITE: 24, BLACK: 12}


def _white_path():
    return list(range(24, 0, -1))                       # [24,23,...,1]


def _black_path():
    return list(range(12, 0, -1)) + list(range(24, 12, -1))  # [12..1, 24..13]


PATHS = {WHITE: _white_path(), BLACK: _black_path()}
# absolute point -> 0-based index along that player's path (0 = head).
INDEX = {pl: {p: i for i, p in enumerate(PATHS[pl])} for pl in (WHITE, BLACK)}


@dataclass
class NardState:
    # board[point] = (owner, count) for the occupied points 1..24.
    board: dict = field(default_factory=dict)
    off: dict = field(default_factory=lambda: {WHITE: 0, BLACK: 0})
    roll: tuple = ()          # the FULL pair rolled this turn (for display)
    dice: tuple = ()          # the UNUSED die values still to play this turn
    to_move: int = WHITE
    first_turn: dict = field(default_factory=lambda: {WHITE: True, BLACK: True})
    head_moved: int = 0       # checkers moved off the head so far THIS turn
    ply: int = 0
    winner: object = None


class Nard(Game):
    uid = "nard"
    name = "Nard"

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
        roll = self._roll(rng)
        return NardState(
            board={HEAD[WHITE]: (WHITE, NCHK), HEAD[BLACK]: (BLACK, NCHK)},
            off={WHITE: 0, BLACK: 0},
            roll=roll,
            dice=self._expand(roll),
            to_move=WHITE,
            first_turn={WHITE: True, BLACK: True},
            head_moved=0,
            ply=0,
            winner=None,
        )

    def current_player(self, s):
        return s.to_move

    # -- geometry helpers ---------------------------------------------------
    @staticmethod
    def _pip(pl, p):
        """Pips remaining for a pl-checker on point p (1..6 inside home)."""
        return 24 - INDEX[pl][p]

    # -- board queries ------------------------------------------------------
    @staticmethod
    def _owner_count(board, p):
        return board.get(p, (None, 0))

    def _blocked(self, board, pl, p):
        """True if point p is held by ANY opponent checker (no hitting)."""
        o, n = self._owner_count(board, p)
        return o is not None and o != pl and n >= 1

    def _all_home(self, s, pl):
        """All 15 of pl's checkers are in the home quadrant (pip 1..6)."""
        for p, (o, n) in s.board.items():
            if o == pl and self._pip(pl, p) > 6:
                return False
        return True

    def _highest_home_pip(self, s, pl):
        """Largest occupied pip for pl (for the bear-off 'overshoot' rule)."""
        hi = 0
        for p, (o, n) in s.board.items():
            if o == pl:
                hi = max(hi, self._pip(pl, p))
        return hi

    def _head_cap(self, s, pl):
        """Max checkers that may leave the head THIS turn (2 on the first turn)."""
        return 2 if s.first_turn[pl] else 1

    # -- single-die sub-move generation -------------------------------------
    def _submoves_for_die(self, s, pl, die, head_moved):
        """All legal sub-moves (move strings) using ONE die value, on state s.

        Respects the head cap: no further checker may leave the head once
        ``head_moved`` has reached the cap. Encodings:
          ``"F>T"``    advance a checker from point F to point T
          ``"F>off"``  bear off the checker on point F
        """
        board = s.board
        out = {}   # move-string -> ("move"/"off", from, to)
        home = self._all_home(s, pl)
        hi = self._highest_home_pip(s, pl) if home else 0
        head_pt = HEAD[pl]
        cap = self._head_cap(s, pl)

        for p, (o, n) in board.items():
            if o != pl or n <= 0:
                continue
            if p == head_pt and head_moved >= cap:
                continue   # head cap reached -- this checker cannot leave
            ni = INDEX[pl][p] + die
            if ni <= 23:
                dest = PATHS[pl][ni]
                if not self._blocked(board, pl, dest):
                    out[f"{p}>{dest}"] = ("move", p, dest)
            elif home:
                pip = self._pip(pl, p)
                if pip == die:
                    out[f"{p}>off"] = ("off", p, None)          # exact bear-off
                elif die > pip and pip == hi:
                    out[f"{p}>off"] = ("off", p, None)          # overshoot
        return out

    # -- max-dice usage (the "must use both if possible" rule) --------------
    def _max_usable(self, s, pl, dice, head_moved):
        """Maximum number of the given dice playable over the rest of the turn.

        Recursive look-ahead over the remaining dice, threading the head-move
        count so the cap is honoured. Cheap: depth <= 4, branching small."""
        if not dice:
            return 0
        best = 0
        for die in set(dice):
            subs = self._submoves_for_die(s, pl, die, head_moved)
            if not subs:
                continue
            rest = list(dice)
            rest.remove(die)
            for kind, frm, to in subs.values():
                ns = self._apply_sub(s, pl, kind, frm, to)
                hm = head_moved + (1 if frm == HEAD[pl] else 0)
                got = 1 + self._max_usable(ns, pl, tuple(rest), hm)
                if got > best:
                    best = got
                    if best == len(dice):
                        return best
        return best

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        pl = s.to_move
        target = self._max_usable(s, pl, s.dice, s.head_moved)
        if target == 0:
            return ["pass"]   # no remaining die can be legally played
        # Offer only sub-moves that PRESERVE the maximum dice usage.
        moves = set()
        for die in set(s.dice):
            subs = self._submoves_for_die(s, pl, die, s.head_moved)
            if not subs:
                continue
            rest = list(s.dice)
            rest.remove(die)
            for mv, (kind, frm, to) in subs.items():
                ns = self._apply_sub(s, pl, kind, frm, to)
                hm = s.head_moved + (1 if frm == HEAD[pl] else 0)
                if 1 + self._max_usable(ns, pl, tuple(rest), hm) == target:
                    moves.add(mv)
        return sorted(moves)

    # -- apply a single sub-move (no turn/roll/head logic) ------------------
    def _apply_sub(self, s, pl, kind, frm, to):
        """Return a new NardState with one checker moved; pure board update.

        No hitting / no bar: destinations are always empty or own. Does NOT touch
        dice, to_move, winner, head_moved or ply -- callers manage those.
        ``first_turn`` is preserved (the head cap reads it during look-ahead)."""
        board = {p: (o, n) for p, (o, n) in s.board.items()}
        off = dict(s.off)

        def remove(p):
            o, n = board[p]
            if n == 1:
                del board[p]
            else:
                board[p] = (o, n - 1)

        def add(p):
            if p in board and board[p][0] == pl:
                board[p] = (pl, board[p][1] + 1)
            else:
                board[p] = (pl, 1)

        if kind == "move":
            remove(frm)
            add(to)
        elif kind == "off":
            remove(frm)
            off[pl] += 1

        return NardState(board=board, off=off, roll=s.roll, dice=s.dice,
                         to_move=pl, first_turn=dict(s.first_turn),
                         head_moved=s.head_moved, ply=s.ply, winner=None)

    # -- parse a move string into a sub-move tuple --------------------------
    def _parse(self, move):
        frm_s, to_s = move.split(">")
        if to_s == "off":
            return ("off", int(frm_s), None)
        return ("move", int(frm_s), int(to_s))

    # -- apply --------------------------------------------------------------
    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        pl = s.to_move

        if move == "pass":
            ply = s.ply + 1
            winner = self._leader(s) if ply >= PLY_CAP else None
            board = {p: (o, n) for p, (o, n) in s.board.items()}
            if winner is not None:
                return NardState(board=board, off=dict(s.off), roll=(), dice=(),
                                 to_move=pl, first_turn=dict(s.first_turn),
                                 head_moved=0, ply=ply, winner=winner)
            nft = dict(s.first_turn)
            nft[pl] = False
            nxt = 1 - pl
            new_roll = self._roll(rng)
            return NardState(board=board, off=dict(s.off), roll=new_roll,
                             dice=self._expand(new_roll), to_move=nxt,
                             first_turn=nft, head_moved=0, ply=ply, winner=None)

        if move not in self.legal_moves(s):
            raise ValueError(f"illegal move {move} for {NAMES[pl]}")
        kind, frm, to = self._parse(move)
        ns = self._apply_sub(s, pl, kind, frm, to)
        new_head_moved = s.head_moved + (1 if frm == HEAD[pl] else 0)
        die = self._consuming_die(s, pl, move)
        rest = list(s.dice)
        rest.remove(die)
        remaining = tuple(rest)
        ns.dice = remaining
        ns.head_moved = new_head_moved

        winner = pl if ns.off[pl] >= NCHK else None
        ply = s.ply + 1
        if winner is None and ply >= PLY_CAP:
            winner = self._leader(ns)

        if winner is not None:
            return NardState(board=ns.board, off=ns.off, roll=(), dice=(),
                             to_move=pl, first_turn=dict(s.first_turn),
                             head_moved=new_head_moved, ply=ply, winner=winner)

        # same player keeps moving while a remaining die is playable.
        probe = NardState(board=ns.board, off=ns.off, roll=s.roll,
                          dice=remaining, to_move=pl,
                          first_turn=dict(s.first_turn),
                          head_moved=new_head_moved, ply=ply)
        if remaining and self._max_usable(probe, pl, remaining, new_head_moved) > 0:
            return probe

        # turn ends -> roll for the opponent.
        nft = dict(s.first_turn)
        nft[pl] = False
        nxt = 1 - pl
        new_roll = self._roll(rng)
        return NardState(board=ns.board, off=ns.off, roll=new_roll,
                         dice=self._expand(new_roll), to_move=nxt,
                         first_turn=nft, head_moved=0, ply=ply, winner=None)

    def _consuming_die(self, s, pl, move):
        """Which UNUSED die value produces `move` (prefer the smallest -- keeps a
        larger die available for another checker, the overshoot case)."""
        cands = []
        for die in set(s.dice):
            if move in self._submoves_for_die(s, pl, die, s.head_moved):
                cands.append(die)
        if not cands:
            raise ValueError(f"no die produces {move}")
        return min(cands)

    # -- terminal / returns -------------------------------------------------
    def _leader(self, s):
        def pips(pl):
            tot = 0
            for p, (o, n) in s.board.items():
                if o == pl:
                    tot += self._pip(pl, p) * n
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
            "off": {str(k): v for k, v in s.off.items()},
            "roll": list(s.roll),
            "dice": list(s.dice),
            "to_move": s.to_move,
            "first_turn": {str(k): v for k, v in s.first_turn.items()},
            "head_moved": s.head_moved,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d):
        return NardState(
            board={int(p): (v[0], v[1]) for p, v in d["board"].items()},
            off={int(k): v for k, v in d["off"].items()},
            roll=tuple(d["roll"]),
            dice=tuple(d["dice"]),
            to_move=d["to_move"],
            first_turn={int(k): v for k, v in d.get(
                "first_turn", {"0": True, "1": True}).items()},
            head_moved=d.get("head_moved", 0),
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    # -- move log -----------------------------------------------------------
    def describe_move(self, s, move):
        pl = s.to_move
        if move == "pass":
            return (f"{NAMES[pl]} (dice {','.join(map(str, s.dice))}) "
                    f"— no legal move, forfeits")
        kind, frm, to = self._parse(move)
        head = " (off head)" if frm == HEAD[pl] else ""
        if kind == "off":
            return f"{NAMES[pl]} bears off from {frm}{head}"
        return f"{NAMES[pl]} {frm}→{to}{head}"

    # -- render -------------------------------------------------------------
    def _layout(self):
        """Polygon triangles for the 24 points + a right-hand off-tray.

        Classic layout: points 13..24 along the top (left→right), points 12..1
        along the bottom, with a central gap for the traditional divider. White
        (seat 0) head is the top-right (point 24) and home is the bottom-right
        (points 1..6); Black head is the bottom-left (point 12) and home is the
        top-left (points 13..18)."""
        cells = []
        W = 14.0
        TOP_Y0, TOP_TIP = 0.0, 4.5
        BOT_Y0, BOT_TIP = 11.0, 6.5

        def col_x(slot):
            return slot + (1.0 if slot >= 6 else 0.0)  # gap for the divider

        for slot, p in enumerate(range(13, 25)):        # top: 13..24
            x = col_x(slot)
            cells.append({"id": str(p), "points": [
                [x, TOP_Y0], [x + 1, TOP_Y0], [x + 0.5, TOP_TIP]]})
        for slot, p in enumerate(range(12, 0, -1)):      # bottom: 12..1
            x = col_x(slot)
            cells.append({"id": str(p), "points": [
                [x, BOT_Y0], [x + 1, BOT_Y0], [x + 0.5, BOT_TIP]]})

        ox = W
        cells.append({"id": "off", "points": [
            [ox, 0.0], [ox + 1.0, 0.0], [ox + 1.0, 11.0], [ox, 11.0]]})
        return cells

    def render(self, s, perspective=None):
        cells = self._layout()

        pieces = []
        for p, (o, n) in s.board.items():
            pieces.append({
                "cell": str(p),
                "owner": o,
                "stack": [o] * n,
                "label": str(n) if n > 2 else "",
            })

        off_owner = WHITE if s.off[WHITE] >= s.off[BLACK] else BLACK
        if s.off[WHITE] or s.off[BLACK]:
            pieces.append({"cell": "off", "owner": off_owner,
                           "stack": [off_owner],
                           "label": f"{s.off[WHITE]}/{s.off[BLACK]}"})

        # tint each player's home quadrant + the off-tray, to orient the board.
        tints = {"off": "#2f3a27"}
        for p in range(1, 7):          # White home
            tints[str(p)] = "#3a3227"
        for p in range(13, 19):        # Black home
            tints[str(p)] = "#27313a"

        tally = (f"{NAMES[WHITE]}: {s.off[WHITE]} off  ·  "
                 f"{NAMES[BLACK]}: {s.off[BLACK]} off")
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins!  ·  {tally}"
        else:
            dice_s = ", ".join(map(str, s.dice)) if s.dice else "—"
            dbl = " (double!)" if len(set(s.roll)) == 1 else ""
            cap = self._head_cap(s, s.to_move) - s.head_moved
            head_note = f" · may still move {max(0, cap)} off the head"
            stuck = "" if self.legal_moves(s) != ["pass"] else " — no move, forfeits"
            caption = (f"{NAMES[s.to_move]} to move · rolled {s.roll[0]}-{s.roll[1]}"
                       f"{dbl} · dice left [{dice_s}]{head_note}{stuck}  ·  {tally}")

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
