"""Pure-stdlib selftest for Tâb (Lane's 1820s Cairo ruleset).

Anchors: the stick-dice value mapping (0/1/2/3/4 whites -> 6/1/2/3/4) and the
extra-throw chain (1/4/6 continue, 2/3 end it); the exact boustrophedon track
for BOTH seats (frozen successor tables incl. the branch square, verified
against Lane's lettered diagram and Ludii's Tab.lud track strings);
conversion only by tâb, foremost-Christian-first, advancing one square;
enemy-home-row entry only while enemy pieces remain there and only once per
piece; the freeze of pieces parked in the enemy home row (own home row must
empty, single-'eggeh exception); capture of whole enemy piles; stacking,
tâb-only splitting, and stack reduction on re-entering a passed row (with the
optional-pass escape); win by total capture reached VIA apply_move; honest
no-progress draw [0,0]; serialize round-trip; seeded determinism; random
playouts to a terminal with invariants.

Run: cd engine && PYTHONPATH=. python3 games/tab/selftest.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.tab.game import (Tab, TabState, THROW_VALUE, EXTRA, PLY_CAP,
                            NO_PROGRESS_CAP, HOME_ROW, DEFAULT_N)

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


G = Tab()


def mk(groups0, groups1, bank, to_move=0, N=9, np=0, ply=0):
    """Build a state from terse group tuples (cell, count, conv, visited,
    entered)."""
    def gl(lst):
        return [{"cell": c, "count": n, "conv": cv,
                 "visited": frozenset(vis), "entered": ent}
                for (c, n, cv, vis, ent) in lst]
    return TabState(groups={0: gl(groups0), 1: gl(groups1)},
                    roll=tuple(bank), bank=tuple(bank),
                    to_move=to_move, ply=ply, np=np, winner=None, N=N)


def christians(seat, N=9, cols=None):
    r = HOME_ROW[seat]
    return [((c, r), 1, False, {r}, False) for c in (cols or range(N))]


# ---------------------------------------------------------------- dice ------
check(THROW_VALUE == {0: 6, 1: 1, 2: 2, 3: 3, 4: 4},
      "throw value mapping (whites up -> value)")
check(EXTRA == {1, 4, 6}, "extra-throw set is {tab, 4, 6}")
rng = random.Random(123)
seen = set()
for _ in range(200):
    ch = Tab._chain(rng)
    seen.update(ch)
    check(ch[-1] in (2, 3), "a chain ends with 2 or 3")
    check(all(v in (1, 4, 6) for v in ch[:-1]),
          "all non-final chain values are extra throws")
check(seen == {1, 2, 3, 4, 6}, "all five throw values occur")

# ---------------------------------------------------------------- track -----
# Frozen successor tables for N=9, cross-checked against Lane's diagram
# (A..I / K..S / k..s / a..i) and Ludii Tab.lud's track strings.
EXPECT = {
    (0, (0, 3)): [((1, 3), False)],
    (0, (8, 3)): [((8, 2), False)],          # home exit "I -> K"
    (0, (8, 2)): [((7, 2), False)],          # "K -> L" (right-to-left)
    (0, (0, 2)): [((0, 1), False)],          # "S -> k"
    (0, (0, 1)): [((1, 1), False)],          # "k -> l" (left-to-right)
    (0, (8, 1)): [((8, 2), False), ((8, 0), True)],   # branch "s -> K | a"
    (0, (8, 0)): [((7, 0), False)],          # enemy row "a -> b"
    (0, (0, 0)): [((0, 1), False)],          # enemy row exit "i -> k"
    (1, (8, 0)): [((7, 0), False)],
    (1, (0, 0)): [((0, 1), False)],          # home exit
    (1, (0, 1)): [((1, 1), False)],
    (1, (8, 1)): [((8, 2), False)],
    (1, (8, 2)): [((7, 2), False)],
    (1, (0, 2)): [((0, 1), False), ((0, 3), True)],   # branch
    (1, (0, 3)): [((1, 3), False)],          # enemy row
    (1, (8, 3)): [((8, 2), False)],          # enemy row exit
}
for (seat, cell), want in EXPECT.items():
    got = Tab._succ(9, seat, cell)
    check(got == want, f"successor of {cell} for seat {seat}: {got} != {want}")

# both seats share ONE directed middle loop of length 2N
cell = (8, 2)
loop = []
for _ in range(18):
    loop.append(cell)
    cell = Tab._succ(9, 0, cell)[0][0]
check(cell == (8, 2) and len(set(loop)) == 18,
      "the middle loop is a single 18-cell cycle")
cell1 = (0, 1)
loop1 = []
for _ in range(18):
    loop1.append(cell1)
    cell1 = Tab._succ(9, 1, cell1)[0][0]   # [0] = the loop continuation
check(cell1 == (0, 1) and set(loop1) == set(loop),
      "seat 1 walks the same 18-cell loop in the same direction")

# ---------------------------------------------------------- conversion ------
s = mk(christians(0), christians(1), bank=(2, 3))
check(G.legal_moves(s) == ["pass"],
      "no tab in the bank + no Muslims -> forced pass")
s = mk(christians(0), christians(1), bank=(1, 2))
check(G.legal_moves(s) == ["8,3>8,2"],
      "a tab converts ONLY the foremost Christian (Lane: 'commence with the "
      "kelb in beyt I'); the 2 is unusable until then")
s2 = G.apply_move(s, "8,3>8,2", random.Random(0))
g = next(g for g in s2.groups[0] if g["cell"] == (8, 2))
check(g["conv"] and g["visited"] == frozenset({3, 2}),
      "conversion makes a Muslim, advancing one square (I -> K)")
check(s2.to_move == 0 and s2.bank == (2,),
      "banked values are spent one per ply by the same player")
# Lane's opening example: tab,4,2 from beyt I ends on Q = 7th square from I
s = mk(christians(0), christians(1), bank=(1, 4, 2))
s = G.apply_move(s, "8,3>8,2", random.Random(0))
mv = [m for m in G.legal_moves(s) if m.startswith("8,2>")]
s = G.apply_move(s, "8,2>4,2", random.Random(0))          # the 4
s = G.apply_move(s, "4,2>2,2", random.Random(0))          # the 2
check(any(g["cell"] == (2, 2) for g in s.groups[0]),
      "Lane's worked opening: tab+4+2 carries the kelb from I to Q")

# foremost-first for seat 1 (mirror): foremost = lowest column
s = mk(christians(0), christians(1, cols=[2, 5, 7]), bank=(1,), to_move=1)
check(G.legal_moves(s) == ["2,0>1,0"],
      "seat 1's foremost Christian is the lowest-column one")

# free order: values may be spent in any order (Lane's capture example)
s = mk([((4, 2), 1, True, {3, 2}, False)] + christians(0, cols=[0]),
       christians(1), bank=(1, 4, 2))
lm = G.legal_moves(s)
check("4,2>3,2" in lm and "4,2>0,2" in lm and "4,2>2,2" in lm,
      "all banked values are playable at once, any order")

# ------------------------------------------------- enemy-row entry ----------
# at the branch with a tab: both continuation and entry offered
s = mk([((8, 1), 1, True, {3, 2, 1}, False)], christians(1), bank=(1,))
lm = G.legal_moves(s)
check(sorted(lm) == ["8,1>8,0", "8,1>8,2"],
      "branch square: continue the loop OR enter the enemy home row")
s2 = G.apply_move(s, "8,1>8,0", random.Random(0))
g = next(g for g in s2.groups[0] if g["cell"] == (8, 0))
check(g["entered"], "entering the enemy home row spends the once-only right")

# entry barred when the enemy home row holds no enemy piece
s = mk([((8, 1), 1, True, {3, 2, 1}, False)],
       [((4, 1), 1, True, {0, 1}, False)], bank=(1,))
check(G.legal_moves(s) == ["8,1>8,2"],
      "no enemy piece in their home row -> entry barred (Lane/Ludii)")

# entry barred for a piece that has already been there
s = mk([((8, 1), 1, True, {3, 2, 1, 0}, True)], christians(1), bank=(1,))
check(G.legal_moves(s) == ["8,1>8,2"],
      "a piece may enter the enemy home row only once")

# ---------------------------------------------------------- freeze ----------
# a piece parked in the enemy home row is frozen while own home row occupied
s = mk([((4, 0), 1, True, {3, 2, 1, 0}, True)] + christians(0, cols=[0]),
       christians(1, cols=[1, 2]), bank=(2,))
check(G.legal_moves(s) == ["pass"],
      "piece in enemy home row frozen while own home row is occupied")
s = mk([((4, 0), 1, True, {3, 2, 1, 0}, True)],
       christians(1, cols=[1, 2]), bank=(2,))
check(G.legal_moves(s) == ["4,0>2,0"],
      "freeze lifts when own home row is empty")
s = mk([((4, 0), 1, True, {3, 2, 1, 0}, True),
        ((3, 3), 2, True, {3}, False)],
       christians(1, cols=[1, 2]), bank=(2,))
check("4,0>2,0" in G.legal_moves(s),
      "the single-'eggeh exception lifts the freeze (Lane/Ludii)")
# ... and moving in the enemy row can capture the Christians camped there
s = mk([((4, 0), 1, True, {3, 2, 1, 0}, True)],
       christians(1, cols=[1, 2]), bank=(2,))
s2 = G.apply_move(s, "4,0>2,0", random.Random(0))
check(G._total(s2.groups[1]) == 1,
      "a raid inside the enemy home row captures a sleeping Christian")

# -------------------------------------------------------- capture -----------
s = mk([((4, 2), 1, True, {3, 2}, False)],
       [((2, 2), 2, True, {0, 1, 2}, False), ((5, 1), 1, True, {0, 1}, False)],
       bank=(2,))
s2 = G.apply_move(s, "4,2>2,2", random.Random(0))
check(G._total(s2.groups[1]) == 1,
      "landing on an enemy pile captures the WHOLE pile")

# --------------------------------------------------------- stacks -----------
s = mk([((4, 2), 1, True, {3, 2}, False), ((2, 2), 1, True, {3, 2}, False)],
       christians(1), bank=(2,))
s2 = G.apply_move(s, "4,2>2,2", random.Random(0))
pile = next(g for g in s2.groups[0] if g["cell"] == (2, 2))
check(pile["count"] == 2 and len(s2.groups[0]) == 1,
      "landing on an own Muslim unites the pieces into one stack")
spec = G.render(s2)
check(any(p.get("stack") == [0, 0] for p in spec["pieces"]),
      "a stack renders with the piece.stack tower primitive")

# a tab on a stack offers whole-stack vs split; other values move it whole
s = mk([((4, 2), 2, True, {3, 2}, False)], christians(1), bank=(1, 3))
lm = G.legal_moves(s)
check("4,2>3,2=ALL" in lm and "4,2>3,2=ONE" in lm and "4,2>1,2" in lm,
      "tab on a stack -> whole-stack or split choice; a 3 moves it whole")
s2 = G.apply_move(s, "4,2>3,2=ONE", random.Random(0))
cnts = sorted((g["cell"], g["count"]) for g in s2.groups[0])
check(cnts == [((3, 2), 1), ((4, 2), 1)],
      "splitting detaches one kelb, the rest stay put")

# a 2-step stack move may NOT split (tab only)
s = mk([((4, 2), 2, True, {3, 2}, False)], christians(1), bank=(2,))
check(G.legal_moves(s) == ["4,2>2,2"],
      "stacks move as one; only a tab can divide them (Lane)")

# ------------------------------------------------------- reduction ----------
# a stack moved back into a row it has passed through is cut to one kelb,
# and such a move is optional (pass offered when it is the only option)
s = mk([((0, 2), 2, True, {3, 2, 1}, False)], christians(1), bank=(2,))
lm = G.legal_moves(s)
check(lm == ["0,2>1,1", "pass"],
      "only-reduction-moves -> pass offered (Lane: 'he need not avail "
      "himself of such a throw')")
s2 = G.apply_move(s, "0,2>1,1", random.Random(0))
pile = next(g for g in s2.groups[0] if g["cell"] == (1, 1))
check(pile["count"] == 1 and G._total(s2.groups[0]) == 1,
      "the reduced stack keeps one kelb; the rest leave the board")
# a single kelb is never reduced
s = mk([((0, 2), 1, True, {3, 2, 1}, False)], christians(1), bank=(2,))
check(G.legal_moves(s) == ["0,2>1,1"],
      "a lone kelb re-circulates freely (no reduction, no pass)")
s2 = G.apply_move(s, "0,2>1,1", random.Random(0))
check(G._total(s2.groups[0]) == 1, "lone kelb survives re-circulation")
# a stack in fresh rows is not reduced
s = mk([((8, 3), 2, True, {3}, False)], christians(1), bank=(3,))
s2 = G.apply_move(s, "8,3>6,2", random.Random(0))
check(next(g for g in s2.groups[0])["count"] == 2,
      "a stack entering a NEW row is not reduced")

# --------------------------------------------- landing on own Christian -----
s = mk([((3, 3), 1, True, {3}, False)] + christians(0, cols=[5]),
       christians(1), bank=(2,))
check(G.legal_moves(s) == ["pass"],
      "may not land on one's own unconverted Christian")

# --------------------------------------------------- win via apply_move -----
s = mk([((4, 2), 1, True, {3, 2}, False)],
       [((2, 2), 3, True, {0, 1, 2}, False)], bank=(2,))
s2 = G.apply_move(s, "4,2>2,2", random.Random(0))
check(s2.winner == 0 and G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0],
      "capturing the last enemy pile wins, reached via apply_move")

# --------------------------------------------------------- honest draw ------
s = mk([((4, 2), 1, True, {3, 2}, False)],
       [((5, 1), 1, True, {0, 1}, False)], bank=(3,),
       np=NO_PROGRESS_CAP - 1)
s2 = G.apply_move(s, "4,2>1,2", random.Random(0))
check(s2.winner == "draw" and G.returns(s2) == [0.0, 0.0],
      "no-progress cap yields an honest DRAW [0,0]")

# --------------------------------------------------- serialize / determinism
s = G.initial_state({"size": 9}, random.Random(42))
d = G.serialize(s)
check(G.serialize(G.deserialize(d)) == d, "serialize round-trips")


def scripted(seed):
    rng = random.Random(seed)
    s = G.initial_state({"size": 9}, random.Random(seed + 1))
    hist = []
    for _ in range(120):
        if G.is_terminal(s):
            break
        mv = G.legal_moves(s)[0]
        s = G.apply_move(s, mv, rng)
        hist.append(G.serialize(s))
    return hist


check(scripted(7) == scripted(7), "seeded play is deterministic")

# ------------------------------------------------------- random playouts ----
t0 = __import__("time").time()
for i in range(220):
    N = (7, 9, 15)[i % 3]
    rng = random.Random(1000 + i)
    s = G.initial_state({"size": N}, rng)
    for _ in range(PLY_CAP + 10):
        if G.is_terminal(s):
            break
        lm = G.legal_moves(s)
        check(len(lm) > 0, "non-terminal state has legal moves")
        for m in lm:
            ok = m == "pass" or all(
                seg.split("=")[0].count(",") == 1 for seg in m.split(">"))
            check(ok, f"move string parses: {m}")
        s = G.apply_move(s, rng.choice(lm), rng)
        for seat in (0, 1):
            for g in s.groups[seat]:
                if not g["conv"]:
                    check(g["count"] == 1 and g["cell"][1] == HOME_ROW[seat],
                          "Christians never move nor stack")
                c, r = g["cell"]
                check(0 <= c < N and 0 <= r < 4, "pieces stay on the board")
    check(G.is_terminal(s), f"playout {i} terminates")
    check(s.winner in (0, 1, "draw"), "winner is a seat or an honest draw")
    check(G._total(s.groups[0]) <= N and G._total(s.groups[1]) <= N,
          "piece counts never grow")
    d = G.serialize(s)
    check(G.serialize(G.deserialize(d)) == d, "terminal state round-trips")
print(f"playouts: 220 games in {__import__('time').time() - t0:.1f}s")

# ----------------------------------------------------------------------------
if FAILS:
    print(f"\n{len(FAILS)} FAILURES")
    sys.exit(1)
print("tab selftest: all checks passed")
