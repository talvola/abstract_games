"""Hex — the classic connection game (Piet Hein 1942 / John Nash 1948).

Played on an N×N rhombus of hexagons (11 is traditional). Players alternate
placing one stone of their colour on any empty cell. You win by forming an
unbroken chain of your stones connecting your two opposite edges:
  * player 0 (Red)  links the TOP edge (r=0) to the BOTTOM edge (r=N-1);
  * player 1 (Blue) links the LEFT edge (c=0) to the RIGHT edge (c=N-1).
A famous theorem: Hex can never end in a draw — once the board fills, exactly
one player has connected. So termination is automatic (≤ N² moves).

Moves are single cells "c,r" (a placement), plus the pie-rule action "swap"
offered to the second player on move 2: instead of placing, they may take the
opening by reflecting it across the main diagonal and recolouring it (Hex is
symmetric under that reflection + colour swap), which equalises first-move
advantage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1


def _neighbors(c: int, r: int):
    return [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1), (c + 1, r - 1), (c - 1, r + 1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


PIE_RULE = True  # offer the second player a "swap" on move 2


@dataclass
class HexState:
    size: int = 11
    board: dict = field(default_factory=dict)  # (c, r) -> 0/1
    to_move: int = RED
    winner: Optional[int] = None
    ply: int = 0


def _connects(board: dict, player: int, size: int) -> bool:
    """Does `player` link their two opposite edges?"""
    if player == RED:  # top (r=0) -> bottom (r=size-1)
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == RED]
        at_goal = lambda cell: cell[1] == size - 1  # noqa: E731
    else:              # left (c=0) -> right (c=size-1)
        starts = [(0, r) for r in range(size) if board.get((0, r)) == BLUE]
        at_goal = lambda cell: cell[0] == size - 1  # noqa: E731
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        for nb in _neighbors(*cur):
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return False


class Hex(Game):
    uid = "hex"
    name = "Hex"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HexState:
        size = int((options or {}).get("size", 11))
        return HexState(size=size)

    def current_player(self, s: HexState) -> int:
        return s.to_move

    def legal_moves(self, s: HexState) -> list[str]:
        if s.winner is not None:
            return []
        moves = [
            f"{c},{r}"
            for r in range(s.size)
            for c in range(s.size)
            if (c, r) not in s.board
        ]
        if PIE_RULE and s.ply == 1:  # second player's first turn
            moves.append("swap")
        return moves

    def apply_move(self, s: HexState, move: str, rng=None) -> HexState:
        if move == "swap":
            # take the opening: reflect the lone stone across c<->r, recolour to mover
            (c, r), _ = next(iter(s.board.items()))
            return HexState(size=s.size, board={(r, c): s.to_move},
                            to_move=1 - s.to_move, winner=None, ply=s.ply + 1)
        c, r = _cell(move)
        board = dict(s.board)
        board[(c, r)] = s.to_move
        winner = s.to_move if _connects(board, s.to_move, s.size) else None
        return HexState(size=s.size, board=board, to_move=1 - s.to_move,
                        winner=winner, ply=s.ply + 1)

    def is_terminal(self, s: HexState) -> bool:
        return s.winner is not None

    def returns(self, s: HexState) -> list[float]:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # unreachable in a real game (no draws)

    def serialize(self, s: HexState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> HexState:
        return HexState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            ply=d.get("ply", len(d["board"])),
        )

    def describe_move(self, s: HexState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        c, r = _cell(move)
        letters = "abcdefghijklmnopqrstuvwxyz"
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def render(self, s: HexState, perspective=None) -> dict:
        names = {RED: "Red", BLUE: "Blue"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""} for (c, r), p in s.board.items()]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        else:
            edge = "top–bottom" if s.to_move == RED else "left–right"
            caption = f"{names[s.to_move]} to move ({edge})"
        return {
            "board": {
                "type": "hex", "shape": "rhombus", "width": s.size, "height": s.size,
                "edges": {"top": RED, "bottom": RED, "left": BLUE, "right": BLUE},
            },
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
