"""Mū Tōrere -- the Māori sliding game on an eight-pointed star.

The board is an eight-pointed star: eight outer points called **kewai** arranged
in a ring (indexed '0'..'7' clockwise) plus a central point, the **putahi**
(id 'c'). Adjacency: each kewai touches its two ring-neighbours (mod 8) and the
putahi; the putahi touches all eight kewai.

Two players, four men each. Player 0 starts on kewai 0,1,2,3 and player 1 on
kewai 4,5,6,7; the putahi starts empty. Players alternate; a move slides ONE of
your men to an EMPTY adjacent point. The only subtlety is moving onto the empty
putahi from a kewai: that is allowed only when one of the kewai's two ring
neighbours holds an ENEMY man. A player with no legal move loses (no captures).

Point ids and their cosmetic geometry (star tips + centre, plus the spoke/ring
lines) are supplied to the generic ``polygons`` renderer; adjacency lives in
code, mirroring nine_mens_morris.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

# Eight kewai on a circle (clockwise from the top) + the central putahi.
CENTER = (5.0, 5.0)
RADIUS = 4.0
PUTAHI = "c"

KEWAI = [str(i) for i in range(8)]
POINTS = KEWAI + [PUTAHI]


def _kewai_xy(i):
    a = math.pi / 2 - i * (2 * math.pi / 8)   # top, going clockwise
    return (CENTER[0] + math.cos(a) * RADIUS,
            CENTER[1] - math.sin(a) * RADIUS)  # screen y grows downward


XY = {str(i): _kewai_xy(i) for i in range(8)}
XY[PUTAHI] = CENTER


def _adjacency():
    adj = {p: set() for p in POINTS}
    for i in range(8):
        a = str(i)
        adj[a].add(str((i + 1) % 8))
        adj[a].add(str((i - 1) % 8))
        adj[a].add(PUTAHI)
        adj[PUTAHI].add(a)
    return {p: frozenset(s) for p, s in adj.items()}


ADJ = _adjacency()

# Ring neighbours of each kewai (the two kewai it touches -- excludes the putahi).
RING_NEIGHBOURS = {str(i): (str((i - 1) % 8), str((i + 1) % 8)) for i in range(8)}


def _line_segments():
    """Cosmetic geometry for the renderer: 8 spokes (centre->kewai) + the ring."""
    segs = []
    for i in range(8):
        segs.append([list(XY[str(i)]), list(XY[PUTAHI])])           # spoke
        segs.append([list(XY[str(i)]), list(XY[str((i + 1) % 8)])])  # ring edge
    return segs


LINES = _line_segments()


@dataclass
class TState:
    pos: dict = field(default_factory=dict)        # point -> player (0/1)
    to_move: int = 0
    ply: int = 0                                    # half-moves played (draw clock)
    winner: object = None                           # set when a player is stuck


class MuTorere(Game):
    uid = "mu_torere"
    name = "Mū Tōrere"
    MEN = 4
    # Defensive hard cap. The real game terminates because a stuck player loses;
    # this only guards against pathological non-progress under random play.
    PLY_CAP = 200

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        pos = {str(i): 0 for i in range(4)}      # player 0 on kewai 0,1,2,3
        pos.update({str(i): 1 for i in range(4, 8)})  # player 1 on kewai 4,5,6,7
        # putahi ('c') starts empty
        return TState(pos=pos, to_move=0, ply=0, winner=None)

    def current_player(self, state):
        return state.to_move

    # ---- move legality -----------------------------------------------------
    def _can_enter_putahi(self, state, kewai, pl):
        """Rule (b): a man may slide from a kewai onto the empty putahi only if
        one of that kewai's two ring-neighbours holds an ENEMY man."""
        enemy = 1 - pl
        return any(state.pos.get(n) == enemy for n in RING_NEIGHBOURS[kewai])

    def _moves_for(self, state, pl):
        out = []
        for src, owner in state.pos.items():
            if owner != pl:
                continue
            for dst in ADJ[src]:
                if dst in state.pos:
                    continue                    # destination occupied
                if dst == PUTAHI:
                    # rule (b): kewai -> empty putahi gated by an adjacent enemy
                    if not self._can_enter_putahi(state, src, pl):
                        continue
                # rule (a) kewai->kewai and rule (c) putahi->kewai: always allowed
                out.append(f"{src}>{dst}")
        return out

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        return self._moves_for(state, state.to_move)

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        src, dst = move.split(">")
        pos = dict(state.pos)
        pos[dst] = pos.pop(src)
        ns = TState(pos=pos, to_move=1 - pl, ply=state.ply + 1, winner=None)
        # Decide loss-by-no-move for the player now on the move.
        if ns.ply < self.PLY_CAP and not self._moves_for(ns, ns.to_move):
            ns.winner = pl                      # opponent (the mover) wins
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return state.winner is None and state.ply >= self.PLY_CAP

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialize ---------------------------------------------------------
    def serialize(self, state):
        return {
            "pos": dict(state.pos),
            "to_move": state.to_move,
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return TState(pos=dict(d["pos"]), to_move=d["to_move"],
                      ply=d.get("ply", 0), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        src, dst = move.split(">")
        name = lambda p: "putahi" if p == PUTAHI else f"kewai {p}"
        return f"{name(src)}->{name(dst)}"

    def render(self, state, perspective=None):
        cells = []
        s = 0.5
        for p in POINTS:
            x, y = XY[p]
            cells.append({"id": p,
                          "points": [[x - s, y - s], [x + s, y - s],
                                     [x + s, y + s], [x - s, y + s]]})
        pieces = [{"cell": p, "owner": v} for p, v in state.pos.items()]
        names = {0: "Black", 1: "White"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw (ply cap)"
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
