"""Mak-yek (Thai/Cambodian; also Apit-sodok / Apit-sodok).

Two players, 16 identical men each, on an 8x8 board. Every man moves like a
ROOK: any number of empty squares orthogonally, never jumping over another
piece. Capture is ACTIVE (only on the mover's turn) and has TWO modes, both
the well-documented standard Mak-yek pair:

* CUSTODIAL / flanking — after you move a man, look outward in each of the four
  orthogonal directions from its destination: if one or more *contiguous* enemy
  men are bracketed in a straight line, with no gap and no friendly man between,
  by a friendly man at the far end, every bracketed enemy man is removed.

* INTERVENTION — if your move lands a man in the single empty square BETWEEN two
  enemy men one square apart on a row or column (enemy - YOU - enemy), both
  enemy men are removed. (This is the inverse of custodial: you are the meat of
  the sandwich, but because the capture is the mover's, you are safe and instead
  capture the two flanking enemies.)

A man that MOVES INTO a flanked/between position is NOT captured (capture is
active, on the mover's turn only). All four directions resolve simultaneously
on the one move, so a single move can capture several lines at once.

WIN — annihilation: capturing all of the opponent's men wins (the player left
with no men loses). A 300-ply no-progress (here: ply) cap draws to guarantee
termination, since rook-shuffling without captures could otherwise loop.

Setup: the standard opening places each side's 16 men on the FIRST and THIRD
rank from that player's side. Player 0 (rows 0 and 2), player 1 (rows 5 and 7).

Cells are "col,row"; moves are clickable "from>to" paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 8
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
PLY_CAP = 300
# rows occupied at setup, per seat (first and third rank from that player)
SETUP_ROWS = {0: (0, 2), 1: (N - 3, N - 1)}   # 0: rows 0,2  |  1: rows 5,7


@dataclass
class MYState:
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
    for seat, rows in SETUP_ROWS.items():
        for row in rows:
            for c in range(N):
                b[(c, row)] = seat
    return b


class MakYek(Game):
    uid = "mak_yek"
    name = "Mak-yek"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> MYState:
        return MYState(board=_start_board())

    def current_player(self, s: MYState) -> int:
        return s.to_move

    def _moves(self, s: MYState) -> list:
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

    def legal_moves(self, s: MYState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    # ---- capture ----------------------------------------------------------

    def _captures_from(self, board: dict, to, player: int) -> set:
        """All enemy cells captured by `player`'s man landing on `to`.

        Resolves both capture modes in every orthogonal direction:
          * CUSTODIAL: an unbroken run of enemy men starting just beyond `to`
            and terminated by a friendly man is captured.
          * INTERVENTION: exactly one enemy man immediately on each side of `to`
            along the same axis (enemy - YOU - enemy) — both are captured.
        Both are detected per-direction; intervention is the symmetric case of
        the single-step custodial run on opposite sides, so the union is taken.
        """
        captured = set()
        enemy = 1 - player

        # CUSTODIAL: for each direction, a contiguous enemy run flanked by a
        # friendly man at the far end is captured.
        for dc, dr in ORTHO:
            line = []
            cc, rr = to[0] + dc, to[1] + dr
            while _on(cc, rr) and board.get((cc, rr)) == enemy:
                line.append((cc, rr))
                cc += dc
                rr += dr
            if line and _on(cc, rr) and board.get((cc, rr)) == player:
                captured.update(line)

        # INTERVENTION: an enemy immediately on BOTH opposite sides of `to`
        # along an axis (enemy - YOU - enemy) captures both. Check the two
        # axes (horizontal, vertical).
        for dc, dr in [(1, 0), (0, 1)]:
            a = (to[0] + dc, to[1] + dr)
            b = (to[0] - dc, to[1] - dr)
            if (_on(*a) and _on(*b)
                    and board.get(a) == enemy and board.get(b) == enemy):
                captured.add(a)
                captured.add(b)

        return captured

    def apply_move(self, s: MYState, move: str, rng=None) -> MYState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        owner = board.pop(frm)
        board[to] = owner
        player = s.to_move

        for cap in self._captures_from(board, to, player):
            del board[cap]

        enemy = 1 - player
        enemy_count = sum(1 for o in board.values() if o == enemy)
        winner = player if enemy_count == 0 else None

        return MYState(board=board, to_move=1 - player, winner=winner, ply=s.ply + 1)

    def is_terminal(self, s: MYState) -> bool:
        return s.winner is not None or s.ply >= PLY_CAP or not self._moves(s)

    def returns(self, s: MYState) -> list[float]:
        if s.winner is not None:
            w = s.winner
        elif s.ply >= PLY_CAP:
            return [0.0, 0.0]
        else:
            w = 1 - s.to_move        # no legal move -> player to move loses
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def serialize(self, s: MYState) -> dict:
        return {
            "board": {f"{c},{r}": o for (c, r), o in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> MYState:
        return MYState(
            board={_cell(k): int(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: MYState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{alg(frm)}-{alg(to)}"

    def render(self, s: MYState, perspective=None) -> dict:
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
