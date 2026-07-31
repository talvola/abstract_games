"""Minefield — a square-board connection game by Mark Steere (May 2024).

Played on the points of an initially empty NxN square grid (rendered here as
an NxN grid of cells). The TOP and BOTTOM board edges are black, the LEFT and
RIGHT edges are white. Black (player 0) must form an ORTHOGONALLY (horizontally
and/or vertically) interconnected path of black stones joining the two black
edges; White (player 1) must join the two white edges.

Players alternate placing one stone of their own colour on an unoccupied point,
Black first. Passing is not allowed, but a player with no available placement
has their turn skipped. Minefield uses the pie rule: on White's first turn he
may switch colours and become Black, claiming the first placement as his own,
instead of placing a white stone.

No player may FORM either of the two prohibited glyphs (nor their reflections,
rotations or colour reversals):

  HARD CORNER  two stones of one colour and one stone of the other colour
               contained in a 2x2 area; the two same-coloured stones are
               diagonally adjacent; one point within the area is unoccupied.

  SWITCH       two stones of each colour contained in a 2x3 or a 2x4 area.
               Two stones of one colour occupy diagonally opposite corner
               points, the two stones of the other colour occupy the other two
               diagonally opposite corner points, and the non-corner points of
               the area are unoccupied.  (2x3 = "short switch", 2x4 = "long
               switch"; both orientations, i.e. 3x2 and 4x2, count.)

Source: the official rule sheet, marksteeregames.com/Minefield_rules.pdf
(Illustrator PDF, ModDate 2026-05-17 — a silent revision of the 2024-05-08
sheet, which had NO pie rule and did not mention colour reversals).  Figure 2
(the two glyphs, decoded from the vector artwork) and Figure 3 (a 9x9 position
whose 13 red dots are exactly Black's illegal placements) are both reproduced
verbatim in selftest.py and both match this implementation exactly.

Design notes carried over from the sheet: Luis Bolanos Mures made a material
contribution; Minefield is an "SPO OOSCG" (Single Placement Only, Orthogonal
Only Square Connection Game).

IMPLEMENTATION NOTES

* "Form a glyph" is judged on the position AFTER the placement.  No glyph can
  ever be present on the board (induction: the empty board has none, and both
  glyphs require an UNOCCUPIED point, so adding a stone can only destroy
  existing glyphs — every glyph created by a move therefore contains the stone
  just placed).  The legality test consequently only has to look at the 2x2 /
  2x3 / 2x4 areas that contain the candidate point, which is what the designer
  means by calling the mechanism "local".

* No crosscut (a full 2x2 with two interlocking opposite-colour diagonals) can
  ever appear: removing any one stone of a crosscut leaves a hard corner, so
  the 4th stone could never have been legally placed.  That is what makes a
  FULL board decisive — see rules.md for the argument.

* Skips are applied inside apply_move (the platform wants a non-empty
  legal_moves on every non-terminal state), so every ply of the game is either
  a placement or the single pie-rule swap.  If NEITHER player can place, the
  game ends; with no connection on the board that is an honest draw.

TERMINATION.  Stones are never removed and every ply either places a stone on a
previously empty point or is the one-off swap, so the game lasts at most
`max_plies(size) = size*size + 1` plies (the +1 is the swap ply, which places no
stone).  No ply cap and no repetition rule are needed or shipped.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black joins top<->bottom (rows), White left<->right (cols)

_ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))

# Switch areas: (width, height) in POINTS.  2x3 / 2x4 and their rotations.
SWITCH_DIMS = ((2, 3), (3, 2), (2, 4), (4, 2))
# Every switch area is exactly 2 points across on one axis; these are the
# lengths of the other axis.  Derived (not repeated) so the whole-board scan
# and the local legality test can never drift apart.
assert all(min(w, h) == 2 for (w, h) in SWITCH_DIMS)
SWITCH_LENGTHS = tuple(sorted({max(w, h) for (w, h) in SWITCH_DIMS}))


def max_plies(size: int) -> int:
    """Provable upper bound on the number of plies in a game of this size.

    Derived from named factors, not pinned: every ply is either a PLACEMENT on
    a previously empty point (at most `size * size` of those, since stones are
    never removed) or the pie-rule SWAP, which places no stone and can happen
    at most once per game.
    """
    return size * size + 1


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class MinefieldState:
    size: int = 11
    board: dict = field(default_factory=dict)   # (c, r) -> BLACK / WHITE
    to_move: int = BLACK
    last: Optional[tuple] = None                # stone placed by the previous mover
    winner: Optional[int] = None
    stalled: bool = False                       # neither player can place
    ply: int = 0
    skips: int = 0                              # turns skipped so far (no placement)


# --------------------------------------------------------------------------
# the two prohibited glyphs
# --------------------------------------------------------------------------

def _hard_corner_at(board: dict, c: int, r: int) -> bool:
    """Is the 2x2 area with corner (c, r) [cells (c..c+1, r..r+1)] a hard corner?

    Exactly three of the four points are occupied; the two occupied points that
    are diagonally adjacent to each other share a colour, and the third stone
    is of the other colour.
    """
    cells = ((c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1))
    holes = [i for i, x in enumerate(cells) if x not in board]
    if len(holes) != 1:
        return False
    hole = holes[0]
    # the point diagonally opposite the hole (index 3 - hole for this ordering)
    lone = board[cells[3 - hole]]
    pair = [board[x] for i, x in enumerate(cells) if i not in (hole, 3 - hole)]
    return pair[0] == pair[1] and pair[0] != lone


def _switch_at(board: dict, c: int, r: int, w: int, h: int) -> bool:
    """Is the w x h area with top-left point (c, r) a switch?

    All four corner points occupied, the two diagonals each monochrome and of
    different colours, and every non-corner point of the area unoccupied.
    """
    tl, tr = (c, r), (c + w - 1, r)
    bl, br = (c, r + h - 1), (c + w - 1, r + h - 1)
    a, b = board.get(tl), board.get(tr)
    d, e = board.get(bl), board.get(br)
    if a is None or b is None or d is None or e is None:
        return False
    if a != e or b != d or a == b:
        return False
    corners = (tl, tr, bl, br)
    for cc in range(c, c + w):
        for rr in range(r, r + h):
            if (cc, rr) not in corners and (cc, rr) in board:
                return False
    return True


def glyphs_on_board(board: dict, size: int) -> list:
    """Every prohibited glyph present anywhere on the board (diagnostic).

    Returns a list of ("hard", c, r) / ("switch", w, h, c, r) tuples, where
    (c, r) is the top-left point of the area.  In real play this is always
    empty: no legal move ever creates a glyph and adding stones can only
    destroy them.
    """
    out = []
    for c in range(size - 1):
        for r in range(size - 1):
            if _hard_corner_at(board, c, r):
                out.append(("hard", c, r))
    for (w, h) in SWITCH_DIMS:
        for c in range(size - w + 1):
            for r in range(size - h + 1):
                if _switch_at(board, c, r, w, h):
                    out.append(("switch", w, h, c, r))
    return out


def forms_glyph(board: dict, size: int, c: int, r: int, player: int) -> bool:
    """Would placing `player`'s stone on the empty point (c, r) form a glyph?

    Only areas CONTAINING (c, r) can gain a glyph, so only those are examined.
    """
    board[(c, r)] = player           # tentatively place (restored below)
    try:
        # hard corners: the 2x2 areas containing (c, r)
        for dc in (-1, 0):
            for dr in (-1, 0):
                cc, rr = c + dc, r + dr
                if 0 <= cc <= size - 2 and 0 <= rr <= size - 2:
                    if _hard_corner_at(board, cc, rr):
                        return True
        # Switches: (c, r) is occupied, so it must be a CORNER of the area —
        # and every switch area is 2 points wide on one axis, so the corner
        # NEXT to (c, r) on that axis is an immediate neighbour.  Requiring
        # that neighbour to be occupied prunes most areas without touching them.
        for dc in (-1, 1):               # 2 x h areas (h = 3, 4)
            cc = c + dc
            if 0 <= cc < size and (cc, r) in board:
                left = cc if dc < 0 else c
                for h in SWITCH_LENGTHS:
                    for dr in (0, h - 1):
                        rr = r - dr
                        if 0 <= rr <= size - h and _switch_at(board, left, rr, 2, h):
                            return True
        for dr in (-1, 1):               # w x 2 areas (w = 3, 4)
            rr = r + dr
            if 0 <= rr < size and (c, rr) in board:
                top = rr if dr < 0 else r
                for w in SWITCH_LENGTHS:
                    for dc in (0, w - 1):
                        cc = c - dc
                        if 0 <= cc <= size - w and _switch_at(board, cc, top, w, 2):
                            return True
        return False
    finally:
        del board[(c, r)]


def placements(board: dict, size: int, player: int) -> list:
    """Every legal placement point for `player`, in (c, r) order."""
    return [(c, r) for r in range(size) for c in range(size)
            if (c, r) not in board and not forms_glyph(board, size, c, r, player)]


def has_placement(board: dict, size: int, player: int) -> bool:
    """Does `player` have ANY legal placement?  (short-circuiting `placements`)"""
    for r in range(size):
        for c in range(size):
            if (c, r) not in board and not forms_glyph(board, size, c, r, player):
                return True
    return False


def connects(board: dict, player: int, size: int) -> bool:
    """Does `player` join their two edges via an ORTHOGONAL chain of stones?"""
    if player == BLACK:                       # row 0 <-> row size-1
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == BLACK]
        at_goal = lambda cell: cell[1] == size - 1   # noqa: E731
    else:                                     # col 0 <-> col size-1
        starts = [(0, r) for r in range(size) if board.get((0, r)) == WHITE]
        at_goal = lambda cell: cell[0] == size - 1   # noqa: E731
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


class Minefield(Game):
    name = "Minefield"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> MinefieldState:
        size = int((options or {}).get("size", 11))
        return MinefieldState(size=size)

    def current_player(self, s: MinefieldState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def legal_moves(self, s: MinefieldState) -> list:
        if self.is_terminal(s):
            return []
        moves = [f"{c},{r}" for (c, r) in placements(s.board, s.size, s.to_move)]
        if s.ply == 1 and len(s.board) == 1:
            moves.append("swap")     # pie rule: White's first turn only
        return moves

    # -- move application ---------------------------------------------------

    def _advance(self, s: MinefieldState, mover: int) -> None:
        """Hand the turn on after `mover` acted, applying the skip rule.

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

    def apply_move(self, s: MinefieldState, move: str, rng=None) -> MinefieldState:
        if move == "swap":
            # Pie rule: White "switches colours and becomes Black, claiming the
            # first placement as his own".  Seats are fixed here, so the
            # value-preserving equivalent is to transpose the position and swap
            # the colours: Minefield is symmetric under reflection in the main
            # diagonal combined with colour reversal (the glyph set is closed
            # under reflections AND colour reversals, and the transpose
            # exchanges the black row-goal with the white column-goal).  Black's
            # lone stone at (c, r) therefore becomes a WHITE stone at (r, c) and
            # Black (seat 0) is on move again — exactly the position the
            # swapper obtains.  Recolouring in place would NOT preserve the
            # value, since the two colours aim at different edges.
            ((c, r), _owner), = s.board.items()
            out = MinefieldState(size=s.size, board={(r, c): WHITE},
                                 to_move=BLACK, last=(r, c), ply=s.ply + 1)
            self._advance(out, WHITE)      # White has just acted
            return out

        me = s.to_move
        p = _cell(move)
        board = dict(s.board)
        board[p] = me
        out = MinefieldState(size=s.size, board=board, to_move=1 - me, last=p,
                             ply=s.ply + 1, skips=s.skips)
        if connects(board, me, s.size):
            out.winner = me
            return out
        self._advance(out, me)
        return out

    # -- termination / scoring ----------------------------------------------

    def is_terminal(self, s: MinefieldState) -> bool:
        return s.winner is not None or s.stalled

    def returns(self, s: MinefieldState) -> list:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]    # both players stuck with nobody connected: a draw

    # -- serialization ------------------------------------------------------

    def serialize(self, s: MinefieldState) -> dict:
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

    def deserialize(self, d: dict) -> MinefieldState:
        return MinefieldState(
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

    def describe_move(self, s: MinefieldState, move: str) -> str:
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

    def heuristic(self, s: MinefieldState) -> list:
        """MCTS payoffs [black, white] from the connection distance: how many
        further stones each side needs to join their edges (0-1 BFS; own stone
        costs 0, empty 1, enemy stone blocks).  Ignores the glyph rules, so it
        is only a rough guide."""
        db = self._edge_distance(s, BLACK)
        dw = self._edge_distance(s, WHITE)
        val = math.tanh(0.35 * (dw - db))       # positive = Black ahead
        return [val, -val]

    def _edge_distance(self, s: MinefieldState, player: int) -> float:
        from collections import deque
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

    def render(self, s: MinefieldState, perspective=None) -> dict:
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
            if s.ply == 1 and len(s.board) == 1:
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
