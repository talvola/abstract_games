"""Cation — a square-board connection game by Luis Bolaños Mures (June 2016).

Played on the points of an initially empty square grid (rendered here as an
N x N grid of cells). Black (player 0) owns the TOP and BOTTOM edges, White
(player 1) the LEFT and RIGHT edges; you win by completing a chain of
ORTHOGONALLY adjacent stones of your colour touching your two opposite edges.
Black moves first; the pie rule applies (White may "swap" on their first turn).

A CROSSCUT is a 2x2 pattern of stones consisting of two diagonally adjacent
black stones and two diagonally adjacent white stones. Cation resolves the
square-board crosscut problem with ko fights. On your turn:

a) If there are NO crosscuts on the board, you must place a stone of your
   colour on an empty point such that it forms no crosscuts containing a stone
   that was placed by the opponent on their LATEST turn (crosscuts made only
   of older stones are allowed — that is the ko mechanism). If no such
   placement exists you must pass; passing is otherwise not allowed.

b) If there ARE crosscuts, you must take a friendly stone from one of them and
   place it on a different empty point where it doesn't create any other
   crosscut. If no such point exists, the stone is simply removed.

Rules source (all three carry the identical 2016 text): the designer's BGG
thread "New games: Cation and Rhode" (boardgamegeek.com/thread/1593043), his
Zillions submission (id 2500, sizes 3x3..19x19), and Stephen Tavener's AiAi
report. A relocated stone counts as "placed on the latest turn" for rule (a)
— confirmed by the Zillions implementation, which moves the "latest" marker to
the relocated stone. The designer mentioned in 2026 that he has "streamlined"
Cation, but no streamlined ruleset is published anywhere we could find, so
this module implements the complete 2016 rules.

Termination: every rule-(b) move destroys at least one crosscut and creates
none, and every rule-(a) placement fills a point, so play normally ends fast
(the game itself is drawless). Two defensive backstops per platform policy:
two consecutive passes (only reachable in a theoretically-impossible dead
full-board position) and a hard ply cap of 8*N*N are declared honest draws.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black connects top<->bottom (rows), White left<->right (cols)

_ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
_DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class CationState:
    size: int = 11
    board: dict = field(default_factory=dict)   # (c, r) -> BLACK/WHITE
    to_move: int = BLACK
    last: Optional[tuple] = None   # stone placed/relocated by the PREVIOUS mover
    winner: Optional[int] = None
    draw: bool = False
    ply: int = 0
    passes: int = 0                # consecutive passes


def _is_crosscut(board: dict, c: int, r: int) -> bool:
    """Is the 2x2 square with lower-left corner (c, r) a crosscut?"""
    a = board.get((c, r))
    b = board.get((c + 1, r))
    d = board.get((c, r + 1))
    e = board.get((c + 1, r + 1))
    return (a is not None and b is not None and d is not None and e is not None
            and a == e and b == d and a != b)


def _crosscut_squares(board: dict, size: int) -> list:
    """Lower-left corners of every crosscut on the board."""
    return [(c, r) for c in range(size - 1) for r in range(size - 1)
            if _is_crosscut(board, c, r)]


def _formed_crosscuts(board: dict, c: int, r: int, player: int) -> list:
    """The crosscuts that placing `player` on the EMPTY point (c, r) would
    form; each is returned as the tuple of the three existing cells in it."""
    opp = 1 - player
    out = []
    for dc, dr in _DIAG:
        diag = board.get((c + dc, r + dr))
        s1 = board.get((c + dc, r))
        s2 = board.get((c, r + dr))
        if diag == player and s1 == opp and s2 == opp:
            out.append(((c + dc, r + dr), (c + dc, r), (c, r + dr)))
    return out


def _connects(board: dict, player: int, size: int) -> bool:
    """Does `player` join their two edges via an ORTHOGONAL chain?"""
    if player == BLACK:  # bottom row 0 <-> top row size-1
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == BLACK]
        at_goal = lambda cell: cell[1] == size - 1  # noqa: E731
    else:                # left col 0 <-> right col size-1
        starts = [(0, r) for r in range(size) if board.get((0, r)) == WHITE]
        at_goal = lambda cell: cell[0] == size - 1  # noqa: E731
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        cc, cr = cur
        for dc, dr in _ORTH:
            nb = (cc + dc, cr + dr)
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return False


class Cation(Game):
    name = "Cation"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CationState:
        size = int((options or {}).get("size", 11))
        return CationState(size=size)

    def current_player(self, s: CationState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def _resolution_moves(self, s: CationState, squares: list) -> list[str]:
        """Rule (b): lift a friendly stone out of a crosscut; replay it on an
        empty point creating no crosscut, else remove it (bare-cell move)."""
        me = s.to_move
        mine = set()
        for (c, r) in squares:
            for cell in ((c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)):
                if s.board[cell] == me:
                    mine.add(cell)
        moves: list[str] = []
        n = s.size
        for p in sorted(mine):
            b2 = dict(s.board)
            del b2[p]
            dests = [
                (c, r)
                for r in range(n) for c in range(n)
                if (c, r) != p and (c, r) not in b2
                and not _formed_crosscuts(b2, c, r, me)
            ]
            if dests:
                moves.extend(f"{p[0]},{p[1]}>{c},{r}" for c, r in dests)
            else:
                moves.append(f"{p[0]},{p[1]}")   # removal only
        return moves

    def _placements(self, s: CationState) -> list[str]:
        """Rule (a): empty points whose placement forms no crosscut containing
        the opponent's latest-placed stone."""
        me = s.to_move
        out = []
        for r in range(s.size):
            for c in range(s.size):
                if (c, r) in s.board:
                    continue
                if s.last is not None:
                    formed = _formed_crosscuts(s.board, c, r, me)
                    if any(s.last in sq for sq in formed):
                        continue
                out.append(f"{c},{r}")
        return out

    def legal_moves(self, s: CationState) -> list[str]:
        if self.is_terminal(s):
            return []
        squares = _crosscut_squares(s.board, s.size)
        if squares:
            return self._resolution_moves(s, squares)
        moves = self._placements(s)
        if not moves:
            return ["pass"]          # forced; passing is otherwise not allowed
        if s.ply == 1:
            moves.append("swap")     # pie rule: White's first turn only
        return moves

    # -- move application ---------------------------------------------------

    def apply_move(self, s: CationState, move: str, rng=None) -> CationState:
        if move == "pass":
            return CationState(size=s.size, board=dict(s.board),
                               to_move=1 - s.to_move, last=None,
                               winner=s.winner, draw=s.passes + 1 >= 2,
                               ply=s.ply + 1, passes=s.passes + 1)
        if move == "swap":
            # Pie rule: White claims Black's lone opening stone as their own.
            (cell, _owner), = s.board.items()
            return CationState(size=s.size, board={cell: s.to_move},
                               to_move=1 - s.to_move, last=cell,
                               ply=s.ply + 1)
        me = s.to_move
        board = dict(s.board)
        if ">" in move:                       # rule (b): relocation
            frm, to = move.split(">")
            fc = _cell(frm)
            tc = _cell(to)
            del board[fc]
            board[tc] = me
            last = tc
        elif _cell(move) in board:            # rule (b): removal only
            del board[_cell(move)]
            last = None
        else:                                 # rule (a): placement
            tc = _cell(move)
            board[tc] = me
            last = tc
        winner = me if last is not None and _connects(board, me, s.size) else None
        return CationState(size=s.size, board=board, to_move=1 - me,
                           last=last, winner=winner, ply=s.ply + 1, passes=0)

    # -- termination / scoring ----------------------------------------------

    def is_terminal(self, s: CationState) -> bool:
        return s.winner is not None or s.draw or s.ply >= 8 * s.size * s.size

    def returns(self, s: CationState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]   # backstop draw (unreachable under sane play)

    # -- serialization ------------------------------------------------------

    def serialize(self, s: CationState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "last": None if s.last is None else f"{s.last[0]},{s.last[1]}",
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
            "passes": s.passes,
        }

    def deserialize(self, d: dict) -> CationState:
        return CationState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            last=None if d.get("last") is None else _cell(d["last"]),
            winner=d.get("winner"),
            draw=d.get("draw", False),
            ply=d.get("ply", 0),
            passes=d.get("passes", 0),
        )

    # -- presentation ---------------------------------------------------------

    def _coord(self, cell) -> str:
        letters = "abcdefghijklmnopqrstuvwxyz"
        c, r = cell
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def describe_move(self, s: CationState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if move == "pass":
            return "pass (forced)"
        if ">" in move:
            frm, to = move.split(">")
            return f"{self._coord(_cell(frm))}→{self._coord(_cell(to))} (crosscut)"
        cell = _cell(move)
        if cell in s.board:
            return f"remove {self._coord(cell)} (crosscut)"
        return self._coord(cell)

    def render(self, s: CationState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.draw or s.ply >= 8 * s.size * s.size:
            caption = "Draw (backstop)"
        elif _crosscut_squares(s.board, s.size):
            caption = f"{names[s.to_move]} to move — resolve a crosscut"
        else:
            edge = "top–bottom" if s.to_move == BLACK else "left–right"
            caption = f"{names[s.to_move]} to move ({edge})"
        return {
            "board": {
                "type": "square", "width": s.size, "height": s.size,
                "edges": {"top": BLACK, "bottom": BLACK, "left": WHITE, "right": WHITE},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
