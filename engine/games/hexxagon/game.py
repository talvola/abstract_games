"""Hexxagon — the hexagonal Ataxx variant (clone / jump / infection).

Played on a hexagon-of-hexes ("hexhex") of side length 5 (61 cells), minus 3
blocked "holes" near the center, leaving 58 playable hexes. Axial coordinates
(q, r); a cell is on the board iff max(|q|, |r|, |q+r|) <= 4. Hex distance is
(|dq| + |dr| + |dq+dr|) // 2.

Each player starts with 3 pieces on alternating corners. On your turn you move
ONE of your pieces onto an EMPTY (non-hole) cell, of two kinds:

  (A) GROW / clone — the target is at hex distance 1 (one of the 6 adjacent
      hexes). A NEW piece of your colour appears there; the source STAYS
      (n -> n+1).
  (B) JUMP — the target is at hex distance EXACTLY 2 (the second ring, 12 hexes).
      The piece RELOCATES: the source becomes empty, count unchanged.

After the piece lands (either kind), EVERY opponent piece in the 6 hexes adjacent
to the DESTINATION flips to your colour (the "infection"). Holes are never
neighbours, never legal targets, and never hold a piece.

A move is encoded as the path "src>dst" (both "q,r").

If a player has at least one legal move they must move; with NO legal move they
PASS (turn skipped). The game ends when the board is full, neither player can
move, or a player is eliminated. When a move WIPES OUT the opponent, the survivor
auto-fills every remaining empty (non-hole) cell. Winner = most pieces; equal =
draw (a tie is possible — 58 playable cells is even).

Termination: each grow adds a piece (board bounded at 58); jumps and flips never
reduce the total, so play can't cycle. A defensive hard ply cap also forces an
end-and-count.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from agp.game import Game

SIDE = 5            # hexhex side length -> 61 cells
N = SIDE - 1        # extreme coordinate magnitude (4)
NAMES = {0: "Red", 1: "Blue"}
HOLE_COLOR = "#2b2b2b"
PLY_CAP = 2000      # defensive: end-and-count if play runs absurdly long

# 6 hex-neighbour directions (axial). Used for grow targets AND infection.
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

# The 3 default "holes": 3 of the 6 cells adjacent to center (0,0), at alternating
# 120deg positions -> 3-fold rotationally symmetric, center stays playable.
STANDARD_HOLES = frozenset({(1, 0), (-1, 1), (0, -1)})


@lru_cache(maxsize=None)
def _all_cells() -> tuple:
    """All 61 on-board axial cells of the side-5 hexhex."""
    out = []
    for q in range(-N, N + 1):
        for r in range(-N, N + 1):
            if max(abs(q), abs(r), abs(q + r)) <= N:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _all_cell_set() -> frozenset:
    return frozenset(_all_cells())


# The 6 corners of the hexagon, listed in cyclic (angular) order. Assigning
# ownership alternately around this ring gives each player 3 non-adjacent corners
# (every piece sits opposite an enemy at hex distance 4).
CORNERS_CYCLIC = ((0, -N), (N, -N), (N, 0), (0, N), (-N, N), (-N, 0))
P0_CORNERS = CORNERS_CYCLIC[0::2]   # (0,-4), (4,0), (-4,4)
P1_CORNERS = CORNERS_CYCLIC[1::2]   # (4,-4), (0,4), (-4,0)


def _holes_for(name: str) -> frozenset:
    return STANDARD_HOLES if name == "standard" else frozenset()


def _playable(holes: frozenset) -> frozenset:
    return _all_cell_set() - holes


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def _hex_dist(a, b) -> int:
    dq, dr = a[0] - b[0], a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def _grow_targets(q, r, playable):
    """On-board, non-hole cells at hex distance 1 (the 6 neighbours)."""
    for dq, dr in DIRS:
        cc = (q + dq, r + dr)
        if cc in playable:
            yield cc


def _jump_targets(q, r, playable):
    """On-board, non-hole cells at hex distance exactly 2 (the 12-cell ring)."""
    for dq in range(-2, 3):
        for dr in range(-2, 3):
            if _hex_dist((0, 0), (dq, dr)) != 2:
                continue
            cc = (q + dq, r + dr)
            if cc in playable:
                yield cc


def _moves_for(board: dict, player: int, playable: frozenset):
    """All legal (src, dst, kind) moves for `player`."""
    moves = []
    for (q, r), p in board.items():
        if p != player:
            continue
        for tc in _grow_targets(q, r, playable):
            if tc not in board:
                moves.append(((q, r), tc, "grow"))
        for tc in _jump_targets(q, r, playable):
            if tc not in board:
                moves.append(((q, r), tc, "jump"))
    return moves


def _flip_neighbours(board: dict, cell, player: int, playable: frozenset) -> list:
    """Opponent pieces in the 6 hexes adjacent to `cell` that flip to `player`."""
    q, r = cell
    out = []
    for dq, dr in DIRS:
        cc = (q + dq, r + dr)
        if cc in playable and board.get(cc) == 1 - player:
            out.append(cc)
    return out


@dataclass
class HexxagonState:
    board: dict = field(default_factory=dict)   # (q, r) -> player (0/1)
    holes: frozenset = STANDARD_HOLES
    to_move: int = 0
    ply: int = 0


class Hexxagon(Game):
    uid = "hexxagon"
    name = "Hexxagon"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HexxagonState:
        opts = options or {}
        holes = _holes_for(str(opts.get("holes", "standard")))
        board = {}
        for c in P0_CORNERS:
            board[c] = 0
        for c in P1_CORNERS:
            board[c] = 1
        return HexxagonState(board=board, holes=holes, to_move=0, ply=0)

    def current_player(self, s: HexxagonState) -> int:
        return s.to_move

    def _board_full(self, s: HexxagonState) -> bool:
        return len(s.board) >= len(_playable(s.holes))

    def is_terminal(self, s: HexxagonState) -> bool:
        if s.ply >= PLY_CAP:
            return True
        if self._board_full(s):
            return True
        playable = _playable(s.holes)
        return (not _moves_for(s.board, 0, playable)
                and not _moves_for(s.board, 1, playable))

    def legal_moves(self, s: HexxagonState) -> list[str]:
        if self.is_terminal(s):
            return []
        playable = _playable(s.holes)
        mine = _moves_for(s.board, s.to_move, playable)
        if mine:
            return [f"{sq},{sr}>{tq},{tr}" for (sq, sr), (tq, tr), _ in mine]
        # no move -> we pass (the opponent must have a move, else terminal)
        return ["pass"]

    def apply_move(self, s: HexxagonState, move: str, rng=None) -> HexxagonState:
        if move == "pass":
            return HexxagonState(board=dict(s.board), holes=s.holes,
                                 to_move=1 - s.to_move, ply=s.ply + 1)
        src_s, dst_s = move.split(">")
        src = _cell(src_s)
        dst = _cell(dst_s)
        playable = _playable(s.holes)
        board = dict(s.board)
        dist = _hex_dist(src, dst)
        # place / relocate
        if dist == 2:           # JUMP: source vacates
            del board[src]
        # (dist == 1 GROW: source piece stays)
        board[dst] = s.to_move
        # infection: flip every adjacent opponent piece
        for fc in _flip_neighbours(board, dst, s.to_move, playable):
            board[fc] = s.to_move
        # Elimination: if this move WIPED OUT the opponent (they had pieces before
        # and none after), the survivor auto-fills every empty playable cell (the
        # arcade-Ataxx / Hexxagon "fills the board automatically" rule). On a board
        # with holes an unreachable empty region would otherwise stay empty, so
        # this matters. Guarded on "had pieces before" so it never fires from a
        # synthetic one-colour position.
        opp = 1 - s.to_move
        opp_before = any(p == opp for p in s.board.values())
        if opp_before and not any(p == opp for p in board.values()):
            for cc in playable:
                board.setdefault(cc, s.to_move)
        return HexxagonState(board=board, holes=s.holes,
                             to_move=1 - s.to_move, ply=s.ply + 1)

    def _counts(self, s: HexxagonState):
        a = sum(1 for p in s.board.values() if p == 0)
        b = sum(1 for p in s.board.values() if p == 1)
        return a, b

    def returns(self, s: HexxagonState) -> list[float]:
        a, b = self._counts(s)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: HexxagonState) -> dict:
        return {
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "holes": [f"{q},{r}" for (q, r) in sorted(s.holes)],
            "to_move": s.to_move,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> HexxagonState:
        holes = frozenset(_cell(k) for k in d.get("holes", []))
        return HexxagonState(
            board={_cell(k): v for k, v in d["board"].items()},
            holes=holes,
            to_move=d["to_move"],
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: HexxagonState, move: str) -> str:
        who = NAMES[s.to_move][0]
        if move == "pass":
            return f"{who}:pass"
        src_s, dst_s = move.split(">")
        dist = _hex_dist(_cell(src_s), _cell(dst_s))
        kind = "grow" if dist == 1 else "jump"
        return f"{who}:{kind} {dst_s}"

    def render(self, s: HexxagonState, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": p, "label": ""}
                  for (q, r), p in s.board.items()]
        tints = {f"{q},{r}": HOLE_COLOR for (q, r) in s.holes}
        a, b = self._counts(s)
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = f"Draw {a}-{b}"
            else:
                winner = 0 if ret[0] > 0 else 1
                caption = f"{NAMES[winner]} wins {max(a, b)}-{min(a, b)}"
        else:
            playable = _playable(s.holes)
            mine = _moves_for(s.board, s.to_move, playable)
            if mine:
                caption = f"{NAMES[s.to_move]} to move  ({a}-{b})"
            else:
                caption = f"{NAMES[s.to_move]} must pass  ({a}-{b})"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": SIDE, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
