"""Standalone correctness anchor for Pallanguzhi.

Run with:  PYTHONPATH=. python3 games/pallanguzhi/selftest.py

Pure stdlib + this game only. Fast (hand-built rule positions plus a batch of
random conformance games). Prints "SELFTEST OK" and exits 0 on success, nonzero
on any failure.

There is no published perft for pallanguzhi; the anchor is a set of baked rule
assertions (setup + opening legal-move count, the kashi/capture-at-four rule, the
lap/relay continuation, the empty-pit ending capture, the end-of-round sweep, and
the win/draw scoring) plus seed conservation + termination across many random
self-play games.
"""

from __future__ import annotations

import json
import random
import sys

from games.pallanguzhi.game import (
    Pallanguzhi, PState, PIT_ORDER, OWN_PITS, N_PITS,
    TOTAL_SEEDS, START_PER_PIT, CAPTURE_AT,
)

G = Pallanguzhi()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def state(overrides, stores=(0, 0), to_move=0, ply=0, done=False):
    board = {pit: 0 for pit in PIT_ORDER}
    for k, v in overrides.items():
        board[k] = v
    return PState(board=dict(board), stores=list(stores),
                  to_move=to_move, ply=ply, done=done)


def grand_total(s):
    return sum(s.board.values()) + sum(s.stores)


# ---------------------------------------------------------------------------
# 1. Setup invariants: 2x7 pits, 84 seeds, 6 per pit, empty stores.
# ---------------------------------------------------------------------------
s0 = G.initial_state()
if N_PITS != 14 or len(set(PIT_ORDER)) != 14:
    fail("pit order is not 14 distinct pits")
if len(OWN_PITS[0]) != 7 or len(OWN_PITS[1]) != 7:
    fail("each player must own exactly 7 pits")
if sum(s0.board.values()) != TOTAL_SEEDS or TOTAL_SEEDS != 84:
    fail("initial board does not total 84 seeds")
if any(s0.board[p] != START_PER_PIT for p in PIT_ORDER) or START_PER_PIT != 6:
    fail("initial pits not all 6 seeds")
if s0.stores != [0, 0]:
    fail("initial stores not empty")
if CAPTURE_AT != 4:
    fail("capture threshold must be 4 (kashi/cow)")
# Counterclockwise order: bottom L->R then top R->L.
assert PIT_ORDER[0] == (0, 0) and PIT_ORDER[6] == (6, 0)
assert PIT_ORDER[7] == (6, 1) and PIT_ORDER[13] == (0, 1)

# Opening: every one of the 7 own pits is non-empty -> exactly 7 legal moves.
if len(G.legal_moves(s0)) != 7:
    fail("opening must offer exactly 7 legal moves")
assert G.current_player(s0) == 0


# ---------------------------------------------------------------------------
# 2. KASHI / cow: a seed that brings a pit to exactly four is captured at once.
# ---------------------------------------------------------------------------
# Single-seed handful from (0,0) -> lands in (1,0) which already holds 3 -> 4 ->
# captured into the mover's store; pit emptied.
s = state({(0, 0): 1, (1, 0): 3})
ns = G.apply_move(s, "0,0")
assert ns.board[(1, 0)] == 0, "pit reaching four must be emptied"
assert ns.stores[0] == 4, "kashi captures the four seeds for the mover"
assert grand_total(ns) == grand_total(s)
# It applies in the OPPONENT's row too (mover still captures). From (6,0) one
# seed crosses into (6,1); preload (6,1)=3 -> becomes 4 -> mover (P0) captures.
s = state({(6, 0): 1, (6, 1): 3})
ns = G.apply_move(s, "6,0")
assert ns.board[(6, 1)] == 0 and ns.stores[0] == 4, "kashi works on opponent pits"


# ---------------------------------------------------------------------------
# 3. EMPTY-PIT ending: last seed, next pit empty -> turn ends, capture the pit
#    BEYOND the empty pit.
# ---------------------------------------------------------------------------
# (0,0)=1 -> last seed into (1,0)->1 (not four). Next pit (2,0) is empty -> end;
# beyond pit (3,0) holds 5 -> all captured.
s = state({(0, 0): 1, (3, 0): 5})
ns = G.apply_move(s, "0,0")
assert ns.board[(1, 0)] == 1, "last seed stays in the landing pit"
assert ns.board[(3, 0)] == 0, "pit beyond the empty pit is captured"
assert ns.stores[0] == 5
assert grand_total(ns) == grand_total(s)

# Two empty pits ahead -> capture nothing. (0,0)=1 -> (1,0)->1; (2,0) empty,
# (3,0) empty -> nothing captured.
s = state({(0, 0): 1})
ns = G.apply_move(s, "0,0")
assert ns.stores[0] == 0, "two empty pits ahead captures nothing"
assert ns.board[(1, 0)] == 1


# ---------------------------------------------------------------------------
# 4. LAP / relay: last seed of a handful, next pit non-empty -> scoop it and
#    keep sowing.
# ---------------------------------------------------------------------------
# (0,0)=1 -> last into (1,0)->6 (set (1,0)=5). Next (2,0)=2 (non-empty) -> scoop
# the 2 seeds and continue: sow (3,0)->1,(4,0)->1. Last (4,0); next (5,0) empty
# -> end, beyond (6,0) empty -> nothing.
s = state({(0, 0): 1, (1, 0): 5, (2, 0): 2})
ns = G.apply_move(s, "0,0")
assert ns.board[(1, 0)] == 6, "landing pit keeps its seeds when relaying"
assert ns.board[(2, 0)] == 0, "the relayed pit is scooped empty"
assert ns.board[(3, 0)] == 1 and ns.board[(4, 0)] == 1, "the lap continues sowing"
assert ns.stores[0] == 0
assert grand_total(ns) == grand_total(s)

# Relay that THEN triggers a kashi mid-lap. (0,0)=1 -> (1,0)->2 (set (1,0)=1);
# next (2,0)=1 non-empty -> scoop 1 -> sow into (3,0); set (3,0)=3 -> becomes 4
# -> captured. After: next pit (4,0) empty -> end, beyond (5,0) empty -> nothing.
s = state({(0, 0): 1, (1, 0): 1, (2, 0): 1, (3, 0): 3})
ns = G.apply_move(s, "0,0")
assert ns.board[(3, 0)] == 0 and ns.stores[0] == 4, "kashi can fire mid-lap"
assert ns.board[(1, 0)] == 2 and ns.board[(2, 0)] == 0


# ---------------------------------------------------------------------------
# 5. apply_move purity: never mutates the input state.
# ---------------------------------------------------------------------------
s = G.initial_state()
before = G.serialize(s)
_ = G.apply_move(s, "3,0")
assert G.serialize(s) == before, "apply_move mutated the input state"


# ---------------------------------------------------------------------------
# 6. END-OF-ROUND sweep + win/draw scoring.
# ---------------------------------------------------------------------------
# Terminal with loose seeds: each side's loose seeds go to that side's owner
# before comparing. P0 stores 30, P1 stores 10; P0 holds 10 on its own row, P1
# holds 4 on its own row. Swept: P0 = 40, P1 = 14 -> P0 wins.
s = state({(0, 0): 10, (0, 1): 4}, stores=(30, 10), to_move=1, done=True)
assert grand_total(s) == 30 + 10 + 14
assert G.returns(s) == [1.0, -1.0], "swept P0 (40) must beat P1 (14)"
swept = G._swept_stores(s.board, s.stores)
assert swept == [40, 14], "swept stores must conserve every seed, got %r" % (swept,)

# Equal swept totals -> draw.
s = state({(0, 0): 2, (0, 1): 2}, stores=(40, 40), to_move=1, done=True)
assert G.returns(s) == [0.0, 0.0], "equal swept totals -> draw"

# Reaching a terminal via apply_move when the opponent's row is emptied. Give P0
# a single seed in (0,0); P1's row already empty; after P0 moves, P1 has no move.
s = state({(0, 0): 1}, stores=(41, 42), to_move=0)
ns = G.apply_move(s, "0,0")
assert ns.done, "round ends when the next player cannot sow"
# (0,0) emptied; one seed sown into (1,0) (P0's row), captured nothing.
assert sum(ns.board[p] for p in OWN_PITS[1]) == 0
r = G.returns(ns)
assert len(r) == 2 and set(r) <= {-1.0, 0.0, 1.0}


# ---------------------------------------------------------------------------
# 7. Serialization round-trips.
# ---------------------------------------------------------------------------
s = state({(0, 0): 7, (3, 1): 2, (5, 0): 1}, stores=(20, 18), to_move=1, ply=9)
d1 = G.serialize(s)
s2 = G.deserialize(d1)
d2 = G.serialize(s2)
assert d1 == d2, "serialize must round-trip"
json.dumps(d1)


# ---------------------------------------------------------------------------
# 8. Conformance: random self-play games terminate with seed conservation
#    throughout (board + stores == 84 always) and well-formed returns.
# ---------------------------------------------------------------------------
rng = random.Random(20260624)
saw_decisive = False
for _ in range(150):
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s):
        moves = G.legal_moves(s)
        assert moves, "non-terminal state must have legal moves"
        assert grand_total(s) == TOTAL_SEEDS, "seeds not conserved"
        s = G.apply_move(s, rng.choice(moves))
        steps += 1
        assert steps <= 6000, "game failed to terminate"
    assert grand_total(s) == TOTAL_SEEDS, "final seed count wrong"
    r = G.returns(s)
    assert len(r) == 2 and all(isinstance(x, float) for x in r)
    assert set(r) <= {-1.0, 0.0, 1.0}
    if r != [0.0, 0.0]:
        saw_decisive = True
assert saw_decisive, "expected at least one decisive random game"


print("SELFTEST OK")
sys.exit(0)
