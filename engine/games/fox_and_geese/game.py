"""Fox and Geese -- the classic asymmetric "tafl"-descended hunt game on the
cross-shaped board of 33 points (a 3x3 centre with a 2x3 arm on each face).

Seat 0 = **Geese** (15 of them); seat 1 = the lone **Fox**. The geese move first.

Board: the 33 points sit on a 7x7 grid with the four 2x2 corner blocks removed.
Points are joined by horizontal/vertical lines everywhere, plus diagonal lines at
the "strong" points -- the classic alquerque pattern, where (col + row) is even.
Adjacency = a single step to a directly-linked point.

Geese move one step along a line to an adjacent empty point, but may only move
FORWARD (toward the fox's starting half), SIDEWAYS, or DIAGONALLY FORWARD -- never
backward or diagonally backward. Geese here move toward DECREASING row. Geese
never capture.

The Fox moves one step along a line to an adjacent empty point (in any direction),
OR jumps an adjacent goose in a straight line along a marked line to the empty
point beyond, removing that goose (as in draughts). Multi-jumps chain: after a
jump the fox may immediately jump again (along any line). Captures are NOT
mandatory; a single step or a one-hop jump may end the turn even when a further
jump is available.

Win conditions (asymmetric):
  * The GEESE win by trapping the fox so that it has no legal move on its turn.
  * The FOX wins by reducing the geese to GEESE_LOSE (2) or fewer -- at which
    point the geese can no longer trap it.

Termination: geese can shuffle sideways/forward without progress, so a no-progress
counter (plies since the last capture) and a hard ply cap both force a draw.

Moves are ">"-separated cell-id paths ("c,r"). A geese/fox step or a single fox
jump is "from>to"; a fox multi-jump is the full landing chain "from>mid1>mid2".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

GEESE, FOX = 0, 1
GEESE_TOTAL = 15
GEESE_LOSE = 2            # fox wins once the geese are reduced to this many (<=)
PLY_CAP = 400            # hard ply cap -> draw
NO_PROGRESS = 60        # plies since the last capture -> draw

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def _on(c, r):
    if not (0 <= c < 7 and 0 <= r < 7):
        return False
    # the four 2x2 corner blocks are off-board (carves the 7x7 into a plus)
    if c in (0, 1) and r in (0, 1):
        return False
    if c in (5, 6) and r in (0, 1):
        return False
    if c in (0, 1) and r in (5, 6):
        return False
    if c in (5, 6) and r in (5, 6):
        return False
    return True


def _strong(c, r):
    return (c + r) % 2 == 0


def _all_points():
    return [(c, r) for r in range(7) for c in range(7) if _on(c, r)]


POINTS = _all_points()
POINT_SET = set(POINTS)


def _dirs(c, r):
    return ORTHO + DIAG if _strong(c, r) else ORTHO


def _build_adj():
    adj = {}
    for (c, r) in POINTS:
        adj[(c, r)] = frozenset(
            (c + dc, r + dr) for (dc, dr) in _dirs(c, r) if _on(c + dc, r + dr)
        )
    return adj


ADJ = _build_adj()


def _lines():
    """Cosmetic connecting lines (adjacency lives in ADJ). Each line is a 2-point
    polyline in cell-coord space. Diagonals only at strong points."""
    segs = []
    seen = set()
    for (c, r) in POINTS:
        for (nc, nr) in ADJ[(c, r)]:
            key = frozenset(((c, r), (nc, nr)))
            if key in seen:
                continue
            seen.add(key)
            segs.append([[c, r], [nc, nr]])
    return segs


LINES = _lines()

# Geese forward = toward DECREASING row (toward the fox's half). Geese may step to
# any linked point whose row does not increase (forward / sideways / diag-forward).

FOX_START = (3, 3)


def _start_geese():
    geese = set()
    for c in (2, 3, 4):          # the bottom arm (a 3-wide x 2-tall block)
        for r in (5, 6):
            geese.add((c, r))
    for c in range(7):           # the full adjacent row
        if _on(c, 4):
            geese.add((c, 4))
    geese.add((0, 3))            # the two endpoints of the central row
    geese.add((6, 3))
    return geese


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class FGState:
    board: dict = field(default_factory=dict)        # (c,r) -> GEESE/FOX
    to_move: int = GEESE
    geese_left: int = GEESE_TOTAL
    ply: int = 0
    since_cap: int = 0                               # plies since last capture
    winner: Optional[int] = None
    drawn: bool = False


class FoxAndGeese(Game):
    uid = "fox_and_geese"
    name = "Fox and Geese"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {g: GEESE for g in _start_geese()}
        board[FOX_START] = FOX
        return FGState(board=board, to_move=GEESE, geese_left=GEESE_TOTAL)

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _fox_sq(self, board):
        for sq, who in board.items():
            if who == FOX:
                return sq
        return None

    def _goose_steps(self, board):
        """(frm, to) for every legal geese step (no backward)."""
        for sq, who in board.items():
            if who != GEESE:
                continue
            c, r = sq
            for (nc, nr) in ADJ[sq]:
                if (nc, nr) in board:
                    continue
                if nr - r > 0:               # backward / diag-backward forbidden
                    continue
                yield sq, (nc, nr)

    def _fox_steps(self, board):
        fox = self._fox_sq(board)
        if fox is None:
            return
        for to in ADJ[fox]:
            if to not in board:
                yield fox, to

    def _fox_jumps_from(self, board, frm):
        """Single-hop jumps from `frm`: yield (mid, land) along straight lines."""
        c, r = frm
        for (dc, dr) in _dirs(c, r):
            mid = (c + dc, r + dr)
            land = (c + 2 * dc, r + 2 * dr)
            if not _on(*land):
                continue
            # both hops must be marked lines (mid linked to frm and to land)
            if mid not in ADJ[frm] or land not in ADJ[mid]:
                continue
            if board.get(mid) == GEESE and land not in board:
                yield mid, land

    def _fox_jump_paths(self, board):
        """All maximal-prefix jump paths (each a tuple of landing cells); every
        non-empty prefix is itself a legal move (captures not mandatory)."""
        fox = self._fox_sq(board)
        if fox is None:
            return []
        paths = []

        def rec(cur_board, cur_sq, path):
            extended = False
            for mid, land in self._fox_jumps_from(cur_board, cur_sq):
                nb = dict(cur_board)
                del nb[cur_sq]
                del nb[mid]
                nb[land] = FOX
                extended = True
                rec(nb, land, path + [land])
            if path:
                paths.append(tuple(path))

        rec(dict(board), fox, [])
        # de-dup while preserving order
        out, seen = [], set()
        for p in paths:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        if state.to_move == GEESE:
            return [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for (f, t) in self._goose_steps(state.board)]
        fox = self._fox_sq(state.board)
        out = [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for (f, t) in self._fox_steps(state.board)]
        for path in self._fox_jump_paths(state.board):
            seq = [fox] + list(path)
            out.append(">".join(f"{c},{r}" for (c, r) in seq))
        return out

    # ---- apply -------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        cells = [_cell(x) for x in move.split(">")]
        board = dict(state.board)
        geese_left = state.geese_left
        captured = 0
        frm = cells[0]
        who = board.pop(frm)
        for nxt in cells[1:]:
            dc = nxt[0] - frm[0]
            dr = nxt[1] - frm[1]
            if max(abs(dc), abs(dr)) == 2:        # a jump: remove the jumped goose
                mid = (frm[0] + dc // 2, frm[1] + dr // 2)
                if board.get(mid) == GEESE:
                    del board[mid]
                    geese_left -= 1
                    captured += 1
            frm = nxt
        board[cells[-1]] = who

        ply = state.ply + 1
        since_cap = 0 if captured else state.since_cap + 1
        ns = FGState(board=board, to_move=1 - state.to_move, geese_left=geese_left,
                     ply=ply, since_cap=since_cap)
        self._settle(ns)
        return ns

    def _settle(self, ns):
        # fox wins by reducing the geese to the trapping threshold
        if ns.geese_left <= GEESE_LOSE:
            ns.winner = FOX
            return
        if ns.ply >= PLY_CAP or ns.since_cap >= NO_PROGRESS:
            ns.drawn = True
            return
        # the side to move with no legal move: if it's the fox, the geese win
        # (the fox is trapped). The geese, by construction, can essentially always
        # move, but guard the symmetric case anyway.
        if not self._raw_has_move(ns):
            ns.winner = 1 - ns.to_move

    def _raw_has_move(self, state):
        if state.to_move == GEESE:
            for _ in self._goose_steps(state.board):
                return True
            return False
        for _ in self._fox_steps(state.board):
            return True
        return bool(self._fox_jump_paths(state.board))

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        return state.winner is not None or state.drawn

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialise ---------------------------------------------------------
    def serialize(self, state):
        return {
            "board": {f"{c},{r}": v for (c, r), v in state.board.items()},
            "to_move": state.to_move,
            "geese_left": state.geese_left,
            "ply": state.ply,
            "since_cap": state.since_cap,
            "winner": state.winner,
            "drawn": state.drawn,
        }

    def deserialize(self, d):
        return FGState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            geese_left=d["geese_left"],
            ply=d.get("ply", 0),
            since_cap=d.get("since_cap", 0),
            winner=d.get("winner"),
            drawn=d.get("drawn", False),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        cells = move.split(">")
        is_jump = any(
            max(abs(int(cells[i + 1].split(",")[0]) - int(cells[i].split(",")[0])),
                abs(int(cells[i + 1].split(",")[1]) - int(cells[i].split(",")[1]))) == 2
            for i in range(len(cells) - 1)
        )
        who = "F" if state.board.get(_cell(cells[0])) == FOX else "G"
        sep = "x" if is_jump else "-"
        return f"{who} " + sep.join(cells)

    def render(self, state, perspective=None):
        cells = []
        for (c, r) in POINTS:
            s = 0.42
            cells.append({"id": f"{c},{r}",
                          "points": [[c - s, r - s], [c + s, r - s],
                                     [c + s, r + s], [c - s, r + s]]})
        pieces = []
        for (c, r), who in state.board.items():
            pieces.append({"cell": f"{c},{r}", "owner": who,
                           "label": "F" if who == FOX else "G"})
        if state.winner == FOX:
            cap = f"Fox wins (geese reduced to {state.geese_left})"
        elif state.winner == GEESE:
            cap = "Geese win (fox trapped)"
        elif state.drawn:
            cap = "Draw"
        else:
            side = "Geese" if state.to_move == GEESE else "Fox"
            cap = f"{side} to move  ·  geese: {state.geese_left}"
        return {
            "board": {"type": "polygons", "cells": cells, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
