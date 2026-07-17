"""Dablot Prejjesne -- the Sami "dablo" battle game from Frostviken, Lapland.

An Alquerque-family game recorded by Nils Keyland (1921). The board is a 6x7
grid of points with all lines drawn: the 42 grid vertices are joined by
horizontal and vertical lines, and both diagonals are drawn through every one
of the 30 small squares, adding a point where they cross (72 points, 191 line
segments in all). Pieces stand on the points and move along the drawn lines.

Each side has 30 pieces: 28 commoners (Sami warriors vs the farmer's tenants),
one prince (Sami prince vs the farmer's son) and one king (Sami king vs the
landlord). All pieces move alike -- one point along a line -- and capture by a
draughts-style short jump, with chains that may change direction. The game's
identity is the rank rule: a piece may only capture an enemy of EQUAL OR LOWER
rank (king > prince > commoner).

Per Keyland (via Ludii) captures are OPTIONAL, and a capture chain may be
stopped at any point; the ``captures`` option switches to the compulsory rule
some modern accounts use. Win by capturing everything, or by leaving the
opponent without a move. Special endings from Keyland: two lone kings are an
immediate draw; two lone pieces of equal (non-king) rank fight a forced
"single combat", stepping toward each other until one falls.

Coordinates are doubled so every point is integral: grid vertices at even
(x, y) with x in 0..10, y in 0..12; square centres at odd (x, y).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math

from agp.game import Game

SAMI, FARMER = 0, 1
CONE, PRINCE, KING = 0, 1, 2          # rank values; capture needs mine >= theirs
RANK_CHAR = {CONE: "", PRINCE: "P", KING: "K"}
SIDE_NAME = {SAMI: "Sami", FARMER: "Farmers"}

PLY_CAP = 1000                        # hard backstop -> draw
NO_CAPTURE_DRAW = 60                  # plies without a capture -> draw
REPETITION_DRAW = 3


# ---------------------------------------------------------------------------
# Board geometry: 6x7 grid vertices + all square centres, lines drawn between
# them. Doubled coordinates: vertices (even, even), centres (odd, odd).
# ---------------------------------------------------------------------------
class _Geom:
    def __init__(self):
        self.verts = [(x, y) for x in range(0, 11, 2) for y in range(0, 13, 2)]
        self.cents = [(x, y) for x in range(1, 10, 2) for y in range(1, 12, 2)]
        self.points = self.verts + self.cents
        pset = set(self.points)

        adj = {p: set() for p in self.points}

        def link(a, b):
            adj[a].add(b)
            adj[b].add(a)

        for (x, y) in self.verts:
            if (x + 2, y) in pset:
                link((x, y), (x + 2, y))          # horizontal grid line
            if (x, y + 2) in pset:
                link((x, y), (x, y + 2))          # vertical grid line
        for (x, y) in self.cents:                 # both diagonals of the square
            for dx in (-1, 1):
                for dy in (-1, 1):
                    link((x, y), (x + dx, y + dy))
        self.adj = {p: frozenset(s) for p, s in adj.items()}

        # (over, land) capture pairs: over is adjacent, land continues the same
        # straight drawn line and is adjacent to over.
        self.cap_pairs = {}
        for p in self.points:
            px, py = p
            pairs = []
            for over in self.adj[p]:
                ox, oy = over
                land = (2 * ox - px, 2 * oy - py)
                if land in self.adj[over] and land != p:
                    pairs.append((over, land))
            self.cap_pairs[p] = pairs

        # Cosmetic board.lines: every drawn segment once.
        seen = set()
        self.lines = []
        for a in self.points:
            for b in self.adj[a]:
                key = tuple(sorted((a, b)))
                if key not in seen:
                    seen.add(key)
                    self.lines.append([[a[0], a[1]], [b[0], b[1]]])

        r = 0.32
        self.polys = [{"id": f"{x},{y}",
                       "points": [[x, y - r], [x + r, y], [x, y + r], [x - r, y]]}
                      for (x, y) in self.points]

    def dist(self, src, dst):
        """Graph (step) distance along drawn lines, ignoring occupancy."""
        if src == dst:
            return 0
        seen = {src}
        q = deque([(src, 0)])
        while q:
            p, d = q.popleft()
            for n in self.adj[p]:
                if n == dst:
                    return d + 1
                if n not in seen:
                    seen.add(n)
                    q.append((n, d + 1))
        return math.inf


GEOM = _Geom()


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _initial_board():
    board = {}
    # Sami (seat 0) at the bottom of the screen (large y), Farmers (seat 1) at
    # the top. 28 commoners fill each side's first five ranks; the prince
    # stands on the diagonal crossing at the player's far right of the next
    # rank; the king on the player's right edge of the middle rank (rank 7),
    # so the two kings face each other from opposite ends of the middle line.
    for (x, y) in GEOM.points:
        if y >= 8:
            board[(x, y)] = (SAMI, CONE)
        elif y <= 4:
            board[(x, y)] = (FARMER, CONE)
    board[(9, 7)] = (SAMI, PRINCE)
    board[(10, 6)] = (SAMI, KING)
    board[(1, 5)] = (FARMER, PRINCE)
    board[(0, 6)] = (FARMER, KING)
    return board


@dataclass
class DState:
    board: dict = field(default_factory=dict)      # (x,y) -> (owner, rank)
    to_move: int = SAMI
    since: int = 0                                 # plies since last capture
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None
    compulsory: bool = False                       # captures option


class DablotPrejjesne(Game):
    name = "Dablot Prejjesne"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        compulsory = str(opts.get("captures", "optional")) == "compulsory"
        st = DState(board=_initial_board(), to_move=SAMI, compulsory=compulsory)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _capture_paths(self, board, sq, player, rank, compulsory):
        """Yield capture paths from sq. Optional mode yields every stopping
        point (each prefix with >=1 jump); compulsory mode yields only paths
        that continue while a further jump exists."""
        for over, land in GEOM.cap_pairs[sq]:
            occ = board.get(over)
            if land in board or occ is None or occ[0] != 1 - player or occ[1] > rank:
                continue
            nb = dict(board)
            del nb[over]
            del nb[sq]
            nb[land] = (player, rank)
            tails = list(self._capture_paths(nb, land, player, rank, compulsory))
            if not compulsory or not tails:
                yield [sq, land]
            for t in tails:
                yield [sq] + t

    def _all_captures(self, board, player, compulsory):
        out = []
        for sq, (who, rank) in board.items():
            if who == player:
                out.extend(self._capture_paths(board, sq, player, rank, compulsory))
        return out

    def _steps(self, board, player):
        out = []
        for sq, (who, _rank) in board.items():
            if who != player:
                continue
            for to in GEOM.adj[sq]:
                if to not in board:
                    out.append([sq, to])
        return out

    def _single_combat(self, state):
        """Keyland's ending: both players down to one piece of equal rank
        (two kings would already be a declared draw). Returns the two piece
        squares (mine, enemy) or None."""
        pieces = list(state.board.items())
        if len(pieces) != 2:
            return None
        (sq_a, (own_a, rk_a)), (sq_b, (own_b, rk_b)) = pieces
        if own_a == own_b or rk_a != rk_b:
            return None
        mine, enemy = (sq_a, sq_b) if own_a == state.to_move else (sq_b, sq_a)
        return mine, enemy

    def _move_lists(self, state):
        board, player = state.board, state.to_move
        caps = self._all_captures(board, player, state.compulsory)
        combat = self._single_combat(state)
        if combat is not None:
            mine, enemy = combat
            if caps:
                return caps
            d0 = GEOM.dist(mine, enemy)
            approach = [[mine, to] for to in GEOM.adj[mine]
                        if to not in board and GEOM.dist(to, enemy) < d0]
            if approach:
                return approach
            # no approach possible (edge corner cases): fall back to any move
            return self._steps(board, player)
        if state.compulsory and caps:
            return caps
        return caps + self._steps(board, player)

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        paths = self._move_lists(state)
        out, seen = [], set()
        for p in paths:
            m = ">".join(f"{x},{y}" for (x, y) in p)
            if m not in seen:
                seen.add(m)
                out.append(m)
        return out

    def apply_move(self, state, move, rng=None):
        pts = [_cell(s) for s in move.split(">")]
        board = dict(state.board)
        player = state.to_move
        piece = board.pop(pts[0])
        captured = False
        for i in range(1, len(pts)):
            frm, to = pts[i - 1], pts[i]
            for over, land in GEOM.cap_pairs[frm]:
                if land == to and board.get(over, (None,))[0] == 1 - player:
                    del board[over]
                    captured = True
                    break
        board[pts[-1]] = piece
        ns = DState(board=board, to_move=1 - player,
                    since=0 if captured else state.since + 1,
                    ply=state.ply + 1, reps=dict(state.reps),
                    compulsory=state.compulsory)
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        if not any(own == ns.to_move for (own, _r) in board.values()):
            ns.winner = player                     # annihilation
        elif not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = player                     # opponent trapped
        return ns

    # ---- terminal ----------------------------------------------------------
    def _only_kings(self, state):
        vals = list(state.board.values())
        return (len(vals) == 2 and vals[0][1] == KING and vals[1][1] == KING
                and vals[0][0] != vals[1][0])

    def _draw(self, state):
        return (state.winner is None
                and (state.ply >= PLY_CAP
                     or state.since >= NO_CAPTURE_DRAW
                     or state.reps.get(self._key(state), 0) >= REPETITION_DRAW
                     or self._only_kings(state)))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    def heuristic(self, state):
        weight = {CONE: 1.0, PRINCE: 2.5, KING: 4.0}
        bal = 0.0
        for (own, rank) in state.board.values():
            bal += weight[rank] if own == SAMI else -weight[rank]
        v = math.tanh(bal / 10.0)
        return [v, -v]

    # ---- keys / serialise --------------------------------------------------
    def _key(self, state):
        cells = ";".join(f"{x},{y}:{own}{rank}"
                         for (x, y), (own, rank) in sorted(state.board.items()))
        return f"{cells}#{state.to_move}"

    def serialize(self, state):
        d = {"board": {f"{x},{y}": [own, rank]
                       for (x, y), (own, rank) in state.board.items()},
             "to_move": state.to_move, "since": state.since, "ply": state.ply,
             "reps": dict(state.reps), "winner": state.winner}
        if state.compulsory:
            d["captures"] = "compulsory"
        return d

    def deserialize(self, d):
        return DState(board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
                      to_move=d["to_move"], since=d.get("since", 0),
                      ply=d.get("ply", 0), reps=dict(d.get("reps", {})),
                      winner=d.get("winner"),
                      compulsory=d.get("captures") == "compulsory")

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        pts = move.split(">")
        jump = any(_cell(pts[i]) not in GEOM.adj[_cell(pts[i - 1])]
                   for i in range(1, len(pts)))
        return ("x" if jump else "-").join(pts)

    def render(self, state, perspective=None):
        pieces = []
        for (x, y), (own, rank) in state.board.items():
            p = {"cell": f"{x},{y}", "owner": own}
            if RANK_CHAR[rank]:
                p["label"] = RANK_CHAR[rank]
            pieces.append(p)
        if state.winner is not None:
            cap = f"{SIDE_NAME[state.winner]} win" + ("s" if state.winner == SAMI else "")
        elif self._draw(state):
            cap = "Draw"
        else:
            caps = self._all_captures(state.board, state.to_move, False)
            word = "must" if state.compulsory else "may"
            cap = f"{SIDE_NAME[state.to_move]} to move" + (f" ({word} capture)" if caps else "")
            if self._single_combat(state) is not None:
                cap += " — single combat"
        return {
            "board": {"type": "polygons", "cells": GEOM.polys, "lines": GEOM.lines},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
