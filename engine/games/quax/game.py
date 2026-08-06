"""Quax (Bill Taylor, 2000) -- "Quadrangular Hex".

A square-lattice connection game.  On your turn you either drop a stone on any
empty cell, or spend the whole turn placing a *link* (the physical game's
"rhombic tile") joining two diagonally adjacent stones of your own colour.  Each
2x2 square of the grid holds at most ONE link, so a link is simultaneously a
connection for you and a permanent cut of the opponent's crossing diagonal.

Two stones of a colour are connected when they are orthogonally adjacent, or
diagonally adjacent with that colour's link between them.  Seat 0 (Black, moves
first) joins the TOP and BOTTOM edges; seat 1 (White) joins the LEFT and RIGHT
edges.  A corner cell counts as part of both of its edges.

Pie rule (on by default): on White's very first turn White may play "swap"
instead of moving, taking over Black's opening stone.  Because the seats' goals
are fixed, "swap" is implemented as the value-preserving TRANSPOSE of the whole
position -- every stone/link is reflected across the main diagonal and changes
owner (see rules.md).

Cells are "c,r" with c (column, 0 = left) and r (row, 0 = BOTTOM) in
0..size-1.  A placement move is a single cell; a link move is
"c1,r1>c2,r2" with the LEFT-hand (smaller column) cell first.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace

from agp.game import Game

BLACK, WHITE = 0, 1
# Seat names + goals.  Ground truth (outside this module): igGameCenter's Quax
# rules page prints a coloured board -- "The left and right edges are colored
# white while the top and bottom edges are colored black ... White should
# connect the Left and Right edges and Black should connect the Top and Bottom
# edges", with "Starting with Black".  AbstractPlay's implementation agrees
# (its player 1 uses lineN/lineS).  selftest.py pins both names and both goals
# to hand-built positions, so swapping either constant fails the suite.
SEAT_NAMES = ("Black", "White")
SEAT_EDGES = ("top-bottom", "left-right")

ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGS = ("/", "\\")


def parse_cell(t: str) -> tuple[int, int]:
    c, r = t.split(",")
    return int(c), int(r)


def cell_name(cell: tuple[int, int]) -> str:
    return f"{cell[0]},{cell[1]}"


def algebraic(cell: tuple[int, int]) -> str:
    """Designer's / igGameCenter's notation: file letter + rank, rank 1 = row 0."""
    return f"{chr(97 + cell[0])}{cell[1] + 1}"


def endpoints(square: tuple[int, int], diag: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """The two cells a link joins.  Always returns the smaller-column cell first.

    A link lives in the 2x2 `square` whose BOTTOM-LEFT corner is `square`;
    "/" joins bottom-left to top-right, "\\" joins top-left to bottom-right.
    """
    sc, sr = square
    if diag == "/":
        return (sc, sr), (sc + 1, sr + 1)
    return (sc, sr + 1), (sc + 1, sr)


def link_move(square: tuple[int, int], diag: str) -> str:
    a, b = endpoints(square, diag)
    return f"{cell_name(a)}>{cell_name(b)}"


def link_of_move(move: str) -> tuple[tuple[int, int], str]:
    """Inverse of `link_move`: "c1,r1>c2,r2" -> (square, diag)."""
    a_s, b_s = move.split(">")
    a, b = parse_cell(a_s), parse_cell(b_s)
    square = (min(a[0], b[0]), min(a[1], b[1]))
    diag = "/" if (a[0] < b[0]) == (a[1] < b[1]) else "\\"
    return square, diag


@dataclass(frozen=True)
class QuaxState:
    size: int = 11
    pie: bool = True
    # (c, r) -> seat
    stones: dict = field(default_factory=dict)
    # (bottom-left corner of the 2x2 square) -> (seat, diag).  Keying links by
    # SQUARE (not by cell pair) makes the crossing rule structural: a square
    # physically holds one rhombic tile, so the crossing link is inexpressible.
    links: dict = field(default_factory=dict)
    to_move: int = BLACK
    winner: int | None = None
    ply: int = 0
    swapped: bool = False
    last: str | None = None


class Quax(Game):
    """Quax -- square-grid connection game with turn-costing diagonal links."""

    # ---------------------------------------------------------------- basics

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> QuaxState:
        o = options or {}
        size = int(o.get("size", 11))
        if size < 2:
            raise ValueError("Quax needs a board of at least 2x2")
        pie = str(o.get("pie", "on")) == "on"
        return QuaxState(size=size, pie=pie)

    def current_player(self, s: QuaxState) -> int:
        return s.to_move

    # ------------------------------------------------------------ move rules

    def _swap_available(self, s: QuaxState) -> bool:
        # The pie rule: White's very first turn, i.e. immediately after Black's
        # single opening move.  `ply` counts moves made, so ply == 1.
        return s.pie and s.ply == 1 and s.to_move == WHITE and not s.swapped

    def _moves(self, s: QuaxState) -> list[str]:
        if s.winner is not None:
            return []
        n = s.size
        moves = []
        for r in range(n):
            for c in range(n):
                if (c, r) not in s.stones:
                    moves.append(f"{c},{r}")
        mover = s.to_move
        for sr in range(n - 1):
            for sc in range(n - 1):
                if (sc, sr) in s.links:
                    continue          # the rhombic cell is already occupied
                for diag in DIAGS:
                    a, b = endpoints((sc, sr), diag)
                    if s.stones.get(a) == mover and s.stones.get(b) == mover:
                        moves.append(link_move((sc, sr), diag))
        if self._swap_available(s):
            moves.append("swap")
        return moves

    def legal_moves(self, s: QuaxState) -> list[str]:
        return self._moves(s)

    # --------------------------------------------------------- connectivity

    def _edges(self, s: QuaxState, seat: int) -> tuple[list, list]:
        """The seat's two target edges as cell lists (corners belong to both)."""
        n = s.size
        if seat == BLACK:                      # top and bottom rows
            return ([(c, n - 1) for c in range(n)], [(c, 0) for c in range(n)])
        return ([(0, r) for r in range(n)], [(n - 1, r) for r in range(n)])

    def _neighbours(self, s: QuaxState, seat: int) -> dict:
        """seat's connection graph: orthogonal adjacency + that seat's links."""
        adj = {cell: [] for cell, o in s.stones.items() if o == seat}
        for (c, r) in adj:
            for dc, dr in ORTHO:
                nb = (c + dc, r + dr)
                if s.stones.get(nb) == seat:
                    adj[(c, r)].append(nb)
        for square, (owner, diag) in s.links.items():
            if owner != seat:
                continue
            a, b = endpoints(square, diag)
            # A link can only have been placed between two of the owner's
            # stones, and stones are never removed, so both ends are present.
            adj[a].append(b)
            adj[b].append(a)
        return adj

    def connection_path(self, s: QuaxState, seat: int):
        """A path of `seat`'s stones joining their two edges, or None.

        Public helper (also used by render to highlight the winning chain), so
        selftest.py exercises it directly as well as through the win check.
        """
        adj = self._neighbours(s, seat)
        side_a, side_b = self._edges(s, seat)
        goal = {cell for cell in side_b if s.stones.get(cell) == seat}
        if not goal:
            return None
        prev = {}
        q = deque()
        for cell in side_a:
            if s.stones.get(cell) == seat and cell not in prev:
                prev[cell] = None
                q.append(cell)
        while q:
            cur = q.popleft()
            if cur in goal:
                path = []
                while cur is not None:
                    path.append(cur)
                    cur = prev[cur]
                path.reverse()
                return path
            for nb in adj[cur]:
                if nb not in prev:
                    prev[nb] = cur
                    q.append(nb)
        return None

    # ------------------------------------------------------------ transition

    def _transpose(self, s: QuaxState) -> QuaxState:
        """Reflect the position across the main diagonal AND swap ownership.

        Quax's move rules are invariant under transposition while the two goals
        are exchanged by it, so this maps a position to one of exactly equal
        value with the colours reversed -- which is what the pie rule needs
        given that this engine's seats have fixed goals.
        """
        stones = {(r, c): 1 - o for (c, r), o in s.stones.items()}
        links = {(sr, sc): (1 - owner, diag)
                 for (sc, sr), (owner, diag) in s.links.items()}
        return replace(s, stones=stones, links=links)

    def apply_move(self, s: QuaxState, move: str, rng=None) -> QuaxState:
        if s.winner is not None:
            raise ValueError("game is over")
        mover = s.to_move
        if move == "swap":
            if not self._swap_available(s):
                raise ValueError("swap is not available")
            t = self._transpose(s)
            ns = replace(t, to_move=1 - mover, ply=s.ply + 1, swapped=True,
                         last="swap")
            # The stone changed hands, so the seat that could newly have a
            # connection is WHITE.  (One stone can never join two opposite
            # edges of a >=2 board, so this can never fire; asserted in
            # selftest.py over every board size.)
            check = WHITE
        elif ">" in move:
            square, diag = link_of_move(move)
            a, b = endpoints(square, diag)
            n = s.size
            if not (0 <= square[0] < n - 1 and 0 <= square[1] < n - 1):
                raise ValueError(f"link off the board: {move}")
            if link_move(square, diag) != move:
                raise ValueError(f"link must be written {link_move(square, diag)}")
            if square in s.links:
                raise ValueError(f"the rhombic cell at {square} is already used")
            if s.stones.get(a) != mover or s.stones.get(b) != mover:
                raise ValueError(f"both ends of {move} must be your own stones")
            links = dict(s.links)
            links[square] = (mover, diag)
            ns = replace(s, links=links, to_move=1 - mover, ply=s.ply + 1,
                         last=move)
            check = mover
        else:
            cell = parse_cell(move)
            if not (0 <= cell[0] < s.size and 0 <= cell[1] < s.size):
                raise ValueError(f"cell off the board: {move}")
            if cell in s.stones:
                raise ValueError(f"{move} is occupied")
            stones = dict(s.stones)
            stones[cell] = mover
            ns = replace(s, stones=stones, to_move=1 - mover, ply=s.ply + 1,
                         last=move)
            check = mover
        if self.connection_path(ns, check) is not None:
            ns = replace(ns, winner=check)
        return ns

    # -------------------------------------------------------------- terminal

    def is_terminal(self, s: QuaxState) -> bool:
        # `not self._moves(s)` means the board is full AND every 2x2 square
        # either holds a link or has no monochromatic diagonal left.  Quax is
        # drawless, so such a position always already contains a winning chain
        # and the game ended earlier -- the branch is provably dead (see
        # rules.md and selftest.py's exhaustive check over full positions).
        return s.winner is not None or not self._moves(s)

    def returns(self, s: QuaxState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]          # honest draw; provably unreachable
        return [1.0, -1.0] if s.winner == BLACK else [-1.0, 1.0]

    # ------------------------------------------------------------ (de)serial

    def serialize(self, s: QuaxState) -> dict:
        return {
            "size": s.size,
            "pie": s.pie,
            "stones": {cell_name(k): v for k, v in s.stones.items()},
            "links": {cell_name(k): [v[0], v[1]] for k, v in s.links.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "swapped": s.swapped,
            "last": s.last,
        }

    def deserialize(self, d: dict) -> QuaxState:
        return QuaxState(
            size=int(d["size"]),
            pie=bool(d["pie"]),
            stones={parse_cell(k): int(v) for k, v in d["stones"].items()},
            links={parse_cell(k): (int(v[0]), v[1]) for k, v in d["links"].items()},
            to_move=int(d["to_move"]),
            winner=None if d["winner"] is None else int(d["winner"]),
            ply=int(d["ply"]),
            swapped=bool(d["swapped"]),
            last=d["last"],
        )

    # ---------------------------------------------------------------- render

    LINK_FILL = ("#e06b6b", "#6b8fe0")     # seat 0 / seat 1, matching colors.js

    def describe_move(self, s: QuaxState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if ">" in move:
            square, diag = link_of_move(move)
            a, b = endpoints(square, diag)
            return f"{algebraic(a)}-{algebraic(b)}"
        return algebraic(parse_cell(move))

    def render(self, s: QuaxState, perspective=None) -> dict:
        n = s.size
        pieces = [{"cell": cell_name(cell), "owner": o}
                  for cell, o in sorted(s.stones.items())]
        overlay = []
        for square in sorted(s.links):
            owner, diag = s.links[square]
            a, b = endpoints(square, diag)
            overlay.append([[a[0], a[1]], [b[0], b[1]], self.LINK_FILL[owner]])
        # Edge tints: Black's top/bottom rows, White's left/right columns, and
        # the four corners in a blend (a corner belongs to BOTH its edges).
        tints = {}
        for c in range(n):
            tints[f"{c},0"] = "#3a2222"
            tints[f"{c},{n - 1}"] = "#3a2222"
        for r in range(n):
            tints[f"0,{r}"] = "#22223a"
            tints[f"{n - 1},{r}"] = "#22223a"
        for c in (0, n - 1):
            for r in (0, n - 1):
                tints[f"{c},{r}"] = "#33223a"
        highlights = []
        if s.winner is not None:
            for cell in self.connection_path(s, s.winner) or ():
                highlights.append({"cell": cell_name(cell), "kind": "goal"})
        elif s.last and s.last != "swap":
            for part in s.last.split(">"):
                highlights.append({"cell": part, "kind": "last-move"})
        if s.winner is not None:
            cap = f"{SEAT_NAMES[s.winner]} wins (connected {SEAT_EDGES[s.winner]})"
        else:
            cap = (f"{SEAT_NAMES[s.to_move]} to move "
                   f"(connect {SEAT_EDGES[s.to_move]})")
            if self._swap_available(s):
                cap += " - or swap"
        spec = {
            "board": {"type": "square", "width": n, "height": n,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
            "actionNames": {"swap": "Swap (pie rule)"},
        }
        if overlay:
            spec["board"]["overlay"] = overlay
        return spec
