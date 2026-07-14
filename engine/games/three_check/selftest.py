#!/usr/bin/env python3
"""Standalone self-test for Three-Check Chess.

Run from the engine dir with:  PYTHONPATH=. python3 games/three_check/selftest.py

Asserts:
  * the correctness ANCHOR: chess perft from the opening = 20 / 400 / 8902 at
    depths 1/2/3 (moves are identical to standard chess);
  * a forcing sequence where the THIRD check ends the game (and that the game is
    NOT over after only one or two checks);
  * a couple of rule-specific positions (double check counts as one; a normal
    move does not increment the counter; serialize round-trips the counters).

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from game import ThreeCheck, TCState, WHITE, BLACK  # noqa: E402
from agp.chesslike import CState  # noqa: E402


def perft(g, state, depth):
    if depth == 0:
        return 1
    total = 0
    for m in g.legal_moves(state):
        total += perft(g, g.apply_move(state, m), depth - 1)
    return total


def play(g, state, moves):
    for m in moves:
        assert m in g.legal_moves(state), f"illegal move {m} in {g.legal_moves(state)}"
        state = g.apply_move(state, m)
    return state


def test_perft_anchor():
    g = ThreeCheck()
    s = g.initial_state()
    for depth, expect in ((1, 20), (2, 400), (3, 8902)):
        got = perft(g, s, depth)
        assert got == expect, f"perft({depth}) = {got}, expected {expect}"
    print(f"  perft anchor OK: 20 / 400 / 8902")


def test_three_checks_wins():
    """A forcing line where White delivers three checks and wins on the third.

    1. e4 e5  2. Bc4 Nc6  3. Qh5 g6  4. Qf3? ... we instead build a line where
    White checks on moves 3, 4 and 5.  We construct it explicitly and verify the
    counter and terminality after each check.
    """
    g = ThreeCheck()
    s = g.initial_state()

    # Open lines for the white queen and bishop.
    s = play(g, s, [
        "4,1>4,3",   # 1. e2-e4
        "4,6>4,4",   # 1...e7-e5
        "5,0>2,3",   # 2. Bf1-c4
        "1,7>2,5",   # 2...Nb8-c6
    ])
    assert not g.is_terminal(s)
    assert s.checks == [0, 0], s.checks

    # 3. Qd1-h5 : not yet check (Black king on e8). 3...Ng8-f6?? exposes nothing,
    # play a quiet move.
    s = play(g, s, ["3,0>7,4", "6,7>5,5"])   # Qd1-h5, Ng8-f6
    assert s.checks == [0, 0], s.checks
    assert not g.is_terminal(s)

    # 4. Qh5xe5+ : queen takes e5 pawn and checks down the open e-file (Black
    # king on e8, e7 vacated).  CHECK #1.
    s = play(g, s, ["7,4>4,4"])   # Qh5xe5+
    assert s.checks == [1, 0], s.checks
    assert not g.is_terminal(s), "one check must not end the game"
    assert g.in_check(s.board, BLACK)

    # 4...Bf8-e7 blocks the check.
    s = play(g, s, ["5,7>4,6"])   # Bf8-e7
    assert not g.in_check(s.board, BLACK)

    # 5. Bc4xf7+ : bishop checks the king (c4-f7 diagonal hits e8).  CHECK #2.
    s = play(g, s, ["2,3>5,6"])   # Bc4xf7+
    assert s.checks == [2, 0], s.checks
    assert not g.is_terminal(s), "two checks must not end the game"

    # 5...Ke8xf7 captures the bishop, getting out of check.
    s = play(g, s, ["4,7>5,6"])   # Ke8xf7
    assert not g.in_check(s.board, BLACK)
    assert not g.is_terminal(s)

    # 6. Qe5-d5+ : queen checks the king now on f7 (d5-e6-f7 diagonal).  CHECK #3
    # -> White wins immediately.
    legal = g.legal_moves(s)
    assert "4,4>3,4" in legal, legal   # Qe5-d5
    s3 = g.apply_move(s, "4,4>3,4")
    assert s3.checks == [3, 0], s3.checks
    assert g.in_check(s3.board, BLACK)
    assert g.is_terminal(s3), "third check must end the game"
    assert g.returns(s3) == [1.0, -1.0], g.returns(s3)
    # No legal moves are offered once terminal.
    assert g.legal_moves(s3) == [], g.legal_moves(s3)
    print("  three-checks-wins sequence OK (game ends on the third check)")


def test_normal_move_no_increment():
    g = ThreeCheck()
    s = g.initial_state()
    s2 = g.apply_move(s, "4,1>4,3")   # 1. e4 -- not a check
    assert s2.checks == [0, 0], s2.checks
    assert not g.is_terminal(s2)
    print("  quiet move does not increment counter OK")


def test_double_check_counts_once():
    """A discovered double check increments the counter by exactly one."""
    g = ThreeCheck()
    # Hand-built position: White king g1; White Bb2 on long diagonal toward a
    # black king on g7; White Nf5.  Knight f5->e7 is NOT it; instead put a
    # discovered-check setup: black king e8, white rook e1 behind a white knight
    # on e5; Ne5->d7 gives a discovered rook check on the e-file AND the knight
    # checks from d7? d7 knight attacks e8? knight on d7 attacks f8,b8,c5,e5,b6,f6
    # -- not e8.  Use a cleaner construction.
    #
    # Black king on e8.  White rook on e1 (open e-file except a white bishop on
    # e4).  White bishop e4 -> b7?? no.  Simpler verified double check:
    #   Black Ke8.  White Re1, White Bc4? no.
    # Construct: Black king e8; White knight d6 gives knight-check (d6 attacks
    # e8? knight d6 attacks: e8 yes! c8,b7,b5,c4,e4,f5,f7) -> d6 attacks e8.  Put
    # a white rook on e1 with the e-file otherwise empty for a simultaneous rook
    # check.  That's a (static) double check; to *create* it with one move use a
    # discovered check: knight on e5 -> d6? e5 blocks the rook; moving Ne5->d6
    # uncovers the Re1 check AND lands d6 giving knight check on e8 = double.
    # White Re1 (4,0), White Ne4 (4,3) blocking the e-file, Black Ke8 (4,7).
    # Ne4 -> d6 (3,5) uncovers the Re1 check on the e-file AND the knight on d6
    # attacks e8 -> a discovered double check delivered by one move.
    board = {
        (4, 0): (WHITE, "R"),   # Re1
        (4, 3): (WHITE, "N"),   # Ne4 (blocks the file)
        (4, 7): (BLACK, "K"),   # Ke8
        (0, 0): (WHITE, "K"),   # White king a1 (kept off the action)
        (7, 7): (BLACK, "R"),   # give Black a non-king piece so it's a sane pos
    }
    s = TCState(board=board, to_move=WHITE, castling=frozenset(), ep=None,
                checks=[0, 0],
                reps={g._poskey(board, WHITE, frozenset(), None): 1})
    mv = "4,3>3,5"
    assert mv in g.legal_moves(s), g.legal_moves(s)
    s2 = g.apply_move(s, mv)
    assert g.in_check(s2.board, BLACK)
    assert s2.checks == [1, 0], f"double check should add one, got {s2.checks}"
    print("  double check counts as one OK")


def test_five_check_option():
    """Under checks_to_win=5, three checks do NOT end the game; five do.

    The threshold is per-state (an option), so we verify it discriminates: the
    SAME check tally is terminal at 3 but not at 5, and vice-versa."""
    g = ThreeCheck()

    # The option reaches the state.
    s5 = g.initial_state(options={"checks_to_win": 5})
    assert s5.checks_to_win == 5, s5.checks_to_win
    s3 = g.initial_state()
    assert s3.checks_to_win == 3, s3.checks_to_win

    # Discriminating position: White has given exactly three checks.
    def at(ctw, wchecks):
        board = {(4, 0): (WHITE, "K"), (4, 7): (BLACK, "K"),
                 (7, 7): (BLACK, "R")}
        return TCState(board=board, to_move=WHITE, castling=frozenset(),
                       ep=None, checks=[wchecks, 0], checks_to_win=ctw,
                       reps={g._poskey(board, WHITE, frozenset(), None): 1})

    assert g.is_terminal(at(3, 3)), "3 checks wins under the three-check rule"
    assert not g.is_terminal(at(5, 3)), "3 checks must NOT win under five-check"
    assert not g.is_terminal(at(5, 4)), "4 checks must NOT win under five-check"
    assert g.is_terminal(at(5, 5)), "5 checks wins under the five-check rule"
    assert g.returns(at(5, 5)) == [1.0, -1.0], g.returns(at(5, 5))
    assert g.legal_moves(at(5, 5)) == [], "no moves once won"

    # Replay the classic three-check forcing line but under checks_to_win=5:
    # the third check must NOT end the game, and the counter keeps climbing.
    s = g.initial_state(options={"checks_to_win": 5})
    line = ["4,1>4,3", "4,6>4,4", "5,0>2,3", "1,7>2,5",
            "3,0>7,4", "6,7>5,5", "7,4>4,4", "5,7>4,6",
            "2,3>5,6", "4,7>5,6", "4,4>3,4"]   # ends on the THIRD check
    s = play(g, s, line)
    assert s.checks == [3, 0], s.checks
    assert not g.is_terminal(s), "three checks must not win under five-check"
    print("  five-check option OK (3 checks no longer wins; 5 does)")


def test_serialize_roundtrip():
    g = ThreeCheck()
    s = g.initial_state()
    s = g.apply_move(s, "4,1>4,3")
    # Manually bump checks to a non-trivial value and round-trip.
    s = TCState(board=s.board, to_move=s.to_move, castling=s.castling, ep=s.ep,
                halfmove=s.halfmove, ply=s.ply, reps=s.reps, checks=[2, 1],
                checks_to_win=5)
    d = g.serialize(s)
    assert d["checks"] == [2, 1], d
    assert d["checks_to_win"] == 5, d
    s2 = g.deserialize(d)
    assert isinstance(s2, TCState)
    assert s2.checks == [2, 1], s2.checks
    assert s2.checks_to_win == 5, s2.checks_to_win
    # serialize(deserialize(serialize)) is stable.
    assert g.serialize(s2) == d
    print("  serialize round-trip of check counters OK")


def main():
    test_perft_anchor()
    test_three_checks_wins()
    test_normal_move_no_increment()
    test_double_check_counts_once()
    test_five_check_option()
    test_serialize_roundtrip()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
