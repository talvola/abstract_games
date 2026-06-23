"""Pong Hau K'i -- a traditional Chinese/Korean two-player blocking game.

The board has **five points** and **seven edges** (the count given by MathWorld
and Wikipedia). Geometrically it is a square of four corners plus a central
point:

    tl --------- tr          (NB: the top side tl--tr is NOT an edge)
    | \         / |
    |   \     /   |
    |     \ /     |
    |      c      |
    |     / \     |
    |   /     \   |
    | /         \ |
    bl --------- br

Adjacency (7 edges):
  - the centre ``c`` connects to all four corners: c-tl, c-tr, c-bl, c-br;
  - three of the four square sides are edges: tl-bl (left), bl-br (bottom),
    tr-br (right);
  - the fourth side, **tl-tr (top), is NOT an edge** -- exactly one pair of
    same-side corners is left unconnected. This single missing edge is what
    creates Pong Hau K'i's blocking dynamic.

Setup: each player has two stones. Player 0 (Black) occupies the two top
corners (tl, tr); player 1 (White) occupies the two bottom corners (bl, br);
the centre c starts empty. Player 0 moves first.

Move: slide one of your stones along an edge into the single empty point. There
are no captures. A player who has no legal move on their turn loses.

Point ids and cosmetic geometry (corners + centre, and the 7 edge lines) are
supplied to the generic ``polygons`` renderer; adjacency lives in code, in the
same style as nine_mens_morris / mu_torere.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# Five points with screen-space (x grows right, y grows down) coordinates.
XY = {
    "tl": (3.0, 3.0),
    "tr": (7.0, 3.0),
    "bl": (3.0, 7.0),
    "br": (7.0, 7.0),
    "c": (5.0, 5.0),
}
POINTS = ["tl", "tr", "bl", "br", "c"]

# The seven undirected edges. tl-tr (the top side) is deliberately absent.
EDGES = [
    ("c", "tl"), ("c", "tr"), ("c", "bl"), ("c", "br"),  # 4 centre spokes
    ("tl", "bl"),   # left side
    ("bl", "br"),   # bottom side
    ("tr", "br"),   # right side
]


def _adjacency():
    adj = {p: set() for p in POINTS}
    for a, b in EDGES:
        adj[a].add(b)
        adj[b].add(a)
    return {p: frozenset(s) for p, s in adj.items()}


ADJ = _adjacency()

LINES = [[list(XY[a]), list(XY[b])] for a, b in EDGES]


@dataclass
class PState:
    pos: dict = field(default_factory=dict)        # point -> player (0/1)
    to_move: int = 0
    ply: int = 0                                    # half-moves played (draw clock)
    winner: object = None                           # set when a player is stuck


class PongHauKi(Game):
    uid = "pong_hau_ki"
    name = "Pong Hau K'i"
    # Pong Hau K'i is a famous frequent-draw game: with two stones each on five
    # points the position graph is tiny and best play cycles. A stuck player
    # loses, but most lines never reach a stuck position -- so a no-progress /
    # hard ply-cap draw is REQUIRED to guarantee termination under random play.
    PLY_CAP = 60

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        pos = {"tl": 0, "tr": 0, "bl": 1, "br": 1}   # centre 'c' empty
        return PState(pos=pos, to_move=0, ply=0, winner=None)

    def current_player(self, state):
        return state.to_move

    # ---- move legality -----------------------------------------------------
    def _moves_for(self, state, pl):
        out = []
        for src, owner in state.pos.items():
            if owner != pl:
                continue
            for dst in ADJ[src]:
                if dst not in state.pos:             # destination is the empty point
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
        ns = PState(pos=pos, to_move=1 - pl, ply=state.ply + 1, winner=None)
        # Decide loss-by-no-move for the player now on the move.
        if ns.ply < self.PLY_CAP and not self._moves_for(ns, ns.to_move):
            ns.winner = pl                           # opponent (the mover) wins
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
        return PState(pos=dict(d["pos"]), to_move=d["to_move"],
                      ply=d.get("ply", 0), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        src, dst = move.split(">")
        return f"{src}->{dst}"

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
