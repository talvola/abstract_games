"""Cephalopod correctness anchor — pure-stdlib, fast.

Run: PYTHONPATH=. python3 games/cephalopod/selftest.py

No published perft exists, so the anchor is a set of baked rule positions that
pin down Steere's official rules:
  (1) a 5x5 square board of dice, empty at start;
  (2) a capturing placement: adjacent dice summing to <=6 MUST be captured, the
      removed dice leave the board, and the new die shows that SUM in the
      mover's colour;
  (3) a non-capturing placement shows a ONE in the mover's colour;
  (4) capture is mandatory when possible, but the player may choose any
      qualifying subset (not necessarily the maximum) — Steere Fig. 4;
  (5) the board fills and the majority of dice wins (odd cells => no tie).
"""

import sys

from games.cephalopod.game import Cephalopod, CephState


def fail(msg):
    print(f"SELFTEST FAIL: {msg}")
    sys.exit(1)


def expect(cond, msg):
    if not cond:
        fail(msg)


g = Cephalopod()

# (1) initial 5x5 board is empty, Red (0) to move, 25 cells.
s0 = g.initial_state()
expect(s0.size == 5, "default board size should be 5")
expect(s0.board == {}, "initial board should be empty")
expect(g.current_player(s0) == 0, "Red (0) moves first")
expect(not g.is_terminal(s0), "empty board is not terminal")
expect(len(g.legal_moves(s0)) == 25, "empty 5x5 has 25 plain placements")
expect(all("=" not in m for m in g.legal_moves(s0)),
       "no captures possible on an empty board")

# (3) plain one-placement: the new die is a 1 of the mover's colour.
s1 = g.apply_move(s0, "2,2")
expect(s1.board[(2, 2)] == (0, 1), "first placement should be a Red 1")
expect(g.current_player(s1) == 1, "turn passes to Blue")

# (2) capturing placement (Steere Fig. 2 analogue): two adjacent 1s, sum 2 <= 6.
# Build: Red 1 at (1,2), Blue 1 at (3,2). Blue to move places at (2,2).
s = CephState(board={(1, 2): (0, 1), (3, 2): (1, 1)}, to_move=1, size=5)
moves = g.legal_moves(s)
cap = [m for m in moves if m.startswith("2,2=")]
expect(len(cap) == 1, f"exactly one capturing move at (2,2), got {cap}")
expect(cap[0] == "2,2=1,2;3,2", f"capture both 1s: {cap[0]}")
# Capture is MANDATORY at (2,2): no plain '2,2' offered.
expect("2,2" not in moves, "plain placement at a capturable square is illegal")
s2 = g.apply_move(s, cap[0])
expect((1, 2) not in s2.board and (3, 2) not in s2.board,
       "captured dice are removed from the board")
expect(s2.board[(2, 2)] == (1, 2), "new die shows the SUM (2) in Blue's colour")

# (2b) sum capping at 6 / >6 cannot capture: a 5 and a 2 (sum 7) cannot be taken
# together (Fig. 5 analogue) -> a placement adjacent only to them is plain.
s = CephState(board={(1, 2): (0, 5), (3, 2): (1, 2)}, to_move=0, size=5)
moves = g.legal_moves(s)
expect("2,2" in moves, "5+2=7 > 6 -> placement at (2,2) is non-capturing")
expect(not any(m.startswith("2,2=") for m in moves),
       "no capturing move when the only adjacent pair sums to 7")
s3 = g.apply_move(s, "2,2")
expect(s3.board[(2, 2)] == (0, 1), "non-capturing die shows a Red 1")

# (4) mandatory-but-choosable: four adjacent dice 1,1,1,3 (Fig. 3/4). The full
# set sums to 6 (capture all four -> a 6), AND smaller qualifying subsets exist
# (e.g. the two 1s -> a 2). The player CHOOSES; both are legal moves; no plain.
s = CephState(board={
    (2, 1): (1, 1),   # up
    (2, 3): (1, 1),   # down
    (1, 2): (1, 1),   # left
    (3, 2): (1, 3),   # right
}, to_move=0, size=5)
moves = [m for m in g.legal_moves(s) if m.startswith("2,2")]
expect("2,2" not in moves, "capturable square offers no plain placement")
# capture-all: 1+1+1+3 = 6
all_cap = "2,2=1,2;2,1;2,3;3,2"
expect(all_cap in moves, f"capture all four (sum 6) must be legal: {moves}")
sA = g.apply_move(s, all_cap)
expect(sA.board[(2, 2)] == (0, 6), "capturing all four shows a 6")
expect(len(sA.board) == 1, "all four neighbours removed, only the new die left")
# capture-a-subset: the three 1s sum to 3 (a legal smaller choice)
three_ones = "2,2=1,2;2,1;2,3"
expect(three_ones in moves, "capturing just the three 1s (sum 3) must be legal")
sB = g.apply_move(s, three_ones)
expect(sB.board[(2, 2)] == (0, 3), "capturing the three 1s shows a 3")
expect((3, 2) in sB.board, "the un-chosen neighbour (the 3) stays on the board")

# (5) end / majority scoring on a genuinely FULL board. Hand-build a 3x3
# (9 cells, odd) with 8 dice placed so that the 9th, central placement is
# non-capturing (all neighbours are high so no pair sums to <=6), filling the
# board. The new die joins Red; final count must be the majority owner, no tie.
# Layout (values chosen so the centre's four neighbours all pair-sum > 6):
#   (0,0)=R6 (1,0)=B6 (2,0)=R6
#   (0,1)=B6        . (2,1)=R6
#   (0,2)=R6 (1,2)=B6 (2,2)=R6
s = CephState(board={
    (0, 0): (0, 6), (1, 0): (1, 6), (2, 0): (0, 6),
    (0, 1): (1, 6),                 (2, 1): (0, 6),
    (0, 2): (0, 6), (1, 2): (1, 6), (2, 2): (0, 6),
}, to_move=0, size=3)
# Centre (1,1) neighbours are all 6s -> every pair sums to 12 > 6 -> plain.
mv = g.legal_moves(s)
expect(mv == ["1,1"], f"only the empty centre is playable, plainly: {mv}")
s = g.apply_move(s, "1,1")
expect(g.is_terminal(s), "a completely full 3x3 board is terminal")
expect(len(s.board) == 9, "full board has all 9 cells occupied")
a = sum(1 for o, _ in s.board.values() if o == 0)
b = sum(1 for o, _ in s.board.values() if o == 1)
expect((a, b) == (6, 3), f"Red 6 vs Blue 3 expected, got {a}-{b}")
ret = g.returns(s)
expect(ret != [0.0, 0.0], "odd-celled board cannot end in a tie")
expect(ret == [1.0, -1.0], "Red holds the majority and wins")
expect(sum(ret) == 0.0, "returns are zero-sum and well-formed")

# (6) REGRESSION: play a FULL game from the empty initial state to a natural
# terminal and assert the board ends COMPLETELY FULL with the majority winning.
# The old ply-cap terminal (4 * cells = 100 on 5x5) fired BEFORE the board could
# fill — because a capturing turn frees cells, the board needs many more plies
# than cells to fill. A deterministic greedy driver (no randomness) plays one
# game on the default 5x5: it prefers a plain "1" placement when available (this
# strictly raises the bounded pip-sum and drives toward a full board), else takes
# the first legal capture. This bounded single playthrough must reach a FULL board.
s = g.initial_state()                     # default 5x5, empty
guard = 0
while not g.is_terminal(s):
    moves = g.legal_moves(s)
    expect(moves, "a non-terminal state must offer at least one legal move")
    # A legal move always exists while any cell is empty (place, capturing if
    # forced else a plain "1"); prefer plain placements to fill the board.
    plain = [m for m in moves if "=" not in m]
    s = g.apply_move(s, plain[0] if plain else moves[0])
    guard += 1
    expect(guard <= 12 * s.size * s.size,
           "full-game driver exceeded the backstop cap (should never happen)")
expect(len(s.board) == s.size * s.size,
       f"terminal board must be COMPLETELY FULL: {len(s.board)}/{s.size*s.size}")
expect(all((c, r) in s.board for c in range(s.size) for r in range(s.size)),
       "every cell must be occupied at the natural terminal")
fa = sum(1 for o, _ in s.board.values() if o == 0)
fb = sum(1 for o, _ in s.board.values() if o == 1)
expect(fa != fb, f"odd-celled full board cannot tie, got {fa}-{fb}")
fret = g.returns(s)
expect(fret == ([1.0, -1.0] if fa > fb else [-1.0, 1.0]),
       f"winner must be the dice majority ({fa}-{fb}), got {fret}")

# serialize round-trips
import json
s = CephState(board={(0, 0): (0, 1), (1, 0): (1, 4)}, to_move=1, size=5, plies=3)
d = g.serialize(s)
json.dumps(d)
expect(g.serialize(g.deserialize(d)) == d, "serialize must round-trip")

print("SELFTEST OK")
sys.exit(0)
