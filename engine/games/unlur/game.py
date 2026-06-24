"""Unlur, by Jorge Gómez Arrausi (2001) -- an asymmetric hex connection game.

Played on a hexagonal board of hexagons (a "hexhex") of side length N (the
designer's original size is 6; 7 and 8 are also playable). Stones are never
moved or captured. The two roles -- Black and White -- have DIFFERENT goals:

  * BLACK wins by forming a single connected chain of BLACK stones that touches
    THREE NON-ADJACENT (mutually alternating) sides of the hexagon -- a "Y".
  * WHITE wins by forming a single connected chain of WHITE stones that touches
    TWO OPPOSITE sides of the hexagon -- a "line".

Crucially the goals are *complementary* and completing your OPPONENT'S goal
LOSES the game: if Black ever connects two opposite sides (a line) without also
having a Y, Black loses; if White ever connects three non-adjacent sides (a Y)
without also having a line, White loses. Draws are impossible.

The "contract" opening fixes who is who. In phase 1 BOTH players place BLACK
stones (only on the INTERIOR -- never on a border hex) on alternating turns, or
they may PASS. The moment a player passes, that player becomes BLACK for the
rest of the game (inheriting every black stone already on the board) and the
other player becomes WHITE; White then makes the first move of normal play.
After the contract, players alternate placing their OWN colour anywhere empty.

Coordinates are axial ``(q, r)`` (the third cube coord is ``s = -q - r``); a
cell is on a hexhex of side N iff ``max(|q|, |r|, |s|) <= N-1``. The six sides
are indexed 0..5 around the board; "opposite" = indices differing by 3,
"non-adjacent" = the alternating triple {0,2,4} or {1,3,5}.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

# Colours (NOT seats). A seat *plays* a colour once the contract resolves.
BLACK, WHITE = 0, 1


def _neighbors(q: int, r: int):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1), (q + 1, r - 1), (q - 1, r + 1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    out = []
    n = size - 1
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            s = -q - r
            if abs(q) <= n and abs(r) <= n and abs(s) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


@lru_cache(maxsize=None)
def _corners(size: int) -> tuple:
    n = size - 1
    return ((n, 0), (n, -n), (0, -n), (-n, 0), (-n, n), (0, n))


@lru_cache(maxsize=None)
def _side_id(size: int) -> dict:
    """Map EVERY border cell (corners included) -> set of side indices 0..5.

    A border cell lies on a side when one cube coordinate is pinned at +(N-1) or
    -(N-1). Corners pin two coordinates, so a corner belongs to TWO sides. Sides
    are indexed so that consecutive indices are geometrically adjacent and
    +3 (mod 6) is the opposite side.
    """
    n = size - 1
    sides = {
        ("q", n): 0, ("r", -n): 1, ("s", n): 2,
        ("q", -n): 3, ("r", n): 4, ("s", -n): 5,
    }
    out: dict = {}
    for (q, r) in _cells(size):
        s = -q - r
        ids = set()
        for name, val in (("q", q), ("r", r), ("s", s)):
            if val == n or val == -n:
                ids.add(sides[(name, val)])
        if ids:
            out[(q, r)] = ids
    return out


@lru_cache(maxsize=None)
def _border(size: int) -> frozenset:
    return frozenset(_side_id(size).keys())


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


@dataclass
class UnlurState:
    size: int = 6
    board: dict = field(default_factory=dict)       # (q, r) -> colour BLACK/WHITE
    to_move: int = 0                                 # seat (0/1) to move
    phase: str = "contract"                          # "contract" | "play"
    black_seat: Optional[int] = None                 # which seat plays Black (set on pass)
    winner: Optional[int] = None                     # winning SEAT
    win_reason: Optional[str] = None
    last: Optional[tuple] = None
    ply: int = 0


def _group(board: dict, start: tuple, colour: int) -> set:
    if board.get(start) != colour:
        return set()
    seen, stack = {start}, [start]
    while stack:
        cq, cr = stack.pop()
        for nb in _neighbors(cq, cr):
            if nb not in seen and board.get(nb) == colour:
                seen.add(nb)
                stack.append(nb)
    return seen


def _colour_groups(board: dict, colour: int) -> list:
    groups, seen = [], set()
    for cell, c in board.items():
        if c == colour and cell not in seen:
            g = _group(board, cell, colour)
            seen |= g
            groups.append(g)
    return groups


def _has_line(board: dict, size: int, colour: int) -> bool:
    """A connected `colour` chain touching two OPPOSITE sides (indices i, i+3)."""
    side_of = _side_id(size)
    for g in _colour_groups(board, colour):
        sides = set()
        for c in g:
            sides |= side_of.get(c, set())
        for i in range(3):
            if i in sides and (i + 3) in sides:
                return True
    return False


def _has_y(board: dict, size: int, colour: int) -> bool:
    """A connected `colour` chain touching three NON-ADJACENT sides:
    the alternating triple {0,2,4} or {1,3,5}."""
    side_of = _side_id(size)
    for g in _colour_groups(board, colour):
        sides = set()
        for c in g:
            sides |= side_of.get(c, set())
        if {0, 2, 4} <= sides or {1, 3, 5} <= sides:
            return True
    return False


class Unlur(Game):
    uid = "unlur"
    name = "Unlur"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> UnlurState:
        size = int((options or {}).get("size", 6))
        return UnlurState(size=size)

    def current_player(self, s: UnlurState) -> int:
        return s.to_move

    # ---- colour bookkeeping -----------------------------------------------
    def _colour_of_seat(self, s: UnlurState, seat: int) -> int:
        """Which colour `seat` places. Undefined before the contract resolves;
        during the contract everyone places BLACK."""
        if s.black_seat is None:
            return BLACK
        return BLACK if seat == s.black_seat else WHITE

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, s: UnlurState) -> list[str]:
        if self.is_terminal(s):
            return []
        if s.phase == "contract":
            # Place BLACK on any empty INTERIOR cell, or pass.
            border = _border(s.size)
            moves = [f"{q},{r}" for (q, r) in _cells(s.size)
                     if (q, r) not in s.board and (q, r) not in border]
            moves.append("pass")
            return moves
        # Normal play: place own colour on any empty cell.
        return [f"{q},{r}" for (q, r) in _cells(s.size) if (q, r) not in s.board]

    def apply_move(self, s: UnlurState, move: str, rng=None) -> UnlurState:
        if s.phase == "contract" and move == "pass":
            # Passer becomes Black; the other seat becomes White and moves next.
            black_seat = s.to_move
            return UnlurState(
                size=s.size, board=dict(s.board), to_move=1 - s.to_move,
                phase="play", black_seat=black_seat, last=s.last, ply=s.ply + 1,
            )

        q, r = _cell(move)
        if (q, r) not in _cell_set(s.size) or (q, r) in s.board:
            raise ValueError(f"illegal move {move!r}")
        if s.phase == "contract" and (q, r) in _border(s.size):
            raise ValueError("cannot place on a border cell during the contract")

        mover = s.to_move
        colour = self._colour_of_seat(s, mover)
        board = dict(s.board)
        board[(q, r)] = colour

        winner = None
        reason = None
        if s.phase == "play":
            black_seat = s.black_seat
            white_seat = 1 - black_seat
            mover_is_black = (mover == black_seat)
            has_y = _has_y(board, s.size, colour)
            has_line = _has_line(board, s.size, colour)
            if mover_is_black:
                # Black goal = Y. Black's own line (without a Y) is a self-loss.
                if has_y:
                    winner, reason = black_seat, "Black Y (three non-adjacent sides)"
                elif has_line:
                    winner, reason = white_seat, "Black completed a line -> Black loses"
            else:
                # White goal = line. White's own Y (without a line) is a self-loss.
                if has_line:
                    winner, reason = white_seat, "White line (two opposite sides)"
                elif has_y:
                    winner, reason = black_seat, "White completed a Y -> White loses"

        return UnlurState(
            size=s.size, board=board, to_move=1 - mover, phase=s.phase,
            black_seat=s.black_seat, winner=winner, win_reason=reason,
            last=(q, r), ply=s.ply + 1,
        )

    def is_terminal(self, s: UnlurState) -> bool:
        if s.winner is not None:
            return True
        # Safety: a wholly full board cannot occur before someone connects on a
        # hexhex, but guard termination anyway.
        return s.phase == "play" and len(s.board) >= len(_cells(s.size))

    def returns(self, s: UnlurState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: UnlurState) -> dict:
        return {
            "size": s.size,
            "board": {f"{q},{r}": c for (q, r), c in s.board.items()},
            "to_move": s.to_move,
            "phase": s.phase,
            "black_seat": s.black_seat,
            "winner": s.winner,
            "win_reason": s.win_reason,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> UnlurState:
        last = d.get("last")
        return UnlurState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            phase=d.get("phase", "contract"),
            black_seat=d.get("black_seat"),
            winner=d.get("winner"),
            win_reason=d.get("win_reason"),
            last=(_cell(last) if last else None),
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: UnlurState, move: str) -> str:
        if move == "pass":
            return "pass (become Black)"
        return move

    # ---- presentation ------------------------------------------------------
    def _role_name(self, s: UnlurState, seat: int) -> str:
        if s.black_seat is None:
            return f"Player {seat + 1}"
        return "Black" if seat == s.black_seat else "White"

    def render(self, s: UnlurState, perspective=None) -> dict:
        # Tint the six sides so the goals are visible. Alternating sides
        # {0,2,4} / {1,3,5} are tinted two shades: Black needs one whole
        # alternating triple (a Y), White needs any one opposite pair (a line,
        # one cell of each shade). This is a visual aid only -- either triple
        # works for Black and either pairing for White.
        side_of = _side_id(s.size)
        tint_even = "#3a3a44"   # sides 0,2,4
        tint_odd = "#cfc9bd"    # sides 1,3,5
        tints = {}
        for (q, r), ids in side_of.items():
            even = any(i % 2 == 0 for i in ids)
            tints[f"{q},{r}"] = tint_even if even else tint_odd

        # Stones are coloured by COLOUR (black/white), independent of seat. Map
        # colour -> a seat for the renderer's palette: prefer the real black/white
        # seats once known, else BLACK->0 / WHITE->1 so contract stones read black.
        if s.black_seat is None:
            colour_owner = {BLACK: 0, WHITE: 1}
        else:
            colour_owner = {BLACK: s.black_seat, WHITE: 1 - s.black_seat}
        pieces = [
            {"cell": f"{q},{r}", "owner": colour_owner[c],
             "label": ("B" if c == BLACK else "W")}
            for (q, r), c in s.board.items()
        ]

        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})

        if s.winner is not None:
            caption = f"{self._role_name(s, s.winner)} wins -- {s.win_reason}"
        elif s.phase == "contract":
            caption = (f"Contract phase: {self._role_name(s, s.to_move)} places a "
                       f"black stone (interior only) or passes to become Black")
        else:
            caption = f"{self._role_name(s, s.to_move)} to move"

        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
