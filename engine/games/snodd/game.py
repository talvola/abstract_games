"""Snodd, by Dr Eric Silverman (2021) -- Xodd/Yodd (Luis Bolaños Mures) ported to
the snub square tiling.

Snodd is rules-identical to Yodd/Xodd; only the board changes. Where Yodd is
played on the hexagonal (degree-6) grid and Xodd on the square (degree-4) grid,
Snodd is played on the *vertices of the snub square tiling* (vertex config
3.3.4.3.4), where each interior point has degree exactly 5. Each playable point
is drawn as one cell of the dual Cairo pentagonal tiling.

Rules:
* An empty board of snub-square vertices. Two players, Red (player 0) and Blue
  (player 1); Red moves first.
* On a turn a player places ONE or TWO stones of *either* colour on empty cells
  (on Red's opening turn, only one stone). No captures, no movement.
* A *group* is a set of connected like-coloured stones (connected through the
  board's adjacency graph). At the END of every turn the TOTAL number of groups
  on the board (both colours) must be ODD.
* A player may PASS instead of placing, but only if it keeps the total odd (so
  Red can't pass on the opening turn -- an empty board has zero groups). Two
  passes in a row end the game.
* You WIN by having FEWER groups of your own colour at game end. Since the total
  is odd, the two counts are never equal -- there are no draws.

Modelling notes (identical to Yodd):
* A turn is up to two placement sub-moves by the same player. ``current_player``
  stays put after the first stone so the player can place a second or end the
  turn; the turn auto-ends once the stone cap (1 on the opening turn, else 2) is
  reached. Moves: ``"<cellid>=red"`` / ``"<cellid>=blue"`` to place, ``"end"`` to
  stop after one stone, ``"pass"`` to pass the whole turn.
* The odd invariant means the board is always odd at the start of a (non-opening)
  turn, so ``pass`` is always available -- ``legal_moves`` is never empty. A first
  stone that leaves an even count is only offered if a parity-fixing second stone
  exists, so the player is never stranded mid-turn.
* The win is decided by group counts at the end (two passes), stored as ``winner``.

The board graph (snub-square vertices, their degree-5 adjacency, and the Cairo
pentagon polygons for rendering) is generated OFFLINE and stored in board.json so
that this module stays pure-stdlib.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1
_TOK = {RED: "red", BLUE: "blue"}
_COLOR = {"red": RED, "blue": BLUE}

_BOARD_PATH = os.path.join(os.path.dirname(__file__), "board.json")
with open(_BOARD_PATH, "r", encoding="utf-8") as _f:
    _BOARD = json.load(_f)

# Static board data (shared, immutable).
CELLS = _BOARD["cells"]                        # [{id, pts}]
CELL_IDS = [c["id"] for c in CELLS]
ADJ = {cid: tuple(ns) for cid, ns in _BOARD["adj"].items()}
_PTS = {c["id"]: c["pts"] for c in CELLS}


def _label(board: dict):
    """Flood-fill the board into groups. Returns (labels, total, red, blue) where
    labels maps each occupied cell to its group id."""
    labels = {}
    gid = 0
    red = blue = 0
    for cell, color in board.items():
        if cell in labels:
            continue
        labels[cell] = gid
        stack = [cell]
        while stack:
            cur = stack.pop()
            for nb in ADJ[cur]:
                if board.get(nb) == color and nb not in labels:
                    labels[nb] = gid
                    stack.append(nb)
        gid += 1
        if color == RED:
            red += 1
        else:
            blue += 1
    return labels, red + blue, red, blue


def _adj_groups(board: dict, labels: dict, c: str, color: int) -> int:
    """Number of distinct ``color`` groups adjacent to empty cell ``c``."""
    seen = set()
    for nb in ADJ[c]:
        if board.get(nb) == color:
            seen.add(labels[nb])
    return len(seen)


def _completable_slow(board: dict, c: str, color: int, empties: list) -> bool:
    """Exact check: after placing (c, color), does some second placement bring the
    total back to odd? Only used in dense positions where the fast test fails."""
    board2 = dict(board)
    board2[c] = color
    labels2, total2, _, _ = _label(board2)
    for c2 in empties:
        if c2 == c:
            continue
        for col2 in (RED, BLUE):
            if (total2 + 1 - _adj_groups(board2, labels2, c2, col2)) % 2 == 1:
                return True
    return False


@dataclass
class SnoddState:
    board: dict = field(default_factory=dict)   # cell id -> RED / BLUE
    to_move: int = RED
    turn_cells: list = field(default_factory=list)  # cells placed so far this turn
    passes: int = 0                              # consecutive passes
    over: bool = False
    winner: Optional[int] = None


class Snodd(Game):
    name = "Snodd"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SnoddState:
        return SnoddState()

    def current_player(self, s: SnoddState) -> int:
        return s.to_move

    def legal_moves(self, s: SnoddState) -> list[str]:
        if s.over:
            return []
        board = s.board
        empties = [c for c in CELL_IDS if c not in board]
        labels, total, _, _ = _label(board)
        placed = len(s.turn_cells)

        if placed == 0:
            is_first = not board
            moves = []
            if total % 2 == 1:
                moves.append("pass")
            # Isolated empty cells (no occupied neighbour) always flip parity when
            # filled (a fresh +1 group), and stay isolated no matter what the first
            # stone does elsewhere -- a sound "the turn is still completable" witness.
            iso = {e for e in empties if all(board.get(nb) is None for nb in ADJ[e])}
            for c in empties:
                forb = None
                for col in (RED, BLUE):
                    after1 = total + 1 - _adj_groups(board, labels, c, col)
                    if after1 % 2 == 1:               # odd -> may stop after one stone
                        moves.append(f"{c}={_TOK[col]}")
                    elif not is_first:                # even -> need a valid second stone
                        if forb is None:
                            forb = {c, *ADJ[c]}
                        if len(iso) > 7 or (iso - forb) \
                                or _completable_slow(board, c, col, empties):
                            moves.append(f"{c}={_TOK[col]}")
            return moves

        # placed == 1 (only reachable on a non-opening turn, cap = 2): place a
        # second stone that lands on odd, or end now if already odd.
        moves = []
        if total % 2 == 1:
            moves.append("end")
        for c in empties:
            for col in (RED, BLUE):
                if (total + 1 - _adj_groups(board, labels, c, col)) % 2 == 1:
                    moves.append(f"{c}={_TOK[col]}")
        return moves

    def apply_move(self, s: SnoddState, move: str, rng=None) -> SnoddState:
        if move == "pass":
            passes = s.passes + 1
            if passes >= 2:
                _, _, red, blue = _label(s.board)
                winner = RED if red < blue else BLUE
                return SnoddState(board=s.board, to_move=1 - s.to_move,
                                  turn_cells=[], passes=passes, over=True, winner=winner)
            return SnoddState(board=s.board, to_move=1 - s.to_move,
                              turn_cells=[], passes=passes)

        if move == "end":
            return SnoddState(board=s.board, to_move=1 - s.to_move,
                              turn_cells=[], passes=0)

        # placement "<cellid>=red" / "<cellid>=blue"
        cell_id, _, tok = move.partition("=")
        if cell_id not in ADJ:
            raise ValueError(f"unknown cell {cell_id!r}")
        color = _COLOR[tok]
        if cell_id in s.board:
            raise ValueError(f"cell {cell_id} occupied")
        board = dict(s.board)
        board[cell_id] = color
        turn_cells = s.turn_cells + [cell_id]
        cap = 1 if not s.board else 2
        if len(turn_cells) >= cap:                    # turn auto-ends at the cap
            return SnoddState(board=board, to_move=1 - s.to_move,
                              turn_cells=[], passes=0)
        return SnoddState(board=board, to_move=s.to_move,
                          turn_cells=turn_cells, passes=0)

    def is_terminal(self, s: SnoddState) -> bool:
        return s.over

    def returns(self, s: SnoddState) -> list[float]:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: SnoddState) -> dict:
        return {
            "board": dict(s.board),
            "to_move": s.to_move,
            "turn_cells": list(s.turn_cells),
            "passes": s.passes,
            "over": s.over,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> SnoddState:
        return SnoddState(
            board=dict(d["board"]),
            to_move=d["to_move"],
            turn_cells=list(d.get("turn_cells", [])),
            passes=d.get("passes", 0),
            over=d.get("over", False),
            winner=d.get("winner"),
        )

    def describe_move(self, s: SnoddState, move: str) -> str:
        if move == "pass":
            return "pass"
        if move == "end":
            return "end turn"
        cell_id, _, tok = move.partition("=")
        return f"{tok.capitalize()} {cell_id}"

    def render(self, s: SnoddState, perspective=None) -> dict:
        names = {RED: "Red", BLUE: "Blue"}
        _, total, red, blue = _label(s.board)
        cells = [{"id": cid, "points": _PTS[cid]} for cid in CELL_IDS]
        pieces = [{"cell": cid, "owner": v, "label": ""} for cid, v in s.board.items()]
        highlights = [{"cell": cid, "kind": "last-move"} for cid in s.turn_cells]
        if s.over:
            caption = f"{names[s.winner]} wins ({red} red vs {blue} blue groups)"
        else:
            who = names[s.to_move]
            counts = f"R:{red} B:{blue} (total {total})"
            if s.turn_cells:
                need = "may end turn" if total % 2 == 1 else "must place a 2nd stone (total must be odd)"
                caption = f"{who} — placed 1 stone, {need} · {counts}"
            else:
                caption = f"{who} to move · {counts}"
        return {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
