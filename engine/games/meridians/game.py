"""Meridians, by Kanare Kato (2021).

A "line-of-sight" placement + annihilation game on a centerless hexagonal board
tessellated with triangles.  Object: eliminate ALL of the opponent's stones.

Board (standard 6/7 size, the only published "regular" size):
  A hexagon of triangle-grid INTERSECTIONS with two short sides (6 points) and
  four long sides (7 points) -> 114 points total.  In axial cube coords
  (x, y, z) with x+y+z=0, the board is exactly
        x in [-6, 5],  y in [-6, 6],  z = -x-y in [-5, 6].
  Rows (constant y) have widths 6,7,8,9,10,11,12,11,10,9,8,7,6 -- the asymmetry
  (range shifted by 1 on the x/z axes) is what makes it "centerless".  We use
  axial (q=x, r=y) cell ids "q,r".  An interior point has 6 neighbours and lies
  on 3 straight-line families ("meridians"): the q, r and (q+r) axes.

Rules as implemented (official Kanare Kato rules PDF, "Meridians_EN.pdf", 2023):
  * Light (player 0) moves first, then alternate.
  * LINE OF SIGHT: two same-colour stones "see" each other if they lie on one of
    the three grid lines with no OPPONENT stone strictly between them (friendly
    stones in between are fine).
  * PLACEMENT.  Turn 1: any empty point.  Turn 2 onward: an empty point that is
    seen by (on a straight line, no enemy between, from) at least one existing
    friendly stone.  (The turn-2 rule "so that your two stones have a path" is
    just this general line-of-sight rule.)  Passing only when no legal move.
  * PATH (life).  A group is ALIVE iff one of its stones has a straight line of
    one-or-more EMPTY points ending at a stone of a DIFFERENT friendly group
    (i.e. clear line of sight, through empties only, to another friendly group).
  * A turn is:   1. remove ALL of the opponent's dead groups, then
                 2. place one stone.
    (Step 1 is skipped while the opponent has taken fewer than two turns, since
    a lone first stone is never "dead" before it can be paired.)
  * WIN: after the second turn, a player with NO stones at the start of their
    turn loses (their stones were all captured).  Win is an EVENT stored in
    state (the opening looks empty), not a board predicate.

Termination safeguard (NON-ORIGINAL): the published game ends by annihilation /
resignation and has no draw.  To guarantee the engine terminates under random
self-play we add a hard ply cap (PLY_CAP) that ends the game as a DRAW; it is far
beyond any sane real game and never triggers in practice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

LIGHT, DARK = 0, 1  # player 0 = Light (moves first), player 1 = Dark

# The three straight-line families on a triangular grid (each with its opposite):
# q-axis (1,0), r-axis (0,1), and the (q+r)/diagonal axis (1,-1).
_LINE_DIRS = [(1, 0), (0, 1), (1, -1)]
# 6 edge-adjacency neighbours (for grouping).
_NBRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

PLY_CAP = 1000  # non-original draw safeguard (never reached in real play)


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


@lru_cache(maxsize=None)
def _board_cells(size: int) -> tuple:
    """All on-board axial (q, r) points for a board of the given size.

    size = the larger side length (long sides = `size` points, short sides =
    `size - 1`).  Standard board is size 7 -> 114 points.  In cube coords the
    box is x in [-(size-1), size-2], y in [-(size-1), size-1], z in [-(size-2), size-1].
    """
    n = size - 1
    out = []
    for q in range(-n, n):              # x in [-n, n-1]
        for r in range(-n, n + 1):      # y in [-n, n]
            z = -q - r
            if -n <= q <= n - 1 and -n <= r <= n and -(n - 1) <= z <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_board_cells(size))


@dataclass
class MeridiansState:
    size: int = 7                                 # long-side length (standard 7)
    board: dict = field(default_factory=dict)     # (q, r) -> 0/1
    to_move: int = LIGHT
    winner: Optional[int] = None
    turns: tuple = (0, 0)                          # completed placement turns per player
    last: Optional[tuple] = None
    ply: int = 0


# --------------------------------------------------------------------------- #
#  Geometry helpers
# --------------------------------------------------------------------------- #
def _group(board: dict, start: tuple, player: int) -> set:
    """Connected like-coloured component (edge adjacency) containing `start`."""
    if board.get(start) != player:
        return set()
    seen, stack = {start}, [start]
    while stack:
        cq, cr = stack.pop()
        for dq, dr in _NBRS:
            nb = (cq + dq, cr + dr)
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return seen


def _all_groups(board: dict, player: int) -> list:
    seen = set()
    groups = []
    for cell, p in board.items():
        if p == player and cell not in seen:
            g = _group(board, cell, player)
            seen |= g
            groups.append(g)
    return groups


def _group_id_map(board: dict, player: int) -> dict:
    """cell -> group index, for that player's stones."""
    out = {}
    for i, g in enumerate(_all_groups(board, player)):
        for c in g:
            out[c] = i
    return out


def _sees_friendly(board: dict, cell: tuple, player: int, size: int) -> bool:
    """PLACEMENT line-of-sight: from empty `cell`, along any of the 3 line
    families, is there a friendly stone reachable with no OPPONENT stone before
    it?  (Friendly stones in between are allowed -- the first stone hit settles
    it: if it's friendly -> visible; if it's enemy -> blocked that direction.)"""
    opp = 1 - player
    on = _cell_set(size)
    for dq, dr in _LINE_DIRS:
        for sign in (1, -1):
            sq, sr = dq * sign, dr * sign
            q, r = cell[0] + sq, cell[1] + sr
            while (q, r) in on:
                v = board.get((q, r))
                if v == player:
                    return True
                if v == opp:
                    break          # opponent blocks this direction
                q += sq
                r += sr
    return False


def _has_path(board: dict, cell: tuple, player: int, size: int, gid: dict) -> bool:
    """LIFE line-of-sight from a stone at `cell`: along any line family, the run
    of EMPTY points ends at a stone of a DIFFERENT friendly group."""
    on = _cell_set(size)
    my_group = gid.get(cell)
    for dq, dr in _LINE_DIRS:
        for sign in (1, -1):
            sq, sr = dq * sign, dr * sign
            q, r = cell[0] + sq, cell[1] + sr
            steps = 0
            while (q, r) in on:
                v = board.get((q, r))
                if v is None:
                    steps += 1
                    q += sq
                    r += sr
                    continue
                # first non-empty point on this ray:
                if v == player and steps >= 1 and gid.get((q, r)) != my_group:
                    return True
                break  # any stone (enemy, or friendly with steps==0/same group) blocks
    return False


def _dead_groups(board: dict, player: int, size: int) -> list:
    """All groups of `player` with NO path to a different friendly group."""
    groups = _all_groups(board, player)
    gid = _group_id_map(board, player)
    dead = []
    for g in groups:
        if not any(_has_path(board, c, player, size, gid) for c in g):
            dead.append(g)
    return dead


def _remove_dead(board: dict, player: int, size: int) -> dict:
    """Return a copy of `board` with all of `player`'s dead groups removed."""
    dead = _dead_groups(board, player, size)
    if not dead:
        return board
    drop = set().union(*dead)
    return {c: v for c, v in board.items() if c not in drop}


# --------------------------------------------------------------------------- #
#  Game
# --------------------------------------------------------------------------- #
class Meridians(Game):
    uid = "meridians"
    name = "Meridians"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> MeridiansState:
        size = int((options or {}).get("size", 7))
        return MeridiansState(size=size)

    def current_player(self, s: MeridiansState) -> int:
        return s.to_move

    # --- the board the active player faces AFTER capturing enemy dead groups --
    def _board_after_capture(self, s: MeridiansState) -> dict:
        """Step 1 of the active player's turn: remove the OPPONENT's dead groups.
        Skipped while the opponent has taken fewer than two turns (a lone first
        stone is never dead before it can be paired)."""
        opp = 1 - s.to_move
        if s.turns[opp] < 2:
            return s.board
        return _remove_dead(s.board, opp, s.size)

    def _placements(self, s: MeridiansState, board: dict) -> list[str]:
        on = _cell_set(s.size)
        mine = s.turns[s.to_move]
        empties = [c for c in on if c not in board]
        if mine == 0:
            cells = empties                       # first stone: anywhere
        else:
            cells = [c for c in empties
                     if _sees_friendly(board, c, s.to_move, s.size)]
        return [f"{q},{r}" for (q, r) in cells]

    def legal_moves(self, s: MeridiansState) -> list[str]:
        if self.is_terminal(s):
            return []
        board = self._board_after_capture(s)
        # If the capture wiped out the mover (can't happen: we remove the
        # OPPONENT's dead groups) -- guard for completeness.
        moves = self._placements(s, board)
        if not moves:
            return ["pass"]   # no legal placement -> forced pass
        return moves

    def apply_move(self, s: MeridiansState, move: str, rng=None) -> MeridiansState:
        if self.is_terminal(s):
            raise ValueError("game is over")
        mover = s.to_move
        opp = 1 - mover

        # Step 1 of the turn: remove the opponent's dead groups (persisted into
        # the stored board, exactly as the physical procedure does).
        board = dict(self._board_after_capture(s))
        turns = list(s.turns)

        if move == "pass":
            # No legal placement -> the turn is just the capture step.
            pass
        else:
            q, r = _cell(move)
            if (q, r) not in _cell_set(s.size) or (q, r) in board:
                raise ValueError(f"illegal placement {move!r}")
            board[(q, r)] = mover                 # Step 2: place one stone.
            turns[mover] += 1

        ns = MeridiansState(size=s.size, board=board, to_move=opp,
                            winner=None, turns=tuple(turns),
                            last=(s.last if move == "pass" else (q, r)),
                            ply=s.ply + 1)
        return self._finalize(ns, captured_player=opp)

    def _finalize(self, s: MeridiansState, captured_player: int) -> MeridiansState:
        """Decide the game end for the state that is about to be presented to
        `s.to_move` (== captured_player): the loss/annihilation rule is "after
        the second turn, a player with NO stones at the start of their turn
        loses".  The opponent has just (in apply_move) removed this player's dead
        groups as their capture step would, so we check the same removal here to
        surface the WIN as an explicit event."""
        nxt = s.to_move           # the player about to move (== captured_player)
        other = 1 - nxt
        if s.turns[0] >= 2 and s.turns[1] >= 2:
            # The board this player will face after the opponent's capture step.
            faced = _remove_dead(s.board, nxt, s.size)
            if not any(v == nxt for v in faced.values()):
                # All of this player's stones were captured -> they lose now.
                return MeridiansState(size=s.size, board=faced, to_move=nxt,
                                      winner=other, turns=s.turns,
                                      last=s.last, ply=s.ply)
        if s.ply >= PLY_CAP:
            # Non-original draw safeguard (never reached in real play).
            return MeridiansState(size=s.size, board=s.board, to_move=nxt,
                                  winner=-1, turns=s.turns, last=s.last, ply=s.ply)
        return s

    def is_terminal(self, s: MeridiansState) -> bool:
        return s.winner is not None

    def returns(self, s: MeridiansState) -> list[float]:
        if s.winner == LIGHT:
            return [1.0, -1.0]
        if s.winner == DARK:
            return [-1.0, 1.0]
        return [0.0, 0.0]   # draw (only via the non-original ply cap)

    # --- serialization -----------------------------------------------------
    def serialize(self, s: MeridiansState) -> dict:
        return {
            "size": s.size,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "turns": list(s.turns),
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> MeridiansState:
        last = d.get("last")
        return MeridiansState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            turns=tuple(d.get("turns", (0, 0))),
            last=(_cell(last) if last else None),
            ply=d.get("ply", len(d["board"])),
        )

    def describe_move(self, s: MeridiansState, move: str) -> str:
        if move == "pass":
            return "pass (no legal placement)"
        return move

    # --- render ------------------------------------------------------------
    def render(self, s: MeridiansState, perspective=None) -> dict:
        import math
        cells_xy = _board_cells(s.size)
        SQ3 = math.sqrt(3.0)

        def px(q, r):
            return (q + r / 2.0, r * SQ3 / 2.0)

        rad = 0.30
        poly_cells = []
        coord = {}
        for (q, r) in cells_xy:
            cx, cy = px(q, r)
            coord[(q, r)] = (cx, cy)
            pts = [[cx + rad * math.cos(math.radians(60 * i - 30)),
                    cy + rad * math.sin(math.radians(60 * i - 30))]
                   for i in range(6)]
            poly_cells.append({"id": f"{q},{r}", "points": pts})

        # Draw the three meridian line families as full chords across the board.
        on = _cell_set(s.size)
        lines = []
        for dq, dr in _LINE_DIRS:
            seen_starts = set()
            for (q, r) in cells_xy:
                # walk back to the start of this line
                bq, br = q - dq, r - dr
                if (bq, br) in on:
                    continue
                if (q, r) in seen_starts:
                    continue
                # walk forward collecting the whole maximal line
                pts = []
                cq, cr = q, r
                while (cq, cr) in on:
                    seen_starts.add((cq, cr))
                    pts.append(list(coord[(cq, cr)]))
                    cq += dq
                    cr += dr
                if len(pts) >= 2:
                    lines.append(pts + ["#caa472"])

        pieces = [{"cell": f"{q},{r}", "owner": p} for (q, r), p in s.board.items()]
        highlights = []
        if s.last is not None and s.last in s.board:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})

        names = {LIGHT: "Light", DARK: "Dark"}
        if s.winner == LIGHT or s.winner == DARK:
            caption = f"{names[s.winner]} wins (annihilation)"
        elif s.winner == -1:
            caption = "Draw (ply cap)"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": poly_cells, "lines": lines},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
