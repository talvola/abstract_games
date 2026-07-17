"""Awithlaknannai Mosona -- a Zuni "fighting serpents" game in the Alquerque
family.

The board is the elongated serpent lattice: three parallel rows of points joined
into a long strip of triangles/lozenges. The middle row has 9 points; the two
outer (top/bottom) rows have 8 points each (25 points total). Each outer point
sits between two middle points and is joined to both by a diagonal line; the
middle-row points are joined to each other horizontally. A piece moves and
captures only along these drawn lines.

Each side has 12 men; the single centre point of the middle row starts empty. A
man steps one point along a line to an empty point, or jumps an adjacent enemy
along a line to the empty point immediately beyond, removing it (draughts-style
short jump). Captures are compulsory and chain (a multi-jump may change direction
at each enemy). Capture all of the enemy -- or leave them with no move -- to win.

The ``size`` option selects the board: 25 points (the game above) or 49 points --
Kolowis Awithlaknannai, Culin's long "fighting serpents" board (17-point middle
row, 16-point outer rows, 23 men each; the centre AND the two end points of the
middle row start empty).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK = 0, 1
PLY_CAP = {25: 400, 49: 800}   # hard draw backstop, scaled to piece count
NO_CAPTURE_DRAW = 50

# ---------------------------------------------------------------------------
# Board geometry: the serpent lattice, parameterized by middle-row length.
#
# Layout on a render grid (x right, y down). Middle row y=1, top row y=0,
# bottom row y=2. Middle points sit on even x = 0,2,...,2(n-1); each outer
# point sits on odd x BETWEEN two middle points, joined diagonally to both.
# Middle points are joined horizontally to the next middle point. This
# triangulates the strip into lozenges.
#
# size 25 = Awithlaknannai Mosona (9 middle + 8 + 8), size 49 = Kolowis
# Awithlaknannai (17 middle + 16 + 16), both per Culin 1907.
# ---------------------------------------------------------------------------
MID_Y = 1
TOP_Y = 0
BOT_Y = 2
SIZES = {25: 9, 49: 17}     # total points -> middle-row points


class _Geom:
    def __init__(self, n_mid):
        self.mid = [(2 * i, MID_Y) for i in range(n_mid)]
        self.top = [(2 * i + 1, TOP_Y) for i in range(n_mid - 1)]
        self.bot = [(2 * i + 1, BOT_Y) for i in range(n_mid - 1)]
        self.points = self.mid + self.top + self.bot
        self.centre = (n_mid - 1, MID_Y)

        adj = {p: set() for p in self.points}

        def link(a, b):
            adj[a].add(b)
            adj[b].add(a)

        # middle row: horizontal line through all points
        for i in range(n_mid - 1):
            link(self.mid[i], self.mid[i + 1])
        # each outer point joins the two middle points flanking it
        for outer in (self.top, self.bot):
            for (x, y) in outer:
                link((x, y), (x - 1, MID_Y))
                link((x, y), (x + 1, MID_Y))
        self.adj = {p: frozenset(s) for p, s in adj.items()}

        # For each point, the (over, land) capture pairs along a straight drawn
        # line: over is adjacent, land is the next collinear point in the SAME
        # direction that is itself adjacent to `over`.
        self.cap_pairs = {}
        for p in self.points:
            px, py = p
            pairs = []
            for over in self.adj[p]:
                ox, oy = over
                dx, dy = ox - px, oy - py
                land = (ox + dx, oy + dy)
                if land in self.adj[over] and land != p:
                    pairs.append((over, land))
            self.cap_pairs[p] = pairs

        # Cosmetic board.lines: every drawn edge once.
        seen = set()
        self.lines = []
        for a in self.points:
            for b in self.adj[a]:
                key = tuple(sorted((a, b)))
                if key not in seen:
                    seen.add(key)
                    self.lines.append([[a[0], a[1]], [b[0], b[1]]])

        # Tiny diamond polygon per point for the 'polygons' renderer.
        r = 0.32
        self.polys = [{"id": f"{x},{y}",
                       "points": [[x, y - r], [x + r, y], [x, y + r], [x - r, y]]}
                      for (x, y) in self.points]


_GEOMS = {}


def geom(size):
    if size not in _GEOMS:
        _GEOMS[size] = _Geom(SIZES[size])
    return _GEOMS[size]


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class AState:
    board: dict = field(default_factory=dict)        # (x,y) -> WHITE/BLACK
    to_move: int = WHITE
    since: int = 0
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None
    size: int = 25                                   # 25 | 49 (kolowis)


class Awithlaknannai(Game):
    uid = "awithlaknannai"
    name = "Awithlaknannai Mosona"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        size = int(opts.get("size", 25))
        if size not in SIZES:
            size = 25
        g = geom(size)
        cx = g.centre[0]
        last = g.mid[-1][0]
        board = {}
        # WHITE: full bottom row + left half of the middle row.
        # BLACK: full top row + right half of the middle row.
        # Kolowis (49): the two END points of the middle row also start empty
        # (Culin 1907 setup — 23 men each), unlike the 25-point game where only
        # the centre is empty (12 men each).
        for p in g.bot:
            board[p] = WHITE
        for p in g.top:
            board[p] = BLACK
        for (x, y) in g.mid:
            if size == 49 and (x == 0 or x == last):
                continue
            if x < cx:
                board[(x, y)] = WHITE
            elif x > cx:
                board[(x, y)] = BLACK
        # centre point stays empty
        st = AState(board=board, to_move=WHITE, size=size)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _capture_paths(self, g, board, sq, player):
        found = False
        for over, land in g.cap_pairs[sq]:
            if land in board or board.get(over) != 1 - player:
                continue
            nb = dict(board)
            del nb[over]
            del nb[sq]
            nb[land] = player
            found = True
            tails = list(self._capture_paths(g, nb, land, player))
            if tails:
                for t in tails:
                    yield [sq] + t
            else:
                yield [sq, land]
        if not found:
            return

    def _all_captures(self, g, board, player):
        out = []
        for sq, who in board.items():
            if who == player:
                out.extend(self._capture_paths(g, board, sq, player))
        return out

    def _steps(self, g, board, player):
        out = []
        for sq, who in board.items():
            if who != player:
                continue
            for to in g.adj[sq]:
                if to not in board:
                    out.append([sq, to])
        return out

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        g = geom(state.size)
        caps = self._all_captures(g, state.board, state.to_move)
        paths = caps if caps else self._steps(g, state.board, state.to_move)
        return [">".join(f"{x},{y}" for (x, y) in p) for p in paths]

    def apply_move(self, state, move, rng=None):
        g = geom(state.size)
        pts = [_cell(s) for s in move.split(">")]
        board = dict(state.board)
        player = state.to_move
        who = board.pop(pts[0])
        captured = False
        for i in range(1, len(pts)):
            frm, to = pts[i - 1], pts[i]
            # a jump is a cap_pairs hop (over, land); a step is a plain adj hop.
            for over, land in g.cap_pairs[frm]:
                if land == to and board.get(over) == 1 - player:
                    board.pop(over, None)
                    captured = True
                    break
        board[pts[-1]] = who
        since = 0 if captured else state.since + 1
        ns = AState(board=board, to_move=1 - player, since=since,
                    ply=state.ply + 1, reps=dict(state.reps), size=state.size)
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        if not any(v == ns.to_move for v in board.values()):
            ns.winner = player
        elif not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = player
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.ply >= PLY_CAP[state.size] or state.since >= NO_CAPTURE_DRAW
                     or state.reps.get(self._key(state), 0) >= 3))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- keys / serialise --------------------------------------------------
    def _key(self, state):
        b = ",".join(f"{x},{y}:{state.board[(x, y)]}"
                     for (x, y) in geom(state.size).points if (x, y) in state.board)
        return f"{b}#{state.to_move}"

    def serialize(self, state):
        d = {"board": {f"{x},{y}": v for (x, y), v in state.board.items()},
             "to_move": state.to_move, "since": state.since, "ply": state.ply,
             "reps": dict(state.reps), "winner": state.winner}
        if state.size != 25:      # omit default so old payloads round-trip unchanged
            d["size"] = state.size
        return d

    def deserialize(self, d):
        return AState(board={_cell(k): v for k, v in d["board"].items()},
                      to_move=d["to_move"], since=d.get("since", 0), ply=d.get("ply", 0),
                      reps=dict(d.get("reps", {})), winner=d.get("winner"),
                      size=int(d.get("size", 25)))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        g = geom(state.size)
        pts = move.split(">")
        # A segment is a STEP if its destination is a drawn-line neighbour (in
        # adj); otherwise it is a capturing jump (a cap_pairs hop). NB: middle-row
        # neighbours differ by dx==2, so distance alone would mislabel a step.
        jump = any(_cell(pts[i]) not in g.adj[_cell(pts[i - 1])]
                   for i in range(1, len(pts)))
        return ("x" if jump else "-").join(pts)

    def render(self, state, perspective=None):
        g = geom(state.size)
        names = {WHITE: "White", BLACK: "Black"}
        pieces = [{"cell": f"{x},{y}", "owner": who}
                  for (x, y), who in state.board.items()]
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        else:
            must = self._all_captures(g, state.board, state.to_move)
            cap = f"{names[state.to_move]} to move" + (" (must capture)" if must else "")
        return {
            "board": {"type": "polygons", "cells": g.polys, "lines": g.lines},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
