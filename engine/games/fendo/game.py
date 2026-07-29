"""Fendo — Dieter Stein, 2014.

A 7x7 board. Each player owns 7 pieces and starts with one of them on the middle
cell of their own side (seat 0 on a4, seat 1 on g4); the other six wait in stock.
Fences are laid on the edges *between* orthogonally adjacent cells and belong to
neither player.

Each turn a player must either

  (a) select one of their pieces **in the open area**, optionally slide it
      rook-wise (any distance, at most one right-angle turn, crossing neither a
      piece nor a fence), and then build a fence on one of the empty sides of the
      cell it ends on; or
  (b) enter a new piece from stock onto an empty cell that is exactly one such
      move away from one of their pieces in the open area (no fence is built).

An *area* is a connected region of cells (connectivity is broken by fences and by
the board edge). An area with exactly one piece in it is **closed** and scores its
whole size for that piece's owner; an area with two or more pieces is **open**; an
area with none is **empty**. A fence may never create an empty area nor leave more
than one open area. The game ends when no open area remains; the larger total of
closed-area cells wins.

Move strings (platform notation):
  "c1,r1>c2,r2=FENCE_N"  move then fence on side N of the destination
  "c,r>c,r=FENCE_N"      stay put and fence on side N of that cell
  "P@c,r"                enter a piece from stock (reserve drop)
  "pass"                 no action available

A fence move is ALWAYS a two-cell path, even when the piece does not move: the
web click-router matches a *complete* move before it tries to extend a path, so a
one-cell "c,r=FENCE_N" would swallow the click that selects the piece and make
move-then-fence unreachable in the UI.  A BARE "c,r" is never legal either (it
would collide with stock entry) — entering a piece uses the drop channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agp.game import Game

SIZE = 7
NCELLS = SIZE * SIZE
EMPTY = -1

# Compass directions, in (dc, dr).  r increases upward (north).
DIRS = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
DIR_ORDER = ("N", "E", "S", "W")

# Two players' home cells: seat 0 on the west edge, seat 1 on the east edge,
# both on the middle rank (a4 / g4 — matches the designer's diagram and the
# AbstractPlay reference implementation).
START = ((0, SIZE // 2), (SIZE - 1, SIZE // 2))

# Every fence lives on one of these two edge families:
#   ("h", c, r) — the edge between (c, r) and (c, r+1)   [north side of (c,r)]
#   ("v", c, r) — the edge between (c, r) and (c+1, r)   [east  side of (c,r)]
# There are 7*6 of each, so 84 internal edges in total — which is also the hard
# bound on how long a game can run (see rules.md, "Termination").
MAX_FENCES = 2 * SIZE * (SIZE - 1)


def idx(c: int, r: int) -> int:
    return r * SIZE + c


def cell_name(c: int, r: int) -> str:
    return f"{c},{r}"


def parse_cell(text: str) -> tuple[int, int]:
    c, r = text.split(",")
    return int(c), int(r)


def algebraic(c: int, r: int) -> str:
    """Designer/AbstractPlay style name, used only in the move log."""
    return f"{chr(ord('a') + c)}{r + 1}"


def edge_key(c: int, r: int, d: str) -> Optional[tuple[str, int, int]]:
    """The canonical fence key for side ``d`` of cell ``(c, r)``, or None if that
    side is the board's outer boundary (which is already a solid wall)."""
    if d == "N":
        return ("h", c, r) if r + 1 < SIZE else None
    if d == "S":
        return ("h", c, r - 1) if r - 1 >= 0 else None
    if d == "E":
        return ("v", c, r) if c + 1 < SIZE else None
    if d == "W":
        return ("v", c - 1, r) if c - 1 >= 0 else None
    raise ValueError(d)


# Precomputed geometry: STEP[i][d] = (neighbour index, fence key) for direction
# ``d`` out of cell ``i``, or None when that side is the board rim.  Pure speed —
# it says exactly what ``edge_key`` says.
STEP = [
    {d: (idx(i % SIZE + DIRS[d][0], i // SIZE + DIRS[d][1]),
         edge_key(i % SIZE, i // SIZE, d))
     for d in DIR_ORDER if edge_key(i % SIZE, i // SIZE, d) is not None}
    for i in range(NCELLS)
]
# Perpendicular directions, for the single allowed right-angle turn.
PERP = {"N": ("E", "W"), "S": ("E", "W"), "E": ("N", "S"), "W": ("N", "S")}


@dataclass(frozen=True)
class FState:
    board: tuple          # NCELLS entries: EMPTY or the owning seat (0/1)
    fences: frozenset     # of ("h"|"v", c, r)
    stock: tuple          # pieces still off-board, per seat
    to_move: int
    passes: int           # consecutive passes immediately before now
    over: bool
    last: Optional[str] = None   # last move string, for the render highlight


class Fendo(Game):
    """Fendo (Dieter Stein, 2014)."""

    @property
    def num_players(self) -> int:
        return 2

    # ---------------- setup ----------------

    def initial_state(self, options: Optional[dict] = None, rng=None) -> FState:
        board = [EMPTY] * NCELLS
        for seat, (c, r) in enumerate(START):
            board[idx(c, r)] = seat
        return FState(
            board=tuple(board),
            fences=frozenset(),
            stock=(SIZE - 1, SIZE - 1),
            to_move=0,
            passes=0,
            over=False,
            last=None,
        )

    def current_player(self, state: FState) -> int:
        return state.to_move

    # ---------------- geometry ----------------

    @staticmethod
    def blocked(fences, c: int, r: int, d: str) -> bool:
        """True if a piece on (c, r) may not step in direction ``d`` — off the
        board, or a fence on that side.  (``STEP`` is the precomputed form of
        exactly this test; kept as the plain statement of it.)"""
        k = edge_key(c, r, d)
        return k is None or k in fences

    @classmethod
    def areas(cls, board, fences) -> list[tuple[list[int], list[int]]]:
        """Partition the board into connected areas.  Returns a list of
        ``(cells, owners)`` where ``owners`` lists the seat of every piece in the
        area (so ``len(owners)`` is 0 = empty, 1 = closed, >=2 = open)."""
        seen = [False] * NCELLS
        out = []
        for start in range(NCELLS):
            if seen[start]:
                continue
            seen[start] = True
            stack = [start]
            cells = []
            owners = []
            while stack:
                i = stack.pop()
                cells.append(i)
                if board[i] != EMPTY:
                    owners.append(board[i])
                for j, k in STEP[i].values():
                    if not seen[j] and k not in fences:
                        seen[j] = True
                        stack.append(j)
            out.append((cells, owners))
        return out

    @classmethod
    def open_area(cls, board, fences) -> Optional[set]:
        """The single open area (>=2 pieces), or None if there is none."""
        for cells, owners in cls.areas(board, fences):
            if len(owners) >= 2:
                return set(cells)
        return None

    @classmethod
    def reachable(cls, board, fences, c: int, r: int) -> set:
        """Every empty cell a piece on (c, r) can slide to: rook-wise, any
        distance, with at most ONE right-angle turn, crossing neither a piece nor
        a fence.  Excludes the piece's own cell."""
        out = set()
        start = idx(c, r)
        for d1 in DIR_ORDER:
            # first leg (length >= 1)
            i = start
            leg1 = []
            while True:
                step = STEP[i].get(d1)
                if step is None or step[1] in fences:
                    break
                i = step[0]
                if board[i] != EMPTY:
                    break
                leg1.append(i)
                out.add(i)
            # second leg, perpendicular (length >= 1) — the single allowed turn
            for m in leg1:
                for d2 in PERP[d1]:
                    i = m
                    while True:
                        step = STEP[i].get(d2)
                        if step is None or step[1] in fences:
                            break
                        i = step[0]
                        if board[i] != EMPTY:
                            break
                        out.add(i)
        return out

    # ---------------- move generation ----------------

    @classmethod
    def _targets(cls, board, fences, seat: int, open_cells: set) -> dict:
        """{piece cell index: set of destination cell indices}.  A piece may
        always stay where it is, so its own cell is always in its target set."""
        res = {}
        for i in sorted(open_cells):
            if board[i] != seat:
                continue
            c, r = i % SIZE, i // SIZE
            dests = {j for j in cls.reachable(board, fences, c, r) if j in open_cells}
            dests.add(i)
            res[i] = dests
        return res

    @classmethod
    def fence_ok(cls, board, fences, key) -> bool:
        """**The rule, stated globally**: after adding fence ``key`` there must be
        no empty area anywhere and at most one open area.  ``legal_moves`` uses
        the equivalent local form below (this whole-board version is kept as the
        readable definition and is cross-checked against it in ``selftest.py``)."""
        nf = fences | {key}
        n_open = 0
        for _cells, owners in cls.areas(board, nf):
            if not owners:
                return False
            if len(owners) >= 2:
                n_open += 1
                if n_open > 1:
                    return False
        return True

    @staticmethod
    def _split_ok(fences, key, open_cells: set, x: int, y: int,
                  pieces: set) -> bool:
        """Local form of ``fence_ok``.  A new fence always lies *inside* the open
        area (its two cells `x`,`y` were connected, and `x` holds the moving
        piece), so no other area can change: either the open area survives whole,
        or it splits in two and each part must hold at least one piece with at
        most one part holding two or more.  ``pieces`` = the piece cells of the
        open area after the move."""
        seen = {x}
        stack = [x]
        cnt = 1 if x in pieces else 0
        while stack:
            i = stack.pop()
            for j, k in STEP[i].values():
                if j in seen or k == key or k in fences or j not in open_cells:
                    continue
                if j == y:
                    return True                     # still connected: no split
                seen.add(j)
                stack.append(j)
                if j in pieces:
                    cnt += 1
        other = len(pieces) - cnt
        return cnt >= 1 and other >= 1 and (cnt == 1 or other == 1)

    def legal_moves(self, state: FState) -> list[str]:
        if state.over:
            return []
        board, fences = state.board, state.fences
        open_cells = self.open_area(board, fences)
        if open_cells is None:
            return []          # terminal; apply_move never leaves such a state live
        seat = state.to_move
        targets = self._targets(board, fences, seat, open_cells)
        base_pieces = {i for i in open_cells if board[i] != EMPTY}

        moves = []

        # (b) enter a piece from stock
        if state.stock[seat] > 0:
            entries = set()
            for dests in targets.values():
                entries |= dests
            for j in sorted(entries):
                if board[j] == EMPTY:
                    moves.append(f"P@{cell_name(j % SIZE, j // SIZE)}")

        # (a) (optionally move a piece and) build a fence
        for i, dests in sorted(targets.items()):
            frm = cell_name(i % SIZE, i // SIZE)
            for j in sorted(dests):
                pieces = base_pieces if i == j else (base_pieces - {i}) | {j}
                to = cell_name(j % SIZE, j // SIZE)
                for d in DIR_ORDER:
                    step = STEP[j].get(d)
                    if step is None or step[1] in fences:
                        continue
                    if not self._split_ok(fences, step[1], open_cells,
                                          j, step[0], pieces):
                        continue
                    # Always a TWO-cell path, even when the piece stays put
                    # ("c,r>c,r"): a one-cell path would be consumed by the web
                    # click-router as the piece-selection click, making
                    # move-then-fence unreachable.  See rules.md.
                    moves.append(f"{frm}>{to}=FENCE_{d}")

        if not moves:
            moves.append("pass")
        return moves

    # ---------------- move application ----------------

    @staticmethod
    def _parse(move: str):
        """-> ('pass',) | ('enter', j) | ('fence', i, j, dir)"""
        if move == "pass":
            return ("pass",)
        if move.startswith("P@"):
            c, r = parse_cell(move[2:])
            return ("enter", idx(c, r))
        path, _, choice = move.partition("=")
        if not choice.startswith("FENCE_"):
            raise ValueError(f"bad move {move!r}")
        d = choice[len("FENCE_"):]
        if d not in DIRS:
            raise ValueError(f"bad fence side in {move!r}")
        parts = path.split(">")
        # A fence move is ALWAYS a two-cell path; "from>from" = the piece stays
        # put.  A one-cell path is rejected on purpose (see legal_moves).
        if len(parts) != 2:
            raise ValueError(f"bad move {move!r}")
        i = idx(*parse_cell(parts[0]))
        j = idx(*parse_cell(parts[1]))
        return ("fence", i, j, d)

    def apply_move(self, state: FState, move: str, rng=None) -> FState:
        if state.over:
            raise ValueError("game is over")
        kind = self._parse(move)
        seat = state.to_move
        board = list(state.board)
        fences = state.fences
        stock = list(state.stock)
        passes = state.passes

        if kind[0] == "pass":
            passes += 1
        elif kind[0] == "enter":
            j = kind[1]
            if stock[seat] <= 0 or board[j] != EMPTY:
                raise ValueError(f"illegal entry {move!r}")
            board[j] = seat
            stock[seat] -= 1
            passes = 0
        else:
            _, i, j, d = kind
            board[i] = EMPTY
            board[j] = seat
            key = edge_key(j % SIZE, j // SIZE, d)
            fences = fences | {key}
            passes = 0

        board = tuple(board)
        # The game ends when no open area is left, or on two consecutive passes.
        over = passes >= 2 or self.open_area(board, fences) is None
        return FState(
            board=board,
            fences=fences,
            stock=tuple(stock),
            to_move=1 - seat,
            passes=passes,
            over=over,
            last=move,
        )

    # ---------------- results ----------------

    def is_terminal(self, state: FState) -> bool:
        return state.over

    @classmethod
    def scores(cls, state: FState) -> tuple[int, int]:
        """Cells of closed areas owned by each seat.  Cells still in the open
        area (only possible after a double pass) and cells of empty areas (which
        the fence rule makes unreachable) score for nobody."""
        sc = [0, 0]
        for cells, owners in cls.areas(state.board, state.fences):
            if len(owners) == 1:
                sc[owners[0]] += len(cells)
        return sc[0], sc[1]

    def returns(self, state: FState) -> list[float]:
        if not state.over:
            return [0.0, 0.0]
        a, b = self.scores(state)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, state: FState) -> list[float]:
        a, b = self.scores(state)
        v = (a - b) / float(NCELLS)
        return [v, -v]

    # ---------------- persistence ----------------

    def serialize(self, state: FState) -> dict:
        return {
            "board": list(state.board),
            "fences": sorted([k[0], k[1], k[2]] for k in state.fences),
            "stock": list(state.stock),
            "to_move": state.to_move,
            "passes": state.passes,
            "over": state.over,
            "last": state.last,
        }

    def deserialize(self, data: dict) -> FState:
        return FState(
            board=tuple(data["board"]),
            fences=frozenset((k[0], int(k[1]), int(k[2])) for k in data["fences"]),
            stock=tuple(data["stock"]),
            to_move=int(data["to_move"]),
            passes=int(data["passes"]),
            over=bool(data["over"]),
            last=data.get("last"),
        )

    # ---------------- presentation ----------------

    def describe_move(self, state: FState, move: str) -> str:
        kind = self._parse(move)
        if kind[0] == "pass":
            return "pass"
        if kind[0] == "enter":
            j = kind[1]
            return f"enter {algebraic(j % SIZE, j // SIZE)}"
        _, i, j, d = kind
        to = algebraic(j % SIZE, j // SIZE)
        if i == j:
            return f"{to} stays, fence {d}"
        return f"{algebraic(i % SIZE, i // SIZE)}-{to}, fence {d}"

    def render(self, state: FState, perspective: Optional[int] = None) -> dict:
        pieces = []
        for i, v in enumerate(state.board):
            if v != EMPTY:
                pieces.append({"cell": cell_name(i % SIZE, i // SIZE), "owner": v})

        fh, fv = [], []
        for kind, c, r in sorted(state.fences):
            (fh if kind == "h" else fv).append([c, r])

        # Shade each closed area in its owner's colour so the territory reads.
        tints = {}
        for cells, owners in self.areas(state.board, state.fences):
            if len(owners) == 1:
                col = ("#5a2222", "#1e2f5a")[owners[0]]
                for i in cells:
                    tints[cell_name(i % SIZE, i // SIZE)] = col

        highlights = []
        if state.last and state.last != "pass":
            kind = self._parse(state.last)
            if kind[0] == "enter":
                j = kind[1]
                highlights.append({"cell": cell_name(j % SIZE, j // SIZE),
                                   "kind": "last-move"})
            else:
                _, i, j, _d = kind
                for k in ({i, j} if i != j else {j}):
                    highlights.append({"cell": cell_name(k % SIZE, k // SIZE),
                                       "kind": "last-move"})

        a, b = self.scores(state)
        if state.over:
            if a > b:
                caption = f"Red wins {a}-{b}"
            elif b > a:
                caption = f"Blue wins {b}-{a}"
            else:
                caption = f"Draw {a}-{b}"
        else:
            caption = (f"{('Red', 'Blue')[state.to_move]} to move — "
                       f"closed area {a}-{b}")

        spec = {
            "board": {
                "type": "square", "width": SIZE, "height": SIZE,
                "fences": {"h": fh, "v": fv},
                "tints": tints,
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "reserve": {
                str(p): {"P": n} for p, n in enumerate(state.stock) if n > 0
            },
            "choiceTitle": "Place a fence",
            "choiceNames": {
                "FENCE_N": "Fence: north side",
                "FENCE_S": "Fence: south side",
                "FENCE_E": "Fence: east side",
                "FENCE_W": "Fence: west side",
            },
        }
        return spec
