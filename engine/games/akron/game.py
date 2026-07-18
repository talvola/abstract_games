"""Akron (Cameron Browne 2002) -- 3D stacking connection game.

Two players, Black and White, on an 8x8 (or 10x10) grid of holes, each with
n*n/2 balls. Black connects the West and East edges, White connects the South
and North edges (corners belong to both adjoining edges). Balls stack in the
square-pyramidal interstitials: a level-L position (L >= 1) exists wherever a
full 2x2 "flat stable square" of level L-1 balls (any colour mix) supports it.

TOUCH / CONNECTION. Two balls touch iff they are orthogonally adjacent on the
same level, or one rests directly upon the other (its support square contains
the other). Connection = chain of touching same-colour balls, subject to the
OVER/UNDER rule: where connections cross, the uppermost prevails.
Concretely (verified against Browne's AG#14 Figures 2-6, his official rules
v3.7, his gamerz.net PBM help file and igGameCenter):
  * EDGE over EDGE: the orthogonal adjacencies whose midpoints share one plan
    "crossing point" stack up perpendicular level by level. The highest
    same-colour adjacent pair over a crossing point owns it; every lower pair
    of the *other* colour crossing that point is severed (AG#14 Fig 5/6,
    igGameCenter cut diagram).
  * PIECE over PIECE: a ball with an enemy ball directly overhead (same plan
    position, a higher level) is cut from ALL connections (official rules
    v3.7: "any piece with a differently coloured piece directly overhead is
    effectively cut from all connections"). With several balls stacked over
    one plan point the topmost prevails: balls below it of the other colour
    are cut.

TURN. Either ADD a ball from your pile to any vacant *board-level* hole, or
MOVE one of your on-board balls to any valid empty point that touches a ball
connected to it (excluding the moving ball itself). A point is valid if it is
on the board surface or supported by a full square of four balls before,
during and after the move (so the mover cannot support its own destination,
and balls that dropped this turn cannot be used as support). A ball that
supports exactly one ball may move: the supported ball drops into the vacated
pocket, cascading while each dropper in turn supported exactly one ball (a
lift that would strand two or more balls is illegal). The mover may not take
the place of a dropping ball (destinations must be empty before the move).

WIN (official v3.7 / PBM-server default): a connection wins only if it still
exists after the opponent's replying move -- implemented as: after every move,
if the player NOT on move now spans their two edges, they win immediately.
(This also awards the game to the opponent when the mover lifts an overpass
and reveals the opponent's connection, per AG#14.) A player whose opponent
has no legal move also wins. Repeating a position (same balls + same player
to move) a third time is an automatic draw, plus a hard ply cap.

Move strings: cells are "L,c,r" (level, column, row; level-L grid is
(n-L)x(n-L), plan position (c+L/2, r+L/2)). Placement = "0,c,r"; movement =
"L,c,r>L',c',r'"; pie rule = "swap" (second player's first turn).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1          # BLACK: West<->East (c), WHITE: South<->North (r)
PLY_CAP = 600


def _pos(s):
    L, c, r = s.split(",")
    return (int(L), int(c), int(r))


def _key(p):
    return f"{p[0]},{p[1]},{p[2]}"


def _plan2(p):
    """Doubled plan coordinates (half-units -> ints): level-L index (c,r)
    sits over plan point (c + L/2, r + L/2)."""
    L, c, r = p
    return (2 * c + L, 2 * r + L)


def _supporters(p):
    """The four positions a level-L>=1 ball rests on (pylos convention)."""
    L, c, r = p
    if L == 0:
        return ()
    return ((L - 1, c, r), (L - 1, c + 1, r),
            (L - 1, c, r + 1), (L - 1, c + 1, r + 1))


def _over_slots(p):
    """The four level-L+1 positions whose support square contains ``p``."""
    L, c, r = p
    return ((L + 1, c - 1, r - 1), (L + 1, c, r - 1),
            (L + 1, c - 1, r), (L + 1, c, r))


def _touches(a, b):
    """Geometric touch between two positions (colour-blind): same-level
    orthogonal neighbours, or one rests on the other."""
    La, ca, ra = a
    Lb, cb, rb = b
    if La == Lb:
        return abs(ca - cb) + abs(ra - rb) == 1
    if Lb == La + 1:
        return cb in (ca - 1, ca) and rb in (ra - 1, ra)
    if La == Lb + 1:
        return ca in (cb - 1, cb) and ra in (rb - 1, rb)
    return False


def _touch_candidates(p):
    """Every position that could touch ``p``: 4 orthogonal + rests-on/under."""
    L, c, r = p
    out = [(L, c + 1, r), (L, c - 1, r), (L, c, r + 1), (L, c, r - 1)]
    out.extend(_supporters(p))
    out.extend(_over_slots(p))
    return out


@dataclass
class AkronState:
    size: int = 8
    board: dict = field(default_factory=dict)      # "L,c,r" -> colour 0/1
    pile: list = field(default_factory=lambda: [32, 32])   # per COLOUR
    seat_colour: list = field(default_factory=lambda: [0, 1])  # seat -> colour
    to_move: int = 0                                # seat index
    winner: object = None                           # None / seat / "draw"
    ply: int = 0
    history: dict = field(default_factory=dict)     # repetition counts
    last: Optional[str] = None                      # last-touched cell ids "a|b"


# ---------------------------------------------------------------------------
# position analysis (cuts + touch graph), on a plain {(L,c,r): colour} dict
# ---------------------------------------------------------------------------

def _cut_info(balls):
    """Return (column_cut, cut_edges) applying the over/under rule.

    column_cut: set of positions cut from ALL connections (enemy ball above
    them in their plan column, topmost prevails).
    cut_edges: set of frozenset({a, b}) orthogonal touches severed by a
    higher perpendicular enemy pair over the same crossing point.
    """
    cols = {}
    for p in balls:
        cols.setdefault(_plan2(p), []).append(p)
    column_cut = set()
    for lst in cols.values():
        if len(lst) < 2:
            continue
        lst.sort()                                # by level (plan equal)
        top_colour = balls[lst[-1]]
        for p in lst[:-1]:
            if balls[p] != top_colour:
                column_cut.add(p)

    by_mid = {}
    for p, col in balls.items():
        if p in column_cut:
            continue
        L, c, r = p
        for q in ((L, c + 1, r), (L, c, r + 1)):
            if balls.get(q) == col and q not in column_cut:
                pa, pb = _plan2(p), _plan2(q)
                mid = ((pa[0] + pb[0]) // 2, (pa[1] + pb[1]) // 2)
                by_mid.setdefault(mid, []).append((L, col, p, q))
    cut_edges = set()
    for lst in by_mid.values():
        if len(lst) < 2:
            continue
        lst.sort(key=lambda t: t[0])
        top_colour = lst[-1][1]
        for L, col, p, q in lst[:-1]:
            if col != top_colour:
                cut_edges.add(frozenset((p, q)))
    return column_cut, cut_edges


def _touch_graph(balls):
    """Adjacency (same-colour touches, over/under cuts applied)."""
    column_cut, cut_edges = _cut_info(balls)
    adj = {p: [] for p in balls}
    for p, col in balls.items():
        if p in column_cut:
            continue
        L, c, r = p
        for q in ((L, c + 1, r), (L, c, r + 1)):        # orthogonal
            if (balls.get(q) == col and q not in column_cut
                    and frozenset((p, q)) not in cut_edges):
                adj[p].append(q)
                adj[q].append(p)
        for q in _over_slots(p):                        # q rests on p
            if balls.get(q) == col and q not in column_cut:
                adj[p].append(q)
                adj[q].append(p)
    return adj


def _component(adj, start):
    seen = {start}
    stack = [start]
    while stack:
        cur = stack.pop()
        for nb in adj[cur]:
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return seen


def _spans(balls, colour, size):
    """Does ``colour`` connect its two edges? Edge contact is via board-level
    balls on the border lines (elevated balls never project onto an edge
    line). BLACK: c==0 <-> c==size-1;  WHITE: r==0 <-> r==size-1."""
    if colour == BLACK:
        starts = [p for p, col in balls.items()
                  if col == colour and p[0] == 0 and p[1] == 0]
        def at_goal(p):
            return p[0] == 0 and p[1] == size - 1
    else:
        starts = [p for p, col in balls.items()
                  if col == colour and p[0] == 0 and p[2] == 0]
        def at_goal(p):
            return p[0] == 0 and p[2] == size - 1
    if not starts:
        return False
    adj = _touch_graph(balls)
    column_cut, _ = _cut_info(balls)
    starts = [p for p in starts if p not in column_cut]
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        for nb in adj[cur]:
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return False


def _resolve_drops(balls, f):
    """Lift ball ``f``; resolve the drop cascade.

    Returns (new_balls_without_f, moved) where moved maps NEW position ->
    ORIGINAL position for every ball that dropped, or None if the lift is
    illegal (some dropper supported 2+ balls, which would strand them)."""
    nb = dict(balls)
    del nb[f]
    moved = {}
    slot = f
    while True:
        over = [q for q in _over_slots(slot) if q in nb and q not in moved]
        if len(over) == 0:
            return nb, moved
        if len(over) > 1:
            return None                 # would strand balls -> illegal lift
        q = over[0]
        colour = nb.pop(q)
        nb[slot] = colour
        moved[slot] = q          # ball originally at q now sits at slot
        slot = q


class Akron(Game):
    uid = "akron"
    name = "Akron"

    @property
    def num_players(self):
        return 2

    # ---- helpers -----------------------------------------------------------
    def _balls(self, state):
        return {_pos(k): v for k, v in state.board.items()}

    def _all_positions(self, size):
        for L in range(size):
            n = size - L
            for r in range(n):
                for c in range(n):
                    yield (L, c, r)

    def _valid_empty_points(self, balls, size):
        """Empty points that are on the board or fully supported (pre-move)."""
        out = []
        for c in range(size):
            for r in range(size):
                if (0, c, r) not in balls:
                    out.append((0, c, r))
        # elevated: only positions over a full square can exist
        for p in list(balls):
            for q in _over_slots(p):
                if q in balls or q in out:
                    continue
                L, c, r = q
                if not (0 <= c <= size - 1 - L and 0 <= r <= size - 1 - L):
                    continue
                if all(s in balls for s in _supporters(q)):
                    out.append(q)
        return out

    def _movement_moves(self, state, balls=None, first_only=False):
        """All movement moves for the seat to move (or just one, early-exit)."""
        if balls is None:
            balls = self._balls(state)
        mc = state.seat_colour[state.to_move]
        size = state.size
        adj = _touch_graph(balls)
        dests = self._valid_empty_points(balls, size)
        moves = []
        comp_of = {}
        for p in balls:
            if p not in comp_of:
                comp = _component(adj, p)
                for q in comp:
                    comp_of[q] = comp
        for f, col in balls.items():
            if col != mc:
                continue
            n_over = sum(1 for q in _over_slots(f) if q in balls)
            if n_over > 1:
                continue                                    # pinned
            G = comp_of[f] - {f}
            if not G:
                continue                    # isolated/cut ball cannot move
            res = _resolve_drops(balls, f)
            if res is None:
                continue                    # cascade would strand balls
            pb, moved = res
            for d in dests:
                if d == f:
                    continue
                if d in pb:                 # filled by a dropper
                    continue
                if d[0] > 0:
                    sup = _supporters(d)
                    if any(s not in pb or s in moved for s in sup):
                        continue            # support broken during/after
                cands = _touch_candidates(d)
                # touches a ball connected to the mover: before ...
                if not any(q in G for q in cands):
                    continue
                # ... and after the move (identities from G, post positions)
                ok = False
                for q in cands:
                    if q in pb and pb[q] == mc and moved.get(q, q) in G:
                        ok = True
                        break
                if not ok:
                    continue
                moves.append(f"{_key(f)}>{_key(d)}")
                if first_only:
                    return moves
        return moves

    # ---- core --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        size = int((options or {}).get("size", 8))
        n = size * size // 2
        return AkronState(size=size, pile=[n, n])

    def current_player(self, state):
        return state.to_move

    def legal_moves(self, state):
        if state.winner is not None:
            return []
        balls = self._balls(state)
        mc = state.seat_colour[state.to_move]
        moves = []
        if state.ply == 1:
            moves.append("swap")
        if state.pile[mc] > 0:
            for c in range(state.size):
                for r in range(state.size):
                    if (0, c, r) not in balls:
                        moves.append(f"0,{c},{r}")
        moves.extend(self._movement_moves(state, balls))
        return moves

    def _has_any_move(self, state):
        if state.winner is not None:
            return False
        balls = self._balls(state)
        mc = state.seat_colour[state.to_move]
        if state.ply == 1:
            return True                                    # swap available
        if state.pile[mc] > 0:
            if sum(1 for p in balls if p[0] == 0) < state.size * state.size:
                return True     # a free board hole exists
        return bool(self._movement_moves(state, balls, first_only=True))

    def _position_key(self, state):
        import hashlib
        items = ";".join(f"{k}:{v}" for k, v in sorted(state.board.items()))
        raw = (f"{items}|m{state.seat_colour[state.to_move]}"
               f"|p{state.pile[0]},{state.pile[1]}")
        return hashlib.md5(raw.encode()).hexdigest()

    def apply_move(self, state, move, rng=None):
        if state.winner is not None:
            raise ValueError("game over")
        mover = state.to_move
        mc = state.seat_colour[mover]
        balls = self._balls(state)
        size = state.size

        if move == "swap":
            if state.ply != 1:
                raise ValueError("swap only on the second player's first turn")
            ns = AkronState(size=size, board=dict(state.board),
                            pile=list(state.pile),
                            seat_colour=[state.seat_colour[1],
                                         state.seat_colour[0]],
                            to_move=1 - mover, ply=state.ply + 1,
                            history=dict(state.history), last=state.last)
            self._post_move(ns, mover)
            return ns

        if ">" in move:
            f_s, d_s = move.split(">")
            f, d = _pos(f_s), _pos(d_s)
            if balls.get(f) != mc:
                raise ValueError(f"not your ball: {f_s}")
            legal = self._movement_moves(state, balls)
            if move not in legal:
                raise ValueError(f"illegal movement {move!r}")
            res = _resolve_drops(balls, f)
            nb, moved = res
            nb[d] = mc
            board = {_key(p): col for p, col in nb.items()}
            ns = AkronState(size=size, board=board, pile=list(state.pile),
                            seat_colour=list(state.seat_colour),
                            to_move=1 - mover, ply=state.ply + 1,
                            history=dict(state.history),
                            last=f"{_key(f)}|{_key(d)}")
            self._post_move(ns, mover)
            return ns

        # placement
        p = _pos(move)
        if p[0] != 0:
            raise ValueError("balls from the pile go on the board only")
        if not (0 <= p[1] < size and 0 <= p[2] < size):
            raise ValueError(f"off board: {move}")
        if p in balls:
            raise ValueError(f"occupied: {move}")
        if state.pile[mc] <= 0:
            raise ValueError("pile empty")
        board = dict(state.board)
        board[move] = mc
        pile = list(state.pile)
        pile[mc] -= 1
        ns = AkronState(size=size, board=board, pile=pile,
                        seat_colour=list(state.seat_colour),
                        to_move=1 - mover, ply=state.ply + 1,
                        history=dict(state.history), last=move)
        self._post_move(ns, mover)
        return ns

    def _post_move(self, ns, mover):
        """Win/draw bookkeeping after a completed move by seat ``mover``."""
        balls = self._balls(ns)
        # 1. delayed win: the NON-mover's connection exists after the mover's
        #    reply -> non-mover wins (covers both survival and revealed wins).
        non_mover = 1 - mover
        if _spans(balls, ns.seat_colour[non_mover], ns.size):
            ns.winner = non_mover
            return
        # 2. repetition draw (third occurrence of the same position)
        key = self._position_key(ns)
        n = ns.history.get(key, 0) + 1
        ns.history[key] = n
        if n >= 3:
            ns.winner = "draw"
            return
        # 3. hard ply cap
        if ns.ply >= PLY_CAP:
            ns.winner = "draw"
            return
        # 4. no legal move for the player now to move -> they lose
        if not self._has_any_move(ns):
            ns.winner = mover
            return

    def is_terminal(self, state):
        return state.winner is not None

    def returns(self, state):
        if state.winner in (None, "draw"):
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- bot eval ----------------------------------------------------------
    def heuristic(self, state):
        """Cheap connection-distance eval: Dijkstra over board-level plan with
        own ball = 0, empty = 1, enemy = 2 (can be stepped over). Returns a
        payoff per SEAT."""
        import heapq
        balls = self._balls(state)
        size = state.size
        level0 = {(p[1], p[2]): col for p, col in balls.items() if p[0] == 0}

        def dist(colour):
            if colour == BLACK:
                starts = [(0, r) for r in range(size)]
                def goal(c, r):
                    return c == size - 1
            else:
                starts = [(c, 0) for c in range(size)]
                def goal(c, r):
                    return r == size - 1
            def cost(c, r):
                v = level0.get((c, r))
                if v == colour:
                    return 0
                if v is None:
                    return 1
                return 2
            pq = [(cost(c, r), (c, r)) for (c, r) in starts]
            best = {p: d for d, p in pq}
            heapq.heapify(pq)
            while pq:
                d, (c, r) = heapq.heappop(pq)
                if d > best.get((c, r), 1e9):
                    continue
                if goal(c, r):
                    return d
                for c2, r2 in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                    if 0 <= c2 < size and 0 <= r2 < size:
                        nd = d + cost(c2, r2)
                        if nd < best.get((c2, r2), 1e9):
                            best[(c2, r2)] = nd
                            heapq.heappush(pq, (nd, (c2, r2)))
            return size * 2
        d_black = dist(BLACK)
        d_white = dist(WHITE)
        v_black = max(-1.0, min(1.0, (d_white - d_black) / float(state.size)))
        out = [0.0, 0.0]
        for seat in range(2):
            out[seat] = v_black if state.seat_colour[seat] == BLACK else -v_black
        return out

    # ---- serialization -----------------------------------------------------
    def serialize(self, state):
        return {
            "size": state.size,
            "board": dict(state.board),
            "pile": list(state.pile),
            "seat_colour": list(state.seat_colour),
            "to_move": state.to_move,
            "winner": state.winner,
            "ply": state.ply,
            "history": dict(state.history),
            "last": state.last,
        }

    def deserialize(self, d):
        return AkronState(
            size=d.get("size", 8),
            board=dict(d["board"]),
            pile=list(d["pile"]),
            seat_colour=list(d.get("seat_colour", [0, 1])),
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            history=dict(d.get("history", {})),
            last=d.get("last"),
        )

    # ---- notation ----------------------------------------------------------
    def _cell_name(self, key):
        L, c, r = _pos(key)
        return f"{chr(ord('a') + c)}{r + 1}" + "'" * L

    def describe_move(self, state, move):
        if move == "swap":
            return "swap (steal the first move)"
        if ">" in move:
            f, d = move.split(">")
            return f"{self._cell_name(f)}→{self._cell_name(d)}"
        return self._cell_name(move)

    # ---- render ------------------------------------------------------------
    def render(self, state, perspective=None):
        balls = self._balls(state)
        size = state.size
        shown = [(0, c, r) for r in range(size) for c in range(size)]
        elevated = set()
        for p in balls:
            if p[0] > 0:
                elevated.add(p)
        for p in self._valid_empty_points(balls, size):
            if p[0] > 0:
                elevated.add(p)
        shown.extend(sorted(elevated))          # low levels draw first

        cells = []
        tints = {}
        for p in shown:
            L, c, r = p
            cx = c + 0.5 * L
            cy = r + 0.5 * L
            h = max(0.16, 0.46 - 0.045 * L)
            cells.append({
                "id": _key(p),
                "points": [[round(cx - h, 3), round(cy - h, 3)],
                           [round(cx + h, 3), round(cy - h, 3)],
                           [round(cx + h, 3), round(cy + h, 3)],
                           [round(cx - h, 3), round(cy + h, 3)]],
            })
            if p not in balls:
                base = ["#2c3340", "#39404e", "#464e5e", "#535c6e",
                        "#606a7e", "#6d788e", "#7a869e", "#8794ae"]
                tints[_key(p)] = base[min(L, 7)]

        # seat-coloured goal bands (Black seat: W-E, White seat: S-N)
        m = size - 0.5
        overlay = [
            [[-0.68, -0.5], [-0.68, m], "#15151a"],       # West  (Black's)
            [[m + 0.18, -0.5], [m + 0.18, m], "#15151a"],  # East
            [[-0.5, -0.68], [m, -0.68], "#e8e8ee"],        # South (White's)
            [[-0.5, m + 0.18], [m, m + 0.18], "#e8e8ee"],  # North
        ]

        pieces = []
        for p, colour in sorted(balls.items()):
            seat = state.seat_colour.index(colour)
            pieces.append({"cell": _key(p), "owner": seat})

        highlights = []
        if state.last:
            for cell in state.last.split("|"):
                if cell in state.board:
                    highlights.append({"cell": cell, "kind": "last-move"})

        names = {0: "P1", 1: "P2"}
        cname = {BLACK: "Black (W–E)", WHITE: "White (S–N)"}
        pb, pw = state.pile[BLACK], state.pile[WHITE]
        who = (f"{names[state.to_move]} = "
               f"{cname[state.seat_colour[state.to_move]]}")
        supply = f"piles Black {pb} / White {pw}"
        if state.winner == "draw":
            cap = f"Draw (repetition) — {supply}"
        elif state.winner is not None:
            w = state.winner
            cap = (f"{names[w]} ({cname[state.seat_colour[w]]}) wins — "
                   f"connection held — {supply}")
        else:
            cap = f"{who} to move — {supply}"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints,
                      "overlay": overlay,
                      "extent": [-0.8, -0.8, size + 0.6, size + 0.6]},
            "pieces": pieces,
            "highlights": highlights,
            "actionNames": {"swap": "Swap (steal first move)"},
            "caption": cap,
        }
