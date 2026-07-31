#!/usr/bin/env python3
"""Bamboo — correctness anchors.  Pure stdlib; imports only `agp` + this game.

Anchors, strongest first:

* **Both rule-sheet figures, exactly.**  The green dots of Fig. 1 and Fig. 2 are
  the COMPLETE set of available placements for two specific 61-cell positions.
  Both were transcribed from the PDF's vector artwork (138 parsed disc paths:
  fill colour + centre), and both are reproduced cell-for-cell here.  Fig. 2 is
  the *discriminating* figure: it is the one that proves the rule is a
  whole-position invariant over ALL of the mover's groups rather than a test of
  just the group the new stone joins (which would print 8 dots, not 4).  Each
  figure's PREMISE is asserted too — board size, stone counts, per-seat group
  counts and largest groups, whose turn it is — because a mis-transcribed
  position passes every assertion built on it.
* **An independent brute-force move generator.**  `game.placements()` is an
  O(cells) incremental formula; `_ref_placements()` below recomputes every group
  from scratch after every hypothetical placement.  They are compared on every
  position of thousands of random plies, on every board size.
* **Exhaustive solve of the smallest board** (side 2, 7 cells): every reachable
  position enumerated, then solved.  Proves cycle-freedom, drawlessness and the
  game value in one pass.
* Serialize round-trip compared as STATES (plus an exact key-set assertion),
  swept over whole games.
* `render()` bounds and the render caption's winner attribution, on every size.
* The `heuristic`'s shape, zero-sum-ness, seat symmetry and DIRECTION (pinned to
  a measured value on a constructed position), plus a drive through `MCTSBot`
  with the rollout cutoff forced low so the eval is actually consulted.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.bamboo.game import (          # noqa: E402
    Bamboo, BambooState, DIRS, SIZES, cell_count, cell_name, groups_of,
    invariant_holds, neighbors, spec_for,
)

G = Bamboo()
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


def cellstr(c):
    return f"{c[0]},{c[1]}"


# --------------------------------------------------------------------------
#  Independent reference implementations (deliberately naive)
# --------------------------------------------------------------------------

def _ref_groups(size, stones, seat):
    R = size - 1
    on = lambda c: max(abs(c[0]), abs(c[1]), abs(c[0] + c[1])) <= R   # noqa: E731
    mine = {c for c, p in stones.items() if p == seat}
    out, seen = [], set()
    for c in sorted(mine):
        if c in seen:
            continue
        comp, st = {c}, [c]
        seen.add(c)
        while st:
            cur = st.pop()
            for nb in neighbors(*cur):
                if on(nb) and nb in mine and nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    st.append(nb)
        out.append(comp)
    return out


def _label_groups_ref(size, stones, seat):
    """cell -> group index, built from the reference group finder."""
    lab = {}
    for i, grp in enumerate(_ref_groups(size, stones, seat)):
        for c in grp:
            lab[c] = i
    return lab


def _ref_placements(size, stones, seat, reading="all-groups"):
    """The rule sheet's clause applied by brute force.

    reading="all-groups"  — every group of the mover must satisfy size <= count
                            (the rule sheet; what this package implements)
    reading="placed-only" — only the group the new stone joins is tested
                            (AbstractPlay gameslib's reading; see rules.md)
    """
    R = size - 1
    cells = [(q, r) for q in range(-R, R + 1) for r in range(-R, R + 1)
             if abs(q + r) <= R]
    out = []
    for c in sorted(cells):
        if c in stones:
            continue
        s2 = dict(stones)
        s2[c] = seat
        gs = _ref_groups(size, s2, seat)
        cnt = len(gs)
        if reading == "all-groups":
            ok = max(len(x) for x in gs) <= cnt
        else:
            ok = next(len(x) for x in gs if c in x) <= cnt
        if ok:
            out.append(c)
    return out


# --------------------------------------------------------------------------
#  1. Board geometry
# --------------------------------------------------------------------------

def test_geometry():
    for n in SIZES + (2, 3):
        sp = spec_for(n)
        check(len(sp.cells) == cell_count(n) == 3 * n * n - 3 * n + 1,
              f"size {n}: cell count {len(sp.cells)} != 3n^2-3n+1")
        check(len(set(sp.cells)) == len(sp.cells), f"size {n}: duplicate cells")
        # adjacency is symmetric and has the right degree profile
        for c in sp.cells:
            for nb in sp.nbrs[c]:
                check(c in sp.nbrs[nb], f"size {n}: adjacency not symmetric")
        degs = sorted(len(sp.nbrs[c]) for c in sp.cells)
        if n >= 3:
            check(degs.count(3) == 6, f"size {n}: expected 6 corners, got {degs.count(3)}")
            check(degs.count(4) == 6 * (n - 2),
                  f"size {n}: wrong number of degree-4 edge cells")
            check(degs.count(6) == cell_count(n) - 6 * (n - 1),
                  f"size {n}: wrong number of interior cells")
        # algebraic names are unique and match the printed row/column layout
        names = [cell_name(n, c) for c in sp.cells]
        check(len(set(names)) == len(names), f"size {n}: duplicate cell names")
    # bottom-left is a1, and the top row is the (2n-1)-th letter
    check(cell_name(5, (-4, 4)) == "a1", "size 5: (-4,4) should be a1")
    check(cell_name(5, (0, -4)) == "i1", "size 5: (0,-4) should be i1")
    check(cell_name(5, (4, -4)) == "i5", "size 5: (4,-4) should be i5")
    check(cell_name(5, (0, 0)) == "e5", "size 5: centre should be e5")
    check(len(DIRS) == 6 and len(set(DIRS)) == 6, "DIRS must be 6 distinct offsets")


# --------------------------------------------------------------------------
#  2. The rule-sheet figures  (marksteeregames.com/Bamboo_rules.pdf)
#
#  Rows top-to-bottom of the printed hexhex of side 5; 'R'/'B' stones, '.' empty.
#  Row i (0 = top) is algebraic rank chr('i' - i); column j (0 = left) is index
#  j+1 within that row — so writing the greens BOTH as (row, col) and as
#  algebraic names pins the coordinate mapping to the picture.
# --------------------------------------------------------------------------

FIG1_ROWS = [
    ".BRBR",
    "BBRR.B",
    "RB.BRBR",
    "RBBR.B.R",
    "B.RRB..RB",
    "R.BB.R..",
    "BR.B.BR",
    "BRRR.R",
    "BRBBR",
]
FIG1_GREEN_RC = [(0, 0), (1, 4), (2, 2), (3, 4), (3, 6), (4, 1),
                 (4, 5), (4, 6), (5, 4), (5, 7), (6, 2), (6, 4)]
FIG1_GREEN_ALG = ["i1", "h5", "g3", "f5", "f7", "e2",
                  "e6", "e7", "d5", "d8", "c3", "c5"]

FIG2_ROWS = [
    "BBRBR",
    "BBRRRB",
    "RBBBRBR",
    "RBBR.B.R",
    "B.RRB..RB",
    "R.BBRR.R",
    "BR.B.BR",
    "BRRR.R",
    "BRBBR",
]
FIG2_GREEN_RC = [(3, 6), (4, 6), (5, 6), (6, 2)]
FIG2_GREEN_ALG = ["f7", "e7", "d7", "c3"]


def _fig_cell(i, j, size=5):
    R = size - 1
    r = i - R
    return (max(-R, -R - r) + j, r)


def _parse_fig(rows):
    stones = {}
    for i, row in enumerate(rows):
        want = 5 + i if i <= 4 else 13 - i
        check(len(row) == want, f"figure row {i} should have {want} cells")
        for j, ch in enumerate(row):
            if ch in "RB":
                stones[_fig_cell(i, j)] = 0 if ch == "R" else 1
    return stones


def _find_move_order(target, tries=200, seed=7):
    """A legal alternating move order (Red first) reaching exactly `target`,
    or None.  Randomised, but seeded, so the test is deterministic."""
    rng = random.Random(seed)
    for _ in range(tries):
        s = G.initial_state({"size": 5})
        left = {p: {c for c, v in target.items() if v == p} for p in (0, 1)}
        order = []
        while len(order) < len(target):
            seat = s.to_move
            cand = [c for c in G.placements(s) if c in left[seat]]
            if not cand:
                break
            c = rng.choice(cand)
            s = G.apply_move(s, cellstr(c))
            left[seat].discard(c)
            order.append(c)
        if len(order) == len(target) and dict(s.stones) == target:
            return order
    return None


def test_figures():
    figs = [
        ("Fig. 1 (Red to move)", FIG1_ROWS, FIG1_GREEN_RC, FIG1_GREEN_ALG, 0,
         dict(stones=46, empty=15, groups=(9, 10), largest=(5, 6),
              per_seat=(23, 23))),
        ("Fig. 2 (Blue to move)", FIG2_ROWS, FIG2_GREEN_RC, FIG2_GREEN_ALG, 1,
         dict(stones=51, empty=10, groups=(7, 9), largest=(7, 9),
              per_seat=(26, 25))),
    ]
    for label, rows, green_rc, green_alg, seat, pre in figs:
        stones = _parse_fig(rows)
        s = BambooState(size=5, stones=dict(stones), to_move=seat)

        # ---- the figure's PREMISE, not just its illustrated outcome --------
        check(len(spec_for(5).cells) == 61, f"{label}: board must be side 5")
        check(len(stones) == pre["stones"],
              f"{label}: transcribed {len(stones)} stones, expected {pre['stones']}")
        check(61 - len(stones) == pre["empty"], f"{label}: wrong empty count")
        # Turn parity: Red moves first and the players alternate, so the stone
        # counts must be (k, k) with Red to move or (k+1, k) with Blue to move.
        # For Fig. 2 (26 Red, 25 Blue, Blue to move) this also pins WHICH
        # colour is which — a red/blue swap makes the position unreachable.
        per = tuple(sum(1 for v in stones.values() if v == p) for p in (0, 1))
        check(per == pre["per_seat"],
              f"{label}: stones per seat {per} != {pre['per_seat']}")
        check(per[0] - per[1] == (0 if seat == 0 else 1),
              f"{label}: {per} with seat {seat} to move contradicts alternating "
              f"play starting with Red")
        for p in (0, 1):
            gs = groups_of(spec_for(5), stones, p)
            check(len(gs) == pre["groups"][p],
                  f"{label}: seat {p} has {len(gs)} groups, expected {pre['groups'][p]}")
            check(max(len(x) for x in gs) == pre["largest"][p],
                  f"{label}: seat {p} largest group {max(len(x) for x in gs)}, "
                  f"expected {pre['largest'][p]}")
            check(invariant_holds(spec_for(5), stones, p),
                  f"{label}: seat {p} violates the invariant — bad transcription")

        # ---- the two ways of naming the green cells must agree -------------
        green = {_fig_cell(i, j) for i, j in green_rc}
        check({cell_name(5, c) for c in green} == set(green_alg),
              f"{label}: (row,col) and algebraic green sets disagree")
        check(len(green) == len(green_rc) == len(green_alg),
              f"{label}: duplicate green cell")

        # ---- the legal-move set must EQUAL the printed green set -----------
        got = set(G.placements(s))
        check(got == green,
              f"{label}: placements {sorted(cell_name(5, c) for c in got)} "
              f"!= printed {sorted(green_alg)}")
        check(set(G.legal_moves(s)) == {cellstr(c) for c in green},
              f"{label}: legal_moves disagrees with the printed green set")
        check(set(_ref_placements(5, stones, seat)) == green,
              f"{label}: brute-force reference disagrees with the printed green set")

    # ---- each figure must be a LEGALLY REACHABLE position -------------
    # The strongest premise check available: search for an alternating move
    # order (Red first) every prefix of which is legal.  A mis-transcribed
    # board is very unlikely to admit one.
    for label, rows in (("Fig. 1", FIG1_ROWS), ("Fig. 2", FIG2_ROWS)):
        target = _parse_fig(rows)
        order = _find_move_order(target, tries=200, seed=7)
        check(order is not None,
              f"{label}: no legal move order reaches the printed position — "
              f"the transcription is probably wrong")
        if order is not None:
            check(len(order) == len(target),
                  f"{label}: move order has {len(order)} of {len(target)} stones")

    # ---- Fig. 2 is the DISCRIMINATOR ----------------------------------
    # Under the "only the group the new stone joins" reading (AbstractPlay
    # gameslib's), Fig. 2 would print 8 dots.  The rule sheet prints 4.
    st2 = _parse_fig(FIG2_ROWS)
    loose = set(_ref_placements(5, st2, 1, reading="placed-only"))
    strict = {_fig_cell(i, j) for i, j in FIG2_GREEN_RC}
    check(strict < loose and len(loose) == 8,
          f"Fig. 2 should discriminate: placed-only reading gives {len(loose)} "
          f"cells, all-groups gives {len(strict)}")
    check(set(G.placements(BambooState(size=5, stones=st2, to_move=1))) == strict,
          "Fig. 2: the package must implement the all-groups reading")
    # Fig. 1 does NOT discriminate between those two — recorded so nobody
    # mistakes it for proof of the all-groups reading.
    st1 = _parse_fig(FIG1_ROWS)
    check(set(_ref_placements(5, st1, 0, reading="placed-only")) ==
          set(_ref_placements(5, st1, 0)),
          "Fig. 1 is expected to be silent on the two readings")

    # ---- Fig. 1 settles AFTER vs BEFORE ------------------------------
    # "the number of groups he has" could be read as the count BEFORE the
    # placement.  On Fig. 1 that reading prints 14 cells, not the 12 drawn.
    for label, stones, seat, printed, want in (("Fig. 1", st1, 0, 12, 14),
                                               ("Fig. 2", st2, 1, 4, 8)):
        before = len(groups_of(spec_for(5), stones, seat))
        n = 0
        for c in spec_for(5).cells:
            if c in stones:
                continue
            s2 = dict(stones)
            s2[c] = seat
            if max(len(x) for x in groups_of(spec_for(5), s2, seat)) <= before:
                n += 1
        check(n == want and n != printed,
              f"{label}: the count-BEFORE reading gives {n} cells, expected "
              f"{want} (and it must differ from the {printed} printed)")


# --------------------------------------------------------------------------
#  3. Move generation vs the brute-force reference, over whole games
# --------------------------------------------------------------------------

def test_movegen_vs_reference():
    rng = random.Random(4242)
    positions = 0
    # How many of the mover's OWN groups a candidate cell touches.  k is what
    # the incremental formula branches on, so the comparison below is only
    # meaningful if every value of k is actually exercised; k <= 3 always,
    # because a hex cell's six neighbours form a ring and two consecutive ones
    # are themselves adjacent.
    kdist = {0: 0, 1: 0, 2: 0, 3: 0}
    k0_illegal = 0
    for size in SIZES:
        for _ in range(3 if size >= 6 else 6):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                fast = sorted(G.placements(s))
                slow = sorted(_ref_placements(size, s.stones, s.to_move))
                check(fast == slow,
                      f"size {size}: incremental placements != brute force "
                      f"at ply {len(s.stones)}")
                # the opponent's set is computed by the same code path
                opp = sorted(G.placements(s, 1 - s.to_move))
                check(opp == sorted(_ref_placements(size, s.stones, 1 - s.to_move)),
                      f"size {size}: opponent placements != brute force")
                sp = spec_for(size)
                lab = _label_groups_ref(size, s.stones, s.to_move)
                for c in sp.cells:
                    if c in s.stones:
                        continue
                    k = len({lab[nb] for nb in sp.nbrs[c] if nb in lab})
                    check(k <= 3, f"a cell cannot touch {k} of your own groups")
                    kdist[k] += 1
                    if k == 0 and c not in fast:
                        k0_illegal += 1
                positions += 1
                s = G.apply_move(s, cellstr(rng.choice(fast)))
            # every reachable position satisfied the invariant for BOTH seats
    check(positions > 400, f"only {positions} positions compared")
    check(all(n > 0 for n in kdist.values()) and kdist[3] >= 20,
          f"branch coverage too thin: k distribution {kdist}")
    check(k0_illegal == 0,
          f"{k0_illegal} isolated placements were rejected — a cell with no "
          f"friendly neighbour must ALWAYS be legal")
    print(f"  movegen vs brute force: {positions} positions, "
          f"merge-arity coverage {kdist}")


# --------------------------------------------------------------------------
#  4. Invariant, termination, drawlessness, winner attribution
# --------------------------------------------------------------------------

def test_games():
    rng = random.Random(99)
    for size in SIZES:
        sp = spec_for(size)
        cap = cell_count(size)          # derived, not pinned
        for _ in range(6 if size >= 6 else 12):
            s = G.initial_state({"size": size})
            check(sorted(G.legal_moves(s)) == sorted(cellstr(c) for c in sp.cells),
                  f"size {size}: every cell must be legal on the empty board")
            check(not G.is_terminal(s), f"size {size}: fresh state is terminal")
            plies = 0
            while not G.is_terminal(s):
                mv = rng.choice(G.legal_moves(s))
                before = json.dumps(G.serialize(s), sort_keys=True)
                s2 = G.apply_move(s, mv)
                check(json.dumps(G.serialize(s), sort_keys=True) == before,
                      "apply_move mutated its input state")
                s = s2
                plies += 1
                check(len(s.stones) == plies,
                      "one stone per ply, never removed (the termination monovariant)")
                check(plies <= cap, f"size {size}: game exceeded {cap} plies")
                for p in (0, 1):
                    check(invariant_holds(sp, s.stones, p),
                          f"size {size}: invariant broken for seat {p}")
            # terminal
            check(G.legal_moves(s) == [], "terminal state must have no moves")
            check(s.winner is not None, "winner must be set by apply_move")
            check(s.winner == 1 - s.to_move,
                  "the winner is exactly the player who placed last")
            check(G.returns(s) in ([1.0, -1.0], [-1.0, 1.0]),
                  f"non-decisive returns {G.returns(s)} — Bamboo cannot draw")
            check(G.returns(s)[s.winner] == 1.0, "returns disagrees with winner")
    print("  random games: termination monovariant + drawlessness OK")


def test_winner_is_reached_via_apply_move():
    """Point 13: `winner` is set only inside apply_move, so a hand-built dead
    position has winner=None.  is_terminal/returns must still be right."""
    rng = random.Random(7)
    s = G.initial_state({"size": 4})
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    bare = BambooState(size=s.size, stones=dict(s.stones), to_move=s.to_move)
    check(bare.winner is None, "hand-built state should carry no winner")
    check(G.is_terminal(bare), "is_terminal must work without a stored winner")
    check(G.returns(bare) == G.returns(s),
          "returns must agree with or without the stored winner")
    check(G.legal_moves(bare) == [], "a stuck hand-built state has no moves")


def test_illegal_moves():
    s = G.initial_state({"size": 4})
    s = G.apply_move(s, "0,0")
    for bad, why in [("0,0", "occupied"), ("9,9", "off board"),
                     ("99,-99", "off board")]:
        try:
            G.apply_move(s, bad)
            check(False, f"apply_move accepted an illegal move ({why})")
        except ValueError:
            pass
    # a placement that would violate the invariant must be rejected even when
    # fed directly to apply_move (it is not in legal_moves)
    sp = spec_for(4)
    stones = {(0, 0): 0, (1, 0): 0}          # Red: one group of 2, count 1
    check(not invariant_holds(sp, stones, 0), "premise: 2 stones in 1 group is illegal")
    s2 = BambooState(size=4, stones={(0, 0): 0}, to_move=0)
    check((1, 0) not in G.placements(s2),
          "extending a lone stone to a group of 2 must be illegal")
    try:
        G.apply_move(s2, "1,0")
        check(False, "apply_move accepted an invariant-violating placement")
    except ValueError:
        pass
    # ...but an isolated second stone is always fine
    check((2, 0) in G.placements(s2), "an isolated new group must always be legal")


# --------------------------------------------------------------------------
#  5. Constructed positions random play cannot be relied on to reach
# --------------------------------------------------------------------------

def test_constructed():
    sp = spec_for(5)

    # (a) The merge case that separates the two readings, minimal form.
    #     Red: one group of 4 (a straight line) + three singletons, two of them
    #     two apart, so one cell merges exactly those two.
    line = [(-4, 0), (-3, 0), (-2, 0), (-1, 0)]        # 4 in a row
    singles = [(0, 3), (-2, 3), (0, -3)]               # (0,3) & (-2,3) 2 apart
    stones = {c: 0 for c in line + singles}
    check(invariant_holds(sp, stones, 0),
          "premise: 4 stones in the largest of 4 groups is legal")
    gs = groups_of(sp, stones, 0)
    check(sorted(len(x) for x in gs) == [1, 1, 1, 4], "premise: [4,1,1,1]")
    s = BambooState(size=5, stones=stones, to_move=0)
    bridge = (-1, 3)                                   # merges the two singletons
    check({(0, 3), (-2, 3)} <= set(sp.nbrs[bridge]),
          "premise: (-1,3) touches both singletons")
    check(not any(bridge in sp.nbrs[c] for c in line + [(0, -3)]),
          "premise: the bridge must not also touch the 4-group")
    check(bridge not in G.placements(s),
          "merging two singletons here leaves groups [4,3,1]: the 4-group now "
          "exceeds the group count of 3, so the placement is ILLEGAL")
    check(bridge in _ref_placements(5, stones, 0, reading="placed-only"),
          "premise: the placed-group-only reading would allow it")

    # (b) The tight case: max group size == group count.  Nothing may merge,
    #     nothing may grow the largest group; isolated placements stay legal.
    stones = {(-4, 0): 0, (-3, 0): 0, (-2, 0): 0,      # group of 3
              (0, 3): 0, (0, -3): 0}                   # + 2 singletons  -> [3,1,1]
    check(len(groups_of(sp, stones, 0)) == 3, "premise: 3 groups")
    s = BambooState(size=5, stones=stones, to_move=0)
    ok = set(G.placements(s))
    check((-1, 0) not in ok, "growing the maximal group to 4 with 3 groups is illegal")
    check((-4, 1) not in ok, "any growth of the maximal group is illegal")
    check((1, 3) in ok and (2, 2) in ok, "isolated placements remain legal")
    for c in ok:
        s2 = dict(stones)
        s2[c] = 0
        check(invariant_holds(sp, s2, 0), f"placement {c} breaks the invariant")
    for c in sp.cells:
        if c in stones or c in ok:
            continue
        s2 = dict(stones)
        s2[c] = 0
        check(not invariant_holds(sp, s2, 0),
              f"{c} was rejected but does not break the invariant")

    # (c) The opponent's groups are irrelevant: repainting Blue's stones or
    #     moving them around must not change Red's move set.
    rng = random.Random(1234)
    base = {(-4, 0): 0, (-3, 0): 0, (0, 3): 0, (0, -3): 0}
    s = BambooState(size=5, stones=dict(base), to_move=0)
    want = set(G.placements(s))
    empties = [c for c in sp.cells if c not in base]
    for _ in range(60):
        blue = rng.sample(empties, 12)
        stones = dict(base)
        stones.update({c: 1 for c in blue})
        s = BambooState(size=5, stones=stones, to_move=0)
        check(set(G.placements(s)) == want - set(blue),
              "Blue's stones must only block cells, never change Red's rule")

    # (d) Every cell of an empty board is legal on every size (the reason the
    #     first player can never be stuck, hence no draw).
    for n in SIZES + (2, 3):
        s = BambooState(size=n)
        check(len(G.placements(s)) == cell_count(n),
              f"size {n}: the empty board must offer every cell")


# --------------------------------------------------------------------------
#  6. Exhaustive solve of the smallest board (side 2, 7 cells)
# --------------------------------------------------------------------------

def test_exhaustive_side2():
    size = 2
    frontier = {(frozenset(), 0)}
    seen = set(frontier)
    depth, terminals = 0, 0
    while frontier:
        nxt = set()
        for key, seat in frontier:
            stones = dict(key)
            check(len(stones) == depth, "ply count must equal the stone count")
            opts = G.placements(BambooState(size=size, stones=stones, to_move=seat))
            if not opts:
                terminals += 1
                check(depth > 0, "the empty board must never be terminal")
                continue
            for c in opts:
                s2 = dict(stones)
                s2[c] = seat
                k2 = (frozenset(s2.items()), 1 - seat)
                if k2 not in seen:
                    seen.add(k2)
                    nxt.add(k2)
        frontier = nxt
        depth += 1
    longest = depth - 1
    check((len(seen), terminals, longest) == (175, 29, 6),
          f"side-2 state space changed: {len(seen)} positions, {terminals} "
          f"terminal, longest {longest} plies (expected 175 / 29 / 6)")
    check(longest < cell_count(size),
          "side 2 never fills its 7th cell — the game can end with the board "
          "NOT full")

    memo = {}

    def solve(stones, seat):
        key = (frozenset(stones.items()), seat)
        if key in memo:
            return memo[key]
        opts = G.placements(BambooState(size=size, stones=stones, to_move=seat))
        if not opts:
            memo[key] = -1
            return -1
        v = -1
        for c in opts:
            s2 = dict(stones)
            s2[c] = seat
            if -solve(s2, 1 - seat) > 0:
                v = 1
                break
        memo[key] = v
        return v

    check(solve({}, 0) == -1,
          "side 2 (7 cells) is a second-player win with perfect play")
    print(f"  side-2 exhaustive: {len(seen)} positions, {terminals} terminals, "
          f"longest {longest} plies, value = second-player win")


# --------------------------------------------------------------------------
#  7. serialize / deserialize — compared as STATES, plus the exact key set
# --------------------------------------------------------------------------

KEYS = {"size", "stones", "to_move", "winner", "last"}


def test_serialize():
    rng = random.Random(31337)
    checked = 0
    for size in SIZES:
        s = G.initial_state({"size": size})
        while True:
            d = G.serialize(s)
            check(set(d) == KEYS, f"serialize keys {set(d)} != {KEYS}")
            json.dumps(d)                       # must be JSON-able
            back = G.deserialize(json.loads(json.dumps(d)))
            check(back == s, f"state round-trip failed at ply {len(s.stones)}")
            check(back.stones == s.stones and back.last == s.last and
                  back.winner == s.winner and back.to_move == s.to_move and
                  back.size == s.size, "field-by-field round-trip failed")
            checked += 1
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    check(checked > 150, f"only {checked} states round-tripped")
    print(f"  serialize: {checked} states round-tripped as states (keys pinned)")


# --------------------------------------------------------------------------
#  8. render() — declared bounds on every size, and the caption's attribution
# --------------------------------------------------------------------------

def test_render():
    rng = random.Random(5)
    for size in SIZES:
        sp = spec_for(size)
        ids = {cellstr(c) for c in sp.cells}
        s = G.initial_state({"size": size})
        # reach a FAR-CORNER position through apply_move: play the six corners
        corners = [(size - 1, 0), (0, size - 1), (-(size - 1), size - 1),
                   (-(size - 1), 0), (0, -(size - 1)), (size - 1, -(size - 1))]
        for c in corners:
            check(c in sp.cellset, f"size {size}: corner {c} not on the board")
            if cellstr(c) in G.legal_moves(s):
                s = G.apply_move(s, cellstr(c))
            # opponent replies elsewhere so the corners alternate colours
            if not G.is_terminal(s):
                other = [m for m in G.legal_moves(s)
                         if m not in {cellstr(x) for x in corners}]
                if other:
                    s = G.apply_move(s, rng.choice(other))
        placed = {cellstr(c) for c in corners} & {cellstr(c) for c in s.stones}
        check(len(placed) == 6, f"size {size}: only {len(placed)} corners occupied")
        spec = G.render(s)
        b = spec["board"]
        check(b["type"] == "hex" and b["shape"] == "hexagon" and b["size"] == size,
              f"size {size}: render declares {b}")
        for p in spec["pieces"]:
            check(p["cell"] in ids,
                  f"size {size}: piece at {p['cell']} lies OUTSIDE the declared board")
        check({p["cell"] for p in spec["pieces"]} ==
              {cellstr(c) for c in s.stones}, f"size {size}: pieces != stones")
        for h in spec["highlights"]:
            check(h["cell"] in ids, f"size {size}: highlight outside the board")
        json.dumps(spec)

    # ---- the caption's winner attribution (never on the legality path) ----
    for seed in range(12):
        rng = random.Random(seed)
        s = G.initial_state({"size": 4})
        while not G.is_terminal(s):
            prev = G.render(s)["caption"]
            check("to move" in prev and "wins" not in prev,
                  f"mid-game caption looks terminal: {prev}")
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        cap = G.render(s)["caption"]
        winner = ("Red", "Blue")[s.winner]
        loser = ("Red", "Blue")[1 - s.winner]
        check(cap.startswith(f"{winner} wins"),
              f"caption names the wrong winner: {cap} (winner is {winner})")
        check(f"{loser} has no legal placement" in cap,
              f"caption does not name the stuck player: {cap}")
        # and the same on a hand-built dead state with no stored winner
        bare = BambooState(size=s.size, stones=dict(s.stones), to_move=s.to_move)
        check(G.render(bare)["caption"] == cap,
              "caption must not depend on the stored winner")
    print("  render: bounds on every size + caption attribution OK")


# --------------------------------------------------------------------------
#  9. describe_move / helpers
# --------------------------------------------------------------------------

def test_helpers():
    s = G.initial_state({"size": 5})
    check(G.describe_move(s, "-4,4") == "a1", "describe_move should give a1")
    check(G.describe_move(s, "nonsense") == "nonsense",
          "describe_move must not raise on junk")
    check(G.group_count(s, 0) == 0 and G.largest_group(s, 0) == 0,
          "empty board has no groups")
    stones = {(0, 0): 0, (1, 0): 0, (0, 3): 0, (0, 2): 1}
    s = BambooState(size=5, stones=stones, to_move=0)
    check(G.group_count(s, 0) == 2 and G.largest_group(s, 0) == 2,
          "group_count/largest_group disagree with the board")
    check(G.group_count(s, 1) == 1 and G.largest_group(s, 1) == 1,
          "Blue's group accounting is wrong")
    check(G.group_of(s, (0, 0)) == {(0, 0), (1, 0)}, "group_of is wrong")
    check(G.group_of(s, (0, 2)) == {(0, 2)}, "group_of crosses colours")
    check(G.group_of(s, (4, 0)) == set(), "group_of on an empty cell")
    # helpers must agree with the reference on random boards
    rng = random.Random(2)
    for _ in range(200):
        s = G.initial_state({"size": 4})
        for _ in range(rng.randrange(0, 20)):
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        for p in (0, 1):
            ref = _ref_groups(4, s.stones, p)
            check(G.group_count(s, p) == len(ref), "group_count != reference")
            check(G.largest_group(s, p) == (max(len(x) for x in ref) if ref else 0),
                  "largest_group != reference")
            for c in s.stones:
                if s.stones[c] == p:
                    check(G.group_of(s, c) in ref, "group_of != reference")
            # game.py carries TWO group implementations — the readable
            # `groups_of` (used by invariant_holds, i.e. by apply_move) and the
            # labelling pass inside `placements`.  They must agree.
            gs = groups_of(spec_for(4), s.stones, p)
            check(sorted(len(x) for x in gs) == sorted(len(x) for x in ref),
                  "groups_of != reference")
            check(invariant_holds(spec_for(4), s.stones, p) ==
                  (not ref or max(len(x) for x in ref) <= len(ref)),
                  "invariant_holds != reference")


# --------------------------------------------------------------------------
#  10. heuristic — SHAPE, DIRECTION (pinned to measured values), and the
#      consumer path (MCTSBot with the rollout cutoff forced to fire)
# --------------------------------------------------------------------------

def test_heuristic():
    sp = spec_for(5)
    # A constructed position: Red has 5 scattered singletons (maximum slack),
    # Blue a 3-line plus 2 singletons (3 groups, largest 3 — at his limit).
    red = [(-4, 0), (0, -4), (4, -4), (0, 4), (-2, 2)]
    blue = [(0, 0), (1, 0), (2, 0), (2, 2), (-3, -1)]
    stones = {c: 0 for c in red}
    stones.update({c: 1 for c in blue})
    for p in (0, 1):
        check(invariant_holds(sp, stones, p),
              f"premise: the constructed position must be legal for seat {p}")
    s = BambooState(size=5, stones=dict(stones), to_move=0)
    check((G.group_count(s, 0), G.largest_group(s, 0)) == (5, 1),
          "premise: Red should be 5 singletons")
    check((G.group_count(s, 1), G.largest_group(s, 1)) == (3, 3),
          "premise: Blue should be 3 groups with a largest of 3")
    mob = (len(G.placements(s, 0)), len(G.placements(s, 1)))
    check(mob == (51, 41), f"premise: mobility {mob}, expected (51, 41)")

    h = G.heuristic(s)
    check(isinstance(h, list) and len(h) == 2, f"heuristic must be a 2-list: {h}")
    check(all(isinstance(x, float) for x in h), "heuristic entries must be floats")
    check(abs(h[0] - 0.6640) < 1e-3,
          f"heuristic direction/scale drifted: {h[0]:.4f}, expected ~0.6640")
    check(h[0] > 0, "the side with MORE available placements must score higher")
    check(abs(h[0] + h[1]) < 1e-12, "heuristic must be zero-sum")

    # seat symmetry: swapping the colours negates the score
    swapped = BambooState(size=5, stones={c: 1 - v for c, v in stones.items()},
                          to_move=1)
    hs = G.heuristic(swapped)
    check(abs(hs[0] + h[0]) < 1e-12, f"seat symmetry broken: {hs} vs {h}")

    # empty board is dead even; every value stays bounded
    check(G.heuristic(G.initial_state({"size": 5})) == [0.0, -0.0],
          "the empty board must evaluate to 0")
    rng = random.Random(8)
    for size in SIZES:
        s = G.initial_state({"size": size})
        while True:
            h = G.heuristic(s)
            check(len(h) == 2 and all(-1.0 <= x <= 1.0 for x in h),
                  f"heuristic out of range: {h}")
            check(abs(h[0] + h[1]) < 1e-12, "heuristic must be zero-sum")
            if G.is_terminal(s):
                check(h == G.returns(s),
                      f"at a terminal the heuristic must equal returns: "
                      f"{h} vs {G.returns(s)}")
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))

    # the actual consumer: force the rollout cutoff so the heuristic is used
    from agp.mcts import MCTSBot
    s = G.initial_state({"size": 4})
    for _ in range(6):
        mv = MCTSBot(random.Random(3), iterations=30, max_rollout=4).select(G, s)
        check(mv in G.legal_moves(s), "MCTSBot returned an illegal move")
        s = G.apply_move(s, mv)
    print("  heuristic: shape, direction (pinned), symmetry, MCTSBot path OK")


def main():
    test_geometry()
    test_figures()
    test_movegen_vs_reference()
    test_games()
    test_winner_is_reached_via_apply_move()
    test_illegal_moves()
    test_constructed()
    test_exhaustive_side2()
    test_serialize()
    test_render()
    test_helpers()
    test_heuristic()
    if FAILS:
        print(f"\n{len(FAILS)} FAILURE(S)")
        return 1
    print("\nbamboo selftest: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
