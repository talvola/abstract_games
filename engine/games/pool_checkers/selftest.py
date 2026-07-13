#!/usr/bin/env python3
"""Standalone correctness self-test for Pool Checkers.

Run from engine/ with:  PYTHONPATH=. python3 games/pool_checkers/selftest.py

Pool checkers = Russian draughts rules (men capture forward & backward, flying
kings, capture mandatory but ANY / not maximum, finish a started chain) EXCEPT
for one defining rule: DEFERRED promotion — a man reaching the king row during a
capture chain does NOT become a king mid-sequence; it keeps jumping as a man and
promotes only at the end.

This test asserts:
  1. Opening perft node counts on the 8x8 board (no captures in the opening, so
     these match the published 8x8 draughts opening tree): 7 / 49 / 302 / 1469.
  2. THE DEFERRED-PROMOTION ANCHOR: a constructed position where a man reaches
     the king row mid-capture. In Pool it stops there as a man (no king-style
     continuation); we prove a flying KING on that same square WOULD have a
     further capture, so the deferral is what makes the difference (this is the
     Pool-vs-Russian distinction).
  3. THE ANY-CAPTURE (non-max) anchor: a position with a 1-capture and a
     2-capture option; Pool makes BOTH legal (Brazilian's majority rule would
     prune the shorter one). This is the Pool-vs-Brazilian distinction.
  4. A man capturing backward; a flying-king long capture and chain; end-of-
     sequence promotion; a win via apply_move; termination; serialization.

Pure stdlib; imports only the agp package / this game. Prints "SELFTEST OK" and
exits 0 on success, nonzero on failure.
"""
import sys

from games.pool_checkers.game import (
    PoolCheckers, DraughtsState, _king_capture_paths, _king_row,
)

G = PoolCheckers()


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
# 1. Opening perft (the shared 8x8 anchor)
# ---------------------------------------------------------------------------
PUBLISHED = {1: 7, 2: 49, 3: 302, 4: 1469}
init = G.initial_state()
for d, expected in PUBLISHED.items():
    got = perft(init, d)
    if got != expected:
        fail(f"perft({d}) = {got}, expected published {expected}")
    print(f"perft({d}) = {got}  OK (published {expected})")

if len(init.board) != 24:
    fail(f"opening has {len(init.board)} pieces, expected 24")
white = [p for p, v in init.board.items() if v[0] == 0]
black = [p for p, v in init.board.items() if v[0] == 1]
if len(white) != 12 or len(black) != 12:
    fail(f"expected 12 men each, got white={len(white)} black={len(black)}")


# ---------------------------------------------------------------------------
# 2. THE DEFERRED-PROMOTION ANCHOR (Pool vs Russian)
# ---------------------------------------------------------------------------
# White man at (1,5). Black man at (2,6): jump direction (+1,+1) lands on (3,7),
# the WHITE king row. Beyond that, along the (+1,-1) diagonal from (3,7), sits a
# black man at (5,5) with the intervening square (4,6) empty.
#
#   * As a MAN (Pool): from (3,7) the man needs an ADJACENT enemy at (4,6) to
#     jump (5,5). (4,6) is empty, so the man cannot reach (5,5): the chain ends
#     with a single capture, and the man promotes only now, at the end.
#   * As a flying KING (what Russian would give by promoting immediately at
#     (3,7)): it slides (+1,-1) over empty (4,6), jumps (5,5), lands on (6,4) —
#     a SECOND capture. Pool forbids this because the man is NOT yet a king.
POS = {(1, 5): (0, "m"), (2, 6): (1, "m"), (5, 5): (1, "m")}
st = board_from(POS)
moves = set(G.legal_moves(st))
# Pool: only the single-capture man move exists.
if moves != {"1,5>3,7"}:
    fail(f"deferred-promotion: expected only single capture 1,5>3,7, got {sorted(moves)}")
ns = G.apply_move(st, "1,5>3,7")
if ns.board.get((3, 7)) != (0, "k"):
    fail("man ending the chain on the king row did not promote at end")
if (5, 5) not in ns.board:
    fail("man wrongly captured the far piece as if it were a flying king mid-chain")
if (2, 6) in ns.board:
    fail("first captured man not removed")
# Prove the deferral matters: a flying KING on (3,7) WOULD capture (5,5), so
# Russian's immediate promotion would extend the chain where Pool's does not.
king_board = {(3, 7): (0, "k"), (5, 5): (1, "m")}
kpaths = _king_capture_paths(king_board, (3, 7), (3, 7), 0, frozenset())
if not kpaths:
    fail("sanity: a flying king from (3,7) should be able to capture (5,5)")
print("DEFERRED promotion (man keeps jumping as a man; Russian would continue as king)  OK")


# ---------------------------------------------------------------------------
# 3. THE ANY-CAPTURE (non-max) ANCHOR (Pool vs Brazilian)
# ---------------------------------------------------------------------------
# White man on (4,4). Two capture options:
#   - jump (5,5) land (6,6): a 1-capture sequence.
#   - jump (3,3) land (2,2), then jump (1,1) land (0,0): a 2-capture sequence.
# Pool allows ANY -> BOTH are legal. (Brazilian's majority rule would prune the
# 1-capture move.)
st = board_from({
    (4, 4): (0, "m"),
    (5, 5): (1, "m"),
    (3, 3): (1, "m"), (1, 1): (1, "m"),
})
moves = set(G.legal_moves(st))
if "4,4>6,6" not in moves:
    fail(f"ANY-capture: short 1-capture move missing (Brazilian would prune it); got {sorted(moves)}")
if "4,4>2,2>0,0" not in moves:
    fail(f"ANY-capture: long 2-capture move missing; got {sorted(moves)}")
# no quiet move offered while a capture exists
counts = {m: len(m.split(">")) - 1 for m in moves}
if not all(v >= 1 for v in counts.values()):
    fail(f"a non-capturing move offered while captures exist: {counts}")
print("ANY-capture (both a short and a long capture legal; Brazilian would force the max)  OK")


# ---------------------------------------------------------------------------
# 4a. Man captures BACKWARD; capture is mandatory
# ---------------------------------------------------------------------------
st = board_from({(4, 4): (0, "m"), (5, 3): (1, "m")})
moves = set(G.legal_moves(st))
if moves != {"4,4>6,2"}:
    fail(f"man backward capture / mandatory-capture failed; legal = {sorted(moves)}")
ns = G.apply_move(st, "4,4>6,2")
if (5, 3) in ns.board or ns.board.get((6, 2)) != (0, "m"):
    fail("backward capture did not resolve correctly")
print("man backward capture (mandatory)  OK")


# ---------------------------------------------------------------------------
# 4b. Flying-king long capture + chain + no double-jump
# ---------------------------------------------------------------------------
st = board_from({(0, 0): (0, "k"), (5, 5): (1, "m")})
if set(G.legal_moves(st)) != {"0,0>6,6", "0,0>7,7"}:
    fail(f"flying king long capture wrong: {sorted(G.legal_moves(st))}")
st = board_from({(0, 0): (0, "k"), (2, 2): (1, "m"), (5, 3): (1, "m")})
if "0,0>4,4>6,2" not in set(G.legal_moves(st)):
    fail("flying king failed to chain two captures")
# single piece cannot be jumped twice
st = board_from({(4, 4): (0, "k"), (6, 6): (1, "m")})
if max(len(m.split(">")) - 1 for m in G.legal_moves(st)) != 1:
    fail("flying king jumped a single piece more than once")
print("flying king long capture + chain + no double-jump  OK")


# ---------------------------------------------------------------------------
# 4c. Quiet-move promotion at the king row
# ---------------------------------------------------------------------------
st = board_from({(4, 6): (0, "m")})
ns = G.apply_move(st, "4,6>5,7")
if ns.board.get((5, 7)) != (0, "k"):
    fail("man ending a quiet move on last rank did not promote")
# a man that captures but ends BELOW the last rank stays a man
st = board_from({(2, 2): (0, "m"), (3, 3): (1, "m")})
ns = G.apply_move(st, "2,2>4,4")
if ns.board.get((4, 4)) != (0, "m"):
    fail("man not ending on last rank was wrongly promoted")
print("promotion at end of sequence only  OK")


# ---------------------------------------------------------------------------
# 4d. Win via apply_move; termination; serialization
# ---------------------------------------------------------------------------
# Reach a win by capturing Black's last piece with a move, then Black has none.
st = DraughtsState(board={(4, 4): (0, "m"), (5, 5): (1, "m")}, to_move=0)
ns = G.apply_move(st, "4,4>6,6")   # captures Black's only man
if any(v[0] == 1 for v in ns.board.values()):
    fail("Black still has a piece after its last man was captured")
if not G.is_terminal(ns):
    fail("state where Black (to move) has no piece should be terminal")
if G.returns(ns) != [1.0, -1.0]:
    fail(f"expected White win [1,-1], got {G.returns(ns)}")

s = G.initial_state()
if G.deserialize(G.serialize(s)).board != s.board:
    fail("serialize/deserialize did not round-trip the board")
if _king_row(0) != 7 or _king_row(1) != 0:
    fail("king rows wrong")
print("win via apply_move + termination + serialization  OK")


print("SELFTEST OK")
sys.exit(0)
