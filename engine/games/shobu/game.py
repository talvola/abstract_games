"""Shobu — Manny Vega & Jamie Sajdak (2019, Smirk & Dagger).

A two-player abstract played across FOUR 4x4 boards arranged in a 2x2
super-layout. Two boards are a DARK colour and two are LIGHT, arranged so each
player faces one dark + one light board. The two boards on a player's side of
the table are that player's HOME boards.

  super-layout (board index b at super-position (b%2, b//2)):

        +--------+--------+
        | b=2    | b=3    |    <- player 1's HOME row (far)
        | LIGHT  | DARK   |
        +--------+--------+
        | b=0    | b=1    |    <- player 0's HOME row (near)
        | DARK   | LIGHT  |
        +--------+--------+

DARK boards lie on one diagonal (b=0, b=3), LIGHT on the other (b=1, b=2), so
each player owns exactly one dark and one light home board.

Each board is a 4x4 grid of cells (c, r), c,r in 0..3. Each player has 4 stones
on EVERY board, on their nearest row of that board: player 0 on row r=0, player
1 on row r=3 (16 stones per player total).

A TURN = a PASSIVE move then a matching AGGRESSIVE move, both by the same player:

  * PASSIVE move: pick one of your stones on one of your two HOME boards and
    move it 1 or 2 squares in any of the 8 directions (orthogonal/diagonal).
    It may NOT push: every square it passes over and lands on must be EMPTY.

  * AGGRESSIVE move: move one of your stones the SAME direction and SAME
    distance, on a board of the OPPOSITE COLOUR to the board the passive move
    was made on (dark<->light). It MAY push: along the line of travel there may
    be AT MOST ONE stone, and that stone must be an OPPONENT's (never two
    stones, never your own). The pushed stone is shoved one further square in
    the move direction; the square it lands on must be empty OR off the board
    (off the board => the stone is removed from the game).

A passive move is only legal if a matching aggressive move also exists; the
engine surfaces only such passive moves, then constrains the aggressive choices.

WIN: the instant an opponent has NO stones left on ANY ONE of the four boards.

This is a "win as event" — checked after an aggressive (capturing) move and
stored in ``winner``. A hard ply cap forces a draw for termination safety (real
games end well before it).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

SIZE = 4
NBOARDS = 4
# Dark boards on one diagonal, light on the other.
DARK_BOARDS = frozenset({0, 3})
# Home boards by player: player 0 = near row (b//2 == 0), player 1 = far row.
HOME = {0: frozenset({0, 1}), 1: frozenset({2, 3})}
# A player's starting row on every board.
START_ROW = {0: 0, 1: 3}

# The 8 directions (dc, dr).
DIRS = [
    (dc, dr)
    for dc in (-1, 0, 1)
    for dr in (-1, 0, 1)
    if (dc, dr) != (0, 0)
]

# Hard ply cap (each ply = one full passive+aggressive turn). Real games end
# fast; this is purely a termination guarantee.
PLY_CAP = 200


def _is_dark(b: int) -> bool:
    return b in DARK_BOARDS


def _opp_colour_boards(b: int) -> list[int]:
    dark = _is_dark(b)
    return [ob for ob in range(NBOARDS) if _is_dark(ob) != dark]


def _key(b: int, c: int, r: int) -> str:
    return f"{b},{c},{r}"


def _parse_cell(s: str) -> tuple[int, int, int]:
    b, c, r = s.split(",")
    return int(b), int(c), int(r)


def _parse_move(move: str) -> tuple[tuple, tuple]:
    """'b,c,r>b,c2,r2' -> ((b,c,r),(b2,c2,r2))."""
    a, b = move.split(">")
    return _parse_cell(a), _parse_cell(b)


def _in_bounds(c: int, r: int) -> bool:
    return 0 <= c < SIZE and 0 <= r < SIZE


@dataclass
class ShobuState:
    # board -> {(c, r): player}
    boards: tuple = field(default_factory=tuple)
    to_move: int = 0
    # Pending passive: None, or (dc, dr, dist, passive_board) once a passive
    # move has been made this turn and we await the aggressive move.
    pending: Optional[tuple] = None
    winner: Optional[int] = None
    ply: int = 0  # number of completed full turns

    def board(self, b: int) -> dict:
        return self.boards[b]


def _initial_boards() -> tuple:
    boards = []
    for b in range(NBOARDS):
        cells: dict = {}
        for c in range(SIZE):
            cells[(c, START_ROW[0])] = 0
            cells[(c, START_ROW[1])] = 1
        boards.append(cells)
    return tuple(boards)


def _passive_moves(s: ShobuState, player: int) -> list[tuple]:
    """All (board, from, to, dc, dr, dist) legal no-push passive moves on
    ``player``'s home boards (ignoring the aggressive-match requirement)."""
    out = []
    for b in HOME[player]:
        cells = s.boards[b]
        for (c, r), owner in cells.items():
            if owner != player:
                continue
            for dc, dr in DIRS:
                for dist in (1, 2):
                    # Every traversed square (1..dist) must be in-bounds & empty.
                    ok = True
                    for k in range(1, dist + 1):
                        nc, nr = c + dc * k, r + dr * k
                        if not _in_bounds(nc, nr) or (nc, nr) in cells:
                            ok = False
                            break
                    if ok:
                        out.append((b, (c, r), (c + dc * dist, r + dr * dist),
                                    dc, dr, dist))
    return out


def _aggressive_result(cells: dict, c: int, r: int, dc: int, dr: int,
                       dist: int, player: int):
    """If the aggressive move from (c,r) by (dc,dr)*dist is legal on this board,
    return (dest, pushed_from, pushed_to_or_None) where pushed_to is None if the
    pushed stone goes off-board (removed). Else return None.

    Rule: along the line of travel (the ``dist`` squares the moving stone passes
    over/lands on) there may be AT MOST ONE stone, and it must be an OPPONENT's.
    The pushed stone is carried in front of the mover: it ends up ONE square
    beyond the mover's destination (i.e. at origin + dir*(dist+1)). That landing
    square must be empty (no second stone there) or off the board (off-board =>
    the pushed stone is removed). This faithfully models a 2-space push, where
    an opponent stone anywhere in the path is shoved fully clear of the mover.
    """
    enemy = 1 - player
    path = [(c + dc * k, r + dr * k) for k in range(1, dist + 1)]
    dest = path[-1]
    # destination must be in bounds
    if not _in_bounds(*dest):
        return None
    occupied = [p for p in path if p in cells]
    if len(occupied) > 1:
        return None
    if not occupied:
        return (dest, None, None)
    pushed = occupied[0]
    if cells[pushed] != enemy:
        return None  # can't push your own stone
    # The pushed stone is carried in front of the mover to one square beyond the
    # destination: origin + dir*(dist+1).
    lc, lr = c + dc * (dist + 1), r + dr * (dist + 1)
    if not _in_bounds(lc, lr):
        return (dest, pushed, None)  # shoved off the board -> removed
    if (lc, lr) in cells:
        return None  # would push two stones / shove into an occupied square
    return (dest, pushed, (lc, lr))


def _aggressive_moves(s: ShobuState, player: int, dc: int, dr: int, dist: int,
                      passive_board: int) -> list[tuple]:
    """All legal aggressive moves matching (dc,dr,dist) on boards of the colour
    opposite to ``passive_board``. Returns (board, from, dest, result)."""
    out = []
    for b in _opp_colour_boards(passive_board):
        cells = s.boards[b]
        for (c, r), owner in cells.items():
            if owner != player:
                continue
            res = _aggressive_result(cells, c, r, dc, dr, dist, player)
            if res is not None:
                dest = res[0]
                out.append((b, (c, r), dest, res))
    return out


def _board_loser(s: ShobuState) -> Optional[int]:
    """If some board has zero stones for a player, return that player (loser)."""
    for b in range(NBOARDS):
        cells = s.boards[b]
        for p in (0, 1):
            if not any(v == p for v in cells.values()):
                return p
    return None


class Shobu(Game):
    uid = "shobu"
    name = "Shobu"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ShobuState:
        return ShobuState(boards=_initial_boards(), to_move=0)

    def current_player(self, s: ShobuState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def legal_moves(self, s: ShobuState) -> list[str]:
        if self.is_terminal(s):
            return []
        player = s.to_move
        if s.pending is None:
            # Offer passive moves that ALSO admit a matching aggressive move.
            out = []
            for (b, frm, to, dc, dr, dist) in _passive_moves(s, player):
                if _aggressive_moves(s, player, dc, dr, dist, b):
                    out.append(f"{_key(b, *frm)}>{_key(b, *to)}")
            return out
        dc, dr, dist, passive_board = s.pending
        out = []
        for (b, frm, dest, _res) in _aggressive_moves(
                s, player, dc, dr, dist, passive_board):
            out.append(f"{_key(b, *frm)}>{_key(b, *dest)}")
        return out

    def apply_move(self, s: ShobuState, move: str, rng=None) -> ShobuState:
        if self.is_terminal(s):
            raise ValueError("game over")
        player = s.to_move
        (fb, fc, fr), (tb, tc, tr) = _parse_move(move)

        if s.pending is None:
            return self._apply_passive(s, player, fb, fc, fr, tb, tc, tr, move)
        return self._apply_aggressive(s, player, fb, fc, fr, tb, tc, tr, move)

    def _apply_passive(self, s, player, fb, fc, fr, tb, tc, tr, move):
        if fb != tb:
            raise ValueError(f"passive move stays on one board: {move!r}")
        if fb not in HOME[player]:
            raise ValueError(f"passive must be on a home board: {move!r}")
        cells = s.boards[fb]
        if cells.get((fc, fr)) != player:
            raise ValueError(f"no own stone at source: {move!r}")
        dc_raw, dr_raw = tc - fc, tr - fr
        dist = max(abs(dc_raw), abs(dr_raw))
        if dist not in (1, 2):
            raise ValueError(f"distance must be 1 or 2: {move!r}")
        dc = (dc_raw > 0) - (dc_raw < 0)
        dr = (dr_raw > 0) - (dr_raw < 0)
        if (dc * dist, dr * dist) != (dc_raw, dr_raw):
            raise ValueError(f"not a straight 8-dir move: {move!r}")
        # No-push, empty path.
        for k in range(1, dist + 1):
            nc, nr = fc + dc * k, fr + dr * k
            if not _in_bounds(nc, nr) or (nc, nr) in cells:
                raise ValueError(f"passive move blocked: {move!r}")
        # Must admit a matching aggressive move.
        if not _aggressive_moves(s, player, dc, dr, dist, fb):
            raise ValueError(f"passive has no matching aggressive move: {move!r}")

        new_cells = dict(cells)
        del new_cells[(fc, fr)]
        new_cells[(tc, tr)] = player
        boards = tuple(
            new_cells if i == fb else b for i, b in enumerate(s.boards)
        )
        return ShobuState(
            boards=boards, to_move=player,
            pending=(dc, dr, dist, fb), winner=None, ply=s.ply,
        )

    def _apply_aggressive(self, s, player, fb, fc, fr, tb, tc, tr, move):
        if fb != tb:
            raise ValueError(f"aggressive move stays on one board: {move!r}")
        dc_pending, dr_pending, dist, passive_board = s.pending
        if fb not in _opp_colour_boards(passive_board):
            raise ValueError(f"aggressive must be opposite-colour board: {move!r}")
        cells = s.boards[fb]
        if cells.get((fc, fr)) != player:
            raise ValueError(f"no own stone at source: {move!r}")
        dc_raw, dr_raw = tc - fc, tr - fr
        d = max(abs(dc_raw), abs(dr_raw))
        dc = (dc_raw > 0) - (dc_raw < 0)
        dr = (dr_raw > 0) - (dr_raw < 0)
        if (dc, dr, d) != (dc_pending, dr_pending, dist):
            raise ValueError(f"aggressive must match passive dir+dist: {move!r}")
        res = _aggressive_result(cells, fc, fr, dc, dr, dist, player)
        if res is None or res[0] != (tc, tr):
            raise ValueError(f"illegal aggressive move: {move!r}")

        dest, pushed_from, pushed_to = res
        new_cells = dict(cells)
        del new_cells[(fc, fr)]
        if pushed_from is not None:
            del new_cells[pushed_from]
            if pushed_to is not None:
                new_cells[pushed_to] = 1 - player  # opponent stone shoved
            # else: pushed off the board -> removed
        new_cells[dest] = player
        boards = tuple(
            new_cells if i == fb else b for i, b in enumerate(s.boards)
        )
        nxt = ShobuState(
            boards=boards, to_move=1 - player, pending=None,
            winner=None, ply=s.ply + 1,
        )
        loser = _board_loser(nxt)
        if loser is not None:
            return ShobuState(
                boards=boards, to_move=nxt.to_move, pending=None,
                winner=1 - loser, ply=nxt.ply,
            )
        return nxt

    # ---- termination -------------------------------------------------------
    def is_terminal(self, s: ShobuState) -> bool:
        if s.winner is not None:
            return True
        if s.pending is None and s.ply >= PLY_CAP:
            return True
        # Safety: a player with no legal move (only possible mid-turn anomaly).
        if s.pending is None and not self._has_any_full_turn(s):
            return True
        return False

    def _has_any_full_turn(self, s: ShobuState) -> bool:
        for (b, _frm, _to, dc, dr, dist) in _passive_moves(s, s.to_move):
            if _aggressive_moves(s, s.to_move, dc, dr, dist, b):
                return True
        return False

    def returns(self, s: ShobuState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        if self.is_terminal(s) and s.winner is None:
            # ply cap or stalemate -> draw
            return [0.0, 0.0]
        return [0.0, 0.0]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: ShobuState) -> dict:
        return {
            "boards": [
                {f"{c},{r}": p for (c, r), p in b.items()}
                for b in s.boards
            ],
            "to_move": s.to_move,
            "pending": list(s.pending) if s.pending is not None else None,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> ShobuState:
        boards = tuple(
            {(_p2(k)): v for k, v in b.items()} for b in d["boards"]
        )
        pending = d.get("pending")
        return ShobuState(
            boards=boards,
            to_move=d["to_move"],
            pending=tuple(pending) if pending is not None else None,
            winner=d.get("winner"),
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: ShobuState, move: str) -> str:
        (fb, fc, fr), (tb, tc, tr) = _parse_move(move)
        phase = "passive" if s.pending is None else "aggressive"
        return f"{phase}: board {fb} ({fc},{fr})->({tc},{tr})"

    # ---- presentation ------------------------------------------------------
    def render(self, s: ShobuState, perspective=None) -> dict:
        GAP = 1.2
        # Colours for the two board kinds.
        dark_tint = "#3b3326"
        light_tint = "#d9c7a3"
        cells = []
        tints = {}
        for b in range(NBOARDS):
            bx = (b % 2) * (SIZE + GAP)
            by = (b // 2) * (SIZE + GAP)
            tint = dark_tint if _is_dark(b) else light_tint
            for c in range(SIZE):
                for r in range(SIZE):
                    ox = bx + c
                    oy = by + r
                    pts = [
                        [round(ox, 3), round(oy, 3)],
                        [round(ox + 1, 3), round(oy, 3)],
                        [round(ox + 1, 3), round(oy + 1, 3)],
                        [round(ox, 3), round(oy + 1, 3)],
                    ]
                    cid = _key(b, c, r)
                    cells.append({"id": cid, "points": pts})
                    tints[cid] = tint

        pieces = []
        for b in range(NBOARDS):
            for (c, r), p in s.boards[b].items():
                pieces.append({"cell": _key(b, c, r), "owner": p, "label": ""})

        highlights = []
        names = {0: "Player 0 (near)", 1: "Player 1 (far)"}
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif self.is_terminal(s):
            caption = "Draw (ply cap)"
        else:
            phase = ("choose AGGRESSIVE move (same dir+dist, opposite colour)"
                     if s.pending is not None else
                     "choose PASSIVE move (your home board, no push)")
            caption = f"{names[s.to_move]} to move — {phase}"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }


def _p2(s: str) -> tuple:
    c, r = s.split(",")
    return int(c), int(r)
