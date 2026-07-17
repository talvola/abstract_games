"""Jul-Gonu (줄고누 / ne-jul-gonu) — Korean custodial capture game on a 4x4 board.

Ruleset as implemented (sources: Wikipedia "Jul-gonu"; J.P. Neto, The World of
Abstract Games, julgonu page — Wikipedia's own primary citation):

* 4x4 points. 4 pieces each, filling the player's back rank (seat 0 = row 0,
  seat 1 = row 3).

* MOVE: one step orthogonally to an adjacent EMPTY point.

* REPETITION BAN (positional superko): a move may not recreate ANY position
  (board arrangement + side to move) that has already occurred in the game.
  (jpneto: "A move cannot be made that repeats any previous position";
  Wikipedia words it more weakly as "the previous position" — we follow the
  stronger jpneto/ZRF formulation and document it in rules.md.)

* CAPTURE is CUSTODIAL and ACTIVE ONLY: after YOUR move, look outward from the
  moved piece's destination in each of the four orthogonal directions; an
  unbroken line of one or two enemy pieces flanked at the far end by another
  friendly piece is captured (removed). On a 4-length line a run of two is the
  physical maximum, so "one or two" is exact; the code handles any run length.
  A row capture and a column capture can BOTH fire on one move (the only
  multi-capture case). Moving INTO a sandwich is safe (capture must be created
  by the capturing player's own move); no corner rule (unlike Hasami Shogi).

* WIN: reduce the opponent to ONE piece (a lone piece can no longer capture),
  or leave the opponent with no legal move on their turn (stalemate — which
  includes having every move barred by the repetition ban).

* Termination backstops (platform conformance; superko already bounds the game
  but random play could wander): NO_PROGRESS_CAP consecutive captureless plies
  or PLY_CAP total plies -> honest draw [0, 0]. Both are far above the solved
  optimal-play length (the full solve of the position graph puts the forced
  win well under the caps — see rules.md / _solve.py).

Cells are "c,r"; moves are clickable "c1,r1>c2,r2" paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 4
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
NAMES = {0: "Black", 1: "White"}
NO_PROGRESS_CAP = 80    # captureless plies -> draw (solved optimal line is far shorter)
PLY_CAP = 250           # hard total-ply cap -> draw


@dataclass
class JGState:
    board: dict = field(default_factory=dict)   # (c, r) -> 0 | 1
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0
    no_progress: int = 0        # consecutive plies without a capture
    history: list = field(default_factory=list)  # position keys seen (incl. current)


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


def _poskey(board: dict, to_move: int) -> str:
    """Canonical position key: 16 chars row-major ('.', 'B', 'W') + side to move."""
    chars = []
    for r in range(N):
        for c in range(N):
            o = board.get((c, r))
            chars.append("." if o is None else "BW"[o])
    return "".join(chars) + str(to_move)


class JulGonu(Game):
    name = "Jul-Gonu"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> JGState:
        board = _start_board()
        return JGState(board=board, history=[_poskey(board, 0)])

    def current_player(self, s: JGState) -> int:
        return s.to_move

    # ---- move generation --------------------------------------------------

    def _captures_from(self, board: dict, to, player: int) -> set:
        """Enemy cells captured by `player`'s piece landing on `to` (active
        custodial: outward run of enemies closed by a friendly piece)."""
        captured = set()
        enemy = 1 - player
        for dc, dr in ORTHO:
            line = []
            cc, rr = to[0] + dc, to[1] + dr
            while _on(cc, rr) and board.get((cc, rr)) == enemy:
                line.append((cc, rr))
                cc += dc
                rr += dr
            if line and _on(cc, rr) and board.get((cc, rr)) == player:
                captured.update(line)
        return captured

    def _slides(self, s: JGState):
        """All one-step slides for the player to move, ignoring the repetition ban."""
        out = []
        me = s.to_move
        for (c, r), pl in s.board.items():
            if pl != me:
                continue
            for dc, dr in ORTHO:
                tc, tr = c + dc, r + dr
                if _on(tc, tr) and (tc, tr) not in s.board:
                    out.append(((c, r), (tc, tr)))
        return out

    def _result_board(self, s: JGState, frm, to) -> dict:
        board = dict(s.board)
        pl = board.pop(frm)
        board[to] = pl
        for cap in self._captures_from(board, to, pl):
            del board[cap]
        return board

    def _moves(self, s: JGState) -> list:
        """Legal moves: slides whose resulting position has not occurred before."""
        seen = set(s.history)
        out = []
        for frm, to in self._slides(s):
            board = self._result_board(s, frm, to)
            if _poskey(board, 1 - s.to_move) not in seen:
                out.append((frm, to))
        return out

    def legal_moves(self, s: JGState) -> list[str]:
        if s.winner is not None or s.ply >= PLY_CAP or s.no_progress >= NO_PROGRESS_CAP:
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    # ---- state transitions ------------------------------------------------

    def apply_move(self, s: JGState, move: str, rng=None) -> JGState:
        frm, to = (_cell(x) for x in move.split(">"))
        player = s.to_move
        board = self._result_board(s, frm, to)
        captured = len(s.board) - len(board)
        enemy_left = sum(1 for o in board.values() if o != player)
        winner = player if enemy_left <= 1 else None
        nxt = 1 - player
        return JGState(
            board=board,
            to_move=nxt,
            winner=winner,
            ply=s.ply + 1,
            no_progress=0 if captured else s.no_progress + 1,
            history=s.history + [_poskey(board, nxt)],
        )

    def is_terminal(self, s: JGState) -> bool:
        if s.winner is not None:
            return True
        if s.ply >= PLY_CAP or s.no_progress >= NO_PROGRESS_CAP:
            return True
        return not self._moves(s)     # stalemate (incl. all moves repetition-barred)

    def returns(self, s: JGState) -> list[float]:
        if s.winner is not None:
            w = s.winner
        elif s.ply >= PLY_CAP or s.no_progress >= NO_PROGRESS_CAP:
            return [0.0, 0.0]         # backstop draw
        else:
            w = 1 - s.to_move         # stalemated player loses
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    # ---- misc -------------------------------------------------------------

    def heuristic(self, s: JGState) -> list[float]:
        """Material balance, one payoff per seat (bounded, returns-convention)."""
        n0 = sum(1 for o in s.board.values() if o == 0)
        n1 = len(s.board) - n0
        v = (n0 - n1) / 4.0 * 0.8
        return [v, -v]

    def serialize(self, s: JGState) -> dict:
        return {
            "board": {f"{c},{r}": o for (c, r), o in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "no_progress": s.no_progress,
            "history": list(s.history),
        }

    def deserialize(self, d: dict) -> JGState:
        return JGState(
            board={_cell(k): int(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
            history=list(d.get("history", [])),
        )

    def describe_move(self, s: JGState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcd'[c[0]]}{c[1] + 1}"  # noqa: E731
        board = dict(s.board)
        pl = board.pop(frm)
        board[to] = pl
        caps = sorted(self._captures_from(board, to, pl))
        out = f"{alg(frm)}-{alg(to)}"
        if caps:
            out += "x" + "x".join(alg(c) for c in caps)
        return out

    def render(self, s: JGState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": o} for (c, r), o in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret[0] == ret[1] else f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
