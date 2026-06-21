#!/usr/bin/env python3
"""Standalone correctness self-test for Brazilian Draughts.

Run from engine/ with:  PYTHONPATH=. python3 games/brazilian_draughts/selftest.py

Brazilian draughts is International (Polish) draughts rules played on the smaller
8x8 board (12 men per side), so the move generator is identical to International
Draughts scaled down. This test asserts:

  1. Opening perft node counts for the 8x8 board, depths 1-4:
        perft(1)=7, perft(2)=49, perft(3)=302, perft(4)=1469.
     These are the well-known 8x8 draughts opening perft numbers: the opening
     tree contains no captures until well past depth 4, so the move tree (men
     moving forward only) is identical between the 8x8 international/Brazilian
     ruleset and English/American checkers, for which 7 / 49 / 302 / 1469 are
     the published opening node counts.
  2. Rule positions exercising the International ruleset on 8x8: a man capturing
     BACKWARD; a flying king's long-range capture and a flying-king chain; the
     maximum-capture (majority) rule forcing the longest sequence and pruning
     shorter ones; end-of-move-only promotion (king row = 7 for White / 0 for
     Black); and the "no jumping the same piece twice" rule.

Pure stdlib; imports only the agp package / this game. Prints "SELFTEST OK" and
exits 0 on success, nonzero on failure.
"""
import sys

from games.brazilian_draughts.game import BrazilianDraughts, DraughtsState

G = BrazilianDraughts()


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
# 1. Opening perft (the anchor) — 8x8 board
# ---------------------------------------------------------------------------
PUBLISHED = {1: 7, 2: 49, 3: 302, 4: 1469}
init = G.initial_state()
for d, expected in PUBLISHED.items():
    got = perft(init, d)
    if got != expected:
        fail(f"perft({d}) = {got}, expected published {expected}")
    print(f"perft({d}) = {got}  OK (published {expected})")

# sanity: 12 men each, only on dark squares, three ranks each
if len(init.board) != 24:
    fail(f"opening has {len(init.board)} pieces, expected 24")
if any((c + r) % 2 == 0 for (c, r) in init.board):
    fail("a piece sits on a light square in the opening")
white = [p for p, v in init.board.items() if v[0] == 0]
black = [p for p, v in init.board.items() if v[0] == 1]
if len(white) != 12 or len(black) != 12:
    fail(f"expected 12 men each, got white={len(white)} black={len(black)}")
if any(r not in (0, 1, 2) for (c, r) in white):
    fail("white man not on rows 0-2")
if any(r not in (5, 6, 7) for (c, r) in black):
    fail("black man not on rows 5-7")


# ---------------------------------------------------------------------------
# 2a. Man captures BACKWARD
# ---------------------------------------------------------------------------
# White man on (4,4). A black man on (5,3) is diagonally BEHIND it (White moves
# toward higher rows). Landing (6,2) is empty -> must capture backward.
st = board_from({(4, 4): (0, "m"), (5, 3): (1, "m")})
moves = set(G.legal_moves(st))
if "4,4>6,2" not in moves:
    fail(f"man backward capture missing; legal = {sorted(moves)}")
# capture is mandatory: only the capture is legal, no quiet move
if moves != {"4,4>6,2"}:
    fail(f"a quiet move offered while a capture exists; legal = {sorted(moves)}")
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
# it landing on (6,6) or (7,7) -- distinct flying captures.
st = board_from({(0, 0): (0, "k"), (5, 5): (1, "m")})
moves = set(G.legal_moves(st))
expect = {"0,0>6,6", "0,0>7,7"}
if moves != expect:
    fail(f"flying king captures = {sorted(moves)}, expected {sorted(expect)}")
ns = G.apply_move(st, "0,0>7,7")
if (5, 5) in ns.board:
    fail("flying-captured man not removed")
if ns.board.get((7, 7)) != (0, "k"):
    fail("king did not fly to (7,7)")
print("flying king long capture  OK")

# Flying-king CHAIN: king (0,0); black men (2,2) and (5,3). Jump (2,2), land on
# (4,4), then turn down-right and jump (5,3). Two-piece capture must exist.
st = board_from({(0, 0): (0, "k"), (2, 2): (1, "m"), (5, 3): (1, "m")})
moves = G.legal_moves(st)
maxcaps = max(len(m.split(">")) - 1 for m in moves)
if maxcaps < 2:
    fail(f"flying king failed to chain two captures; max = {maxcaps}")
if "0,0>4,4>6,2" not in set(moves):
    fail(f"expected flying-king chain 0,0>4,4>6,2; legal = {sorted(moves)}")
ns = G.apply_move(st, "0,0>4,4>6,2")
if (2, 2) in ns.board or (5, 3) in ns.board:
    fail("flying-king chain did not remove both enemy men")
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
    (5, 5): (1, "m"),                     # leads to a 1-capture branch
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
# 2d. End-of-move promotion only (king row = 7 for White)
# ---------------------------------------------------------------------------
# Quiet move ending on the last rank promotes.
st = board_from({(4, 6): (0, "m")})
ns = G.apply_move(st, "4,6>5,7")
if ns.board.get((5, 7)) != (0, "k"):
    fail("man ending a quiet move on last rank did not promote")
# A capture ending on the last rank promotes.
st = board_from({(3, 5): (0, "m"), (4, 6): (1, "m")})
moves = set(G.legal_moves(st))
if "3,5>5,7" not in moves:
    fail(f"expected forward capture to last rank; legal = {sorted(moves)}")
ns = G.apply_move(st, "3,5>5,7")
if ns.board.get((5, 7)) != (0, "k"):
    fail("man ending capture on last rank did not promote")
# A man that captures but ENDS below the last rank stays a man.
st = board_from({(2, 2): (0, "m"), (3, 3): (1, "m")})
ns = G.apply_move(st, "2,2>4,4")
if ns.board.get((4, 4)) != (0, "m"):
    fail("man not ending on last rank was wrongly promoted")
print("promotion (end-of-move)  OK")


# ---------------------------------------------------------------------------
# 2e. "no jumping the same piece twice" for a flying king
# ---------------------------------------------------------------------------
# King (4,4) with a single black man (6,6). After jumping it the king may not
# turn around and jump it again -> at most a 1-capture sequence.
st = board_from({(4, 4): (0, "k"), (6, 6): (1, "m")})
moves = G.legal_moves(st)
if max(len(m.split(">")) - 1 for m in moves) != 1:
    fail("flying king jumped a single piece more than once")
print("no double-jump of one piece  OK")


# ---------------------------------------------------------------------------
# 2f. Win = opponent has no legal move; round-trip serialization
# ---------------------------------------------------------------------------
# Black to move with its only man blocked/captured: White wins.
st = DraughtsState(board={(0, 0): (0, "m")}, to_move=1)  # Black has no piece
if not G.is_terminal(st):
    fail("state with no Black piece should be terminal")
if G.returns(st) != [1.0, -1.0]:
    fail(f"expected White win returns [1,-1], got {G.returns(st)}")

s = G.initial_state()
if G.deserialize(G.serialize(s)).board != s.board:
    fail("serialize/deserialize did not round-trip the board")
print("terminal/win + serialization  OK")


print("SELFTEST OK")
sys.exit(0)
