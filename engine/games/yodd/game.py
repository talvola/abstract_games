"""Yodd, by Luis Bolaños Mures -- https://mindsports.nl/index.php/the-pit/623-yodd

Rules:
* Hexagonal (hexhex) board, empty to start. Two players, Red (player 0) and Blue
  (player 1); Red moves first.
* On a turn a player places ONE or TWO stones of *either* colour on empty cells
  (on Red's opening turn, only one stone). No captures, no movement.
* A *group* is a set of connected like-coloured stones. At the END of every turn
  the TOTAL number of groups on the board (both colours) must be ODD.
* A player may PASS instead of placing, but only if it keeps the total odd (so
  Red can't pass on the opening turn -- an empty board has zero groups). Two
  passes in a row end the game.
* You WIN by having FEWER groups of your own colour at game end. Since the total
  is odd, the two counts are never equal -- there are no draws.

Modelling notes:
* A turn is up to two placement sub-moves by the same player. ``current_player``
  stays put after the first stone so the player can place a second or end the
  turn; the turn auto-ends once the stone cap (1 on the opening turn, else 2) is
  reached. Moves: ``"q,r=red"`` / ``"q,r=blue"`` to place, ``"end"`` to stop
  after one stone, ``"pass"`` to pass the whole turn.
* The odd invariant means the board is always odd at the start of a (non-opening)
  turn, so ``pass`` is always available -- ``legal_moves`` is never empty. A first
  stone that leaves an even count is only offered if a parity-fixing second stone
  exists, so the player is never stranded mid-turn.
* The win is decided by group counts at the end (two passes), stored as ``winner``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1
_TOK = {RED: "red", BLUE: "blue"}
_COLOR = {"red": RED, "blue": BLUE}


def _neighbors(q: int, r: int):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1), (q + 1, r - 1), (q - 1, r + 1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    out = []
    for q in range(-(size - 1), size):
        for r in range(-(size - 1), size):
            if abs(q + r) <= size - 1:
                out.append((q, r))
    return tuple(out)


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


def _cid(c: tuple) -> str:
    return f"{c[0]},{c[1]}"


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
            for nb in _neighbors(*cur):
                if board.get(nb) == color and nb not in labels:
                    labels[nb] = gid
                    stack.append(nb)
        gid += 1
        if color == RED:
            red += 1
        else:
            blue += 1
    return labels, red + blue, red, blue


def _adj_groups(board: dict, labels: dict, c: tuple, color: int) -> int:
    """Number of distinct ``color`` groups adjacent to empty cell ``c``."""
    seen = set()
    for nb in _neighbors(*c):
        if board.get(nb) == color:
            seen.add(labels[nb])
    return len(seen)


def _completable_slow(board: dict, c: tuple, color: int, empties: list) -> bool:
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
class YoddState:
    size: int = 6
    board: dict = field(default_factory=dict)   # (q, r) -> RED / BLUE
    to_move: int = RED
    turn_cells: list = field(default_factory=list)  # cells placed so far this turn
    passes: int = 0                              # consecutive passes
    over: bool = False
    winner: Optional[int] = None


class Yodd(Game):
    uid = "yodd"
    name = "Yodd"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> YoddState:
        size = int((options or {}).get("size", 6))
        return YoddState(size=size)

    def current_player(self, s: YoddState) -> int:
        return s.to_move

    def legal_moves(self, s: YoddState) -> list[str]:
        if s.over:
            return []
        board = s.board
        empties = [c for c in _cells(s.size) if c not in board]
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
            iso = {e for e in empties if all(board.get(nb) is None for nb in _neighbors(*e))}
            for c in empties:
                forb = None
                for col in (RED, BLUE):
                    after1 = total + 1 - _adj_groups(board, labels, c, col)
                    if after1 % 2 == 1:               # odd -> may stop after one stone
                        moves.append(f"{_cid(c)}={_TOK[col]}")
                    elif not is_first:                # even -> need a valid second stone
                        if forb is None:
                            forb = {c, *_neighbors(*c)}
                        if len(iso) > 7 or (iso - forb) \
                                or _completable_slow(board, c, col, empties):
                            moves.append(f"{_cid(c)}={_TOK[col]}")
            return moves

        # placed == 1 (only reachable on a non-opening turn, cap = 2): place a
        # second stone that lands on odd, or end now if already odd.
        moves = []
        if total % 2 == 1:
            moves.append("end")
        for c in empties:
            for col in (RED, BLUE):
                if (total + 1 - _adj_groups(board, labels, c, col)) % 2 == 1:
                    moves.append(f"{_cid(c)}={_TOK[col]}")
        return moves

    def apply_move(self, s: YoddState, move: str, rng=None) -> YoddState:
        if move == "pass":
            passes = s.passes + 1
            if passes >= 2:
                _, _, red, blue = _label(s.board)
                winner = RED if red < blue else BLUE
                return YoddState(size=s.size, board=s.board, to_move=1 - s.to_move,
                                 turn_cells=[], passes=passes, over=True, winner=winner)
            return YoddState(size=s.size, board=s.board, to_move=1 - s.to_move,
                             turn_cells=[], passes=passes)

        if move == "end":
            return YoddState(size=s.size, board=s.board, to_move=1 - s.to_move,
                             turn_cells=[], passes=0)

        # placement "q,r=red" / "q,r=blue"
        cell_str, _, tok = move.partition("=")
        c = _cell(cell_str)
        color = _COLOR[tok]
        if c in s.board:
            raise ValueError(f"cell {cell_str} occupied")
        board = dict(s.board)
        board[c] = color
        turn_cells = s.turn_cells + [_cid(c)]
        cap = 1 if not s.board else 2
        if len(turn_cells) >= cap:                    # turn auto-ends at the cap
            return YoddState(size=s.size, board=board, to_move=1 - s.to_move,
                             turn_cells=[], passes=0)
        return YoddState(size=s.size, board=board, to_move=s.to_move,
                         turn_cells=turn_cells, passes=0)

    def is_terminal(self, s: YoddState) -> bool:
        return s.over

    def returns(self, s: YoddState) -> list[float]:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: YoddState) -> dict:
        return {
            "size": s.size,
            "board": {_cid(c): v for c, v in s.board.items()},
            "to_move": s.to_move,
            "turn_cells": list(s.turn_cells),
            "passes": s.passes,
            "over": s.over,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> YoddState:
        return YoddState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            turn_cells=list(d.get("turn_cells", [])),
            passes=d.get("passes", 0),
            over=d.get("over", False),
            winner=d.get("winner"),
        )

    def describe_move(self, s: YoddState, move: str) -> str:
        if move == "pass":
            return "pass"
        if move == "end":
            return "end turn"
        cell_str, _, tok = move.partition("=")
        return f"{tok.capitalize()} {cell_str}"

    def render(self, s: YoddState, perspective=None) -> dict:
        names = {RED: "Red", BLUE: "Blue"}
        _, total, red, blue = _label(s.board)
        pieces = [{"cell": _cid(c), "owner": v, "label": ""} for c, v in s.board.items()]
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
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
