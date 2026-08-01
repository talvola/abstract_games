"""Necklace - a square-board connection game by Mark Steere and Luis Bolanos
Mures (March 2024).

Played on the points of an initially empty NxN square grid (rendered here as an
NxN grid of cells).  The TOP and BOTTOM board edges are RED, the LEFT and RIGHT
edges are BLUE.  Red (player 0) must form a path of red stones - interconnected
via HORIZONTAL or VERTICAL adjacencies only - connecting the two red sides;
Blue (player 1) must connect the two blue sides.  Diagonal adjacency does NOT
connect: the designers call Necklace an "OOSCG" (orthogonal only square
connection game).

Players alternate placing one stone of their own colour on an unoccupied point,
RED FIRST.  "Passing is not allowed, but if you don't have an available
placement, your turn is skipped."

PLACEMENT RESTRICTIONS (both must hold; the official sheet lists exactly these
two and no others):

  1. Your placement must not create a CROSSCUT.  A crosscut is four stones, two
     of each colour, filling a 2x2 area, each stone orthogonally adjacent to its
     two enemy stones - i.e. a filled 2x2 whose two diagonals are monochrome and
     of opposite colours.  Figure 2 of the sheet prints "the two possible
     crosscut formations", which are exactly the two diagonal orientations.

  2. After your placement, any group of unoccupied points must include an edge
     point.  ("Any empty region - a maximal set of orthogonally adjacent, empty
     points - must include a point on the edge of the board.")  This is the
     no-loop rule the design notes describe, and it is what gives the game its
     name: a closed necklace of stones is forbidden.

Source: the official rule sheet, marksteeregames.com/Necklace_rules.pdf
(Illustrator PDF, ModDate 2024-03-30 17:33:21 PDT, md5
43183b5648e896bbe07e168ae0fec4fd).  All three figures are reproduced verbatim
in selftest.py:

  Figure 1  a 9x9 position in which Red has won.  Its coloured frame is the
            ground truth for the seat/edge mapping: the RED bars are the top and
            bottom of the board, the BLUE bars the left and right, and the
            winning red chain runs from the top row to the bottom row.
  Figure 2  the two crosscut formations.
  Figure 3  a 9x9 position with a green dot on AN illegal placement (the sheet
            does not claim it is the only one, and it is not); the dot sits on
            the BOTTOM EDGE and filling it would strand the empty group
            (3,7),(4,6),(4,7),(5,7) with no edge point.  The selftest pins the
            FULL illegal-placement set for both colours, which is what actually
            discriminates the wrong readings of restriction 1.

NOTE ON THE PIE RULE.  The official sheet has NO pie rule - the PLAY section
says only "starting with Red".  (AbstractPlay's implementation carries a
site-level `flags: ["pie"]`, which is a UI convention of that site, not a rule
of Necklace.)  This package follows the sheet: no swap.

IMPLEMENTATION NOTES

* Restriction 1 is judged on the position AFTER the placement, and only the
  four 2x2 areas containing the new stone can gain a crosscut, so the test is
  local: the placement is illegal iff some diagonal neighbour holds a FRIENDLY
  stone while both of the two points orthogonally between them hold ENEMY
  stones.  By induction no crosscut is ever present on the board (the empty
  board has none and no legal move creates one) - `crosscuts_on_board` is the
  diagnostic that checks this and the selftest asserts it every ply.

* Restriction 2 is likewise judged AFTER the placement, and only empty regions
  TOUCHING the new stone can change, so it suffices to flood out from each
  empty orthogonal neighbour of the candidate point (with the candidate point
  treated as a wall) and require every such flood to reach an edge point.
  `enclosed_regions` is the independent whole-board recomputation; the selftest
  cross-checks the two against each other on every position it visits.

* Skips are applied inside apply_move (the platform wants a non-empty
  legal_moves on every non-terminal state), so EVERY ply of the game is a
  placement.  If NEITHER player can place, the game ends; with no connection on
  the board that would be an honest draw.  That branch is provably unreachable
  (rules.md carries the proof, and selftest.py asserts both of its lemmas on
  constructed inputs), but a fabricated tiebreak would be a bug, so the draw is
  real code rather than an invented winner.

* A DECISIVE RESULT OUTRANKS THE STALL: the winning connection is checked
  before the skip/stall bookkeeping, so a placement that connects wins even if
  it simultaneously leaves both players with no legal placement.

TERMINATION.  Every ply places one stone on a previously empty point and stones
are never removed or moved, so the number of empty points strictly decreases
and the game lasts at most `max_plies(size) = size * size` plies.  A skipped
turn is not a ply of its own (it is folded into the placement that precedes
it), so it cannot extend the bound.  No ply cap and no repetition rule are
needed or shipped.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1        # Red joins top<->bottom (rows), Blue left<->right (cols)

_ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))
_DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def max_plies(size: int) -> int:
    """Provable upper bound on the number of plies in a game of this size.

    Derived from named factors, not pinned: every ply places exactly one stone
    on a previously empty point, stones are never removed or moved, and there
    are `size * size` points.  A skipped turn places no stone but is also not a
    ply here (it is folded into the preceding placement inside `apply_move`),
    so it adds nothing to the bound.
    """
    return size * size


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class NecklaceState:
    size: int = 11
    board: dict = field(default_factory=dict)   # (c, r) -> RED / BLUE
    to_move: int = RED
    last: Optional[tuple] = None                # stone placed by the previous mover
    winner: Optional[int] = None
    stalled: bool = False                       # neither player can place
    ply: int = 0
    skips: int = 0                              # turns skipped so far (no placement)


# --------------------------------------------------------------------------
# restriction 1: crosscuts
# --------------------------------------------------------------------------

def creates_crosscut(board: dict, c: int, r: int, player: int) -> bool:
    """Would `player` placing on the empty point (c, r) create a crosscut?

    A crosscut is a filled 2x2 whose two diagonals are monochrome and of
    opposite colours.  Only the four 2x2 areas containing (c, r) can gain one,
    and in each of them (c, r) is a corner, so the test is: the diagonally
    opposite point holds a FRIENDLY stone and both remaining points of that 2x2
    hold ENEMY stones.
    """
    enemy = 1 - player
    for dc, dr in _DIAG:
        if (board.get((c + dc, r + dr)) == player
                and board.get((c + dc, r)) == enemy
                and board.get((c, r + dr)) == enemy):
            return True
    return False


def crosscuts_on_board(board: dict, size: int) -> list:
    """Every crosscut present anywhere on the board (diagnostic).

    Returns the (c, r) top-left points of the offending 2x2 areas.  In real
    play this is ALWAYS empty: the empty board has no crosscut and no legal
    placement creates one.
    """
    out = []
    for c in range(size - 1):
        for r in range(size - 1):
            a = board.get((c, r))
            b = board.get((c + 1, r))
            d = board.get((c, r + 1))
            e = board.get((c + 1, r + 1))
            if a is None or b is None or d is None or e is None:
                continue
            if a == e and b == d and a != b:
                out.append((c, r))
    return out


# --------------------------------------------------------------------------
# restriction 2: every empty region must contain an edge point
# --------------------------------------------------------------------------

def is_edge(size: int, c: int, r: int) -> bool:
    """Is (c, r) a point on the edge of the board?  (Corners count, of course.)"""
    return c == 0 or r == 0 or c == size - 1 or r == size - 1


def encloses(board: dict, size: int, c: int, r: int) -> bool:
    """Would placing ANY stone on the empty point (c, r) strand an empty region?

    Colour-blind - restriction 2 does not care whose stone it is.  Placing at
    (c, r) can only affect empty regions that touch (c, r), so it is enough to
    flood out from each empty orthogonal neighbour with (c, r) treated as a
    wall and require every such flood to reach an edge point.

    (Regions not touching (c, r) are unchanged and satisfied the rule already:
    the empty board does, and every legal placement preserves it.)

    Each neighbour gets its OWN `seen` set.  Sharing one `seen` across the four
    floods is UNSOUND: a flood that exits early at an edge leaves its frontier
    marked, and a later flood then refuses to expand through those points and
    can report a false enclosure.  `proven` is the sound form of that
    memoisation - a point enqueued by a flood that DID reach an edge is itself
    edge-connected (same component as the edge point), so reaching one is
    proof enough for a later flood.
    """
    blocked = (c, r)
    proven = set()
    for dc, dr in _ORTH:
        start = (c + dc, r + dr)
        if not (0 <= start[0] < size and 0 <= start[1] < size):
            continue
        if start in board or start in proven:
            # occupied, or already known to lie in an edge-connected region
            continue
        # breadth-first so the nearest edge point is found first
        seen = {blocked, start}
        queue = deque([start])
        found = False
        while queue:
            cc, cr = queue.popleft()
            if is_edge(size, cc, cr) or (cc, cr) in proven:
                found = True
                break
            for ec, er in _ORTH:
                nb = (cc + ec, cr + er)
                if not (0 <= nb[0] < size and 0 <= nb[1] < size):
                    continue
                if nb in board or nb in seen:
                    continue
                seen.add(nb)
                queue.append(nb)
        if not found:
            return True
        seen.discard(blocked)
        proven |= seen
    return False


def enclosed_regions(board: dict, size: int) -> list:
    """Every empty region with no edge point (diagnostic, whole-board).

    Returns a list of sorted (c, r) tuples.  In real play this is ALWAYS empty
    - that is exactly restriction 2, maintained inductively.  This function is
    an INDEPENDENT recomputation of the rule, deliberately written without
    reference to any candidate point, so the selftest can cross-check the local
    `encloses` predicate against it.
    """
    out = []
    seen = set()
    for r0 in range(size):
        for c0 in range(size):
            if (c0, r0) in board or (c0, r0) in seen:
                continue
            region = []
            stack = [(c0, r0)]
            seen.add((c0, r0))
            touches_edge = False
            while stack:
                cur = stack.pop()
                region.append(cur)
                if is_edge(size, *cur):
                    touches_edge = True
                for dc, dr in _ORTH:
                    nb = (cur[0] + dc, cur[1] + dr)
                    if not (0 <= nb[0] < size and 0 <= nb[1] < size):
                        continue
                    if nb in board or nb in seen:
                        continue
                    seen.add(nb)
                    stack.append(nb)
            if not touches_edge:
                out.append(tuple(sorted(region)))
    return out


# --------------------------------------------------------------------------
# legality / connection
# --------------------------------------------------------------------------

def placements(board: dict, size: int, player: int) -> list:
    """Every legal placement point for `player`, in (c, r) reading order."""
    return [(c, r) for r in range(size) for c in range(size)
            if (c, r) not in board
            and not creates_crosscut(board, c, r, player)
            and not encloses(board, size, c, r)]


def has_placement(board: dict, size: int, player: int) -> bool:
    """Does `player` have ANY legal placement?  (short-circuiting `placements`)"""
    for r in range(size):
        for c in range(size):
            if ((c, r) not in board
                    and not creates_crosscut(board, c, r, player)
                    and not encloses(board, size, c, r)):
                return True
    return False


def connects(board: dict, player: int, size: int) -> bool:
    """Does `player` join their two edges via an ORTHOGONAL chain of stones?"""
    if player == RED:                          # row 0 <-> row size-1
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == RED]
        goal = size - 1

        def at_goal(cell):
            return cell[1] == goal
    else:                                      # col 0 <-> col size-1
        starts = [(0, r) for r in range(size) if board.get((0, r)) == BLUE]
        goal = size - 1

        def at_goal(cell):
            return cell[0] == goal
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


def connection_path(board: dict, player: int, size: int) -> list:
    """One winning chain for `player`, or [] if there is none (diagnostic/render)."""
    if player == RED:
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == RED]

        def at_goal(cell):
            return cell[1] == size - 1
    else:
        starts = [(0, r) for r in range(size) if board.get((0, r)) == BLUE]

        def at_goal(cell):
            return cell[0] == size - 1
    prev = {s: None for s in starts}
    queue = deque(starts)
    while queue:
        cur = queue.popleft()
        if at_goal(cur):
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        for dc, dr in _ORTH:
            nb = (cur[0] + dc, cur[1] + dr)
            if nb not in prev and board.get(nb) == player:
                prev[nb] = cur
                queue.append(nb)
    return []


class Necklace(Game):
    name = "Necklace"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> NecklaceState:
        size = int((options or {}).get("size", 11))
        return NecklaceState(size=size)

    def current_player(self, s: NecklaceState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def legal_moves(self, s: NecklaceState) -> list:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in placements(s.board, s.size, s.to_move)]

    # -- move application ---------------------------------------------------

    def _advance(self, s: NecklaceState, mover: int) -> None:
        """Hand the turn on after `mover` placed, applying the skip rule.

        "Passing is not allowed, but if you don't have an available placement,
        your turn is skipped."  A skip is not a ply of its own here: if the
        opponent cannot place we simply give the turn back to `mover`; if
        neither side can place the game is over.
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

    def apply_move(self, s: NecklaceState, move: str, rng=None) -> NecklaceState:
        me = s.to_move
        p = _cell(move)
        board = dict(s.board)
        board[p] = me
        out = NecklaceState(size=s.size, board=board, to_move=1 - me, last=p,
                            ply=s.ply + 1, skips=s.skips)
        # A decisive result outranks the stall bookkeeping.
        if connects(board, me, s.size):
            out.winner = me
            return out
        self._advance(out, me)
        return out

    # -- termination / scoring ----------------------------------------------

    def is_terminal(self, s: NecklaceState) -> bool:
        return s.winner is not None or s.stalled

    def returns(self, s: NecklaceState) -> list:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]    # both players stuck with nobody connected: a draw

    # -- serialization ------------------------------------------------------

    def serialize(self, s: NecklaceState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "last": None if s.last is None else f"{s.last[0]},{s.last[1]}",
            "winner": s.winner,
            "stalled": s.stalled,
            "ply": s.ply,
            "skips": s.skips,
        }

    def deserialize(self, d: dict) -> NecklaceState:
        return NecklaceState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            last=None if d.get("last") is None else _cell(d["last"]),
            winner=d.get("winner"),
            stalled=d.get("stalled", False),
            ply=d.get("ply", 0),
            skips=d.get("skips", 0),
        )

    # -- presentation -------------------------------------------------------

    def _coord(self, cell) -> str:
        letters = "abcdefghijklmnopqrstuvwxyz"
        c, r = cell
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def describe_move(self, s: NecklaceState, move: str) -> str:
        p = _cell(move)
        text = self._coord(p)
        nxt = self.apply_move(s, move)
        if nxt.winner is not None:
            text += "#"
        elif nxt.stalled:
            text += " (both stuck)"
        elif nxt.skips > s.skips:
            text += " (opponent skipped)"
        return text

    # -- bot evaluation -----------------------------------------------------

    def _edge_distance(self, s: NecklaceState, player: int) -> int:
        """How many further stones `player` needs to join their two edges.

        A 0-1 BFS over the board: one of your own stones costs 0 to pass
        through, an empty point costs 1, an enemy stone blocks.  Ignores both
        placement restrictions, so it is only a rough guide - which is all the
        rollout cutoff needs.
        """
        n = s.size
        big = n * n
        dist = {}
        dq = deque()
        for i in range(n):
            cell = (i, 0) if player == RED else (0, i)
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
            if (cur[1] if player == RED else cur[0]) == n - 1:
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

    def heuristic(self, s: NecklaceState) -> list:
        """MCTS rollout-cutoff evaluation: payoffs [red, blue].

        Positive = Red is closer to joining the top and bottom edges than Blue
        is to joining the left and right ones.  MEASURED through `MCTSBot`, the
        consumer that uses it: 17/24 head-to-head against the same bot with no
        evaluation at the production shape (9x9, max_rollout=50, 0.5s/move,
        colours alternating), and 9/9 at max_rollout=4 where the cutoff fires on
        every rollout.  See rules.md.
        """
        val = math.tanh(0.35 * (self._edge_distance(s, BLUE)
                                - self._edge_distance(s, RED)))
        return [val, -val]

    def render(self, s: NecklaceState, perspective=None) -> dict:
        names = {RED: "Red", BLUE: "Blue"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.stalled:
            caption = "Draw - neither player has a legal placement"
        else:
            edge = "top-bottom" if s.to_move == RED else "left-right"
            caption = f"{names[s.to_move]} to move ({edge})"
        # The winning chain goes in FIRST so the last-move marker still wins on
        # the point they share: Board.jsx keys `highlights` by cell (last write
        # wins) and draws only the 'goal' and 'last-move' kinds.
        highlights = []
        if s.winner is not None:
            highlights += [{"cell": f"{c},{r}", "kind": "goal"}
                           for (c, r) in connection_path(s.board, s.winner, s.size)]
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})
        return {
            "board": {
                "type": "square", "width": s.size, "height": s.size,
                "edges": {"top": RED, "bottom": RED,
                          "left": BLUE, "right": BLUE},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
