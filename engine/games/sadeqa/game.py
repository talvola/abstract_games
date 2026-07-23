"""Sadéqa -- a two-row multi-lap Ethiopian mancala (Selus sub-family).

Played by the Jimma of western Ethiopia; recorded by Pankhurst as "Sadeqa V"
(Game 84) and written up by Ralf Gering in *Abstract Games* magazine, issue 16
(Winter 2003). Sadéqa belongs to the *Selus* class and is described there as
"almost identical to Sulus Nishtaw, except that it is played on a two-row board
with 20 holes and four seeds in each hole initially." This module implements the
rules exactly as printed in that article (the Sadéqa-specific block first, then
Sulus Nishtaw, then the shared "Basic Rules").

Board model for the platform: a 10-wide x 2-tall SQUARE board (two rows of ten
holes). Player 0 = South (row 0, bottom), player 1 = North (row 1, top). Each
player owns his own row. Captured seeds are tallied per player (no store pits).
A *warana* ("speared"; the same thing the article's shared rules call a *wegue*,
"wound") is a marked hole owned by whoever created it; it retains its seeds and
those seeds score for its owner at the end of the game.

Key rules (see rules.md for the full one-page write-up and every interpretation):

  * MULTI-LAP counter-clockwise sowing. Lift a hole's whole contents and drop one
    seed per hole around a fixed 20-hole ring; if the last seed lands in an
    occupied non-warana hole you re-lift that hole and sow another lap ("relay").
  * A move (lap chain) ENDS when the last seed lands in:
      - an EMPTY hole ("kwah") -> nothing captured;
      - an OPPONENT's hole holding exactly 3 (now 4) -> a new warana owned by the
        mover is created on the opponent's side; nothing captured;
      - a WARANA. If it is owned by the OPPONENT: capture the dropped seed plus one
        more from that warana (only the 1 dropped seed if the warana was empty),
        then make a BONUS move (start again from any own non-warana hole). If it
        is owned by the MOVER: nothing captured, the move ends.
  * A warana can ONLY be made on the OPPONENT's side. If the last seed makes a hole
    on the MOVER's OWN side reach 4, that is NOT a warana -- all four seeds are
    re-lifted and sown in a new lap (relay continues). (Inherited from Sulus
    Nishtaw.)
  * First-move exception (shared Basic Rules): on the very first move of the game a
    hole reaching four seeds never creates a warana -- it relays instead.
  * Passing is illegal while a legal move exists; a player with no legal move is
    skipped. The game ends when NEITHER player has a legal move (all remaining
    seeds are locked in warana / empty holes).
  * Score = captured seeds + seeds sitting in warana you own. Most points wins; an
    equal split is an honest DRAW.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# ---------------------------------------------------------------------------
# Geometry -- 20 holes addressed "col,row", col 0..9, row 0 (South) / 1 (North).
# ---------------------------------------------------------------------------
WIDTH = 10
SOUTH, NORTH = 0, 1

SOUTH_PITS = [(c, 0) for c in range(WIDTH)]
NORTH_PITS = [(c, 1) for c in range(WIDTH)]
OWN_PITS = {SOUTH: SOUTH_PITS, NORTH: NORTH_PITS}

# One physical COUNTER-CLOCKWISE ring, pinned from the article's notation figure
# (South numbered 1..10 left->right, North numbered 10..1 left->right):
#   South row left->right (holes 1..10), up the right edge, North row right->left
#   (holes 1..10), down the left edge, back to South hole 1.
PIT_ORDER = SOUTH_PITS + [(c, 1) for c in range(WIDTH - 1, -1, -1)]
PIT_INDEX = {p: i for i, p in enumerate(PIT_ORDER)}
N_PITS = len(PIT_ORDER)                 # 20

SEEDS_PER_HOLE = 4
TOTAL_SEEDS = WIDTH * 2 * SEEDS_PER_HOLE  # 80

# Anti-loop backstops (real games converge as warana lock seeds out of play).
LAP_CAP = 5000            # max laps inside ONE move -- guards apply_move
NO_PROGRESS_CAP = 400     # moves with no capture AND no new warana -> terminal
PLY_CAP = 4000            # hard ply cap -> terminal

SIDE_NAME = {SOUTH: "South", NORTH: "North"}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _owner(pit):
    """The player whose ROW this hole sits in (physical side)."""
    return pit[1]


def _hole_number(pit):
    """Article numbering: South 1..10 left->right, North 10..1 left->right."""
    c, r = pit
    return (c + 1) if r == SOUTH else (WIDTH - c)


@dataclass
class SadeqaState:
    board: dict = field(default_factory=dict)     # pit -> seed count (all pits)
    warana: dict = field(default_factory=dict)    # pit -> owner (only warana holes)
    captured: list = field(default_factory=lambda: [0, 0])
    to_move: int = SOUTH
    ply: int = 0
    no_progress: int = 0
    done: bool = False


class Sadeqa(Game):
    uid = "sadeqa"
    name = "Sadéqa"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> SadeqaState:
        board = {p: SEEDS_PER_HOLE for p in PIT_ORDER}
        return SadeqaState(board=board, warana={}, captured=[0, 0],
                           to_move=SOUTH, ply=0, no_progress=0, done=False)

    def current_player(self, s: SadeqaState) -> int:
        return s.to_move

    # -- helpers ------------------------------------------------------------
    def _has_move(self, board, warana, player) -> bool:
        return any(board[p] > 0 and p not in warana for p in OWN_PITS[player])

    def _resolve(self, board, warana, mover, start_pit, first_move):
        """Play the full multi-lap move from `start_pit`. Pure (copies inputs).

        Returns (board, warana, captured, bonus, made_warana).
        """
        board = dict(board)
        warana = dict(warana)
        lap_start = start_pit
        captured = 0
        bonus = False
        made_warana = False

        for _ in range(LAP_CAP):
            stones = board[lap_start]
            board[lap_start] = 0
            idx = PIT_INDEX[lap_start]
            last_pit = lap_start
            last_before = 0
            for step in range(1, stones + 1):
                pit = PIT_ORDER[(idx + step) % N_PITS]
                last_before = board[pit]
                board[pit] += 1
                last_pit = pit

            # -- classify where the last seed landed --
            if last_pit in warana:
                if warana[last_pit] != mover:
                    # capture from opponent's warana (+ bonus move)
                    if last_before == 0:
                        captured += 1
                        board[last_pit] -= 1
                    else:
                        captured += 2
                        board[last_pit] -= 2
                    bonus = True
                # own warana -> nothing captured; either way the move ends
                break

            if last_before == 0:
                # kwah: last seed dropped into an empty hole -> move ends
                break

            if (not first_move and _owner(last_pit) != mover
                    and last_before == 3):
                # opponent hole of three -> a new warana owned by the mover
                warana[last_pit] = mover
                made_warana = True
                break

            # otherwise: occupied non-warana hole -> relay (lift & sow again).
            # This covers the mover's OWN hole reaching four (never a warana),
            # opponent holes not holding exactly three, and the first-move case.
            lap_start = last_pit

        return board, warana, captured, bonus, made_warana

    # -- legal moves --------------------------------------------------------
    def legal_moves(self, s: SadeqaState) -> list[str]:
        if s.done:
            return []
        return [f"{c},{r}" for (c, r) in OWN_PITS[s.to_move]
                if s.board[(c, r)] > 0 and (c, r) not in s.warana]

    # -- apply --------------------------------------------------------------
    def apply_move(self, s: SadeqaState, move: str, rng=None) -> SadeqaState:
        player = s.to_move
        start = _cell(move)
        first_move = (s.ply == 0)
        board, warana, captured, bonus, made_warana = self._resolve(
            s.board, s.warana, player, start, first_move)

        cap = list(s.captured)
        cap[player] += captured
        ply = s.ply + 1
        progress = captured > 0 or made_warana
        no_progress = 0 if progress else s.no_progress + 1

        opp = 1 - player
        mover_has = self._has_move(board, warana, player)
        opp_has = self._has_move(board, warana, opp)

        done = ((not mover_has and not opp_has)
                or no_progress >= NO_PROGRESS_CAP
                or ply >= PLY_CAP)

        if done:
            to_move = opp
        elif bonus:
            # the mover is entitled to a bonus move; skip him only if he now has
            # none (then the opponent plays; both-empty is already `done`).
            to_move = player if mover_has else opp
        else:
            # normal end of move -> opponent, unless the opponent must pass.
            to_move = opp if opp_has else player

        return SadeqaState(board=board, warana=warana, captured=cap,
                           to_move=to_move, ply=ply, no_progress=no_progress,
                           done=done)

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s: SadeqaState) -> bool:
        return s.done

    def scores(self, s: SadeqaState) -> list:
        pts = list(s.captured)
        for pit, owner in s.warana.items():
            pts[owner] += s.board[pit]
        return pts

    def returns(self, s: SadeqaState) -> list:
        a, b = self.scores(s)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s: SadeqaState) -> dict:
        return {
            "board": {f"{c},{r}": n for (c, r), n in s.board.items()},
            "warana": {f"{c},{r}": o for (c, r), o in s.warana.items()},
            "captured": list(s.captured),
            "to_move": s.to_move,
            "ply": s.ply,
            "no_progress": s.no_progress,
            "done": s.done,
        }

    def deserialize(self, d: dict) -> SadeqaState:
        return SadeqaState(
            board={_cell(k): v for k, v in d["board"].items()},
            warana={_cell(k): v for k, v in d.get("warana", {}).items()},
            captured=list(d["captured"]),
            to_move=d["to_move"],
            ply=d["ply"],
            no_progress=d.get("no_progress", 0),
            done=d["done"],
        )

    # -- render -------------------------------------------------------------
    def render(self, s: SadeqaState, perspective=None) -> dict:
        # Translucent tint of the warana OWNER's seat colour marks warana holes.
        WARANA_TINT = {SOUTH: "#d23b3b66", NORTH: "#3b6fd266"}
        pieces = []
        for (c, r), n in s.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": r,                 # disc colour = physical side
                "label": str(n),
            })
        tints = {f"{c},{r}": WARANA_TINT[o] for (c, r), o in s.warana.items()}

        pa, pb = self.scores(s)
        caption = f"South {pa} — North {pb}"
        if s.done:
            if pa > pb:
                caption += "  ·  South wins"
            elif pb > pa:
                caption += "  ·  North wins"
            else:
                caption += "  ·  Draw"
        else:
            caption += f"  ·  {SIDE_NAME[s.to_move]} to move"

        return {
            "board": {"type": "square", "width": WIDTH, "height": 2,
                      "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }

    # -- move log -----------------------------------------------------------
    def describe_move(self, s: SadeqaState, move: str) -> str:
        pit = _cell(move)
        n = s.board.get(pit, 0)
        return f"{SIDE_NAME[_owner(pit)]} {_hole_number(pit)} ({n} seeds)"
