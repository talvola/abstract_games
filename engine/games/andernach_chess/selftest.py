#!/usr/bin/env python3
"""Standalone self-test for Andernach Chess.

Run from the engine dir with:
    PYTHONPATH=. python3 games/andernach_chess/selftest.py

Asserts (pure stdlib -- imports only ``agp`` + this game):
  * the correctness ANCHOR: engine-derived opening perft = 20 / 400 / 8902 /
    197410 at depths 1-4. Depths 1-3 equal standard chess (no capture is possible
    until move 3, and a colour-flip on a leaf capture does not change that ply's
    move count); depth 4 is the first to DIFFER (chess = 197281) because a flipped
    piece changes the descendant moves;
  * a CAPTURING piece flips to the opponent's colour (reached via apply_move):
    White captures a Black rook with a knight -> the square now holds a BLACK
    knight, and a king capture does NOT flip;
  * en passant flips the capturing pawn, and a capture-promotion promotes THEN
    flips (a White pawn capturing onto rank 7 becomes a Black queen);
  * a capture that would flip the mover's piece into giving check to the MOVER's
    OWN king is ILLEGAL (legality is computed on the post-flip board);
  * serialize round-trips a colour-changed position.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from game import AndernachChess  # noqa: E402
from agp.chesslike import CState, WHITE, BLACK  # noqa: E402


def perft(g, state, depth):
    if depth == 0:
        return 1
    return sum(perft(g, g.apply_move(state, m), depth - 1)
               for m in g.legal_moves(state))


def mkstate(g, board, to_move=WHITE, ep=None, castling=frozenset()):
    return CState(board=dict(board), to_move=to_move, castling=castling, ep=ep,
                  reps={g._poskey(board, to_move, castling, ep): 1})


def test_perft_anchor():
    g = AndernachChess()
    s = g.initial_state()
    for depth, expect in ((1, 20), (2, 400), (3, 8902), (4, 197410)):
        got = perft(g, s, depth)
        assert got == expect, f"perft({depth}) = {got}, expected {expect}"
    # depths 1-3 match chess; depth 4 must differ from chess's 197281.
    assert perft(g, s, 4) != 197281
    print("  perft anchor OK: 20 / 400 / 8902 / 197410 (d4 differs from chess)")


def test_capture_flips_colour():
    g = AndernachChess()
    # White knight b1 captures a Black rook on c3.
    board = {(1, 0): (WHITE, "N"), (2, 2): (BLACK, "R"),
             (7, 0): (WHITE, "K"), (0, 7): (BLACK, "K")}
    s = mkstate(g, board)
    assert "1,0>2,2" in g.legal_moves(s)
    s2 = g.apply_move(s, "1,0>2,2")
    assert s2.board[(2, 2)] == (BLACK, "N"), s2.board[(2, 2)]
    assert (1, 0) not in s2.board
    print("  capturing piece flips to enemy colour OK (White N capture -> Black N)")


def test_king_capture_no_flip():
    g = AndernachChess()
    # White king e5 captures a Black pawn on e6 -- king must NOT change colour.
    board = {(4, 4): (WHITE, "K"), (4, 5): (BLACK, "P"), (0, 0): (BLACK, "K")}
    s = mkstate(g, board)
    assert "4,4>4,5" in g.legal_moves(s)
    s2 = g.apply_move(s, "4,4>4,5")
    assert s2.board[(4, 5)] == (WHITE, "K"), s2.board[(4, 5)]
    print("  king capture does NOT flip colour OK")


def test_quiet_move_no_flip():
    g = AndernachChess()
    board = {(1, 0): (WHITE, "N"), (7, 0): (WHITE, "K"), (0, 7): (BLACK, "K")}
    s = mkstate(g, board)
    s2 = g.apply_move(s, "1,0>2,2")     # quiet knight move, no capture
    assert s2.board[(2, 2)] == (WHITE, "N"), s2.board[(2, 2)]
    print("  quiet (non-capturing) move does NOT flip colour OK")


def test_en_passant_flips():
    g = AndernachChess()
    board = {(4, 4): (WHITE, "P"), (3, 4): (BLACK, "P"),
             (7, 0): (WHITE, "K"), (0, 7): (BLACK, "K")}
    ep = ((3, 5), (3, 4))               # Black pawn just double-stepped to (3,4)
    s = mkstate(g, board, ep=ep)
    assert "4,4>3,5" in g.legal_moves(s)
    s2 = g.apply_move(s, "4,4>3,5")
    assert s2.board[(3, 5)] == (BLACK, "P"), s2.board[(3, 5)]   # flipped
    assert (3, 4) not in s2.board                                # captured pawn gone
    assert (4, 4) not in s2.board
    print("  en-passant capture flips the pawn OK")


def test_capture_promotion_flips():
    g = AndernachChess()
    # White pawn b7 captures a Black rook on c8 and promotes -> Black queen.
    board = {(1, 6): (WHITE, "P"), (2, 7): (BLACK, "R"),
             (7, 0): (WHITE, "K"), (7, 7): (BLACK, "K")}
    s = mkstate(g, board)
    assert "1,6>2,7=Q" in g.legal_moves(s)
    s2 = g.apply_move(s, "1,6>2,7=Q")
    assert s2.board[(2, 7)] == (BLACK, "Q"), s2.board[(2, 7)]
    print("  capture-promotion promotes THEN flips OK (White P -> Black Q)")


def test_self_check_via_flip_is_illegal():
    g = AndernachChess()
    # White Ka1, White Rf1, Black Nd1 on the same rank as the white king with
    # b1/c1 empty. Rf1xd1 would put a BLACK rook on d1 giving check to Ka1 along
    # rank 0 -> the capture is ILLEGAL. Non-capturing rook moves stay legal.
    board = {(0, 0): (WHITE, "K"), (5, 0): (WHITE, "R"),
             (3, 0): (BLACK, "N"), (4, 7): (BLACK, "K")}
    s = mkstate(g, board)
    moves = g.legal_moves(s)
    assert "5,0>3,0" not in moves, "self-check-via-flip capture must be illegal"
    # sanity: the post-flip board really does check White
    nb, _ = g._resolve(board, (5, 0), (3, 0), None)
    assert nb[(3, 0)] == (BLACK, "R")
    assert g.in_check(nb, WHITE)
    # the rook may still slide up to (but not onto) the knight, and along its file
    assert "5,0>4,0" in moves and "5,0>5,5" in moves
    print("  capture that flips into self-check is ILLEGAL OK (legality on post-flip board)")


def test_serialize_roundtrip():
    g = AndernachChess()
    board = {(1, 0): (WHITE, "N"), (2, 2): (BLACK, "R"),
             (7, 0): (WHITE, "K"), (0, 7): (BLACK, "K")}
    s = mkstate(g, board)
    s = g.apply_move(s, "1,0>2,2")      # produce a colour-changed position
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert s2.board == s.board
    assert s2.board[(2, 2)] == (BLACK, "N")
    assert g.serialize(s2) == d
    print("  serialize round-trip of a colour-changed position OK")


def main():
    test_perft_anchor()
    test_capture_flips_colour()
    test_king_capture_no_flip()
    test_quiet_move_no_flip()
    test_en_passant_flips()
    test_capture_promotion_flips()
    test_self_check_via_flip_is_illegal()
    test_serialize_roundtrip()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
