"""Alvéole — Lines of Action on a hexagonal board (Cédric Leclinche).

Alvéole ("honeycomb") is a Lines-of-Action variant played on a *hexhex* board
of 5 cells per side (61 cells). Each player has 9 pieces set on the perimeter.

A move: pick one of your pieces and slide it in one of the SIX hex directions a
distance EXACTLY equal to the total number of pieces (both colours) standing on
that whole line — the line through the piece along that axis, counting the
piece itself + every piece ahead of it + every piece behind it. You may JUMP
OVER your own pieces but may NOT land on one; you may NOT jump over an enemy
piece; landing on an enemy piece CAPTURES it (it is removed).

You win by gathering ALL your surviving pieces into a single connected group
(6-adjacency); a lone piece counts as connected. Connection is checked after
every move, so:
  * if your move connects YOUR pieces, you win — even if it also connects the
    opponent (simultaneous connection = the MOVER wins, per the reference);
  * a capture that leaves the OPPONENT in one connected group makes THEM win
    (reducing the enemy to a single connected mass, incl. to one piece, is a
    loss for the capturer).

If the player to move has no legal move, they lose. A hard ply cap declares an
honest draw so random play always terminates.

This mirrors the author's open-source BGA implementation
(github.com/devoreve/alveole): its doubled-coordinate move generation, capture
rule, 6-neighbour connectivity win, mover-wins-on-simultaneous check, and the
exact 9-piece starting layout, all re-expressed here in axial (q,r) coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

SIZE = 5           # cells per side of the hexhex board
PLY_CAP = 300      # random-play termination backstop -> honest draw

# The three hex line-axes (each used in both directions via sign ±1).
AXES = [(1, 0), (0, 1), (1, -1)]
# Full 6-neighbourhood for the connected-group win.
NEIGHBORS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    """All on-board axial cells of a hexhex of side ``size``."""
    out = []
    n = size - 1
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            if abs(q) <= n and abs(r) <= n and abs(q + r) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


def _on(size: int, q: int, r: int) -> bool:
    return (q, r) in _cell_set(size)


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


# --- starting layout ---------------------------------------------------------
# Extracted from the reference (setupNewGame, doubled coords x=col*2, y) and
# mapped to axial by q = x/2 - 4, r = y/2 - x/4 - 2. Both players hold 3
# alternating corners plus 6 more perimeter cells.
_RED_START = [
    (-4, 1), (-4, 4), (-3, -1), (-1, 4), (0, -4),
    (1, 3), (3, -4), (4, -3), (4, 0),
]
_BLUE_START = [
    (-4, 0), (-4, 3), (-3, 4), (-1, -3), (0, 4),
    (1, -4), (3, 1), (4, -4), (4, -1),
]


def _start_board() -> dict:
    b = {}
    for c in _RED_START:
        b[c] = 0
    for c in _BLUE_START:
        b[c] = 1
    return b


def _line_count(board: dict, size: int, q: int, r: int, dq: int, dr: int) -> int:
    """Pieces on the whole line through (q,r) along axis (dq,dr), incl. it."""
    count = 1
    for sgn in (1, -1):
        cq, cr = q + sgn * dq, r + sgn * dr
        while _on(size, cq, cr):
            if (cq, cr) in board:
                count += 1
            cq += sgn * dq
            cr += sgn * dr
    return count


def _connected(board: dict, player: int) -> bool:
    cells = [pos for pos, pl in board.items() if pl == player]
    if len(cells) <= 1:
        return True
    seen = {cells[0]}
    stack = [cells[0]]
    while stack:
        q, r = stack.pop()
        for dq, dr in NEIGHBORS:
            nb = (q + dq, r + dr)
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return len(seen) == len(cells)


@dataclass
class AlveoleState:
    board: dict = field(default_factory=dict)   # (q, r) -> 0/1
    to_move: int = 0
    winner: Optional[int] = None
    drawn: bool = False
    ply: int = 0


class Alveole(Game):
    name = "Alvéole"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AlveoleState:
        return AlveoleState(board=_start_board())

    def current_player(self, s: AlveoleState) -> int:
        return s.to_move

    def _raw_moves(self, s: AlveoleState) -> list[str]:
        board, player, out = s.board, s.to_move, []
        for (q, r), pl in list(board.items()):
            if pl != player:
                continue
            for dq, dr in AXES:
                d = _line_count(board, SIZE, q, r, dq, dr)
                for sgn in (1, -1):
                    sdq, sdr = sgn * dq, sgn * dr
                    tq, tr = q + sdq * d, r + sdr * d
                    if not _on(SIZE, tq, tr):
                        continue
                    # can't jump an enemy: any enemy strictly between = blocked.
                    blocked = any(
                        board.get((q + sdq * k, r + sdr * k)) not in (None, player)
                        for k in range(1, d)
                    )
                    if blocked or board.get((tq, tr)) == player:
                        continue
                    out.append(f"{q},{r}>{tq},{tr}")
        return out

    def is_terminal(self, s: AlveoleState) -> bool:
        return s.winner is not None or s.drawn or not self._raw_moves(s)

    def legal_moves(self, s: AlveoleState) -> list[str]:
        return [] if self.is_terminal(s) else self._raw_moves(s)

    def apply_move(self, s: AlveoleState, move: str, rng=None) -> AlveoleState:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        mover = s.to_move
        board = dict(s.board)
        del board[frm]
        board[to] = mover  # captures any enemy already on `to`

        p = _connected(board, mover)
        o = _connected(board, 1 - mover)
        winner, drawn = None, False
        if p:
            # Mover connected -> mover wins, even on simultaneous connection.
            winner = mover
        elif o:
            # A capture that leaves the opponent in one group hands them the win.
            winner = 1 - mover
        ply = s.ply + 1
        if winner is None and ply >= PLY_CAP:
            drawn = True
        return AlveoleState(board=board, to_move=1 - mover, winner=winner,
                            drawn=drawn, ply=ply)

    def returns(self, s: AlveoleState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        if s.drawn:
            return [0.0, 0.0]
        # terminal because the player to move has no move: they lose.
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: AlveoleState) -> dict:
        return {
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "drawn": s.drawn,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> AlveoleState:
        return AlveoleState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], winner=d["winner"],
            drawn=d.get("drawn", False), ply=d.get("ply", 0),
        )

    def describe_move(self, s: AlveoleState, move: str) -> str:
        fs, ts = move.split(">")
        to = _cell(ts)
        cap = to in s.board and s.board[to] != s.to_move
        return f"{fs}{'x' if cap else '-'}{ts}"

    def render(self, s: AlveoleState, perspective=None) -> dict:
        names = {0: "Red", 1: "Blue"}
        pieces = [{"cell": f"{q},{r}", "owner": p, "label": ""}
                  for (q, r), p in s.board.items()]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.drawn:
            caption = "Draw"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
