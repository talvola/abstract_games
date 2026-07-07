"""*Star (a.k.a. Star-Star), by Ea Ea (formerly Craige Schensted), c. 2004.

Ea Ea's later connection / scoring masterwork -- DISTINCT from both our ``star``
(Schensted's earlier 1983 game, an alternating-side hexagon scored by border-cell
touches) and ``starweb`` / ``superstar`` (Christian Freeling's games on a
six-fold hex board).  *Star is played on the five-sided *STAR tournament board
and scored by EDGE-CELL OWNERSHIP with a "fewest stars" award.  Its signature is
a built-in correctness invariant: the two players' combined score is always the
number of edge cells plus one -> always odd -> the game is DRAWLESS.

BOARD (reconstructed from the official Kadon *STAR rulebook, pp.14-15 board
diagram + notation on p.20, cross-checked against Wikipedia "*Star").  The board
has FIVE sectors, addressed ``*``, ``S``, ``T``, ``A``, ``R`` in the rulebook
(here sector index 0..4).  Each sector is a triangular array of RINGS 1..10
counting out from the centre, with ring ``r`` holding exactly ``r`` cells
(offsets 0..r-1, offset 0 on the sector's left boundary).  So a sector has
1+2+...+10 = 55 cells and the whole board has 5*55 = 275 cells.  The outermost
ring (ring 10) contributes 10 cells per sector = 50 EDGE cells (the rulebook's
"pericells"); the offset-0 cell of ring 10 in each sector is a CORNER (5 corners,
the star's points, the rulebook's "quark" cells).

Adjacency is the natural mudcrack-hex triangulation: within a sector cell
(r,k) neighbours (r,k+-1), (r-1,k-1), (r-1,k), (r+1,k), (r+1,k+1) [a Y-triangle];
across the ray between a sector and its counter-clockwise neighbour the left-edge
column (offset 0) meets the neighbour's right-edge column (offset r-1); and the
central STAR-shaped BRIDGE links the five ring-1 cells to EACH OTHER (a clique)
-- the bridge is never played on but CONDUCTS a connection for BOTH players.
Corner (tip) cells then have exactly 3 neighbours.  This graph reproduces the
combined-score invariant (see selftest.py).

PLAY.  White (player 0) moves first.  On a turn a player places one stone (in
Double *Star, TWO stones -- but only ONE on White's very first move) on any
empty cell; the bridge is never a cell so it is automatically unplayable.
Stones never move.  Passing is legal; two successive passes end the game
(safety nets: full board / ply cap).

SCORING (rulebook pp.4-5, verbatim structure).
  * A STAR is a connected group of one colour containing TWO OR MORE edge cells.
  * A star OWNS every edge cell it contains, PLUS every edge cell it SURROUNDS
    that is not owned by another star.  Surrounding is resolved by the reduction
    the rulebook/Wikipedia describe: groups owning fewer than two edge cells are
    removed, and each empty region then bordered by exactly one colour's stars is
    owned by that colour (a region touching both colours is neutral).
  * Each edge cell owned = 1 point.
  * The player owning THREE OR MORE of the five corner cells gets +1 point.
  * AWARD: count each colour's separate stars; the player with FEWER stars has
    their score raised by twice the difference, the other lowered by the same.

Because every edge cell resolves to exactly one owner, the corner bonus adds
exactly 1 (5 is odd), and the award is zero-sum, the combined score is always
(#edge cells)+1 = 51 on the full board -- odd, hence no ties.

Sources:
  Kadon *STAR rulebook  https://gamepuzzles.com/starbook-final.pdf
  Double *Star (Ea Ea)  http://ea.ea.home.mindspring.com/*DoubleStar.html (archived)
  https://en.wikipedia.org/wiki/*Star
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1  # White (0) moves first
NSEC = 5
RINGS = 10          # rings 1..10; ring 10 is the outer EDGE ring
PLY_CAP = 700       # hard safety backstop (board holds <= 275 stones)


# ---------------------------------------------------------------------------
# board geometry
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _cells() -> tuple:
    """All 275 cells as (sector, ring, offset); ring r has r cells."""
    out = []
    for s in range(NSEC):
        for r in range(1, RINGS + 1):
            for k in range(r):
                out.append((s, r, k))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set() -> frozenset:
    return frozenset(_cells())


def _valid(s: int, r: int, k: int) -> bool:
    return 1 <= r <= RINGS and 0 <= k < r


@lru_cache(maxsize=None)
def _adj() -> dict:
    """Neighbour map. Intra-sector Y-triangle + inter-sector ray links +
    the central bridge clique among the five ring-1 cells."""
    on = _cell_set()
    adj = {c: set() for c in on}

    def link(a, b):
        if a in on and b in on:
            adj[a].add(b)
            adj[b].add(a)

    for (s, r, k) in on:
        # intra-sector triangular-hex adjacency
        for (rr, kk) in ((r, k - 1), (r, k + 1),
                         (r - 1, k - 1), (r - 1, k),
                         (r + 1, k), (r + 1, k + 1)):
            if _valid(s, rr, kk):
                link((s, r, k), (s, rr, kk))
        # inter-sector: left edge (offset 0) of s meets right edge of s-1
        if k == 0:
            ls = (s - 1) % NSEC
            link((s, r, 0), (ls, r, r - 1))
            if r + 1 <= RINGS:
                link((s, r, 0), (ls, r + 1, r))

    # the STAR bridge links the five ring-1 cells to each other
    ring1 = [(s, 1, 0) for s in range(NSEC)]
    for i in range(NSEC):
        for j in range(i + 1, NSEC):
            link(ring1[i], ring1[j])

    return {c: frozenset(v) for c, v in adj.items()}


@lru_cache(maxsize=None)
def _edge_cells() -> frozenset:
    """The 50 edge cells (pericells): the outermost ring (ring 10)."""
    return frozenset(c for c in _cells() if c[1] == RINGS)


@lru_cache(maxsize=None)
def _corner_cells() -> frozenset:
    """The 5 corner cells (quarks / star points): ring 10, offset 0."""
    return frozenset((s, RINGS, 0) for s in range(NSEC))


def _cell(t: str) -> tuple:
    s, r, k = t.split(",")
    return int(s), int(r), int(k)


def _str(c: tuple) -> str:
    return f"{c[0]},{c[1]},{c[2]}"


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def _groups(board: dict, player: int) -> list:
    """Connected components of ``player``'s stones."""
    adj = _adj()
    out, seen = [], set()
    for cell, p in board.items():
        if p != player or cell in seen:
            continue
        comp, stack = {cell}, [cell]
        seen.add(cell)
        while stack:
            x = stack.pop()
            for nb in adj[x]:
                if nb not in seen and board.get(nb) == player:
                    seen.add(nb)
                    comp.add(nb)
                    stack.append(nb)
        out.append(comp)
    return out


def _analyze(board: dict) -> dict:
    """Full *Star analysis of a position. Returns a dict with per-player edge
    points, corner ownership, star counts, final scores and the edge-owner map."""
    adj = _adj()
    edges = _edge_cells()
    corners = _corner_cells()

    # 1. groups; a group is a STAR iff it holds >= 2 edge cells
    star_cell = {}            # cell -> owning colour (only cells in a star)
    star_count = {WHITE: 0, BLACK: 0}
    for player in (WHITE, BLACK):
        for comp in _groups(board, player):
            if len(comp & edges) >= 2:
                star_count[player] += 1
                for c in comp:
                    star_cell[c] = player

    # 2. reduction: every cell not in a star is "empty"; flood empty regions and
    #    give a region to a colour iff it is bordered by exactly that one colour.
    region_owner = {}
    seen = set()
    for c in _cells():
        if c in star_cell or c in seen:
            continue
        comp, stack, cols = {c}, [c], set()
        seen.add(c)
        while stack:
            x = stack.pop()
            for nb in adj[x]:
                if nb in star_cell:
                    cols.add(star_cell[nb])
                elif nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    stack.append(nb)
        owner = next(iter(cols)) if len(cols) == 1 else None
        for x in comp:
            region_owner[x] = owner

    # 3. edge-cell ownership
    edge_owner = {}
    for e in edges:
        edge_owner[e] = star_cell[e] if e in star_cell else region_owner.get(e)

    edge_pts = {WHITE: 0, BLACK: 0}
    for e, o in edge_owner.items():
        if o is not None:
            edge_pts[o] += 1

    corner_own = {WHITE: 0, BLACK: 0}
    for c in corners:
        o = edge_owner[c]
        if o is not None:
            corner_own[o] += 1

    # 4. final scores: edge points + corner bonus + star-count award
    score = dict(edge_pts)
    for p in (WHITE, BLACK):
        if corner_own[p] >= 3:
            score[p] += 1
    if star_count[WHITE] != star_count[BLACK]:
        diff = abs(star_count[WHITE] - star_count[BLACK])
        fewer = WHITE if star_count[WHITE] < star_count[BLACK] else BLACK
        score[fewer] += 2 * diff
        score[1 - fewer] -= 2 * diff

    return {
        "edge_pts": edge_pts,
        "corner_own": corner_own,
        "star_count": star_count,
        "score": score,
        "edge_owner": edge_owner,
    }


def _score(board: dict) -> dict:
    return _analyze(board)["score"]


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------

@dataclass
class StarStarState:
    board: dict = field(default_factory=dict)     # (s,r,k) -> 0/1
    to_move: int = WHITE
    moves_left: int = 1                            # stones left in the current turn
    per_turn: int = 1                             # 1 = *Star, 2 = Double *Star
    passes: int = 0                               # consecutive pass turns
    ply: int = 0
    last: Optional[tuple] = None
    winner: Optional[int] = None
    over: bool = False


# ---------------------------------------------------------------------------
# game
# ---------------------------------------------------------------------------

class StarStar(Game):
    uid = "star_star"
    name = "*Star"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> StarStarState:
        opts = options or {}
        per_turn = int(opts.get("stones_per_turn", 1))
        per_turn = 2 if per_turn == 2 else 1
        # White's very first move places only ONE stone even in Double *Star.
        return StarStarState(per_turn=per_turn, moves_left=1)

    def current_player(self, s: StarStarState) -> int:
        return s.to_move

    def legal_moves(self, s: StarStarState) -> list:
        if self.is_terminal(s):
            return []
        moves = [_str(c) for c in _cells() if c not in s.board]
        moves.append("pass")
        return moves

    def apply_move(self, s: StarStarState, move: str, rng=None) -> StarStarState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move

        if move == "pass":
            ns = StarStarState(
                board=dict(s.board), to_move=1 - mover,
                moves_left=s.per_turn, per_turn=s.per_turn,
                passes=s.passes + 1, ply=s.ply + 1, last=None,
            )
            self._maybe_finish(ns, force=(ns.passes >= 2 or ns.ply >= PLY_CAP))
            return ns

        cell = _cell(move)
        if cell not in _cell_set() or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        board[cell] = mover

        left = s.moves_left - 1
        if left <= 0:
            # turn complete -> hand over, refill the stone budget
            ns = StarStarState(
                board=board, to_move=1 - mover,
                moves_left=s.per_turn, per_turn=s.per_turn,
                passes=0, ply=s.ply + 1, last=cell,
            )
        else:
            # same player places again (Double *Star second stone)
            ns = StarStarState(
                board=board, to_move=mover,
                moves_left=left, per_turn=s.per_turn,
                passes=0, ply=s.ply + 1, last=cell,
            )
        self._maybe_finish(
            ns, force=(len(board) >= len(_cells()) or ns.ply >= PLY_CAP)
        )
        return ns

    def _maybe_finish(self, ns: StarStarState, force: bool = False):
        if not force:
            return
        sc = _score(ns.board)
        if sc[WHITE] > sc[BLACK]:
            ns.winner = WHITE
        elif sc[BLACK] > sc[WHITE]:
            ns.winner = BLACK
        else:
            # *Star is drawless by design; a bare double-pass tie (only possible
            # before the board resolves) defaults to the first player.
            ns.winner = WHITE
        ns.over = True

    def is_terminal(self, s: StarStarState) -> bool:
        return s.over

    def returns(self, s: StarStarState) -> list:
        if s.winner == WHITE:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: StarStarState) -> list:
        sc = _score(s.board)
        v = math.tanh((sc[WHITE] - sc[BLACK]) / 8.0)
        return [v, -v]

    def serialize(self, s: StarStarState) -> dict:
        return {
            "board": {_str(c): p for c, p in s.board.items()},
            "to_move": s.to_move,
            "moves_left": s.moves_left,
            "per_turn": s.per_turn,
            "passes": s.passes,
            "ply": s.ply,
            "last": (_str(s.last) if s.last is not None else None),
            "winner": s.winner,
            "over": s.over,
        }

    def deserialize(self, d: dict) -> StarStarState:
        last = d.get("last")
        return StarStarState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            moves_left=d.get("moves_left", 1),
            per_turn=d.get("per_turn", 1),
            passes=d.get("passes", 0),
            ply=d.get("ply", len(d["board"])),
            last=(_cell(last) if last else None),
            winner=d.get("winner"),
            over=d.get("over", False),
        )

    def describe_move(self, s: StarStarState, move: str) -> str:
        if move == "pass":
            return "pass"
        cell = _cell(move)
        if cell in _corner_cells():
            return f"{move} (corner)"
        if cell in _edge_cells():
            return f"{move} (edge)"
        return move

    # ------------------------------------------------------------------ render
    def _layout(self):
        """Cell centres for the pentagonal star layout (cached)."""
        cache = getattr(self, "_layout_cache", None)
        if cache is not None:
            return cache
        # tip unit vectors: sector s tip at angle 90 - 72*s degrees
        tips = []
        for s in range(NSEC):
            a = math.radians(90 - 72 * s)
            tips.append((math.cos(a), math.sin(a)))
        pos = {}
        for (s, r, k) in _cells():
            t = 0.5 if r == 1 else k / (r - 1)
            ts = tips[s]
            tn = tips[(s + 1) % NSEC]
            # non-normalised interpolation -> mid-side pinches in -> pointed star
            dx = (1 - t) * ts[0] + t * tn[0]
            dy = (1 - t) * ts[1] + t * tn[1]
            rad = r
            pos[(s, r, k)] = (rad * dx, -rad * dy)  # flip y for screen coords
        cache = pos
        self._layout_cache = cache
        return cache

    def render(self, s: StarStarState, perspective=None) -> dict:
        pos = self._layout()
        edges = _edge_cells()
        corners = _corner_cells()
        hw = 0.42  # half-size of a cell glyph hexagon

        def hexpts(cx, cy):
            return [[round(cx + hw * math.cos(math.radians(60 * i + 30)), 3),
                     round(cy + hw * math.sin(math.radians(60 * i + 30)), 3)]
                    for i in range(6)]

        cells = []
        tints = {}
        for c in _cells():
            cx, cy = pos[c]
            cid = _str(c)
            cells.append({"id": cid, "points": hexpts(cx, cy)})
            if c in corners:
                tints[cid] = "#caa75a"   # gold corner (quark)
            elif c in edges:
                tints[cid] = "#8a7a3a"   # dim gold edge ring (pericells)
            elif c[1] == 1:
                tints[cid] = "#6a4a8a"   # bridge ring (the five centre cells)

        pieces = [
            {"cell": _str(c), "owner": p, "label": ""}
            for c, p in s.board.items()
        ]

        highlights = []
        if s.last is not None:
            highlights.append({"cell": _str(s.last), "kind": "last-move"})

        info = _analyze(s.board)
        w, b = info["score"][WHITE], info["score"][BLACK]
        names = {WHITE: "White", BLACK: "Black"}
        if s.over:
            caption = f"{names[s.winner]} wins - White {w}, Black {b}"
        else:
            extra = ""
            if s.per_turn == 2 and s.moves_left > 1:
                extra = f" (2 stones this turn)"
            elif s.per_turn == 2:
                extra = f" (1 stone left)"
            caption = f"{names[s.to_move]} to move{extra} - White {w}, Black {b}"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
