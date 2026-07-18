#!/usr/bin/env python3
"""Standalone correctness anchor for Magnetic Chess.

Run from the engine dir with::

    PYTHONPATH=. python3 games/magnetic_chess/selftest.py

Pure stdlib + this game only.  Prints ``SELFTEST OK`` and exits 0 on success.

Because there is no published engine/oracle for Magnetic Chess, the anchors are:

  * perft(1) = 20 (hand-derived) and the full perft(2) = 437, FROZEN.  perft(2)
    differs from orthodox chess's 400 precisely because magnetism displaces
    pieces after White's first move -- so this count is a genuine regression net
    for the magnet, not a re-test of ordinary chess.
  * a hand-derived depth-2 node: after 1.Nf3 the magnet drags Black's f7-pawn to
    f4, which BOTH removes that pawn's moves (blocked by the knight) AND opens
    f7 so the Black king gains a step -> exactly 19 Black replies.
  * the worked diagram from the rules page (Qd4-d5) reproduced move-for-move:
    same-charge rook repelled, opposite-charge rook & bishop attracted, and a
    king blocking the field line so the piece behind it is untouched.
  * each magnetic effect in isolation (attraction, repulsion, repulsion blocked
    at the edge, king neutrality, king as a blocker) plus multi-piece resolution.
  * magnetic promotion (a pawn dragged onto the last rank becomes a Queen).
  * win by king capture; no en passant; relaxed pawn double-step; check-free
    castling with the rook as the field source; move-string uniqueness;
    serialize round-trips; and random games terminating with valid returns.
"""

import random
import sys
from pathlib import Path

from agp.loader import load_from_dir
from agp.chesslike import CState, WHITE, BLACK

_man, G = load_from_dir(Path(__file__).resolve().parent)


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def mk(board, to_move=WHITE, castling=frozenset()):
    st = CState(board=dict(board), to_move=to_move, castling=castling)
    st.reps = {G._poskey_state(st): 1}
    return st


def perft(s, d):
    if d == 0:
        return 1
    return sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


# --------------------------------------------------------------------------- #
# 1. Setup + perft anchors
# --------------------------------------------------------------------------- #
s0 = G.initial_state()
check(s0.to_move == WHITE, "White to move first")
check(s0.board[(4, 0)] == (WHITE, "K") and s0.board[(4, 7)] == (BLACK, "K"), "kings on e1/e8")
check(sum(1 for _ in s0.board) == 32, "32 pieces at the start")

check(len(G.legal_moves(s0)) == 20, "perft(1) = 20")
check(perft(s0, 2) == 437, "perft(2) = 437 (frozen; != orthodox 400 due to the magnet)")

# 1.Nf3 (g1->f3): magnet drags Black's f7-pawn to f4; the f2-pawn is blocked by
# the f1-bishop and does not move.
s1 = G.apply_move(s0, "6,0>5,2")
check(s1.board.get((5, 3)) == (BLACK, "P"), "1.Nf3 attracts the f7-pawn to f4")
check((5, 6) not in s1.board, "f7 is now empty")
check(s1.board.get((5, 1)) == (WHITE, "P"), "the f2-pawn is blocked (unmoved)")
check(len(G.legal_moves(s1)) == 19, "depth-2 node: 19 Black replies after 1.Nf3")
check("4,7>5,6" in G.legal_moves(s1), "...Kf7 is newly legal (the magnet vacated f7)")

# --------------------------------------------------------------------------- #
# 2. The worked diagram from the rules page: Qd4-d5.
#    Before:  bd8  Kd6  qa5 Rc5 rf5 Pg5  Qd4  bd2   (White to move)
#    After the queen lands on d5:
#      * Rc5 (same charge) is repelled left, stopping at b5 (blocked by qa5);
#      * rf5 (opposite) is attracted to e5 (adjacent to the queen);
#      * bd2 (opposite) is attracted up to d4 (adjacent below the queen);
#      * bd8 is NOT attracted -- the King on d6 blocks the file.
# --------------------------------------------------------------------------- #
diagram = {(3, 7): (1, "B"), (3, 5): (0, "K"), (0, 4): (1, "Q"), (2, 4): (0, "R"),
           (5, 4): (1, "R"), (6, 4): (0, "P"), (3, 3): (0, "Q"), (3, 1): (1, "B")}
res = G.apply_move(mk(diagram), "3,3>3,4")
expected = {(3, 7): (1, "B"), (3, 5): (0, "K"), (0, 4): (1, "Q"), (1, 4): (0, "R"),
            (3, 4): (0, "Q"), (4, 4): (1, "R"), (6, 4): (0, "P"), (3, 3): (1, "B")}
check(res.board == expected, "the rules-page Qd5 diagram is reproduced exactly")

# --------------------------------------------------------------------------- #
# 3. Each magnetic effect in isolation.
# --------------------------------------------------------------------------- #
# Attraction: an opposite-charge rook far down the file is pulled adjacent.
r = G.apply_move(mk({(3, 6): (0, "Q"), (3, 0): (1, "R"), (0, 0): (0, "K"), (7, 7): (1, "K")}),
                 "3,6>3,5")                     # Q to d6; black Rd1 attracted up
check(r.board.get((3, 4)) == (1, "R") and (3, 0) not in r.board, "attraction pulls adjacent")

# Repulsion: a same-charge rook slides away until blocked / to the edge.
r = G.apply_move(mk({(1, 5): (0, "Q"), (3, 5): (0, "R"), (0, 0): (0, "K"), (7, 7): (1, "K")}),
                 "1,5>2,5")                      # Q to c6 (col2,row5); white R (col3,row5) repelled right to the edge
check(r.board.get((7, 5)) == (0, "R") and (3, 5) not in r.board, "repulsion slides to the far edge")

# Repulsion blocked at the edge: an adjacent same-charge rook already on the edge
# cannot be pushed off -> it stays put.
r = G.apply_move(mk({(1, 6): (0, "Q"), (0, 5): (0, "R"), (4, 0): (0, "K"), (4, 7): (1, "K")}),
                 "1,6>1,5")                      # Q to b5; Ra5 (a-file edge) can't be pushed left
check(r.board.get((0, 5)) == (0, "R"), "repulsion cannot push a piece off the board")

# King neutrality: a moving KING generates no field -- its neighbours are frozen.
r = G.apply_move(mk({(3, 3): (0, "K"), (2, 3): (0, "R"), (4, 3): (1, "R"), (0, 7): (1, "K")}),
                 "3,3>3,2")
check(r.board.get((2, 3)) == (0, "R") and r.board.get((4, 3)) == (1, "R"),
      "a king move triggers no magnetism")

# King as a blocker (also shown by the Qd5 diagram): nothing behind a king is pulled.
r = G.apply_move(mk({(3, 1): (0, "Q"), (3, 3): (1, "K"), (3, 6): (1, "R"), (0, 0): (0, "K")}),
                 "3,1>3,2")                      # Q up the d-file; the enemy King on d4 shields Rd7
check(r.board.get((3, 6)) == (1, "R"), "a king blocks the field line")

# --------------------------------------------------------------------------- #
# 4. Magnetic promotion: a pawn dragged onto the last rank becomes a Queen.
# --------------------------------------------------------------------------- #
r = G.apply_move(mk({(5, 0): (0, "R"), (6, 1): (0, "P"), (4, 0): (0, "K"), (0, 7): (1, "K")}),
                 "5,0>6,0")                      # Rf1-g1 repels the g2-pawn up to g8 = Q
check(r.board.get((6, 7)) == (0, "Q") and (6, 1) not in r.board, "magnetic promotion to Queen")

# --------------------------------------------------------------------------- #
# 5. Win by king capture (no check / checkmate).
# --------------------------------------------------------------------------- #
st = mk({(4, 3): (0, "Q"), (4, 4): (1, "K"), (0, 0): (0, "K")})
check("4,3>4,4" in G.legal_moves(st), "the king-capturing move is legal")
won = G.apply_move(st, "4,3>4,4")
check(G._winner(won.board) == WHITE, "White wins by capturing the Black king")
check(G.is_terminal(won) and G.returns(won) == [1.0, -1.0], "terminal + returns after king capture")
check(G.legal_moves(won) == [], "no moves once the game is won")
bwon = G.apply_move(mk({(4, 3): (1, "Q"), (4, 4): (0, "K"), (0, 0): (1, "K")}, to_move=BLACK),
                    "4,3>4,4")
check(G._winner(bwon.board) == BLACK and G.returns(bwon) == [-1.0, 1.0], "symmetric Black win")

# --------------------------------------------------------------------------- #
# 6. No en passant; relaxed double-step; check-free castling (rook = field source)
# --------------------------------------------------------------------------- #
# No e.p.: a double step creates no e.p. target and no capture is offered.
after_dbl = G.apply_move(mk({(4, 4): (0, "P"), (3, 6): (1, "P"), (4, 0): (0, "K"),
                             (4, 7): (1, "K")}, to_move=BLACK), "3,6>3,4")
check(after_dbl.ep is None and "4,4>3,5" not in G.legal_moves(after_dbl), "no en passant")

# Double step from the 1st rank (a pawn magnetism pushed back home may re-launch).
check("2,0>2,2" in G.legal_moves(mk({(2, 0): (0, "P"), (4, 4): (0, "K"), (0, 7): (1, "K")})),
      "a pawn on the 1st rank may still double-step")

# Castling is legal through an attacked square (no check), and the rook's arrival
# is the field source: here the Black rook on f8 is attracted down to f2.
cst = mk({(4, 0): (0, "K"), (7, 0): (0, "R"), (5, 7): (1, "R"), (4, 7): (1, "K")},
         castling=frozenset("KQkq"))
check("4,0>6,0" in G.legal_moves(cst), "O-O is legal through an attacked square")
oc = G.apply_move(cst, "4,0>6,0")
check(oc.board.get((6, 0)) == (0, "K") and oc.board.get((5, 0)) == (0, "R"), "O-O places K/R")
check(oc.board.get((5, 1)) == (1, "R") and (5, 7) not in oc.board,
      "castling's field comes from the ROOK (the f8-rook is pulled to f2)")

# --------------------------------------------------------------------------- #
# 7. Move-string uniqueness + serialize round-trips.
# --------------------------------------------------------------------------- #
ms = G.legal_moves(s0)
check(len(ms) == len(set(ms)), "legal moves are unique strings")
for st in (s0, s1, res, won, oc):
    d = G.serialize(st)
    check(G.serialize(G.deserialize(d)) == d, "serialize round-trips")

# --------------------------------------------------------------------------- #
# 8. Random games terminate with well-formed returns.
# --------------------------------------------------------------------------- #
rng = random.Random(20240717)
for _ in range(8):
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s) and steps < 5000:
        moves = G.legal_moves(s)
        check(len(moves) > 0, "a non-terminal state must have a legal move")
        s = G.apply_move(s, rng.choice(moves))
        steps += 1
    check(G.is_terminal(s), "random game reached a terminal state")
    r = G.returns(s)
    check(len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r), "well-formed returns")

print("SELFTEST OK")
