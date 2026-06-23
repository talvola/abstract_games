"""Selftest for Hasami Shogi (Dai Hasami Shogi).

Pure-stdlib correctness anchor (no third-party libs, fast). Run with:
    PYTHONPATH=. python3 games/hasami_shogi/selftest.py

Asserts the baked rule facts:
  (1) men move like a rook (any distance orthogonally, never jumping);
  (2) custodial capture of a single man and of an unbroken enemy line, that
      capture is active (a man moving INTO a sandwich is safe), and the corner
      capture;
  (3) the five-in-a-row win and the decimation win, each REACHED via apply_move.
"""

import sys

from games.hasami_shogi.game import HasamiShogi, HSState, N


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def st(board, to_move=0, ply=0, winner=None):
    return HSState(board=dict(board), to_move=to_move, ply=ply, winner=winner)


def moves(g, s):
    return set(g.legal_moves(s))


G = HasamiShogi()

# ---------------------------------------------------------------------------
# (0) initial state sanity
# ---------------------------------------------------------------------------
s0 = G.initial_state()
assert sum(1 for o in s0.board.values() if o == 0) == 9, "player 0 should have 9 men"
assert sum(1 for o in s0.board.values() if o == 1) == 9, "player 1 should have 9 men"
assert all(s0.board[(c, 0)] == 0 for c in range(N)), "player 0 fills row 0"
assert all(s0.board[(c, N - 1)] == 1 for c in range(N)), "player 1 fills row 8"
assert G.current_player(s0) == 0
assert not G.is_terminal(s0)
# serialize round-trips
assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0), "serialize round-trip"

# ---------------------------------------------------------------------------
# (1) rook movement: any distance orthogonally, no diagonal, no jumping
# ---------------------------------------------------------------------------
# lone man on a near-empty board: full file + rank reachable
s = st({(4, 4): 0}, to_move=0)
ms = moves(G, s)
# whole file (column 4) and rank (row 4) minus its own square = 16 cells
expected = set()
for c in range(N):
    if c != 4:
        expected.add(f"4,4>{c},4")
for r in range(N):
    if r != 4:
        expected.add(f"4,4>4,{r}")
assert ms == expected, f"rook move set wrong: {ms ^ expected}"
# no diagonal moves
assert "4,4>5,5" not in ms, "diagonal move should be illegal"

# blocking: a piece in the path stops the slide and is NOT jumped
s = st({(4, 4): 0, (4, 6): 1}, to_move=0)
ms = moves(G, s)
assert "4,4>4,5" in ms, "should reach square before blocker"
assert "4,4>4,6" not in ms, "cannot land on enemy"
assert "4,4>4,7" not in ms, "cannot jump over a piece"
assert "4,4>4,8" not in ms, "cannot jump over a piece"

# ---------------------------------------------------------------------------
# (2a) custodial capture of a single enemy man
# ---------------------------------------------------------------------------
# friendly at (5,4), enemy at (4,4); move a friendly man to (3,4) -> 4,4 captured
s = st({(5, 4): 0, (4, 4): 1, (3, 0): 0}, to_move=0)
s2 = G.apply_move(s, "3,0>3,4")
assert (4, 4) not in s2.board, "single sandwiched enemy man must be captured"
assert (3, 4) in s2.board and (5, 4) in s2.board, "flankers remain"

# ---------------------------------------------------------------------------
# (2b) custodial capture of an unbroken LINE of enemy men
# ---------------------------------------------------------------------------
# enemies at (4,4),(5,4),(6,4); friendly far flank at (7,4); land friendly at (3,4)
s = st({(7, 4): 0, (4, 4): 1, (5, 4): 1, (6, 4): 1, (3, 0): 0}, to_move=0)
s2 = G.apply_move(s, "3,0>3,4")
for cell in [(4, 4), (5, 4), (6, 4)]:
    assert cell not in s2.board, f"line capture should remove {cell}"

# a GAP breaks the bracket: enemy, empty, enemy -> nothing captured
s = st({(7, 4): 0, (4, 4): 1, (6, 4): 1, (3, 0): 0}, to_move=0)
s2 = G.apply_move(s, "3,0>3,4")
assert (4, 4) in s2.board and (6, 4) in s2.board, "gap must prevent capture"

# ---------------------------------------------------------------------------
# (2c) capture is ACTIVE — moving INTO a sandwich is safe
# ---------------------------------------------------------------------------
# enemies at (3,4) and (5,4); player 0 moves a man into (4,4) between them.
s = st({(3, 4): 1, (5, 4): 1, (4, 0): 0}, to_move=0)
s2 = G.apply_move(s, "4,0>4,4")
assert (4, 4) in s2.board and s2.board[(4, 4)] == 0, "man moving into a sandwich is safe"
assert (3, 4) in s2.board and (5, 4) in s2.board, "enemies remain"

# and the enemy must not be self-captured either: it is the mover who captures
# (no capture of the just-moved piece)
assert sum(1 for o in s2.board.values() if o == 0) == 1

# ---------------------------------------------------------------------------
# (2d) corner capture
# ---------------------------------------------------------------------------
# enemy on corner (0,0); player 0 holds (1,0) already and moves a man to (0,1)
s = st({(0, 0): 1, (1, 0): 0, (0, 5): 0}, to_move=0)
s2 = G.apply_move(s, "0,5>0,1")
assert (0, 0) not in s2.board, "corner enemy must be captured when both neighbours held"

# corner NOT captured if only one neighbour held
s = st({(0, 0): 1, (0, 5): 0}, to_move=0)
s2 = G.apply_move(s, "0,5>0,1")
assert (0, 0) in s2.board, "corner safe with only one neighbour held"

# ---------------------------------------------------------------------------
# (3a) five-in-a-row win reached via apply_move
# ---------------------------------------------------------------------------
# Player 0: four men in a row on row 4 at c=1..4, plus one man to slide in at c=5.
s = st({(1, 4): 0, (2, 4): 0, (3, 4): 0, (4, 4): 0, (5, 7): 0,
        (8, 8): 1, (7, 8): 1}, to_move=0)
assert not G.is_terminal(s)
s2 = G.apply_move(s, "5,7>5,4")  # completes 1..5 on row 4 (off home row 0)
assert s2.winner == 0, "five orthogonally in a row off home row should win"
assert G.is_terminal(s2)
assert G.returns(s2) == [1.0, -1.0]

# diagonal five-in-a-row also wins
s = st({(0, 1): 0, (1, 2): 0, (2, 3): 0, (3, 4): 0, (4, 6): 0,
        (8, 8): 1, (7, 8): 1}, to_move=0)
s2 = G.apply_move(s, "4,6>4,5")  # diagonal (0,1)(1,2)(2,3)(3,4)(4,5)
assert s2.winner == 0, "five diagonally in a row off home row should win"

# a five-in-a-row that lies ON the home row does NOT win
# player 0 home row is row 0: line entirely on row 0 must be ignored
s = st({(0, 0): 0, (1, 0): 0, (2, 0): 0, (3, 0): 0, (4, 5): 0,
        (8, 8): 1, (7, 8): 1}, to_move=0)
s2 = G.apply_move(s, "4,5>4,0")  # makes 0..4 on row 0 (the home row)
assert s2.winner is None, "five-in-a-row on the home row must not win"

# ---------------------------------------------------------------------------
# (3b) decimation win reached via apply_move
# ---------------------------------------------------------------------------
# Player 1 has exactly 2 men; player 0 captures one (custodial) -> opp down to 1.
s = st({(5, 4): 0, (4, 4): 1, (3, 0): 0, (8, 8): 1}, to_move=0)
assert sum(1 for o in s.board.values() if o == 1) == 2
s2 = G.apply_move(s, "3,0>3,4")  # captures (4,4); player 1 left with just (8,8)
assert sum(1 for o in s2.board.values() if o == 1) == 1
assert s2.winner == 0, "reducing opponent to a single man should win"
assert G.is_terminal(s2)

print("SELFTEST OK")
sys.exit(0)
