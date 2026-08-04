"""Nakatta Pro — a square-board connection game by Mark Steere (April 2026).

Played on the points (intersections) of an initially empty NxN square grid,
rendered here as an NxN grid of cells.  The TOP and BOTTOM board edges are
black, the LEFT and RIGHT edges are white.  Black (player 0) wins by forming a
chain of ORTHOGONALLY (horizontally or vertically) interconnected black stones
joining the two black edges; White (player 1) joins the two white edges.

Black plays first, then turns alternate; on your turn you place one stone of
your colour on an unoccupied point.  Passing is not allowed, but a player with
no available placement has their turn skipped.  Nothing is ever moved, removed
or captured.  The whole game is the ban on three PROHIBITED GLYPHS.

    "Players are not allowed to form any of the glyphs (patterns) in Figure 2
     (or their reflections, rotations, or color reversals)."

Figure 2 prints exactly three glyphs.  Their cell coordinates are decoded below
from the sheet's VECTOR artwork (see selftest.py, which re-derives them), not
from a reading of the prose — the sheet gives no prose definition at all.  `.`
is a point the glyph requires to be UNOCCUPIED (a blue dot in the figure):

    HARD CORNER (2x2)       BARE ATTACHMENT (2x3)     BROKEN SWITCH (2x3)

        W .                       . .                       . B
        B W                       . .                       . .
                                  B W                       B W

Only the first has a name in Steere's own sheets (Nakatta and Minefield both
call the identical 2x2 pattern a "hard corner"); the two 2x3 names are this
package's, chosen to describe what they are:

  * BARE ATTACHMENT — an "attachment" (two orthogonally adjacent stones of
    opposite colour) with BOTH of the two rows beside it clear.  Nakatta bans
    an attachment with ONE clear row beside it (its "naked attachment"); this
    is the same idea one row weaker.

  * BROKEN SWITCH — Minefield's 2x3 "switch" with one of its four corner
    stones removed: two stones of one colour on diagonally opposite corners of
    the 2x3, one enemy stone on a third corner, the fourth corner and both
    non-corner points unoccupied.

That is precisely why the game is, in the designer's words, "the long
undiscovered Middle-earth between Nakatta and Minefield" — and it is a fact
about the glyph sets, not a slogan; selftest.py proves both halves:

    NAKATTA-legal  (subset of)  NAKATTA PRO-legal  (subset of)  MINEFIELD-legal

  * every Nakatta Pro glyph CONTAINS a Nakatta glyph (both 2x3 glyphs contain a
    2x2 naked attachment), so Nakatta Pro forbids strictly less than Nakatta;
  * no Nakatta Pro-legal position can contain a Minefield switch (the 2x4 long
    switch IS a bare attachment; removing any one corner stone from the 2x3
    short switch leaves a broken switch, so its last stone can never be
    legally played), so Nakatta Pro forbids strictly more than Minefield.

Source: the official rule sheet, marksteeregames.com/Nakatta_Pro_rules.pdf
(Adobe Illustrator PDF; the prose extracts with pdftotext but the FIGURES
carry no text, and the figures are the rule.  CreationDate 2026-04-22,
ModDate 2026-06-14, md5 21c52dd947eb4f620c24d93fc6565b95).  The sheet has been
revised once since publication; the revision fixes the typo "contibution" ->
"contribution" in the design notes and changes NOTHING else — all three figures
are bit-for-bit identical in the two revisions (checked by parsing both PDFs'
vector artwork, and by a pixel diff whose only difference is that one word).

THE SHEET'S FIGURE 3 IS WRONG, AND THIS PACKAGE FOLLOWS FIGURE 2.
Figure 3 prints a 9x9 position with "all of the illegal placements for Black"
marked by red dots.  Every one of its seven red dots really does form a glyph
of Figure 2, and both of its green dots (points it calls out as legal) really
are legal — but SEVENTEEN further unoccupied points also form a glyph, so its
claim that "all of the other unoccupied points are legal placements for Black"
is false.  This is not a reading error on our side: the identical pipeline
(same PDF parser, same matcher, same D4-and-colour closure) reproduces the
sibling MINEFIELD sheet's Figure 3 EXACTLY, 13 red dots out of 13 with both
greens legal.  And no rule of the sheet's own format can produce Figure 3: an
exhaustive search over every prohibited-pattern set drawable as areas up to
3x3 / 2x4 — and, separately, over every SUBSET of Figure 2's own 32-element
glyph orbit — shows two of the seven red dots cannot be made illegal without
also making one of the figure's "legal" points illegal.  Figure 3 is therefore
stale or hand-edited artwork, and Figure 2 is the rule.  selftest.py pins all
of this: the seven red dots, the two green dots, and the seventeen extra points
Figure 3 omits.

IMPLEMENTATION NOTES

* "Form a glyph" is judged on the position AFTER the placement, and it is
  implemented as a LOCAL test on the (at most 4 + 12) 2x2 / 2x3 / 3x2 areas
  containing the placed point.  The two are equivalent because every glyph
  contains at least one point required to be UNOCCUPIED: the empty board holds
  no glyph, adding a stone can only destroy glyphs elsewhere, and an area not
  containing the placed point is unchanged.  So no legal position ever contains
  a glyph and every glyph a move could create contains the stone just played.
  `glyphs_on_board` performs the full global scan and selftest.py asserts the
  two agree on the sheet's figures and on every empty point of every position
  of whole random games.

* NO PIE RULE.  Nakatta's sheet has one and Minefield's 2026 revision added
  one; the Nakatta Pro sheet — in BOTH its revisions — has none, so none is
  shipped.  See rules.md.

* Skips are applied inside apply_move (the platform requires a non-empty
  legal_moves on every non-terminal state), so every ply of the game is a
  placement; a skipped turn is never a ply of its own.

TERMINATION.  Stones are never removed and there is no pie swap, so every ply
places a stone on a previously empty point: a game lasts at most
`max_plies(size) = size * size` plies.  No ply cap and no repetition rule are
needed or shipped.  Cycles are impossible by construction.

DRAWS.  A crosscut can never appear (removing any stone from one leaves a hard
corner), so a FILLED board always has exactly one winner.  The one loose end is
the early stall: if NEITHER player has a legal placement while empty points
remain, that is an honest draw (`winner=None`, returns [0, 0]) and never a
fabricated tiebreak.  A decisive connection outranks the stall test, because
apply_move returns as soon as the mover connects.

BOT.  A `heuristic` IS shipped (connection distance), and it was MEASURED
through MCTSBot -- the consumer that uses it -- before being shipped, not after.
A Nakatta Pro game runs to roughly 0.85 * size**2 plies, so from the smallest
offered board upwards MCTSBot's 50-ply rollout cutoff always bites and a bot
without an eval scores every rollout as a draw, i.e. has no signal at all.
Head to head at 7x7 with the cutoff forced (`max_rollout=6`), seats alternated,
identical budgets, the only difference being whether the game object exposes
`heuristic`: **40-0**, and **39-1** on an independent replay with different
seeds.  rules.md carries the numbers.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black joins top<->bottom (rows), White joins left<->right (cols)
EMPTY = None

_ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))


# --------------------------------------------------------------------------
# the prohibited glyphs of Figure 2, and their closure
# --------------------------------------------------------------------------
#
# A pattern is a dict {(dc, dr): BLACK / WHITE / EMPTY}.  The three base
# patterns are transcribed from the sheet's vector artwork; selftest.py
# re-derives the same cell coordinates from the PDF-parsed figure and asserts
# the blue dots are exactly the EMPTY points.

HARD_CORNER = {(0, 0): WHITE, (1, 0): EMPTY,
               (0, 1): BLACK, (1, 1): WHITE}

BARE_ATTACHMENT = {(0, 0): EMPTY, (1, 0): EMPTY,
                   (0, 1): EMPTY, (1, 1): EMPTY,
                   (0, 2): BLACK, (1, 2): WHITE}

BROKEN_SWITCH = {(0, 0): EMPTY, (1, 0): BLACK,
                 (0, 1): EMPTY, (1, 1): EMPTY,
                 (0, 2): BLACK, (1, 2): WHITE}

BASE_GLYPHS = (("hard corner", HARD_CORNER),
               ("bare attachment", BARE_ATTACHMENT),
               ("broken switch", BROKEN_SWITCH))


def _colour_reverse(pat: dict) -> dict:
    return {k: (EMPTY if v is EMPTY else 1 - v) for k, v in pat.items()}


def _rotate(pat: dict) -> dict:
    """Rotate a quarter turn: (c, r) -> (-r, c)."""
    return {(-r, c): v for (c, r), v in pat.items()}


def _reflect(pat: dict) -> dict:
    """Reflect in the horizontal axis: (c, r) -> (c, -r)."""
    return {(c, -r): v for (c, r), v in pat.items()}


def _normalise(pat: dict) -> dict:
    c0 = min(c for c, _ in pat)
    r0 = min(r for _, r in pat)
    return {(c - c0, r - r0): v for (c, r), v in pat.items()}


def _closure(base: dict) -> list:
    """Every reflection, rotation and colour reversal of `base` (deduplicated).

    The sheet allows all three transformations, so the group is the full
    dihedral group of the square times the colour swap.
    """
    out = {}
    cur = dict(base)
    for _ in range(4):
        for img in (cur, _reflect(cur)):
            for pat in (img, _colour_reverse(img)):
                n = _normalise(pat)
                out[frozenset(n.items())] = n
        cur = _rotate(cur)
    return list(out.values())


def _build_glyph_table():
    """{(width, height): {row-major tuple of cell values: glyph name}}."""
    table = {}
    for name, base in BASE_GLYPHS:
        for pat in _closure(base):
            w = max(c for c, _ in pat) + 1
            h = max(r for _, r in pat) + 1
            key = tuple(pat[(c, r)] for r in range(h) for c in range(w))
            table.setdefault((w, h), {})[key] = name
    return table


GLYPHS = _build_glyph_table()
GLYPH_SHAPES = tuple(sorted(GLYPHS))          # ((2, 2), (2, 3), (3, 2))

# The hard corner is symmetric enough that its orbit has 8 members; the bare
# attachment 8; the broken switch 16.  Pinned so a change to _closure is loud.
assert sum(len(v) for v in GLYPHS.values()) == 32, "glyph orbit size changed"
assert GLYPH_SHAPES == ((2, 2), (2, 3), (3, 2)), GLYPH_SHAPES

# Every glyph must contain at least one EMPTY point — this is what makes the
# local legality test equivalent to the sheet's global "no glyph on the board".
assert all(EMPTY in key for shape in GLYPHS for key in GLYPHS[shape])


def max_plies(size: int) -> int:
    """Provable upper bound on the number of plies in a game of this size.

    Derived from named factors, not pinned: EVERY ply is a placement on a
    previously empty point (stones are never removed, there is no pie swap and
    a skipped turn is not a ply of its own), and there are `size * size`
    points.
    """
    return size * size


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class NakattaProState:
    size: int = 13
    board: dict = field(default_factory=dict)   # (c, r) -> BLACK / WHITE
    to_move: int = BLACK
    last: Optional[tuple] = None                # stone placed by the previous mover
    winner: Optional[int] = None
    stalled: bool = False                       # neither player can place
    ply: int = 0
    skips: int = 0                              # turns skipped so far (no placement)


# --------------------------------------------------------------------------
# glyph detection
# --------------------------------------------------------------------------

def _glyph_at(board: dict, c0: int, r0: int, w: int, h: int):
    """The name of the glyph filling the w x h area anchored at (c0, r0), or None."""
    key = tuple(board.get((c0 + c, r0 + r), EMPTY) for r in range(h) for c in range(w))
    return GLYPHS[(w, h)].get(key)


def glyphs_on_board(board: dict, size: int) -> list:
    """Every prohibited glyph present anywhere on the board (global scan).

    Returns (name, c0, r0, width, height) tuples.  In real play this is always
    empty — no legal move ever creates a glyph and adding stones can only
    destroy them — so it exists for the figure checks and for the equivalence
    assertion in selftest.py rather than for the legality path.
    """
    out = []
    for (w, h) in GLYPH_SHAPES:
        for c0 in range(size - w + 1):
            for r0 in range(size - h + 1):
                name = _glyph_at(board, c0, r0, w, h)
                if name is not None:
                    out.append((name, c0, r0, w, h))
    return out


def forms_glyph(board: dict, size: int, c: int, r: int, player: int) -> bool:
    """Would placing `player`'s stone on the unoccupied point (c, r) form a glyph?

    Only areas CONTAINING (c, r) can gain one (see the module docstring), so
    only those are examined: 4 areas of 2x2, 6 of 2x3 and 6 of 3x2.
    """
    board[(c, r)] = player           # tentatively place (restored below)
    try:
        for (w, h) in GLYPH_SHAPES:
            for c0 in range(max(0, c - w + 1), min(c, size - w) + 1):
                for r0 in range(max(0, r - h + 1), min(r, size - h) + 1):
                    if _glyph_at(board, c0, r0, w, h) is not None:
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


class NakattaPro(Game):
    name = "Nakatta Pro"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> NakattaProState:
        size = int((options or {}).get("size", 13))
        return NakattaProState(size=size)

    def current_player(self, s: NakattaProState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def legal_moves(self, s: NakattaProState) -> list:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in placements(s.board, s.size, s.to_move)]

    # -- move application ---------------------------------------------------

    def _advance(self, s: NakattaProState, mover: int) -> None:
        """Hand the turn on after `mover` placed, applying the skip rule.

        "Passing is not allowed, but if you don't have an available placement,
        your turn is skipped."  A skip is not a ply of its own here: if the
        opponent cannot place we simply give the turn back to `mover`; if
        neither side can place, the game is over.
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

    def apply_move(self, s: NakattaProState, move: str, rng=None) -> NakattaProState:
        me = s.to_move
        p = _cell(move)
        board = dict(s.board)
        board[p] = me
        out = NakattaProState(size=s.size, board=board, to_move=1 - me, last=p,
                              ply=s.ply + 1, skips=s.skips)
        if connects(board, me, s.size):
            out.winner = me            # a decisive result outranks the stall test
            return out
        self._advance(out, me)
        return out

    # -- termination / scoring ----------------------------------------------

    def is_terminal(self, s: NakattaProState) -> bool:
        return s.winner is not None or s.stalled

    def returns(self, s: NakattaProState) -> list:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]    # both players stuck with nobody connected: a draw

    # -- serialization ------------------------------------------------------

    def serialize(self, s: NakattaProState) -> dict:
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

    def deserialize(self, d: dict) -> NakattaProState:
        return NakattaProState(
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

    def describe_move(self, s: NakattaProState, move: str) -> str:
        p = _cell(move)
        text = self._coord(p)
        nxt = self.apply_move(s, move)
        if nxt.winner is not None:
            text += "#"
        elif nxt.skips > s.skips:
            text += " (opponent skipped)"
        return text

    def heuristic(self, s: NakattaProState) -> list:
        """MCTS payoffs [black, white] from the connection distance.

        MUST return a LIST of `num_players` payoffs -- MCTSBot indexes it per
        player in back-propagation, and a bare float raises there.  Positive
        means Black is ahead; the two entries are always exact negatives, so
        the eval is zero-sum and a symmetric position scores 0-0.

        The value is the difference in how many FURTHER stones each side needs
        to join their edges (a 0-1 BFS: an own stone costs 0, an unoccupied
        point 1, an enemy stone blocks), squashed with tanh.  It ignores all
        three glyph bans, so it is a rough guide only -- but a rough guide is
        the whole of the bot's signal here (see the module docstring for the
        head-to-head measurement that justifies shipping it).
        """
        db = self._edge_distance(s, BLACK)
        dw = self._edge_distance(s, WHITE)
        val = math.tanh(0.35 * (dw - db))       # positive = Black ahead
        return [val, -val]

    def _edge_distance(self, s: NakattaProState, player: int) -> float:
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

    def render(self, s: NakattaProState, perspective=None) -> dict:
        # SEAT_NAMES is pinned to the sheet's Figure 1 in selftest.py: the
        # figure's caption is "Black wins" and its winning chain joins the TOP
        # and BOTTOM edges, so seat 0 (top/bottom) is Black.  The test asserts
        # that against the parsed artwork, not against this tuple.
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
