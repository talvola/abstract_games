"""Slimetrail selftest — pure stdlib, fast.
Run: PYTHONPATH=. python3 games/slimetrail/selftest.py

Anchors (baked rule asserts):
  (1) board + goals + start: N x N, goals at opposite corners (0,0)/(N-1,N-1),
      marker on the centre cell; the two goals start empty/playable.
  (2) a move SLIMES the vacated cell, and the marker can never re-enter it.
  (3) reaching a goal wins (reached via apply_move): landing on (0,0) wins for
      player 0, on (N-1,N-1) for player 1, regardless of who moved.
  (4) a trapped player (no legal slide on their turn) LOSES.
  (5) serialize round-trips.
"""
from __future__ import annotations
import sys
from games.slimetrail.game import Slimetrail, SlimeState, PLY_CAP


def check(cond, msg):
    if not cond:
        print("SELFTEST FAIL:", msg)
        sys.exit(1)


G = Slimetrail()

# --- (1) board + goals + start --------------------------------------------
s0 = G.initial_state()
check(s0.size == 8, "default board is 8x8")
check(s0.marker == (4, 4), "marker starts on the centre cell")
check(len(s0.slimed) == 0, "no slime initially")
check(G.num_players == 2, "2 players")
check(s0.to_move == 0, "player 0 (Red) moves first")
check(not G.is_terminal(s0), "initial state not terminal")
check(G._goal0(8) == (0, 0), "player 0 goal is bottom-left")
check(G._goal1(8) == (7, 7), "player 1 goal is top-right")
# goals are empty cells, not slimed at start
check((0, 0) not in s0.slimed and (7, 7) not in s0.slimed, "goals not slimed at start")

# round-trip serialize (5)
s_rt = G.deserialize(G.serialize(s0))
check(G.serialize(s_rt) == G.serialize(s0), "serialize round-trips")

# --- legal moves are the 8 king-neighbours from the centre ----------------
lm = G.legal_moves(s0)
check(len(lm) == 8, "centre marker has 8 king moves")
for d in ("3,3", "4,3", "5,3", "3,4", "5,4", "3,5", "4,5", "5,5"):
    check(d in lm, f"king neighbour {d} is legal")
check("4,4" not in lm, "marker cannot stay put")

# --- (2) a move slimes the vacated cell; can't revisit it -----------------
s1 = G.apply_move(s0, "5,4")           # slide right
check(s1.marker == (5, 4), "marker moved to 5,4")
check((4, 4) in s1.slimed, "vacated cell 4,4 is now slimed")
check(s1.to_move == 1, "turn passed to player 1")
# from 5,4 the marker may NOT step back onto the slimed 4,4
lm1 = G.legal_moves(s1)
check("4,4" not in lm1, "cannot move back onto the slimed cell")
check("4,3" in lm1 and "4,5" in lm1, "other king neighbours of 5,4 are legal")
# slime is permanent: move away and confirm 4,4 stays slimed and unenterable
s2 = G.apply_move(s1, "5,5")
check((4, 4) in s2.slimed and (5, 4) in s2.slimed, "slime accumulates and is permanent")

# --- (3) reaching a goal wins (reach via apply_move) ----------------------
# Player 0 to move with the marker adjacent to its own goal (0,0).
sg0 = SlimeState(size=8, marker=(1, 1), slimed=frozenset(), to_move=0)
check("0,0" in G.legal_moves(sg0), "marker can slide onto goal 0,0")
sg0b = G.apply_move(sg0, "0,0")
check(sg0b.winner == 0, "landing on (0,0) wins for player 0")
check(G.is_terminal(sg0b), "win state is terminal")
check(G.legal_moves(sg0b) == [], "terminal state has no legal moves")
check(G.returns(sg0b) == [1.0, -1.0], "returns reflect player 0 win")

# Player 1's goal (7,7): owner wins regardless of who moves onto it. Here it is
# player 0 to move, but landing on (7,7) still makes RED (player 1) the winner.
sg1 = SlimeState(size=8, marker=(6, 6), slimed=frozenset(), to_move=0)
check("7,7" in G.legal_moves(sg1), "marker can slide onto goal 7,7")
sg1b = G.apply_move(sg1, "7,7")
check(sg1b.winner == 1, "landing on (7,7) wins for player 1 even when player 0 moved it")
check(G.returns(sg1b) == [-1.0, 1.0], "returns reflect player 1 win")

# Player 1 reaching their own goal normally.
sg1c = SlimeState(size=8, marker=(6, 7), slimed=frozenset(), to_move=1)
sg1d = G.apply_move(sg1c, "7,7")
check(sg1d.winner == 1, "player 1 wins landing on own goal")

# --- (4) trapped player LOSES ---------------------------------------------
# Box the marker into a corner on a small 3x3 board so it has no move.
# Marker at (1,1) centre; surround all 8 neighbours with slime -> no move.
n = 3
all_neighbours = {(c, r) for c in range(3) for r in range(3)} - {(1, 1)}
strap = SlimeState(size=n, marker=(1, 1), slimed=frozenset(all_neighbours), to_move=0)
check(G._raw_moves(strap) == [], "marker fully boxed in has no raw moves")
check(G.is_terminal(strap), "trapped position is terminal")
check(G.legal_moves(strap) == [], "trapped: no legal moves")
check(G.returns(strap) == [-1.0, 1.0], "player 0 to move and trapped -> player 0 loses")
# symmetric: if player 1 were to move and trapped, player 1 loses
strap1 = SlimeState(size=n, marker=(1, 1), slimed=frozenset(all_neighbours), to_move=1)
check(G.returns(strap1) == [1.0, -1.0], "player 1 to move and trapped -> player 1 loses")

# Reach a trap via apply_move (not just hand-built): on a 3x3, walk the marker
# until it boxes itself. Sanity: a full game on 3x3 always terminates decisively.
import random
rng = random.Random(12345)
for seed in range(50):
    rng2 = random.Random(seed)
    s = G.initial_state({"size": "3"})
    steps = 0
    while not G.is_terminal(s):
        mv = rng2.choice(G.legal_moves(s))
        s = G.apply_move(s, mv)
        steps += 1
        check(steps <= 3 * 3 + 2, "game on 3x3 terminates within bound")
    ret = G.returns(s)
    check(ret in ([1.0, -1.0], [-1.0, 1.0]), "every 3x3 game ends decisively")

# --- termination bound on default board -----------------------------------
s = G.initial_state()
steps = 0
rng3 = random.Random(7)
while not G.is_terminal(s):
    s = G.apply_move(s, rng3.choice(G.legal_moves(s)))
    steps += 1
    check(steps <= 8 * 8 + 1, "8x8 game terminates within N*N bound")

print("SELFTEST OK")
sys.exit(0)
