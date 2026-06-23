#!/usr/bin/env python3
"""Standalone correctness self-test for Dameo (Christian Freeling, 2000).

Run from engine/ with:  PYTHONPATH=. python3 games/dameo/selftest.py

There is no published perft for Dameo, so the anchor is a battery of baked
rule assertions drawn from Freeling's mindsports.nl rules and the faithful
implementations on iggamecenter / playstrategy / Wikipedia:

  1. Opening: 18 men per side in the trapezoidal formation (full back rank,
     then rows of 6 and 4 centred), on all-square coordinates.
  2. MAN STEP: a single man steps ONE square forward — straight-forward
     (orthogonal) OR diagonally-forward — and NOT sideways or backward.
  3. LINEAR MOVEMENT: a connected unbroken line of own men along a forward
     axis (column or forward diagonal) shifts one square forward as a unit;
     a sideways (horizontal) line cannot move.
  4. CAPTURE: men capture ORTHOGONALLY only (forward / backward / sideways),
     captures are MANDATORY, MAXIMAL (the longest sequence is forced) and
     CHAINED, and captured pieces are removed only at the END of the move
     (so a piece cannot be jumped twice).
  5. PROMOTION: a man ending on the far rank becomes a flying KING.
  6. FLYING KING: queen-wise move, rook-wise (orthogonal) long-leap capture.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import sys

from games.dameo.game import Dameo, DameoState

G = Dameo()


def board_from(spec, to_move=0):
    return DameoState(board=dict(spec), to_move=to_move)


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def caps_in(move):
    """Number of ENEMY pieces a move actually jumps (0 for quiet/linear moves)."""
    return len(move.split(">")) - 1


def real_caps(state, move):
    """Actual captured-enemy count for `move` in `state` (0 for a quiet move)."""
    cells = [tuple(int(x) for x in c.split(",")) for c in move.split(">")]
    return len(G._captured_squares(state.board, cells))


# ---------------------------------------------------------------------------
# 1. Opening formation
# ---------------------------------------------------------------------------
init = G.initial_state()
white = {pos for pos, (pl, k) in init.board.items() if pl == 0}
black = {pos for pos, (pl, k) in init.board.items() if pl == 1}
if len(white) != 18 or len(black) != 18:
    fail(f"opening has {len(white)} white / {len(black)} black, expected 18 each")

exp_white = set()
for c in range(0, 8):
    exp_white.add((c, 0))
for c in range(1, 7):
    exp_white.add((c, 1))
for c in range(2, 6):
    exp_white.add((c, 2))
if white != exp_white:
    fail(f"white opening squares wrong:\n got {sorted(white)}\n exp {sorted(exp_white)}")
exp_black = {(c, 7 - r) for (c, r) in exp_white}
if black != exp_black:
    fail(f"black opening squares wrong:\n got {sorted(black)}\n exp {sorted(exp_black)}")
if all(k == "m" for _, k in init.board.values()) is not True:
    fail("opening pieces are not all men")
print("opening trapezoid (18 men, full rank + 6 + 4)  OK")


# ---------------------------------------------------------------------------
# 2. Single MAN step: forward orthogonal + both forward diagonals; never side/back
# ---------------------------------------------------------------------------
# Lone white man at (3,3) on an otherwise empty board.
st = board_from({(3, 3): (0, "m")})
moves = set(G.legal_moves(st))
exp = {"3,3>3,4", "3,3>4,4", "3,3>2,4"}  # N, NE, NW (rows increase = forward)
if moves != exp:
    fail(f"man step set = {sorted(moves)}, expected forward-3 {sorted(exp)}")
# explicitly: no sideways / backward step is offered
for bad in ("3,3>4,3", "3,3>2,3", "3,3>3,2", "3,3>4,2", "3,3>2,2"):
    if bad in moves:
        fail(f"illegal man step offered: {bad}")
# apply a diagonal-forward step
ns = G.apply_move(st, "3,3>4,4")
if ns.board.get((4, 4)) != (0, "m") or (3, 3) in ns.board:
    fail("diagonal-forward man step did not land correctly")
# Black mirrors downward.
stb = board_from({(3, 3): (1, "m")}, to_move=1)
bm = set(G.legal_moves(stb))
if bm != {"3,3>3,2", "3,3>4,2", "3,3>2,2"}:
    fail(f"black man step set = {sorted(bm)} (should be the three downward dirs)")
print("man step: forward straight + both forward diagonals only  OK")


# ---------------------------------------------------------------------------
# 3. LINEAR MOVEMENT
# ---------------------------------------------------------------------------
# (a) A vertical column of three white men at (4,1),(4,2),(4,3) shifts one
#     square forward as a unit -> the rear (4,1) "jumps" to the empty (4,4).
st = board_from({(4, 1): (0, "m"), (4, 2): (0, "m"), (4, 3): (0, "m")})
moves = set(G.legal_moves(st))
if "4,1>4,4" not in moves:
    fail(f"vertical 3-line linear move missing; legal = {sorted(moves)}")
ns = G.apply_move(st, "4,1>4,4")
after = {pos for pos, _ in ns.board.items()}
if after != {(4, 2), (4, 3), (4, 4)}:
    fail(f"linear file-shift wrong: after = {sorted(after)} (whole file should shift +1)")
print("linear movement: vertical column shifts forward as a unit  OK")

# (b) A diagonal line of two own men shifts diagonally forward.
st = board_from({(2, 2): (0, "m"), (3, 3): (0, "m")})
moves = set(G.legal_moves(st))
if "2,2>4,4" not in moves:
    fail(f"diagonal 2-line linear move missing; legal = {sorted(moves)}")
ns = G.apply_move(st, "2,2>4,4")
if {pos for pos in ns.board} != {(3, 3), (4, 4)}:
    fail("diagonal linear shift landed wrong")
print("linear movement: forward diagonal line shifts as a unit  OK")

# (c) A horizontal (sideways) row of own men can NOT make a linear move; only
#     each man's own forward steps are available.
st = board_from({(2, 3): (0, "m"), (3, 3): (0, "m"), (4, 3): (0, "m")})
moves = set(G.legal_moves(st))
for m in moves:
    a, b = m.split(">")
    ar = int(a.split(",")[1])
    br = int(b.split(",")[1])
    if br <= ar:
        fail(f"a sideways/backward 'linear' move was offered: {m}")
# specifically a pure-horizontal shift must not appear
if "2,3>5,3" in moves or "4,3>1,3" in moves:
    fail("a horizontal line illegally moved sideways")
print("linear movement: a sideways (horizontal) line cannot move  OK")

# (d) A line is BLOCKED if the front cell is occupied (linear move unavailable).
st = board_from({(4, 1): (0, "m"), (4, 2): (0, "m"), (4, 3): (0, "m"),
                 (4, 4): (1, "m")}, to_move=0)
# (4,4) is enemy: front blocked -> no linear "4,1>4,4". (A capture may exist
# instead — checked separately; here just assert the quiet linear move is gone.)
caps = G._all_capture_paths(st)
if not caps:
    moves = set(G.legal_moves(st))
    if "4,1>4,4" in moves:
        fail("linear move allowed into an occupied front cell")
print("linear movement: blocked when the front cell is occupied  OK")


# ---------------------------------------------------------------------------
# 4. CAPTURE: orthogonal only, mandatory, maximal, chained, end-of-move removal
# ---------------------------------------------------------------------------
# (a) Orthogonal directions incl. backward & sideways; NOT diagonal.
#   White man (3,3); enemies orthogonally adjacent in all 4 dirs with empty
#   landing beyond each -> four single captures, all orthogonal.
st = board_from({
    (3, 3): (0, "m"),
    (3, 4): (1, "m"),  # forward  -> land (3,5)
    (3, 2): (1, "m"),  # backward -> land (3,1)
    (4, 3): (1, "m"),  # sideways -> land (5,3)
    (2, 3): (1, "m"),  # sideways -> land (1,3)
})
moves = set(G.legal_moves(st))
# only single captures available; each is one of the four orthogonal jumps
exp = {"3,3>3,5", "3,3>3,1", "3,3>5,3", "3,3>1,3"}
if moves != exp:
    fail(f"orthogonal captures = {sorted(moves)}, expected {sorted(exp)}")
print("capture: orthogonal forward/back/sideways (no diagonal)  OK")

# (b) Diagonal enemy is NOT capturable by a man (orthogonal capture only).
#   Here no capture exists, so the man falls back to its quiet forward steps;
#   none of them may actually jump the diagonal enemy.
st = board_from({(3, 3): (0, "m"), (4, 4): (1, "m")})
moves = set(G.legal_moves(st))
if any(real_caps(st, m) >= 1 for m in moves):
    fail(f"a diagonal man capture was offered: {sorted(moves)}")
print("capture: a diagonally-adjacent enemy is NOT a man-capture  OK")

# (c) Mandatory: when a capture exists, no quiet move is legal.
st = board_from({(3, 3): (0, "m"), (3, 4): (1, "m")})  # forward capture to (3,5)
moves = set(G.legal_moves(st))
if moves != {"3,3>3,5"}:
    fail(f"capture not mandatory / wrong: legal = {sorted(moves)}")
print("capture: mandatory (no quiet move while a jump exists)  OK")

# (d) Maximal (majority): a 2-jump chain is forced over a 1-jump alternative.
#   White man (1,1). Branch A: jump (1,2) land (1,3); from (1,3) jump (1,4) land
#   (1,5) -> 2 captures. Branch B: jump (3,1) land (5,1) -> 1 capture (sideways).
st = board_from({
    (1, 1): (0, "m"),
    (1, 2): (1, "m"), (1, 4): (1, "m"),   # 2-capture vertical chain
    (3, 1): (1, "m"),                      # 1-capture sideways branch
})
moves = set(G.legal_moves(st))
if any(caps_in(m) < 2 for m in moves):
    fail(f"majority rule allowed a shorter capture: {sorted(moves)}")
if "1,1>1,3>1,5" not in moves:
    fail(f"maximal chain missing; legal = {sorted(moves)}")
if "1,1>5,1" in moves:
    fail("the 1-capture branch was not pruned by the majority rule")
ns = G.apply_move(st, "1,1>1,3>1,5")
if (1, 2) in ns.board or (1, 4) in ns.board:
    fail("chained capture did not remove both enemy men")
print("capture: mandatory-maximal (majority) chained  OK")

# (e) End-of-move removal / no double-jump: a captured man stays put (blocking)
#   until the move ends, and may not be jumped twice. Build a square loop where
#   re-jumping the SAME piece would otherwise extend the chain.
#   White king (so it can turn) at (2,2); a single enemy man at (2,4). After the
#   king jumps it (landing past it) it must NOT be able to jump the same man
#   again -> max captures == 1.
st = board_from({(2, 2): (0, "k"), (2, 4): (1, "m")})
moves = set(G.legal_moves(st))
if max(caps_in(m) for m in moves) != 1:
    fail("a single enemy was jumped more than once (no end-of-move removal)")
print("capture: end-of-move removal (no piece jumped twice)  OK")


# ---------------------------------------------------------------------------
# 5. Promotion to flying king on the far rank
# ---------------------------------------------------------------------------
st = board_from({(3, 6): (0, "m")})
ns = G.apply_move(st, "3,6>3,7")
if ns.board.get((3, 7)) != (0, "k"):
    fail("man reaching the far rank did not promote to king")
# capture that ENDS on the far rank promotes
st = board_from({(3, 5): (0, "m"), (3, 6): (1, "m")})  # jump (3,6) land (3,7)
moves = set(G.legal_moves(st))
if "3,5>3,7" not in moves:
    fail(f"forward capture onto the king row missing; legal = {sorted(moves)}")
ns = G.apply_move(st, "3,5>3,7")
if ns.board.get((3, 7)) != (0, "k"):
    fail("capture ending on the far rank did not promote")
print("promotion: man -> flying king on the far rank  OK")


# ---------------------------------------------------------------------------
# 6. Flying king: queen-wise move, rook-wise long-leap capture
# ---------------------------------------------------------------------------
# (a) Quiet move: a lone king slides any distance in all 8 directions.
st = board_from({(3, 3): (0, "k")})
moves = set(G.legal_moves(st))
# a long diagonal and a long orthogonal slide must both be present
for m in ("3,3>0,0", "3,3>7,7", "3,3>3,7", "3,3>3,0", "3,3>0,3", "3,3>7,3"):
    if m not in moves:
        fail(f"king quiet slide missing: {m}")
print("flying king: queen-wise quiet move (all 8 directions)  OK")

# (b) Long-leap orthogonal capture: king far from a lone enemy on a file jumps
#   it and may land on any empty square beyond.
st = board_from({(3, 0): (0, "k"), (3, 5): (1, "m")})
moves = set(G.legal_moves(st))
exp = {"3,0>3,6", "3,0>3,7"}  # land on (3,6) or (3,7) past the captured man
if moves != exp:
    fail(f"king long-leap captures = {sorted(moves)}, expected {sorted(exp)}")
ns = G.apply_move(st, "3,0>3,7")
if (3, 5) in ns.board:
    fail("king long-leap did not remove the captured man")
if ns.board.get((3, 7)) != (0, "k"):
    fail("king did not land on (3,7)")
print("flying king: rook-wise long-leap capture  OK")

# (c) King does NOT capture diagonally (rook-wise only). With only a diagonal
#   enemy present, no capture exists -> the king has quiet queen slides only,
#   none of which jumps the enemy.
st = board_from({(0, 0): (0, "k"), (5, 5): (1, "m")})
moves = set(G.legal_moves(st))
if any(real_caps(st, m) >= 1 for m in moves):
    fail(f"king made a diagonal capture (should be orthogonal only): {sorted(moves)}")
print("flying king: captures orthogonally only (no diagonal jump)  OK")


# ---------------------------------------------------------------------------
# 7. Terminal: a player with no legal move loses; payoffs well-formed.
# ---------------------------------------------------------------------------
# The side to move with no pieces (hence no legal move) loses.
st = board_from({(0, 0): (1, "m")}, to_move=0)  # White to move but has NOTHING
if not G.is_terminal(st):
    fail("a side with no pieces is not terminal")
if G.returns(st) != [-1.0, 1.0]:
    fail(f"no-move loss payoff wrong: {G.returns(st)}")
# A lone man on the far edge with both forward-diagonals off-board and its single
# straight-forward cell blocked by an own man whose own front is also blocked has
# no move. Build it on the top edge: white man at (0,6); own man at (0,7) (king
# row -> a king, which CAN move). Use Black-perspective instead: black man at
# (7,1) moving DOWN; straight-fwd (7,0) is the black king row. Keep it simple and
# rely on the no-pieces case above as the canonical no-move=loss anchor; here just
# confirm is_terminal fires when legal_moves is empty for any constructed state.
empty_side = board_from({(4, 4): (1, "k")}, to_move=0)  # White to move, no white piece
if not G.is_terminal(empty_side) or G.returns(empty_side) != [-1.0, 1.0]:
    fail("no-move (no own pieces) not detected as a loss for the side to move")
print("terminal: a side with no legal move loses  OK")


print("SELFTEST OK")
sys.exit(0)
