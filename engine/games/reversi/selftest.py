#!/usr/bin/env python3
"""Pure-stdlib selftest for Reversi / Othello (incl. the size & goal options).

Run from the engine dir with:
    PYTHONPATH=. python3 games/reversi/selftest.py

Asserts:
  * the default 8×8 fixed-diagonal start is unchanged (backward compatible);
  * the 10×10 (Grand Othello) start places the four centre discs correctly and a
    seeded random game plays to a full/blocked board and terminates;
  * the flip mechanic on a hand-built position;
  * the ``goal`` option flips the win comparison — most-discs vs fewest-discs
    (Anti-/misère Othello) — and an equal count is an honest draw under both;
  * serialize round-trips size + goal.

Prints "SELFTEST OK" and exits 0 on success.
"""

from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from game import Reversi, ReversiState  # noqa: E402


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


def test_default_start_unchanged():
    g = Reversi()
    s = g.initial_state()
    check(s.size == 8 and s.opening == "othello" and s.goal == "most",
          f"default options {s.size}/{s.opening}/{s.goal}")
    # White (1) on the \-diagonal centre, Black (0) on the /-diagonal centre.
    check(s.board == {(3, 3): 1, (4, 4): 1, (3, 4): 0, (4, 3): 0},
          f"8×8 start board {s.board}")
    # Black to move has the four classic opening placements.
    check(set(g.legal_moves(s)) == {"3,2", "2,3", "5,4", "4,5"},
          f"8×8 opening moves {g.legal_moves(s)}")
    print("  8×8 default start unchanged OK")


def test_grand_start_and_playout():
    g = Reversi()
    s = g.initial_state(options={"size": 10})
    check(s.size == 10, "size=10 stored")
    # centre lo=4, hi=5 -> White (4,4)&(5,5), Black (4,5)&(5,4)
    check(s.board == {(4, 4): 1, (5, 5): 1, (4, 5): 0, (5, 4): 0},
          f"10×10 start board {s.board}")
    spec = g.render(s)
    check(spec["board"]["width"] == 10 and spec["board"]["height"] == 10,
          "render is 10×10")

    rng = random.Random(2024)
    steps = 0
    while not g.is_terminal(s) and steps < 500:
        s = g.apply_move(s, rng.choice(g.legal_moves(s)), rng=rng)
        steps += 1
    check(g.is_terminal(s), "10×10 random game terminates")
    b, w = g._counts(s)
    check(b + w <= 100, f"disc count within a 10×10 board ({b}+{w})")
    check(g.returns(s) in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]),
          "terminal returns are win/loss/draw")
    print(f"  10×10 start + random playout OK ({steps} plies, {b}-{w})")


def test_flip_mechanic():
    g = Reversi()
    # Black plays 2,3 to bracket the White disc on 3,3 against Black 4,3.
    s = g.initial_state()
    check("2,3" in g.legal_moves(s), "2,3 is a legal Black opener")
    s2 = g.apply_move(s, "2,3")
    check(s2.board[(3, 3)] == 0, "the bracketed White disc flipped to Black")
    check(s2.board[(2, 3)] == 0, "the placed disc is Black")
    check(s2.to_move == 1, "White to move next")
    print("  flip mechanic OK")


def _full_board(n, black_cells):
    """A completely filled n×n board (terminal): the given cells are Black (0),
    every other cell is White (1)."""
    bc = set(black_cells)
    return {(c, r): (0 if (c, r) in bc else 1)
            for c in range(n) for r in range(n)}


def test_goal_option():
    g = Reversi()
    # A full 8×8 board with 20 Black and 44 White discs (terminal: no empties).
    black = [(c, r) for c in range(4) for r in range(5)]   # 20 cells
    board = _full_board(8, black)
    check(len(board) == 64, "board is full")

    most = ReversiState(board=dict(board), to_move=0, size=8, goal="most")
    check(g.is_terminal(most), "full board is terminal")
    b, w = g._counts(most)
    check((b, w) == (20, 44), f"counts {b}-{w}")
    check(g.returns(most) == [-1.0, 1.0], "most-discs: White (44) wins")

    few = ReversiState(board=dict(board), to_move=0, size=8, goal="fewest")
    check(g.returns(few) == [1.0, -1.0], "fewest-discs: Black (20) wins")

    # Equal counts -> honest draw under BOTH goals.
    half = [(c, r) for c in range(4) for r in range(8)]    # 32 cells
    tie = _full_board(8, half)
    for goal in ("most", "fewest"):
        s = ReversiState(board=dict(tie), to_move=0, size=8, goal=goal)
        check(g.returns(s) == [0.0, 0.0], f"32-32 is a draw under goal={goal}")
    print("  goal option OK (most/fewest flip; equal = draw)")


def test_serialize_roundtrip():
    g = Reversi()
    s = g.initial_state(options={"size": 10, "goal": "fewest", "opening": "reversi"})
    s = g.apply_move(s, g.legal_moves(s)[0])
    blob = json.dumps(g.serialize(s))
    s2 = g.deserialize(json.loads(blob))
    check(g.serialize(s2) == g.serialize(s), "serialize round-trips")
    check(s2.size == 10 and s2.goal == "fewest" and s2.opening == "reversi",
          f"options survive: {s2.size}/{s2.goal}/{s2.opening}")
    print("  serialize round-trip OK")


def main():
    test_default_start_unchanged()
    test_grand_start_and_playout()
    test_flip_mechanic()
    test_goal_option()
    test_serialize_roundtrip()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
