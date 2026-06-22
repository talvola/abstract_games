"""Kalah (the commercial Mancala, "Kalah(6,4)") on a 6+6 board with two stores.

Each side has six pits of four seeds plus a store. On your turn you scoop up a
pit and sow the seeds one per hollow, counter-clockwise, **into your own store but
skipping the opponent's**. Two bonus rules give Kalah its bite: landing the last
seed in your **own store grants another turn**, and landing it in one of your own
**empty pits captures** that seed plus everything in the opposite pit. When a
player's pits all empty out the other player sweeps their remaining seeds; the
larger store wins.

Pits are addressed "col,row" (col 0..5; row 0 = South / player 0, row 1 = North /
player 1) so the renderer shows them as number-labelled pits like Oware; the two
stores are reported in the caption.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SOUTH, NORTH = 0, 1
SEEDS = 4
TOTAL = 48
PLY_CAP = 400
SIDE = {SOUTH: "South", NORTH: "North"}

SOUTH_PITS = [(c, 0) for c in range(6)]
NORTH_PITS = [(c, 1) for c in range(6)]
OWN_PITS = {SOUTH: SOUTH_PITS, NORTH: NORTH_PITS}

# One physical counter-clockwise ring of 14 slots: South's six pits, South's store
# ("SS"), North's six pits (right-to-left), North's store ("NS").
RING = (SOUTH_PITS + ["SS"]
        + [(c, 1) for c in (5, 4, 3, 2, 1, 0)] + ["NS"])
RING_INDEX = {slot: i for i, slot in enumerate(RING)}
STORE = {SOUTH: "SS", NORTH: "NS"}
SKIP = {SOUTH: "NS", NORTH: "SS"}        # the store you sow past


def _opposite(pit):
    """The pit directly across the board (same column, other row)."""
    return (pit[0], 1 - pit[1])


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class KalahState:
    board: dict = field(default_factory=dict)            # (c,r) -> seeds
    stores: list = field(default_factory=lambda: [0, 0])
    to_move: int = SOUTH
    ply: int = 0


class Kalah(Game):
    uid = "kalah"
    name = "Kalah"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {p: SEEDS for p in SOUTH_PITS + NORTH_PITS}
        return KalahState(board=board, to_move=SOUTH)

    def current_player(self, s):
        return s.to_move

    def _empty_side(self, board, player):
        return all(board[p] == 0 for p in OWN_PITS[player])

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in OWN_PITS[s.to_move] if s.board[(c, r)] > 0]

    def apply_move(self, s, move, rng=None):
        player = s.to_move
        board = dict(s.board)
        stores = list(s.stores)
        start = _cell(move)
        seeds = board[start]
        board[start] = 0
        i = RING_INDEX[start]
        last = start
        while seeds > 0:
            i = (i + 1) % len(RING)
            slot = RING[i]
            if slot == SKIP[player]:
                continue
            if slot == STORE[player]:
                stores[player] += 1
                last = slot
            else:
                board[slot] += 1
                last = slot
            seeds -= 1

        extra_turn = last == STORE[player]
        # capture: last seed in your own previously-empty pit, opposite non-empty
        if (last in OWN_PITS[player] and board[last] == 1
                and board[_opposite(last)] > 0):
            stores[player] += 1 + board[_opposite(last)]
            board[last] = 0
            board[_opposite(last)] = 0

        nxt = player if extra_turn else 1 - player
        ns = KalahState(board=board, stores=stores, to_move=nxt, ply=s.ply + 1)
        # if the side now to move has no seeds, the game is over (handled in
        # is_terminal/returns via the end-sweep); but if the *mover* emptied the
        # board such that nobody can act, terminal too.
        return ns

    # ---- terminal / scoring ------------------------------------------------
    def is_terminal(self, s):
        return (s.ply >= PLY_CAP
                or self._empty_side(s.board, SOUTH)
                or self._empty_side(s.board, NORTH))

    def _final_scores(self, s):
        sc = list(s.stores)
        # each player sweeps any seeds remaining in their own pits
        for pl in (SOUTH, NORTH):
            sc[pl] += sum(s.board[p] for p in OWN_PITS[pl])
        return sc

    def returns(self, s):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        a, b = self._final_scores(s)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- (de)serialise -----------------------------------------------------
    def serialize(self, s):
        return {"board": {f"{c},{r}": n for (c, r), n in s.board.items()},
                "stores": list(s.stores), "to_move": s.to_move, "ply": s.ply}

    def deserialize(self, d):
        return KalahState(board={_cell(k): n for k, n in d["board"].items()},
                          stores=list(d["stores"]), to_move=d["to_move"], ply=d.get("ply", 0))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s, move):
        c, r = _cell(move)
        return f"{SIDE[r]} {'abcdef'[c]} ({s.board[(c, r)]})"

    def render(self, s, perspective=None):
        pieces = [{"cell": f"{c},{r}", "owner": r, "label": str(n)}
                  for (c, r), n in s.board.items()]
        if self.is_terminal(s):
            a, b = self._final_scores(s)
            res = "Draw" if a == b else f"{SIDE[SOUTH if a > b else NORTH]} wins"
            cap = f"{res}  ·  South {a} — North {b}"
        else:
            cap = f"South {s.stores[SOUTH]} — North {s.stores[NORTH]}  ·  {SIDE[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": 6, "height": 2},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
