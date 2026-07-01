"""Lasker Morris (Ten Men's Morris) -- Emanuel Lasker's improved mill game.

Same 24-point board as Nine Men's Morris (three concentric squares joined by the
four mid-side spokes; 16 mills; no diagonals), but with two changes that make the
game more dynamic:

  * each player has **ten** men instead of nine, and
  * there is **no rigid two-phase structure** -- on every turn, as long as you
    still have men in hand, you may *either* place a new man on any empty point
    *or* slide an already-placed man to an adjacent empty point.  Placing and
    moving are freely interleaved from the very first move.  Only once your hand
    is empty are you restricted to sliding.

Forming a "mill" (three of your men in a line) lets you remove one enemy man.
Reduce the opponent below three men, or leave them with no legal move, to win.

The board, adjacency, mill table and RenderSpec are identical to Nine Men's
Morris -- the proven ``polygons`` morris render.  Points are addressed by their
grid coordinate ``"x,y"`` on a 0..6 layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# 24 points: outer ring, middle ring, inner ring (each an 8-cycle), wired by four
# spokes at the mid-side points. Coordinates on a 0..6 grid (x right, y down).
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
    # spokes connect the mid-side point of each ring (indices 1,3,5,7)
    for k in (1, 3, 5, 7):
        o = f"{OUTER[k][0]},{OUTER[k][1]}"
        m = f"{MIDDLE[k][0]},{MIDDLE[k][1]}"
        c = f"{INNER[k][0]},{INNER[k][1]}"
        adj[o].add(m); adj[m].add(o)
        adj[m].add(c); adj[c].add(m)
    return {p: frozenset(s) for p, s in adj.items()}


ADJ = _ring_adj()


def _mills():
    mills = []
    for ring in RINGS:                      # four edges of three per ring
        ids = [f"{x},{y}" for (x, y) in ring]
        for k in (0, 2, 4, 6):
            mills.append((ids[k], ids[(k + 1) % 8], ids[(k + 2) % 8]))
    for k in (1, 3, 5, 7):                  # four spokes
        mills.append((f"{OUTER[k][0]},{OUTER[k][1]}",
                      f"{MIDDLE[k][0]},{MIDDLE[k][1]}",
                      f"{INNER[k][0]},{INNER[k][1]}"))
    return mills


MILLS = _mills()
MILLS_AT = {p: [m for m in MILLS if p in m] for p in POINTS}


# Cosmetic line segments for the renderer: the ring edges + the four spokes.
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


@dataclass
class MState:
    pos: dict = field(default_factory=dict)       # point -> player
    to_move: int = 0
    placed: list = field(default_factory=lambda: [0, 0])   # men placed per player
    removing: bool = False                          # a mill was just formed; remove an enemy
    since_mill: int = 0                             # plies since the last mill/placement (draw clock)
    reps: dict = field(default_factory=dict)
    winner: object = None                           # set when someone is reduced/stuck


class LaskerMorris(Game):
    uid = "lasker_morris"
    name = "Lasker Morris"
    MEN = 10
    FLYING = True          # optional: a player down to 3 men may fly anywhere
    DRAW_PLIES = 50        # plies with no mill and no placement -> draw

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        st = MState()
        self.FLYING = opts.get("flying", "yes") != "no"
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- helpers -----------------------------------------------------------
    def _in_hand(self, state, pl):
        return self.MEN - state.placed[pl]

    def _count(self, state, pl):
        return sum(1 for v in state.pos.values() if v == pl) + self._in_hand(state, pl)

    def _on_board(self, state, pl):
        return sum(1 for v in state.pos.values() if v == pl)

    def _is_mill(self, pos, point, pl):
        return any(all(pos.get(q) == pl for q in m) for m in MILLS_AT[point])

    def _removable(self, state, enemy):
        """Enemy men that may be removed: those not in a mill, unless all are."""
        men = [p for p, v in state.pos.items() if v == enemy]
        free = [p for p in men if not self._is_mill(state.pos, p, enemy)]
        return free if free else men

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        pl = state.to_move
        if state.removing:
            return self._removable(state, 1 - pl)
        in_hand = self._in_hand(state, pl)
        empties = [p for p in POINTS if p not in state.pos]
        out = []
        # Lasker's rule: while you still hold men in hand you MAY place a new man
        # OR slide an already-placed man -- both are legal on the same turn.
        if in_hand > 0:
            out.extend(empties)                       # placements (single-point strings)
        # slides -- available from move one, not only after the hand is empty.
        flying = self.FLYING and in_hand == 0 and self._on_board(state, pl) == 3
        for p, v in state.pos.items():
            if v != pl:
                continue
            targets = empties if flying else [q for q in ADJ[p] if q not in state.pos]
            for q in targets:
                out.append(f"{p}>{q}")
        return out

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        pos = dict(state.pos)
        placed = list(state.placed)
        since = state.since_mill + 1

        if state.removing:
            del pos[move]                       # remove the chosen enemy man
            since = 0
            ns = self._mk(pos, 1 - pl, placed, False, since, state)
            return self._settle(ns)

        if ">" in move:                          # slide (from>to)
            frm, to = move.split(">")
            pos[to] = pos.pop(frm)
            landed = to
        else:                                    # place from hand
            pos[move] = pl
            placed[pl] += 1
            since = 0
            landed = move

        if self._is_mill(pos, landed, pl) and self._removable_exists(pos, 1 - pl):
            # same player removes an enemy man before the turn passes
            ns = self._mk(pos, pl, placed, True, since, state)
            return ns
        ns = self._mk(pos, 1 - pl, placed, False, since, state)
        return self._settle(ns)

    def _removable_exists(self, pos, enemy):
        return any(v == enemy for v in pos.values())

    def _mk(self, pos, to_move, placed, removing, since, state):
        ns = MState(pos=pos, to_move=to_move, placed=placed, removing=removing,
                    since_mill=since, reps=dict(state.reps), winner=state.winner)
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        return ns

    def _settle(self, ns):
        """At the start of `ns.to_move`'s turn, decide loss-by-reduction/stuck."""
        pl = ns.to_move
        # reduced below three men (counting men still in hand -- a player who can
        # never again reach three men on the board has lost).
        if self._count(ns, pl) < 3:
            ns.winner = 1 - pl
            return ns
        if not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = 1 - pl
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.since_mill >= self.DRAW_PLIES
                     or state.reps.get(self._key(state), 0) >= 3))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- keys / serialize --------------------------------------------------
    def _key(self, state):
        board = ",".join(f"{p}:{state.pos[p]}" for p in POINTS if p in state.pos)
        return f"{board}#{state.to_move}#{state.placed[0]}{state.placed[1]}#{int(state.removing)}"

    def serialize(self, state):
        return {
            "pos": {p: v for p, v in state.pos.items()},
            "to_move": state.to_move,
            "placed": list(state.placed),
            "removing": state.removing,
            "since_mill": state.since_mill,
            "reps": dict(state.reps),
            "winner": state.winner,
        }

    def deserialize(self, d):
        return MState(pos=dict(d["pos"]), to_move=d["to_move"],
                      placed=list(d["placed"]), removing=d.get("removing", False),
                      since_mill=d.get("since_mill", 0), reps=dict(d.get("reps", {})),
                      winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if state.removing:
            return f"x{move}"
        if ">" in move:
            return move.replace(">", "-")
        return f"@{move}"

    def render(self, state, perspective=None):
        cells = []
        for (x, y) in [(int(p.split(",")[0]), int(p.split(",")[1])) for p in POINTS]:
            s = 0.42
            cells.append({"id": f"{x},{y}",
                          "points": [[x - s, y - s], [x + s, y - s],
                                     [x + s, y + s], [x - s, y + s]]})
        pieces = [{"cell": p, "owner": v} for p, v in state.pos.items()]
        names = {0: "White", 1: "Black"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        elif state.removing:
            cap = f"{names[state.to_move]}: remove an enemy man"
        else:
            left = self._in_hand(state, state.to_move)
            if left > 0:
                cap = f"{names[state.to_move]} to place or move ({left} in hand)"
            else:
                cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
