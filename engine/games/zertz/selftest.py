"""ZERTZ correctness anchor -- pure stdlib, fast.

Run: PYTHONPATH=. python3 games/zertz/selftest.py

There is no published perft for ZERTZ; the anchor is a set of baked rule
assertions plus hand-built positions exercising each core rule:
  (1) a 37-ring hexhex (side 4) board whose ring set SHRINKS;
  (2) placement = put a pooled marble on a vacant ring, THEN remove a free ring;
  (3) capture = jump an adjacent marble of any colour to the empty ring beyond,
      banking it into the MOVER's reserve; captures are mandatory and CHAIN;
  (4) isolation = a fully-occupied cut-off ring group is claimed by the mover;
  (5) win = a winning captured set (3 of each, or 4W / 5G / 6B).
"""

import sys

from games.zertz.game import (
    Zertz, ZState, ALL_RINGS, POOL, _cell, _cid, DIRS,
)


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


G = Zertz()

# ---- (1) board: 37 rings, hexhex side 4 -----------------------------------
check(len(ALL_RINGS) == 37, "board must have 37 rings")
s0 = G.initial_state()
check(len(s0.rings) == 37, "initial board has 37 rings")
check(s0.pool == {"W": 6, "G": 8, "B": 10}, f"pool must be 6/8/10, got {s0.pool}")
check(sum(s0.reserve[0].values()) == 0 and sum(s0.reserve[1].values()) == 0,
      "reserves start empty")

# render uses polygons (shrinking board) + a pinned extent + neutral fills
r = G.render(s0)
check(r["board"]["type"] == "polygons", "render must use polygons for shrink")
check(len(r["board"]["cells"]) == 37, "render emits all 37 rings at start")
check("extent" in r["board"] and len(r["board"]["extent"]) == 4,
      "render pins a 4-tuple extent")

# ---- (2) placement = place a marble THEN remove a free ring ----------------
# On the full board, opening moves are placements (no captures possible).
opening = G.legal_moves(s0)
check(all("@" in m for m in opening), "opening moves are all placements")
check(any(m.startswith("W@") for m in opening)
      and any(m.startswith("B@") for m in opening),
      "all pooled colours offered at the opening")

# place a marble on a central ring -> same player must now remove a free ring
s1 = G.apply_move(s0, "W@0,0")
check(G.current_player(s1) == 0, "placement keeps the turn (to remove a ring)")
check(s1.pending_removal, "after placing, a ring-removal step is pending")
check(s1.pool["W"] == 5, "pool decremented after a white placement")
removals = G.legal_moves(s1)
check(removals and all(m.startswith("x") for m in removals),
      "removal step offers only ring removals")
# a free ring must be a vacant EDGE ring (e.g. a corner), never the centre
check("x0,0" not in removals, "the just-placed marble's ring is not free")
check("x3,0" in removals, "an outer corner ring is free")

# removing a ring shrinks the board to 36
s2 = G.apply_move(s1, "x3,0")
check(len(s2.rings) == 36, "removing a ring shrinks the board to 36")
check((3, 0) not in s2.rings, "the removed ring is gone")
check(G.current_player(s2) == 1, "turn passes after the ring removal")
# the renderer now omits the removed ring but keeps the full extent
r2 = G.render(s2)
check(len(r2["board"]["cells"]) == 36, "render drops the removed ring")
check(r2["board"]["extent"] == r["board"]["extent"],
      "extent stays pinned to the full board as it shrinks")

# ---- (3) capture: hand-built jump, mandatory + into mover's reserve --------
# Three rings in a line on the q-axis: marble at (0,0) jumps (1,0) to land (2,0).
cap = ZState(
    rings=ALL_RINGS,
    marbles={(0, 0): "W", (1, 0): "B"},
    to_move=0,
)
moves = G.legal_moves(cap)
check(all(">" in m for m in moves), "with a jump available, ONLY captures are legal")
check("0,0>2,0" in moves, "the straight jump 0,0>2,0 is offered")
after = G.apply_move(cap, "0,0>2,0")
check((2, 0) in after.marbles and (0, 0) not in after.marbles,
      "the jumping marble moved to the landing ring")
check((1, 0) not in after.marbles, "the jumped marble was removed from the board")
check(after.reserve[0]["B"] == 1, "the jumped black marble banked into MOVER's reserve")
check(G.current_player(after) == 1, "single jump (no chain) passes the turn")

# capture is MANDATORY: even with pool + vacant rings, no placement is offered
check(not any("@" in m for m in moves), "you may not place while a jump exists")

# ---- (3b) chained capture: one marble jumps twice, same turn ---------------
# Layout so (-2,0) jumps (-1,0)->(0,0), then (0,0) jumps (1,0)->(2,0).
chain = ZState(
    rings=ALL_RINGS,
    marbles={(-2, 0): "W", (-1, 0): "B", (1, 0): "G"},
    to_move=0,
)
c1 = G.apply_move(chain, "-2,0>0,0")
check(G.current_player(c1) == 0, "chain keeps the turn after the first jump")
check(c1.chain_from == "0,0", "chain continues from the landing ring")
cont = G.legal_moves(c1)
check(cont == ["0,0>2,0"], f"only the continuation jump is legal, got {cont}")
c2 = G.apply_move(c1, "0,0>2,0")
check(c2.reserve[0]["B"] == 1 and c2.reserve[0]["G"] == 1,
      "both jumped marbles banked over the chain")
check((2, 0) in c2.marbles, "the marble ended on the final landing ring")
check(G.current_player(c2) == 1, "turn passes once the chain is exhausted")

# ---- (4) isolation: removing a ring cuts off a fully-occupied group --------
# Build a tiny connected ring set: a "bridge" ring (4,-2) links a 2-ring island
# {(5,-3),(6,-3)} (both occupied) to the rest. Remove the bridge -> the island
# is fully occupied and cut off -> the mover claims both marbles.
# Use real board cells; choose a chain along the top edge.
# (5,-3),(6,-3) are valid (|q|,|r|,|q+r|<=3? 6,-3 -> q+r=3 ok).
iso_rings = set(ALL_RINGS)
# place a marble + pending removal state where removing (4,-2) isolates the pair
iso = ZState(
    rings=frozenset(iso_rings),
    marbles={(5, -3): "W", (6, -3): "B"},
    pool=dict(POOL),
    to_move=0,
    pending_removal=True,
)
# (5,-3)'s only board neighbours within the island+bridge: verify connectivity
# breaks when we remove the linking rings. Find a single ring whose removal
# isolates the occupied pair. We remove rings around them to force a cut.
# Simplify: directly assert the isolation resolver claims a fully-occupied
# disconnected component.
rings_small = frozenset({(5, -3), (6, -3)})   # an island, disconnected from nothing else
res = [{"W": 0, "G": 0, "B": 0}, {"W": 0, "G": 0, "B": 0}]
nr, nm = G._resolve_isolation(
    rings=frozenset(set(rings_small) | {(0, 0)}),   # two components: island + lone (0,0)
    marbles={(5, -3): "W", (6, -3): "B"},            # island fully occupied, (0,0) empty
    reserve=res, mover=0)
check(res[0]["W"] == 1 and res[0]["B"] == 1,
      "isolation: fully-occupied cut-off group claimed by the mover")
check((5, -3) not in nr and (6, -3) not in nr, "isolated rings removed")
check((0, 0) in nr, "the still-connected empty ring stays")

# a cut-off group with a VACANT ring is NOT captured
res2 = [{"W": 0, "G": 0, "B": 0}, {"W": 0, "G": 0, "B": 0}]
nr2, nm2 = G._resolve_isolation(
    rings=frozenset({(5, -3), (6, -3), (0, 0)}),
    marbles={(5, -3): "W"},        # island has a vacant ring (6,-3)
    reserve=res2, mover=0)
check(sum(res2[0].values()) == 0, "a cut-off group with a vacant ring isn't claimed")
check((5, -3) in nr2 and (6, -3) in nr2, "unclaimed island rings remain")

# ---- (4d) TEST D: isolation resolved on the PLACEMENT path ------------------
# Regression for the deferred-isolation bug: a marble placed on the LAST vacant
# ring of an already cut-off group must be claimed by the mover IMMEDIATELY in
# apply_move's placement branch -- not only in the ring-removal step.
# rings = {(0,0),(3,0),(3,-1)}, marbles {(0,0):W,(3,0):G}, mover 0 plays B@3,-1.
# {(3,0),(3,-1)} is adjacent ((3,0)+(0,-1)=(3,-1)) and disconnected from (0,0);
# placing B@3,-1 fills its last vacancy -> mover claims G + B, those rings go.
testD = ZState(
    rings=frozenset({(0, 0), (3, 0), (3, -1)}),
    marbles={(0, 0): "W", (3, 0): "G"},
    pool=dict(POOL),
    to_move=0,
)
d_after = G.apply_move(testD, "B@3,-1")
check(d_after.reserve[0] == {"W": 0, "G": 1, "B": 1},
      f"TEST D: placement-triggered isolation claims G+B into mover's reserve, "
      f"got {d_after.reserve[0]}")
check((3, 0) not in d_after.rings and (3, -1) not in d_after.rings,
      "TEST D: the now fully-occupied isolated rings were removed")
check((3, 0) not in d_after.marbles and (3, -1) not in d_after.marbles,
      "TEST D: the claimed marbles left the board")
check((0, 0) in d_after.rings and d_after.marbles.get((0, 0)) == "W",
      "TEST D: the still-connected ring/marble is untouched")
check(d_after.reserve[1] == {"W": 0, "G": 0, "B": 0},
      "TEST D: the opponent's reserve is unaffected")

# ---- (5) win: reach a winning set via apply_move ---------------------------
# Drive a real capture that completes 4 white captured -> player 0 wins.
win = ZState(
    rings=ALL_RINGS,
    marbles={(0, 0): "G", (1, 0): "W"},
    reserve=[{"W": 3, "G": 0, "B": 0}, {"W": 0, "G": 0, "B": 0}],
    to_move=0,
)
ws = G.apply_move(win, "0,0>2,0")          # jumps the white marble at (1,0)
check(ws.reserve[0]["W"] == 4, "fourth white captured")
check(G.is_terminal(ws), "4 white is terminal")
check(ws.winner == 0, "player 0 wins on 4 white")
check(G.returns(ws) == [1.0, -1.0], "returns reward the winner")

# triple-set win (3 of each) via a capture that completes it
win3 = ZState(
    rings=ALL_RINGS,
    marbles={(0, 0): "W", (1, 0): "B"},
    reserve=[{"W": 3, "G": 3, "B": 2}, {"W": 0, "G": 0, "B": 0}],
    to_move=0,
)
ws3 = G.apply_move(win3, "0,0>2,0")        # banks the 3rd black
check(ws3.winner == 0 and G.is_terminal(ws3), "3-of-each set wins")

# single-colour win sets are exactly 4W / 5G / 6B
from games.zertz.game import WIN_SINGLE
check(WIN_SINGLE == {"W": 4, "G": 5, "B": 6}, "win sets must be 4W/5G/6B")

# ---- serialization round-trips ---------------------------------------------
d = G.serialize(c2)
re = G.deserialize(d)
check(G.serialize(re) == d, "serialize round-trips")

print("SELFTEST OK")
sys.exit(0)
