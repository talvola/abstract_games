"""Cannon — David E. Whitcher's 2003 war game (PyroMyth Games).

Rules implemented from the official nestorgames rulebook (CANNON_EN.pdf),
cross-checked against the author's own Zillions implementation (submission
id=150, Cannont.zrf), iggamecenter.com/en/rules/cannon and
boardspace.net/cannon/english/Cannon.htm. Where sources differ the rulebook +
the author's .zrf win (see rules.md "Interpretations").

Board: 10x10 points (files a-j = cols 0-9, ranks 1-10 = rows 0-9; the renderer
draws row 0 at the bottom = Black's side). Seat 0 = Black (moves first, plays
"up", +row); seat 1 = Red (plays "down", -row).

Setup: Black soldiers on cols 0,2,4,6,8 x rows 1,2,3; Red soldiers on cols
1,3,5,7,9 x rows 6,7,8 (the staggered array from the .zrf board-setup:
a2-a4/c/e/g/i and b7-b9/d/f/h/j). Plies 0 and 1: Black then Red place their
immobile TOWN on their own back rank (row 0 / row 9) excluding the corners.

A SOLDIER may:
  * step to an adjacent empty point, forward straight or forward-diagonal;
  * capture an adjacent enemy piece forward straight, forward-diagonal or
    SIDEWAYS (never backward, never sideways-diagonal);
  * retreat exactly TWO points backward (straight or diagonal back) when it is
    adjacent (any of 8) to an enemy piece; both points must be empty.

A CANNON is any orthogonal or diagonal line of 3 adjacent friendly SOLDIERS
(a Town never forms part of a cannon). A cannon may:
  * SLIDE: its rear soldier jumps to the empty point just beyond the front
    soldier (the formation shifts one step along its own line, either way);
  * SHOOT (a non-move capture): if the point directly in front of the cannon
    is EMPTY, it may capture an enemy piece 2 or 3 points beyond its front
    soldier. Only that first point must be empty — per the rulebook/.zrf the
    long shot passes over the 2nd point whatever stands there.

Win: capture or shoot the enemy Town, or leave the opponent with no legal
move (stalemate; passing is not allowed). The rulebook has no official draw
rule; as platform termination backstops a threefold repetition of the same
position with the same player to move, or 1000 plies, is an honest draw.

Move strings: town placement is a single cell "c,r"; everything else is
"from>to". The Chebyshev distance disambiguates: 1 = step/capture, 2 =
retreat, 3 = cannon slide, 4/5 = cannon shot (from = the cannon's REAR
soldier, to = the shot target; the shooter does not move).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 10
PLY_CAP = 1000
NAMES = {0: "Black", 1: "Red"}
HOME_ROW = {0: 0, 1: N - 1}
DIRS8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
SOLDIER_COLS = {0: (0, 2, 4, 6, 8), 1: (1, 3, 5, 7, 9)}
SOLDIER_ROWS = {0: (1, 2, 3), 1: (6, 7, 8)}
FILES = "abcdefghij"


@dataclass
class CNState:
    board: dict = field(default_factory=dict)   # (c, r) -> (owner, "S"|"T")
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0
    reps: dict = field(default_factory=dict)    # position-hash -> count (since last capture)
    repeats: int = 1                            # count of the CURRENT position


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {}
    for seat in (0, 1):
        for c in SOLDIER_COLS[seat]:
            for r in SOLDIER_ROWS[seat]:
                b[(c, r)] = (seat, "S")
    return b


def _poskey(board: dict, to_move: int) -> str:
    items = ";".join(f"{c},{r},{o},{k}" for (c, r), (o, k) in sorted(board.items()))
    return hashlib.md5(f"{items}|{to_move}".encode()).hexdigest()


def _alg(cell) -> str:
    return f"{FILES[cell[0]]}{cell[1] + 1}"


class Cannon(Game):
    uid = "cannon_game"
    name = "Cannon"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CNState:
        return CNState(board=_start_board())

    def current_player(self, s: CNState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------

    def _moves(self, s: CNState) -> list:
        """Raw moves as ((from), (to)) pairs, or ("place", cell) in the town phase."""
        if s.winner is not None:
            return []
        p = s.to_move
        b = s.board

        if s.ply < 2:                                    # town placement phase
            row = HOME_ROW[p]
            return [("place", (c, row)) for c in range(1, N - 1) if (c, row) not in b]

        f = 1 if p == 0 else -1                          # forward row direction
        out = []
        for (c, r), (owner, kind) in b.items():
            if owner != p or kind != "S":
                continue
            # step forward (straight or diagonal) to an empty point
            for dc in (-1, 0, 1):
                t = (c + dc, r + f)
                if _on(*t) and t not in b:
                    out.append(((c, r), t))
            # capture forward (straight/diagonal) or sideways
            for dc, dr in ((-1, f), (0, f), (1, f), (-1, 0), (1, 0)):
                t = (c + dc, r + dr)
                if _on(*t) and t in b and b[t][0] != p:
                    out.append(((c, r), t))
            # retreat 2 back (straight or diagonal) if adjacent to an enemy piece
            if any(b.get((c + dc, r + dr), (p, ""))[0] != p for dc, dr in DIRS8):
                for dc in (-1, 0, 1):
                    mid = (c + dc, r - f)
                    t = (c + 2 * dc, r - 2 * f)
                    if _on(*t) and mid not in b and t not in b:
                        out.append(((c, r), t))
            # cannon actions, with this soldier as the REAR of the line
            for dc, dr in DIRS8:
                if (b.get((c + dc, r + dr)) != (p, "S")
                        or b.get((c + 2 * dc, r + 2 * dr)) != (p, "S")):
                    continue
                p3 = (c + 3 * dc, r + 3 * dr)            # point in front of the muzzle
                if not _on(*p3) or p3 in b:
                    continue
                out.append(((c, r), p3))                 # slide (to the empty point)
                p4 = (c + 4 * dc, r + 4 * dr)
                if not _on(*p4):
                    continue
                if p4 in b and b[p4][0] != p:
                    out.append(((c, r), p4))             # short shot
                p5 = (c + 5 * dc, r + 5 * dr)
                if _on(*p5) and p5 in b and b[p5][0] != p:
                    out.append(((c, r), p5))             # long shot (p4 may be occupied)
        return out

    def legal_moves(self, s: CNState) -> list[str]:
        if self.is_terminal(s):
            return []
        out = []
        for a, t in self._moves(s):
            if a == "place":
                out.append(f"{t[0]},{t[1]}")
            else:
                out.append(f"{a[0]},{a[1]}>{t[0]},{t[1]}")
        return out

    # ---- state transition ---------------------------------------------------

    def apply_move(self, s: CNState, move: str, rng=None) -> CNState:
        board = dict(s.board)
        winner = None
        captured = False

        if ">" not in move:                              # town placement
            board[_cell(move)] = (s.to_move, "T")
        else:
            frm, to = (_cell(x) for x in move.split(">"))
            dist = max(abs(to[0] - frm[0]), abs(to[1] - frm[1]))
            if dist >= 4:                                # cannon shot: shooter stays
                tgt = board.pop(to)
                captured = True
                if tgt[1] == "T":
                    winner = s.to_move
            else:                                        # step/capture/retreat/slide
                tgt = board.pop(to, None)
                if tgt is not None:
                    captured = True
                    if tgt[1] == "T":
                        winner = s.to_move
                board[to] = board.pop(frm)

        ply = s.ply + 1
        # Repetition tracking: captures (and town placements) are irreversible
        # progress, so the history resets there.
        reps = {} if (captured or ply <= 2) else dict(s.reps)
        key = _poskey(board, 1 - s.to_move)
        reps[key] = reps.get(key, 0) + 1
        return CNState(board=board, to_move=1 - s.to_move, winner=winner,
                       ply=ply, reps=reps, repeats=reps[key])

    # ---- termination ---------------------------------------------------------

    def is_terminal(self, s: CNState) -> bool:
        if s.winner is not None:
            return True
        if s.repeats >= 3 or s.ply >= PLY_CAP:
            return True
        return not self._moves(s)

    def returns(self, s: CNState) -> list[float]:
        if s.winner is not None:
            w = s.winner
        elif s.repeats >= 3 or s.ply >= PLY_CAP:
            return [0.0, 0.0]                            # honest backstop draw
        else:
            w = 1 - s.to_move                            # no legal move -> you lose
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    # ---- persistence ---------------------------------------------------------

    def serialize(self, s: CNState) -> dict:
        return {
            "board": {f"{c},{r}": f"{k}{o}" for (c, r), (o, k) in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "reps": dict(s.reps),
            "repeats": s.repeats,
        }

    def deserialize(self, d: dict) -> CNState:
        return CNState(
            board={_cell(k): (int(v[1]), v[0]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            reps={k: int(v) for k, v in d.get("reps", {}).items()},
            repeats=d.get("repeats", 1),
        )

    # ---- presentation --------------------------------------------------------

    def describe_move(self, s: CNState, move: str) -> str:
        if ">" not in move:
            return f"Town {_alg(_cell(move))}"
        frm, to = (_cell(x) for x in move.split(">"))
        dist = max(abs(to[0] - frm[0]), abs(to[1] - frm[1]))
        if dist >= 4:
            return f"{_alg(frm)}x{_alg(to)} (shot)"
        if dist == 3:
            return f"{_alg(frm)}-{_alg(to)} (slide)"
        if dist == 2:
            return f"{_alg(frm)}-{_alg(to)} (retreat)"
        cap = to in s.board
        return f"{_alg(frm)}{'x' if cap else '-'}{_alg(to)}"

    def heuristic(self, s: CNState) -> list:
        """Soldier-material balance squashed to (-1, 1) for rollout cutoffs."""
        import math
        bal = 0.0
        for (o, k) in s.board.values():
            if k == "S":
                bal += 1.0 if o == 0 else -1.0
        v = math.tanh(0.18 * bal)
        return [v, -v]

    def render(self, s: CNState, perspective=None) -> dict:
        pieces = []
        for (c, r), (o, k) in s.board.items():
            piece = {"cell": f"{c},{r}", "owner": o, "label": ""}
            if k == "T":
                piece["glyph"] = "♜"                # tower glyph for the Town
            pieces.append(piece)
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret[0] == ret[1]:
                caption = "Draw (repetition / ply cap)"
            else:
                caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        elif s.ply < 2:
            caption = f"{NAMES[s.to_move]}: place your Town on your back rank (not a corner)"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
