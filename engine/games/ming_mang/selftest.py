"""Selftest for Ming Mang (Mig-mang / Gundru) — pure stdlib.

Run with:  PYTHONPATH=. python3 games/ming_mang/selftest.py

Anchors:
  (a) Wikipedia's enumerated multi-capture cases (one-line-both-sides,
      row+column, three directions) with exact CONVERSIONS;
  (b) conversion invariant: board population constant (= 2*(2n-2)) after
      EVERY move of a random playout, which reaches a terminal;
  (c) corner immunity (emergent — no cell beyond the corner);
  (d) moving INTO a sandwich is safe + NO intervention capture;
  (e) positional superko: a would-repeat move is absent from legal_moves;
  (f) cannot-move LOSS reached via apply_move (blockade), and
      annihilation-by-conversion win reached via apply_move;
  (g) frozen opening legal-move counts for sizes 8 / 9 / 17;
  (h) 180-degree symmetry of the opening move sets;
  (i) last_stone_leap: leap REMOVES (not converts), is optional, only for a
      lone stone, and absent when the option is off.
"""

import random
import sys

from games.ming_mang.game import (
    MingMang, MMState, position_key, start_board,
)


def st(board, to_move=0, n=8, leap=False, ply=0, no_progress=0):
    b = dict(board)
    return MMState(n=n, leap=leap, board=b, to_move=to_move, ply=ply,
                   no_progress=no_progress,
                   history=[position_key(b, to_move)])


G = MingMang()

# ---------------------------------------------------------------------------
# (0) initial state / setup / round-trip
# ---------------------------------------------------------------------------
s0 = G.initial_state()
assert s0.n == 8
assert sum(1 for o in s0.board.values() if o == 0) == 14, "Black has 2n-2=14"
assert sum(1 for o in s0.board.values() if o == 1) == 14, "White has 2n-2=14"
assert all(s0.board[(0, r)] == 0 for r in range(8)), "Black fills left file"
assert all(s0.board[(c, 0)] == 0 for c in range(1, 7)), "Black fills bottom interior"
assert all(s0.board[(7, r)] == 1 for r in range(8)), "White fills right file"
assert all(s0.board[(c, 7)] == 1 for c in range(1, 7)), "White fills top interior"
assert G.current_player(s0) == 0, "Black (seat 0) moves first"
assert not G.is_terminal(s0)
assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0), "round-trip"
# 180-degree rotational symmetry of the setup itself
assert all(s0.board[(7 - c, 7 - r)] == 1 - o for (c, r), o in s0.board.items())

# rook movement basics: no diagonal, no jumping, land empty
s = st({(4, 4): 0, (7, 7): 1})
ms = set(G.legal_moves(s))
assert "4,4>5,5" not in ms, "no diagonal"
assert "4,4>7,4" in ms and "4,4>4,7" in ms, "full rook range"
s = st({(4, 2): 0, (4, 5): 1, (0, 0): 1})
ms = set(G.legal_moves(s))
assert "4,2>4,4" in ms and "4,2>4,5" not in ms and "4,2>4,6" not in ms, \
    "stop before a blocker, never jump/land on it"

# ---------------------------------------------------------------------------
# (a) Wikipedia's multi-capture cases — captures CONVERT in place
# ---------------------------------------------------------------------------
# Case 1: one line, both sides — F E E _ E F on row 4; land in the gap.
s = st({(0, 4): 0, (1, 4): 1, (2, 4): 1, (4, 4): 1, (5, 4): 0,
        (3, 0): 0, (7, 7): 1})
before = len(s.board)
s2 = G.apply_move(s, "3,0>3,4")
for cell in [(1, 4), (2, 4), (4, 4)]:
    assert s2.board[cell] == 0, f"{cell} must CONVERT to the mover"
assert len(s2.board) == before, "conversion keeps population constant"
assert s2.no_progress == 0, "capture resets the no-progress counter"

# Case 2: row + column simultaneously.
s = st({(3, 0): 0, (4, 4): 1, (5, 4): 0, (3, 5): 1, (3, 6): 0, (7, 7): 1})
s2 = G.apply_move(s, "3,0>3,4")
assert s2.board[(4, 4)] == 0 and s2.board[(3, 5)] == 0, "row AND column fire"
assert s2.board[(5, 4)] == 0 and s2.board[(3, 6)] == 0, "flankers untouched"

# Case 3: three directions at once (left line of 2, right, and up).
s = st({(0, 4): 0, (1, 4): 1, (2, 4): 1, (4, 4): 1, (5, 4): 0,
        (3, 5): 1, (3, 6): 0, (3, 0): 0, (7, 7): 1})
s2 = G.apply_move(s, "3,0>3,4")
for cell in [(1, 4), (2, 4), (4, 4), (3, 5)]:
    assert s2.board[cell] == 0, f"3-direction capture converts {cell}"

# a GAP breaks the bracket; a friendly stone inside the run breaks it too
s = st({(0, 4): 0, (1, 4): 1, (2, 4): 1, (4, 4): 1, (5, 0): 0, (7, 7): 1})
s2 = G.apply_move(s, "5,0>5,4")   # left run = [(4,4)], but (3,4) is EMPTY, not a flank
assert s2.board[(4, 4)] == 1, "gap before the far flank prevents capture"
assert s2.board[(1, 4)] == 1 and s2.board[(2, 4)] == 1, "distant line untouched"
s = st({(0, 4): 0, (1, 4): 1, (2, 4): 0, (3, 4): 1, (4, 0): 0, (7, 7): 1})
s2 = G.apply_move(s, "4,0>4,4")   # left: run [(3,4)] flanked by own (2,4) -> taken
assert s2.board[(3, 4)] == 0, "short run flanked by the nearer friendly converts"
assert s2.board[(1, 4)] == 1, "the enemy beyond the friendly stone is safe"

# ---------------------------------------------------------------------------
# (b) conversion invariant over a random playout (default 8x8, leap off)
# ---------------------------------------------------------------------------
rng = random.Random(42)
s = G.initial_state()
total = 2 * (2 * s.n - 2)
plies = 0
while not G.is_terminal(s) and plies < 250:
    ms = G.legal_moves(s)
    assert ms, "non-terminal state must have moves"
    s = G.apply_move(s, rng.choice(ms))
    assert len(s.board) == total, "board population must stay constant"
    assert all(o in (0, 1) for o in s.board.values())
    plies += 1
assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)
if G.is_terminal(s):
    r = G.returns(s)
    assert len(r) == 2 and r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0])

# ---------------------------------------------------------------------------
# (c) corner immunity — no cell beyond a corner, so no sandwich
# ---------------------------------------------------------------------------
s = st({(0, 0): 1, (0, 3): 0, (2, 0): 0, (7, 7): 1})
s2 = G.apply_move(s, "0,3>0,1")   # adjacent along the file: beyond is off-board
assert s2.board[(0, 0)] == 1, "corner stone immune (file)"
s2 = G.apply_move(s, "2,0>1,0")   # adjacent along the rank
assert s2.board[(0, 0)] == 1, "corner stone immune (rank)"

# ---------------------------------------------------------------------------
# (d) moving INTO a sandwich is safe; NO intervention capture
# ---------------------------------------------------------------------------
s = st({(3, 4): 1, (5, 4): 1, (4, 0): 0, (0, 7): 0, (7, 7): 1})
s2 = G.apply_move(s, "4,0>4,4")   # lands BETWEEN two enemies, no far flanks
assert s2.board[(4, 4)] == 0, "mover survives entering a sandwich"
assert s2.board[(3, 4)] == 1 and s2.board[(5, 4)] == 1, \
    "NO intervention capture (unlike Mak-yek)"
# ...and the enemy may then capture by RE-making the sandwich with a move
s3 = G.apply_move(s2, "3,4>3,3")            # step away
s4 = G.apply_move(s3, "0,7>0,6")            # black waits
s5 = G.apply_move(s4, "3,3>3,4")            # re-make the sandwich: captures
assert s5.board[(4, 4)] == 1, "re-made sandwich converts the entered stone"

# ---------------------------------------------------------------------------
# (e) positional superko — the would-repeat move is illegal
# ---------------------------------------------------------------------------
s = st({(3, 3): 0, (5, 5): 1})
s1 = G.apply_move(s, "3,3>3,4")
s2 = G.apply_move(s1, "5,5>5,4")
s3 = G.apply_move(s2, "3,4>3,3")            # black back home (to_move differs)
ms = set(G.legal_moves(s3))
assert "5,4>5,5" not in ms, "white returning would recreate the start position"
assert "5,4>5,6" in ms, "other moves remain legal"

# ---------------------------------------------------------------------------
# (f) cannot-move loss (blockade) and annihilation win — via apply_move
# ---------------------------------------------------------------------------
# Blockade: white's only stone is cornered at (0,0) by black at (0,1),(1,0).
s = st({(0, 0): 1, (0, 1): 0, (1, 4): 0})
s2 = G.apply_move(s, "1,4>1,0")
assert s2.board[(0, 0)] == 1, "corner stone was not captured (immune)"
assert G.legal_moves(s2) == [] and G.is_terminal(s2), "white is blockaded"
assert G.returns(s2) == [1.0, -1.0], "player who cannot move loses"

# Annihilation-by-conversion: converting white's last stone wins.
s = st({(5, 4): 0, (4, 4): 1, (3, 0): 0})
s2 = G.apply_move(s, "3,0>3,4")
assert s2.board[(4, 4)] == 0, "last white stone converted"
assert s2.winner == 0 and G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0]

# ---------------------------------------------------------------------------
# (g) frozen opening legal-move counts (8 / 9 / 17)
# ---------------------------------------------------------------------------
# Per seat at the start: the 2(n-2) stones not on a corner or a far end each
# have n-2 moves; the corner-adjacent full-file ends are locked. = 2(n-2)^2.
for size, frozen in [(8, 72), (9, 98), (17, 450)]:
    si = G.initial_state(options={"size": size})
    assert len(si.board) == 2 * (2 * size - 2)
    got = len(G.legal_moves(si))
    assert got == frozen, f"opening moves size {size}: {got} != {frozen}"

# ---------------------------------------------------------------------------
# (h) 180-degree symmetry: white's opening move set = rotation of black's
# ---------------------------------------------------------------------------
for size in (8, 9, 17):
    si = G.initial_state(options={"size": size})
    black = set(G.legal_moves(si))
    sw = st(si.board, to_move=1, n=size)
    white = set(G.legal_moves(sw))
    m = size - 1
    rot = lambda c, r: (m - c, m - r)   # noqa: E731

    def rot_move(mv):
        a, b = mv.split(">")
        (c1, r1), (c2, r2) = (tuple(map(int, x.split(","))) for x in (a, b))
        return f"{m - c1},{m - r1}>{m - c2},{m - r2}"

    assert {rot_move(mv) for mv in black} == white, f"180 symmetry, size {size}"

# ---------------------------------------------------------------------------
# (i) last_stone_leap option
# ---------------------------------------------------------------------------
# Lone black stone leaps over an adjacent enemy; leapt stone is REMOVED.
board = {(3, 3): 0, (3, 4): 1, (7, 7): 1}
s = st(board, leap=True)
ms = set(G.legal_moves(s))
assert "3,3>3,5" in ms, "lone stone may leap over the adjacent enemy"
assert "3,3>3,2" in ms, "leaping is optional — rook slides still offered"
s2 = G.apply_move(s, "3,3>3,5")
assert (3, 4) not in s2.board, "leapt stone is REMOVED"
assert sum(1 for o in s2.board.values() if o == 1) == 1, "not converted"
assert s2.board[(3, 5)] == 0 and (3, 3) not in s2.board, "leaper landed"
assert s2.no_progress == 0, "leap capture is progress"

# leap only exists for a LONE stone, and only when the option is on
s = st({(3, 3): 0, (0, 0): 0, (3, 4): 1, (7, 7): 1}, leap=True)
assert "3,3>3,5" not in set(G.legal_moves(s)), "two stones: no leap"
s = st(board, leap=False)
assert "3,3>3,5" not in set(G.legal_moves(s)), "option off: no leap"

# leap that removes the last enemy stone wins
s = st({(3, 3): 0, (3, 4): 1}, leap=True)
s2 = G.apply_move(s, "3,3>3,5")
assert s2.winner == 0 and G.returns(s2) == [1.0, -1.0], "leap-out win"

# ---------------------------------------------------------------------------
# heuristic shape: one payoff per seat (never a bare float)
# ---------------------------------------------------------------------------
h = G.heuristic(s0)
assert isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9
s = st({(0, 0): 0, (1, 1): 0, (7, 7): 1})
h = G.heuristic(s)
assert h[0] > 0 > h[1], "material lead scores positive for the leader"

print("SELFTEST OK")
sys.exit(0)
