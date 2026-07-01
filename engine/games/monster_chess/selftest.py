#!/usr/bin/env python3
"""Standalone correctness anchor for Monster Chess.

Run from the engine dir with::

    PYTHONPATH=. python3 games/monster_chess/selftest.py

Pure stdlib + this game only. Prints ``SELFTEST OK`` and exits 0 on success.

Asserts:
  * the setup (White K + 4 pawns; Black's full 16-piece army);
  * the double-move turn cycle: White moves TWICE (to_move stays White with
    moves_left 2 -> 1) then flips to Black; Black moves ONCE then flips to White
    with moves_left = 2;
  * White may move its king THROUGH check -- a first move that leaves the White
    king attacked is still legal (no self-check filter);
  * Black may not leave its king capturable by White in two moves -- moves that
    do are excluded, a safe move is kept, and a king-capturing move is always kept;
  * White wins by capturing the Black king (reached via apply_move: winner set,
    is_terminal, returns correct); symmetric Black king-capture;
  * serialize round-trips (moves_left + winner);
  * random games terminate within the ply cap with well-formed returns.
"""

import random
import sys

from agp.chesslike import WHITE, BLACK
from games.monster_chess.game import MonsterChess, MState

G = MonsterChess()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


# --------------------------------------------------------------------------- #
# 1. Setup
# --------------------------------------------------------------------------- #
s0 = G.initial_state()
check(s0.board[(4, 0)] == (WHITE, "K"), "White King on e1")
for c in (2, 3, 4, 5):
    check(s0.board[(c, 1)] == (WHITE, "P"), f"White pawn on file {c} rank 2")
white_men = [sq for sq, (pl, _) in s0.board.items() if pl == WHITE]
black_men = [sq for sq, (pl, _) in s0.board.items() if pl == BLACK]
check(len(white_men) == 5, "White has exactly 5 men (K + 4P)")
check(len(black_men) == 16, "Black has the full 16-piece army")
check(s0.to_move == WHITE and s0.moves_left == 2, "White to move, 2 moves left")
check(s0.board[(4, 7)] == (BLACK, "K"), "Black King on e8")

# --------------------------------------------------------------------------- #
# 2. Double-move turn cycle
# --------------------------------------------------------------------------- #
s1 = G.apply_move(s0, "3,1>3,2")           # d2-d3 (White's first move)
check(s1.to_move == WHITE and s1.moves_left == 1, "still White after 1st move, 1 left")
s2 = G.apply_move(s1, "2,1>2,2")           # c2-c3 (White's second move)
check(s2.to_move == BLACK and s2.moves_left == 1, "Black to move after White's 2 moves")
s3 = G.apply_move(s2, "0,6>0,5")           # a7-a6 (Black's single move)
check(s3.to_move == WHITE and s3.moves_left == 2, "White to move again with 2 moves")
# purity: applying did not mutate the source states
check(s0.to_move == WHITE and s0.moves_left == 2, "apply_move did not mutate s0")

# --------------------------------------------------------------------------- #
# 3. White may move its king through check (no self-check filter)
# --------------------------------------------------------------------------- #
# White K e1; Black rook h2 rakes rank 2; Black K e8. White to move.
sc = MState(board={(4, 0): (WHITE, "K"), (7, 1): (BLACK, "R"), (4, 7): (BLACK, "K")},
            to_move=WHITE, castling=frozenset(), ep=None, moves_left=2)
lm_w = G.legal_moves(sc)
# e1-e2 lands on e2, which the h2 rook attacks along the rank -> illegal in ordinary
# chess, but LEGAL in Monster Chess (king may pass through check).
check("4,0>4,1" in lm_w, "White king may step INTO an attacked square")
check(G.attacked(sc.board, 4, 1, BLACK), "sanity: e2 really is attacked by the rook")

# --------------------------------------------------------------------------- #
# 4. Black may not leave its king capturable by White in two moves
# --------------------------------------------------------------------------- #
# White K a1; Black K c1 (two king-steps away -> reachable in 2) + a spare Black
# rook h8. Black to move.
sb = MState(board={(0, 0): (WHITE, "K"), (2, 0): (BLACK, "K"), (7, 7): (BLACK, "R")},
            to_move=BLACK, castling=frozenset(), ep=None, moves_left=1)
lm_b = G.legal_moves(sb)
# Moving the rook leaves the king on c1, which White reaches in 2 (Kb1, Kxc1) -> illegal.
check("7,7>7,6" not in lm_b, "Black may not leave its king capturable in 2 (rook move)")
# Kc1-b1 / Kc1-b2 / Kc1-c2 stay within White's 2-move reach -> illegal.
check("2,0>1,0" not in lm_b, "Kc1-b1 is capturable in 1 -> illegal")
check("2,0>2,1" not in lm_b, "Kc1-c2 is capturable in 2 -> illegal")
# Kc1-d1 is 3 king-steps from a1 (White has only the king) -> SAFE, must be legal.
check("2,0>3,0" in lm_b, "Kc1-d1 escapes White's 2-move reach -> legal")

# A Black move that captures the White king is always legal even if 'unsafe'.
sk = MState(board={(3, 0): (WHITE, "K"), (4, 0): (BLACK, "K"), (0, 7): (BLACK, "R")},
            to_move=BLACK, castling=frozenset(), ep=None, moves_left=1)
check("4,0>3,0" in G.legal_moves(sk), "Black may always capture the White king")

# --------------------------------------------------------------------------- #
# 5. Winning by king capture (via apply_move)
# --------------------------------------------------------------------------- #
# White K d5 adjacent to Black K e5; White to move -> Kxe5 wins.
sw = MState(board={(3, 4): (WHITE, "K"), (4, 4): (BLACK, "K")},
            to_move=WHITE, castling=frozenset(), ep=None, moves_left=2)
check("3,4>4,4" in G.legal_moves(sw), "White has the king-capturing move")
won = G.apply_move(sw, "3,4>4,4")
check(won.winner == WHITE, "White winner set after capturing the Black king")
check(G.is_terminal(won), "position is terminal after king capture")
check(G.returns(won) == [1.0, -1.0], "returns give White the win")
check(G.legal_moves(won) == [], "no legal moves once won")
# capturing on the FIRST of White's two moves ends the turn immediately.
check(won.moves_left == 0, "king capture ends White's turn at once")

# Symmetric: Black captures the White king.
bw = G.apply_move(sk, "4,0>3,0")
check(bw.winner == BLACK and G.returns(bw) == [-1.0, 1.0], "Black wins by king capture")

# --------------------------------------------------------------------------- #
# 6. serialize round-trips (incl. moves_left + winner)
# --------------------------------------------------------------------------- #
for st in (s0, s1, s2, s3, won):
    d = G.serialize(st)
    again = G.serialize(G.deserialize(d))
    check(again == d, "serialize round-trips")
    check(d["moves_left"] == st.moves_left, "moves_left serialized")
    check(d["winner"] == st.winner, "winner serialized")

# --------------------------------------------------------------------------- #
# 7. Random games terminate
# --------------------------------------------------------------------------- #
rng = random.Random(1234)
for g in range(6):
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s) and steps < 5000:
        moves = G.legal_moves(s)
        check(len(moves) > 0, "non-terminal state must have a legal move")
        s = G.apply_move(s, rng.choice(moves))
        steps += 1
    check(G.is_terminal(s), "random game reached a terminal state")
    r = G.returns(s)
    check(len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r), "well-formed returns")

print("SELFTEST OK")
