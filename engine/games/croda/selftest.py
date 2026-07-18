#!/usr/bin/env python3
"""Standalone correctness self-test for Croda (Ljuban Dedić, 1995).

Run from engine/ with:  PYTHONPATH=. python3 games/croda/selftest.py

Anchors:
  1. Opening position (24 men each on the first three ranks) and White's exact
     first-move count, derived by hand: only the 8 rank-3 men can move, each
     with 3 forward steps (straight + 2 diagonals) except the a/h-file men
     (2 each, one diagonal off-board) = 6*3 + 2*2 = 22. perft(2) = 484 by
     colour symmetry.
  2. The printed "Coup Turc in Croda" problem from Christian Freeling's
     article "International Checkers Versus Croda", Abstract Games #9 (Spring
     2002) p.5-6, replayed move for move to the printed winning line:
       1.f1-e2 a5:d5  2.c2-d3 d5:d1:h1:h3:e3  3.e2:e4:e6:c6:c8+
     Both Black captures and White's final chain are forced (unique maximal),
     exercising deferred removal, no-double-jump blocking, king routing and
     end-of-sequence promotion in one published position.
  3. Rule units: majority capture forced over a smaller capture; man captures
     orthogonally backward but never diagonally; king long-leap multi-turn
     chain; the Coup Turc blocking mechanism (an already-jumped piece blocks
     a further jump that immediate removal would allow); a man jumping ON and
     OFF the far rank mid-capture does not promote; a fully blocked player
     loses.
  4. Random playouts all reach a terminal.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import random
import sys

from games.croda.game import Croda, CrodaState, PLY_CAP

G = Croda()


def perft(state, depth):
    if depth == 0:
        return 1
    total = 0
    for m in G.legal_moves(state):
        total += perft(G.apply_move(state, m), depth - 1)
    return total


def board_from(spec, to_move=0):
    return CrodaState(board=dict(spec), to_move=to_move)


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def ncaps(m):
    return len(m.split(">")) - 1


# ---------------------------------------------------------------------------
# 1. Opening position + hand-derived first-move count
# ---------------------------------------------------------------------------
init = G.initial_state()
if len(init.board) != 48:
    fail(f"opening has {len(init.board)} pieces, expected 48")
if sum(1 for v in init.board.values() if v == (0, "m")) != 24:
    fail("White does not have 24 men")
if sum(1 for v in init.board.values() if v == (1, "m")) != 24:
    fail("Black does not have 24 men")

moves = set(G.legal_moves(init))
expect = set()
for c in range(8):
    expect.add(f"{c},2>{c},3")                # straight forward
    if c > 0:
        expect.add(f"{c},2>{c - 1},3")        # diagonal forward-left
    if c < 7:
        expect.add(f"{c},2>{c + 1},3")        # diagonal forward-right
if moves != expect:
    fail(f"opening moves != hand-derived 22-move set; got {sorted(moves)}")
if len(moves) != 22:
    fail(f"opening move count {len(moves)}, expected 22")
print(f"opening: 48 pieces, {len(moves)} first moves  OK (derived 22)")

if perft(init, 2) != 484:
    fail(f"perft(2) = {perft(init, 2)}, expected 22*22 = 484 by symmetry")
print("perft(2) = 484  OK")


# ---------------------------------------------------------------------------
# 2. The "Coup Turc in Croda" (Abstract Games #9, p.5-6) — replay to the win
# ---------------------------------------------------------------------------
# Diagram (pixel-verified from the magazine PDF):
#   Black: king a5; men c7, d6, e5, h4.
#   White: men c2, c5, e1, f1, f3, h2.  White to play and win.
# Files a-h = col 0-7, rank n = row n-1.
pos = board_from({
    (0, 4): (1, "k"),                                              # a5 K
    (2, 6): (1, "m"), (3, 5): (1, "m"), (4, 4): (1, "m"), (7, 3): (1, "m"),
    (2, 1): (0, "m"), (2, 4): (0, "m"), (4, 0): (0, "m"),
    (5, 0): (0, "m"), (5, 2): (0, "m"), (7, 1): (0, "m"),
})

# 1. f1-e2 (a quiet diagonal-forward man step; no White capture exists)
mv = "5,0>4,1"
lm = G.legal_moves(pos)
if any(ncaps(m) > 1 for m in lm):
    fail("unexpected White capture available in the problem position")
if mv not in lm:
    fail(f"1.f1-e2 not legal; legal = {sorted(lm)}")
if G.describe_move(pos, mv) != "f1-e2":
    fail(f"describe_move(f1-e2) = {G.describe_move(pos, mv)}")
pos = G.apply_move(pos, mv)

# 1... a5:d5 — Black's ONLY legal move (king short chain: over c5, e5 blocks)
lm = G.legal_moves(pos)
if lm != ["0,4>3,4"]:
    fail(f"1...a5:d5 not forced; legal = {sorted(lm)}")
if G.describe_move(pos, "0,4>3,4") != "a5xd5":
    fail("describe_move(a5xd5) wrong")
pos = G.apply_move(pos, "0,4>3,4")
if (2, 4) in pos.board or pos.board.get((3, 4)) != (1, "k"):
    fail("a5xd5 did not capture c5 / land the king on d5")

# 2. c2-d3
lm = G.legal_moves(pos)
if "2,1>3,2" not in lm:
    fail(f"2.c2-d3 not legal; legal = {sorted(lm)}")
pos = G.apply_move(pos, "2,1>3,2")

# 2... d5:d1:h1:h3:e3 — the UNIQUE maximal (4-piece) capture. The chain stops
# on e3: e1 (already captured, not yet removed) blocks capturing e2 southward,
# and d3/f3 (captured) block west/east — the Coup Turc.
lm = G.legal_moves(pos)
want = "3,4>3,0>7,0>7,2>4,2"
if lm != [want]:
    fail(f"2...d5:d1:h1:h3:e3 not the unique forced capture; legal = {sorted(lm)}")
if G.describe_move(pos, want) != "d5xd1xh1xh3xe3":
    fail("describe_move(d5xd1xh1xh3xe3) wrong")
pos = G.apply_move(pos, want)
for sq in [(3, 2), (4, 0), (7, 1), (5, 2)]:
    if sq in pos.board:
        fail(f"2...d5:d1:h1:h3:e3 left captured piece on {sq}")
if pos.board.get((4, 2)) != (1, "k"):
    fail("Black king did not stop on e3")
if [sq for sq, v in pos.board.items() if v[0] == 0] != [(4, 1)]:
    fail("White should have exactly the e2 man left")

# 3. e2:e4:e6:c6:c8+ — White's man chain-captures king e3 and men e5, d6, c7,
# ends on the far rank and only THEN promotes.
lm = G.legal_moves(pos)
want = "4,1>4,3>4,5>2,5>2,7"
if lm != [want]:
    fail(f"3.e2:e4:e6:c6:c8 not the unique forced capture; legal = {sorted(lm)}")
pos = G.apply_move(pos, want)
if pos.board.get((2, 7)) != (0, "k"):
    fail("man ending its capture on c8 did not promote to king")
blacks = [sq for sq, v in pos.board.items() if v[0] == 1]
if blacks != [(7, 3)]:
    fail(f"Black should keep only the h4 man; has {sorted(blacks)}")
print('the "Coup Turc in Croda" (AG#9) replays to the printed win  OK')


# ---------------------------------------------------------------------------
# 2b. The "Croda Problem" (AG#9 p.7) — official solution printed in AG#10 p.12
#     (John McCallion): 1.f1e2 g4:e4 2.a1b2 a2:c2:c4 3.e3f4 a3:c3:e3
#     4.f4:d4:b4:b6 c6:a6 5.e2:e4:e6:c6:c8+
# ---------------------------------------------------------------------------
pos = board_from({
    (2, 6): (1, "m"), (2, 5): (1, "m"), (3, 5): (1, "m"), (1, 4): (1, "m"),
    (4, 4): (1, "m"), (6, 3): (1, "m"), (7, 3): (1, "m"), (0, 2): (1, "m"),
    (0, 1): (1, "m"),
    (5, 3): (0, "m"), (1, 2): (0, "m"), (2, 2): (0, "m"), (3, 2): (0, "m"),
    (4, 2): (0, "m"), (7, 1): (0, "m"), (0, 0): (0, "m"), (4, 0): (0, "m"),
    (5, 0): (0, "m"),
})
line = [
    ("5,0>4,1", False),                    # 1. f1-e2
    ("6,3>4,3", True),                     # 1... g4:e4 (forced)
    ("0,0>1,1", False),                    # 2. a1-b2
    ("0,1>2,1>2,3", True),                 # 2... a2:c2:c4 (forced)
    ("4,2>5,3", False),                    # 3. e3-f4
    ("0,2>2,2>4,2", True),                 # 3... a3:c3:e3 (forced)
    ("5,3>3,3>1,3>1,5", True),             # 4. f4:d4:b4:b6 (compulsory)
    ("2,5>0,5", True),                     # 4... c6:a6 (forced)
    ("4,1>4,3>4,5>2,5>2,7", True),         # 5. e2:e4:e6:c6:c8+ (compulsory)
]
for mv, forced in line:
    lm = G.legal_moves(pos)
    if mv not in lm:
        fail(f"AG10 solution move {mv} not legal; legal = {sorted(lm)}")
    if forced and lm != [mv]:
        fail(f"AG10 solution move {mv} should be forced; legal = {sorted(lm)}")
    pos = G.apply_move(pos, mv)
if pos.board.get((2, 7)) != (0, "k"):
    fail("AG10 problem: man ending on c8 did not promote")
if sorted(sq for sq, v in pos.board.items() if v[0] == 1) != [(0, 5), (7, 3)]:
    fail("AG10 problem: Black should keep exactly a6 and h4")
if sorted(sq for sq, v in pos.board.items() if v[0] == 0) != [(2, 7), (4, 0), (7, 1)]:
    fail("AG10 problem: White should keep exactly Kc8, e1, h2")
print('the AG#9 "Croda Problem" replays to the official AG#10 solution  OK')


# ---------------------------------------------------------------------------
# 3a. Majority rule: a 2-capture chain prunes a 1-capture option
# ---------------------------------------------------------------------------
st = board_from({
    (3, 3): (0, "m"),
    (4, 3): (1, "m"),                    # 1-capture branch (east)
    (3, 4): (1, "m"), (3, 6): (1, "m"),  # 2-capture branch (north, north)
})
lm = G.legal_moves(st)
if lm != ["3,3>3,5>3,7"]:
    fail(f"majority rule failed; legal = {sorted(lm)}")
ns = G.apply_move(st, "3,3>3,5>3,7")
if (3, 4) in ns.board or (3, 6) in ns.board:
    fail("majority chain did not remove both men")
if ns.board.get((3, 7)) != (0, "k"):
    fail("man ending its capture on the far rank did not promote")
print("majority capture over smaller capture  OK")

# 3b. Men capture backward/sideways orthogonally, but NEVER diagonally
st = board_from({(3, 3): (0, "m"), (3, 2): (1, "m")})   # enemy straight BEHIND
lm = set(G.legal_moves(st))
if lm != {"3,3>3,1"}:
    fail(f"man backward orthogonal capture not forced; legal = {sorted(lm)}")
st = board_from({(3, 3): (0, "m"), (2, 3): (1, "m")})   # enemy SIDEWAYS
if set(G.legal_moves(st)) != {"3,3>1,3"}:
    fail("man sideways capture not forced")
st = board_from({(3, 3): (0, "m"), (4, 4): (1, "m")})   # enemy DIAGONAL
lm = set(G.legal_moves(st))
if "3,3>5,5" in lm or any(ncaps(m) > 1 for m in lm):
    fail(f"man captured diagonally; legal = {sorted(lm)}")
if "3,3>4,4" in lm:
    fail("man stepped onto an occupied square")
if lm != {"3,3>3,4", "3,3>2,4"}:   # diagonal-right blocked by the enemy man
    fail(f"quiet man moves wrong; legal = {sorted(lm)}")
print("man captures orthogonally only (fwd/back/side, never diagonal)  OK")

# 3c. King long-leap capture with a turn (fly, land anywhere beyond, continue)
st = board_from({(0, 0): (0, "k"), (0, 4): (1, "m"), (3, 5): (1, "m")})
lm = set(G.legal_moves(st))
expect = {f"0,0>0,5>{c},5" for c in (4, 5, 6, 7)}
if lm != expect:
    fail(f"king multi-turn long leap wrong; legal = {sorted(lm)}")
ns = G.apply_move(st, "0,0>0,5>7,5")
if (0, 4) in ns.board or (3, 5) in ns.board or ns.board.get((7, 5)) != (0, "k"):
    fail("king chain capture did not remove both men / land on h6")
print("king long-leap chain capture  OK")

# 3d. No-double-jump + landing on the vacated origin: a man loops a 2x2 block
# of enemies (g3, f4, e3, f2) from g2 and returns to g2, its own vacated
# start square. It may NOT then re-jump g3 (already captured). Both loop
# directions are the only maximal chains. (The landing-block half of the Coup
# Turc — a captured-but-unremoved piece occupying a landing square — is
# exercised by the AG#9 replay above: Black's chain must STOP on e3 because
# captured e1 blocks the jump over e2, which is exactly why the printed line
# is the unique 4-capture.)
st = board_from({
    (6, 1): (0, "m"),
    (6, 2): (1, "m"), (5, 3): (1, "m"), (4, 2): (1, "m"), (5, 1): (1, "m"),
})
lm = set(G.legal_moves(st))
fwd = "6,1>6,3>4,3>4,1>6,1"    # over g3, f4, e3, f2, back to origin g2
rev = "6,1>4,1>4,3>6,3>6,1"    # the same loop, entered westward
if lm != {fwd, rev}:
    fail(f"man loop chains wrong; legal = {sorted(lm)}")
if max(ncaps(m) for m in lm) != 4:
    fail("man loop did not capture all 4")
ns = G.apply_move(st, fwd)
if [sq for sq, v in ns.board.items() if v[0] == 1]:
    fail("loop capture left a black piece")
if ns.board.get((6, 1)) != (0, "m"):
    fail("man did not end (unpromoted) back on its vacated origin g2")
print("no-double-jump; landing on the vacated origin  OK")

# 3e. Promotion only at sequence END: a man jumps ON and OFF the far rank
# Man d6; Black d7, e8, f7. Chain d6:d8:f8:f6 visits the far rank twice but
# ends on f6 -> stays a MAN.
st = board_from({
    (3, 5): (0, "m"),
    (3, 6): (1, "m"), (4, 7): (1, "m"), (5, 6): (1, "m"),
})
lm = G.legal_moves(st)
want = "3,5>3,7>5,7>5,5"
if lm != [want]:
    fail(f"on-and-off far-rank chain not forced; legal = {sorted(lm)}")
ns = G.apply_move(st, want)
if ns.board.get((5, 5)) != (0, "m"):
    fail("man that visited the far rank mid-capture promoted (it must not)")
print("no mid-sequence promotion (on-and-off the far rank)  OK")

# 3f. A fully blocked player loses
st = board_from({
    (0, 5): (1, "m"),                     # Black man a6, moving toward row 0
    (0, 4): (0, "m"), (1, 4): (0, "m"),   # a5/b5 block both forward steps
    (0, 3): (0, "m"),                     # a4 blocks the landing of a jump
}, to_move=1)
if G.legal_moves(st) != [] or not G.is_terminal(st):
    fail("blocked Black player still has moves")
if G.returns(st) != [1.0, -1.0]:
    fail(f"blocked player did not lose: returns = {G.returns(st)}")
print("blocked player loses  OK")


# ---------------------------------------------------------------------------
# 4. Termination: random playouts
# ---------------------------------------------------------------------------
rng = random.Random(2026)
results = {"w": 0, "b": 0, "d": 0}
for g in range(200):
    s = G.initial_state()
    plies = 0
    while not G.is_terminal(s):
        lm = G.legal_moves(s)
        if not lm:
            fail("non-terminal state with no legal moves")
        s = G.apply_move(s, rng.choice(lm))
        plies += 1
        if plies > PLY_CAP + 2:
            fail("playout exceeded the ply cap without terminating")
    r = G.returns(s)
    if len(r) != 2:
        fail("returns not length 2")
    results["w" if r[0] > 0 else "b" if r[1] > 0 else "d"] += 1
    # round-trip a mid/terminal state
    if g % 50 == 0 and G.serialize(G.deserialize(G.serialize(s))) != G.serialize(s):
        fail("serialize round-trip failed")
print(f"200 random playouts terminated  OK (W {results['w']} / B {results['b']} / draw {results['d']})")

print("SELFTEST OK")
sys.exit(0)
