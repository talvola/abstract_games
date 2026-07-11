"""Omega, by Néstor Romeral Andrés (2010).  (The hex scoring game — not Omega Chess.)

A placement/scoring game on a hexagon-of-hexagons ("hexhex") board of side
5..10 (option, default 6).  Two players: White (seat 0, moves first) and
Black (seat 1).  Stones never move and are never captured.

Turn structure (rulebook, nestorgames OMEGA_EN.pdf):
    "Each turn, the current player must place one stone of each color in play
     on any free spaces on the board."
For 2 players each turn therefore places TWO stones: one of the mover's own
colour and one of the opponent's colour, on two distinct free cells.  The
rulebook does not prescribe an order for the two placements within a turn
(the outcome is order-independent); this implementation canonicalises
own-colour first, then the opponent's colour.

Move encoding — the multi-move sub-turn pattern: each ply places ONE stone
and is the single cell id ``"q,r"`` (axial).  ``state.phase`` tracks which
stone of the turn is being placed (0 = the mover's own colour, 1 = the
opponent's colour); ``to_move`` stays with the mover for both plies.  A lone
``"q,r"`` is always a complete ply, so there is no prefix-matching ambiguity.

Game end (rulebook):
    "The game ends when, just before white's turn, it is not possible to play
     a complete round (all players).  For a 2-player game, at least 4 free
     spaces are needed to play a complete round."
I.e. after Black completes a turn, the game is over iff fewer than 4 free
cells remain.  A few cells always remain free at the end.

Scoring (rulebook):
    "The 'value' of a group is the number of stones on that group.  To
     calculate your score multiply the values of all the groups of your
     color.  The player with the highest score wins.  In case of a tie, the
     last of the tied players wins."
Groups are maximal 6-connected same-colour components; the score is the
PRODUCT of the group sizes (Python big ints).  The tie-break is explicit in
the rulebook: turn order is White then Black, so in this 2-player port a tie
in products is a WIN FOR BLACK — there are no draws.

The optional pie rule ("may be applied upon agreement") and the 3-/4-player
configurations are not implemented (num_players is fixed per package).

Termination: every ply fills exactly one empty cell and the end condition
fires at the first round boundary with < 4 free cells, so a game lasts at
most `cells` plies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
MIN_SIDE, MAX_SIDE = 5, 10
DEFAULT_SIDE = 6
ROUND_NEED = 4  # free cells needed for a complete 2-player round (2 stones each)


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
            if abs(q) <= n and abs(r) <= n and abs(-q - r) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


def _group_sizes(board: dict, colour: int) -> list[int]:
    """Sizes of all maximal 6-connected components of ``colour``."""
    seen = set()
    sizes = []
    for cell, c in board.items():
        if c != colour or cell in seen:
            continue
        comp = {cell}
        stack = [cell]
        while stack:
            cq, cr = stack.pop()
            for nb in _neighbors(cq, cr):
                if nb not in comp and board.get(nb) == colour:
                    comp.add(nb)
                    stack.append(nb)
        seen |= comp
        sizes.append(len(comp))
    sizes.sort(reverse=True)
    return sizes


def _score(board: dict, colour: int) -> int:
    """Omega score = product of the colour's group sizes (big int).
    Empty product (no stones — unreachable in a played game) = 1."""
    prod = 1
    for sz in _group_sizes(board, colour):
        prod *= sz
    return prod


def _fmt_score(score: int) -> str:
    """Scores can be gigantic on big boards; abbreviate past 7 digits."""
    return str(score) if score < 10 ** 7 else f"{float(score):.4g}"


@dataclass
class OmegaState:
    size: int = DEFAULT_SIDE
    board: dict = field(default_factory=dict)   # (q, r) -> WHITE/BLACK (colour)
    to_move: int = WHITE                         # seat whose TURN it is
    phase: int = 0                               # 0 = place own colour, 1 = opponent's
    last: tuple = ()                             # cells placed in the current/last turn
    done: bool = False
    winner: Optional[int] = None                 # set when done (ties go to Black)


class Omega(Game):
    name = "Omega"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> OmegaState:
        options = options or {}
        try:
            size = int(options.get("size", DEFAULT_SIDE))
        except (TypeError, ValueError):
            size = DEFAULT_SIDE
        size = max(MIN_SIDE, min(MAX_SIDE, size))
        return OmegaState(size=size)

    def current_player(self, s: OmegaState) -> int:
        return s.to_move

    def legal_moves(self, s: OmegaState) -> list[str]:
        if s.done:
            return []
        return [f"{q},{r}" for (q, r) in _cells(s.size) if (q, r) not in s.board]

    def apply_move(self, s: OmegaState, move: str, rng=None) -> OmegaState:
        if s.done:
            raise ValueError("game is over")
        cell = _cell(move)
        if cell not in _cell_set(s.size):
            raise ValueError(f"off-board cell {move!r}")
        if cell in s.board:
            raise ValueError(f"cell {move!r} is occupied")

        mover = s.to_move
        colour = mover if s.phase == 0 else 1 - mover
        board = dict(s.board)
        board[cell] = colour

        if s.phase == 0:
            # First stone of the turn placed; same player places the opponent's.
            return OmegaState(size=s.size, board=board, to_move=mover,
                              phase=1, last=(cell,), done=False, winner=None)

        # Second stone: the turn is complete.
        last = s.last + (cell,)
        nxt = 1 - mover
        done = False
        winner = None
        if nxt == WHITE:
            # Round boundary — "just before white's turn": end the game if a
            # complete round (4 free cells) no longer fits.
            free = len(_cells(s.size)) - len(board)
            if free < ROUND_NEED:
                done = True
                sw, sb = _score(board, WHITE), _score(board, BLACK)
                if sw > sb:
                    winner = WHITE
                else:
                    # Higher score wins; on a TIE the rulebook awards the win
                    # to "the last of the tied players" in turn order = Black.
                    winner = BLACK
        return OmegaState(size=s.size, board=board, to_move=nxt,
                          phase=0, last=last, done=done, winner=winner)

    def is_terminal(self, s: OmegaState) -> bool:
        return s.done

    def returns(self, s: OmegaState) -> list[float]:
        if not s.done or s.winner is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if s.winner == WHITE else [-1.0, 1.0]

    def heuristic(self, s: OmegaState) -> list:
        """log-score margin squashed to (-1, 1) as [white, black] payoffs.
        Products are compared on a log scale (sum of log group sizes)."""
        lw = sum(math.log(sz) for sz in _group_sizes(s.board, WHITE))
        lb = sum(math.log(sz) for sz in _group_sizes(s.board, BLACK))
        v = math.tanh((lw - lb) / 3.0)
        return [v, -v]

    def serialize(self, s: OmegaState) -> dict:
        return {
            "size": s.size,
            "board": {f"{q},{r}": c for (q, r), c in s.board.items()},
            "to_move": s.to_move,
            "phase": s.phase,
            "last": [f"{q},{r}" for (q, r) in s.last],
            "done": s.done,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> OmegaState:
        return OmegaState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            phase=d.get("phase", 0),
            last=tuple(_cell(x) for x in d.get("last", [])),
            done=d.get("done", False),
            winner=d.get("winner"),
        )

    def describe_move(self, s: OmegaState, move: str) -> str:
        colour = s.to_move if s.phase == 0 else 1 - s.to_move
        return f"{move} ({'White' if colour == WHITE else 'Black'} stone)"

    def render(self, s: OmegaState, perspective=None) -> dict:
        names = {WHITE: "White", BLACK: "Black"}
        pieces = [{"cell": f"{q},{r}", "owner": c, "label": ""}
                  for (q, r), c in s.board.items()]
        highlights = [{"cell": f"{q},{r}", "kind": "last-move"} for (q, r) in s.last]
        sw, sb = _score(s.board, WHITE), _score(s.board, BLACK)
        scores = f"scores {_fmt_score(sw)}–{_fmt_score(sb)}"
        if s.done:
            if s.winner == BLACK and sw == sb:
                caption = f"Black wins the tie ({scores})"
            else:
                caption = f"{names[s.winner]} wins ({scores})"
        else:
            mover = names[s.to_move]
            stone = ("your own stone" if s.phase == 0
                     else f"{names[1 - s.to_move]}'s stone")
            caption = f"{mover} to move — place {stone} ({scores})"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
