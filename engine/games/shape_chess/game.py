"""Shape Chess (Xingqi, 形棋) — 日出 "Richu" of Guangzhou, 2022 ruleset.

Rules per David Ploog's article in Abstract Games magazine #24 (Winter 2022),
pp. 4-7 (the definitive English source; BGG id 367618):

* Square board, 12x12 or larger (stones sit on the points of the grid; any Go
  or Renju board works).  Black begins.
* A turn is ONE of:
    - DROP an own stone on an empty point;
    - JUMP an own stone to any empty point, anywhere on the board;
    - PUSH an adjacent-to-empty opposing stone to an adjacent empty point
      (any of its 8 neighbours; the MOVER chooses which) and place an own
      stone at the origin.  (Pushes and drops add a stone; jumps do not.)
* A SHAPE is a stone together with all same-coloured stones reachable by
  orthogonal or diagonal steps (8-connectivity).  A shape is SYMMETRIC if it
  is preserved by reflection along some line: a vertical or horizontal grid
  or half-grid line, or a diagonal (slope +-1) through the points.  Rotational
  symmetry does NOT count.
* If after a player's turn there are symmetric shapes of >= 6 stones of the
  player's OWN colour: each such shape is removed from the board and scores
  (n - 5) points for an n-stone shape, and the player immediately takes
  ANOTHER turn (this chains).  Opponent shapes are never checked or removed
  on your turn.
* The first player to reach the winning score (4 in the standard game;
  adjustable per the article) wins immediately.

Implementation additions (documented in rules.md; the article gives no
draw rule):
* If the whole board fills up there is no legal move: the game ends and the
  higher score wins (equal scores = draw).
* No-progress guard: if no scoring happens for max(120, n*n) consecutive
  turns, or after 6*n*n total turns, the game ends the same way (higher
  score wins, genuine tie is an honest draw).

Move grammar:
  drop  = "c,r"            (one empty cell)
  jump  = "c1,r1>c2,r2"    (own stone -> any empty cell)
  push  = "c1,r1>c2,r2"    (ENEMY stone -> adjacent empty cell; an own stone
                            appears at c1,r1)  -- disambiguated from a jump
                            by the colour of the origin stone.
Cells are "col,row", 0-based, row 0 at the bottom (a1 = "0,0" in the
article's algebraic coordinates; file letters include 'i').
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1
DEFAULT_SIZE = 12
DEFAULT_TARGET = 4

DIRS8 = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


# ---------------------------------------------------------------------------
# shapes & symmetry
# ---------------------------------------------------------------------------

def components(cells) -> list:
    """8-connected components of a set of (x, y) points."""
    cells = set(cells)
    out = []
    while cells:
        seed = cells.pop()
        comp = {seed}
        stack = [seed]
        while stack:
            x, y = stack.pop()
            for dx, dy in DIRS8:
                nb = (x + dx, y + dy)
                if nb in cells:
                    cells.remove(nb)
                    comp.add(nb)
                    stack.append(nb)
        out.append(comp)
    return out


def symmetric(comp) -> bool:
    """True iff the point set is preserved by reflection along some line.

    Any mirror line that maps the lattice-point set to itself must be one of:
      * a vertical line   x = (min_x+max_x)/2   (grid or half-grid),
      * a horizontal line y = (min_y+max_y)/2   (grid or half-grid),
      * a diagonal   y =  x + c  with c = (min_d+max_d)/2, d = y-x, c integer
        (a half-integer diagonal offset maps lattice points off-lattice),
      * an anti-diagonal x + y = c with c = (min_s+max_s)/2, s = x+y, c integer.
    The axis position is forced by the set's bounding extents.  Rotational
    symmetry does not count (per the article's explicit examples).
    """
    S = set(comp)
    xs = [p[0] for p in S]
    ys = [p[1] for p in S]
    sx = min(xs) + max(xs)
    if all((sx - x, y) in S for x, y in S):
        return True
    sy = min(ys) + max(ys)
    if all((x, sy - y) in S for x, y in S):
        return True
    ds = [y - x for x, y in S]
    c2 = min(ds) + max(ds)
    if c2 % 2 == 0:
        c = c2 // 2
        if all((y - c, x + c) in S for x, y in S):
            return True
    ss = [x + y for x, y in S]
    c2 = min(ss) + max(ss)
    if c2 % 2 == 0:
        c = c2 // 2
        if all((c - y, c - x) in S for x, y in S):
            return True
    return False


def sweep(stones) -> tuple:
    """Remove every symmetric shape of >= 6 stones from the point set.

    Returns (points_scored, removed_set):  each removed n-shape scores n - 5.
    """
    pts = 0
    removed = set()
    for comp in components(stones):
        if len(comp) >= 6 and symmetric(comp):
            pts += len(comp) - 5
            removed |= comp
    return pts, removed


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------

@dataclass
class SCState:
    n: int = DEFAULT_SIZE
    target: int = DEFAULT_TARGET
    board: dict = field(default_factory=dict)   # (c, r) -> BLACK/WHITE
    scores: list = field(default_factory=lambda: [0, 0])
    to_move: int = BLACK
    winner: Optional[int] = None
    noscore: int = 0            # consecutive turns without a scoring event
    ply: int = 0
    stopped: bool = False       # no-progress / ply-cap stop -> score comparison
    bonus: bool = False         # mover is on an extra turn after scoring
    last: Optional[list] = None  # cells of the last action (for highlights)


class ShapeChess(Game):
    name = "Shape Chess"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SCState:
        opts = options or {}
        n = int(opts.get("size", DEFAULT_SIZE))
        target = int(opts.get("target", DEFAULT_TARGET))
        return SCState(n=n, target=target)

    def current_player(self, s: SCState) -> int:
        return s.to_move

    # ---- moves -------------------------------------------------------------

    def legal_moves(self, s: SCState) -> list:
        if self.is_terminal(s):
            return []
        n = s.n
        board = s.board
        p = s.to_move
        empties = [(c, r) for c in range(n) for r in range(n)
                   if (c, r) not in board]
        out = []
        # drops
        for c, r in empties:
            out.append(f"{c},{r}")
        # jumps: any own stone to any empty point
        own = [pos for pos, pl in board.items() if pl == p]
        for oc, orr in own:
            frm = f"{oc},{orr}>"
            for c, r in empties:
                out.append(f"{frm}{c},{r}")
        # pushes: any enemy stone to any adjacent empty point
        for (ec, er), pl in board.items():
            if pl == p:
                continue
            for dc, dr in DIRS8:
                tc, tr = ec + dc, er + dr
                if 0 <= tc < n and 0 <= tr < n and (tc, tr) not in board:
                    out.append(f"{ec},{er}>{tc},{tr}")
        return out

    def is_terminal(self, s: SCState) -> bool:
        return (s.winner is not None or s.stopped
                or len(s.board) >= s.n * s.n)

    def apply_move(self, s: SCState, move: str, rng=None) -> SCState:
        p = s.to_move
        board = dict(s.board)
        if ">" in move:
            a_s, b_s = move.split(">")
            a, b = _cell(a_s), _cell(b_s)
            if board[a] == p:              # jump
                del board[a]
                board[b] = p
                last = [a_s, b_s]
            else:                          # push: enemy stone a -> b, own at a
                board[b] = board[a]
                board[a] = p
                last = [a_s, b_s]
        else:                              # drop
            a = _cell(move)
            board[a] = p
            last = [move]

        # sweep the mover's OWN symmetric shapes of >= 6 stones
        mine = {pos for pos, pl in board.items() if pl == p}
        pts, removed = sweep(mine)
        scores = list(s.scores)
        winner = None
        if pts:
            for pos in removed:
                del board[pos]
            scores[p] += pts
            noscore = 0
            if scores[p] >= s.target:
                winner = p
            to_move = p                    # extra turn (chains)
            bonus = True
        else:
            noscore = s.noscore + 1
            to_move = 1 - p
            bonus = False

        ply = s.ply + 1
        n = s.n
        stopped = False
        if winner is None:
            if noscore >= max(120, n * n) or ply >= 6 * n * n:
                stopped = True
        return SCState(n=n, target=s.target, board=board, scores=scores,
                       to_move=to_move, winner=winner, noscore=noscore,
                       ply=ply, stopped=stopped, bonus=bonus, last=last)

    # ---- result ------------------------------------------------------------

    def returns(self, s: SCState) -> list:
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == BLACK else [-1.0, 1.0]
        # board full / no-progress stop: higher score wins, tie = honest draw
        b, w = s.scores
        if b > w:
            return [1.0, -1.0]
        if w > b:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: SCState) -> list:
        b, w = s.scores
        stones_b = sum(1 for pl in s.board.values() if pl == BLACK)
        stones_w = sum(1 for pl in s.board.values() if pl == WHITE)
        d = (b - w) / max(1, s.target) + 0.01 * (stones_b - stones_w)
        val = math.tanh(1.5 * d)
        return [val, -val]

    # ---- serialize ---------------------------------------------------------

    def serialize(self, s: SCState) -> dict:
        return {
            "n": s.n,
            "target": s.target,
            "board": {f"{c},{r}": pl for (c, r), pl in s.board.items()},
            "scores": list(s.scores),
            "to_move": s.to_move,
            "winner": s.winner,
            "noscore": s.noscore,
            "ply": s.ply,
            "stopped": s.stopped,
            "bonus": s.bonus,
            "last": s.last,
        }

    def deserialize(self, d: dict) -> SCState:
        return SCState(
            n=d["n"], target=d.get("target", DEFAULT_TARGET),
            board={_cell(k): v for k, v in d["board"].items()},
            scores=list(d.get("scores", [0, 0])),
            to_move=d["to_move"], winner=d.get("winner"),
            noscore=d.get("noscore", 0), ply=d.get("ply", 0),
            stopped=d.get("stopped", False), bonus=d.get("bonus", False),
            last=d.get("last"),
        )

    # ---- notation ----------------------------------------------------------

    def _alg(self, cell_str: str) -> str:
        c, r = _cell(cell_str)
        return f"{chr(ord('a') + c)}{r + 1}"

    def describe_move(self, s: SCState, move: str) -> str:
        p = s.to_move
        board = dict(s.board)
        if ">" in move:
            a_s, b_s = move.split(">")
            a, b = _cell(a_s), _cell(b_s)
            if board.get(a) == p:
                kind = f"Jump {self._alg(a_s)}-{self._alg(b_s)}"
                del board[a]
                board[b] = p
            else:
                kind = f"Push {self._alg(a_s)}:{self._alg(b_s)}"
                board[b] = board[a]
                board[a] = p
        else:
            kind = f"Drop {self._alg(move)}"
            board[_cell(move)] = p
        pts, _ = sweep({pos for pos, pl in board.items() if pl == p})
        return f"{kind} (+{pts})" if pts else kind

    # ---- render ------------------------------------------------------------

    def render(self, s: SCState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [{"cell": f"{c},{r}", "owner": pl}
                  for (c, r), pl in s.board.items()]
        highlights = [{"cell": cell, "kind": "last-move"}
                      for cell in (s.last or [])]
        score_str = f"Black {s.scores[0]} - {s.scores[1]} White (to {s.target})"
        if s.winner is not None:
            caption = f"{names[s.winner]} wins! {score_str}"
        elif self.is_terminal(s):
            ret = self.returns(s)
            why = "board full" if len(s.board) >= s.n * s.n else "no progress"
            if ret[0] == ret[1]:
                caption = f"Draw ({why}) - {score_str}"
            else:
                caption = (f"{names[BLACK] if ret[0] > 0 else names[WHITE]}"
                           f" wins ({why}) - {score_str}")
        else:
            extra = " again (bonus turn)" if s.bonus else " to move"
            caption = f"{names[s.to_move]}{extra} - {score_str}"
        return {
            "board": {"type": "square", "width": s.n, "height": s.n},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
