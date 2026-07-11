"""Blooms, by Nick Bentley (2018).

A Go-like capture game on a hexhex board where EACH PLAYER OWNS TWO COLOURS
of stones (four colours on the board in all). Official rules (the designer's
site, nickbentley.games/blooms-rules/, "Blooms 2.0", Nov 2018):

  * A *bloom* is a single stone, or an entire group of connected stones of
    the SAME colour (6-adjacency). Stones of the same player's two different
    colours do NOT connect.
  * A bloom is *fenced* when there are no empty spaces adjacent to any of
    its stones.
  * To start, Player 1 places 1 stone of either of her colours on any empty
    space. From then on, starting with Player 2, the players take turns:
    place 1 or 2 stones onto any empty spaces; if you place 2, they must be
    DIFFERENT colours (i.e. one of each of your colours).
  * After placement, capture ALL fenced enemy blooms (evaluated
    simultaneously on the board as it stands after your placement).
  * The first player to have captured X stones in total wins.

There are NO illegal placements: "suicide" (leaving your own bloom fenced)
is legal — your fenced bloom simply stays on the board and the opponent
captures it at the end of their next turn (own blooms are never removed on
your own turn). Removing a fenced enemy bloom during your capture step can
give your own fenced bloom liberties again (the sacrifice-rescue tactic).
There is no passing and no ko rule: the monotonically increasing capture
score is what kills cycles (the designer's stated design).

Board sizes (per the designer / Board Game Arena): hexhex 4, 5 or 6 cells
per side. The designer recommends new players start at size 5 with X = 20.
Capture targets used here ("auto"): 15 / 20 / 30 for sizes 4 / 5 / 6
(size-5 value is the designer's own; 15 and 30 from the Abstract Games
magazine treatment at abstractgames.org/blooms.html, which gives 15 for
base-4 and "25 or 30" for base-6 — we pick 30, matching the designer's
preference for larger X on larger boards). X is also directly selectable
as an option, as the designer frames X as a tunable.

TURN ENCODING (multi-move pattern): a turn is 1 or 2 sub-moves by the same
player. A placement is the string "q,r=C" where C is the colour letter
(player 1: R=Red / O=Orange; player 2: B=Blue / G=Green). After the first
placement of a turn the player may either place the OTHER colour ("q,r=C2")
or play "done" to end the turn on one stone. The game's very first turn
(one stone only) ends automatically. Captures resolve only when the turn
ends, per the official "after placement" wording — a bloom fenced by your
first stone is not removed until your turn ends.

Termination: captures are monotonic and the board strictly fills between
captures, so play cannot cycle; a generous hard ply cap (honest draw) is
kept as a defensive backstop, along with a draw for the provably
unreachable "no empty cell at the start of a turn" position.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

# Colour indices. Seat 0 owns 0..1, seat 1 owns 2..3.
LETTERS = ["R", "O", "B", "G"]
IDX = {L: i for i, L in enumerate(LETTERS)}
NAMES = {"R": "Red", "O": "Orange", "B": "Blue", "G": "Green"}
FILLS = ["#d23b3b", "#e8892a", "#3b6fd2", "#3aa84a"]
STROKES = ["#7a1414", "#8a4d0e", "#173a7a", "#1c5a26"]

AUTO_TARGET = {4: 15, 5: 20, 6: 30}


def _seat(colour: int) -> int:
    return 0 if colour < 2 else 1


def _own_colours(seat: int) -> tuple[int, int]:
    return (0, 1) if seat == 0 else (2, 3)


def _neighbors(q: int, r: int):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1),
            (q + 1, r - 1), (q - 1, r + 1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    """All on-board axial cells of a hexhex of side ``size``."""
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


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


def _fenced_enemy_stones(board: dict, size: int, mover: int) -> set:
    """All stones of the mover's OPPONENT belonging to fenced blooms.

    Blooms are connected components of a SINGLE colour index (a player's two
    colours never connect). Fenced = no empty adjacent cell anywhere on the
    bloom. Evaluated simultaneously: every enemy bloom fenced on the board
    as passed in is captured, even if removing one such bloom would have
    given another its liberties back.
    """
    on = _cell_set(size)
    enemy = set(_own_colours(1 - mover))
    seen: set = set()
    captured: set = set()
    for cell, ci in board.items():
        if ci not in enemy or cell in seen:
            continue
        # flood-fill this bloom (same colour index only)
        bloom = {cell}
        stack = [cell]
        fenced = True
        while stack:
            cq, cr = stack.pop()
            for nb in _neighbors(cq, cr):
                if nb not in on:
                    continue
                v = board.get(nb)
                if v is None:
                    fenced = False
                elif v == ci and nb not in bloom:
                    bloom.add(nb)
                    stack.append(nb)
        seen |= bloom
        if fenced:
            captured |= bloom
    return captured


@dataclass
class BloomsState:
    size: int = 5
    target: int = 20
    board: dict = field(default_factory=dict)   # (q, r) -> colour index 0..3
    to_move: int = 0
    turn_no: int = 0                             # completed turns so far
    placed: Optional[tuple] = None               # first cell placed this turn
    captures: list = field(default_factory=lambda: [0, 0])
    ply: int = 0                                 # sub-moves applied
    last: tuple = ()                             # cells placed on the previous turn
    winner: Optional[int] = None
    over: bool = False


class Blooms(Game):
    name = "Blooms"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> BloomsState:
        opts = options or {}
        size = int(opts.get("size", 5))
        tgt = str(opts.get("target", "auto"))
        if tgt == "auto":
            target = AUTO_TARGET.get(size, 5 * (size - 1))
        else:
            target = int(tgt)
        return BloomsState(size=size, target=target)

    def current_player(self, s: BloomsState) -> int:
        return s.to_move

    # -- move generation ---------------------------------------------------

    def legal_moves(self, s: BloomsState) -> list[str]:
        if self.is_terminal(s):
            return []
        empties = [c for c in _cells(s.size) if c not in s.board]
        moves: list[str] = []
        if s.placed is None:
            for ci in _own_colours(s.to_move):
                L = LETTERS[ci]
                moves.extend(f"{q},{r}={L}" for (q, r) in empties)
        else:
            first_ci = s.board[s.placed]
            a, b = _own_colours(s.to_move)
            other = b if first_ci == a else a
            L = LETTERS[other]
            moves.extend(f"{q},{r}={L}" for (q, r) in empties)
            moves.append("done")
        return moves

    # -- transition --------------------------------------------------------

    def _ply_cap(self, size: int) -> int:
        # Defensive only: captures are monotonic and the board strictly fills
        # between captures, so real play can't get near this.
        return 40 * len(_cells(size))

    def apply_move(self, s: BloomsState, move: str, rng=None) -> BloomsState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move

        if move == "done":
            if s.placed is None:
                raise ValueError("cannot end the turn before placing a stone")
            return self._end_turn(s, dict(s.board), (s.placed,))

        # placement "q,r=C"
        if "=" not in move:
            raise ValueError(f"bad move {move!r}")
        cell_part, letter = move.rsplit("=", 1)
        if letter not in IDX:
            raise ValueError(f"unknown colour {letter!r}")
        ci = IDX[letter]
        if _seat(ci) != mover:
            raise ValueError(f"{NAMES[letter]} is not your colour")
        cell = _cell(cell_part)
        if cell not in _cell_set(s.size):
            raise ValueError(f"off-board {move!r}")
        if cell in s.board:
            raise ValueError(f"occupied {move!r}")
        if s.placed is not None:
            if s.turn_no == 0:
                raise ValueError("the first turn places exactly one stone")
            if s.board[s.placed] == ci:
                raise ValueError("two stones in a turn must be different colours")

        board = dict(s.board)
        board[cell] = ci

        if s.placed is not None:
            # second stone: the turn ends
            return self._end_turn(s, board, (s.placed, cell))
        if s.turn_no == 0:
            # the game's very first turn places exactly one stone
            return self._end_turn(s, board, (cell,))
        # first stone of a normal turn: same player continues (place or done)
        return BloomsState(
            size=s.size, target=s.target, board=board, to_move=mover,
            turn_no=s.turn_no, placed=cell, captures=list(s.captures),
            ply=s.ply + 1, last=s.last,
        )

    def _end_turn(self, s: BloomsState, board: dict, placed_cells: tuple) -> BloomsState:
        """Resolve the capture step and hand the turn over."""
        mover = s.to_move
        captured = _fenced_enemy_stones(board, s.size, mover)
        for c in captured:
            del board[c]
        captures = list(s.captures)
        captures[mover] += len(captured)

        ns = BloomsState(
            size=s.size, target=s.target, board=board, to_move=1 - mover,
            turn_no=s.turn_no + 1, placed=None, captures=captures,
            ply=s.ply + 1, last=placed_cells,
        )
        if captures[mover] >= s.target:
            ns.winner = mover
            ns.over = True
        elif len(board) >= len(_cells(s.size)):
            # Board full at the start of a turn: provably unreachable with the
            # shipped capture targets (see rules.md); honest defensive draw.
            ns.winner = None
            ns.over = True
        elif ns.ply >= self._ply_cap(s.size):
            ns.winner = None  # hard-cap honest draw (defensive backstop)
            ns.over = True
        return ns

    def is_terminal(self, s: BloomsState) -> bool:
        return s.over

    def returns(self, s: BloomsState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: BloomsState) -> list:
        """Capture-race progress for truncated MCTS rollouts."""
        d = (s.captures[0] - s.captures[1]) / max(1, s.target)
        v = math.tanh(1.5 * d)
        return [v, -v]

    # -- serialization -----------------------------------------------------

    def serialize(self, s: BloomsState) -> dict:
        return {
            "size": s.size,
            "target": s.target,
            "board": {f"{q},{r}": ci for (q, r), ci in s.board.items()},
            "to_move": s.to_move,
            "turn_no": s.turn_no,
            "placed": (f"{s.placed[0]},{s.placed[1]}" if s.placed is not None else None),
            "captures": list(s.captures),
            "ply": s.ply,
            "last": [f"{q},{r}" for (q, r) in s.last],
            "winner": s.winner,
            "over": s.over,
        }

    def deserialize(self, d: dict) -> BloomsState:
        placed = d.get("placed")
        return BloomsState(
            size=d["size"],
            target=d["target"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            turn_no=d.get("turn_no", 0),
            placed=(_cell(placed) if placed else None),
            captures=list(d.get("captures", [0, 0])),
            ply=d.get("ply", 0),
            last=tuple(_cell(x) for x in d.get("last", [])),
            winner=d.get("winner"),
            over=d.get("over", False),
        )

    # -- presentation --------------------------------------------------------

    def describe_move(self, s: BloomsState, move: str) -> str:
        if move == "done":
            board = dict(s.board)
            n = len(_fenced_enemy_stones(board, s.size, s.to_move))
            return "done" + (f" (×{n})" if n else "")
        cell_part, letter = move.rsplit("=", 1)
        ends = s.placed is not None or s.turn_no == 0
        label = f"{NAMES.get(letter, letter)} {cell_part}"
        if ends:
            board = dict(s.board)
            board[_cell(cell_part)] = IDX[letter]
            n = len(_fenced_enemy_stones(board, s.size, s.to_move))
            if n:
                label += f" (×{n})"
        return label

    def render(self, s: BloomsState, perspective=None) -> dict:
        seat_names = {0: "Red/Orange", 1: "Blue/Green"}
        pieces = []
        for (q, r), ci in s.board.items():
            pieces.append({
                "cell": f"{q},{r}", "owner": _seat(ci),
                "fill": FILLS[ci], "stroke": STROKES[ci],
            })
        highlights = [{"cell": f"{q},{r}", "kind": "last-move"} for (q, r) in s.last]
        if s.placed is not None:
            highlights.append(
                {"cell": f"{s.placed[0]},{s.placed[1]}", "kind": "last-move"})

        score = f"captures {s.captures[0]}/{s.target} : {s.captures[1]}/{s.target}"
        if s.over:
            if s.winner is None:
                caption = f"Draw — {score}"
            else:
                caption = f"{seat_names[s.winner]} wins — {score}"
        elif s.placed is not None:
            a, b = _own_colours(s.to_move)
            other = b if s.board[s.placed] == a else a
            caption = (f"{seat_names[s.to_move]}: 2nd stone "
                       f"({NAMES[LETTERS[other]]}) or done — {score}")
        else:
            caption = f"{seat_names[s.to_move]} to move — {score}"

        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "choiceNames": {L: NAMES[L] for L in LETTERS},
            "choiceTitle": "Stone colour",
        }
