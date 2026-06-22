"""Twelve Men's Morris -- Nine Men's Morris on the same 24-point board, with the
four diagonal lines connecting the corners of the three concentric squares added.

Identical to Nine Men's Morris except:

* each player has **twelve** men (not nine);
* the four ring corners each get a **diagonal spoke** joining the outer, middle
  and inner corner (e.g. top-left ``(0,0)-(1,1)-(2,2)``).  These four diagonals
  add four new mills and give each of the eight corner points an extra adjacency
  (to the corresponding corner of the neighbouring ring).

Everything else -- alternate placement then sliding along lines, mill-then-remove,
the not-from-a-mill removal restriction, flying when down to three men, and the
win/draw conditions -- is exactly as in Nine Men's Morris.

Because every point now lies on more than one mill, the board is famously
draw-prone.  Points are addressed by their grid coordinate ``"x,y"`` on a 0..6
layout (x right, y down).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# 24 points: outer ring, middle ring, inner ring (each an 8-cycle), wired by four
# mid-side spokes AND -- new for Twelve Men's Morris -- four corner diagonals.
OUTER = [(0, 0), (3, 0), (6, 0), (6, 3), (6, 6), (3, 6), (0, 6), (0, 3)]
MIDDLE = [(1, 1), (3, 1), (5, 1), (5, 3), (5, 5), (3, 5), (1, 5), (1, 3)]
INNER = [(2, 2), (3, 2), (4, 2), (4, 3), (4, 4), (3, 4), (2, 4), (2, 3)]
RINGS = [OUTER, MIDDLE, INNER]

POINTS = [f"{x},{y}" for ring in RINGS for (x, y) in ring]

# Mid-side spokes sit at ring indices 1,3,5,7; corners (the diagonal hubs) at
# indices 0,2,4,6.
SPOKE_IDX = (1, 3, 5, 7)
CORNER_IDX = (0, 2, 4, 6)


def _ring_adj():
    adj = {p: set() for p in POINTS}
    for ring in RINGS:
        ids = [f"{x},{y}" for (x, y) in ring]
        for i in range(8):
            adj[ids[i]].add(ids[(i + 1) % 8])
            adj[ids[i]].add(ids[(i - 1) % 8])
    # spokes connect the mid-side point of each ring
    for k in SPOKE_IDX:
        o = f"{OUTER[k][0]},{OUTER[k][1]}"
        m = f"{MIDDLE[k][0]},{MIDDLE[k][1]}"
        c = f"{INNER[k][0]},{INNER[k][1]}"
        adj[o].add(m); adj[m].add(o)
        adj[m].add(c); adj[c].add(m)
    # NEW: corner diagonals connect the corner point of each ring
    for k in CORNER_IDX:
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
    for k in SPOKE_IDX:                      # four mid-side spokes
        mills.append((f"{OUTER[k][0]},{OUTER[k][1]}",
                      f"{MIDDLE[k][0]},{MIDDLE[k][1]}",
                      f"{INNER[k][0]},{INNER[k][1]}"))
    for k in CORNER_IDX:                     # NEW: four corner diagonals
        mills.append((f"{OUTER[k][0]},{OUTER[k][1]}",
                      f"{MIDDLE[k][0]},{MIDDLE[k][1]}",
                      f"{INNER[k][0]},{INNER[k][1]}"))
    return mills


MILLS = _mills()
MILLS_AT = {p: [m for m in MILLS if p in m] for p in POINTS}


# Cosmetic line segments for the renderer: ring edges + mid-side spokes + diagonals.
def _line_segments():
    segs = []
    for ring in RINGS:
        for i in range(8):
            segs.append([list(ring[i]), list(ring[(i + 1) % 8])])
    for k in SPOKE_IDX:
        segs.append([list(OUTER[k]), list(MIDDLE[k])])
        segs.append([list(MIDDLE[k]), list(INNER[k])])
    for k in CORNER_IDX:                     # NEW: four corner diagonals
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


class TwelveMensMorris(Game):
    uid = "twelve_mens_morris"
    name = "Twelve Men's Morris"
    MEN = 12
    FLYING = True          # the standard rule: a player down to 3 men may fly anywhere
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
    def _count(self, state, pl):
        return sum(1 for v in state.pos.values() if v == pl) + (self.MEN - state.placed[pl])

    def _on_board(self, state, pl):
        return sum(1 for v in state.pos.values() if v == pl)

    def _is_mill(self, pos, point, pl):
        return any(all(pos.get(q) == pl for q in m) for m in MILLS_AT[point])

    def _phase_placing(self, state, pl):
        return state.placed[pl] < self.MEN

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
        if self._phase_placing(state, pl):
            return [p for p in POINTS if p not in state.pos]
        # movement phase
        flying = self.FLYING and self._on_board(state, pl) == 3
        empties = [p for p in POINTS if p not in state.pos]
        out = []
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
        removing = False
        winner = state.winner

        if state.removing:
            del pos[move]                       # remove the chosen enemy man
            since = 0
            nxt = 1 - pl
            ns = self._mk(pos, nxt, placed, False, since, state)
            return self._settle(ns)

        if ">" in move:                          # movement
            frm, to = move.split(">")
            pos[to] = pos.pop(frm)
            landed = to
        else:                                    # placement
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
        # reduced below three men (only meaningful once placing is done)
        if not self._phase_placing(ns, pl) and self._on_board(ns, pl) < 3:
            ns.winner = 1 - pl
            return ns
        if not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = 1 - pl
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        if state.winner is not None:
            return False
        # Full-board deadlock: 12+12 men fill all 24 points at the end of the
        # placement phase with no mill pending (no capture left to free a square).
        # Nobody can slide, so neither side is at fault -- traditional Twelve
        # Men's Morris scores this as a DRAW (the variant's signature drawishness),
        # NOT a loss for the player to move. (No recursion: avoids legal_moves.)
        if not state.removing and len(state.pos) == len(POINTS):
            return True
        return (state.since_mill >= self.DRAW_PLIES
                or state.reps.get(self._key(state), 0) >= 3)

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
        elif self._phase_placing(state, state.to_move):
            left = self.MEN - state.placed[state.to_move]
            cap = f"{names[state.to_move]} to place ({left} in hand)"
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
