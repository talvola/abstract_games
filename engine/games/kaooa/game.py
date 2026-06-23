"""Kaooa (Vultures and Crows) -- a traditional Indian hunt game on a 10-point
five-pointed star (pentagram).

Asymmetric: player 0 = **Crows** (7 of them, placed one per turn, then moved),
player 1 = **Vulture** (a single bird that captures crows by jumping them). The
**Crows move first** (placing the first crow). After the first crow is on the
board the Vulture is dropped onto any empty point, and thereafter it may step or
jump-capture on its turns *while crows are still being placed*. Pieces step one
point along a drawn star segment to an empty point; the Vulture may instead jump
a single adjacent crow along a straight star line to the empty point beyond,
removing it (draughts-style short jump; no multi-jumps). **The Vulture wins by
capturing four crows; the Crows win by trapping the Vulture (it has no legal
move).** A no-progress ply cap ends the game in a draw for safety.

The 10 points are the 5 outer tips (T0..T4) and the 5 inner pentagon vertices
(I0..I4); adjacency is exactly the points joined by a single drawn star segment
(see ADJ below, derived geometrically from the {5/2} star strokes).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

CROW, VULTURE = 0, 1
CROWS_TOTAL = 7
CROWS_TO_LOSE = 4          # vulture wins once this many crows are captured
PLY_CAP = 300

# --- the 10 points -------------------------------------------------------
TIPS = ["T0", "T1", "T2", "T3", "T4"]
INNERS = ["I0", "I1", "I2", "I3", "I4"]
POINTS = TIPS + INNERS

# The five straight strokes of the pentagram, each listed as the ordered run of
# points it passes through (tip -> inner -> inner -> tip). Adjacency = every
# consecutive pair; jumps = every collinear (x, mid, beyond) triple.
STROKES = [
    ["T0", "I1", "I0", "T2"],
    ["T1", "I0", "I2", "T3"],
    ["T2", "I2", "I3", "T4"],
    ["T3", "I3", "I4", "T0"],
    ["T4", "I4", "I1", "T1"],
]


def _build_adj():
    adj = {p: set() for p in POINTS}
    for seq in STROKES:
        for i in range(len(seq) - 1):
            a, b = seq[i], seq[i + 1]
            adj[a].add(b)
            adj[b].add(a)
    return {p: frozenset(v) for p, v in adj.items()}


ADJ = _build_adj()


def _build_jumps():
    """over -> {src: land}: for each point `over`, the straight-line landing
    point reached by jumping from `src` over `over`. Derived from the collinear
    triples along each stroke."""
    jumps = {}            # (src, over) -> land
    for seq in STROKES:
        for i in range(len(seq) - 2):
            a, m, b = seq[i], seq[i + 1], seq[i + 2]
            jumps[(a, m)] = b
            jumps[(b, m)] = a
    return jumps


JUMPS = _build_jumps()    # (src, over) -> land

# Display coordinates for the polygons renderer (screen y grows downward).
COORDS = {
    "T0": (0.0, -5.0), "T1": (4.755, -1.545), "T2": (2.939, 4.045),
    "T3": (-2.939, 4.045), "T4": (-4.755, -1.545),
    "I0": (1.817, 0.59), "I1": (1.123, -1.545), "I2": (0.0, 1.91),
    "I3": (-1.817, 0.59), "I4": (-1.123, -1.545),
}

# Cosmetic lines tracing the five star strokes (endpoint tip to endpoint tip).
LINES = [[list(COORDS[seq[0]]), list(COORDS[seq[-1]])] for seq in STROKES]


@dataclass
class KState:
    board: dict = field(default_factory=dict)        # point-id -> CROW/VULTURE
    to_move: int = CROW
    in_hand: int = CROWS_TOTAL                        # crows yet to be placed
    vulture_placed: bool = False
    captured: int = 0                                 # crows captured by vulture
    ply: int = 0
    winner: object = None


class Kaooa(Game):
    uid = "kaooa"
    name = "Kaooa"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return KState(board={}, to_move=CROW)

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _vulture_pos(self, board):
        for p, who in board.items():
            if who == VULTURE:
                return p
        return None

    def _vulture_moves(self, board):
        """yield (frm, to, captured_or_None) for the vulture's steps & jumps."""
        v = self._vulture_pos(board)
        if v is None:
            return
        for nb in ADJ[v]:
            if nb not in board:
                yield v, nb, None
            elif board[nb] == CROW:
                land = JUMPS.get((v, nb))
                if land is not None and land not in board:
                    yield v, land, nb       # jump capturing the crow at nb

    def _crow_slides(self, board):
        for p, who in board.items():
            if who != CROW:
                continue
            for nb in ADJ[p]:
                if nb not in board:
                    yield p, nb

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        if state.to_move == CROW:
            if state.in_hand > 0:
                return [p for p in POINTS if p not in state.board]
            return [f"{f}>{t}" for (f, t) in self._crow_slides(state.board)]
        # vulture's turn
        if not state.vulture_placed:
            # vulture drops onto any empty point (the first crow is already down)
            return [p for p in POINTS if p not in state.board]
        return [f"{f}>{t}" for (f, t, _) in self._vulture_moves(state.board)]

    def apply_move(self, state, move, rng=None):
        board = dict(state.board)
        in_hand, captured = state.in_hand, state.captured
        vulture_placed = state.vulture_placed
        if ">" not in move:                      # a placement / drop
            if state.to_move == CROW:
                board[move] = CROW
                in_hand -= 1
            else:
                board[move] = VULTURE
                vulture_placed = True
        else:
            frm, to = move.split(">")
            who = board.pop(frm)
            board[to] = who
            if who == VULTURE:
                over = self._jumped_over(frm, to)
                if over is not None and board.get(over) == CROW:
                    del board[over]
                    captured += 1
        ns = KState(board=board, to_move=1 - state.to_move, in_hand=in_hand,
                    vulture_placed=vulture_placed, captured=captured,
                    ply=state.ply + 1)
        self._settle(ns)
        return ns

    def _jumped_over(self, frm, to):
        """the midpoint of a vulture jump frm->to, or None for a plain step."""
        if to in ADJ[frm]:
            return None                          # adjacent => a step, not a jump
        for over in ADJ[frm]:
            if JUMPS.get((frm, over)) == to:
                return over
        return None

    def _settle(self, ns):
        if ns.captured >= CROWS_TO_LOSE:
            ns.winner = VULTURE
            return
        # the side to move with no legal move loses (vulture trapped -> crows win)
        if not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = 1 - ns.to_move

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return state.winner is None and state.ply >= PLY_CAP

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialise ---------------------------------------------------------
    def serialize(self, state):
        return {
            "board": dict(state.board),
            "to_move": state.to_move,
            "in_hand": state.in_hand,
            "vulture_placed": state.vulture_placed,
            "captured": state.captured,
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return KState(
            board=dict(d["board"]),
            to_move=d["to_move"], in_hand=d["in_hand"],
            vulture_placed=d["vulture_placed"], captured=d["captured"],
            ply=d.get("ply", 0), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if ">" not in move:
            who = "crow" if state.to_move == CROW else "vulture"
            return f"{who}@{move}"
        frm, to = move.split(">")
        cap = self._jumped_over(frm, to) is not None
        return f"{frm}{'x' if cap else '-'}{to}"

    def render(self, state, perspective=None):
        s = 0.55
        cells = [{"id": p,
                  "points": [[COORDS[p][0] - s, COORDS[p][1] - s],
                             [COORDS[p][0] + s, COORDS[p][1] - s],
                             [COORDS[p][0] + s, COORDS[p][1] + s],
                             [COORDS[p][0] - s, COORDS[p][1] + s]]}
                 for p in POINTS]
        pieces = [{"cell": p, "owner": who,
                   "label": "V" if who == VULTURE else "C"}
                  for p, who in state.board.items()]
        if state.winner is not None:
            cap = ("Vulture wins" if state.winner == VULTURE else "Crows win")
        elif self._draw(state):
            cap = "Draw"
        else:
            side = "Crows" if state.to_move == CROW else "Vulture"
            if state.to_move == CROW and state.in_hand > 0:
                extra = f" — place ({state.in_hand} in hand)"
            elif state.to_move == VULTURE and not state.vulture_placed:
                extra = " — drop the vulture"
            else:
                extra = ""
            cap = (f"{side} to move{extra}  ·  "
                   f"captured {state.captured}/{CROWS_TO_LOSE}")
        return {
            "board": {"type": "polygons", "cells": cells, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
