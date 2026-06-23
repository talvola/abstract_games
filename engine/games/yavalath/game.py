"""Yavalath, by Cameron Browne (2007) — the famous computer-designed game.

Yavalath is the hex analogue of Squava: a misère/positive hybrid n-in-a-row
played on a hexagonal board of hexagons (a "hexhex") of side length 5 = 61
cells. It was discovered in November 2007 by the LUDI system (an evolutionary
game-design program) guided by Cameron Browne, and published by nestorgames.

Two players alternately place one stone of their colour on any empty cell.
Stones never move and are never captured (exactly like Hex / Gomoku) — the game
is **placement only**.

After a player places a stone, the lines through that stone along the three hex
axes are evaluated:

  * If the placer now has **four or more** of their stones in an unbroken row,
    the placer **WINS** immediately.
  * Otherwise, if the placer now has **exactly three** in a row (and no four),
    the placer **LOSES** immediately. This is the misère twist: you are
    forbidden from making three-in-a-row unless it is part of a four.
  * **Four takes precedence**: a placement that simultaneously makes a three AND
    a four counts as a four — and therefore a **WIN**.

If the board fills (61 stones) with no four and no decisive three, the game is a
**DRAW**. There are no captures or movement, so the game always terminates in at
most 61 placements.

Coordinates are axial (q, r); the third cube coordinate is s = -q-r. A cell is
on the board iff max(|q|, |r|, |s|) <= 4. The three line axes are the three pairs
of opposite hex directions: (q+1,r)/(q-1,r), (q,r+1)/(q,r-1), and
(q+1,r-1)/(q-1,r+1).

Yavalath has a known first-player advantage; a common fix is a pie / swap rule
offered to the second player on their first turn. This package implements the
base game and offers the swap as the optional ``pie`` move (the manifest ``pie``
option, default ON), mirroring the platform's other placement games.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}

WIN_LEN = 4
LOSE_LEN = 3

SIDE = 5  # hexagon side length (cells per side) -> 61 cells

# The three line axes on a hex board: each is one (dq, dr) direction whose
# opposite (-dq, -dr) completes the line.
AXES = [(1, 0), (0, 1), (1, -1)]


def _neighbors(q: int, r: int):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1), (q + 1, r - 1), (q - 1, r + 1)]


@lru_cache(maxsize=None)
def _cells(side: int) -> tuple:
    """All on-board axial cells of a hexhex of side ``side`` (max coord = side-1)."""
    out = []
    n = side - 1
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            s = -q - r
            if abs(q) <= n and abs(r) <= n and abs(s) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(side: int) -> frozenset:
    return frozenset(_cells(side))


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


def _max_run(board: dict, cell, player: int) -> int:
    """Longest unbroken run of ``player``'s stones through ``cell`` over the 3 hex axes."""
    q, r = cell
    best = 1
    for dq, dr in AXES:
        run = 1
        for sign in (1, -1):
            cq, cr = q + dq * sign, r + dr * sign
            while board.get((cq, cr)) == player:
                run += 1
                cq += dq * sign
                cr += dr * sign
        if run > best:
            best = run
    return best


@dataclass
class YavalathState:
    side: int = SIDE
    board: dict = field(default_factory=dict)   # (q, r) -> player
    to_move: int = WHITE
    winner: Optional[int] = None                 # seat index that won, or None
    last: Optional[tuple] = None                 # last placed cell
    ply: int = 0
    pie: bool = True


class Yavalath(Game):
    uid = "yavalath"
    name = "Yavalath"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> YavalathState:
        opts = options or {}
        side = int(opts.get("size", SIDE))
        pie = bool(opts.get("pie", True))
        return YavalathState(side=side, pie=pie)

    def current_player(self, s: YavalathState) -> int:
        return s.to_move

    def legal_moves(self, s: YavalathState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = [f"{q},{r}" for (q, r) in _cells(s.side) if (q, r) not in s.board]
        if s.pie and s.ply == 1:  # second player's first turn
            moves.append("swap")
        return moves

    def _outcome(self, board: dict, cell, player: int) -> Optional[int]:
        """Winner after ``player`` placed at ``cell``, or None if play continues.

        Four-or-more in a row  -> placer wins (returns player).
        Exactly three (no four) -> placer loses (returns opponent).
        Otherwise               -> None.

        Four takes precedence because we test the longest run: a placement that
        makes both a 3 and a 4 reports run >= 4 (a win).
        """
        run = _max_run(board, cell, player)
        if run >= WIN_LEN:
            return player
        if run == LOSE_LEN:
            return 1 - player
        return None

    def apply_move(self, s: YavalathState, move: str, rng=None) -> YavalathState:
        if move == "swap":
            if not (s.pie and s.ply == 1):
                raise ValueError("swap not available")
            (cell, _), = list(s.board.items())
            board = {cell: s.to_move}
            return YavalathState(side=s.side, board=board, to_move=1 - s.to_move,
                                 last=cell, ply=s.ply + 1, pie=s.pie)
        cell = _cell(move)
        if cell not in _cell_set(s.side) or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        mover = s.to_move
        board = dict(s.board)
        board[cell] = mover
        winner = self._outcome(board, cell, mover)
        return YavalathState(
            side=s.side, board=board, to_move=1 - mover,
            winner=winner, last=cell, ply=s.ply + 1, pie=s.pie,
        )

    def is_terminal(self, s: YavalathState) -> bool:
        if s.winner is not None:
            return True
        return len(s.board) >= len(_cells(s.side))  # full board -> draw

    def returns(self, s: YavalathState) -> list[float]:
        if s.winner == WHITE:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: YavalathState) -> dict:
        return {
            "side": s.side,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "ply": s.ply,
            "pie": s.pie,
        }

    def deserialize(self, d: dict) -> YavalathState:
        last = d.get("last")
        return YavalathState(
            side=d.get("side", SIDE),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            last=(_cell(last) if last else None),
            ply=d.get("ply", len(d["board"])),
            pie=d.get("pie", True),
        )

    def describe_move(self, s: YavalathState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        return f"{NAMES[s.to_move][0]}:{move}"

    def render(self, s: YavalathState, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": p, "label": ""}
                  for (q, r), p in s.board.items()]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw (full board)"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.side},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
