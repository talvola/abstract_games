"""Oust, by Mark Steere (2007) -- https://www.marksteeregames.com/

Rules (paraphrased from the official sheet):
* Hexagonal board, empty to start. Red (player 0) and Blue (player 1) alternate
  placing a stone of their colour on any empty cell.
* A *group* is a set of connected like-coloured stones (a lone stone is a group).
* NON-CAPTURING placement: connects to no stones, or only to enemy stones. It is
  always legal and ENDS your turn.
* CAPTURING placement: connects to one or more of your OWN groups, forming a new
  larger group. Legal only if that new group touches >=1 enemy group AND every
  touched enemy group is strictly smaller than the new group; all those enemy
  groups are then removed.
* After a capture you MUST keep placing until you make a non-capturing placement,
  which ends the turn (or until you have no legal placement).
* If you have no legal placement on your turn you pass. The rules guarantee at
  least one player always has a placement, so the game never deadlocks.
* You WIN by making a placement that captures ALL enemy stones. Draws cannot occur.

The win is an *event* (a capture that empties the opponent), not a board
predicate -- at the opening both sides have zero stones -- so the state carries
an explicit ``winner``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1


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


@dataclass
class OustState:
    size: int = 5
    board: dict = field(default_factory=dict)  # (q, r) -> 0/1
    to_move: int = RED
    winner: Optional[int] = None


def _find_group(board: dict, start: tuple) -> set:
    color = board.get(start)
    if color is None:
        return set()
    seen, stack = {start}, [start]
    while stack:
        cq, cr = stack.pop()
        for nb in _neighbors(cq, cr):
            if nb not in seen and board.get(nb) == color:
                seen.add(nb)
                stack.append(nb)
    return seen


def _classify(board: dict, q: int, r: int, player: int):
    """Return ('invalid'|'non-capturing'|'capturing', captured_cells)."""
    if (q, r) in board:
        return "invalid", None

    enemy = 1 - player
    has_friendly = any(board.get(nb) == player for nb in _neighbors(q, r))
    if not has_friendly:
        return "non-capturing", None

    # Build the merged friendly group that would include the placed stone.
    new_group = {(q, r)}
    stack = [(q, r)]
    while stack:
        cq, cr = stack.pop()
        for nb in _neighbors(cq, cr):
            if nb not in new_group and board.get(nb) == player:
                new_group.add(nb)
                stack.append(nb)

    # Enemy groups adjacent to the new group.
    enemy_groups, seen_enemy = [], set()
    for (mq, mr) in new_group:
        for nb in _neighbors(mq, mr):
            if board.get(nb) == enemy and nb not in seen_enemy:
                grp = _find_group(board, nb)
                seen_enemy |= grp
                enemy_groups.append(grp)

    if not enemy_groups:
        return "invalid", None
    new_size = len(new_group)
    if any(len(g) >= new_size for g in enemy_groups):
        return "invalid", None

    captured = set()
    for g in enemy_groups:
        captured |= g
    return "capturing", captured


def _valid_placements(state: OustState, player: int) -> list[tuple]:
    out = []
    for (q, r) in _cells(state.size):
        if (q, r) in state.board:
            continue
        kind, _ = _classify(state.board, q, r, player)
        if kind != "invalid":
            out.append((q, r))
    return out


class Oust(Game):
    uid = "oust"
    name = "Oust"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> OustState:
        size = int((options or {}).get("size", 5))
        return OustState(size=size)

    def current_player(self, s: OustState) -> int:
        return s.to_move

    def legal_moves(self, s: OustState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{q},{r}" for (q, r) in _valid_placements(s, s.to_move)]

    def apply_move(self, s: OustState, move: str, rng=None) -> OustState:
        q, r = _cell(move)
        mover = s.to_move
        kind, captured = _classify(s.board, q, r, mover)
        if kind == "invalid":
            raise ValueError(f"illegal move {move!r} for player {mover}")

        board = dict(s.board)
        board[(q, r)] = mover

        if kind == "non-capturing":
            return self._advance(s.size, board, mover)

        # capturing
        for c in captured:
            del board[c]
        enemy = 1 - mover
        if not any(v == enemy for v in board.values()):
            return OustState(size=s.size, board=board, to_move=mover, winner=mover)

        nxt = OustState(size=s.size, board=board, to_move=mover)
        if _valid_placements(nxt, mover):
            return nxt  # must keep placing -- same player's turn continues
        return self._advance(s.size, board, mover)

    def _advance(self, size: int, board: dict, just_moved: int) -> OustState:
        """End ``just_moved``'s turn: hand to the opponent, skipping a player
        who cannot place (a pass)."""
        opp = 1 - just_moved
        probe = OustState(size=size, board=board, to_move=opp)
        if _valid_placements(probe, opp):
            return OustState(size=size, board=board, to_move=opp)
        # Opponent passes; back to the player who just moved.
        if _valid_placements(probe, just_moved):
            return OustState(size=size, board=board, to_move=just_moved)
        # Safety net: rules guarantee this can't happen (no draws). Resolve by
        # stone count so the engine never deadlocks.
        red = sum(1 for v in board.values() if v == RED)
        blue = len(board) - red
        winner = RED if red >= blue else BLUE
        return OustState(size=size, board=board, to_move=just_moved, winner=winner)

    def is_terminal(self, s: OustState) -> bool:
        return s.winner is not None

    def returns(self, s: OustState) -> list[float]:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: OustState) -> dict:
        return {
            "size": s.size,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> OustState:
        return OustState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
        )

    def render(self, s: OustState, perspective=None) -> dict:
        names = {RED: "Red", BLUE: "Blue"}
        pieces = [
            {"cell": f"{q},{r}", "owner": p, "label": ""}
            for (q, r), p in s.board.items()
        ]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
