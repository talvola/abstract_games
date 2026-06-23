"""Congkak / Sungka / Congklak — the Malay/Indonesian/Bruneian/Filipino mancala.

Two rows of **seven** holes (*rumah* / houses) plus each player's **store** (the
big home hole, *rumah besar* / *head*). Seven seeds per small hole at the start,
so **98 seeds** in all.

This package implements the standard **single-lap-with-relay** Congkak rules (the
sequential-turn version — we do NOT model the simultaneous opening some regional
variants use; play strictly alternates):

* **Sowing** — scoop one of your own non-empty holes and drop one seed per hollow
  going around the board, **including your own store** but **skipping the
  opponent's store**.
* **Relay / continuation** (the signature rule) — if the last seed lands in an
  **occupied** hole, you **scoop up that whole hole** (the seeds already there
  plus the one you just dropped) and keep sowing. You relay over and over until
  the last seed finally lands in an **empty hole** or in your **store**.
* **Last seed in your store** → you take **another turn**.
* **Last seed in an empty hole on YOUR side** → **capture**: that seed plus all
  the seeds in the directly-opposite (opponent's) hole go to your store; the turn
  then ends.
* **Last seed in an empty hole on the OPPONENT's side** → the turn ends with no
  capture (the lone seed stays in the opponent's hole).

The game ends when the player to move has no seeds to sow; the opponent sweeps any
seeds left in their own holes into their store, and whoever has more seeds in their
store wins.

Holes are addressed "col,row" (col 0..6; row 0 = South / player 0, row 1 = North /
player 1) so the renderer shows them as number-labelled pits like Kalah/Oware; the
two stores are reported in the caption.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SOUTH, NORTH = 0, 1
HOLES = 7
SEEDS = 7
TOTAL = 98
PLY_CAP = 1000           # defensive cap; relay turns are bounded but generous
SIDE = {SOUTH: "South", NORTH: "North"}

SOUTH_PITS = [(c, 0) for c in range(HOLES)]
NORTH_PITS = [(c, 1) for c in range(HOLES)]
OWN_PITS = {SOUTH: SOUTH_PITS, NORTH: NORTH_PITS}

# One physical counter-clockwise ring: South's seven holes, South's store ("SS"),
# North's seven holes (right-to-left), North's store ("NS").
RING = (SOUTH_PITS + ["SS"]
        + [(c, 1) for c in (6, 5, 4, 3, 2, 1, 0)] + ["NS"])
RING_INDEX = {slot: i for i, slot in enumerate(RING)}
STORE = {SOUTH: "SS", NORTH: "NS"}
SKIP = {SOUTH: "NS", NORTH: "SS"}        # the store you sow past


def _opposite(pit):
    """The hole directly across the board (same column, other row)."""
    return (pit[0], 1 - pit[1])


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class CongkakState:
    board: dict = field(default_factory=dict)            # (c,r) -> seeds
    stores: list = field(default_factory=lambda: [0, 0])
    to_move: int = SOUTH
    ply: int = 0


class Congkak(Game):
    uid = "congkak"
    name = "Congkak"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {p: SEEDS for p in SOUTH_PITS + NORTH_PITS}
        return CongkakState(board=board, to_move=SOUTH)

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

        last = start                       # set inside the loop
        extra_turn = False
        # Relay loop: keep sowing while the last seed lands in an occupied hole.
        while True:
            seeds = board[start]
            board[start] = 0
            i = RING_INDEX[start]
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

            if last == STORE[player]:
                extra_turn = True
                break
            # last is a hole. If it was occupied before this seed (now >1), relay.
            if board[last] > 1:
                start = last
                continue
            break                          # landed in a hole that is now exactly 1

        # Capture: last seed landed in your OWN previously-empty hole.
        if (last != STORE[player] and last in OWN_PITS[player]
                and board[last] == 1 and board[_opposite(last)] > 0):
            stores[player] += 1 + board[_opposite(last)]
            board[last] = 0
            board[_opposite(last)] = 0

        nxt = player if extra_turn else 1 - player
        return CongkakState(board=board, stores=stores, to_move=nxt, ply=s.ply + 1)

    # ---- terminal / scoring ------------------------------------------------
    def is_terminal(self, s):
        if s.ply >= PLY_CAP:
            return True
        # The game ends when the player to move has no seeds to sow.
        return self._empty_side(s.board, s.to_move)

    def _final_scores(self, s):
        sc = list(s.stores)
        # each player sweeps any seeds remaining in their own holes
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
        return CongkakState(board={_cell(k): n for k, n in d["board"].items()},
                            stores=list(d["stores"]), to_move=d["to_move"],
                            ply=d.get("ply", 0))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s, move):
        c, r = _cell(move)
        return f"{SIDE[r]} {'abcdefg'[c]} ({s.board[(c, r)]})"

    def render(self, s, perspective=None):
        pieces = [{"cell": f"{c},{r}", "owner": r, "label": str(n)}
                  for (c, r), n in s.board.items()]
        if self.is_terminal(s):
            a, b = self._final_scores(s)
            res = "Draw" if a == b else f"{SIDE[SOUTH if a > b else NORTH]} wins"
            cap = f"{res}  ·  South {a} — North {b}"
        else:
            cap = (f"South {s.stores[SOUTH]} — North {s.stores[NORTH]}"
                   f"  ·  {SIDE[s.to_move]} to move")
        return {
            "board": {"type": "square", "width": HOLES, "height": 2},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
