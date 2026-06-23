"""Slither (Corey Clark, 2010) — a modern connection game.

Played on an N×N board of intersections (Clark recommends 8×8 as a minimum;
this package defaults to 8 and offers larger boards as a `size` option).

  * Black (player 0) connects the TOP edge (row 0) to the BOTTOM edge (row N-1).
  * White (player 1) connects the LEFT edge (col 0) to the RIGHT edge (col N-1).
  * The four corners belong to BOTH sides.

A TURN has two parts, performed in this order:
  1. OPTIONAL slide — move one of your stones already on the board to an
     orthogonally OR diagonally adjacent (a chess king's step) EMPTY
     intersection.
  2. MANDATORY place — put a new stone of your colour on an empty intersection.

The defining constraint (the "no bare diagonal" rule): at the CONCLUSION of the
turn, every pair of diagonally-adjacent stones of the mover's colour must share
a common ORTHOGONALLY-adjacent stone of that colour. In other words a diagonal
contact is only allowed when the two stones are also joined around the corner by
a third like-coloured stone. Both the slide and the place must respect this —
the whole turn is one move and the test is applied to the final board.

The WIN CONDITION is **orthogonal connection**: a player wins by linking their
two opposite edges with an unbroken 4-orthogonally-connected chain of their own
stones. (Stones do NOT connect diagonally for the purpose of winning — only
orthogonal adjacency counts. The diagonal rule above governs legality, not the
connection itself.)

Move encoding (clickable `>`-separated cell path; cell ids use "c,r"):
  * place only:      "pc,pr"                  (one click on the empty target)
  * slide + place:   "from>to>pc,pr"          (click own stone, the empty
                                                adjacent slide target, then the
                                                empty placement cell)

Termination: a hard ply cap yields a draw (the diagonal rule does not by itself
bound the game, and optional slides admit cycles); a player who has no legal
turn loses.

FLAG / ruleset choices (see rules.md):
  * The task brief described the constraint as "no orthogonal self-adjacency"
    and a diagonal win; the PUBLISHED Slither rules are the opposite — the
    constraint is on bare DIAGONAL contacts and the win is an ORTHOGONAL chain.
    This package implements the published rules (LittleGolem / MindSports /
    designer), and flags the discrepancy.
  * First player: sources differ (BGG: Black first; MindSports: White first).
    This package has Black (player 0) move first, matching the platform's
    seat-0 = top/bottom convention.
  * The optional pie/swap rule is NOT implemented (documented omission).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1
PLY_CAP = 400  # hard cap -> draw


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


def _ortho(c: int, r: int, size: int):
    if c > 0:
        yield (c - 1, r)
    if c < size - 1:
        yield (c + 1, r)
    if r > 0:
        yield (c, r - 1)
    if r < size - 1:
        yield (c, r + 1)


def _king(c: int, r: int, size: int):
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == 0 and dr == 0:
                continue
            nc, nr = c + dc, r + dr
            if 0 <= nc < size and 0 <= nr < size:
                yield (nc, nr)


def _diagonals(c: int, r: int, size: int):
    for dc in (-1, 1):
        for dr in (-1, 1):
            nc, nr = c + dc, r + dr
            if 0 <= nc < size and 0 <= nr < size:
                yield (nc, nr)


def _legal_position(board: dict, player: int, size: int) -> bool:
    """No 'bare diagonal' for `player`: every pair of diagonally-adjacent
    stones of `player` must share a common orthogonally-adjacent stone of
    `player`."""
    for (c, r), p in board.items():
        if p != player:
            continue
        for (dc, dr) in _diagonals(c, r, size):
            if board.get((dc, dr)) != player:
                continue
            # (c,r) and (dc,dr) are diagonal same-colour neighbours. They must
            # share a common orthogonal like-colour stone. The two shared
            # orthogonal cells of a diagonal pair are (c,dr) and (dc,r).
            if board.get((c, dr)) == player or board.get((dc, r)) == player:
                continue
            return False
    return True


def _connects(board: dict, player: int, size: int) -> bool:
    """Does `player` link their two opposite edges with a 4-orthogonal chain?

    Black (0): TOP row (r=0) -> BOTTOM row (r=size-1).
    White (1): LEFT col (c=0) -> RIGHT col (c=size-1).
    """
    if player == BLACK:
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == BLACK]
        at_goal = lambda cell: cell[1] == size - 1  # noqa: E731
    else:
        starts = [(0, r) for r in range(size) if board.get((0, r)) == WHITE]
        at_goal = lambda cell: cell[0] == size - 1  # noqa: E731
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        for nb in _ortho(cur[0], cur[1], size):
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return False


@dataclass
class SlitherState:
    size: int = 8
    board: dict = field(default_factory=dict)  # (c, r) -> 0/1
    to_move: int = BLACK
    winner: Optional[int] = None
    ply: int = 0
    last_cells: tuple = ()  # cells touched by the last move (for highlight)
    no_move_loss: bool = False


class Slither(Game):
    name = "Slither"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SlitherState:
        size = int((options or {}).get("size", 8))
        return SlitherState(size=size)

    def current_player(self, s: SlitherState) -> int:
        return s.to_move

    def _gen(self, s: SlitherState):
        """Yield (move_str, new_board) for every legal turn.

        A turn is an optional king-step slide of one own stone to an empty cell,
        followed by a mandatory placement on an empty cell; the FINAL board must
        satisfy the no-bare-diagonal rule for the mover.
        """
        size = s.size
        me = s.to_move
        board = s.board
        empties = [
            (c, r)
            for r in range(size)
            for c in range(size)
            if (c, r) not in board
        ]
        my_stones = [cell for cell, p in board.items() if p == me]

        # --- placement-only turns ---
        for (pc, pr) in empties:
            nb = dict(board)
            nb[(pc, pr)] = me
            if _legal_position(nb, me, size):
                yield f"{pc},{pr}", nb

        # --- slide-then-place turns ---
        for (fc, fr) in my_stones:
            for (tc, tr) in _king(fc, fr, size):
                if (tc, tr) in board:
                    continue  # slide target must be empty
                slid = dict(board)
                del slid[(fc, fr)]
                slid[(tc, tr)] = me
                # Placement on any cell empty AFTER the slide (the vacated
                # source cell (fc,fr) is now a legal placement target too).
                for pr in range(size):
                    for pc in range(size):
                        if (pc, pr) in slid:
                            continue
                        nb = dict(slid)
                        nb[(pc, pr)] = me
                        if _legal_position(nb, me, size):
                            yield f"{fc},{fr}>{tc},{tr}>{pc},{pr}", nb

    def legal_moves(self, s: SlitherState) -> list[str]:
        if s.winner is not None or s.no_move_loss or s.ply >= PLY_CAP:
            return []
        return [m for m, _nb in self._gen(s)]

    def _board_after(self, s: SlitherState, move: str):
        """Recompute the board resulting from `move` (also used for highlight)."""
        parts = move.split(">")
        me = s.to_move
        if len(parts) == 1:
            pc, pr = _cell(parts[0])
            nb = dict(s.board)
            nb[(pc, pr)] = me
            return nb, ((pc, pr),)
        # slide + place
        fc, fr = _cell(parts[0])
        tc, tr = _cell(parts[1])
        pc, pr = _cell(parts[2])
        nb = dict(s.board)
        del nb[(fc, fr)]
        nb[(tc, tr)] = me
        nb[(pc, pr)] = me
        return nb, ((fc, fr), (tc, tr), (pc, pr))

    def apply_move(self, s: SlitherState, move: str, rng=None) -> SlitherState:
        nb, touched = self._board_after(s, move)
        winner = s.to_move if _connects(nb, s.to_move, s.size) else None
        nxt = SlitherState(
            size=s.size,
            board=nb,
            to_move=1 - s.to_move,
            winner=winner,
            ply=s.ply + 1,
            last_cells=touched,
        )
        if winner is None and nxt.ply < PLY_CAP:
            if not any(True for _ in self._gen(nxt)):
                nxt.no_move_loss = True
        return nxt

    def is_terminal(self, s: SlitherState) -> bool:
        return s.winner is not None or s.no_move_loss or s.ply >= PLY_CAP

    def returns(self, s: SlitherState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        if s.no_move_loss:
            loser = s.to_move
            return [-1.0, 1.0] if loser == BLACK else [1.0, -1.0]
        return [0.0, 0.0]  # ply-cap draw

    def serialize(self, s: SlitherState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "last_cells": [[c, r] for (c, r) in s.last_cells],
            "no_move_loss": s.no_move_loss,
        }

    def deserialize(self, d: dict) -> SlitherState:
        return SlitherState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            ply=d.get("ply", 0),
            last_cells=tuple((c, r) for c, r in d.get("last_cells", [])),
            no_move_loss=d.get("no_move_loss", False),
        )

    def describe_move(self, s: SlitherState, move: str) -> str:
        parts = move.split(">")
        if len(parts) == 1:
            return parts[0]
        return f"{parts[0]}->{parts[1]}, +{parts[2]}"

    def render(self, s: SlitherState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        highlights = [
            {"cell": f"{c},{r}", "kind": "last-move"} for (c, r) in s.last_cells
        ]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins (orthogonal connection)"
        elif s.no_move_loss:
            caption = f"{names[s.to_move]} has no legal turn and loses"
        elif s.ply >= PLY_CAP:
            caption = "Draw (ply cap)"
        else:
            edge = "top–bottom" if s.to_move == BLACK else "left–right"
            caption = f"{names[s.to_move]} to move ({edge})"
        return {
            "board": {
                "type": "square",
                "width": s.size,
                "height": s.size,
                "edges": {"top": BLACK, "bottom": BLACK, "left": WHITE, "right": WHITE},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
