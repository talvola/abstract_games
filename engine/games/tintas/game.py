"""Tintas (Dieter Stein, 2016) -- the colour-collection game.

49 pieces (7 each of 7 colours) are scattered AT RANDOM over a 49-cell hex
board (a hexhex-4 core of 37 cells plus six 2-cell bumps in 6-fold pinwheel
symmetry -- verified cell-for-cell against the official board diagram at
spielstein.com). One neutral pawn starts off the board.

First move of the game: place the pawn on any cell and collect the piece
there. Every later turn: slide the pawn in a straight hex line over any
number of vacant cells; it stops on the FIRST occupied cell and you collect
that piece. You MAY then keep sliding (any direction) as long as each further
slide lands on a piece of the SAME colour as those collected this turn --
stopping is always allowed (an explicit "end" sub-move). If the pawn sees no
piece in any of its six lines, you must JUMP it to any occupied cell, collect
that piece, and the turn ends immediately (no chaining after a jump).

WIN: collect all 7 pieces of one colour (instant), or -- once NO player can
still complete a colour (i.e. both players hold at least one piece of every
colour) -- the player holding 4+ pieces in at least 4 different colours wins.
The board empties in at most 49 collections, and with an empty board exactly
one player has 4+ majorities, so the game always ends with a winner.

Randomness (the initial spread) happens in ``initial_state`` and is stored in
the state; ``has_randomness`` is true. Per the official rule, the spread is
re-randomised if all seven pieces of any one colour come out adjacent as a
single group.

Move encoding (sub-move style, like the multi-move chess/backgammon pattern):
every move is a single cell id "q,r" -- the cell the pawn goes to (placement,
slide landing, or stuck-jump target; a state never offers two kinds at once)
-- plus the non-cell action "end" to stop an optional chain. Single-cell moves
give one-click play in the generic UI, and optional continuation is trivially
expressible (targets + an "end" button).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from agp.game import Game

# --- board geometry: hexhex-4 core (37) + six 2-cell pinwheel bumps = 49 ---
RADIUS = 3
_CORE = {
    (q, r)
    for q in range(-RADIUS, RADIUS + 1)
    for r in range(-RADIUS, RADIUS + 1)
    if max(abs(q), abs(r), abs(q + r)) <= RADIUS
}
# Six 2-cell bumps on the 4th ring; each maps to the next under the 60-degree
# rotation (q, r) -> (-r, q+r). Verified against the official board diagram.
BUMPS = [
    (2, -4), (3, -4),
    (4, -2), (4, -1),
    (2, 2), (1, 3),
    (-2, 4), (-3, 4),
    (-4, 2), (-4, 1),
    (-2, -2), (-1, -3),
]
CELLS = tuple(sorted(_CORE | set(BUMPS)))
assert len(CELLS) == 49
CELLSET = frozenset(CELLS)

# the 6 axial hex directions
DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]

COLORS = ("R", "O", "Y", "G", "B", "P", "W")
COLOR_NAMES = {"R": "red", "O": "orange", "Y": "yellow", "G": "green",
               "B": "blue", "P": "purple", "W": "white"}
# piece colours sampled from the official diagrams
FILL = {"R": "#ed1c24", "O": "#f7941d", "Y": "#ffe714", "G": "#5fc22e",
        "B": "#29abe2", "P": "#9266cc", "W": "#f8f8f4"}
STROKE = {"R": "#7c0e12", "O": "#8a5210", "Y": "#8a7a00", "G": "#2d6414",
          "B": "#14587a", "P": "#4d3573", "W": "#555555"}

# Pointy-top hex pixel layout matching the web hex renderer (R=30):
# x = SQRT3*(q + r/2)*R, y = 1.5*r*R; vertices at 60*i - 30 degrees.
HEX_R = 30.0
_SQRT3 = math.sqrt(3.0)


def _hex_poly(q, r):
    cx, cy = _SQRT3 * (q + r / 2.0) * HEX_R, 1.5 * r * HEX_R
    pts = []
    for i in range(6):
        a = math.radians(60 * i - 30)
        pts.append([round(cx + HEX_R * math.cos(a), 3),
                    round(cy + HEX_R * math.sin(a), 3)])
    return pts


def _cid(c):
    return f"{c[0]},{c[1]}"


def _cell(s):
    q, r = s.split(",")
    return (int(q), int(r))


def _zero_hand():
    return {c: 0 for c in COLORS}


@dataclass
class TState:
    board: dict = field(default_factory=dict)  # (q,r) -> colour letter
    pawn: object = None                        # (q,r) or None (pre-placement)
    collected: list = field(default_factory=lambda: [_zero_hand(), _zero_hand()])
    to_move: int = 0
    chain: object = None   # colour letter while a same-colour chain may continue
    winner: object = None


class Tintas(Game):
    uid = "tintas"
    name = "Tintas"

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def _one_clump(self, cells):
        """True iff `cells` (7 of them) form ONE hex-adjacent group."""
        cells = set(cells)
        start = next(iter(cells))
        seen = {start}
        stack = [start]
        while stack:
            q, r = stack.pop()
            for dq, dr in DIRS:
                n = (q + dq, r + dr)
                if n in cells and n not in seen:
                    seen.add(n)
                    stack.append(n)
        return len(seen) == len(cells)

    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        bag = [c for c in COLORS for _ in range(7)]
        while True:
            rng.shuffle(bag)
            board = dict(zip(CELLS, bag))
            # official setup rule: only if all SEVEN pieces of one colour lie
            # adjacent as one group must the distribution be changed
            by_col = {c: [] for c in COLORS}
            for cell, col in board.items():
                by_col[col].append(cell)
            if not any(self._one_clump(cs) for cs in by_col.values()):
                return TState(board=board)

    def current_player(self, state):
        return state.to_move

    # ---- move generation ----------------------------------------------------
    def _slide_targets(self, state, color=None):
        """First occupied cell along each of the 6 lines from the pawn
        (skipping vacant cells); optionally filtered to `color`."""
        out = []
        pq, pr = state.pawn
        for dq, dr in DIRS:
            q, r = pq + dq, pr + dr
            while (q, r) in CELLSET:
                col = state.board.get((q, r))
                if col is not None:
                    if color is None or col == color:
                        out.append((q, r))
                    break
                q, r = q + dq, r + dr
        return out

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        if state.pawn is None:                      # first move: place anywhere
            return [_cid(c) for c in CELLS]
        if state.chain is not None:                 # optional same-colour chain
            cont = [_cid(c) for c in self._slide_targets(state, state.chain)]
            return cont + ["end"]
        slides = self._slide_targets(state)
        if slides:
            return [_cid(c) for c in slides]
        # stuck: jump to any occupied cell (turn will end after)
        return [_cid(c) for c in sorted(state.board)]

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        collected = [dict(state.collected[0]), dict(state.collected[1])]
        pl = state.to_move

        if move == "end":                           # stop an optional chain
            ns = TState(board=dict(state.board), pawn=state.pawn,
                        collected=collected, to_move=1 - pl, chain=None)
            return self._settle(ns)

        cell = _cell(move)
        board = dict(state.board)
        col = board.pop(cell)
        collected[pl][col] += 1

        if state.pawn is None:                      # opening placement
            ns = TState(board=board, pawn=cell, collected=collected,
                        to_move=1 - pl, chain=None)
            return self._settle(ns)

        if state.chain is None and not self._slide_targets(state):
            # stuck-jump: collect and the turn ends immediately (no chain)
            ns = TState(board=board, pawn=cell, collected=collected,
                        to_move=1 - pl, chain=None)
            return self._settle(ns)

        # a slide landing (turn start or chain continuation)
        ns = TState(board=board, pawn=cell, collected=collected,
                    to_move=pl, chain=col)
        ns = self._settle(ns)
        if ns.winner is not None:
            return ns
        if self._slide_targets(ns, col):            # may keep collecting `col`
            return ns
        ns.to_move = 1 - pl                         # no continuation: turn ends
        ns.chain = None
        return ns

    # ---- outcome ------------------------------------------------------------
    def _settle(self, ns):
        """Instant 7-of-a-colour win; else the official end condition: the game
        goes on only as long as one player can still get seven of one colour --
        once that is impossible (both players hold >=1 of every colour), the
        player with 4+ pieces in at least 4 colours wins (at most one player
        can, since 4 pieces of a colour is that colour's majority)."""
        for p in (0, 1):
            if any(ns.collected[p][c] >= 7 for c in COLORS):
                ns.winner = p
                return ns
        seven_possible = any(ns.collected[1 - p][c] == 0
                             for p in (0, 1) for c in COLORS)
        if not seven_possible:
            for p in (0, 1):
                if sum(1 for c in COLORS if ns.collected[p][c] >= 4) >= 4:
                    ns.winner = p
                    return ns
        return ns

    def is_terminal(self, state):
        if state.winner is not None:
            return True
        # defensive: an empty board is always decided by _settle before this
        # (with the board empty every colour is fully split, so one player has
        # 4+ majorities), but never leave a stateless dead end
        return state.pawn is not None and not state.board

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- heuristic (MCTS rollout-cutoff eval) --------------------------------
    def heuristic(self, state):
        """Progress toward the two win conditions, squashed to (-1, 1)."""
        sc = [0.0, 0.0]
        for p in (0, 1):
            mine, theirs = state.collected[p], state.collected[1 - p]
            best7 = max((mine[c] for c in COLORS if theirs[c] == 0), default=0)
            majors = sum(min(mine[c], 4) for c in COLORS)
            sc[p] = 0.5 * best7 / 7.0 + 0.5 * min(majors / 16.0, 1.0)
        v = math.tanh(2.0 * (sc[0] - sc[1]))
        return [v, -v]

    # ---- serialize -----------------------------------------------------------
    def serialize(self, state):
        return {
            "board": {_cid(c): state.board[c] for c in sorted(state.board)},
            "pawn": None if state.pawn is None else _cid(state.pawn),
            "collected": [{c: state.collected[p][c] for c in COLORS}
                          for p in (0, 1)],
            "to_move": state.to_move,
            "chain": state.chain,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return TState(
            board={_cell(k): v for k, v in d["board"].items()},
            pawn=None if d["pawn"] is None else _cell(d["pawn"]),
            collected=[dict(d["collected"][0]), dict(d["collected"][1])],
            to_move=d["to_move"],
            chain=d.get("chain"),
            winner=d.get("winner"),
        )

    # ---- presentation --------------------------------------------------------
    def describe_move(self, state, move):
        if move == "end":
            return "end turn"
        cell = _cell(move)
        name = COLOR_NAMES.get(state.board.get(cell, ""), "?")
        if state.pawn is None:
            return f"start {move} ({name})"
        if state.chain is None and not self._slide_targets(state):
            return f"jump {move} ({name})"
        return f"{move} ({name})"

    def render(self, state, perspective=None):
        # Irregular 49-cell hex board -> `polygons` (the generic hex renderer
        # only draws full hexhex shapes), laid out like the web hex grid.
        cells = [{"id": _cid(c), "points": _hex_poly(*c)} for c in CELLS]
        pieces = [{"cell": _cid(c), "fill": FILL[col], "stroke": STROKE[col],
                   "label": col}
                  for c, col in sorted(state.board.items())]
        highlights = []
        if state.pawn is not None:
            pieces.append({"cell": _cid(state.pawn), "fill": "#1c1c1c",
                           "stroke": "#f5f5f5", "label": "✦"})
            highlights.append({"cell": _cid(state.pawn), "kind": "last-move"})

        reserve = {str(p): {c: state.collected[p][c] for c in COLORS
                            if state.collected[p][c]} for p in (0, 1)}

        names = {0: "Player 1", 1: "Player 2"}

        def _hand(p):
            h = " ".join(f"{state.collected[p][c]}{c}" for c in COLORS
                         if state.collected[p][c])
            return h or "—"
        tally = f"  ·  {names[0]}: {_hand(0)} / {names[1]}: {_hand(1)}"

        if state.winner is not None:
            cap = f"{names[state.winner]} wins" + tally
        elif state.pawn is None:
            cap = f"{names[state.to_move]}: place the pawn anywhere" + tally
        elif state.chain is not None:
            cap = (f"{names[state.to_move]}: may collect more "
                   f"{COLOR_NAMES[state.chain]} or end" + tally)
        elif not self._slide_targets(state):
            cap = f"{names[state.to_move]}: pawn is stuck — jump anywhere" + tally
        else:
            cap = f"{names[state.to_move]} to move the pawn" + tally

        return {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "highlights": highlights,
            "reserve": reserve,
            "caption": cap,
        }
