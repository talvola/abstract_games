"""Pure-stdlib correctness anchors for Silo.

Run: cd engine && PYTHONPATH=. python3 games/silo/selftest.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from agp.loader import load_from_dir

RED, BLUE = 0, 1


def _load():
    man, g = load_from_dir(Path(__file__).resolve().parent)
    return g


def test_setup():
    g = _load()
    st = g.initial_state()
    # Fig 1: alternating stacks of 3 red / 3 blue across a 1x6 strip.
    assert st.width == 6 and st.height == 3
    assert st.board == [[RED] * 3, [BLUE] * 3, [RED] * 3,
                        [BLUE] * 3, [RED] * 3, [BLUE] * 3], st.board
    assert g._n(st) == 9
    assert st.to_move == RED and st.ply == 0
    # 1x8 option: alternating stacks of 4.
    st8 = g.initial_state({"setup": "1x8"})
    assert st8.width == 8 and st8.height == 4 and g._n(st8) == 16
    assert st8.board[0] == [RED] * 4 and st8.board[1] == [BLUE] * 4
    print("ok setup")


def test_opposite_directions():
    g = _load()
    st = g.initial_state()
    # Red (seat 0) moves toward the high end (+1).
    assert set(g.legal_moves(st)) == {"0,0>1,0", "2,0>3,0", "4,0>5,0"}, g.legal_moves(st)
    # Force Blue to move: Blue moves toward the low end (-1).
    st.to_move = BLUE
    st.ply = 4  # avoid the pie condition for this direction check
    assert set(g.legal_moves(st)) == {"1,0>0,0", "3,0>2,0", "5,0>4,0"}, g.legal_moves(st)
    print("ok opposite directions")


def test_highest_own_carry_enemies_above():
    # Reproduces Fig 5 (Blue move): the source stack (cell 3) is
    # bottom->top R,R,B,R,B,R,R.  Blue's HIGHEST blue is the upper one, with two
    # reds stacked above it; Blue carries [B,R,R] one square left onto cell 2.
    g = _load()
    board = [
        [RED],                          # cell 0  (1 red)
        [BLUE] * 7,                     # cell 1  (7 blue)
        [RED, RED, RED],                # cell 2  destination
        [RED, RED, BLUE, RED, BLUE, RED, RED],  # cell 3  source
        [], [],                         # cells 4,5 empty
    ]
    # 9 reds, 9 blues total.
    reds = sum(c.count(RED) for c in board)
    blues = sum(c.count(BLUE) for c in board)
    assert reds == 9 and blues == 9, (reds, blues)
    from games.silo.game import SState
    st = SState(board=board, width=6, height=3, to_move=BLUE, ply=6)
    assert "3,0>2,0" in g.legal_moves(st)
    ns = g.apply_move(st, "3,0>2,0")
    assert ns.board[2] == [RED, RED, RED, BLUE, RED, RED], ns.board[2]   # Fig 5b left
    assert ns.board[3] == [RED, RED, BLUE, RED], ns.board[3]              # Fig 5b right
    assert ns.winner is None and not ns.draw
    print("ok highest-own + carry-enemies-above (Fig 5)")


def test_win_one_contiguous_substack():
    # Red gathers all 9 reds into one contiguous run (Fig 2 style).
    g = _load()
    from games.silo.game import SState
    board = [
        [], [],
        [], [],
        [RED],            # cell 4: the last red, moving right
        [RED] * 8,        # cell 5: eight reds already contiguous
    ]
    board[0] = [BLUE] * 9   # the nine blues parked at the far end
    st = SState(board=board, width=6, height=3, to_move=RED, ply=20)
    assert not g.is_terminal(st)
    ns = g.apply_move(st, "4,0>5,0")
    assert ns.board[5] == [RED] * 9
    assert ns.winner == RED and g.is_terminal(ns)
    assert g.returns(ns) == [1.0, -1.0]
    # A run split by an enemy checker is NOT a win.
    split = [[], [], [], [], [], [RED] * 4 + [BLUE] + [RED] * 5]
    split[0] = [BLUE] * 8
    assert not g._won(split, RED, 9)
    print("ok win = one contiguous substack")


def test_pie_swap():
    g = _load()
    st = g.initial_state()
    st1 = g.apply_move(st, "0,0>1,0")        # Red opens
    assert st1.to_move == BLUE and st1.ply == 1
    assert "swap" in g.legal_moves(st1)
    st2 = g.apply_move(st1, "swap")
    assert st2.swapped and st2.to_move == RED and st2.ply == 2
    # swap = reflect + recolour of the post-opening board.
    expect = [[1 - o for o in st1.board[5 - c]] for c in range(6)]
    assert st2.board == expect, st2.board
    # Setup is symmetric under the swap transform (sanity on the symmetry).
    sym = [[1 - o for o in st.board[5 - c]] for c in range(6)]
    assert sym == st.board
    # No second swap offered.
    assert "swap" not in g.legal_moves(st2)
    print("ok pie swap")


def test_skip_when_no_move():
    g = _load()
    from games.silo.game import SState
    # All blues jammed at cell 0 -> Blue has no legal move (can't go below 0).
    # A red is interspersed among them so Blue has NOT won (run is split).
    board = [[BLUE, BLUE, BLUE, BLUE, RED, BLUE, BLUE, BLUE, BLUE, BLUE],
             [RED] * 8, [], [], [], []]
    assert sum(c.count(RED) for c in board) == 9
    assert sum(c.count(BLUE) for c in board) == 9
    assert g._has_move(board, BLUE, 6) is False
    assert g._has_move(board, RED, 6) is True
    assert g._won(board, BLUE, 9) is False   # blues split by a red -> not a win
    # If Red moves and Blue still can't move, Blue is skipped -> Red again.
    assert g._next_mover(board, RED, 6) == RED
    st = SState(board=[list(c) for c in board], width=6, height=3, to_move=RED, ply=2)
    ns = g.apply_move(st, "1,0>2,0")
    assert ns.to_move == RED and ns.winner is None and not ns.draw
    print("ok skip when no move")


def test_termination():
    g = _load()
    rng = random.Random(12345)
    for trial in range(40):
        st = g.initial_state()
        steps = 0
        cap = g._ply_cap(st) + 5
        while not g.is_terminal(st):
            moves = g.legal_moves(st)
            assert moves, "non-terminal state must have moves"
            st = g.apply_move(st, rng.choice(moves))
            steps += 1
            assert steps <= cap, "exceeded ply cap"
        r = g.returns(st)
        assert r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]), r
    print("ok termination (40 random games)")


def main():
    test_setup()
    test_opposite_directions()
    test_highest_own_carry_enemies_above()
    test_win_one_contiguous_substack()
    test_pie_swap()
    test_skip_when_no_move()
    test_termination()
    print("all silo selftests passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("SELFTEST FAILED:", e)
        sys.exit(1)
