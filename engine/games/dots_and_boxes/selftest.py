"""Pure-stdlib selftest for Dots and Boxes. Run:

    cd engine && PYTHONPATH=. python3 games/dots_and_boxes/selftest.py
"""

from __future__ import annotations

import random

from games.dots_and_boxes.game import DotsAndBoxes, DBState

G = DotsAndBoxes()


def edge_count(m, n):
    return m * (n + 1) + n * (m + 1)


def test_opening_move_count():
    # Default 5x5: 5*6 + 5*6 = 60 edges, all undrawn and legal at the opening.
    s = G.initial_state()
    assert (s.m, s.n) == (5, 5)
    assert len(G.legal_moves(s)) == 60 == edge_count(5, 5)
    # Every move is unique and is a valid H/V edge id.
    lm = G.legal_moves(s)
    assert len(set(lm)) == len(lm)
    # A couple of other sizes.
    s3 = G.initial_state({"size": "3x3"})
    assert len(G.legal_moves(s3)) == edge_count(3, 3) == 24
    s2 = G.initial_state({"size": "2x2"})
    assert len(G.legal_moves(s2)) == edge_count(2, 2) == 12


def test_non_completing_passes_turn():
    s = G.initial_state({"size": "2x2"})
    assert G.current_player(s) == 0
    s2 = G.apply_move(s, "H0,0")          # an outer edge completes nothing
    assert G.current_player(s2) == 1, "non-completing move must pass the turn"
    assert s2.scores == [0, 0]


def test_completing_box_grants_extra_move():
    # 1x1 box: edges H0,0 H0,1 V0,0 V1,0. Draw three, then the 4th completes it.
    s = DBState(m=1, n=1,
                h_edges=frozenset({(0, 0), (0, 1)}),
                v_edges=frozenset({(0, 0)}),
                to_move=0)
    assert G.current_player(s) == 0
    assert not G.is_terminal(s)
    s2 = G.apply_move(s, "V1,0")          # closes box (0,0)
    assert s2.owners.get((0, 0)) == 0
    assert s2.scores == [1, 0]
    # board is now full (4 edges drawn) => terminal; the "extra move" is moot but
    # the mover did NOT pass: to_move stayed 0.
    assert s2.to_move == 0, "completing a box must keep the SAME player to move"
    assert G.is_terminal(s2)
    assert G.returns(s2) == [1.0, -1.0]


def test_same_player_keeps_moving_midgame():
    # 1x2 board (boxes (0,0),(0,1)); close the lower box but leave edges so the
    # game is NOT over -> the mover must keep the turn AND have legal moves.
    s = DBState(m=1, n=2,
                h_edges=frozenset({(0, 0), (0, 1)}),  # bottom + middle
                v_edges=frozenset({(0, 0)}),          # left of lower box
                to_move=0)
    s2 = G.apply_move(s, "V1,0")          # completes lower box (0,0)
    assert s2.owners == {(0, 0): 0}
    assert s2.scores == [1, 0]
    assert s2.to_move == 0
    assert not G.is_terminal(s2)
    assert len(G.legal_moves(s2)) > 0     # invariant: non-terminal => has moves


def test_double_box_one_extra_move():
    # 1x2 board: leave ONLY the shared middle edge H0,1 undrawn. Drawing it
    # completes BOTH boxes for the mover (score +2) -- exactly one "move again"
    # (here the board becomes full, so terminal). Verifies a single line can
    # close two boxes and is scored for both.
    all_h = {(0, 0), (0, 1), (0, 2)}      # H0,0 H0,1 H0,2  (r=0,1,2)
    all_v = {(0, 0), (1, 0), (0, 1), (1, 1)}  # V0,0 V1,0 V0,1 V1,1
    s = DBState(m=1, n=2,
                h_edges=frozenset(all_h - {(0, 1)}),   # everything but the shared edge
                v_edges=frozenset(all_v),
                to_move=1)
    assert G.legal_moves(s) == ["H0,1"]
    s2 = G.apply_move(s, "H0,1")
    assert s2.scores == [0, 2], "one line closing two boxes scores both"
    assert s2.owners == {(0, 0): 1, (0, 1): 1}
    assert G.is_terminal(s2)
    assert G.returns(s2) == [-1.0, 1.0]


def test_full_playout_terminates_and_scores():
    # Play a full random game on a small board; it must terminate with all edges
    # drawn and a well-formed payoff, and box totals must sum to the box count.
    rng = random.Random(12345)
    for size, (m, n) in [("3x3", (3, 3)), ("2x2", (2, 2)), ("5x4", (5, 4))]:
        s = G.initial_state({"size": size})
        steps = 0
        while not G.is_terminal(s):
            mv = rng.choice(G.legal_moves(s))
            s = G.apply_move(s, mv)
            steps += 1
            assert steps <= edge_count(m, n) + 1
        assert len(s.h_edges) + len(s.v_edges) == edge_count(m, n)
        assert sum(s.scores) == m * n, "every box must be claimed at game end"
        r = G.returns(s)
        assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)
        if s.scores[0] == s.scores[1]:
            assert r == [0.0, 0.0]
        else:
            assert (r == [1.0, -1.0]) == (s.scores[0] > s.scores[1])


def test_tie_is_a_draw():
    # 5x4 = 20 boxes (even) CAN tie. Construct a reached 10-10 terminal by
    # forcing a full board with a split of owners is hard; instead verify the
    # draw branch directly via a terminal state with equal scores.
    # Build a full 1x2 board where each player owns one box.
    full_h = frozenset({(0, 0), (0, 1), (0, 2)})
    full_v = frozenset({(0, 0), (1, 0), (0, 1), (1, 1)})
    s = DBState(m=1, n=2, h_edges=full_h, v_edges=full_v,
                owners={(0, 0): 0, (0, 1): 1}, scores=[1, 1], to_move=0)
    assert G.is_terminal(s)
    assert G.returns(s) == [0.0, 0.0], "equal boxes => draw"


def test_serialize_roundtrip():
    rng = random.Random(7)
    s = G.initial_state({"size": "3x3"})
    for _ in range(15):
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    d = G.serialize(s)
    s2 = G.deserialize(d)
    assert G.serialize(s2) == d
    # JSON-able
    import json
    json.dumps(d)


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("dots_and_boxes selftest: all tests passed")


if __name__ == "__main__":
    main()
