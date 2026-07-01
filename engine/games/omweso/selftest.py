"""Standalone correctness anchor for Omweso.

Run with:  PYTHONPATH=. python3 games/omweso/selftest.py

Pure stdlib + this game only. Fast (a set of hand-built rule positions plus a
handful of random conformance games). Prints "SELFTEST OK" and exits 0 on
success, nonzero on any failure.
"""

from __future__ import annotations

import json
import random
import sys

from games.omweso.game import (
    Omweso, OmwesoState, OWN_PITS, SOW_ORDER, SOW_INDEX,
    INNER_ROW, OUTER_ROW, WIDTH,
)

G = Omweso()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def state(overrides, to_move=0, ply=0):
    board = {(c, r): 0 for r in range(4) for c in range(WIDTH)}
    for k, v in overrides.items():
        board[k] = v
    return OmwesoState(board=dict(board), to_move=to_move, ply=ply)


def total(s):
    return sum(s.board.values())


# ---------------------------------------------------------------------------
# 1. Setup invariants: 4 seeds in each outer-row pit, inner rows empty, 64 total.
# ---------------------------------------------------------------------------
s0 = G.initial_state()
if total(s0) != 64:
    fail("initial board does not total 64 seeds")
for c in range(WIDTH):
    if s0.board[(c, OUTER_ROW[0])] != 4 or s0.board[(c, OUTER_ROW[1])] != 4:
        fail("outer-row pits should start at 4 seeds")
    if s0.board[(c, INNER_ROW[0])] != 0 or s0.board[(c, INNER_ROW[1])] != 0:
        fail("inner-row pits should start empty")
if sum(s0.board[p] for p in OWN_PITS[0]) != 32:
    fail("South should own 32 seeds")
if sum(s0.board[p] for p in OWN_PITS[1]) != 32:
    fail("North should own 32 seeds")

# Sowing circuits are 16 distinct pits each, all owned by that player.
for pl in (0, 1):
    assert len(SOW_ORDER[pl]) == 16 and len(set(SOW_ORDER[pl])) == 16
    assert set(SOW_ORDER[pl]) == set(OWN_PITS[pl])
    assert len(SOW_INDEX[pl]) == 16

# South's circuit: inner row L->R then outer row R->L (a physical loop).
assert SOW_ORDER[0][0] == (0, 1) and SOW_ORDER[0][7] == (7, 1)
assert SOW_ORDER[0][8] == (7, 0) and SOW_ORDER[0][15] == (0, 0)


# ---------------------------------------------------------------------------
# 2. Only pits with >= 2 seeds are legal sources.
# ---------------------------------------------------------------------------
s = state({(0, 0): 1, (1, 0): 2, (3, 1): 5}, to_move=0)
moves = set(G.legal_moves(s))
assert moves == {"1,0", "3,1"}, f"legal sources wrong: {moves}"
assert "0,0" not in moves, "a 1-seed pit must not be a legal source"


# ---------------------------------------------------------------------------
# 3. Basic sowing (no relay, no capture): one seed per pit, counterclockwise.
# ---------------------------------------------------------------------------
# South sows 2 from (0,1) [inner col0, index 0] -> (1,1),(2,1).
s = state({(0, 1): 2}, to_move=0)
ns = G.apply_move(s, "0,1")
assert ns.board[(0, 1)] == 0
assert ns.board[(1, 1)] == 1 and ns.board[(2, 1)] == 1
assert total(ns) == total(s), "seed count must be conserved"
assert ns.to_move == 1

# South sows from inner col7 (7,1) down to the outer row: (7,0) then (6,0).
s = state({(7, 1): 2}, to_move=0)
ns = G.apply_move(s, "7,1")
assert ns.board[(7, 0)] == 1 and ns.board[(6, 0)] == 1


# ---------------------------------------------------------------------------
# 4. Relay: last seed in an occupied (non-capturing) pit -> pick up & continue.
# ---------------------------------------------------------------------------
# Start (7,1)=2 sows into (7,0),(6,0); preload (6,0)=1 so it becomes 2 (occupied,
# OUTER row -> never a capture) -> relay from (6,0) into (5,0),(4,0).
s = state({(7, 1): 2, (6, 0): 1}, to_move=0)
ns = G.apply_move(s, "7,1")
assert ns.board[(6, 0)] == 0, "relayed pit must be emptied and re-sown"
assert ns.board[(7, 0)] == 1
assert ns.board[(5, 0)] == 1 and ns.board[(4, 0)] == 1
assert total(ns) == total(s), "relay conserves seeds"


# ---------------------------------------------------------------------------
# 5. Capture: last seed lands in an occupied INNER pit whose opposing column
#    (both opponent pits) is occupied -> capture both + re-sow from lap start.
# ---------------------------------------------------------------------------
# South starts (0,0)=2 [outer col0, index 15]; sows into (0,1) then (1,1).
# Preload (1,1)=1 so the last seed makes it 2 (occupied inner col1). Opponent
# column 1: (1,2)=3 and (1,3)=2 both occupied -> capture 5, re-sow from (0,0).
s = state({(0, 0): 2, (1, 1): 1, (1, 2): 3, (1, 3): 2}, to_move=0)
before = total(s)
ns = G.apply_move(s, "0,0")
assert ns.board[(1, 2)] == 0 and ns.board[(1, 3)] == 0, "both opp pits captured"
# Re-sow 5 captured seeds from (0,0): (0,1),(1,1),(2,1),(3,1),(4,1).
assert ns.board[(0, 1)] == 2, "(0,1) got the sow seed then a re-sow seed"
assert ns.board[(1, 1)] == 3, "(1,1): 1 preload +1 sow +1 re-sow"
assert ns.board[(2, 1)] == 1 and ns.board[(3, 1)] == 1 and ns.board[(4, 1)] == 1
assert ns.board[(0, 0)] == 0
assert total(ns) == before, "capture re-sows onto the board; total conserved"

# No capture when only ONE of the opposing column pits is occupied.
s = state({(0, 0): 2, (1, 1): 1, (1, 2): 3, (1, 3): 0}, to_move=0)
ns = G.apply_move(s, "0,0")
# (1,1) becomes 2 (occupied inner) but opp column not both filled -> relay, not
# capture: (1,2) survives.
assert ns.board[(1, 2)] == 3, "no capture when opposing column not both occupied"

# Landing in your OWN inner row that is EMPTY (becomes 1) never captures.
s = state({(0, 0): 1, (0, 1): 0, (0, 2): 3, (0, 3): 3}, to_move=0)
# (0,0)=1 is not a legal source (needs >=2); use a source that lands on an empty
# inner pit. Start (7,1)? Instead: (0,1) empty target via (7,0) chain is complex;
# simplest: last seed into empty inner pit -> turn ends, no capture.
s = state({(1, 1): 2, (2, 2): 9, (2, 3): 9}, to_move=0)
ns = G.apply_move(s, "1,1")  # sows into (2,1)=1 (empty) then (3,1)=1 (empty)
assert ns.board[(2, 2)] == 9 and ns.board[(2, 3)] == 9, "empty landing never captures"


# ---------------------------------------------------------------------------
# 6. Multi-lap capture chain (relay into a capture).
# ---------------------------------------------------------------------------
# South (0,1)=3 [index0] sows into (1,1),(2,1),(3,1). Make (3,1) become 2
# (occupied inner col3) with opp col3 both filled -> capture, re-sow from (0,1).
s = state({(0, 1): 3, (3, 1): 1, (3, 2): 2, (3, 3): 2}, to_move=0)
before = total(s)
ns = G.apply_move(s, "0,1")
assert ns.board[(3, 2)] == 0 and ns.board[(3, 3)] == 0, "captured opp col 3"
assert total(ns) == before


# ---------------------------------------------------------------------------
# 7. Loss by no legal move (reached via apply_move).
# ---------------------------------------------------------------------------
# North is already reduced to <=1 per pit; South (who can never add to North's
# pits except by capturing them) plays a quiet move -> North then cannot move.
s = state({(0, 0): 2, (0, 2): 1, (3, 3): 1}, to_move=0)
assert not G.is_terminal(s), "South can still move"
ns = G.apply_move(s, "0,0")  # sows into own (0,1),(1,1); no capture
assert ns.to_move == 1
assert G._stuck(ns), "North has no pit with >=2 seeds"
assert G.is_terminal(ns) and G.legal_moves(ns) == []
assert G.returns(ns) == [1.0, -1.0], "the player who cannot move loses"


# ---------------------------------------------------------------------------
# 8. Serialization round-trips (JSON-able).
# ---------------------------------------------------------------------------
s = state({(0, 0): 7, (3, 1): 2, (5, 2): 9}, to_move=1, ply=13)
d1 = G.serialize(s)
d2 = G.serialize(G.deserialize(d1))
assert d1 == d2, "serialize must round-trip"
json.dumps(d1)


# ---------------------------------------------------------------------------
# 9. apply_move purity: never mutates the input state.
# ---------------------------------------------------------------------------
s = G.initial_state()
before = G.serialize(s)
_ = G.apply_move(s, G.legal_moves(s)[0])
assert G.serialize(s) == before, "apply_move mutated the input state"


# ---------------------------------------------------------------------------
# 10. Conformance: random games terminate, seeds always conserved (==64), and
#     returns are well-formed.
# ---------------------------------------------------------------------------
rng = random.Random(20260701)
for _ in range(40):
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s):
        assert total(s) == 64, "seeds not conserved (should always be 64)"
        moves = G.legal_moves(s)
        assert moves, "non-terminal state must have legal moves"
        s = G.apply_move(s, rng.choice(moves))
        steps += 1
        assert steps <= 2000, "game failed to terminate"
    assert total(s) == 64, "final seed count wrong"
    r = G.returns(s)
    assert len(r) == 2 and all(isinstance(x, float) for x in r)
    assert set(r) <= {-1.0, 0.0, 1.0}


print("SELFTEST OK")
sys.exit(0)
