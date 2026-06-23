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
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK = 0, 1
PLY_CAP = 400
NO_CAPTURE_DRAW = 50

# ---------------------------------------------------------------------------
# Board geometry: the serpent lattice.
#
# Layout on a render grid (x right, y down). Middle row y=1, top row y=0,
# bottom row y=2. Middle points sit on even x = 0,2,...,16 (nine points); each
# outer point sits on odd x = 1,3,...,15 (eight points) BETWEEN two middle
# points, joined diagonally to both. Middle points are joined horizontally to
# the next middle point. This triangulates the strip into 8 lozenges.
# ---------------------------------------------------------------------------
MID_Y = 1
TOP_Y = 0
BOT_Y = 2
N_MID = 9          # middle row points
N_OUTER = 8        # each outer row

MID = [(2 * i, MID_Y) for i in range(N_MID)]          # x = 0,2,...,16
TOP = [(2 * i + 1, TOP_Y) for i in range(N_OUTER)]    # x = 1,3,...,15
BOT = [(2 * i + 1, BOT_Y) for i in range(N_OUTER)]    # x = 1,3,...,15

POINTS = MID + TOP + BOT                               # 9 + 8 + 8 = 25
CENTRE = (8, MID_Y)                                    # middle of middle row


def _build_adjacency():
    adj = {p: set() for p in POINTS}

    def link(a, b):
        adj[a].add(b)
        adj[b].add(a)

    # middle row: horizontal line through all 9 points
    for i in range(N_MID - 1):
        link(MID[i], MID[i + 1])
    # each outer point joins the two middle points flanking it
    for outer in (TOP, BOT):
        for (x, y) in outer:
            left = (x - 1, MID_Y)
            right = (x + 1, MID_Y)
            link((x, y), left)
            link((x, y), right)
    return {p: frozenset(s) for p, s in adj.items()}


ADJ = _build_adjacency()

# Precompute, for each point, the (over, land) capture pairs reachable along a
# straight drawn line: over is an adjacent point, land is the next collinear
# point in the SAME direction that is itself adjacent to `over`.
def _capture_pairs():
    out = {}
    for p in POINTS:
        px, py = p
        pairs = []
        for over in ADJ[p]:
            ox, oy = over
            dx, dy = ox - px, oy - py
            land = (ox + dx, oy + dy)
            if land in ADJ[over] and land != p:
                pairs.append((over, land))
        out[p] = pairs
    return out


CAP_PAIRS = _capture_pairs()


def _line_segments():
    """Cosmetic board.lines: every drawn edge once, as [[x,y],[x,y]]."""
    seen = set()
    segs = []
    for a in POINTS:
        for b in ADJ[a]:
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            segs.append([[a[0], a[1]], [b[0], b[1]]])
    return segs


LINES = _line_segments()


def _polys():
    """Tiny diamond polygon per point for the 'polygons' renderer."""
    cells = []
    r = 0.32
    for (x, y) in POINTS:
        verts = [[x, y - r], [x + r, y], [x, y + r], [x - r, y]]
        cells.append({"id": f"{x},{y}", "points": verts})
    return cells


POLYS = _polys()


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


class Awithlaknannai(Game):
    uid = "awithlaknannai"
    name = "Awithlaknannai Mosona"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {}
        # WHITE: full bottom row + left half of the middle row.
        for p in BOT:
            board[p] = WHITE
        for (x, y) in MID:
            if x < CENTRE[0]:
                board[(x, y)] = WHITE
        # BLACK: full top row + right half of the middle row.
        for p in TOP:
            board[p] = BLACK
        for (x, y) in MID:
            if x > CENTRE[0]:
                board[(x, y)] = BLACK
        # centre point stays empty
        st = AState(board=board, to_move=WHITE)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _capture_paths(self, board, sq, player):
        found = False
        for over, land in CAP_PAIRS[sq]:
            if land in board or board.get(over) != 1 - player:
                continue
            nb = dict(board)
            del nb[over]
            del nb[sq]
            nb[land] = player
            found = True
            tails = list(self._capture_paths(nb, land, player))
            if tails:
                for t in tails:
                    yield [sq] + t
            else:
                yield [sq, land]
        if not found:
            return

    def _all_captures(self, board, player):
        out = []
        for sq, who in board.items():
            if who == player:
                out.extend(self._capture_paths(board, sq, player))
        return out

    def _steps(self, board, player):
        out = []
        for sq, who in board.items():
            if who != player:
                continue
            for to in ADJ[sq]:
                if to not in board:
                    out.append([sq, to])
        return out

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        caps = self._all_captures(state.board, state.to_move)
        paths = caps if caps else self._steps(state.board, state.to_move)
        return [">".join(f"{x},{y}" for (x, y) in p) for p in paths]

    def apply_move(self, state, move, rng=None):
        pts = [_cell(s) for s in move.split(">")]
        board = dict(state.board)
        player = state.to_move
        who = board.pop(pts[0])
        captured = False
        for i in range(1, len(pts)):
            frm, to = pts[i - 1], pts[i]
            # a jump is a CAP_PAIRS hop (over, land); a step is a plain ADJ hop.
            for over, land in CAP_PAIRS[frm]:
                if land == to and board.get(over) == 1 - player:
                    board.pop(over, None)
                    captured = True
                    break
        board[pts[-1]] = who
        since = 0 if captured else state.since + 1
        ns = AState(board=board, to_move=1 - player, since=since,
                    ply=state.ply + 1, reps=dict(state.reps))
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
                and (state.ply >= PLY_CAP or state.since >= NO_CAPTURE_DRAW
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
                     for (x, y) in POINTS if (x, y) in state.board)
        return f"{b}#{state.to_move}"

    def serialize(self, state):
        return {"board": {f"{x},{y}": v for (x, y), v in state.board.items()},
                "to_move": state.to_move, "since": state.since, "ply": state.ply,
                "reps": dict(state.reps), "winner": state.winner}

    def deserialize(self, d):
        return AState(board={_cell(k): v for k, v in d["board"].items()},
                      to_move=d["to_move"], since=d.get("since", 0), ply=d.get("ply", 0),
                      reps=dict(d.get("reps", {})), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        pts = move.split(">")
        # A segment is a STEP if its destination is a drawn-line neighbour (in
        # ADJ); otherwise it is a capturing jump (a CAP_PAIRS hop). NB: middle-row
        # neighbours differ by dx==2, so distance alone would mislabel a step.
        jump = any(_cell(pts[i]) not in ADJ[_cell(pts[i - 1])]
                   for i in range(1, len(pts)))
        return ("x" if jump else "-").join(pts)

    def render(self, state, perspective=None):
        names = {WHITE: "White", BLACK: "Black"}
        pieces = [{"cell": f"{x},{y}", "owner": who}
                  for (x, y), who in state.board.items()]
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        else:
            must = self._all_captures(state.board, state.to_move)
            cap = f"{names[state.to_move]} to move" + (" (must capture)" if must else "")
        return {
            "board": {"type": "polygons", "cells": POLYS, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
