"""Congkak correctness anchor (pure stdlib). No published perft for Congkak, so
the anchor is a set of baked rule assertions:

  (1) board shape: 2 rows of 7 holes + 2 stores, 7 seeds/hole, 98 total at start;
  (2) sowing counter-clockwise drops one seed per hole INCLUDING your own store
      but SKIPPING the opponent's store;
  (3) the RELAY / continuation rule (last seed on a non-empty hole -> scoop it up
      and keep sowing) and the EXTRA-TURN-on-own-store rule;
  (4) the CAPTURE rule (last seed in your OWN empty hole -> take it + the opposite
      hole into your store; turn ends) and the no-capture cases;
  (5) game end (player to move has no seeds) + sweep + most-seeds win;
  plus seed conservation (== 98) across a full random game.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.congkak.game import (  # noqa: E402
    Congkak, CongkakState, SOUTH, NORTH, HOLES, SEEDS, TOTAL)

G = Congkak()
EMPTY = {(c, r): 0 for r in (0, 1) for c in range(HOLES)}


def main():
    # (1) board shape ------------------------------------------------------
    s = G.initial_state()
    assert len(s.board) == 2 * HOLES == 14, "two rows of seven holes"
    assert all(v == SEEDS == 7 for v in s.board.values()), "7 seeds per hole"
    assert sum(s.board.values()) == TOTAL == 98, "98 seeds total"
    assert s.stores == [0, 0] and s.to_move == SOUTH
    assert len(G.legal_moves(s)) == 7, "seven non-empty holes to choose from"

    # (2) sowing includes OWN store, skips OPPONENT's store ---------------
    # 13 seeds from (0,0): the other six South holes (1..6) each +1, South store
    # (SS) +1, then North holes from (6,1) down to (1,1) each +1 (six of them).
    # The 13th (last) seed lands in (1,1) -- a North hole -- so the turn passes
    # and North's far hole (0,1) is NOT reached. This exercises the include-own-
    # store / skip-opponent-store sowing without triggering a relay.
    b = dict(EMPTY); b[(0, 0)] = 13
    st = CongkakState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "0,0")
    assert st2.stores[SOUTH] == 1, "one seed went into South's own store"
    assert st2.stores[NORTH] == 0, "nothing ever went into North's store"
    assert all(st2.board[(c, 0)] == 1 for c in range(1, 7)), "South holes 1..6 each +1"
    assert all(st2.board[(c, 1)] == 1 for c in range(1, 7)), "North holes 1..6 each +1"
    assert st2.board[(0, 1)] == 0, "the far North hole was not reached by 13 seeds"
    assert st2.board[(0, 0)] == 0
    assert st2.to_move == NORTH, "last seed in a North hole -> turn passes"

    # confirm the opponent's store is skipped even when we sow far enough to lap:
    # 15 seeds from (0,0) would reach NS (North's store) at ring index 15 -> it
    # must be skipped, so the 15th seed wraps to South's first hole instead.
    b = dict(EMPTY); b[(0, 0)] = 15
    st = CongkakState(board=b, stores=[0, 0], to_move=SOUTH)
    # 15 seeds: holes (1..6,0)=6, SS=1 (7), North (6..0,1)=7 (14), wrap skips NS,
    # 15th -> (0,0). (0,0) was emptied so it becomes 1 (an empty hole) -> capture
    # of the opposite North hole (0,1) which now holds 1.
    st2 = G.apply_move(st, "0,0")
    assert st2.stores[NORTH] == 0, "North's store stayed empty (skipped)"

    # (3a) RELAY: last seed lands on an OCCUPIED hole -> scoop & continue ---
    # South (0,0)=2 seeds. Sow -> (1,0)+1, (2,0)+1. Make (2,0) occupied so it
    # becomes >1 and relays. Set (2,0)=3 (becomes 4), then relay sows 4 from
    # (2,0): (3,0),(4,0),(5,0),(6,0) each +1; last is (6,0) which was empty -> 1.
    b = dict(EMPTY); b[(0, 0)] = 2; b[(2, 0)] = 3
    st = CongkakState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "0,0")
    assert st2.board[(0, 0)] == 0 and st2.board[(2, 0)] == 0, "relayed hole emptied"
    assert st2.board[(1, 0)] == 1, "first lap dropped a seed in (1,0)"
    # second lap from (2,0) (4 seeds) -> (3,0),(4,0),(5,0),(6,0) each 1
    assert all(st2.board[(c, 0)] == 1 for c in (3, 4, 5, 6)), "relay lap dropped seeds"
    # last landed in (6,0), own side, was empty -> capture of opposite (6,1) (empty)
    # so no extra capture; just the lone seed. Stores unchanged.
    assert st2.stores[SOUTH] == 0, "no capture (opposite hole empty)"
    assert st2.to_move == NORTH, "turn ends after relay finishes on empty hole"

    # (3b) EXTRA TURN: last seed in your own store ------------------------
    # South (4,0)=3 seeds -> (5,0),(6,0),SS. Last in store -> extra turn.
    b = dict(EMPTY); b[(4, 0)] = 3
    st = CongkakState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "4,0")
    assert st2.stores[SOUTH] == 1, "one seed into store"
    assert st2.to_move == SOUTH, "store landing -> another turn"

    # (4a) CAPTURE: last seed in your OWN empty hole, opposite non-empty ---
    # South (0,0)=1 -> lands in empty (1,0); opposite (1,1)=5 -> capture 1+5=6.
    b = dict(EMPTY); b[(0, 0)] = 1; b[(1, 1)] = 5
    st = CongkakState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "0,0")
    assert st2.stores[SOUTH] == 6, "captured own seed + opposite hole"
    assert st2.board[(1, 0)] == 0 and st2.board[(1, 1)] == 0, "both holes emptied"
    assert st2.to_move == NORTH, "turn ends after a capture"

    # (4b) NO capture when the OPPOSITE hole is empty ---------------------
    b = dict(EMPTY); b[(0, 0)] = 1            # opposite (1,1) empty
    st = CongkakState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "0,0")
    assert st2.stores[SOUTH] == 0 and st2.board[(1, 0)] == 1, "lone seed stays, no capture"
    assert st2.to_move == NORTH

    # (4c) NO capture when last seed lands on the OPPONENT's empty hole ----
    # South sows so the last seed lands on North's side in an empty hole.
    # (6,0)=2 -> (SS)? no: (6,0) next is SS (store), then (6,1). 2 seeds: SS, (6,1).
    # Last in (6,1) (North side, empty) -> turn ends, no capture, +1 to own store.
    b = dict(EMPTY); b[(6, 0)] = 2
    st = CongkakState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "6,0")
    assert st2.stores[SOUTH] == 1, "passed own store once"
    assert st2.board[(6, 1)] == 1, "lone seed left in opponent's hole"
    assert st2.to_move == NORTH, "no capture on opponent's side; turn ends"

    # (5) game end + sweep + win ------------------------------------------
    # South to move with an empty South side -> terminal; North sweeps its holes.
    b = dict(EMPTY); b[(3, 1)] = 2; b[(4, 1)] = 3      # South side empty
    st = CongkakState(board=b, stores=[40, 50], to_move=SOUTH)
    assert G.is_terminal(st), "player to move has no seeds -> game over"
    assert G._final_scores(st) == [40, 55], "North sweeps 5 into its store"
    assert G.returns(st) == [-1.0, 1.0], "more seeds in store wins"

    # NOT terminal while the player to move still has a seed somewhere
    b = dict(EMPTY); b[(0, 0)] = 1
    st = CongkakState(board=b, stores=[0, 0], to_move=SOUTH)
    assert not G.is_terminal(st)

    # seed conservation across a full random game (== 98 always) ----------
    import random
    rng = random.Random(7)
    st = G.initial_state()
    while not G.is_terminal(st):
        assert sum(st.board.values()) + sum(st.stores) == TOTAL, "seeds not conserved"
        st = G.apply_move(st, rng.choice(G.legal_moves(st)))
    assert sum(st.board.values()) + sum(st.stores) == TOTAL
    assert sum(G._final_scores(st)) == TOTAL, "all 98 seeds accounted for at end"

    # serialize round-trips
    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
