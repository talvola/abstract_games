"""Ot-tjin (Aw-li On-nam Ot-tjin) -- a multi-lap relay-sowing "make fish"
Mancala of the Penihing people of the Mahakam River, Central Borneo.

First recorded by Carl Sophus Lumholtz in *Through Central Borneo* (1920);
the modern write-up followed here is Ralf Gering's article in *Abstract Games*
magazine, issue 14 (Summer 2003). This module implements the rules exactly as
given there.

Board model for the platform: a 9-wide x 2-tall SQUARE board (two rows of nine
holes), plus two off-board stores (fish collectors) shown only in the caption.
Player 0 = South (row 0, bottom), player 1 = North (row 1, top). Each cell's
rendered LABEL is its seed count.

SOWING ORIENTATION (pinned by brute-forcing the printed endgame-problem
solution against every orientation / numbering -- exactly one convention
replays the line; see selftest.py):

  * Seeds are sown CLOCKWISE, one at a time, around the 18 playing holes in a
    single fixed cycle. Stores are NOT sown into -- they only hold caught fish.
  * The cycle (sowing direction, +1): North row left->right, then South row
    right->left, then wrap. In (col,row) terms:
        (0,1)(1,1)...(8,1) (8,0)(7,0)...(0,0) -> back to (0,1)
    So each player, at his turn, sows first along his OWN row from his right to
    his left (Lumholtz's "from right to left" as seen by that player) and then
    on into the opponent's row -- and captured fish go to the store on his LEFT,
    which is why the distribution is clockwise.
  * Hole numbering (1..9, each as the player sees his own row right->left):
        South hole n -> cell (9 - n, 0)   [hole 1 = right = col 8]
        North hole n -> cell (n - 1, 1)   [hole 1 = left  = col 0]

MULTI-LAP RELAY + "make fish": pick up all seeds of one of your holes and sow.
If the last seed lands in an OCCUPIED hole, lift that hole's whole contents and
sow again in a new lap -- repeat until the last seed lands in

  * an EMPTY hole (it now holds exactly 1): the move ends, nothing is captured
    ("gok"); or
  * a hole then holding as many seeds as each hole held at the START of the game
    (e.g. 5 in the five-seed variant, i.e. dropping the last seed into a hole
    that already held 4): that is a FISH ("ara ot-tjin"). The fish (the whole
    contents of that hole) goes to the mover's store and the move ends. Only one
    fish can be caught per move.

If a player cannot move (all his holes are empty), his opponent captures ALL
remaining seeds on the board and the game ends. The player who has caught more
fish (== more seeds) wins; an equal catch is an honest DRAW.

NO RESULT / REPLAY: Lumholtz noted that if seeds are "left on either side, but
not enough to proceed", the seeds keep circulating with no captures -- an
impasse. Traditionally the game then ends WITHOUT RESULT and is replayed (it is
NOT a draw, and the remaining seeds are NOT divided). For the platform we must
still guarantee termination, so a long capture-less stretch (or a hard ply cap)
ends the game; as in `vai_lung_thlan` the result is then decided purely by the
seeds ACTUALLY captured (uncaptured seeds belong to no one -- never fabricate a
winner). A tied catch at that point is a draw, mirroring the "no result"
outcome of the printed endgame problem.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

WIDTH = 9

# Sowing cycle (+1 direction): North (top) row left->right, then South (bottom)
# row right->left, then wrap. Pinned against the printed endgame solution.
CYCLE = [(c, 1) for c in range(WIDTH)] + [(c, 0) for c in range(WIDTH - 1, -1, -1)]
CIDX = {cell: i for i, cell in enumerate(CYCLE)}
NCYC = len(CYCLE)  # 18

SIDE_NAME = {0: "South", 1: "North"}

# Anti-loop backstops (the game is guaranteed to terminate for random play).
NO_PROGRESS_CAP = 220   # plies with no fish caught -> "no result" terminal
PLY_CAP = 4000          # hard ply cap
RELAY_CAP = 100000      # per-move relay-lap safety (unreachable in real play)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def own_cells(player):
    """Cells belonging to `player`, ordered by hole number 1..9."""
    if player == 0:
        return [(WIDTH - n, 0) for n in range(1, WIDTH + 1)]   # holes 1..9
    return [(n - 1, 1) for n in range(1, WIDTH + 1)]


OWN_CELLS = {0: own_cells(0), 1: own_cells(1)}


def _owner(cell):
    return 0 if cell[1] == 0 else 1


def _hole_number(cell):
    c, r = cell
    return (WIDTH - c) if r == 0 else (c + 1)


@dataclass
class OtState:
    board: dict = field(default_factory=dict)   # (col,row) -> seed count
    stores: list = field(default_factory=lambda: [0, 0])  # SEEDS caught per player
    sph: int = 3                                 # seeds per hole at game start (fish size)
    to_move: int = 0
    ply: int = 0
    no_progress: int = 0                         # plies since the last fish
    done: bool = False


class OtTjin(Game):
    uid = "ot_tjin"
    name = "Ot-tjin"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> OtState:
        sph = 3
        if options:
            try:
                sph = int(options.get("seeds", 3))
            except (TypeError, ValueError):
                sph = 3
            if sph not in (2, 3, 4, 5):
                sph = 3
        board = {(c, r): sph for r in (0, 1) for c in range(WIDTH)}
        return OtState(board=board, stores=[0, 0], sph=sph,
                       to_move=0, ply=0, no_progress=0, done=False)

    def current_player(self, s: OtState) -> int:
        return s.to_move

    # -- core relay sowing --------------------------------------------------
    @staticmethod
    def _has_move(board, player) -> bool:
        return any(board[c] > 0 for c in OWN_CELLS[player])

    @staticmethod
    def _sow(board, start, sph):
        """Multi-lap relay sow from `start`. Returns (new_board, fish_seeds).

        fish_seeds is 0 (gok) or the size of the caught fish (== sph). Pure:
        does not mutate `board`.
        """
        board = dict(board)
        cur = start
        for _ in range(RELAY_CAP):
            seeds = board[cur]
            board[cur] = 0
            idx = CIDX[cur]
            last = cur
            for step in range(1, seeds + 1):
                cell = CYCLE[(idx + step) % NCYC]
                board[cell] += 1
                last = cell
            cnt = board[last]
            if cnt == sph:
                # "make fish": last seed brought this hole up to the start count
                board[last] = 0
                return board, cnt
            if cnt == 1:
                # gok: last seed landed in a previously-empty hole
                return board, 0
            # last seed landed in an occupied hole -> lift and relay
            cur = last
        # Safety: pathological non-terminating relay -> treat as gok.
        return board, 0

    # -- legal moves --------------------------------------------------------
    def legal_moves(self, s: OtState) -> list[str]:
        if s.done:
            return []
        return [f"{c},{r}" for (c, r) in OWN_CELLS[s.to_move] if s.board[(c, r)] > 0]

    # -- apply --------------------------------------------------------------
    def apply_move(self, s: OtState, move: str, rng=None) -> OtState:
        player = s.to_move
        start = _cell(move)
        board, fish = self._sow(s.board, start, s.sph)
        stores = list(s.stores)
        stores[player] += fish

        ply = s.ply + 1
        no_progress = 0 if fish else s.no_progress + 1
        opp = 1 - player

        board_empty = not any(board.values())
        if board_empty:
            # every seed has been caught as fish -> game over
            done, to_move = True, opp
        elif not self._has_move(board, opp):
            # opponent cannot move -> the mover captures ALL remaining seeds
            remaining = sum(board.values())
            stores[player] += remaining
            board = {c: 0 for c in board}
            done, to_move = True, opp
        elif no_progress >= NO_PROGRESS_CAP or ply >= PLY_CAP:
            # impasse / "no result": end here; seeds still on the board belong to
            # no one and are NOT divided (decided purely by fish already caught).
            done, to_move = True, opp
        else:
            done, to_move = False, opp

        return OtState(board=board, stores=stores, sph=s.sph, to_move=to_move,
                       ply=ply, no_progress=no_progress, done=done)

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s: OtState) -> bool:
        return s.done

    def returns(self, s: OtState) -> list[float]:
        a, b = s.stores
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s: OtState) -> dict:
        return {
            "board": {f"{c},{r}": n for (c, r), n in s.board.items()},
            "stores": list(s.stores),
            "sph": s.sph,
            "to_move": s.to_move,
            "ply": s.ply,
            "no_progress": s.no_progress,
            "done": s.done,
        }

    def deserialize(self, d: dict) -> OtState:
        return OtState(
            board={_cell(k): v for k, v in d["board"].items()},
            stores=list(d["stores"]),
            sph=int(d.get("sph", 3)),
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
            done=d["done"],
        )

    # -- render -------------------------------------------------------------
    def render(self, s: OtState, perspective=None) -> dict:
        pieces = []
        for (c, r), n in s.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": 0 if r == 0 else 1,
                "label": str(n),
            })
        sph = s.sph
        sf, nf = s.stores[0] // sph, s.stores[1] // sph
        caption = (f"South {sf} fish ({s.stores[0]}) — "
                   f"North {nf} fish ({s.stores[1]})")
        if s.done:
            a, b = s.stores
            if a > b:
                caption += "  ·  South wins"
            elif b > a:
                caption += "  ·  North wins"
            else:
                caption += "  ·  Draw / no result"
        else:
            caption += f"  ·  {SIDE_NAME[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": WIDTH, "height": 2},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }

    # -- nicer move log -----------------------------------------------------
    def describe_move(self, s: OtState, move: str) -> str:
        cell = _cell(move)
        side = SIDE_NAME[_owner(cell)]
        n = s.board.get(cell, 0)
        return f"{side} {_hole_number(cell)} ({n} seed{'s' if n != 1 else ''})"
