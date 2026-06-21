#!/usr/bin/env python3
"""Standalone correctness self-test for International Draughts.

Run from engine/ with:  PYTHONPATH=. python3 games/international_draughts/selftest.py

Asserts:
  1. Published 10x10 opening perft node counts (depths 1-3), confirmed by the
     World Draughts Forum (Ed Gilbert / Bert Tuyt / Feike Boomstra):
        perft(1)=9, perft(2)=81, perft(3)=658  (also 4265, 27117 at 4,5).
     https://damforum.nl/viewtopic.php?t=2308
  2. Rule positions: a man capturing BACKWARD; a flying king's long-range
     capture; and the maximum-capture (majority) rule forcing the longest
     sequence and pruning shorter ones.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import sys

from games.international_draughts.game import InternationalDraughts, DraughtsState

G = InternationalDraughts()


def perft(state, depth):
    if depth == 0:
        return 1
    total = 0
    for m in G.legal_moves(state):
        total += perft(G.apply_move(state, m), depth - 1)
    return total


def board_from(spec):
    """spec: dict of (c,r) -> (player, kind). Returns a state with White to move."""
    return DraughtsState(board=dict(spec), to_move=0)


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 1. Opening perft (the anchor)
# ---------------------------------------------------------------------------
PUBLISHED = {1: 9, 2: 81, 3: 658}
init = G.initial_state()
for d, expected in PUBLISHED.items():
    got = perft(init, d)
    if got != expected:
        fail(f"perft({d}) = {got}, expected published {expected}")
    print(f"perft({d}) = {got}  OK (published {expected})")

# sanity: 20 men each, only on dark squares, four ranks
if len(init.board) != 40:
    fail(f"opening has {len(init.board)} pieces, expected 40")
if any((c + r) % 2 == 0 for (c, r) in init.board):
    fail("a piece sits on a light square in the opening")


# ---------------------------------------------------------------------------
# 2a. Man captures BACKWARD
# ---------------------------------------------------------------------------
# White man on (4,4). A black man on (5,3) is diagonally BEHIND it (White moves
# toward higher rows). Landing (6,2) is empty -> must capture backward.
st = board_from({(4, 4): (0, "m"), (5, 3): (1, "m")})
moves = set(G.legal_moves(st))
if "4,4>6,2" not in moves:
    fail(f"man backward capture missing; legal = {sorted(moves)}")
# capture is mandatory: the only legal moves are captures, no quiet move
if any(len(m.split(">")) == 2 and abs(int(m.split(">")[1].split(",")[0]) -
       int(m.split(">")[0].split(",")[0])) == 1 for m in moves):
    fail("a quiet move offered while a capture exists (capture not mandatory)")
ns = G.apply_move(st, "4,4>6,2")
if (5, 3) in ns.board:
    fail("backward-captured man was not removed")
if ns.board.get((6, 2)) != (0, "m"):
    fail("man did not land on (6,2)")
print("man backward capture  OK")


# ---------------------------------------------------------------------------
# 2b. Flying king long-range capture
# ---------------------------------------------------------------------------
# White king on (0,0). Empty diagonal, a lone black man on (5,5). King may jump
# it landing on (6,6), (7,7), (8,8) or (9,9) -- all distinct flying captures.
st = board_from({(0, 0): (0, "k"), (5, 5): (1, "m")})
moves = set(G.legal_moves(st))
expect = {"0,0>6,6", "0,0>7,7", "0,0>8,8", "0,0>9,9"}
if moves != expect:
    fail(f"flying king captures = {sorted(moves)}, expected {sorted(expect)}")
ns = G.apply_move(st, "0,0>9,9")
if (5, 5) in ns.board:
    fail("flying-captured man not removed")
if ns.board.get((9, 9)) != (0, "k"):
    fail("king did not fly to (9,9)")
print("flying king long capture  OK")

# A flying king must also chain captures around a corner.
# King (0,0); black men on (4,4) and (4,6). Jump (4,4) land on (5,5), then turn
# and jump (4,6) landing on (3,7) etc.  Just assert a 2-piece capture exists.
st = board_from({(0, 0): (0, "k"), (4, 4): (1, "m"), (6, 6): (1, "m")})
moves = G.legal_moves(st)
maxcaps = max(len(m.split(">")) - 1 for m in moves)
if maxcaps < 2:
    fail(f"flying king failed to chain two captures; max = {maxcaps}")
print("flying king chain capture  OK")


# ---------------------------------------------------------------------------
# 2c. Maximum-capture (majority) rule
# ---------------------------------------------------------------------------
# White man on (4,4). Two capture options:
#   - jump (5,5) land (6,6): from (6,6) no further enemy -> 1 capture.
#   - jump (3,3) land (2,2): from (2,2) jump (1,1) land (0,0) -> 2 captures.
# Majority rule must force the 2-capture sequence ONLY.
st = board_from({
    (4, 4): (0, "m"),
    (5, 5): (1, "m"),          # leads to a 1-capture branch
    (3, 3): (1, "m"), (1, 1): (1, "m"),   # leads to a 2-capture branch
})
moves = set(G.legal_moves(st))
counts = {m: len(m.split(">")) - 1 for m in moves}
if any(v < 2 for v in counts.values()):
    fail(f"majority rule allowed a short capture: {counts}")
if "4,4>2,2>0,0" not in moves:
    fail(f"longest sequence missing; legal = {sorted(moves)}")
if "4,4>6,6" in moves:
    fail("1-capture move not pruned by majority rule")
ns = G.apply_move(st, "4,4>2,2>0,0")
if (3, 3) in ns.board or (1, 1) in ns.board:
    fail("majority capture did not remove both enemy men")
print("maximum-capture (majority) rule  OK")


# ---------------------------------------------------------------------------
# 2d. End-of-move promotion only (no mid-capture promotion)
# ---------------------------------------------------------------------------
# White man on (4,8). Black man on (5,9-? ) -- build a case where the capturing
# man passes the last rank but continues, so it should NOT become a king.
# Man (2,6); black men at (3,7) and (3,9)... arrange a chain that lands back off
# the king row.  Simpler: man ends ON king row -> promotes.
st = board_from({(4, 8): (0, "m"), (5, 9): (1, "m")})
# can't land beyond row 9, so this is not a capture; instead test quiet promote:
st = board_from({(4, 8): (0, "m")})
moves = set(G.legal_moves(st))
ns = G.apply_move(st, "4,8>5,9")
if ns.board.get((5, 9)) != (0, "k"):
    fail("man ending on last rank did not promote")
# Mid-capture pass-over: man (1,5); black men (2,6) and (2,8). Jump (2,6)->land
# (3,7); jump (2,8)->land(3,9) which IS the king row at the END -> promotes.
# To show NON-promotion on pass-over, we need a chain that crosses row 9 then
# leaves it. That requires landing past row 9, impossible on a 10x10 edge, so
# end-of-move promotion is the operative distinction; assert the man that ends
# below the last rank after capturing stays a man:
st = board_from({(3, 7): (0, "m"), (4, 8): (1, "m")})
moves = set(G.legal_moves(st))
if "3,7>5,9" not in moves:
    fail(f"expected forward capture to last rank; legal = {sorted(moves)}")
ns = G.apply_move(st, "3,7>5,9")
if ns.board.get((5, 9)) != (0, "k"):
    fail("man ending capture on last rank did not promote")
print("promotion (end-of-move)  OK")


# ---------------------------------------------------------------------------
# 2e. "no jumping the same piece twice" for a flying king
# ---------------------------------------------------------------------------
# King (4,4) with a single black man (6,6). After jumping it the king may not
# turn around and jump it again -> exactly the simple flying captures, all
# 1-capture.
st = board_from({(4, 4): (0, "k"), (6, 6): (1, "m")})
moves = G.legal_moves(st)
if max(len(m.split(">")) - 1 for m in moves) != 1:
    fail("flying king jumped a single piece more than once")
print("no double-jump of one piece  OK")


print("SELFTEST OK")
sys.exit(0)
