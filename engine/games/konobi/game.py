"""Konobi — a drawless connection game by Luis Bolaños Mures (2012).

Played on the points of an initially empty NxN square board. Black owns the
top and bottom edges, White the left and right edges. Starting with Black,
players alternate placing one stone of their colour on an empty point.

Definitions (verbatim from the designer's rule sheet):
  * Two like-coloured stones are STRONGLY connected if orthogonally adjacent,
    and WEAKLY connected if diagonally adjacent WITHOUT sharing any strongly
    connected neighbour (a like-coloured stone orthogonally adjacent to both).
    Different-coloured stones never connect.
  * A chain is a set of connected stones (strong or weak links both count).

Placement restrictions:
  1. The kosumi/nobi rule (the game's namesake): "It's illegal to make a weak
     connection to a certain stone unless it's impossible to make a placement
     which is both strongly connected to that stone and not weakly connected
     to another."  Concretely: if your placement would be weakly connected to
     stone q, it is legal only if EVERY empty orthogonal neighbour of q would,
     if played, be weakly connected to some stone (or form a crosscut, i.e.
     be illegal).  If any "clean" strong attachment to q exists, you must not
     attach to q weakly.  (When a placement weakly connects to several stones,
     the condition must hold for each of them.)
  2. No CROSSCUT: you may never complete a 2x2 checkerboard of two diagonally
     adjacent Black and two diagonally adjacent White stones.

If a player has no legal placement they must pass (passing is otherwise not
allowed). The winner is the player who completes a chain of their colour
touching their two opposite edges. Because a diagonal pair sharing a friendly
orthogonal neighbour is chain-connected THROUGH that neighbour, chain
connectivity is exactly 8-connectivity of like-coloured stones; the crosscut
ban keeps opposing chains from crossing, so a finished game has one winner.
Draws are impossible in practice; a hypothetical double-pass with no winner
is scored as an honest draw (never observed; see rules.md).

Pie rule: on White's first turn only, White may "swap" — Black's opening
stone is removed and replaced by a White stone on the diagonally mirrored
point ("a point diagonally symmetrical to it", per the designer's Zillions
description; the .zrf mirrors across the other diagonal — equivalent up to
the board's 180° symmetry).

Sources: BGG #123213 description, the official Konobi.pdf rule sheet (Nov
2012, incl. the worked legality examples and the 5x5 sample game used by
selftest.py), and the designer's Konobi.zrf v1.1 (its `verifications` /
`verify-nobi-impossible` encode rule 1; see rules.md for a note on one .zrf
pattern this port intentionally does not reproduce).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black: top<->bottom.  White: left<->right.

_ORTH = [(0, -1), (1, 0), (0, 1), (-1, 0)]
_DIAG = [(1, -1), (1, 1), (-1, 1), (-1, -1)]
_DIRS8 = _ORTH + _DIAG


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class KonobiState:
    size: int = 11
    board: dict = field(default_factory=dict)  # (c, r) -> BLACK/WHITE
    to_move: int = BLACK
    winner: Optional[int] = None
    ply: int = 0
    passes: int = 0      # consecutive passes
    dead: bool = False   # double pass with no winner -> honest draw


def _weak_partners(board: dict, c: int, r: int, player: int) -> list:
    """Stones `player` would become WEAKLY connected to by playing (c, r).

    Weak = diagonally adjacent friendly stone with NO friendly stone on either
    of the two shared orthogonal cells (which would strongly connect to both,
    making the link strong-mediated instead).
    """
    out = []
    for dc, dr in _DIAG:
        q = (c + dc, r + dr)
        if board.get(q) != player:
            continue
        if board.get((c + dc, r)) == player or board.get((c, r + dr)) == player:
            continue
        out.append(q)
    return out


def _makes_crosscut(board: dict, c: int, r: int, player: int) -> bool:
    """Would playing `player` at (c, r) complete a 2x2 crosscut checkerboard?"""
    opp = 1 - player
    for dc, dr in _DIAG:
        if (board.get((c + dc, r + dr)) == player
                and board.get((c + dc, r)) == opp
                and board.get((c, r + dr)) == opp):
            return True
    return False


def _legal_placement(board: dict, size: int, c: int, r: int, player: int) -> bool:
    if not (0 <= c < size and 0 <= r < size) or (c, r) in board:
        return False
    if _makes_crosscut(board, c, r, player):
        return False
    for q in _weak_partners(board, c, r, player):
        # Weak attachment to q is legal only if NO placement exists that is
        # strongly connected to q, legal, and weakly connected to nothing.
        for dc, dr in _ORTH:
            ac, ar = q[0] + dc, q[1] + dr
            if not (0 <= ac < size and 0 <= ar < size) or (ac, ar) in board:
                continue
            if _makes_crosscut(board, ac, ar, player):
                continue  # that placement would be illegal anyway
            if not _weak_partners(board, ac, ar, player):
                return False  # a clean strong attachment exists -> illegal
    return True


def _connects(board: dict, player: int, size: int) -> bool:
    """Does `player` span their two edges via an 8-connected chain?"""
    if player == BLACK:  # top (r=0) <-> bottom (r=size-1)
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == BLACK]
        at_goal = lambda cell: cell[1] == size - 1  # noqa: E731
    else:                # left (c=0) <-> right (c=size-1)
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


def _best_span(board: dict, player: int, size: int) -> float:
    """Largest fraction of the goal axis covered by one chain of `player`."""
    axis = 1 if player == BLACK else 0  # Black spans rows, White columns
    seen = set()
    best = 0.0
    for start, p in board.items():
        if p != player or start in seen:
            continue
        stack = [start]
        seen.add(start)
        lo = hi = start[axis]
        while stack:
            cc, cr = stack.pop()
            for dc, dr in _DIRS8:
                nb = (cc + dc, cr + dr)
                if nb not in seen and board.get(nb) == player:
                    seen.add(nb)
                    stack.append(nb)
                    lo = min(lo, nb[axis])
                    hi = max(hi, nb[axis])
        best = max(best, (hi - lo + 1) / size)
    return best


class Konobi(Game):
    name = "Konobi"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> KonobiState:
        size = int((options or {}).get("size", 11))
        return KonobiState(size=size)

    def current_player(self, s: KonobiState) -> int:
        return s.to_move

    def _placements(self, s: KonobiState) -> list:
        return [
            f"{c},{r}"
            for r in range(s.size)
            for c in range(s.size)
            if (c, r) not in s.board
            and _legal_placement(s.board, s.size, c, r, s.to_move)
        ]

    def legal_moves(self, s: KonobiState) -> list:
        if s.winner is not None or s.dead:
            return []
        moves = self._placements(s)
        if s.ply == 1:  # White's first turn: pie rule
            moves.append("swap")
        if not moves:
            return ["pass"]  # forced pass; never return []
        return moves

    def apply_move(self, s: KonobiState, move: str, rng=None) -> KonobiState:
        if move == "pass":
            passes = s.passes + 1
            return KonobiState(size=s.size, board=dict(s.board),
                               to_move=1 - s.to_move, winner=s.winner,
                               ply=s.ply + 1, passes=passes,
                               dead=passes >= 2)
        if move == "swap":
            # Pie rule per the designer's .zrf: Black's lone stone is removed
            # and White gets a stone on the diagonally mirrored point.
            (c, r), _ = next(iter(s.board.items()))
            return KonobiState(size=s.size, board={(r, c): WHITE},
                               to_move=BLACK, winner=None, ply=s.ply + 1)
        c, r = _cell(move)
        board = dict(s.board)
        board[(c, r)] = s.to_move
        winner = s.to_move if _connects(board, s.to_move, s.size) else None
        return KonobiState(size=s.size, board=board, to_move=1 - s.to_move,
                           winner=winner, ply=s.ply + 1)

    def is_terminal(self, s: KonobiState) -> bool:
        return s.winner is not None or s.dead

    def returns(self, s: KonobiState) -> list:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # double-pass stalemate: honest draw (unreachable in practice)

    def heuristic(self, s: KonobiState) -> list:
        d = _best_span(s.board, BLACK, s.size) - _best_span(s.board, WHITE, s.size)
        return [d, -d]

    def serialize(self, s: KonobiState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "passes": s.passes,
            "dead": s.dead,
        }

    def deserialize(self, d: dict) -> KonobiState:
        return KonobiState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            ply=d.get("ply", len(d["board"])),
            passes=d.get("passes", 0),
            dead=d.get("dead", False),
        )

    def describe_move(self, s: KonobiState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if move == "pass":
            return "pass (no legal placement)"
        c, r = _cell(move)
        letters = "abcdefghijklmnopqrstuvwxyz"
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def render(self, s: KonobiState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.dead:
            caption = "Draw (double pass)"
        else:
            edge = "top–bottom" if s.to_move == BLACK else "left–right"
            caption = f"{names[s.to_move]} to move ({edge})"
        return {
            "board": {
                "type": "square", "width": s.size, "height": s.size,
                "edges": {"top": BLACK, "bottom": BLACK,
                          "left": WHITE, "right": WHITE},
            },
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
