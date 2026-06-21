"""Tanbo (Mark Steere, 1993; re-released with a denser opening April 2026).

A Go-family ROOT-PRUNING game played on an N x N grid of intersections. The
board starts pre-seeded with single-stone "roots" of both colours. On your turn
you GROW one of your own roots by placing a stone, and any root (of EITHER
colour) that can no longer grow is pruned off the board. You win by annihilating
all of your opponent's roots.

This module reuses Atari Go's orthogonal group machinery (`_neighbors` /
`_group`) but the capture rule is fundamentally different: in Tanbo a root is
removed when it is **bounded** (cannot legally grow), NOT when it has zero
liberties. The two notions differ, so the resolution code below is Tanbo's own.

Faithful to Mark Steere's published rules (marksteeregames.com/Tanbo_rules.pdf):

  * ROOT:  a maximally-connected (4-orthogonal) monochrome group of stones,
    possibly a single stone. Roots never merge and new roots are never created.
  * PLACEMENT:  you must place one stone of your colour on an empty point that is
    orthogonally adjacent to EXACTLY ONE of your own on-board stones. (Adjacent
    to two-or-more own stones, or to none, is illegal.) Because the new stone
    touches exactly one own stone, it joins exactly one of your roots -- the
    "current root" you grew this turn.
  * BOUNDED:  a root is "bounded" if there is no empty point that is adjacent to
    exactly one stone of that root and not adjacent to any other stone of that
    root's colour -- i.e. no legal placement exists that would enlarge it.
  * PRUNING:  after your placement, if your CURRENT root is now bounded, you must
    remove your current root (and only it); your turn ends. Otherwise, you must
    remove EVERY OTHER root (of either colour) that is now bounded.
  * WIN:  when all roots of one colour have been removed, the player of the other
    colour wins. A player can win on either player's turn.

See rules.md for the full ruleset and the documented ruleset/interpretation
choices (starting layout, self-capture, termination).

Moves are single-cell placements "c,r" (col, row), 0-indexed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


def _neighbors(c: int, r: int, size: int):
    if c > 0:
        yield (c - 1, r)
    if c < size - 1:
        yield (c + 1, r)
    if r > 0:
        yield (c, r - 1)
    if r < size - 1:
        yield (c, r + 1)


def _group(board: dict, start: tuple[int, int], size: int) -> set:
    """Maximally-connected (4-orthogonal) same-colour root containing `start`."""
    colour = board[start]
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for nb in _neighbors(c, r, size):
            if nb not in seen and board.get(nb) == colour:
                seen.add(nb)
                stack.append(nb)
    return seen


def _all_roots(board: dict, size: int) -> list[set]:
    """Partition the board into its roots (connected monochrome groups)."""
    seen: set = set()
    roots: list[set] = []
    for cell in board:
        if cell in seen:
            continue
        grp = _group(board, cell, size)
        seen |= grp
        roots.append(grp)
    return roots


def _can_grow(board: dict, root: set, size: int) -> bool:
    """True if `root` can still legally grow, i.e. it is NOT bounded.

    A root can grow iff there exists an empty point adjacent to EXACTLY ONE
    stone of this root and adjacent to NO OTHER stone of this root's colour.
    (Placement by the owning player at that point would extend exactly this
    root, which is the only legal kind of growth.)
    """
    if not root:
        return False
    colour = board[next(iter(root))]
    # Candidate empty points: any empty neighbour of a root stone.
    candidates: set = set()
    for c, r in root:
        for nb in _neighbors(c, r, size):
            if nb not in board:
                candidates.add(nb)
    for ec, er in candidates:
        own_adj = 0          # same-colour stones adjacent to this empty point
        in_root_adj = 0      # of those, how many belong to THIS root
        for nb in _neighbors(ec, er, size):
            v = board.get(nb)
            if v == colour:
                own_adj += 1
                if nb in root:
                    in_root_adj += 1
        # Legal growth of THIS root: empty point touches exactly one own stone
        # and that stone is in this root.
        if own_adj == 1 and in_root_adj == 1:
            return True
    return False


def _legal_placement(board: dict, c: int, r: int, mover: int, size: int) -> bool:
    """A placement is legal iff (c,r) is empty and orthogonally adjacent to
    EXACTLY ONE of the mover's own stones."""
    if (c, r) in board:
        return False
    own_adj = 0
    for nb in _neighbors(c, r, size):
        if board.get(nb) == mover:
            own_adj += 1
            if own_adj > 1:
                return False
    return own_adj == 1


def _resolve(board: dict, c: int, r: int, mover: int, size: int) -> dict:
    """Apply a legal placement of `mover` at (c, r) on a COPY of `board` and
    prune bounded roots per Tanbo rules. Returns the new board.

    Caller guarantees the placement is legal. The new stone joins exactly one of
    the mover's roots (the CURRENT root). If that current root is bounded after
    the placement, only it is removed; otherwise every OTHER bounded root (of
    either colour) is removed.
    """
    nb = dict(board)
    nb[(c, r)] = mover
    current_root = _group(nb, (c, r), size)
    if not _can_grow(nb, current_root, size):
        # Current-root capture: remove the current root only.
        for cell in current_root:
            del nb[cell]
        return nb
    # Non-current-roots capture: remove every other bounded root.
    to_remove: list[set] = []
    for root in _all_roots(nb, size):
        if root == current_root:
            continue
        if not _can_grow(nb, root, size):
            to_remove.append(root)
    for root in to_remove:
        for cell in root:
            del nb[cell]
    return nb


def _has_colour(board: dict, colour: int) -> bool:
    for v in board.values():
        if v == colour:
            return True
    return False


def _seed_layout(size: int) -> dict:
    """The 2026 dense Tanbo opening: single-stone roots on the even sublattice,
    coloured as a checkerboard, with one empty point between adjacent stones.

    Stones occupy points (c, r) with both c and r even; colour = (i + j) % 2 over
    the sublattice indices (i = c // 2, j = r // 2). On an odd board this is
    point-symmetric, Black gets one more seed than White on sizes where the
    sublattice count is odd (e.g. 9x9, 13x13) -- Black also moves first.
    """
    board: dict = {}
    coords = list(range(0, size, 2))  # 0,2,4,... up to size-1 (size odd)
    for j, r in enumerate(coords):
        for i, c in enumerate(coords):
            board[(c, r)] = (i + j) % 2
    return board


def _board_key(board: dict, size: int) -> str:
    return "".join(
        "." if (c, r) not in board else ("B" if board[(c, r)] == BLACK else "W")
        for r in range(size)
        for c in range(size)
    )


@dataclass
class TanboState:
    size: int = 11
    board: dict = field(default_factory=dict)  # (c, r) -> 0/1
    to_move: int = BLACK
    winner: Optional[int] = None
    last_move: Optional[tuple] = None
    ply: int = 0
    no_move_loss: bool = False  # player to move has no legal placement -> loses
    cap_draw: bool = False      # ply-cap safety net reached (draw)


class Tanbo(Game):
    uid = "tanbo"
    name = "Tanbo"

    # Hard ply cap (draw safety net). Each ply either grows a root or prunes one;
    # the game provably terminates, but the conformance harness wants a guaranteed
    # bound under random play. This cap is far above any real game length.
    PLY_CAP = 4000

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> TanboState:
        size = int((options or {}).get("size", 11))
        if size % 2 == 0:
            size += 1  # Tanbo boards are odd; keep the seeding symmetric.
        s = TanboState(size=size, board=_seed_layout(size))
        return s

    def current_player(self, s: TanboState) -> int:
        return s.to_move

    def _legal_cells(self, s: TanboState):
        for r in range(s.size):
            for c in range(s.size):
                if _legal_placement(s.board, c, r, s.to_move, s.size):
                    yield (c, r)

    def legal_moves(self, s: TanboState) -> list[str]:
        if s.winner is not None or s.no_move_loss:
            return []
        return [f"{c},{r}" for (c, r) in self._legal_cells(s)]

    def apply_move(self, s: TanboState, move: str, rng=None) -> TanboState:
        c, r = _cell(move)
        nb = _resolve(s.board, c, r, s.to_move, s.size)
        ply = s.ply + 1
        winner: Optional[int] = None
        # Win: an opponent colour fully annihilated.
        if not _has_colour(nb, BLACK):
            winner = WHITE
        elif not _has_colour(nb, WHITE):
            winner = BLACK
        nxt = TanboState(
            size=s.size,
            board=nb,
            to_move=1 - s.to_move,
            winner=winner,
            last_move=(c, r),
            ply=ply,
        )
        if winner is None:
            if ply >= self.PLY_CAP:
                # Draw safety net (practically unreachable; Tanbo games are short).
                nxt.cap_draw = True
            elif not any(True for _ in self._legal_cells(nxt)):
                # Player to move has no legal placement -> they lose.
                nxt.no_move_loss = True
        return nxt

    def is_terminal(self, s: TanboState) -> bool:
        return s.winner is not None or s.no_move_loss or s.cap_draw

    def returns(self, s: TanboState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        if s.no_move_loss:
            loser = s.to_move
            return [-1.0, 1.0] if loser == BLACK else [1.0, -1.0]
        return [0.0, 0.0]

    def serialize(self, s: TanboState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "last_move": list(s.last_move) if s.last_move is not None else None,
            "ply": s.ply,
            "no_move_loss": s.no_move_loss,
            "cap_draw": s.cap_draw,
        }

    def deserialize(self, d: dict) -> TanboState:
        return TanboState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            last_move=tuple(d["last_move"]) if d.get("last_move") is not None else None,
            ply=d.get("ply", 0),
            no_move_loss=d.get("no_move_loss", False),
            cap_draw=d.get("cap_draw", False),
        )

    def describe_move(self, s: TanboState, move: str) -> str:
        c, r = _cell(move)
        letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"  # Go convention skips 'I'
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{s.size - r}"

    def render(self, s: TanboState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        highlights = []
        if s.last_move is not None and s.last_move in s.board:
            highlights.append(
                {"cell": f"{s.last_move[0]},{s.last_move[1]}", "kind": "last-move"}
            )
        if s.winner is not None:
            caption = f"{names[s.winner]} wins (opponent annihilated)"
        elif s.no_move_loss:
            caption = f"{names[s.to_move]} has no legal move and loses"
        elif s.cap_draw:
            caption = "Draw (ply cap)"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
