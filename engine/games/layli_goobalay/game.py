"""Layli Goobalay -- the Somali multiple-lap mancala ("exercise with circles").

First described outside Somalia by G. Marin, *Somali Games*, JRAI 61: 499-511
(1931); the modern write-up followed here is Ralf Gering's article in *Abstract
Games* magazine, issue 13 (Spring 2003), pp. 9 + 14, with additional information
from Jama Musse Jama (*Layli Goobalay: Variante Somala del Gioco Nazionale
Africano*, Redsea-Online, Pisa 2002).

Board model: a WIDTH x 2 SQUARE board of holes. Player 0 = South (row 0, the
bottom row), player 1 = North (row 1). Each player owns the row nearest him.
Captured balls are tallied per player (there are no store pits). Balls are "dry
camel dung"; the article calls them balls, so does this module.

Rules in brief (see rules.md for the full page and every interpretation):

  * MULTIPLE-LAP (relay) sowing. Lift the whole contents of one of your own holes
    that is not an Uur and drop one ball per following hole, CLOCKWISE, around
    the whole 2*WIDTH ring (Uur holes are sown into like any other). If the last
    ball falls into an OCCUPIED hole you take that hole's contents, including the
    ball you just dropped, and sow another lap. The move ends only when the last
    ball falls into an EMPTY hole (or into an Uur).
  * If the last ball falls into an empty hole on YOUR OWN side, you capture that
    ball together with the contents of the hole OPPOSITE it, provided that hole
    holds one, two, or four-or-more balls.
  * If the opposite hole holds exactly THREE, one of the three is moved across so
    that both holes hold two. Those two holes are now an **Uur** ("pregnancy")
    and BOTH belong to their creator. An Uur may never be emptied by either
    player; balls are still sown into it, and if the last ball falls into an Uur
    the move simply ends. Every ball that ever lands in either hole of an Uur
    belongs to the Uur's creator.
  * Otherwise nothing is captured -- *abar*, "famine".  A relay chain that never
    dies (the balls circulate for ever) is also an abar; see rules.md.
  * The game ends when the player to move has NO legal move. Each side scores the
    balls he captured + the balls sitting in his own Uur's + the balls left on
    his own side outside Uur's. Most balls wins; an equal split is an honest DRAW.

CORRECTNESS ANCHOR: the magazine's endgame problem and its published solution
(both lines, with every 'U' / 'x n' annotation and the final margins) are
replayed by selftest.py. See that file and rules.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import tanh

from agp.game import Game

SOUTH, NORTH = 0, 1
SIDE_NAME = {SOUTH: "South", NORTH: "North"}

DEFAULT_WIDTH = 12
SEEDS_PER_HOLE = 4

# Anti-loop backstops.  A relay chain CAN be endless (rare, and only on the small
# boards: ~0.04% of moves on 2x6, none seen in 33 000 moves on 2x8 / 2x12).  The
# chain is a deterministic function of (hole in hand, board), so a repeated
# configuration proves it never ends; RELAY_WATCH says after how many laps to
# start watching for that repeat (the longest chain that DOES end, over ~2400
# random games on all three boards, is 95 laps -- so watching costs nothing in
# real play).  LAP_CAP is then only a memory/time guard.  The other two caps make
# the whole GAME terminate (SPEC hard invariant 5).
RELAY_WATCH = 512
LAP_CAP = 100000
NO_PROGRESS_CAP = 300     # plies with no capture / no new Uur / no growth of an
                          # Uur -> the balls "circulate in a repeating pattern"
PLY_CAP = 4000

# Translucent seat colours marking the two holes of an Uur with its OWNER's tint.
UUR_TINT = {SOUTH: "#d23b3b66", NORTH: "#3b6fd266"}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _key(pit) -> str:
    return "%d,%d" % pit


def _opposite(pit):
    """The hole directly across the board (same column, other row)."""
    return (pit[0], 1 - pit[1])


def _own_pits(width, player):
    return [(c, player) for c in range(width)]


def ring(width: int, direction: str):
    """The fixed sowing cycle, as a list of holes in sowing order.

    Rendered with South (row 0) at the bottom, the ANTI-clockwise cycle runs
    left->right along South's row, up the right edge, right->left along North's
    row and down the left edge.  CLOCKWISE (Marin's direction, the default) is
    its reverse: left->right along NORTH's row, then right->left along South's.

    Note that clockwise makes both players sow their own holes in INCREASING
    own-hole-number order (holes are numbered from each player's right).
    """
    ccw = ([(c, SOUTH) for c in range(width)]
           + [(c, NORTH) for c in range(width - 1, -1, -1)])
    return ccw if direction == "anticlockwise" else list(reversed(ccw))


def hole_number(pit, width: int) -> int:
    """Article notation: each player's holes are numbered 1..width from HIS RIGHT.

    South sits at the bottom facing up, so South's hole 1 is the right-hand
    column; North sits at the top facing down, so North's hole 1 is the
    left-hand column.
    """
    c, r = pit
    return (width - c) if r == SOUTH else (c + 1)


def pit_of_number(player: int, n: int, width: int):
    """Inverse of hole_number (used by selftest.py to replay printed notation)."""
    return (width - n, SOUTH) if player == SOUTH else (n - 1, NORTH)


@dataclass
class LayliState:
    board: dict = field(default_factory=dict)   # pit -> ball count
    uur: dict = field(default_factory=dict)     # pit -> owner (both holes of a pair)
    captured: list = field(default_factory=lambda: [0, 0])
    to_move: int = SOUTH
    width: int = DEFAULT_WIDTH
    direction: str = "clockwise"
    ply: int = 0
    no_progress: int = 0


class LayliGoobalay(Game):
    name = "Layli Goobalay"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> LayliState:
        opts = options or {}
        width = int(opts.get("size", DEFAULT_WIDTH))
        direction = str(opts.get("direction", "clockwise"))
        if direction not in ("clockwise", "anticlockwise"):
            direction = "clockwise"
        board = {(c, r): SEEDS_PER_HOLE for r in (SOUTH, NORTH)
                 for c in range(width)}
        return LayliState(board=board, uur={}, captured=[0, 0], to_move=SOUTH,
                          width=width, direction=direction, ply=0, no_progress=0)

    def current_player(self, s: LayliState) -> int:
        return s.to_move

    # -- core sowing --------------------------------------------------------
    def _resolve(self, s: LayliState, mover: int, start, _watch: bool = False):
        """Play one complete (multi-lap) move from `start`.  Pure.

        Returns (board, uur, captured, kind) where `kind` is the article's
        annotation for the move: "U" (an Uur was created), "x<n>" (n balls
        captured), "" (abar / the move died in an Uur).

        Fast path (`_watch=False`): just sow, for at most RELAY_WATCH laps.  If
        the chain has not died by then it is (in every case ever observed)
        endless, and the move is re-run from the top with `_watch=True`, which
        records every configuration and stops at the FIRST repeat -- see the
        "endless relay" note in rules.md.  `s` is never mutated, so re-running
        is safe.
        """
        board = dict(s.board)
        uur = dict(s.uur)
        order = ring(s.width, s.direction)
        idx = {p: i for i, p in enumerate(order)}
        n = len(order)
        own = mover                      # the mover's row == his seat index
        lap = start
        seen = set() if _watch else None

        for _ in range(LAP_CAP if _watch else RELAY_WATCH):
            if seen is not None:
                # The chain is a deterministic function of (hole in hand, board),
                # so one configuration seen twice proves the balls just circulate
                # for ever.  Nothing is ever captured, so the move is an abar --
                # and stopping at the FIRST repeat (rather than after some number
                # of laps) makes the outcome independent of any cap constant.
                key = (lap, tuple(board[p] for p in order))
                if key in seen:
                    return board, uur, 0, ""
                seen.add(key)
            balls = board[lap]
            board[lap] = 0
            i0 = idx[lap]
            last, before = lap, 0
            for step in range(1, balls + 1):
                pit = order[(i0 + step) % n]
                before = board[pit]
                board[pit] += 1
                last = pit

            if last in uur:
                # "if the last ball is dropped into an Uur hole, the move ends"
                return board, uur, 0, ""
            if before > 0:
                # occupied hole -> take its contents (incl. the last ball) & relay
                lap = last
                continue

            # the last ball fell into an EMPTY hole -> the move ends here
            if last[1] != own:
                return board, uur, 0, ""            # abar (opponent's side)
            opp = _opposite(last)
            if opp in uur:
                return board, uur, 0, ""            # an Uur may never be emptied
            k = board[opp]
            if k == 3:
                board[opp] = 2
                board[last] = 2
                uur[last] = mover
                uur[opp] = mover
                return board, uur, 0, "U"
            if k == 0:
                return board, uur, 0, ""            # abar (opposite hole empty)
            board[opp] = 0
            board[last] = 0
            return board, uur, k + 1, "x%d" % (k + 1)

        if not _watch:
            # RELAY_WATCH laps and still going -> endless.  Re-run canonically.
            return self._resolve(s, mover, start, _watch=True)
        # Not reached: the cycle watch always fires first on an endless chain
        # (worst period observed is ~27 000 laps).  Kept as a hard guard so a
        # pathological chain can never hang the server; also an abar.
        return board, uur, 0, ""

    # -- legal moves --------------------------------------------------------
    def _moves_for(self, s: LayliState, player: int) -> list:
        return [p for p in _own_pits(s.width, player)
                if s.board[p] > 0 and p not in s.uur]

    def legal_moves(self, s: LayliState) -> list:
        if self._capped(s):
            return []
        return [_key(p) for p in self._moves_for(s, s.to_move)]

    def _capped(self, s: LayliState) -> bool:
        return s.no_progress >= NO_PROGRESS_CAP or s.ply >= PLY_CAP

    # -- apply --------------------------------------------------------------
    def apply_move(self, s: LayliState, move: str, rng=None) -> LayliState:
        mover = s.to_move
        start = _cell(move)
        before_in_uur = sum(s.board[p] for p in s.uur)
        board, uur, captured, kind = self._resolve(s, mover, start)
        after_in_uur = sum(board[p] for p in uur)

        cap = list(s.captured)
        cap[mover] += captured
        # "Progress" = something irreversible happened (a capture, a new Uur, or
        # balls locked away inside an Uur).  Anything else may repeat forever.
        progress = captured > 0 or kind == "U" or after_in_uur > before_in_uur
        return LayliState(
            board=board, uur=uur, captured=cap, to_move=1 - mover,
            width=s.width, direction=s.direction, ply=s.ply + 1,
            no_progress=0 if progress else s.no_progress + 1,
        )

    # -- terminal / scoring -------------------------------------------------
    def is_terminal(self, s: LayliState) -> bool:
        return self._capped(s) or not self._moves_for(s, s.to_move)

    def scores(self, s: LayliState) -> list:
        pts = list(s.captured)
        for pit, n in s.board.items():
            owner = s.uur.get(pit)
            pts[pit[1] if owner is None else owner] += n
        return pts

    def returns(self, s: LayliState) -> list:
        a, b = self.scores(s)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: LayliState) -> list:
        a, b = self.scores(s)
        v = tanh((a - b) / float(2 * s.width))
        return [v, -v]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s: LayliState) -> dict:
        return {
            "board": {_key(p): n for p, n in s.board.items()},
            "uur": {_key(p): o for p, o in s.uur.items()},
            "captured": list(s.captured),
            "to_move": s.to_move,
            "width": s.width,
            "direction": s.direction,
            "ply": s.ply,
            "no_progress": s.no_progress,
        }

    def deserialize(self, d: dict) -> LayliState:
        return LayliState(
            board={_cell(k): v for k, v in d["board"].items()},
            uur={_cell(k): v for k, v in d.get("uur", {}).items()},
            captured=list(d["captured"]),
            to_move=d["to_move"],
            width=d.get("width", DEFAULT_WIDTH),
            direction=d.get("direction", "clockwise"),
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
        )

    # -- render -------------------------------------------------------------
    def render(self, s: LayliState, perspective=None) -> dict:
        pieces = [{"cell": _key(p), "owner": p[1], "label": str(n)}
                  for p, n in sorted(s.board.items())]
        tints = {_key(p): UUR_TINT[o] for p, o in s.uur.items()}

        a, b = self.scores(s)
        caption = "South %d — North %d" % (a, b)
        if self.is_terminal(s):
            caption += "  ·  " + ("South wins" if a > b else
                                  "North wins" if b > a else "Draw")
        else:
            caption += "  ·  %s to move" % SIDE_NAME[s.to_move]
        if s.uur:
            n_uur = len(s.uur) // 2
            caption += "  ·  %d Uur" % n_uur + ("s" if n_uur > 1 else "")

        return {
            "board": {"type": "square", "width": s.width, "height": 2,
                      "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }

    # -- move log -----------------------------------------------------------
    def describe_move(self, s: LayliState, move: str) -> str:
        pit = _cell(move)
        _, _, _, kind = self._resolve(s, s.to_move, pit)
        return "%s %d%s" % (SIDE_NAME[pit[1]], hole_number(pit, s.width), kind)
