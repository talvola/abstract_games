"""Akimbo — a drawless square-board connection game by Luis Bolaños Mures (2026).

Akimbo is the direct successor of the same designer's Rhode (2016): same board
model, same "naked diagonal" / crosscut machinery, same edges and pie rule.
Where Rhode FORCES you to consolidate diagonal links (spending a whole turn),
Akimbo instead simply CONSTRAINS how many unconsolidated diagonals may exist:

- Black (player 0) owns the TOP and BOTTOM edges → wins by an orthogonal chain
  joining row 0 to row N-1. White (player 1) owns the LEFT and RIGHT edges →
  wins by an orthogonal chain joining col 0 to col N-1. Diagonal adjacency does
  NOT connect. Black moves first; the pie rule applies (White may "swap" on
  their first turn).

- A NAKED DIAGONAL of colour C is a 2×2 square in which one diagonal pair are
  both C and BOTH of the other two corners are ≠ C (empty or the opposite
  colour). This is exactly Rhode's "weak pair".

- A CROSSCUT is a 2×2 of four stones forming two interlocking opposite-colour
  naked diagonals (two black diagonally adjacent, two white diagonally adjacent).

RULES (as implemented, verified against the designer's own reference JavaScript
`Akimbo.html`, author luigi87 = Bolaños Mures — the definitive oracle):

- LEGALITY (`isValidAkimboMove`): you place a stone of your colour on an empty
  point; the placement is legal iff, *immediately after placing and BEFORE any
  crosscut removal*, the number of naked diagonals of EACH colour separately is
  ≤ 1. I.e. count_naked(BLACK) ≤ 1 AND count_naked(WHITE) ≤ 1. The bound must
  hold "not even momentarily" before removal — so it is checked on the raw
  post-placement board. (Placing your stone can only change your own colour's
  naked count, never the opponent's, so the opponent bound is invariant; the
  reference checks both and so do we.)

- PLACEMENT RESOLUTION (`resolveCrosscutsOnBoard`): after a legal placement at
  p, for EVERY crosscut 2×2 that CONTAINS p, remove YOUR OTHER stone in that
  crosscut (the corner that is your colour and is not p). p is never removed;
  opponent stones are never removed. A stone shared by two such crosscuts is
  removed once. Only crosscuts touching p are resolved — on reachable boards
  that is the only place a crosscut can be (see termination note).

- WIN CHECK (`checkWin`): tested AFTER the removal step, for the mover only
  (the move only adds/removes the mover's stones, so only the mover can newly
  connect). A removal can, in principle, break a chain the placement just made.

- PIE RULE: on White's first turn only, White may "swap". Fixed-seat,
  value-preserving implementation identical to Rhode: reflect Black's lone
  opening stone across the main diagonal and recolour it White (Akimbo is
  symmetric under transpose + colour swap, since Black joins rows and White
  joins columns). The reference is a hotseat that swaps physical sides; the
  transpose+recolour is the fixed-seat equivalent.

Board size: default 13×13 (the reference implementation's default); a `size`
option offers 9/11/13.

Termination: Akimbo is drawless in real play. The ≤1-per-colour bound means at
most one naked diagonal of each colour exists after any placement, hence at
most one crosscut, and it must touch the placed stone (else it pre-existed on a
board that induction shows is crosscut-free), so it is always resolved — the
board is crosscut-free at the start of every turn, and a crosscut-free full
board has exactly one winning chain. As the standard defensive backstop, a hard
ply cap of 8·N·N (or a double pass, reachable only from constructed near-full
boards where a player has no legal placement) is scored as an honest DRAW; a
winner is never fabricated. Seeded random playouts (selftest.py) terminate far
below the cap with zero draws.

Sources: the designer's reference JS `Akimbo.html` (luigi87 / Bolaños Mures) and
BGG item 466041 ("Akimbo", 2026). Successor to Rhode (BGG thread 1593043).
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
class AkimboState:
    size: int = 13
    board: dict = field(default_factory=dict)   # (c, r) -> BLACK/WHITE
    to_move: int = BLACK
    last: Optional[tuple] = None   # stone placed by the PREVIOUS mover
    winner: Optional[int] = None
    draw: bool = False
    ply: int = 0
    passes: int = 0                # consecutive passes (constructed boards only)


def _is_crosscut(board: dict, c: int, r: int) -> bool:
    """Is the 2x2 square with lower-left corner (c, r) a crosscut? (Two
    diagonally adjacent black stones and two diagonally adjacent white stones.)"""
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


def _naked_diagonals(board: dict, player: int) -> list:
    """All naked diagonals of `player` (Rhode's 'weak pairs', identical
    definition): a diagonally adjacent friendly pair such that NEITHER of the
    two other corners of their 2x2 square is friendly (each corner is empty or
    the opposite colour). Each naked diagonal is returned once as a sorted
    tuple. Mirrors the reference `recheckSquare`: TypeA naked-for-col iff
    TL==col && BR==col && TR!=col && BL!=col (and the TypeB twin)."""
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


def _count_naked(board: dict, player: int) -> int:
    return len(_naked_diagonals(board, player))


def _is_legal_placement(board: dict, p: tuple, player: int) -> bool:
    """Akimbo legality (`isValidAkimboMove`): place `player` at empty point p;
    legal iff, on the raw post-placement board (BEFORE any crosscut removal),
    count_naked(BLACK) <= 1 AND count_naked(WHITE) <= 1. Mutates `board` and
    restores it (caller passes a throwaway copy or is fine with restore)."""
    if p in board:
        return False
    board[p] = player
    ok = _count_naked(board, BLACK) <= 1 and _count_naked(board, WHITE) <= 1
    del board[p]
    return ok


def _removals(board: dict, placed: tuple, player: int) -> set:
    """Crosscut resolution (`resolveCrosscutsOnBoard`): for every crosscut 2x2
    that CONTAINS the just-placed point, remove `player`'s OTHER stone in it
    (the placed stone is exempt; enemy stones stay). Only squares touching
    `placed` are scanned — the faithful port of the reference's local scan."""
    px, pr = placed
    out = set()
    for c in (px - 1, px):
        for r in (pr - 1, pr):
            if _is_crosscut(board, c, r):
                for cell in ((c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)):
                    if board.get(cell) == player and cell != placed:
                        out.add(cell)
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


class Akimbo(Game):
    name = "Akimbo"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AkimboState:
        size = int((options or {}).get("size", 13))
        return AkimboState(size=size)

    def current_player(self, s: AkimboState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def legal_moves(self, s: AkimboState) -> list[str]:
        if self.is_terminal(s):
            return []
        me = s.to_move
        b = dict(s.board)                # one throwaway copy, mutated+restored
        moves = [f"{c},{r}"
                 for r in range(s.size) for c in range(s.size)
                 if (c, r) not in s.board and _is_legal_placement(b, (c, r), me)]
        if not moves:
            return ["pass"]              # no legal placement -> forced skip
        if s.ply == 1:
            moves.append("swap")         # pie rule: White's first turn only
        return moves

    # -- move application ---------------------------------------------------

    def apply_move(self, s: AkimboState, move: str, rng=None) -> AkimboState:
        if move == "pass":
            return AkimboState(size=s.size, board=dict(s.board),
                               to_move=1 - s.to_move, last=None,
                               winner=s.winner, draw=s.passes + 1 >= 2,
                               ply=s.ply + 1, passes=s.passes + 1)
        if move == "swap":
            # Pie rule ("change sides"): White takes over Black's opening.
            # Fixed-seat equivalent: reflect the lone stone across the main
            # diagonal and recolour it — Akimbo is symmetric under transpose +
            # colour swap (Black joins rows, White joins columns), so White's
            # position is exactly as strong as Black's was.
            ((c, r), _owner), = s.board.items()
            return AkimboState(size=s.size, board={(r, c): s.to_move},
                               to_move=1 - s.to_move, last=(r, c),
                               ply=s.ply + 1)
        me = s.to_move
        board = dict(s.board)
        p = _cell(move)
        board[p] = me
        for dead in _removals(board, p, me):
            del board[dead]
        winner = me if _connects(board, me, s.size) else None
        return AkimboState(size=s.size, board=board, to_move=1 - me,
                           last=p, winner=winner, ply=s.ply + 1, passes=0)

    # -- termination / scoring ----------------------------------------------

    def is_terminal(self, s: AkimboState) -> bool:
        return s.winner is not None or s.draw or s.ply >= 8 * s.size * s.size

    def returns(self, s: AkimboState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]   # backstop draw (unreachable under real play)

    # -- bot guidance --------------------------------------------------------

    def heuristic(self, s: AkimboState) -> list:
        """Connection-distance eval as MCTS payoffs [black, white]: fewest
        additional stones each side needs to join their edges (0-1 BFS; own
        stone = 0, empty = 1, enemy = blocked), squashed to (-1, 1)."""
        db = self._edge_distance(s, BLACK)
        dw = self._edge_distance(s, WHITE)
        import math
        val = math.tanh(0.35 * (dw - db))   # positive = Black ahead
        return [val, -val]

    def _edge_distance(self, s: AkimboState, player: int) -> float:
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

    def serialize(self, s: AkimboState) -> dict:
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

    def deserialize(self, d: dict) -> AkimboState:
        return AkimboState(
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

    def describe_move(self, s: AkimboState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        if move == "pass":
            return "pass (forced)"
        p = _cell(move)
        me = s.to_move
        text = self._coord(p)
        b2 = dict(s.board)
        b2[p] = me
        dead = _removals(b2, p, me)
        if dead:
            text += f" (removes {', '.join(self._coord(x) for x in sorted(dead))})"
        return text

    def render(self, s: AkimboState, perspective=None) -> dict:
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
