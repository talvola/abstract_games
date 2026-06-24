"""Gess — the Go+chess hybrid with 3x3 "footprint" pieces (the Archimedeans,
Cambridge, 1994).

Two players, Black (player 0, bottom) and White (player 1, top), play on the
**20x20 grid of CELLS** internally; the inner **18x18** (c,r in 1..18) is the
playable area, and the outer ring (c in {0,19} or r in {0,19}) is the BORDER /
kill-zone. Black moves first. Coordinates are 0-indexed `(c, r)`; cell strings
are `"c,r"`.

A "piece" is not a fixed object: each turn a player picks ANY 3x3 block of cells
(identified by its CENTER, which must be an inner cell 1..18) such that the 3x3
contains only that player's stones (zero enemy), and at least one of the 8 cells
around the center holds a stone of theirs. The center may be empty or hold a
stone.

Each OCCUPIED outer cell of the 3x3 enables movement in that cell's compass
direction (corner -> diagonal, edge -> orthogonal). Range: center OCCUPIED ->
unlimited; center EMPTY -> at most 3. The footprint translates as a rigid unit,
one cell at a time; it advances while the footprint contains no non-carried
stone and stops at the first step where the footprint covers any non-carried
stone (own or enemy both block), or it may stop earlier on a clear square. The
center must remain on the inner board.

When the piece stops, ALL non-carried stones in the destination 3x3 are removed
(self-capture is legal). Then the carried stones are placed at their original
offsets; any that land on a border cell vanish (border kill).

A RING = a 3x3 whose 8 outer cells all hold YOUR stones and whose center is
EMPTY. After a move resolves: if the MOVER has zero rings, the mover LOSES (even
if the opponent is also ringless); else if the OPPONENT has zero rings, the
opponent loses (mover wins).

Move strings are `"cx,cy>dx,dy"` (footprint center source -> destination); the
direction and distance are implied by the vector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 20          # full grid 0..19
INNER_LO = 1    # inclusive inner-board bound
INNER_HI = 18   # inclusive inner-board bound

BLACK, WHITE = 0, 1
NAMES = {BLACK: "Black", WHITE: "White"}

# The 8 compass directions, indexed by the 3x3 outer-cell offset that enables
# them: offset (dc,dr) relative to center -> that same (dc,dr) is the direction.
DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

# Termination safeguards (NOT part of original Gess — see rules.md).
NO_PROGRESS_CAP = 60   # plies with no capture -> draw
HARD_PLY_CAP = 400     # absolute ply cap -> draw


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _s(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _file(c) -> str:
    # files a..t for c 0..19
    return "abcdefghijklmnopqrst"[c]


def _alg(cell) -> str:
    # file-letter + 1-based row, e.g. (11,2) -> "l3"
    return f"{_file(cell[0])}{cell[1] + 1}"


def _is_inner(c, r) -> bool:
    return INNER_LO <= c <= INNER_HI and INNER_LO <= r <= INNER_HI


def _is_border(c, r) -> bool:
    return c == 0 or c == N - 1 or r == 0 or r == N - 1


def _start_board() -> dict:
    """The standard 43-stone-per-side opening, vertically mirror-symmetric.

    Black (bottom):
      row 2 (r=1): c in {2,4,6,7,8,9,10,11,12,13,15,17}
      row 3 (r=2): c in {1,2,3,5,7,8,9,10,12,14,16,17,18}
      row 4 (r=3): c in {2,4,6,7,8,9,10,11,12,13,15,17}
      row 7 (r=6): c in {2,5,8,11,14,17}
    White = vertical mirror (r -> 19-r), same files.
    Black ring center l3 = (11,2); White ring center l18 = (11,17).
    """
    b = {}
    black = set()
    for c in [2, 4, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17]:
        black.add((c, 1))
    for c in [1, 2, 3, 5, 7, 8, 9, 10, 12, 14, 16, 17, 18]:
        black.add((c, 2))
    for c in [2, 4, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17]:
        black.add((c, 3))
    for c in [2, 5, 8, 11, 14, 17]:
        black.add((c, 6))
    for cell in black:
        b[cell] = BLACK
    for (c, r) in black:
        b[(c, N - 1 - r)] = WHITE
    return b


@dataclass
class CState:
    board: dict = field(default_factory=dict)   # (c,r) -> owner (0/1)
    to_move: int = 0
    winner: Optional[int] = None                 # set on a win event
    draw: bool = False
    no_progress: int = 0                         # plies since last capture
    ply: int = 0                                 # total plies played


def _count_rings(board: dict, player: int) -> int:
    """Number of rings owned by `player`: a 3x3 with 8 outer cells = player's
    stones and an EMPTY center. Centers are inner cells (1..18)."""
    n = 0
    for cx in range(INNER_LO, INNER_HI + 1):
        for cy in range(INNER_LO, INNER_HI + 1):
            if (cx, cy) in board:
                continue  # center must be empty
            ok = True
            for dc, dr in DIRS:
                if board.get((cx + dc, cy + dr)) != player:
                    ok = False
                    break
            if ok:
                n += 1
    return n


class Gess(Game):
    uid = "gess"
    name = "Gess"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CState:
        return CState(board=_start_board())

    def current_player(self, s: CState) -> int:
        return s.to_move

    # ---- footprint helpers ------------------------------------------------
    @staticmethod
    def _footprint_owner(board, cx, cy, player):
        """If the 3x3 centered at (cx,cy) is a legal footprint for `player`,
        return the set of carried-stone offsets (dc,dr) that hold the player's
        stones (including center if occupied). Otherwise return None.

        Legal: (a) center inner; (b) only player's stones in the 3x3 (no enemy);
        (c) at least one of the 8 surrounding cells holds the player's stone.
        """
        if not _is_inner(cx, cy):
            return None
        carried = []
        surround = False
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                occ = board.get((cx + dc, cy + dr))
                if occ is None:
                    continue
                if occ != player:
                    return None  # enemy stone in the footprint -> illegal
                carried.append((dc, dr))
                if not (dc == 0 and dr == 0):
                    surround = True
        if not surround:
            return None
        return carried

    def _gen_from_center(self, s: CState, cx, cy):
        """Generate all legal moves (as (dx,dy) destination centers) for the
        footprint centered at (cx,cy), if it is a legal footprint."""
        board = s.board
        player = s.to_move
        carried = self._footprint_owner(board, cx, cy, player)
        if carried is None:
            return []
        carried_set = set(carried)
        center_occupied = (0, 0) in carried_set
        max_dist = N if center_occupied else 3

        # enabled directions: an OCCUPIED outer cell enables its own direction
        dirs = [(dc, dr) for (dc, dr) in DIRS if (dc, dr) in carried_set]

        # carried absolute SOURCE cells: lifted off the board for this move, so
        # they never count as blockers (the piece slides out from under itself).
        carried_cells = [(cx + oc, cy + orr) for (oc, orr) in carried]
        lifted = set(carried_cells)

        out = []
        for (dc, dr) in dirs:
            for k in range(1, max_dist + 1):
                ncx, ncy = cx + dc * k, cy + dr * k
                if not _is_inner(ncx, ncy):
                    break  # center must stay inner
                # Does the footprint at this step (the 3x3 around (ncx,ncy))
                # overlap any stone that is NOT part of this piece? The piece's
                # carried stones are lifted off the board for the move, so only
                # their SOURCE cells (`lifted`) are exempt — every other on-board
                # stone in the footprint is a real blocker, INCLUDING one that
                # happens to sit where a carried stone would land (a leading
                # carried stone bumping into an enemy/own stone must STOP there,
                # not slide through it). Exempting the carried stones' *projected*
                # cells would mask exactly that collision, so we do not.
                blocked = False
                for fdc in (-1, 0, 1):
                    for fdr in (-1, 0, 1):
                        cell = (ncx + fdc, ncy + fdr)
                        if cell in lifted:
                            continue  # one of this piece's lifted source cells
                        if cell in board:
                            blocked = True
                            break
                    if blocked:
                        break
                # this step is a legal stop (clear or a collision-stop)
                out.append((ncx, ncy))
                if blocked:
                    break  # must stop here; cannot advance further
        return out

    def _gen_moves(self, s: CState):
        """All legal moves as (src_center, dst_center) tuples."""
        moves = []
        for cx in range(INNER_LO, INNER_HI + 1):
            for cy in range(INNER_LO, INNER_HI + 1):
                for (dx, dy) in self._gen_from_center(s, cx, cy):
                    moves.append(((cx, cy), (dx, dy)))
        return moves

    def legal_moves(self, s: CState):
        if self.is_terminal(s):
            return []
        return [f"{_s(src)}>{_s(dst)}" for (src, dst) in self._gen_moves(s)]

    # ---- applying a move --------------------------------------------------
    def apply_move(self, s: CState, move: str, rng=None) -> CState:
        src_s, dst_s = move.split(">")
        cx, cy = _cell(src_s)
        ndx, ndy = _cell(dst_s)
        player = s.to_move
        board = dict(s.board)

        carried = self._footprint_owner(board, cx, cy, player)
        # carried absolute source cells
        carried_cells = [(cx + oc, cy + orr) for (oc, orr) in carried]
        offsets = list(carried)  # (dc,dr) offsets relative to center

        # LIFT carried stones off the board
        for cell in carried_cells:
            del board[cell]

        # CAPTURE: remove all (remaining) stones lying in the destination 3x3
        captured = 0
        for fdc in (-1, 0, 1):
            for fdr in (-1, 0, 1):
                cell = (ndx + fdc, ndy + fdr)
                if cell in board:
                    del board[cell]
                    captured += 1

        # PLACE carried stones at destination in original relative offsets,
        # then BORDER-KILL any that land on a border cell.
        for (oc, orr) in offsets:
            tc, tr = ndx + oc, ndy + orr
            if _is_border(tc, tr):
                continue  # shoved off the edge -> vanishes
            board[(tc, tr)] = player

        # Resolve rings & win (mover evaluated first).
        opp = 1 - player
        mover_rings = _count_rings(board, player)
        opp_rings = _count_rings(board, opp)
        winner = None
        if mover_rings == 0:
            winner = opp           # mover stranded itself -> mover loses
        elif opp_rings == 0:
            winner = player        # opponent ringless -> mover wins

        no_progress = 0 if captured else s.no_progress + 1
        ply = s.ply + 1
        draw = False
        if winner is None:
            if no_progress >= NO_PROGRESS_CAP or ply >= HARD_PLY_CAP:
                draw = True

        return CState(board=board, to_move=opp, winner=winner, draw=draw,
                      no_progress=no_progress, ply=ply)

    def is_terminal(self, s: CState) -> bool:
        if s.winner is not None or s.draw:
            return True
        # a side with no legal move cannot occur in normal play (a player with a
        # ring always has at least that footprint to move), but guard anyway.
        return not self._gen_moves(s)

    def returns(self, s: CState):
        if s.draw:
            return [0.0, 0.0]
        if s.winner is not None:
            w = s.winner
        else:
            # side to move has no move -> it loses
            w = 1 - s.to_move
        return [1.0, -1.0] if w == BLACK else [-1.0, 1.0]

    # ---- serialization ----------------------------------------------------
    def serialize(self, s: CState) -> dict:
        return {
            "board": {_s(k): v for k, v in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "no_progress": s.no_progress,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> CState:
        return CState(
            board={_cell(k): int(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            draw=d.get("draw", False),
            no_progress=d.get("no_progress", 0),
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: CState, move: str) -> str:
        src_s, dst_s = move.split(">")
        src, dst = _cell(src_s), _cell(dst_s)
        # detect a capture: any opponent stone in the destination 3x3 (carried
        # cells are the mover's own; the move always self-captures none of its
        # own carried stones, but may self-capture other own stones too).
        player = s.to_move
        carried = self._footprint_owner(s.board, src[0], src[1], player) or []
        carried_dst = set((dst[0] + oc, dst[1] + orr) for (oc, orr) in carried)
        cap = False
        for fdc in (-1, 0, 1):
            for fdr in (-1, 0, 1):
                cell = (dst[0] + fdc, dst[1] + fdr)
                if cell in carried_dst:
                    continue
                if cell in s.board:
                    cap = True
        sep = "x" if cap else "-"
        return f"{_alg(src)}{sep}{_alg(dst)}"

    # ---- rendering --------------------------------------------------------
    def render(self, s: CState, perspective=None) -> dict:
        pieces = [{"cell": _s(cell), "owner": owner}
                  for cell, owner in s.board.items()]
        # tint the border kill-zone lightly so the twilight ring is visible
        tints = {}
        for c in range(N):
            for r in range(N):
                if _is_border(c, r):
                    tints[_s((c, r))] = "#e6ddc4"
        if s.winner is not None:
            cap = f"{NAMES[s.winner]} wins"
        elif s.draw:
            cap = "Draw"
        elif self.is_terminal(s):
            cap = f"{NAMES[1 - s.to_move]} wins (no moves)"
        else:
            br = _count_rings(s.board, BLACK)
            wr = _count_rings(s.board, WHITE)
            cap = (f"{NAMES[s.to_move]} to move  ·  "
                   f"rings B {br} / W {wr}")
        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
