#!/usr/bin/env python3
"""Correctness anchor for Sittuyin (Burmese chess).

No standard published perft exists for Sittuyin (and the deployment phase makes a
fixed opening perft meaningless), so the anchor is *conformance* (random games --
including a full random deployment -- terminate, with legal moves at every
non-terminal node) plus hand-built **rule positions** that pin down the
Sittuyin-specific rules:

  * the fixed staggered pawn (Ne) formation (a-d on the home rank, e-h one rank
    up) for both sides;
  * the deployment / setup phase: each side places exactly 8 pieces from its
    reserve, confined to its own three ranks, with the chariots (R) restricted to
    the back rank; the play phase begins (and check/checkmate engage) only once
    both reserves are empty;
  * the piece moves: General = ferz (4 diagonals), Elephant = 4 diagonals + one
    step straight forward (colour-dependent), pawn steps forward / captures
    diagonally forward;
  * the sit-tu promotion reached via apply_move: a pawn on a promotion-diagonal
    square (in the enemy half) promotes to a General -- in place or onto an
    adjacent empty diagonal -- but ONLY if the player has no General;
  * a checkmate reached via apply_move ends the game with the right result, and
    stalemate is a draw;
  * a serialize round-trip including the setup-phase reserves.

Pure stdlib (imports only ``agp`` + this game). Run with:
    PYTHONPATH=. python3 games/sittuyin/selftest.py
Prints "SELFTEST OK" and exits 0 on success; raises / exits non-zero on failure.
"""

from __future__ import annotations

import random
import sys

from agp.chesslike import CState, WHITE, BLACK
from games.sittuyin.game import (
    Sittuyin, WHITE_PAWNS, BLACK_PAWNS, WHITE_PROMO, BLACK_PROMO,
)

G = Sittuyin()


def st(board, to_move=WHITE):
    return CState(board=dict(board), to_move=to_move, castling=frozenset(),
                  ep=None, reps={}, hands={WHITE: {}, BLACK: {}})


def dests_from(state, frm):
    out = set()
    for m in G.legal_moves(state):
        base = m.split("=")[0]
        a, b = base.split(">")
        if a == f"{frm[0]},{frm[1]}":
            c, r = b.split(",")
            out.add((int(c), int(r)))
    return out


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# --------------------------------------------------------------------------- #
# Pawn formation: a-d on the home rank, e-h one rank further forward.
# --------------------------------------------------------------------------- #
def test_pawn_formation():
    s = G.initial_state()
    wp = {sq for sq, (pl, t) in s.board.items() if pl == WHITE and t == "P"}
    bp = {sq for sq, (pl, t) in s.board.items() if pl == BLACK and t == "P"}
    check(wp == set(WHITE_PAWNS), f"White pawn formation wrong: {sorted(wp)}")
    check(bp == set(BLACK_PAWNS), f"Black pawn formation wrong: {sorted(bp)}")
    check(wp == {(0, 2), (1, 2), (2, 2), (3, 2), (4, 3), (5, 3), (6, 3), (7, 3)},
          "White pawns not in the staggered a-d/e-h split")
    check(bp == {(0, 4), (1, 4), (2, 4), (3, 4), (4, 5), (5, 5), (6, 5), (7, 5)},
          "Black pawns not in the staggered a-d/e-h split")
    # No non-pawn pieces start on the board.
    nonpawn = [sq for sq, (pl, t) in s.board.items() if t != "P"]
    check(nonpawn == [], f"non-pawns should not start on board: {nonpawn}")


# --------------------------------------------------------------------------- #
# Deployment / setup phase: 8 placements per side, confined to own half, rooks
# on the back rank; the play phase begins when both reserves empty.
# --------------------------------------------------------------------------- #
def test_setup_phase():
    s = G.initial_state()
    check(s.hands[WHITE] == {"K": 1, "G": 1, "R": 2, "E": 2, "N": 2},
          f"White reserve wrong: {s.hands[WHITE]}")
    check(s.hands[BLACK] == {"K": 1, "G": 1, "R": 2, "e": 2, "N": 2},
          f"Black reserve wrong: {s.hands[BLACK]}")
    check(not G.is_terminal(s), "setup start should not be terminal")

    # Every legal setup move is a drop confined to the player's own half.
    for m in G.legal_moves(s):
        check("@" in m, f"setup move should be a drop: {m}")
        r = int(m.split("@")[1].split(",")[1])
        check(0 <= r <= 2, f"White drop outside own half (row {r}): {m}")
    # Chariots only on the back rank (row 0 for White).
    rook_rows = {int(m.split(",")[1]) for m in G.legal_moves(s) if m.startswith("R@")}
    check(rook_rows == {0}, f"White chariot drop rows should be {{0}}, got {rook_rows}")

    # A placement on an enemy-half square (or beyond own 3 ranks) is illegal.
    check("K@0,3" not in G.legal_moves(s), "should not deploy onto rank 4 (row 3)")
    check("K@0,7" not in G.legal_moves(s), "should not deploy into enemy half")

    # Play a full random deployment; assert 16 placements and empty reserves.
    rng = random.Random(99)
    placements = 0
    while G._in_setup(s):
        ms = G.legal_moves(s)
        check(len(ms) > 0, "empty legal_moves during setup")
        s = G.apply_move(s, rng.choice(ms))
        placements += 1
        check(placements <= 16, "more than 16 placements in setup")
    check(placements == 16, f"expected 16 placements, got {placements}")
    check(all(n == 0 for h in s.hands.values() for n in h.values()),
          "reserves not empty after setup")
    check(s.to_move == WHITE, "White should move first in the play phase")
    # Correct piece inventory on the board.
    from collections import Counter
    cnt = Counter((pl, t) for (pl, t) in s.board.values())
    check(cnt[(WHITE, "K")] == 1 and cnt[(WHITE, "G")] == 1
          and cnt[(WHITE, "R")] == 2 and cnt[(WHITE, "E")] == 2
          and cnt[(WHITE, "N")] == 2 and cnt[(WHITE, "P")] == 8,
          f"White inventory wrong after deploy: {dict(cnt)}")


# --------------------------------------------------------------------------- #
# Check/checkmate must NOT engage during the setup phase.
# --------------------------------------------------------------------------- #
def test_no_check_during_setup():
    s = G.initial_state()
    # Drop both kings on the same file with nothing between -- irrelevant in setup.
    s = G.apply_move(s, "K@4,0")          # White king
    # Black to deploy; place a chariot on the same file as ... still setup, no check.
    check(not G.is_terminal(s), "still in setup, must not be terminal")
    check(G.returns(s) == [0.0, 0.0], "setup returns must be draw-valued")
    # All Black moves are still placements.
    for m in G.legal_moves(s):
        check("@" in m, f"Black still deploying: unexpected non-drop {m}")


# --------------------------------------------------------------------------- #
# Piece moves.
# --------------------------------------------------------------------------- #
def test_general_is_ferz():
    s = st({(3, 3): (WHITE, "G"), (7, 7): (WHITE, "K"), (7, 5): (WHITE, "R"),
            (0, 0): (BLACK, "K"), (0, 5): (BLACK, "R")})
    d = dests_from(s, (3, 3))
    check(d == {(2, 2), (4, 2), (2, 4), (4, 4)},
          f"General should be a ferz (4 diagonals), got {sorted(d)}")


def test_elephant_white():
    s = st({(3, 3): (WHITE, "E"), (7, 7): (WHITE, "K"), (7, 5): (WHITE, "R"),
            (0, 0): (BLACK, "K"), (0, 5): (BLACK, "R")})
    d = dests_from(s, (3, 3))
    expect = {(2, 2), (4, 2), (2, 4), (4, 4), (3, 4)}   # 4 diag + straight forward (up)
    check(d == expect, f"White Elephant dests wrong: {sorted(d)} want {sorted(expect)}")
    check((3, 2) not in d and (2, 3) not in d and (4, 3) not in d,
          "Elephant moved straight back/sideways")


def test_elephant_black():
    s = st({(3, 3): (BLACK, "e"), (0, 0): (BLACK, "K"), (0, 5): (BLACK, "R"),
            (7, 7): (WHITE, "K"), (7, 5): (WHITE, "R")}, to_move=BLACK)
    d = dests_from(s, (3, 3))
    expect = {(2, 2), (4, 2), (2, 4), (4, 4), (3, 2)}   # 4 diag + straight forward (down)
    check(d == expect, f"Black Elephant dests wrong: {sorted(d)} want {sorted(expect)}")


def test_pawn_move_and_capture():
    s = st({(3, 3): (WHITE, "P"), (2, 4): (BLACK, "P"), (7, 7): (WHITE, "K"),
            (0, 0): (BLACK, "K"), (7, 0): (WHITE, "R")})
    d = dests_from(s, (3, 3))
    check(d == {(3, 4), (2, 4)},
          f"Pawn should step forward + capture diagonally, got {sorted(d)}")
    # No double step from the home rank.
    s2 = st({(0, 2): (WHITE, "P"), (7, 7): (WHITE, "K"), (0, 0): (BLACK, "K"),
             (7, 0): (WHITE, "R")})
    check(dests_from(s2, (0, 2)) == {(0, 3)}, "pawn must not have a double step")


# --------------------------------------------------------------------------- #
# Sit-tu promotion (the signature rule), reached via apply_move.
# --------------------------------------------------------------------------- #
def test_promotion_squares_are_the_long_diagonals():
    # WHITE_PROMO = the enemy-half (rows 4..7) squares of both long diagonals.
    check(WHITE_PROMO == {(4, 4), (5, 5), (6, 6), (7, 7), (3, 4), (2, 5), (1, 6), (0, 7)},
          f"White promotion squares wrong: {sorted(WHITE_PROMO)}")
    check(BLACK_PROMO == {(0, 0), (1, 1), (2, 2), (3, 3), (4, 3), (5, 2), (6, 1), (7, 0)},
          f"Black promotion squares wrong: {sorted(BLACK_PROMO)}")


def test_promotion_requires_no_general():
    # No White general -> a pawn on (4,4) (a promotion square) may promote.
    s = st({(4, 4): (WHITE, "P"), (7, 7): (WHITE, "K"), (0, 7): (BLACK, "K"),
            (7, 5): (WHITE, "R")})
    promos = sorted(m for m in G.legal_moves(s) if m.endswith("=G"))
    check("4,4>4,4=G" in promos, f"in-place promotion missing: {promos}")
    check("4,4>5,5=G" in promos, f"adjacent-diagonal promotion missing: {promos}")
    s2 = G.apply_move(s, "4,4>4,4=G")
    check(s2.board[(4, 4)] == (WHITE, "G"), "in-place promotion did not yield a General")
    s3 = G.apply_move(s, "4,4>5,5=G")
    check(s3.board.get((5, 5)) == (WHITE, "G") and (4, 4) not in s3.board,
          "diagonal promotion did not move the new General")

    # With a General still on the board -> promotion is illegal.
    s = st({(4, 4): (WHITE, "P"), (7, 7): (WHITE, "K"), (0, 7): (BLACK, "K"),
            (1, 1): (WHITE, "G"), (7, 5): (WHITE, "R")})
    check([m for m in G.legal_moves(s) if m.endswith("=G")] == [],
          "promotion must be illegal while the player still has a General")

    # A pawn NOT on a promotion diagonal cannot promote.
    s = st({(3, 5): (WHITE, "P"), (7, 7): (WHITE, "K"), (0, 7): (BLACK, "K"),
            (7, 5): (WHITE, "R")})
    check([m for m in G.legal_moves(s) if m.endswith("=G")] == [],
          "promotion must be illegal off the long diagonals")


# --------------------------------------------------------------------------- #
# Checkmate ends the game; stalemate is a draw. (Reached/constructed in the
# play phase -- both reserves empty.)
# --------------------------------------------------------------------------- #
def test_checkmate():
    board = {
        (0, 7): (BLACK, "K"),
        (0, 0): (WHITE, "R"),   # checks along the a-file
        (1, 1): (WHITE, "R"),   # covers b7,b8
        (7, 0): (WHITE, "K"),
    }
    s = st(board, to_move=BLACK)
    check(G.in_check(s.board, BLACK), "expected Black in check")
    check(G.legal_moves(s) == [], "expected checkmate (no legal moves)")
    check(G.is_terminal(s), "checkmate should be terminal")
    check(G.returns(s) == [1.0, -1.0], f"White should win, got {G.returns(s)}")


def test_checkmate_via_apply_move():
    # Reach a mate by actually delivering it: Black king a8; White rook from a3
    # to a-file gives mate with the b-file rook already covering b7/b8.
    board = {
        (0, 7): (BLACK, "K"),
        (3, 0): (WHITE, "R"),   # will slide to a1, giving check up the a-file
        (1, 1): (WHITE, "R"),   # covers b7,b8 (the escape squares)
        (7, 0): (WHITE, "K"),
    }
    s = st(board, to_move=WHITE)
    s = G.apply_move(s, "3,0>0,0")   # rook d1->a1: checks a8 king; b-rook covers escape
    check(G.is_terminal(s), "should be checkmate after the rook check")
    check(G.returns(s) == [1.0, -1.0], f"White wins the mate, got {G.returns(s)}")


def test_stalemate_is_draw():
    board = {
        (0, 7): (BLACK, "K"),
        (1, 0): (WHITE, "R"),   # file b -> covers b7,b8
        (7, 6): (WHITE, "R"),   # rank 7 -> covers a7
        (7, 0): (WHITE, "K"),
    }
    s = st(board, to_move=BLACK)
    check(not G.in_check(s.board, BLACK), "stalemate must not be in check")
    check(G.legal_moves(s) == [], "expected no legal moves (stalemate)")
    check(G.is_terminal(s), "stalemate should be terminal")
    check(G.returns(s) == [0.0, 0.0], f"stalemate must be a draw, got {G.returns(s)}")


# --------------------------------------------------------------------------- #
# Conformance: random games (incl. random deployment) terminate with legal moves
# and a serialize round-trip.
# --------------------------------------------------------------------------- #
def test_conformance():
    rng = random.Random(20260624)
    for g in range(25):
        s = G.initial_state()
        plies = 0
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            check(len(ms) > 0, f"empty legal_moves at non-terminal (game {g})")
            if plies % 29 == 0:
                check(G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s),
                      "serialize did not round-trip")
            s = G.apply_move(s, rng.choice(ms))
            plies += 1
            check(plies <= G.PLY_CAP + 20, "exceeded ply cap (non-termination)")
        ret = G.returns(s)
        check(ret in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0]),
              f"unexpected returns {ret}")


def main():
    test_pawn_formation()
    test_setup_phase()
    test_no_check_during_setup()
    test_general_is_ferz()
    test_elephant_white()
    test_elephant_black()
    test_pawn_move_and_capture()
    test_promotion_squares_are_the_long_diagonals()
    test_promotion_requires_no_general()
    test_checkmate()
    test_checkmate_via_apply_move()
    test_stalemate_is_draw()
    test_conformance()
    print("SELFTEST OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"SELFTEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
