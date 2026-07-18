"""Jetan, or Martian Chess — Edgar Rice Burroughs, *The Chessmen of Mars* (1922).

10x10 board, Black (South, seat 0, moves first here) vs Orange (North, seat 1).
Pieces move an EXACT number of single-square steps ("combination moves": the
direction may change at each step, but no square may be entered twice in one
move). Non-jumpers need empty intermediate squares; jumpers (Thoat, Flier,
Princess) may pass over occupied squares. Capture by replacement on the FINAL
square only.

Per side: 8 Panthans, 2 Warriors, 2 Padwars, 2 Dwars, 2 Fliers, 2 Thoats,
1 Chief, 1 Princess.

  Panthan  P : 1 step forward, forward-diagonal or sideways (never backward)
  Warrior  W : exactly 2 orthogonal steps, no jump
  Padwar   Pd: exactly 2 diagonal steps, no jump
  Dwar     D : exactly 3 orthogonal steps, no jump
  Flier    F : exactly 3 diagonal steps, MAY jump
  Thoat    T : 2 steps, one orthogonal + one diagonal (either order), MAY jump
  Chief    C : exactly 3 steps, any mix of orthogonal/diagonal, no jump
  Princess Pr: as Chief but MAY jump; cannot capture; may not END a move on a
               threatened square; one-time "escape" to any empty unthreatened
               square (encoded as the drop-style move "E@c,r").

Win: land any piece on the enemy Princess, or Chief takes Chief.
Draw (Burroughs): a Chief captured by anything but the enemy Chief; or both
sides reduced to <=3 pieces of equal total value and no win within the next
ten moves (five apiece). Completeness (Handscomb, Abstract Games #6): draw on
threefold repetition or 50 captureless moves by each player; plus a hard ply
cap as an engine backstop. Stalemate (no legal move) loses.

Rule ambiguities are resolved per the Abstract Games issue 6 "suggested
standard" (Handscomb/Smith): Chained Panthan, Chained Warrior, Chained Padwar,
Chained Dwar, Chained Flier, Wild Thoat, Chained Wild Chief, Brave Chained
Wild Princess with a Brave Free Wild escape. See rules.md.

Standalone ``agp.game.Game`` (like Congo): no check/checkmate machinery —
wins/draws are capture EVENTS stored in state.

Cells are "col,row": col 0..9 = files a..j, row 0..9 = ranks 1..10. Seat 0
(Black) starts on rows 0-1 and moves toward row 9.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 10
PLY_CAP = 1000            # hard backstop only; the rules below end games first
NO_CAPTURE_CAP = 100      # 50 captureless moves by each player -> draw
ENDGAME_MOVES = 10        # "the ensuing ten moves, five apiece"
REPETITION = 3

NAMES = {0: "Black (South)", 1: "Orange (North)"}

KIND_NAME = {
    "P": "Panthan", "W": "Warrior", "Pd": "Padwar", "D": "Dwar",
    "F": "Flier", "T": "Thoat", "C": "Chief", "Pr": "Princess",
}

# Piece values (Handscomb, Abstract Games #6) — used for the endgame
# equal-value test and the bot heuristic.
VALUES = {"P": 1, "W": 2, "Pd": 2, "T": 3, "D": 4, "F": 4, "C": 10, "Pr": 0}

ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))
KING = ORTH + DIAG

# kind -> (steps, step-directions, may_jump) for the uniform exact-N walkers.
WALKERS = {
    "W": (2, ORTH, False),
    "Pd": (2, DIAG, False),
    "D": (3, ORTH, False),
    "F": (3, DIAG, True),
    "C": (3, KING, False),
    "Pr": (3, KING, True),
}

_ESC_RE = re.compile(r"^E@(\d+),(\d+)$")


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _cid(c, r) -> str:
    return f"{c},{r}"


def _on(c, r) -> bool:
    return 0 <= c < N and 0 <= r < N


def _fwd(pl: int) -> int:
    return 1 if pl == 0 else -1


@dataclass
class JState:
    board: dict = field(default_factory=dict)   # (c, r) -> (player, kind)
    to_move: int = 0
    winner: Optional[int] = None
    over: bool = False                          # terminal event (win OR draw)
    reason: str = ""
    ply: int = 0
    captureless: int = 0
    escape_used: list = field(default_factory=lambda: [False, False])
    endgame: Optional[int] = None               # plies left in the 10-move countdown
    history: dict = field(default_factory=dict)  # poskey -> count (repetition)
    chief_rule: str = "draw"                    # "draw" (Burroughs) | "plays_on"


def _poskey(board: dict, to_move: int, escape_used) -> str:
    items = ";".join(f"{c},{r}:{pl}{k}" for (c, r), (pl, k) in sorted(board.items()))
    return f"{to_move}|{int(escape_used[0])}{int(escape_used[1])}|{items}"


def _start_board() -> dict:
    """Burroughs' Appendix setup. Back row, left to right FROM EACH PLAYER'S
    OWN SIDE: Warrior Padwar Dwar Flier Chief Princess Flier Dwar Padwar
    Warrior; second row: Thoat, 8 Panthans, Thoat. Black plays from the south
    (rows 0-1); Orange from the north (rows 8-9). The mirrored perspectives
    put each Chief opposite the enemy Princess."""
    back = ["W", "Pd", "D", "F", "C", "Pr", "F", "D", "Pd", "W"]
    b: dict = {}
    for c, k in enumerate(back):
        b[(c, 0)] = (0, k)                 # Black: left-to-right = col 0..9
        b[(N - 1 - c, N - 1)] = (1, k)     # Orange: left-to-right = col 9..0
    for c in range(N):
        k = "T" if c in (0, N - 1) else "P"
        b[(c, 1)] = (0, k)
        b[(c, N - 2)] = (1, k)
    return b


# --------------------------------------------------------------------------- #
# Move generation
# --------------------------------------------------------------------------- #

def _piece_paths(board: dict, frm, pl: int, kind: str):
    """All movement paths (lists of cells, start included) for the piece at
    `frm`, validating intermediate squares and the no-revisit rule but NOT the
    final square's occupancy (callers filter the endpoint)."""
    out = []
    if kind == "P":
        f = _fwd(pl)
        for dc, dr in ((0, f), (1, f), (-1, f), (1, 0), (-1, 0)):
            to = (frm[0] + dc, frm[1] + dr)
            if _on(*to):
                out.append([frm, to])
        return out
    if kind == "T":
        # one orthogonal + one diagonal step, either order; jumps.
        for s1, s2 in ((ORTH, DIAG), (DIAG, ORTH)):
            for d1 in s1:
                a = (frm[0] + d1[0], frm[1] + d1[1])
                if not _on(*a):
                    continue
                for d2 in s2:
                    b = (a[0] + d2[0], a[1] + d2[1])
                    if _on(*b) and b != frm:
                        out.append([frm, a, b])
        return out
    n, dirs, jump = WALKERS[kind]

    def dfs(path):
        cur = path[-1]
        depth = len(path) - 1
        if depth == n:
            out.append(path)
            return
        for dc, dr in dirs:
            nxt = (cur[0] + dc, cur[1] + dr)
            if not _on(*nxt) or nxt in path:
                continue
            # intermediate squares must be empty for non-jumpers; the FINAL
            # square's occupancy is the caller's business (capture / blocked).
            if depth < n - 1 and not jump and nxt in board:
                continue
            dfs(path + [nxt])

    dfs([frm])
    return out


def _attacks(board: dict, pl: int):
    """Every square where one of `pl`'s pieces could END a move (= capture
    there). The Princess is excluded — she cannot capture, so she threatens
    nothing. Endpoint occupancy is irrelevant to whether the path exists (the
    endpoint is never an intermediate square), so this is exact for asking
    "may the enemy Princess stand on empty square t?"."""
    out = set()
    for cell, (p, kind) in board.items():
        if p != pl or kind == "Pr":
            continue
        for path in _piece_paths(board, cell, pl, kind):
            out.add(path[-1])
    return out


def _moves(s: JState):
    """All legal move strings for the player to move."""
    pl = s.to_move
    out = []
    ppos = None
    for cell, (p, kind) in s.board.items():
        if p == pl and kind == "Pr":
            ppos = cell
            break
    attacks = None
    if ppos is not None:
        # Threats are evaluated with the Princess GONE from her origin (she
        # will have moved away), like king safety in chess.
        b2 = dict(s.board)
        del b2[ppos]
        attacks = _attacks(b2, 1 - pl)
    for cell in sorted(s.board):
        p, kind = s.board[cell]
        if p != pl:
            continue
        for path in _piece_paths(s.board, cell, pl, kind):
            to = path[-1]
            occ = s.board.get(to)
            if kind == "Pr":
                # may not capture; may not END on a threatened square (Brave:
                # passing OVER threatened squares is fine).
                if occ is None and to not in attacks:
                    out.append(">".join(_cid(*x) for x in path))
            elif occ is None or occ[0] != pl:
                out.append(">".join(_cid(*x) for x in path))
    # The one-time escape: to any empty, unthreatened square (Handscomb: an
    # up-to-10-step jumping combination move reaches every square, so the
    # escape is simply "any unoccupied square not threatened by the enemy").
    if ppos is not None and not s.escape_used[pl]:
        for c in range(N):
            for r in range(N):
                t = (c, r)
                if t not in s.board and t not in attacks:
                    out.append(f"E@{c},{r}")
    return out


def _endgame_condition(board: dict) -> bool:
    """Both sides reduced to three pieces or less, of equal (total) value."""
    counts = [0, 0]
    vals = [0, 0]
    for (pl, k) in board.values():
        counts[pl] += 1
        vals[pl] += VALUES[k]
    return counts[0] <= 3 and counts[1] <= 3 and vals[0] == vals[1]


# --------------------------------------------------------------------------- #

class Jetan(Game):
    name = "Jetan"
    PLY_CAP = PLY_CAP

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> JState:
        opts = options or {}
        board = _start_board()
        chief_rule = opts.get("chief_rule", "draw")
        st = JState(board=board, chief_rule=chief_rule)
        st.history = {_poskey(board, 0, st.escape_used): 1}
        return st

    def current_player(self, s: JState) -> int:
        return s.to_move

    def _legal(self, s: JState):
        mv = getattr(s, "_mv", None)
        if mv is None:
            mv = _moves(s)
            s._mv = mv          # pure cache; not a dataclass field, never serialized
        return mv

    def legal_moves(self, s: JState):
        if self.is_terminal(s):
            return []
        return self._legal(s)

    def apply_move(self, s: JState, move: str, rng=None) -> JState:
        board = dict(s.board)
        pl = s.to_move
        winner: Optional[int] = None
        over = False
        reason = ""
        esc = list(s.escape_used)
        captured = None

        m = _ESC_RE.match(move)
        if m:
            to = (int(m.group(1)), int(m.group(2)))
            ppos = next(c for c, (p, k) in board.items() if p == pl and k == "Pr")
            del board[ppos]
            board[to] = (pl, "Pr")
            esc[pl] = True
        else:
            cells = [_cell(x) for x in move.split(">")]
            frm, to = cells[0], cells[-1]
            _, kind = board.pop(frm)
            captured = board.get(to)
            board[to] = (pl, kind)
            if captured is not None:
                ck = captured[1]
                if ck == "Pr":
                    winner, over, reason = pl, True, "princess captured"
                elif ck == "C":
                    if kind == "C":
                        winner, over, reason = pl, True, "chief takes chief"
                    elif s.chief_rule == "draw":
                        over, reason = True, "chief slain by a lesser piece"
                    # "plays_on": the Chief is simply lost; the game continues.

        ply = s.ply + 1
        captureless = 0 if captured is not None else s.captureless + 1
        endgame = s.endgame
        history = dict(s.history)

        if not over:
            if _endgame_condition(board):
                endgame = ENDGAME_MOVES if endgame is None else endgame - 1
                if endgame <= 0:
                    over, reason = True, "endgame ten-move rule"
            else:
                endgame = None
            if not over and captureless >= NO_CAPTURE_CAP:
                over, reason = True, "50 captureless moves each"
            if not over:
                key = _poskey(board, 1 - pl, esc)
                history[key] = history.get(key, 0) + 1
                if history[key] >= REPETITION:
                    over, reason = True, "threefold repetition"
            if not over and ply >= PLY_CAP:
                over, reason = True, "ply cap"

        return JState(board=board, to_move=1 - pl, winner=winner, over=over,
                      reason=reason, ply=ply, captureless=captureless,
                      escape_used=esc, endgame=endgame, history=history,
                      chief_rule=s.chief_rule)

    # ---- termination ---- #
    def is_terminal(self, s: JState) -> bool:
        if s.over:
            return True
        return not self._legal(s)

    def returns(self, s: JState):
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if s.over:
            return [0.0, 0.0]
        # stalemate: the player to move has no legal move and loses
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def heuristic(self, s: JState):
        bal = 0.0
        for (pl, k) in s.board.values():
            v = VALUES[k]
            bal += v if pl == 0 else -v
        x = math.tanh(bal / 12.0)
        return [x, -x]

    # ---- serialize ---- #
    def serialize(self, s: JState) -> dict:
        return {
            "board": {_cid(c, r): [pl, k] for (c, r), (pl, k) in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "over": s.over,
            "reason": s.reason,
            "ply": s.ply,
            "captureless": s.captureless,
            "escape_used": list(s.escape_used),
            "endgame": s.endgame,
            "history": dict(s.history),
            "chief_rule": s.chief_rule,
        }

    def deserialize(self, d: dict) -> JState:
        return JState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            over=d["over"],
            reason=d["reason"],
            ply=d["ply"],
            captureless=d["captureless"],
            escape_used=list(d["escape_used"]),
            endgame=d["endgame"],
            history=dict(d["history"]),
            chief_rule=d["chief_rule"],
        )

    # ---- presentation ---- #
    def describe_move(self, s: JState, move: str) -> str:
        alg = lambda x: f"{'abcdefghij'[x[0]]}{x[1] + 1}"  # noqa: E731
        m = _ESC_RE.match(move)
        if m:
            to = (int(m.group(1)), int(m.group(2)))
            ppos = next((c for c, (p, k) in s.board.items()
                         if p == s.to_move and k == "Pr"), None)
            src = alg(ppos) if ppos else "?"
            return f"Pr{src}~{alg(to)} (escape)"
        cells = [_cell(x) for x in move.split(">")]
        _, kind = s.board[cells[0]]
        occ = s.board.get(cells[-1])
        sep = "x" if occ is not None else "-"
        txt = f"{kind}{alg(cells[0])}{sep}{alg(cells[-1])}"
        if occ is not None:
            if occ[1] == "Pr" or (occ[1] == "C" and kind == "C"):
                txt += "#"                      # a game-winning capture
            elif occ[1] == "C" and s.chief_rule == "draw":
                txt += "="                      # instant draw (chief slain)
        return txt

    def render(self, s: JState, perspective=None) -> dict:
        pieces = [
            {"cell": _cid(c, r), "owner": pl, "label": k}
            for (c, r), (pl, k) in s.board.items()
        ]
        # The Barsoomian board is checkered black and orange (black at each
        # player's bottom-left, per Abstract Games #6).
        tints = {}
        for c in range(N):
            for r in range(N):
                tints[_cid(c, r)] = "#221d18" if (c + r) % 2 == 0 else "#4a2d12"

        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins ({s.reason})"
        elif s.over:
            caption = f"Draw ({s.reason})"
        elif self.is_terminal(s):
            caption = f"{NAMES[1 - s.to_move]} wins (stalemate)"
        else:
            caption = f"{NAMES[s.to_move]} to move"
            if s.endgame is not None:
                caption += f" — endgame: {s.endgame} plies to a draw"

        # The one-time Princess escape is offered as a reserve chip "E": click
        # it, then click any highlighted (empty, unthreatened) square.
        reserve = {
            str(pl): ({"E": 1} if not s.escape_used[pl] else {})
            for pl in (0, 1)
        }
        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "reserve": reserve,
            "caption": caption,
        }
