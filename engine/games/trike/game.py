"""Trike (Alek Erickson, 2020) -- an elegant, draw-free combinatorial game on a
triangle of hexagons, played with a single SHARED NEUTRAL pawn.

Board
-----
An equilateral triangle of hexagonal cells with ``size`` hexes on a side
(default 11; published sizes run 6..12, we expose 7/9/11/13). Cells use the
triangular (row, col) layout shared with the Game of Y: ``row`` in ``0..size-1``
and ``col`` in ``0..row`` (row 0 is the apex). Each cell touches up to six
neighbours (the six hex directions). Rendered as `polygons` (hexagons).

Turn
----
A single neutral pawn sits on the board (it is owned by NO player). On a turn the
active player:
  1. slides the pawn in a straight line along one of the six hex directions, any
     number of cells, over EMPTY cells only (it may not jump over, or land on, an
     occupied cell), landing on an empty cell;
  2. drops a stone of THEIR OWN colour on that landing cell; the pawn then rests
     on top of that stone.
Passing is not allowed. Every move places one stone on a previously empty cell,
so the board strictly fills and the game terminates in at most (#cells) plies.

Opening + pie rule
------------------
The host (player 0 / white) opens by placing a white stone on ANY cell and the
pawn on top of it (modelled as a normal "destination cell" move from the empty
board). The guest (player 1 / blue) then either plays normally as blue, OR
invokes the pie rule via the ``"swap"`` move: the lone opening stone is recoloured
to the guest and the turn passes back, so the guest effectively takes over the
host's opening (mirrors the Game of Y's swap). After that the game alternates.

End + scoring
-------------
The game ends the instant the pawn is TRAPPED -- every one of the six lines out of
the pawn's cell is immediately blocked by an occupied neighbour (or the board
edge), so there is no empty cell to move to. Score = the number of stones a player
OWNS among the pawn's final cell (the stone directly under the pawn always counts)
plus its up-to-six adjacent cells. The higher score wins. Trike is provably
draw-free; we nonetheless guard a tie defensively as a draw (it cannot arise in
legal play).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLUE = 0, 1
# the six hex directions in the triangular (row, col) layout (shared with Y)
DIRS = [(0, -1), (0, 1), (-1, -1), (-1, 0), (1, 0), (1, 1)]


def _cell(s: str):
    r, c = s.split(",")
    return int(r), int(c)


def _cid(p) -> str:
    return f"{p[0]},{p[1]}"


@dataclass
class TrikeState:
    size: int = 11
    board: dict = field(default_factory=dict)   # (row, col) -> owner (0/1)
    pawn: Optional[tuple] = None                 # (row, col) of the neutral pawn, or None pre-opening
    to_move: int = WHITE
    ply: int = 0


class Trike(Game):
    uid = "trike"
    name = "Trike"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> TrikeState:
        size = int((options or {}).get("size", 11))
        return TrikeState(size=size)

    # ---- geometry ---------------------------------------------------------
    @staticmethod
    def _on(size: int, r: int, c: int) -> bool:
        return 0 <= r < size and 0 <= c <= r

    def _cells(self, size: int):
        return [(r, c) for r in range(size) for c in range(r + 1)]

    def _slide_targets(self, s: TrikeState):
        """Empty cells the pawn can slide to: in each of the 6 directions, walk over
        empty cells and yield each, stopping at the first occupied cell or edge."""
        pr, pc = s.pawn
        for dr, dc in DIRS:
            r, c = pr + dr, pc + dc
            while self._on(s.size, r, c) and (r, c) not in s.board:
                yield (r, c)
                r += dr
                c += dc

    # ---- core game --------------------------------------------------------
    def current_player(self, s: TrikeState) -> int:
        return s.to_move

    def _raw_moves(self, s: TrikeState) -> list[str]:
        if s.pawn is None:
            # opening: host places stone + pawn on any cell
            return [_cid(p) for p in self._cells(s.size)]
        out = [_cid(t) for t in self._slide_targets(s)]
        if s.ply == 1 and len(s.board) == 1:
            out.append("swap")   # pie rule for the guest's first turn
        return out

    def is_terminal(self, s: TrikeState) -> bool:
        if s.pawn is None:
            return False
        # trapped iff no empty neighbour in any direction (one step suffices)
        return not any(
            self._on(s.size, s.pawn[0] + dr, s.pawn[1] + dc)
            and (s.pawn[0] + dr, s.pawn[1] + dc) not in s.board
            for dr, dc in DIRS
        )

    def legal_moves(self, s: TrikeState) -> list[str]:
        return [] if self.is_terminal(s) else self._raw_moves(s)

    def apply_move(self, s: TrikeState, move: str, rng=None) -> TrikeState:
        board = dict(s.board)
        if move == "swap":
            sq = next(iter(board))
            board[sq] = s.to_move           # recolour the lone opening stone to the swapper
            return TrikeState(size=s.size, board=board, pawn=s.pawn,
                              to_move=1 - s.to_move, ply=s.ply + 1)
        to = _cell(move)
        board[to] = s.to_move               # drop the mover's stone on the landing cell
        return TrikeState(size=s.size, board=board, pawn=to,
                          to_move=1 - s.to_move, ply=s.ply + 1)

    # ---- scoring ----------------------------------------------------------
    def _scores(self, s: TrikeState) -> tuple:
        """(#stones owned by white, #stones owned by blue) on the pawn's cell + its
        adjacent cells."""
        pr, pc = s.pawn
        cells = [(pr, pc)] + [(pr + dr, pc + dc) for dr, dc in DIRS]
        w = b = 0
        for cell in cells:
            owner = s.board.get(cell)
            if owner == WHITE:
                w += 1
            elif owner == BLUE:
                b += 1
        return w, b

    def returns(self, s: TrikeState) -> list[float]:
        if not self.is_terminal(s):
            return [0.0, 0.0]
        w, b = self._scores(s)
        if w > b:
            return [1.0, -1.0]
        if b > w:
            return [-1.0, 1.0]
        return [0.0, 0.0]   # draw-free in practice; defensive only

    # ---- serialization ----------------------------------------------------
    def serialize(self, s: TrikeState) -> dict:
        return {
            "size": s.size,
            "board": {_cid(p): v for p, v in s.board.items()},
            "pawn": _cid(s.pawn) if s.pawn is not None else None,
            "to_move": s.to_move,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> TrikeState:
        return TrikeState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            pawn=_cell(d["pawn"]) if d.get("pawn") is not None else None,
            to_move=d["to_move"],
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: TrikeState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        who = "W" if s.to_move == WHITE else "B"
        if s.pawn is None:
            return f"{who} open {move}"
        return f"{who} {move}"

    # ---- presentation -----------------------------------------------------
    @staticmethod
    def _hex(cx, cy, rad):
        import math
        pts = []
        for k in range(6):
            a = math.radians(60 * k + 30)
            pts.append([round(cx + rad * math.cos(a), 3), round(cy + rad * math.sin(a), 3)])
        return pts

    def render(self, s: TrikeState, perspective=None) -> dict:
        import math
        S = 10.0
        rad = S * 0.62
        cells = []
        for (r, c) in self._cells(s.size):
            cx = S * (c - r / 2.0) * math.sqrt(3)
            cy = S * 1.5 * r
            cells.append({"id": _cid((r, c)), "points": self._hex(cx, cy, rad)})

        pieces = [{"cell": _cid(p), "owner": v} for p, v in s.board.items()]
        highlights = []
        if s.pawn is not None:
            # the neutral pawn: a labelled marker over its stone (owner 2 = neutral colour)
            pieces.append({"cell": _cid(s.pawn), "owner": 2, "label": "P", "shape": "ring"})
            highlights.append({"cell": _cid(s.pawn), "kind": "last-move"})

        names = {WHITE: "White", BLUE: "Blue"}
        if self.is_terminal(s):
            w, b = self._scores(s)
            if w > b:
                cap = f"White wins {w}-{b}"
            elif b > w:
                cap = f"Blue wins {b}-{w}"
            else:
                cap = f"Draw {w}-{b}"
        elif s.pawn is None:
            cap = "White to open (place stone + pawn)"
        else:
            cap = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
