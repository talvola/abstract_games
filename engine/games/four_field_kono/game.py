"""Four Field Kono (네밭고누) — a traditional Korean slide-and-capture game on a 4x4 board.

There are TWO move types (standard Four Field Kono — Wikipedia, R.C. Bell,
Cyningstan):

1. The defining ("signature") *capturing jump*: a piece jumps over one
   ORTHOGONALLY-ADJACENT piece of its OWN colour and lands on the cell directly
   beyond it — that landing cell MUST contain an OPPONENT piece, which is
   captured (removed). The jumper ends on that cell. The three cells (jumper,
   jumped-over, landing) lie in a straight orthogonal line, with the jumped
   piece your own and the enemy at the far end.

2. A plain *non-capturing slide*: a piece moves one step ORTHOGONALLY to an
   ADJACENT EMPTY cell. (No diagonal moves.)

Illegal jumps: jumping onto an EMPTY cell, jumping OVER an enemy piece, or
jumping over an empty gap. Only one capture per turn — no multi-jumps.

The board starts COMPLETELY FULL (player 0 on rows 0-1, player 1 on rows 2-3, 8
pieces each), so the first move is necessarily a capturing jump (no empty cell
to slide into); slides become available once captures open space.

WIN: a player wins when the opponent has no legal move — i.e. can make neither a
capturing jump NOR a slide. This is the standard win condition (the player to
move who is fully blocked loses).

Move notation (both types are >-paths, distinguished by distance):
  - capturing jump:  "c,r>c2,r2"  (two cells apart, orthogonal; lands on enemy)
  - non-capturing slide: "c,r>c2,r2"  (one cell apart, orthogonal; to an empty cell)

Termination: slides allow non-capturing maneuvering, so we cap consecutive
non-capturing (slide) plies (NO_PROGRESS_CAP) -> draw, plus a hard ply cap. Any
capture resets the no-progress counter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 4
NAMES = {0: "Black", 1: "White"}
# Slides allow non-capturing maneuvering, so the game can loop. Two safety nets:
#  - NO_PROGRESS_CAP: consecutive non-capturing (slide) plies with no capture
#    -> draw (a capture resets the counter to 0);
#  - PLY_CAP: a hard cap on total plies -> draw.
NO_PROGRESS_CAP = 60
PLY_CAP = 200


@dataclass
class FFKState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0
    no_progress: int = 0   # consecutive non-capturing (slide) plies


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {}
    for c in range(N):
        b[(c, 0)] = 0
        b[(c, 1)] = 0
        b[(c, 2)] = 1
        b[(c, 3)] = 1
    return b


class FourFieldKono(Game):
    uid = "four_field_kono"
    name = "Four Field Kono"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> FFKState:
        return FFKState(board=_start_board())

    def current_player(self, s: FFKState) -> int:
        return s.to_move

    def _jumps(self, s: FFKState) -> list:
        """Capturing jumps for the player to move.

        (from) --own neighbour--> (landing = enemy), all in a straight line.
        """
        out = []
        me = s.to_move
        for (c, r), pl in s.board.items():
            if pl != me:
                continue
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                mc, mr = c + dc, r + dr          # the jumped-over cell
                lc, lr = c + 2 * dc, r + 2 * dr  # the landing cell
                if not _on(lc, lr):
                    continue
                mid = s.board.get((mc, mr))
                land = s.board.get((lc, lr))
                # jumped cell must be OUR OWN piece; landing must be an OPPONENT.
                if mid == me and land is not None and land != me:
                    out.append(((c, r), (lc, lr)))
        return out

    def _slides(self, s: FFKState) -> list:
        """Non-capturing single-step orthogonal slides to an adjacent EMPTY cell."""
        out = []
        me = s.to_move
        for (c, r), pl in s.board.items():
            if pl != me:
                continue
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                tc, tr = c + dc, r + dr
                if not _on(tc, tr):
                    continue
                if (tc, tr) not in s.board:      # destination must be empty
                    out.append(((c, r), (tc, tr)))
        return out

    def _moves(self, s: FFKState) -> list:
        """All legal moves: capturing jumps + non-capturing slides."""
        return self._jumps(s) + self._slides(s)

    def legal_moves(self, s: FFKState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    def apply_move(self, s: FFKState, move: str, rng=None) -> FFKState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        pl = board.pop(frm)
        # Distinguish by Manhattan distance: 2 == capturing jump, 1 == slide.
        is_capture = abs(frm[0] - to[0]) + abs(frm[1] - to[1]) == 2
        board[to] = pl                       # jump lands on/removes the enemy; slide relocates
        nxt = 1 - pl
        ply = s.ply + 1
        no_progress = 0 if is_capture else s.no_progress + 1
        # Win when the opponent has no legal move (no jump AND no slide).
        probe = FFKState(board=board, to_move=nxt)
        winner = pl if not self._moves(probe) else None
        return FFKState(board=board, to_move=nxt, winner=winner,
                        ply=ply, no_progress=no_progress)

    def is_terminal(self, s: FFKState) -> bool:
        if s.winner is not None:
            return True
        if s.ply >= PLY_CAP or s.no_progress >= NO_PROGRESS_CAP:
            return True
        return not self._moves(s)

    def returns(self, s: FFKState) -> list[float]:
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if (s.ply >= PLY_CAP or s.no_progress >= NO_PROGRESS_CAP) and self._moves(s):
            return [0.0, 0.0]               # no-progress / ply-cap draw
        # No legal move for the player to move -> they lose.
        w = 1 - s.to_move
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def serialize(self, s: FFKState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "no_progress": s.no_progress,
        }

    def deserialize(self, d: dict) -> FFKState:
        return FFKState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
        )

    def describe_move(self, s: FFKState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcd'[c[0]]}{c[1] + 1}"  # noqa: E731
        # 2-cell move = capturing jump ('x'); 1-cell move = slide ('-').
        sep = "x" if abs(frm[0] - to[0]) + abs(frm[1] - to[1]) == 2 else "-"
        return f"{alg(frm)}{sep}{alg(to)}"

    def render(self, s: FFKState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p}
                  for (c, r), p in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret[0] == ret[1]:
                caption = "Draw"
            else:
                caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
