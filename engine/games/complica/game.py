"""Complica — Reiner Knizia's Connect-4 variant with column-push (1991).

A 4-wide, 7-tall grid. On your turn you choose a column and drop a disc into it:

  * If the column is NOT full, the disc stacks on top (falls to the lowest empty
    cell), exactly like Connect Four.
  * If the column IS full, the whole column is pushed DOWN by one row: the bottom
    disc falls off the board, every disc drops one row, and your new disc enters
    at the very top.

Because full columns cycle, the board can change radically each move and a single
move can complete lines for either player. First to make four of their own discs
in a line — horizontal, vertical, or diagonal — wins. The end-of-game check is
symmetric (not "the mover"): after a move we count fours for BOTH players; the
game ends only when EXACTLY ONE player has a four-in-a-row (that player wins). If
a move gives BOTH players a four simultaneously, nobody wins and play continues.

There is no natural draw (a full column just cycles, so there are always four
legal moves), so a hard ply-cap draw backstop guarantees termination.

Cells are "col,row" with row 0 at the BOTTOM, col 0 at the LEFT (cols 0..3, rows
0..6). A move is the single COLUMN index as a 1-based string ("1".."4"), which the
generic UI renders as four column buttons. Player 0 = Red, 1 = Yellow.

Faithful to AbstractPlay's open-source `gameslib` Complica implementation
(src/games/complica.ts): 4x7 board, fill-from-bottom drop, push-down-on-full with
the bottom disc dropping off and the new disc entering at the top, and the
"only-one-player-has-four ends the game" win rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WIDTH, HEIGHT, CONNECT = 4, 7, 4
NAMES = {0: "Red", 1: "Yellow"}
# line directions to scan (both signs are walked, so these cover all 4 axes)
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
# hard draw backstop: cycling columns mean the game can loop forever
PLY_CAP = 300


@dataclass
class ComplicaState:
    board: dict = field(default_factory=dict)   # (col, row) -> player
    to_move: int = 0
    winner: Optional[int] = None
    plies: int = 0


class Complica(Game):
    name = "Complica"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ComplicaState:
        return ComplicaState()

    def current_player(self, s: ComplicaState) -> int:
        return s.to_move

    def legal_moves(self, s: ComplicaState) -> list[str]:
        if self.is_terminal(s):
            return []
        # every column is always playable (full columns push), so all 4 columns
        return [str(c + 1) for c in range(WIDTH)]

    # ---- helpers -----------------------------------------------------------

    @staticmethod
    def _lowest_empty(board: dict, col: int) -> Optional[int]:
        """Lowest empty row in `col` (0 = bottom), or None if the column is full."""
        for r in range(HEIGHT):
            if (col, r) not in board:
                return r
        return None

    def _drop(self, board: dict, col: int, player: int) -> None:
        """Mutate `board`: drop a disc for `player` into `col` (stack or push)."""
        r = self._lowest_empty(board, col)
        if r is not None:
            board[(col, r)] = player
            return
        # column full -> push down one: bottom (row 0) drops off, then top gets disc
        for row in range(HEIGHT - 1):
            board[(col, row)] = board[(col, row + 1)]
        board[(col, HEIGHT - 1)] = player

    @staticmethod
    def _has_four(board: dict, player: int) -> bool:
        for (c, r), p in board.items():
            if p != player:
                continue
            for dc, dr in DIRS:
                run = 1
                cc, rr = c + dc, r + dr
                while board.get((cc, rr)) == player:
                    run += 1
                    if run >= CONNECT:
                        return True
                    cc += dc
                    rr += dr
        return False

    # ---- core --------------------------------------------------------------

    def apply_move(self, s: ComplicaState, move: str, rng=None) -> ComplicaState:
        col = int(move) - 1
        board = dict(s.board)
        self._drop(board, col, s.to_move)
        # symmetric end check: game ends only when EXACTLY ONE player has a four
        f0 = self._has_four(board, 0)
        f1 = self._has_four(board, 1)
        winner = None
        if f0 != f1:
            winner = 0 if f0 else 1
        return ComplicaState(
            board=board,
            to_move=1 - s.to_move,
            winner=winner,
            plies=s.plies + 1,
        )

    def is_terminal(self, s: ComplicaState) -> bool:
        return s.winner is not None or s.plies >= PLY_CAP

    def returns(self, s: ComplicaState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- serialization -----------------------------------------------------

    def serialize(self, s: ComplicaState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "plies": s.plies,
        }

    def deserialize(self, d: dict) -> ComplicaState:
        board = {}
        for k, v in d["board"].items():
            c, r = k.split(",")
            board[(int(c), int(r))] = v
        return ComplicaState(
            board=board,
            to_move=d["to_move"],
            winner=d["winner"],
            plies=d.get("plies", 0),
        )

    def describe_move(self, s: ComplicaState, move: str) -> str:
        col = int(move)
        full = self._lowest_empty(s.board, col - 1) is None
        verb = "push col" if full else "drop col"
        return f"{NAMES[s.to_move][0]}:{verb} {col}"

    # ---- render ------------------------------------------------------------

    def render(self, s: ComplicaState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw (ply cap)"
        else:
            caption = f"{NAMES[s.to_move]} to move — pick a column"
        return {
            "board": {"type": "square", "width": WIDTH, "height": HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
