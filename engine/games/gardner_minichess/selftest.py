#!/usr/bin/env python3
"""Standalone correctness anchor for Gardner's Minichess.

Run from the engine dir with::

    PYTHONPATH=. python3 games/gardner_minichess/selftest.py

Pure stdlib + this game only (no third-party engine), fast. Prints ``SELFTEST OK``
and exits 0 on success, nonzero on any failure.

It asserts:

* the setup: 10 men per side, back rank R N B Q K (a->e) for both colours, five
  pawns each, kings on the e-file facing each other;
* the opening **perft** baseline d1=7, d2=53, d3=506. These match the published
  Gardner 5x5 minichess node counts (the well-known 7 / 53 / 506 / 4775 series)
  and are independently reproduced by this engine's move generator. d1=7 is
  hand-verified below: five single-square pawn pushes plus the b1 knight's two
  moves (Na3, Nc3) = 7 (no double step, so each pawn has exactly one push);
* a **checkmate** reached via apply_move (terminal + the mated side loses);
* **promotion** to each of Q/R/B/N on the last rank;
* serialize round-trips.
"""

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.gardner_minichess.game import GardnerMinichess

G = GardnerMinichess()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


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
check(len(s0.board) == 20, "20 men at the start (10 per side)")
BACK = ["R", "N", "B", "Q", "K"]
for c in range(5):
    check(s0.board[(c, 0)] == (WHITE, BACK[c]), "White back rank R N B Q K (a->e)")
    check(s0.board[(c, 1)] == (WHITE, "P"), "White pawns on rank 2")
    check(s0.board[(c, 3)] == (BLACK, "P"), "Black pawns on rank 4")
    check(s0.board[(c, 4)] == (BLACK, BACK[c]), "Black back rank R N B Q K (a->e)")
check(s0.board[(4, 0)] == (WHITE, "K") and s0.board[(4, 4)] == (BLACK, "K"),
      "kings face each other on the e-file")
wp = sum(1 for v in s0.board.values() if v == (WHITE, "P"))
bp = sum(1 for v in s0.board.values() if v == (BLACK, "P"))
check(wp == 5 and bp == 5, "five pawns per side")

# --------------------------------------------------------------------------- #
# 2. Opening perft baseline (matches the published 7/53/506/4775 series)
# --------------------------------------------------------------------------- #
check(perft(s0, 1) == 7, "perft(1) must be 7")
check(perft(s0, 2) == 53, "perft(2) must be 53")
check(perft(s0, 3) == 506, "perft(3) must be 506")

# Hand-verify d1=7: no double step, so each of the 5 pawns has exactly one push;
# the b1 knight has Na3 and Nc3; every other piece is hemmed in at the start.
opening = set(G.legal_moves(s0))
check(len(opening) == 7, "exactly 7 opening moves")
pawn_pushes = {f"{c},1>{c},2" for c in range(5)}
check(pawn_pushes <= opening, "all five single-square pawn pushes are legal")
check("1,0>0,2" in opening and "1,0>2,2" in opening, "the b1 knight has Na3 and Nc3")
# No double step exists from the opening.
check(not any(m.endswith(">"+f"{c},3") for c in range(5) for m in opening),
      "no pawn double step from the opening")

# --------------------------------------------------------------------------- #
# 3. Checkmate, reached via apply_move (winner is decided by returns(), not stored)
# --------------------------------------------------------------------------- #
# White queen on a4 swings to d4 and mates the black king on e5; the white king
# on e3 covers e4, the queen covers d4/d5/e5.
b = {(4, 4): (BLACK, "K"), (0, 3): (WHITE, "Q"), (4, 2): (WHITE, "K")}
st = CState(board=b, to_move=WHITE, castling=frozenset())
check("0,3>3,3" in G.legal_moves(st), "Qa4-d4 is legal")
st2 = G.apply_move(st, "0,3>3,3")
check(G.is_terminal(st2), "the position after Qd4# is terminal")
check(G.in_check(st2.board, BLACK), "black king is in check (mate, not stalemate)")
check(G.returns(st2) == [1.0, -1.0], "White (player 0) wins the checkmate")

# Stalemate is a draw, not a win: lone black king a5, white Qc4 + Kc3, black to move.
bs = {(0, 4): (BLACK, "K"), (2, 3): (WHITE, "Q"), (2, 2): (WHITE, "K")}
sts = CState(board=bs, to_move=BLACK, castling=frozenset())
check(G.is_terminal(sts) and not G.in_check(bs, BLACK), "stalemate is terminal")
check(G.returns(sts) == [0.0, 0.0], "stalemate is a draw")

# --------------------------------------------------------------------------- #
# 4. Promotion to each of Q/R/B/N on the last rank
# --------------------------------------------------------------------------- #
bp_ = {(0, 3): (WHITE, "P"), (0, 0): (WHITE, "K"), (4, 4): (BLACK, "K")}
stp = CState(board=bp_, to_move=WHITE, castling=frozenset())
promo = {m for m in G.legal_moves(stp) if m.startswith("0,3>0,4")}
check(promo == {"0,3>0,4=Q", "0,3>0,4=R", "0,3>0,4=B", "0,3>0,4=N"},
      "pawn promotes to exactly Q/R/B/N on the last rank")
for ch in ("Q", "R", "B", "N"):
    after = G.apply_move(stp, f"0,3>0,4={ch}")
    check(after.board.get((0, 4)) == (WHITE, ch), f"promotion to {ch} places the piece")

# --------------------------------------------------------------------------- #
# 5. Serialize round-trips
# --------------------------------------------------------------------------- #
check(G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0),
      "serialize must round-trip the opening position")
s1 = G.apply_move(s0, "1,0>2,2")     # Nc3
check(G.serialize(G.deserialize(G.serialize(s1))) == G.serialize(s1),
      "serialize must round-trip after a move")

print("SELFTEST OK")
sys.exit(0)
