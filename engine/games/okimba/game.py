"""Okimba — a drawless square-board connection game by Luis Bolaños Mures (2026).

The "no captures" successor of Rhode / Akimbo (same designer, same board model
and the same naked-diagonal definition). Played on the points of an initially
empty N x N grid. Black (player 0) owns the TOP and BOTTOM edges, White
(player 1) the LEFT and RIGHT edges; you win by completing a chain of
ORTHOGONALLY adjacent stones of your colour touching your two opposite edges.
Black moves first; the pie rule applies (White may "swap" on their first turn).

Okimba's rule (designer's BGG wording, item 468749):

- A NAKED DIAGONAL is a pair of like-coloured, diagonally adjacent stones with
  no other like-coloured stone adjacent to both. (This is exactly Rhode's
  "weak pair": the two points adjacent to both are the other two corners of
  their 2x2 square, and neither may hold a friendly stone.)
- On your turn, place a stone of your colour on an empty point. THERE MUST
  NEVER BE MORE THAN ONE NAKED DIAGONAL ON THE BOARD (summed over BOTH
  colours). You cannot pass unless you have no legal move.
- You win if a chain of orthogonally connected stones of your colour touches
  your two opposite edges.

There are NO captures/removals. A crosscut (a 2x2 with two interlocking
opposite-colour naked diagonals) contains TWO naked diagonals at once, so the
"at most one naked diagonal" rule forbids ever completing one — the reason
Okimba needs no removal step and stays drawless without material loss.

Definitive oracle: the designer's own reference implementation `Okimba.html`
(author luigi87 = Bolaños Mures). Key functions cross-checked:
`recheckSquare` (the naked-diagonal test, identical to `_weak_pairs`),
`isValidOkimbaMove` (place, require `nakedDiags[0].size + nakedDiags[1].size
<= 1`, restore — a TOTAL-of-both-colours cap of 1), `checkWin` (post-move
orthogonal edge-to-edge chain), and `play()`, which — unlike Akimbo — does NOT
call `resolveCrosscutsOnBoard`: the stone is simply placed. A player with no
legal move is silently skipped (modelled here as a forced `"pass"`).

Board convention (cells `"c,r"`, c=col, r=row) matches this library's Rhode:
Black joins row 0 to row N-1, White joins col 0 to col N-1.

Termination: Okimba is drawless in real play. As the platform's standard
defensive backstop, a hard ply cap of 8*N*N (and a double pass, reachable only
if both players are simultaneously stuck with nobody connected) is declared an
honest DRAW — never a fabricated winner.

Default board size 11x11 (Okimba's BGG metadata family tag "Components: 11 x 11
Grids"). The reference UI happens to default its dropdown to 13x13; the
designer's published metadata specifies 11, so that is this package's default.
The `size` option offers 9 / 11 / 13.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black connects top<->bottom (rows), White left<->right (cols)

_ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class OkimbaState:
    size: int = 11
    board: dict = field(default_factory=dict)   # (c, r) -> BLACK/WHITE
    to_move: int = BLACK
    last: Optional[tuple] = None   # stone placed by the PREVIOUS mover
    winner: Optional[int] = None
    draw: bool = False
    ply: int = 0
    passes: int = 0                # consecutive passes (both stuck)


def _naked_diagonals(board: dict, player: int) -> list:
    """All naked diagonals of `player`: diagonally adjacent friendly stones
    with no friendly stone orthogonally adjacent to both (i.e. neither of the
    2x2 corners between them is friendly). Each is returned once, as a sorted
    tuple. Identical to Rhode's `_weak_pairs` and to the reference JS
    `recheckSquare` (TL==col && BR==col && TR!=col && BL!=col, and the
    anti-diagonal twin)."""
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


def _naked_count(board: dict) -> int:
    """Total naked diagonals on the board, summed over BOTH colours."""
    return len(_naked_diagonals(board, BLACK)) + len(_naked_diagonals(board, WHITE))


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


class Okimba(Game):
    name = "Okimba"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> OkimbaState:
        size = int((options or {}).get("size", 11))
        return OkimbaState(size=size)

    def current_player(self, s: OkimbaState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def _legal_placements(self, s: OkimbaState) -> list:
        """Empty points where placing the mover's stone leaves at most ONE
        naked diagonal on the whole board (both colours summed). Mirrors the
        reference `isValidOkimbaMove`: place, test the total, restore."""
        me = s.to_move
        out = []
        for r in range(s.size):
            for c in range(s.size):
                if (c, r) in s.board:
                    continue
                s.board[(c, r)] = me
                ok = _naked_count(s.board) <= 1
                del s.board[(c, r)]
                if ok:
                    out.append((c, r))
        return out

    def legal_moves(self, s: OkimbaState) -> list[str]:
        if self.is_terminal(s):
            return []
        placements = self._legal_placements(s)
        moves = [f"{c},{r}" for (c, r) in placements]
        if not moves:
            return ["pass"]          # no legal placement -> forced skip
        if s.ply == 1:
            moves.append("swap")     # pie rule: White's first turn only
        return moves

    # -- move application ---------------------------------------------------

    def apply_move(self, s: OkimbaState, move: str, rng=None) -> OkimbaState:
        if move == "pass":
            return OkimbaState(size=s.size, board=dict(s.board),
                               to_move=1 - s.to_move, last=None,
                               winner=s.winner, draw=s.passes + 1 >= 2,
                               ply=s.ply + 1, passes=s.passes + 1)
        if move == "swap":
            # Pie rule ("swap sides"): White takes over Black's opening.
            # Fixed-seat equivalent: reflect the lone stone across the main
            # diagonal and recolour it — Okimba is symmetric under transpose +
            # colour swap (Black joins rows, White joins columns), so White's
            # position is exactly as strong as Black's was. Recolouring in
            # place would NOT preserve the value (the colours aim at different
            # edges). Same convention as this library's Rhode / Hex / Konobi.
            ((c, r), _owner), = s.board.items()
            return OkimbaState(size=s.size, board={(r, c): s.to_move},
                               to_move=1 - s.to_move, last=(r, c),
                               ply=s.ply + 1)
        me = s.to_move
        board = dict(s.board)
        p = _cell(move)
        board[p] = me                       # place only — Okimba has no removal
        winner = me if _connects(board, me, s.size) else None
        return OkimbaState(size=s.size, board=board, to_move=1 - me,
                           last=p, winner=winner, ply=s.ply + 1, passes=0)

    # -- termination / scoring ----------------------------------------------

    def is_terminal(self, s: OkimbaState) -> bool:
        return s.winner is not None or s.draw or s.ply >= 8 * s.size * s.size

    def returns(self, s: OkimbaState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]   # backstop draw (unreachable under real play)

    # -- bot guidance --------------------------------------------------------

    def heuristic(self, s: OkimbaState) -> list:
        """Connection-distance eval as MCTS payoffs [black, white]: fewest
        additional stones each side needs to join their edges (0-1 BFS; own
        stone = 0, empty = 1, enemy = blocked), squashed to (-1, 1)."""
        db = self._edge_distance(s, BLACK)
        dw = self._edge_distance(s, WHITE)
        import math
        val = math.tanh(0.35 * (dw - db))   # positive = Black ahead
        return [val, -val]

    def _edge_distance(self, s: OkimbaState, player: int) -> float:
        from collections import deque
        n = s.size
        big = n * n
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

    def serialize(self, s: OkimbaState) -> dict:
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

    def deserialize(self, d: dict) -> OkimbaState:
        return OkimbaState(
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

    def describe_move(self, s: OkimbaState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if move == "pass":
            return "pass (forced)"
        return self._coord(_cell(move))

    def render(self, s: OkimbaState, perspective=None) -> dict:
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
