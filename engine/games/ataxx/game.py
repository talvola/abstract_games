"""Ataxx — 7x7 expansion / infection game.

Two players each start with two pieces on opposite corners. On your turn you
move ONE of your pieces to an EMPTY target cell, of two kinds:

  (A) GROW / clone — the target is a Chebyshev-distance-1 neighbour (one of the 8
      surrounding cells). A NEW piece of your colour appears there; the source
      piece STAYS. You go from n to n+1 pieces.
  (B) JUMP — the target is at Chebyshev distance EXACTLY 2. The piece RELOCATES:
      the source becomes empty, piece count unchanged.

After the piece lands (either kind), EVERY opponent piece in the 8 cells
orthogonally or diagonally adjacent to the DESTINATION flips to your colour
(the signature "infection").

A move is encoded as the path "src>dst" (both "col,row").

If a player has at least one legal move they must move. If a player has NO legal
move they PASS (their turn is skipped). When NEITHER player can move (or the
board is full), the game ends and the player with MORE pieces wins; equal counts
draw.

Termination: each grow adds a piece (board bounded at 49 cells); jumps and flips
never reduce the total piece count, so the board state can't cycle indefinitely.
A defensive hard ply cap also forces an end-and-count.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 7
NAMES = {0: "Red", 1: "Blue"}
# 8 adjacency directions (for flipping and for distance-1 grow targets)
DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
PLY_CAP = 2000  # defensive: end-and-count if play runs absurdly long


@dataclass
class AtaxxState:
    board: dict = field(default_factory=dict)   # (c, r) -> player (0/1)
    to_move: int = 0
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _grow_targets(c, r):
    """Empty-able cells at Chebyshev distance 1."""
    for dc, dr in DIRS:
        cc, rr = c + dc, r + dr
        if _on(cc, rr):
            yield cc, rr


def _jump_targets(c, r):
    """Cells at Chebyshev distance exactly 2 (the ring two out)."""
    for dc in range(-2, 3):
        for dr in range(-2, 3):
            if max(abs(dc), abs(dr)) != 2:
                continue
            cc, rr = c + dc, r + dr
            if _on(cc, rr):
                yield cc, rr


def _moves_for(board: dict, player: int):
    """All legal "src>dst" moves for `player`."""
    moves = []
    for (c, r), p in board.items():
        if p != player:
            continue
        for tc, tr in _grow_targets(c, r):
            if (tc, tr) not in board:
                moves.append(((c, r), (tc, tr), "grow"))
        for tc, tr in _jump_targets(c, r):
            if (tc, tr) not in board:
                moves.append(((c, r), (tc, tr), "jump"))
    return moves


def _flip_neighbours(board: dict, cell, player: int) -> list:
    """Opponent pieces adjacent (8-way) to `cell` that flip to `player`."""
    c, r = cell
    out = []
    for dc, dr in DIRS:
        cc, rr = c + dc, r + dr
        if _on(cc, rr) and board.get((cc, rr)) == 1 - player:
            out.append((cc, rr))
    return out


class Ataxx(Game):
    uid = "ataxx"
    name = "Ataxx"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AtaxxState:
        # Player 0 (Red): top-left + bottom-right; Player 1 (Blue): top-right + bottom-left.
        board = {
            (0, 0): 0, (N - 1, N - 1): 0,
            (N - 1, 0): 1, (0, N - 1): 1,
        }
        return AtaxxState(board=board, to_move=0, ply=0)

    def current_player(self, s: AtaxxState) -> int:
        return s.to_move

    def _board_full(self, s: AtaxxState) -> bool:
        return len(s.board) >= N * N

    def is_terminal(self, s: AtaxxState) -> bool:
        if s.ply >= PLY_CAP:
            return True
        if self._board_full(s):
            return True
        # ends when neither player has a move
        return not _moves_for(s.board, 0) and not _moves_for(s.board, 1)

    def legal_moves(self, s: AtaxxState) -> list[str]:
        if self.is_terminal(s):
            return []
        mine = _moves_for(s.board, s.to_move)
        if mine:
            return [f"{sc},{sr}>{tc},{tr}" for (sc, sr), (tc, tr), _ in mine]
        # no move -> we pass (the opponent must have a move, else terminal)
        return ["pass"]

    def apply_move(self, s: AtaxxState, move: str, rng=None) -> AtaxxState:
        if move == "pass":
            return AtaxxState(board=dict(s.board), to_move=1 - s.to_move, ply=s.ply + 1)
        src_s, dst_s = move.split(">")
        src = _cell(src_s)
        dst = _cell(dst_s)
        board = dict(s.board)
        c, r = src
        tc, tr = dst
        dist = max(abs(tc - c), abs(tr - r))
        # place / relocate
        if dist == 2:           # JUMP: source vacates
            del board[src]
        # (dist == 1 GROW: source piece stays)
        board[dst] = s.to_move
        # infection: flip every adjacent opponent piece
        for fc in _flip_neighbours(board, dst, s.to_move):
            board[fc] = s.to_move
        return AtaxxState(board=board, to_move=1 - s.to_move, ply=s.ply + 1)

    def _counts(self, s: AtaxxState):
        a = sum(1 for p in s.board.values() if p == 0)
        b = sum(1 for p in s.board.values() if p == 1)
        return a, b

    def returns(self, s: AtaxxState) -> list[float]:
        a, b = self._counts(s)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: AtaxxState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> AtaxxState:
        return AtaxxState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: AtaxxState, move: str) -> str:
        who = NAMES[s.to_move][0]
        if move == "pass":
            return f"{who}:pass"
        src_s, dst_s = move.split(">")
        c, r = _cell(src_s)
        tc, tr = _cell(dst_s)
        dist = max(abs(tc - c), abs(tr - r))
        kind = "grow" if dist == 1 else "jump"
        return f"{who}:{kind} {dst_s}"

    def render(self, s: AtaxxState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        a, b = self._counts(s)
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = f"Draw {a}-{b}"
            else:
                winner = 0 if ret[0] > 0 else 1
                caption = f"{NAMES[winner]} wins {max(a, b)}-{min(a, b)}"
        else:
            mine = _moves_for(s.board, s.to_move)
            if mine:
                caption = f"{NAMES[s.to_move]} to move  ({a}-{b})"
            else:
                caption = f"{NAMES[s.to_move]} must pass  ({a}-{b})"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
