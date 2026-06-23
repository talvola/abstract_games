"""Toguz Kumalak (Toguz korgool) -- the Kazakh/Kyrgyz "nine pebbles" mancala.

Board model for the platform: a 9-wide x 2-tall SQUARE board. Each cell is a
pit ("otau"); its rendered LABEL is the ball count. Player 0 = bottom row
(row 0, cols 0..8), Player 1 = top row (row 1, cols 0..8). Captured balls live
in per-player KAZANS (stores) that are not board cells and are never sown into.

162 balls total, 9 in every pit at start. Sowing is counterclockwise:
 - from a pit holding exactly 1 ball: pick it up and drop it in the NEXT pit;
 - from a pit holding >1 ball: leave ONE ball behind in the source pit, then
   sow the remaining balls one per consecutive pit. (Equivalently: lift all
   the balls, and the FIRST one goes back into the just-emptied source pit --
   which is the way the rule is usually phrased.)

Capture: if the LAST sown ball lands in an OPPONENT pit whose resulting count is
EVEN, all balls in that pit go to the mover's kazan.

Tuzdik (the signature rule): if the last sown ball lands in an OPPONENT pit
bringing its count to exactly THREE, that pit becomes the mover's "tuzdik"
(a sacred hole), PROVIDED (a) the mover does not already have a tuzdik (max one
per player), (b) it is not the opponent's NINTH/last pit, and (c) it is not the
mirror-symmetric pit of the opponent's existing tuzdik. Once a tuzdik exists,
any ball that ever lands in it is immediately transferred to its owner's kazan
(and it never sows onward / is never chosen as a source).

Win: first player to accumulate MORE THAN 81 balls (>= 82) in their kazan wins.
When the game otherwise ends (a side has no sowable balls, or the ply cap), every
loose ball still on the board is swept to the player on whose own row it sits and
added to that player's kazan before the final comparison; more balls wins, equal
(81-81) is a draw.

See rules.md for the full as-implemented ruleset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
# 18 pits, addressed "col,row" with col in 0..8, row in {0 (bottom), 1 (top)}.
#
# Counterclockwise sowing order (a fixed cycle of the 18 pits): player 0 sows
# left-to-right along its own bottom row (cols 0..8 at row 0), then crosses to
# the top row and continues right-to-left (cols 8..0 at row 1), then wraps back
# to the start. This is the standard physical toguz kumalak loop.
WIDTH = 9
PIT_ORDER = (
    (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0),  # bottom L->R
    (8, 1), (7, 1), (6, 1), (5, 1), (4, 1), (3, 1), (2, 1), (1, 1), (0, 1),  # top R->L
)
PIT_INDEX = {pit: i for i, pit in enumerate(PIT_ORDER)}

START_PER_PIT = 9
TOTAL_BALLS = WIDTH * 2 * START_PER_PIT  # 162
WIN_THRESHOLD = 82           # > 81 captured balls is an outright win
HALF = TOTAL_BALLS // 2      # 81 (the draw line)
PLY_CAP = 2000               # hard ply cap -> sweep remaining balls (anti-loop)

SIDE_NAME = {0: "Bottom", 1: "Top"}


def _owner(pit) -> int:
    return 0 if pit[1] == 0 else 1


OWN_PITS = {
    0: [p for p in PIT_ORDER if _owner(p) == 0],
    1: [p for p in PIT_ORDER if _owner(p) == 1],
}

# The opponent's "ninth"/last pit (the one that can never become a tuzdik).
# In each player's own sowing direction the pits run 1..9. Player 0's pits go
# left->right cols 0..8, so its 9th pit is (8,0). Player 1's pits go right->left
# cols 8..0, so its 9th pit is (0,1).
LAST_PIT = {0: (8, 0), 1: (0, 1)}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _mirror(pit):
    """The mirror-symmetric pit on the other row at the SAME column.

    Two pits are "symmetric" when they sit at the same position counting from
    each player's own first pit. Player 0 pit (c,0) corresponds (1-indexed,
    along each side's own direction) to player 1 pit (c,1): both are the
    (c+1)-th pit of their respective owner. So the symmetric partner is the
    same column on the opposite row.
    """
    c, r = pit
    return (c, 1 - r)


@dataclass
class TKState:
    # board[(col,row)] -> ball count (every pit present; 0 allowed).
    board: dict = field(default_factory=dict)
    kazans: list = field(default_factory=lambda: [0, 0])  # captured balls per player
    # tuzdiks[player] = the pit that player owns as a tuzdik, or None.
    tuzdiks: list = field(default_factory=lambda: [None, None])
    to_move: int = 0
    ply: int = 0
    done: bool = False


class ToguzKumalak(Game):
    uid = "toguz_kumalak"
    name = "Toguz Kumalak"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> TKState:
        board = {pit: START_PER_PIT for pit in PIT_ORDER}
        return TKState(board=board, kazans=[0, 0], tuzdiks=[None, None],
                       to_move=0, ply=0, done=False)

    def current_player(self, s: TKState) -> int:
        return s.to_move

    # -- helpers ------------------------------------------------------------
    def _tuzdik_owner(self, tuzdiks, pit):
        """Return the player who owns `pit` as a tuzdik, or None."""
        for player in (0, 1):
            if tuzdiks[player] == pit:
                return player
        return None

    def _has_balls(self, board, player) -> bool:
        """Does `player` have any ball in a sowable pit (not a tuzdik)?"""
        return any(board[p] > 0 for p in OWN_PITS[player])

    def _swept_kazans(self, board, kazans, tuzdiks):
        """Final-result kazans after the end-game board sweep.

        When the game ends, every loose ball still on the board is won by the
        player on whose side (row) it sits: each player adds the balls remaining
        in THEIR OWN pit-row to their own kazan before the final comparison.
        Tuzdik holes never hold balls, so they contribute nothing. Returns a new
        list; does not mutate inputs. Total is conserved (kazans + board == 162).
        """
        out = list(kazans)
        for player in (0, 1):
            for p in OWN_PITS[player]:
                out[player] += board[p]
        return out

    def _candidate_pits(self, s: TKState, player):
        """Non-empty pits the player owns and may sow from (tuzdiks excluded)."""
        own_tuz = s.tuzdiks[player]
        opp_tuz = s.tuzdiks[1 - player]
        out = []
        for p in OWN_PITS[player]:
            if p == own_tuz or p == opp_tuz:
                continue
            if s.board[p] > 0:
                out.append(p)
        return out

    # -- core sowing / capture ---------------------------------------------
    def _sow(self, s: TKState, player, start_pit):
        """Sow from `start_pit` for `player`.

        Returns (new_board, new_kazans, new_tuzdiks). Does NOT mutate inputs.
        Handles the leave-one-behind rule, ball-into-tuzdik diversion, capture,
        and tuzdik creation.
        """
        board = dict(s.board)
        kazans = list(s.kazans)
        tuzdiks = list(s.tuzdiks)

        seeds = board[start_pit]
        idx = PIT_INDEX[start_pit]
        n = len(PIT_ORDER)

        if seeds == 1:
            # Single ball: pick it up and drop it in the next pit.
            board[start_pit] = 0
            to_place = [PIT_ORDER[(idx + 1) % n]]
        else:
            # >1: leave one behind; the remaining (seeds-1) balls go one per pit
            # starting at the source pit itself ("first stone into the emptied
            # hole"), then onward.
            board[start_pit] = 0
            to_place = [PIT_ORDER[(idx + k) % n] for k in range(seeds)]
            # to_place[0] == start_pit (the leave-one-behind ball), then onward.

        last_pit = None
        for pit in to_place:
            owner_tuz = self._tuzdik_owner(tuzdiks, pit)
            if owner_tuz is not None:
                # Any ball landing in a tuzdik is immediately banked to its
                # owner's kazan; the tuzdik never accumulates and never is the
                # "last pit" for capture/creation purposes.
                kazans[owner_tuz] += 1
            else:
                board[pit] = board[pit] + 1
            last_pit = pit

        # Capture / tuzdik creation are evaluated on the LAST sown ball, but
        # only if it landed in a non-tuzdik OPPONENT pit.
        opp = 1 - player
        if last_pit is not None and self._tuzdik_owner(tuzdiks, last_pit) is None \
                and _owner(last_pit) == opp:
            count = board[last_pit]
            if count == 3 and self._can_make_tuzdik(tuzdiks, player, last_pit):
                # Becomes the mover's tuzdik; its current 3 balls are banked.
                tuzdiks[player] = last_pit
                kazans[player] += board[last_pit]
                board[last_pit] = 0
            elif count % 2 == 0:
                # Even count -> capture all balls in the pit.
                kazans[player] += board[last_pit]
                board[last_pit] = 0

        return board, kazans, tuzdiks

    def _can_make_tuzdik(self, tuzdiks, player, pit) -> bool:
        """All three tuzdik restrictions."""
        # (a) at most one tuzdik per player
        if tuzdiks[player] is not None:
            return False
        # (b) cannot be the opponent's ninth/last pit
        opp = 1 - player
        if pit == LAST_PIT[opp]:
            return False
        # (c) cannot be symmetric to the opponent's existing tuzdik
        opp_tuz = tuzdiks[opp]
        if opp_tuz is not None and _mirror(opp_tuz) == pit:
            return False
        return True

    # -- legal moves --------------------------------------------------------
    def legal_moves(self, s: TKState) -> list[str]:
        if self.is_terminal(s):
            return []
        cands = self._candidate_pits(s, s.to_move)
        return [f"{c},{r}" for (c, r) in cands]

    # -- apply --------------------------------------------------------------
    def apply_move(self, s: TKState, move: str, rng=None) -> TKState:
        player = s.to_move
        start = _cell(move)
        board, kazans, tuzdiks = self._sow(s, player, start)

        ply = s.ply + 1
        opp = 1 - player
        done = False

        # Outright win by accumulating more than half (>= 82).
        if kazans[player] >= WIN_THRESHOLD or kazans[opp] >= WIN_THRESHOLD:
            done = True

        # If the player to move next (the opponent) has no sowable balls, the
        # game ends. At terminal the loose balls remaining on the board are swept
        # to the player on whose own row they sit (see returns / _swept_kazans);
        # this is the natural end when a side is emptied.
        if not done and not self._has_sowable(board, tuzdiks, opp):
            done = True

        # Hard ply cap (anti-loop safety): end the game.
        if not done and ply >= PLY_CAP:
            done = True

        return TKState(
            board=board,
            kazans=kazans,
            tuzdiks=tuzdiks,
            to_move=opp,
            ply=ply,
            done=done,
        )

    def _has_sowable(self, board, tuzdiks, player) -> bool:
        """Does `player` have a non-empty pit to sow from (excluding tuzdiks)?"""
        own_tuz = tuzdiks[player]
        opp_tuz = tuzdiks[1 - player]
        for p in OWN_PITS[player]:
            if p == own_tuz or p == opp_tuz:
                continue
            if board[p] > 0:
                return True
        return False

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s: TKState) -> bool:
        return s.done

    def returns(self, s: TKState) -> list[float]:
        a, b = self._swept_kazans(s.board, s.kazans, s.tuzdiks)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s: TKState) -> dict:
        return {
            "board": {f"{c},{r}": n for (c, r), n in s.board.items()},
            "kazans": list(s.kazans),
            "tuzdiks": [None if t is None else f"{t[0]},{t[1]}" for t in s.tuzdiks],
            "to_move": s.to_move,
            "ply": s.ply,
            "done": s.done,
        }

    def deserialize(self, d: dict) -> TKState:
        return TKState(
            board={_cell(k): v for k, v in d["board"].items()},
            kazans=list(d["kazans"]),
            tuzdiks=[None if t is None else _cell(t) for t in d["tuzdiks"]],
            to_move=d["to_move"],
            ply=d["ply"],
            done=d["done"],
        )

    # -- render -------------------------------------------------------------
    def render(self, s: TKState, perspective=None) -> dict:
        pieces = []
        tints = {}
        for (c, r), n in s.board.items():
            cell = f"{c},{r}"
            owner_tuz = self._tuzdik_owner(s.tuzdiks, (c, r))
            piece = {"cell": cell, "owner": 0 if r == 0 else 1, "label": str(n)}
            if owner_tuz is not None:
                # Mark a tuzdik visibly: a star glyph + a tint in the owner's hue.
                piece["label"] = "*"
                tints[cell] = "#d4a017" if owner_tuz == 0 else "#7a3fb0"
            pieces.append(piece)

        caption = f"Bottom {s.kazans[0]} — Top {s.kazans[1]}"
        if s.done:
            # At terminal the loose balls are swept to their own side; decide the
            # winner from the swept totals (not the raw kazans).
            a, b = self._swept_kazans(s.board, s.kazans, s.tuzdiks)
            if a > b:
                caption += f"  ·  Bottom wins ({a}–{b})"
            elif b > a:
                caption += f"  ·  Top wins ({b}–{a})"
            else:
                caption += "  ·  Draw"
        else:
            caption += f"  ·  {SIDE_NAME[s.to_move]} to move"

        spec = {
            "board": {"type": "square", "width": WIDTH, "height": 2},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
        if tints:
            spec["board"]["tints"] = tints
        return spec

    # -- nicer move log -----------------------------------------------------
    def describe_move(self, s: TKState, move: str) -> str:
        c, r = _cell(move)
        side = SIDE_NAME[0 if r == 0 else 1]
        # Number pits 1..9 along each player's own sowing direction.
        num = (c + 1) if r == 0 else (WIDTH - c)
        return f"{side} pit {num} ({s.board.get((c, r), 0)} balls)"
