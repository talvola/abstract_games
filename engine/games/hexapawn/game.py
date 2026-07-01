"""Hexapawn — Martin Gardner's 3x3 pawns game (Scientific American, 1962).

A tiny chess-pawn race famous as an AI teaching game (Gardner's matchbox
learning machine "HER"/"HEXAPAWN"). Each side starts with three pawns on its
home rank. Pawns move exactly like chess pawns with NO double-step, NO en
passant and NO promotion: advance one square straight forward to an EMPTY
square, or capture one square diagonally forward onto an enemy pawn (diagonal
moves are capture-only).

You win if any of your pawns reaches the far rank, OR if your opponent has no
legal move on their turn (the side to move with no move LOSES). There are no
draws. Player 0 = White (home rank row 0, advances upward); player 1 = Black
(home rank row 2, advances downward).

Moves are clickable cell paths "from>to": "0,0>0,1" (push) or "0,0>1,1"
(diagonal capture). Play strictly progresses (every move advances a pawn one
row or removes material) so the game always terminates and cannot cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 3
NAMES = {0: "White", 1: "Black"}
# Pure-safety ply cap for conformance; unreachable in real play (a 3x3
# hexapawn game ends in well under 10 plies).
PLY_CAP = 30


@dataclass
class HexState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
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
        b[(c, 2)] = 1
    return b


def _fwd(player: int) -> int:
    return 1 if player == 0 else -1


def _far_row(player: int) -> int:
    return N - 1 if player == 0 else 0


class Hexapawn(Game):
    # uid comes from manifest.json, not hardcoded here.
    name = "Hexapawn"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HexState:
        return HexState(board=_start_board())

    def current_player(self, s: HexState) -> int:
        return s.to_move

    def _moves(self, s: HexState) -> list:
        out = []
        dr = _fwd(s.to_move)
        for (c, r), pl in s.board.items():
            if pl != s.to_move:
                continue
            nr = r + dr
            # straight forward: only onto an EMPTY square
            if _on(c, nr) and (c, nr) not in s.board:
                out.append(((c, r), (c, nr)))
            # diagonals: CAPTURE ONLY (an enemy pawn must be there)
            for dc in (-1, 1):
                nc = c + dc
                if not _on(nc, nr):
                    continue
                occ = s.board.get((nc, nr))
                if occ is not None and occ != s.to_move:
                    out.append(((c, r), (nc, nr)))
        return out

    def legal_moves(self, s: HexState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    def apply_move(self, s: HexState, move: str, rng=None) -> HexState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        pl = board.pop(frm)
        board[to] = pl                                  # capture overwrites the dest
        winner = pl if to[1] == _far_row(pl) else None
        return HexState(board=board, to_move=1 - pl, winner=winner, ply=s.ply + 1)

    def is_terminal(self, s: HexState) -> bool:
        return s.winner is not None or s.ply >= PLY_CAP or not self._moves(s)

    def returns(self, s: HexState) -> list[float]:
        if s.winner is not None:
            w = s.winner
        elif not self._moves(s):
            w = 1 - s.to_move                          # no move -> to_move loses
        else:
            return [0.0, 0.0]                           # ply-cap safety draw (unreachable)
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def serialize(self, s: HexState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> HexState:
        return HexState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: HexState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        cap = to in s.board
        alg = lambda c: f"{'abc'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{alg(frm)}{'x' if cap else '-'}{alg(to)}"

    def render(self, s: HexState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
