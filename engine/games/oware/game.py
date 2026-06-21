"""Oware (Awari / Awalé) -- the canonical two-rank Mancala game.

Board model for the platform: a 6-wide x 2-tall SQUARE board. Each cell is a
pit; its rendered LABEL is the seed count. Player 0 = South (row 0, cols 0..5),
Player 1 = North (row 1, cols 0..5). Captured seeds live in per-player stores
that are shown in the render caption (they are not board cells and are never
sown into).

See rules.md for the full, as-implemented ruleset (Oware has many regional
variants; the choices made here are documented there).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
# 12 pits, addressed "col,row" with col in 0..5, row in {0 (South), 1 (North)}.
#
# Counterclockwise sowing order (a fixed cycle of the 12 pits): South sows
# left-to-right along its own row (cols 0..5 at row 0), then crosses to North's
# row and continues right-to-left (cols 5..0 at row 1), then wraps back to the
# start. This is the standard physical Oware loop.
PIT_ORDER = (
    (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0),   # South row, left -> right
    (5, 1), (4, 1), (3, 1), (2, 1), (1, 1), (0, 1),   # North row, right -> left
)
PIT_INDEX = {pit: i for i, pit in enumerate(PIT_ORDER)}

# Which player owns each pit (by its row).
def _owner(pit):
    return 0 if pit[1] == 0 else 1


SOUTH_PITS = [p for p in PIT_ORDER if _owner(p) == 0]
NORTH_PITS = [p for p in PIT_ORDER if _owner(p) == 1]
OWN_PITS = {0: SOUTH_PITS, 1: NORTH_PITS}

TOTAL_SEEDS = 48
WIN_THRESHOLD = 25            # >= 25 captured seeds is an outright win
PLY_CAP = 400                 # hard ply cap -> sweep remaining seeds (anti-loop)

SIDE_NAME = {0: "South", 1: "North"}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class OwareState:
    # board[(col,row)] -> seed count (every pit present; 0 allowed).
    board: dict = field(default_factory=dict)
    stores: list = field(default_factory=lambda: [0, 0])  # captured seeds per player
    to_move: int = 0
    ply: int = 0
    done: bool = False


class Oware(Game):
    uid = "oware"
    name = "Oware"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> OwareState:
        board = {pit: 4 for pit in PIT_ORDER}
        return OwareState(board=board, stores=[0, 0], to_move=0, ply=0, done=False)

    def current_player(self, s: OwareState) -> int:
        return s.to_move

    # -- core sowing / capture (pure helpers operating on plain dicts) ------
    def _has_seeds(self, board, player) -> bool:
        return any(board[p] > 0 for p in OWN_PITS[player])

    def _sow_and_capture(self, board, player, start_pit):
        """Sow from `start_pit` for `player`; return (new_board, captured).

        Applies the grand-slam rule (a move that would capture ALL of the
        opponent's seeds captures nothing). Does NOT mutate `board`.
        """
        board = dict(board)
        seeds = board[start_pit]
        board[start_pit] = 0

        idx = PIT_INDEX[start_pit]
        n = len(PIT_ORDER)
        last_pit = start_pit
        placed = 0
        step = 0
        while placed < seeds:
            step += 1
            pit = PIT_ORDER[(idx + step) % n]
            if pit == start_pit:
                # 12+ seed lap: skip the originating pit.
                continue
            board[pit] = board[pit] + 1
            last_pit = pit
            placed += 1

        # Capture: last seed must land in an OPPONENT pit now holding 2 or 3.
        opp = 1 - player
        captured = 0
        capture_pits = []
        if _owner(last_pit) == opp and board[last_pit] in (2, 3):
            order_idx = PIT_INDEX[last_pit]
            k = 0
            while True:
                pit = PIT_ORDER[(order_idx - k) % len(PIT_ORDER)]
                if _owner(pit) != opp:
                    break
                if board[pit] in (2, 3):
                    capture_pits.append(pit)
                    captured += board[pit]
                    k += 1
                else:
                    break

        # Grand-slam: a move that would capture every opponent seed captures
        # nothing (the "Awari" convention). Detect by checking if the opponent
        # would have zero seeds left after the capture.
        opp_total_after = sum(board[p] for p in OWN_PITS[opp])
        if captured > 0 and captured == opp_total_after:
            captured = 0
            capture_pits = []

        for pit in capture_pits:
            board[pit] = 0

        return board, captured

    # -- legal moves --------------------------------------------------------
    def _candidate_pits(self, board, player):
        """Non-empty pits the player owns (raw candidates, before feeding rule)."""
        return [p for p in OWN_PITS[player] if board[p] > 0]

    def legal_moves(self, s: OwareState) -> list[str]:
        if self.is_terminal(s):
            return []
        player = s.to_move
        board = s.board
        cands = self._candidate_pits(board, player)
        opp = 1 - player

        # Starvation / feeding rule: if the opponent has no seeds, the mover
        # MUST choose a move that feeds the opponent (lands a seed on the
        # opponent's row) if any such move exists.
        if not self._has_seeds(board, opp):
            feeding = []
            for pit in cands:
                nb, _ = self._sow_and_capture(board, player, pit)
                if self._has_seeds(nb, opp):
                    feeding.append(pit)
            if feeding:
                cands = feeding
            # else: no feeding move exists -> all candidate moves are legal,
            # and the game will end after this turn (handled in apply_move).

        return [f"{c},{r}" for (c, r) in cands]

    # -- apply --------------------------------------------------------------
    def apply_move(self, s: OwareState, move: str, rng=None) -> OwareState:
        player = s.to_move
        start = _cell(move)
        board, captured = self._sow_and_capture(s.board, player, start)
        stores = list(s.stores)
        stores[player] += captured

        ply = s.ply + 1
        opp = 1 - player
        done = False

        # Outright win by majority.
        if stores[player] >= WIN_THRESHOLD:
            done = True

        # If the opponent now has no seeds, the game ends: a player who cannot
        # move (empty side) on their turn triggers the end, and each player
        # sweeps the seeds remaining on their own side into their store. (The
        # feeding obligation in legal_moves means this only happens when the
        # opponent genuinely could not be fed.)
        if not done and not self._has_seeds(board, opp):
            board, stores = self._sweep(board, stores)
            done = True

        # Hard ply cap (anti-loop): sweep remaining seeds to owners.
        if not done and ply >= PLY_CAP:
            board, stores = self._sweep(board, stores)
            done = True

        return OwareState(
            board=board,
            stores=stores,
            to_move=opp,
            ply=ply,
            done=done,
        )

    @staticmethod
    def _sweep(board, stores):
        """Each player collects all remaining seeds on their own side."""
        board = dict(board)
        stores = list(stores)
        for player in (0, 1):
            for pit in OWN_PITS[player]:
                stores[player] += board[pit]
                board[pit] = 0
        return board, stores

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s: OwareState) -> bool:
        return s.done

    def returns(self, s: OwareState) -> list[float]:
        a, b = s.stores
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s: OwareState) -> dict:
        return {
            "board": {f"{c},{r}": n for (c, r), n in s.board.items()},
            "stores": list(s.stores),
            "to_move": s.to_move,
            "ply": s.ply,
            "done": s.done,
        }

    def deserialize(self, d: dict) -> OwareState:
        return OwareState(
            board={_cell(k): v for k, v in d["board"].items()},
            stores=list(d["stores"]),
            to_move=d["to_move"],
            ply=d["ply"],
            done=d["done"],
        )

    # -- render -------------------------------------------------------------
    def render(self, s: OwareState, perspective=None) -> dict:
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
    def describe_move(self, s: OwareState, move: str) -> str:
        c, r = _cell(move)
        side = SIDE_NAME[0 if r == 0 else 1]
        # Label pits a-f along each player's own sowing direction for readability.
        if r == 0:
            letter = "abcdef"[c]
        else:
            letter = "abcdef"[c]
        return f"{side} {letter} ({s.board.get((c, r), 0)} seeds)"
