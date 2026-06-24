#!/usr/bin/env python3
"""Standalone self-test for Checkless Chess.

Run from the engine dir with:
  PYTHONPATH=. python3 games/checkless_chess/selftest.py

Pure-stdlib (imports only ``agp`` + this game).  Asserts:

  * the correctness ANCHOR -- opening perft 20 / 400 / 8890 at depths 1/2/3.
    d1=20 and d2=400 equal standard chess (no check is possible that shallow);
    d3 = 8890 is *engine-derived*: it is standard chess's 8902 minus the 12
    depth-3 leaves that are non-mating checks (White's 3rd move giving a check
    the enemy king can flee), which are now illegal.  Frozen here.
  * a non-mating check move is ILLEGAL (a rook that could check a king that can
    flee -> that move is absent from legal_moves);
  * a checkMATING move IS legal and wins (a back-rank mate-in-1: the mating
    check is offered, gives check, is terminal, and White wins);
  * a normal non-checking move is unaffected;
  * serialize round-trips.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from game import ChecklessChess, WHITE, BLACK  # noqa: E402
from agp.chesslike import CState  # noqa: E402


def perft(g, state, depth):
    if depth == 0:
        return 1
    return sum(perft(g, g.apply_move(state, m), depth - 1) for m in g.legal_moves(state))


def _state(g, board, to_move=WHITE):
    return CState(board=board, to_move=to_move, castling=frozenset(), ep=None,
                  reps={g._poskey(board, to_move, frozenset(), None): 1})


def test_perft_anchor():
    g = ChecklessChess()
    s = g.initial_state()
    # d1/d2 == standard chess; d3 = 8890 (engine-derived: 8902 - 12 illegal
    # non-mating checks at depth 3).
    for depth, expect in ((1, 20), (2, 400), (3, 8890)):
        got = perft(g, s, depth)
        assert got == expect, f"perft({depth}) = {got}, expected {expect}"
    print("  perft anchor OK: 20 / 400 / 8890 (d3 engine-derived: chess 8902 - 12)")


def test_nonmating_check_illegal():
    """A rook that *could* give check to a king that can simply walk away must
    not be allowed to (it is a non-mating check)."""
    g = ChecklessChess()
    # White Ra1, White Kh1; Black Ke8 alone.  Ra1-e1 would check up the e-file,
    # but the black king flees to d7/f7 etc -> not mate -> the move is illegal.
    board = {(0, 0): (WHITE, "R"), (7, 0): (WHITE, "K"), (4, 7): (BLACK, "K")}
    s = _state(g, board)
    lm = g.legal_moves(s)

    check_move = "0,0>4,0"           # Ra1-e1, giving a (non-mating) check on e-file
    assert check_move not in lm, f"non-mating check {check_move} must be illegal"

    # Sanity: that very move *does* give check in plain terms (apply_move is the
    # inherited base method, so this is the unfiltered successor) -- so it really
    # is a check that is being filtered, not an unrelated illegality.
    succ = g.apply_move(s, check_move)
    assert g.in_check(succ.board, succ.to_move), "test move should actually give check"

    # A normal non-checking rook move IS allowed.
    quiet = "0,0>0,3"                 # Ra1-a4: does not attack the king
    assert quiet in lm, f"quiet rook move {quiet} should be legal; legal={sorted(lm)}"
    qs = g.apply_move(s, quiet)
    assert not g.in_check(qs.board, qs.to_move)
    print("  non-mating check is illegal; quiet move unaffected OK")


def test_mating_check_legal_and_wins():
    """A back-rank mate-in-one: the mating check IS legal, is terminal, wins."""
    g = ChecklessChess()
    # Black Kg8 boxed in by its own pawns f7/g7/h7; White Ra1, White Kg1.
    # Ra1-a8 is mate (king g8 has no flight, f8/h8 covered by the rook).
    board = {
        (6, 7): (BLACK, "K"),
        (5, 6): (BLACK, "P"), (6, 6): (BLACK, "P"), (7, 6): (BLACK, "P"),
        (0, 0): (WHITE, "R"), (6, 0): (WHITE, "K"),
    }
    s = _state(g, board)
    mate = "0,0>0,7"                  # Ra1-a8#
    assert mate in g.legal_moves(s), f"mating check must be legal; legal={sorted(g.legal_moves(s))}"

    s2 = g.apply_move(s, mate)
    assert g.in_check(s2.board, s2.to_move), "mating move gives check"
    assert g.legal_moves(s2) == [], "checkmate -> opponent has no reply"
    assert g.is_terminal(s2), "checkmate is terminal"
    assert g.returns(s2) == [1.0, -1.0], f"White wins the mate; got {g.returns(s2)}"
    print("  checkmating check is legal and wins OK")


def test_normal_opening_moves_present():
    g = ChecklessChess()
    s = g.initial_state()
    lm = g.legal_moves(s)
    assert "4,1>4,3" in lm and "6,0>5,2" in lm, "ordinary opening moves must be present"
    s2 = g.apply_move(s, "4,1>4,3")
    assert not g.is_terminal(s2)
    print("  ordinary opening moves unaffected OK")


def test_serialize_roundtrip():
    g = ChecklessChess()
    s = g.initial_state()
    s = g.apply_move(s, "4,1>4,3")
    s = g.apply_move(s, "4,6>4,4")
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d, "serialize(deserialize(serialize)) must be stable"
    assert set(g.legal_moves(s)) == set(g.legal_moves(s2)), "round-trip preserves legal moves"
    print("  serialize round-trip OK")


def main():
    test_perft_anchor()
    test_nonmating_check_illegal()
    test_mating_check_legal_and_wins()
    test_normal_opening_moves_present()
    test_serialize_roundtrip()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
