"""Terrace — Anton Dresden & Buzz Siler (published 1991/1992 by Siler/Siler).

A square board whose squares sit at **different heights**.  Level 1 is a single
corner square; the squares rise stepwise in L-shaped "terraces" to the two
opposite corners, which are the highest.  On an 8x8 board there are eight
levels, on the 6x6 board six::

    elevation(c, r) = min(max(c, r), max(N-1-c, N-1-r)) + 1

so a1 and h8 are level 1 and a8 and h1 are level 8.  Every level splits into
exactly TWO one-square-wide L-shaped chains (verified in ``selftest.py``), which
is what the publisher's rule "it cannot move across the centerpoint of the
board" describes: the two chains are never orthogonally adjacent, so the rule is
already implied by the geometry.

Pieces come in sizes 1..4 (1..3 on the 6x6 board); one size-1 piece per player is
marked **T** and is that player's royal piece.

The four rules (Siler/Siler, "The 4 rules of Terrace", terracegames.com/rules,
archived 2006-04-30):

* **Moving on the same level** — to any vacant square on the same level it can
  reach *without jumping over an opponent's piece*.  Your OWN pieces may be
  jumped (Wikipedia: "are allowed to jump over their own pieces").
* **Moving up** — straight or diagonally up, one square, to a vacant square one
  level higher.
* **Moving down** — straight down only, one square, to a vacant square one level
  lower.  (Diagonal moves down are for capturing only.)
* **Capturing** — move DIAGONALLY DOWN one level onto a piece of the same size or
  smaller.  "Any piece" includes your own: cannibalism is the game's signature
  rule, and the publisher advertises it as such.

You win by moving your T to the lowest square across the board (seat 0 -> the
far level-1 corner, seat 1 -> a1) or by capturing the opponent's T.  If the
player to move cannot move at all, the game is a draw ("there is no winner and
no loser").

Move strings are the platform's ``"from>to"`` cell paths, e.g. ``"2,1>3,2"``;
a capture is written the same way, with an occupied destination.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import tanh
from typing import Optional

from agp.game import Game

# --------------------------------------------------------------------------
# Piece encoding.  0 = empty; otherwise a small int packing owner/size/royal so
# the board is a flat tuple of ints (cheap to hash, copy and JSON-serialise).
MAX_SIZE = 4


def enc(owner: int, size: int, royal: bool) -> int:
    return 1 + owner * (2 * MAX_SIZE) + (size - 1) * 2 + (1 if royal else 0)


def dec(code: int) -> tuple[int, int, bool]:
    v = code - 1
    return v // (2 * MAX_SIZE), (v % (2 * MAX_SIZE)) // 2 + 1, bool(v % 2)


def owner_of(code: int) -> int:
    return (code - 1) // (2 * MAX_SIZE)


def size_of(code: int) -> int:
    return ((code - 1) % (2 * MAX_SIZE)) // 2 + 1


def is_royal(code: int) -> bool:
    return bool((code - 1) % 2)


# --------------------------------------------------------------------------
# Board geometry


def elevation(c: int, r: int, n: int) -> int:
    """Height of square (c, r) on an n x n Terrace board, 1 = lowest.

    Reproduces the published board exactly: L-shaped terraces rising stepwise
    from the two lowest, diagonally opposite corners (0,0) and (n-1,n-1) to the
    two highest corners (0,n-1) and (n-1,0).
    """
    return min(max(c, r), max(n - 1 - c, n - 1 - r)) + 1


ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))


class Geometry:
    """Precomputed neighbour tables for one board size."""

    def __init__(self, n: int):
        self.n = n
        self.ncells = n * n
        # The largest piece rank in the set that ships with this board.
        self.largest = 4 if n == 8 else 3
        self.elev = tuple(elevation(i % n, i // n, n) for i in range(n * n))
        # seat 0 runs for the far level-1 corner, seat 1 for (0,0)
        self.target = (n * n - 1, 0)

        def nb(i, dirs):
            c, r = i % n, i // n
            out = []
            for dc, dr in dirs:
                x, y = c + dc, r + dr
                if 0 <= x < n and 0 <= y < n:
                    out.append(y * n + x)
            return tuple(sorted(out))

        orth = [nb(i, ORTH) for i in range(n * n)]
        diag = [nb(i, DIAG) for i in range(n * n)]
        e = self.elev
        # Straight OR diagonal, one level up (the "moving up" rule).
        self.up_any = tuple(
            tuple(j for j in sorted(orth[i] + diag[i]) if e[j] == e[i] + 1)
            for i in range(n * n))
        # Straight only, one level down (the "moving down" rule).
        self.down_orth = tuple(
            tuple(j for j in orth[i] if e[j] == e[i] - 1) for i in range(n * n))
        # Straight, same level: the terrace chain used by the same-level move.
        self.same_orth = tuple(
            tuple(j for j in orth[i] if e[j] == e[i]) for i in range(n * n))
        # Diagonal, one level down: the capture direction.
        self.diag_down = tuple(
            tuple(j for j in diag[i] if e[j] == e[i] - 1) for i in range(n * n))
        # Straight, one level up: only used by the Rank Capture variant.
        self.up_orth = tuple(
            tuple(j for j in orth[i] if e[j] == e[i] + 1) for i in range(n * n))


_GEOM: dict[int, Geometry] = {}


def geom(n: int) -> Geometry:
    g = _GEOM.get(n)
    if g is None:
        g = _GEOM[n] = Geometry(n)
    return g


def cell_name(c: int, r: int) -> str:
    return f"{c},{r}"


def parse_cell(text: str) -> tuple[int, int]:
    c, r = text.split(",")
    return int(c), int(r)


def algebraic(i: int, n: int) -> str:
    """Publisher-style square name (a1..h8), used only in the move log."""
    return f"{chr(ord('a') + i % n)}{i // n + 1}"


# --------------------------------------------------------------------------
# Published starting positions.  Each entry is seat 0's back two ranks, given as
# rank 1 then rank 2, west to east; ``None`` = empty square, ``"T"`` = the royal
# (a size-1 piece).  Seat 1's array is the 180-degree rotation of seat 0's (the
# board itself has that symmetry), which ``setup_board`` derives and
# ``selftest.py`` checks against the transcribed AbstractPlay tables.
#
#  * "long" is the standard game: 16 pieces each on 8x8 (4 of each size),
#    12 each on 6x6 (4 of each of the three sizes) — Wikipedia's description of
#    the 1997 revision, "12 pieces per player instead of 16. Two rows separate
#    the two players' pieces, instead of four."
#  * "short" is the publisher's quick setup (terracegames.com/boardgame.html,
#    "Short Game (15 to 20 minutes)"): one rank, both end squares left empty.
SETUPS = {
    (8, "long"): (["T", 1, 2, 2, 3, 3, 4, 4],
                  [4, 4, 3, 3, 2, 2, 1, 1]),
    (8, "short"): ([None, 4, 3, 3, 2, 2, "T", None],),
    (6, "long"): (["T", 1, 2, 2, 3, 3],
                  [3, 3, 2, 2, 1, 1]),
    (6, "short"): ([None, 3, 2, 2, "T", None],),
}

# Plies without a capture after which the game is drawn.  Terrace as published
# has NO such rule; it is added purely to guarantee termination (see rules.md),
# so it is set deliberately loose: 200 plies = 100 moves EACH, twice the chess
# 50-move convention.  It is the only thing that bounds the game — every capture
# removes a piece for good, so a game can hold at most (pieces - 1) captures and
# therefore at most `pieces * QUIET_LIMIT` plies.  Measured on the default
# setup, uniform-random play trips it once in 2000 games (see rules.md).
QUIET_LIMIT = 200

RESULT_TEXT = {
    "target": "T reached the far corner",
    "royal": "T captured",
    "stalemate": "no legal move",
    "quiet": f"{QUIET_LIMIT} plies without a capture",
}


@dataclass(frozen=True)
class TState:
    board: tuple            # n*n entries, 0 = empty, else a piece code
    to_move: int
    size: int               # board side, 6 or 8
    setup: str              # "long" | "short"  (recorded; no rule reads it)
    capture: str            # "standard" | "rank"
    quiet: int              # plies since the last capture
    ply: int
    winner: Optional[int]   # None = live, -1 = draw, 0/1 = that seat won
    end: Optional[str] = None    # why it ended, for the caption
    last: Optional[str] = None   # last move, for the render highlight


class Terrace(Game):
    """Terrace (Anton Dresden & Buzz Siler)."""

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------- setup

    @staticmethod
    def setup_board(n: int, setup: str) -> tuple:
        """The published opening array.  Seat 0's ranks are laid out from the
        table; seat 1's are the 180-degree rotation, which is how the board's own
        symmetry maps one player's home onto the other's."""
        board = [0] * (n * n)
        rows = SETUPS[(n, setup)]
        for r, row in enumerate(rows):
            assert len(row) == n, (n, setup, r)
            for c, entry in enumerate(row):
                if entry is None:
                    continue
                royal = entry == "T"
                size = 1 if royal else int(entry)
                board[r * n + c] = enc(0, size, royal)
                # 180-degree rotation for the opponent
                board[(n - 1 - r) * n + (n - 1 - c)] = enc(1, size, royal)
        return tuple(board)

    def initial_state(self, options: Optional[dict] = None, rng=None) -> TState:
        o = options or {}
        n = int(o.get("board", 8))
        if n not in (6, 8):
            raise ValueError(f"board size must be 6 or 8, got {n!r}")
        setup = str(o.get("setup", "long"))
        if setup not in ("long", "short"):
            raise ValueError(f"unknown setup {setup!r}")
        capture = str(o.get("capture", "standard"))
        if capture not in ("standard", "rank"):
            raise ValueError(f"unknown capture rule {capture!r}")
        return TState(
            board=self.setup_board(n, setup),
            to_move=0,
            size=n,
            setup=setup,
            capture=capture,
            quiet=0,
            ply=0,
            winner=None,
            end=None,
            last=None,
        )

    def current_player(self, state: TState) -> int:
        return state.to_move

    # -------------------------------------------------------- move rules

    @staticmethod
    def same_level_targets(board: tuple, g: Geometry, i: int, seat: int) -> list[int]:
        """Every vacant square the piece on ``i`` can reach along its terrace.

        The terrace is walked square by square; an OPPONENT's piece stops the
        walk (it may be neither entered nor jumped), one of your own may be
        passed over.  Each level of a Terrace board splits into two chains that
        are simple paths (asserted in selftest.py), so "the route" between two
        squares of a chain is unique and this flood fill is exactly the
        publisher's "which it can reach without jumping over an opponent's
        piece".
        """
        out = []
        seen = {i}
        stack = [i]
        while stack:
            k = stack.pop()
            for j in g.same_orth[k]:
                if j in seen:
                    continue
                code = board[j]
                if code and owner_of(code) != seat:
                    continue            # an opponent's piece blocks the chain
                seen.add(j)
                stack.append(j)
                if code == 0:
                    out.append(j)
        return out

    @staticmethod
    def capture_targets(board: tuple, g: Geometry, i: int, rule: str) -> list[int]:
        """Squares the piece on ``i`` may capture on (its own pieces included —
        cannibalism is legal and is the game's signature rule)."""
        mine = size_of(board[i])
        out = []
        if rule == "standard":
            # "A piece can capture any piece which is the same size or smaller
            # by MOVING DIAGONALLY DOWN to the next lower level, into its
            # square."  (Siler/Siler, rules.html)
            for j in g.diag_down[i]:
                code = board[j]
                if code and size_of(code) <= mine:
                    out.append(j)
            return out
        # Rank Capture (Tom Hawkins, Terrace Times Summer 1995).  Only the
        # capturing rule changes; movement and setups are untouched.
        for j in g.up_orth[i]:              # straight up: must be LARGER…
            code = board[j]
            if not code:
                continue
            sz = size_of(code)
            # …except assassination: a rank-1 piece (the T included) may take a
            # largest-rank piece straight above it.
            if sz < mine or (mine == 1 and sz == g.largest):
                out.append(j)
        for j in g.same_orth[i]:            # same level, adjacent: at least equal
            code = board[j]
            if code and size_of(code) <= mine:
                out.append(j)
        for j in g.diag_down[i]:            # diagonally down: at most one smaller
            code = board[j]
            if code and mine >= size_of(code) - 1:
                out.append(j)
        return out

    def legal_moves(self, state: TState) -> list[str]:
        if state.winner is not None:
            return []
        g = geom(state.size)
        n = state.size
        board = state.board
        seat = state.to_move
        pairs = []
        for i, code in enumerate(board):
            if code == 0 or owner_of(code) != seat:
                continue
            for j in g.up_any[i]:           # straight or diagonally up
                if board[j] == 0:
                    pairs.append((i, j))
            for j in g.down_orth[i]:        # straight down only
                if board[j] == 0:
                    pairs.append((i, j))
            for j in self.same_level_targets(board, g, i, seat):
                pairs.append((i, j))
            for j in self.capture_targets(board, g, i, state.capture):
                pairs.append((i, j))
        # The four families land on disjoint (elevation, occupancy) classes, so
        # this dedupe is defensive only — selftest.py asserts it never bites.
        seen = set()
        out = []
        for i, j in pairs:
            if (i, j) in seen:
                continue
            seen.add((i, j))
            out.append(f"{cell_name(i % n, i // n)}>{cell_name(j % n, j // n)}")
        out.sort()
        return out

    # ------------------------------------------------------ move application

    @staticmethod
    def _parse(move: str, n: int) -> tuple[int, int]:
        parts = move.split(">")
        if len(parts) != 2:
            raise ValueError(f"bad move {move!r}")
        out = []
        for p in parts:
            c, r = parse_cell(p)
            if not (0 <= c < n and 0 <= r < n):
                raise ValueError(f"off-board cell in {move!r}")
            out.append(r * n + c)
        if out[0] == out[1]:
            raise ValueError(f"null move {move!r}")
        return out[0], out[1]

    @staticmethod
    def royal_cell(board: tuple, seat: int) -> Optional[int]:
        for i, code in enumerate(board):
            if code and is_royal(code) and owner_of(code) == seat:
                return i
        return None

    def apply_move(self, state: TState, move: str, rng=None) -> TState:
        if state.winner is not None:
            raise ValueError("game is over")
        n = state.size
        g = geom(n)
        i, j = self._parse(move, n)
        seat = state.to_move
        code = state.board[i]
        if code == 0 or owner_of(code) != seat:
            raise ValueError(f"no piece of seat {seat} on {move.split('>')[0]}")
        # Reject an illegal-but-parseable move.  The server already gates on
        # `move in legal_moves`, so this is defence in depth -- but the failure
        # mode it closes is the worst one there is: without it, "0,0>7,7" walks
        # a T straight to the far corner and is scored as a WIN.
        if move not in self.legal_moves(state):
            raise ValueError(f"illegal move {move!r}")

        board = list(state.board)
        captured = board[j] != 0
        board[j] = code
        board[i] = 0
        board = tuple(board)
        quiet = 0 if captured else state.quiet + 1

        # ------------------------------------------------------------------
        # Result.  A DECISIVE result is decided BEFORE the draw conditions: a T
        # that reaches its corner (or a T that is captured) on the very ply that
        # strands the opponent or trips the no-capture counter still wins.
        winner: Optional[int] = None
        end: Optional[str] = None
        mine = self.royal_cell(board, seat)
        theirs = self.royal_cell(board, 1 - seat)
        if theirs is None:
            winner, end = seat, "royal"
        elif mine is None:                      # you may cannibalise your own T
            winner, end = 1 - seat, "royal"
        elif mine == g.target[seat]:
            winner, end = seat, "target"
        else:
            nxt = TState(board=board, to_move=1 - seat, size=n, setup=state.setup,
                         capture=state.capture, quiet=quiet, ply=state.ply + 1,
                         winner=None)
            if not self.legal_moves(nxt):
                # "If a player cannot make an allowed move, there is no winner
                # and no loser."  (Siler/Siler, rules.html)
                winner, end = -1, "stalemate"
            elif quiet >= QUIET_LIMIT:
                winner, end = -1, "quiet"

        return TState(board=board, to_move=1 - seat, size=n, setup=state.setup,
                      capture=state.capture, quiet=quiet, ply=state.ply + 1,
                      winner=winner, end=end, last=move)

    # ------------------------------------------------------------- results

    def is_terminal(self, state: TState) -> bool:
        return state.winner is not None

    def returns(self, state: TState) -> list[float]:
        if state.winner is None or state.winner == -1:
            return [0.0, 0.0]
        return [1.0, -1.0] if state.winner == 0 else [-1.0, 1.0]

    def heuristic(self, state: TState) -> list[float]:
        """Material (by size) plus how far each T still has to travel."""
        if state.winner is not None:
            return self.returns(state)
        n = state.size
        g = geom(n)
        mat = [0, 0]
        for code in state.board:
            if code:
                mat[owner_of(code)] += size_of(code)
        far = [1.0, 1.0]
        for seat in (0, 1):
            i = self.royal_cell(state.board, seat)
            if i is None:
                continue
            t = g.target[seat]
            d = max(abs(i % n - t % n), abs(i // n - t // n))
            far[seat] = d / float(n - 1)
        v = 0.7 * tanh((mat[0] - mat[1]) / 8.0) + 0.3 * (far[1] - far[0])
        return [v, -v]

    # --------------------------------------------------------- persistence

    def serialize(self, state: TState) -> dict:
        return {
            "board": list(state.board),
            "to_move": state.to_move,
            "size": state.size,
            "setup": state.setup,
            "capture": state.capture,
            "quiet": state.quiet,
            "ply": state.ply,
            "winner": state.winner,
            "end": state.end,
            "last": state.last,
        }

    def deserialize(self, data: dict) -> TState:
        return TState(
            board=tuple(int(x) for x in data["board"]),
            to_move=int(data["to_move"]),
            size=int(data["size"]),
            setup=str(data["setup"]),
            capture=str(data["capture"]),
            quiet=int(data["quiet"]),
            ply=int(data["ply"]),
            winner=None if data["winner"] is None else int(data["winner"]),
            end=data["end"],
            last=data["last"],
        )

    # -------------------------------------------------------- presentation

    def describe_move(self, state: TState, move: str) -> str:
        n = state.size
        i, j = self._parse(move, n)
        code = state.board[i]
        if code == 0:
            return move
        tag = "T" if is_royal(code) else str(size_of(code))
        victim = state.board[j]
        if victim == 0:
            sep = "-"
        elif owner_of(victim) == owner_of(code):
            sep = "*"                        # cannibalism
        else:
            sep = "x"
        return f"{tag} {algebraic(i, n)}{sep}{algebraic(j, n)}"

    # The generic renderer draws a `board.labels` entry on an EMPTY cell in a
    # faint stone colour (`#8f8674` in web/src/Board.jsx).  The ramp below must
    # therefore stay clear of it at its light end, or the elevation number on
    # the highest terraces -- exactly the squares whose height matters most --
    # becomes invisible against its own tint.  `selftest.py` asserts the margin.
    LABEL_COLOUR = (0x8F, 0x86, 0x74)
    TINT_LO = (0x1A, 0x17, 0x12)
    TINT_HI = (0x70, 0x66, 0x53)

    @classmethod
    def _tint(cls, level: int, n: int) -> str:
        """Dark-to-light stone ramp so the terraces read at a glance."""
        t = (level - 1) / float(n - 1)
        return "#%02x%02x%02x" % tuple(
            int(round(a + (b - a) * t)) for a, b in zip(cls.TINT_LO, cls.TINT_HI))

    def render(self, state: TState, perspective: Optional[int] = None) -> dict:
        n = state.size
        g = geom(n)
        pieces = []
        for i, code in enumerate(state.board):
            if code == 0:
                continue
            owner, size, royal = dec(code)
            pieces.append({
                "cell": cell_name(i % n, i // n),
                "owner": owner,
                "size": size,                    # disc scales with the piece
                "label": "T" if royal else str(size),
            })

        tints = {}
        labels = {}
        for i in range(n * n):
            cid = cell_name(i % n, i // n)
            tints[cid] = self._tint(g.elev[i], n)
            labels[cid] = str(g.elev[i])
        # The two goal squares, in their owner's colours.
        tints[cell_name(g.target[0] % n, g.target[0] // n)] = "#5a2222"
        tints[cell_name(g.target[1] % n, g.target[1] // n)] = "#1e2f5a"

        highlights = []
        if state.last:
            for k in self._parse(state.last, n):
                highlights.append({"cell": cell_name(k % n, k // n),
                                   "kind": "last-move"})

        names = ("Red", "Blue")
        if state.winner is None:
            caption = f"{names[state.to_move]} to move"
            if state.quiet >= QUIET_LIMIT // 2:
                caption += f" — {state.quiet}/{QUIET_LIMIT} plies without a capture"
        elif state.winner == -1:
            caption = f"Draw — {RESULT_TEXT[state.end]}"
        else:
            caption = f"{names[state.winner]} wins — {RESULT_TEXT[state.end]}"

        return {
            "board": {
                "type": "square", "width": n, "height": n,
                "tints": tints,
                "labels": labels,
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
