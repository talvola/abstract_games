"""Crossway — a connection game by Mark Steere (2007).

Played with a Go set (traditionally 19x19). Players alternate placing one
stone of their colour on any empty cell. Stones connect to neighbours via the
8 orthogonal AND diagonal adjacencies, and you win by forming an unbroken chain
of your stones joining your two opposite edges:
  * Black (player 0) links the TOP (North) edge to the BOTTOM (South) edge;
  * White (player 1) links the LEFT (West) edge to the RIGHT (East) edge.
A corner counts as part of BOTH adjoining edges.

The signature CROSSWAY rule is a PLACEMENT RESTRICTION, not a connectivity
tweak: "A player must never complete the formation [a 2x2 checkerboard] or a
90-degree rotation of it." The forbidden 2x2 squares are

      B W            W B
      W B    and     B W

i.e. a 2x2 in which the two diagonals are filled with opposite colours, so the
two diagonal links would CROSS. Because that pattern can never appear, no two
opposite-colour diagonal connections ever cross — connectivity is then plain
8-adjacency. (Source: Mark Steere's official Crossway rule sheet,
marksteeregames.com, May 2007.)

If a player has NO legal placement, they forfeit (pass) and the opponent keeps
placing. Crossway can never end in a draw — exactly one player connects. So
termination is automatic. Crossway uses the pie rule: on move 2 White may
"swap" — take over Black's opening. Because the goals are transposed (Black
joins rows, White joins columns), the swap reflects Black's lone stone across
the main diagonal (c,r)->(r,c) and recolours it White, which preserves its
value; recolouring in place would not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # player 0 = Black (top<->bottom), player 1 = White (left<->right)

# 8-connectivity: orthogonal + diagonal neighbours.
_DIRS8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


PIE_RULE = True  # offer White a "swap" on move 2


@dataclass
class CrosswayState:
    size: int = 13
    board: dict = field(default_factory=dict)  # (c, r) -> 0/1
    to_move: int = BLACK
    winner: Optional[int] = None
    ply: int = 0


def _completes_crossing(board: dict, c: int, r: int, player: int) -> bool:
    """Would placing `player`'s stone at (c, r) complete a forbidden 2x2
    checkerboard (an X-crossing of opposite-colour diagonals)?

    A 2x2 square is forbidden when its two diagonals each hold one colour and
    the two colours differ. The placed stone sits at one corner of the 2x2; we
    check each of the four 2x2 squares containing (c, r): the diagonally
    opposite corner must be `player` (same colour, completing player's
    diagonal) while BOTH of the other two corners are the opponent (their
    crossing diagonal). That is exactly the Figure-2 pattern and its rotation.
    """
    opp = 1 - player
    # The four 2x2 squares that include (c, r); (dc, dr) = the diagonal partner.
    for dc, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        diag = board.get((c + dc, r + dr))      # opposite corner of the 2x2
        side1 = board.get((c + dc, r))          # the two "crossing" cells
        side2 = board.get((c, r + dr))
        if diag == player and side1 == opp and side2 == opp:
            return True
    return False


def _connects(board: dict, player: int, size: int) -> bool:
    """Does `player` link their two opposite edges via an 8-connected chain?"""
    if player == BLACK:  # top (r=0) -> bottom (r=size-1)
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == BLACK]
        at_goal = lambda cell: cell[1] == size - 1  # noqa: E731
    else:                # left (c=0) -> right (c=size-1)
        starts = [(0, r) for r in range(size) if board.get((0, r)) == WHITE]
        at_goal = lambda cell: cell[0] == size - 1  # noqa: E731
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        cc, cr = cur
        for dc, dr in _DIRS8:
            nb = (cc + dc, cr + dr)
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return False


class Crossway(Game):
    uid = "crossway"
    name = "Crossway"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CrosswayState:
        size = int((options or {}).get("size", 13))
        return CrosswayState(size=size)

    def current_player(self, s: CrosswayState) -> int:
        return s.to_move

    def _placements(self, s: CrosswayState) -> list[str]:
        """Empty cells where `to_move` may legally place (no crossing formed)."""
        return [
            f"{c},{r}"
            for r in range(s.size)
            for c in range(s.size)
            if (c, r) not in s.board
            and not _completes_crossing(s.board, c, r, s.to_move)
        ]

    def legal_moves(self, s: CrosswayState) -> list[str]:
        if s.winner is not None:
            return []
        moves = self._placements(s)
        # No legal placement -> the player forfeits (pass); never return [].
        if not moves:
            return ["pass"]
        if PIE_RULE and s.ply == 1:  # White's first turn
            moves.append("swap")
        return moves

    def apply_move(self, s: CrosswayState, move: str, rng=None) -> CrosswayState:
        if move == "pass":
            return CrosswayState(size=s.size, board=dict(s.board),
                                 to_move=1 - s.to_move, winner=s.winner,
                                 ply=s.ply + 1)
        if move == "swap":
            # Pie rule ("change sides"): White takes over Black's opening.
            # Crossway's goals are transposed (Black joins top<->bottom rows,
            # White joins left<->right columns), so the value-preserving swap
            # reflects the lone stone across the main diagonal (c,r)->(r,c) and
            # recolours it White. Recolouring in place would NOT preserve value
            # (the colours aim at different edges). Same convention as Rhode/
            # Cation/Konobi.
            (c, r), _ = next(iter(s.board.items()))
            return CrosswayState(size=s.size, board={(r, c): s.to_move},
                                 to_move=1 - s.to_move, winner=None, ply=s.ply + 1)
        c, r = _cell(move)
        board = dict(s.board)
        board[(c, r)] = s.to_move
        winner = s.to_move if _connects(board, s.to_move, s.size) else None
        return CrosswayState(size=s.size, board=board, to_move=1 - s.to_move,
                             winner=winner, ply=s.ply + 1)

    def is_terminal(self, s: CrosswayState) -> bool:
        return s.winner is not None

    def returns(self, s: CrosswayState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # unreachable in a real game (no draws)

    def serialize(self, s: CrosswayState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> CrosswayState:
        return CrosswayState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            ply=d.get("ply", len(d["board"])),
        )

    def describe_move(self, s: CrosswayState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if move == "pass":
            return "pass (no placement)"
        c, r = _cell(move)
        letters = "abcdefghijklmnopqrstuvwxyz"
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def render(self, s: CrosswayState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        else:
            edge = "top–bottom" if s.to_move == BLACK else "left–right"
            caption = f"{names[s.to_move]} to move ({edge})"
        return {
            "board": {
                "type": "square", "width": s.size, "height": s.size,
                # Black goal = N/S edges; White goal = W/E edges.
                "edges": {"top": BLACK, "bottom": BLACK, "left": WHITE, "right": WHITE},
            },
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
