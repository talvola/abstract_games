"""Blast Radius -- Mark Steere (November 2024).

Implemented from the author's rule sheet
(marksteeregames.com/Blast_Radius_rules.pdf).  The sheet was **silently revised**
between 2024-12-02 and 2025-05-28: the OBJECT paragraph gained the parenthetical
"(except at the conclusion of Red's first turn)".  This package implements the
current (2025) text; see ``rules.md``.

Board model
-----------
A hexagonal board (hexhex) of side ``size``: axial cells ``(q, r)`` with
``|q|, |r|, |q + r| <= size - 1`` (so ``size`` 6 = 91 cells, the AbstractPlay
default).  Cell ids are the platform's axial ``"q,r"`` strings; hex distance is
the usual cube metric.  The board starts EMPTY.

Rules as implemented
--------------------
* A **stack** is one or more like-coloured checkers on one cell; its *height* is
  the number of checkers.  Stacks are always mono-coloured (you may only add to
  your own).
* A stack's **radiation exclusion zone (REZ)** is every cell at hex distance
  ``<= height``, *ground zero included*.  Figure 1 of the sheet marks, for a
  height-2 red stack and a height-1 blue stack, exactly the cells at distance
  ``<= 2`` and ``<= 1`` -- 16 red + 2 purple (overlap) + 4 blue dots, and the two
  stack cells themselves are covered by their discs.  ``selftest.py`` replays it.
* **Play** -- Red (seat 0) first, then alternating, one checker per turn:
  1. you may not place inside a REZ, except on a friendly stack at ground zero;
  2. you must form the smallest stack you can -- so if any cell is empty *and*
     outside every REZ you must place there; otherwise you must place on one of
     your own shortest stacks.
* **Captures** -- if the placement makes a stack of height >= 2, every *other*
  stack (friendly and enemy alike) inside the newly formed REZ is removed.  The
  new stack itself survives: Figure 4's green dot (the placement) is not one of
  the yellow dots (the removals).
* **Object** -- if the opponent has no checkers on the board at the conclusion of
  your turn you win, *except* at the conclusion of Red's first turn (when the
  board trivially holds no blue checkers).

Termination (proved, so there is no ply cap and no repetition rule)
-------------------------------------------------------------------
Write the position's stack heights as a vector sorted in *descending* order and
padded with zeros to the cell count.  Every legal move raises that vector
strictly in lexicographic order, and the vector is bounded, so no position can
repeat and the game must end.  See ``rules.md`` for the argument and
``selftest.py``, which asserts the increase on every ply of thousands of games.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

SIZES = (4, 5, 6, 7)
SEAT_NAMES = ("Red", "Blue")

# Tints painted on the cells of each side's radiation exclusion zones.  The
# purple overlap colour mirrors Figure 1, where cells inside both REZs are drawn
# with a purple dot.
REZ_TINT = ("#4a2725", "#232f4a", "#3d2747")


def cells(size):
    """Axial cells of a hexhex of side ``size``, in render order."""
    n = size - 1
    return [(q, r) for r in range(-n, n + 1)
            for q in range(max(-n, -n - r), min(n, n - r) + 1)]


def dist(a, b):
    """Hex distance between two axial cells."""
    dq = a[0] - b[0]
    dr = a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def cid(c):
    return f"{c[0]},{c[1]}"


def _cell(txt):
    q, r = txt.split(",")
    return int(q), int(r)


def on_board(c, size):
    n = size - 1
    return abs(c[0]) <= n and abs(c[1]) <= n and abs(c[0] + c[1]) <= n


def ball(centre, radius, size):
    """On-board cells at hex distance <= ``radius`` from ``centre``."""
    q0, r0 = centre
    out = []
    for dq in range(-radius, radius + 1):
        lo = max(-radius, -radius - dq)
        hi = min(radius, radius - dq)
        for dr in range(lo, hi + 1):
            c = (q0 + dq, r0 + dr)
            if on_board(c, size):
                out.append(c)
    return out


def rez_cells(board, size):
    """{cell: set(owners)} -- every cell covered by some stack's REZ.

    Ground zero counts as inside its own stack's REZ (that is why rule 1 needs
    the "except on a friendly stack at ground zero" carve-out at all).
    """
    out = {}
    for c, (owner, height) in board.items():
        for d in ball(c, height, size):
            out.setdefault(d, set()).add(owner)
    return out


def free_cells(board, size):
    """Empty cells outside every REZ -- the placements rule 2 forces on you."""
    rez = rez_cells(board, size)
    return [c for c in cells(size) if c not in board and c not in rez]


def blast(board, cell, size):
    """Cells removed by forming a stack of height >= 2 on ``cell``.

    ``board`` is the position **after** the checker has been added.  The newly
    formed stack sits at ground zero of its own REZ and is never removed.
    """
    owner, height = board[cell]
    if height < 2:
        return []
    return [c for c in board if c != cell and dist(c, cell) <= height]


@dataclass
class BRState:
    size: int = 6
    board: dict = field(default_factory=dict)   # {(q,r): (owner, height)}
    to_move: int = 0
    ply: int = 0                                # completed plies
    last: tuple = None                          # the placement just made
    removed: tuple = ()                         # stacks blown up by it


class BlastRadius(Game):
    name = "Blast Radius"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        n = int((options or {}).get("size", 6))
        if n not in SIZES:
            raise ValueError(f"unsupported board size {n}; choose from {SIZES}")
        return BRState(size=n)

    def current_player(self, s):
        return s.to_move

    # ---- terminal / result -------------------------------------------------

    def _counts(self, s):
        """(stacks, checkers) per seat."""
        st = [0, 0]
        ch = [0, 0]
        for owner, height in s.board.values():
            st[owner] += 1
            ch[owner] += height
        return st, ch

    def is_terminal(self, s):
        # "at the conclusion of your turn ... except at the conclusion of Red's
        # first turn" -- so the check is live from ply 2 onwards.  A state only
        # ever exists at the conclusion of a turn, so no extra bookkeeping is
        # needed to tell whose turn just ended.
        if s.ply < 2:
            return False
        st, _ = self._counts(s)
        return st[0] == 0 or st[1] == 0

    def returns(self, s):
        st, _ = self._counts(s)
        if st[0] == 0 and st[1] == 0:
            # An honest draw.  Proved unreachable: the mover's own new stack is
            # never blown up, so a turn always ends with the mover on the board
            # (selftest asserts it over every ply of every random game).
            return [0.0, 0.0]
        if st[1] == 0:
            return [1.0, -1.0]
        if st[0] == 0:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- moves -------------------------------------------------------------

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        free = free_cells(s.board, s.size)
        if free:
            return [cid(c) for c in free]
        mine = [(c, h) for c, (o, h) in s.board.items() if o == s.to_move]
        if not mine:
            # Unreachable: a seat with no stacks has already lost (or it is
            # Red's opening / Blue's reply, both of which have free cells on
            # every supported board size).  See rules.md for the proof.
            return []
        low = min(h for _, h in mine)
        return [cid(c) for c in cells(s.size)
                if c in s.board and s.board[c] == (s.to_move, low)]

    def apply_move(self, s, move, rng=None):
        c = _cell(move)
        board = dict(s.board)
        prev = board.get(c)
        if prev is not None and prev[0] != s.to_move:
            # Stacks are mono-coloured: you may only ever add to your own.
            raise ValueError(f"{move} holds an enemy stack")
        board[c] = (s.to_move, (0 if prev is None else prev[1]) + 1)
        removed = blast(board, c, s.size)
        for d in removed:
            del board[d]
        return BRState(size=s.size, board=board, to_move=1 - s.to_move,
                       ply=s.ply + 1, last=c, removed=tuple(removed))

    # ---- bot eval ----------------------------------------------------------

    def heuristic(self, s):
        """A LIST of per-seat payoffs (MCTS convention), not a bare float.

        **The sign is counter-intuitive and was MEASURED, not guessed.** Owning
        FEWER stacks than your opponent is good: every checker you put down is
        one more target for the next detonation, and rule 2 forces you to keep
        putting them down.  Two independent measurements agree, on two board
        sizes (see rules.md):

        * the stack-count difference correlates **negatively** (-0.22 / -0.33 on
          sides 4 / 5) with the sampled win probability of seat 0;
        * greedy play on this eval scores 0.58 (800 games, side 4) / 0.61 (the
          250-game paired match in ``selftest.py``) against a random player,
          while the opposite sign scores 0.42 / 0.34 and a constant scores 0.50.

        A total-material term was measured too and is inconsistent (+0.24 / +0.04),
        so it is deliberately left out.  ``selftest.py`` pins both the values and
        the direction.
        """
        if self.is_terminal(s):
            return self.returns(s)
        st, _ = self._counts(s)
        v = math.tanh(0.2 * (st[1] - st[0]))
        return [v, -v]

    # ---- persistence -------------------------------------------------------

    def serialize(self, s):
        return {
            "size": s.size,
            "board": {cid(c): [o, h] for c, (o, h) in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "last": None if s.last is None else cid(s.last),
            "removed": [cid(c) for c in s.removed],
        }

    def deserialize(self, d):
        return BRState(
            size=d["size"],
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            last=None if d.get("last") is None else _cell(d["last"]),
            removed=tuple(_cell(k) for k in d.get("removed", ())),
        )

    # ---- presentation ------------------------------------------------------

    def describe_move(self, s, move):
        c = _cell(move)
        if c not in s.board:
            return move
        _, height = s.board[c]
        board = dict(s.board)
        board[c] = (s.to_move, height + 1)
        n = len(blast(board, c, s.size))
        tag = f"{move} ({height}→{height + 1})"
        return tag + (f" ×{n}" if n else "")

    def render(self, s, perspective=None):
        rez = rez_cells(s.board, s.size)
        tints = {}
        for c, owners in rez.items():
            tints[cid(c)] = REZ_TINT[2] if len(owners) > 1 else REZ_TINT[min(owners)]
        # `stack` is the platform's tower primitive (Lasca/Accasta/Attangle): a
        # side-view of the checkers with a height badge, drawn in the seat colour
        # from colors.js.  A bare `label` would render as TEXT ONLY with no disc
        # at all, and hard-coding a `fill` to get a disc back would duplicate the
        # seat palette inside the engine.
        pieces = [{"cell": cid(c), "owner": o, "stack": [o] * h}
                  for c, (o, h) in s.board.items()]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": cid(s.last), "kind": "last-move"})
        for c in s.removed:
            highlights.append({"cell": cid(c), "kind": "last-move"})
        st, ch = self._counts(s)
        info = (f"stacks {st[0]}-{st[1]}, checkers {ch[0]}-{ch[1]}")
        if self.is_terminal(s):
            r = self.returns(s)
            cap = ("Draw" if r[0] == r[1] else
                   f"{SEAT_NAMES[0 if r[0] > r[1] else 1]} wins") + f" · {info}"
        else:
            cap = f"{SEAT_NAMES[s.to_move]} to move · {info}"
            if not free_cells(s.board, s.size):
                cap += " · board saturated: must build a stack"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
