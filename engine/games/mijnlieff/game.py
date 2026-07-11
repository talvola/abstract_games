"""Mijnlieff (Andy Hopwood, 2010) -- the "you choose where I play" line game.

Winner of the UK Games Expo 2010 Best Abstract Game award. 4x4 board (cell ids
"c,r", c/r in 0..3). Each player has EIGHT tiles in their colour: TWO each of
FOUR types. The just-placed tile's type dictates where the OPPONENT must play
on their next turn (and next turn ONLY -- tiles exert no permanent restriction,
and intervening pieces do NOT block the straight/diagonal lines).

The four types (letters used in this package; official names from the Hopwood
Games rules sheet):

  S  STRAIGHTS  "Makes your opponent play into any one of the empty squares
                 that lie in a straight line from where you play it."
                 (= same row or column, any distance)
  D  DIAGONALS  "... in a diagonal line from where you play it."
                 (= same diagonal, any distance)
  P  PUSHERS    "... any one of the empty spaces that DO NOT touch the square
                 you play this into."  (not one of the 8 neighbouring squares)
  L  PULLERS    "... any one of the empty spaces that touch the square you
                 play this into."     (one of the 8 neighbouring squares)

FIRST MOVE.  "Light begins by playing any piece into any outside space" -- the
first tile must go on one of the 12 squares around the edge of the board (the
central 2x2 is barred for the opening placement only).

PASSING.  "If you are unable to play because there are no legal spaces
available you must PASS. If the other player PASSES you have a free play into
ANY space on the board."  The pass is forced, so this package resolves it
inside apply_move: the same player simply moves again, unconstrained.

ENDING.  "As soon as one player places their last piece their opponent gets
ONE last chance to play, which they forsake if they have to PASS, and the game
ends."  ("ONE last chance means ONE last piece.")

SCORING.  "Players score 1 point for each straight or diagonal continuous LINE
of three pieces in their colour. Longer lines score more points, 1 extra point
for each extra piece. So a line of 4 = 2 points."  Lines must be consecutive
(a gap or an opposing piece interrupts). Implemented as: 1 point per set of 3
consecutive collinear cells (orthogonal or diagonal) all in your colour -- a
line of 4 contains two such windows = 2 points. Highest score wins; an equal
score is an honest DRAW (the official sheet specifies no tiebreak).

(Rules verified against the official Hopwood Games rules sheet
[boardspace.net/mijnlieff/english/Mijnlieff_Rules.pdf] and Kate Morley's
solved-game analysis [iamkate.com/data/mijnlieff/], which agree on all points.
Mijnlieff is a win for the second player with perfect play.)

Move encoding (reserve-tray drop, as in Quantik/Gobblet):
    "<type>@c,r"  -- e.g. "S@1,0" places a Straight on cell (1,0).
In the web UI: click your tile chip in the reserve tray, then a highlighted
cell. The squares the current player is allowed to use are tinted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 4
TYPES = ["S", "D", "P", "L"]
TYPE_NAME = {"S": "Straight", "D": "Diagonal", "P": "Pusher", "L": "Puller"}
TYPE_GLYPH = {"S": "✚", "D": "✕", "P": "◯", "L": "●"}
# S = orthogonal arrows, D = diagonal arrows, P = large (hollow) circle,
# L = small (filled) circle -- matching the official iconography.

# The 4 line directions for scoring windows of 3.
_DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


def _cell(sv: str):
    c, r = sv.split(",")
    return int(c), int(r)


def _on_board(c: int, r: int) -> bool:
    return 0 <= c < N and 0 <= r < N


@dataclass
class MState:
    # board[(c, r)] -> (owner, type)
    board: dict = field(default_factory=dict)
    # hands[owner] -> {type: count} remaining off-board
    hands: dict = field(default_factory=dict)
    to_move: int = 0
    # The placement constraining the CURRENT mover: (type, c, r), or None for a
    # free placement (after an opponent pass). The empty board = the opening
    # edge restriction.
    constraint: Optional[tuple] = None
    last_cell: Optional[tuple] = None   # last placement, for the UI highlight
    just_passed: Optional[int] = None   # seat that just had to pass (caption)
    last_chance: bool = False           # current mover is on the ONE final tile
    finished: bool = False


class Mijnlieff(Game):
    uid = "mijnlieff"
    name = "Mijnlieff"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> MState:
        hands = {0: {t: 2 for t in TYPES}, 1: {t: 2 for t in TYPES}}
        return MState(board={}, hands=hands, to_move=0)

    def current_player(self, s: MState) -> int:
        return s.to_move

    # --- placement legality -------------------------------------------------
    @staticmethod
    def _allowed(board: dict, constraint: Optional[tuple], c: int, r: int) -> bool:
        """May a tile go on empty cell (c, r) under `constraint`?"""
        if not board:
            # Opening move: any OUTSIDE (edge) square -- not the central 2x2.
            return c in (0, N - 1) or r in (0, N - 1)
        if constraint is None:          # free placement after a pass
            return True
        t, pc, pr = constraint
        dc, dr = c - pc, r - pr
        if t == "S":                    # same row or column, any distance
            return dc == 0 or dr == 0
        if t == "D":                    # same diagonal, any distance
            return abs(dc) == abs(dr)   # (dc,dr)==(0,0) impossible: occupied
        cheb = max(abs(dc), abs(dr))
        if t == "L":                    # puller: one of the 8 touching squares
            return cheb == 1
        return cheb > 1                 # pusher: NOT touching

    def _targets(self, s_board: dict, constraint: Optional[tuple]):
        return [(c, r) for c in range(N) for r in range(N)
                if (c, r) not in s_board
                and self._allowed(s_board, constraint, c, r)]

    def legal_moves(self, s: MState):
        if self.is_terminal(s):
            return []
        me = s.to_move
        avail = [t for t in TYPES if s.hands[me].get(t, 0) > 0]
        return [f"{t}@{c},{r}"
                for (c, r) in self._targets(s.board, s.constraint)
                for t in avail]

    # --- scoring --------------------------------------------------------------
    @staticmethod
    def _score(board: dict, player: int) -> int:
        """1 point per window of 3 consecutive collinear cells all owned by
        `player` (orthogonal or diagonal). A run of 4 = two windows = 2 pts."""
        pts = 0
        for c in range(N):
            for r in range(N):
                for dc, dr in _DIRS:
                    if not _on_board(c + 2 * dc, r + 2 * dr):
                        continue
                    if all(board.get((c + i * dc, r + i * dr), (None,))[0] == player
                           for i in range(3)):
                        pts += 1
        return pts

    def scores(self, s: MState):
        return [self._score(s.board, p) for p in (0, 1)]

    # --- moves ----------------------------------------------------------------
    def apply_move(self, s: MState, move: str, rng=None) -> MState:
        t, cell_s = move.split("@")
        c, r = _cell(cell_s)
        me = s.to_move
        board = dict(s.board)
        hands = {p: dict(h) for p, h in s.hands.items()}
        board[(c, r)] = (me, t)
        hands[me][t] -= 1

        ns = MState(board=board, hands=hands, to_move=me,
                    constraint=(t, c, r), last_cell=(c, r))

        opp = 1 - me
        opp_can = (sum(hands[opp].values()) > 0
                   and bool(self._targets(board, (t, c, r))))

        if s.last_chance:
            # This WAS the one final tile: the game ends now, regardless.
            ns.finished = True
        elif sum(hands[me].values()) == 0:
            # I placed my last tile: the opponent gets ONE last chance,
            # forsaken if they'd have to pass.
            if opp_can:
                ns.to_move = opp
                ns.last_chance = True
            else:
                ns.finished = True
        elif opp_can:
            ns.to_move = opp
        else:
            # Opponent must PASS -> I play again, into ANY empty square.
            ns.constraint = None
            ns.just_passed = opp
        return ns

    def is_terminal(self, s: MState) -> bool:
        return s.finished

    def returns(self, s: MState):
        a, b = self.scores(s)
        if a == b:
            return [0.0, 0.0]
        return [1.0, -1.0] if a > b else [-1.0, 1.0]

    def heuristic(self, s: MState):
        import math
        a, b = self.scores(s)
        v = math.tanh((a - b) / 2.0)
        return [v, -v]

    # --- serialization ----------------------------------------------------------
    def serialize(self, s: MState) -> dict:
        return {
            "board": {f"{c},{r}": [o, t] for (c, r), (o, t) in s.board.items()},
            "hands": {str(p): dict(h) for p, h in s.hands.items()},
            "to_move": s.to_move,
            "constraint": (list(s.constraint) if s.constraint else None),
            "last_cell": (list(s.last_cell) if s.last_cell else None),
            "just_passed": s.just_passed,
            "last_chance": s.last_chance,
            "finished": s.finished,
        }

    def deserialize(self, d: dict) -> MState:
        con = d.get("constraint")
        lc = d.get("last_cell")
        return MState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            hands={int(p): dict(h) for p, h in d["hands"].items()},
            to_move=d["to_move"],
            constraint=(con[0], con[1], con[2]) if con else None,
            last_cell=(lc[0], lc[1]) if lc else None,
            just_passed=d.get("just_passed"),
            last_chance=bool(d.get("last_chance")),
            finished=bool(d.get("finished")),
        )

    def describe_move(self, s: MState, move: str) -> str:
        t, cell_s = move.split("@")
        c, r = _cell(cell_s)
        return f"{TYPE_NAME[t]} @ {c + 1},{r + 1}"

    # --- rendering ---------------------------------------------------------------
    def render(self, s: MState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": o, "label": TYPE_GLYPH[t]}
                  for (c, r), (o, t) in s.board.items()]

        highlights = []
        if s.last_cell:
            highlights.append({"cell": f"{s.last_cell[0]},{s.last_cell[1]}",
                               "kind": "last-move"})

        # Tint the squares the current player is allowed to use.
        tints = {}
        if not s.finished:
            for (c, r) in self._targets(s.board, s.constraint):
                tints[f"{c},{r}"] = "#24321f"

        reserve = {str(p): {t: n for t, n in s.hands[p].items() if n > 0}
                   for p in (0, 1)}

        names = {0: "Red", 1: "Blue"}
        a, b = self.scores(s)
        if s.finished:
            if a == b:
                cap = f"Game over — draw {a}–{b}"
            else:
                w = 0 if a > b else 1
                cap = f"Game over — {names[w]} wins {max(a, b)}–{min(a, b)}"
        else:
            cap = f"{names[s.to_move]} to move"
            if not s.board:
                cap += " — first tile must go on an edge square"
            elif s.constraint is None:
                who = names.get(s.just_passed, "Opponent")
                cap += f" — {who} passed: play any empty square"
            else:
                t, pc, pr = s.constraint
                where = {
                    "S": f"in line (row/column) with {pc + 1},{pr + 1}",
                    "D": f"on a diagonal through {pc + 1},{pr + 1}",
                    "L": f"touching {pc + 1},{pr + 1}",
                    "P": f"NOT touching {pc + 1},{pr + 1}",
                }[t]
                cap += f" — {TYPE_NAME[t]}: must play {where}"
            if s.last_chance:
                cap += " (final tile)"
            cap += f"  [score {a}–{b}]"

        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "reserve": reserve,
            "highlights": highlights,
            "caption": cap,
        }
