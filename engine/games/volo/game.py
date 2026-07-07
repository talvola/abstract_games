"""Volo, by Dieter Stein (2010) — published by nestorgames.

Inspired by flocking birds. Played on the intersection points of a hexagonal
"hexhex" grid (edge 7 = 120 points for the standard board, edge 6 = 84 for the
small board) with the six CORNERS and the CENTRE removed (the "sky"). Each
player owns birds of one colour and wins by gathering ALL of their on-board
birds into ONE contiguous flock (adjacency-connected group).

Each turn you choose ONE of:

  * ADD a bird on a vacant point that is (a) NOT adjacent to a friendly bird and
    (b) NOT inside a region controlled by the opponent (a vacant region whose
    surrounding birds include none of your own — i.e. it has no "open path", a
    chain of vacant/friendly points, to any friendly bird).

  * FLY.  A single bird, or an entire flock that forms a straight line, moves
    rigidly in a straight line (any of the 6 hex directions, any distance) over
    vacant points — it may PASS OVER friendly birds but an ENEMY bird blocks the
    flight.  The move MUST end adjacent to another friendly bird (enlarging a
    flock) and may NEVER split an existing flock.  A single bird belonging to a
    larger flock may also fly ("rearrange") provided the rest of its flock stays
    joined and the move attaches it to a further flock (net enlargement).

REGIONS.  After a move, if the OPPONENT's birds are separated into two or more
regions (no open path between them), all but one region is removed and returned
to the owner's supply — the MOVER chooses which region survives.  (A player's
own move can only ever fragment the opponent, never themselves, so the choice is
always about the opponent.)  It is possible the opponent is thereby reduced to a
single flock and wins immediately.

WIN PRIORITY (regions are always secondary): if your move brings ALL your birds
into one flock you WIN at once, even if it simultaneously fragments the opponent
— no regions are cleared.  Otherwise regions are resolved, and then if the
opponent is left with a single flock the opponent wins.

PASS.  If no add and no fly is available you MUST pass.  If the only legal adds
are into your OWN enclosed regions (and you have no fly) you MAY pass.  Two
consecutive passes end the game in a DRAW.  A hard ply cap is also a draw
(termination backstop — flights can otherwise cycle forever).

MOVE ENCODING (strings):
  * add           -> "q,r"                    (single point)
  * single fly    -> "q1,r1>q2,r2"            (from > to)
  * whole flock   -> "*q1,r1>q2,r2"           ('*' + anchor(min cell) > its dest)
  * pass          -> "pass"
  * region choice -> append "=q,r" naming the surviving region's representative
                     (its minimum cell) when a move fragments the opponent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))
AXES = ((1, 0), (0, 1), (1, -1))  # the 3 line axes (for straight-line flocks)


@lru_cache(maxsize=None)
def _points(R: int) -> frozenset:
    """On-board points of a hexhex of radius R minus the 6 corners and centre."""
    corners = {(R, 0), (R, -R), (0, -R), (-R, 0), (-R, R), (0, R)}
    out = set()
    for q in range(-R, R + 1):
        for r in range(-R, R + 1):
            s = -q - r
            if max(abs(q), abs(r), abs(s)) <= R and (q, r) not in corners and (q, r) != (0, 0):
                out.add((q, r))
    return frozenset(out)


@lru_cache(maxsize=None)
def _nests(R: int) -> tuple:
    """(seat0_nests, seat1_nests): the 6 edge-midpoint nests, alternating."""
    M = 6 if R == 6 else 4  # standard insets at magnitude 6; small board at 4
    D = ((2, -1), (1, -2), (-1, -1), (-2, 1), (-1, 2), (1, 1))  # cyclic around rim
    nests = [((M // 2) * d[0], (M // 2) * d[1]) for d in D]
    return (tuple(nests[0::2]), tuple(nests[1::2]))


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def _cid(p) -> str:
    return f"{p[0]},{p[1]}"


def _neighbors(p):
    q, r = p
    return [(q + dq, r + dr) for dq, dr in DIRS]


def _flocks(board: dict, colour: int) -> list:
    """Adjacency-connected components (flocks) of `colour`."""
    seen, out = set(), []
    for p, c in board.items():
        if c != colour or p in seen:
            continue
        comp, stack = [p], [p]
        seen.add(p)
        while stack:
            cur = stack.pop()
            for nb in _neighbors(cur):
                if nb not in seen and board.get(nb) == colour:
                    seen.add(nb)
                    comp.append(nb)
                    stack.append(nb)
        out.append(comp)
    return out


def _component(board: dict, start, colour: int) -> set:
    comp, stack = {start}, [start]
    while stack:
        for nb in _neighbors(stack.pop()):
            if nb not in comp and board.get(nb) == colour:
                comp.add(nb)
                stack.append(nb)
    return comp


def _regions(board: dict, pts: frozenset, colour: int) -> list:
    """Open-path regions of `colour`: birds connected through vacant/own points.

    Returns a list of sets of that colour's bird cells (one per region)."""
    passable = {c for c in pts if board.get(c) in (None, colour)}
    seen, regions = set(), []
    for c in passable:
        if c in seen:
            continue
        comp, stack = [c], [c]
        seen.add(c)
        birds = set()
        while stack:
            cur = stack.pop()
            if board.get(cur) == colour:
                birds.add(cur)
            for nb in _neighbors(cur):
                if nb in passable and nb not in seen:
                    seen.add(nb)
                    comp.append(nb)
                    stack.append(nb)
        if birds:
            regions.append(birds)
    return regions


def _is_line(cells: list) -> bool:
    """Does a flock form a single contiguous straight line along one axis?"""
    if len(cells) <= 1:
        return True
    for ax in AXES:
        # perpendicular invariant: q (for r-axis), r (for q-axis), or s.
        if ax == (1, 0):
            key = lambda p: p[1]          # constant r
            pos = lambda p: p[0]          # order by q
        elif ax == (0, 1):
            key = lambda p: p[0]          # constant q
            pos = lambda p: p[1]          # order by r
        else:  # (1,-1)  -> constant s = -q-r
            key = lambda p: -p[0] - p[1]
            pos = lambda p: p[0]
        ks = {key(p) for p in cells}
        if len(ks) != 1:
            continue
        vs = sorted(pos(p) for p in cells)
        if vs[-1] - vs[0] == len(vs) - 1 and len(set(vs)) == len(vs):
            return True
    return False


@dataclass
class VState:
    R: int = 6
    board: dict = field(default_factory=dict)  # (q,r) -> 0/1
    to_move: int = 0
    supply: tuple = (60, 60)
    ply: int = 0
    passes: int = 0
    winner: Optional[int] = None
    drawn: bool = False
    draw_kind: str = ""
    last: Optional[list] = None                 # list of cell-ids to highlight
    _map: Optional[dict] = field(default=None, repr=False, compare=False)


class Volo(Game):
    uid = "volo"
    name = "Volo"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup ---------------------------------------------------------------

    def initial_state(self, options=None, rng=None) -> VState:
        opts = options or {}
        size = int(opts.get("size", 120))
        R = 6 if size >= 120 else 5
        pts = _points(R)
        n0, n1 = _nests(R)
        board = {}
        for p in n0:
            board[p] = 0
        for p in n1:
            board[p] = 1
        supply = (len(pts) // 2 - len(n0), len(pts) // 2 - len(n1))
        return VState(R=R, board=board, supply=supply)

    def current_player(self, s: VState) -> int:
        return s.to_move

    # ---- move generation -----------------------------------------------------

    def _build(self, s: VState) -> dict:
        """Return {move_string: (new_board, new_supply, winner_or_None)}.

        Boards are POST region-clearing; winner set when the move ends the game.
        'pass' is handled separately in apply_move."""
        if s._map is not None:
            return s._map
        R, board, me = s.R, s.board, s.to_move
        opp = 1 - me
        pts = _points(R)
        out = {}

        # ---- collect candidate ACTIONS as (label, resulting_board_preclear) ----
        actions = []  # (move_str_base, board_after_action)

        # ADD moves ----------------------------------------------------------
        add_own_only = []   # adds that are only into your own regions
        add_useful = []     # adds not restricted to own regions
        if s.supply[me] > 0:
            # classify every vacant point by its vacant-region's touching birds
            vac = [c for c in pts if c not in board]
            vacset = set(vac)
            seenv = set()
            for start in vac:
                if start in seenv:
                    continue
                comp, stack = [start], [start]
                seenv.add(start)
                touch_me = touch_opp = False
                while stack:
                    cur = stack.pop()
                    for nb in _neighbors(cur):
                        b = board.get(nb)
                        if b == me:
                            touch_me = True
                        elif b == opp:
                            touch_opp = True
                        elif nb in vacset and nb not in seenv:
                            seenv.add(nb)
                            comp.append(nb)
                            stack.append(nb)
                if not touch_me:
                    continue  # opponent-controlled region -> illegal add
                for c in comp:
                    # not adjacent to a friendly bird
                    if any(board.get(nb) == me for nb in _neighbors(c)):
                        continue
                    if touch_opp:
                        add_useful.append(c)
                    else:
                        add_own_only.append(c)
            add_sup = list(s.supply)
            add_sup[me] -= 1
            add_sup = tuple(add_sup)
            for c in add_useful + add_own_only:
                nb = dict(board)
                nb[c] = me
                actions.append((_cid(c), nb, add_sup))

        # FLY moves ----------------------------------------------------------
        flocks = _flocks(board, me)
        # single-bird flies (lone bird, or one bird out of a larger flock)
        for F in flocks:
            Fset = set(F)
            for b in F:
                if len(F) > 1:
                    rem = Fset - {b}
                    # removing b must not split the remaining flock
                    if len(_component({**{p: me for p in rem}}, next(iter(rem)), me)) != len(rem):
                        continue
                else:
                    rem = set()
                for dq, dr in DIRS:
                    q, r = b
                    dist = 0
                    while True:
                        q += dq
                        r += dr
                        cell = (q, r)
                        if cell not in pts:
                            break
                        occ = board.get(cell)
                        if occ == opp:
                            break  # enemy blocks
                        dist += 1
                        if occ is not None:
                            continue  # pass over a friendly bird
                        # land on vacant `cell`
                        nb = dict(board)
                        del nb[b]
                        nb[cell] = me
                        newflock = _component(nb, cell, me)
                        # must enlarge: attach to a friendly bird outside the moved unit
                        if len(F) > 1:
                            if not (rem <= newflock) or len(newflock) <= len(F):
                                continue
                        else:
                            if len(newflock) < 2:
                                continue
                        actions.append((f"{_cid(b)}>{_cid(cell)}", nb, s.supply))
        # whole-flock line flies (size >= 2, straight line) — rigid translation
        for F in flocks:
            if len(F) < 2 or not _is_line(F):
                continue
            Fset = set(F)
            anchor = min(F)
            for dq, dr in DIRS:
                dist = 0
                while True:
                    dist += 1
                    dest = {(q + dq * dist, r + dr * dist) for (q, r) in F}
                    if any(c not in pts for c in dest):
                        break
                    # swept cells for each bird up to `dist`, excluding self-cells
                    blocked = False
                    for (q, r) in F:
                        for k in range(1, dist + 1):
                            c = (q + dq * k, r + dr * k)
                            if board.get(c) == opp:
                                blocked = True
                                break
                        if blocked:
                            break
                    if blocked:
                        break
                    # destinations must be vacant (ignoring the flock's own cells)
                    if any((c in board and c not in Fset) for c in dest):
                        continue
                    nb = dict(board)
                    for c in F:
                        del nb[c]
                    for c in dest:
                        nb[c] = me
                    achor_dest = (anchor[0] + dq * dist, anchor[1] + dr * dist)
                    newflock = _component(nb, achor_dest, me)
                    if len(newflock) <= len(F):
                        continue  # must enlarge (attach to another flock)
                    actions.append((f"*{_cid(anchor)}>{_cid(achor_dest)}", nb, s.supply))

        # ---- resolve each action: win priority + region clearing -----------
        for base, pboard, act_sup in actions:
            # (1) mover win?  all my birds one flock -> win, regions ignored.
            myf = _flocks(pboard, me)
            if len(myf) == 1:
                out[base] = (pboard, act_sup, me)
                continue
            # (2) region clearing for the opponent
            regs = _regions(pboard, pts, opp)
            if len(regs) <= 1:
                winner = self._winner_after(pboard, me, opp)
                out[base] = (pboard, act_sup, winner)
            else:
                for keep in regs:
                    fboard = dict(pboard)
                    removed = 0
                    for reg in regs:
                        if reg is keep:
                            continue
                        for c in reg:
                            del fboard[c]
                            removed += 1
                    sup = list(act_sup)
                    sup[opp] += removed
                    rep = min(keep)
                    winner = self._winner_after(fboard, me, opp)
                    out[f"{base}={_cid(rep)}"] = (fboard, tuple(sup), winner)

        s._map = out
        return out

    @staticmethod
    def _winner_after(board, me, opp):
        # mover already checked; after clearing, opponent single flock -> opp wins.
        of = _flocks(board, opp)
        if len(of) == 1:
            return opp
        mf = _flocks(board, me)
        if len(mf) == 1:
            return me
        return None

    def _legal(self, s: VState):
        mp = self._build(s)
        strings = list(mp.keys())
        if not strings:
            return ["pass"]                       # forced pass (no action at all)
        if self._has_useful_action(s):
            return strings                        # must act
        return strings + ["pass"]                 # may pass (only own-region adds)

    def _has_useful_action(self, s: VState) -> bool:
        """True if the mover has a fly, or an add that is NOT restricted to their
        own enclosed region — i.e. an action they are obliged to consider."""
        mp = self._build(s)
        if any(">" in k for k in mp):             # any legal fly
            return True
        me, opp, pts, board = s.to_move, 1 - s.to_move, _points(s.R), s.board
        if s.supply[me] <= 0:
            return False
        vacset = {c for c in pts if c not in board}
        seenv = set()
        for start in vacset:
            if start in seenv:
                continue
            comp, stack = [start], [start]
            seenv.add(start)
            touch_me = touch_opp = False
            while stack:
                for nb in _neighbors(stack.pop()):
                    b = board.get(nb)
                    if b == me:
                        touch_me = True
                    elif b == opp:
                        touch_opp = True
                    elif nb in vacset and nb not in seenv:
                        seenv.add(nb)
                        comp.append(nb)
                        stack.append(nb)
            if not (touch_me and touch_opp):
                continue                          # own-region or opponent-region
            # a neutral region (touches both): a legal non-own-region add exists?
            for c in comp:
                if not any(board.get(nb) == me for nb in _neighbors(c)):
                    return True
        return False

    def legal_moves(self, s: VState):
        if s.winner is not None or s.drawn:
            return []
        return self._legal(s)

    def is_terminal(self, s: VState) -> bool:
        return s.winner is not None or s.drawn

    # ---- apply ---------------------------------------------------------------

    def apply_move(self, s: VState, move: str, rng=None) -> VState:
        if move == "pass":
            passes = s.passes + 1
            drawn = passes >= 2
            return VState(R=s.R, board=dict(s.board), to_move=1 - s.to_move,
                          supply=s.supply, ply=s.ply + 1, passes=passes,
                          drawn=drawn, draw_kind=("double-pass" if drawn else ""),
                          last=None)
        mp = self._build(s)
        if move not in mp:
            raise ValueError(f"illegal move {move!r}")
        board, supply, winner = mp[move]
        ply = s.ply + 1
        drawn = False
        kind = ""
        if winner is None and ply >= self._cap(s.R):
            drawn, kind = True, "ply-cap"
        # last-move highlight
        base = move.split("=")[0]
        if base.startswith("*"):
            base = base[1:]
        last = [c for c in base.split(">")]
        return VState(R=s.R, board=board, to_move=1 - s.to_move, supply=supply,
                      ply=ply, passes=0, winner=winner, drawn=drawn,
                      draw_kind=kind, last=last)

    @staticmethod
    def _cap(R: int) -> int:
        return 4 * len(_points(R))

    def returns(self, s: VState):
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- heuristic -----------------------------------------------------------

    def heuristic(self, s: VState):
        f0 = len(_flocks(s.board, 0)) or 1
        f1 = len(_flocks(s.board, 1)) or 1
        # fewer flocks (closer to a single flock) is better
        score0 = math.tanh((f1 - f0) / 3.0)
        return [score0, -score0]

    # ---- serialize -----------------------------------------------------------

    def serialize(self, s: VState) -> dict:
        return {
            "R": s.R,
            "board": {_cid(p): c for p, c in s.board.items()},
            "to_move": s.to_move,
            "supply": list(s.supply),
            "ply": s.ply,
            "passes": s.passes,
            "winner": s.winner,
            "drawn": s.drawn,
            "draw_kind": s.draw_kind,
            "last": list(s.last) if s.last else None,
        }

    def deserialize(self, d: dict) -> VState:
        return VState(
            R=d["R"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            supply=tuple(d.get("supply", [60, 60])),
            ply=d.get("ply", 0),
            passes=d.get("passes", 0),
            winner=d.get("winner"),
            drawn=d.get("drawn", False),
            draw_kind=d.get("draw_kind", ""),
            last=list(d["last"]) if d.get("last") else None,
        )

    # ---- presentation --------------------------------------------------------

    def describe_move(self, s: VState, move: str) -> str:
        if move == "pass":
            return "pass"
        parts = move.split("=")
        base = parts[0]
        choice = parts[1] if len(parts) > 1 else None
        if base.startswith("*"):
            a, b = base[1:].split(">")
            flock = _component(s.board, _cell(a), s.to_move)
            txt = f"flock {a}→{b} ({len(flock)} birds)"
        elif ">" in base:
            a, b = base.split(">")
            txt = f"fly {a}→{b}"
        else:
            txt = f"add {base}"
        if choice:
            txt += f" [keep region @{choice}]"
        return txt

    def render(self, s: VState, perspective=None) -> dict:
        names = {0: "Orange", 1: "Blue"}
        pts = _points(s.R)
        pieces = [{"cell": _cid(p), "owner": c, "label": ""}
                  for p, c in s.board.items()]
        highlights = []
        for c in (s.last or []):
            highlights.append({"cell": c, "kind": "last-move"})
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.drawn:
            caption = f"Draw ({s.draw_kind})"
        else:
            f = len(_flocks(s.board, s.to_move))
            caption = f"{names[s.to_move]} to move — {f} flock(s)"
        # hexhex render; the 6 corners + centre are simply never occupied.
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.R + 1},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
