#!/usr/bin/env python3
"""Standalone self-test for No-Castling Chess.

Run from the engine dir with:
    PYTHONPATH=. python3 games/no_castling_chess/selftest.py

Asserts:
  * the correctness ANCHOR: opening perft = 20 / 400 / 8902 at depths 1/2/3,
    identical to standard chess (castling cannot occur that shallow, so no node
    is added or removed);
  * on a position where standard chess WOULD offer both castles, No-Castling
    Chess offers NEITHER (while the ordinary one-square king moves are still
    available) -- verified by diffing against a `Chess` instance on the SAME
    board and rights.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from game import NoCastlingChess  # noqa: E402
from agp.chesslike import CState, WHITE, BLACK  # noqa: E402
from games.chess.game import Chess  # noqa: E402


def perft(g, state, depth):
    if depth == 0:
        return 1
    return sum(perft(g, g.apply_move(state, m), depth - 1)
               for m in g.legal_moves(state))


def test_perft_anchor():
    g = NoCastlingChess()
    s = g.initial_state()
    for depth, expect in ((1, 20), (2, 400), (3, 8902)):
        got = perft(g, s, depth)
        assert got == expect, f"perft({depth}) = {got}, expected {expect}"
    print("  perft anchor OK: 20 / 400 / 8902")


def _castle_ready_board():
    """A legal position (White to move, not in check) where both kings still
    have their rooks in the corners and the back ranks are clear between king
    and rook, so standard chess offers both O-O and O-O-O for White."""
    return {
        (4, 0): (WHITE, "K"), (0, 0): (WHITE, "R"), (7, 0): (WHITE, "R"),
        (4, 7): (BLACK, "K"), (0, 7): (BLACK, "R"), (7, 7): (BLACK, "R"),
    }


def _state(g, board):
    rights = frozenset("KQkq")
    return CState(board=dict(board), to_move=WHITE, castling=rights, ep=None,
                  reps={g._poskey(board, WHITE, rights, None): 1})


def test_no_castling_offered():
    board = _castle_ready_board()
    KSIDE, QSIDE = "4,0>6,0", "4,0>2,0"   # king's two-square castling moves

    std = Chess()
    std_moves = std.legal_moves(_state(std, board))
    assert KSIDE in std_moves, f"standard chess should offer O-O: {std_moves}"
    assert QSIDE in std_moves, f"standard chess should offer O-O-O: {std_moves}"

    nc = NoCastlingChess()
    nc_moves = nc.legal_moves(_state(nc, board))
    assert KSIDE not in nc_moves, "No-Castling Chess must NOT offer O-O"
    assert QSIDE not in nc_moves, "No-Castling Chess must NOT offer O-O-O"

    # The ordinary one-square king steps are still there (sanity: the king is
    # not simply frozen). From e1 the king may step to d1/f1/d2/e2/f2.
    for step in ("4,0>3,0", "4,0>5,0", "4,0>3,1", "4,0>4,1", "4,0>5,1"):
        assert step in nc_moves, f"one-square king step {step} missing: {nc_moves}"

    # Every legal No-Castling move is also legal in standard chess on this board
    # (the only difference is the two removed castles).
    assert set(nc_moves) == set(std_moves) - {KSIDE, QSIDE}, (
        "No-Castling legal set should equal standard minus the two castles")
    print("  no-castling: both castles removed, king still steps normally OK")


def main():
    test_perft_anchor()
    test_no_castling_offered()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
