"""Selftest for Mak-yek (Thai/Cambodian; Apit-sodok).

Pure-stdlib correctness anchor (no third-party libs, fast). Run with:
    PYTHONPATH=. python3 games/mak_yek/selftest.py

Asserts the baked rule facts:
  (1) men move like a rook (any distance orthogonally, no diagonal, no jumping);
  (2) CUSTODIAL capture of a single man and of an unbroken enemy line, active
      (moving INTO a sandwich is safe), gap breaks the bracket;
  (3) INTERVENTION capture: landing between two enemy men one apart captures
      BOTH (and is the mover's, so the mover is safe);
  (4) multi-direction capture on one move;
  (5) win = capture ALL enemy men (annihilation), reached via apply_move.
"""

import sys

from games.mak_yek.game import MakYek, MYState, N, SETUP_ROWS


def st(board, to_move=0, ply=0, winner=None):
    return MYState(board=dict(board), to_move=to_move, ply=ply, winner=winner)


def moves(g, s):
    return set(g.legal_moves(s))


G = MakYek()

# ---------------------------------------------------------------------------
# (0) initial state / setup: 16 men each, on first and third rank from player
# ---------------------------------------------------------------------------
s0 = G.initial_state()
assert sum(1 for o in s0.board.values() if o == 0) == 16, "player 0 should have 16 men"
assert sum(1 for o in s0.board.values() if o == 1) == 16, "player 1 should have 16 men"
assert all(s0.board[(c, 0)] == 0 for c in range(N)), "player 0 fills row 0"
assert all(s0.board[(c, 2)] == 0 for c in range(N)), "player 0 fills row 2"
assert all(s0.board[(c, 5)] == 1 for c in range(N)), "player 1 fills row 5"
assert all(s0.board[(c, 7)] == 1 for c in range(N)), "player 1 fills row 7"
assert all((c, 1) not in s0.board for c in range(N)), "row 1 starts empty"
assert SETUP_ROWS == {0: (0, 2), 1: (5, 7)}, "setup rows = first and third rank"
assert G.current_player(s0) == 0
assert not G.is_terminal(s0)
assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0), "serialize round-trip"

# ---------------------------------------------------------------------------
# (1) rook movement: any distance orthogonally, no diagonal, no jumping
# ---------------------------------------------------------------------------
s = st({(4, 4): 0}, to_move=0)
ms = moves(G, s)
expected = set()
for c in range(N):
    if c != 4:
        expected.add(f"4,4>{c},4")
for r in range(N):
    if r != 4:
        expected.add(f"4,4>4,{r}")
assert ms == expected, f"rook move set wrong: {ms ^ expected}"
assert "4,4>5,5" not in ms, "diagonal move should be illegal"

# blocking: path stops at the blocker and never jumps it
s = st({(4, 2): 0, (4, 5): 1}, to_move=0)
ms = moves(G, s)
assert "4,2>4,4" in ms, "should reach square before blocker"
assert "4,2>4,5" not in ms, "cannot land on enemy"
assert "4,2>4,6" not in ms, "cannot jump over a piece"
assert "4,2>4,7" not in ms, "cannot jump over a piece"

# ---------------------------------------------------------------------------
# (2a) CUSTODIAL capture of a single enemy man
# ---------------------------------------------------------------------------
# friendly flank at (5,4), enemy at (4,4); land a friendly man at (3,4) -> (4,4) gone
s = st({(5, 4): 0, (4, 4): 1, (3, 0): 0}, to_move=0)
s2 = G.apply_move(s, "3,0>3,4")
assert (4, 4) not in s2.board, "single flanked enemy must be captured"
assert (3, 4) in s2.board and (5, 4) in s2.board, "flankers remain"

# ---------------------------------------------------------------------------
# (2b) CUSTODIAL capture of an unbroken LINE of enemy men
# ---------------------------------------------------------------------------
s = st({(7, 4): 0, (4, 4): 1, (5, 4): 1, (6, 4): 1, (3, 0): 0}, to_move=0)
s2 = G.apply_move(s, "3,0>3,4")
for cell in [(4, 4), (5, 4), (6, 4)]:
    assert cell not in s2.board, f"line capture should remove {cell}"

# a GAP breaks the bracket: enemy, empty, enemy -> nothing captured
s = st({(7, 4): 0, (4, 4): 1, (6, 4): 1, (3, 0): 0}, to_move=0)
s2 = G.apply_move(s, "3,0>3,4")
assert (4, 4) in s2.board and (6, 4) in s2.board, "gap must prevent custodial capture"

# ---------------------------------------------------------------------------
# (2c) capture is ACTIVE — moving INTO a custodial sandwich is safe
# ---------------------------------------------------------------------------
# friendlies at (3,4),(5,4) is intervention-shaped for ENEMY; here test custodial:
# enemies at (3,4) and (5,4); player 0 moves a man to (4,4). Intervention fires
# (that is mode 3); to test the "into a sandwich is safe" custodial sense, use a
# friendly flank scenario where the MOVER is the bracketed colour:
# enemies (2,4) friendly-flank pattern would capture the mover only if passive.
# Simpler: a man sliding between two ENEMIES is not removed (it captures, 2c==3a).
s = st({(3, 4): 1, (5, 4): 1, (4, 0): 0}, to_move=0)
s2 = G.apply_move(s, "4,0>4,4")
assert (4, 4) in s2.board and s2.board[(4, 4)] == 0, "man moving into a sandwich is safe"

# ---------------------------------------------------------------------------
# (3) INTERVENTION capture: land between two enemies one apart -> BOTH captured
# ---------------------------------------------------------------------------
s = st({(3, 4): 1, (5, 4): 1, (4, 0): 0}, to_move=0)
s2 = G.apply_move(s, "4,0>4,4")
assert (3, 4) not in s2.board and (5, 4) not in s2.board, "intervention captures BOTH enemies"
assert (4, 4) in s2.board, "intervening man survives"

# intervention along a column too
s = st({(4, 3): 1, (4, 5): 1, (0, 4): 0}, to_move=0)
s2 = G.apply_move(s, "0,4>4,4")
assert (4, 3) not in s2.board and (4, 5) not in s2.board, "column intervention captures BOTH"

# intervention needs enemies on BOTH sides: only one side -> no intervention
s = st({(3, 4): 1, (4, 0): 0}, to_move=0)
s2 = G.apply_move(s, "4,0>4,4")
assert (3, 4) in s2.board, "single adjacent enemy is not an intervention capture"

# a friendly (not enemy) on one side -> no intervention capture
s = st({(3, 4): 0, (5, 4): 1, (4, 0): 0}, to_move=0)
s2 = G.apply_move(s, "4,0>4,4")
assert (5, 4) in s2.board, "intervention requires ENEMY on both sides"

# ---------------------------------------------------------------------------
# (4) one move captures in MULTIPLE directions at once
# ---------------------------------------------------------------------------
# Land at (4,4): custodial to the right (enemy (5,4), friend (6,4)) AND
# custodial upward (enemy (4,5), friend (4,6)). Both removed in one move.
s = st({(4, 0): 0, (5, 4): 1, (6, 4): 0, (4, 5): 1, (4, 6): 0}, to_move=0)
s2 = G.apply_move(s, "4,0>4,4")
assert (5, 4) not in s2.board, "rightward custodial capture"
assert (4, 5) not in s2.board, "upward custodial capture"
assert (6, 4) in s2.board and (4, 6) in s2.board, "friendly flankers remain"

# ---------------------------------------------------------------------------
# (5) WIN = capture ALL enemy men (annihilation), reached via apply_move
# ---------------------------------------------------------------------------
# Player 1 has exactly one man; player 0 captures it custodially -> opp at 0.
s = st({(5, 4): 0, (4, 4): 1, (3, 0): 0}, to_move=0)
assert sum(1 for o in s.board.values() if o == 1) == 1
s2 = G.apply_move(s, "3,0>3,4")
assert sum(1 for o in s2.board.values() if o == 1) == 0, "last enemy captured"
assert s2.winner == 0, "capturing all enemy men wins"
assert G.is_terminal(s2)
assert G.returns(s2) == [1.0, -1.0]

# capturing two-via-intervention down to zero also wins
s = st({(3, 4): 1, (5, 4): 1, (4, 0): 0}, to_move=0)
s2 = G.apply_move(s, "4,0>4,4")
assert sum(1 for o in s2.board.values() if o == 1) == 0
assert s2.winner == 0, "intervention that clears the last enemies wins"

# not terminal while the opponent still has a man and a move
s = st({(5, 4): 0, (4, 4): 1, (3, 0): 0, (0, 7): 1}, to_move=0)
s2 = G.apply_move(s, "3,0>3,4")
assert sum(1 for o in s2.board.values() if o == 1) == 1
assert s2.winner is None and not G.is_terminal(s2), "one enemy man left -> not won yet"

print("SELFTEST OK")
sys.exit(0)
