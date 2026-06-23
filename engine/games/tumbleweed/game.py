"""Tumbleweed, by Mike Zapawa (2020).

A modern hex influence / area game played on a hexagonal board of hexagons
(a "hexhex") of side length N (default 8). Each hex holds at most ONE stack,
which is a pile of 1..K tokens of a SINGLE colour (the colour that "owns" /
controls that hex).

LINE OF SIGHT.  For a given mover and a target hex, look outward along each of
the 6 straight hex directions. Along a direction, the FIRST stack encountered
is the only relevant one: if it belongs to the mover it contributes 1 to the
target's line-of-sight (LOS) count; either way that stack BLOCKS sight beyond
it, so nothing further along that direction is seen. The mover's LOS to a hex
is therefore an integer in 0..6 (one per direction). The mover's own / enemy /
neutral stacks all block sight; only the FIRST stack on each ray matters.

MOVE.  Pick any hex (empty, yours, enemy, or the neutral centre) and compute
its LOS count L for the mover. You may place a stack of your colour and height
exactly L on that hex IFF:

  * L >= 1                      (at least one of your stacks sees it), AND
  * L > current_height(target)  (strictly taller than what is there now).

Placing REPLACES whatever stack was on the target. So with L you can settle an
empty hex (height 0 -> L >= 1), grow your own shorter stack, or capture a
shorter enemy / the neutral stack. A player may also PASS.

SETUP.  A neutral stack of height 2 sits on the centre hex (0,0). Each player
gets ONE starting stack of height 1. We implement a SIMPLE FIXED opening (see
rules.md): the official game uses a host/guest "settlement" opening where the
players choose the two starting hexes; that adds an asymmetric meta-phase we
deliberately omit. Player 0 (White) starts at the NW-ish corner cell, player 1
(Black) at the symmetric SE-ish corner cell, both height 1.

END.  The game ends when both players pass in succession, or when no legal
non-pass move remains for the player to move (they are forced to pass and the
opponent then also has no move / passes). A hard ply cap also forces an end as
a termination safety net (each non-pass placement strictly changes the board,
so genuine play cannot loop).

WIN.  Scored by "OWNED + CONTROLLED": at game end EVERY cell is awarded. An
OCCUPIED cell counts for whoever's colour tops it (neutral stack -> nobody); an
EMPTY cell counts for the player with STRICTLY GREATER line-of-sight to it (same
LOS rule as placement). Equal LOS (including 0-0) is neutral. Highest total wins;
equal totals is a draw. (Both scores plus neutrals == the whole board.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NEUTRAL = -1  # owner of the centre stack at setup

# The six axial hex directions.
_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    """All on-board axial cells of a hexhex of side ``size`` (= N)."""
    out = []
    n = size - 1
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            s = -q - r
            if abs(q) <= n and abs(r) <= n and abs(s) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


def _cell(s: str) -> tuple[int, int]:
    q, r = s.split(",")
    return int(q), int(r)


def _start_cells(size: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """Fixed symmetric starting hexes for the two players.

    We use two opposite NON-corner border cells well away from the centre, so
    each player begins with a single height-1 stack that can already "see" the
    neutral centre. (q, -1) on the +q border and its point-reflection.
    """
    n = size - 1
    a = (n, -1)        # White: just below the +q corner, on the q=n edge
    b = (-n, 1)        # Black: the point-reflection through the centre
    return a, b


# Board maps (q, r) -> (owner, height): owner WHITE/BLACK/NEUTRAL, height >= 1.


@dataclass
class TumbleweedState:
    size: int = 8
    board: dict = field(default_factory=dict)   # (q, r) -> (owner, height)
    to_move: int = WHITE
    passes: int = 0                              # consecutive passes
    ply: int = 0
    last: Optional[tuple] = None                 # last placed cell
    winner: Optional[int] = None                 # set at game end (or None=draw)
    over: bool = False


def _los_count(board: dict, size: int, target: tuple, player: int) -> int:
    """Number of ``player`` stacks that have line-of-sight to ``target``.

    Along each of the 6 directions, find the FIRST occupied hex; it contributes
    1 iff it belongs to ``player``. A stack always blocks further sight. The
    target hex itself is not counted (we look strictly outward from it).
    """
    on = _cell_set(size)
    count = 0
    for dq, dr in _DIRS:
        q, r = target[0] + dq, target[1] + dr
        while (q, r) in on:
            stk = board.get((q, r))
            if stk is not None:
                if stk[0] == player:
                    count += 1
                break  # first stack blocks the rest of this ray
            q += dq
            r += dr
    return count


def _control_counts(board: dict, size: int) -> tuple[int, int]:
    """(white_score, black_score) — Tumbleweed's "owned + controlled" scoring.

    EVERY cell on the board is awarded at game end:

      * an OCCUPIED cell counts for the player whose colour tops it (the
        neutral stack counts for nobody);
      * an EMPTY cell counts for the player with STRICTLY GREATER line-of-sight
        to it (the same LOS rule as placement). Equal LOS (including 0-0) is
        neutral and counts for neither.

    white_score + black_score + neutrals == total cells on the board.
    """
    w = b = 0
    for cell in _cells(size):
        stk = board.get(cell)
        if stk is not None:
            if stk[0] == WHITE:
                w += 1
            elif stk[0] == BLACK:
                b += 1
            # NEUTRAL-topped occupied cell: counts for nobody
            continue
        # empty cell: awarded by strictly-greater line of sight
        lw = _los_count(board, size, cell, WHITE)
        lb = _los_count(board, size, cell, BLACK)
        if lw > lb:
            w += 1
        elif lb > lw:
            b += 1
        # equal (incl. 0-0): neutral
    return w, b


class Tumbleweed(Game):
    uid = "tumbleweed"
    name = "Tumbleweed"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> TumbleweedState:
        opts = options or {}
        size = int(opts.get("size", 8))
        a, b = _start_cells(size)
        board = {
            (0, 0): (NEUTRAL, 2),
            a: (WHITE, 1),
            b: (BLACK, 1),
        }
        return TumbleweedState(size=size, board=board, to_move=WHITE)

    def current_player(self, s: TumbleweedState) -> int:
        return s.to_move

    # -- move generation ---------------------------------------------------

    def _placements(self, s: TumbleweedState) -> list[str]:
        moves = []
        for cell in _cells(s.size):
            los = _los_count(s.board, s.size, cell, s.to_move)
            if los < 1:
                continue
            cur = s.board.get(cell)
            cur_h = cur[1] if cur is not None else 0
            if los > cur_h:
                moves.append(f"{cell[0]},{cell[1]}")
        return moves

    def legal_moves(self, s: TumbleweedState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = self._placements(s)
        moves.append("pass")  # passing is always legal
        return moves

    # -- transition --------------------------------------------------------

    def _ply_cap(self, size: int) -> int:
        # Generous safety cap; real games are far shorter. Each non-pass move
        # strictly changes the board, so this only guards against pathology.
        return 4 * len(_cells(size)) + 10

    def apply_move(self, s: TumbleweedState, move: str, rng=None) -> TumbleweedState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move
        if move == "pass":
            passes = s.passes + 1
            ply = s.ply + 1
            ns = TumbleweedState(
                size=s.size, board=dict(s.board), to_move=1 - mover,
                passes=passes, ply=ply, last=None,
            )
            self._maybe_finish(ns, force=(passes >= 2))
            return ns

        cell = _cell(move)
        if cell not in _cell_set(s.size):
            raise ValueError(f"off-board {move!r}")
        los = _los_count(s.board, s.size, cell, mover)
        cur = s.board.get(cell)
        cur_h = cur[1] if cur is not None else 0
        if los < 1 or los <= cur_h:
            raise ValueError(f"illegal placement {move!r}: los={los} cur_h={cur_h}")
        board = dict(s.board)
        board[cell] = (mover, los)  # replaces whatever was there
        ns = TumbleweedState(
            size=s.size, board=board, to_move=1 - mover,
            passes=0, ply=s.ply + 1, last=cell,
        )
        self._maybe_finish(ns)
        return ns

    def _maybe_finish(self, ns: TumbleweedState, force: bool = False):
        """Set winner/over on ``ns`` if the game has ended."""
        end = force
        if not end and ns.ply >= self._ply_cap(ns.size):
            end = True
        if not end:
            # Forced end if the player to move has no placement AND the other
            # player also has none (i.e. the board is fully locked). A single
            # side with no move simply passes on its turn; two passes then end
            # it via the `force` path above.
            if not self._placements(ns):
                # peek: does the opponent (next to move after a forced pass)
                # have any move?
                peek = TumbleweedState(size=ns.size, board=ns.board,
                                       to_move=1 - ns.to_move)
                if not self._placements(peek):
                    end = True
        if end:
            w, b = _control_counts(ns.board, ns.size)
            if w > b:
                ns.winner = WHITE
            elif b > w:
                ns.winner = BLACK
            else:
                ns.winner = None  # draw
            ns.over = True

    def is_terminal(self, s: TumbleweedState) -> bool:
        return s.over

    def returns(self, s: TumbleweedState) -> list[float]:
        if s.winner == WHITE:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- serialization -----------------------------------------------------

    def serialize(self, s: TumbleweedState) -> dict:
        return {
            "size": s.size,
            "board": {f"{q},{r}": [owner, h] for (q, r), (owner, h) in s.board.items()},
            "to_move": s.to_move,
            "passes": s.passes,
            "ply": s.ply,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "winner": s.winner,
            "over": s.over,
        }

    def deserialize(self, d: dict) -> TumbleweedState:
        last = d.get("last")
        return TumbleweedState(
            size=d["size"],
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            passes=d.get("passes", 0),
            ply=d.get("ply", 0),
            last=(_cell(last) if last else None),
            winner=d.get("winner"),
            over=d.get("over", False),
        )

    def describe_move(self, s: TumbleweedState, move: str) -> str:
        if move == "pass":
            return "pass"
        cell = _cell(move)
        los = _los_count(s.board, s.size, cell, s.to_move)
        return f"{move} (h{los})"

    # -- rendering ---------------------------------------------------------

    def render(self, s: TumbleweedState, perspective=None) -> dict:
        names = {WHITE: "White", BLACK: "Black"}
        pieces = []
        for (q, r), (owner, h) in s.board.items():
            p = {"cell": f"{q},{r}", "label": str(h)}
            if owner == NEUTRAL:
                p["owner"] = 0
                p["fill"] = "#9e9e9e"
                p["stroke"] = "#555555"
            else:
                p["owner"] = owner
            # stacking glyph: a tower of `h` bands of this owner.
            stack_owner = owner if owner != NEUTRAL else 0
            p["stack"] = [stack_owner] * h
            pieces.append(p)

        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})

        w, b = _control_counts(s.board, s.size)
        if s.over:
            if s.winner is None:
                caption = f"Draw — White {w}, Black {b}"
            else:
                caption = f"{names[s.winner]} wins — White {w}, Black {b}"
        else:
            caption = f"{names[s.to_move]} to move — White {w}, Black {b}"

        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
