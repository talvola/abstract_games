"""Diffusion correctness anchor -- pure stdlib, no third-party imports.

Covers, in order:
  A  the frozen 12-pit distribution table (the crux of the ruleset)
  B  the rule sheet's setup and every worked example (Figures 1,3,4,5,6,7,8)
  C  geometry invariants: no wrap, source never refilled, ring = king-neighbours
  D  overflow, stores never capping, 48-stone conservation
  E  TERMINATION: the potential certificate, Psi strictly decreasing, no repeats
  F  a decisive result outranks the ply cap; both-blocks-vacant is unreachable
  G  seat symmetry under the board's 180-degree rotation (so neither seat is
     untested)
  H  serialize/deserialize STATE round-trip + exact key set + non-vacuity
  I  render(): declared dimensions, every piece in bounds, labels correct
  J  heuristic shape (list of num_players payoffs) under a forced rollout cutoff
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                # noqa: E402
from agp.mcts import MCTSBot                                        # noqa: E402

MAN, G = load_from_dir(Path(__file__).resolve().parent)
M = sys.modules[type(G).__module__]        # the LIVE module (synthetic name!)

PITS, IDX, RINGS = M.PITS, M.IDX, M.RINGS
POT, POT_C, PLY_CAP = M.POT, M.POT_C, M.PLY_CAP
BLOCKS, PIT_NAME, MAXPIT = M.BLOCKS, M.PIT_NAME, M.MAXPIT

_checks = [0]


def ok(cond, msg):
    _checks[0] += 1
    if not cond:
        raise AssertionError(msg)


def key(cell):
    return "%d,%d" % cell


def mk(counts, variant="v1", stores=(0, 0), to_move=0, ply=0, last=None):
    """A state from {(col,row): stones}."""
    pits = [0] * 12
    for cell, n in counts.items():
        pits[IDX[cell]] = n
    return M.DiffusionState(pits=tuple(pits), stores=tuple(stores),
                            to_move=to_move, ply=ply, variant=variant, last=last)


def counts_of(s):
    return {p: s.pits[IDX[p]] for p in PITS if s.pits[IDX[p]]}


# ===========================================================================
# A.  The frozen distribution table.
#     Extracted from Figures 3 and 4 of Diffusion_rules.pdf: starting at the
#     most CLOCKWISE adjacent slot, walking COUNTERCLOCKWISE.  Columns 0 and 7
#     are the two slots of the left / right store.
# ===========================================================================
FROZEN_RINGS = {
    # bottom row (rank 1):  E, NE, N, NW, W
    (1, 0): ((2, 0), (2, 1), (1, 1), (0, 1), (0, 0)),
    (2, 0): ((3, 0), (3, 1), (2, 1), (1, 1), (1, 0)),
    (3, 0): ((4, 0), (4, 1), (3, 1), (2, 1), (2, 0)),
    (4, 0): ((5, 0), (5, 1), (4, 1), (3, 1), (3, 0)),
    (5, 0): ((6, 0), (6, 1), (5, 1), (4, 1), (4, 0)),
    (6, 0): ((7, 0), (7, 1), (6, 1), (5, 1), (5, 0)),
    # top row (rank 2):  W, SW, S, SE, E
    (1, 1): ((0, 1), (0, 0), (1, 0), (2, 0), (2, 1)),
    (2, 1): ((1, 1), (1, 0), (2, 0), (3, 0), (3, 1)),
    (3, 1): ((2, 1), (2, 0), (3, 0), (4, 0), (4, 1)),
    (4, 1): ((3, 1), (3, 0), (4, 0), (5, 0), (5, 1)),
    (5, 1): ((4, 1), (4, 0), (5, 0), (6, 0), (6, 1)),
    (6, 1): ((5, 1), (5, 0), (6, 0), (7, 0), (7, 1)),
}
ok(set(FROZEN_RINGS) == set(PITS), "frozen table covers exactly the 12 pits")
for p in PITS:
    ok(RINGS[p] == FROZEN_RINGS[p],
       "ring for %s: %r != frozen %r" % (PIT_NAME[p], RINGS[p], FROZEN_RINGS[p]))

# The move-log notation, frozen as a literal.  PIT_NAME is what describe_move
# prints, and everything else here is keyed by (col,row) tuples -- so without
# this table a reversed file order or a flipped rank number would be entirely
# self-consistent and completely invisible.  Files a-f run left to right; rank 1
# is the BOTTOM row (Player A's near row), rank 2 the top -- the same algebraic
# convention as the AbstractPlay reference implementation.
FROZEN_NAMES = {
    (1, 0): "a1", (2, 0): "b1", (3, 0): "c1",
    (4, 0): "d1", (5, 0): "e1", (6, 0): "f1",
    (1, 1): "a2", (2, 1): "b2", (3, 1): "c2",
    (4, 1): "d2", (5, 1): "e2", (6, 1): "f2",
}
ok(PIT_NAME == FROZEN_NAMES, "pit names %r != frozen %r" % (PIT_NAME, FROZEN_NAMES))
ok(M.NAME_PIT == {v: k for k, v in FROZEN_NAMES.items()}, "NAME_PIT is the inverse")
# and the names really do describe the geometry: rank 1 is the row whose ring
# starts due EAST (Fig. 3), rank 2 the row whose ring starts due WEST (Fig. 4)
for p, nm in FROZEN_NAMES.items():
    first = RINGS[p][0]
    ok((first[0] == p[0] + 1) == (nm[1] == "1"),
       "%s: rank 1 must sow east first, rank 2 west first" % nm)

# ===========================================================================
# B.  Setup + every worked example in the rule sheet.
# ===========================================================================
for variant in ("v1", "v2"):
    s0 = G.initial_state({"variant": variant})
    ok(sum(s0.pits) == 48 and set(s0.pits) == {4}, "Fig1: 12 pits x 4 = 48 stones")
    ok(s0.stores == (0, 0), "Fig1: stores start empty")
    ok(not G.is_terminal(s0), "opening is not terminal (%s)" % variant)
    ok(len(G.legal_moves(s0)) == 12, "12 opening moves (%s)" % variant)
    ok(G.current_player(s0) == 0, "Player A moves first")
    a, b = G.block_counts(s0)
    ok(a == 24 and b == 24, "opening blocks 24/24 (%s)" % variant)

# Block assignment, read off Figures 2 and 7.
ok(BLOCKS["v1"][0] == tuple(p for p in PITS if p[0] <= 3), "Fig2: block A = left 2x3")
ok(BLOCKS["v1"][1] == tuple(p for p in PITS if p[0] >= 4), "Fig2: block B = right 2x3")
ok(BLOCKS["v2"][0] == tuple(p for p in PITS if p[1] == 0), "Fig7: block A = lower 1x6")
ok(BLOCKS["v2"][1] == tuple(p for p in PITS if p[1] == 1), "Fig7: block B = upper 1x6")


def replay(name, before, src, want_counts, want_off, variant="v1", want_ret=None,
           stores=(0, 0), want_stores=None):
    s = mk(before, variant=variant, stores=stores)
    ok(not G.is_terminal(s), "%s: setup position is live" % name)
    ok(key(src) in G.legal_moves(s), "%s: %s is a legal source" % (name, PIT_NAME[src]))
    t = G.apply_move(s, key(src))
    ok(counts_of(t) == {c: n for c, n in want_counts.items() if n},
       "%s: pits %r != expected %r" % (name, counts_of(t), want_counts))
    off = (t.stores[0] - s.stores[0]) + (t.stores[1] - s.stores[1])
    ok(off == want_off, "%s: %d stones to store, expected %d" % (name, off, want_off))
    ok(sum(t.pits) + t.stores[0] + t.stores[1]
       == sum(s.pits) + s.stores[0] + s.stores[1], "%s: conservation" % name)
    ok(t.pits[IDX[src]] == 0, "%s: source pit is emptied and never refilled" % name)
    if want_stores is not None:
        ok(t.stores == tuple(want_stores),
           "%s: stores %r != %r" % (name, t.stores, want_stores))
    if want_ret is not None:
        ok(G.is_terminal(t), "%s: position is terminal" % name)
        ok(G.returns(t) == want_ret,
           "%s: returns %r != %r" % (name, G.returns(t), want_ret))
        ok(G.legal_moves(t) == [], "%s: terminal has no legal moves" % name)
    else:
        ok(not G.is_terminal(t), "%s: position is not terminal" % name)
    return t


# Figure 3 -- 5 stones from d1 fill all five adjacent pits, one each.
replay("Fig3", {(1, 0): 1, (4, 0): 5}, (4, 0),
       {(1, 0): 1, (5, 0): 1, (5, 1): 1, (4, 1): 1, (3, 1): 1, (3, 0): 1}, 0)

# Figure 4 -- the store counts as TWO slots: a2's 5 stones put 2 in the store.
replay("Fig4", {(1, 1): 5, (5, 0): 1}, (1, 1),
       {(5, 0): 1, (1, 0): 1, (2, 0): 1, (2, 1): 1}, 2)

# Figure 5 -- OVERFLOW: the stone bound for the full d2 goes to a store.
replay("Fig5", {(3, 0): 4, (4, 1): 5}, (3, 0),
       {(4, 0): 1, (4, 1): 5, (3, 1): 1, (2, 1): 1}, 1)

# Figure 6 -- Player B wins: the right 2x3 block becomes vacant (and note the
# move was played FROM that block, i.e. you can empty your own block yourself).
t = replay("Fig6", {(3, 1): 1, (3, 0): 1, (4, 1): 2}, (4, 1),
           {(3, 1): 2, (3, 0): 2}, 0, want_ret=[-1.0, 1.0])
ok(G.block_counts(t) == (4, 0), "Fig6: block B empty, block A holds 4")

# Figure 8 -- Diffusion v2: a2's two stones both leave the board, emptying the
# whole upper 1x6 block, so Player B wins.
t = replay("Fig8", {(1, 1): 2, (3, 0): 1, (5, 0): 1}, (1, 1),
           {(3, 0): 1, (5, 0): 1}, 2, variant="v2", want_ret=[-1.0, 1.0])
ok(t.stores == (2, 0), "Fig8: both stones went to the left store")

# the SAME position in v1 is not a win at all -- the variants really differ
t2 = G.apply_move(mk({(1, 1): 2, (3, 0): 1, (5, 0): 1}, variant="v1"), key((1, 1)))
ok(not G.is_terminal(t2), "Fig8 position is NOT terminal under the v1 blocks")

# Player A can win the same way (mirror of Figure 8): scoop f1, both stones go
# to the right store, emptying the lower row.
t = replay("Fig8-mirror", {(6, 0): 2, (3, 1): 1, (5, 1): 1}, (6, 0),
           {(3, 1): 1, (5, 1): 1}, 2, variant="v2", want_ret=[1.0, -1.0])
ok(t.stores == (0, 2), "Fig8-mirror: both stones went to the right store")

# ---------------------------------------------------------------------------
# The 2006/2008 revision of the same rule sheet (recovered from the Wayback
# Machine) prints the stone COUNTS in its figures, which pins the numbers -- and
# the store totals -- exactly.  Its three worked examples, replayed here:
#   "Edge Move"  (Fig. 3): a non-corner pit, no store slots, no overflow
#   "Corner Move"(Fig. 4): the store counting as two slots
#   "Max 5-Count"(Fig. 5): two overflows in one distribution, and the sequence
#                          carrying on past them to the next slot
def row(top, bot):
    d = {}
    for c in range(1, 7):
        d[(c, 1)] = top[c - 1]
        d[(c, 0)] = bot[c - 1]
    return d


replay("2008 Fig3 Edge Move",
       row([4, 4, 4, 4, 4, 4], [4, 4, 4, 4, 4, 4]), (3, 0),
       row([4, 5, 5, 5, 4, 4], [4, 4, 0, 5, 4, 4]), 0, want_stores=(0, 0))
replay("2008 Fig4 Corner Move",
       row([3, 0, 2, 0, 0, 2], [0, 0, 0, 0, 1, 0]), (1, 1),
       row([0, 0, 2, 0, 0, 2], [1, 0, 0, 0, 1, 0]), 2,
       stores=(20, 20), want_stores=(22, 20))
replay("2008 Fig5 Max 5-Count",
       row([2, 0, 1, 4, 0, 1], [0, 0, 5, 5, 0, 0]), (4, 1),
       row([2, 0, 2, 0, 0, 1], [0, 0, 5, 5, 1, 0]), 2,
       stores=(20, 10), want_stores=(20, 12))

# unknown variant is rejected rather than silently defaulting
try:
    G.initial_state({"variant": "v3"})
    ok(False, "unknown variant must raise")
except ValueError:
    ok(True, "unknown variant raises")

# ===========================================================================
# C.  Geometry invariants.
# ===========================================================================
for p in PITS:
    rg = RINGS[p]
    ok(len(rg) == 5, "%s has exactly 5 adjacent slots" % PIT_NAME[p])
    ok(len(set(rg)) == 5, "%s: slots are distinct" % PIT_NAME[p])
    ok(p not in rg, "%s is not in its own ring" % PIT_NAME[p])
    for q in rg:
        dc, dr = q[0] - p[0], q[1] - p[1]
        ok(max(abs(dc), abs(dr)) == 1, "%s: %r is a king-neighbour" % (PIT_NAME[p], q))
        ok(0 <= q[0] <= 7 and 0 <= q[1] <= 1, "%s: %r on the board" % (PIT_NAME[p], q))
    # every king-neighbour of a 2-row cell exists, so the ring is complete
    nbrs = {(p[0] + dc, p[1] + dr) for dc in (-1, 0, 1) for dr in (-1, 0, 1)
            if not (dc == 0 and dr == 0)}
    nbrs = {q for q in nbrs if 0 <= q[0] <= 7 and 0 <= q[1] <= 1}
    ok(set(rg) == nbrs, "%s ring == its full king-neighbourhood" % PIT_NAME[p])
    # the two rows' rings are exact 180-degree rotations of each other
    ok(tuple(M.sigma(q) for q in rg) == RINGS[M.sigma(p)],
       "%s ring is the sigma-image of %s's" % (PIT_NAME[p], PIT_NAME[M.sigma(p)]))
# MAXPIT stones and exactly 5 slots => distribution can never wrap
ok(MAXPIT == 5 and all(len(RINGS[p]) == MAXPIT for p in PITS),
   "max pit (%d) == ring length => no second lap is ever possible" % MAXPIT)

# ===========================================================================
# D.  Overflow / stores.
# ===========================================================================
# a full pit stays at 5 and the stone is banked
t = replay("overflow-1", {(1, 1): 1, (3, 0): 1, (4, 0): 5}, (3, 0),
           {(1, 1): 1, (4, 0): 5}, 1)
# every slot full  ->  all 5 stones leave the board
before = {(3, 0): 5, (4, 0): 5, (4, 1): 5, (3, 1): 5, (2, 1): 5, (2, 0): 5}
after = {c: 5 for c in before if c != (3, 0)}
replay("overflow-all", before, (3, 0), after, 5)
# stores do NOT cap: drive one well past 5
s = mk({(1, 1): 5}, stores=(0, 0), variant="v1")
tot = 0
for _ in range(4):
    s = mk({(1, 1): 5, (6, 0): 1}, stores=s.stores, variant="v1")
    s = G.apply_move(s, key((1, 1)))
    tot += 2
ok(s.stores[0] == tot and tot > MAXPIT,
   "left store holds %d (> %d): stores never overflow" % (s.stores[0], MAXPIT))

# ===========================================================================
# E.  TERMINATION.
# ===========================================================================
# E1. the potential certificate, recomputed from the SHIPPED weights
ok(POT == {p: POT[M.sigma(p)] for p in PITS}, "POT is sigma-symmetric")
ok(min(POT.values()) == 0, "POT >= 0 (so Phi >= 0)")
n_cons, worst = 0, None
for p in PITS:
    for n in range(1, MAXPIT + 1):
        tgt = RINGS[p][:n]
        if any(tc in (0, 7) for tc, _ in tgt):
            continue                          # a store slot: not conserving
        d = sum(POT[q] for q in tgt) - n * POT[p]
        n_cons += 1
        worst = d if worst is None else max(worst, d)
ok(n_cons == 46, "46 conserving-capable (source, count) cases, got %d" % n_cons)
ok(worst <= -1, "every conserving move drops Phi by >= 1 (worst %r)" % worst)
rise = max(sum(POT[q] for q in RINGS[p][:n] if q[0] not in (0, 7)) - n * POT[p]
           for p in PITS for n in range(1, MAXPIT + 1))
ok(rise == 96, "max possible rise in Phi is 96, got %d" % rise)
ok(POT_C == rise + 1, "POT_C (%d) == max rise + 1" % POT_C)
ok(PLY_CAP == POT_C * 48 + 4 * sum(POT.values()) == 5944,
   "PLY_CAP == Psi(opening) == 5944, got %d" % PLY_CAP)


def psi(s):
    return POT_C * sum(s.pits) + sum(s.pits[IDX[p]] * POT[p] for p in PITS)


ok(psi(G.initial_state()) == PLY_CAP, "Psi(opening) == PLY_CAP")

# E2. Psi strictly decreases on EVERY move; no position ever repeats.
NGAMES = 220
longest, shortest, total_plies = 0, 10 ** 9, 0
winner_tally = {0: 0, 1: 0, "draw": 0}
for variant in ("v1", "v2"):
    for g in range(NGAMES):
        rng = random.Random(g * 31 + (0 if variant == "v1" else 7))
        s = G.initial_state({"variant": variant})
        seen = {s.pits}
        prev = psi(s)
        while not G.is_terminal(s):
            mv = rng.choice(G.legal_moves(s))
            snap = json.dumps(G.serialize(s), sort_keys=True)
            t = G.apply_move(s, mv)
            ok(json.dumps(G.serialize(s), sort_keys=True) == snap,
               "apply_move must not mutate its input state")
            cur = psi(t)
            ok(cur <= prev - 1, "Psi did not drop: %d -> %d" % (prev, cur))
            ok(sum(t.pits) + t.stores[0] + t.stores[1] == 48,
               "48 stones conserved (pits %d + stores %r)" % (sum(t.pits), t.stores))
            ok(t.pits[IDX[M._cell(mv)]] == 0, "the scooped pit is left empty")
            ok(t.to_move == 1 - s.to_move, "the turn must pass to the other player")
            ok(t.ply == s.ply + 1, "ply must advance by exactly 1")
            ok(t.last == mv and t.variant == s.variant, "last move / variant carried")
            ok(t.pits not in seen, "a position repeated -- Psi proof is wrong")
            seen.add(t.pits)
            prev = cur
            s = t
            # both blocks vacant must be unreachable from ANY live position
            if not G.is_terminal(s):
                for m2 in G.legal_moves(s):
                    u = G.apply_move(s, m2)
                    ca, cb = G.block_counts(u)
                    ok(not (ca == 0 and cb == 0),
                       "both blocks vacant is reachable: %r" % (u.pits,))
            ok(bool(G.legal_moves(s)) != G.is_terminal(s),
               "legal_moves is non-empty exactly when not terminal")
        ok(s.ply < PLY_CAP, "game ended before the ply cap (%d)" % s.ply)
        ret = G.returns(s)
        ok(sorted(ret) == [-1.0, 1.0], "a finished game is decisive, got %r" % (ret,))
        winner_tally[0 if ret[0] > 0 else 1] += 1
        longest = max(longest, s.ply)
        shortest = min(shortest, s.ply)
        total_plies += s.ply
ok(longest < 300, "longest random game %d plies (expect ~140)" % longest)
ok(winner_tally[0] > 0 and winner_tally[1] > 0, "both seats win some games")

# ===========================================================================
# F.  A decisive result outranks the ply cap; the cap itself is a pure backstop.
# ===========================================================================
won_a = mk({(4, 0): 3}, variant="v1")            # block A vacant -> A wins
ok(G.is_terminal(won_a) and G.returns(won_a) == [1.0, -1.0], "block A vacant: A wins")
won_b = mk({(1, 0): 3}, variant="v1")
ok(G.is_terminal(won_b) and G.returns(won_b) == [-1.0, 1.0], "block B vacant: B wins")
for base, want in ((won_a, [1.0, -1.0]), (won_b, [-1.0, 1.0])):
    for poison in (dict(ply=PLY_CAP), dict(ply=10 ** 9),
                   dict(ply=PLY_CAP, stores=(10 ** 6, 10 ** 6))):
        s = M.DiffusionState(pits=base.pits, stores=poison.get("stores", (0, 0)),
                             to_move=1, ply=poison["ply"], variant="v1")
        ok(G.is_terminal(s), "poisoned state still terminal")
        ok(G.returns(s) == want,
           "DECISIVE RESULT MUST OUTRANK THE PLY CAP: %r with %r" % (G.returns(s), poison))
# and the cap does declare a draw when nothing decisive is on the board
capped = M.DiffusionState(pits=(4,) * 12, stores=(0, 0), to_move=0,
                          ply=PLY_CAP, variant="v1")
ok(G.is_terminal(capped) and G.returns(capped) == [0.0, 0.0],
   "the ply cap is a real (if unreachable) draw backstop")
ok(not G.is_terminal(M.DiffusionState(pits=(4,) * 12, stores=(0, 0), to_move=0,
                                      ply=PLY_CAP - 1, variant="v1")),
   "one ply below the cap is still live (the cap assertion is not vacuous)")
# an honest draw, not a fabricated winner, for the (unreachable) double vacancy
empty = mk({}, variant="v1")
ok(G.is_terminal(empty) and G.returns(empty) == [0.0, 0.0],
   "both blocks vacant scores an honest 0-0 draw")

# The winner is "the owner of the vacant block", FULL STOP -- it must not depend
# on whose turn it happens to be, because a player routinely loses on his own
# move (Fig. 6) and wins on his opponent's.
for base, want in ((won_a, [1.0, -1.0]), (won_b, [-1.0, 1.0])):
    for tm in (0, 1):
        alt = M.DiffusionState(pits=base.pits, stores=(4, 9), to_move=tm,
                               ply=17, variant=base.variant, last="2,1")
        ok(G.is_terminal(alt) and G.returns(alt) == want,
           "the winner must not depend on who is to move (to_move=%d)" % tm)

# apply_move must reject what legal_moves excludes.  The server gates on
# `move in legal_moves`, so this is defence in depth -- but a bot, a replay or a
# future endpoint that skips the gate must not be able to play a null move
# (scooping an empty pit) or a move after the game is over: either would break
# both the termination proof and the no-draws claim.
_open = G.initial_state()
for badmv in ("0,0", "7,1", "9,9", "3,5"):
    try:
        G.apply_move(_open, badmv)
        ok(False, "apply_move accepted the non-pit source %r" % badmv)
    except (ValueError, KeyError):
        ok(True, "apply_move rejects the non-pit source %r" % badmv)
_live = mk({(1, 0): 4, (4, 0): 4}, variant="v1")     # b1 is empty, game is live
ok(not G.is_terminal(_live) and "2,0" not in G.legal_moves(_live), "fixture: b1 empty")
try:
    G.apply_move(_live, "2,0")
    ok(False, "apply_move accepted a scoop of an EMPTY pit (a null move)")
except ValueError:
    ok(True, "apply_move rejects a scoop of an empty pit")
try:
    G.apply_move(won_a, "4,0")
    ok(False, "apply_move accepted a move in a finished game")
except ValueError:
    ok(True, "apply_move rejects a move in a finished game")

# `block_counts` is what win detection reads: check it against an INDEPENDENT
# recomputation straight off the rendered board, per block and per variant.
for variant in ("v1", "v2"):
    rng = random.Random(4242)
    s = G.initial_state({"variant": variant})
    for _ in range(400):
        if G.is_terminal(s):
            s = G.initial_state({"variant": variant})
        rep = G.render(s)
        by_cell = {p["cell"]: p for p in rep["pieces"]}
        brute = [0, 0]
        for seat, cells in enumerate(BLOCKS[variant]):
            for cell in cells:
                brute[seat] += int(by_cell[key(cell)]["label"])
        ok(tuple(brute) == G.block_counts(s),
           "block_counts %r != brute force %r" % (G.block_counts(s), tuple(brute)))
        ok((brute[0] == 0 or brute[1] == 0) == (G.is_terminal(s) and s.ply < PLY_CAP),
           "is_terminal agrees with a brute-force vacancy scan")
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))

# ===========================================================================
# G.  Seat symmetry: the board's 180-degree rotation swaps the two blocks in
#     BOTH variants, so neither seat can go untested.
# ===========================================================================
def mirror(s):
    pits = [0] * 12
    for p in PITS:
        pits[IDX[M.sigma(p)]] = s.pits[IDX[p]]
    return M.DiffusionState(pits=tuple(pits), stores=(s.stores[1], s.stores[0]),
                            to_move=1 - s.to_move, ply=s.ply, variant=s.variant,
                            last=(key(M.sigma(M._cell(s.last))) if s.last else None))


for variant in ("v1", "v2"):
    a, b = BLOCKS[variant]
    ok(tuple(sorted(M.sigma(p) for p in a)) == tuple(sorted(b)),
       "sigma maps block A onto block B (%s)" % variant)
    rng = random.Random(99)
    checked = 0
    for g in range(40):
        s = G.initial_state({"variant": variant})
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            mrs = G.legal_moves(mirror(s))
            ok(sorted(mrs) == sorted(key(M.sigma(M._cell(m))) for m in ms),
               "legal moves do not conjugate under sigma (%s)" % variant)
            ok(G.current_player(mirror(s)) == 1 - G.current_player(s),
               "sigma swaps the player to move")
            ok(G.block_counts(mirror(s)) == G.block_counts(s)[::-1],
               "sigma swaps the block counts")
            ok(G.heuristic(mirror(s)) == G.heuristic(s)[::-1],
               "sigma reverses the heuristic")
            mv = rng.choice(ms)
            ok(G.apply_move(mirror(s), key(M.sigma(M._cell(mv)))) ==
               mirror(G.apply_move(s, mv)),
               "apply_move does not commute with sigma (%s, %s)" % (variant, mv))
            ok(G.describe_move(mirror(s), key(M.sigma(M._cell(mv)))).split()[1:] ==
               G.describe_move(s, mv).split()[1:],
               "describe_move does not conjugate under sigma")
            checked += 1
            s = G.apply_move(s, mv)
        ok(G.returns(mirror(s)) == G.returns(s)[::-1],
           "sigma reverses the result (%s)" % variant)
    ok(checked > 1000, "sigma checked at %d plies (%s)" % (checked, variant))

# ===========================================================================
# H.  serialize / deserialize -- compare STATES, and pin the key set.
# ===========================================================================
KEYS = {"pits", "stores", "to_move", "ply", "variant", "last"}
for variant in ("v1", "v2"):
    for g in range(12):
        rng = random.Random(5000 + g)
        s = G.initial_state({"variant": variant})
        while True:
            d = G.serialize(s)
            ok(set(d) == KEYS, "serialize keys %r != %r" % (set(d), KEYS))
            json.dumps(d)
            back = G.deserialize(d)
            ok(back == s, "STATE round-trip failed: %r != %r" % (back, s))
            ok(G.serialize(back) == d, "serialize(deserialize(d)) != d")
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
# non-vacuity: a DROPPED field must fail loudly, not silently re-default
full = G.serialize(G.apply_move(G.initial_state(), "3,0"))
for k in sorted(KEYS):
    partial = {kk: vv for kk, vv in full.items() if kk != k}
    try:
        G.deserialize(partial)
        ok(False, "deserialize silently tolerated a missing %r" % k)
    except KeyError:
        ok(True, "deserialize rejects a missing %r" % k)
# and every field is load-bearing: changing it changes the state
for k in sorted(KEYS):
    d = dict(full)
    d[k] = ({"pits": [0] * 12, "stores": [7, 9], "to_move": 1 - d["to_move"],
             "ply": d["ply"] + 5, "variant": "v2", "last": "1,1"})[k]
    ok(G.deserialize(d) != G.deserialize(full), "field %r is not load-bearing" % k)

# ===========================================================================
# I.  render(): declared dimensions and in-bounds pieces, from a real position.
# ===========================================================================
for variant in ("v1", "v2"):
    rng = random.Random(77)
    s = G.initial_state({"variant": variant})
    states = [s]
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        states.append(s)
    # ply 0, a mid-game position and the terminal one
    for st in (states[0], states[len(states) // 2], states[-1]):
        rep = G.render(st)
        bd = rep["board"]
        ok(bd["type"] == "square" and bd["width"] == 8 and bd["height"] == 2,
           "render declares an 8x2 square board, got %r" % bd)
        for pc in rep["pieces"]:
            c, r = M._cell(pc["cell"])
            ok(0 <= c < bd["width"] and 0 <= r < bd["height"],
               "piece at %s is outside the declared board" % pc["cell"])
        by_cell = {pc["cell"]: pc for pc in rep["pieces"]}
        ok(len(rep["pieces"]) == 14, "12 pits + 2 store readouts, got %d"
           % len(rep["pieces"]))
        for p in PITS:
            ok(by_cell[key(p)]["label"] == str(st.pits[IDX[p]]),
               "pit %s label != its stone count" % PIT_NAME[p])
        ok(by_cell["0,0"]["label"] == str(st.stores[0]), "left store readout")
        ok(by_cell["7,0"]["label"] == str(st.stores[1]), "right store readout")
        seats = {pc["owner"] for pc in rep["pieces"] if M._cell(pc["cell"])[0] in
                 range(1, 7)}
        ok(seats == {0, 1}, "pits are tinted by their block owner, got %r" % seats)
        ok(set(bd["tints"]) == {key(c) for c in PITS} | {key(c) for c in M.STORE_CELLS},
           "tints cover all 12 pits and all 4 store cells")
        # WHICH pit carries WHICH seat colour.  Asserting only that both seats
        # appear lets the two blocks be swapped wholesale -- the discs would then
        # be drawn in the wrong colour on top of correctly-tinted cells.
        for seat, cells in enumerate(BLOCKS[variant]):
            for cell in cells:
                ok(by_cell[key(cell)]["owner"] == seat,
                   "pit %s is drawn as seat %r, but its block belongs to seat %d"
                   % (PIT_NAME[cell], by_cell[key(cell)]["owner"], seat))
                ok(bd["tints"][key(cell)] == bd["tints"][key(cells[0])],
                   "pit %s tinted unlike the rest of its block" % PIT_NAME[cell])
        ok(bd["tints"][key(BLOCKS[variant][0][0])]
           != bd["tints"][key(BLOCKS[variant][1][0])],
           "the two blocks must be tinted differently")
        # a store belongs to NEITHER player (seat 2 = the neutral colour)
        for c in ("0,0", "7,0"):
            ok(by_cell[c]["owner"] == 2,
               "store readout %s must be neutral, got owner %r"
               % (c, by_cell[c]["owner"]))
        # the caption must tell the mover to empty HIS OWN block -- naming the
        # opponent's would instruct the player to lose.
        cap = rep["caption"]
        ca_, cb_ = G.block_counts(st)
        if not G.is_terminal(st):
            ok(M.SIDE[st.to_move] + " to move" in cap, "caption names the mover: %r" % cap)
            ok(M.BLOCK_NAME[variant][st.to_move] in cap
               and M.BLOCK_NAME[variant][1 - st.to_move] not in cap,
               "caption must name the MOVER'S OWN block: %r" % cap)
        elif ca_ == 0 and cb_ != 0:
            ok("Player A wins" in cap and M.BLOCK_NAME[variant][0] in cap,
               "terminal caption must credit block A's owner: %r" % cap)
        elif cb_ == 0 and ca_ != 0:
            ok("Player B wins" in cap and M.BLOCK_NAME[variant][1] in cap,
               "terminal caption must credit block B's owner: %r" % cap)
        json.dumps(rep)
    # every legal move has a description
    for st in states[:-1]:
        for mv in G.legal_moves(st):
            src = M._cell(mv)
            nxt = G.apply_move(st, mv)
            off = ((nxt.stores[0] - st.stores[0]) + (nxt.stores[1] - st.stores[1]))
            want = "%s sows %d" % (PIT_NAME[src], st.pits[IDX[src]])
            if off:
                want += " (%d to store)" % off
            ok(G.describe_move(st, mv) == want,
               "describe_move %r != %r" % (G.describe_move(st, mv), want))

# ===========================================================================
# J.  The store split is immaterial; heuristic shape under a forced cutoff.
# ===========================================================================
rng = random.Random(11)
s = G.initial_state()
for _ in range(60):
    if G.is_terminal(s):
        break
    for stores in ((0, 0), (48, 0), (0, 48), (7, 9)):
        alt = M.DiffusionState(pits=s.pits, stores=stores, to_move=s.to_move,
                               ply=s.ply, variant=s.variant, last=s.last)
        ok(G.legal_moves(alt) == G.legal_moves(s), "store split changed legal_moves")
        ok(G.is_terminal(alt) == G.is_terminal(s), "store split changed is_terminal")
        ok(G.returns(alt) == G.returns(s), "store split changed returns")
    s = G.apply_move(s, rng.choice(G.legal_moves(s)))

for variant in ("v1", "v2"):
    rng = random.Random(3)
    s = G.initial_state({"variant": variant})
    for _ in range(30):
        h = G.heuristic(s)
        ok(isinstance(h, list) and len(h) == G.num_players,
           "heuristic must be a LIST of num_players payoffs, got %r" % (h,))
        ok(all(isinstance(v, float) and -1.0 <= v <= 1.0 for v in h),
           "heuristic payoffs out of range: %r" % (h,))
        ok(abs(h[0] + h[1]) < 1e-9, "heuristic is zero-sum")
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))

# ...and its DIRECTION, which shape/range/zero-sum checks cannot see.  The goal
# is to empty YOUR OWN block, so the seat with fewer stones in its own block must
# score higher.  A sign-flipped (or constant) heuristic still passes every check
# above, still conjugates under sigma, and simply makes the MCTS bot play to lose.
for variant in ("v1", "v2"):
    a_cells, b_cells = BLOCKS[variant]
    lop = mk({a_cells[0]: 1, b_cells[0]: 5, b_cells[1]: 5, b_cells[2]: 4},
             variant=variant)
    ok(not G.is_terminal(lop), "heuristic fixture is live (%s)" % variant)
    h = G.heuristic(lop)
    ok(h[0] > 0.4 > -0.4 > h[1],
       "heuristic must favour the seat whose OWN block is emptier: %r (%s)"
       % (h, variant))
    hm = G.heuristic(mirror(lop))
    ok(hm[1] > 0.4 > -0.4 > hm[0],
       "...and the mirror image must favour the other seat: %r (%s)" % (hm, variant))
    # strictly monotone: every extra stone in your own block must hurt you
    prev = None
    for n in range(1, MAXPIT + 1):
        v = G.heuristic(mk({a_cells[0]: n, b_cells[0]: MAXPIT}, variant=variant))[0]
        ok(prev is None or v < prev,
           "seat 0's eval must strictly fall as its own block fills (%d stones, %s)"
           % (n, variant))
        prev = v
# force the rollout cutoff so a malformed heuristic cannot hide
mv = MCTSBot(random.Random(1), iterations=40, max_rollout=4).select(
    G, G.initial_state())
ok(mv in G.legal_moves(G.initial_state()), "MCTS with max_rollout=4 picks a legal move")

print("diffusion selftest OK  (%d assertions; random games: %d..%d plies, "
      "avg %.1f; A/B wins %d/%d)"
      % (_checks[0], shortest, longest, total_plies / (2 * NGAMES),
         winner_tally[0], winner_tally[1]))
