"""Pex — Hex on Marjorie Rice's convex-pentagon tiling (David J. Bush, 2008).

Pex is a member of the Hex/connection family. It is played on a rhombus of
CONGRUENT CONVEX PENTAGONS rather than hexagons: specifically Marjorie Rice's
"type 11" pentagonal tiling (one of the 15 known monohedral convex-pentagon
tilings). David Bush picked type 11 because it satisfies two properties that
carry the Hex no-draw theorem over to pentagons:

  1. No vertex has more than three edges meeting at it (the tiling is trivalent),
     so its dual is a triangulation — a filled board can never be a draw.
  2. It is topologically distinct from a hexagonal grid: half the interior cells
     touch SEVEN neighbours (drawn YELLOW) and the other half touch only FIVE
     (drawn GREEN).

Rules are exactly Hex:
  * Players alternate placing one stone of their colour on any empty cell.
  * RED (player 0) wins by connecting the TOP and BOTTOM board edges with an
    unbroken chain of red stones; BLUE (player 1) connects LEFT and RIGHT.
  * A famous theorem (which type 11 preserves) guarantees NO DRAWS: once the
    board fills, exactly one player has connected — so play always terminates
    (<= 128 placements on the canonical 8x8 board).
  * PIE RULE: the second player, on their first turn, may "swap" instead of
    placing — taking over the first player's colour/opening. This equalises the
    first-move advantage.

The board itself (128 pentagons, their adjacency graph, the pentagon polygons
for rendering, and which cells lie on each of the four coloured edges) was
reconstructed directly from igGameCenter's official 8x8 Pex board image and is
stored in board.json. Cell ids are the official-style labels: a column letter
A-H, a row number 1-8, and a suffix Y (yellow / 7-neighbour) or G (green /
5-neighbour) — e.g. "D4Y". A move is a single cell id (a placement), or the
literal "swap".
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1

_BOARD_PATH = os.path.join(os.path.dirname(__file__), "board.json")
with open(_BOARD_PATH, "r", encoding="utf-8") as _f:
    _BOARD = json.load(_f)

# Static board data (shared, immutable).
CELLS = _BOARD["cells"]                       # [{id, t, pts}]
CELL_IDS = [c["id"] for c in CELLS]
ADJ = {cid: tuple(ns) for cid, ns in _BOARD["adj"].items()}
TERRAIN = {c["id"]: c["t"] for c in CELLS}    # id -> "Y" | "G"
_E = _BOARD["edges"]
TOP, BOTTOM = frozenset(_E["top"]), frozenset(_E["bottom"])
LEFT, RIGHT = frozenset(_E["left"]), frozenset(_E["right"])
# RED connects top<->bottom, BLUE connects left<->right.
GOAL = {RED: (TOP, BOTTOM), BLUE: (LEFT, RIGHT)}


def _connects(board: dict, colour: int) -> bool:
    """Does `colour` link its two opposite edges through its own stones?"""
    a_edge, b_edge = GOAL[colour]
    starts = [c for c in a_edge if board.get(c) == colour]
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if cur in b_edge:
            return True
        for nb in ADJ[cur]:
            if nb not in seen and board.get(nb) == colour:
                seen.add(nb)
                stack.append(nb)
    return False


@dataclass
class PexState:
    board: dict = field(default_factory=dict)   # cell id -> colour (RED/BLUE)
    to_move: int = 0                            # seat index to move
    red_seat: int = 0                           # which seat plays RED (flips on swap)
    winner: Optional[int] = None                # winning COLOUR (RED/BLUE)
    last_move: Optional[str] = None
    ply: int = 0

    def colour_of_seat(self, seat: int) -> int:
        return RED if seat == self.red_seat else BLUE


class Pex(Game):
    name = "Pex"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> PexState:
        return PexState()

    def current_player(self, s: PexState) -> int:
        return s.to_move

    def _swap_available(self, s: PexState) -> bool:
        # Pie rule: offered to the second seat on its very first action.
        return s.ply == 1 and s.winner is None

    def legal_moves(self, s: PexState) -> list[str]:
        if s.winner is not None:
            return []
        moves = [c for c in CELL_IDS if c not in s.board]
        if self._swap_available(s):
            moves.append("swap")
        return moves

    def apply_move(self, s: PexState, move: str, rng=None) -> PexState:
        if move == "swap":
            if not self._swap_available(s):
                raise ValueError("swap is not available")
            # The second player takes over the opening: they become RED (owning
            # the lone first stone), the opener becomes BLUE, and the opener is
            # back on the move. Colours of stones on the board are unchanged.
            return PexState(
                board=dict(s.board),
                to_move=1 - s.to_move,
                red_seat=s.to_move,          # swapping seat now plays RED
                winner=None,
                last_move="swap",
                ply=s.ply + 1,
            )

        if move not in ADJ:
            raise ValueError(f"unknown cell {move!r}")
        if move in s.board:
            raise ValueError(f"cell {move!r} is occupied")
        colour = s.colour_of_seat(s.to_move)
        board = dict(s.board)
        board[move] = colour
        winner = colour if _connects(board, colour) else None
        return PexState(
            board=board,
            to_move=1 - s.to_move,
            red_seat=s.red_seat,
            winner=winner,
            last_move=move,
            ply=s.ply + 1,
        )

    def is_terminal(self, s: PexState) -> bool:
        return s.winner is not None

    def returns(self, s: PexState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]
        win_seat = s.red_seat if s.winner == RED else 1 - s.red_seat
        return [1.0 if p == win_seat else -1.0 for p in range(2)]

    def serialize(self, s: PexState) -> dict:
        return {
            "board": dict(s.board),
            "to_move": s.to_move,
            "red_seat": s.red_seat,
            "winner": s.winner,
            "last_move": s.last_move,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> PexState:
        return PexState(
            board=dict(d["board"]),
            to_move=d["to_move"],
            red_seat=d.get("red_seat", 0),
            winner=d["winner"],
            last_move=d.get("last_move"),
            ply=d.get("ply", len(d["board"])),
        )

    def describe_move(self, s: PexState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        return move

    def render(self, s: PexState, perspective=None) -> dict:
        names = {RED: "Red", BLUE: "Blue"}
        # Terrain + edge tints: green/yellow interior, edge cells tinted toward
        # their owning colour so the goal borders are visible.
        tints = {}
        for cid in CELL_IDS:
            tints[cid] = "#fffca8" if TERRAIN[cid] == "Y" else "#8ff5c0"
        for cid in TOP | BOTTOM:
            tints[cid] = "#e79a9a"      # red edge
        for cid in LEFT | RIGHT:
            tints[cid] = "#9aa6e8"      # blue edge
        for cid in (TOP | BOTTOM) & (LEFT | RIGHT):
            tints[cid] = "#c79ac7"      # shared corner (belongs to a red + a blue edge)
        cells = [{"id": c["id"], "points": c["pts"]} for c in CELLS]
        pieces = [{"cell": cid, "owner": col, "label": ""}
                  for cid, col in s.board.items()]
        highlights = []
        if s.last_move and s.last_move != "swap" and s.last_move in ADJ:
            highlights.append({"cell": s.last_move, "kind": "last-move"})
        if s.winner is not None:
            win_seat = s.red_seat if s.winner == RED else 1 - s.red_seat
            caption = f"{names[s.winner]} wins (P{win_seat + 1})"
        else:
            colour = s.colour_of_seat(s.to_move)
            edge = "top–bottom" if colour == RED else "left–right"
            caption = f"P{s.to_move + 1} to move as {names[colour]} ({edge})"
        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
