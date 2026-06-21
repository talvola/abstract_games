"""Standalone correctness anchor for Oware.

Run with:  PYTHONPATH=. python3 games/oware/selftest.py

Pure stdlib + this game only. Fast (a handful of random conformance games plus
a set of hand-built rule positions). Prints "SELFTEST OK" and exits 0 on
success, nonzero on any failure.
"""

from __future__ import annotations

import random
import sys

from games.oware.game import Oware, OwareState, PIT_ORDER, PIT_INDEX, OWN_PITS

G = Oware()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def state(board_overrides, stores=(0, 0), to_move=0, ply=0, done=False):
    """Build a state; board defaults to all-zero, then apply overrides."""
    board = {pit: 0 for pit in PIT_ORDER}
    for k, v in board_overrides.items():
        board[k] = v
    return OwareState(board=dict(board), stores=list(stores),
                      to_move=to_move, ply=ply, done=done)


def total_on_board(s):
    return sum(s.board.values())


# ---------------------------------------------------------------------------
# 1. Setup invariants
# ---------------------------------------------------------------------------
s0 = G.initial_state()
if sum(s0.board.values()) != 48:
    fail("initial board does not total 48 seeds")
if any(s0.board[p] != 4 for p in PIT_ORDER):
    fail("initial pits not all 4 seeds")
if s0.stores != [0, 0]:
    fail("initial stores not zero")
if len(set(PIT_ORDER)) != 12:
    fail("pit order not 12 distinct pits")

# Pit order: South L->R then North R->L (counterclockwise).
assert PIT_ORDER[0] == (0, 0) and PIT_ORDER[5] == (5, 0)
assert PIT_ORDER[6] == (5, 1) and PIT_ORDER[11] == (0, 1)


# ---------------------------------------------------------------------------
# 2. Basic sowing (no capture): seeds go counterclockwise, one per pit.
# ---------------------------------------------------------------------------
# South sows 3 seeds from (2,0): should fill (3,0),(4,0),(5,0).
# (North loaded with 4 so the game does not end via the empty-side sweep.)
s = state({(2, 0): 3, (0, 1): 4}, to_move=0)
ns = G.apply_move(s, "2,0")
assert ns.board[(2, 0)] == 0
assert ns.board[(3, 0)] == 1 and ns.board[(4, 0)] == 1 and ns.board[(5, 0)] == 1
assert ns.stores == [0, 0], "no capture expected"
assert not ns.done

# South sows from the last South pit (5,0) into the North row.
s = state({(5, 0): 2, (0, 1): 4}, to_move=0)
ns = G.apply_move(s, "5,0")
# next pits in cycle after (5,0): (5,1),(4,1) -- but lands making them 1 each
assert ns.board[(5, 1)] == 1 and ns.board[(4, 1)] == 1


# ---------------------------------------------------------------------------
# 3. 12+ lap skips ONLY the originating pit.
# ---------------------------------------------------------------------------
# Put 12 seeds in one pit; sowing 12 should skip the origin and land 1 in each
# of the OTHER 11 pits and then 1 more wrapping past the origin into the next.
s = state({(0, 0): 12}, to_move=0)
ns = G.apply_move(s, "0,0")
# Origin must remain empty (skipped on the lap).
assert ns.board[(0, 0)] == 0, "origin pit should be skipped on a 12-lap"
# 11 other pits got 1 each (11 seeds), 12th seed wraps to the next pit (1,0)
# making it 2.
assert ns.board[(1, 0)] == 2, "12th seed should land in (1,0) after skipping origin"
for pit in PIT_ORDER:
    if pit not in ((0, 0), (1, 0)):
        assert ns.board[pit] == 1
assert total_on_board(ns) + sum(ns.stores) == 12


# ---------------------------------------------------------------------------
# 4. Capture: last seed lands in opponent pit making it 2 or 3.
# ---------------------------------------------------------------------------
# (Each case keeps an extra North pit loaded so the capture is never a
# grand-slam -- those are tested separately below.)
# South sows 1 seed from (5,0) -> lands in (5,1) (North). Make (5,1) become 2.
s = state({(5, 0): 1, (5, 1): 1, (0, 1): 4}, to_move=0)
ns = G.apply_move(s, "5,0")
assert ns.board[(5, 1)] == 0, "captured pit emptied"
assert ns.stores[0] == 2, "south captured 2 seeds"

# Make it 3 instead.
s = state({(5, 0): 1, (5, 1): 2, (0, 1): 4}, to_move=0)
ns = G.apply_move(s, "5,0")
assert ns.stores[0] == 3 and ns.board[(5, 1)] == 0

# Making it 4 (or 1) -> no capture.
s = state({(5, 0): 1, (5, 1): 3, (0, 1): 4}, to_move=0)
ns = G.apply_move(s, "5,0")
assert ns.stores[0] == 0 and ns.board[(5, 1)] == 4

# Landing in own row never captures.
s = state({(2, 0): 1, (3, 0): 2, (0, 1): 4}, to_move=0)
ns = G.apply_move(s, "2,0")
assert ns.stores[0] == 0 and ns.board[(3, 0)] == 3


# ---------------------------------------------------------------------------
# 5. Back-propagating multi-capture along consecutive 2/3 opponent pits.
# ---------------------------------------------------------------------------
# Sowing order in North row is (5,1),(4,1),(3,1),(2,1),(1,1),(0,1).
# South sows from (5,0) with 4 seeds: lands in (5,1),(4,1),(3,1),(2,1).
# Pre-load so the chain (2,1)<-(3,1)<-(4,1) all become 2/3, but (5,1) becomes 4
# to break the chain there.
s = state({(5, 0): 4,
           (5, 1): 3,   # +1 -> 4  (breaks chain)
           (4, 1): 1,   # +1 -> 2  (capture)
           (3, 1): 2,   # +1 -> 3  (capture)
           (2, 1): 1},  # +1 -> 2  (last seed, capture)
          to_move=0)
ns = G.apply_move(s, "5,0")
# Last seed landed in (2,1)=2 -> capture; back-propagate to (3,1)=3, (4,1)=2,
# then (5,1)=4 breaks the chain.
assert ns.board[(2, 1)] == 0 and ns.board[(3, 1)] == 0 and ns.board[(4, 1)] == 0
assert ns.board[(5, 1)] == 4, "chain stops at the 4-pit"
assert ns.stores[0] == 2 + 3 + 2, "captured 7 seeds along the chain"


# ---------------------------------------------------------------------------
# 6. Grand-slam rule: would capture ALL opponent seeds -> captures nothing.
# ---------------------------------------------------------------------------
# North has seeds only in (5,1)=1. South sows 1 from (5,0) -> (5,1) becomes 2,
# which would capture all of North's seeds. Convention: played, captures nothing.
s = state({(5, 0): 1, (5, 1): 1}, to_move=0)
# (North's only seeds are in (5,1).)
assert sum(s.board[p] for p in OWN_PITS[1]) == 1
ns = G.apply_move(s, "5,0")
assert ns.stores[0] == 0, "grand slam must capture nothing"
assert ns.board[(5, 1)] == 2, "grand-slammed seeds stay on the board"

# But a partial capture that does NOT empty the opponent is fine.
s = state({(5, 0): 1, (5, 1): 1, (0, 1): 5}, to_move=0)
ns = G.apply_move(s, "5,0")
assert ns.stores[0] == 2, "non-grand-slam capture still happens"
assert ns.board[(5, 1)] == 0


# ---------------------------------------------------------------------------
# 7. Starvation / feeding rule.
# ---------------------------------------------------------------------------
# North has no seeds. South to move. South must pick a move that feeds North.
# (4,0)=1 -> sows into (5,0) (own row) -> does NOT feed -> illegal.
# (5,0)=2 -> sows into (5,1),(4,1) (North) -> feeds -> legal & required.
s = state({(4, 0): 1, (5, 0): 2}, to_move=0)  # North empty
moves = G.legal_moves(s)
assert moves == ["5,0"], f"only the feeding move should be legal, got {moves}"

# If NO feeding move exists, the game ends after the move with a sweep.
# North empty; South only has (0,0)=1 which sows into (1,0) (own row) -> cannot
# ever feed North. So the game ends and South sweeps its remaining seeds.
s = state({(0, 0): 1, (1, 0): 3}, to_move=0)  # North empty, no feed possible
moves = G.legal_moves(s)
assert "0,0" in moves and "1,0" in moves, "all moves legal when no feed exists"
ns = G.apply_move(s, "1,0")
assert ns.done, "game ends when opponent starved with no rescue"
# South had 1 (in (0,0)) + sowed (1,0)'s 3 -> all 4 stay South's side, swept.
assert ns.stores[0] == 4 and ns.stores[1] == 0
assert total_on_board(ns) == 0, "all seeds swept off the board"


# ---------------------------------------------------------------------------
# 8. End-of-game sweep totals are conserved; majority win threshold.
# ---------------------------------------------------------------------------
# Reaching 25 wins outright. (Extra North pit so the capture isn't a grand-slam.)
s = state({(5, 0): 1, (5, 1): 1, (0, 1): 4}, stores=(23, 0), to_move=0)
ns = G.apply_move(s, "5,0")  # captures 2 -> 25
assert ns.stores[0] == 25 and ns.done
assert G.returns(ns) == [1.0, -1.0]

# Draw scoring 24-24.
s = state({}, stores=(24, 24), to_move=0, done=True)
assert G.returns(s) == [0.0, 0.0]


# ---------------------------------------------------------------------------
# 9. Serialization round-trips.
# ---------------------------------------------------------------------------
s = state({(0, 0): 7, (3, 1): 2}, stores=(5, 9), to_move=1, ply=12)
d1 = G.serialize(s)
s2 = G.deserialize(d1)
d2 = G.serialize(s2)
assert d1 == d2, "serialize must round-trip"
# JSON-able
import json
json.dumps(d1)


# ---------------------------------------------------------------------------
# 10. apply_move purity: never mutates the input state.
# ---------------------------------------------------------------------------
s = G.initial_state()
before = G.serialize(s)
_ = G.apply_move(s, "2,0")
after = G.serialize(s)
assert before == after, "apply_move mutated the input state"


# ---------------------------------------------------------------------------
# 11. Conformance: random self-play games terminate, with well-formed returns
#     and seed conservation throughout.
# ---------------------------------------------------------------------------
rng = random.Random(1234)
for game_i in range(40):
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s):
        moves = G.legal_moves(s)
        assert moves, "non-terminal state must have legal moves"
        # Seed conservation: board + both stores == 48 at every step.
        assert total_on_board(s) + sum(s.stores) == 48, "seeds not conserved"
        mv = rng.choice(moves)
        s = G.apply_move(s, mv)
        steps += 1
        assert steps <= 1000, "game failed to terminate"
    assert total_on_board(s) + sum(s.stores) == 48, "final seed count wrong"
    r = G.returns(s)
    assert len(r) == 2 and all(isinstance(x, float) for x in r)
    assert set(r) <= {-1.0, 0.0, 1.0}
    # At terminal, all seeds should be in stores (every ending sweeps/captures).
    # (Win-by-25 may leave seeds on the board; allow that case.)
    if s.stores[0] < 25 and s.stores[1] < 25:
        assert total_on_board(s) == 0, "non-win ending should sweep board empty"


print("SELFTEST OK")
sys.exit(0)
