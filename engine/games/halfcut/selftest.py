#!/usr/bin/env python3
"""Correctness anchors for Halfcut (Mark Steere, August 2023).

Pure stdlib.  The rule sheet (marksteeregames.com/Halfcut_rules.pdf, md5
4d0c94735c463c4e7d1e9e8702a41794, ModDate 2023-08-14 04:46:07 PDT - the live
file today and its only Wayback capture are byte-identical) has SEVEN figures
and every one of them is load-bearing.  All seven are transcribed here from the
vector artwork itself: `pdftocairo -svg` was parsed for filled disc paths, whose
bounding-box centres were snapped to each figure's 6x6 lattice - not eyeballed
pixels.  The prose prints eleven group sizes across Figures 3/4/5/7 and every
one of them is asserted.

  FIGURE 1   "Blue has won."  The coloured frame is the GROUND TRUTH OUTSIDE
             THE ENGINE for the seat<->edge mapping: the RED bars are the top
             and bottom, the BLUE bars the left and right, and the winning blue
             chain runs from the left column to the right column.  Under the
             transposed reading NEITHER colour connects, so a transposed engine
             cannot pass it.
  FIGURE 2   the crosscut shape.
  FIGURE 3   "Red has crosscut groups of sizes 1 and 4.  Blue has crosscut
             groups of sizes 2 and 3."  Pins the PER-CHECKER reading of
             "crosscut group" (a crosscut has up to two of them per colour,
             because its two same-coloured checkers are diagonally opposed and
             so need not be connected) and the orthogonal-only group definition.
  FIGURE 4   Red MAY place on the ?: his new crosscut group of size 3 is larger
             than the blue crosscut group of size 2 - while the SAME crosscut's
             other blue group has size 3.  This is the "at least one" anchor.
  FIGURE 5   the same square judged for both colours: Red may NOT (new group 3
             vs blue groups 3 and 5), Blue MAY (new group 9 vs red groups 1
             and 1).
  FIG 6a/6b  before/after.  Red places the dotted checker (new group 4) and
             kills EXACTLY ONE blue checker - the crosscut checker whose group
             has size 2.  The crosscut's other blue checker (group size 5)
             survives, AND the second checker of the size-2 group survives.
             This is what proves removal takes crosscut CHECKERS, not groups.
  FIGURE 7   simultaneous crosscuts: new group 3 beats the left crosscut's blue
             size-2 group but not either of the right crosscut's blue size-3
             groups, so the placement is illegal.

FIGURE PREMISES ARE ASSERTED, NOT JUST OUTCOMES.  A mis-transcribed board
satisfies every assertion built on it, so each figure's preconditions are
checked too: that the marked square really is empty, that the pre-placement
position really is crosscut-free (the invariant the whole game rests on), that
exactly the stated NUMBER of crosscuts is formed, and - for 6a/6b - that the
dead checker's group had size 2 and its group-mate is still standing.

ANCHOR DISCRIMINATING POWER (MEASURED below, not assumed).  Fourteen wrong
readings of the crosscut/removal rule are enumerated, and the exact map of
which anchor kills which is pinned in EXPECTED_KILLS.  What the measurement
found:
  * The seven PRINTED figures kill 12 of the 14.  They are blind to exactly
    two, and both blind spots are closed here with deliberate extra inputs:
      - "only the FIRST crosscut of a simultaneous pair is judged": figure 7 is
        the only simultaneous-crosscut figure and it happens to print the
        FAILING crosscut first, so it cannot see this.  Closed with figure 7's
        horizontal MIRROR - legality never looks at the board edges, so it is
        invariant under every isometry of the grid, which makes the mirror a
        rigorous consequence of the figure while reversing the enumeration
        order.
      - "remove only the SMALLEST enemy crosscut group": every printed example
        has the crosscut's two enemy groups either equal (fig 5: 1 and 1) or
        with only one under the threshold (fig 6: 2 and 5).  Closed with a
        constructed position whose one crosscut has blue groups of sizes 1 and
        2 under a size-4 attacker (also confirmed against the gameslib oracle).
  * Only figures 6a/6b and that constructed position touch the REMOVAL rule at
    all; every other figure stops at legality.  Using the engine's own
    resolve() output as an expected position-after would be circular, so the
    removal battery runs ONLY on the two externally-sourced anchors.
  * Figure 4 is the only anchor that separates "larger than at least ONE of the
    crosscut's enemy groups" from "larger than ALL of them" via a LEGAL
    placement - and "larger than all" is a real published ruleset (gameslib
    ships it as its `clearcut` variant); figure 6 kills it too (4 is not > 5).
  * NO anchor distinguishes simultaneous from sequential removal - and none
    could, because the two are provably identical (see rules.md).  That is
    proven algebraically rather than tested.

The other anchors: the two lemmas of the drawlessness proof, tested on
CONSTRUCTED inputs (a draw is unreachable, so random play can never exercise
them) and exhaustively on small boards; the Crossway theorem verified over all
2**(n*n) full boards for n <= 4; exhaustive solves of the 2x2 and 3x3 boards
(which also PROVE the state graph acyclic and the termination monovariant
strictly increasing on every one of their edges); the serialize round-trip
compared as STATE OBJECTS over a whole game; and render bounds at every offered
board size from a far-corner position.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import itertools                                                # noqa: E402
import random                                                   # noqa: E402
from dataclasses import replace                                 # noqa: E402
from games.halfcut.game import (                                # noqa: E402
    BLUE, RED, Halfcut, HalfcutState, connection_path, connects, crosscuts_formed,
    crosscuts_on_board, group_of, group_size, group_size_signature, has_placement,
    is_legal, placements, resolve,
)

G = Halfcut()
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


# ==========================================================================
# the seven figures, transcribed TOP ROW FIRST from the vector artwork
# ==========================================================================
N = 6
FIGS = {
    "F1":  [". R . . . .", ". R . . . .", ". R . . B B",
            ". R B R B R", "B B B B B R", ". R . . . R"],
    "F2":  [". . . . . .", ". . . . . .", ". . . . . .",
            ". R B . . .", ". B R . . .", ". . . . . ."],
    "F3":  [". . . . . .", ". . . . . .", ". . R B B B",
            ". B B R R .", ". . . R R .", ". . . . . ."],
    "F4":  [". . . . . .", ". B R R R .", ". B R . . .",
            ". . B B B .", ". R . . . B", ". R . . . ."],
    "F5":  [". . R . . .", ". . R R R R", ". B . B R .",
            ". B B B R .", ". . R . B .", ". . B R B B"],
    "F6a": ["R R . . . .", "R . B B B .", ". . R B . B",
            ". . R B R R", ". . R R B B", ". . . . . ."],
    "F6b": ["R R . . . .", "R . B B B .", ". . R B . B",
            ". . R B R R", ". . R R . B", ". . . . . ."],
    "F7":  [". . R . . .", ". B R . . .", ". B . B B B",
            ". R B R . .", ". R B . R .", ". . B . R R"],
}


def fig(name):
    """The figure as a board dict.  Printed rows are TOP first; engine r=0 is
    the BOTTOM row, so row i of the artwork is r = N-1-i."""
    bd = {}
    for i, row in enumerate(FIGS[name]):
        r = N - 1 - i
        for c, ch in enumerate(row.split()):
            if ch == "R":
                bd[(c, r)] = RED
            elif ch == "B":
                bd[(c, r)] = BLUE
    return bd


def at(c, row_from_top):
    return (c, N - 1 - row_from_top)


# --------------------------------------------------------------------------
# FIGURE 1 - the seat/edge mapping, pinned to the printed frame
# --------------------------------------------------------------------------
b1 = fig("F1")
check(len(b1) == 18, f"PREMISE: figure 1 has 18 checkers, transcribed {len(b1)}")
check(sum(1 for v in b1.values() if v == RED) == 9
      and sum(1 for v in b1.values() if v == BLUE) == 9,
      "PREMISE: figure 1 is 9 red vs 9 blue - equal counts, consistent with Red "
      "moving first and BLUE having just made the winning placement")
check(crosscuts_on_board(b1, N) == [],
      "PREMISE: figure 1 is crosscut-free (it is a real game position)")
check(connects(b1, BLUE, N), "figure 1: BLUE has won")
check(not connects(b1, RED, N), "figure 1: Red has NOT connected")
# ground truth outside the engine: the sheet says the winner in figure 1 is
# BLUE and the blue frame bars are the LEFT and RIGHT of the board.
winner = BLUE
spec = G.render(HalfcutState(size=N, board=b1, winner=winner))
check(spec["board"]["edges"]["left"] == winner and spec["board"]["edges"]["right"] == winner,
      "render: the winner of figure 1 owns the LEFT and RIGHT edges")
check(spec["board"]["edges"]["top"] == 1 - winner and spec["board"]["edges"]["bottom"] == 1 - winner,
      "render: the other seat owns the TOP and BOTTOM edges")
check(spec["caption"] == "Blue wins",
      f"render caption names the figure-1 winner Blue, got {spec['caption']!r}")
path = connection_path(b1, BLUE, N)
check(min(p[0] for p in path) == 0 and max(p[0] for p in path) == N - 1,
      "connection_path for figure 1 spans column 0 to column 5")
check(all(b1[p] == BLUE for p in path), "connection_path returns only BLUE checkers")
# the transposed reading is the one non-automorphism of the board, and it fails
tb1 = {(r, c): v for (c, r), v in b1.items()}
check(not connects(tb1, BLUE, N) and not connects(tb1, RED, N),
      "DISCRIMINATOR: under the transposed reading NOBODY connects in figure 1")
# seat 0 is Red and moves first ("starting with Red")
check(G.initial_state(options={"size": N}).to_move == RED == 0, "Red (seat 0) moves first")

# --------------------------------------------------------------------------
# FIGURE 2 - the crosscut shape
# --------------------------------------------------------------------------
b2 = fig("F2")
check(len(b2) == 4, "figure 2 prints exactly four checkers")
check(len(crosscuts_on_board(b2, N)) == 1, "figure 2 is exactly one crosscut")
check(sorted(b2.values()) == [RED, RED, BLUE, BLUE], "two checkers of each colour")

# --------------------------------------------------------------------------
# FIGURE 3 - "Red ... sizes 1 and 4.  Blue ... sizes 2 and 3."
# --------------------------------------------------------------------------
b3 = fig("F3")
cc = crosscuts_on_board(b3, N)
check(len(cc) == 1, "PREMISE: figure 3 contains exactly one crosscut")
c0, r0 = cc[0]
quad = [(c0, r0), (c0 + 1, r0), (c0, r0 + 1), (c0 + 1, r0 + 1)]
check(sorted(group_size(b3, p) for p in quad if b3[p] == RED) == [1, 4],
      "figure 3: red crosscut groups have sizes 1 and 4")
check(sorted(group_size(b3, p) for p in quad if b3[p] == BLUE) == [2, 3],
      "figure 3: blue crosscut groups have sizes 2 and 3")
check(group_of(b3, quad[0]) | group_of(b3, quad[3]) != group_of(b3, quad[0]),
      "figure 3's two red crosscut checkers are in DIFFERENT groups")

# --------------------------------------------------------------------------
# FIGURE 4 - "at least one"
# --------------------------------------------------------------------------
b4, q4 = fig("F4"), at(1, 3)
check(q4 not in b4, "PREMISE: figure 4's ? square is empty")
check(crosscuts_on_board(b4, N) == [], "PREMISE: figure 4 is crosscut-free")
cr4 = crosscuts_formed(b4, q4[0], q4[1], RED)
check(len(cr4) == 1, "PREMISE: red forms exactly ONE crosscut on figure 4's ?")
nb4, rem4, mine4 = resolve(b4, q4[0], q4[1], RED)
check(mine4 == 3, f"figure 4: red's newly formed crosscut group is size 3, got {mine4}")
check(sorted(group_size({**b4, q4: RED}, p) for p in cr4[0]) == [2, 3],
      "figure 4: the crosscut's blue groups are sizes 2 and 3")
check(nb4 is not None, "figure 4: 'Red can place on the ?'")
check(rem4 == (at(1, 2),), f"figure 4: exactly the size-2 blue checker dies, got {rem4}")

# --------------------------------------------------------------------------
# FIGURE 5 - the same square, judged for each colour
# --------------------------------------------------------------------------
b5, q5 = fig("F5"), at(3, 4)
check(q5 not in b5, "PREMISE: figure 5's ? square is empty")
check(crosscuts_on_board(b5, N) == [], "PREMISE: figure 5 is crosscut-free")
cr5R = crosscuts_formed(b5, q5[0], q5[1], RED)
cr5B = crosscuts_formed(b5, q5[0], q5[1], BLUE)
check(len(cr5R) == 1 and len(cr5B) == 1,
      "PREMISE: each colour forms exactly one crosscut on figure 5's ?")
check(set(cr5R[0]) != set(cr5B[0]),
      "PREMISE: they are DIFFERENT crosscuts (the two colours cannot share one)")
nb5R, _, mine5R = resolve(b5, q5[0], q5[1], RED)
check(mine5R == 3, f"figure 5: red's would-be group is size 3, got {mine5R}")
check(sorted(group_size({**b5, q5: RED}, p) for p in cr5R[0]) == [3, 5],
      "figure 5: the crosscut's blue groups are sizes 3 and 5")
check(nb5R is None, "figure 5: 'Red can't place on the ?'")
nb5B, rem5B, mine5B = resolve(b5, q5[0], q5[1], BLUE)
check(mine5B == 9, f"figure 5: blue's new group is size 9, got {mine5B}")
check(sorted(group_size({**b5, q5: BLUE}, p) for p in cr5B[0]) == [1, 1],
      "figure 5: the crosscut's red groups are sizes 1 and 1")
check(nb5B is not None, "figure 5: 'Blue could place on the ?'")
check(sorted(rem5B) == sorted(cr5B[0]),
      f"figure 5: BOTH size-1 red checkers die (9 > 1 twice), got {rem5B}")

# --------------------------------------------------------------------------
# FIGURES 6a / 6b - the removal rule
# --------------------------------------------------------------------------
b6a, dot = fig("F6a"), at(3, 4)      # 6a is AFTER the placement, BEFORE removal
b6b = fig("F6b")
check(b6a.get(dot) == RED, "PREMISE: figure 6a's yellow dot is on a RED checker")
check(len(b6a) - len(b6b) == 1, "PREMISE: 6a -> 6b loses exactly one checker")
b6 = {k: v for k, v in b6a.items() if k != dot}
check(crosscuts_on_board(b6, N) == [], "PREMISE: the pre-placement position is crosscut-free")
check(len(crosscuts_on_board(b6a, N)) == 1,
      "PREMISE: figure 6a (mid-turn) shows exactly one crosscut")
nb6, rem6, mine6 = resolve(b6, dot[0], dot[1], RED)
check(nb6 is not None, "figures 6a/6b: the placement is legal")
check(mine6 == 4, f"figure 6: red's new crosscut group is size 4, got {mine6}")
check(nb6 == b6b, "figures 6a/6b: the resulting board is EXACTLY figure 6b")
check(len(rem6) == 1, f"'kills a blue checker' - exactly one, got {rem6}")
killed = rem6[0]
check(group_size(b6a, killed) == 2,
      "the dead checker's group had size 2 - so a WHOLE GROUP was not taken")
mate = [p for p in group_of(b6a, killed) if p != killed][0]
check(nb6.get(mate) == BLUE,
      "its group-mate SURVIVES: removal takes crosscut CHECKERS, never groups")
other = [p for p in crosscuts_formed(b6, dot[0], dot[1], RED)[0] if p != killed][0]
check(group_size(b6a, other) == 5,
      "the crosscut's other blue checker is in a size-5 group")
check(nb6.get(other) == BLUE, "and it survives, because 5 is not smaller than 4")
check(crosscuts_on_board(nb6, N) == [],
      "figure 6b is crosscut-free: the crosscut half-cut itself")

# --------------------------------------------------------------------------
# FIGURE 7 - simultaneous crosscuts
# --------------------------------------------------------------------------
b7, q7 = fig("F7"), at(2, 2)
check(q7 not in b7, "PREMISE: figure 7's ? square is empty")
check(crosscuts_on_board(b7, N) == [], "PREMISE: figure 7 is crosscut-free")
cr7 = crosscuts_formed(b7, q7[0], q7[1], RED)
check(len(cr7) == 2, f"figure 7: TWO crosscuts are formed, got {len(cr7)}")
nb7, _, mine7 = resolve(b7, q7[0], q7[1], RED)
check(mine7 == 3, f"figure 7: red's would-be group is size 3, got {mine7}")
after7 = {**b7, q7: RED}
check(sorted(sorted(group_size(after7, p) for p in pair) for pair in cr7) == [[2, 3], [3, 3]],
      "figure 7: the two crosscuts' blue groups are {2,3} and {3,3}")
check(len(set(cr7[0]) & set(cr7[1])) == 1,
      "PREMISE: the two crosscuts SHARE one blue checker (the size-3 group)")
check(nb7 is None, "figure 7: 'This placement is not allowed for Red.'")

# ==========================================================================
# ANCHOR DISCRIMINATING POWER - fifteen wrong readings, scored per figure
# ==========================================================================
def variant_legal(bd, c, r, me, kind):
    """`is_legal` under a deliberately WRONG reading of the rules."""
    enemy = 1 - me
    if kind == "diag8":                      # groups connect diagonally too
        def gsz(b, p):
            who, seen, stack = b[p], {p}, [p]
            while stack:
                cc, rr = stack.pop()
                for dc in (-1, 0, 1):
                    for dr in (-1, 0, 1):
                        nb = (cc + dc, rr + dr)
                        if nb not in seen and b.get(nb) == who:
                            seen.add(nb)
                            stack.append(nb)
            return len(seen)
    else:
        gsz = group_size
    if kind == "orthocut":                   # like colours ORTHOGONALLY opposed
        crosses = []
        for dc, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            if (bd.get((c + dc, r + dr)) == enemy and bd.get((c + dc, r)) == me
                    and bd.get((c, r + dr)) == enemy):
                crosses.append(((c + dc, r + dr), (c, r + dr)))
    else:
        crosses = crosscuts_formed(bd, c, r, me)
    if not crosses:
        return True
    nb = dict(bd)
    nb[(c, r)] = me
    if kind == "before":                     # mover's size read BEFORE placing
        mine = max([gsz(bd, p) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    for p in [(c + dc, r + dr)] if bd.get(p) == me] or [0])
    elif kind == "diagfriend":               # size of the OTHER friendly checker
        mine = max(gsz(nb, (c + dc, r + dr))
                   for dc, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1))
                   if nb.get((c + dc, r + dr)) == me)
    else:
        mine = gsz(nb, (c, r))
    allpairs = [p for pair in crosses for p in pair]
    if kind == "all":                        # larger than ALL of the crosscut's
        return all(all(mine > gsz(nb, p) for p in pair) for pair in crosses)
    if kind == "boardwide-any":              # at least one across ALL crosscuts
        return any(mine > gsz(nb, p) for p in allpairs)
    if kind == "ge":                         # >= instead of >
        return all(any(mine >= gsz(nb, p) for p in pair) for pair in crosses)
    if kind == "first-only":                 # only the first crosscut is judged
        return any(mine > gsz(nb, p) for p in crosses[0])
    if kind == "no-crosscut":                # crosscuts simply forbidden
        return False
    if kind == "free":                       # crosscuts always allowed
        return True
    return all(any(mine > gsz(nb, p) for p in pair) for pair in crosses)


def variant_kill(bd, c, r, me, kind):
    """The removal set under a deliberately WRONG reading."""
    nb = dict(bd)
    nb[(c, r)] = me
    mine = group_size(nb, (c, r))
    crosses = crosscuts_formed(bd, c, r, me)
    kill = set()
    for pair in crosses:
        for p in pair:
            if kind == "whole-group" and group_size(nb, p) < mine:
                kill |= group_of(nb, p)
            elif kind == "both" or (kind == "smallest-only" and
                                    group_size(nb, p) == min(group_size(nb, q) for q in pair)):
                kill.add(p)
            elif kind == "none":
                pass
            elif kind == "correct" and group_size(nb, p) < mine:
                kill.add(p)
    return {k: v for k, v in nb.items() if k not in kill}


WRONG = ["all", "boardwide-any", "ge", "first-only", "no-crosscut", "free",
         "before", "diagfriend", "diag8", "orthocut"]
WRONG_KILL = ["whole-group", "both", "smallest-only", "none"]
# each figure as (board, cell, mover, expected-legal, expected-board-after)
# Legality depends only on the local pattern and on group sizes, never on the
# board edges, so it is invariant under EVERY isometry of the grid.  Figure 7's
# horizontal mirror is therefore a rigorous consequence of figure 7 - and it
# reverses the order in which the two crosscuts are enumerated, which is what
# closes the gap around "only the first crosscut is judged".  Without it NO
# figure kills that reading, because figure 7 happens to print the FAILING
# crosscut first.
b7m = {(N - 1 - c, r): v for (c, r), v in b7.items()}
q7m = (N - 1 - q7[0], q7[1])
check(len(crosscuts_formed(b7m, q7m[0], q7m[1], RED)) == 2,
      "figure 7 mirrored still forms two crosscuts")
check(resolve(b7m, q7m[0], q7m[1], RED)[0] is None,
      "figure 7 mirrored is illegal too (legality is isometry-invariant)")
check([sorted(group_size({**b7m, q7m: RED}, p) for p in pair)
       for pair in crosscuts_formed(b7m, q7m[0], q7m[1], RED)] == [[2, 3], [3, 3]],
      "and the mirror enumerates the PASSING crosscut first")

CASES = {
    "F4": (b4, q4, RED, True, None),
    "F7mirror": (b7m, q7m, RED, False, None),
    "F5R": (b5, q5, RED, False, None),
    "F5B": (b5, q5, BLUE, True, None),
    "F6": (b6, dot, RED, True, b6b),
    "F7": (b7, q7, RED, False, None),
}
# CONSTRUCTED, because no figure can kill it: "remove the enemy crosscut
# checkers which are part of enemy crosscut groups which are SMALLER THAN YOUR
# NEWLY FORMED CROSSCUT GROUP" is a threshold, not a minimum.  Every printed
# example has the crosscut's two enemy groups either equal (fig 5: 1 and 1) or
# with only one of them under the threshold (fig 6: 2 and 5), so "remove only
# the smallest" agrees with the sheet on all seven figures.  Here the ONE
# crosscut's two blue groups have sizes 1 and 2, both under a size-4 attacker,
# and both must die.  (5x5, r growing upwards, ? = the placement at (2,2))
#
#     . B B . .
#     R R ? B .
#     . . R . .
#
CB = {(3, 3): RED, (1, 2): RED, (0, 2): RED, (2, 1): RED,
      (3, 2): BLUE, (2, 3): BLUE, (1, 3): BLUE}
CP = (2, 2)
check(crosscuts_on_board(CB, 5) == [], "PREMISE: the constructed position is crosscut-free")
_cc = crosscuts_formed(CB, CP[0], CP[1], RED)
check(len(_cc) == 1, f"PREMISE: the constructed placement forms ONE crosscut, got {len(_cc)}")
_cb, _crem, _cmine = resolve(CB, CP[0], CP[1], RED)
check(_cmine == 4, f"PREMISE: the attacking red group has size 4, got {_cmine}")
check(sorted(group_size({**CB, CP: RED}, p) for p in _cc[0]) == [1, 2],
      "PREMISE: the crosscut's two blue groups have DIFFERENT sizes 1 and 2, both under 4")
check(_cb is not None and sorted(_crem) == [(2, 3), (3, 2)],
      f"BOTH under-sized blue checkers die, not merely the smallest: {_crem}")
check(_cb.get((1, 3)) == BLUE,
      "and the size-2 group's OTHER checker still survives (checkers, not groups)")
CASES["CONSTRUCTED"] = (CB, CP, RED, True, _cb)

# The MEASURED kill map, pinned so a future edit that silently weakens an
# anchor is caught.  Read it as: which anchors can see each wrong reading.
EXPECTED_KILLS = {
    "all":            ["F4", "F6"],
    "boardwide-any":  ["F7", "F7mirror"],
    "ge":             ["F5R", "F7", "F7mirror"],
    "first-only":     ["F7mirror"],
    "no-crosscut":    ["CONSTRUCTED", "F4", "F5B", "F6"],
    "free":           ["F5R", "F7", "F7mirror"],
    "before":         ["F4"],
    "diagfriend":     ["CONSTRUCTED", "F5R"],
    "diag8":          ["F5R", "F6", "F7", "F7mirror"],
    "orthocut":       ["F7", "F7mirror"],
    "whole-group":    ["CONSTRUCTED", "F6"],
    "both":           ["F6"],
    "smallest-only":  ["CONSTRUCTED"],
    "none":           ["CONSTRUCTED", "F6"],
}

kills = {}
for kind in WRONG:
    killers = [nm for nm, (bd, p, me, legal, _) in CASES.items()
               if variant_legal(bd, p[0], p[1], me, kind) != legal]
    kills[kind] = sorted(killers)
    check(killers, f"DISCRIMINATION GAP: no figure kills the wrong reading {kind!r}")
for kind in WRONG_KILL:
    # only cases whose position-after comes from OUTSIDE the engine count here
    killers = [nm for nm, (bd, p, me, legal, want) in CASES.items()
               if legal and want is not None
               and variant_kill(bd, p[0], p[1], me, kind) != want]
    kills[kind] = sorted(killers)
    check(killers, f"DISCRIMINATION GAP: no figure kills the wrong removal {kind!r}")
# the sanity control: the CORRECT reading must be killed by nothing
check(not [nm for nm, (bd, p, me, legal, _) in CASES.items()
           if variant_legal(bd, p[0], p[1], me, "correct") != legal],
      "control: the shipped reading survives every figure")
check(not [nm for nm, (bd, p, me, legal, want) in CASES.items()
           if legal and want is not None
           and variant_kill(bd, p[0], p[1], me, "correct") != want],
      "control: the shipped removal survives every externally-sourced anchor")
# per-figure kill counts, so the report can quote them
percase = {nm: sum(1 for k in kills.values() if nm in k) for nm in CASES}
NW = len(WRONG) + len(WRONG_KILL)
# MEASURED, not assumed.  The printed figures alone kill 12 of the 14 wrong
# readings; the remaining two need constructed inputs, and this is exactly the
# gap the brief asks to be closed deliberately:
#   * "only the first crosscut is judged" - figure 7 prints the FAILING
#     crosscut first, so it cannot see the difference.  Killed by its mirror.
#   * "remove only the smallest enemy crosscut group" - agrees with all seven
#     figures.  Killed by CONSTRUCTED (enemy groups 1 and 2 under a 4).
figures_only = [k for k, v in kills.items()
                if any(nm in ("F4", "F5R", "F5B", "F6", "F7") for nm in v)]
check(len(figures_only) == NW - 2,
      f"the printed figures alone kill {len(figures_only)} of {NW} wrong readings "
      f"(expected {NW - 2}); blind to {sorted(set(kills) - set(figures_only))}")
check(sorted(set(kills) - set(figures_only)) == ["first-only", "smallest-only"],
      f"the figures' blind spots are exactly first-only and smallest-only, "
      f"got {sorted(set(kills) - set(figures_only))}")
check(kills == EXPECTED_KILLS,
      "the measured kill map matches the recorded one:\n    got      "
      + repr({k: sorted(v) for k, v in sorted(kills.items())})
      + "\n    expected " + repr({k: sorted(v) for k, v in sorted(EXPECTED_KILLS.items())}))
check(all("F6" in kills[k] for k in WRONG_KILL if k != "smallest-only"),
      "figures 6a/6b kill every wrong REMOVAL reading that any figure kills")
check(kills["smallest-only"] == ["CONSTRUCTED"],
      f"'remove only the smallest' is killed ONLY by the constructed position, "
      f"got {kills['smallest-only']}")
check(not any(nm not in ("F6", "CONSTRUCTED") for k in WRONG_KILL for nm in kills[k]),
      "no other anchor touches the removal rule at all - every other figure "
      "stops at legality, and using the engine's own output as the expected "
      "position-after would be circular")
print(f"  anchor kill counts (of {NW} wrong readings):",
      {nm: percase[nm] for nm in sorted(percase)})

# ==========================================================================
# LEMMA 1 (drawlessness, step 1):
#   at most ONE colour can be blocked at any given empty square,
#   so a position with an empty square always has a legal placement for
#   somebody, so "both players stuck" implies a FULL board.
# ==========================================================================
# (a) the arithmetic core, exhaustively.  If Red is blocked at e via one
#     quadrant and Blue via another, the quadrants must be OPPOSITE (they need
#     disjoint pairs of e's orthogonal neighbours, and each pair must be all
#     enemy), which forces
#         1 + max(P,Q) <= N_R <= min(U,V)  and  1 + max(U,V) <= N_B <= min(P,Q)
#     where P,Q are the two red groups and U,V the two blue ones.
bad = 0
for P in range(1, 13):
    for Q in range(1, 13):
        for U in range(1, 13):
            for V in range(1, 13):
                for merged_r in (False, True):
                    for merged_b in (False, True):
                        NR = 1 + (P if merged_r else P + Q)
                        NB = 1 + (U if merged_b else U + V)
                        if NR <= min(U, V) and NB <= min(P, Q):
                            bad += 1
check(bad == 0, f"LEMMA 1 (arithmetic): {bad} size assignments block both colours")
# (b) the geometry + arithmetic together, exhaustively over EVERY 3x3 board
both_blocked = 0
n3cells = [(c, r) for r in range(3) for c in range(3)]
for assign in itertools.product((None, RED, BLUE), repeat=9):
    bd = {p: v for p, v in zip(n3cells, assign) if v is not None}
    for p in n3cells:
        if p in bd:
            continue
        if not is_legal(bd, p[0], p[1], RED) and not is_legal(bd, p[0], p[1], BLUE):
            both_blocked += 1
check(both_blocked == 0,
      f"LEMMA 1 (all 19683 3x3 boards): {both_blocked} squares block both colours")

# --------------------------------------------------------------------------
# `has_placement` is a SEPARATE short-circuiting implementation of
# `placements`, and it is what decides every skipped turn and the stall.  A
# disagreement invents or suppresses a skip - and the sweep's skip assertion
# cannot see it, because that assertion calls the same predicate and so agrees
# with itself.  Random play cannot reach the discriminating case either (it
# needs the FIRST empty square in reading order to be illegal while a later one
# is legal, and the first empty square is usually the a1 corner), so it is
# constructed here: a mutant returning the verdict of the first empty square
# only was the sole survivor of the mutation run until this went in.
# --------------------------------------------------------------------------
for me in (RED, BLUE):
    you = 1 - me
    # a1 = (0,0) is the first square in reading order; make it illegal for `me`
    # via the only 2x2 a corner has, and leave the rest of the board empty.
    HB = {(1, 1): me, (1, 0): you, (0, 1): you}
    check(crosscuts_formed(HB, 0, 0, me) and not is_legal(HB, 0, 0, me),
          f"PREMISE: seat {me} may not play the first empty square (group 1 vs 1)")
    check(is_legal(HB, 3, 3, me), f"PREMISE: seat {me} can still play elsewhere")
    check(has_placement(HB, 5, me) is True,
          f"has_placement must SCAN, not judge the first empty square (seat {me})")
    check((0, 0) not in placements(HB, 5, me) and (3, 3) in placements(HB, 5, me),
          f"placements agrees on that position (seat {me})")
    check(has_placement(HB, 5, me) == bool(placements(HB, 5, me)),
          f"has_placement and placements agree on the constructed position (seat {me})")
# and the genuinely-stuck direction: on a 2x2 the stuck player has NO placement
HS = {(0, 1): RED, (1, 1): BLUE, (1, 0): RED}
check(not has_placement(HS, 2, BLUE) and placements(HS, 2, BLUE) == [],
      "and it reports False when the player really is stuck")
check(has_placement(HS, 2, RED) and placements(HS, 2, RED) == [(0, 0)],
      "while the other colour can still play that same square")

# ==========================================================================
# LEMMA 2 (drawlessness, step 2) - the Crossway theorem:
#   on a FULL, crosscut-free board exactly one player has connected.
#   (With no crosscut, two diagonally adjacent friends on a full board are
#   joined through one of the two squares between them, so orthogonal
#   connectivity coincides with king connectivity and the standard
#   8-vs-4 duality applies.)
# ==========================================================================
for n in (2, 3, 4):
    cells = [(c, r) for r in range(n) for c in range(n)]
    tot = free = 0
    for bits in itertools.product((RED, BLUE), repeat=n * n):
        tot += 1
        b = dict(zip(cells, bits))
        if crosscuts_on_board(b, n):
            continue
        free += 1
        if connects(b, RED, n) == connects(b, BLUE, n):
            check(False, f"LEMMA 2 fails on a full crosscut-free {n}x{n} board: {b}")
            break
    check(free > 0, f"lemma 2: {free}/{tot} full {n}x{n} boards are crosscut-free")
    print(f"  lemma 2 verified on all {free}/{tot} crosscut-free full {n}x{n} boards")

# ==========================================================================
# EXHAUSTIVE SOLVES of the 2x2 and 3x3 boards.  These also prove the state
# graph ACYCLIC (an explicit in-progress set) and the termination monovariant
# strictly increasing on every edge - the two things random play cannot prove.
# ==========================================================================
def solve(n):
    memo, inprog = {}, set()
    stat = dict(states=0, edges=0, draws=0, captures=0, skips=0, simultaneous=0)

    def rec(s):
        k = (tuple(sorted(s.board.items())), s.to_move)
        if k in memo:
            return memo[k]
        check(k not in inprog, f"CYCLE in the {n}x{n} state graph")
        if G.is_terminal(s):
            if s.winner is None:
                stat["draws"] += 1
            memo[k] = G.returns(s)[RED]
            return memo[k]
        inprog.add(k)
        stat["states"] += 1
        if crosscuts_on_board(s.board, n):
            check(False, f"a crosscut survived a turn on {n}x{n}")
        sig = group_size_signature(s.board)
        me, best = s.to_move, None
        for mv in G.legal_moves(s):
            c, r = int(mv.split(",")[0]), int(mv.split(",")[1])
            if len(crosscuts_formed(s.board, c, r, me)) > 1:
                stat["simultaneous"] += 1
            nxt = G.apply_move(s, mv)
            stat["edges"] += 1
            stat["captures"] += 1 if nxt.removed else 0
            stat["skips"] += 1 if nxt.skips > s.skips else 0
            if not group_size_signature(nxt.board) > sig:
                check(False, f"MONOVARIANT did not increase on {n}x{n}: {mv}")
            v = rec(nxt)
            sv = v if me == RED else -v
            best = sv if best is None or sv > best else best
        inprog.discard(k)
        memo[k] = best if me == RED else -best
        return memo[k]

    val = rec(G.initial_state(options={"size": n}))
    return val, stat


for n, want in ((2, 1.0), (3, 1.0)):
    val, stat = solve(n)
    check(val == want, f"{n}x{n} solved value for Red is {want}, got {val}")
    check(stat["draws"] == 0, f"{n}x{n}: {stat['draws']} reachable DRAWS - there must be none")
    check(stat["skips"] > 0, f"{n}x{n}: the skip rule is reached ({stat['skips']} edges)")
    print(f"  {n}x{n} solved: Red wins; {stat['states']} states, {stat['edges']} edges, "
          f"{stat['captures']} capture edges, {stat['skips']} skip edges, "
          f"{stat['simultaneous']} simultaneous-crosscut edges, 0 draws, no cycles")

# ==========================================================================
# CONSTRUCTED: the stalled/draw branch.  It is unreachable (lemmas 1+2), so
# random play can never exercise it - but the code exists, so pin its payoff.
# ==========================================================================
st = HalfcutState(size=5, stalled=True)
check(G.is_terminal(st) and G.returns(st) == [0.0, 0.0],
      "a stalled state is terminal and scores an honest DRAW (never a fake winner)")
check(G.returns(HalfcutState(size=5, winner=RED)) == [1.0, -1.0], "Red win scores +1/-1")
check(G.returns(HalfcutState(size=5, winner=BLUE)) == [-1.0, 1.0], "Blue win scores -1/+1")
# A DECISIVE RESULT OUTRANKS THE STALL BOOKKEEPING.  Reached through apply_move,
# because `winner` is only ever set there.
s = G.initial_state(options={"size": 2})
for mv in ("0,1", "1,1", "1,0"):
    s = G.apply_move(s, mv)
check(s.skips == 1 and s.to_move == RED,
      f"2x2: after 3 plies Blue is stuck and Red plays again (skips={s.skips})")
s2 = G.apply_move(s, "0,0")
check(s2.winner == RED and not s2.stalled,
      "the connecting placement wins even though it also ends all placement")
check(G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0], "and scores as a Red win")
poisoned = replace(s2, skips=10 ** 6, stalled=True)
check(G.returns(poisoned) == [1.0, -1.0],
      "a decisive result OUTRANKS the stall/skip counters")

# ==========================================================================
# RANDOM SWEEP - every invariant of the proof, checked on live positions
# ==========================================================================
rng = random.Random(20230814)
sweep = dict(games=0, plies=0, captures=0, killed=0, maxkill=0, simultaneous=0,
             skips=0, draws=0, wins={RED: 0, BLUE: 0}, maxply=0, empties=0)
for size, games in ((5, 12), (7, 8), (9, 5), (13, 2)):
    for _ in range(games):
        s = G.initial_state(options={"size": size})
        sweep["games"] += 1
        prev_sig = ()
        while not G.is_terminal(s):
            # invariant A: no crosscut ever survives a turn
            if crosscuts_on_board(s.board, size):
                check(False, f"a crosscut survived a turn at ply {s.ply} ({size}x{size})")
            # invariant B: the monovariant strictly increases
            sig = group_size_signature(s.board)
            check(sig >= prev_sig, "the group-size signature never decreases")
            prev_sig = sig
            moves = G.legal_moves(s)
            check(moves, "legal_moves is non-empty on a non-terminal state")
            # invariant C (lemma 1) on EVERY empty square of a live position,
            # and the local predicate agreed with by the whole-board diagnostic
            legal_here = {(c, r) for r in range(size) for c in range(size)
                          if (c, r) not in s.board}
            sweep["empties"] += len(legal_here)
            for p in legal_here:
                lr = is_legal(s.board, p[0], p[1], RED)
                lb = is_legal(s.board, p[0], p[1], BLUE)
                check(lr or lb, f"LEMMA 1 fails at {p} in a live {size}x{size} position")
                nbd, _, _ = resolve(s.board, p[0], p[1], s.to_move)
                if nbd is not None:
                    check(crosscuts_on_board(nbd, size) == [],
                          f"placing at {p} left a crosscut standing")
            check({f"{c},{r}" for (c, r) in placements(s.board, size, s.to_move)} == set(moves),
                  "placements() and legal_moves() agree")
            mv = rng.choice(moves)
            c, r = int(mv.split(",")[0]), int(mv.split(",")[1])
            ncc = len(crosscuts_formed(s.board, c, r, s.to_move))
            before = dict(s.board)
            nxt = G.apply_move(s, mv)
            check(s.board == before, "apply_move does not mutate the input state")
            if ncc > 1:
                sweep["simultaneous"] += 1
                # Two crosscuts formed in OPPOSITE quadrants would make all four
                # of the new checker's orthogonal neighbours enemies, so its
                # group would have size 1 and could not exceed any enemy group:
                # every LEGAL simultaneous crosscut therefore uses ADJACENT
                # quadrants and shares exactly one enemy checker.
                pairs = crosscuts_formed(s.board, c, r, s.to_move)
                check(ncc == 2, f"at most two crosscuts can be legally formed, got {ncc}")
                check(len(set(pairs[0]) & set(pairs[1])) == 1,
                      "a legal simultaneous crosscut shares exactly one enemy checker")
            if nxt.removed:
                sweep["captures"] += 1
                sweep["killed"] += len(nxt.removed)
                sweep["maxkill"] = max(sweep["maxkill"], len(nxt.removed))
                check(all(before.get(p) == 1 - s.to_move for p in nxt.removed),
                      "only ENEMY checkers are ever removed")
                for pair in crosscuts_formed(before, c, r, s.to_move):
                    check(set(pair) & set(nxt.removed),
                          "every crosscut formed loses at least one of ITS OWN "
                          "enemy checkers (two crosscuts may share one, so the "
                          "count of dead checkers can be less than the count of "
                          "crosscuts - figure 7's pair shares a checker)")
            check(nxt.board.get((c, r)) == s.to_move, "the placed checker is on the board")
            if nxt.skips > s.skips:
                sweep["skips"] += 1
                check(not has_placement(nxt.board, size, 1 - s.to_move),
                      "a skip is recorded only when that player really has no placement")
            check(group_size_signature(nxt.board) > sig,
                  f"MONOVARIANT did not increase at ply {s.ply}")
            s = nxt
        sweep["plies"] += s.ply
        sweep["maxply"] = max(sweep["maxply"], s.ply)
        if s.winner is None:
            sweep["draws"] += 1
        else:
            sweep["wins"][s.winner] += 1
            check(connects(s.board, s.winner, size), "the declared winner really connects")
            check(not connects(s.board, 1 - s.winner, size), "and the loser does not")
            wp = connection_path(s.board, s.winner, size)
            check(wp and all(s.board.get(q) == s.winner for q in wp),
                  "the winning chain is made only of the winner's checkers")
            lo, hi = (1, 1) if s.winner == RED else (0, 0)
            check(min(q[lo] for q in wp) == 0 and max(q[hi] for q in wp) == size - 1,
                  "the winning chain really spans the winner's two sides")
            check(all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
                      for a, b in zip(wp, wp[1:])),
                  "consecutive chain squares are ORTHOGONALLY adjacent")
check(sweep["draws"] == 0,
      f"{sweep['draws']} DRAWS in the random sweep - a draw is a bug until proven otherwise")
check(sweep["captures"] > 20 and sweep["skips"] > 0 and sweep["simultaneous"] > 0,
      f"the sweep really reached the rare paths: {sweep}")
check(min(sweep["wins"].values()) > 0, f"both colours win games in the sweep: {sweep['wins']}")
print("  random sweep:", sweep)

# ==========================================================================
# SERIALIZE / DESERIALIZE - compared as STATE OBJECTS, over a whole game, with
# the exact key set pinned.  (`serialize(deserialize(d)) == d` cannot see a
# dropped field: deserialize re-defaults it and serialize re-omits it.)
# ==========================================================================
KEYS = {"size", "board", "to_move", "last", "removed", "winner", "stalled", "ply", "skips"}
seen_shapes = dict(removed=False, skips=False, winner=False, last=False)
rng = random.Random(7)
for size in (2, 2, 5, 7):     # 2x2 is the cheapest way to force skips > 0
    for _ in range(4):
        s = G.initial_state(options={"size": size})
        while True:
            d = G.serialize(s)
            check(set(d) == KEYS, f"serialize emits exactly {sorted(KEYS)}, got {sorted(d)}")
            import json as _json
            _json.dumps(d)
            check(G.deserialize(d) == s, "deserialize(serialize(s)) == s (STATE objects)")
            if s.removed:
                seen_shapes["removed"] = True
            if s.skips:
                seen_shapes["skips"] = True
            if s.winner is not None:
                seen_shapes["winner"] = True
            if s.last is not None:
                seen_shapes["last"] = True
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
check(all(seen_shapes.values()),
      f"the round-trip sweep covered every field shape: {seen_shapes}")
# and a hand-built state with every field non-default
rich = HalfcutState(size=9, board={(0, 0): RED, (1, 1): BLUE}, to_move=BLUE,
                    last=(1, 1), removed=((2, 2), (3, 3)), winner=None,
                    stalled=False, ply=17, skips=3)
check(G.deserialize(G.serialize(rich)) == rich, "round-trip of a fully-populated state")

# ==========================================================================
# describe_move - a public surface that is NOT on the legality path
# ==========================================================================
check(G.describe_move(HalfcutState(size=5), "2,3") == "c4", "plain placement notation")
check(G.describe_move(HalfcutState(size=N, board=b6, to_move=RED),
                      f"{dot[0]},{dot[1]}") == "d2xe2",
      "a capturing placement names the dead checker: "
      + G.describe_move(HalfcutState(size=N, board=b6, to_move=RED), f"{dot[0]},{dot[1]}"))
s = G.initial_state(options={"size": 2})
for mv in ("0,1", "1,1"):
    s = G.apply_move(s, mv)
check(G.describe_move(s, "1,0").endswith("(opponent skipped)"),
      f"a placement that strands the opponent is flagged: {G.describe_move(s, '1,0')!r}")
s = G.apply_move(s, "1,0")
check(G.describe_move(s, "0,0") == "a1#", f"a winning placement is flagged with #")

# ==========================================================================
# RENDER - the declared board must contain every piece, at EVERY offered size,
# from a FAR-CORNER position reached through apply_move (a fresh state has no
# pieces, so the per-size check would be vacuous).
# ==========================================================================
import json                                                     # noqa: E402
man = json.loads((Path(__file__).resolve().parent / "manifest.json").read_text())
SIZES = man["options"]["size"]["choices"]
check(man["options"]["size"]["default"] in SIZES, "the default size is one of the choices")
for size in SIZES:
    s = G.initial_state(options={"size": size})
    # walk the two far corners: Red down the last column, Blue along the top row
    for mv in (f"{size-1},{size-1}", f"{size-1},0", f"0,{size-1}", "0,0"):
        if mv in G.legal_moves(s):
            s = G.apply_move(s, mv)
            if G.is_terminal(s):
                break
    spec = G.render(s)
    bd = spec["board"]
    check(bd["type"] == "square" and bd["width"] == size and bd["height"] == size,
          f"render declares a {size}x{size} square board, got {bd}")
    check(spec["pieces"], f"size {size}: the far-corner position has pieces to draw")
    for pc in spec["pieces"]:
        c, r = int(pc["cell"].split(",")[0]), int(pc["cell"].split(",")[1])
        check(0 <= c < bd["width"] and 0 <= r < bd["height"],
              f"size {size}: piece at {pc['cell']} is outside the declared board")
        check(pc["owner"] in (0, 1), "piece owners are seat indices")
    for hl in spec["highlights"]:
        c, r = int(hl["cell"].split(",")[0]), int(hl["cell"].split(",")[1])
        check(0 <= c < bd["width"] and 0 <= r < bd["height"],
              f"size {size}: highlight at {hl['cell']} is outside the declared board")
        check(hl["kind"] in ("goal", "last-move"),
              f"Board.jsx only draws 'goal' and 'last-move' highlights, got {hl['kind']!r}")
    check(set(bd["edges"]) == {"top", "bottom", "left", "right"}, "all four edges declared")
    json.dumps(spec)
# the corner-touching far position must actually reach the far files/ranks
check(max(int(p["cell"].split(",")[0]) for p in G.render(s)["pieces"]) == SIZES[-1] - 1,
      "the far-corner probe really put a piece on the last column")

# ==========================================================================
# NO `heuristic` IS SHIPPED - assert that, so a future re-add has to come with
# its own measurement rather than sliding in on a plausible-looking 1-ply
# number.  An edge-distance evaluation was written and played head to head
# through MCTSBot against the same bot with a constant-zero evaluation (what a
# game without a heuristic gets): 28/50 at the production shape (9x9,
# max_rollout=50, 0.5 s/move) - indistinguishable from nothing - even though it
# scored 13/14 with the cutoff forced (max_rollout=4).  See rules.md.
# ==========================================================================
check(not hasattr(G, "heuristic"),
      "no heuristic is shipped; if you add one, MEASURE it through MCTSBot "
      "against a constant-zero evaluation and pin the numbers here")
from agp.mcts import MCTSBot                                    # noqa: E402
st = G.initial_state(options={"size": 9})
mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(G, st)
check(mv in G.legal_moves(st),
      "MCTSBot with a FORCED rollout cutoff still returns a legal move "
      "(the no-heuristic fallback path)")

print(("FAILED: %d" % len(FAILS)) if FAILS else "halfcut selftest: all checks passed")
sys.exit(1 if FAILS else 0)
