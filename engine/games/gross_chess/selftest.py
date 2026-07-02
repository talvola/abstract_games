#!/usr/bin/env python3
"""Standalone correctness anchor for Gross Chess (Fergus Duniho, 2009).

Run from the engine root with::

    PYTHONPATH=. python3 games/gross_chess/selftest.py

Pure stdlib (imports only ``agp`` + this game). Asserts:

  * the exact 12x12 opening array and frozen self-computed perft 1-3 from the
    start (perft(1)=72 was additionally verified by an independent hand count;
    perft(2)=5184=72^2 -- the armies provably cannot interact at depth 2);
  * exact legal-target sets for the fairy pieces: Wizard (ferz+camel),
    Champion (wazir+dabbaba+alfil), Marshall, Archbishop;
  * Cannon and Vao hop mechanics: rider moves stop before the screen, capture
    requires exactly one screen, the screen itself is not capturable, no
    capture without a screen, and hop CHECK detection (attacked());
  * the two-or-three square initial pawn step with multi-square en passant
    (capture on either passed square removes the pawn from its landing square;
    the right expires after one turn);
  * flexible (Grotesque) castling: all king destinations, rook placement
    adjacent to the king, rights bookkeeping, blocked-square and
    through-check refusals;
  * tiered reserve promotion (10th rank B/N/V/W; 11th +R/C/S; 12th all,
    compulsory) and the reserve pool cap (a 3rd queen in play blocks =Q);
  * a scripted opening with a capture, a capture-promotion, checkmate and
    stalemate positions, and a serialize/deserialize round-trip (incl. the
    multi-target ep field).

Prints "SELFTEST OK" and exits 0 on success, nonzero on any failure.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import GrossChess, RANK1, RANK2  # noqa: E402
from agp.chesslike import CState, WHITE, BLACK  # noqa: E402

G = GrossChess()


def fail(msg: str):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def perft(state, depth: int) -> int:
    if depth == 0:
        return 1
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


def state_from(pieces: dict, to_move=WHITE, rights=frozenset(), ep=None) -> CState:
    board = dict(pieces)
    return CState(board=board, to_move=to_move, castling=rights, ep=ep,
                  reps={G._poskey(board, to_move, rights, ep): 1})


def targets(state, src):
    pre = f"{src[0]},{src[1]}>"
    return sorted(set(m.split(">")[1].split("=")[0]
                      for m in G.legal_moves(state) if m.startswith(pre)))


def cells(*pairs):
    return sorted(f"{c},{r}" for (c, r) in pairs)


# --------------------------------------------------------------------------- #
# 1. Opening array
# --------------------------------------------------------------------------- #
s0 = G.initial_state()
if RANK1 != ["M", "A", "V", "W", "C", None, None, "C", "W", "V", "A", "M"]:
    fail("rank-1 array changed")
if RANK2 != [None, "R", "S", "N", "B", "Q", "K", "B", "N", "S", "R", None]:
    fail("rank-2 array changed")
if len(s0.board) != 64:
    fail(f"expected 64 starting pieces, got {len(s0.board)}")
for c in range(12):
    for (row, arr, pl) in ((0, RANK1, WHITE), (1, RANK2, WHITE),
                           (11, RANK1, BLACK), (10, RANK2, BLACK)):
        want = None if arr[c] is None else (pl, arr[c])
        if s0.board.get((c, row)) != want:
            fail(f"setup mismatch at {(c, row)}: {s0.board.get((c, row))} != {want}")
    if s0.board.get((c, 2)) != (WHITE, "P") or s0.board.get((c, 9)) != (BLACK, "P"):
        fail(f"pawn missing on file {c}")
if s0.board.get((6, 1)) != (WHITE, "K") or s0.board.get((6, 10)) != (BLACK, "K"):
    fail("kings not on the g-file")
if s0.castling != frozenset("KQkq"):
    fail("initial castling rights")

# --------------------------------------------------------------------------- #
# 2. Frozen perft (self-computed 2026-07-01; perft(1) hand-verified)
# --------------------------------------------------------------------------- #
if perft(s0, 1) != 72:
    fail("perft(1) != 72")
if perft(s0, 2) != 5184:
    fail("perft(2) != 5184")
if perft(s0, 3) != 377953:
    fail("perft(3) != 377953")

# --------------------------------------------------------------------------- #
# 3. Fairy leapers: Wizard and Champion exact target sets
# --------------------------------------------------------------------------- #
BASE = {(0, 0): (WHITE, "K"), (11, 11): (BLACK, "K"),
        (11, 0): (WHITE, "R"), (10, 11): (BLACK, "R")}   # rooks off each king's lines

s = state_from({**BASE, **{(5, 5): (WHITE, "W")}})
want = cells((4, 4), (6, 6), (4, 6), (6, 4),                       # ferz
             (6, 8), (4, 8), (8, 6), (2, 6), (6, 2), (4, 2), (8, 4), (2, 4))  # camel
if targets(s, (5, 5)) != want:
    fail(f"Wizard targets: {targets(s, (5, 5))}")

s = state_from({**BASE, **{(5, 5): (WHITE, "S")}})
want = cells((4, 5), (6, 5), (5, 4), (5, 6),                       # wazir
             (3, 5), (7, 5), (5, 3), (5, 7),                       # dabbaba
             (3, 3), (7, 7), (3, 7), (7, 3))                       # alfil
if targets(s, (5, 5)) != want:
    fail(f"Champion targets: {targets(s, (5, 5))}")

# Champion/Wizard leap OVER an occupied square; blocked by a friend on target.
s = state_from({**BASE, **{(5, 5): (WHITE, "S"), (5, 6): (WHITE, "P"),
                             (5, 7): (BLACK, "P")}})
t = targets(s, (5, 5))
if "5,6" in t or "5,7" not in t:
    fail("Champion dabbaba leap/block wrong")

# Marshall = rook+knight, Archbishop = bishop+knight (spot checks)
s = state_from({**BASE, **{(5, 5): (WHITE, "M")}})
t = targets(s, (5, 5))
if not {"5,11", "0,5", "6,7", "3,4"} <= set(t) or "6,6" in t:
    fail(f"Marshall targets: {t}")
s = state_from({**BASE, **{(5, 5): (WHITE, "A")}})
t = targets(s, (5, 5))
if not {"1,1", "9,9", "6,7", "3,4"} <= set(t) or "5,6" in t:
    fail(f"Archbishop targets: {t}")

# --------------------------------------------------------------------------- #
# 4. Cannon / Vao hop mechanics
# --------------------------------------------------------------------------- #
# Cannon at (5,5); screen (5,7); enemy behind screen (5,9); bare enemy (9,5).
s = state_from({**BASE, **{(5, 5): (WHITE, "C"), (5, 7): (BLACK, "P"),
                             (5, 9): (BLACK, "P"), (9, 5): (BLACK, "P")}})
t = set(targets(s, (5, 5)))
if "5,9" not in t:
    fail("Cannon hop capture missing")
if "5,7" in t:
    fail("Cannon may not land on / capture the screen")
if "5,8" in t or "5,10" in t:
    fail("Cannon slid past the screen without capturing")
if "9,5" in t:
    fail("Cannon captured without a screen")
if "8,5" not in t or "5,6" not in t:
    fail("Cannon rider moves missing")

# Vao: screen may be a FRIEND; first piece past the screen must be an enemy.
s = state_from({**BASE, **{(5, 5): (WHITE, "V"), (7, 7): (WHITE, "P"),
                             (9, 9): (BLACK, "P"), (3, 3): (WHITE, "P")}})
t = set(targets(s, (5, 5)))
if "9,9" not in t:
    fail("Vao hop capture over a friendly screen missing")
if "7,7" in t or "8,8" in t or "3,3" in t or "2,2" in t:
    fail(f"Vao move set wrong: {sorted(t)}")

# Two pieces between: no capture (hop is over exactly ONE screen).
s = state_from({**BASE, **{(5, 5): (WHITE, "C"), (5, 6): (BLACK, "P"),
                             (5, 7): (BLACK, "P"), (5, 9): (BLACK, "P")}})
if "5,9" in set(targets(s, (5, 5))):
    fail("Cannon hopped two screens")

# Hop CHECK detection: cannon behind one screen checks the king.
b = dict(BASE)
b.update({(0, 5): (BLACK, "C"), (0, 3): (WHITE, "P")})   # cannon->screen->K at (0,0)
s = state_from(b, to_move=WHITE)
if not G.in_check(s.board, WHITE):
    fail("Cannon check not detected")
b[(0, 2)] = (WHITE, "P")                                  # second screen: no check
if G.in_check(state_from(b).board, WHITE):
    fail("Cannon 'check' through two screens")
b2 = dict(BASE)
b2.update({(4, 4): (BLACK, "V"), (2, 2): (BLACK, "P")})   # vao->screen->K at (0,0)
if not G.in_check(state_from(b2).board, WHITE):
    fail("Vao check not detected")

# --------------------------------------------------------------------------- #
# 5. Pawn triple step + multi-square en passant
# --------------------------------------------------------------------------- #
b = {(0, 2): (WHITE, "P"), (1, 4): (BLACK, "P"), (1, 5): (BLACK, "P"),
     (6, 0): (WHITE, "K"), (6, 11): (BLACK, "K"),
     (11, 0): (WHITE, "R"), (11, 11): (BLACK, "R")}
s = state_from(b)
if targets(s, (0, 2)) != cells((0, 3), (0, 4), (0, 5)):
    fail("pawn initial 1/2/3-step wrong")
s1 = G.apply_move(s, "0,2>0,5")                           # triple step
if s1.ep != (((0, 3), (0, 4)), (0, 5)):
    fail(f"ep after triple step: {s1.ep}")
lm = set(G.legal_moves(s1))
if "1,4>0,3" not in lm or "1,5>0,4" not in lm:
    fail("en passant on a passed square missing")
s2 = G.apply_move(s1, "1,4>0,3")                          # e.p. on the FAR passed square
if (0, 5) in s2.board or s2.board.get((0, 3)) != (BLACK, "P"):
    fail("en passant capture applied wrong")
s2b = G.apply_move(s1, "1,5>0,4")                         # e.p. on the near passed square
if (0, 5) in s2b.board or s2b.board.get((0, 4)) != (BLACK, "P"):
    fail("en passant (near square) applied wrong")
s3 = G.apply_move(s1, "11,11>11,10")                      # decline: right expires
if s3.ep is not None or any("0,3" in m or "0,4" in m
                            for m in G.legal_moves(G.apply_move(s3, "6,0>5,0"))
                            if m.startswith("1,")):
    fail("en passant right did not expire")
# double step -> a single ep target
s4 = G.apply_move(s, "0,2>0,4")
if s4.ep != (((0, 3),), (0, 4)):
    fail(f"ep after double step: {s4.ep}")

# --------------------------------------------------------------------------- #
# 6. Flexible castling
# --------------------------------------------------------------------------- #
CB = {(6, 1): (WHITE, "K"), (1, 1): (WHITE, "R"), (10, 1): (WHITE, "R"),
      (6, 10): (BLACK, "K"), (1, 10): (BLACK, "R"), (10, 10): (BLACK, "R"),
      (0, 2): (WHITE, "P"), (0, 9): (BLACK, "P")}
s = state_from(CB, rights=frozenset("KQkq"))
kt = set(targets(s, (6, 1)))
if not {"8,1", "9,1", "4,1", "3,1", "2,1"} <= kt:
    fail(f"flexible castle destinations missing: {sorted(kt)}")
if "10,1" in kt or "1,1" in kt:
    fail("king castled onto a rook square")
s1 = G.apply_move(s, "6,1>9,1")                           # long kingside castle
if s1.board.get((9, 1)) != (WHITE, "K") or s1.board.get((8, 1)) != (WHITE, "R") \
        or (10, 1) in s1.board:
    fail("kingside castle placement wrong")
if s1.castling != frozenset("kq"):
    fail(f"rights after castling: {s1.castling}")
s2 = G.apply_move(s, "6,1>2,1")                           # longest queenside castle
if s2.board.get((2, 1)) != (WHITE, "K") or s2.board.get((3, 1)) != (WHITE, "R") \
        or (1, 1) in s2.board:
    fail("queenside castle placement wrong")
if G.describe_move(s, "6,1>9,1") != "O-O" or G.describe_move(s, "6,1>2,1") != "O-O-O":
    fail("castle notation wrong")

# any occupied square between king and rook blocks the whole side
b = dict(CB)
b[(2, 1)] = (WHITE, "N")           # not on the king's path, but between R and K
kt = set(targets(state_from(b, rights=frozenset("KQkq")), (6, 1)))
if "4,1" in kt or "3,1" in kt or "2,1" in kt:
    fail("castle allowed with a piece between king and rook")
# through check: enemy rook eyeing (8,1) kills both kingside castles
b = dict(CB)
b[(8, 7)] = (BLACK, "R")
kt = set(targets(state_from(b, rights=frozenset("KQkq")), (6, 1)))
if "8,1" in kt or "9,1" in kt or "4,1" not in kt:
    fail("castle through check allowed")
# moving a rook drops only its own flag
s5 = G.apply_move(s, "10,1>10,5")
if s5.castling != frozenset("Qkq"):
    fail(f"rights after rook move: {s5.castling}")

# --------------------------------------------------------------------------- #
# 7. Tiered reserve promotion
# --------------------------------------------------------------------------- #
PB = {(6, 0): (WHITE, "K"), (6, 11): (BLACK, "K"),
      (11, 0): (WHITE, "R"), (11, 11): (BLACK, "R")}


def promo_choices(row):
    s = state_from({**PB, **{(4, row): (WHITE, "P")}})
    pre = f"4,{row}>4,{row + 1}"
    return sorted(m[len(pre):] for m in G.legal_moves(s) if m.startswith(pre))


if promo_choices(8) != ["", "=B", "=N", "=V", "=W"]:
    fail(f"10th-rank promotion tier: {promo_choices(8)}")
if promo_choices(9) != ["", "=B", "=C", "=N", "=R", "=S", "=V", "=W"]:
    fail(f"11th-rank promotion tier: {promo_choices(9)}")
if promo_choices(10) != ["=A", "=B", "=C", "=M", "=N", "=Q", "=R", "=S", "=V", "=W"]:
    fail(f"last-rank promotion (compulsory): {promo_choices(10)}")

# Pool cap: with 3 queens in play (pool Q=3) the pawn can no longer make one.
b = {**PB, **{(4, 10): (WHITE, "P"), (0, 0): (WHITE, "Q"),
                (1, 0): (WHITE, "Q"), (2, 0): (WHITE, "Q")}}
lm = G.legal_moves(state_from(b))
if "4,10>4,11=Q" in lm or "4,10>4,11=M" not in lm:
    fail("promotion pool cap wrong")

# Capture-promotion: pawn takes a rook on the last rank and becomes a queen.
b = {**PB, **{(4, 10): (WHITE, "P"), (5, 11): (BLACK, "R")}}
s = state_from(b)
s1 = G.apply_move(s, "4,10>5,11=Q")
if s1.board.get((5, 11)) != (WHITE, "Q") or (4, 10) in s1.board:
    fail("capture-promotion applied wrong")

# --------------------------------------------------------------------------- #
# 8. Scripted opening (capture via triple steps), mate, stalemate, round-trip
# --------------------------------------------------------------------------- #
s = G.initial_state()
s = G.apply_move(s, "7,2>7,5")     # h3-h6 (triple)
s = G.apply_move(s, "8,9>8,6")     # i10-i7 (triple)
s = G.apply_move(s, "7,5>8,6")     # h6xi7
if s.board.get((8, 6)) != (WHITE, "P") or len(s.board) != 63 or s.halfmove != 0:
    fail("scripted opening capture wrong")

# checkmate: cornered king, queen guarded by king
b = {(11, 11): (BLACK, "K"), (10, 10): (WHITE, "Q"), (9, 9): (WHITE, "K")}
s = state_from(b, to_move=BLACK)
if not G.is_terminal(s) or G.returns(s) != [1.0, -1.0]:
    fail("checkmate not detected")
# stalemate: same corner, queen a knight's move away
b = {(11, 11): (BLACK, "K"), (9, 10): (WHITE, "Q"), (0, 0): (WHITE, "K")}
s = state_from(b, to_move=BLACK)
if not G.is_terminal(s) or G.returns(s) != [0.0, 0.0]:
    fail("stalemate not detected")

# serialize round-trip through JSON, including the multi-target ep field
s = G.initial_state()
s = G.apply_move(s, "3,2>3,5")
d = json.loads(json.dumps(G.serialize(s)))
s2 = G.deserialize(d)
if s2.board != s.board or s2.ep != s.ep or s2.castling != s.castling \
        or G._poskey_state(s2) != G._poskey_state(s):
    fail("serialize/deserialize round-trip failed")

print("SELFTEST OK")
