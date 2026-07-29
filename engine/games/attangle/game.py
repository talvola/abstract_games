"""Attangle — Dieter Stein, 2006 (rules version 13 May 2008).

The third game of Stein's "stacking game trilogy" (Accasta, Matrx, Attangle).
A hexhex-4 board of 37 spaces; the CENTRE space (d4) is a "void" that must stay
empty for the whole game. Each player owns 18 pieces, all of them in hand at the
start; the board begins empty and White moves first.

A turn is EITHER
  * placing one piece from stock on any empty space (never the void), OR
  * a CAPTURE: two friendly stacks slide in from TWO DIFFERENT DIRECTIONS onto
    one enemy stack.  Pieces travel any distance in a straight line over empty
    spaces only (they may cross the void), so the two attackers are simply the
    first pieces visible from the target along two of its six rays.  The three
    piles merge, and the mover then RETURNS THE TOPMOST PIECE (always his own)
    to stock.  The stack that remains may be at most THREE high.

That height rule is the whole of the capture law: it allows exactly the three
captures the rulebook figures show — 1+1 onto 1 (leaves a 2-stack), 1+1 onto 2,
and 1+2 onto 1 (both leave a 3-stack) — and it is what the designer's rule of
thumb "only one double stack can be involved" is short for.  Triple stacks can
therefore never move and can never be captured: they are frozen for good.

WIN: build your THIRD triple stack (five, in Grand Attangle).  There is no
passing: a player with an empty stock and no capture available loses.

Implemented from the designer's official rules,
https://spielstein.com/games/attangle/rules (this version: 13 May 2008), and
https://spielstein.com/games/attangle/rules/grand-attangle (20 Sep 2009) for the
variant, and differentialled against the AbstractPlay `gameslib` reference
implementation (see _diff_ap.py).

MOVE ENCODING (axial cell ids "q,r"):
  * placement — a single cell, "q,r"       (one click on an empty space)
  * capture   — "att1>att2>target"          (click both attackers, then the
    target).  Both attacker orders are listed as legal moves so the board is
    clickable in either order; they are the same move and produce the same
    state (the merge order depends only on stack HEIGHT, not on which attacker
    was named first).

TERMINATION is a theorem here, not a backstop — see rules.md.  Every capture
that consumes a double stack creates a triple (and triples are permanent), so
at most TARGET*2-1 such captures can ever occur; every other capture creates a
double, and doubles are bounded by the board.  Random games run 33-69 plies;
the proven ceiling is 76 (base) / 110 (grand) — selftest.py re-derives both
numbers from that argument rather than hard-coding them.  So the package
declares NO ply
cap and NO draw: a termination regression would show up loudly as conformance's
"did not terminate", never as a silent cap draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import tanh

from agp.game import Game

WHITE, BLACK = 0, 1
SEAT_NAMES = ("White", "Black")

# The six axial directions of a hex lattice.
DIRS = ((1, 0), (-1, 0), (1, -1), (-1, 1), (0, 1), (0, -1))

ALPHA = "abcdefghijklm"

# Per-variant board geometry.  `SIZE` is the hexhex side length.
SIZE = {"attangle": 4, "grand": 5}
# Pieces owned per player, INCLUDING any that start on the board.
TOTAL = {"attangle": 18, "grand": 27}
# Triple stacks needed to win.
TARGET = {"attangle": 3, "grand": 5}


def _cells(size: int) -> tuple:
    n = size - 1
    return tuple((q, r) for r in range(-n, n + 1) for q in range(-n, n + 1)
                 if abs(q + r) <= n)


CELLS = {v: _cells(SIZE[v]) for v in SIZE}
CELL_SET = {v: frozenset(CELLS[v]) for v in SIZE}


def alg(cell, variant: str = "attangle") -> str:
    """Axial -> the official algebraic name (rows a..g bottom-to-top, columns
    numbered left to right within a row), i.e. the centre of the small board is
    d4 and of the big board e5."""
    n = SIZE[variant] - 1
    q, r = cell
    return f"{ALPHA[n - r]}{q - max(-n, -n - r) + 1}"


def from_alg(s: str, variant: str = "attangle"):
    n = SIZE[variant] - 1
    r = n - ALPHA.index(s[0])
    return (max(-n, -n - r) + int(s[1:]) - 1, r)


def _cid(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _cell(s: str):
    q, r = s.split(",")
    return (int(q), int(r))


# The "voids": spaces that must stay empty all game (pieces may still slide
# ACROSS them).  Standard Attangle has one, the centre; Grand Attangle has
# seven, the centre plus one 6-fold orbit (they form a pinwheel on the board
# figure).  Verified against the marked spaces in spielstein's setup diagram.
VOIDS = {
    "attangle": frozenset({(0, 0)}),
    "grand": frozenset({(0, 0), (2, -3), (3, -1), (1, 2),
                        (-2, 3), (-3, 1), (-1, -2)}),
}

# Grand Attangle's fixed opening setup (spielstein figure "Initial setup"):
# White g6/f2/b4, Black h3/d7/c2 — one 6-fold orbit, colours alternating.
GRAND_SETUP = {
    (3, -2): WHITE, (-2, -1): WHITE, (-1, 3): WHITE,
    (1, -3): BLACK, (2, 1): BLACK, (-3, 2): BLACK,
}


# A stack is a tuple of owners, BOTTOM -> TOP; the top piece controls it.
@dataclass
class AState:
    variant: str = "attangle"
    board: dict = field(default_factory=dict)      # (q,r) -> tuple[int, ...]
    stock: tuple = (18, 18)
    to_move: int = WHITE
    ply: int = 0
    last: tuple = ()                               # cell ids of the last move


class Attangle(Game):
    name = "Attangle"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup -----------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> AState:
        variant = (options or {}).get("variant", "attangle")
        if variant not in SIZE:
            variant = "attangle"
        board = {}
        stock = TOTAL[variant]
        if variant == "grand":
            board = {c: (o,) for c, o in GRAND_SETUP.items()}
            stock -= 3                     # 3 of the 27 start on the board
        return AState(variant=variant, board=board,
                      stock=(stock, stock), to_move=WHITE)

    def current_player(self, state: AState) -> int:
        return state.to_move

    # ---- rules -----------------------------------------------------------
    @staticmethod
    def _triples(state: AState, p: int) -> int:
        return sum(1 for st in state.board.values()
                   if len(st) == 3 and st[-1] == p)

    def _triple_winner(self, state: AState):
        """The player who has completed the winning number of triple stacks.
        Only ever one: a capture makes at most one triple, for the mover, and
        the game stops at once."""
        for p in (WHITE, BLACK):
            if self._triples(state, p) >= TARGET[state.variant]:
                return p
        return None

    def _attackers(self, state: AState, target, p: int) -> list:
        """The stacks controlled by `p` that can reach `target`: the first piece
        visible along each of the six rays (empty spaces, including voids, are
        transparent).  At most one per direction, so any pair automatically
        comes from two different directions."""
        cells = CELL_SET[state.variant]
        out = []
        for dq, dr in DIRS:
            c = (target[0] + dq, target[1] + dr)
            while c in cells and c not in state.board:
                c = (c[0] + dq, c[1] + dr)
            if c in cells and state.board[c][-1] == p:
                out.append(c)
        return out

    def legal_moves(self, state: AState) -> list:
        if self._triple_winner(state) is not None:
            return []
        p = state.to_move
        moves = []
        # Placement from stock: any empty non-void space.
        if state.stock[p] > 0:
            voids = VOIDS[state.variant]
            moves.extend(_cid(c) for c in CELLS[state.variant]
                         if c not in state.board and c not in voids)
        # Captures.  Iterate in cell order, not dict-insertion order, so the
        # move list depends only on the POSITION (a state that has been through
        # serialize/deserialize lists its moves identically).
        for tgt, stk in sorted(state.board.items()):
            if stk[-1] == p:
                continue
            atts = self._attackers(state, tgt, p)
            if len(atts) < 2:
                continue
            t = _cid(tgt)
            for i in range(len(atts)):
                for j in range(i + 1, len(atts)):
                    a, b = atts[i], atts[j]
                    # Max height after taking the top piece back is 3.  This one
                    # rule also forbids moving or capturing a triple stack and
                    # is what "only one double stack may be involved" means.
                    if (len(state.board[a]) + len(state.board[b])
                            + len(stk)) > 4:
                        continue
                    ca, cb = _cid(a), _cid(b)
                    # Both attacker orders: the same move, listed twice so the
                    # board is clickable whichever attacker you pick first.
                    # (Board.jsx matches a click path index-by-index, so with
                    # only one ordering listed the OTHER attacker would not even
                    # be clickable — a silent UI dead end.  The cost is that a
                    # capture carries twice the weight of a placement in the
                    # generic bot's uniform random rollouts, which raises
                    # P(capture) in a rollout by ~1.8x; the two strings apply to
                    # the identical position, so nothing else is affected.)
                    moves.append(f"{ca}>{cb}>{t}")
                    moves.append(f"{cb}>{ca}>{t}")
        return moves

    def apply_move(self, state: AState, move: str, rng=None) -> AState:
        p = state.to_move
        board = dict(state.board)
        stock = list(state.stock)
        parts = move.split(">")
        if len(parts) == 1:
            cell = _cell(parts[0])
            board[cell] = (p,)
            stock[p] -= 1
            last = (parts[0],)
        else:
            a, b, t = (_cell(x) for x in parts)
            sa, sb, st = board[a], board[b], board[t]
            # The taller attacker goes on first, so the mover's two pieces end
            # up directly on top (rulebook Fig. 2.3); then the top one — always
            # the mover's — goes back to stock.
            first, second = (sa, sb) if len(sa) > len(sb) else (sb, sa)
            merged = st + first + second
            del board[a]
            del board[b]
            board[t] = merged[:-1]
            stock[p] += 1
            # Canonical (sorted attackers) so the two orderings of one capture
            # are byte-identical moves, right down to serialize().
            last = tuple(sorted(parts[:2])) + (parts[2],)
        return AState(variant=state.variant, board=board, stock=tuple(stock),
                      to_move=1 - p, ply=state.ply + 1, last=last)

    def is_terminal(self, state: AState) -> bool:
        return not self.legal_moves(state)

    def returns(self, state: AState) -> list:
        w = self._triple_winner(state)
        if w is None:
            # The player to move has no placement and no capture: he resigns.
            w = 1 - state.to_move
        return [1.0 if i == w else -1.0 for i in (WHITE, BLACK)]

    # ---- persistence -----------------------------------------------------
    def serialize(self, state: AState) -> dict:
        return {
            "variant": state.variant,
            "board": {_cid(c): "".join(str(o) for o in st)
                      for c, st in sorted(state.board.items())},
            "stock": list(state.stock),
            "to_move": state.to_move,
            "ply": state.ply,
            "last": list(state.last),
        }

    def deserialize(self, data: dict) -> AState:
        return AState(
            variant=data.get("variant", "attangle"),
            board={_cell(k): tuple(int(ch) for ch in v)
                   for k, v in data["board"].items()},
            stock=tuple(data["stock"]),
            to_move=data["to_move"],
            ply=data.get("ply", 0),
            last=tuple(data.get("last", ())),
        )

    # ---- notation --------------------------------------------------------
    def describe_move(self, state: AState, move: str) -> str:
        v = state.variant
        parts = move.split(">")
        if len(parts) == 1:
            txt = alg(_cell(parts[0]), v)
        else:
            a, b, t = (alg(_cell(x), v) for x in parts)
            lo, hi = sorted((a, b), key=lambda s: (s[0], int(s[1:])))
            txt = f"{lo}+{hi}x{t}"
        try:
            if self.is_terminal(self.apply_move(state, move)):
                txt += "#"
        except Exception:                                   # pragma: no cover
            pass
        return txt

    # ---- bot eval --------------------------------------------------------
    def heuristic(self, state: AState) -> list:
        """Rough eval for the MCTS rollout cutoff: triple stacks are the game
        (they are permanent and TARGET of them wins), double stacks are partial
        progress.  Returns one payoff per seat."""
        tgt = TARGET[state.variant]
        t = [0, 0]
        d = [0, 0]
        for st in state.board.values():
            if len(st) == 3:
                t[st[-1]] += 1
            elif len(st) == 2:
                d[st[-1]] += 1
        score = (t[WHITE] - t[BLACK]) + 0.15 * (d[WHITE] - d[BLACK])
        x = tanh(score / tgt)
        return [x, -x]

    # ---- rendering -------------------------------------------------------
    def render(self, state: AState, perspective=None) -> dict:
        v = state.variant
        tints = {_cid(c): "#15130f" for c in VOIDS[v]}
        labels = {_cid(c): "x" for c in VOIDS[v]}
        pieces = [{"cell": _cid(c), "owner": st[-1], "stack": list(st)}
                  for c, st in state.board.items()]
        highlights = [{"cell": c, "kind": "last-move"} for c in state.last]
        w = self._triple_winner(state)
        if w is None and self.is_terminal(state):
            w = 1 - state.to_move
        tw, tb = self._triples(state, WHITE), self._triples(state, BLACK)
        info = (f"stock {state.stock[WHITE]}-{state.stock[BLACK]}, "
                f"triples {tw}-{tb} of {TARGET[v]}")
        if w is not None:
            cap = f"{SEAT_NAMES[w]} wins ({info})"
        else:
            cap = f"{SEAT_NAMES[state.to_move]} to move — {info}"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": SIZE[v],
                      "tints": tints, "labels": labels},
            "pieces": pieces,
            "highlights": highlights,
            "reserve": {"0": {"P": state.stock[WHITE]},
                        "1": {"P": state.stock[BLACK]}},
            "caption": cap,
        }
