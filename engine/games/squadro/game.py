"""Squadro (Adrián Jiménez Pascual, Gigamic 2018).

Two players race 5 pieces each across a 7x7 board and back. Each piece travels
in a straight line along its own line at a fixed SPEED read from the dots on its
starting cell; the speed on the *return* trip is the complement (out+return = 4,
so 1<->3, 2<->2, 3<->1). First player to send FOUR of their five pieces on a full
round trip (across and back to the start line) wins.

Board / coordinates (platform convention: cell "col,row", col left->right 0..6,
row bottom->top 0..6 — Board.jsx draws row 0 at the BOTTOM):

  * WHITE  (seat 0) has one piece on each of rows 1..5. White moves HORIZONTALLY:
    outbound left->right (start base col 0, turnaround base col 6), then back.
  * BLACK  (seat 1) has one piece on each of cols 1..5. Black moves VERTICALLY:
    outbound bottom->top (start base row 0, turnaround base row 6), then back.

The two players' start cells carry DIFFERENT (complementary) dot patterns — this
asymmetry is the real board (verified vs the Gigamic rulebook and M. Braquet's
reference implementation):

    White outbound speed by ROW  r: {1:3, 2:1, 3:2, 4:1, 5:3}
    Black outbound speed by COL  c: {1:1, 2:3, 3:2, 4:3, 5:1}
    return speed = 4 - outbound

MOVEMENT (the crux). Pick one of your non-finished pieces (encoded by its current
cell "col,row" — deterministic destination). It advances up to `speed` tiles in
its current direction, one tile at a time:
  * If a step lands on the far edge, the piece TURNS AROUND (now points home) and
    STOPS immediately, even with movement left. Its speed becomes the return speed.
  * If a step lands on the start line (while returning) the piece FINISHES (leaves
    the board).
  * If a step lands on a cell occupied by an opponent piece, the piece JUMPS the
    entire CONTIGUOUS group of opponent pieces (landing on the first free cell just
    beyond) and STOPS, even with movement left. Every jumped opponent returns to
    its base — the START base if it had not yet turned around, the TURNAROUND base
    if it was already on its return trip.
Because each player's pieces are on distinct lines, a moving piece only ever meets
OPPONENT pieces (never its own), and the base columns/rows (0 and 6 on a piece's
travel axis) are never occupied by the opponent, so bases are safe.

Termination: pieces only advance, but jumps knock opponents back, so mutual
knock-back could loop. Honest backstops: threefold repetition of the position and
a hard ply cap both yield a DRAW (returns [0,0]).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 7          # board is 7x7 (coords 0..6)
FAR = 6        # far edge / turnaround coordinate
NPIECES = 5
WIN = 4        # finish 4 of 5 to win (n_pieces - 1)

NAMES = {0: "White", 1: "Black"}

# Outbound speeds (return = 4 - outbound). Indexed by the piece's LINE number 1..5
# (row for White, column for Black). Both patterns are palindromes; they are the
# complement of each other at every line index (White[k] + Black[k] == 4).
WHITE_OUT = {1: 3, 2: 1, 3: 2, 4: 1, 5: 3}   # by row
BLACK_OUT = {1: 1, 2: 3, 3: 2, 4: 3, 5: 1}   # by col

# Honest draw backstops.
PLY_CAP = 1000
REP_LIMIT = 3


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class SquadroState:
    # Each piece: {"col": int, "row": int, "ret": bool, "fin": bool}.
    # white[i] rides row i+1; black[i] rides col i+1.
    white: list = field(default_factory=list)
    black: list = field(default_factory=list)
    to_move: int = 0
    winner: Optional[int] = None
    draw: bool = False
    plies: int = 0
    reps: dict = field(default_factory=dict)   # position signature -> count


class Squadro(Game):
    uid = "squadro"
    name = "Squadro"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup -----------------------------------------------------------

    def initial_state(self, options=None, rng=None) -> SquadroState:
        white = [{"col": 0, "row": i + 1, "ret": False, "fin": False}
                 for i in range(NPIECES)]              # rows 1..5, start col 0
        black = [{"col": i + 1, "row": 0, "ret": False, "fin": False}
                 for i in range(NPIECES)]              # cols 1..5, start row 0
        s = SquadroState(white=white, black=black, to_move=0)
        s.reps = {self._sig(s): 1}
        return s

    def current_player(self, s: SquadroState) -> int:
        return s.to_move

    # ---- speeds / geometry ----------------------------------------------

    @staticmethod
    def _out_speed(player: int, piece: dict) -> int:
        return WHITE_OUT[piece["row"]] if player == 0 else BLACK_OUT[piece["col"]]

    @classmethod
    def _speed(cls, player: int, piece: dict) -> int:
        out = cls._out_speed(player, piece)
        return (4 - out) if piece["ret"] else out

    @staticmethod
    def _step(player: int, piece: dict) -> None:
        """Move the piece one tile in its current direction; set ret/fin at edges."""
        if player == 0:  # White: horizontal
            if not piece["ret"]:
                piece["col"] += 1
                if piece["col"] >= FAR:
                    piece["ret"] = True
            else:
                piece["col"] -= 1
                if piece["col"] <= 0:
                    piece["fin"] = True
        else:            # Black: vertical
            if not piece["ret"]:
                piece["row"] += 1
                if piece["row"] >= FAR:
                    piece["ret"] = True
            else:
                piece["row"] -= 1
                if piece["row"] <= 0:
                    piece["fin"] = True

    @staticmethod
    def _send_home(opp_player: int, piece: dict) -> None:
        """A jumped opponent returns to its base: start base if outbound, turnaround
        base if it had already turned around."""
        if opp_player == 0:  # White opponent rides a fixed row, base cols 0/6
            piece["col"] = FAR if piece["ret"] else 0
        else:                # Black opponent rides a fixed col, base rows 0/6
            piece["row"] = FAR if piece["ret"] else 0

    @staticmethod
    def _opp_at(piece: dict, opp: list):
        """Index of an (unfinished) opponent piece sharing the piece's cell, else None."""
        for j, o in enumerate(opp):
            if not o["fin"] and o["col"] == piece["col"] and o["row"] == piece["row"]:
                return j
        return None

    def _advance(self, player: int, piece: dict, opp: list) -> None:
        """Apply one full move to `piece` (mutating it and `opp`)."""
        speed = self._speed(player, piece)
        opp_player = 1 - player
        for _ in range(speed):
            was_ret = piece["ret"]
            self._step(player, piece)
            if piece["ret"] != was_ret:      # just turned around -> stop
                return
            if piece["fin"]:                 # reached home -> stop
                return
            if self._opp_at(piece, opp) is not None:
                # jump the whole contiguous group, one opponent per extra step
                while True:
                    j = self._opp_at(piece, opp)
                    if j is None:
                        break
                    self._step(player, piece)          # hop over
                    self._send_home(opp_player, opp[j])  # knocked-back piece home
                    if piece["fin"]:
                        break
                return                       # crossing ends the move

    # ---- moves -----------------------------------------------------------

    def legal_moves(self, s: SquadroState) -> list[str]:
        if self.is_terminal(s):
            return []
        mine = s.white if s.to_move == 0 else s.black
        # A piece is selected by its current cell; each is unique and always movable.
        return [f"{p['col']},{p['row']}" for p in mine if not p["fin"]]

    def apply_move(self, s: SquadroState, move: str, rng=None) -> SquadroState:
        me = s.to_move
        white = [dict(p) for p in s.white]
        black = [dict(p) for p in s.black]
        mine, opp = (white, black) if me == 0 else (black, white)

        col, row = _cell(move)
        idx = next(i for i, p in enumerate(mine)
                   if not p["fin"] and p["col"] == col and p["row"] == row)
        self._advance(me, mine[idx], opp)

        ns = SquadroState(white=white, black=black, to_move=1 - me,
                          plies=s.plies + 1, reps=dict(s.reps))

        # win: 4 finished
        if sum(1 for p in white if p["fin"]) >= WIN:
            ns.winner = 0
        elif sum(1 for p in black if p["fin"]) >= WIN:
            ns.winner = 1

        if ns.winner is None:
            sig = self._sig(ns)
            ns.reps[sig] = ns.reps.get(sig, 0) + 1
            if ns.reps[sig] >= REP_LIMIT or ns.plies >= PLY_CAP:
                ns.draw = True
        return ns

    def is_terminal(self, s: SquadroState) -> bool:
        return s.winner is not None or s.draw

    def returns(self, s: SquadroState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    # ---- signatures / serialization -------------------------------------

    @staticmethod
    def _sig(s: SquadroState) -> str:
        def enc(lst):
            return ";".join(f"{p['col']},{p['row']},{int(p['ret'])},{int(p['fin'])}"
                            for p in lst)
        return f"{s.to_move}|{enc(s.white)}|{enc(s.black)}"

    def serialize(self, s: SquadroState) -> dict:
        return {
            "white": [dict(p) for p in s.white],
            "black": [dict(p) for p in s.black],
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "plies": s.plies,
            "reps": dict(s.reps),
        }

    def deserialize(self, d: dict) -> SquadroState:
        def dec(lst):
            return [{"col": int(p["col"]), "row": int(p["row"]),
                     "ret": bool(p["ret"]), "fin": bool(p["fin"])} for p in lst]
        return SquadroState(
            white=dec(d["white"]),
            black=dec(d["black"]),
            to_move=d["to_move"],
            winner=d["winner"],
            draw=d.get("draw", False),
            plies=d.get("plies", 0),
            reps={k: int(v) for k, v in d.get("reps", {}).items()},
        )

    # ---- move notation ---------------------------------------------------

    def describe_move(self, s: SquadroState, move: str) -> str:
        me = s.to_move
        mine = [dict(p) for p in (s.white if me == 0 else s.black)]
        opp = [dict(p) for p in (s.black if me == 0 else s.white)]
        col, row = _cell(move)
        idx = next(i for i, p in enumerate(mine)
                   if not p["fin"] and p["col"] == col and p["row"] == row)
        piece = mine[idx]
        before = (piece["col"], piece["row"])
        opp_before = [(o["col"], o["row"]) for o in opp]
        self._advance(me, piece, opp)
        opp_after = [(o["col"], o["row"]) for o in opp]
        jumped = opp_before != opp_after      # some opponent was knocked back
        tag = ""
        if piece["fin"]:
            tag = " ✓"
        elif jumped:
            tag = " ×"
        return (f"{NAMES[me][0]} {before[0]},{before[1]}→"
                f"{piece['col']},{piece['row']}{tag}")

    # ---- render ----------------------------------------------------------

    def render(self, s: SquadroState, perspective=None) -> dict:
        pieces = []
        for p in s.white:
            if p["fin"]:
                continue
            pieces.append({
                "cell": f"{p['col']},{p['row']}",
                "owner": 0,
                "label": str(self._speed(0, p)),
                "prongs": [6] if p["ret"] else [2],   # 6=left(home), 2=right(out)
            })
        for p in s.black:
            if p["fin"]:
                continue
            pieces.append({
                "cell": f"{p['col']},{p['row']}",
                "owner": 1,
                "label": str(self._speed(1, p)),
                "prongs": [4] if p["ret"] else [0],   # 4=down(home), 0=up(out)
            })

        tints = {}
        for r in range(1, 6):
            tints[f"0,{r}"] = "#e8c3bb"    # White start (left)
            tints[f"6,{r}"] = "#f2ddd9"    # White turnaround (right)
        for c in range(1, 6):
            tints[f"{c},0"] = "#bcc8e8"    # Black start (bottom)
            tints[f"{c},6"] = "#dde3f2"    # Black turnaround (top)

        wfin = sum(1 for p in s.white if p["fin"])
        bfin = sum(1 for p in s.black if p["fin"])
        if self.is_terminal(s):
            caption = "Draw" if s.draw else f"{NAMES[s.winner]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        caption += f"  |  finished — {NAMES[0]}: {wfin}/{WIN}, {NAMES[1]}: {bfin}/{WIN}"

        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
