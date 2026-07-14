"""YvY, by Christian Freeling & David Bush (mindsports.nl).

A territory / loop game played on a serrated hexagonal board of 147 cells, 21 of
which are *sprouts* (the degree-2 perimeter spikes, rendered green). Two players,
White (seat 0) and Black (seat 1); White moves first.

Rules (as implemented — see rules.md, sourced verbatim from mindsports.nl):
  * On a turn a player PLACES one stone of HIS OWN colour on any empty cell, or
    PASSES. Passing does NOT forfeit the right to move next turn. Stones never
    move and are never removed during play.
  * SWAP (pie rule): on the second player's first action, when exactly one stone
    is on the board, he may "swap" instead of placing — taking over the opening
    (the lone stone becomes his) and handing the move back to the opener.
  * A GROUP is a set of connected (adjacency-graph) like-coloured stones; a lone
    stone is a group.
  * A LOOP is a group that completely surrounds one or more cells (empty or
    occupied, by anyone). The instant a placement COMPLETES a loop, that player
    WINS immediately, regardless of score ("sudden death").
  * Two consecutive passes end the game, which is then scored.

Scoring at a pass-pass end:
  1. LIFE & DEATH: a group LIVES iff at least one of its stones is on a sprout;
     otherwise it is DEAD. Remove all dead groups (both colours) first.
  2. FENCED-IN: after removal, any like-colour group fenced in (enclosed) by
     another merges into it (counts as one group); a player CONTROLS a sprout if
     he occupies it OR it is fenced in by his stones.
  3. SCORE (each player) = (sprouts controlled) − 2 × (number of his groups).
     Higher score wins. A genuine tie (e.g. an early symmetric double-pass on the
     empty board) is an honest DRAW.

Geometry note (documented interpretation): on THIS extracted board the 21 sprouts
are degree-2 spikes poking into the exterior void, so an empty sprout can NEVER be
enclosed (it always touches "outside") and a surviving/live group always touches
the perimeter, so it can never be fenced in. Consequently the fenced-in machinery
— implemented faithfully below via the same enclosure flood-fill used for loop
detection — is provably inert for scoring here: sprout control reduces to
occupation and there is no group merging. The code stays fully general (it would
compute genuine fenced-in territory on a board whose sprouts weren't spikes).

The board graph (cells, adjacency, sprout cells, pentagon polygons for rendering)
is loaded read-only from board.json so this module stays pure-stdlib.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
_NAMES = {WHITE: "White", BLACK: "Black"}

_BOARD_PATH = os.path.join(os.path.dirname(__file__), "board.json")
with open(_BOARD_PATH, "r", encoding="utf-8") as _f:
    _BOARD = json.load(_f)

# Static board data (shared, immutable).
CELLS = _BOARD["cells"]                                  # [{id, pts}]
CELL_IDS = [c["id"] for c in CELLS]
ADJ = {cid: tuple(ns) for cid, ns in _BOARD["adj"].items()}
_PTS = {c["id"]: c["pts"] for c in CELLS}
SPROUTS = frozenset(_BOARD["sprouts"])
# Outer boundary seeds for the enclosure flood: cells that touch the exterior
# void (degree < 6 on this hex-based graph). Sprout spikes are included — they
# genuinely border the void.
_PERIMETER = frozenset(c for c in CELL_IDS if len(ADJ[c]) < 6)

_PLY_CAP = 800  # hard backstop so random conformance games always terminate


# --------------------------------------------------------------------------- #
# Graph helpers (pure functions over a {cell -> colour} board dict)
# --------------------------------------------------------------------------- #
def _components(board: dict, colour: int) -> list[set]:
    """Connected components (groups) of `colour` stones."""
    seen = set()
    out = []
    for cell, col in board.items():
        if col != colour or cell in seen:
            continue
        comp = {cell}
        seen.add(cell)
        stack = [cell]
        while stack:
            cur = stack.pop()
            for nb in ADJ[cur]:
                if board.get(nb) == colour and nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    stack.append(nb)
        out.append(comp)
    return out


def _enclosed_by(barrier: set) -> set:
    """Cells that `barrier` (a set of stones) completely surrounds.

    Flood-fill the NON-barrier cells starting from the board perimeter; any
    non-barrier cell the flood cannot reach is enclosed by the barrier. Enclosed
    cells may be empty or occupied by anyone. This is the single machine used for
    both loop detection (barrier = one group) and territory (barrier = a colour).
    """
    outside = set()
    stack = []
    for c in _PERIMETER:
        if c not in barrier:
            outside.add(c)
            stack.append(c)
    while stack:
        cur = stack.pop()
        for nb in ADJ[cur]:
            if nb not in barrier and nb not in outside:
                outside.add(nb)
                stack.append(nb)
    return {c for c in CELL_IDS if c not in barrier and c not in outside}


def _forms_loop(board: dict, cell: str, colour: int) -> bool:
    """Does the `colour` group containing `cell` enclose >=1 cell (a loop)?"""
    group = None
    for comp in _components(board, colour):
        if cell in comp:
            group = comp
            break
    if group is None:
        return False
    return bool(_enclosed_by(group))


def _score_board(board: dict):
    """Score a position. Returns (scores, detail) where scores = [white, black].

    detail carries the live board and per-colour breakdown for rendering/tests.
    """
    # 1. Life & death: keep only groups with >=1 stone on a sprout.
    live: dict = {}
    for colour in (WHITE, BLACK):
        for comp in _components(board, colour):
            if any(cell in SPROUTS for cell in comp):
                for cell in comp:
                    live[cell] = colour

    scores = [0, 0]
    detail = {"live": live, "per": {}}
    for colour in (WHITE, BLACK):
        stones = {c for c, v in live.items() if v == colour}
        enclosed = _enclosed_by(stones) if stones else set()
        # 2. Groups after fenced-in merging: components over stones ∪ enclosed
        #    territory that contain at least one stone. (Inert on this geometry:
        #    `enclosed` is always empty for a legitimately-scored live position.)
        nodes = stones | enclosed
        seen = set()
        ngroups = 0
        for n in nodes:
            if n in seen:
                continue
            has_stone = False
            stack = [n]
            seen.add(n)
            while stack:
                cur = stack.pop()
                if cur in stones:
                    has_stone = True
                for nb in ADJ[cur]:
                    if nb in nodes and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            if has_stone:
                ngroups += 1
        # Sprouts controlled: occupied by this colour OR fenced in by it.
        controlled = {s for s in SPROUTS if live.get(s) == colour} | (enclosed & SPROUTS)
        score = len(controlled) - 2 * ngroups
        scores[colour] = score
        detail["per"][colour] = {
            "sprouts": len(controlled),
            "groups": ngroups,
            "score": score,
        }
    return scores, detail


# --------------------------------------------------------------------------- #
@dataclass
class YvyState:
    board: dict = field(default_factory=dict)      # cell id -> WHITE / BLACK
    to_move: int = 0                               # seat to move
    white_seat: int = 0                            # which seat plays WHITE (flips on swap)
    passes: int = 0                                # consecutive passes
    ply: int = 0
    last_move: Optional[str] = None
    over: bool = False
    winner: Optional[int] = None                   # winning COLOUR (WHITE/BLACK) or None
    win_by: Optional[str] = None                   # "loop" | "score" | None

    def colour_of_seat(self, seat: int) -> int:
        return WHITE if seat == self.white_seat else BLACK


class Yvy(Game):
    name = "YvY"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> YvyState:
        return YvyState()

    def current_player(self, s: YvyState) -> int:
        return s.to_move

    def _swap_available(self, s: YvyState) -> bool:
        # Pie rule: second player's very first action, exactly one stone on board.
        return s.ply == 1 and len(s.board) == 1 and not s.over

    def legal_moves(self, s: YvyState) -> list[str]:
        if s.over:
            return []
        moves = [c for c in CELL_IDS if c not in s.board]
        moves.append("pass")
        if self._swap_available(s):
            moves.append("swap")
        return moves

    def apply_move(self, s: YvyState, move: str, rng=None) -> YvyState:
        if s.over:
            raise ValueError("game is over")

        if move == "swap":
            if not self._swap_available(s):
                raise ValueError("swap is not available")
            # Second seat takes over the opening: it now plays WHITE (owns the
            # lone stone); the opener plays BLACK and is back on the move.
            return YvyState(
                board=dict(s.board),
                to_move=1 - s.to_move,
                white_seat=s.to_move,
                passes=0,
                ply=s.ply + 1,
                last_move="swap",
            )

        if move == "pass":
            passes = s.passes + 1
            over = passes >= 2
            winner = win_by = None
            if over:
                scores, _ = _score_board(s.board)
                if scores[WHITE] > scores[BLACK]:
                    winner, win_by = WHITE, "score"
                elif scores[BLACK] > scores[WHITE]:
                    winner, win_by = BLACK, "score"
                # equal -> honest draw (winner stays None)
            return YvyState(
                board=dict(s.board),
                to_move=1 - s.to_move,
                white_seat=s.white_seat,
                passes=passes,
                ply=s.ply + 1,
                last_move="pass",
                over=over,
                winner=winner,
                win_by=win_by,
            )

        # placement of the current player's own colour
        if move not in ADJ:
            raise ValueError(f"unknown cell {move!r}")
        if move in s.board:
            raise ValueError(f"cell {move!r} is occupied")
        colour = s.colour_of_seat(s.to_move)
        board = dict(s.board)
        board[move] = colour

        if _forms_loop(board, move, colour):          # sudden-death loop win
            return YvyState(
                board=board,
                to_move=1 - s.to_move,
                white_seat=s.white_seat,
                passes=0,
                ply=s.ply + 1,
                last_move=move,
                over=True,
                winner=colour,
                win_by="loop",
            )

        ply = s.ply + 1
        # Hard ply-cap backstop: score the position so conformance can't loop.
        if ply >= _PLY_CAP:
            scores, _ = _score_board(board)
            if scores[WHITE] > scores[BLACK]:
                winner, win_by = WHITE, "score"
            elif scores[BLACK] > scores[WHITE]:
                winner, win_by = BLACK, "score"
            else:
                winner = win_by = None
            return YvyState(
                board=board, to_move=1 - s.to_move, white_seat=s.white_seat,
                passes=0, ply=ply, last_move=move, over=True,
                winner=winner, win_by=win_by,
            )

        return YvyState(
            board=board,
            to_move=1 - s.to_move,
            white_seat=s.white_seat,
            passes=0,
            ply=ply,
            last_move=move,
        )

    def is_terminal(self, s: YvyState) -> bool:
        return s.over

    def returns(self, s: YvyState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]
        win_seat = s.white_seat if s.winner == WHITE else 1 - s.white_seat
        return [1.0 if p == win_seat else -1.0 for p in range(2)]

    def serialize(self, s: YvyState) -> dict:
        return {
            "board": dict(s.board),
            "to_move": s.to_move,
            "white_seat": s.white_seat,
            "passes": s.passes,
            "ply": s.ply,
            "last_move": s.last_move,
            "over": s.over,
            "winner": s.winner,
            "win_by": s.win_by,
        }

    def deserialize(self, d: dict) -> YvyState:
        return YvyState(
            board={k: int(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            white_seat=d.get("white_seat", 0),
            passes=d.get("passes", 0),
            ply=d.get("ply", len(d["board"])),
            last_move=d.get("last_move"),
            over=d.get("over", False),
            winner=d.get("winner"),
            win_by=d.get("win_by"),
        )

    def describe_move(self, s: YvyState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if move == "pass":
            return "pass"
        colour = s.colour_of_seat(s.to_move)
        return f"{_NAMES[colour]} {move}"

    def render(self, s: YvyState, perspective=None) -> dict:
        cells = [{"id": cid, "points": _PTS[cid]} for cid in CELL_IDS]
        tints = {sid: "#3ec85a" for sid in SPROUTS}     # sprout cells = green
        pieces = [{"cell": cid, "owner": col, "label": ""}
                  for cid, col in s.board.items()]
        highlights = []
        if s.last_move and s.last_move in ADJ:
            highlights.append({"cell": s.last_move, "kind": "last-move"})

        scores, _ = _score_board(s.board)
        sc = f"W {scores[WHITE]:+d} / B {scores[BLACK]:+d}"
        if s.over:
            if s.winner is None:
                caption = f"Draw ({sc})"
            elif s.win_by == "loop":
                caption = f"{_NAMES[s.winner]} wins — loop! ({sc})"
            else:
                caption = f"{_NAMES[s.winner]} wins on score ({sc})"
        else:
            colour = s.colour_of_seat(s.to_move)
            note = ""
            if s.passes == 1:
                note = " · a 2nd pass ends the game"
            caption = f"P{s.to_move + 1} to move as {_NAMES[colour]} · {sc}{note}"
        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
