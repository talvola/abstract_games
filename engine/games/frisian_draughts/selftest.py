#!/usr/bin/env python3
"""Standalone correctness self-test for Frisian Draughts (Frysk dammen).

Run from engine/ with:  PYTHONPATH=. python3 games/frisian_draughts/selftest.py

Pure-stdlib, fast (well under a second). Imports only this game's module.

Anchors asserted:

  1. Opening perft node counts (depths 1-3). In the opening no captures are yet
     possible, so the differing Frisian capture geometry does not change the
     move tree this shallow: the counts equal the published International /
     Polish-draughts opening perft confirmed by the World Draughts Forum
     (Ed Gilbert / Bert Tuyt / Feike Boomstra):
        perft(1)=9, perft(2)=81, perft(3)=658  (also 4265, 27117 at 4,5).
     https://damforum.nl/viewtopic.php?t=2308
     This validates the no-capture move generator and the dark-square setup.

  2. Frisian-specific rule positions (the distinguishing anchors):
       a. a MAN capturing ORTHOGONALLY (horizontal and vertical), not just
          diagonally -- the defining Frisian feature;
       b. a FLYING KING capturing along an ORTHOGONAL line at range;
       c. a mixed orthogonal-then-diagonal capture chain;
       d. the WEIGHTED maximum-capture rule:
            - on equal piece counts, a sequence capturing a KING is forced over
              one capturing a MAN (a king counts more than a man);
            - but piece count dominates: a 2-man capture is forced over a 1-king
              capture (a king is worth less than two men);
       e. no jumping the same piece twice (flying king).

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import sys

from games.frisian_draughts.game import FrisianDraughts, DraughtsState

G = FrisianDraughts()


def perft(state, depth):
    if depth == 0:
        return 1
    total = 0
    for m in G.legal_moves(state):
        total += perft(G.apply_move(state, m), depth - 1)
    return total


def bf(spec):
    """spec: dict of (c,r) -> (player, kind). State with White to move."""
    return DraughtsState(board=dict(spec), to_move=0)


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 1. Opening perft (no-capture move-gen + setup anchor)
# ---------------------------------------------------------------------------
PUBLISHED = {1: 9, 2: 81, 3: 658}
init = G.initial_state()
for d, expected in PUBLISHED.items():
    got = perft(init, d)
    if got != expected:
        fail(f"perft({d}) = {got}, expected {expected}")
    print(f"perft({d}) = {got}  OK (published {expected})")

if len(init.board) != 40:
    fail(f"opening has {len(init.board)} pieces, expected 40")
if any((c + r) % 2 == 0 for (c, r) in init.board):
    fail("a piece sits on a light square in the opening")
print("opening setup (40 men, dark squares)  OK")


# ---------------------------------------------------------------------------
# 2a. Man captures ORTHOGONALLY (the defining Frisian rule)
# ---------------------------------------------------------------------------
# Pieces live on dark squares (odd col+row). Two dark squares in the same row
# are TWO columns apart with a light square between, so a horizontal capture
# jumps the dark square two away and lands two beyond (four total).
# White man (3,4); black man (5,4) horizontally adjacent (dark); land (7,4).
st = bf({(3, 4): (0, "m"), (5, 4): (1, "m")})
moves = set(G.legal_moves(st))
if moves != {"3,4>7,4"}:
    fail(f"horizontal man capture wrong; legal = {sorted(moves)}")
ns = G.apply_move(st, "3,4>7,4")
if (5, 4) in ns.board or ns.board.get((7, 4)) != (0, "m"):
    fail("horizontal capture did not remove enemy / land correctly")
print("man horizontal capture  OK")

# Vertical: white man (3,4); black man (3,6); land (3,8).
st = bf({(3, 4): (0, "m"), (3, 6): (1, "m")})
if set(G.legal_moves(st)) != {"3,4>3,8"}:
    fail(f"vertical man capture wrong; legal = {sorted(G.legal_moves(st))}")
print("man vertical capture  OK")

# A man with NO capture still moves diagonally FORWARD only (no quiet ortho move).
st = bf({(3, 4): (0, "m")})
qm = set(G.legal_moves(st))
if qm != {"3,4>2,5", "3,4>4,5"}:
    fail(f"man quiet moves should be diagonal-forward only; got {sorted(qm)}")
print("man quiet move diagonal-forward only  OK")


# ---------------------------------------------------------------------------
# 2b. Flying king captures along an ORTHOGONAL line at range
# ---------------------------------------------------------------------------
# White king (1,0); lone black man (1,4) on the same file; king may land on any
# empty dark square beyond: (1,6) or (1,8).
st = bf({(1, 0): (0, "k"), (1, 4): (1, "m")})
moves = set(G.legal_moves(st))
if moves != {"1,0>1,6", "1,0>1,8"}:
    fail(f"king vertical flying capture = {sorted(moves)}")
ns = G.apply_move(st, "1,0>1,8")
if (1, 4) in ns.board or ns.board.get((1, 8)) != (0, "k"):
    fail("king vertical flying capture did not resolve correctly")
print("flying king vertical capture  OK")

# Horizontal flying king.
st = bf({(0, 1): (0, "k"), (4, 1): (1, "m")})
if set(G.legal_moves(st)) != {"0,1>6,1", "0,1>8,1"}:
    fail(f"king horizontal flying capture = {sorted(G.legal_moves(st))}")
print("flying king horizontal capture  OK")

# Diagonal still works exactly as in International draughts.
st = bf({(0, 0): (0, "k"), (5, 5): (1, "m")})
if set(G.legal_moves(st)) != {"0,0>6,6", "0,0>7,7", "0,0>8,8", "0,0>9,9"}:
    fail(f"king diagonal flying capture = {sorted(G.legal_moves(st))}")
print("flying king diagonal capture  OK")


# ---------------------------------------------------------------------------
# 2c. Mixed orthogonal-then-diagonal capture chain
# ---------------------------------------------------------------------------
# Man (1,4): jump black man (3,4) horizontally -> land (5,4); then jump black
# man (6,5) diagonally -> land (7,6). A 2-piece chain mixing line types.
st = bf({(1, 4): (0, "m"), (3, 4): (1, "m"), (6, 5): (1, "m")})
moves = set(G.legal_moves(st))
if moves != {"1,4>5,4>7,6"}:
    fail(f"mixed ortho+diag chain = {sorted(moves)}")
ns = G.apply_move(st, "1,4>5,4>7,6")
if (3, 4) in ns.board or (6, 5) in ns.board:
    fail("mixed chain did not remove both captured men")
print("mixed orthogonal+diagonal chain  OK")


# ---------------------------------------------------------------------------
# 2d. Weighted maximum-capture rule
# ---------------------------------------------------------------------------
# (i) Equal piece count -> capturing a KING is forced over capturing a MAN.
# Two separate white kings, each with one isolated single capture:
#   King A (1,0): captures the black KING (1,4)   -> value (1 piece, 1 king)
#   King B (9,9): captures the black MAN  (6,6)   -> value (1 piece, 0 kings)
st = bf({(1, 0): (0, "k"), (1, 4): (1, "k"),
         (9, 9): (0, "k"), (6, 6): (1, "m")})
moves = set(G.legal_moves(st))
if moves != {"1,0>1,6", "1,0>1,8"}:
    fail(f"weighting should force the king-capture only; got {sorted(moves)}")
print("weighted capture: king preferred over man on equal count  OK")

# (ii) Piece count dominates -> a 2-man capture beats a 1-king capture
#      (a king is worth LESS than two men).
#   Man A (1,2): diagonal chain of two black MEN -> value (2, 0)
#   Man B (1,8): single horizontal capture of a black KING -> value (1, 1)
st = bf({(1, 2): (0, "m"), (2, 3): (1, "m"), (4, 5): (1, "m"),
         (1, 8): (0, "m"), (3, 8): (1, "k")})
moves = set(G.legal_moves(st))
if moves != {"1,2>3,4>5,6"}:
    fail(f"count should dominate (2 men > 1 king); got {sorted(moves)}")
print("weighted capture: piece count dominates king value  OK")

# (iii) The weighting must be the official SUMMED value (king = 1.5 men),
# i.e. _value = 2*captures + kings as an INT — NOT a lexicographic
# (count, then kings) tuple. The summed rule diverges from count-first exactly
# where the counts differ but king-weight flips it: e.g. 2 kings (value 6) TIE
# 3 men (value 6), and 3 kings (value 9) BEAT 4 men (value 8). Guard the formula
# directly so a regression to the tuple ordering is caught.
vk = G._value(bf({(1, 0): (0, "k"), (1, 4): (1, "k")}).board, [(1, 0), (1, 6)])
vm = G._value(bf({(1, 0): (0, "k"), (1, 4): (1, "m")}).board, [(1, 0), (1, 6)])
if not (isinstance(vk, int) and isinstance(vm, int)):
    fail(f"_value must be a summed int, got {vk!r}/{vm!r} (regressed to a tuple?)")
if vk != 3 or vm != 2:
    fail(f"summed weighting wrong: 1-king={vk} (want 3), 1-man={vm} (want 2)")
if not (2 * 2 + 2 == 2 * 3 + 0 and 2 * 3 + 3 > 2 * 4 + 0):
    fail("summed weighting identities broken (2K must tie 3M; 3K must beat 4M)")
print("weighted capture: official summed value, king = 1.5 men  OK")


# ---------------------------------------------------------------------------
# 2e. No jumping the same piece twice (flying king)
# ---------------------------------------------------------------------------
# King (4,4)? 4+4 even = light; use (3,4) dark. Lone black man (5,4): the king may
# jump it once but may not turn around and jump it again -> only 1-piece captures.
st = bf({(3, 4): (0, "k"), (5, 4): (1, "m")})
moves = G.legal_moves(st)
if max(len(m.split(">")) - 1 for m in moves) != 1:
    fail("flying king jumped a single piece more than once")
print("no double-jump of one piece  OK")


# ---------------------------------------------------------------------------
# 2f. End-of-move promotion only
# ---------------------------------------------------------------------------
st = bf({(4, 8): (0, "m")})
ns = G.apply_move(st, "4,8>5,9")
if ns.board.get((5, 9)) != (0, "k"):
    fail("man ending on last rank did not promote")
print("promotion (end-of-move)  OK")


print("SELFTEST OK")
sys.exit(0)
