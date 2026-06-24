"""Entropy (Eric Solomon, 1977) — the Order-vs-Chaos classic.

A 7x7 board and a bag of 49 chips in seven colours (seven of each). Two roles:

  * Chaos (seat 0) draws a chip at random from the bag and places it on any empty
    cell, trying to PREVENT patterns.
  * Order (seat 1) may then slide any one chip horizontally or vertically, any
    distance through empty cells, to rest in an empty cell (no jumping), or pass —
    trying to MAKE patterns.

They alternate (Chaos places, Order moves) until the board is full (49 chips).

Scoring — Order's score S: for every horizontal and vertical line, every
contiguous run of chips of length >= 2 that reads the same forwards and backwards
("a palindrome") scores points equal to its length; overlapping/nested palindromes
all count independently. Examples (Solomon's rulebook):
    red-green-blue-green-red  -> 3 (green-blue-green) + 5 (whole) = 8
    red-red-red               -> 2 (rr) + 2 (rr) + 3 (rrr)        = 7
Length-1 (a lone chip) never scores. Order MAXIMISES S; Chaos MINIMISES it.

Randomness without a chance node: the chip Chaos must place next is DRAWN from the
bag and STORED in state (`next_tile`) the moment it becomes Chaos's turn, exactly
like EinStein stores the rolled die — so the chooser already knows the colour and
the generic UI/bot need no CHANCE handling. ``has_randomness`` is true.

Single-game adaptation: the real game is a two-round match (each player plays both
roles, scores summed, higher total wins). This package is ONE round (seat 0 Chaos,
seat 1 Order); the single-game winner is decided against a par threshold PAR: Order
wins if S > PAR, Chaos wins if S < PAR, draw if S == PAR. See rules.md.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

N = 7
COLOURS = ["A", "B", "C", "D", "E", "F", "G"]   # 7 colours, 7 of each => 49 chips
PER_COLOUR = 7

# Par threshold for the single-game winner. Self-play / random-Chaos studies put a
# typical Order score on a 7x7 board around the low-to-mid 30s; we set PAR so that
# "Order beat a roughly-average outcome" wins. Documented in rules.md as an
# adaptation of the 2-round match (which has no per-round winner).
PAR = 30

CHAOS, ORDER = 0, 1
NAMES = {CHAOS: "Chaos", ORDER: "Order"}

# Distinct fills for the 7 chip colours (chips are NOT owned by a seat — like ZÈRTZ
# marbles we render with piece.fill, not owner).
FILL = {
    "A": "#e6194b",  # red
    "B": "#3cb44b",  # green
    "C": "#4363d8",  # blue
    "D": "#ffe119",  # yellow
    "E": "#f58231",  # orange
    "F": "#911eb4",  # purple
    "G": "#42d4f4",  # cyan
}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _full_bag():
    return {c: PER_COLOUR for c in COLOURS}


def _draw(bag: dict, rng: random.Random):
    """Draw one chip uniformly at random from the bag; return (colour, new_bag)."""
    pool = [c for c in COLOURS for _ in range(bag.get(c, 0))]
    if not pool:
        return None, dict(bag)
    colour = rng.choice(pool)
    nb = dict(bag)
    nb[colour] -= 1
    return colour, nb


def _palindrome_score(line: list) -> int:
    """Sum over every contiguous substring (length >= 2) of `line` that is a
    palindrome of its length. `line` is a list of colour codes or None (None =
    empty cell, which breaks any run since it equals nothing)."""
    total = 0
    n = len(line)
    for i in range(n):
        for j in range(i + 2, n + 1):          # substrings of length >= 2
            seg = line[i:j]
            if any(x is None for x in seg):
                continue
            if seg == seg[::-1]:
                total += len(seg)
    return total


@dataclass
class EntropyState:
    board: dict = field(default_factory=dict)   # (c,r) -> colour code
    bag: dict = field(default_factory=_full_bag)
    next_tile: object = None                    # colour Chaos must place now (its turn)
    to_move: int = CHAOS
    ply: int = 0
    winner: object = None                       # set when terminal


class Entropy(Game):
    uid = "entropy"
    name = "Entropy"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> EntropyState:
        rng = rng or random.Random()
        bag = _full_bag()
        tile, bag = _draw(bag, rng)             # draw Chaos's first chip up front
        return EntropyState(board={}, bag=bag, next_tile=tile, to_move=CHAOS)

    def current_player(self, s: EntropyState) -> int:
        return s.to_move

    # ---- scoring -------------------------------------------------------------
    def order_score(self, s: EntropyState) -> int:
        total = 0
        for r in range(N):
            total += _palindrome_score([s.board.get((c, r)) for c in range(N)])
        for c in range(N):
            total += _palindrome_score([s.board.get((c, r)) for r in range(N)])
        return total

    # ---- moves ---------------------------------------------------------------
    def is_terminal(self, s: EntropyState) -> bool:
        return s.winner is not None

    def _empty(self, s):
        return [(c, r) for c in range(N) for r in range(N) if (c, r) not in s.board]

    def _slides(self, s: EntropyState):
        """All legal Order slides 'fc,fr>tc,tr' (orthogonal, through empties)."""
        out = []
        for (c, r) in list(s.board.keys()):
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                cc, rr = c + dc, r + dr
                while 0 <= cc < N and 0 <= rr < N and (cc, rr) not in s.board:
                    out.append(f"{c},{r}>{cc},{rr}")
                    cc += dc
                    rr += dr
        return out

    def legal_moves(self, s: EntropyState) -> list[str]:
        if s.winner is not None:
            return []
        if s.to_move == CHAOS:
            # Place the drawn next_tile on any empty cell.
            return [f"{c},{r}" for (c, r) in self._empty(s)]
        # Order: slide one chip, or pass.
        return self._slides(s) + ["pass"]

    def _finish(self, board, bag, ply):
        """Board is full -> compute the single-game winner and return a terminal state."""
        st = EntropyState(board=board, bag=bag, next_tile=None, to_move=ORDER, ply=ply)
        s = self.order_score(st)
        if s > PAR:
            st.winner = ORDER
        elif s < PAR:
            st.winner = CHAOS
        else:
            st.winner = "draw"
        return st

    def apply_move(self, s: EntropyState, move: str, rng=None) -> EntropyState:
        rng = rng or random.Random()
        if s.to_move == CHAOS:
            cell = _cell(move)
            board = dict(s.board)
            board[cell] = s.next_tile           # place the stored drawn chip
            if len(board) == N * N:              # 49th chip just filled the board
                return self._finish(board, dict(s.bag), s.ply + 1)
            # Hand off to Order; no new draw yet (the next draw happens when it
            # becomes Chaos's turn again, i.e. after Order moves).
            return EntropyState(board=board, bag=dict(s.bag), next_tile=None,
                                to_move=ORDER, ply=s.ply + 1)

        # Order's turn.
        if move == "pass":
            board = dict(s.board)
        else:
            frm, to = (_cell(x) for x in move.split(">"))
            board = dict(s.board)
            board[to] = board.pop(frm)
        # Now it becomes Chaos's turn: draw the next chip and store it.
        tile, bag = _draw(dict(s.bag), rng)
        return EntropyState(board=board, bag=bag, next_tile=tile,
                            to_move=CHAOS, ply=s.ply + 1)

    def returns(self, s: EntropyState) -> list[float]:
        if s.winner is None or s.winner == "draw":
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # ---- serialize -----------------------------------------------------------
    def serialize(self, s: EntropyState) -> dict:
        return {
            "board": {f"{c},{r}": col for (c, r), col in s.board.items()},
            "bag": dict(s.bag),
            "next_tile": s.next_tile,
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> EntropyState:
        return EntropyState(
            board={_cell(k): v for k, v in d["board"].items()},
            bag=dict(d["bag"]),
            next_tile=d.get("next_tile"),
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    def describe_move(self, s: EntropyState, move: str) -> str:
        if s.to_move == CHAOS:
            c, r = _cell(move)
            return f"Chaos {s.next_tile}@{c},{r}"
        if move == "pass":
            return "Order pass"
        frm, to = move.split(">")
        return f"Order {frm}>{to}"

    # ---- render --------------------------------------------------------------
    def render(self, s: EntropyState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "label": col, "fill": FILL[col]}
                  for (c, r), col in s.board.items()]
        score = self.order_score(s)
        if s.winner is not None:
            if s.winner == "draw":
                caption = f"Board full — Order scored {score} (par {PAR}). Draw."
            else:
                caption = (f"Board full — Order scored {score} (par {PAR}). "
                           f"{NAMES[s.winner]} wins.")
        elif s.to_move == CHAOS:
            caption = (f"Chaos to place colour {s.next_tile} on an empty cell  "
                       f"(Order score {score})")
        else:
            caption = f"Order to slide a chip or pass  (Order score {score})"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
