"""Clusterfuss — Mark Steere, July 2023.

A square board of any size, initially FILLED with checkers in a strict
alternating (checkerboard) pattern; Red occupies the top-left corner cell.
Red moves first.

MOVES.  Every move is an *orthogonal king capture*: you move one of your own
checkers onto an orthogonally adjacent OCCUPIED cell, capturing whatever stood
there by replacement.  The captured checker may be an ENEMY checker **or one of
your own** — friendly capture is legal and strategically load-bearing (the rule
sheet devotes two puzzle figures to exactly that point).  The board therefore
loses exactly one checker per move, plus whatever the enemy-only-group removal
sweeps up.

GROUPS.  A group is a maximal set of checkers interconnected orthogonally.
Diagonal adjacency is irrelevant, and **a group may contain checkers of either
or both colours** — connectivity here is colour-blind, unlike almost every other
connection game.

MOVE RESTRICTION.  A move is legal only if, after the capture, there is exactly
**one group containing your checkers** (that group may also contain enemy
checkers).

ENEMY-ONLY GROUP REMOVAL.  If the move detaches groups made up only of enemy
checkers, they are removed from the board immediately, concluding the turn.
Because the move restriction guarantees exactly one group holds your checkers,
*every* other group is enemy-only, so removal always restores the single-group
invariant stated on the sheet ("at the conclusion of your turn, there should
only be one group on the board").

OBJECT.  Remove all enemy checkers from the board.

SKIPPING.  Passing is not allowed, but a player with no available move has their
turn skipped — handled inside ``apply_move`` (the platform requires a non-empty
``legal_moves`` on every non-terminal state).

TERMINATION (proved, not capped).
  * Every move removes at least one checker from the board and never adds one,
    so the total checker count is a strictly decreasing monovariant, bounded
    below by 1 (once a colour is gone the game is over).  A game therefore lasts
    at most ``n*n - 1`` plies — and that bound is TIGHT (4x4 games reach 15).
    No repetition rule and no ply cap, so no cap can decide an outcome.

SKIPPING IS VACUOUS.  A skipped turn changes nothing, so in principle it could
loop forever.  It cannot:
  * After any legal move the surviving cells are exactly the one group holding
    the mover's checkers (the legality test allows only one such group, and step
    5 deletes every other group).  So the board is ALWAYS a single group — not
    merely by induction from the full starting rectangle, but unconditionally.
  * In a connected group, take a spanning tree and the subtree spanned by one
    player's checkers.  A leaf X of that subtree belongs to that player;
    removing X from the tree leaves all their other checkers in ONE component,
    and every component of the group minus X touches X, so some neighbour Y of X
    lies in that component.  X->Y is legal.
  * Hence every player who still owns a checker always has a legal move, so no
    turn is ever actually skipped and both players can never be immobile at
    once.  The skip is implemented anyway (defensively); ``is_terminal`` scores
    the impossible mutual-immobility position as an honest DRAW rather than
    hanging or inventing a tiebreak, and ``selftest.py`` covers both.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

NAMES = {0: "Red", 1: "Blue"}
SIZES = (4, 5, 6, 8, 10)
DEFAULT_SIZE = 8
ORTHO = ((0, 1), (0, -1), (1, 0), (-1, 0))


@dataclass
class CState:
    n: int = DEFAULT_SIZE
    board: dict = field(default_factory=dict)      # (c, r) -> 0 (Red) / 1 (Blue)
    to_move: int = 0
    ply: int = 0
    last: Optional[tuple] = None                   # ((fc, fr), (tc, tr)) or None


# --------------------------------------------------------------------------- #
# cells                                                                        #
# --------------------------------------------------------------------------- #

def parse_cell(s: str) -> tuple:
    c, r = s.split(",")
    return int(c), int(r)


def cell_name(t) -> str:
    return f"{t[0]},{t[1]}"


def neighbours(cell, n):
    """The orthogonal on-board neighbours of `cell` on an n x n board."""
    c, r = cell
    for dc, dr in ORTHO:
        cc, rr = c + dc, r + dr
        if 0 <= cc < n and 0 <= rr < n:
            yield (cc, rr)


def initial_board(n: int) -> dict:
    """A full board, colours alternating, Red (seat 0) on the TOP-LEFT cell.

    Row 0 is the BOTTOM row (the renderer draws it there), so the top-left cell
    is ``(0, n-1)``.  Red takes every cell whose ``(c + (n-1-r))`` is even,
    which is exactly the shading parity the web renderer uses, so Red always
    sits on one shade of the checkerboard — Figure 1 of the rule sheet.
    """
    return {(c, r): (0 if (c + (n - 1 - r)) % 2 == 0 else 1)
            for r in range(n) for c in range(n)}


# --------------------------------------------------------------------------- #
# groups (COLOUR-BLIND orthogonal connectivity)                                #
# --------------------------------------------------------------------------- #

def components(board: dict, n: int) -> tuple:
    """Label every occupied cell with its group id.

    Returns ``(labels, count)``.  Connectivity ignores colour: a group may hold
    checkers of either or both colours.  Start cells are visited in sorted order
    so labels are deterministic.
    """
    labels: dict = {}
    count = 0
    for start in sorted(board):
        if start in labels:
            continue
        labels[start] = count
        stack = [start]
        while stack:
            cur = stack.pop()
            for nb in neighbours(cur, n):
                if nb in board and nb not in labels:
                    labels[nb] = count
                    stack.append(nb)
        count += 1
    return labels, count


def group_count(board: dict, n: int) -> int:
    return components(board, n)[1]


# --------------------------------------------------------------------------- #
# move generation                                                              #
# --------------------------------------------------------------------------- #

def gen_moves(board: dict, n: int, player: int):
    """Yield every legal ``(from, to)`` capture for `player`.

    A move takes checker X onto an orthogonally adjacent occupied cell Y.  On
    the resulting board the cell X is empty and Y holds one of the mover's
    checkers, so the connectivity of the post-move board is exactly that of the
    pre-move board minus the vertex X.  The move is legal iff exactly one
    component of ``board - X`` contains checkers of `player` — and Y's component
    always does, because Y is now the mover's.  So: legal iff every OTHER
    checker of `player` lies in Y's component.
    """
    mine = sorted(c for c, p in board.items() if p == player)
    for x in mine:
        targets = [y for y in neighbours(x, n) if y in board]
        if not targets:
            continue
        sub = dict(board)
        del sub[x]
        labels, _ = components(sub, n)
        others = {labels[z] for z in mine if z != x}
        for y in targets:
            if others <= {labels[y]}:
                yield (x, y)


def moves_for(board: dict, n: int, player: int) -> list:
    """All legal ``(from, to)`` captures for `player`, sorted."""
    return sorted(gen_moves(board, n, player))


def any_move(board: dict, n: int, player: int) -> bool:
    """Does `player` have at least one legal move?  (Early-exit `moves_for`.)"""
    for _ in gen_moves(board, n, player):
        return True
    return False


def resolve(board: dict, n: int, player: int, x: tuple, y: tuple) -> dict:
    """Apply the capture X->Y for `player`, then remove enemy-only groups."""
    nb = dict(board)
    del nb[x]
    nb[y] = player
    labels, count = components(nb, n)
    if count > 1:
        keep = {labels[c] for c, p in nb.items() if p == player}
        nb = {c: p for c, p in nb.items() if labels[c] in keep}
    return nb


def counts(board: dict) -> tuple:
    red = sum(1 for p in board.values() if p == 0)
    return red, len(board) - red


# --------------------------------------------------------------------------- #
# the game                                                                     #
# --------------------------------------------------------------------------- #

class Clusterfuss(Game):
    name = "Clusterfuss"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup ----------------------------------------------------------- #
    def initial_state(self, options=None, rng=None) -> CState:
        n = int((options or {}).get("size", DEFAULT_SIZE))
        if n not in SIZES:
            raise ValueError(f"unsupported board size {n}; choose one of {SIZES}")
        return CState(n=n, board=initial_board(n), to_move=0, ply=0, last=None)

    # ---- core loop -------------------------------------------------------- #
    def current_player(self, s: CState) -> int:
        return s.to_move

    def is_terminal(self, s: CState) -> bool:
        red, blue = counts(s.board)
        # A DECISIVE result (one colour wiped out) is checked FIRST so it can
        # never be masked by the immobility fallback below.
        if red == 0 or blue == 0:
            return True
        # Immobility.  ``apply_move`` has already skipped the next player's turn
        # if they had no move, so "the side to move has no move" means NEITHER
        # side has one — an honest draw, not a fabricated tiebreak.  Provably
        # unreachable in play (module docstring); ``selftest.py`` exercises it
        # from a hand-built position and asserts play never produces it.
        return not any_move(s.board, s.n, s.to_move)

    def legal_moves(self, s: CState) -> list:
        if self.is_terminal(s):
            return []
        return [f"{cell_name(x)}>{cell_name(y)}"
                for x, y in moves_for(s.board, s.n, s.to_move)]

    def apply_move(self, s: CState, move: str, rng=None) -> CState:
        try:
            frm, to = move.split(">")
            x, y = parse_cell(frm), parse_cell(to)
        except ValueError as e:
            raise ValueError(f"malformed Clusterfuss move {move!r}") from e
        board = resolve(s.board, s.n, s.to_move, x, y)
        nxt = 1 - s.to_move
        out = CState(n=s.n, board=board, to_move=nxt, ply=s.ply + 1, last=(x, y))
        red, blue = counts(board)
        # "Passing is not allowed, but if you don't have an available move,
        # your turn is skipped."  At most one skip can ever occur — a skip
        # changes nothing and some player always has a move (module docstring).
        if red and blue and not any_move(board, s.n, nxt):
            out.to_move = s.to_move
        return out

    def returns(self, s: CState) -> list:
        red, blue = counts(s.board)
        if blue == 0 and red > 0:
            return [1.0, -1.0]
        if red == 0 and blue > 0:
            return [-1.0, 1.0]
        # Empty board, or both players immobile: an honest draw.
        return [0.0, 0.0]

    # ---- persistence ------------------------------------------------------ #
    def serialize(self, s: CState) -> dict:
        return {
            "n": s.n,
            "board": {cell_name(c): p for c, p in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "last": None if s.last is None else [cell_name(s.last[0]),
                                                 cell_name(s.last[1])],
        }

    def deserialize(self, d: dict) -> CState:
        # Every key is read positionally (no ``.get`` defaults) so a field that
        # ``serialize`` stops emitting fails LOUDLY instead of silently
        # re-defaulting — the bug that silently breaks async matches.
        last = d["last"]
        return CState(
            n=d["n"],
            board={parse_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d["ply"],
            last=None if last is None else (parse_cell(last[0]), parse_cell(last[1])),
        )

    # ---- presentation ----------------------------------------------------- #
    def describe_move(self, s: CState, move: str) -> str:
        who = NAMES[s.to_move][0]
        frm, to = move.split(">")
        victim = s.board.get(parse_cell(to))
        after = self.apply_move(s, move)
        removed = len(s.board) - 1 - len(after.board)
        text = f"{who} {frm}x{to}"
        if victim == s.to_move:
            text += " (own)"
        if removed:
            text += f" [{removed} cut off]"
        if self.is_terminal(after):
            ret = self.returns(after)
            text += " wins" if ret[s.to_move] > 0 else " draw"
        elif after.to_move == s.to_move:
            text += f" ({NAMES[1 - s.to_move]} skipped)"
        return text

    def render(self, s: CState, perspective=None) -> dict:
        pieces = [{"cell": cell_name(c), "owner": p} for c, p in sorted(s.board.items())]
        highlights = []
        if s.last is not None:
            highlights = [{"cell": cell_name(s.last[0]), "kind": "last-move"},
                          {"cell": cell_name(s.last[1]), "kind": "last-move"}]
        red, blue = counts(s.board)
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret[0] > ret[1]:
                caption = f"Red wins — Blue wiped out ({red} left)"
            elif ret[1] > ret[0]:
                caption = f"Blue wins — Red wiped out ({blue} left)"
            else:
                caption = f"Draw ({red}-{blue})"
        else:
            caption = f"{NAMES[s.to_move]} to move  (Red {red} – Blue {blue})"
        return {
            "board": {"type": "square", "width": s.n, "height": s.n},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }

    # ---- bot eval --------------------------------------------------------- #
    # NO ``heuristic``, deliberately.  The obvious candidates were MEASURED and
    # carry no signal: over 150 random 6x6 games, the sign of the material
    # balance at 80% of the way through the game agreed with the eventual
    # winner 69/122 times (56.6%, ~1.5 sd — not significant) and the mobility
    # balance 42/80 (52.5%).  That is unsurprising: friendly capture is often
    # the winning move, so spending your own material is not a loss.  Shipping
    # a coin-flip eval only risks a sign error, and the MCTS rollout cutoff
    # (50 plies) is rarely even reached — a whole game is at most n*n-1 plies
    # (63 on the standard board) and a mid-game rollout ends far sooner — so
    # the draw fallback costs almost nothing here.
