"""Pretwa -- a traditional Indian/Bihari capture game played on a board of three
concentric circles crossed by three diameters (six radial spokes meeting at a
centre point). It belongs to the alquerque/draughts family: pieces step along a
line (a ring arc or a spoke) to an adjacent empty point, and capture by jumping a
single adjacent enemy along a line to the empty point beyond. Captures are
compulsory and chain (a multi-jump may freely switch between ring arcs and
diameters). Reduce the opponent TO THREE (or fewer) men to win; if no move can be
made, the side with MORE men wins (equal men = a draw).

BOARD GEOMETRY (documented in rules.md, FLAGGED there for review):
  - 3 concentric circles (rings) + 1 centre point.
  - 3 diameters => 6 equally-spaced radial spokes (s = 0..5) from the centre.
  - 6 spokes x 3 rings = 18 ring points, + centre = 19 points total.
Coordinate / cell id = "ring,spoke":
  - centre = "0,0" (ring 0 uses only spoke 0).
  - ring 1 = inner, ring 2 = middle, ring 3 = outer; spoke s in 0..5.

ADJACENCY (steps) live in code:
  - radial:  centre <-> (1,s);  (1,s) <-> (2,s);  (2,s) <-> (3,s)
  - ring arc: (r,s) <-> (r,(s+-1) mod 6)  for r in 1,2,3

COLLINEAR JUMP TRIPLES a-mid-b (jump over mid, land on b):
  - radial:    (0,0)-(1,s)-(2,s)  and  (1,s)-(2,s)-(3,s)
  - diameter:  (1,s)-(0,0)-(1,(s+3) mod 6)  (the straight line through the centre)
  - ring arc:  (r,s)-(r,(s+1) mod 6)-(r,(s+2) mod 6)  for r in 1,2,3
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK = 0, 1
NRINGS = 3            # concentric circles (not counting the centre)
NSPOKES = 6           # 3 diameters => 6 radial spokes
PLY_CAP = 400
NO_CAPTURE_DRAW = 60
LOSE_AT = 3           # reduced TO this many (<=3) men => that player has lost

CENTRE = (0, 0)


def _points():
    pts = [CENTRE]
    for r in range(1, NRINGS + 1):
        for s in range(NSPOKES):
            pts.append((r, s))
    return pts


POINTS = _points()
POINT_SET = set(POINTS)


def _build_adjacency():
    """step adjacency: set of frozensets {a,b} of directly-connected points."""
    adj = {p: set() for p in POINTS}

    def link(a, b):
        adj[a].add(b)
        adj[b].add(a)

    # radial: centre <-> inner, then ring r <-> ring r+1 on the same spoke
    for s in range(NSPOKES):
        link(CENTRE, (1, s))
        for r in range(1, NRINGS):
            link((r, s), (r + 1, s))
    # ring arcs
    for r in range(1, NRINGS + 1):
        for s in range(NSPOKES):
            link((r, s), (r, (s + 1) % NSPOKES))
    return adj


ADJ = _build_adjacency()


def _build_jumps():
    """jump triples: dict a -> list of (mid, land) collinear with a."""
    jumps = {p: [] for p in POINTS}

    def add(a, mid, land):
        jumps[a].append((mid, land))
        jumps[land].append((mid, a))

    # radial triples on each spoke: centre-inner-middle, inner-middle-outer
    for s in range(NSPOKES):
        add(CENTRE, (1, s), (2, s))
        for r in range(1, NRINGS - 1):
            add((r, s), (r + 1, s), (r + 2, s))
    # diameter through the centre: inner spoke s -- centre -- inner spoke s+3
    for s in range(NSPOKES // 2):           # 0,1,2 pair with 3,4,5
        add((1, s), CENTRE, (1, s + NSPOKES // 2))
    # ring-arc triples on each ring
    for r in range(1, NRINGS + 1):
        for s in range(NSPOKES):
            add((r, s), (r, (s + 1) % NSPOKES), (r, (s + 2) % NSPOKES))
    return jumps


JUMPS = _build_jumps()


def _cell(s):
    a, b = s.split(",")
    return int(a), int(b)


def _str(p):
    return f"{p[0]},{p[1]}"


@dataclass
class PState:
    board: dict = field(default_factory=dict)        # (ring,spoke) -> WHITE/BLACK
    to_move: int = WHITE
    since: int = 0                                    # plies since last capture
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None                             # player index, or None
    over: bool = False                                # terminal reached (may be a draw)


class Pretwa(Game):
    uid = "pretwa"
    name = "Pretwa"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        # WHITE on spokes {0,1,2}, BLACK on spokes {3,4,5}; centre empty.
        board = {}
        for r in range(1, NRINGS + 1):
            for s in range(NSPOKES):
                board[(r, s)] = WHITE if s < NSPOKES // 2 else BLACK
        st = PState(board=board, to_move=WHITE)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _capture_paths(self, board, sq, player):
        found = False
        for (mid, land) in JUMPS[sq]:
            if land in board or board.get(mid) != (1 - player):
                continue
            nb = dict(board)
            del nb[mid]
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
        if self.is_terminal(state):
            return []
        return self._raw_moves(state)

    def _raw_moves(self, state):
        """Legal moves ignoring terminal status (used to detect no-move ends)."""
        caps = self._all_captures(state.board, state.to_move)
        paths = caps if caps else self._steps(state.board, state.to_move)
        return [">".join(_str(p) for p in path) for path in paths]

    @staticmethod
    def _count(board, player):
        return sum(1 for v in board.values() if v == player)

    def apply_move(self, state, move, rng=None):
        pts = [_cell(s) for s in move.split(">")]
        board = dict(state.board)
        player = state.to_move
        who = board.pop(pts[0])
        captured = False
        for i in range(1, len(pts)):
            frm, to = pts[i - 1], pts[i]
            # a jump: frm and to are not directly adjacent -> find the jumped mid
            if to not in ADJ[frm]:
                for (mid, land) in JUMPS[frm]:
                    if land == to:
                        board.pop(mid, None)
                        captured = True
                        break
        board[pts[-1]] = who
        since = 0 if captured else state.since + 1
        ns = PState(board=board, to_move=1 - player, since=since,
                    ply=state.ply + 1, reps=dict(state.reps))
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        # Resolve the result of the new position:
        #  (1) opponent reduced TO three or fewer men (incl. annihilation) -> mover wins;
        #  (2) no-progress / ply-cap / 3-fold repetition -> decide by piece-count majority;
        #  (3) the side to move has no legal move -> decide by piece-count majority.
        # In (2)/(3) more men wins, equal men is a draw.
        opp = ns.to_move
        if self._count(board, opp) <= LOSE_AT:
            ns.winner = player
            ns.over = True
        elif self._no_progress(ns) or not self._raw_moves(ns):
            ns.over = True
            ns.winner = self._majority_winner(board)
        return ns

    # ---- terminal ----------------------------------------------------------
    def _no_progress(self, state):
        """Anti-loop termination (engine addition): ply cap / no-capture / 3-fold."""
        return (state.ply >= PLY_CAP or state.since >= NO_CAPTURE_DRAW
                or state.reps.get(self._key(state), 0) >= 3)

    @classmethod
    def _majority_winner(cls, board):
        """Side with more men wins; equal men => None (a draw)."""
        w, b = cls._count(board, WHITE), cls._count(board, BLACK)
        if w > b:
            return WHITE
        if b > w:
            return BLACK
        return None

    def is_terminal(self, state):
        return state.over

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- keys / serialise --------------------------------------------------
    def _key(self, state):
        b = ",".join(f"{p[0]},{p[1]}:{state.board[p]}"
                     for p in POINTS if p in state.board)
        return f"{b}#{state.to_move}"

    def serialize(self, state):
        return {"board": {_str(p): v for p, v in state.board.items()},
                "to_move": state.to_move, "since": state.since, "ply": state.ply,
                "reps": dict(state.reps), "winner": state.winner, "over": state.over}

    def deserialize(self, d):
        return PState(board={_cell(k): v for k, v in d["board"].items()},
                      to_move=d["to_move"], since=d.get("since", 0), ply=d.get("ply", 0),
                      reps=dict(d.get("reps", {})), winner=d.get("winner"),
                      over=d.get("over", False))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        pts = [_cell(s) for s in move.split(">")]
        jump = any(pts[i] not in ADJ[pts[i - 1]] for i in range(1, len(pts)))
        sep = "x" if jump else "-"
        return sep.join(_str(p) for p in pts)

    # geometry for the polygons renderer ------------------------------------
    @staticmethod
    def _xy(p):
        r, s = p
        if r == 0:
            return (0.0, 0.0)
        ang = math.pi / 2 - 2 * math.pi * s / NSPOKES   # spoke 0 points up
        rad = float(r)
        return (rad * math.cos(ang), -rad * math.sin(ang))

    def _polygons(self):
        # a small square cell footprint centred on each point. The generic
        # polygons renderer (Board.jsx) expects a LIST of {id, points}.
        cells = []
        h = 0.28
        for p in POINTS:
            x, y = self._xy(p)
            cells.append({"id": _str(p),
                          "points": [[x - h, y - h], [x + h, y - h],
                                     [x + h, y + h], [x - h, y + h]]})
        return cells

    def _lines(self):
        segs = []
        # rings as 6-pt polylines (closed) -- cosmetic arcs approximated by chords
        for r in range(1, NRINGS + 1):
            ring = [self._xy((r, s)) for s in range(NSPOKES)]
            poly = [[x, y] for (x, y) in ring] + [list(ring[0])]
            segs.append([[round(x, 4), round(y, 4)] for (x, y) in poly])
        # spokes (centre out to the outer ring)
        for s in range(NSPOKES):
            seg = [self._xy(CENTRE), self._xy((1, s)),
                   self._xy((2, s)), self._xy((3, s))]
            segs.append([[round(x, 4), round(y, 4)] for (x, y) in seg])
        return segs

    def render(self, state, perspective=None):
        names = {WHITE: "White", BLACK: "Black"}
        pieces = [{"cell": _str(p), "owner": who} for p, who in state.board.items()]
        if state.over and state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif state.over:
            cap = "Draw"
        else:
            must = self._all_captures(state.board, state.to_move)
            cap = f"{names[state.to_move]} to move" + (" (must capture)" if must else "")
        return {
            "board": {"type": "polygons", "cells": self._polygons(),
                      "lines": self._lines()},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
