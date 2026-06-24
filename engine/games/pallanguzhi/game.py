"""Pallanguzhi (Pallankuzhi) -- a traditional South Indian / Tamil two-row mancala.

This package implements the **standard single-round "cow / kashi" variant** that
is the most widely documented (mancala.fandom, pallanguzhiguide, imp-art, and the
core of Wikipedia's "Pallanguzhi"). See rules.md for exactly which ruleset was
chosen and why, and which documented alternatives were NOT implemented (the
148-counter / capture-at-six "pasu" multi-round game, and the optional "facing
pit" capture).

Board model for the platform: a 7-wide x 2-tall SQUARE board. Each cell is a pit
(kuzhi); its rendered LABEL is the seed (cowrie / counter) count. Player 0 =
bottom row (row 0, cols 0..6), Player 1 = top row (row 1, cols 0..6). Each player
owns the seven pits in their own row. Captured seeds live in per-player STORES
that are not board cells and are never sown into; they are shown in the caption.

84 seeds total, 6 in every pit at start.

Sowing is counterclockwise. A player lifts ALL seeds from one of their own
non-empty pits and drops them one per pit, crossing onto the opponent's row at
the end of their own row and wrapping around the whole loop.

Two capture mechanics (the signatures of this variant):

  * "Kashi" / cow (capture-at-four): the MOMENT a seed is dropped into a pit and
    that pit thereby reaches exactly FOUR seeds, the mover immediately captures
    all four (they leave the board into the mover's store). This applies to any
    pit reached during sowing, own or opponent.

  * The lap / relay + empty-pit ending: when the last seed of the current handful
    is dropped, look at the NEXT pit in the sowing loop:
      - if that next pit is NON-EMPTY, the mover scoops up all of its seeds and
        continues sowing (a new lap) -- the turn keeps going;
      - if that next pit is EMPTY, the turn ENDS. The mover captures all the
        seeds in the pit BEYOND the empty pit (the next-next pit). If that pit is
        also empty there is nothing to capture. (Two empty pits ahead therefore
        captures nothing, matching Wikipedia.)

A pit emptied to exactly four by the kashi rule mid-lap can still be the "next"
or "beyond" pit for the relay/empty-pit test using its post-capture (possibly 0)
count, exactly as the physical game plays out.

Round / game end: the round ends when the player to move has no non-empty pit on
their own row to sow from (they cannot move). All seeds still loose on the board
are then swept to the player on whose own row they sit, added to that player's
store, and the player with more seeds wins (equal is a draw). This is the
standard single-round scoring (most seeds wins). A hard ply cap is a belt-and-
braces anti-loop safety; with capture-at-four steadily removing seeds and every
lap forced to end at an empty next-pit, ordinary play terminates well before it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
# 14 pits, addressed "col,row" with col in 0..6, row in {0 (bottom), 1 (top)}.
#
# Counterclockwise sowing order (a fixed cycle of the 14 pits): player 0 sows
# left-to-right along its own bottom row (cols 0..6 at row 0), then crosses to
# the top row and continues right-to-left (cols 6..0 at row 1), then wraps back
# to the start. This is the standard physical pallanguzhi loop.
WIDTH = 7
PIT_ORDER = (
    (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0),  # bottom L->R
    (6, 1), (5, 1), (4, 1), (3, 1), (2, 1), (1, 1), (0, 1),  # top R->L
)
PIT_INDEX = {pit: i for i, pit in enumerate(PIT_ORDER)}
N_PITS = len(PIT_ORDER)  # 14

START_PER_PIT = 6
TOTAL_SEEDS = N_PITS * START_PER_PIT  # 84
CAPTURE_AT = 4                         # "kashi" / cow
PLY_CAP = 2000                         # hard anti-loop safety (rarely reached)

SIDE_NAME = {0: "Bottom", 1: "Top"}


def _owner(pit) -> int:
    return 0 if pit[1] == 0 else 1


OWN_PITS = {
    0: [p for p in PIT_ORDER if _owner(p) == 0],
    1: [p for p in PIT_ORDER if _owner(p) == 1],
}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class PState:
    # board[(col,row)] -> seed count (every pit present; 0 allowed).
    board: dict = field(default_factory=dict)
    stores: list = field(default_factory=lambda: [0, 0])  # captured seeds per player
    to_move: int = 0
    ply: int = 0
    done: bool = False


class Pallanguzhi(Game):
    uid = "pallanguzhi"
    name = "Pallanguzhi"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> PState:
        board = {pit: START_PER_PIT for pit in PIT_ORDER}
        return PState(board=board, stores=[0, 0], to_move=0, ply=0, done=False)

    def current_player(self, s: PState) -> int:
        return s.to_move

    # -- helpers ------------------------------------------------------------
    def _has_move(self, board, player) -> bool:
        return any(board[p] > 0 for p in OWN_PITS[player])

    def _swept_stores(self, board, stores):
        """Final-result stores after the end-of-round board sweep.

        Every seed still loose on the board is won by the player on whose own row
        it sits. Returns a new list; does not mutate inputs. Total is conserved.
        """
        out = list(stores)
        for player in (0, 1):
            for p in OWN_PITS[player]:
                out[player] += board[p]
        return out

    # -- core sowing / capture ---------------------------------------------
    def _sow(self, board, stores, player, start_pit):
        """Sow from `start_pit` for `player` through laps/relays + captures.

        Returns (new_board, new_stores). Does NOT mutate the inputs. Implements
        the capture-at-four "kashi" rule (immediate, on the seed that makes a pit
        four), the lap/relay continuation (last seed of a handful, next pit
        non-empty -> scoop it up and keep sowing), and the empty-pit ending
        (next pit empty -> turn ends, capture the pit beyond the empty one).
        """
        board = dict(board)
        stores = list(stores)

        idx = PIT_INDEX[start_pit]
        hand = board[start_pit]
        board[start_pit] = 0

        # A single sow is a sequence of laps. Each lap ends with an empty-next
        # test; if the next pit is non-empty we relay. With capture-at-four
        # steadily draining seeds and laps forced to stop at an empty next-pit
        # this always terminates, but bound the lap count defensively so a single
        # apply_move can never hang the conformance harness.
        max_laps = 100000
        while True:
            max_laps -= 1
            if max_laps <= 0:  # pragma: no cover - defensive, not normally hit
                break
            # Sow the current handful one seed per consecutive pit.
            last_idx = None
            for _ in range(hand):
                idx = (idx + 1) % N_PITS
                pit = PIT_ORDER[idx]
                board[pit] += 1
                # Kashi / cow: a pit brought to exactly four is captured at once.
                if board[pit] == CAPTURE_AT:
                    stores[player] += board[pit]
                    board[pit] = 0
                last_idx = idx

            # After dropping the last seed of this handful, inspect the NEXT pit.
            next_idx = (last_idx + 1) % N_PITS
            next_pit = PIT_ORDER[next_idx]
            if board[next_pit] > 0:
                # Relay/lap: scoop up the next pit and keep sowing.
                hand = board[next_pit]
                board[next_pit] = 0
                idx = next_idx
                continue
            else:
                # Next pit empty -> turn ends; capture the pit BEYOND the empty
                # pit (the next-next pit), if it holds any seeds.
                beyond_idx = (next_idx + 1) % N_PITS
                beyond_pit = PIT_ORDER[beyond_idx]
                if board[beyond_pit] > 0:
                    stores[player] += board[beyond_pit]
                    board[beyond_pit] = 0
                break

        return board, stores

    # -- legal moves --------------------------------------------------------
    def legal_moves(self, s: PState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in OWN_PITS[s.to_move] if s.board[(c, r)] > 0]

    # -- apply --------------------------------------------------------------
    def apply_move(self, s: PState, move: str, rng=None) -> PState:
        player = s.to_move
        start = _cell(move)
        board, stores = self._sow(s.board, s.stores, player, start)

        ply = s.ply + 1
        opp = 1 - player
        done = False

        # The round ends when the next player to move cannot sow (their own row
        # is empty). Loose seeds are swept at terminal (see returns / render).
        if not self._has_move(board, opp):
            done = True
        # Hard ply cap (anti-loop safety).
        if not done and ply >= PLY_CAP:
            done = True

        return PState(board=board, stores=stores, to_move=opp, ply=ply, done=done)

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s: PState) -> bool:
        return s.done

    def returns(self, s: PState) -> list[float]:
        a, b = self._swept_stores(s.board, s.stores)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s: PState) -> dict:
        return {
            "board": {f"{c},{r}": n for (c, r), n in s.board.items()},
            "stores": list(s.stores),
            "to_move": s.to_move,
            "ply": s.ply,
            "done": s.done,
        }

    def deserialize(self, d: dict) -> PState:
        return PState(
            board={_cell(k): v for k, v in d["board"].items()},
            stores=list(d["stores"]),
            to_move=d["to_move"],
            ply=d["ply"],
            done=d["done"],
        )

    # -- render -------------------------------------------------------------
    def render(self, s: PState, perspective=None) -> dict:
        pieces = []
        for (c, r), n in s.board.items():
            pieces.append({"cell": f"{c},{r}", "owner": 0 if r == 0 else 1,
                           "label": str(n)})

        caption = f"Bottom {s.stores[0]} — Top {s.stores[1]}"
        if s.done:
            a, b = self._swept_stores(s.board, s.stores)
            if a > b:
                caption += f"  ·  Bottom wins ({a}–{b})"
            elif b > a:
                caption += f"  ·  Top wins ({b}–{a})"
            else:
                caption += f"  ·  Draw ({a}–{b})"
        else:
            caption += f"  ·  {SIDE_NAME[s.to_move]} to move"

        return {
            "board": {"type": "square", "width": WIDTH, "height": 2},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }

    # -- nicer move log -----------------------------------------------------
    def describe_move(self, s: PState, move: str) -> str:
        c, r = _cell(move)
        side = SIDE_NAME[0 if r == 0 else 1]
        # Number pits 1..7 along each player's own sowing direction.
        num = (c + 1) if r == 0 else (WIDTH - c)
        return f"{side} pit {num} ({s.board.get((c, r), 0)} seeds)"
