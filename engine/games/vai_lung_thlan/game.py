"""Vai lung thlân -- a Mizo (Mizoram, NE India) two-row single-lap sowing game.

First described by Lt.-Col. J. Shakespear, *The Lushei Kuki Clans* (1912); a
modern write-up by Ralf Gering appeared in *Abstract Games* magazine, issue 12
(Winter 2002). This module implements the rules exactly as given there.

Board model for the platform: a 6-wide x 2-tall SQUARE board (two rows of six
holes). Each cell is a hole; its rendered LABEL is the stone count. Player 0 =
South (row 0, the bottom row), player 1 = North (row 1, the top row). Captured
stones live in per-player stores shown in the render caption (they are not board
cells and are never sown into).

Key differences from Oware (see rules.md for the full ruleset):

  * SINGLE LAP. A move is over after one lap -- you never re-lift from the hole
    where the last stone lands. (No relay loop.)
  * The sowing loop INCLUDES the emptied origin hole, so a 12-stone hole always
    lands its last stone back in its own (now empty) hole -> a capture.
  * Capture trigger: the last stone lands in a hole that was EMPTY (it now holds
    exactly 1). You capture that stone plus every immediately-preceding hole,
    walking BACKWARD along the sowing path, that holds exactly one stone -- an
    "unbroken chain of single stones". This can happen on EITHER row and the
    chain may cross rows; there is no owner restriction (you may even scoop up
    single stones in your own row). No grand-slam exception.
  * Captured stones are removed from the board entirely (placed in your store).
  * Most captured stones wins; a genuine 30-30 split is an honest DRAW.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
# 12 holes, addressed "col,row" with col in 0..5, row in {0 (South), 1 (North)}.
#
# Sowing loop (a fixed cycle of the 12 holes): the bottom (South) row is
# traversed right -> left (cols 5..0), then the loop crosses to the top (North)
# row and continues left -> right (cols 0..5), then wraps back to the start.
# This satisfies the rule that a player sows "first along his row and then back
# along that of his opponent" for BOTH seats, and it is the loop that
# reproduces the printed endgame problem's solution exactly (see selftest.py).
PIT_ORDER = (
    (5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0),   # South row, right -> left
    (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1),   # North row, left -> right
)
PIT_INDEX = {pit: i for i, pit in enumerate(PIT_ORDER)}
N_PITS = len(PIT_ORDER)


def _owner(pit):
    return 0 if pit[1] == 0 else 1


SOUTH_PITS = [p for p in PIT_ORDER if _owner(p) == 0]
NORTH_PITS = [p for p in PIT_ORDER if _owner(p) == 1]
OWN_PITS = {0: SOUTH_PITS, 1: NORTH_PITS}

SEEDS_PER_HOLE = 5
TOTAL_SEEDS = 60             # 12 holes x 5
DRAW_EACH = 30               # a 30-30 split is a draw
NO_PROGRESS_CAP = 150        # plies without a capture -> anti-loop terminal
PLY_CAP = 600                # hard ply cap (anti-loop backstop)

SIDE_NAME = {0: "South", 1: "North"}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


# Each player numbers their own holes 1..6 from their RIGHT to their LEFT
# (Gering's article convention). South (facing north) has hole 1 = east = col 5;
# North (facing south) has hole 1 = west = col 0.
def _hole_number(pit):
    c, r = pit
    return (6 - c) if r == 0 else (c + 1)


@dataclass
class VLTState:
    # board[(col,row)] -> stone count (every hole present; 0 allowed).
    board: dict = field(default_factory=dict)
    stores: list = field(default_factory=lambda: [0, 0])  # captured per player
    to_move: int = 0
    ply: int = 0
    no_progress: int = 0
    done: bool = False


class VaiLungThlan(Game):
    uid = "vai_lung_thlan"
    name = "Vai lung thlân"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> VLTState:
        board = {pit: SEEDS_PER_HOLE for pit in PIT_ORDER}
        return VLTState(board=board, stores=[0, 0], to_move=0,
                        ply=0, no_progress=0, done=False)

    def current_player(self, s: VLTState) -> int:
        return s.to_move

    # -- core sowing / capture ---------------------------------------------
    def _has_move(self, board, player) -> bool:
        return any(board[p] > 0 for p in OWN_PITS[player])

    def _sow_and_capture(self, board, start_pit):
        """Sow one lap from `start_pit`; return (new_board, captured).

        Single lap: all lifted stones are dropped one-by-one into the holes
        following the origin (the origin itself is refilled once the lap wraps
        all the way around, i.e. with >= 12 stones). Does NOT mutate `board`.
        """
        board = dict(board)
        stones = board[start_pit]
        board[start_pit] = 0

        idx = PIT_INDEX[start_pit]
        last_pit = start_pit
        for step in range(1, stones + 1):
            pit = PIT_ORDER[(idx + step) % N_PITS]
            board[pit] += 1
            last_pit = pit

        # Capture: the last stone must have landed in a previously-EMPTY hole,
        # i.e. that hole now holds exactly one stone. Then walk BACKWARD along
        # the sowing path collecting the unbroken chain of single-stone holes.
        captured = 0
        if board[last_pit] == 1:
            li = PIT_INDEX[last_pit]
            k = 0
            while True:
                pit = PIT_ORDER[(li - k) % N_PITS]
                if board[pit] == 1:
                    captured += 1
                    board[pit] = 0
                    k += 1
                else:
                    break

        return board, captured

    # -- legal moves --------------------------------------------------------
    def legal_moves(self, s: VLTState) -> list[str]:
        if s.done:
            return []
        # current_player is always a seat that has a move (apply_move skips a
        # seat with an empty row while the board still holds stones -- the
        # "passing is prohibited unless a player has no legal move" rule).
        return [f"{c},{r}" for (c, r) in OWN_PITS[s.to_move] if s.board[(c, r)] > 0]

    # -- apply --------------------------------------------------------------
    def apply_move(self, s: VLTState, move: str, rng=None) -> VLTState:
        player = s.to_move
        start = _cell(move)
        board, captured = self._sow_and_capture(s.board, start)
        stores = list(s.stores)
        stores[player] += captured

        ply = s.ply + 1
        no_progress = 0 if captured else s.no_progress + 1

        # Terminal when every stone has been captured (rules: "the game is
        # finished when no stones are left on the board"). Anti-loop backstops:
        # a long capture-less stretch, or the hard ply cap. On any of these the
        # result is decided purely by the stores actually captured (uncaptured
        # stones belong to no one -- never fabricate a winner).
        board_empty = not any(board.values())
        done = board_empty or no_progress >= NO_PROGRESS_CAP or ply >= PLY_CAP

        # Whose turn next: the opponent, unless the opponent's row is empty (and
        # the game isn't over) -- then that seat must pass and the mover
        # continues.
        opp = 1 - player
        if done:
            to_move = opp
        elif self._has_move(board, opp):
            to_move = opp
        else:
            to_move = player

        return VLTState(board=board, stores=stores, to_move=to_move,
                        ply=ply, no_progress=no_progress, done=done)

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s: VLTState) -> bool:
        return s.done

    def returns(self, s: VLTState) -> list[float]:
        a, b = s.stores
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s: VLTState) -> dict:
        return {
            "board": {f"{c},{r}": n for (c, r), n in s.board.items()},
            "stores": list(s.stores),
            "to_move": s.to_move,
            "ply": s.ply,
            "no_progress": s.no_progress,
            "done": s.done,
        }

    def deserialize(self, d: dict) -> VLTState:
        return VLTState(
            board={_cell(k): v for k, v in d["board"].items()},
            stores=list(d["stores"]),
            to_move=d["to_move"],
            ply=d["ply"],
            no_progress=d.get("no_progress", 0),
            done=d["done"],
        )

    # -- render -------------------------------------------------------------
    def render(self, s: VLTState, perspective=None) -> dict:
        pieces = []
        for (c, r), n in s.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": 0 if r == 0 else 1,
                "label": str(n),
            })
        caption = f"South {s.stores[0]} — North {s.stores[1]}"
        if s.done:
            a, b = s.stores
            if a > b:
                caption += "  ·  South wins"
            elif b > a:
                caption += "  ·  North wins"
            else:
                caption += "  ·  Draw"
        else:
            caption += f"  ·  {SIDE_NAME[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": 6, "height": 2},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }

    # -- nicer move log -----------------------------------------------------
    def describe_move(self, s: VLTState, move: str) -> str:
        pit = _cell(move)
        side = SIDE_NAME[_owner(pit)]
        n = s.board.get(pit, 0)
        return f"{side} {_hole_number(pit)} ({n} stones)"
