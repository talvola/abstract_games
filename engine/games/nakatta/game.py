"""Nakatta — a square-board connection game by Luis Bolanos Mures and Mark Steere (April 2024).

Played on the points (intersections) of an initially empty NxN square grid,
rendered here as an NxN grid of cells.  The TOP and BOTTOM board edges are
black, the LEFT and RIGHT edges are white.  Black (player 0) wins by forming a
chain of ORTHOGONALLY (horizontally or vertically) interconnected black stones
touching the two black edges; White (player 1) joins the two white edges.

Black plays first, then turns alternate.  On your turn you place one stone of
your colour on an empty point; AFTER your placement there must be no "hard
corner" and no "naked attachment" anywhere on the board.  Passing is not
allowed, but a player with no legal move has their turn skipped.  Pie rule:
on White's first turn only, White may swap sides with Black instead of moving.

    HARD CORNER       an illegal 2x2 pattern: two diagonally adjacent stones of
                      the same colour, one stone of the opposite colour, and one
                      empty point.  (The four points of a 2x2 split into two
                      diagonals; one diagonal carries the like-coloured pair, so
                      the empty point is necessarily diagonally opposite the lone
                      enemy stone.  The prose admits no other arrangement.)

    NAKED ATTACHMENT  an illegal 2x2 pattern: two ORTHOGONALLY adjacent empty
                      points, one black stone and one white stone.  (The two
                      stones are then also orthogonally adjacent — an
                      "attachment" — and both points that would clothe it on one
                      side are empty.)

Source: the official rule sheet, marksteeregames.com/Nakatta_rules.pdf
(Adobe Illustrator PDF, ModDate 2024-04-24, md5 ddb59ae747e740e817d02ff8cd90cb57).
The live sheet is byte-identical to its single Wayback capture (2024-06-18), so
unlike five of the six Steere sheets ported before it, this one has never been
revised.  Its three figures are decoded from the vector artwork and reproduced
verbatim in selftest.py:

    Figure 1  a won 9x9 position ("Black wins") — 25 stones, a black chain from
              the top edge to the bottom edge, and (the load-bearing premise)
              ZERO hard corners and ZERO naked attachments, i.e. a legal
              position actually reachable by play.
    Figure 2  a 9x9 position stated to contain exactly SIX hard corners.
    Figure 3  a 9x9 position stated to contain exactly SEVEN naked attachments.

IMPLEMENTATION NOTES

* "There must be no hard corners and no naked attachments on the board" is a
  GLOBAL condition on the position after the placement, and it is implemented
  as a LOCAL test on the (at most four) 2x2 areas containing the placed point.
  The two are equivalent because no legal position ever contains a pattern:
  the empty board contains none, both patterns require at least one EMPTY point
  inside the 2x2, so adding a stone can only destroy patterns that were already
  there, and a 2x2 not containing the placed point is unchanged.  Every pattern
  a move creates therefore contains the stone just placed.  `patterns_on_board`
  performs the full global scan and selftest.py asserts the two agree — both on
  the sheet's figures and on every ply of whole random games.

* Both patterns are closed under reflection, rotation AND colour reversal, and
  transposing the board exchanges Black's row goal with White's column goal.
  Nakatta is therefore symmetric under (transpose + colour swap), which is what
  makes the pie swap implementable as a board transformation — see apply_move.

* Skips are applied inside apply_move (the platform requires a non-empty
  legal_moves on every non-terminal state), so every ply of the game is either a
  placement or the one-off pie swap; a skipped turn is never a ply of its own.

TERMINATION.  Stones are never removed, and every ply either places a stone on a
previously empty point or is the pie swap (which places no stone and can happen
at most once), so a game lasts at most `max_plies(size) = size*size + 1` plies.
No ply cap and no repetition rule are needed or shipped.

BOT.  A `heuristic` IS shipped (connection distance).  It is not decoration:
a Nakatta game runs ~0.85 * size**2 plies, so from the default board size upwards
MCTSBot's 50-ply rollout cutoff always fires and a bot without an eval sees every
rollout as a draw.  See rules.md for the measured head-to-head numbers, including
the two sizes at which the two bots are indistinguishable.

DRAWS.  If NEITHER player has a legal placement and nobody has connected, that
is an honest draw (`winner=None`, returns [0, 0]).  The rule sheet does not say
this cannot happen and this implementation does not pretend otherwise; see
rules.md for what is known about its reachability.  A decisive connection is
always detected BEFORE the stall test (a win outranks the stall), because
apply_move returns immediately when the mover connects.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black joins top<->bottom (rows), White joins left<->right (cols)

_ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))

# The four points of a 2x2 area anchored at (c, r), in a fixed order.  Index i
# and index 3 - i are DIAGONAL partners; every other pair is orthogonal.  Both
# pattern predicates below rely on exactly that property of this ordering.
_QUAD = ((0, 0), (1, 0), (0, 1), (1, 1))
assert all(_QUAD[i][0] != _QUAD[3 - i][0] and _QUAD[i][1] != _QUAD[3 - i][1]
           for i in range(4)), "index i and 3-i must be diagonal partners"


def max_plies(size: int) -> int:
    """Provable upper bound on the number of plies in a game of this size.

    Derived from named factors, not pinned: every ply is either a PLACEMENT on a
    previously empty point (at most `size * size` of those, since stones are
    never removed and a skipped turn is not a ply) or the pie-rule SWAP, which
    places no stone and can happen at most once per game.
    """
    return size * size + 1


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class NakattaState:
    size: int = 13
    board: dict = field(default_factory=dict)   # (c, r) -> BLACK / WHITE
    to_move: int = BLACK
    last: Optional[tuple] = None                # stone placed by the previous mover
    winner: Optional[int] = None
    stalled: bool = False                       # neither player can place
    ply: int = 0
    skips: int = 0                              # turns skipped so far (no placement)
    swapped: bool = False                       # the pie rule was exercised


# --------------------------------------------------------------------------
# the two illegal 2x2 patterns
# --------------------------------------------------------------------------

def _hard_corner_at(board: dict, c: int, r: int) -> bool:
    """Is the 2x2 area anchored at (c, r) a HARD CORNER?

    "Two diagonally adjacent stones of the same color, one stone of the opposite
    color, and one empty point."  So: exactly one of the four points is empty,
    the two stones on the diagonal NOT containing that empty point share a
    colour, and the remaining stone (diagonally opposite the empty point) is of
    the other colour.
    """
    cells = [(c + dc, r + dr) for dc, dr in _QUAD]
    holes = [i for i, x in enumerate(cells) if x not in board]
    if len(holes) != 1:
        return False
    hole = holes[0]
    lone = board[cells[3 - hole]]                 # diagonally opposite the hole
    pair = [board[x] for i, x in enumerate(cells) if i not in (hole, 3 - hole)]
    return pair[0] == pair[1] and pair[0] != lone


def _naked_attachment_at(board: dict, c: int, r: int) -> bool:
    """Is the 2x2 area anchored at (c, r) a NAKED ATTACHMENT?

    "Two orthogonally adjacent empty points, one black stone, and one white
    stone."  So: exactly two of the four points are empty AND they are NOT
    diagonal partners (indices summing to 3), and the two stones differ in
    colour.
    """
    cells = [(c + dc, r + dr) for dc, dr in _QUAD]
    holes = [i for i, x in enumerate(cells) if x not in board]
    if len(holes) != 2 or holes[0] + holes[1] == 3:
        return False
    stones = [board[x] for i, x in enumerate(cells) if i not in holes]
    return stones[0] != stones[1]


def patterns_on_board(board: dict, size: int) -> list:
    """Every illegal pattern present anywhere on the board (global scan).

    Returns a list of ("hard", c, r) / ("naked", c, r) tuples, (c, r) being the
    2x2 area's anchor point.  In real play this is always empty: no legal move
    ever creates a pattern and adding stones can only destroy them.  It is also
    the predicate the rule sheet's Figures 2 and 3 count (6 and 7), so it is
    exercised directly by selftest.py rather than only through legality.
    """
    out = []
    for c in range(size - 1):
        for r in range(size - 1):
            if _hard_corner_at(board, c, r):
                out.append(("hard", c, r))
            if _naked_attachment_at(board, c, r):
                out.append(("naked", c, r))
    return out


def forms_pattern(board: dict, size: int, c: int, r: int, player: int) -> bool:
    """Would placing `player`'s stone on the empty point (c, r) form a pattern?

    Only 2x2 areas CONTAINING (c, r) can gain one (see the module docstring), so
    only those are examined.
    """
    board[(c, r)] = player           # tentatively place (restored below)
    try:
        for dc in (-1, 0):
            for dr in (-1, 0):
                cc, rr = c + dc, r + dr
                if 0 <= cc <= size - 2 and 0 <= rr <= size - 2:
                    if _hard_corner_at(board, cc, rr) or _naked_attachment_at(board, cc, rr):
                        return True
        return False
    finally:
        del board[(c, r)]


def placements(board: dict, size: int, player: int) -> list:
    """Every legal placement point for `player`, in (c, r) order."""
    return [(c, r) for r in range(size) for c in range(size)
            if (c, r) not in board and not forms_pattern(board, size, c, r, player)]


def has_placement(board: dict, size: int, player: int) -> bool:
    """Does `player` have ANY legal placement?  (short-circuiting `placements`)"""
    for r in range(size):
        for c in range(size):
            if (c, r) not in board and not forms_pattern(board, size, c, r, player):
                return True
    return False


def connects(board: dict, player: int, size: int) -> bool:
    """Does `player` join their two edges via an ORTHOGONAL chain of stones?"""
    if player == BLACK:                       # row 0 <-> row size-1
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == BLACK]
        def at_goal(cell):
            return cell[1] == size - 1
    else:                                     # col 0 <-> col size-1
        starts = [(0, r) for r in range(size) if board.get((0, r)) == WHITE]
        def at_goal(cell):
            return cell[0] == size - 1
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


class Nakatta(Game):
    name = "Nakatta"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> NakattaState:
        size = int((options or {}).get("size", 13))
        return NakattaState(size=size)

    def current_player(self, s: NakattaState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def legal_moves(self, s: NakattaState) -> list:
        if self.is_terminal(s):
            return []
        moves = [f"{c},{r}" for (c, r) in placements(s.board, s.size, s.to_move)]
        if s.ply == 1 and len(s.board) == 1 and not s.swapped:
            moves.append("swap")     # pie rule: White's first turn only
        return moves

    # -- move application ---------------------------------------------------

    def _advance(self, s: NakattaState, mover: int) -> None:
        """Hand the turn on after `mover` acted, applying the skip rule.

        "Passing is not allowed, but, if you have no legal moves available, your
        turn is skipped."  A skip is not a ply of its own here: if the opponent
        cannot place we simply give the turn back to `mover`; if neither side
        can place, the game is over.
        """
        opp = 1 - mover
        if has_placement(s.board, s.size, opp):
            s.to_move = opp
        elif has_placement(s.board, s.size, mover):
            s.to_move = mover
            s.skips += 1
        else:
            s.stalled = True
            s.to_move = opp

    def apply_move(self, s: NakattaState, move: str, rng=None) -> NakattaState:
        if move == "swap":
            # Pie rule: "White will have the option, on their first turn only, to
            # swap sides with Black instead of making a regular move."  Seats are
            # fixed on this platform, so the value-preserving equivalent is to
            # transpose the position and reverse the colours.  Nakatta is
            # symmetric under that transformation: both illegal patterns are
            # closed under reflection and under colour reversal, and reflecting
            # in the main diagonal exchanges the black top/bottom goal with the
            # white left/right goal.  Black's lone stone at (c, r) therefore
            # becomes a WHITE stone at (r, c), and Black (seat 0) is on move
            # again — exactly the position the swapper obtains.  Recolouring in
            # place would NOT preserve the value, since the two colours aim at
            # different pairs of edges.
            ((c, r), _owner), = s.board.items()
            out = NakattaState(size=s.size, board={(r, c): WHITE},
                               to_move=BLACK, last=(r, c), ply=s.ply + 1,
                               swapped=True)
            self._advance(out, WHITE)      # White has just acted
            return out

        me = s.to_move
        p = _cell(move)
        board = dict(s.board)
        board[p] = me
        out = NakattaState(size=s.size, board=board, to_move=1 - me, last=p,
                           ply=s.ply + 1, skips=s.skips, swapped=s.swapped)
        if connects(board, me, s.size):
            out.winner = me            # a decisive result outranks the stall test
            return out
        self._advance(out, me)
        return out

    # -- termination / scoring ----------------------------------------------

    def is_terminal(self, s: NakattaState) -> bool:
        return s.winner is not None or s.stalled

    def returns(self, s: NakattaState) -> list:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]    # both players stuck with nobody connected: a draw

    # -- serialization ------------------------------------------------------

    def serialize(self, s: NakattaState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "last": None if s.last is None else f"{s.last[0]},{s.last[1]}",
            "winner": s.winner,
            "stalled": s.stalled,
            "ply": s.ply,
            "skips": s.skips,
            "swapped": s.swapped,
        }

    def deserialize(self, d: dict) -> NakattaState:
        return NakattaState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            last=None if d.get("last") is None else _cell(d["last"]),
            winner=d.get("winner"),
            stalled=d.get("stalled", False),
            ply=d.get("ply", 0),
            skips=d.get("skips", 0),
            swapped=d.get("swapped", False),
        )

    # -- presentation -------------------------------------------------------

    def _coord(self, cell) -> str:
        letters = "abcdefghijklmnopqrstuvwxyz"
        c, r = cell
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def describe_move(self, s: NakattaState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        p = _cell(move)
        text = self._coord(p)
        nxt = self.apply_move(s, move)
        if nxt.winner is not None:
            text += "#"
        elif nxt.skips > s.skips:
            text += " (opponent skipped)"
        return text

    def heuristic(self, s: NakattaState) -> list:
        """MCTS payoffs [black, white] from the connection distance.

        `MCTSBot` truncates its rollouts after `max_rollout` plies (50 by
        default) and scores the position with this instead.  A Nakatta game runs
        to roughly 0.85 * size**2 plies, so at EVERY offered board size the
        cutoff always bites and a bot without an eval scores every rollout as a
        draw -- that is, it has no signal at all.  Measured through MCTSBot, the
        consumer that uses it: at 7x7 with max_rollout=6 (the cutoff forced) the
        bot with this eval beat the identical bot without it 60-0 over 60 games,
        and 56-4 on an independent replay with different seeds.  At the
        platform's DEFAULT 50-ply rollout on the sizes cheap enough to measure
        (9x9, 11x11) the two are indistinguishable -- rules.md reports those
        numbers and does not dress them up.  The eval ships because it is never
        measurably worse and is the bot's only signal from 13x13 upwards.

        The value is the difference in how many further stones each side needs to
        join their edges (0-1 BFS: an own stone costs 0, an empty point 1, an
        enemy stone blocks), squashed with tanh.  It ignores both pattern bans,
        so it is only a rough guide -- but a rough guide beats no guide.
        """
        db = self._edge_distance(s, BLACK)
        dw = self._edge_distance(s, WHITE)
        val = math.tanh(0.35 * (dw - db))       # positive = Black ahead
        return [val, -val]

    def _edge_distance(self, s: NakattaState, player: int) -> float:
        """Fewest further stones `player` needs to join their two edges."""
        n = s.size
        big = n * n
        dist = {}
        dq = deque()
        for i in range(n):
            cell = (i, 0) if player == BLACK else (0, i)
            owner = s.board.get(cell)
            if owner == 1 - player:
                continue
            d = 0 if owner == player else 1
            if dist.get(cell, big) > d:
                dist[cell] = d
                (dq.appendleft if d == 0 else dq.append)(cell)
        best = big
        while dq:
            cur = dq.popleft()
            d = dist[cur]
            if (cur[1] if player == BLACK else cur[0]) == n - 1:
                best = min(best, d)
                continue
            for dc, dr in _ORTH:
                nb = (cur[0] + dc, cur[1] + dr)
                if not (0 <= nb[0] < n and 0 <= nb[1] < n):
                    continue
                owner = s.board.get(nb)
                if owner == 1 - player:
                    continue
                nd = d + (0 if owner == player else 1)
                if dist.get(nb, big) > nd:
                    dist[nb] = nd
                    (dq.appendleft if nd == d else dq.append)(nb)
        return best

    def render(self, s: NakattaState, perspective=None) -> dict:
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
        elif s.stalled:
            caption = "Draw — neither player has a legal placement"
        else:
            edge = "top–bottom" if s.to_move == BLACK else "left–right"
            caption = f"{names[s.to_move]} to move ({edge})"
            if s.ply == 1 and len(s.board) == 1 and not s.swapped:
                caption += " — or swap (pie rule)"
        return {
            "board": {
                "type": "square", "width": s.size, "height": s.size,
                "edges": {"top": BLACK, "bottom": BLACK,
                          "left": WHITE, "right": WHITE},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
