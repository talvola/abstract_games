"""Super Halma -- Stephen Perkis' 10x10 variant of Halma (Abstract Games,
Issue 15, Autumn 2003).

Two players race their 19-piece "home camp" into the diagonally opposite
enemy camp. Player 0 (White, moves first) sits in the top-left corner around
(0,0); player 1 in the bottom-right corner. Camps are the 180-degree
rotationally symmetric staircase of 19 cells (per-row counts 5,5,4,3,2).
Nothing is ever captured -- pieces are never removed.

On your turn you make ONE of (never combined):
  (A) STEP -- move a piece to any of the 8 adjacent (orthogonal/diagonal)
      EMPTY squares.
  (B) JUMP -- Super Halma's defining move. Jump over ANY ONE piece (friend OR
      foe) that lies some number k >= 0 of EMPTY squares away in a straight
      line (one of the 8 directions), landing the SAME number k of empty
      squares beyond it, in that same straight line -- i.e. the landing is the
      mirror image of the start across the jumped piece. All k intervening
      squares on BOTH sides and the landing square must be empty. k = 0 is the
      ordinary adjacent Halma jump. From the landing you MAY continue jumping
      (each hop may pick a new direction); the whole chain is ONE move and you
      may stop after any hop.

Because only empty squares may lie between the mover and the jumped piece, the
jumped piece is always the FIRST occupied square encountered along that
direction. Pieces may enter and exit BOTH camps without restriction.

Moves are the platform's clickable cell-path notation: a single step or single
jump is "a>b"; a jump chain is "a>b>c>..." listing every square landed on.

WIN (anti-spoiling / squatter guard): you win when the OPPONENT's camp is
ENTIRELY OCCUPIED -- by any pieces -- AND at least one of those occupants is
your OWN. An enemy "squatter" parked in your target camp just fills a slot; it
cannot deny your win. (The article's elaborate "small print" anti-spoiling
winning conditions and trapped-piece draw clauses are simplified to this
normal win + squatter guard; see rules.md.)

Termination: no-progress + hard-ply caps -> DRAW (see below and rules.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

NAMES = {0: "White", 1: "Black"}

# 8 directions (king moves).
DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

SIZE = 10
# Per-row column counts of the top-left camp (19 pieces): rows 0..4 -> 5,5,4,3,2.
CAMP_ROWS = [5, 5, 4, 3, 2]

# Termination caps (conformance plays random games -> guarantee a terminal).
PLY_CAP = 500          # hard cap -> draw
NO_PROGRESS_CAP = 80   # plies without the moving player's goal-distance
                       # strictly dropping (or its home-fill count rising)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class SuperHalmaState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0
    no_progress: int = 0


# ---- camp geometry ---------------------------------------------------------

def _camp0():
    """Player 0's camp: the staircase anchored at the top-left corner (0,0)."""
    cells = set()
    for r, cnt in enumerate(CAMP_ROWS):
        for c in range(cnt):
            cells.add((c, r))
    return cells


def _camp1():
    """Player 1's camp: the 180-degree rotation into the bottom-right corner."""
    return {(SIZE - 1 - c, SIZE - 1 - r) for (c, r) in _camp0()}


def camps():
    return _camp0(), _camp1()


def _start_board() -> dict:
    c0, c1 = camps()
    b = {}
    for sq in c0:
        b[sq] = 0
    for sq in c1:
        b[sq] = 1
    return b


def _goal_corner(player: int):
    """The single corner cell of the player's TARGET camp -- reference point
    for the goal-distance no-progress metric."""
    return (SIZE - 1, SIZE - 1) if player == 0 else (0, 0)


def _goal_distance(board: dict, player: int) -> int:
    """Sum of Chebyshev distances of `player`'s pieces to their target corner.
    A move that lowers this is unambiguous forward progress."""
    gc, gr = _goal_corner(player)
    tot = 0
    for (c, r), pl in board.items():
        if pl == player:
            tot += max(abs(c - gc), abs(r - gr))
    return tot


def _filled_count(board: dict, player: int) -> int:
    """How many of `player`'s OWN pieces already sit in its target camp.
    During the final fill the corner-distance can plateau while this rises."""
    target = _camp1() if player == 0 else _camp0()
    return sum(1 for sq in target if board.get(sq) == player)


class SuperHalma(Game):
    uid = "super_halma"
    name = "Super Halma"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SuperHalmaState:
        return SuperHalmaState(board=_start_board(), to_move=0)

    def current_player(self, s: SuperHalmaState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def _steps(self, s: SuperHalmaState, frm):
        c, r = frm
        out = []
        for dc, dr in DIRS:
            t = (c + dc, r + dr)
            if 0 <= t[0] < SIZE and 0 <= t[1] < SIZE and t not in s.board:
                out.append([frm, t])
        return out

    def _jump_dests(self, s: SuperHalmaState, frm):
        """The SET of squares reachable from `frm` by one or more jumps.

        Because nothing is captured, a jump chain is a pure relocation of the
        moving piece -- only its final square affects the outcome, and a player
        may stop after ANY hop -- so every reachable landing square is a legal
        jump destination and the intermediate path is immaterial. We therefore
        flood-fill the reachable landings (each square processed once, a global
        visited set), which is O(cells) and avoids the combinatorial blow-up of
        enumerating every distinct chain path.

        Single hop in a direction (dc, dr): find the FIRST occupied square at
        distance d (all d-1 squares before it must be empty -- "any number of
        empty spaces away"), which is the jumped piece; land at the mirror
        distance 2d, requiring squares d+1..2d-1 and the landing to be empty.
        The moving piece is treated as vacated for the whole chain."""
        occ = s.board

        def occupied(sq):
            if sq == frm:
                return False
            return sq in occ

        def onboard(sq):
            return 0 <= sq[0] < SIZE and 0 <= sq[1] < SIZE

        def hops_from(here):
            c, r = here
            outs = []
            for dc, dr in DIRS:
                # First occupied square along (dc, dr): squares 1..d-1 empty.
                d = 1
                blocked = False
                while True:
                    over = (c + d * dc, r + d * dr)
                    if not onboard(over):
                        blocked = True
                        break
                    if occupied(over):
                        break
                    d += 1
                if blocked:
                    continue  # ran off the board with no piece to jump over
                # `over` (distance d) is the jumped piece; land at distance 2d
                # (the mirror), needing squares d+1..2d-1 empty and land empty.
                clear = True
                for k in range(d + 1, 2 * d):
                    mid = (c + k * dc, r + k * dr)
                    if not onboard(mid) or occupied(mid):
                        clear = False
                        break
                if not clear:
                    continue
                land = (c + 2 * d * dc, r + 2 * d * dr)
                if onboard(land) and not occupied(land):
                    outs.append(land)
            return outs

        reachable = set()
        stack = [frm]
        seen = {frm}
        while stack:
            here = stack.pop()
            for land in hops_from(here):
                if land not in seen:
                    seen.add(land)
                    reachable.add(land)
                    stack.append(land)
        return reachable

    def _all_moves(self, s: SuperHalmaState) -> list[tuple]:
        """Return the deduped set of (frm, dest) pairs. Every move is a single
        2-cell hop `frm>dest`: a step (adjacent empty) or a jump (any
        flood-fill-reachable landing). A jump landing that coincides with a step
        square is the same move and is deduped automatically."""
        out = set()
        for (c, r), pl in s.board.items():
            if pl != s.to_move:
                continue
            frm = (c, r)
            for path in self._steps(s, frm):
                out.add((frm, path[1]))
            for dest in self._jump_dests(s, frm):
                out.add((frm, dest))
        return sorted(out)

    def _draw(self, s: SuperHalmaState) -> bool:
        return s.ply >= PLY_CAP or s.no_progress >= NO_PROGRESS_CAP

    def legal_moves(self, s: SuperHalmaState) -> list[str]:
        if s.winner is not None or self._draw(s):
            return []
        return [f"{frm[0]},{frm[1]}>{dest[0]},{dest[1]}" for frm, dest in self._all_moves(s)]

    def apply_move(self, s: SuperHalmaState, move: str, rng=None) -> SuperHalmaState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        pl = board.pop(cells[0])
        board[cells[-1]] = pl                     # nothing removed -- pure relocation
        # progress metric: goal-distance dropped OR more of the mover's pieces
        # are now home in the target camp (the latter keeps the final fill,
        # where corner-distance plateaus, from false-drawing a real win).
        dist_before = _goal_distance(s.board, pl)
        dist_after = _goal_distance(board, pl)
        fill_before = _filled_count(s.board, pl)
        fill_after = _filled_count(board, pl)
        progressed = dist_after < dist_before or fill_after > fill_before
        no_progress = 0 if progressed else s.no_progress + 1
        # win (anti-spoiling squatter guard): the target camp is ENTIRELY
        # OCCUPIED (by any pieces) AND at least one occupant is the mover's OWN.
        target = _camp1() if pl == 0 else _camp0()
        full = all(sq in board for sq in target)
        mine_present = any(board.get(sq) == pl for sq in target)
        winner = pl if (full and mine_present) else None
        return SuperHalmaState(
            board=board, to_move=1 - pl, winner=winner,
            ply=s.ply + 1, no_progress=no_progress,
        )

    def is_terminal(self, s: SuperHalmaState) -> bool:
        return s.winner is not None or self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: SuperHalmaState) -> list[float]:
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if self._draw(s):
            return [0.0, 0.0]
        # no legal move (extremely unlikely in Super Halma): mover loses.
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: SuperHalmaState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "no_progress": s.no_progress,
        }

    def deserialize(self, d: dict) -> SuperHalmaState:
        return SuperHalmaState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
        )

    def describe_move(self, s: SuperHalmaState, move: str) -> str:
        (c0, r0), (c1, r1) = [_cell(x) for x in move.split(">")]
        # Every move is a single 2-cell hop: a step has Chebyshev length 1, a
        # jump lands 2+ away (possibly via a chain, collapsed to its endpoint).
        jump = max(abs(c1 - c0), abs(r1 - r0)) >= 2
        sep = "x" if jump else "-"
        return f"{c0},{r0}{sep}{c1},{r1}"

    def render(self, s: SuperHalmaState, perspective=None) -> dict:
        c0, c1 = camps()
        # tint each player's TARGET camp faintly so the goal is visible.
        tints = {}
        for sq in c1:           # player 0's goal
            tints[f"{sq[0]},{sq[1]}"] = "#ffdede"
        for sq in c0:           # player 1's goal
            tints[f"{sq[0]},{sq[1]}"] = "#dedeff"
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = "Draw (no-progress / ply cap)"
            else:
                caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
