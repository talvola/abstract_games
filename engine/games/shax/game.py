"""Shax -- the Somali national mill game (also *jare* / *jar*).

Played on the standard 24-point morris board (three concentric squares joined
by four mid-side spokes, NO diagonals) with **twelve** men per player, so after
the placement phase the board is completely full.

How it differs from Nine Men's Morris (per Rick Davies, "An Introduction to
Shax: a Somali game", Mogadishu 1988):

* Mills ("jare") formed during placement capture nothing; only the FIRST jare
  matters -- it gives its maker priority at the transition.
* When all 24 men are down, the first-jare player removes one enemy man from
  anywhere, then the other player removes one enemy man (whether or not they
  made a jare), then the first-jare player makes the first slide. If NO jare
  was made, the second placer takes that priority role instead (documented
  interpretation -- see rules.md).
* Captures remove any enemy man -- men standing in a mill are NOT protected.
* No flying, ever.
* A blocked player never loses: the opponent must play a move that frees them
  ("jid i sii aan jar aheyn"); if that forced move happens to make a jare it
  captures nothing (*oodan*).

Win by reducing the opponent to two men. Draw backstops: 50 plies without a
placement/removal, threefold repetition, or a lock nobody can open.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from agp.game import Game

# 24 points: outer, middle, inner ring (each an 8-cycle) wired by four spokes
# at the mid-side points. Coordinates on a 0..6 grid (x right, y down).
OUTER = [(0, 0), (3, 0), (6, 0), (6, 3), (6, 6), (3, 6), (0, 6), (0, 3)]
MIDDLE = [(1, 1), (3, 1), (5, 1), (5, 3), (5, 5), (3, 5), (1, 5), (1, 3)]
INNER = [(2, 2), (3, 2), (4, 2), (4, 3), (4, 4), (3, 4), (2, 4), (2, 3)]
RINGS = [OUTER, MIDDLE, INNER]

POINTS = [f"{x},{y}" for ring in RINGS for (x, y) in ring]


def _ring_adj():
    adj = {p: set() for p in POINTS}
    for ring in RINGS:
        ids = [f"{x},{y}" for (x, y) in ring]
        for i in range(8):
            adj[ids[i]].add(ids[(i + 1) % 8])
            adj[ids[i]].add(ids[(i - 1) % 8])
    for k in (1, 3, 5, 7):  # spokes join the mid-side points of the rings
        o = f"{OUTER[k][0]},{OUTER[k][1]}"
        m = f"{MIDDLE[k][0]},{MIDDLE[k][1]}"
        c = f"{INNER[k][0]},{INNER[k][1]}"
        adj[o].add(m); adj[m].add(o)
        adj[m].add(c); adj[c].add(m)
    return {p: frozenset(s) for p, s in adj.items()}


ADJ = _ring_adj()


def _mill_lines():
    mills = []
    for ring in RINGS:  # four edges of three per ring
        ids = [f"{x},{y}" for (x, y) in ring]
        for k in (0, 2, 4, 6):
            mills.append((ids[k], ids[(k + 1) % 8], ids[(k + 2) % 8]))
    for k in (1, 3, 5, 7):  # four spokes
        mills.append((f"{OUTER[k][0]},{OUTER[k][1]}",
                      f"{MIDDLE[k][0]},{MIDDLE[k][1]}",
                      f"{INNER[k][0]},{INNER[k][1]}"))
    return mills


MILLS = _mill_lines()
MILLS_AT = {p: [m for m in MILLS if p in m] for p in POINTS}


def _line_segments():
    segs = []
    for ring in RINGS:
        for i in range(8):
            segs.append([list(ring[i]), list(ring[(i + 1) % 8])])
    for k in (1, 3, 5, 7):
        segs.append([list(OUTER[k]), list(MIDDLE[k])])
        segs.append([list(MIDDLE[k]), list(INNER[k])])
    return segs


LINES = _line_segments()

MEN = 12


@dataclass
class SState:
    pos: dict = field(default_factory=dict)      # point -> player
    to_move: int = 0
    placed: list = field(default_factory=lambda: [0, 0])
    first_jare: object = None                    # who milled first in placement
    trans_removals: int = 0                      # transition removals left (2,1,0)
    removing: bool = False                       # mill just made: remove an enemy
    freeing: bool = False                        # forced move to free the opponent
    since_removal: int = 0                       # plies since placement/removal
    reps: dict = field(default_factory=dict)
    dead: bool = False                           # unopenable lock -> draw
    winner: object = None


class Shax(Game):
    name = "Shax"
    DRAW_PLIES = 50   # plies with no placement and no removal -> draw

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        st = SState()
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- helpers -----------------------------------------------------------
    def _placing(self, state):
        return state.placed[0] + state.placed[1] < 2 * MEN

    def _on_board(self, pos, pl):
        return sum(1 for v in pos.values() if v == pl)

    def _is_mill(self, pos, point, pl):
        return any(all(pos.get(q) == pl for q in m) for m in MILLS_AT[point])

    def _slides(self, pos, pl):
        out = []
        for p, v in pos.items():
            if v != pl:
                continue
            for q in ADJ[p]:
                if q not in pos:
                    out.append(f"{p}>{q}")
        return out

    def _frees(self, pos, move, mover, blocked):
        """Does `mover` playing slide `move` leave `blocked` with a slide?"""
        frm, to = move.split(">")
        np = dict(pos)
        np[to] = np.pop(frm)
        return any(True for _ in self._slides(np, blocked))

    def _enemy_points(self, pos, enemy):
        """Shax: a capture may take ANY enemy man, mills give no protection."""
        return [p for p in POINTS if pos.get(p) == enemy]

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        pl = state.to_move
        if state.trans_removals > 0 or state.removing:
            return self._enemy_points(state.pos, 1 - pl)
        if self._placing(state):
            return [p for p in POINTS if p not in state.pos]
        if state.freeing:
            blocked = 1 - pl
            return [m for m in self._slides(state.pos, pl)
                    if self._frees(state.pos, m, pl, blocked)]
        return self._slides(state.pos, pl)

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        pos = dict(state.pos)
        placed = list(state.placed)
        first_jare = state.first_jare
        trans = state.trans_removals
        since = state.since_removal + 1
        removing = False
        freeing = False

        if state.trans_removals > 0:
            # transition removal (board just filled): take any enemy man
            del pos[move]
            trans -= 1
            since = 0
            nxt = 1 - pl
        elif state.removing:
            del pos[move]
            since = 0
            nxt = 1 - pl
        elif self._placing(state):
            pos[move] = pl
            placed[pl] += 1
            since = 0
            if first_jare is None and self._is_mill(pos, move, pl):
                first_jare = pl
            if placed[0] + placed[1] == 2 * MEN:
                # board full: priority = first jare maker, else the 2nd placer
                nxt = first_jare if first_jare is not None else 1
                trans = 2
            else:
                nxt = 1 - pl
        else:
            frm, to = move.split(">")
            pos[to] = pos.pop(frm)
            if (not state.freeing and self._is_mill(pos, to, pl)
                    and self._enemy_points(pos, 1 - pl)):
                # a new jare: same player removes an enemy man (from anywhere).
                # A forced freeing move never captures, even if it mills (oodan).
                removing = True
                nxt = pl
            else:
                nxt = 1 - pl

        ns = SState(pos=pos, to_move=nxt, placed=placed, first_jare=first_jare,
                    trans_removals=trans, removing=removing, freeing=freeing,
                    since_removal=since, reps=dict(state.reps),
                    dead=state.dead, winner=state.winner)
        self._settle(ns)
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        return ns

    def _settle(self, ns):
        """At the start of `ns.to_move`'s turn decide reduction / blockade."""
        if ns.winner is not None or ns.dead:
            return
        if ns.trans_removals > 0 or ns.removing or self._placing(ns):
            return  # a placement/removal is always available
        pl = ns.to_move
        if self._on_board(ns.pos, pl) < 3:
            ns.winner = 1 - pl           # reduced to two men: loss
            return
        if ns.since_removal >= self.DRAW_PLIES:
            return                       # draw clock has run out
        if self._slides(ns.pos, pl):
            ns.freeing = False
            return
        # `pl` is blocked -- they never lose for that: the opponent must free
        # them ("jid i sii aan jar aheyn").
        opp = 1 - pl
        opp_slides = self._slides(ns.pos, opp)
        frees = [m for m in opp_slides if self._frees(ns.pos, m, opp, pl)]
        if not frees:
            ns.dead = True               # nobody can open the position: draw
            return
        ns.to_move = opp
        ns.freeing = True

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.dead
                     or state.since_removal >= self.DRAW_PLIES
                     or state.reps.get(self._key(state), 0) >= 3))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    def heuristic(self, state):
        """Material + mobility eval. Returns a payoff PER SEAT (list of 2)."""
        c0 = self._on_board(state.pos, 0) + (MEN - state.placed[0])
        c1 = self._on_board(state.pos, 1) + (MEN - state.placed[1])
        m0 = len(self._slides(state.pos, 0))
        m1 = len(self._slides(state.pos, 1))
        v = math.tanh(0.35 * (c0 - c1) + 0.04 * (m0 - m1))
        return [v, -v]

    # ---- keys / serialize --------------------------------------------------
    def _key(self, state):
        board = ",".join(f"{p}:{state.pos[p]}" for p in POINTS if p in state.pos)
        return (f"{board}#{state.to_move}#{state.placed[0]},{state.placed[1]}"
                f"#{state.trans_removals}#{int(state.removing)}"
                f"#{int(state.freeing)}")

    def serialize(self, state):
        return {
            "pos": dict(state.pos),
            "to_move": state.to_move,
            "placed": list(state.placed),
            "first_jare": state.first_jare,
            "trans_removals": state.trans_removals,
            "removing": state.removing,
            "freeing": state.freeing,
            "since_removal": state.since_removal,
            "reps": dict(state.reps),
            "dead": state.dead,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return SState(pos=dict(d["pos"]), to_move=d["to_move"],
                      placed=list(d["placed"]), first_jare=d.get("first_jare"),
                      trans_removals=d.get("trans_removals", 0),
                      removing=d.get("removing", False),
                      freeing=d.get("freeing", False),
                      since_removal=d.get("since_removal", 0),
                      reps=dict(d.get("reps", {})),
                      dead=d.get("dead", False), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if state.trans_removals > 0 or state.removing:
            return f"x{move}"
        if ">" in move:
            s = move.replace(">", "-")
            return f"{s} (frees)" if state.freeing else s
        return f"@{move}"

    def render(self, state, perspective=None):
        cells = []
        for p in POINTS:
            x, y = (int(t) for t in p.split(","))
            s = 0.42
            cells.append({"id": p,
                          "points": [[x - s, y - s], [x + s, y - s],
                                     [x + s, y + s], [x - s, y + s]]})
        pieces = [{"cell": p, "owner": v} for p, v in state.pos.items()]
        names = {0: "White", 1: "Black"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        elif state.trans_removals > 0:
            n = 3 - state.trans_removals
            cap = f"{names[state.to_move]}: opening removal {n} of 2"
        elif state.removing:
            cap = f"{names[state.to_move]}: jare! remove an enemy man"
        elif self._placing(state):
            left = MEN - state.placed[state.to_move]
            jare = ("" if state.first_jare is None
                    else f" - first jare: {names[state.first_jare]}")
            cap = f"{names[state.to_move]} to place ({left} in hand){jare}"
        elif state.freeing:
            cap = (f"{names[state.to_move]} must free "
                   f"{names[1 - state.to_move]} (no capture)")
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
