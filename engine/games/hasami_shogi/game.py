"""Hasami Shogi — Dai Hasami Shogi variant ("sandwiching chess").

Two players, 9 identical men each, on a 9x9 board. Player 0 fills row 0,
player 1 fills row 8. Every man moves like a ROOK: any number of empty squares
orthogonally, never jumping over another piece.

Ruleset as implemented (documented because Hasami Shogi rules vary):

* CAPTURE is CUSTODIAL (Tafl-style flanking) and ACTIVE — it happens only as a
  result of YOUR move. After you move a man, look outward in each of the four
  orthogonal directions from the destination: if one or more *contiguous* enemy
  men are bracketed in a straight line, with no gap and no friendly man between,
  by a friendly man (or a board corner — see below) at the far end, every
  bracketed enemy man is removed. A man that *moves into* a spot between two
  enemies is NOT captured (capture is active, on the mover's turn only).

* CORNER capture: a man sitting on one of the four board corners is captured if
  the mover occupies BOTH orthogonal squares adjacent to that corner (the two
  cells along the two edges meeting at the corner). This is the standard Dai
  Hasami Shogi corner rule, treated as a custodial-equivalent.

* WIN — both standard goals are implemented:
  (a) Annihilation/decimation: reduce the opponent to a single man (capture all
      but one of their nine). The exact threshold is documented in rules.md.
  (b) 5-in-a-row: form an unbroken line of EXACTLY 5+ of your own men,
      orthogonally OR diagonally, entirely OUTSIDE your own starting row
      (no part of the line may lie on your home row). Achieving this on your
      move wins immediately.

* A 300-ply cap draws (custodial shuffling could otherwise loop forever).

Pieces: identical men; owner 0 = player 0 (home row 0), owner 1 = player 1
(home row 8). Cells are "col,row"; moves are clickable "from>to" paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 9
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG8 = ORTHO + [(1, 1), (1, -1), (-1, 1), (-1, -1)]
CORNERS = [(0, 0), (N - 1, 0), (0, N - 1), (N - 1, N - 1)]
PLY_CAP = 300
WIN_LINE = 5          # length of an "n-in-a-row" that wins
SURVIVOR_MIN = 1      # opponent loses when reduced to this many men (capture all but one)
HOME_ROW = {0: 0, 1: N - 1}


@dataclass
class HSState:
    board: dict = field(default_factory=dict)   # (c, r) -> 0 | 1  (owner)
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {}
    for c in range(N):
        b[(c, 0)] = 0
        b[(c, N - 1)] = 1
    return b


class HasamiShogi(Game):
    uid = "hasami_shogi"
    name = "Hasami Shogi"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HSState:
        return HSState(board=_start_board())

    def current_player(self, s: HSState) -> int:
        return s.to_move

    def _moves(self, s: HSState) -> list:
        out = []
        for (c, r), owner in s.board.items():
            if owner != s.to_move:
                continue
            for dc, dr in ORTHO:
                cc, rr = c + dc, r + dr
                while _on(cc, rr) and (cc, rr) not in s.board:
                    out.append(((c, r), (cc, rr)))
                    cc += dc
                    rr += dr
        return out

    def legal_moves(self, s: HSState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    # ---- capture ----------------------------------------------------------

    def _captures_from(self, board: dict, to, player: int) -> set:
        """All enemy cells captured by `player`'s man landing on `to`."""
        captured = set()
        enemy = 1 - player
        # custodial flanking along each orthogonal direction
        for dc, dr in ORTHO:
            line = []
            cc, rr = to[0] + dc, to[1] + dr
            while _on(cc, rr) and board.get((cc, rr)) == enemy:
                line.append((cc, rr))
                cc += dc
                rr += dr
            # line is a contiguous run of enemy men; it is captured iff the
            # square just beyond holds a friendly man (the far flank).
            if line and _on(cc, rr) and board.get((cc, rr)) == player:
                captured.update(line)
        # corner capture: an enemy man on a corner is taken if `player` holds
        # both edge-neighbours of that corner.
        for corner in CORNERS:
            if board.get(corner) != enemy:
                continue
            cx, cy = corner
            nbrs = [(cx + dc, cy + dr) for dc, dr in ORTHO if _on(cx + dc, cy + dr)]
            if all(board.get(nb) == player for nb in nbrs):
                captured.add(corner)
        return captured

    # ---- win detection ----------------------------------------------------

    def _five_in_row(self, board: dict, player: int) -> bool:
        """Player has 5+ contiguous men in any of the 8 directions, with the
        whole line off their own home row."""
        home = HOME_ROW[player]
        owned = {cell for cell, o in board.items() if o == player}
        for cell in owned:
            for dc, dr in DIAG8:
                # count only from a line start (no owned man one step back)
                pc, pr = cell[0] - dc, cell[1] - dr
                if (pc, pr) in owned:
                    continue
                run = []
                cc, rr = cell
                while (cc, rr) in owned:
                    run.append((cc, rr))
                    cc += dc
                    rr += dr
                if len(run) >= WIN_LINE and all(c[1] != home for c in run):
                    return True
        return False

    def apply_move(self, s: HSState, move: str, rng=None) -> HSState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        owner = board.pop(frm)
        board[to] = owner
        player = s.to_move

        for cap in self._captures_from(board, to, player):
            del board[cap]

        winner = None
        # (a) decimation: opponent reduced to a single man
        enemy = 1 - player
        enemy_count = sum(1 for o in board.values() if o == enemy)
        if enemy_count <= SURVIVOR_MIN:
            winner = player
        # (b) five-in-a-row off home row
        elif self._five_in_row(board, player):
            winner = player

        return HSState(board=board, to_move=1 - player, winner=winner, ply=s.ply + 1)

    def is_terminal(self, s: HSState) -> bool:
        return s.winner is not None or s.ply >= PLY_CAP or not self._moves(s)

    def returns(self, s: HSState) -> list[float]:
        if s.winner is not None:
            w = s.winner
        elif s.ply >= PLY_CAP:
            return [0.0, 0.0]
        else:
            w = 1 - s.to_move        # no legal move -> player to move loses
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def serialize(self, s: HSState) -> dict:
        return {
            "board": {f"{c},{r}": o for (c, r), o in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> HSState:
        return HSState(
            board={_cell(k): int(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: HSState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcdefghi'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{alg(frm)}-{alg(to)}"

    def render(self, s: HSState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": o, "label": ""}
                  for (c, r), o in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = "Draw (ply cap)"
            else:
                caption = f"Player {0 if ret[0] > 0 else 1} wins"
        else:
            caption = f"Player {s.to_move} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "caption": caption,
        }
