"""Conspirateurs -- a traditional French race game (pre-1800), here following the
nestorgames 2-player edition (Nestor Romeral Andres, 2018).

Conspirateurs resembles Halma / Chinese Checkers: there is NO capturing, and you
win by getting ALL of your "conspirateurs" (men) into the corner/edge SANCTUARIES
("shelter holes") around the rim of the board.

Board: 17x17 square cells. A 9-wide x 5-tall block of cells at the dead centre is
the "secret meeting place" (the drop zone). A ring of SANCTUARY cells sits on the
board perimeter (see SANCTUARIES below).

A game has two phases:

  DROP PHASE -- players alternate placing one man at a time on any vacant cell of
  the 9x5 central area. With 20 men each, that is 40 placements (20 per side)...
  the central area is 45 cells, so the two drops interleave (leaving 5 cells free)
  until each side has placed all 20. No man may move until BOTH sides have finished
  dropping.

  MOVE PHASE -- on your turn you move ONE man, making either:
    (A) a STEP to one of the 8 adjacent (orthogonal/diagonal) EMPTY cells, or
    (B) a JUMP over exactly one adjacent occupied cell (friend OR foe, on a
        sanctuary or not) landing on the EMPTY cell immediately beyond. From the
        landing cell you MAY continue jumping (each hop may change direction); the
        whole chain is ONE move and you may stop after any hop. A jumped man is
        NOT captured (there is no capturing).
  A man that BEGINS the turn already on a sanctuary may NOT move. A move may never
  leave the 17x17 board.

WIN: the first player to have ALL of their men resting on sanctuary cells wins.
A sanctuary holds at most one man (enforced naturally -- cells hold one man).

Moves use the platform's clickable cell-path notation:
  * a DROP is a single cell id, e.g. "8,8".
  * a STEP is "from>to", e.g. "8,7>8,6".
  * a JUMP chain is "from>land>land>...", listing every cell the man lands on.

Player 0 = Black (moves first), Player 1 = White.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 17                      # 17x17 board
MEN = 20                    # men IN PLAY per player (nestorgames 2p edition: 20 men;
                            # the box supplies 21 cones per colour, one spare)
NAMES = {0: "Black", 1: "White"}

# 8 king-move directions.
DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

# Defensive termination: the move phase is a pure race with no captures and a
# "can't move once sheltered" rule, so material only ever flows toward the rim.
# These caps guarantee termination under random play; real games finish far below.
PLY_CAP = 600              # hard cap on TOTAL plies (drop + move) -> draw
NO_PROGRESS_CAP = 60       # move-phase plies with no shelter gained by the mover -> draw


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r) -> bool:
    return 0 <= c < N and 0 <= r < N


# ---- board geometry --------------------------------------------------------

def _center_area() -> set:
    """The central 9-wide x 5-tall drop block (45 cells), centred on the board.

    Cols 4..12 (9 cells), rows 6..10 (5 cells), centred on (8,8)."""
    cells = set()
    c0 = (N - 9) // 2          # 4
    r0 = (N - 5) // 2          # 6
    for c in range(c0, c0 + 9):
        for r in range(r0, r0 + 5):
            cells.add((c, r))
    return cells


def _sanctuaries() -> set:
    """Perimeter sanctuary ("shelter hole") cells.

    RECONSTRUCTED LAYOUT (see rules.md -- flagged for review): the published
    Conspirateurs board marks 39 perimeter cells as shelters. The exact pixel map
    of those 39 cells is not recoverable from the available text sources, so this
    package uses a clean, fully (4-fold + mirror) symmetric reconstruction of
    **40** shelter cells: an L-shaped cluster of 7 in each of the four corners
    plus a 3-cell cluster at the midpoint of each of the four edges. This is
    faithful in spirit (shelters cluster at the corners and edge-midpoints of the
    rim, capacity comfortably exceeds the 20 men a side must shelter) and only the
    decorative count differs from the published 39 by one. The rules of play
    (drop, step/jump, no-capture, all-men-home win) are exact.
    """
    s = set()
    lo = N - 1                 # 16
    # Four corner L-clusters: the corner cell + 3 cells inward along each border.
    for (cc, cr) in [(0, 0), (lo, 0), (0, lo), (lo, lo)]:
        s.add((cc, cr))
        # horizontal arm (along the row at cr)
        for k in range(1, 4):
            s.add((cc + (1 if cc == 0 else -1) * k, cr))
        # vertical arm (along the col at cc)
        for k in range(1, 4):
            s.add((cc, cr + (1 if cr == 0 else -1) * k))
    # Four edge-midpoint clusters: 3 cells centred on each edge's middle.
    mid = N // 2               # 8
    for k in (-1, 0, 1):
        s.add((mid + k, 0))    # top edge
        s.add((mid + k, lo))   # bottom edge
        s.add((0, mid + k))    # left edge
        s.add((lo, mid + k))   # right edge
    return s


CENTER_AREA = _center_area()
SANCTUARIES = _sanctuaries()


@dataclass
class CState:
    board: dict = field(default_factory=dict)      # (c, r) -> player
    to_move: int = 0
    dropped: tuple = (0, 0)                         # men dropped so far per player
    winner: Optional[int] = None
    ply: int = 0
    no_progress: int = 0


def _in_drop_phase(s: CState) -> bool:
    return s.dropped[0] < MEN or s.dropped[1] < MEN


def _sheltered_count(board: dict, player: int) -> int:
    return sum(1 for sq in SANCTUARIES if board.get(sq) == player)


class Conspirateurs(Game):
    uid = "conspirateurs"
    name = "Conspirateurs"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CState:
        return CState(board={}, to_move=0, dropped=(0, 0))

    def current_player(self, s: CState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------

    def _drop_moves(self, s: CState) -> list[str]:
        return [f"{c},{r}" for (c, r) in sorted(CENTER_AREA) if (c, r) not in s.board]

    def _step_targets(self, s: CState, frm):
        c, r = frm
        out = []
        for dc, dr in DIRS:
            t = (c + dc, r + dr)
            if _on(*t) and t not in s.board:
                out.append(t)
        return out

    def _jump_targets(self, s: CState, frm):
        """Every cell reachable from `frm` by one or more jumps. Multi-jumps are
        allowed and the man may stop after any hop, so every reachable landing is
        a legal destination. We enumerate DESTINATIONS (BFS with a global `seen`
        set), not full chains -- this is finite and cheap (a dense chain
        enumeration is combinatorially explosive). The man's start cell is treated
        as vacated for the whole turn. Each destination is emitted as a 2-cell
        `frm>dest` move (the platform's click-source-then-destination path)."""
        board = s.board
        seen = {frm}
        out = []
        stack = [frm]
        while stack:
            c, r = stack.pop()
            for dc, dr in DIRS:
                over = (c + dc, r + dr)
                land = (c + 2 * dc, r + 2 * dr)
                if not _on(*land):
                    continue
                # `over` occupied (start cell counts as vacated), `land` empty.
                over_occ = over != frm and over in board
                land_occ = land != frm and land in board
                if over_occ and not land_occ and land not in seen:
                    seen.add(land)
                    out.append(land)
                    stack.append(land)
        return out

    def _move_phase_moves(self, s: CState) -> list[list]:
        out = []
        for (c, r), pl in s.board.items():
            if pl != s.to_move:
                continue
            # A man that begins the turn on a sanctuary may not move.
            if (c, r) in SANCTUARIES:
                continue
            frm = (c, r)
            for t in self._step_targets(s, frm):
                out.append([frm, t])
            for t in self._jump_targets(s, frm):
                out.append([frm, t])
        return out

    def _has_move(self, s: CState) -> bool:
        """Cheap non-emptiness test for the move phase (a single step or the first
        hop of a jump suffices) -- avoids enumerating full jump chains."""
        board = s.board
        for (c, r), pl in board.items():
            if pl != s.to_move or (c, r) in SANCTUARIES:
                continue
            for dc, dr in DIRS:
                t = (c + dc, r + dr)
                if _on(*t) and t not in board:
                    return True                       # a step
                over = t
                land = (c + 2 * dc, r + 2 * dr)
                if _on(*land) and over in board and land not in board:
                    return True                       # a jump
        return False

    def _draw(self, s: CState) -> bool:
        return s.ply >= PLY_CAP or s.no_progress >= NO_PROGRESS_CAP

    def legal_moves(self, s: CState) -> list[str]:
        if s.winner is not None or self._draw(s):
            return []
        if _in_drop_phase(s):
            return self._drop_moves(s)
        moves = [">".join(f"{c},{r}" for c, r in path)
                 for path in self._move_phase_moves(s)]
        return moves

    def apply_move(self, s: CState, move: str, rng=None) -> CState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        if _in_drop_phase(s):
            # a drop: single vacant central cell
            (c, r) = cells[0]
            board[(c, r)] = s.to_move
            dropped = list(s.dropped)
            dropped[s.to_move] += 1
            dropped = tuple(dropped)
            still_dropping = dropped[0] < MEN or dropped[1] < MEN
            # In the drop phase a side that has finished is simply skipped.
            nxt = 1 - s.to_move
            if still_dropping and dropped[nxt] >= MEN:
                nxt = s.to_move  # the other side is done; keep dropping mine
            return CState(board=board, to_move=nxt, dropped=dropped,
                          winner=None, ply=s.ply + 1, no_progress=0)

        # move phase: relocate the man from path[0] to path[-1] (nothing removed)
        pl = board.pop(cells[0])
        board[cells[-1]] = pl
        before = _sheltered_count(s.board, pl)
        after = _sheltered_count(board, pl)
        progressed = after > before
        no_progress = 0 if progressed else s.no_progress + 1
        winner = pl if after >= MEN else None
        return CState(board=board, to_move=1 - pl, dropped=s.dropped,
                      winner=winner, ply=s.ply + 1, no_progress=no_progress)

    def is_terminal(self, s: CState) -> bool:
        if s.winner is not None or self._draw(s):
            return True
        if _in_drop_phase(s):
            return False                              # drop cells always remain
        return not self._has_move(s)

    def returns(self, s: CState) -> list[float]:
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if self._draw(s):
            return [0.0, 0.0]
        # no legal move (a stuck mover) -> they lose
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: CState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "dropped": list(s.dropped),
            "winner": s.winner,
            "ply": s.ply,
            "no_progress": s.no_progress,
        }

    def deserialize(self, d: dict) -> CState:
        return CState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            dropped=tuple(d.get("dropped", [0, 0])),
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
        )

    def describe_move(self, s: CState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        if _in_drop_phase(s):
            return f"drop {cells[0][0]},{cells[0][1]}"
        # A step lands on a king-adjacent cell (Chebyshev distance 1); anything
        # farther is a jump (destination-only notation).
        cheb = max(abs(cells[-1][0] - cells[0][0]), abs(cells[-1][1] - cells[0][1]))
        sep = "-" if cheb == 1 else "x"
        return sep.join(f"{c},{r}" for c, r in cells)

    def render(self, s: CState, perspective=None) -> dict:
        tints = {}
        for (c, r) in CENTER_AREA:
            tints[f"{c},{r}"] = "#dfeefb"          # drop zone: pale blue
        for (c, r) in SANCTUARIES:
            tints[f"{c},{r}"] = "#ffe9a8"          # shelters: warm gold (drawn over)
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = "Draw (no-progress / ply cap)"
            else:
                caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        elif _in_drop_phase(s):
            caption = (f"{NAMES[s.to_move]} to drop "
                       f"({s.dropped[s.to_move]}/{MEN} placed)")
        else:
            home = _sheltered_count(s.board, s.to_move)
            caption = f"{NAMES[s.to_move]} to move ({home}/{MEN} sheltered)"
        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
