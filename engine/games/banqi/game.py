"""Banqi (半棋) — "Dark Chess" / "Blind Chess" (暗棋), the Taiwanese ruleset.

All 32 xiangqi pieces are shuffled face-down onto the 32 squares of a 4x8
half-board. A turn is one of: FLIP a face-down piece (revealing it), MOVE one
of your revealed pieces one square orthogonally to an empty square, or CAPTURE
an adjacent revealed enemy piece of equal or lower rank.

Taiwanese ranking: General > Advisor > Elephant > Chariot > Horse > Soldier,
with the classic exception that Soldiers capture the General while the General
cannot capture Soldiers. The Cannon sits outside the ranking: it captures a
piece of ANY rank, but only by jumping (xiangqi-style) over exactly one screen
(any piece — friend, foe, or face-down) along a rank or file; it can never
capture an adjacent piece, and it is itself capturable by any piece except a
Soldier. Only face-up enemy pieces may ever be captured.

Colours are decided by the first flip: the first player plays the colour of
the first piece they reveal. A player with no legal move loses (usually: all
their pieces are captured and no face-down pieces remain to flip).

Randomness follows the platform pattern (EinStein): the shuffle happens in
``initial_state`` with the passed rng and is STORED in the state; flips merely
reveal it. The render spec shows face-down pieces only as neutral "?" discs —
their identity is never emitted — while the raw state does contain the layout
(accepted, documented simplification; the MCTS bot can "peek").

Cells are "c,r" with c 0..7, r 0..3. Moves: flip = "c,r"; move/capture =
"c,r>c,r". Honest-draw backstops: threefold repetition, a 64-ply
no-flip/no-capture rule, and a hard ply cap.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WIDTH, HEIGHT = 8, 4
RED, BLACK = 0, 1
COLOR_NAMES = {RED: "Red", BLACK: "Black"}

QUIET_CAP = 64      # plies without a flip or a capture -> draw
PLY_CAP = 1500      # absolute backstop -> draw
ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))

# Piece kinds (xiangqi letters): General Advisor Elephant Chariot(R) Horse
# Cannon Soldier. Per colour: 1G 2A 2E 2R 2H 2C 5S = 16.
KIND_COUNTS = {"G": 1, "A": 2, "E": 2, "R": 2, "H": 2, "C": 2, "S": 5}
RANK = {"G": 6, "A": 5, "E": 4, "R": 3, "H": 2, "S": 1}   # cannon is outside the ranking
KIND_NAMES = {"G": "General", "A": "Advisor", "E": "Elephant", "R": "Chariot",
              "H": "Horse", "C": "Cannon", "S": "Soldier"}

# Material values for the MCTS rollout-cutoff heuristic (the bot sees the
# stored shuffle — the platform's standard simplification for stored randomness).
PIECE_VALUES = {"G": 6.0, "A": 5.0, "E": 4.0, "R": 3.5, "H": 3.0, "C": 4.5, "S": 1.5}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < WIDTH and 0 <= r < HEIGHT


def can_capture(a: str, t: str) -> bool:
    """May a revealed piece of kind `a` STEP-capture a revealed enemy of kind `t`?

    (Cannon jumps are handled separately — a cannon never step-captures, and a
    cannon jump may take any kind.)"""
    if a == "C":
        return False                      # cannons capture only by jumping
    if t == "C":
        return a != "S"                   # cannon: vulnerable to all but the Soldier
    if a == "S":
        return t in ("G", "S")            # soldier fells the General (and trades with soldiers)
    if a == "G":
        return t != "S"                   # general takes anything except Soldiers
    return RANK[a] >= RANK[t]             # equal or lower rank


@dataclass
class BanqiState:
    # (c, r) -> (color, kind, face_up)
    board: dict = field(default_factory=dict)
    colors: Optional[int] = None          # colour played by SEAT 0 (None until the first flip)
    to_move: int = 0                      # seat index
    quiet: int = 0                        # plies since the last flip/capture
    ply: int = 0
    reps: dict = field(default_factory=dict)  # position key -> count (reset on flip/capture)
    draw: Optional[str] = None            # "repetition" once threefold is hit


def _poskey(board: dict, to_move: int) -> str:
    """Canonical position string for repetition detection. Face-down pieces are
    static between flips (and flips reset the table), so they encode as '#'."""
    out = []
    for r in range(HEIGHT):
        for c in range(WIDTH):
            p = board.get((c, r))
            if p is None:
                out.append(".")
            elif not p[2]:
                out.append("#")
            else:
                out.append(p[1].upper() if p[0] == RED else p[1].lower())
    return "".join(out) + str(to_move)


class Banqi(Game):
    name = "Banqi (Dark Chess)"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> BanqiState:
        rng = rng or random.Random()
        pieces = [(col, k)
                  for col in (RED, BLACK)
                  for k, n in KIND_COUNTS.items()
                  for _ in range(n)]
        rng.shuffle(pieces)
        board = {}
        i = 0
        for r in range(HEIGHT):
            for c in range(WIDTH):
                col, k = pieces[i]
                board[(c, r)] = (col, k, False)
                i += 1
        return BanqiState(board=board)

    def current_player(self, s: BanqiState) -> int:
        return s.to_move

    # ---- move generation -------------------------------------------------- #
    def _moves(self, s: BanqiState):
        board = s.board
        out = []
        # Flips: legal whenever any face-down piece remains.
        for (c, r), (col, k, up) in board.items():
            if not up:
                out.append(f"{c},{r}")
        if s.colors is None:
            return out                    # colours undecided: only flips exist
        my_col = s.colors if s.to_move == 0 else 1 - s.colors
        for (c, r), (col, k, up) in board.items():
            if not up or col != my_col:
                continue
            for dc, dr in ORTHO:
                nc, nr = c + dc, r + dr
                if not _on(nc, nr):
                    continue
                tgt = board.get((nc, nr))
                if tgt is None:
                    out.append(f"{c},{r}>{nc},{nr}")
                elif tgt[2] and tgt[0] != my_col and can_capture(k, tgt[1]):
                    out.append(f"{c},{r}>{nc},{nr}")
            if k == "C":                  # cannon jump-captures
                for dc, dr in ORTHO:
                    nc, nr = c + dc, r + dr
                    # skip empties to the screen
                    while _on(nc, nr) and (nc, nr) not in board:
                        nc, nr = nc + dc, nr + dr
                    if not _on(nc, nr):
                        continue
                    nc, nr = nc + dc, nr + dr   # past the screen
                    while _on(nc, nr) and (nc, nr) not in board:
                        nc, nr = nc + dc, nr + dr
                    if not _on(nc, nr):
                        continue
                    tgt = board[(nc, nr)]       # first piece after the screen
                    if tgt[2] and tgt[0] != my_col:
                        out.append(f"{c},{r}>{nc},{nr}")
        return out

    def legal_moves(self, s: BanqiState):
        if self.is_terminal(s):
            return []
        return self._moves(s)

    # ---- apply ------------------------------------------------------------ #
    def apply_move(self, s: BanqiState, move: str, rng=None) -> BanqiState:
        board = dict(s.board)
        if ">" not in move:               # flip
            cell = _cell(move)
            col, k, _up = board[cell]
            board[cell] = (col, k, True)
            colors = s.colors
            if colors is None:            # the first flip assigns colours
                colors = col if s.to_move == 0 else 1 - col
            return BanqiState(board=board, colors=colors, to_move=1 - s.to_move,
                              quiet=0, ply=s.ply + 1, reps={}, draw=None)
        frm, to = (_cell(x) for x in move.split(">"))
        piece = board.pop(frm)
        captured = to in board
        board[to] = piece
        if captured:
            quiet, reps, draw = 0, {}, None
        else:
            quiet = s.quiet + 1
            reps = dict(s.reps)
            key = _poskey(board, 1 - s.to_move)
            reps[key] = reps.get(key, 0) + 1
            draw = "repetition" if reps[key] >= 3 else None
        return BanqiState(board=board, colors=s.colors, to_move=1 - s.to_move,
                          quiet=quiet, ply=s.ply + 1, reps=reps, draw=draw)

    # ---- termination ------------------------------------------------------ #
    def is_terminal(self, s: BanqiState) -> bool:
        if s.draw is not None or s.quiet >= QUIET_CAP or s.ply >= PLY_CAP:
            return True
        return not self._moves(s)

    def returns(self, s: BanqiState):
        if not self._moves(s):            # no legal move at your turn: you lose
            return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]
        return [0.0, 0.0]                 # repetition / no-progress / ply-cap draw

    # ---- serialize --------------------------------------------------------- #
    def serialize(self, s: BanqiState) -> dict:
        return {
            "board": {f"{c},{r}": [col, k, up]
                      for (c, r), (col, k, up) in s.board.items()},
            "colors": s.colors,
            "to_move": s.to_move,
            "quiet": s.quiet,
            "ply": s.ply,
            "reps": dict(s.reps),
            "draw": s.draw,
        }

    def deserialize(self, d: dict) -> BanqiState:
        return BanqiState(
            board={_cell(k): (v[0], v[1], bool(v[2])) for k, v in d["board"].items()},
            colors=d.get("colors"),
            to_move=d["to_move"],
            quiet=d.get("quiet", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            draw=d.get("draw"),
        )

    # ---- bot heuristic (material at the rollout cutoff) -------------------- #
    def heuristic(self, s: BanqiState):
        if s.colors is None:
            return [0.0, 0.0]
        import math
        bal = 0.0                          # positive = seat 0's colour is ahead
        for (col, k, _up) in s.board.values():
            v = PIECE_VALUES[k]
            bal += v if col == s.colors else -v
        score = math.tanh(bal / 10.0)
        return [score, -score]

    # ---- presentation ------------------------------------------------------ #
    def describe_move(self, s: BanqiState, move: str) -> str:
        if ">" not in move:
            return f"flip {move}"
        frm, to = (_cell(x) for x in move.split(">"))
        col, k, _up = s.board[frm]
        cap = to in s.board
        return f"{k}{frm[0]},{frm[1]}{'x' if cap else '-'}{to[0]},{to[1]}"

    def _seat_name(self, s: BanqiState, seat: int) -> str:
        if s.colors is None:
            return f"P{seat + 1}"
        col = s.colors if seat == 0 else 1 - s.colors
        return f"{COLOR_NAMES[col]} (P{seat + 1})"

    def render(self, s: BanqiState, perspective=None) -> dict:
        pieces = []
        for (c, r), (col, k, up) in s.board.items():
            if not up:
                # Face-down: a neutral "?" disc. The piece's identity is NEVER
                # emitted here (no kind, no colour, no owner) — no UI leak.
                pieces.append({"cell": f"{c},{r}", "label": "?",
                               "fill": "#6b5b3e", "stroke": "#e4d6b0"})
            else:
                owner = 0 if col == s.colors else 1
                pieces.append({"cell": f"{c},{r}", "owner": owner, "label": k})

        hidden = sum(1 for p in s.board.values() if not p[2])
        if s.draw is not None:
            caption = "Draw (threefold repetition)"
        elif s.quiet >= QUIET_CAP:
            caption = f"Draw ({QUIET_CAP} moves without a flip or capture)"
        elif s.ply >= PLY_CAP:
            caption = "Draw (ply cap)"
        elif not self._moves(s):
            caption = f"{self._seat_name(s, 1 - s.to_move)} wins — {self._seat_name(s, s.to_move)} cannot move"
        elif s.colors is None:
            caption = "P1 flips any piece — its colour becomes P1's side"
        else:
            caption = f"{self._seat_name(s, s.to_move)} to move — {hidden} face-down"

        return {
            "board": {"type": "square", "width": WIDTH, "height": HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
