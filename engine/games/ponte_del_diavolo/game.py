"""Ponte del Diavolo ("Devil's Bridge"), Martin Ebel 2007 (Hans im Glueck / Rio
Grande Games).

A territory / connection game on a plain 10x10 grid. Two players place coloured
island squares ("tiles") and gray bridges.

On your turn you do ONE of:
  * place TWO tiles of your colour on two empty, un-blocked squares, or
  * place ONE bridge connecting two of your own tiles.

An **island** is exactly FOUR orthogonally-connected tiles of one colour (never
5+). A **sandbank** is a group of 1-3 such tiles. An island may never touch
another same-colour island or sandbank, *even diagonally* (the "touching rule").
Sandbanks of the same colour may touch each other diagonally, and tiles of
different colours may touch freely.

A **bridge** joins two same-colour tiles that are a straight orthogonal step,
a straight diagonal step, or a knight's-move apart -- i.e. spanning ONE (ortho /
diagonal) or TWO (knight) empty water squares. The spanned water must be empty,
a bridge may not cross a tile or another bridge, and each tile supports at most
one bridge. Bridges link islands (and sandbanks) into scoring groups.

Scoring: each maximal group of islands connected by bridges scores the
triangular number of its island count (1 island = 1, 2 = 3, 3 = 6, 4 = 10, ...,
n*(n+1)/2). Sandbanks score nothing. Highest total wins; ties break on most
islands, then most bridges, then a shared victory (draw).

The turn's two-tile placement is modelled as TWO sub-moves by the same player
(place first tile, then second tile), so the generic click-to-move UI does one
click per tile. A bridge is the ">"-path "a>b" between two of your tiles; a
placement is a single empty cell "c,r"; "pass" ends your turn (offered only when
you cannot place two tiles). Cells are "col,row" with col,row in 0..9.

Deviation from the published game: the optional Alex Randolph pie / colour-swap
start rule is OMITTED for simplicity -- player 0 (Light) simply moves first.
Component limits are enforced (40 tiles per colour, 15 bridges total).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

LIGHT, DARK = 0, 1
NAMES = {LIGHT: "Light", DARK: "Dark"}
SIZE = 10
MAX_TILES = 40           # per colour (80 island squares, 2 colours)
MAX_BRIDGES = 15         # total gray bridges, shared pool
PLY_CAP = 1000           # safety net; the game ends well before this

ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
NEIGH8 = ORTH + DIAG

# offsets (b - a) for the two tiles a bridge may connect
BRIDGE_OFFSETS = [
    (2, 0), (-2, 0), (0, 2), (0, -2),            # orthogonal, 1 gap
    (2, 2), (2, -2), (-2, 2), (-2, -2),          # diagonal, 1 gap
    (1, 2), (1, -2), (-1, 2), (-1, -2),          # knight, 2 gaps
    (2, 1), (2, -1), (-2, 1), (-2, -1),
]


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _sig(v):
    return (v > 0) - (v < 0)


def _bridge_cells(a, b):
    """The water square(s) a bridge from tile a to tile b spans (must be empty).
    Returns None if a->b is not a legal bridge shape."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    adx, ady = abs(dx), abs(dy)
    sx, sy = _sig(dx), _sig(dy)
    if (adx, ady) in ((2, 0), (0, 2), (2, 2)):
        return [(ax + dx // 2, ay + dy // 2)]
    if (adx, ady) == (1, 2):
        return [(ax, ay + sy), (ax + sx, ay + sy)]
    if (adx, ady) == (2, 1):
        return [(ax + sx, ay), (ax + sx, ay + sy)]
    return None


def _crosses(s1, s2):
    """Do open segments s1, s2 properly intersect? Shared endpoints don't count."""
    (a, b), (c, d) = s1, s2
    if {a, b} & {c, d}:
        return False

    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2 = orient(a, b, c), orient(a, b, d)
    o3, o4 = orient(c, d, a), orient(c, d, b)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def _group_of(board, start, color, limit=None):
    """Orthogonally-connected same-colour component containing `start`.
    Stops early once size exceeds `limit` (if given)."""
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ORTH:
            nb = (x + dx, y + dy)
            if nb not in seen and board.get(nb) == color:
                seen.add(nb)
                stack.append(nb)
                if limit is not None and len(seen) > limit:
                    return seen
    return seen


def _single_ok(board, color, cell):
    """Is placing one `color` tile on empty `cell` legal? (board is the position
    BEFORE the placement, which is assumed already legal.)"""
    board2 = dict(board)
    board2[cell] = color
    g = _group_of(board2, cell, color, limit=4)
    if len(g) > 4:                       # would create a group of 5+
        return False
    if len(g) == 4:                      # cell completes an island
        for (x, y) in g:
            for dx, dy in NEIGH8:
                nb = (x + dx, y + dy)
                if nb not in g and board2.get(nb) == color:
                    return False         # island touches another same-colour tile
    # cell (in whatever group) must not sit next to an EXISTING same-colour island
    for dx, dy in NEIGH8:
        nb = (cell[0] + dx, cell[1] + dy)
        if nb not in g and board.get(nb) == color:
            gg = _group_of(board2, nb, color, limit=4)
            if len(gg) == 4:
                return False
    return True


def _groups(board, color):
    """All orthogonal same-colour components (list of frozensets)."""
    out = []
    seen = set()
    for pos, v in board.items():
        if v != color or pos in seen:
            continue
        g = _group_of(board, pos, color)
        seen |= g
        out.append(frozenset(g))
    return out


@dataclass
class PonteState:
    board: dict = field(default_factory=dict)          # (c,r) -> LIGHT/DARK
    bridges: list = field(default_factory=list)        # list of (a, b), a<b, a,b tiles
    to_move: int = LIGHT
    phase: int = 0                                      # 0 = start of turn, 1 = second tile
    pending: object = None                             # first tile placed this turn
    light_passed: bool = False
    ended: bool = False
    ply: int = 0


class PonteDelDiavolo(Game):
    uid = "ponte_del_diavolo"
    name = "Ponte del Diavolo"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return PonteState()

    def current_player(self, s):
        return s.to_move

    # ---- geometry helpers -------------------------------------------------

    def _blocked(self, s):
        """Water squares sitting under a bridge (no tile may be placed there)."""
        out = set()
        for (a, b) in s.bridges:
            for c in _bridge_cells(a, b) or []:
                out.add(c)
        return out

    def _legal_singles(self, board, blocked, color):
        return [(c, r) for r in range(SIZE) for c in range(SIZE)
                if (c, r) not in board and (c, r) not in blocked
                and _single_ok(board, color, (c, r))]

    def _has_second(self, board, color, singles, t1):
        """After placing t1, does a legal second tile exist?"""
        far = [t2 for t2 in singles if t2 != t1
               and max(abs(t2[0] - t1[0]), abs(t2[1] - t1[1])) > 1]
        if far:
            return True                       # a distant legal single is unaffected by t1
        b2 = dict(board)
        b2[t1] = color
        for t2 in singles:
            if t2 != t1 and _single_ok(b2, color, t2):
                return True
        return False

    def _legal_bridges(self, s, color):
        board = s.board
        blocked = self._blocked(s)
        bridged = {t for (a, b) in s.bridges for t in (a, b)}
        segs = list(s.bridges)
        found = set()
        for a, v in board.items():
            if v != color or a in bridged:
                continue
            for dx, dy in BRIDGE_OFFSETS:
                b = (a[0] + dx, a[1] + dy)
                if board.get(b) != color or b in bridged:
                    continue
                key = (a, b) if a <= b else (b, a)
                if key in found:
                    continue
                cells = _bridge_cells(a, b)
                if cells is None:
                    continue
                if any(c in board or c in blocked for c in cells):
                    continue
                if any(_crosses((a, b), seg) for seg in segs):
                    continue
                found.add(key)
        return sorted(found)

    # ---- moves ------------------------------------------------------------

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        color = s.to_move
        blocked = self._blocked(s)

        if s.phase == 1:                      # must place the second tile
            return [f"{c},{r}" for (c, r) in self._legal_singles(s.board, blocked, color)]

        singles = self._legal_singles(s.board, blocked, color)
        tiles_left = MAX_TILES - sum(1 for v in s.board.values() if v == color)
        firsts = []
        if tiles_left >= 2:
            firsts = [t1 for t1 in singles if self._has_second(s.board, color, singles, t1)]

        moves = [f"{c},{r}" for (c, r) in firsts]
        if len(s.bridges) < MAX_BRIDGES:
            for (a, b) in self._legal_bridges(s, color):
                moves.append(f"{a[0]},{a[1]}>{b[0]},{b[1]}")
                moves.append(f"{b[0]},{b[1]}>{a[0]},{a[1]}")
        if not firsts:                        # cannot place two tiles -> may pass
            moves.append("pass")
        return moves

    def _end_turn(self, board, bridges, mover, light_passed, ply):
        # After Light passes, Dark takes exactly one more turn, then the game ends.
        ended = light_passed and mover == DARK
        return PonteState(board=board, bridges=bridges, to_move=1 - mover,
                          phase=0, pending=None, light_passed=light_passed,
                          ended=ended, ply=ply)

    def apply_move(self, s, move, rng=None):
        color = s.to_move
        board = dict(s.board)
        bridges = list(s.bridges)
        ply = s.ply + 1

        if move == "pass":
            if color == DARK:                 # Dark passes -> game ends immediately
                return PonteState(board=board, bridges=bridges, to_move=LIGHT,
                                  phase=0, pending=None,
                                  light_passed=s.light_passed, ended=True, ply=ply)
            # Light passes -> hand Dark one final turn
            return PonteState(board=board, bridges=bridges, to_move=DARK,
                              phase=0, pending=None, light_passed=True,
                              ended=False, ply=ply)

        if ">" in move:                       # a bridge (a full turn)
            a_s, b_s = move.split(">")
            a, b = _cell(a_s), _cell(b_s)
            key = (a, b) if a <= b else (b, a)
            bridges.append(key)
            return self._end_turn(board, bridges, color, s.light_passed, ply)

        cell = _cell(move)                    # a tile placement
        board[cell] = color
        if s.phase == 0:
            return PonteState(board=board, bridges=bridges, to_move=color,
                              phase=1, pending=cell, light_passed=s.light_passed,
                              ended=False, ply=ply)
        return self._end_turn(board, bridges, color, s.light_passed, ply)

    def is_terminal(self, s):
        return s.ended or s.ply >= PLY_CAP

    # ---- scoring ----------------------------------------------------------

    def _tally(self, s, color):
        """Return (score, island_count, bridge_count) for `color`."""
        groups = _groups(s.board, color)
        idx = {}
        for i, g in enumerate(groups):
            for cell in g:
                idx[cell] = i
        parent = list(range(len(groups)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i, j):
            parent[find(i)] = find(j)

        bridge_count = 0
        for (a, b) in s.bridges:
            if s.board.get(a) == color and s.board.get(b) == color:
                bridge_count += 1
                if a in idx and b in idx:
                    union(idx[a], idx[b])

        islands_in = {}                       # root -> island count
        for i, g in enumerate(groups):
            if len(g) == 4:
                islands_in[find(i)] = islands_in.get(find(i), 0) + 1
        score = sum(n * (n + 1) // 2 for n in islands_in.values())
        island_count = sum(1 for g in groups if len(g) == 4)
        return score, island_count, bridge_count

    def returns(self, s):
        l = self._tally(s, LIGHT)
        d = self._tally(s, DARK)
        if l > d:
            return [1.0, -1.0]
        if d > l:
            return [-1.0, 1.0]
        return [0.0, 0.0]                     # shared victory (tie on all criteria)

    # ---- serialization ----------------------------------------------------

    def serialize(self, s):
        return {
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "bridges": [[list(a), list(b)] for (a, b) in s.bridges],
            "to_move": s.to_move,
            "phase": s.phase,
            "pending": (list(s.pending) if s.pending is not None else None),
            "light_passed": s.light_passed,
            "ended": s.ended,
            "ply": s.ply,
        }

    def deserialize(self, d):
        bridges = []
        for a, b in d.get("bridges", []):
            a, b = tuple(a), tuple(b)
            bridges.append((a, b) if a <= b else (b, a))
        pend = d.get("pending")
        return PonteState(
            board={_cell(k): v for k, v in d["board"].items()},
            bridges=bridges,
            to_move=d["to_move"],
            phase=d.get("phase", 0),
            pending=(tuple(pend) if pend is not None else None),
            light_passed=d.get("light_passed", False),
            ended=d.get("ended", False),
            ply=d.get("ply", 0),
        )

    # ---- notation ---------------------------------------------------------

    def describe_move(self, s, move):
        name = NAMES[s.to_move]
        if move == "pass":
            return f"{name} passes"
        if ">" in move:
            a, b = move.split(">")
            return f"{name} bridge {a}-{b}"
        lead = "" if s.phase == 1 else "+"     # phase-1 = the turn's 2nd tile
        return f"{name} tile {move}{lead}"

    # ---- rendering --------------------------------------------------------

    def render(self, s, perspective=None):
        pieces = [{"cell": f"{c},{r}", "owner": v} for (c, r), v in s.board.items()]
        if s.pending is not None:
            pieces_last = f"{s.pending[0]},{s.pending[1]}"
        else:
            pieces_last = None

        # bridges as gray overlay lines drawn over the cells
        overlay = []
        for (a, b) in s.bridges:
            overlay.append([[a[0], a[1]], [b[0], b[1]], "#5b5b66"])

        # faint tint on completed islands, in each owner's colour
        tints = {}
        tint_col = {LIGHT: "#5a4a2a", DARK: "#2a3a5a"}
        for color in (LIGHT, DARK):
            for g in _groups(s.board, color):
                if len(g) == 4:
                    for (c, r) in g:
                        tints[f"{c},{r}"] = tint_col[color]

        highlights = []
        if pieces_last is not None:
            highlights.append({"cell": pieces_last, "kind": "last-move"})

        ls, li, lb = self._tally(s, LIGHT)
        ds, di, db = self._tally(s, DARK)
        score_txt = f"Light {ls} ({li}i/{lb}b) — Dark {ds} ({di}i/{db}b)"
        if self.is_terminal(s):
            lt, dt = (ls, li, lb), (ds, di, db)
            res = "Light wins" if lt > dt else "Dark wins" if dt > lt else "Shared victory"
            caption = f"{res}  ·  {score_txt}"
        else:
            turn = NAMES[s.to_move]
            step = "  (2nd tile)" if s.phase == 1 else ""
            caption = f"{turn} to move{step}  ·  {score_txt}"

        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE,
                      "overlay": overlay, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
