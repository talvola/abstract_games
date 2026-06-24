"""Pure-stdlib correctness anchor for Quantik. Run by tests/test_games.py and
standalone:  PYTHONPATH=. python3 games/quantik/selftest.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.quantik.game import Quantik, QState  # noqa: E402


def _state(board=None, hands=None, to_move=0, winner=None):
    g = Quantik()
    s = g.initial_state()
    if board is not None:
        s.board = dict(board)
    if hands is not None:
        s.hands = {p: dict(h) for p, h in hands.items()}
    s.to_move = to_move
    s.winner = winner
    return s


def test_opening_move_count():
    g = Quantik()
    s = g.initial_state()
    # Empty board: 16 cells x 4 shapes available, no restriction => 64 moves.
    assert len(g.legal_moves(s)) == 64, len(g.legal_moves(s))
    # All distinct.
    assert len(set(g.legal_moves(s))) == 64


def test_opponent_shape_blocks():
    """A shape the OPPONENT placed in a row/col/zone forbids that shape there."""
    g = Quantik()
    # Opponent (player 1) placed shape A at (0,0). Player 0 to move.
    s = _state(board={(0, 0): (1, "A")}, to_move=0)
    legal = set(g.legal_moves(s))
    # Same row (row 0): cells (1,0),(2,0),(3,0) cannot take A.
    assert "A@1,0" not in legal and "A@2,0" not in legal and "A@3,0" not in legal
    # Same column (col 0): (0,1),(0,2),(0,3) cannot take A.
    assert "A@0,1" not in legal and "A@0,2" not in legal and "A@0,3" not in legal
    # Same 2x2 zone (top-left {(0,0),(1,0),(0,1),(1,1)}): (1,1) cannot take A.
    assert "A@1,1" not in legal
    # A cell sharing NONE of row/col/zone with (0,0) -- e.g. (2,2) -- CAN take A.
    assert "A@2,2" in legal
    # Other shapes are unaffected everywhere empty.
    assert "B@1,0" in legal and "C@0,1" in legal and "D@1,1" in legal


def test_own_shape_allowed():
    """Your OWN same shape in a line/zone does NOT block you."""
    g = Quantik()
    # Player 0 already has shape A at (0,0); player 0 to move again.
    s = _state(board={(0, 0): (0, "A")}, to_move=0)
    legal = set(g.legal_moves(s))
    # Same row / col / zone: placing your OWN shape A again is allowed.
    assert "A@1,0" in legal   # same row
    assert "A@0,1" in legal   # same column
    assert "A@1,1" in legal   # same zone
    # And an unrelated cell of course.
    assert "A@3,3" in legal


def test_win_completing_row_any_colours():
    """Completing a row with all 4 distinct shapes wins, regardless of colour."""
    g = Quantik()
    # Row 0 has A,B,C from mixed colours; player 0 to place D at (3,0) -> win.
    board = {(0, 0): (1, "A"), (1, 0): (0, "B"), (2, 0): (1, "C")}
    hands = {0: {"A": 2, "B": 1, "C": 2, "D": 2},
             1: {"A": 1, "B": 2, "C": 1, "D": 2}}
    s = _state(board=board, hands=hands, to_move=0)
    assert "D@3,0" in set(g.legal_moves(s))
    ns = g.apply_move(s, "D@3,0")
    assert ns.winner == 0, ns.winner
    assert g.is_terminal(ns)
    assert g.returns(ns) == [1.0, -1.0]


def test_win_completing_zone():
    """Completing a 2x2 zone with all 4 shapes wins."""
    g = Quantik()
    # Bottom-right zone cells: (2,2),(3,2),(2,3),(3,3). Fill A,B,C; place D.
    board = {(2, 2): (0, "A"), (3, 2): (1, "B"), (2, 3): (0, "C")}
    hands = {0: {"A": 1, "B": 2, "C": 1, "D": 2},
             1: {"A": 2, "B": 1, "C": 2, "D": 2}}
    s = _state(board=board, hands=hands, to_move=1)
    assert "D@3,3" in set(g.legal_moves(s))
    ns = g.apply_move(s, "D@3,3")
    assert ns.winner == 1, ns.winner
    assert g.is_terminal(ns)


def test_no_win_when_repeated_shape():
    """A full line with a repeated shape (not all 4 distinct) is NOT a win."""
    g = Quantik()
    # Row 0 = A,A,B,? ; placing C at (3,0) leaves shapes {A,B,C} -> no win.
    board = {(0, 0): (0, "A"), (1, 0): (1, "A"), (2, 0): (0, "B")}
    hands = {0: {"A": 0, "B": 1, "C": 2, "D": 2},
             1: {"A": 1, "B": 2, "C": 2, "D": 2}}
    s = _state(board=board, hands=hands, to_move=0)
    ns = g.apply_move(s, "C@3,0")
    assert ns.winner is None, ns.winner


def test_loss_on_no_legal_move():
    """Reaching a position where the player to move has no legal placement
    makes the player who just moved win."""
    g = Quantik()
    # Construct: player 1 to move, has only shape A left, and A is blocked on
    # every empty cell because player 0 (opponent) has A reaching all of them.
    # Empty cells: (3,0) and (3,3). Player 0 has A in row 0, col 3, and the
    # bottom-right zone, blocking A at both empties.
    board = {
        (0, 0): (0, "A"),   # blocks A in row 0 (covers (3,0)) and col 0
        (3, 1): (0, "A"),   # blocks A in col 3 (covers (3,0) and (3,3))
        (2, 3): (0, "A"),   # blocks A in bottom-right zone (covers (3,3))
        # fill remaining non-target cells so only (3,0),(3,3) are empty
        (1, 0): (1, "B"), (2, 0): (1, "C"),
        (0, 1): (1, "B"), (1, 1): (0, "C"), (2, 1): (1, "D"),
        (0, 2): (0, "B"), (1, 2): (1, "C"), (2, 2): (0, "D"), (3, 2): (1, "B"),
        (0, 3): (1, "C"), (1, 3): (0, "B"), (3, 3): None,  # placeholder removed below
    }
    del board[(3, 3)]  # keep (3,3) empty
    # Player 1 holds only A.
    hands = {0: {"A": 0, "B": 0, "C": 0, "D": 0},
             1: {"A": 1, "B": 0, "C": 0, "D": 0}}
    s = _state(board=board, hands=hands, to_move=1)
    # Sanity: empties are exactly (3,0) and (3,3).
    empties = [(c, r) for c in range(4) for r in range(4) if (c, r) not in s.board]
    assert set(empties) == {(3, 0), (3, 3)}, empties
    # Player 1's only shape A is blocked on both empties -> no legal move.
    assert g.legal_moves(s) == [], g.legal_moves(s)
    # is_terminal is False on the hand-built stuck state (winner set only in
    # apply_move). Reach it via apply_move: have player 0 make the move that
    # leaves player 1 stuck.
    # Build the pre-state: player 0 to move, about to place A at (3,1).
    pre_board = dict(board)
    del pre_board[(3, 1)]
    pre_hands = {0: {"A": 1, "B": 0, "C": 0, "D": 0},
                 1: {"A": 1, "B": 0, "C": 0, "D": 0}}
    pre = _state(board=pre_board, hands=pre_hands, to_move=0)
    # Placing A@3,1 must be legal for player 0 (no opponent A blocks it there).
    assert "A@3,1" in set(g.legal_moves(pre))
    ns = g.apply_move(pre, "A@3,1")
    # Now player 1 is stuck -> player 0 wins via loss-on-no-move.
    assert ns.winner == 0, ns.winner
    assert g.is_terminal(ns)


def test_serialize_roundtrip():
    g = Quantik()
    s = g.initial_state()
    s = g.apply_move(s, "A@0,0")
    s = g.apply_move(s, "B@1,1")
    s = g.apply_move(s, "C@2,2")
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert s2.board == s.board
    assert s2.hands == s.hands
    assert s2.to_move == s.to_move
    assert s2.winner == s.winner
    # Reserves reflect placements: player 0 placed A and C, player 1 placed B.
    assert s.hands[0] == {"A": 1, "B": 2, "C": 1, "D": 2}
    assert s.hands[1] == {"A": 2, "B": 1, "C": 2, "D": 2}


def test_random_playouts_terminate():
    import random
    g = Quantik()
    rng = random.Random(12345)
    for _ in range(300):
        s = g.initial_state()
        steps = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            assert moves, "non-terminal state with no moves"
            s = g.apply_move(s, rng.choice(moves))
            steps += 1
            assert steps <= 16, steps
        r = g.returns(s)
        assert r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0])


def run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"quantik selftest: {len(fns)} tests passed")


if __name__ == "__main__":
    run()
