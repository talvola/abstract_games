"""Halma -- George Howard Monks' 1883 jump-race game (the ancestor of Chinese
Checkers).

The board is a square grid (8x8 or 16x16, a manifest option). Each player's
pieces begin packed into a triangular CAMP in one corner; player 0 sits in the
top-left corner (around (0,0)) and player 1 in the diagonally opposite
bottom-right corner. Nothing is ever captured -- pieces are never removed.

On your turn you make ONE of:
  (A) STEP -- move a piece to any of the 8 adjacent (orthogonal/diagonal) EMPTY
      squares.
  (B) JUMP -- hop over exactly one adjacent occupied square (friend OR foe) in
      any of the 8 directions, landing on the EMPTY square immediately beyond.
      From the landing square you MAY continue jumping (each subsequent hop may
      be in a different direction); the whole chain is ONE move and you may stop
      after any hop.

Moves are the platform's clickable cell-path notation: a single step is
"a>b"; a jump chain is "a>b>c>..." listing every square the piece lands on.

WIN (anti-spoiling): you win when the OPPONENT's starting camp (your target) is
ENTIRELY OCCUPIED -- by any pieces -- AND at least one of those occupants is
your OWN. An enemy "squatter" parked in your target camp therefore just fills a
slot; it cannot deny your win. You still must actually deliver at least one of
your own pieces into the camp.

NO LEAVING THE TARGET CAMP: once one of your pieces has reached the opposing
(target) camp, it may not leave it again -- it may still move WITHIN the camp.

Termination: see the module-level cap notes and rules.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

NAMES = {0: "Player 1", 1: "Player 2"}

# 8 directions (king moves).
DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

# No-progress draw rule: plies since the last STEP or since a JUMP that changed
# the "distance-to-goal" picture. We use a simple, robust definition: a ply is
# "progress" if it is a jump-chain of length >= 2 cells OR a step that is not a
# pure shuffle; to keep it simple and guaranteed-terminating we just cap the
# total number of plies and also a no-progress counter on the sum-of-distances.
PLY_CAP = 400          # hard cap -> draw (both 8x8 and 16x16 finish well under this in real play)
NO_PROGRESS_CAP = 60   # plies without the moving player's total goal-distance strictly decreasing


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class HalmaState:
    size: int = 8
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0
    no_progress: int = 0


# ---- camp geometry ---------------------------------------------------------

def _camp_rows(size: int):
    """Per-row column counts of the corner camp at (0,0), top-left.

    8x8  (10 pieces): rows 0..3 -> 4,3,2,1.
    16x16 (19 pieces): rows 0..4 -> 5,5,4,3,2.
    """
    if size == 8:
        return [4, 3, 2, 1]
    return [5, 5, 4, 3, 2]


def _camp0(size: int):
    """Player 0's camp: the triangle anchored at the top-left corner (0,0)."""
    cells = set()
    for r, cnt in enumerate(_camp_rows(size)):
        for c in range(cnt):
            cells.add((c, r))
    return cells


def _camp1(size: int):
    """Player 1's camp: the 180-degree rotation into the bottom-right corner."""
    return {(size - 1 - c, size - 1 - r) for (c, r) in _camp0(size)}


def camps(size: int):
    return _camp0(size), _camp1(size)


def _start_board(size: int) -> dict:
    c0, c1 = camps(size)
    b = {}
    for sq in c0:
        b[sq] = 0
    for sq in c1:
        b[sq] = 1
    return b


def _goal_corner(player: int, size: int):
    """The single corner cell of the player's TARGET camp -- used as the
    reference point for the goal-distance no-progress metric."""
    # player 0 targets camp1 (bottom-right corner (size-1,size-1));
    # player 1 targets camp0 (top-left corner (0,0)).
    return (size - 1, size - 1) if player == 0 else (0, 0)


def _goal_distance(board: dict, player: int, size: int) -> int:
    """Sum of Chebyshev distances of `player`'s pieces to their target corner.
    A move that lowers this is unambiguous forward progress."""
    gc, gr = _goal_corner(player, size)
    tot = 0
    for (c, r), pl in board.items():
        if pl == player:
            tot += max(abs(c - gc), abs(r - gr))
    return tot


def _filled_count(board: dict, player: int, size: int) -> int:
    """How many of `player`'s OWN pieces already sit in its target camp.
    During the final fill the corner-distance can plateau while this still
    rises, so progress = (goal-distance drops) OR (this count rises)."""
    target = _camp1(size) if player == 0 else _camp0(size)
    return sum(1 for sq in target if board.get(sq) == player)


class Halma(Game):
    uid = "halma"
    name = "Halma"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HalmaState:
        size = 8
        if options:
            size = int(options.get("size", 8))
        if size not in (8, 16):
            size = 8
        return HalmaState(size=size, board=_start_board(size), to_move=0)

    def current_player(self, s: HalmaState) -> int:
        return s.to_move

    # ---- "no leaving the target camp" predicate ---------------------------
    def _move_allowed(self, s: HalmaState, frm, dest) -> bool:
        """Canonical "no leaving the opposing camp" rule (documented in
        rules.md):

        Once a piece has reached the OPPOSING (target) camp -- the camp the
        mover is racing to fill -- it may no longer leave it; it may only move
        to cells that are themselves in the target camp (i.e. it may still move
        WITHIN the camp). A piece NOT currently in the target camp is
        unrestricted.
        """
        target_camp = _camp1(s.size) if s.to_move == 0 else _camp0(s.size)
        if frm in target_camp and dest not in target_camp:
            return False
        return True

    # ---- move generation ---------------------------------------------------
    def _steps(self, s: HalmaState, frm):
        c, r = frm
        out = []
        for dc, dr in DIRS:
            t = (c + dc, r + dr)
            if 0 <= t[0] < s.size and 0 <= t[1] < s.size and t not in s.board:
                if self._move_allowed(s, frm, t):
                    out.append([frm, t])
        return out

    def _jump_paths(self, s: HalmaState, frm):
        """All jump chains from `frm`. The piece is treated as vacated from its
        start. You may stop after any hop, so every intermediate landing that is
        a legal stop is its own path. Visited-landing tracking prevents an
        infinite shuttle within one chain."""
        size = s.size
        occ = s.board
        paths = []

        # Treat the moving piece's start square as vacated for the whole chain
        # (it can neither be landed on nor jumped over as if still present).
        def occupied(sq):
            if sq == frm:
                return False
            return sq in occ

        def recurse(path, visited):
            here = path[-1]
            c, r = here
            for dc, dr in DIRS:
                over = (c + dc, r + dr)
                land = (c + 2 * dc, r + 2 * dr)
                if not (0 <= land[0] < size and 0 <= land[1] < size):
                    continue
                if not occupied(over):
                    continue
                if occupied(land) or land in visited:
                    continue
                # the "no leaving the target camp" rule: if the piece starts in
                # the target camp it must remain inside it for the WHOLE chain --
                # it may neither stop nor pass through a cell outside the camp.
                if not self._move_allowed(s, frm, land):
                    continue
                newpath = path + [land]
                paths.append(newpath)
                recurse(newpath, visited | {land})

        recurse([frm], {frm})
        return paths

    def _all_moves(self, s: HalmaState) -> list[list]:
        out = []
        for (c, r), pl in s.board.items():
            if pl != s.to_move:
                continue
            out.extend(self._steps(s, (c, r)))
            out.extend(self._jump_paths(s, (c, r)))
        return out

    def _draw(self, s: HalmaState) -> bool:
        return s.ply >= PLY_CAP or s.no_progress >= NO_PROGRESS_CAP

    def legal_moves(self, s: HalmaState) -> list[str]:
        if s.winner is not None or self._draw(s):
            return []
        moves = [">".join(f"{c},{r}" for c, r in path) for path in self._all_moves(s)]
        return moves

    def apply_move(self, s: HalmaState, move: str, rng=None) -> HalmaState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        pl = board.pop(cells[0])
        board[cells[-1]] = pl                     # nothing removed -- pure relocation
        # progress metric: goal-distance dropped OR more of the mover's pieces
        # are now home in the target camp (the latter keeps the final fill,
        # where corner-distance plateaus, from false-drawing a real win).
        dist_before = _goal_distance(s.board, pl, s.size)
        dist_after = _goal_distance(board, pl, s.size)
        fill_before = _filled_count(s.board, pl, s.size)
        fill_after = _filled_count(board, pl, s.size)
        progressed = dist_after < dist_before or fill_after > fill_before
        no_progress = 0 if progressed else s.no_progress + 1
        # win (anti-spoiling): the target camp is ENTIRELY OCCUPIED (by any
        # pieces) AND at least one occupant is the mover's OWN. An enemy squatter
        # just fills a slot and cannot deny the win.
        target = _camp1(s.size) if pl == 0 else _camp0(s.size)
        full = all(sq in board for sq in target)
        mine_present = any(board.get(sq) == pl for sq in target)
        winner = pl if (full and mine_present) else None
        return HalmaState(
            size=s.size, board=board, to_move=1 - pl, winner=winner,
            ply=s.ply + 1, no_progress=no_progress,
        )

    def is_terminal(self, s: HalmaState) -> bool:
        return s.winner is not None or self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: HalmaState) -> list[float]:
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if self._draw(s):
            return [0.0, 0.0]
        # no legal move (extremely unlikely in Halma): the player to move loses
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: HalmaState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "no_progress": s.no_progress,
        }

    def deserialize(self, d: dict) -> HalmaState:
        return HalmaState(
            size=d.get("size", 8),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
        )

    def describe_move(self, s: HalmaState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        jump = len(cells) > 2 or (len(cells) == 2 and max(abs(cells[1][0] - cells[0][0]),
                                                          abs(cells[1][1] - cells[0][1])) == 2)
        sep = "-" if not jump else "x"
        return sep.join(f"{c},{r}" for c, r in cells)

    def render(self, s: HalmaState, perspective=None) -> dict:
        c0, c1 = camps(s.size)
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
            "board": {"type": "square", "width": s.size, "height": s.size, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
