"""Atari Go (a.k.a. Capture Go / first-capture Go).

A teaching variant of Go on an N×N grid of intersections. Players alternate
placing a stone of their colour on an empty intersection; Black (player 0) moves
first. After a placement, any maximally-connected enemy group (4-orthogonal
adjacency) left with zero liberties is removed; enemy captures are resolved
BEFORE checking the mover's own group.

Rules implemented here:
  * SUICIDE is illegal — a move that leaves the mover's own just-placed group
    with no liberties AND captures nothing is forbidden.
  * POSITIONAL SUPERKO — a move may not recreate any board position that has
    occurred before (this subsumes the simple ko / immediate-recapture rule).
  * WIN — the FIRST player to capture ANY enemy stone(s) wins immediately. That
    is the whole point of Atari Go.
  * If the player to move has no legal move (board full or every move is
    suicide/superko-illegal and captures nothing), they LOSE (rare).

The liberty/group logic here is the reusable heart of every Go-family game.

Moves are single-cell placements "c,r" (col, row), 0-indexed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


def _neighbors(c: int, r: int, size: int):
    if c > 0:
        yield (c - 1, r)
    if c < size - 1:
        yield (c + 1, r)
    if r > 0:
        yield (c, r - 1)
    if r < size - 1:
        yield (c, r + 1)


def _group(board: dict, start: tuple[int, int], size: int) -> set:
    """Maximally-connected same-colour group containing `start`."""
    colour = board[start]
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for nb in _neighbors(c, r, size):
            if nb not in seen and board.get(nb) == colour:
                seen.add(nb)
                stack.append(nb)
    return seen


def _has_liberty(board: dict, group: set, size: int) -> bool:
    """True if any stone in `group` has an empty orthogonal neighbour."""
    for c, r in group:
        for nb in _neighbors(c, r, size):
            if nb not in board:
                return True
    return False


def _board_key(board: dict, size: int) -> str:
    """Canonical position key (only the stones matter, not whose turn)."""
    return "".join(
        "." if (c, r) not in board else ("B" if board[(c, r)] == BLACK else "W")
        for r in range(size)
        for c in range(size)
    )


@dataclass
class AtariGoState:
    size: int = 9
    board: dict = field(default_factory=dict)  # (c, r) -> 0/1
    to_move: int = BLACK
    winner: Optional[int] = None
    history: frozenset = field(default_factory=frozenset)  # seen board keys
    last_move: Optional[tuple] = None
    no_move_loss: bool = False  # player to move has no legal move -> they lose


def _resolve(board: dict, c: int, r: int, mover: int, size: int):
    """Apply a placement of `mover` at (c, r) on a COPY of `board`.

    Returns (new_board, captured_any). Removes enemy groups with no liberties
    first, then the mover's own group if it ended with no liberties. Does NOT
    enforce legality (suicide/superko) — callers do that.
    """
    nb = dict(board)
    nb[(c, r)] = mover
    enemy = 1 - mover
    captured = False
    # Resolve enemy captures BEFORE checking own group.
    checked: set = set()
    for ec, er in _neighbors(c, r, size):
        if nb.get((ec, er)) == enemy and (ec, er) not in checked:
            grp = _group(nb, (ec, er), size)
            checked |= grp
            if not _has_liberty(nb, grp, size):
                for cell in grp:
                    del nb[cell]
                captured = True
    if not captured:
        # Own group may now be self-captured (suicide candidate).
        own = _group(nb, (c, r), size)
        if not _has_liberty(nb, own, size):
            for cell in own:
                del nb[cell]
            # captured stays False -> this was a pure suicide.
    return nb, captured


class AtariGo(Game):
    uid = "atari_go"
    name = "Atari Go"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AtariGoState:
        size = int((options or {}).get("size", 9))
        s = AtariGoState(size=size)
        s.history = frozenset({_board_key(s.board, size)})
        return s

    def current_player(self, s: AtariGoState) -> int:
        return s.to_move

    def _legal(self, s: AtariGoState):
        """Yield (move_str, new_board, captured) for every legal placement."""
        for r in range(s.size):
            for c in range(s.size):
                if (c, r) in s.board:
                    continue
                nb, captured = _resolve(s.board, c, r, s.to_move, s.size)
                # Suicide: own group removed and nothing captured.
                if not captured and (c, r) not in nb:
                    continue
                # Positional superko: must not recreate a prior board.
                if _board_key(nb, s.size) in s.history:
                    continue
                yield f"{c},{r}", nb, captured

    def legal_moves(self, s: AtariGoState) -> list[str]:
        if s.winner is not None or s.no_move_loss:
            return []
        return [m for m, _nb, _cap in self._legal(s)]

    def apply_move(self, s: AtariGoState, move: str, rng=None) -> AtariGoState:
        c, r = _cell(move)
        nb, captured = _resolve(s.board, c, r, s.to_move, s.size)
        winner = s.to_move if captured else None
        new_history = s.history | {_board_key(nb, s.size)}
        nxt = AtariGoState(
            size=s.size,
            board=nb,
            to_move=1 - s.to_move,
            winner=winner,
            history=new_history,
            last_move=(c, r),
        )
        # If the game isn't already won, check whether the next player is stuck.
        if winner is None:
            if not any(True for _ in self._legal(nxt)):
                nxt.no_move_loss = True
        return nxt

    def is_terminal(self, s: AtariGoState) -> bool:
        return s.winner is not None or s.no_move_loss

    def returns(self, s: AtariGoState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        if s.no_move_loss:
            # The player to move (s.to_move) has no legal move and loses.
            loser = s.to_move
            return [-1.0, 1.0] if loser == BLACK else [1.0, -1.0]
        return [0.0, 0.0]

    def serialize(self, s: AtariGoState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "history": sorted(s.history),
            "last_move": list(s.last_move) if s.last_move is not None else None,
            "no_move_loss": s.no_move_loss,
        }

    def deserialize(self, d: dict) -> AtariGoState:
        return AtariGoState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            history=frozenset(d.get("history", [])),
            last_move=tuple(d["last_move"]) if d.get("last_move") is not None else None,
            no_move_loss=d.get("no_move_loss", False),
        )

    def describe_move(self, s: AtariGoState, move: str) -> str:
        c, r = _cell(move)
        letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"  # Go convention skips 'I'
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{s.size - r}"  # row 0 drawn at top -> highest number

    def render(self, s: AtariGoState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        highlights = []
        if s.last_move is not None:
            highlights.append({"cell": f"{s.last_move[0]},{s.last_move[1]}", "kind": "last-move"})
        if s.winner is not None:
            caption = f"{names[s.winner]} wins (first capture)"
        elif s.no_move_loss:
            caption = f"{names[s.to_move]} has no legal move and loses"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
