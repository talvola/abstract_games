#!/usr/bin/env python3
"""Standalone correctness anchor for Grasshopper Chess.

Run from the engine dir with::

    PYTHONPATH=. python3 games/grasshopper_chess/selftest.py

Pure stdlib + this game only (no third-party engine), fast. Prints ``SELFTEST OK``
and exits 0 on success, nonzero on any failure.

It asserts:

* the setup: 8 grasshoppers per side on rank 3 / rank 6, 8 pawns, 8 back-rank
  pieces, 48 men, "G" labels;
* a self-computed **opening perft baseline** (d1 = 14, d2 = 212, d3 = 4074),
  hand-verified below (the grasshopper wall blocks every pawn and knight at the
  start, so the only opening moves are grasshopper hops; the e-file grasshopper is
  pinned, giving 7 files x 2 = 14);
* the signature **hop** in all four cases on an open board: over a single hurdle to
  the square immediately beyond (move / capture); no hurdle -> no move; friendly
  square beyond the hurdle -> blocked;
* a grasshopper **gives check** by hopping onto the king's square (attack detection);
* the opening pin: a grasshopper directly in front of the king on the king's file is
  pinned by the enemy grasshopper behind the pawn (validates attack detection);
* serialize round-trips.

No published perft table exists for this variant; the perft numbers here are this
engine's own regression baseline, derived from the move generator.
"""

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.grasshopper_chess.game import GrasshopperChess

G = GrasshopperChess()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def targets(state, frm):
    out = set()
    for m in G.legal_moves(state):
        base = m.split("=")[0]
        f, t = base.split(">")
        if f == frm:
            tc, tr = t.split(",")
            out.add((int(tc), int(tr)))
    return out


def perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


# --------------------------------------------------------------------------- #
# 1. Setup
# --------------------------------------------------------------------------- #
s0 = G.initial_state()
check(len(s0.board) == 48, "48 men at the start (24 per side)")
wg = sum(1 for v in s0.board.values() if v == (WHITE, "G"))
bg = sum(1 for v in s0.board.values() if v == (BLACK, "G"))
check(wg == 8 and bg == 8, f"8 grasshoppers per side (got {wg}/{bg})")
for c in range(8):
    check(s0.board[(c, 2)] == (WHITE, "G"), "White grasshoppers on rank 3 (row 2)")
    check(s0.board[(c, 5)] == (BLACK, "G"), "Black grasshoppers on rank 6 (row 5)")
    check(s0.board[(c, 1)] == (WHITE, "P"), "White pawns on rank 2")
    check(s0.board[(c, 6)] == (BLACK, "P"), "Black pawns on rank 7")
wp = sum(1 for v in s0.board.values() if v == (WHITE, "P"))
check(wp == 8, "8 white pawns")

# --------------------------------------------------------------------------- #
# 2. Opening perft baseline (engine-derived, hand-verified)
# --------------------------------------------------------------------------- #
check(perft(s0, 1) == 14, "perft(1) must be 14")
check(perft(s0, 2) == 212, "perft(2) must be 212")
check(perft(s0, 3) == 4074, "perft(3) must be 4074")

# Hand-verification of d1=14: pawns are blocked by the grasshopper directly in
# front; knights cannot reach rank 3 (own grasshoppers there); so only grasshopper
# hops exist. Each non-e file grasshopper has exactly two: a forward hop (over the
# enemy grasshopper on rank 6, landing on the enemy pawn = capture) and a forward-
# diagonal hop (also a capture on rank 6). The e-file grasshopper (in front of the
# king) is pinned by Black's e6 grasshopper (hurdle = the e2 pawn) and has 0 moves.
byfrom = {}
for c in range(8):
    byfrom[c] = targets(s0, f"{c},2")
for c in range(8):
    if c == 4:
        check(byfrom[c] == set(), "e-file grasshopper is pinned (0 moves)")
    else:
        check(len(byfrom[c]) == 2, f"file {c} grasshopper must have exactly 2 hops")
        check(all(tr == 6 for (_, tr) in byfrom[c]),
              "opening grasshopper hops all land on rank 6 (captures)")
check(sum(len(v) for v in byfrom.values()) == 14, "total grasshopper hops = 14")

# --------------------------------------------------------------------------- #
# 3. The hop on an open board: the four cases
# --------------------------------------------------------------------------- #
WK, BK = (7, 0), (7, 7)   # kings parked out of the way

# (a) over a single hurdle to the square immediately beyond -> move
b = {(0, 0): (WHITE, "G"), (0, 3): (BLACK, "P"), WK: (WHITE, "K"), BK: (BLACK, "K")}
st = CState(board=b, to_move=WHITE, castling=frozenset())
check((0, 4) in targets(st, "0,0"),
      "grasshopper a1 hops over hurdle a4 to land on a5")

# (b) no hurdle on a line -> no move along it
b = {(0, 0): (WHITE, "G"), WK: (WHITE, "K"), BK: (BLACK, "K")}
st = CState(board=b, to_move=WHITE, castling=frozenset())
# Up the a-file (and the a1-h8 diagonal) there is no hurdle -> no landing there.
check((0, 4) not in targets(st, "0,0") and (0, 5) not in targets(st, "0,0"),
      "grasshopper has no move along an empty (hurdle-less) line")

# (c) friendly piece beyond the hurdle -> blocked
b = {(0, 0): (WHITE, "G"), (0, 3): (BLACK, "P"), (0, 4): (WHITE, "N"),
     WK: (WHITE, "K"), BK: (BLACK, "K")}
st = CState(board=b, to_move=WHITE, castling=frozenset())
check((0, 4) not in targets(st, "0,0"),
      "friendly piece on the landing square blocks the hop")

# (d) enemy beyond the hurdle -> capture
b = {(0, 0): (WHITE, "G"), (0, 3): (WHITE, "P"), (0, 4): (BLACK, "N"),
     WK: (WHITE, "K"), BK: (BLACK, "K")}
st = CState(board=b, to_move=WHITE, castling=frozenset())
check((0, 4) in targets(st, "0,0"),
      "enemy on the landing square is captured by the hop")

# --------------------------------------------------------------------------- #
# 4. A grasshopper gives check by hopping onto the king's square
# --------------------------------------------------------------------------- #
b = {(0, 0): (WHITE, "G"), (0, 3): (WHITE, "P"), (0, 4): (BLACK, "K"),
     WK: (WHITE, "K")}
check(G.attacked(b, 0, 4, WHITE),
      "white grasshopper a1 attacks the king on a5 (hop over a4)")
check(G.in_check(b, BLACK), "black king on a5 is in check from the grasshopper")
# remove the hurdle: no check (a grasshopper cannot reach an open line)
b2 = {(0, 0): (WHITE, "G"), (0, 4): (BLACK, "K"), WK: (WHITE, "K")}
check(not G.attacked(b2, 0, 4, WHITE), "no hurdle -> the grasshopper gives no check")

# --------------------------------------------------------------------------- #
# 5. Opening pin: moving the e-file grasshopper would expose the king
# --------------------------------------------------------------------------- #
# In the start position, removing the e3 grasshopper opens the e-file so Black's e6
# grasshopper hops over the e2 pawn onto e1. Confirm the engine sees the threat.
b = dict(s0.board)
del b[(4, 2)]                                   # lift the e3 grasshopper
check(G.attacked(b, 4, 0, BLACK),
      "with e3 vacated, the black e6 grasshopper attacks e1 over the e2 pawn")

# --------------------------------------------------------------------------- #
# 6. Serialize round-trips
# --------------------------------------------------------------------------- #
check(G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0),
      "serialize must round-trip the opening position")
s1 = G.apply_move(s0, "0,2>0,6")               # a grasshopper hop / capture
check(G.serialize(G.deserialize(G.serialize(s1))) == G.serialize(s1),
      "serialize must round-trip after a grasshopper move")

print("SELFTEST OK")
sys.exit(0)
