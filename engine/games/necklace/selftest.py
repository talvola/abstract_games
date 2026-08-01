#!/usr/bin/env python3
"""Correctness anchors for Necklace (Mark Steere & Luis Bolanos Mures, 2024).

Pure stdlib.  The rule sheet (marksteeregames.com/Necklace_rules.pdf, md5
43183b5648e896bbe07e168ae0fec4fd, ModDate 2024-03-30 17:33:21 PDT) has three
figures and all three are transcribed here from the 600dpi render of the
Illustrator artwork (disc centroids extracted by blob analysis, then snapped to
the 9x9 lattice - not eyeballed):

  FIGURE 1  "Red has won": a 9x9 position, 13 red vs 12 blue stones (Red has
            just moved), the frame RED on top and bottom / BLUE on left and
            right, and a red chain running from the top row to the bottom row.
            This figure is the GROUND TRUTH OUTSIDE THE ENGINE for the
            seat<->edge mapping, and it is a real discriminator: under the
            TRANSPOSED reading of the board NEITHER colour connects, so a
            transposed engine cannot pass it.
  FIGURE 2  the two crosscut formations (both diagonal orientations).
  FIGURE 3  a 9x9 position with a green dot on an illegal placement.  The dot
            sits on the BOTTOM EDGE and filling it strands the empty group
            {(3,7),(4,6),(4,7),(5,7)} - which is what the assertion below pins;
            note that (2,7) is a RED stone and (3,6) a BLUE one in this very
            figure, so an "empty group" naming them would be self-contradictory.
            The figure's premises are asserted too
            (14 vs 14 stones, the position itself crosscut-free and with no
            stranded empty region), because a mis-transcribed board satisfies
            every assertion built on it.

ANCHOR DISCRIMINATING POWER (measured, not assumed; see the report):

  * Figure 2 alone kills only 5 of 9 enumerated wrong crosscut readings - it is
    blind to every OVER-permissive variant (e.g. "only one orthogonal partner
    need be an enemy"), because those fire on the printed formations too.  The
    full illegal-placement SETS of Figure 3 kill 9 of 9, so both are asserted.
  * Figure 3 kills 6 of 7 enumerated wrong enclosure readings, and is BLIND to
    exactly the one this package originally shipped: reusing a single `seen`
    set across the four floods of `encloses`.  That bug is caught only by
    cross-checking the local predicate against the whole-board recomputation
    `enclosed_regions`, which is therefore done at EVERY empty point of EVERY
    position the random sweep visits.

The other anchors: the two lemmas of the drawlessness proof, tested on
CONSTRUCTED inputs (a draw is unreachable, so random play can never exercise
them); exhaustive solves of the 2x2 and 3x3 boards; the serialize round-trip
compared as STATE OBJECTS over a whole game; render bounds at every offered
board size from a far-corner position; and the ply bound.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json                                                     # noqa: E402
import random                                                   # noqa: E402
from dataclasses import replace                                 # noqa: E402
from games.necklace.game import (                               # noqa: E402
    BLUE, RED, Necklace, NecklaceState, connection_path, connects,
    creates_crosscut, crosscuts_on_board, enclosed_regions, encloses, is_edge,
    max_plies, placements,
)

G = Necklace()
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)
        # A broken rule fails inside the random sweep on nearly every ply; bail
        # out rather than spend minutes printing the same failure.  No effect on
        # a passing run.
        if len(FAILS) > 12:
            print("FAILED: %d (bailing out)" % len(FAILS))
            sys.exit(1)


def board_of(red, blue):
    bd = {p: RED for p in red}
    bd.update({p: BLUE for p in blue})
    return bd


N = 9   # all three figures are 9x9

# --------------------------------------------------------------------------
# FIGURE 1 - "Red has won"
# --------------------------------------------------------------------------
FIG1_RED = [(5, 0), (5, 1), (3, 2), (4, 2), (5, 2), (3, 3), (4, 3), (3, 4),
            (3, 5), (3, 6), (3, 7), (4, 7), (4, 8)]
FIG1_BLUE = [(0, 4), (1, 4), (2, 4), (6, 4), (7, 4), (8, 4), (2, 5), (4, 5),
             (5, 5), (6, 5), (6, 7), (7, 7)]
FIG1 = board_of(FIG1_RED, FIG1_BLUE)

# premises of the figure ---------------------------------------------------
check(len(FIG1_RED) == 13 and len(FIG1_BLUE) == 12,
      "Figure 1 has 13 red and 12 blue stones (Red moved first and has just moved)")
check(len(FIG1) == 25, "Figure 1's 25 stones sit on 25 distinct points")
check(crosscuts_on_board(FIG1, N) == [],
      "Figure 1 is a legal position: no crosscut anywhere")
check(enclosed_regions(FIG1, N) == [],
      "Figure 1 is a legal position: every empty region touches an edge")

# the win itself -----------------------------------------------------------
check(connects(FIG1, RED, N), "Figure 1: Red connects the top and bottom rows")
check(not connects(FIG1, BLUE, N), "Figure 1: Blue does NOT connect")
path = connection_path(FIG1, RED, N)
check(path and path[0][1] == 0 and path[-1][1] == N - 1,
      "Figure 1: the printed red chain runs from row 0 to row 8")
check(all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(path, path[1:])),
      "Figure 1: the red chain is ORTHOGONALLY connected (no diagonal links)")
# ... and diagonal links really are worthless: the red stones (5,2) and (4,3)
# are diagonally adjacent, so an 8-connected engine would find a shorter chain.
check(len(path) == 12, "Figure 1: the orthogonal red chain is 12 stones long")

# the figure DISCRIMINATES the transpose (it is not a symmetry of the game once
# the goal edges are coloured) - this is what pins the seat<->edge mapping.
FIG1_T = {(r, c): v for (c, r), v in FIG1.items()}
check(not connects(FIG1_T, RED, N) and not connects(FIG1_T, BLUE, N),
      "Figure 1 transposed: NEITHER colour connects, so the figure fixes the orientation")

# --------------------------------------------------------------------------
# FIGURE 2 - the two crosscut formations
# --------------------------------------------------------------------------
FIG2 = {(6, 2): RED, (5, 2): BLUE, (5, 3): RED, (6, 3): BLUE,      # one diagonal
        (2, 5): RED, (3, 5): BLUE, (2, 6): BLUE, (3, 6): RED}      # the other
check(sorted(crosscuts_on_board(FIG2, N)) == [(2, 5), (5, 2)],
      "Figure 2 prints exactly two crosscuts, one per diagonal orientation")
check({(FIG2[(6, 2)], FIG2[(5, 3)]), (FIG2[(2, 5)], FIG2[(3, 6)])} == {(RED, RED)},
      "Figure 2's two red pairs lie on the two OPPOSITE diagonals")
for cell, who in FIG2.items():
    rest = {k: v for k, v in FIG2.items() if k != cell}
    check(creates_crosscut(rest, cell[0], cell[1], who),
          f"Figure 2: replaying the {['red', 'blue'][who]} stone at {cell} completes a crosscut")
    # ...and the OTHER colour on that same point does not
    check(not creates_crosscut(rest, cell[0], cell[1], 1 - who),
          f"Figure 2: the opposite colour on {cell} completes nothing")

# The crosscut ban is COLOUR-BLIND in the sense that it is symmetric: swapping
# every colour in Figure 2 leaves two crosscuts.
FIG2_SWAP = {k: 1 - v for k, v in FIG2.items()}
check(sorted(crosscuts_on_board(FIG2_SWAP, N)) == [(2, 5), (5, 2)],
      "Figure 2 colour-reversed is still two crosscuts")

# A crosscut needs FOUR stones: any 2x2 with a hole is not one.
for hole in FIG2:
    rest = {k: v for k, v in FIG2.items() if k != hole}
    check(len(crosscuts_on_board(rest, N)) == 1,
          f"removing {hole} destroys exactly one of the two crosscuts")

# --------------------------------------------------------------------------
# FIGURE 3 - the illegal placement (green dot)
# --------------------------------------------------------------------------
FIG3_RED = [(3, 1), (6, 1), (2, 2), (2, 3), (3, 3), (6, 3), (1, 4), (6, 4),
            (1, 5), (2, 5), (5, 5), (6, 6), (2, 7), (6, 7)]
FIG3_BLUE = [(1, 2), (5, 3), (2, 4), (5, 4), (3, 5), (4, 5), (2, 6), (3, 6),
             (5, 6), (1, 7), (3, 8), (4, 8), (6, 8), (7, 8)]
FIG3 = board_of(FIG3_RED, FIG3_BLUE)
GREEN = (5, 8)

# premises -----------------------------------------------------------------
check(len(FIG3_RED) == 14 and len(FIG3_BLUE) == 14,
      "Figure 3 has 14 stones of each colour (so it is Red's turn)")
check(len(FIG3) == 28, "Figure 3's 28 stones sit on 28 distinct points")
check(crosscuts_on_board(FIG3, N) == [], "Figure 3 is a legal position: no crosscut")
check(enclosed_regions(FIG3, N) == [],
      "Figure 3 is a legal position: every empty region touches an edge")
check(GREEN not in FIG3, "Figure 3's green dot marks an UNOCCUPIED point")
check(is_edge(N, *GREEN), "Figure 3's green dot is itself on the bottom edge")

# the illegality it illustrates -------------------------------------------
check(encloses(FIG3, N, *GREEN),
      "Figure 3: the green dot would strand an empty group with no edge point")
check(not creates_crosscut(FIG3, GREEN[0], GREEN[1], RED)
      and not creates_crosscut(FIG3, GREEN[0], GREEN[1], BLUE),
      "Figure 3: the green dot is illegal ONLY by the empty-region rule")
after = dict(FIG3)
after[GREEN] = RED
check(enclosed_regions(after, N) == [((3, 7), (4, 6), (4, 7), (5, 7))],
      "Figure 3: the stranded group is exactly {(3,7),(4,6),(4,7),(5,7)}")
after[GREEN] = BLUE
check(enclosed_regions(after, N) == [((3, 7), (4, 6), (4, 7), (5, 7))],
      "Figure 3: the empty-region rule is colour-blind - blue strands the same group")

# The figure kills the 8-adjacency reading: (3,7) is diagonally adjacent to the
# empty bottom-edge point (2,8), so an 8-connected empty-region rule would call
# the green dot LEGAL.
check((2, 8) not in FIG3 and is_edge(N, 2, 8),
      "Figure 3 premise: (2,8) is an empty bottom-edge point diagonally touching (3,7)")

# The full illegal-placement sets, for BOTH colours.  These (not the single
# green dot) are what kill every enumerated wrong crosscut reading.
EMPTY3 = [(c, r) for r in range(N) for c in range(N) if (c, r) not in FIG3]
check(len(EMPTY3) == 53, "Figure 3 leaves 53 empty points")
FIG3_ILLEGAL = {
    RED: {(0, 3), (0, 6), (1, 6), (3, 4), (4, 2), (4, 3), (4, 4), (4, 6),
          (4, 7), (5, 7), (5, 8), (7, 5)},
    BLUE: {(0, 3), (0, 6), (1, 3), (4, 2), (4, 3), (4, 4), (4, 7), (5, 7),
           (5, 8), (6, 5), (7, 5)},
}
for who in (RED, BLUE):
    got = {p for p in EMPTY3 if p not in placements(FIG3, N, who)}
    check(got == FIG3_ILLEGAL[who],
          f"Figure 3: illegal placements for {['red', 'blue'][who]} = {sorted(FIG3_ILLEGAL[who])}, got {sorted(got)}")
# nine of those are enclosure-illegal for BOTH colours; the rest are crosscuts
BOTH = FIG3_ILLEGAL[RED] & FIG3_ILLEGAL[BLUE]
check({p for p in EMPTY3 if encloses(FIG3, N, *p)} == BOTH,
      "Figure 3: the colour-independent illegal points are exactly the enclosing ones")

# --------------------------------------------------------------------------
# the 5x5 diagram printed in rules.md (so the documentation cannot rot)
# --------------------------------------------------------------------------
DOC = board_of([(3, 2), (2, 3)], [(4, 3)])
check(crosscuts_on_board(DOC, 5) == [] and enclosed_regions(DOC, 5) == [],
      "the rules.md 5x5 diagram is a legal position")
check(encloses(DOC, 5, 3, 4), "rules.md diagram: (3,4) is an illegal placement")
check(not creates_crosscut(DOC, 3, 4, RED) and not creates_crosscut(DOC, 3, 4, BLUE),
      "rules.md diagram: (3,4) is illegal ONLY by the empty-region rule")
probe = dict(DOC)
probe[(3, 4)] = BLUE
check(enclosed_regions(probe, 5) == [((3, 3),)],
      "rules.md diagram: playing (3,4) seals the single point (3,3)")
check({p for p in ((c, r) for r in range(5) for c in range(5)) if p not in DOC
       and encloses(DOC, 5, *p)} == {(3, 4)},
      "rules.md diagram: (3,4) is the ONLY enclosing placement on that board")

# --------------------------------------------------------------------------
# the two lemmas of the drawlessness proof, on CONSTRUCTED inputs
# --------------------------------------------------------------------------
# LEMMA A.  If placing RED at p creates a crosscut AND placing BLUE at p creates
# a crosscut, then all four orthogonal neighbours of p are occupied.  (Proof:
# the red block forces some horizontal neighbour ENEMY=blue and the blue block
# forces a horizontal neighbour ENEMY=red, so the two 2x2s use OPPOSITE
# diagonals; likewise vertically.)  Exhaustive over all 3^8 colourings of the
# 8 neighbours of an interior point.
COLOURS = (None, RED, BLUE)
NBRS = [(dc, dr) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dc, dr) != (0, 0)]
both_blocked = 0
lemma_a_ok = True
for code in range(3 ** 8):
    bd = {}
    x = code
    for (dc, dr) in NBRS:
        col = COLOURS[x % 3]
        x //= 3
        if col is not None:
            bd[(5 + dc, 5 + dr)] = col
    if creates_crosscut(bd, 5, 5, RED) and creates_crosscut(bd, 5, 5, BLUE):
        both_blocked += 1
        if any((5 + dc, 5 + dr) not in bd for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            lemma_a_ok = False
check(lemma_a_ok,
      "LEMMA A: a point blocked for BOTH colours has all four orthogonal neighbours occupied")
check(both_blocked > 0,
      f"LEMMA A is not vacuous: {both_blocked} of 6561 neighbourhoods block both colours")

# LEMMA A, edge form (also EXHAUSTIVE).  On the edge of the board the two
# candidate 2x2 areas share their inward neighbour, which the red block wants
# blue and the blue block wants red, so no EDGE point can ever be blocked for
# both colours.  Enumerated by masking the off-board neighbours to empty: four
# side orientations (3^5 colourings each) and four corners (3^3 each).
edge_both = 0
edge_cases = 0
OFFBOARD = [
    [(dc, dr) for dc, dr in NBRS if dr == -1],                       # top row
    [(dc, dr) for dc, dr in NBRS if dr == 1],                        # bottom row
    [(dc, dr) for dc, dr in NBRS if dc == -1],                       # left column
    [(dc, dr) for dc, dr in NBRS if dc == 1],                        # right column
    [(dc, dr) for dc, dr in NBRS if dr == -1 or dc == -1],           # top-left corner
    [(dc, dr) for dc, dr in NBRS if dr == -1 or dc == 1],            # top-right
    [(dc, dr) for dc, dr in NBRS if dr == 1 or dc == -1],            # bottom-left
    [(dc, dr) for dc, dr in NBRS if dr == 1 or dc == 1],             # bottom-right
]
for missing in OFFBOARD:
    live = [d for d in NBRS if d not in missing]
    for code in range(3 ** len(live)):
        bd = {}
        x = code
        for (dc, dr) in live:
            col = COLOURS[x % 3]
            x //= 3
            if col is not None:
                bd[(5 + dc, 5 + dr)] = col
        edge_cases += 1
        if creates_crosscut(bd, 5, 5, RED) and creates_crosscut(bd, 5, 5, BLUE):
            edge_both += 1
check(edge_both == 0,
      f"LEMMA A (edge form): no edge point is ever blocked for both colours ({edge_both} found)")
check(edge_cases == 4 * 3 ** 5 + 4 * 3 ** 3,
      f"LEMMA A (edge form) enumerated all {4 * 3 ** 5 + 4 * 3 ** 3} edge/corner neighbourhoods, got {edge_cases}")

# LEMMA B (COLOUR-INDEPENDENT, so this enumeration over all 2^16 OCCUPANCY
# patterns of the 4x4 board is exhaustive: neither `encloses` nor
# `enclosed_regions` ever reads a stone's colour).  In any legal non-full
# position some empty point is enclosure-LEGAL - take a leaf of a spanning tree
# of an empty region rooted at one of its edge points.
#
# Stronger, and still colour-free: some enclosure-legal point is either NOT an
# isolated empty point or IS on the edge.  By Lemma A a point can be blocked
# for both colours only when all four of its orthogonal neighbours are
# occupied, and by Lemma A's edge form never when it is on the edge - so such a
# point is playable by at least one colour WHATEVER the colouring.  Hence no
# legal non-full position is stuck, for any assignment of colours.
lemma_b_bad = 0
lemma_b_seen = 0
never_stuck_bad = 0
stuck = 0
colour_checked = 0
for mask in range(1 << 16):
    occ = [(i % 4, i // 4) for i in range(16) if mask >> i & 1]
    if len(occ) == 16:
        continue
    bd = {p: RED for p in occ}            # colour is irrelevant to both lemmas
    if enclosed_regions(bd, 4):
        continue                          # not a position the rules can produce
    lemma_b_seen += 1
    free = [(c, r) for r in range(4) for c in range(4) if (c, r) not in bd]
    legal = [p for p in free if not encloses(bd, 4, *p)]
    if not legal:
        lemma_b_bad += 1
    elif not any(is_edge(4, *p) or any((p[0] + dc, p[1] + dr) not in bd
                                       and 0 <= p[0] + dc < 4 and 0 <= p[1] + dr < 4
                                       for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                 for p in legal):
        never_stuck_bad += 1
    # ... and the colour-AWARE form through `placements` itself, on the
    # near-full positions where a stall could plausibly arise (a belt-and-braces
    # cross-check that the real legality path agrees with the two lemmas).
    if len(free) <= 8:
        cbd = {p: RED if (p[0] * 7 + p[1] * 3 + mask) % 2 else BLUE for p in occ}
        if not crosscuts_on_board(cbd, 4):
            colour_checked += 1
            if not placements(cbd, 4, RED) and not placements(cbd, 4, BLUE):
                stuck += 1
check(lemma_b_bad == 0,
      f"LEMMA B: every legal non-full 4x4 position has an enclosure-legal point ({lemma_b_bad} counterexamples)")
check(never_stuck_bad == 0,
      f"no legal non-full 4x4 position can be stuck under ANY colouring ({never_stuck_bad} counterexamples)")
check(lemma_b_seen > 40000,
      f"LEMMA B covered {lemma_b_seen} legal non-full 4x4 occupancy patterns")
check(stuck == 0,
      f"no near-full legal 4x4 position leaves BOTH players with no placement ({stuck} found)")
check(colour_checked > 2000,
      f"the colour-aware stall check ran on {colour_checked} near-full 4x4 positions")

# --------------------------------------------------------------------------
# exhaustive solves of the smallest boards
# --------------------------------------------------------------------------
def solve(size):
    memo = {}
    seen = {"draws": 0, "skips": 0, "stalled": 0, "full": 0}

    def rec(s):
        if G.is_terminal(s):
            if s.winner is None:
                seen["draws"] += 1
            if s.stalled:
                seen["stalled"] += 1
            if len(s.board) == size * size:
                seen["full"] += 1
            return G.returns(s)[0]
        key = (frozenset(s.board.items()), s.to_move)
        if key in memo:
            return memo[key]
        me = s.to_move
        best = None
        for mv in G.legal_moves(s):
            nxt = G.apply_move(s, mv)
            if nxt.skips > s.skips:
                seen["skips"] += 1
            v = rec(nxt)
            if best is None or (v > best if me == RED else v < best):
                best = v
        memo[key] = best
        return best

    return rec(G.initial_state(options={"size": size})), seen, len(memo)


for size, want in ((2, 1.0), (3, 1.0)):
    val, seen, nodes = solve(size)
    check(val == want,
          f"{size}x{size} solves to {want:+.0f} for Red (first player), got {val:+.0f}")
    check(seen["draws"] == 0 and seen["stalled"] == 0,
          f"{size}x{size}: no terminal is a draw or a stall ({seen})")
    check(seen["skips"] > 0,
          f"{size}x{size}: the skip rule really fires ({seen['skips']} skip events)")

# --------------------------------------------------------------------------
# random-play sweep: invariants, predicate cross-check, termination
# --------------------------------------------------------------------------
rng = random.Random(20240330)
games = 0
skip_games = 0
cross_checks = 0
full_boards = 0
draws = 0
for size, ngames, deep in ((5, 24, True), (7, 12, True), (9, 6, False), (11, 3, False)):
    for _ in range(ngames):
        s = G.initial_state(options={"size": size})
        games += 1
        prev_mover = None
        while not G.is_terminal(s):
            mover = s.to_move
            moves = G.legal_moves(s)
            check(moves, "a non-terminal state always has a legal move")
            # the two whole-board invariants
            check(crosscuts_on_board(s.board, size) == [],
                  "no crosscut is ever present on the board")
            check(enclosed_regions(s.board, size) == [],
                  "no empty region is ever stranded")
            # Local predicate vs whole-board recomputation, at EVERY empty
            # point.  This is the only check that sees the shared-`seen` flood
            # bug (Figure 3 does not); the mechanism is size-independent, so it
            # runs on the two smaller sizes where it is exhaustive and cheap.
            if deep:
                for r in range(size):
                    for c in range(size):
                        if (c, r) in s.board:
                            continue
                        probe = dict(s.board)
                        probe[(c, r)] = RED
                        cross_checks += 1
                        check(encloses(s.board, size, c, r) == bool(enclosed_regions(probe, size)),
                              f"encloses({c},{r}) disagrees with the whole-board recomputation")
            # every offered move is genuinely legal, and nothing legal is missing
            want = {f"{c},{r}" for (c, r) in placements(s.board, size, mover)}
            check(set(moves) == want, "legal_moves == placements for the player to move")
            s = G.apply_move(s, rng.choice(moves))
            check(s.ply <= max_plies(size), "ply count stays within max_plies(size)")
            prev_mover = mover
        check(s.winner is not None, "every game ends with a winner")
        if s.winner is None:
            draws += 1
        check(connects(s.board, s.winner, size), "the winner really connects their edges")
        check(not connects(s.board, 1 - s.winner, size), "the loser does not connect")
        check(s.winner == prev_mover, "the winner is the player who placed the last stone")
        check(not s.stalled, "no game ever ends stalled")
        if s.skips:
            skip_games += 1
        if len(s.board) == size * size:
            full_boards += 1
check(draws == 0, f"the random sweep found {draws} draws (expected 0)")
check(skip_games > 0, f"the random sweep exercised the skip rule ({skip_games}/{games} games)")
check(cross_checks > 10000,
      f"the encloses/enclosed_regions cross-check ran on {cross_checks} points")

# --------------------------------------------------------------------------
# a decisive result outranks the skip / stall bookkeeping
# --------------------------------------------------------------------------
# 3x3: 1,0 / 0,0 / 1,1 / 0,1 / 1,2  -> Red joins rows 0..2 down column 1.
s = G.initial_state(options={"size": 3})
for mv in ("1,0", "0,0", "1,1", "0,1", "1,2"):
    check(mv in G.legal_moves(s), f"{mv} is legal in the 3x3 win line")
    s = G.apply_move(s, mv)
check(s.winner == RED and G.is_terminal(s), "Red wins the constructed 3x3 line")
check(G.returns(s) == [1.0, -1.0], "Red's win scores [+1,-1]")
for poisoned in (replace(s, skips=10 ** 9), replace(s, stalled=True),
                 replace(s, ply=10 ** 9), replace(s, skips=7, stalled=True)):
    check(G.is_terminal(poisoned) and G.returns(poisoned) == [1.0, -1.0],
          "a decisive result outranks the skip / stall counters")
    check(G.render(poisoned)["caption"].startswith("Red"),
          "the caption still announces the winner with the counters tripped")
# and the stall branch is real code, not a fabricated tiebreak
stalled = NecklaceState(size=3, board={}, stalled=True)
check(G.is_terminal(stalled) and G.returns(stalled) == [0.0, 0.0],
      "a genuine double-stall is an honest DRAW (unreachable, but honest)")

# The stall REACHED THROUGH apply_move, so the branch is exercised end to end.
# The position below MUST violate restriction 2 - that is exactly what the
# drawlessness proof says: the empty point (1,1) is interior with all four
# orthogonal neighbours occupied, which is the only way a point can be blocked
# for both colours, and no legal game can ever produce it.  The one playable
# point (3,0) is a corner whose own region is a single edge point, so filling
# it is legal; afterwards nobody can move and nobody has connected.
DEAD = board_of([(0, 0), (0, 2), (0, 3), (1, 2), (2, 0), (2, 1)],
                [(0, 1), (1, 0), (1, 3), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3)])
check(enclosed_regions(DEAD, 4) == [((1, 1),)],
      "the constructed dead position violates restriction 2 at (1,1) - as the proof requires")
check(crosscuts_on_board(DEAD, 4) == [], "the constructed dead position has no crosscut")
check(not connects(DEAD, RED, 4) and not connects(DEAD, BLUE, 4),
      "nobody is connected in the constructed dead position")
check(creates_crosscut(DEAD, 1, 1, RED) and creates_crosscut(DEAD, 1, 1, BLUE),
      "(1,1) is crosscut-blocked for BOTH colours")
dead = NecklaceState(size=4, board=dict(DEAD), to_move=RED, ply=len(DEAD))
check(G.legal_moves(dead) == ["3,0"], f"only 3,0 is playable, got {G.legal_moves(dead)}")
after_dead = G.apply_move(dead, "3,0")
check(after_dead.stalled and after_dead.winner is None,
      "playing the last free point leaves BOTH players stuck")
check(G.is_terminal(after_dead) and G.returns(after_dead) == [0.0, 0.0],
      "a double-stall reached through apply_move scores an honest 0-0 draw")
check(G.render(after_dead)["caption"].startswith("Draw"),
      "the draw is captioned as a draw, not as a win for either side")
check(G.describe_move(dead, "3,0").endswith("(both stuck)"),
      "describe_move marks the placement that stalls the game")

# --------------------------------------------------------------------------
# seat <-> edge mapping, pinned to Figure 1's printed frame
# --------------------------------------------------------------------------
# The artwork prints RED bars on the TOP and BOTTOM and BLUE bars on the LEFT
# and RIGHT, and the prose says play starts with Red.  So the FIRST player must
# own the top/bottom edges in render(), and must be the winner of Figure 1.
fresh = G.initial_state(options={"size": N})
check(G.current_player(fresh) == RED, "Red (seat 0) moves first, per the sheet")
spec = G.render(fresh)
e = spec["board"]["edges"]
check(e["top"] == e["bottom"] == G.current_player(fresh),
      "the first player owns the TOP and BOTTOM edges, as printed in Figure 1")
check(e["left"] == e["right"] == 1 - G.current_player(fresh),
      "the second player owns the LEFT and RIGHT edges")
# Figure 1's winner is the top/bottom player, reached through apply_move
fig1_minus = {k: v for k, v in FIG1.items() if k != (5, 0)}
check(crosscuts_on_board(fig1_minus, N) == [] and enclosed_regions(fig1_minus, N) == [],
      "Figure 1 minus its top stone is still a legal position")
st = NecklaceState(size=N, board=fig1_minus, to_move=RED, ply=len(fig1_minus))
check("5,0" in G.legal_moves(st), "Red may replay Figure 1's top stone")
won = G.apply_move(st, "5,0")
check(won.winner == e["top"], "the winner of Figure 1 is the TOP/BOTTOM-edge player")
check(G.render(won)["caption"].startswith("Red"),
      "the caption names that player 'Red', matching the figure's red frame")
check(G.describe_move(st, "5,0") == "f1#", "describe_move marks the winning placement")
# the winning chain is highlighted, and the last-move marker survives on the
# point it shares with the chain (Board.jsx keys highlights by cell)
spec_won = G.render(won)
kinds = {}
for h in spec_won["highlights"]:
    kinds[h["cell"]] = h["kind"]
check(set(h["kind"] for h in spec_won["highlights"]) <= {"goal", "last-move"},
      "render only uses highlight kinds Board.jsx actually draws")
check(kinds.get("5,0") == "last-move",
      "the last-move marker outranks the winning-chain marker on their shared point")
check(sum(1 for k in kinds.values() if k == "goal") == len(path) - 1,
      "every other point of the winning chain is marked 'goal'")
for cid in kinds:
    c, r = (int(x) for x in cid.split(","))
    check(won.board.get((c, r)) == won.winner, f"highlighted point {cid} holds a winner's stone")

# --------------------------------------------------------------------------
# serialize / deserialize - compared as STATE OBJECTS, over a whole game
# --------------------------------------------------------------------------
KEYS = {"size", "board", "to_move", "last", "winner", "stalled", "ply", "skips"}
rng = random.Random(5)
covered = set()
for _ in range(12):
    s = G.initial_state(options={"size": 7})
    while True:
        d = G.serialize(s)
        check(set(d) == KEYS, f"serialize emits exactly {sorted(KEYS)}, got {sorted(d)}")
        json.dumps(d)
        check(G.deserialize(d) == s, "deserialize(serialize(s)) == s (STATE comparison)")
        check(G.serialize(G.deserialize(d)) == d, "serialize round-trips")
        covered.add(("last", s.last is None))
        covered.add(("winner", s.winner is None))
        covered.add(("skips", s.skips > 0))
        covered.add(("stalled", s.stalled))
        covered.add(("board", len(s.board) == 0))
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
for field in ("last", "winner", "skips", "board"):
    check((field, True) in covered and (field, False) in covered,
          f"the round-trip sweep covered both shapes of `{field}`")
# a dropped field must be caught: this is the mutation the STATE comparison sees
d = G.serialize(G.initial_state(options={"size": 7}))
for key in ("skips", "stalled", "last", "winner"):
    trimmed = {k: v for k, v in d.items() if k != key}
    check(set(G.serialize(G.deserialize(trimmed))) == KEYS,
          f"deserialize defaults a missing `{key}` (so the key-set assertion is what guards it)")

# --------------------------------------------------------------------------
# render bounds at EVERY offered board size, from a far-corner position
# --------------------------------------------------------------------------
man = json.loads((Path(__file__).resolve().parent / "manifest.json").read_text())
sizes = man["options"]["size"]["choices"]
check(man["options"]["size"]["default"] in sizes, "the default size is one of the choices")
check(G.initial_state().size == man["options"]["size"]["default"],
      f"initial_state() with no options uses the manifest default "
      f"({man['options']['size']['default']}), got {G.initial_state().size}")
for size in sizes:
    st = G.initial_state(options={"size": size})
    for cell in ((0, 0), (size - 1, size - 1), (size - 1, 0), (0, size - 1)):
        mv = f"{cell[0]},{cell[1]}"
        check(mv in G.legal_moves(st), f"corner {mv} is legal on the {size}x{size} board")
        st = G.apply_move(st, mv)
    spec = G.render(st)
    b = spec["board"]
    check(b["type"] == "square", "square board")
    check(b["width"] == size and b["height"] == size,
          f"render declares {size}x{size}, got {b['width']}x{b['height']}")
    check(set(b["edges"]) == {"top", "bottom", "left", "right"}, "all four edges coloured")
    check(b["edges"]["top"] == b["edges"]["bottom"] == RED
          and b["edges"]["left"] == b["edges"]["right"] == BLUE,
          "top/bottom are Red's edges, left/right are Blue's")
    check(len(spec["pieces"]) == 4, "all four corner stones are rendered")
    for p in spec["pieces"]:
        c, r = (int(x) for x in p["cell"].split(","))
        check(0 <= c < b["width"] and 0 <= r < b["height"],
              f"rendered piece {p['cell']} lies inside the declared {size}x{size} board")
    check(max_plies(size) == size * size,
          "max_plies is size*size - one stone per ply, nothing ever removed")

# --------------------------------------------------------------------------
# heuristic: SHAPE, direction (pinned to measured values) and the real consumer
# --------------------------------------------------------------------------
st = G.initial_state(options={"size": 9})
h = G.heuristic(st)
check(isinstance(h, list) and len(h) == 2,
      "heuristic returns a LIST of num_players payoffs (a bare float breaks back-prop)")
check(all(isinstance(x, float) for x in h), "heuristic payoffs are floats")
check(abs(h[0] + h[1]) < 1e-9, "heuristic is zero-sum")
check(abs(h[0]) < 1e-9, "the empty board is dead even")
ahead = NecklaceState(size=9, board={(4, r): RED for r in range(7)})
behind = NecklaceState(size=9, board={(4, r): BLUE for r in range(7)})
check(G.heuristic(ahead)[0] > 0.9,
      f"a near-complete RED column scores high for Red, got {G.heuristic(ahead)}")
check(G.heuristic(behind)[0] < -0.3,
      f"a near-complete BLUE column scores low for Red, got {G.heuristic(behind)}")
check(G.heuristic(ahead)[0] > G.heuristic(st)[0] > G.heuristic(behind)[0],
      "heuristic DIRECTION: a better Red position scores higher for Red")
check(max(abs(x) for x in G.heuristic(ahead)) <= 1.0, "heuristic is bounded to [-1,1]")
# ENEMY STONES BLOCK.  A complete blue row across a 9x9 board cuts Red off
# entirely, so Red's distance is the "unreachable" sentinel and the eval is
# pinned at -1; if enemy stones merely cost a step it would be a mild -0.6.
walled = NecklaceState(size=9, board={(c, 4): BLUE for c in range(9)})
check(G._edge_distance(walled, RED) >= 81,
      f"a solid enemy wall makes Red's edge distance unreachable, got {G._edge_distance(walled, RED)}")
check(G.heuristic(walled)[0] < -0.999,
      f"a solid enemy wall pins the eval at -1 for Red, got {G.heuristic(walled)}")
# seat symmetry: transposing the board and swapping colours must negate the eval
mirror = NecklaceState(size=9, board={(r, c): 1 - v for (c, r), v in ahead.board.items()})
check(abs(G.heuristic(mirror)[0] + G.heuristic(ahead)[0]) < 1e-9,
      "heuristic is antisymmetric under transpose + colour swap")
# the real consumer, with the cutoff FORCED (a malformed payoff only bites there)
from agp.mcts import MCTSBot                                    # noqa: E402
mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(G, st)
check(mv in G.legal_moves(st), "MCTSBot with a forced rollout cutoff returns a legal move")

print(("FAILED: %d" % len(FAILS)) if FAILS else "necklace selftest: all checks passed")
sys.exit(1 if FAILS else 0)
