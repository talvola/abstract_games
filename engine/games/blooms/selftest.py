"""Standalone correctness anchor for Blooms (Nick Bentley, 2018).

Run from the engine dir:  PYTHONPATH=. python3 games/blooms/selftest.py

There is no published perft for Blooms, so the anchor is the official
ruleset (nickbentley.games "Blooms 2.0", cross-checked vs
abstractgames.org/blooms.html and the AiAi report) asserted on hand-built
positions:

  (1) hexhex board sizes 4/5/6 -> 37/61/91 cells with axial 6-adjacency;
  (2) the game's FIRST turn places exactly ONE stone (either colour), later
      turns place 1 or 2, two stones must be DIFFERENT colours;
  (3) blooms connect per COLOUR (a player's two colours never connect);
  (4) capture of a fenced enemy bloom happens at END of turn (not after the
      first stone), stones credited to the capturer;
  (5) SIMULTANEOUS multi-bloom capture (two mutually-fencing enemy blooms
      both fall);
  (6) suicide is legal; the fenced bloom survives the owner's turn and is
      harvested by the opponent's next turn-end;
  (7) sacrifice-rescue: capturing the enemy bloom that fences your own
      fenced bloom frees it;
  (8) capture-target win fires via apply_move (win as event);
  (9) serialize round-trip; (10) random-playout termination.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import random
import sys

from games.blooms.game import (
    Blooms, BloomsState, _cells, _neighbors, _fenced_enemy_stones,
    IDX, AUTO_TARGET,
)

G = Blooms()
R, O, B, GR = IDX["R"], IDX["O"], IDX["B"], IDX["G"]


def die(msg):
    print(f"SELFTEST FAIL: {msg}")
    sys.exit(1)


def check(cond, msg):
    if not cond:
        die(msg)


# ---------------------------------------------------------------- (1) board
check(len(_cells(4)) == 37, "hexhex4 must have 37 cells")
check(len(_cells(5)) == 61, "hexhex5 must have 61 cells")
check(len(_cells(6)) == 91, "hexhex6 must have 91 cells")
check(set(_neighbors(0, 0)) == {(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)},
      "axial 6-adjacency")
s0 = G.initial_state()
check(s0.size == 5 and s0.target == 20, "default = size 5, X = 20 (designer)")
check(G.initial_state(options={"size": 4}).target == 15, "auto X: size 4 -> 15")
check(G.initial_state(options={"size": 6}).target == 30, "auto X: size 6 -> 30")
check(G.initial_state(options={"size": 4, "target": "25"}).target == 25,
      "explicit target option")

# ------------------------------------------------- (2) placement structure
s = G.initial_state(options={"size": 4})
lm = G.legal_moves(s)
check(len(lm) == 2 * 37, "first turn: one stone of either colour on 37 cells")
check(all("=" in m and m.rsplit("=", 1)[1] in ("R", "O") for m in lm),
      "P1 places only R/O")
check("done" not in lm, "no 'done' before placing")
s1 = G.apply_move(s, "0,0=R")
check(s1.to_move == 1 and s1.placed is None and s1.turn_no == 1,
      "the game's first turn ends after ONE stone")

lm = G.legal_moves(s1)
check(len(lm) == 2 * 36, "P2 first stone: either colour on 36 empties")
check(all(m.rsplit("=", 1)[1] in ("B", "G") for m in lm), "P2 places only B/G")
s2 = G.apply_move(s1, "1,0=B")
check(s2.to_move == 1 and G.current_player(s2) == 1 and s2.placed == (1, 0),
      "after 1st stone of a normal turn the same player continues")
lm = G.legal_moves(s2)
check("done" in lm, "'done' offered after the first stone")
check(all(m == "done" or m.rsplit("=", 1)[1] == "G" for m in lm),
      "second stone must be the OTHER colour (G after B)")
check(not any(m.startswith("1,0=") for m in lm), "occupied cell not offered")
def must_raise(state, move, why):
    try:
        G.apply_move(state, move)
    except ValueError:
        return
    die(f"{move} should be illegal: {why}")

must_raise(s2, "2,0=B", "two stones in a turn must differ in colour")
must_raise(s2, "2,0=R", "R is not seat 1's colour")
must_raise(s2, "1,0=G", "occupied cell")
must_raise(s1, "done", "'done' before placing a stone")
must_raise(s, "4,0=R", "off-board cell on a size-4 board")
must_raise(s, "0,0=B", "B is not seat 0's colour")
s3 = G.apply_move(s2, "done")
check(s3.to_move == 0 and s3.placed is None and s3.turn_no == 2,
      "'done' ends the turn on one stone")
s2b = G.apply_move(s2, "2,0=G")
check(s2b.to_move == 0 and s2b.placed is None, "second stone ends the turn")

# ------------------------------------ (3) blooms connect per COLOUR only
board = {(0, 0): B, (1, 0): GR}  # same seat, different colours: 2 blooms
st = BloomsState(size=4, target=15, board=dict(board), to_move=0, turn_no=4)
# fence (0,0)'s remaining nbrs but leave (1,0)'s own nbrs open:
for c in [(-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]:
    st.board[c] = R
caps = _fenced_enemy_stones(st.board, 4, 0)
check(caps == {(0, 0)}, "B bloom fenced (its G neighbour is part of the fence), "
                        "G bloom NOT part of the B bloom and not fenced")

# ------------------------------------------- (4) end-of-turn capture timing
st = BloomsState(size=4, target=15, board={(0, 0): B}, to_move=0, turn_no=4)
for c in [(1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]:
    st.board[c] = R if c[0] % 2 == 0 else O
mid = G.apply_move(st, "-1,0=O")          # fences the B stone... but
check((0, 0) in mid.board, "capture must NOT resolve after the 1st stone")
end = G.apply_move(mid, "done")
check((0, 0) not in end.board, "fenced enemy bloom captured at turn end")
check(end.captures[0] == 1 and end.captures[1] == 0, "capturer credited")
# same position, capture via a 2nd stone instead of done
mid2 = G.apply_move(st, "3,0=O")
end2 = G.apply_move(mid2, "-1,0=R")
check((0, 0) not in end2.board and end2.captures[0] == 1,
      "capture resolves after the 2nd stone too")

# --------------------------------------- (5) simultaneous multi-bloom capture
# B bloom {(0,0)} and G bloom {(1,0)} fence each other; outside ring all
# seat-0 except (2,0). Placing at (2,0) fences BOTH -> both captured, even
# though removing either would free the other.
board = {(0, 0): B, (1, 0): GR}
outside = [(-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1), (1, 1), (2, -1)]
for i, c in enumerate(outside):
    board[c] = R if i % 2 == 0 else O
st = BloomsState(size=4, target=15, board=board, to_move=0, turn_no=6)
mid = G.apply_move(st, "2,0=R")
end = G.apply_move(mid, "done")
check((0, 0) not in end.board and (1, 0) not in end.board,
      "both mutually-fencing enemy blooms captured simultaneously")
check(end.captures[0] == 2, "both stones credited")

# --------------------------------------------------- (6) suicide is legal
# Seat 0's R stone at (0,0) has one liberty (-1,1); seat 0 fills it itself.
board = {(0, 0): R}
for c in [(1, 0), (-1, 0), (0, 1), (1, -1)]:
    board[c] = B
board[(0, -1)] = GR
st = BloomsState(size=4, target=15, board=board, to_move=0, turn_no=6)
mid = G.apply_move(st, "-1,1=O")          # legal self-fencing placement
end = G.apply_move(mid, "done")
check((0, 0) in end.board, "own fenced bloom is NOT removed on own turn")
check(end.captures == [0, 0], "no captures for anyone yet")
# opponent plays anything far away; harvest happens at THEIR turn end
mid = G.apply_move(end, "3,-3=B")
harv = G.apply_move(mid, "done")
check((0, 0) not in harv.board, "opponent harvests the suicided bloom")
check(harv.captures[1] == 1, "harvest credited to the opponent")
check((-1, 1) in harv.board, "the O fence stone itself survives (has liberties)")

# ------------------------------------------------- (7) sacrifice-rescue
# Seat 0's R bloom {(0,0)} is fenced; part of its fence is enemy B bloom
# {(1,0)} whose last liberty (2,0) seat 0 fills this turn: B is captured at
# seat 0's turn end, freeing (1,0) and rescuing the R bloom.
board = {(0, 0): R, (1, 0): B}
for c in [(-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]:   # rest of R's fence
    board[c] = GR
for c in [(1, 1), (2, -1)]:                               # B's other nbrs
    board[c] = O
st = BloomsState(size=4, target=15, board=board, to_move=0, turn_no=8)
end = G.apply_move(G.apply_move(st, "2,0=O"), "done")
check((1, 0) not in end.board, "enemy fencing bloom captured")
check((0, 0) in end.board, "own bloom rescued by the capture")
check(end.captures[0] == 1, "rescue capture credited")
# and the rescued bloom now has a liberty, so the opponent can't harvest it
# without actually refilling (1,0):
mid = G.apply_move(end, "3,-3=B")
nxt = G.apply_move(mid, "done")
check((0, 0) in nxt.board, "rescued bloom survives the opponent's turn")

# ------------------------------------------ (8) capture-target win (event)
board = {(0, 0): B, (1, 0): B}
for c in [(-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1), (1, 1), (2, -1)]:
    board[c] = R
st = BloomsState(size=4, target=2, board=board, to_move=0, turn_no=8)
check(not G.is_terminal(st), "not terminal before the win event")
end = G.apply_move(G.apply_move(st, "2,0=O"), "done")
check(end.over and end.winner == 0, "reaching X captures wins immediately")
check(G.is_terminal(end) and G.returns(end) == [1.0, -1.0], "returns for P1 win")
check(G.legal_moves(end) == [], "no moves after the game ends")

# --------------------------------------------------- (9) serialize round-trip
for probe in (s0, s2, mid, end):
    d = G.serialize(probe)
    json.dumps(d)
    d2 = G.serialize(G.deserialize(d))
    check(json.dumps(d, sort_keys=True) == json.dumps(d2, sort_keys=True),
          "serialize must round-trip")

# ------------------------------------------------ (10) random termination
rng = random.Random(7)
lengths, results = [], {0: 0, 1: 0, None: 0}
for i in range(40):
    st = G.initial_state(options={"size": 4})
    guard = 0
    while not G.is_terminal(st):
        ms = G.legal_moves(st)
        check(ms, "non-terminal state must have moves")
        st = G.apply_move(st, rng.choice(ms))
        guard += 1
        check(guard < 5000, "runaway game")
    lengths.append(st.turn_no)
    results[st.winner] += 1
check(results[None] == 0, "random play should never hit the draw backstops")
print(f"  playouts: 40 games size4, turns min/avg/max = "
      f"{min(lengths)}/{sum(lengths)/len(lengths):.1f}/{max(lengths)}, "
      f"wins P1={results[0]} P2={results[1]}")

print("SELFTEST OK")
