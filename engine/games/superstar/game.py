"""Superstar, by Christian Freeling (mid-1980s).

The "missing link" between Craige Schensted's *Star* and Freeling's later
*Starweb*: a connection / scoring game with a strong Havannah flavour, played on
the SAME 217-cell star-shaped board Starweb later reused.

BOARD (reconstructed from the official MindSports diagram + cell-for-cell
verified, see selftest.py).  The playing area is a six-fold-symmetric star: a
hexagon-of-hexes of side 7 (a hexhex-7, 127 cells) with a triangular chunk of 15
cells grown outward from the middle of each of the six sides -> 217 playable
cells.  Surrounding the star is a ring of exactly 60 cells called the EDGE; the
edge is NOT part of the playing area (you never place there) -- it exists only to
define STARs.

  * 12 OUTWARD corners  -- the convex tips of the six arms (each is adjacent to
    exactly 3 edge cells: a lone stone there is a 1-point star).  A cell with
    exactly 3 on-board neighbours.
  *  6 INWARD  corners  -- the concave notches between adjacent arms.  A cell
    with exactly 5 on-board neighbours.

The board has TWELVE SIDES.  Per Freeling: "A side is formed by 5 cells: an
inward corner, an outward corner and the 3 cells in between.  Thus the six
inward corners each belong to two sides."  Concretely each side is the boundary
arc  [inward corner, two slant cells, outward corner, one flat-top cell]; the two
sides of an arm split at the arm's flat top.  The 12 sides exactly partition the
54 boundary cells (the 6 inward corners double-counted).

PLAY.  White (player 0) moves first.  Players alternate placing one stone on a
vacant cell; passing is legal and not compulsory.  The game ends when both
players pass in succession, after which the score is counted.

SCORING.  Three formations, scored SIMULTANEOUSLY -- a single chain (connected
component of one colour) can score in all three capacities, and a player's total
is the sum over all their chains:

  * STAR       -- a chain touching >= 3 edge cells.  Value = (edge cells touched)
                  - 2.  ("touching" = hex-adjacent to that edge cell.)
  * SUPERSTAR  -- a chain connecting >= 3 sides.  Value = 5*(S - 2), S = number of
                  distinct sides it connects.  A chain "connects" a side when it
                  occupies any of that side's 5 cells; an inward-corner stone
                  connects 2 sides at once.
  * LOOP       -- a chain surrounding >= 1 cell.  Value = 1 per enclosed vacant
                  cell + 5 per enclosed opponent stone (enclosed friendly stones
                  score nothing).  Enclosure is Havannah-style: a cell is
                  surrounded when it cannot reach the board boundary without
                  crossing this chain.

KOMI.  The second player (Black) receives ``komi`` points up front to offset the
first-move advantage; Freeling notes accurate komi has not been established, so
the default is 0 and it is an integer option (a genuine tie is an honest DRAW).

WIN.  Highest total wins.  A genuine tie (equal totals) is a DRAW.

Coordinates are axial (q, r); the third cube coordinate is s = -q - r.

Source: https://mindsports.nl/index.php/the-pit/552-superstar
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1  # White (0) moves first; Black (1) moves second and gets komi

# The six axial hex directions.
_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

PLY_CAP = 500  # hard safety backstop (board holds <= 217 stones)


def _s(q: int, r: int) -> int:
    return -q - r


@lru_cache(maxsize=None)
def _cells() -> tuple:
    """The 217 playable cells: a hexhex-7 base (127) + six triangular chunks (15
    each), identical to the Starweb board."""
    base = set()
    for q in range(-6, 7):
        for r in range(-6, 7):
            if max(abs(q), abs(r), abs(_s(q, r))) <= 6:
                base.add((q, r))

    # +q chunk: outward rows q = 7, 8, 9 with widths 6, 5, 4, anchored at r = -6.
    chunk = set()
    for k in (1, 2, 3):
        q = 6 + k
        width = 7 - k
        for r in range(-6, -6 + width):
            chunk.add((q, r))

    def rot(q, r):  # 60-degree rotation about the centre, in axial coords
        return (-r, q + r)

    add = set()
    cur = chunk
    for _ in range(6):
        add |= cur
        cur = {rot(q, r) for (q, r) in cur}

    return tuple(sorted(base | add))


@lru_cache(maxsize=None)
def _cell_set() -> frozenset:
    return frozenset(_cells())


def _onboard_nbrs(cell) -> int:
    on = _cell_set()
    q, r = cell
    return sum(1 for dq, dr in _DIRS if (q + dq, r + dr) in on)


@lru_cache(maxsize=None)
def _edge() -> frozenset:
    """The 60-cell EDGE: cells adjacent to the playing area but not part of it."""
    on = _cell_set()
    out = set()
    for (q, r) in on:
        for dq, dr in _DIRS:
            nb = (q + dq, r + dr)
            if nb not in on:
                out.add(nb)
    return frozenset(out)


@lru_cache(maxsize=None)
def _edge_touch() -> dict:
    """playing cell -> frozenset of EDGE cells it is hex-adjacent to."""
    edge = _edge()
    out = {}
    for (q, r) in _cells():
        out[(q, r)] = frozenset(
            (q + dq, r + dr) for dq, dr in _DIRS if (q + dq, r + dr) in edge
        )
    return out


@lru_cache(maxsize=None)
def _outward() -> frozenset:
    """12 outward corners: playing cells with exactly 3 on-board neighbours."""
    return frozenset(c for c in _cells() if _onboard_nbrs(c) == 3)


@lru_cache(maxsize=None)
def _inward() -> frozenset:
    """6 inward corners: playing cells with exactly 5 on-board neighbours."""
    return frozenset(c for c in _cells() if _onboard_nbrs(c) == 5)


@lru_cache(maxsize=None)
def _boundary() -> frozenset:
    """The 54 boundary cells of the playing area (fewer than 6 on-board nbrs)."""
    return frozenset(c for c in _cells() if _onboard_nbrs(c) < 6)


@lru_cache(maxsize=None)
def _sides() -> tuple:
    """The 12 sides, each a frozenset of 5 boundary cells.

    A side is the boundary arc from an outward corner down a slant to an inward
    corner, plus the one flat-top cell adjacent to the outward corner:
    ``[inward corner, slant, slant, outward corner, flat-top cell]``.  Built by
    walking the boundary cycle out from each outward corner: the direction whose
    third cell is an inward corner is the slant; the other neighbour is the
    flat-top cell.
    """
    bnd = _boundary()
    OC = _outward()
    IC = _inward()

    def bnbrs(c):
        q, r = c
        return [(q + dq, r + dr) for dq, dr in _DIRS if (q + dq, r + dr) in bnd]

    def walk3(oc, first):
        # oc, first, then two more cells along the boundary (no backtracking)
        path = [oc, first]
        prev, cur = oc, first
        for _ in range(2):
            nxt = [n for n in bnbrs(cur) if n != prev]
            cand = [n for n in nxt if n not in path]
            cur2 = cand[0] if cand else nxt[0]
            path.append(cur2)
            prev, cur = cur, cur2
        return path  # length 4: [oc, a, b, c]

    sides = []
    for oc in sorted(OC):
        slant = None
        flatmid = None
        for n in bnbrs(oc):
            p = walk3(oc, n)
            if p[3] in IC:
                slant = p  # [oc, slant1, slant2, inward corner]
            else:
                flatmid = n
        assert slant is not None and flatmid is not None
        sides.append(frozenset([flatmid, oc, slant[1], slant[2], slant[3]]))
    return tuple(sides)


@lru_cache(maxsize=None)
def _side_of() -> dict:
    """playing cell -> frozenset of side indices it belongs to (0, 1, or 2)."""
    out = {c: set() for c in _cells()}
    for i, side in enumerate(_sides()):
        for c in side:
            out[c].add(i)
    return {c: frozenset(v) for c, v in out.items()}


def _cell(t: str) -> tuple[int, int]:
    q, r = t.split(",")
    return int(q), int(r)


@dataclass
class SuperstarState:
    board: dict = field(default_factory=dict)   # (q, r) -> 0/1
    to_move: int = WHITE
    passes: int = 0                              # consecutive passes
    ply: int = 0
    komi: int = 0                                # points for the SECOND player (Black)
    last: Optional[tuple] = None                 # last placed cell
    winner: Optional[int] = None                 # set at game end (None => draw)
    over: bool = False


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def _chains(board: dict, player: int) -> list[set]:
    """All connected components of ``player``'s stones."""
    out, seen = [], set()
    for cell, p in board.items():
        if p != player or cell in seen:
            continue
        comp, stack = {cell}, [cell]
        seen.add(cell)
        while stack:
            cq, cr = stack.pop()
            for dq, dr in _DIRS:
                nb = (cq + dq, cr + dr)
                if nb not in seen and board.get(nb) == player:
                    seen.add(nb)
                    comp.add(nb)
                    stack.append(nb)
        out.append(comp)
    return out


def _star_value(chain: set) -> int:
    """Edge cells the chain touches, minus 2 (0 unless it touches >= 3)."""
    et = _edge_touch()
    touched = set()
    for c in chain:
        touched |= et[c]
    n = len(touched)
    return n - 2 if n >= 3 else 0


def _superstar_value(chain: set) -> int:
    """5*(S-2) where S = distinct sides the chain connects (0 unless S >= 3)."""
    so = _side_of()
    sides = set()
    for c in chain:
        sides |= so[c]
    S = len(sides)
    return 5 * (S - 2) if S >= 3 else 0


def _enclosed(board: dict, chain: set) -> set:
    """Playing cells surrounded by ``chain`` (Havannah-style): flood the OUTSIDE
    from the playing-area boundary through every non-chain cell; anything not
    reached is enclosed by the chain."""
    on = _cell_set()
    bnd = _boundary()
    reached = set()
    stack = []
    for c in bnd:
        if c not in chain:
            reached.add(c)
            stack.append(c)
    while stack:
        cq, cr = stack.pop()
        for dq, dr in _DIRS:
            nb = (cq + dq, cr + dr)
            if nb in on and nb not in chain and nb not in reached:
                reached.add(nb)
                stack.append(nb)
    return set(c for c in on if c not in chain and c not in reached)


def _loop_value(board: dict, player: int, chain: set) -> int:
    """1 per enclosed vacant cell + 5 per enclosed opponent stone."""
    opp = 1 - player
    val = 0
    for c in _enclosed(board, chain):
        occ = board.get(c)
        if occ is None:
            val += 1
        elif occ == opp:
            val += 5
    return val


def _raw_score(board: dict, player: int) -> int:
    """Total of star + superstar + loop over all of ``player``'s chains
    (before komi)."""
    total = 0
    for chain in _chains(board, player):
        total += _star_value(chain)
        total += _superstar_value(chain)
        total += _loop_value(board, player, chain)
    return total


def _score(board: dict, player: int, komi: int) -> int:
    """Final score for a player (Black gets komi added)."""
    total = _raw_score(board, player)
    if player == BLACK:
        total += komi
    return total


class Superstar(Game):
    uid = "superstar"
    name = "Superstar"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SuperstarState:
        opts = options or {}
        komi = int(opts.get("komi", 0))
        return SuperstarState(komi=komi)

    def current_player(self, s: SuperstarState) -> int:
        return s.to_move

    def legal_moves(self, s: SuperstarState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = [f"{q},{r}" for (q, r) in _cells() if (q, r) not in s.board]
        moves.append("pass")  # passing is always legal, never compulsory
        return moves

    def apply_move(self, s: SuperstarState, move: str, rng=None) -> SuperstarState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move

        if move == "pass":
            ns = SuperstarState(
                board=dict(s.board), to_move=1 - mover, passes=s.passes + 1,
                ply=s.ply + 1, komi=s.komi, last=None,
            )
            self._maybe_finish(ns, force=(ns.passes >= 2 or ns.ply >= PLY_CAP))
            return ns

        cell = _cell(move)
        if cell not in _cell_set() or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        board[cell] = mover
        ns = SuperstarState(
            board=board, to_move=1 - mover, passes=0,
            ply=s.ply + 1, komi=s.komi, last=cell,
        )
        # Safety nets: a full board or the hard ply cap also end the game.
        self._maybe_finish(
            ns, force=(len(board) >= len(_cells()) or ns.ply >= PLY_CAP)
        )
        return ns

    def _maybe_finish(self, ns: SuperstarState, force: bool = False):
        if not force:
            return
        w = _score(ns.board, WHITE, ns.komi)
        b = _score(ns.board, BLACK, ns.komi)
        if w > b:
            ns.winner = WHITE
        elif b > w:
            ns.winner = BLACK
        else:
            ns.winner = None  # genuine tie -> honest draw
        ns.over = True

    def is_terminal(self, s: SuperstarState) -> bool:
        return s.over

    def returns(self, s: SuperstarState) -> list[float]:
        if s.winner == WHITE:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # draw (or pre-terminal)

    def heuristic(self, s: SuperstarState) -> list:
        """Score-differential eval squashed to (-1, 1) as [white, black] payoffs,
        used by MCTS when a rollout is truncated before the game ends."""
        w = _score(s.board, WHITE, s.komi)
        b = _score(s.board, BLACK, s.komi)
        v = math.tanh((w - b) / 8.0)
        return [v, -v]

    def serialize(self, s: SuperstarState) -> dict:
        return {
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "passes": s.passes,
            "ply": s.ply,
            "komi": s.komi,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "winner": s.winner,
            "over": s.over,
        }

    def deserialize(self, d: dict) -> SuperstarState:
        last = d.get("last")
        return SuperstarState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            passes=d.get("passes", 0),
            ply=d.get("ply", len(d["board"])),
            komi=d.get("komi", 0),
            last=(_cell(last) if last else None),
            winner=d.get("winner"),
            over=d.get("over", False),
        )

    def describe_move(self, s: SuperstarState, move: str) -> str:
        if move == "pass":
            return "pass"
        cell = _cell(move)
        if cell in _outward():
            return f"{move} (outward)"
        if cell in _inward():
            return f"{move} (inward)"
        return move

    def render(self, s: SuperstarState, perspective=None) -> dict:
        rad = 0.58
        edge = _edge()
        outward = _outward()
        inward = _inward()
        side_cells = set()
        for side in _sides():
            side_cells |= side

        def hexpts(q, r):
            cx = math.sqrt(3) * (q + r / 2.0)
            cy = 1.5 * r
            return [[round(cx + rad * math.cos(math.radians(60 * k + 30)), 3),
                     round(cy + rad * math.sin(math.radians(60 * k + 30)), 3)]
                    for k in range(6)]

        cells = []
        tints = {}
        # playing cells
        for (q, r) in _cells():
            cid = f"{q},{r}"
            cells.append({"id": cid, "points": hexpts(q, r)})
            if (q, r) in inward:
                tints[cid] = "#6a4a8a"     # inward corner (violet)
            elif (q, r) in outward:
                tints[cid] = "#8a5a2a"     # outward corner (warm)
            elif (q, r) in side_cells:
                tints[cid] = "#4a4030"     # other side cells (dim)
        # off-board EDGE ring cells -- not playable; used only for STAR scoring
        for (q, r) in edge:
            cid = f"e:{q},{r}"
            cells.append({"id": cid, "points": hexpts(q, r)})
            tints[cid] = "#caa75a"         # gold edge ring

        pieces = [
            {"cell": f"{q},{r}", "owner": p, "label": ""}
            for (q, r), p in s.board.items()
        ]

        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})

        names = {WHITE: "White", BLACK: "Black"}
        w = _score(s.board, WHITE, s.komi)
        b = _score(s.board, BLACK, s.komi)
        komi_note = f" (komi {s.komi})" if s.komi else ""
        if s.over:
            if s.winner is None:
                caption = f"Draw — White {w}, Black {b}{komi_note}"
            else:
                caption = f"{names[s.winner]} wins — White {w}, Black {b}{komi_note}"
        else:
            caption = f"{names[s.to_move]} to move — White {w}, Black {b}{komi_note}"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
