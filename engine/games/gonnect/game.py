"""Gonnect (João Pedro Neto, 2000) — a connection game played with Go rules.

Played on an N×N board of intersections. Players alternate placing one stone of
their colour on an empty intersection; Black (player 0) moves first. Standard Go
captures apply: after a placement, any enemy group (4-orthogonal adjacency) left
with zero liberties is removed (enemy captures are resolved BEFORE the mover's
own group). SUICIDE is illegal and POSITIONAL SUPERKO forbids recreating any
prior whole-board position.

The WIN CONDITION is **connection**, not capture or territory: a player wins by
linking their two OPPOSITE board edges with an unbroken 4-orthogonally-connected
chain of their own stones.
  * Black (player 0) connects the TOP edge (row 0) to the BOTTOM edge (row N-1).
  * White (player 1) connects the LEFT edge (col 0) to the RIGHT edge (col N-1).
Because a capture can break an existing chain, the connection is always checked
on the POST-CAPTURE board.

As in Go there is **no passing** (passing is not allowed / loses): a player with
no legal move loses.

The Go liberty/group-capture logic mirrors `games/atari_go`; the edge-connection
win check mirrors `games/hex` (but on a square board with 4-orthogonal adjacency).

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


def _connects(board: dict, player: int, size: int) -> bool:
    """Does `player` link their two opposite edges with a 4-orthogonal chain?

    Black (0): TOP row (r=0) -> BOTTOM row (r=size-1).
    White (1): LEFT col (c=0) -> RIGHT col (c=size-1).
    BFS over the player's stones starting from those touching one edge.
    """
    if player == BLACK:  # top (r=0) -> bottom (r=size-1)
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == BLACK]
        at_goal = lambda cell: cell[1] == size - 1  # noqa: E731
    else:  # left (c=0) -> right (c=size-1)
        starts = [(0, r) for r in range(size) if board.get((0, r)) == WHITE]
        at_goal = lambda cell: cell[0] == size - 1  # noqa: E731
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        for nb in _neighbors(cur[0], cur[1], size):
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return False


@dataclass
class GonnectState:
    size: int = 9
    board: dict = field(default_factory=dict)  # (c, r) -> 0/1
    to_move: int = BLACK
    winner: Optional[int] = None
    history: frozenset = field(default_factory=frozenset)  # seen board keys
    last_move: Optional[tuple] = None
    no_move_loss: bool = False  # player to move has no legal move -> they lose


class Gonnect(Game):
    name = "Gonnect"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> GonnectState:
        size = int((options or {}).get("size", 9))
        s = GonnectState(size=size)
        s.history = frozenset({_board_key(s.board, size)})
        return s

    def current_player(self, s: GonnectState) -> int:
        return s.to_move

    def _legal(self, s: GonnectState):
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

    def legal_moves(self, s: GonnectState) -> list[str]:
        if s.winner is not None or s.no_move_loss:
            return []
        return [m for m, _nb, _cap in self._legal(s)]

    def apply_move(self, s: GonnectState, move: str, rng=None) -> GonnectState:
        c, r = _cell(move)
        nb, _captured = _resolve(s.board, c, r, s.to_move, s.size)
        # Connection is checked on the POST-CAPTURE board (captures can break a
        # chain, so only the mover can win on their own move).
        winner = s.to_move if _connects(nb, s.to_move, s.size) else None
        new_history = s.history | {_board_key(nb, s.size)}
        nxt = GonnectState(
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

    def is_terminal(self, s: GonnectState) -> bool:
        return s.winner is not None or s.no_move_loss

    def returns(self, s: GonnectState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        if s.no_move_loss:
            # The player to move (s.to_move) has no legal move and loses.
            loser = s.to_move
            return [-1.0, 1.0] if loser == BLACK else [1.0, -1.0]
        return [0.0, 0.0]

    def serialize(self, s: GonnectState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "history": sorted(s.history),
            "last_move": list(s.last_move) if s.last_move is not None else None,
            "no_move_loss": s.no_move_loss,
        }

    def deserialize(self, d: dict) -> GonnectState:
        return GonnectState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            history=frozenset(d.get("history", [])),
            last_move=tuple(d["last_move"]) if d.get("last_move") is not None else None,
            no_move_loss=d.get("no_move_loss", False),
        )

    def describe_move(self, s: GonnectState, move: str) -> str:
        c, r = _cell(move)
        letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"  # Go convention skips 'I'
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{s.size - r}"  # row 0 drawn at top -> highest number

    def render(self, s: GonnectState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        highlights = []
        if s.last_move is not None:
            highlights.append(
                {"cell": f"{s.last_move[0]},{s.last_move[1]}", "kind": "last-move"}
            )
        if s.winner is not None:
            caption = f"{names[s.winner]} wins (connection)"
        elif s.no_move_loss:
            caption = f"{names[s.to_move]} has no legal move and loses"
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
