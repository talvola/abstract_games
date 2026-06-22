"""Quoridor (Mirko Marchesi, 1997) -- race your pawn to the far side while dropping
walls to lengthen your opponent's path. The platform's first game with **wall /
edge state**.

A 9x9 board; each player's pawn starts at the middle of their home row and must
reach the opposite row. On your turn you either step your pawn one square
orthogonally (jumping the opponent's pawn when it is in the way) or place one of
your ten **walls** in a groove between cells. A wall is two cells long and blocks
movement across it; walls may not overlap, cross, or leave *either* pawn with no
path to its goal.

Moves: a pawn move is the path string ``"fc,fr>tc,tr"``; a wall is ``"Hc,r"``
(horizontal) or ``"Vc,r"`` (vertical), where ``(c,r)`` is the post at the shared
corner of cells (c,r),(c+1,r),(c,r+1),(c+1,r+1), with ``c,r in 0..7``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from agp.game import Game

N = 9
DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]
GOAL_ROW = {0: N - 1, 1: 0}            # player 0 starts row 0 -> goal row 8, etc.
PLY_CAP = 400                          # safety net: real games are ~50 moves


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


@dataclass
class QState:
    pawns: list = field(default_factory=lambda: [(N // 2, 0), (N // 2, N - 1)])
    walls_h: frozenset = field(default_factory=frozenset)   # posts with H walls
    walls_v: frozenset = field(default_factory=frozenset)   # posts with V walls
    counts: list = field(default_factory=lambda: [10, 10])
    to_move: int = 0
    ply: int = 0
    winner: object = None


class Quoridor(Game):
    uid = "quoridor"
    name = "Quoridor"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return QState()

    def current_player(self, s):
        return s.to_move

    # ---- wall blocking -----------------------------------------------------
    def _blocked(self, wh, wv, frm, to):
        """Is a step between adjacent cells frm,to blocked by a wall?"""
        (c, r), (tc, tr) = frm, to
        if c == tc:                                  # vertical step
            lo = min(r, tr)
            return (c, lo) in wh or (c - 1, lo) in wh
        lo = min(c, tc)                              # horizontal step
        return (lo, r) in wv or (lo, r - 1) in wv

    # ---- pawn moves --------------------------------------------------------
    def _pawn_moves(self, s):
        me = s.pawns[s.to_move]
        opp = s.pawns[1 - s.to_move]
        out = []
        for dc, dr in DIRS:
            adj = (me[0] + dc, me[1] + dr)
            if not _on(*adj) or self._blocked(s.walls_h, s.walls_v, me, adj):
                continue
            if adj != opp:
                out.append(adj)
                continue
            # opponent in the way: jump straight, else diagonal
            beyond = (adj[0] + dc, adj[1] + dr)
            if _on(*beyond) and not self._blocked(s.walls_h, s.walls_v, adj, beyond):
                out.append(beyond)
            else:
                for pc, pr in ((dr, dc), (-dr, -dc)):   # perpendiculars
                    side = (adj[0] + pc, adj[1] + pr)
                    if _on(*side) and not self._blocked(s.walls_h, s.walls_v, adj, side):
                        out.append(side)
        return out

    # ---- wall placement ----------------------------------------------------
    def _wall_ok(self, s, kind, c, r):
        if not (0 <= c < N - 1 and 0 <= r < N - 1):
            return False
        wh, wv = s.walls_h, s.walls_v
        if (c, r) in wh or (c, r) in wv:             # post already used (no crossing)
            return False
        if kind == "H":
            if (c - 1, r) in wh or (c + 1, r) in wh:  # overlap another H wall
                return False
            nh, nv = wh | {(c, r)}, wv
        else:
            if (c, r - 1) in wv or (c, r + 1) in wv:
                return False
            nh, nv = wh, wv | {(c, r)}
        # both pawns must still have a path to their goal
        return all(self._has_path(nh, nv, s.pawns[p], GOAL_ROW[p]) for p in (0, 1))

    def _has_path(self, wh, wv, start, goal_row):
        seen = {start}
        q = deque([start])
        while q:
            c, r = q.popleft()
            if r == goal_row:
                return True
            for dc, dr in DIRS:
                nb = (c + dc, r + dr)
                if _on(*nb) and nb not in seen and not self._blocked(wh, wv, (c, r), nb):
                    seen.add(nb)
                    q.append(nb)
        return False

    def _wall_moves(self, s):
        if s.counts[s.to_move] == 0:
            return []
        out = []
        for r in range(N - 1):
            for c in range(N - 1):
                if self._wall_ok(s, "H", c, r):
                    out.append(f"H{c},{r}")
                if self._wall_ok(s, "V", c, r):
                    out.append(f"V{c},{r}")
        return out

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        me = s.pawns[s.to_move]
        out = [f"{me[0]},{me[1]}>{t[0]},{t[1]}" for t in self._pawn_moves(s)]
        out += self._wall_moves(s)
        return out

    def apply_move(self, s, move, rng=None):
        pl = s.to_move
        if move[0] in "HV":
            c, r = _cell(move[1:])
            wh = s.walls_h | ({(c, r)} if move[0] == "H" else set())
            wv = s.walls_v | ({(c, r)} if move[0] == "V" else set())
            counts = list(s.counts)
            counts[pl] -= 1
            return QState(pawns=list(s.pawns), walls_h=frozenset(wh), walls_v=frozenset(wv),
                          counts=counts, to_move=1 - pl, ply=s.ply + 1)
        to = _cell(move.split(">")[1])
        pawns = list(s.pawns)
        pawns[pl] = to
        winner = pl if to[1] == GOAL_ROW[pl] else None
        return QState(pawns=pawns, walls_h=s.walls_h, walls_v=s.walls_v,
                      counts=list(s.counts), to_move=1 - pl, ply=s.ply + 1, winner=winner)

    def is_terminal(self, s):
        return s.winner is not None or s.ply >= PLY_CAP

    def returns(self, s):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # ---- (de)serialise -----------------------------------------------------
    def serialize(self, s):
        return {"pawns": [list(p) for p in s.pawns],
                "walls_h": sorted([list(w) for w in s.walls_h]),
                "walls_v": sorted([list(w) for w in s.walls_v]),
                "counts": list(s.counts), "to_move": s.to_move,
                "ply": s.ply, "winner": s.winner}

    def deserialize(self, d):
        return QState(pawns=[tuple(p) for p in d["pawns"]],
                      walls_h=frozenset(tuple(w) for w in d["walls_h"]),
                      walls_v=frozenset(tuple(w) for w in d["walls_v"]),
                      counts=list(d["counts"]), to_move=d["to_move"],
                      ply=d.get("ply", 0), winner=d.get("winner"))

    def describe_move(self, s, move):
        if move[0] in "HV":
            return f"wall {move[0]}@{move[1:]}"
        return move.replace(">", "-")

    def render(self, s, perspective=None):
        names = {0: "Player 1", 1: "Player 2"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": "♟"}
                  for p, (c, r) in enumerate(s.pawns)]
        # goal-edge tint: each player's target row, in their colour, faintly
        tints = {}
        for p in (0, 1):
            for c in range(N):
                tints.setdefault(f"{c},{GOAL_ROW[p]}", ["#3a2222", "#22223a"][p])
        if s.winner is not None:
            cap = f"{names[s.winner]} wins (reached the far side)"
        else:
            cap = (f"{names[s.to_move]} to move  ·  walls left: "
                   f"P1 {s.counts[0]} / P2 {s.counts[1]}")
        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints,
                      "walls": {"h": [list(w) for w in s.walls_h],
                                "v": [list(w) for w in s.walls_v]}},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
