#!/usr/bin/env python3
"""Standalone correctness anchor for Shako (Jean-Louis Cazaux, 1990).

Run from the engine dir with::

    PYTHONPATH=. python3 games/shako/selftest.py

Pure stdlib + this game only (no third-party engine), fast. Prints ``SELFTEST OK``
and exits 0 on success, nonzero on any failure.

It asserts:

* the setup (cannons in rank-1 corners, elephants in rank-2 corners, the
  E R N B Q K B N R E back rank with Q on e / K on f, 10 pawns on rank 3, 44 men);
* a self-computed **opening perft baseline** (d1 = 58, d2 = 3364, d3 = 185938) and a
  hand-derived decomposition of the 58 opening moves;
* the **Cannon** moves like a rook on empty lines but captures ONLY over a single
  screen (and gives check the same way);
* the **Elephant** = Ferz + Alfil: one or two diagonal squares, leaping the
  intermediate (and NOT orthogonal / NOT a knight);
* **promotion** to Q/R/B/N/Cannon/Elephant and **castling** on the f-file king;
* a serialize round-trip.

No published perft table exists for Shako, so the perft numbers here are this
engine's own regression baseline, derived from (and pinning) the move generator.
The opening count 58 is hand-verified in the decomposition below.
"""

import sys
import time

from agp.chesslike import CState, WHITE, BLACK
from games.shako.game import Shako

G = Shako()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def st(board, to_move=WHITE, castling="", ep=None):
    rights = frozenset(castling)
    return CState(board=dict(board), to_move=to_move, castling=rights, ep=ep,
                  reps={G._poskey(board, to_move, rights, ep): 1})


def targets(state, frm):
    out = set()
    for m in G.legal_moves(state):
        base = m.split("=")[0]
        f, t = base.split(">")
        if f == frm:
            tc, tr = t.split(",")
            out.add((int(tc), int(tr)))
    return out


def perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


# --------------------------------------------------------------------------- #
# 1. Setup
# --------------------------------------------------------------------------- #
s0 = G.initial_state()
check(len(s0.board) == 44, "44 men at the start (22 per side)")
# cannons in the rank-1 corners
for c in (0, 9):
    check(s0.board[(c, 0)] == (WHITE, "C"), "White cannon in a rank-1 corner")
    check(s0.board[(c, 9)] == (BLACK, "C"), "Black cannon in a rank-10 corner")
# elephants in the rank-2 corners
for c in (0, 9):
    check(s0.board[(c, 1)] == (WHITE, "E"), "White elephant in a rank-2 corner")
    check(s0.board[(c, 8)] == (BLACK, "E"), "Black elephant in a rank-9 corner")
# back rank E R N B Q K B N R E  (queen e=file4, king f=file5)
expect = ["E", "R", "N", "B", "Q", "K", "B", "N", "R", "E"]
for i, t in enumerate(expect):
    check(s0.board[(i, 1)] == (WHITE, t), f"White back rank file {i} should be {t}")
    check(s0.board[(i, 8)] == (BLACK, t), f"Black back rank file {i} should be {t}")
check(s0.board[(4, 1)] == (WHITE, "Q"), "White queen on e2")
check(s0.board[(5, 1)] == (WHITE, "K"), "White king on f2")
# 10 pawns on rank 3 / rank 8
for c in range(10):
    check(s0.board[(c, 2)] == (WHITE, "P"), "White pawns on rank 3")
    check(s0.board[(c, 7)] == (BLACK, "P"), "Black pawns on rank 8")
wp = sum(1 for v in s0.board.values() if v == (WHITE, "P"))
check(wp == 10, "10 white pawns")

# --------------------------------------------------------------------------- #
# 2. Opening perft baseline (engine-derived, hand-verified) + decomposition
# --------------------------------------------------------------------------- #
check(perft(s0, 1) == 58, "perft(1) must be 58")
# Hand decomposition of the 58 opening moves:
#   pawns 20 (10 x {1-step, 2-step}); cannons 16 (2 x 8 rook-slides along rank 1);
#   elephants 4 (2 x {Ferz to b1/i1, Alfil leap to c4/h4}); knights 6 (2 x 3);
#   rooks 2 (b2/i2 each one step down); bishops 4 (2 x 2 diagonals onto rank 1);
#   queen 3; king 3.  20+16+4+6+2+4+3+3 = 58.
from collections import defaultdict
bytype = defaultdict(int)
for m in G.legal_moves(s0):
    f = m.split("=")[0].split(">")[0]
    c, r = (int(x) for x in f.split(","))
    bytype[s0.board[(c, r)][1]] += 1
check(dict(bytype) == {"P": 20, "C": 16, "E": 4, "N": 6, "R": 2, "B": 4, "Q": 3, "K": 3},
      f"opening move decomposition mismatch: {dict(bytype)}")

t = time.time()
check(perft(s0, 2) == 3364, "perft(2) must be 3364")
check(perft(s0, 3) == 185938, "perft(3) must be 185938")
print(f"  perft anchor OK (d1=58, d2=3364, d3=185938) in {time.time() - t:.1f}s")

# --------------------------------------------------------------------------- #
# 3. The Cannon: rook on empty lines, capture only over a single screen
# --------------------------------------------------------------------------- #
WK, BK = (5, 0), (5, 9)   # kings parked out of the way (NOT on a tested file)

# (a) on an open file/rank the cannon slides like a rook (no capture)
b = {(0, 0): (WHITE, "C"), WK: (WHITE, "K"), BK: (BLACK, "K")}
st_c = st(b, WHITE)
tg = targets(st_c, "0,0")
check((0, 8) in tg, "cannon slides up an empty file like a rook")        # a1 -> a9
check((4, 0) in tg, "cannon slides along an empty rank like a rook")     # a1 -> e1
check((6, 0) not in tg, "cannon stops at the king on f1 (rank-slide blocked)")

# (b) NO screen -> cannot capture the lone enemy directly ahead
b = {(0, 0): (WHITE, "C"), (0, 5): (BLACK, "N"), WK: (WHITE, "K"), BK: (BLACK, "K")}
st_c = st(b, WHITE)
tg = targets(st_c, "0,0")
check((0, 5) not in tg, "cannon may not capture an enemy with no screen between")
check((0, 4) in tg and (0, 6) not in tg,
      "cannon slides up to (not past) the enemy when there is no screen")

# (c) exactly ONE screen -> the cannon captures the enemy beyond it
b = {(0, 0): (WHITE, "C"), (0, 3): (WHITE, "P"), (0, 7): (BLACK, "N"),
     WK: (WHITE, "K"), BK: (BLACK, "K")}
st_c = st(b, WHITE)
tg = targets(st_c, "0,0")
check((0, 7) in tg, "cannon jumps one screen to capture the enemy beyond")
check((0, 3) not in tg and (0, 4) not in tg,
      "cannon cannot land on or beyond-but-before its own screen")
# slides up to just below the screen
check((0, 1) in tg and (0, 2) in tg, "cannon slides up to the square before its screen")

# (d) TWO screens -> no capture (cannot jump two pieces)
b = {(0, 0): (WHITE, "C"), (0, 3): (WHITE, "P"), (0, 5): (WHITE, "P"),
     (0, 7): (BLACK, "N"), WK: (WHITE, "K"), BK: (BLACK, "K")}
st_c = st(b, WHITE)
check((0, 7) not in targets(st_c, "0,0"), "cannon may not jump two screens")

# (e) the cannon gives check the same way (attack detection through one screen)
b = {(0, 0): (WHITE, "C"), (0, 3): (BLACK, "P"), (0, 7): (BLACK, "K"),
     WK: (WHITE, "K")}
check(G.attacked(b, 0, 7, WHITE), "white cannon checks the king over one screen")
check(G.in_check(b, BLACK), "black king is in check from the cannon over a screen")
# remove the screen -> no check
b2 = {(0, 0): (WHITE, "C"), (0, 7): (BLACK, "K"), WK: (WHITE, "K")}
check(not G.attacked(b2, 0, 7, WHITE), "no screen -> the cannon gives no check")

# --------------------------------------------------------------------------- #
# 4. The Elephant = Ferz + Alfil (one OR two diagonal squares, leaping)
# --------------------------------------------------------------------------- #
# Lone elephant on e5 (4,4); kings far away.
b = {(4, 4): (WHITE, "E"), (0, 0): (WHITE, "K"), (9, 9): (BLACK, "K")}
st_e = st(b, WHITE)
tg = targets(st_e, "4,4")
expect_e = {(3, 3), (5, 3), (3, 5), (5, 5),    # Ferz (one diagonal step)
            (2, 2), (6, 2), (2, 6), (6, 6)}    # Alfil (two diagonal, leaping)
check(tg == expect_e, f"elephant move set wrong: {sorted(tg)}")

# The Alfil leg LEAPS: an occupied intermediate square does not block the 2-step.
b = {(4, 4): (WHITE, "E"), (5, 5): (BLACK, "P"),     # piece on the intermediate
     (0, 0): (WHITE, "K"), (9, 9): (BLACK, "K")}
st_e = st(b, WHITE)
check((6, 6) in targets(st_e, "4,4"),
      "elephant leaps over an occupied intermediate diagonal square (Alfil)")

# It is NOT orthogonal and NOT a knight.
for bad in ((4, 5), (4, 6), (5, 4), (6, 4), (3, 4), (4, 3), (6, 5), (5, 6)):
    check(bad not in expect_e, f"elephant must not reach {bad} (orthogonal/knight)")

# --------------------------------------------------------------------------- #
# 5. Promotion to Q/R/B/N/Cannon/Elephant
# --------------------------------------------------------------------------- #
b = {(0, 8): (WHITE, "P"), (5, 0): (WHITE, "K"), (5, 9): (BLACK, "K")}
st_p = st(b, WHITE)
promos = {m.split("=")[1] for m in G.legal_moves(st_p) if m.startswith("0,8>0,9=")}
check(promos == {"Q", "R", "B", "N", "C", "E"}, f"promotion choices = {promos}")
s_after = G.apply_move(st_p, "0,8>0,9=C")
check(s_after.board.get((0, 9)) == (WHITE, "C"), "pawn did not promote to a Cannon")

# --------------------------------------------------------------------------- #
# 6. Castling on the f-file king (kingside f->h rook i->g, queenside f->d rook b->e)
# --------------------------------------------------------------------------- #
base = {(5, 0): (WHITE, "K"), (8, 0): (WHITE, "R"), (1, 0): (WHITE, "R"),
        (5, 9): (BLACK, "K")}
sc = st(base, WHITE, castling="KQ")
kd = targets(sc, "5,0")
check((7, 0) in kd, "kingside castle target h1 (7,0) missing")
check((3, 0) in kd, "queenside castle target d1 (3,0) missing")
# execute kingside: K->h1 (7,0), rook i1(8,0)->g1(6,0)
sk = G.apply_move(sc, "5,0>7,0")
check(sk.board.get((7, 0)) == (WHITE, "K") and sk.board.get((6, 0)) == (WHITE, "R")
      and (8, 0) not in sk.board, "kingside castling placement wrong")
# execute queenside: K->d1 (3,0), rook b1(1,0)->e1(4,0)
sq = G.apply_move(sc, "5,0>3,0")
check(sq.board.get((3, 0)) == (WHITE, "K") and sq.board.get((4, 0)) == (WHITE, "R")
      and (1, 0) not in sq.board, "queenside castling placement wrong")
# cannot castle through an attacked square: a black rook on g1 (6,0) hits the
# kingside king path -> kingside illegal, queenside still ok.
blocked = dict(base)
blocked[(6, 9)] = (BLACK, "R")     # g-file rook attacks g1 (6,0)
sb = st(blocked, WHITE, castling="KQ")
kd = targets(sb, "5,0")
check((7, 0) not in kd, "castling through attacked square g1 was allowed")
check((3, 0) in kd, "queenside castling wrongly blocked")

# --------------------------------------------------------------------------- #
# 7. Serialize round-trips
# --------------------------------------------------------------------------- #
check(G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0),
      "serialize must round-trip the opening position")
s1 = G.apply_move(s0, "0,2>0,4")               # a pawn double-step (creates ep)
check(G.serialize(G.deserialize(G.serialize(s1))) == G.serialize(s1),
      "serialize must round-trip after a pawn double-step")

print("SELFTEST OK")
sys.exit(0)
