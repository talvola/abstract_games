"""Anchor, by Steven Meyers (2000).

A hexagonal territorial game published in *Abstract Games* magazine issue 5
(Spring 2001, "Anchor — Redefining Life and Death" by Kerry Handscomb, rules by
the designer). Go-like territory scoring on the standard Havannah board
(hexhex, 8 cells per side), but life and death are redefined: there are no
liberties, no captures during play, and no eyes.

* Black and White alternately place a stone on any empty hex (Black first) or
  pass; stones never move. Two consecutive passes end the game.
* The six board corners are marked alternately black and white: each player has
  three HOME corners (their colour) and three AWAY corners.
* An ANCHOR is a connected group touching at least two sides of the board
  (a corner cell touches both of its sides), EXCEPT that a group touching
  exactly two ADJACENT sides is an anchor only if those sides meet at one of
  the owner's home corners. So a lone stone in a home corner is an anchor; in
  an away corner it is not.
* At the end every stone not part of an anchor is dead — determined
  simultaneously, by explicit connection only (dead enemy stones are NOT
  removed first to enable other connections). Dead stones are removed; then
  each player scores 1 point per empty hex whose bordering stones are all
  their own (Go-style territory; regions touching both colours or no stones
  are neutral) plus 1 point per dead enemy stone. Higher total wins; an equal
  score is a draw.
* Pie rule: in place of their first move White may play ``"swap"``. Because
  the home corners make the board colour-asymmetric, the swap recolours the
  opening stone AND reflects it through the board centre (the central
  reflection maps each player's home corners exactly onto the other's, so the
  resulting position is strategically identical to the one White declined).

Coordinates are axial (q, r) exactly as in the Havannah module: on-board iff
max(|q|, |r|, |q+r|) <= size-1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1


def _neighbors(q: int, r: int):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1), (q + 1, r - 1), (q - 1, r + 1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    out = []
    n = size - 1
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            if abs(q + r) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


# ---------------------------------------------------------------------------
# Sides and corners.
#
# Side ids follow the Havannah module: a border cell lies on the side whose
# cube coordinate (q, r, or s = -q-r) is pinned at +/-(size-1):
#   q=+n -> 0, r=-n -> 1, s=+n -> 2, q=-n -> 3, r=+n -> 4, s=-n -> 5.
# Unlike Havannah's edge classification, in Anchor a CORNER cell belongs to
# BOTH of its sides. Adjacent sides i, i+1 (mod 6) meet at exactly one corner.
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _sides_of(size: int) -> dict:
    """Map border cell -> frozenset of side ids (corners get two)."""
    n = size - 1
    out = {}
    for (q, r) in _cells(size):
        s = -q - r
        ids = set()
        if q == n:
            ids.add(0)
        if r == -n:
            ids.add(1)
        if s == n:
            ids.add(2)
        if q == -n:
            ids.add(3)
        if r == n:
            ids.add(4)
        if s == -n:
            ids.add(5)
        if ids:
            out[(q, r)] = frozenset(ids)
    return out


@lru_cache(maxsize=None)
def _pair_corner(size: int) -> dict:
    """Adjacent side pair (frozenset) -> the corner cell where they meet."""
    n = size - 1
    return {
        frozenset({0, 1}): (n, -n),
        frozenset({1, 2}): (0, -n),
        frozenset({2, 3}): (-n, 0),
        frozenset({3, 4}): (-n, n),
        frozenset({4, 5}): (0, n),
        frozenset({5, 0}): (n, 0),
    }


@lru_cache(maxsize=None)
def _home_corners(size: int) -> tuple:
    """(black_home_corners, white_home_corners) — alternating around the board.

    Matches the magazine's Figure 1 (in its projection: top corner white, then
    alternating). The assignment is unique up to rotation, which does not
    change the game.
    """
    n = size - 1
    black = frozenset({(n, -n), (-n, 0), (0, n)})
    white = frozenset({(n, 0), (0, -n), (-n, n)})
    return black, white


# ---------------------------------------------------------------------------
# Groups / anchors / scoring
# ---------------------------------------------------------------------------
def _groups(board: dict, color: int) -> list:
    stones = {c for c, v in board.items() if v == color}
    seen, out = set(), []
    for c in sorted(stones):
        if c in seen:
            continue
        g = {c}
        stack = [c]
        while stack:
            cur = stack.pop()
            for nb in _neighbors(*cur):
                if nb in stones and nb not in g:
                    g.add(nb)
                    stack.append(nb)
        seen |= g
        out.append(g)
    return out


def _is_anchor(group: set, color: int, size: int) -> bool:
    sides_of = _sides_of(size)
    sides = set()
    for c in group:
        sides |= sides_of.get(c, frozenset())
    if len(sides) < 2:
        return False
    if len(sides) == 2:
        pair = frozenset(sides)
        corner = _pair_corner(size).get(pair)
        if corner is not None:  # the two sides are adjacent
            home = _home_corners(size)[color]
            return corner in home
    return True  # two non-adjacent sides, or three or more sides


def score(board: dict, size: int):
    """Full end-of-game accounting.

    Returns (dead, territory, prisoners, totals) where dead is
    {color: set(cells)}, and territory/prisoners/totals are per-colour
    [black, white] lists (totals = territory + prisoners).
    """
    dead = {BLACK: set(), WHITE: set()}
    for color in (BLACK, WHITE):
        for g in _groups(board, color):
            if not _is_anchor(g, color, size):
                dead[color] |= g
    live = {c: v for c, v in board.items() if c not in dead[BLACK] and c not in dead[WHITE]}

    on = _cell_set(size)
    empty = on - set(live)
    territory = [0, 0]
    seen = set()
    for c in sorted(empty):
        if c in seen:
            continue
        region = {c}
        stack = [c]
        border = set()
        while stack:
            cur = stack.pop()
            for nb in _neighbors(*cur):
                if nb not in on:
                    continue
                if nb in live:
                    border.add(live[nb])
                elif nb not in region:
                    region.add(nb)
                    stack.append(nb)
        seen |= region
        if border == {BLACK}:
            territory[BLACK] += len(region)
        elif border == {WHITE}:
            territory[WHITE] += len(region)
    prisoners = [len(dead[WHITE]), len(dead[BLACK])]  # you score the ENEMY dead
    totals = [territory[i] + prisoners[i] for i in (BLACK, WHITE)]
    return dead, territory, prisoners, totals


def _cell(s: str) -> tuple:
    q, r = s.split(",")
    return int(q), int(r)


# ---------------------------------------------------------------------------
# State / Game
# ---------------------------------------------------------------------------
@dataclass
class AnchorState:
    size: int = 8
    board: dict = field(default_factory=dict)  # (q, r) -> BLACK/WHITE
    to_move: int = BLACK
    passes: int = 0
    ply: int = 0
    pie: bool = True
    last: Optional[object] = None  # (q, r), "pass", "swap", or None


class Anchor(Game):
    name = "Anchor"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AnchorState:
        opts = options or {}
        size = int(opts.get("size", 8))
        pie = bool(opts.get("pie", True))
        return AnchorState(size=size, pie=pie)

    def current_player(self, s: AnchorState) -> int:
        return s.to_move

    def _ply_cap(self, s: AnchorState) -> int:
        return 2 * len(_cells(s.size)) + 16

    def legal_moves(self, s: AnchorState) -> list:
        if self.is_terminal(s):
            return []
        moves = [f"{q},{r}" for (q, r) in _cells(s.size) if (q, r) not in s.board]
        if s.pie and s.ply == 1 and len(s.board) == 1:
            moves.append("swap")
        moves.append("pass")
        return moves

    def apply_move(self, s: AnchorState, move: str, rng=None) -> AnchorState:
        if move == "pass":
            return AnchorState(size=s.size, board=dict(s.board), to_move=1 - s.to_move,
                               passes=s.passes + 1, ply=s.ply + 1, pie=s.pie, last="pass")
        if move == "swap":
            if not (s.pie and s.ply == 1 and len(s.board) == 1):
                raise ValueError("swap not available")
            ((q, r), _), = list(s.board.items())
            # Recolour AND reflect through the centre: the central reflection
            # maps Black's home corners onto White's, so the swapped position
            # is exactly the mirror of the one White declined.
            board = {(-q, -r): WHITE}
            return AnchorState(size=s.size, board=board, to_move=BLACK,
                               passes=0, ply=s.ply + 1, pie=s.pie, last="swap")
        q, r = _cell(move)
        if (q, r) not in _cell_set(s.size) or (q, r) in s.board:
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        board[(q, r)] = s.to_move
        return AnchorState(size=s.size, board=board, to_move=1 - s.to_move,
                           passes=0, ply=s.ply + 1, pie=s.pie, last=(q, r))

    def is_terminal(self, s: AnchorState) -> bool:
        return s.passes >= 2 or s.ply >= self._ply_cap(s)

    def returns(self, s: AnchorState) -> list:
        if not self.is_terminal(s):
            return [0.0, 0.0]
        _, _, _, totals = score(s.board, s.size)
        if totals[BLACK] > totals[WHITE]:
            return [1.0, -1.0]
        if totals[WHITE] > totals[BLACK]:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # honest draw on an equal score

    def heuristic(self, s: AnchorState) -> list:
        _, _, _, totals = score(s.board, s.size)
        v = math.tanh((totals[BLACK] - totals[WHITE]) / 10.0)
        return [v, -v]

    # ---- serialization ----------------------------------------------------
    def serialize(self, s: AnchorState) -> dict:
        last = s.last
        if isinstance(last, tuple):
            last = f"{last[0]},{last[1]}"
        return {
            "size": s.size,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "passes": s.passes,
            "ply": s.ply,
            "pie": s.pie,
            "last": last,
        }

    def deserialize(self, d: dict) -> AnchorState:
        last = d.get("last")
        if isinstance(last, str) and "," in last:
            last = _cell(last)
        return AnchorState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            passes=d.get("passes", 0),
            ply=d.get("ply", len(d["board"])),
            pie=d.get("pie", True),
            last=last,
        )

    # ---- presentation -----------------------------------------------------
    def describe_move(self, s: AnchorState, move: str) -> str:
        if move == "pass":
            return "pass"
        if move == "swap":
            return "swap (pie)"
        return move

    def render(self, s: AnchorState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        black_home, white_home = _home_corners(s.size)
        # Home-corner markers in the seat colours (dimmed so stones read on top).
        tints = {}
        for (q, r) in black_home:
            tints[f"{q},{r}"] = "#6e2222"   # seat 0 (red) dimmed
        for (q, r) in white_home:
            tints[f"{q},{r}"] = "#22406e"   # seat 1 (blue) dimmed
        pieces = [{"cell": f"{q},{r}", "owner": p} for (q, r), p in s.board.items()]
        highlights = []
        if isinstance(s.last, tuple):
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})

        dead, terr, pris, totals = score(s.board, s.size)
        tally = (f"B {totals[BLACK]} ({terr[BLACK]}+{pris[BLACK]}) / "
                 f"W {totals[WHITE]} ({terr[WHITE]}+{pris[WHITE]})")
        if self.is_terminal(s):
            if totals[BLACK] == totals[WHITE]:
                caption = f"Draw — {tally}"
            else:
                w = BLACK if totals[BLACK] > totals[WHITE] else WHITE
                caption = f"{names[w]} wins — {tally}"
        else:
            passed = "  ·  opponent passed" if s.last == "pass" else ""
            caption = f"{names[s.to_move]} to move{passed}  ·  if scored now: {tally}"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
