"""TwixT (Alex Randolph, 1962) -- the classic peg-and-bridge connection game.

Each turn a player adds a peg to an empty hole. A new peg automatically links to
every friendly peg a knight's-move away, **unless** the link would cross a bridge
already on the board (bridges of either colour). Red links the top and bottom
edges; Black links the left and right edges; first to connect their two sides
wins. Unlike Hex, TwixT can draw (a full board with no connection).

Red owns the top/bottom border rows and may not play the left/right border
columns; Black owns the left/right columns and may not play the top/bottom rows;
the four corner holes belong to no one. Holes are "c,r" with c,r in 0..size-1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

RED, BLACK = 0, 1
KNIGHT = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _seg_key(a, b):
    return (a, b) if a <= b else (b, a)


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


@dataclass
class TState:
    size: int = 12
    pegs: dict = field(default_factory=dict)         # (c,r) -> player
    bridges: dict = field(default_factory=dict)      # frozenset segs per player {0:set,1:set}
    to_move: int = RED
    winner: object = None

    def __post_init__(self):
        if not self.bridges:
            self.bridges = {RED: set(), BLACK: set()}


class TwixT(Game):
    uid = "twixt"
    name = "TwixT"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        size = int((options or {}).get("size", 12))
        return TState(size=size)

    def current_player(self, s):
        return s.to_move

    def _playable(self, s, c, r, pl):
        n = s.size
        if not (0 <= c < n and 0 <= r < n) or (c, r) in s.pegs:
            return False
        # corners belong to no one
        if c in (0, n - 1) and r in (0, n - 1):
            return False
        if pl == RED:
            return 0 < c < n - 1            # red may not play black's left/right columns
        return 0 < r < n - 1                # black may not play red's top/bottom rows

    def _board_full(self, s):
        return len(s.pegs) >= s.size * s.size - 4      # all non-corner holes filled

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        n = s.size
        placements = [f"{c},{r}" for r in range(n) for c in range(n)
                      if self._playable(s, c, r, s.to_move)]
        if placements:
            return placements
        return [] if self._board_full(s) else ["pass"]   # forced pass when stuck but not full

    def _new_bridges(self, s, at, pl):
        """Knight-move links from `at` to friendly pegs that don't cross a bridge."""
        existing = s.bridges[RED] | s.bridges[BLACK]
        out = []
        for dc, dr in KNIGHT:
            nb = (at[0] + dc, at[1] + dr)
            if s.pegs.get(nb) != pl:
                continue
            seg = _seg_key(at, nb)
            if not any(_crosses(seg, e) for e in existing):
                out.append(seg)
        return out

    def _connected(self, s, pl):
        n = s.size
        if pl == RED:
            starts = [p for p in s.pegs if s.pegs[p] == RED and p[1] == 0]
            goal = lambda p: p[1] == n - 1            # noqa: E731
        else:
            starts = [p for p in s.pegs if s.pegs[p] == BLACK and p[0] == 0]
            goal = lambda p: p[0] == n - 1            # noqa: E731
        adj = {}
        for a, b in s.bridges[pl]:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        seen = set(starts)
        stack = list(starts)
        while stack:
            p = stack.pop()
            if goal(p):
                return True
            for q in adj.get(p, ()):
                if q not in seen:
                    seen.add(q)
                    stack.append(q)
        return False

    def apply_move(self, s, move, rng=None):
        pl = s.to_move
        bridges = {RED: set(s.bridges[RED]), BLACK: set(s.bridges[BLACK])}
        if move == "pass":
            return TState(size=s.size, pegs=dict(s.pegs), bridges=bridges, to_move=1 - pl)
        at = _cell(move)
        pegs = dict(s.pegs)
        pegs[at] = pl
        ns = TState(size=s.size, pegs=pegs, bridges=bridges, to_move=1 - pl)
        for seg in self._new_bridges(s, at, pl):
            ns.bridges[pl].add(seg)
        if self._connected(ns, pl):
            ns.winner = pl
        elif self._board_full(ns):
            ns.winner = "draw"
        return ns

    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner in (None, "draw"):
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    def serialize(self, s):
        return {"size": s.size,
                "pegs": {f"{c},{r}": p for (c, r), p in s.pegs.items()},
                "bridges": {str(pl): sorted([list(a), list(b)] for (a, b) in s.bridges[pl])
                            for pl in (RED, BLACK)},
                "to_move": s.to_move, "winner": s.winner}

    def deserialize(self, d):
        br = {RED: set(), BLACK: set()}
        for pl in (RED, BLACK):
            for a, b in d.get("bridges", {}).get(str(pl), []):
                br[pl].add(_seg_key(tuple(a), tuple(b)))
        return TState(size=d["size"], pegs={_cell(k): v for k, v in d["pegs"].items()},
                      bridges=br, to_move=d["to_move"], winner=d.get("winner"))

    def describe_move(self, s, move):
        return move

    def render(self, s, perspective=None):
        n = s.size
        pieces = [{"cell": f"{c},{r}", "owner": p} for (c, r), p in s.pegs.items()]
        # bridges as overlay lines (drawn over the cells) in each player's colour
        colour = {RED: "#e06b6b", BLACK: "#6b8fe0"}
        overlay = []
        for pl in (RED, BLACK):
            for (a, b) in s.bridges[pl]:
                overlay.append([[a[0], a[1]], [b[0], b[1]], colour[pl]])
        tints = {}
        for c in range(1, n - 1):
            tints[f"{c},0"] = "#3a2222"; tints[f"{c},{n - 1}"] = "#3a2222"   # red edges
        for r in range(1, n - 1):
            tints[f"0,{r}"] = "#22223a"; tints[f"{n - 1},{r}"] = "#22223a"   # black edges
        names = {RED: "Red", BLACK: "Black"}
        if s.winner == "draw":
            cap = "Draw (no connection)"
        elif s.winner is not None:
            cap = f"{names[s.winner]} wins (connected)"
        else:
            cap = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": n, "height": n, "overlay": overlay, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
