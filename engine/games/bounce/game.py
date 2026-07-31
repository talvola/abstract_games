"""Bounce — Mark Steere, August 2023.

A square board of any even size, filled with a checkerboard pattern of Red and
Blue checkers except the four corner squares, which start empty (8x8 => 30
checkers each).  A GROUP is a monocoloured, ORTHOGONALLY interconnected set of
checkers.

On your turn you move one of your checkers to ANY unoccupied square on the
board (it is a teleport, not a step).  The checker you move must be part of a
strictly LARGER group after your move than it was before your move.  If you
have no legal move at all, you must instead remove any one of your own
checkers from the board, which concludes your turn.

If, at the conclusion of your turn, all of your checkers form one group, you
win.  Red moves first.

Termination (proof, so there is no ply cap and no repetition rule):
    Let S_p be the multiset of group sizes of player p, written in DESCENDING
    order.  A move by p takes the moved checker out of its group A (size a),
    possibly splitting A into fragments (each of size < a), and drops it on an
    empty square where it merges with some set of groups C_1..C_k plus possibly
    some of those fragments, forming a new group of size b, and the rule
    requires b > a.  Every element removed from S_p is either a (< b by the
    rule) or some C_i (< b, since b >= 1 + C_i); every element added is either
    b itself or a fragment (< a < b).  So S_p and S_p' agree on the count of
    every value strictly greater than b, and at the value b itself S_p' has one
    more.  Hence **S_p increases strictly lexicographically on every move by
    p**, and p's group structure is untouched by the opponent's turns (groups
    are monocoloured and adjacency is direct, so only p can change them).
    A player's checker count n_p never rises and drops by exactly one on every
    removal.  For fixed n_p there are only finitely many (partition(n_p))
    possible S_p and each move strictly increases it, so only finitely many
    moves can occur between two removals; and there are at most n_p removals.
    Therefore the game is finite.

    A corollary of the same argument: the MAXIMUM group size max(S_p) is
    non-decreasing while n_p is constant.  `_max_group` is exactly that
    monovariant, and it is also the win test (max == n_p).

No draws are possible: a player reduced to a single checker trivially has all
their checkers in one group and therefore wins at the conclusion of that very
turn, so nobody can ever run out of checkers, so every turn has a legal action
and the (finite) game always ends with somebody unified.

Move notation
    "c,r>c,r"   move a checker from one square to an empty square
    "c,r"       (single cell) remove that checker — offered ONLY on a turn with
                no legal move, so the two forms never coexist in legal_moves.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))
FILES = "abcdefghijklmnopqrstuvwxyz"
SEAT_NAMES = ("Red", "Blue")

# Board sizes offered in the lobby.  The sheet allows "any even size"; these are
# the playable ones (gameslib ships 8 and 10).  Size must be even and >= 4:
# on a 2x2 board every square is a corner, so both players would start with no
# checkers at all.
SIZES = (6, 8, 10)


@dataclass
class BounceState:
    n: int = 8
    board: dict = field(default_factory=dict)   # (c, r) -> seat 0/1
    to_move: int = 0
    winner: Optional[int] = None                # set only inside apply_move
    ply: int = 0
    last: Optional[list] = None                 # ["c,r", "c,r"] or ["c,r"]
    last_kind: str = ""                         # "move" | "remove" | ""
    _moves: Optional[list] = field(default=None, repr=False, compare=False)


def cell_id(p) -> str:
    return f"{p[0]},{p[1]}"


def parse_cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def algebraic(p, n: int) -> str:
    """"a1"-style name; column letters left-to-right, row 1 at the BOTTOM
    (row 0 is drawn at the bottom by the renderer)."""
    return f"{FILES[p[0]]}{p[1] + 1}"


def is_corner(c: int, r: int, n: int) -> bool:
    return c in (0, n - 1) and r in (0, n - 1)


def setup_board(n: int) -> dict:
    """Checkerboard fill, corners empty.  Seat 0 (Red) takes the squares with
    (col+row) ODD, which — with row 0 at the bottom — puts Red on the c8/a2
    squares of the rulebook's Figure 1 and leaves all four corners empty
    (two corners fall on each parity when n is even)."""
    b = {}
    for r in range(n):
        for c in range(n):
            if is_corner(c, r, n):
                continue
            b[(c, r)] = 0 if (c + r) % 2 == 1 else 1
    return b


def label_groups(board: dict, seat: int):
    """Return (gid_of_cell, cells_of_gid) for one seat's orthogonal groups."""
    gid = {}
    cells = []
    for p, owner in board.items():
        if owner != seat or p in gid:
            continue
        g = len(cells)
        comp = [p]
        gid[p] = g
        i = 0
        while i < len(comp):
            c, r = comp[i]
            i += 1
            for dc, dr in ORTH:
                q = (c + dc, r + dr)
                if q not in gid and board.get(q) == seat:
                    gid[q] = g
                    comp.append(q)
        cells.append(comp)
    return gid, cells


def group_sizes(board: dict, seat: int) -> list:
    """Group sizes of `seat`, sorted DESCENDING — the termination monovariant."""
    _, cells = label_groups(board, seat)
    return sorted((len(c) for c in cells), reverse=True)


def group_containing(board: dict, start, seat: int) -> set:
    """The orthogonally connected group of `seat` checkers containing `start`."""
    comp = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for dc, dr in ORTH:
            q = (c + dc, r + dr)
            if q not in comp and board.get(q) == seat:
                comp.add(q)
                stack.append(q)
    return comp


class Bounce(Game):
    name = "Bounce"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup ---------------------------------------------------------------

    def initial_state(self, options=None, rng=None) -> BounceState:
        opts = options or {}
        n = int(opts.get("size", 8))
        if n % 2 != 0 or n < 4:
            raise ValueError("board size must be even and at least 4")
        return BounceState(n=n, board=setup_board(n))

    def current_player(self, s: BounceState) -> int:
        return s.to_move

    # ---- move generation -----------------------------------------------------

    def _raw_moves(self, s: BounceState) -> list:
        """Every legal (from, to) whose moved checker ends in a strictly larger
        group than the one it left."""
        board, n, seat = s.board, s.n, s.to_move
        gid, gcells = label_groups(board, seat)
        empties = [(c, r) for r in range(n) for c in range(n) if (c, r) not in board]
        if not empties:
            return []
        moves = []
        for frm in sorted(gid):
            a = gid[frm]
            from_size = len(gcells[a])
            # How group `a` falls apart once `frm` leaves it: relabel a \ {frm}.
            sub = {}
            sub_size = []
            for p in gcells[a]:
                if p == frm or p in sub:
                    continue
                k = len(sub_size)
                comp = [p]
                sub[p] = k
                i = 0
                while i < len(comp):
                    c, r = comp[i]
                    i += 1
                    for dc, dr in ORTH:
                        q = (c + dc, r + dr)
                        if q != frm and q not in sub and gid.get(q) == a:
                            sub[q] = k
                            comp.append(q)
                sub_size.append(len(comp))
            for to in empties:
                seen = set()
                total = 0
                for dc, dr in ORTH:
                    q = (to[0] + dc, to[1] + dr)
                    if q == frm or board.get(q) != seat:
                        continue
                    if gid[q] == a:
                        key = ("s", sub[q])
                        size = sub_size[sub[q]]
                    else:
                        key = ("g", gid[q])
                        size = len(gcells[gid[q]])
                    if key not in seen:
                        seen.add(key)
                        total += size
                if 1 + total > from_size:
                    moves.append(f"{cell_id(frm)}>{cell_id(to)}")
        return moves

    def _moves_cached(self, s: BounceState) -> list:
        if s._moves is None:
            if s.winner is not None:
                s._moves = []
            else:
                mv = self._raw_moves(s)
                if not mv:
                    # CHECKER REMOVAL: no legal move => remove any one of your
                    # own checkers.  Cannot be empty: a player is never reduced
                    # below one checker (at one checker they have already won).
                    mv = [cell_id(p) for p in sorted(s.board) if s.board[p] == s.to_move]
                s._moves = mv
        return s._moves

    def legal_moves(self, s: BounceState) -> list:
        return list(self._moves_cached(s))

    def is_terminal(self, s: BounceState) -> bool:
        return s.winner is not None

    # ---- apply ---------------------------------------------------------------

    def apply_move(self, s: BounceState, move: str, rng=None) -> BounceState:
        if s.winner is not None:
            raise ValueError("game is over")
        seat = s.to_move
        board = dict(s.board)
        if ">" in move:
            fs, ts = move.split(">")
            frm, to = parse_cell(fs), parse_cell(ts)
            if move not in self._moves_cached(s):
                raise ValueError(f"illegal move {move!r}")
            del board[frm]
            board[to] = seat
            last, kind = [fs, ts], "move"
        else:
            p = parse_cell(move)
            if move not in self._moves_cached(s):
                raise ValueError(f"illegal move {move!r}")
            del board[p]
            last, kind = [move], "remove"
        # OBJECT: checked at the conclusion of the mover's own turn.  Only the
        # mover's own groups can have changed (groups are monocoloured), so
        # checking just the mover is equivalent to checking both players.
        winner = seat if self._unified(board, seat) else None
        return BounceState(n=s.n, board=board, to_move=1 - seat, winner=winner,
                           ply=s.ply + 1, last=last, last_kind=kind)

    @staticmethod
    def _unified(board: dict, seat: int) -> bool:
        """All of `seat`'s checkers in ONE group.  A lone checker counts (it is
        trivially one group); having NO checkers does not (there is no group) —
        matching AbstractPlay's implementation.  Zero checkers is unreachable
        anyway: the last-but-one removal already leaves one group and wins."""
        _, cells = label_groups(board, seat)
        return len(cells) == 1

    def returns(self, s: BounceState) -> list:
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    # ---- heuristic (MCTS rollout cutoff) -------------------------------------

    @staticmethod
    def _progress(board: dict, seat: int) -> float:
        """How close `seat` is to unification, in [0, 1]; 1.0 exactly when the
        seat is unified — i.e. exactly when `_unified` is true, including the
        zero-checker case, which is False for both and unreachable in play.
        (largest group - 1) / (checkers - 1) — the normalised monovariant."""
        sizes = group_sizes(board, seat)
        n = sum(sizes)
        if n == 0:
            return 0.0     # no checkers => no group (unreachable; see _unified)
        if n == 1:
            return 1.0
        return (sizes[0] - 1) / (n - 1)

    def heuristic(self, s: BounceState) -> list:
        if s.winner is not None:
            return self.returns(s)
        d = self._progress(s.board, 0) - self._progress(s.board, 1)
        v = math.tanh(1.5 * d)
        return [v, -v]

    # ---- serialize -----------------------------------------------------------

    def serialize(self, s: BounceState) -> dict:
        return {
            "n": s.n,
            "board": {cell_id(p): owner for p, owner in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "last": list(s.last) if s.last else None,
            "last_kind": s.last_kind,
        }

    def deserialize(self, d: dict) -> BounceState:
        return BounceState(
            n=d["n"],
            board={parse_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            last=list(d["last"]) if d.get("last") else None,
            last_kind=d.get("last_kind", ""),
        )

    # ---- presentation --------------------------------------------------------

    def describe_move(self, s: BounceState, move: str) -> str:
        seat = s.to_move
        if ">" not in move:
            return f"x{algebraic(parse_cell(move), s.n)} (no legal move)"
        fs, ts = move.split(">")
        frm, to = parse_cell(fs), parse_cell(ts)
        before = len(group_containing(s.board, frm, seat)) if s.board.get(frm) == seat else 0
        board = dict(s.board)
        board.pop(frm, None)
        board[to] = seat
        after = len(group_containing(board, to, seat))
        return f"{algebraic(frm, s.n)}-{algebraic(to, s.n)} ({before}→{after})"

    def render(self, s: BounceState, perspective=None) -> dict:
        pieces = [{"cell": cell_id(p), "owner": owner} for p, owner in s.board.items()]
        highlights = [{"cell": c, "kind": "last-move"} for c in (s.last or [])]
        if s.winner is not None:
            caption = f"{SEAT_NAMES[s.winner]} wins — all checkers in one group"
        else:
            mover = SEAT_NAMES[s.to_move]
            mv = self._moves_cached(s)
            if mv and ">" not in mv[0]:
                caption = f"{mover} has no legal move — remove one of your checkers"
            else:
                caption = f"{mover} to move"
        return {
            "board": {"type": "square", "width": s.n, "height": s.n},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
