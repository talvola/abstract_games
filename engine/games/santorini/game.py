"""Santorini — Gordon Hamilton's build-and-climb game (Roxley Games).

BASE GAME ONLY (no god powers). Two players, each with 2 Workers, on a 5x5
grid. Every space has a building LEVEL 0..4:
  0 = ground, 1/2/3 = building tiers, 4 = dome (impassable cap).
A space holds at most one Worker; a Worker may stand on a level-1/2/3 building
but never on a dome.

PHASES
------
1. PLACEMENT — the Start Player (player 0) places both of their Workers on
   unoccupied spaces first, then player 1 places both of theirs. A placement
   move is a single cell "c,r" (one click). Order of seats placing:
   0, 0, 1, 1.  (Roxley rulebook: the Start Player places first.)
2. PLAY — beginning with player 0. A turn = MOVE one of your Workers, then
   BUILD with that same Worker.
     MOVE: to one of the up-to-8 adjacent spaces that is unoccupied (no Worker,
           not a dome) and at most ONE level higher than the Worker's current
           space (step up 0 or 1 level; step DOWN any number of levels).
     BUILD: on one of the up-to-8 spaces adjacent to the Worker's NEW position
           that is unoccupied (no Worker) and not already a dome. Raises that
           space's level by 1 (a build on a level-3 space makes it a dome=4).
   Move encoding (play phase): the path "wfrom>wto>buildcell" (three "c,r"
   cells). A WINNING CLIMB (moving onto a level-3 building) is the 2-cell path
   "wfrom>wto" (no build cell): you win immediately, no build happens.

WIN
---
  * CLIMB win (primary): move a Worker up onto a level-3 building -> win now.
  * STUCK-opponent win: the player to move has no legal move (no Worker can
    move-and-build, and no winning climb) -> that player LOSES.

TERMINATION
-----------
Real games end via a climb / stuck win well before the board fills, but a
defensive hard ply cap (-> draw) is included as a non-original safeguard
against pathological loops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZE = 5
DOME = 4
NAMES = {0: "Red", 1: "Blue"}

DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

# Placement order: start player (0) places both Workers, then player 1.
PLACEMENT_ORDER = [0, 0, 1, 1]

PLY_CAP = 400  # defensive (non-original) safeguard -> draw


def _cell(sv: str):
    c, r = sv.split(",")
    return int(c), int(r)


def _s(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _alg(cell) -> str:
    # a1-style: column letter a..e, row number 1..5
    return f"{'abcde'[cell[0]]}{cell[1] + 1}"


def _in_bounds(c, r) -> bool:
    return 0 <= c < SIZE and 0 <= r < SIZE


@dataclass
class SState:
    # levels[(c,r)] = building level 0..4 (0..4); default 0
    levels: dict = field(default_factory=dict)
    # workers[(c,r)] = owner 0/1  (exactly one worker per occupied cell)
    workers: dict = field(default_factory=dict)
    to_move: int = 0
    placed: int = 0                  # how many Workers placed so far (0..4)
    winner: Optional[int] = None     # set on a climb win (win-as-event)
    draw: bool = False               # ply-cap safeguard
    ply: int = 0                     # full turns elapsed in the play phase

    def level(self, cell) -> int:
        return self.levels.get(cell, 0)


class Santorini(Game):
    uid = "santorini"
    name = "Santorini"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SState:
        return SState()

    # ---- phase helpers ----------------------------------------------------
    @staticmethod
    def _in_placement(s: SState) -> bool:
        return s.placed < len(PLACEMENT_ORDER)

    def current_player(self, s: SState) -> int:
        if self._in_placement(s):
            return PLACEMENT_ORDER[s.placed]
        return s.to_move

    # ---- move generation --------------------------------------------------
    def _placement_moves(self, s: SState) -> list[str]:
        out = []
        for r in range(SIZE):
            for c in range(SIZE):
                if (c, r) not in s.workers:
                    out.append(_s((c, r)))
        return out

    def _play_moves(self, s: SState) -> list[str]:
        """All move-then-build turns for the player to move, plus 2-cell
        winning climbs (moving onto a level-3 building)."""
        player = s.to_move
        out = []
        worker_cells = [cell for cell, owner in s.workers.items() if owner == player]
        for wfrom in worker_cells:
            fl = s.level(wfrom)
            for dc, dr in DIRS:
                wto = (wfrom[0] + dc, wfrom[1] + dr)
                if not _in_bounds(*wto):
                    continue
                if wto in s.workers:        # destination occupied by a worker
                    continue
                tl = s.level(wto)
                if tl == DOME:              # cannot stand on a dome
                    continue
                if tl - fl > 1:             # at most one level up
                    continue
                if tl == 3:
                    # CLIMB WIN: moving up onto a level-3 building. No build.
                    out.append(f"{_s(wfrom)}>{_s(wto)}")
                    continue
                # Normal move: now enumerate builds adjacent to wto.
                for bc, br in DIRS:
                    bcell = (wto[0] + bc, wto[1] + br)
                    if not _in_bounds(*bcell):
                        continue
                    if bcell == wfrom:
                        # wfrom is vacated by the move -> a legal build target.
                        pass
                    elif bcell in s.workers:
                        continue
                    if s.level(bcell) == DOME:
                        continue
                    out.append(f"{_s(wfrom)}>{_s(wto)}>{_s(bcell)}")
        return out

    def legal_moves(self, s: SState) -> list[str]:
        if self.is_terminal(s):
            return []
        if self._in_placement(s):
            return self._placement_moves(s)
        return self._play_moves(s)

    # ---- applying a move --------------------------------------------------
    def apply_move(self, s: SState, move: str, rng=None) -> SState:
        levels = dict(s.levels)
        workers = dict(s.workers)

        if self._in_placement(s):
            seat = PLACEMENT_ORDER[s.placed]
            cell = _cell(move)
            workers[cell] = seat
            placed = s.placed + 1
            # First play-phase mover is player 0.
            to_move = 0 if placed >= len(PLACEMENT_ORDER) else s.to_move
            return SState(levels=levels, workers=workers, to_move=to_move,
                          placed=placed, ply=0)

        player = s.to_move
        path = [_cell(x) for x in move.split(">")]
        wfrom, wto = path[0], path[1]
        # move the worker
        del workers[wfrom]
        workers[wto] = player

        winner = None
        if len(path) == 2:
            # winning climb (moved up onto a level-3 building); no build
            winner = player
        else:
            bcell = path[2]
            levels[bcell] = levels.get(bcell, 0) + 1

        ply = s.ply + 1
        draw = False
        if winner is None and ply >= PLY_CAP:
            draw = True

        return SState(levels=levels, workers=workers, to_move=1 - player,
                      placed=s.placed, winner=winner, draw=draw, ply=ply)

    def is_terminal(self, s: SState) -> bool:
        if s.winner is not None or s.draw:
            return True
        if self._in_placement(s):
            return False
        # the side to move with no legal move loses
        return not self._play_moves(s)

    def returns(self, s: SState) -> list[float]:
        if s.draw:
            return [0.0, 0.0]
        if s.winner is not None:
            w = s.winner
        else:
            # the side to move has no legal move -> it loses
            w = 1 - s.to_move
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    # ---- serialization ----------------------------------------------------
    def serialize(self, s: SState) -> dict:
        return {
            "levels": {_s(k): v for k, v in s.levels.items()},
            "workers": {_s(k): v for k, v in s.workers.items()},
            "to_move": s.to_move,
            "placed": s.placed,
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> SState:
        return SState(
            levels={_cell(k): int(v) for k, v in d["levels"].items()},
            workers={_cell(k): int(v) for k, v in d["workers"].items()},
            to_move=d["to_move"],
            placed=d["placed"],
            winner=d.get("winner"),
            draw=d.get("draw", False),
            ply=d.get("ply", 0),
        )

    # ---- move-log notation ------------------------------------------------
    def describe_move(self, s: SState, move: str) -> str:
        if self._in_placement(s):
            return f"place {_alg(_cell(move))}"
        path = [_cell(x) for x in move.split(">")]
        if len(path) == 2:
            return f"{_alg(path[0])}-{_alg(path[1])} WIN"
        return f"{_alg(path[0])}-{_alg(path[1])} ^{_alg(path[2])}"

    # ---- rendering --------------------------------------------------------
    def render(self, s: SState, perspective=None) -> dict:
        levels = {_s(k): v for k, v in s.levels.items() if v >= 1}
        pieces = [{"cell": _s(cell), "owner": owner}
                  for cell, owner in s.workers.items()]

        if s.winner is not None:
            cap = f"{NAMES[s.winner]} wins (climbed to level 3)"
        elif s.draw:
            cap = "Draw (ply cap)"
        elif self._in_placement(s):
            seat = PLACEMENT_ORDER[s.placed]
            # how many of THIS seat's placements remain
            remaining = sum(1 for x in PLACEMENT_ORDER[s.placed:] if x == seat)
            noun = "worker" if remaining == 1 else "workers"
            cap = f"{NAMES[seat]} to place a worker ({remaining} {noun} left)"
        elif self.is_terminal(s):
            cap = f"{NAMES[1 - s.to_move]} wins (opponent stuck)"
        else:
            cap = f"{NAMES[s.to_move]} to move (move a worker, then build)"

        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE,
                      "levels": levels},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
