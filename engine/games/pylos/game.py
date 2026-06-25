"""Pylos (David G. Royffe, Gigamic) -- the pyramid stacking game.

Two players share a pool of 30 spheres (15 each, one colour per player) and
build a 4-level pyramid on a 4x4 base. On your turn you make ONE of:

  * PLACE a sphere from your reserve onto any empty valid position, or
  * RAISE one of your own FREE spheres (nothing on top of it) up to a higher,
    empty, valid position.

A position is VALID iff it is empty AND its support is present: a level-0 base
square is always supportable; a level L>=1 position needs the 2x2 block of four
spheres directly beneath it to be fully present.

THE SQUARE (take-back).  If the sphere you just placed/raised COMPLETES a 2x2
square of four spheres all of YOUR colour (at any level), you MAY then take back
1 or 2 of your own spheres that are currently FREE, returning them to your
reserve (0 is allowed -- the take-back is optional). The take-back is modelled as
a multi-action turn: the same player keeps the move and picks free own spheres
one at a time (move ``"take:L,c,r"``) up to two, ending the turn with ``"done"``.

WIN.  The first player to put a sphere on the APEX (the single level-3 position)
wins immediately -- whether by placing from reserve or by raising. A player who
cannot move (out of reserve and no legal raise) loses.

TERMINATION.  Raising + take-backs recycle spheres, so play could in principle
cycle. A hard ply cap (PLY_CAP) ends an over-long game as a draw. Random playouts
terminate well within the cap and reach apex wins.

Board representation: ``board["L,c,r"] = owner`` for each occupied position, plus
``reserve = [n0, n1]`` reserve counts. Positions: level L has a (4-L)x(4-L) grid;
position (L,c,r) sits at pixel ((c+0.5*L),(r+0.5*L)); its supporters (L>=1) are the
four level-(L-1) positions (c,r),(c+1,r),(c,r+1),(c+1,r+1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BASE = 4                     # 4x4 base
NLEVELS = 4                  # levels 0..3
BALLS_PER_PLAYER = 15        # 30 total
PLY_CAP = 300                # hard draw cap (recycling could otherwise loop)


def _pos(s):
    L, c, r = s.split(",")
    return (int(L), int(c), int(r))


def _key(L, c, r):
    return f"{L},{c},{r}"


@lru_cache(maxsize=None)
def _all_positions():
    """All 30 positions as (L,c,r), level 0 first (16+9+4+1)."""
    out = []
    for L in range(NLEVELS):
        n = BASE - L
        for r in range(n):
            for c in range(n):
                out.append((L, c, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _supporters(L, c, r):
    """The four level-(L-1) positions a level-L (L>=1) sphere rests on, or ()."""
    if L == 0:
        return ()
    return ((L - 1, c, r), (L - 1, c + 1, r),
            (L - 1, c, r + 1), (L - 1, c + 1, r + 1))


@lru_cache(maxsize=None)
def _squares():
    """Every 2x2 square (a tuple of four positions) at any level.

    A square at level L is the four positions (L,c,r),(L,c+1,r),(L,c,r+1),
    (L,c+1,r+1) for each top-left (c,r). Returned as a tuple of 4-tuples."""
    out = []
    for L in range(NLEVELS):
        n = BASE - L
        for r in range(n - 1):
            for c in range(n - 1):
                out.append(((L, c, r), (L, c + 1, r),
                            (L, c, r + 1), (L, c + 1, r + 1)))
    return tuple(out)


@lru_cache(maxsize=None)
def _squares_containing(pos):
    """The 2x2 squares that include position ``pos``."""
    return tuple(sq for sq in _squares() if pos in sq)


APEX = (3, 0, 0)


@dataclass
class PylosState:
    board: dict = field(default_factory=dict)         # "L,c,r" -> owner 0/1
    reserve: list = field(default_factory=lambda: [BALLS_PER_PLAYER,
                                                    BALLS_PER_PLAYER])
    to_move: int = 0
    winner: object = None                              # None / 0 / 1 / "draw"
    ply: int = 0                                       # full turns elapsed
    # take-back sub-turn (None unless a square was just completed):
    pending: bool = False                              # awaiting take-back / done
    taken: int = 0                                     # how many taken back so far
    last: Optional[str] = None                         # last placed/raised pos id


class Pylos(Game):
    uid = "pylos"
    name = "Pylos"

    @property
    def num_players(self):
        return 2

    # ---- helpers -----------------------------------------------------------
    def _supported(self, board, L, c, r):
        """Is position (L,c,r) supportable (all four supporters present)?"""
        if L == 0:
            return True
        return all(_key(*s) in board for s in _supporters(L, c, r))

    def _is_free(self, board, pos):
        """A sphere is FREE iff no sphere rests directly on top of it.

        Position (L,c,r) supports up to four level-(L+1) positions; it is free
        iff none of those are occupied."""
        L, c, r = pos
        for (nc, nr) in ((c - 1, r - 1), (c, r - 1), (c - 1, r), (c, r)):
            if 0 <= nc < BASE - (L + 1) and 0 <= nr < BASE - (L + 1):
                if _key(L + 1, nc, nr) in board:
                    return False
        return True

    def _valid_targets(self, board):
        """Empty positions whose support is present (place/raise destinations)."""
        out = []
        for (L, c, r) in _all_positions():
            if _key(L, c, r) in board:
                continue
            if self._supported(board, L, c, r):
                out.append((L, c, r))
        return out

    def _completes_square(self, board, mover, pos):
        """True iff ``pos`` (just filled by ``mover``) completes a same-colour 2x2."""
        for sq in _squares_containing(pos):
            if all(board.get(_key(*p)) == mover for p in sq):
                return True
        return False

    # ---- core --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        return PylosState()

    def current_player(self, state):
        return state.to_move

    def legal_moves(self, state):
        if state.winner is not None:
            return []
        if state.pending:
            # Take-back sub-turn: pick a free own sphere, or stop.
            moves = ["done"]
            for pos, owner in state.board.items():
                if owner != state.to_move:
                    continue
                if self._is_free(state.board, _pos(pos)):
                    moves.append(f"take:{pos}")
            return moves

        mover = state.to_move
        targets = self._valid_targets(state.board)
        moves = []
        # PLACE from reserve.
        if state.reserve[mover] > 0:
            for (L, c, r) in targets:
                moves.append(_key(L, c, r))
        # RAISE one of your own free spheres up to a higher valid position.
        own_free = [p for p in _all_positions()
                    if state.board.get(_key(*p)) == mover
                    and self._is_free(state.board, p)]
        for src in own_free:
            sL = src[0]
            for (L, c, r) in targets:
                if L <= sL:
                    continue                       # must go UP a level
                # the moving sphere may not be one of the destination supporters
                if src in _supporters(L, c, r):
                    continue
                moves.append(f"{_key(*src)}>{_key(L, c, r)}")
        return moves

    def apply_move(self, state, move, rng=None):
        if state.winner is not None:
            raise ValueError("game over")
        mover = state.to_move

        # ---- take-back sub-turn ------------------------------------------
        if state.pending:
            if move == "done":
                ns = PylosState(board=dict(state.board),
                                reserve=list(state.reserve),
                                to_move=1 - mover, ply=state.ply + 1,
                                last=state.last)
                self._maybe_end(ns)
                return ns
            if not move.startswith("take:"):
                raise ValueError(f"illegal take-back {move!r}")
            pos = move[len("take:"):]
            if state.board.get(pos) != mover or not self._is_free(state.board, _pos(pos)):
                raise ValueError(f"cannot take back {pos!r}")
            board = dict(state.board)
            del board[pos]
            reserve = list(state.reserve)
            reserve[mover] += 1
            taken = state.taken + 1
            if taken >= 2:                      # max two -> turn ends
                ns = PylosState(board=board, reserve=reserve,
                                to_move=1 - mover, ply=state.ply + 1,
                                last=state.last)
                self._maybe_end(ns)
                return ns
            return PylosState(board=board, reserve=reserve, to_move=mover,
                              ply=state.ply, last=state.last,
                              pending=True, taken=taken)

        # ---- a placing / raising move ------------------------------------
        if ">" in move:                          # RAISE
            src_s, dst_s = move.split(">")
            src, dst = _pos(src_s), _pos(dst_s)
            if state.board.get(src_s) != mover:
                raise ValueError(f"not your sphere: {src_s}")
            if not self._is_free(state.board, src):
                raise ValueError(f"sphere not free: {src_s}")
            if dst[0] <= src[0]:
                raise ValueError("raise must go up a level")
            board = dict(state.board)
            del board[src_s]
            if dst_s in board or not self._supported(board, *dst):
                raise ValueError(f"invalid destination {dst_s}")
            if src in _supporters(*dst):
                raise ValueError("sphere supports its own destination")
            board[dst_s] = mover
            placed = dst
        else:                                    # PLACE from reserve
            if state.reserve[mover] <= 0:
                raise ValueError("no spheres in reserve")
            dst = _pos(move)
            if move in state.board or not self._supported(state.board, *dst):
                raise ValueError(f"invalid placement {move}")
            board = dict(state.board)
            board[move] = mover
            placed = dst

        reserve = list(state.reserve)
        if ">" not in move:
            reserve[mover] -= 1

        # APEX win (place or raise onto the top).
        if placed == APEX:
            return PylosState(board=board, reserve=reserve, to_move=mover,
                              winner=mover, ply=state.ply + 1, last=_key(*placed))

        # Square completed by the just-placed sphere -> take-back sub-turn.
        if self._completes_square(board, mover, placed):
            ns = PylosState(board=board, reserve=reserve, to_move=mover,
                            ply=state.ply, last=_key(*placed),
                            pending=True, taken=0)
            # If nothing is free to take back, the sub-turn is empty; still
            # offer "done" so the turn can end (legal_moves always has "done").
            return ns

        ns = PylosState(board=board, reserve=reserve, to_move=1 - mover,
                        ply=state.ply + 1, last=_key(*placed))
        # Draw cap, and loss-by-no-move (out of reserve + no raise).
        self._maybe_end(ns)
        return ns

    def _maybe_end(self, ns):
        if ns.winner is not None:
            return
        if ns.ply >= PLY_CAP:
            ns.winner = "draw"
            return
        if not self.legal_moves(ns):
            # The player to move cannot act -> they lose.
            ns.winner = 1 - ns.to_move

    def is_terminal(self, state):
        return state.winner is not None

    def returns(self, state):
        if state.winner in (None, "draw"):
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialization -----------------------------------------------------
    def serialize(self, state):
        return {
            "board": dict(state.board),
            "reserve": list(state.reserve),
            "to_move": state.to_move,
            "winner": state.winner,
            "ply": state.ply,
            "pending": state.pending,
            "taken": state.taken,
            "last": state.last,
        }

    def deserialize(self, d):
        return PylosState(
            board=dict(d["board"]),
            reserve=list(d["reserve"]),
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            pending=d.get("pending", False),
            taken=d.get("taken", 0),
            last=d.get("last"),
        )

    def describe_move(self, state, move):
        if move == "done":
            return "done (end turn)"
        if move.startswith("take:"):
            return f"take back {move[len('take:'):]}"
        if ">" in move:
            return f"raise {move.replace('>', '->')}"
        return f"place {move}"

    # ---- render ------------------------------------------------------------
    def render(self, state, perspective=None):
        # Order cells level 0 -> 3 so higher levels draw ON TOP (the stacking).
        cells = []
        tints = {}
        # faint per-level tints so the tiers read.
        level_tint = ["#2c3340", "#343c4c", "#3e4658", "#4a5468"]
        # cell half-size shrinks slightly per level.
        half = [0.46, 0.40, 0.34, 0.28]
        for (L, c, r) in _all_positions():
            cx = c + 0.5 * L
            cy = r + 0.5 * L
            h = half[L]
            cells.append({
                "id": _key(L, c, r),
                "points": [[round(cx - h, 3), round(cy - h, 3)],
                           [round(cx + h, 3), round(cy - h, 3)],
                           [round(cx + h, 3), round(cy + h, 3)],
                           [round(cx - h, 3), round(cy + h, 3)]],
            })
            if _key(L, c, r) not in state.board:
                tints[_key(L, c, r)] = level_tint[L]

        pieces = [{"cell": pos, "owner": owner}
                  for pos, owner in state.board.items()]

        highlights = []
        if state.last and state.last in state.board:
            highlights.append({"cell": state.last, "kind": "last-move"})

        names = {0: "Dark", 1: "Light"}
        r0, r1 = state.reserve
        supply = f"reserve  {names[0]} {r0} | {names[1]} {r1}"
        if state.winner == "draw":
            cap = f"Draw (ply cap) — {supply}"
        elif state.winner is not None:
            cap = f"{names[state.winner]} wins (reached the apex) — {supply}"
        elif state.pending:
            cap = (f"{names[state.to_move]} made a square — take back "
                   f"{2 - state.taken} more free sphere(s) or 'done' — {supply}")
        else:
            cap = f"{names[state.to_move]} to move (place or raise) — {supply}"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
