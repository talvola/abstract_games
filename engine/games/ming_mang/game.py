"""Ming Mang (Tibetan mig mangs; also Mig-mang, Ming-mang; Ludii calls the
game "Gundru") — the Tibetan custodial-CONVERSION board game.

NOT the same game as Tibetan Go (our `tibetan_go`), which shares the name
"mig mang" and the traditional 17x17 board but is a Go variant.

Ruleset as implemented (Wikipedia "Ming mang (game)", cyningstan leaflet #55,
Winther "Tibetan Gundru", Ludii Gundru.lud — all agree on the material rules):

* n x n board (default 8; options 9 "Gundru board" and 17 "traditional").
  Each seat starts with 2n-2 stones on the board occupying two adjacent sides:
  seat 0 (Black, moves first per cyningstan) = the full LEFT file plus the
  bottom-rank interior; seat 1 (White) = the full RIGHT file plus the top-rank
  interior. 180-degree rotationally symmetric; matches the Wikipedia diagram.
* A move slides one stone like a ROOK (orthogonal, any distance, no jumping,
  must land on an empty cell).
* ACTIVE custodial capture, resolved independently in all four orthogonal
  directions from the destination: an unbroken run of one or more enemy
  stones with a friendly stone just beyond is captured. Multiple directions
  fire simultaneously on the one move.
* Captured stones are CONVERTED to the capturer's colour in place (replaced
  from an off-board reserve). Total board population is CONSTANT (2*(2n-2))
  all game — the game's identity, and what makes it a Reversi cousin.
* Moving INTO a sandwich is safe (capture only ever fires for the mover).
  There is NO intervention capture (unlike Mak-yek): landing between two
  enemy stones captures nothing unless each run is flanked beyond by a
  friendly stone. Corner stones are immune emergently (no cell beyond).
* POSITIONAL SUPERKO (Wikipedia's repetition ban): a move may not recreate
  any previous position (board + player-to-move); such moves are illegal.
* A player who cannot move on their turn LOSES (annihilation-by-conversion
  and blockade both end this way; cyningstan rules 9-10, Ludii BlockWin).
* Termination backstops (platform policy — fortress standoffs are real):
  80 plies with no capture -> DRAW; hard 600-ply cap -> DRAW. No fabricated
  tiebreak: a fortress standoff is a genuine tie.
* Option `last_stone_leap` (off by default; Rin-chen Lha-mo 1926 / Ludii
  HopCapture): a player down to ONE stone may also capture by a single
  orthogonal short leap over an adjacent enemy stone to the empty cell just
  beyond; the leapt stone is REMOVED (not converted). The leap is optional.

Cells are "col,row" with 0,0 bottom-left; moves are clickable "from>to".
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
NO_PROGRESS_CAP = 80    # plies without any capture -> draw (fortress standoff)
PLY_CAP = 600           # hard backstop -> draw
SIZES = (8, 9, 17)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def position_key(board: dict, to_move: int) -> str:
    """Stable, compact key for (board arrangement, player to move)."""
    items = ";".join(f"{c},{r}:{o}" for (c, r), o in sorted(board.items()))
    return hashlib.sha1(f"{to_move}|{items}".encode()).hexdigest()[:16]


def start_board(n: int) -> dict:
    """Seat 0 = full left file + bottom-rank interior; seat 1 = the 180-degree
    rotation (full right file + top-rank interior). 2n-2 stones each."""
    b = {}
    for r in range(n):
        b[(0, r)] = 0
        b[(n - 1, r)] = 1
    for c in range(1, n - 1):
        b[(c, 0)] = 0
        b[(c, n - 1)] = 1
    return b


@dataclass
class MMState:
    n: int = 8
    leap: bool = False              # last_stone_leap option
    board: dict = field(default_factory=dict)   # (c, r) -> 0 | 1  (owner)
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0
    no_progress: int = 0            # plies since the last capture
    history: list = field(default_factory=list)  # position keys, incl. current


class MingMang(Game):
    name = "Ming Mang"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> MMState:
        opts = options or {}
        n = int(opts.get("size", 8))
        if n not in SIZES:
            n = 8
        leap = str(opts.get("last_stone_leap", "off")) == "on"
        board = start_board(n)
        return MMState(n=n, leap=leap, board=board,
                       history=[position_key(board, 0)])

    def current_player(self, s: MMState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------

    def _on(self, s: MMState, c, r):
        return 0 <= c < s.n and 0 <= r < s.n

    def _pseudo_moves(self, s: MMState) -> list:
        """Rook slides (+ the lone-stone leap when enabled), pre-superko."""
        out = []
        me = s.to_move
        mine = [cell for cell, o in s.board.items() if o == me]
        for (c, r) in mine:
            for dc, dr in ORTHO:
                cc, rr = c + dc, r + dr
                while self._on(s, cc, rr) and (cc, rr) not in s.board:
                    out.append(((c, r), (cc, rr)))
                    cc += dc
                    rr += dr
        if s.leap and len(mine) == 1:
            c, r = mine[0]
            enemy = 1 - me
            for dc, dr in ORTHO:
                mid = (c + dc, r + dr)
                to = (c + 2 * dc, r + 2 * dr)
                if (self._on(s, *to) and s.board.get(mid) == enemy
                        and to not in s.board):
                    out.append(((c, r), to))
        return out

    def _custodial(self, board: dict, to, player: int, n: int) -> set:
        """Enemy cells captured by `player`'s stone standing on `to`: in each
        orthogonal direction, an unbroken enemy run with a friendly stone just
        beyond. (No intervention capture; corners immune emergently.)"""
        captured = set()
        enemy = 1 - player
        for dc, dr in ORTHO:
            run = []
            cc, rr = to[0] + dc, to[1] + dr
            while 0 <= cc < n and 0 <= rr < n and board.get((cc, rr)) == enemy:
                run.append((cc, rr))
                cc += dc
                rr += dr
            if run and 0 <= cc < n and 0 <= rr < n \
                    and board.get((cc, rr)) == player:
                captured.update(run)
        return captured

    def _result_board(self, s: MMState, frm, to):
        """Board after the move frm->to, captures resolved. Returns
        (board, ncaptured) — ncaptured counts conversions + leap removal."""
        board = dict(s.board)
        me = s.to_move
        ncap = 0
        # lone-stone leap: distance-2 straight move over an occupied midpoint
        # (a slide can never cross an occupied cell, so this is unambiguous)
        mid = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
        if (abs(to[0] - frm[0]) + abs(to[1] - frm[1]) == 2
                and (frm[0] == to[0] or frm[1] == to[1])
                and mid in board and mid != frm):
            del board[mid]          # leapt stone is REMOVED, not converted
            ncap += 1
        del board[frm]
        board[to] = me
        for cell in self._custodial(board, to, me, s.n):
            board[cell] = me        # conversion in place
            ncap += 1
        return board, ncap

    def _legal(self, s: MMState) -> list:
        """Superko-filtered (frm, to) pairs, cached on the state."""
        cached = getattr(s, "_legal_cache", None)
        if cached is not None:
            return cached
        seen = set(s.history)
        out = []
        for frm, to in self._pseudo_moves(s):
            board, _ = self._result_board(s, frm, to)
            if position_key(board, 1 - s.to_move) not in seen:
                out.append((frm, to))
        s._legal_cache = out
        return out

    def legal_moves(self, s: MMState) -> list[str]:
        if s.winner is not None or s.ply >= PLY_CAP \
                or s.no_progress >= NO_PROGRESS_CAP:
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._legal(s)]

    # ---- state transitions -------------------------------------------------

    def apply_move(self, s: MMState, move: str, rng=None) -> MMState:
        frm, to = (_cell(x) for x in move.split(">"))
        board, ncap = self._result_board(s, frm, to)
        me = s.to_move
        enemy_count = sum(1 for o in board.values() if o == 1 - me)
        winner = me if enemy_count == 0 else None
        return MMState(
            n=s.n, leap=s.leap, board=board, to_move=1 - me, winner=winner,
            ply=s.ply + 1,
            no_progress=0 if ncap else s.no_progress + 1,
            history=s.history + [position_key(board, 1 - me)],
        )

    def is_terminal(self, s: MMState) -> bool:
        return (s.winner is not None or s.ply >= PLY_CAP
                or s.no_progress >= NO_PROGRESS_CAP or not self._legal(s))

    def returns(self, s: MMState) -> list[float]:
        if s.winner is not None:
            w = s.winner
        elif s.ply >= PLY_CAP or s.no_progress >= NO_PROGRESS_CAP:
            return [0.0, 0.0]       # honest draw — fortress standoff / cap
        else:
            w = 1 - s.to_move       # cannot move (blockade / superko-locked)
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def heuristic(self, s: MMState) -> list[float]:
        diff = sum(1 if o == 0 else -1 for o in s.board.values())
        v = math.tanh(diff / (2 * s.n - 2))
        return [v, -v]              # one payoff PER SEAT, like returns

    # ---- serialization -----------------------------------------------------

    def serialize(self, s: MMState) -> dict:
        return {
            "n": s.n,
            "leap": s.leap,
            "board": {f"{c},{r}": o for (c, r), o in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "no_progress": s.no_progress,
            "history": list(s.history),
        }

    def deserialize(self, d: dict) -> MMState:
        return MMState(
            n=int(d.get("n", 8)),
            leap=bool(d.get("leap", False)),
            board={_cell(k): int(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
            history=list(d.get("history", [])),
        )

    # ---- presentation ------------------------------------------------------

    def describe_move(self, s: MMState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        files = "abcdefghijklmnopq"
        alg = lambda c: f"{files[c[0]]}{c[1] + 1}"  # noqa: E731
        _, ncap = self._result_board(s, frm, to)
        return f"{alg(frm)}-{alg(to)}" + (f" x{ncap}" if ncap else "")

    def render(self, s: MMState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": o, "label": ""}
                  for (c, r), o in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = "Draw (no progress)" \
                    if s.no_progress >= NO_PROGRESS_CAP else "Draw (ply cap)"
            else:
                caption = f"{'Black' if ret[0] > 0 else 'White'} wins"
        else:
            caption = f"{'Black' if s.to_move == 0 else 'White'} to move"
        return {
            "board": {"type": "square", "width": s.n, "height": s.n},
            "pieces": pieces,
            "caption": caption,
        }
