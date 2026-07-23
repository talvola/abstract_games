"""Standalone correctness anchor for Super Halma (pure stdlib: agp + this game).

Asserts:
  (a) the frozen initial legal-move count from the start position (40);
  (b) hand-checked long-range symmetric jumps (mirror landing, first-occupied
      only, blocking on both sides, chaining);
  (c) a win REACHED via apply_move (fill the last enemy-camp square), plus the
      squatter guard (an enemy piece in the target camp cannot deny the win).
"""

from pathlib import Path

from agp.loader import load_from_dir
from games.super_halma.game import SuperHalmaState, _camp0, _camp1

HERE = Path(__file__).resolve().parent


def load():
    _, g = load_from_dir(HERE)
    return g


def test_setup_and_initial_count():
    g = load()
    s = g.initial_state()
    assert len(s.board) == 38, len(s.board)
    assert sum(1 for v in s.board.values() if v == 0) == 19
    assert sum(1 for v in s.board.values() if v == 1) == 19
    # camps: 180-degree symmetric staircase of 19 (per-row 5,5,4,3,2).
    assert len(_camp0()) == 19 and len(_camp1()) == 19
    assert _camp1() == {(9 - c, 9 - r) for (c, r) in _camp0()}
    # FROZEN initial legal-move count: 21 steps + 19 jumps = 40.
    lm = g.legal_moves(s)
    assert len(lm) == 40, len(lm)


def test_long_range_jump():
    g = load()
    # Mirror jump: mover (0,5), piece 3 cells east at (3,5) with 2 empties
    # between; land 2 empties beyond at (6,5).
    s = SuperHalmaState(board={(0, 5): 0, (3, 5): 1}, to_move=0)
    assert "0,5>6,5" in g.legal_moves(s)
    # k = 0 diagonal adjacent jump.
    s2 = SuperHalmaState(board={(0, 0): 0, (1, 1): 1}, to_move=0)
    assert "0,0>2,2" in g.legal_moves(s2)
    # landing occupied -> no jump.
    s3 = SuperHalmaState(board={(0, 5): 0, (3, 5): 1, (6, 5): 1}, to_move=0)
    assert "0,5>6,5" not in g.legal_moves(s3)
    # a far-side intervening square occupied -> no jump.
    s4 = SuperHalmaState(board={(0, 5): 0, (3, 5): 1, (5, 5): 0}, to_move=0)
    assert "0,5>6,5" not in g.legal_moves(s4)
    # only the FIRST occupied square is jumpable; a piece behind it is not.
    s5 = SuperHalmaState(board={(0, 5): 0, (1, 5): 1, (2, 5): 1}, to_move=0)
    east = [m for m in g.legal_moves(s5) if m.startswith("0,5>") and m.endswith(",5")]
    assert east == [], east
    # chained jumps reach BOTH stopping points as 2-cell endpoint moves:
    # (0,0) over (1,0) to (2,0), then over (3,0) on to (4,0).
    s6 = SuperHalmaState(board={(0, 0): 0, (1, 0): 1, (3, 0): 1}, to_move=0)
    chain = g.legal_moves(s6)
    assert "0,0>2,0" in chain and "0,0>4,0" in chain


def test_win_via_apply():
    g = load()
    target = _camp1()  # player 0's goal
    empty = (8, 5)     # leave one edge camp cell empty (has an outside neighbour)
    board = {sq: 0 for sq in target if sq != empty}
    board[(7, 4)] = 0  # an own piece outside the camp, adjacent to the empty cell
    board[(0, 0)] = 1  # player 1 must have a piece somewhere
    s = SuperHalmaState(board=board, to_move=0)
    assert s.winner is None
    s2 = g.apply_move(s, "7,4>8,5")   # step in to complete the camp
    assert s2.winner == 0, s2.winner
    assert g.is_terminal(s2)
    assert g.returns(s2) == [1.0, -1.0]


def test_squatter_guard():
    g = load()
    target = _camp1()
    empty = (8, 5)
    squat = (9, 9)                    # an enemy piece parked in the target camp
    board = {sq: 0 for sq in target if sq not in (empty, squat)}
    board[squat] = 1                  # enemy squatter
    board[(7, 4)] = 0                 # own piece to fill the last cell
    s = SuperHalmaState(board=board, to_move=0)
    s2 = g.apply_move(s, "7,4>8,5")
    # camp is entirely occupied and >=1 occupant is player 0's -> win stands.
    assert s2.winner == 0, s2.winner


if __name__ == "__main__":
    test_setup_and_initial_count()
    test_long_range_jump()
    test_win_via_apply()
    test_squatter_guard()
    print("super_halma selftest: all tests passed")
