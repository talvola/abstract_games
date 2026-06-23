"""Pentalath (a.k.a. Ndengrod), by Cameron Browne (2009) — published by nestorgames.

Five-in-a-row WITH Go-style group capture, on a hexagonal board of hexes.

Designed by Cameron Browne's evolutionary game-design program (the most-liked
output, originally "Ndengrod"; renamed Pentalath by Néstor Romeral Andrés as a
sister game to Yavalath). It is played on the same board as Yavalath: a HEXHEX
board with 5 hexes per side (61 cells), axial coordinates "q,r", 6-neighbour
adjacency. The corners are NOT clipped — it is a full hexagon of hexes.

Rules (as implemented; sources: cambolbro.com/games/pentalath, the nestorgames
Yavalath/Pentalath rulebook, BGG #51401):

* Players alternate placing one stone of their colour on an empty cell. Black
  (player 0) moves first.
* CAPTURE (Go-style): after a placement, any same-coloured GROUP (maximally
  connected, 6-neighbour) with NO FREEDOM — i.e. no adjacent EMPTY board cell —
  is captured and removed. As in Go, enemy groups are resolved BEFORE the
  mover's own group: "Pieces may not commit suicide but may create their own
  freedom through capture."
  - LIBERTY/FREEDOM = an adjacent EMPTY board cell. The board EDGE does NOT grant
    freedom (an off-board neighbour is not an empty cell), exactly as in Go.
* NO SUICIDE: a placement whose own just-placed group would have no freedom AND
  which captures nothing is ILLEGAL. (A placement that fills its own last liberty
  but, by capturing an adjacent enemy group, opens up a freedom IS legal.)
* WIN: make a line of FIVE OR MORE of your stones in a row along one of the three
  hex axes. Because a capture can break up a line, the win is checked on the
  POST-CAPTURE board, so only the mover can complete a line on their own move.

There is no ko/superko rule in Pentalath (unlike Gonnect): repetition is bounded
instead by a no-progress ply cap, since captures recycle cells and could loop.

Swap (pie rule): the standard rules let the SECOND player, on their first turn,
swap colours instead of placing. Modelled as the move "swap", available only as
player 1's very first action.

Moves are single-cell placements "q,r" (axial), or the literal "swap".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1

# The three hex axes (each as a unit step); a line runs in one of these directions.
AXES = [(1, 0), (0, 1), (1, -1)]

# Draw if this many plies pass with no capture and no progress toward filling.
# Captures recycle cells, so a pure ply cap guarantees termination.
NO_PROGRESS_CAP = 80


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


def _neighbors(q: int, r: int):
    return [
        (q + 1, r),
        (q - 1, r),
        (q, r + 1),
        (q, r - 1),
        (q + 1, r - 1),
        (q - 1, r + 1),
    ]


@lru_cache(maxsize=None)
def _cells(size: int) -> frozenset:
    """All on-board axial cells of a hexhex board with `size` hexes per side."""
    out = set()
    for q in range(-(size - 1), size):
        for r in range(-(size - 1), size):
            if abs(q + r) <= size - 1:
                out.add((q, r))
    return frozenset(out)


def _on_board(cell: tuple[int, int], size: int) -> bool:
    return cell in _cells(size)


def _group(board: dict, start: tuple, size: int) -> set:
    """Maximally-connected same-colour group containing `start`."""
    colour = board.get(start)
    if colour is None:
        return set()
    seen, stack = {start}, [start]
    while stack:
        q, r = stack.pop()
        for nb in _neighbors(q, r):
            if nb not in seen and board.get(nb) == colour:
                seen.add(nb)
                stack.append(nb)
    return seen


def _has_freedom(board: dict, group: set, size: int) -> bool:
    """True if any stone of `group` has an adjacent EMPTY on-board cell.

    The board edge grants no freedom: only an in-bounds, unoccupied neighbour
    counts (an off-board neighbour is not an empty cell).
    """
    for q, r in group:
        for nb in _neighbors(q, r):
            if _on_board(nb, size) and nb not in board:
                return True
    return False


def _resolve(board: dict, q: int, r: int, mover: int, size: int):
    """Place `mover` at (q, r) on a COPY of `board`; resolve captures.

    Returns (new_board, captured_any). Enemy zero-freedom groups are removed
    first, then the mover's own group if it ended with no freedom (a suicide
    candidate). Does NOT enforce legality — callers reject pure suicide.
    """
    nb = dict(board)
    nb[(q, r)] = mover
    enemy = 1 - mover
    captured = False
    checked: set = set()
    for ec, er in _neighbors(q, r):
        if nb.get((ec, er)) == enemy and (ec, er) not in checked:
            grp = _group(nb, (ec, er), size)
            checked |= grp
            if not _has_freedom(nb, grp, size):
                for cell in grp:
                    del nb[cell]
                captured = True
    if not captured:
        own = _group(nb, (q, r), size)
        if not _has_freedom(nb, own, size):
            for cell in own:
                del nb[cell]
            # captured stays False -> this was a pure suicide (illegal).
    return nb, captured


def _has_five(board: dict, player: int) -> bool:
    """True if `player` has 5+ in a row along one of the 3 hex axes."""
    for (q, r), p in board.items():
        if p != player:
            continue
        for dq, dr in AXES:
            # Count only from a line start (no predecessor of same colour).
            if board.get((q - dq, r - dr)) == player:
                continue
            n = 1
            cq, cr = q + dq, r + dr
            while board.get((cq, cr)) == player:
                n += 1
                cq += dq
                cr += dr
            if n >= 5:
                return True
    return False


@dataclass
class PentalathState:
    size: int = 5
    board: dict = field(default_factory=dict)  # (q, r) -> 0/1
    to_move: int = BLACK
    winner: Optional[int] = None
    last_move: Optional[tuple] = None
    ply: int = 0
    no_progress: int = 0  # plies since the last capture (reset on capture)
    swap_available: bool = False  # player 1's first turn may swap instead
    draw: bool = False


class Pentalath(Game):
    name = "Pentalath"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> PentalathState:
        opts = options or {}
        size = int(opts.get("size", 5))
        swap = bool(opts.get("swap", True))
        s = PentalathState(size=size)
        s.swap_available = swap  # becomes actionable once Black has placed
        return s

    def current_player(self, s: PentalathState) -> int:
        return s.to_move

    def _placements(self, s: PentalathState):
        """Yield (move_str, new_board, captured) for every legal placement."""
        for (q, r) in _cells(s.size):
            if (q, r) in s.board:
                continue
            nb, captured = _resolve(s.board, q, r, s.to_move, s.size)
            # Pure suicide: own stone removed and nothing captured -> illegal.
            if not captured and (q, r) not in nb:
                continue
            yield f"{q},{r}", nb, captured

    def _can_swap(self, s: PentalathState) -> bool:
        # Swap is offered to White on its first action: exactly one stone placed.
        return s.swap_available and s.to_move == WHITE and s.ply == 1

    def legal_moves(self, s: PentalathState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = [m for m, _nb, _cap in self._placements(s)]
        if self._can_swap(s):
            moves.append("swap")
        return moves

    def apply_move(self, s: PentalathState, move: str, rng=None) -> PentalathState:
        if move == "swap":
            if not self._can_swap(s):
                raise ValueError("swap is not available")
            # The swapping player (White, the mover) takes over the opening: every
            # stone on the board becomes White's, then play hands back to Black.
            # (Mirrors the hex pie rule: recolour to the mover, then to_move flips.)
            nb = {cell: s.to_move for cell in s.board}
            return PentalathState(
                size=s.size,
                board=nb,
                to_move=1 - s.to_move,
                winner=None,
                last_move=s.last_move,
                ply=s.ply + 1,
                no_progress=s.no_progress + 1,
                swap_available=False,
            )

        q, r = _cell(move)
        nb, captured = _resolve(s.board, q, r, s.to_move, s.size)
        if not captured and (q, r) not in nb:
            raise ValueError(f"illegal (suicide) move {move!r}")

        winner = s.to_move if _has_five(nb, s.to_move) else None
        no_progress = 0 if captured else s.no_progress + 1
        draw = False
        if winner is None and no_progress >= NO_PROGRESS_CAP:
            draw = True
        nxt = PentalathState(
            size=s.size,
            board=nb,
            to_move=1 - s.to_move,
            winner=winner,
            last_move=(q, r),
            ply=s.ply + 1,
            no_progress=no_progress,
            swap_available=s.swap_available,
            draw=draw,
        )
        # Safety: if the next player is somehow stuck (board full), it's a draw.
        if winner is None and not draw:
            if not any(True for _ in self._placements(nxt)):
                nxt.draw = True
        return nxt

    def is_terminal(self, s: PentalathState) -> bool:
        return s.winner is not None or s.draw

    def returns(self, s: PentalathState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: PentalathState) -> dict:
        return {
            "size": s.size,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "last_move": list(s.last_move) if s.last_move is not None else None,
            "ply": s.ply,
            "no_progress": s.no_progress,
            "swap_available": s.swap_available,
            "draw": s.draw,
        }

    def deserialize(self, d: dict) -> PentalathState:
        return PentalathState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            last_move=tuple(d["last_move"]) if d.get("last_move") is not None else None,
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
            swap_available=d.get("swap_available", False),
            draw=d.get("draw", False),
        )

    def describe_move(self, s: PentalathState, move: str) -> str:
        if move == "swap":
            return "swap"
        return move

    def render(self, s: PentalathState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{q},{r}", "owner": p, "label": ""}
            for (q, r), p in s.board.items()
        ]
        highlights = []
        if s.last_move is not None:
            highlights.append(
                {"cell": f"{s.last_move[0]},{s.last_move[1]}", "kind": "last-move"}
            )
        if s.winner is not None:
            caption = f"{names[s.winner]} wins (five in a row)"
        elif s.draw:
            caption = "Draw"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
