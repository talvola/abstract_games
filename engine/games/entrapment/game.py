"""Entrapment (Rich Gowell, 1999) -- trap and capture all of your opponent's
"roamers" in a growing maze of barriers.

Rules implemented from the official Boardspace.net rules page, with every
ambiguity resolved against the Boardspace Java reference implementation
(github.com/ddyer0/boardspace.net, ``entrapment/EntrapmentBoard.java``), which
the deep-QA differential uses as its oracle.  Summary:

* 7x7 (or 6x7) squares; each player has 3 (or 4) roamers and 25 barriers.
  Barriers sit in the grooves BETWEEN squares (one groove per adjacent pair).
* Setup: players alternate (White first) placing roamers on any empty square.
* After the last placement White takes a ONE-action turn; every turn after
  that is TWO actions: the first must move a roamer, the second moves a
  roamer or places a barrier (or, once your 25 barriers are all placed,
  relocates one of your *resting* barriers instead of placing).
* A roamer moves 1 or 2 squares in a straight orthogonal line, landing on an
  empty square.  Per move it may jump AT MOST ONE of: a friendly roamer or a
  friendly *resting* barrier.  Enemy barriers/roamers and *standing* barriers
  are impassable.  Any resting barrier crossed flips to *standing* --
  permanently immovable and impassable to both players.  (There is no
  voluntary "flip" action: the Boardspace implementation flips only by
  jumping, and the rules' turn structure offers only move/place/relocate.)
* A roamer with all four sides blocked (edge, any barrier, any roamer) is
  *trapped*.  A trapped roamer that cannot escape -- no legal move of its
  own and no friendly roamer adjacent across an empty groove that can move
  -- is captured immediately (checked after every action, mover-first,
  mirroring the Java ``checkDead``/``checkTrapped`` pipeline).  If a player
  already had a trapped roamer, any additional roamer of theirs that becomes
  trapped is captured immediately; if one action newly traps two roamers of
  one player, the MOVER chooses which one is captured (a kill-selection
  move).  A player whose roamer is trapped must use their first action to
  move it (or a friendly roamer adjacent across an empty groove); if the
  second action starts with the roamer still trapped, it is likewise
  restricted to escape moves / barrier play.
* You win by capturing all enemy roamers.  If one action leaves BOTH sides
  with no roamers, the non-mover wins (Boardspace rule).

State/board model: a doubled grid.  Squares live at even coordinates
``(2c,2r)``; the groove between two adjacent squares is the odd cell between
them.  Cell ids are ``"x,y"`` in this doubled grid.  Moves:

* setup placement / kill selection: ``"x,y"`` (a square)
* roamer move: ``"x1,y1>x2,y2"`` (squares, straight, 1 or 2 steps)
* barrier placement: ``"B@x,y"`` (a groove; reserve-tray drop move)
* barrier relocation: ``"g1>g2"`` (groove to groove, supply exhausted only)
* ``"pass"``: engine backstop for the (theoretically constructible, never
  seen in practice) corner where a mandated action has no legal move.

Termination backstops (honest draws): 80 consecutive actions with no
progress (no placement, flip or capture), or 1200 total actions.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

from agp.game import Game

DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]
NOP_CAP = 80      # actions without placement/flip/capture -> draw
PLY_CAP = 1200    # absolute action cap -> draw


def _p(cell):
    x, y = cell.split(",")
    return int(x), int(y)


def _c(x, y):
    return f"{x},{y}"


@dataclass
class EState:
    w: int = 7                 # squares wide
    h: int = 7                 # squares tall
    nro: int = 3               # roamers per player
    ro: list = field(default_factory=list)      # [ [cell|None]*nro, ... ] slot order
    bars: dict = field(default_factory=dict)    # groove cell -> [owner, up]
    trapped: set = field(default_factory=set)   # roamer cells currently trapped
    unplaced: list = field(default_factory=lambda: [3, 3])
    supply: list = field(default_factory=lambda: [25, 25])
    dead: list = field(default_factory=lambda: [0, 0])
    to_move: int = 0
    phase: str = "place"       # place|act1|act2|kill_self1|kill_other1|kill_self2|kill_other2
    placement_done: bool = False
    single_turn: bool = False   # White's one-action turn right after setup
    ply: int = 0
    nop: int = 0
    winner: object = None
    draw: bool = False


class Entrapment(Game):
    uid = "entrapment"
    name = "Entrapment"

    @property
    def num_players(self):
        return 2

    # ------------------------------------------------------------- helpers --
    def _on_sq(self, s, x, y):
        return (x % 2 == 0 and y % 2 == 0
                and 0 <= x <= 2 * s.w - 2 and 0 <= y <= 2 * s.h - 2)

    def _occ(self, s):
        return {c: pl for pl in (0, 1) for c in s.ro[pl] if c}

    def _bar_blocks(self, s, pl, gx, gy):
        """Groove barrier impassable for pl (enemy-owned or standing)."""
        b = s.bars.get(_c(gx, gy))
        return b is not None and (b[0] != pl or b[1])

    def _is_trapped(self, s, cell, occ):
        x, y = _p(cell)
        for dx, dy in DIRS:
            nx, ny = x + 2 * dx, y + 2 * dy
            if (self._on_sq(s, nx, ny)
                    and _c(x + dx, y + dy) not in s.bars
                    and _c(nx, ny) not in occ):
                return False
        return True

    def _is_dead(self, s, cell, occ, recurse=False):
        """No escape: mirrors Boardspace EntrapmentBoard.isDead exactly,
        including its quirks (the depth-1 neighbour recursion, and the
        distance-2 block that treats any non-enemy occupant as an out)."""
        pl = occ[cell]
        x, y = _p(cell)
        for dx, dy in DIRS:
            nx, ny = x + 2 * dx, y + 2 * dy
            if not self._on_sq(s, nx, ny):
                continue
            b1 = s.bars.get(_c(x + dx, y + dy))
            if b1 is not None and (b1[0] != pl or b1[1]):
                continue                                   # impassable barrier
            dc = _c(nx, ny)
            docc = occ.get(dc)
            if docc is not None and docc != pl:
                continue                                   # enemy roamer
            barriers = 1 if b1 is not None else 0
            if docc == pl:
                barriers += 1
                if not recurse and barriers == 1 and not self._is_dead(s, dc, occ, True):
                    return False                           # adjacent friend can move
            else:
                return False                               # adjacent empty
            if barriers < 2:
                mx, my = x + 4 * dx, y + 4 * dy
                if not self._on_sq(s, mx, my):
                    continue
                d2occ = occ.get(_c(mx, my))
                if d2occ is not None and d2occ != pl:
                    continue
                b2 = s.bars.get(_c(x + 3 * dx, y + 3 * dy))
                if b2 is not None and (b2[0] != pl or b2[1]):
                    continue
                if b2 is not None:
                    barriers += 1
                if barriers < 2:
                    return False
        return True

    def _roamer_moves(self, s, cell, occ):
        """1- or 2-step straight moves; at most one jumped friendly object
        (roamer or resting barrier); mirrors addMoveRoamerMoves."""
        pl = occ[cell]
        x, y = _p(cell)
        out = []
        for dx, dy in DIRS:
            nx, ny = x + 2 * dx, y + 2 * dy
            if not self._on_sq(s, nx, ny):
                continue
            b1 = s.bars.get(_c(x + dx, y + dy))
            if b1 is not None and (b1[0] != pl or b1[1]):
                continue
            dc = _c(nx, ny)
            docc = occ.get(dc)
            if docc is not None and docc != pl:
                continue
            barriers = 0
            if docc == pl:
                barriers += 1
            else:
                out.append(f"{cell}>{dc}")
            if b1 is not None:
                barriers += 1
            if barriers < 2:
                mx, my = x + 4 * dx, y + 4 * dy
                if self._on_sq(s, mx, my) and _c(mx, my) not in occ:
                    b2 = s.bars.get(_c(x + 3 * dx, y + 3 * dy))
                    if b2 is not None and (b2[0] != pl or b2[1]):
                        continue
                    if b2 is not None and barriers == 1:
                        continue
                    out.append(f"{cell}>{_c(mx, my)}")
        return out

    def _escape_moves(self, s, who, occ):
        """Moves of trapped roamers, plus ALL moves of untrapped friendly
        roamers adjacent (across an EMPTY groove) to a trapped one."""
        out = []
        for c in s.ro[who]:
            if c and c in s.trapped:
                out += self._roamer_moves(s, c, occ)
        for c in s.ro[who]:
            if c and c not in s.trapped:
                x, y = _p(c)
                for dx, dy in DIRS:
                    a = _c(x + 2 * dx, y + 2 * dy)
                    if (self._on_sq(s, x + 2 * dx, y + 2 * dy)
                            and _c(x + dx, y + dy) not in s.bars
                            and a in s.trapped and occ.get(a) == who):
                        out += self._roamer_moves(s, c, occ)
                        break
        return out

    def _all_moves(self, s, who, occ):
        out = []
        for c in s.ro[who]:
            if c:
                out += self._roamer_moves(s, c, occ)
        return out

    def _ntrap(self, s, pl):
        return sum(1 for c in s.ro[pl] if c and c in s.trapped)

    def _empty_grooves(self, s):
        out = []
        for gy in range(0, 2 * s.h - 1):
            for gx in range(0, 2 * s.w - 1):
                if (gx + gy) % 2 == 1 and _c(gx, gy) not in s.bars:
                    out.append(_c(gx, gy))
        return out

    # ----------------------------------------------------- capture pipeline --
    def _remove_dead(self, s, cell):
        for pl in (0, 1):
            for i, c in enumerate(s.ro[pl]):
                if c == cell:
                    s.ro[pl][i] = None
                    s.dead[pl] += 1
                    s.trapped.discard(cell)
                    return pl
        raise AssertionError(f"no roamer at {cell}")

    def _check_trapped(self, s, kill):
        killed = False
        for pl in (0, 1):
            prev = self._ntrap(s, pl)
            for i in range(s.nro):
                c = s.ro[pl][i]
                if not c:
                    continue
                occ = self._occ(s)
                ist = self._is_trapped(s, c, occ)
                was = c in s.trapped
                if ist != was:
                    if ist:
                        s.trapped.add(c)
                        if kill and prev > 0:      # second entrapment: killed at once
                            self._remove_dead(s, c)
                            killed = True
                    else:
                        s.trapped.discard(c)
        if killed:
            self._check_trapped(s, False)

    def _check_dead(self, s, first):
        order = []
        occ0 = self._occ(s)
        if first is not None and first in occ0:
            order.append(first)
        for pl in (0, 1):
            for c in list(s.ro[pl]):
                if c and c != first:
                    order.append(c)
        for c in order:
            occ = self._occ(s)
            if c in occ and self._is_dead(s, c, occ):
                self._remove_dead(s, c)

    def _pick_roamer(self, s, cell):
        for pl in (0, 1):
            for i, c in enumerate(s.ro[pl]):
                if c == cell:
                    s.ro[pl][i] = None
                    s.trapped.discard(cell)
                    self._check_trapped(s, True)
                    return pl
        raise AssertionError(f"no roamer at {cell}")

    def _add_roamer(self, s, pl, cell):
        for i, c in enumerate(s.ro[pl]):
            if c is None:
                s.ro[pl][i] = cell
                s.trapped.discard(cell)
                return
        raise AssertionError("no free roamer slot")

    # ------------------------------------------------------ turn transitions --
    def _set_winner(self, s, w1, w2):
        """w1 = all of mover's opponent's roamers dead; w2 = all of mover's.
        Both at once -> the non-mover wins (Boardspace setGameOver rule)."""
        me, opp = s.to_move, 1 - s.to_move
        s.winner = opp if (w1 and w2) else (me if w1 else opp)

    def _after_action(self, s, group):
        me, opp = s.to_move, 1 - s.to_move
        if group == "B":                       # after the turn's FIRST action
            w1, w2 = s.dead[opp] == s.nro, s.dead[me] == s.nro
            if w1 or w2:
                self._set_winner(s, w1, w2)    # a winning first action ends the turn
                return
            if self._ntrap(s, me) >= 2:
                s.phase = "kill_self1"
                return
            if self._ntrap(s, opp) >= 2:
                s.phase = "kill_other1"
                return
            s.phase = "act2"
            return
        # group A: after the second action / a setup placement / a *2 kill
        if self._ntrap(s, me) >= 2:
            s.phase = "kill_self2"
            return
        if self._ntrap(s, opp) >= 2:
            s.phase = "kill_other2"
            return
        self._end_turn(s)

    def _end_turn(self, s):
        me, opp = s.to_move, 1 - s.to_move
        if s.placement_done:
            w1, w2 = s.dead[opp] == s.nro, s.dead[me] == s.nro
            if w1 or w2:
                self._set_winner(s, w1, w2)
                return
        s.to_move = opp
        s.single_turn = False
        if not s.placement_done:
            if s.unplaced[opp] > 0:
                s.phase = "place"
            else:
                s.placement_done = True        # White's one-action first turn
                s.single_turn = True
                s.phase = "act2"
        else:
            s.phase = "act1"

    # ------------------------------------------------------------- Game API --
    def initial_state(self, options=None, rng=None):
        opts = options or {}
        board = str(opts.get("board", "7x7"))
        nro = int(opts.get("roamers", 3))
        w, h = (7, 6) if board == "6x7" else (7, 7)
        return EState(w=w, h=h, nro=nro,
                      ro=[[None] * nro, [None] * nro],
                      unplaced=[nro, nro])

    def current_player(self, s):
        return s.to_move

    def is_terminal(self, s):
        return s.winner is not None or s.draw

    def returns(self, s):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        me = s.to_move
        occ = self._occ(s)
        ph = s.phase
        if ph == "place":
            return [_c(x, y)
                    for y in range(0, 2 * s.h - 1, 2)
                    for x in range(0, 2 * s.w - 1, 2)
                    if _c(x, y) not in occ]
        if ph.startswith("kill"):
            victim = me if "self" in ph else 1 - me
            return [c for c in s.ro[victim] if c and c in s.trapped]
        if self._ntrap(s, me) > 0:
            base = self._escape_moves(s, me, occ)
        else:
            base = self._all_moves(s, me, occ)
        if ph == "act2":
            if s.supply[me] > 0:
                base = base + [f"B@{g}" for g in self._empty_grooves(s)]
            else:
                empties = self._empty_grooves(s)
                for src in sorted(s.bars):
                    o, up = s.bars[src]
                    if o == me and not up:
                        base = base + [f"{src}>{d}" for d in empties]
        return base if base else ["pass"]

    def apply_move(self, s, move, rng=None):
        if move not in self.legal_moves(s):
            raise ValueError(f"illegal move {move!r}")
        ns = copy.deepcopy(s)
        ns.ply += 1
        me = ns.to_move
        ph = ns.phase
        dead0 = ns.dead[0] + ns.dead[1]
        flips = 0
        progress = False

        if move == "pass":
            self._after_action(ns, "B" if ph == "act1" else "A")
        elif ph == "place":
            ns.unplaced[me] -= 1
            self._add_roamer(ns, me, move)
            self._check_dead(ns, move)
            self._check_trapped(ns, True)
            progress = True
            self._after_action(ns, "A")
        elif ph.startswith("kill"):
            victim = me if "self" in ph else 1 - me
            for i, c in enumerate(ns.ro[victim]):
                if c == move:
                    ns.ro[victim][i] = None
                    break
            ns.trapped.discard(move)
            self._check_trapped(ns, True)
            ns.dead[victim] += 1
            self._check_dead(ns, None)
            self._check_trapped(ns, True)
            progress = True
            self._after_action(ns, "B" if ph.endswith("1") else "A")
        elif move.startswith("B@"):
            ns.supply[me] -= 1
            ns.bars[move[2:]] = [me, False]
            self._check_dead(ns, None)
            self._check_trapped(ns, True)
            progress = True
            self._after_action(ns, "A")
        else:
            src, dst = move.split(">")
            sx, sy = _p(src)
            if sx % 2 == 0 and sy % 2 == 0:               # roamer move
                self._pick_roamer(ns, src)
                tx, ty = _p(dst)
                steps = max(abs(tx - sx), abs(ty - sy)) // 2
                ux = (tx - sx) // (2 * steps) if tx != sx else 0
                uy = (ty - sy) // (2 * steps) if ty != sy else 0
                for k in range(1, 2 * steps, 2):          # grooves crossed
                    g = _c(sx + ux * k, sy + uy * k)
                    b = ns.bars.get(g)
                    if b is not None and not b[1]:
                        b[1] = True                       # jumped -> standing
                        flips += 1
                self._add_roamer(ns, me, dst)
                self._check_dead(ns, dst)
                self._check_trapped(ns, True)
                self._after_action(ns, "B" if ph == "act1" else "A")
            else:                                         # barrier relocation
                b = ns.bars.pop(src)
                self._check_trapped(ns, True)
                ns.bars[dst] = [b[0], False]
                self._check_dead(ns, None)
                self._check_trapped(ns, True)
                self._after_action(ns, "A")

        if flips or (ns.dead[0] + ns.dead[1]) != dead0:
            progress = True
        ns.nop = 0 if progress else ns.nop + 1
        if ns.winner is None and not ns.draw and (ns.nop >= NOP_CAP or ns.ply >= PLY_CAP):
            ns.draw = True
        return ns

    # ---------------------------------------------------------- (de)serialise --
    def serialize(self, s):
        return {"w": s.w, "h": s.h, "nro": s.nro,
                "ro": [list(s.ro[0]), list(s.ro[1])],
                "bars": {k: [v[0], bool(v[1])] for k, v in sorted(s.bars.items())},
                "trapped": sorted(s.trapped),
                "unplaced": list(s.unplaced), "supply": list(s.supply),
                "dead": list(s.dead), "to_move": s.to_move, "phase": s.phase,
                "placement_done": s.placement_done, "single_turn": s.single_turn,
                "ply": s.ply, "nop": s.nop,
                "winner": s.winner, "draw": s.draw}

    def deserialize(self, d):
        return EState(w=d["w"], h=d["h"], nro=d["nro"],
                      ro=[list(d["ro"][0]), list(d["ro"][1])],
                      bars={k: [v[0], bool(v[1])] for k, v in d["bars"].items()},
                      trapped=set(d["trapped"]),
                      unplaced=list(d["unplaced"]), supply=list(d["supply"]),
                      dead=list(d["dead"]), to_move=d["to_move"], phase=d["phase"],
                      placement_done=d["placement_done"],
                      single_turn=d.get("single_turn", False), ply=d.get("ply", 0),
                      nop=d.get("nop", 0), winner=d.get("winner"),
                      draw=d.get("draw", False))

    # ----------------------------------------------------------------- extras --
    def _sqname(self, cell):
        x, y = _p(cell)
        return f"{chr(97 + x // 2)}{y // 2 + 1}"

    def _grname(self, cell):
        x, y = _p(cell)
        if x % 2 == 1:                                    # vertical groove
            return f"{self._sqname(_c(x - 1, y))}|{self._sqname(_c(x + 1, y))}"
        return f"{self._sqname(_c(x, y - 1))}|{self._sqname(_c(x, y + 1))}"

    def describe_move(self, s, move):
        if move == "pass":
            return "pass"
        if move.startswith("B@"):
            return f"barrier {self._grname(move[2:])}"
        if ">" in move:
            src, dst = move.split(">")
            if _p(src)[0] % 2 == 0 and _p(src)[1] % 2 == 0:
                sx, sy = _p(src)
                tx, ty = _p(dst)
                steps = max(abs(tx - sx), abs(ty - sy)) // 2
                ux = (tx - sx) // (2 * steps) if tx != sx else 0
                uy = (ty - sy) // (2 * steps) if ty != sy else 0
                flip = any(not b[1] for k in range(1, 2 * steps, 2)
                           for b in [s.bars.get(_c(sx + ux * k, sy + uy * k))] if b)
                return (f"{self._sqname(src)}-{self._sqname(dst)}"
                        + (" (flips barrier)" if flip else ""))
            return f"barrier {self._grname(src)} to {self._grname(dst)}"
        if s.phase.startswith("kill"):
            return f"capture {self._sqname(move)}"
        return f"roamer {self._sqname(move)}"

    def heuristic(self, s):
        v = math.tanh(1.2 * (s.dead[1] - s.dead[0]) / s.nro
                      + 0.3 * (self._ntrap(s, 1) - self._ntrap(s, 0)))
        return [v, -v]

    def render(self, s, perspective=None):
        SQ, GR = 1.0, 0.34
        P = SQ + GR

        def band(i):
            q, rm = divmod(i, 2)
            lo = q * P + rm * SQ
            return lo, lo + (SQ if rm == 0 else GR)

        ytop = 2 * s.h - 2
        cells, tints = [], {}
        for gy in range(0, 2 * s.h - 1):
            for gx in range(0, 2 * s.w - 1):
                if gx % 2 == 1 and gy % 2 == 1:
                    continue
                x0, x1 = band(gx)
                y0, y1 = band(ytop - gy)
                cid = _c(gx, gy)
                cells.append({"id": cid, "points": [[round(x0, 3), round(y0, 3)],
                                                    [round(x1, 3), round(y0, 3)],
                                                    [round(x1, 3), round(y1, 3)],
                                                    [round(x0, 3), round(y1, 3)]]})
                if gx % 2 == 0 and gy % 2 == 0:
                    tints[cid] = "#2a2620"
                else:
                    b = s.bars.get(cid)
                    tints[cid] = "#c9a96e" if (b and b[1]) else "#1d1a16"

        occ = self._occ(s)
        pieces = [{"cell": c, "owner": pl} for c, pl in occ.items()]
        pieces += [{"cell": g, "owner": o, "shape": "fill"}
                   for g, (o, up) in sorted(s.bars.items()) if not up]
        highlights = [{"cell": c, "kind": "goal"} for c in sorted(s.trapped)]

        names = {0: "Player 1", 1: "Player 2"}
        me = s.to_move
        if s.winner is not None:
            cap = f"{names[s.winner]} wins — all enemy roamers captured"
        elif s.draw:
            cap = "Draw (no progress)"
        else:
            what = {
                "place": f"place a roamer ({s.unplaced[me]} left)",
                "kill_self1": "choose which of YOUR trapped roamers is captured",
                "kill_self2": "choose which of YOUR trapped roamers is captured",
                "kill_other1": "choose which OPPONENT trapped roamer is captured",
                "kill_other2": "choose which OPPONENT trapped roamer is captured",
            }.get(s.phase)
            if what is None:
                trapped_me = self._ntrap(s, me) > 0
                if s.phase == "act1":
                    what = ("action 1 of 2: free your trapped roamer"
                            if trapped_me else "action 1 of 2: move a roamer")
                else:
                    second = "place a barrier" if s.supply[me] > 0 else "move a resting barrier"
                    what = (f"escape, or {second}" if trapped_me
                            else f"move a roamer, or {second}")
                    what = ("one action: " if s.single_turn else "action 2 of 2: ") + what
            cap = (f"{names[me]} — {what} · captured: "
                   f"P1 {s.dead[0]}/{s.nro}, P2 {s.dead[1]}/{s.nro}")
        reserve = {str(pl): ({"B": s.supply[pl]} if s.supply[pl] > 0 else {})
                   for pl in (0, 1)}
        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "reserve": reserve,
            "actionNames": {"pass": "Pass (no legal action)"},
            "caption": cap,
        }
