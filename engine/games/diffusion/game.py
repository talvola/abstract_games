"""Diffusion (Mark Steere, January 2006) -- a *diffusion* Mancala.

Board model: a SQUARE board 8 wide x 2 tall.

    col:   0     1  2  3  4  5  6     7
    row 1  [L]   a2 b2 c2 d2 e2 f2   [R]      <- Player B sits here
    row 0  [L]   a1 b1 c1 d1 e1 f1   [R]      <- Player A sits here

Columns 1..6 are the twelve **pits**; columns 0 and 7 are the two ends of the
board, i.e. the left and right **stores**.  The rule sheet says "treat a store
as two pits when distributing stones", and on a two-row board an end column is
*literally* two cells -- so the store columns need no special geometry at all:
the distribution ring is just the eight king-neighbours of a cell in this 2x8
grid, of which a pit always has exactly five.

A move scoops all stones out of one non-empty pit and drops them one by one
into the first ``n`` slots of that pit's ring, walking **counterclockwise from
the most clockwise slot** (Figures 3 and 4).  For a bottom-row pit that arc is
E, NE, N, NW, W; for a top-row pit it is the 180-degree rotation, W, SW, S, SE,
E.  Since a pit holds at most 5 stones and always has exactly 5 ring slots,
distribution never wraps and the source pit never receives a stone.

A stone that lands in a store slot leaves the board.  So does the 6th stone of
any pit (overflow).  Stones never come back, which is what makes the game
finite -- see ``rules.md`` for the full termination proof (the potential
``POT``/``POT_C`` below is its certificate).

A player owns one block of pits and wins the moment **his own** block is
completely vacant -- whoever emptied it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from agp.game import Game

WIDTH, HEIGHT = 8, 2
MAXPIT = 5                     # a pit holds at most 5 stones
TOTAL_STONES = 48

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
# The twelve pits, ordered bottom row left->right then top row left->right.
PITS = tuple((c, r) for r in (0, 1) for c in range(1, 7))
IDX = {p: i for i, p in enumerate(PITS)}          # i = r*6 + (c-1)
STORE_CELLS = ((0, 0), (0, 1), (7, 0), (7, 1))

# Distribution ring: the existing king-neighbours of a 2-row cell, listed
# counterclockwise starting at the most clockwise one.
#   bottom row (r=0):  E  NE  N  NW  W
#   top row    (r=1):  W  SW  S  SE  E     (the 180-degree rotation of the above)
RING_DIRS = {
    0: ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)),
    1: ((-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0)),
}
RINGS = {p: tuple((p[0] + dc, p[1] + dr) for dc, dr in RING_DIRS[p[1]])
         for p in PITS}

# Human-readable pit names: files a-f (columns 1-6), ranks 1 (bottom) / 2 (top).
PIT_NAME = {(c, r): "abcdef"[c - 1] + str(r + 1) for (c, r) in PITS}
NAME_PIT = {v: k for k, v in PIT_NAME.items()}

# ---------------------------------------------------------------------------
# Blocks (who owns what)
# ---------------------------------------------------------------------------
# v1  (rule sheet, Fig. 2): two 2x3 blocks.  Player A = left, Player B = right.
# v2  (Diffusion v2, Fig. 7): two 1x6 blocks.  Player A = bottom, B = top.
BLOCKS = {
    "v1": (tuple(p for p in PITS if p[0] <= 3),
           tuple(p for p in PITS if p[0] >= 4)),
    "v2": (tuple(p for p in PITS if p[1] == 0),
           tuple(p for p in PITS if p[1] == 1)),
}
BLOCK_NAME = {
    "v1": ("left 2x3 block", "right 2x3 block"),
    "v2": ("lower 1x6 block", "upper 1x6 block"),
}
SIDE = {0: "Player A", 1: "Player B"}

# ---------------------------------------------------------------------------
# Termination certificate (see rules.md)
# ---------------------------------------------------------------------------
# POT is a per-pit weight with the property that every stone-CONSERVING move
# strictly decreases Phi = sum(stones_in_pit * POT[pit]) by at least 1.  A move
# that is not conserving strictly decreases S = the on-board stone count, and
# can raise Phi by at most 96.  Hence Psi = 97*S + Phi drops by >= 1 on EVERY
# move, and Psi(opening) = 97*48 + 4*sum(POT) = 5944 >= Psi >= 0.
POT = {}
for _c, _v in zip(range(1, 7), (35, 34, 33, 32, 27, 0)):
    POT[(_c, 0)] = _v
for _c, _v in zip(range(1, 7), (0, 27, 32, 33, 34, 35)):
    POT[(_c, 1)] = _v
POT_C = 97                                        # 1 + max possible rise in Phi
PLY_CAP = POT_C * TOTAL_STONES + 4 * sum(POT.values())   # == 5944

# The seat-swapping symmetry of the board: rotate 180 degrees.  It maps block A
# onto block B in BOTH variants.
def sigma(cell):
    c, r = cell
    return (7 - c, 1 - r)


def _cell(text: str):
    c, r = text.split(",")
    return int(c), int(r)


def _key(cell) -> str:
    return "%d,%d" % cell


@dataclass(frozen=True)
class DiffusionState:
    pits: tuple = ()                 # 12 counts, index = row*6 + (col-1)
    stores: tuple = (0, 0)           # (left, right) -- immaterial to play
    to_move: int = 0
    ply: int = 0
    variant: str = "v1"
    last: Optional[str] = None       # last scooped pit, for the board highlight


class Diffusion(Game):
    name = "Diffusion"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> DiffusionState:
        variant = str((options or {}).get("variant", "v1"))
        if variant not in BLOCKS:
            raise ValueError("unknown variant %r (expected v1 or v2)" % variant)
        return DiffusionState(pits=(4,) * 12, stores=(0, 0), to_move=0,
                              ply=0, variant=variant, last=None)

    def current_player(self, s: DiffusionState) -> int:
        return s.to_move

    # -- blocks -------------------------------------------------------------
    def block_counts(self, s: DiffusionState):
        """(stones in block A, stones in block B)."""
        a, b = BLOCKS[s.variant]
        return (sum(s.pits[IDX[p]] for p in a),
                sum(s.pits[IDX[p]] for p in b))

    def _vacant(self, s: DiffusionState):
        ca, cb = self.block_counts(s)
        return ca == 0, cb == 0

    # -- moves --------------------------------------------------------------
    def legal_moves(self, s: DiffusionState) -> list:
        if self.is_terminal(s):
            return []
        return [_key(p) for p in PITS if s.pits[IDX[p]] > 0]

    def _sow(self, s: DiffusionState, src):
        """Distribute src's stones.  Returns (pits, stores, n_scooped)."""
        pits = list(s.pits)
        stores = [s.stores[0], s.stores[1]]
        n = pits[IDX[src]]
        pits[IDX[src]] = 0
        # Stones leave the board in two ways: they land in one of a store's two
        # slots, or they are the 6th stone of a pit (overflow).  The rule sheet
        # explicitly lets the player pick which store to bank an overflow stone
        # in, so the split is immaterial; we bank everything into the store on
        # the SOURCE pit's own half.  For a store SLOT that is also the store it
        # physically lands in (a corner pit's store slots are on its own side),
        # and it reproduces the store counts in Figures 4 and 5 of the 2006/2008
        # revision of the rule sheet.
        bank = 0 if src[0] <= 3 else 1
        for (tc, tr) in RINGS[src][:n]:
            if tc == 0 or tc == WIDTH - 1:              # a store slot
                stores[bank] += 1
            elif pits[IDX[(tc, tr)]] >= MAXPIT:         # overflow
                stores[bank] += 1
            else:
                pits[IDX[(tc, tr)]] += 1
        return tuple(pits), (stores[0], stores[1]), n

    def apply_move(self, s: DiffusionState, move, rng=None) -> DiffusionState:
        if self.is_terminal(s):
            raise ValueError("game is over")
        src = _cell(move)
        if src not in IDX or s.pits[IDX[src]] <= 0:
            raise ValueError("illegal move %r" % (move,))
        pits, stores, _ = self._sow(s, src)
        return DiffusionState(pits=pits, stores=stores, to_move=1 - s.to_move,
                              ply=s.ply + 1, variant=s.variant, last=_key(src))

    # -- terminal -----------------------------------------------------------
    def is_terminal(self, s: DiffusionState) -> bool:
        va, vb = self._vacant(s)
        # A vacant block is checked FIRST so a decisive result can never be
        # absorbed by the (provably unreachable) ply-cap backstop.
        return va or vb or s.ply >= PLY_CAP

    def returns(self, s: DiffusionState) -> list:
        va, vb = self._vacant(s)
        if va and vb:
            # Provably unreachable (see rules.md): both blocks vacant means the
            # whole board is empty, which requires every stone to have been in
            # the single scooped pit -- so one block was already vacant before
            # the move.  Scored as an honest draw rather than a fake tiebreak.
            return [0.0, 0.0]
        if va:
            return [1.0, -1.0]
        if vb:
            return [-1.0, 1.0]
        return [0.0, 0.0]                     # ply cap: provably unreachable

    # -- persistence --------------------------------------------------------
    def serialize(self, s: DiffusionState) -> dict:
        return {
            "pits": list(s.pits),
            "stores": list(s.stores),
            "to_move": s.to_move,
            "ply": s.ply,
            "variant": s.variant,
            "last": s.last,
        }

    def deserialize(self, d: dict) -> DiffusionState:
        # Every key is read POSITIONALLY (no .get defaults) so a field dropped
        # from serialize() fails loudly instead of silently re-defaulting.
        return DiffusionState(
            pits=tuple(d["pits"]),
            stores=tuple(d["stores"]),
            to_move=d["to_move"],
            ply=d["ply"],
            variant=d["variant"],
            last=d["last"],
        )

    # -- presentation -------------------------------------------------------
    def render(self, s: DiffusionState, perspective=None) -> dict:
        blocks = BLOCKS[s.variant]
        owner = {}
        for seat, cells in enumerate(blocks):
            for p in cells:
                owner[p] = seat

        pieces = [{"cell": _key(p), "owner": owner[p],
                   "label": str(s.pits[IDX[p]])} for p in PITS]
        # Each store spans its column's two cells (that is why it counts as two
        # pits when distributing); its running total is printed on the lower of
        # the two, in the neutral colour (seat 2 = "owned by neither side").
        pieces.append({"cell": "0,0", "owner": 2, "label": str(s.stores[0])})
        pieces.append({"cell": "7,0", "owner": 2, "label": str(s.stores[1])})

        tints = {}
        for p in blocks[0]:
            tints[_key(p)] = "#d23b3b33"
        for p in blocks[1]:
            tints[_key(p)] = "#3b6fd233"
        for cell in STORE_CELLS:
            tints[_key(cell)] = "#9a917c26"

        ca, cb = self.block_counts(s)
        off = s.stores[0] + s.stores[1]
        if self.is_terminal(s):
            va, vb = self._vacant(s)
            if va and vb:
                head = "Draw"
            elif va:
                head = "Player A wins - the %s is vacant" % BLOCK_NAME[s.variant][0]
            elif vb:
                head = "Player B wins - the %s is vacant" % BLOCK_NAME[s.variant][1]
            else:
                head = "Draw (ply cap)"
        else:
            head = "%s to move - empty the %s to win" % (
                SIDE[s.to_move], BLOCK_NAME[s.variant][s.to_move])
        caption = "%s  ·  A %d - B %d on board  ·  %d in the stores" % (
            head, ca, cb, off)

        return {
            "board": {"type": "square", "width": WIDTH, "height": HEIGHT,
                      "tints": tints},
            "pieces": pieces,
            "highlights": ([{"cell": s.last, "kind": "last-move"}]
                           if s.last else []),
            "caption": caption,
        }

    def describe_move(self, s: DiffusionState, move) -> str:
        src = _cell(move)
        n = s.pits[IDX[src]]
        _, stores, _ = self._sow(s, src)
        off = (stores[0] - s.stores[0]) + (stores[1] - s.stores[1])
        txt = "%s sows %d" % (PIT_NAME[src], n)
        if off:
            txt += " (%d to store)" % off
        return txt

    # -- bot eval -----------------------------------------------------------
    def heuristic(self, s: DiffusionState) -> list:
        """One payoff per seat: you want YOUR OWN block empty."""
        ca, cb = self.block_counts(s)
        v = math.tanh((cb - ca) / 6.0)
        return [v, -v]
