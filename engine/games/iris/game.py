"""Iris, by Craig Duncan, 2019 (BGG 286792).

A two-player abstract on a "hexhex" board (a hexagon made of hexagonal cells)
of side length *n*. It is a close sibling of Duncan's Exo-Hex (2019) and
Side Stitch (2017): the same best-group-with-recursive-tiebreak scoring, but
here the scoring targets are the board's own **coloured perimeter cells**.

BOARD.  A hexhex-n board has 6(n-1) perimeter cells (radius == n-1) and an
interior of gray cells (radius <= n-2). The perimeter is "rainbow" coloured so
that **each perimeter cell's same-coloured partner is exactly its 180-degree
rotation image** — i.e. the antipode (q, r) -> (-q, -r). A rotation preserves
radius, so a perimeter cell maps to a perimeter cell, and a corner maps to the
opposite corner. Thus the 6(n-1) perimeter cells split into 3(n-1) antipodal
pairs, one colour per pair. Mechanically only the *pairing* matters (which cell
is forced as the second stone after a coloured first stone); the actual hue is
cosmetic and is emitted for the UI via board.tints.

TURN PROTOCOL (1, then 2, 2, 2, ...).
  * On the very first turn Player 1 (Black, seat 0) plays a SINGLE stone to any
    empty GRAY interior cell.
  * Thereafter each turn a player plays TWO stones, subject to:
    1) If the first stone is on a COLOURED perimeter cell, the second stone MUST
       be on the corresponding same-coloured cell on the opposite side (the
       antipode). Both cells must be empty (an atomic pair).
    2) If the first stone is on a GRAY interior cell, the second stone MUST be
       on any empty NON-ADJACENT gray cell. If every remaining empty gray cell
       is adjacent to the first stone, the second stone is FORFEITED (the turn
       is a single stone).

There is no pie rule (the 1-2-2 protocol self-balances).

END & SCORING.  The game ends when the board is full or both players pass in
succession. Each player's stones form connected groups (plain hex adjacency); a
group scores the number of COLOURED perimeter cells it occupies. The owner of
the single highest-scoring group wins; ties recurse (set the tied best groups
aside, compare next-best, etc. — i.e. compare descending group-score lists
lexicographically, missing == 0). The designer states a full tie is impossible;
that holds for played-out boards, but an early symmetric double-pass genuinely
ties all the way down — such a total tie is scored as an honest DRAW.

Move encoding: an atomic pair is "c1>c2"; a single opening/forfeit stone is
"c1"; passing is "pass". Cells are axial ids "q,r".

Sources: designer's rules in the BGG description (objectid 286792);
https://drericsilverman.com/2020/03/12/connection-games-v-side-stitch/
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # seat 0 = Black, plays the single opening stone

_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
_CORNER_UNITS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]


def _radius(q: int, r: int) -> int:
    return max(abs(q), abs(r), abs(q + r))


def _antipode(c: tuple) -> tuple:
    return (-c[0], -c[1])


@lru_cache(maxsize=None)
def _all_cells(n: int) -> tuple:
    """Every cell of the hexhex-n board: radius <= n-1."""
    rad = n - 1
    out = [
        (q, r)
        for q in range(-rad, rad + 1)
        for r in range(-rad, rad + 1)
        if _radius(q, r) <= rad
    ]
    return tuple(sorted(out))


@lru_cache(maxsize=None)
def _all_set(n: int) -> frozenset:
    return frozenset(_all_cells(n))


@lru_cache(maxsize=None)
def _perim(n: int) -> frozenset:
    """Coloured perimeter cells: radius == n-1."""
    return frozenset(c for c in _all_cells(n) if _radius(*c) == n - 1)


@lru_cache(maxsize=None)
def _gray(n: int) -> frozenset:
    """Gray interior cells: radius <= n-2."""
    return frozenset(c for c in _all_cells(n) if _radius(*c) <= n - 2)


@lru_cache(maxsize=None)
def _pairs(n: int) -> tuple:
    """The 3(n-1) antipodal perimeter pairs, canonical (lo, hi) sorted."""
    seen, out = set(), []
    for c in sorted(_perim(n)):
        if c in seen:
            continue
        a = _antipode(c)
        seen.add(c)
        seen.add(a)
        out.append((min(c, a), max(c, a)))
    return tuple(out)


@lru_cache(maxsize=None)
def _pair_hue(n: int) -> dict:
    """cell -> hue in [0,360); both members of an antipodal pair share a hue.

    Hue = 2 * (screen angle folded into [0,180)). Antipodes are 180 deg apart,
    so they fold to the same value; distinct pairs get distinct hues, spanning
    the whole colour wheel — a rainbow with opposite cells matching.
    """
    out = {}
    for c in _perim(n):
        cx = math.sqrt(3) * (c[0] + c[1] / 2.0)
        cy = 1.5 * c[1]
        ang = math.degrees(math.atan2(cy, cx)) % 180.0
        out[c] = (ang * 2.0) % 360.0
    return out


def _hsl_hex(h: float, s: float, l: float) -> str:
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = l - c / 2
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return "#%02x%02x%02x" % (
        round((r + m) * 255), round((g + m) * 255), round((b + m) * 255)
    )


def _cell(t: str) -> tuple:
    q, r = t.split(",")
    return int(q), int(r)


def _fmt(c: tuple) -> str:
    return f"{c[0]},{c[1]}"


def _adjacent(a: tuple, b: tuple) -> bool:
    return (b[0] - a[0], b[1] - a[1]) in _DIRS


def _groups(board: dict, player: int, n: int) -> list:
    """Connected components of ``player``'s stones under hex adjacency."""
    owned = {c for c, p in board.items() if p == player}
    out, seen = [], set()
    for cell in owned:
        if cell in seen:
            continue
        comp, stack = {cell}, [cell]
        seen.add(cell)
        while stack:
            cq, cr = stack.pop()
            for dq, dr in _DIRS:
                nb = (cq + dq, cr + dr)
                if nb in owned and nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    stack.append(nb)
        out.append(comp)
    return out


def _score_list(board: dict, player: int, n: int) -> list:
    """Player's group scores (coloured perimeter cells contained), desc.
    Groups touching no coloured cell score 0 and are dropped."""
    perim = _perim(n)
    scores = [sum(1 for c in g if c in perim) for g in _groups(board, player, n)]
    return sorted((x for x in scores if x > 0), reverse=True)


def _compare(a: list, b: list) -> int:
    """Recursive-tiebreak comparison of two descending score lists.
    +1 if a wins, -1 if b wins, 0 on a genuine total tie (missing == 0)."""
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x != y:
            return 1 if x > y else -1
    return 0


@dataclass
class IrisState:
    n: int = 5
    board: dict = field(default_factory=dict)   # (q, r) -> 0/1
    to_move: int = BLACK
    passes: int = 0                             # consecutive passes
    ply: int = 0
    last: list = field(default_factory=list)    # cells placed last move
    winner: Optional[int] = None
    over: bool = False


class Iris(Game):
    name = "Iris"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> IrisState:
        opts = options or {}
        n = int(str(opts.get("size", 5)))
        if n < 3:
            raise ValueError("Iris needs a hexhex side >= 3")
        return IrisState(n=n)

    def current_player(self, s: IrisState) -> int:
        return s.to_move

    # ---- move generation --------------------------------------------------

    def _empty_gray(self, s: IrisState) -> list:
        return sorted(c for c in _gray(s.n) if c not in s.board)

    def legal_moves(self, s: IrisState) -> list:
        if self.is_terminal(s):
            return []
        moves = []
        if s.ply == 0:
            # Black's opening: a single stone on any empty gray cell.
            for c in self._empty_gray(s):
                moves.append(_fmt(c))
            moves.append("pass")
            return moves

        # Coloured-first atomic pairs: perimeter cell + its antipode, both empty.
        for lo, hi in _pairs(s.n):
            if lo not in s.board and hi not in s.board:
                moves.append(f"{_fmt(lo)}>{_fmt(hi)}")

        # Gray-first pairs: two empty NON-ADJACENT gray cells.
        empt = self._empty_gray(s)
        for i in range(len(empt)):
            ci = empt[i]
            has_partner = False
            for j in range(len(empt)):
                if i == j:
                    continue
                if not _adjacent(ci, empt[j]):
                    has_partner = True
                    if j > i:
                        moves.append(f"{_fmt(ci)}>{_fmt(empt[j])}")
            # Forfeit: gray first stone with every remaining empty gray adjacent.
            if not has_partner:
                moves.append(_fmt(ci))

        moves.append("pass")
        return moves

    # ---- apply ------------------------------------------------------------

    def apply_move(self, s: IrisState, move: str, rng=None) -> IrisState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move

        if move == "pass":
            ns = IrisState(
                n=s.n, board=dict(s.board), to_move=1 - mover,
                passes=s.passes + 1, ply=s.ply + 1, last=[],
            )
            self._maybe_finish(ns, force=(ns.passes >= 2))
            return ns

        cells = [_cell(x) for x in move.split(">")]
        allset = _all_set(s.n)
        for c in cells:
            if c not in allset:
                raise ValueError(f"off-board cell {c} in {move!r}")
            if c in s.board:
                raise ValueError(f"cell {c} occupied in {move!r}")
        if len(cells) not in (1, 2):
            raise ValueError(f"bad move {move!r}")

        if s.ply == 0:
            if len(cells) != 1 or cells[0] not in _gray(s.n):
                raise ValueError("opening must be a single gray stone")
        elif len(cells) == 1:
            c = cells[0]
            if c not in _gray(s.n):
                raise ValueError("single (forfeit) stone must be gray")
            # Forfeit legal only if no empty gray is non-adjacent to c.
            for d in _gray(s.n):
                if d != c and d not in s.board and not _adjacent(c, d):
                    raise ValueError("second stone not forfeited: a legal gray "
                                     "non-adjacent cell exists")
        else:
            c1, c2 = cells
            if c1 == c2:
                raise ValueError("two distinct cells required")
            if c1 in _perim(s.n) or c2 in _perim(s.n):
                # Coloured pair: must be an antipodal perimeter pair.
                if not (c1 in _perim(s.n) and c2 in _perim(s.n)
                        and _antipode(c1) == c2):
                    raise ValueError("coloured first stone forces its antipode")
            else:
                # Gray pair: both gray, non-adjacent.
                if _adjacent(c1, c2):
                    raise ValueError("gray second stone must be non-adjacent")

        board = dict(s.board)
        for c in cells:
            board[c] = mover
        ns = IrisState(
            n=s.n, board=board, to_move=1 - mover, passes=0,
            ply=s.ply + 1, last=list(cells),
        )
        self._maybe_finish(ns, force=(len(board) >= len(_all_cells(s.n))))
        return ns

    def _maybe_finish(self, ns: IrisState, force: bool = False):
        if not force:
            return
        cmp = _compare(_score_list(ns.board, BLACK, ns.n),
                       _score_list(ns.board, WHITE, ns.n))
        ns.winner = BLACK if cmp > 0 else (WHITE if cmp < 0 else None)
        ns.over = True

    def is_terminal(self, s: IrisState) -> bool:
        return s.over

    def returns(self, s: IrisState) -> list:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: IrisState) -> list:
        a = _score_list(s.board, BLACK, s.n)
        b = _score_list(s.board, WHITE, s.n)
        diff = 0.0
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else 0
            y = b[i] if i < len(b) else 0
            diff += (x - y) * (0.5 ** i)
        v = math.tanh(diff / 4.0)
        return [v, -v]

    # ---- serialize --------------------------------------------------------

    def serialize(self, s: IrisState) -> dict:
        return {
            "n": s.n,
            "board": {_fmt(c): p for c, p in s.board.items()},
            "to_move": s.to_move,
            "passes": s.passes,
            "ply": s.ply,
            "last": [_fmt(c) for c in s.last],
            "winner": s.winner,
            "over": s.over,
        }

    def deserialize(self, d: dict) -> IrisState:
        return IrisState(
            n=d.get("n", 5),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            passes=d.get("passes", 0),
            ply=d.get("ply", len(d["board"])),
            last=[_cell(x) for x in d.get("last", [])],
            winner=d.get("winner"),
            over=d.get("over", False),
        )

    def describe_move(self, s: IrisState, move: str) -> str:
        if move == "pass":
            return "pass"
        cells = move.split(">")
        if len(cells) == 2:
            c1, c2 = (_cell(cells[0]), _cell(cells[1]))
            if c1 in _perim(s.n) and c2 in _perim(s.n):
                return f"{cells[0]} + {cells[1]} (antipodal pair)"
            return f"{cells[0]} + {cells[1]}"
        if s.ply != 0:
            return f"{move} (forfeit)"
        return move

    # ---- render -----------------------------------------------------------

    def render(self, s: IrisState, perspective=None) -> dict:
        n = s.n
        rad = 0.58
        perim = _perim(n)
        hue = _pair_hue(n)

        def hexpts(q, r):
            cx = math.sqrt(3) * (q + r / 2.0)
            cy = 1.5 * r
            return [[round(cx + rad * math.cos(math.radians(60 * k + 30)), 3),
                     round(cy + rad * math.sin(math.radians(60 * k + 30)), 3)]
                    for k in range(6)]

        cells, tints = [], {}
        for c in _all_cells(n):
            cid = _fmt(c)
            cells.append({"id": cid, "points": hexpts(*c)})
            if c in perim:
                tints[cid] = _hsl_hex(hue[c], 0.70, 0.62)
            else:
                tints[cid] = "#cdc8bb"  # gray interior

        pieces = [
            {"cell": _fmt(c), "owner": p, "label": ""}
            for c, p in s.board.items()
        ]
        highlights = [{"cell": _fmt(c), "kind": "last-move"} for c in s.last]

        names = {BLACK: "Black", WHITE: "White"}
        bl = _score_list(s.board, BLACK, n)
        wh = _score_list(s.board, WHITE, n)

        def top(xs):
            return xs[0] if xs else 0

        if s.over:
            result = "Draw" if s.winner is None else f"{names[s.winner]} wins"
            caption = (f"{result} — best group: "
                       f"Black {top(bl)}, White {top(wh)}")
        else:
            phase = "opening (1 gray stone)" if s.ply == 0 else "2 stones"
            caption = (f"{names[s.to_move]} to move [{phase}] — best group: "
                       f"Black {top(bl)}, White {top(wh)}")

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
