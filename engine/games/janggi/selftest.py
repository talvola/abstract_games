#!/usr/bin/env python3
"""Standalone correctness anchor for Janggi (Korean Chess).

Run from the engine directory:  PYTHONPATH=. python3 games/janggi/selftest.py

Pure stdlib + this game only. Fast (well under a second). Asserts:

  * a self-computed perft regression baseline (31 / 949 / 29697 at depths 1-3),
  * cannon jump-to-capture and the three cannon restrictions
    (no jumping over / capturing / screening with another cannon),
  * elephant 1+2 leap with intermediate-square blocking,
  * palace diagonals for General and Guard (centre <-> corner),
  * soldier forward + sideways, and soldier palace-diagonal inside the enemy
    palace (forward only, never backward),
  * the bikjang / flying-general rule (a move exposing the two generals on an
    open file is illegal),
  * a constructed checkmate (no legal move -> side to move loses),
  * a light conformance sweep (random self-play always terminates with a
    well-formed result).

Exits 0 and prints "SELFTEST OK" on success; raises (nonzero) on any failure.

The perft numbers are this implementation's own baseline. No published Janggi
perft from the standard symmetric opening was available to cross-check, so the
gate is: perft regression baseline + the rule-specific positions below +
conformance. (See rules.md for the documented ruleset choices, esp. bikjang.)
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from games.janggi.game import (  # noqa: E402
    Janggi, JGState, _pseudo_targets, _generals_face,
)

G = Janggi()


def st(board, to_move=0):
    return JGState(board=dict(board), to_move=to_move)


def targets(board, sq):
    return set(_pseudo_targets(dict(board), sq))


def legal(board, to_move=0):
    return set(G.legal_moves(st(board, to_move)))


def perft(s, depth):
    if depth == 0:
        return 1
    n = 0
    for m in G.legal_moves(s):
        n += perft(G.apply_move(s, m), depth - 1)
    return n


def test_perft():
    s = G.initial_state()
    expect = {1: 31, 2: 949, 3: 29697}
    for d, want in expect.items():
        got = perft(s, d)
        assert got == want, f"perft({d}) = {got}, expected {want}"


def test_opening_setup():
    b = G.initial_state().board
    # generals one row into the palace, on the centre file
    assert b[(4, 1)] == "G" and b[(4, 8)] == "g"
    # symmetric back rank R H E A . A E H R
    assert [b.get((c, 0)) for c in range(9)] == \
        ["R", "H", "E", "A", None, "A", "E", "H", "R"]
    # cannons on files 1 & 7, third rank from the edge
    assert b[(1, 2)] == "C" and b[(7, 2)] == "C"
    assert b[(1, 7)] == "c" and b[(7, 7)] == "c"


def test_cannon_jump_capture():
    # C jumps the single screen S and may capture the enemy chariot beyond it.
    b = {(0, 0): "C", (0, 3): "S", (0, 7): "r", (4, 1): "G", (4, 8): "g"}
    assert targets(b, (0, 0)) == {(0, 4), (0, 5), (0, 6), (0, 7)}


def test_cannon_no_cannon_screen():
    # The screen is an enemy cannon -> the cannon cannot move along that line.
    b = {(0, 0): "C", (0, 3): "c", (0, 7): "r", (4, 1): "G", (4, 8): "g"}
    assert targets(b, (0, 0)) == set()


def test_cannon_cannot_capture_cannon():
    # Valid (non-cannon) screen, but the target beyond it is a cannon -> may
    # slide to the empties but NOT capture the cannon.
    b = {(0, 0): "C", (0, 3): "S", (0, 7): "c", (4, 1): "G", (4, 8): "g"}
    assert targets(b, (0, 0)) == {(0, 4), (0, 5), (0, 6)}


def test_elephant_leap_and_blocks():
    base = {(4, 4): "E", (4, 1): "G", (4, 8): "g"}
    full = {(1, 2), (1, 6), (2, 1), (2, 7), (6, 1), (6, 7), (7, 2), (7, 6)}
    assert targets(base, (4, 4)) == full
    # block the right-orthogonal leg (5,4): drops the two right-leg landings
    b = dict(base); b[(5, 4)] = "S"
    assert targets(b, (4, 4)) == full - {(7, 2), (7, 6)}
    # block the first diagonal of the up-right branch (5,6): drops only (6,7)
    b = dict(base); b[(5, 6)] = "S"
    assert targets(b, (4, 4)) == full - {(6, 7)}


def test_general_palace_diagonals():
    # General on the palace centre reaches all 8 palace points (incl. corners).
    b = {(4, 1): "G", (4, 8): "g"}
    assert targets(b, (4, 1)) == {
        (3, 0), (4, 0), (5, 0), (3, 1), (5, 1), (3, 2), (4, 2), (5, 2)}


def test_guard_palace_diagonal():
    # Guard on a corner can step diagonally to the (empty) palace centre.
    b = {(3, 0): "A", (4, 2): "G", (4, 8): "g"}
    assert targets(b, (3, 0)) == {(3, 1), (4, 0), (4, 1)}


def test_soldier_forward_sideways():
    # Cho soldier mid-board: forward (+row) and sideways, never backward.
    b = {(4, 4): "S", (4, 1): "G", (4, 8): "g"}
    assert targets(b, (4, 4)) == {(4, 5), (3, 4), (5, 4)}


def test_soldier_enemy_palace_diagonal():
    # Cho soldier on a front corner of the enemy palace: forward, sideways, and
    # the forward palace diagonal toward the centre; not the backward diagonal.
    b = {(3, 7): "S", (4, 1): "G", (4, 8): "g"}
    assert targets(b, (3, 7)) == {(3, 8), (2, 7), (4, 7), (4, 8)}
    # On the far (back) corner the only palace diagonal is backward -> excluded.
    b2 = {(5, 9): "S", (4, 1): "G", (4, 7): "g"}
    assert targets(b2, (5, 9)) == {(4, 9), (6, 9)}


def test_bikjang_facing():
    assert _generals_face({(4, 1): "G", (4, 8): "g"}) is True
    assert _generals_face({(4, 1): "G", (4, 8): "g", (4, 5): "S"}) is False
    # A move that exposes the generals on an open file is illegal: the Han
    # soldier screening file 4 may only move forward (stay on the file), not
    # sideways off it.
    b = {(4, 0): "G", (4, 9): "g", (4, 5): "s"}
    soldier_moves = {m for m in legal(b, to_move=1) if m.startswith("4,5>")}
    assert soldier_moves == {"4,5>4,4"}, soldier_moves


def test_checkmate():
    # Three Cho chariots cover files 3,4,5; the Han general at (4,9) is mated.
    b = {(4, 1): "R", (3, 1): "R", (5, 1): "R", (4, 9): "g", (4, 0): "G"}
    s = st(b, to_move=1)
    assert G.legal_moves(s) == []
    assert G.is_terminal(s)
    assert G.returns(s) == [1.0, -1.0]   # Cho wins, Han (to move) loses


def test_serialize_roundtrip():
    s = G.initial_state()
    s2 = G.deserialize(G.serialize(s))
    assert G.serialize(s2) == G.serialize(s)


def test_conformance():
    rng = random.Random(20260621)
    for _ in range(12):
        s = G.initial_state()
        while not G.is_terminal(s):
            mv = G.legal_moves(s)
            assert mv, "non-terminal state with no legal moves"
            s = G.apply_move(s, rng.choice(mv))
        r = G.returns(s)
        assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)
        assert sum(r) == 0.0


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
