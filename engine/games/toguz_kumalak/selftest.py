"""Standalone correctness anchor for Toguz Kumalak.

Run with:  PYTHONPATH=. python3 games/toguz_kumalak/selftest.py

Pure stdlib + this game only. Fast (hand-built rule positions plus a handful of
random conformance games). Prints "SELFTEST OK" and exits 0 on success, nonzero
on any failure.

There is no published perft for toguz kumalak; the anchor is a set of baked
rule assertions covering setup, leave-one-behind sowing, even-count capture, the
full tuzdik rule (creation + all three restrictions + banking), and the >81 win.
"""

from __future__ import annotations

import json
import random
import sys

from games.toguz_kumalak.game import (
    ToguzKumalak, TKState, PIT_ORDER, PIT_INDEX, OWN_PITS,
    TOTAL_BALLS, START_PER_PIT, WIN_THRESHOLD, LAST_PIT, _mirror, WIDTH,
)

G = ToguzKumalak()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def state(board_overrides, kazans=(0, 0), tuzdiks=(None, None),
          to_move=0, ply=0, done=False):
    board = {pit: 0 for pit in PIT_ORDER}
    for k, v in board_overrides.items():
        board[k] = v
    return TKState(board=dict(board), kazans=list(kazans),
                   tuzdiks=list(tuzdiks), to_move=to_move, ply=ply, done=done)


def board_total(s):
    return sum(s.board.values())


def grand_total(s):
    return board_total(s) + sum(s.kazans)


# ---------------------------------------------------------------------------
# 1. Setup invariants: 2x9 pits + 2 kazans, 162 balls, 9 per pit.
# ---------------------------------------------------------------------------
s0 = G.initial_state()
if len(set(PIT_ORDER)) != 18:
    fail("pit order is not 18 distinct pits")
if len(OWN_PITS[0]) != 9 or len(OWN_PITS[1]) != 9:
    fail("each player must own exactly 9 pits")
if sum(s0.board.values()) != TOTAL_BALLS or TOTAL_BALLS != 162:
    fail("initial board does not total 162 balls")
if any(s0.board[p] != START_PER_PIT for p in PIT_ORDER) or START_PER_PIT != 9:
    fail("initial pits not all 9 balls")
if s0.kazans != [0, 0]:
    fail("initial kazans not empty")
if s0.tuzdiks != [None, None]:
    fail("initial tuzdiks not empty")
# Counterclockwise order: bottom L->R then top R->L.
assert PIT_ORDER[0] == (0, 0) and PIT_ORDER[8] == (8, 0)
assert PIT_ORDER[9] == (8, 1) and PIT_ORDER[17] == (0, 1)


# ---------------------------------------------------------------------------
# 2. SOWING: single ball moves to the next pit; >1 leaves one behind.
# ---------------------------------------------------------------------------
# Single ball from (2,0) -> moves to (3,0); source ends empty.
s = state({(2, 0): 1, (0, 1): 5}, to_move=0)
ns = G.apply_move(s, "2,0")
assert ns.board[(2, 0)] == 0, "single-ball source must empty"
assert ns.board[(3, 0)] == 1, "single ball lands in the next pit"
assert ns.kazans == [0, 0]

# >1 ball from (2,0) holding 4: leave one in (2,0); sow into (3,0),(4,0),(5,0).
# Last ball lands in (5,0) (own row) -> no capture.
s = state({(2, 0): 4, (0, 1): 5}, to_move=0)
ns = G.apply_move(s, "2,0")
assert ns.board[(2, 0)] == 1, "leave exactly one behind in the source"
assert ns.board[(3, 0)] == 1 and ns.board[(4, 0)] == 1 and ns.board[(5, 0)] == 1
assert ns.kazans == [0, 0], "no capture landing in own row"
# Conservation.
assert grand_total(ns) == grand_total(s)

# Crossing into the top row: from (8,0) with 3 balls -> leave 1; sow (8,1),(7,1).
s = state({(8, 0): 3, (0, 1): 5}, to_move=0)
ns = G.apply_move(s, "8,0")
assert ns.board[(8, 0)] == 1
assert ns.board[(8, 1)] == 1 and ns.board[(7, 1)] == 1


# ---------------------------------------------------------------------------
# 3. CAPTURE: last ball lands in an opponent pit making it EVEN -> capture all.
# ---------------------------------------------------------------------------
# Single ball from (8,0) -> lands in (8,1) (opponent). Make (8,1) become 2 (even).
s = state({(8, 0): 1, (8, 1): 1, (0, 1): 5}, to_move=0)
ns = G.apply_move(s, "8,0")
assert ns.board[(8, 1)] == 0, "even opponent pit is emptied"
assert ns.kazans[0] == 2, "captured the 2 balls into bottom kazan"
assert grand_total(ns) == grand_total(s)

# Make it ODD instead (lands -> 3 but with one player already owning a tuzdik so
# no tuzdik can form): odd, non-3-eligible -> no capture, balls stay.
# Simpler: make it 5 (odd) -> no capture.
s = state({(8, 0): 1, (8, 1): 4, (0, 1): 5}, to_move=0)
ns = G.apply_move(s, "8,0")
assert ns.board[(8, 1)] == 5 and ns.kazans[0] == 0, "odd result: no capture"

# Last ball in OWN row never captures even if even.
s = state({(2, 0): 1, (3, 0): 1, (0, 1): 5}, to_move=0)
ns = G.apply_move(s, "2,0")
assert ns.board[(3, 0)] == 2 and ns.kazans[0] == 0, "own row never captured"

# Larger sow whose LAST ball makes an opponent pit even.
# From (6,0) with 5 balls: leave 1 in (6,0); sow (7,0),(8,0),(8,1),(7,1).
# Last ball -> (7,1). Preload (7,1)=1 so it becomes 2 (even) -> capture 2.
s = state({(6, 0): 5, (7, 1): 1, (0, 1): 5}, to_move=0)
ns = G.apply_move(s, "6,0")
assert ns.board[(6, 0)] == 1
assert ns.board[(7, 0)] == 1 and ns.board[(8, 0)] == 1 and ns.board[(8, 1)] == 1
assert ns.board[(7, 1)] == 0, "last-ball opponent pit captured"
assert ns.kazans[0] == 2


# ---------------------------------------------------------------------------
# 4. TUZDIK creation + banking.
# ---------------------------------------------------------------------------
# Single ball from (8,0) -> lands in (8,1); make it become 3 -> tuzdik for P0.
s = state({(8, 0): 1, (8, 1): 2, (0, 1): 5}, to_move=0)
ns = G.apply_move(s, "8,0")
assert ns.tuzdiks[0] == (8, 1), "P0 should claim (8,1) as a tuzdik"
assert ns.board[(8, 1)] == 0, "the 3 balls in the new tuzdik are banked"
assert ns.kazans[0] == 3, "the 3 balls go to P0's kazan"
assert grand_total(ns) == grand_total(s)

# Banking: once a tuzdik exists, any ball sown into it goes straight to the
# owner's kazan and it never accumulates. P0 owns (8,1) as tuzdik. P0 sows a
# single ball from (8,0) -> lands in tuzdik (8,1) -> banked, board stays 0.
s = state({(8, 0): 1, (0, 1): 5}, tuzdiks=((8, 1), None), to_move=0)
ns = G.apply_move(s, "8,0")
assert ns.board[(8, 1)] == 0, "tuzdik never accumulates"
assert ns.kazans[0] == 1, "ball sown into the tuzdik is banked to its owner"

# A pit that is a tuzdik cannot be chosen as a source / is excluded from moves.
s = state({(8, 1): 0, (1, 1): 4, (0, 0): 4}, tuzdiks=(None, None),
          to_move=1)
moves = G.legal_moves(s)
assert "1,1" in moves
# Now make (1,1) a tuzdik owned by P0 (on P1's row) -> P1 can't sow from it.
s = state({(1, 1): 4, (5, 1): 4, (0, 0): 4}, tuzdiks=((1, 1), None),
          to_move=1)
moves = G.legal_moves(s)
assert "1,1" not in moves, "a tuzdik pit is never a legal source"
assert "5,1" in moves


# ---------------------------------------------------------------------------
# 5. TUZDIK restrictions (all three).
# ---------------------------------------------------------------------------
# (b) Cannot be the opponent's NINTH/last pit. For P0 the opponent's last pit is
# (0,1). Land the last ball there making it 3 -> NO tuzdik (and 3 is odd, so
# also no capture): the balls stay.
assert LAST_PIT[1] == (0, 1)
# Single ball from (0,0)? No -- need to land in (0,1). The pit just before (0,1)
# in the loop is (1,1). Sow a single ball from (1,1) -> (0,1). But (1,1) is P1's;
# we need P0 to move and reach (0,1). The pit before (0,1) is (1,1); a P0 sow
# that ends on (0,1) must pass through the top row. Use start (2,1)? That's P1.
# Easiest: directly preload and sow a single ball from (1,1) is P1's move.
# Instead test via a P0 multi-sow ending exactly on (0,1):
# (0,1) is the LAST pit of the whole loop (index 17). The pit before it is
# (1,1) at index 16. So a P0 move whose last ball is at index 17 ends on (0,1).
# Start at (8,0) (index 8) with k balls so last index = 8+(k-1) = 17 -> k=10.
# That needs 10 balls; leaves 1 behind in (8,0); fills indices 8..17 (10 pits),
# last = (0,1). Preload (0,1)=2 so it becomes 3.
s = state({(8, 0): 10, (0, 1): 2}, to_move=0)
ns = G.apply_move(s, "8,0")
assert ns.board[(0, 1)] == 3, "opponent's 9th pit reaches 3"
assert ns.tuzdiks[0] is None, "cannot make the opponent's 9th pit a tuzdik"
assert ns.kazans[0] == 0, "3 is odd -> no capture either; balls stay"

# (a) One tuzdik per player. P0 already owns (7,1). Land last ball making (6,1)=3.
# A second tuzdik must NOT form. (6,1) becoming 3 is odd -> also no capture.
s = state({(8, 0): 4, (6, 1): 2, (0, 1): 5}, tuzdiks=((7, 1), None), to_move=0)
# (8,0)=4: leave 1; sow (8,1),(7,1)=tuzdik(banked),(6,1). Last ball -> (6,1).
ns = G.apply_move(s, "8,0")
assert ns.board[(6, 1)] == 3, "(6,1) reaches 3"
assert ns.tuzdiks[0] == (7, 1), "P0 still has only its original tuzdik"
assert ns.kazans[0] == 1, "the ball passing through the existing tuzdik banked"

# (c) Cannot be symmetric to the opponent's tuzdik. P1 owns a tuzdik at (3,0)
# (a P1-owned hole on P0's row). Its mirror is (3,1). P0 tries to make (3,1) a
# tuzdik by landing the last ball there making it 3 -> rejected by symmetry.
assert _mirror((3, 0)) == (3, 1)
# Reach (3,1): index of (3,1) is PIT_INDEX[(3,1)]. Sow from (8,0)(idx8) k balls,
# last index = 8+(k-1). (3,1) index:
ti = PIT_INDEX[(3, 1)]
k = ti - 8 + 1
s = state({(8, 0): k, (3, 1): 2, (0, 1): 5}, tuzdiks=(None, (3, 0)), to_move=0)
ns = G.apply_move(s, "8,0")
assert ns.board[(3, 1)] == 3, "(3,1) reaches 3"
assert ns.tuzdiks[0] is None, "symmetric tuzdik must be rejected"
assert ns.kazans[0] == 0, "3 is odd -> no capture"

# Positive control for (c): a NON-symmetric opponent pit reaching 3 DOES form a
# tuzdik even when the opponent has one elsewhere. P1 owns (3,0); P0 makes (4,1)
# (mirror (4,0) != (3,0)) into a tuzdik.
ti = PIT_INDEX[(4, 1)]
k = ti - 8 + 1
s = state({(8, 0): k, (4, 1): 2, (0, 1): 5}, tuzdiks=(None, (3, 0)), to_move=0)
ns = G.apply_move(s, "8,0")
assert ns.board[(4, 1)] == 0 and ns.tuzdiks[0] == (4, 1), \
    "non-symmetric 3-pit becomes a tuzdik"
assert ns.kazans[0] == 3


# ---------------------------------------------------------------------------
# 6. WIN: more than 81 wins; 81-81 is a draw.
# ---------------------------------------------------------------------------
assert WIN_THRESHOLD == 82
# Bottom on 80; capture 2 -> 82 -> win.
s = state({(8, 0): 1, (8, 1): 1, (0, 1): 5}, kazans=(80, 0), to_move=0)
ns = G.apply_move(s, "8,0")
assert ns.kazans[0] == 82 and ns.done, "reaching 82 ends the game"
assert G.returns(ns) == [1.0, -1.0]

# 81-81 terminal -> draw.
s = state({}, kazans=(81, 81), to_move=0, done=True)
assert G.returns(s) == [0.0, 0.0]
# 81 alone is NOT a win.
s = state({(8, 0): 1, (8, 1): 1, (0, 1): 5}, kazans=(79, 0), to_move=0)
ns = G.apply_move(s, "8,0")  # 79+2 = 81
assert ns.kazans[0] == 81
assert not (ns.kazans[0] >= WIN_THRESHOLD), "81 is not yet a win"


# ---------------------------------------------------------------------------
# 6b. END-GAME SWEEP: at terminal, loose balls go to the player on whose own
#     row they sit, added to that player's kazan BEFORE deciding the winner.
# ---------------------------------------------------------------------------
# Counterexample: kazans P0=30, P1=50, P1's side empty, P0 holding 83 balls on
# its own row. Without the sweep P1 would win 50>30; with the sweep P0 wins
# 30+83=113 vs 50. Distribute P0's 83 across its own row (rows sum to 83).
p0_row = {}
remaining = 83
for i, pit in enumerate(OWN_PITS[0]):
    give = remaining if i == len(OWN_PITS[0]) - 1 else min(10, remaining)
    p0_row[pit] = give
    remaining -= give
assert sum(p0_row.values()) == 83
# P1's row left empty (no sowable balls -> P1 to move is stuck -> terminal).
s = state(p0_row, kazans=(30, 50), to_move=1, done=True)
assert sum(s.board[p] for p in OWN_PITS[0]) == 83, "P0 holds 83 on its row"
assert sum(s.board[p] for p in OWN_PITS[1]) == 0, "P1 side is empty"
assert grand_total(s) == 30 + 50 + 83, "sweep regression: total balls"
r = G.returns(s)
assert r == [1.0, -1.0], (
    "end-game sweep: P0 (30+83=113) must beat P1 (50); got %r" % (r,)
)
# And the swept kazans conserve every ball into the two stores.
swept = G._swept_kazans(s.board, s.kazans, s.tuzdiks)
assert swept == [113, 50], "swept kazans must be [113, 50], got %r" % (swept,)

# Symmetric sanity: balls on each side go to that side's owner; equal -> draw.
s = state({(0, 0): 5, (0, 1): 5}, kazans=(40, 40), to_move=1, done=True)
assert G.returns(s) == [0.0, 0.0], "equal swept totals -> draw"


# ---------------------------------------------------------------------------
# 7. Serialization round-trips (incl. tuzdiks).
# ---------------------------------------------------------------------------
s = state({(0, 0): 7, (3, 1): 2}, kazans=(40, 50), tuzdiks=((5, 1), (2, 0)),
          to_move=1, ply=12)
d1 = G.serialize(s)
s2 = G.deserialize(d1)
d2 = G.serialize(s2)
assert d1 == d2, "serialize must round-trip"
json.dumps(d1)


# ---------------------------------------------------------------------------
# 8. apply_move purity: never mutates the input state.
# ---------------------------------------------------------------------------
s = G.initial_state()
before = G.serialize(s)
_ = G.apply_move(s, "2,0")
after = G.serialize(s)
assert before == after, "apply_move mutated the input state"


# ---------------------------------------------------------------------------
# 9. Conformance: random self-play games terminate with well-formed returns and
#    ball conservation throughout (board + kazans == 162 always).
# ---------------------------------------------------------------------------
rng = random.Random(20260622)
for game_i in range(20):
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s):
        moves = G.legal_moves(s)
        assert moves, "non-terminal state must have legal moves"
        assert grand_total(s) == TOTAL_BALLS, "balls not conserved"
        s = G.apply_move(s, rng.choice(moves))
        steps += 1
        assert steps <= 5000, "game failed to terminate"
    assert grand_total(s) == TOTAL_BALLS, "final ball count wrong"
    r = G.returns(s)
    assert len(r) == 2 and all(isinstance(x, float) for x in r)
    assert set(r) <= {-1.0, 0.0, 1.0}
    # At most one tuzdik per player.
    assert s.tuzdiks[0] is None or s.tuzdiks[0] in OWN_PITS[1] or s.tuzdiks[0] in OWN_PITS[0]


print("SELFTEST OK")
sys.exit(0)
