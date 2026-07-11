"""Rhode — a square-board connection game by Luis Bolaños Mures (June 2016).

Played on the points of an initially empty square grid (rendered here as an
N x N grid of cells). Black (player 0) owns the TOP and BOTTOM edges, White
(player 1) the LEFT and RIGHT edges; you win by completing a chain of
ORTHOGONALLY adjacent stones of your colour touching your two opposite edges.
Black moves first; the pie rule applies (White may "swap" on their first turn).

Rhode's twist: diagonal connections must be consolidated, and doing so costs
a whole turn. Definitions (designer's wording):

- A WEAK PAIR is a set of two like-coloured, diagonally adjacent stones such
  that there is no like-coloured stone orthogonally adjacent to both.
- A CROSSCUT is a 2x2 pattern of stones consisting of two diagonally adjacent
  black stones and two diagonally adjacent white stones.

On your turn, if there are any friendly weak pairs on the board, you MUST
place a stone of your colour on an empty point that is orthogonally adjacent
to the two stones in one of those pairs. If there are no such pairs, you may
place a stone of your colour on any empty point. After placing a stone, you
must remove all OTHER friendly stones that are part of any crosscuts; the
stone you just placed is never removed.

Rules sources (identical text in both): the designer's BGG thread "New games:
Cation and Rhode" (boardgamegeek.com/thread/1593043) and his Zillions of Games
submission (id 2501, "Rhode", 2016-06-26, updated 2016-07-09; sizes 3x3-19x19).
Interpretations resolved against the Zillions .zrf:

- The weak-pair obligation is implemented in the .zrf as a higher-priority
  move type (move-priorities fix-diagonal normal): completion placements are
  generated for empty points p with two friendly orthogonal neighbours that
  are diagonally adjacent to each other and whose opposite 2x2 corner holds
  no friendly stone. If NO such move generates (weak pairs exist but every
  completion point is occupied — unreachable in real play, see below), play
  falls through to free placement. We mirror that fallback.
- Removal: the .zrf captures only the friendly diagonal partner of crosscuts
  through the just-placed stone. On reachable boards that equals the literal
  rule, because no crosscut ever survives a turn: every crosscut created by a
  placement contains the placed stone plus exactly one other friendly stone,
  which is removed — so boards are crosscut-free at the start of every turn,
  and consequently every friendly weak pair has at least one EMPTY completion
  point (its 2x2 corners are non-friendly; if both were enemy the 2x2 would
  be a crosscut). We implement the literal rule (scan all crosscuts on the
  post-placement board) so constructed positions also behave per the prose.
  Opponent stones in crosscuts are never removed.
- Win check timing: the .zrf performs the captures inside the move and
  Zillions evaluates win conditions at the end of the move, i.e. the chain
  test runs on the POST-removal board. Only the mover can newly connect (the
  move only adds a mover stone / removes mover stones).
- The .zrf has no pie rule (a Zillions limitation); the BGG prose states the
  pie rule ("change sides") for both games. We implement "swap" as the
  value-preserving single-stone mirror: Black's lone opening stone is
  reflected across the main diagonal and recoloured White (the game is
  symmetric under transpose + colour swap), per the hex/konobi convention.

Termination: the game is drawless in real play — a crosscut-free full board
always contains exactly one winning chain, and boards here are crosscut-free
at every turn start. Removals can shrink the population, so as the standard
defensive backstop a hard ply cap of 8*N*N (and a double pass, reachable only
from constructed full boards) is declared an honest draw. Seeded random
playouts (selftest.py) terminate far below the cap with zero draws.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black connects top<->bottom (rows), White left<->right (cols)

_ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
_DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class RhodeState:
    size: int = 11
    board: dict = field(default_factory=dict)   # (c, r) -> BLACK/WHITE
    to_move: int = BLACK
    last: Optional[tuple] = None   # stone placed by the PREVIOUS mover
    winner: Optional[int] = None
    draw: bool = False
    ply: int = 0
    passes: int = 0                # consecutive passes (constructed boards only)


def _is_crosscut(board: dict, c: int, r: int) -> bool:
    """Is the 2x2 square with lower-left corner (c, r) a crosscut?"""
    a = board.get((c, r))
    b = board.get((c + 1, r))
    d = board.get((c, r + 1))
    e = board.get((c + 1, r + 1))
    return (a is not None and b is not None and d is not None and e is not None
            and a == e and b == d and a != b)


def _crosscut_squares(board: dict, size: int) -> list:
    """Lower-left corners of every crosscut on the board."""
    return [(c, r) for c in range(size - 1) for r in range(size - 1)
            if _is_crosscut(board, c, r)]


def _weak_pairs(board: dict, player: int) -> list:
    """All weak pairs of `player`: diagonally adjacent friendly stones with no
    friendly stone orthogonally adjacent to both (i.e. neither 2x2 corner
    between them is friendly). Each pair is returned once, as a sorted tuple."""
    out = set()
    for (c, r), owner in board.items():
        if owner != player:
            continue
        for dc, dr in ((1, 1), (1, -1)):        # each diagonal pair once
            p2 = (c + dc, r + dr)
            if board.get(p2) != player:
                continue
            corner1 = (c + dc, r)               # the two shared orthogonal
            corner2 = (c, r + dr)               # neighbours of the pair
            if board.get(corner1) != player and board.get(corner2) != player:
                out.add(((c, r), p2))
    return sorted(out)


def _completion_points(board: dict, size: int, player: int) -> set:
    """Empty points orthogonally adjacent to both stones of some friendly
    weak pair — the forced placements (the .zrf's fix-diagonal moves)."""
    out = set()
    for r in range(size):
        for c in range(size):
            if (c, r) in board:
                continue
            for dc, dr in _DIAG:
                # pair = the two orthogonal neighbours (c+dc, r) and (c, r+dr);
                # they are diagonally adjacent to each other, and the pair's
                # other shared orthogonal neighbour is the corner (c+dc, r+dr).
                if (board.get((c + dc, r)) == player
                        and board.get((c, r + dr)) == player
                        and board.get((c + dc, r + dr)) != player):
                    out.add((c, r))
                    break
    return out


def _connects(board: dict, player: int, size: int) -> bool:
    """Does `player` join their two edges via an ORTHOGONAL chain?"""
    if player == BLACK:  # bottom row 0 <-> top row size-1
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == BLACK]
        at_goal = lambda cell: cell[1] == size - 1  # noqa: E731
    else:                # left col 0 <-> right col size-1
        starts = [(0, r) for r in range(size) if board.get((0, r)) == WHITE]
        at_goal = lambda cell: cell[0] == size - 1  # noqa: E731
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        cc, cr = cur
        for dc, dr in _ORTH:
            nb = (cc + dc, cr + dr)
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return False


def _removals(board: dict, size: int, placed: tuple, player: int) -> set:
    """All OTHER friendly stones that are part of any crosscut on the
    post-placement board (the placed stone is exempt; enemy stones stay)."""
    out = set()
    for (c, r) in _crosscut_squares(board, size):
        for cell in ((c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)):
            if board[cell] == player and cell != placed:
                out.add(cell)
    return out


class Rhode(Game):
    name = "Rhode"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> RhodeState:
        size = int((options or {}).get("size", 11))
        return RhodeState(size=size)

    def current_player(self, s: RhodeState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def legal_moves(self, s: RhodeState) -> list[str]:
        if self.is_terminal(s):
            return []
        me = s.to_move
        forced = _completion_points(s.board, s.size, me)
        if forced:
            moves = [f"{c},{r}" for (c, r) in sorted(forced)]
        else:
            moves = [f"{c},{r}" for r in range(s.size) for c in range(s.size)
                     if (c, r) not in s.board]
        if not moves:
            return ["pass"]          # constructed full boards only (defensive)
        if s.ply == 1:
            moves.append("swap")     # pie rule: White's first turn only
        return moves

    # -- move application ---------------------------------------------------

    def apply_move(self, s: RhodeState, move: str, rng=None) -> RhodeState:
        if move == "pass":
            return RhodeState(size=s.size, board=dict(s.board),
                              to_move=1 - s.to_move, last=None,
                              winner=s.winner, draw=s.passes + 1 >= 2,
                              ply=s.ply + 1, passes=s.passes + 1)
        if move == "swap":
            # Pie rule ("change sides"): White takes over Black's opening.
            # Fixed-seat equivalent: reflect the lone stone across the main
            # diagonal and recolour it — Rhode is symmetric under transpose +
            # colour swap (Black joins rows, White joins columns), so White's
            # position is exactly as strong as Black's was. Recolouring in
            # place would NOT preserve the value (the colours aim at
            # different edges). Same convention as the hex/konobi packages.
            ((c, r), _owner), = s.board.items()
            return RhodeState(size=s.size, board={(r, c): s.to_move},
                              to_move=1 - s.to_move, last=(r, c),
                              ply=s.ply + 1)
        me = s.to_move
        board = dict(s.board)
        p = _cell(move)
        board[p] = me
        for dead in _removals(board, s.size, p, me):
            del board[dead]
        winner = me if _connects(board, me, s.size) else None
        return RhodeState(size=s.size, board=board, to_move=1 - me,
                          last=p, winner=winner, ply=s.ply + 1, passes=0)

    # -- termination / scoring ----------------------------------------------

    def is_terminal(self, s: RhodeState) -> bool:
        return s.winner is not None or s.draw or s.ply >= 8 * s.size * s.size

    def returns(self, s: RhodeState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]   # backstop draw (unreachable under real play)

    # -- bot guidance --------------------------------------------------------

    def heuristic(self, s: RhodeState) -> list:
        """Connection-distance eval as MCTS payoffs [black, white]: fewest
        additional stones each side needs to join their edges (0-1 BFS; own
        stone = 0, empty = 1, enemy = blocked), squashed to (-1, 1)."""
        db = self._edge_distance(s, BLACK)
        dw = self._edge_distance(s, WHITE)
        import math
        val = math.tanh(0.35 * (dw - db))   # positive = Black ahead
        return [val, -val]

    def _edge_distance(self, s: RhodeState, player: int) -> float:
        from collections import deque
        n = s.size
        big = n * n
        # source frontier = the player's first edge; target = opposite edge.
        dist = {}
        dq = deque()
        for i in range(n):
            cell = (i, 0) if player == BLACK else (0, i)
            owner = s.board.get(cell)
            if owner == 1 - player:
                continue
            d = 0 if owner == player else 1
            if dist.get(cell, big) > d:
                dist[cell] = d
                (dq.appendleft if d == 0 else dq.append)(cell)
        best = big
        while dq:
            cur = dq.popleft()
            d = dist[cur]
            if (cur[1] if player == BLACK else cur[0]) == n - 1:
                best = min(best, d)
                continue
            for dc, dr in _ORTH:
                nb = (cur[0] + dc, cur[1] + dr)
                if not (0 <= nb[0] < n and 0 <= nb[1] < n):
                    continue
                owner = s.board.get(nb)
                if owner == 1 - player:
                    continue
                nd = d + (0 if owner == player else 1)
                if dist.get(nb, big) > nd:
                    dist[nb] = nd
                    (dq.appendleft if nd == d else dq.append)(nb)
        return best

    # -- serialization ------------------------------------------------------

    def serialize(self, s: RhodeState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "last": None if s.last is None else f"{s.last[0]},{s.last[1]}",
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
            "passes": s.passes,
        }

    def deserialize(self, d: dict) -> RhodeState:
        return RhodeState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            last=None if d.get("last") is None else _cell(d["last"]),
            winner=d.get("winner"),
            draw=d.get("draw", False),
            ply=d.get("ply", 0),
            passes=d.get("passes", 0),
        )

    # -- presentation ---------------------------------------------------------

    def _coord(self, cell) -> str:
        letters = "abcdefghijklmnopqrstuvwxyz"
        c, r = cell
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def describe_move(self, s: RhodeState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if move == "pass":
            return "pass (forced)"
        p = _cell(move)
        me = s.to_move
        text = self._coord(p)
        if _completion_points(s.board, s.size, me):
            text += " (weak pair)"
        b2 = dict(s.board)
        b2[p] = me
        dead = _removals(b2, s.size, p, me)
        if dead:
            text += f" (removes {', '.join(self._coord(x) for x in sorted(dead))})"
        return text

    def render(self, s: RhodeState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.draw or s.ply >= 8 * s.size * s.size:
            caption = "Draw (backstop)"
        elif _completion_points(s.board, s.size, s.to_move):
            caption = f"{names[s.to_move]} to move — must complete a weak pair"
        else:
            edge = "top–bottom" if s.to_move == BLACK else "left–right"
            caption = f"{names[s.to_move]} to move ({edge})"
        return {
            "board": {
                "type": "square", "width": s.size, "height": s.size,
                "edges": {"top": BLACK, "bottom": BLACK, "left": WHITE, "right": WHITE},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
