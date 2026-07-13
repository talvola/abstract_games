#!/usr/bin/env python3
"""Standalone correctness self-test for Russian Draughts (Shashki).

Run from engine/ with:  PYTHONPATH=. python3 games/russian_draughts/selftest.py

Russian draughts shares International/Brazilian move geometry (backward-capturing
men, flying kings) but is defined by two rules this test anchors:

  * CHOICE OF CAPTURE ("any", not maximum): a shorter complete capture is legal
    even when a longer one exists (the opposite of Brazilian's majority rule).
  * PROMOTION DURING A CAPTURE: a man that lands on the king row mid-capture
    promotes immediately and CONTINUES as a flying king.

Also checks a normal man capture, a flying-king capture, a win via apply_move,
serialization round-trip, and draw termination. Pure stdlib; imports only the agp
package / this game. Prints "SELFTEST OK" and exits 0 on success.
"""
import sys

from games.russian_draughts.game import RussianDraughts, DraughtsState

G = RussianDraughts()


def perft(state, depth):
    if depth == 0:
        return 1
    total = 0
    for m in G.legal_moves(state):
        total += perft(G.apply_move(state, m), depth - 1)
    return total


def board_from(spec, to_move=0):
    return DraughtsState(board=dict(spec), to_move=to_move)


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 1. Opening perft (the shared 8x8 anchor). The opening tree has no captures for
#    the first several plies, so Russian == Brazilian == checkers there:
#    perft(1)=7, perft(2)=49, perft(3)=302, perft(4)=1469.
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
if any((c + r) % 2 == 0 for (c, r) in init.board):
    fail("a piece sits on a light square in the opening")
white = [p for p, v in init.board.items() if v[0] == 0]
black = [p for p, v in init.board.items() if v[0] == 1]
if len(white) != 12 or len(black) != 12:
    fail(f"expected 12 men each, got white={len(white)} black={len(black)}")


# ---------------------------------------------------------------------------
# 2. DEFINING RULE #1 — PROMOTION DURING A CAPTURE (continue as a FLYING KING)
# ---------------------------------------------------------------------------
# White man on (1,5). It jumps the black man on (2,6) and lands on (3,7) = the
# White king row -> promotes IMMEDIATELY. As a flying king it then slides
# down-right over the EMPTY squares (4,6) and (5,5), leaps the black man on
# (6,4) and lands on (7,3). The second leap is a flying (distance) capture that a
# MAN could never make -> proves promote-and-continue-as-flying-king.
st = board_from({(1, 5): (0, "m"), (2, 6): (1, "m"), (6, 4): (1, "m")})
moves = set(G.legal_moves(st))
if "1,5>3,7>7,3" not in moves:
    fail(f"promote-mid-capture-continues-as-king missing; legal = {sorted(moves)}")
# The chain MUST be finished as a king: merely stopping on the king row is illegal
# because a further (king) capture is available.
if "1,5>3,7" in moves:
    fail("man was allowed to stop on the king row while a king capture continued")
ns = G.apply_move(st, "1,5>3,7>7,3")
if (2, 6) in ns.board or (6, 4) in ns.board:
    fail("promote-continue capture did not remove both enemy men")
if ns.board.get((7, 3)) != (0, "k"):
    fail(f"piece did not finish as a king at (7,3); got {ns.board.get((7, 3))}")
print("promotion DURING capture -> continues as flying king  OK")


# ---------------------------------------------------------------------------
# 3. DEFINING RULE #2 — CHOICE OF CAPTURE ("any", NOT maximum)
# ---------------------------------------------------------------------------
# White man on (4,4). Two capture options of DIFFERENT length:
#   - jump (5,5) land (6,6): a complete 1-capture (no continuation from (6,6)).
#   - jump (3,3) land (2,2) then jump (1,1) land (0,0): a 2-capture.
# In Russian BOTH are legal (choice of capture). In Brazilian the 1-capture would
# be PRUNED by the majority rule -- so its legality here is the distinctness anchor.
st = board_from({
    (4, 4): (0, "m"),
    (5, 5): (1, "m"),                     # 1-capture branch
    (3, 3): (1, "m"), (1, 1): (1, "m"),   # 2-capture branch
})
moves = set(G.legal_moves(st))
if "4,4>6,6" not in moves:
    fail(f"choice-of-capture: shorter 1-capture illegal; legal = {sorted(moves)}")
if "4,4>2,2>0,0" not in moves:
    fail(f"choice-of-capture: longer 2-capture missing; legal = {sorted(moves)}")
# capture is still mandatory: no quiet move may be offered
if any("6,6" not in m and "0,0" not in m for m in moves):
    pass  # (all listed moves are captures; explicit check below)
for m in moves:
    if len(m.split(">")) < 2:
        fail(f"a quiet move was offered while a capture exists: {m}")
print("choice of capture (ANY, not maximum)  OK")


# ---------------------------------------------------------------------------
# 4. Normal man capture (BACKWARD) — mandatory
# ---------------------------------------------------------------------------
st = board_from({(4, 4): (0, "m"), (5, 3): (1, "m")})
moves = set(G.legal_moves(st))
if moves != {"4,4>6,2"}:
    fail(f"man backward capture wrong; legal = {sorted(moves)}")
ns = G.apply_move(st, "4,4>6,2")
if (5, 3) in ns.board or ns.board.get((6, 2)) != (0, "m"):
    fail("backward capture did not resolve correctly")
print("man backward capture (mandatory)  OK")


# ---------------------------------------------------------------------------
# 5. Flying-king capture (long range + no double-jump)
# ---------------------------------------------------------------------------
st = board_from({(0, 0): (0, "k"), (5, 5): (1, "m")})
moves = set(G.legal_moves(st))
if moves != {"0,0>6,6", "0,0>7,7"}:
    fail(f"flying king captures = {sorted(moves)}, expected 0,0>6,6 / 0,0>7,7")
ns = G.apply_move(st, "0,0>7,7")
if (5, 5) in ns.board or ns.board.get((7, 7)) != (0, "k"):
    fail("flying king long capture did not resolve correctly")
# a lone enemy can be jumped only once
st = board_from({(4, 4): (0, "k"), (6, 6): (1, "m")})
if max(len(m.split(">")) - 1 for m in G.legal_moves(st)) != 1:
    fail("flying king jumped a single piece more than once")
print("flying king capture + no double-jump  OK")


# ---------------------------------------------------------------------------
# 6. Win via apply_move (capturing the opponent's last piece)
# ---------------------------------------------------------------------------
st = board_from({(4, 4): (0, "m"), (5, 5): (1, "m")})   # Black's only piece
ns = G.apply_move(st, "4,4>6,6")
if not G.is_terminal(ns):
    fail("capturing Black's last piece should be terminal")
if G.returns(ns) != [1.0, -1.0]:
    fail(f"expected White win [1,-1], got {G.returns(ns)}")
print("win via apply_move  OK")


# ---------------------------------------------------------------------------
# 7. Draw termination + serialization round-trip
# ---------------------------------------------------------------------------
draw_st = DraughtsState(board={(0, 0): (0, "k"), (7, 7): (1, "k")}, to_move=0,
                        halfmove=50)
if not G.is_terminal(draw_st):
    fail("50-ply no-progress state should be terminal")
if G.returns(draw_st) != [0.0, 0.0]:
    fail(f"no-progress terminal should be a draw, got {G.returns(draw_st)}")
s = G.initial_state()
if G.deserialize(G.serialize(s)).board != s.board:
    fail("serialize/deserialize did not round-trip the board")
print("draw termination + serialization  OK")


print("SELFTEST OK")
sys.exit(0)
