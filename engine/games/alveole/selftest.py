"""Alvéole self-test — pure stdlib (imports only agp + this game).

Anchors:
  * the exact 9-piece opening layout (counts, on-board, disjoint, corner split);
  * line-count movement on constructed positions:
      - jump over a friendly piece,
      - blocked by an enemy in the path,
      - capture on landing;
  * the connected-group win reached via apply_move (a genuine win + a non-win);
  * termination (a random playout reaches a terminal state with zero-sum return).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from games.alveole.game import (  # noqa: E402
    Alveole, AlveoleState, _cell_set, _start_board, SIZE, PLY_CAP,
)

G = Alveole()
CELLS = _cell_set(SIZE)
CORNERS = {(4, 0), (0, 4), (-4, 4), (-4, 0), (0, -4), (4, -4)}


def _st(board, to_move=0, ply=0):
    return AlveoleState(board=dict(board), to_move=to_move, ply=ply)


# --- 1. opening layout --------------------------------------------------------
def test_setup():
    b = _start_board()
    red = {c for c, p in b.items() if p == 0}
    blue = {c for c, p in b.items() if p == 1}
    assert len(red) == 9, len(red)
    assert len(blue) == 9, len(blue)
    assert red.isdisjoint(blue)
    assert red | blue <= CELLS, "some start cell off-board"
    assert len(CELLS) == 61, len(CELLS)
    # 3 alternating corners each; together they cover all 6 corners.
    assert red & CORNERS == {(4, 0), (0, -4), (-4, 4)}, red & CORNERS
    assert blue & CORNERS == {(-4, 0), (4, -4), (0, 4)}, blue & CORNERS
    assert (red | blue) & CORNERS == CORNERS
    # initial_state matches, Red to move, not terminal.
    s = G.initial_state()
    assert s.board == b and s.to_move == 0
    assert not G.is_terminal(s)
    print("ok setup: 61 cells, 9+9 pieces, corners split 3/3")


# --- 2. line-count movement ---------------------------------------------------
def test_basic_distance():
    # two friendly pieces on vertical line q=0 -> count 2 -> move exactly 2.
    s = _st({(0, 0): 0, (0, 2): 0})
    mv = set(G._raw_moves(s))
    assert "0,0>0,-2" in mv, mv          # 2 cells the empty way
    assert "0,2>0,4" in mv, mv
    assert "0,0>0,2" not in mv           # can't land on a friendly
    print("ok distance = line count (2 pieces -> 2 cells)")


def test_jump_friendly():
    # friendly directly ahead is jumped over; land on the empty cell beyond.
    s = _st({(0, 0): 0, (0, 1): 0})      # count on q=0 line = 2
    mv = set(G._raw_moves(s))
    assert "0,0>0,2" in mv, mv           # jumps over friendly (0,1)
    print("ok jump over a friendly piece")


def test_blocked_by_enemy():
    # an enemy in the path blocks; the clear direction stays legal.
    s = _st({(0, 0): 0, (0, 1): 1})      # count = 2, enemy at distance 1
    mv = set(G._raw_moves(s))
    assert "0,0>0,2" not in mv, mv       # cannot jump the enemy
    assert "0,0>0,-2" in mv, mv          # other way is clear
    print("ok blocked by an enemy in the path")


def test_capture_on_landing():
    s = _st({(0, 0): 0, (4, 0): 0, (0, 2): 1, (-4, 0): 1, (-4, 2): 1})
    mv = set(G._raw_moves(s))
    assert "0,0>0,2" in mv, mv           # land on enemy at distance 2 = capture
    ns = G.apply_move(s, "0,0>0,2")
    assert ns.board.get((0, 2)) == 0     # mover now sits there
    assert (0, 0) not in ns.board
    assert sum(1 for p in ns.board.values() if p == 1) == 2  # one enemy removed
    assert ns.winner is None             # neither side connected
    print("ok capture removes the enemy on landing")


# --- 3. connected-group win / non-win -----------------------------------------
def test_win_by_connection():
    # Red: (0,0)-(0,1) already adjacent + stray (3,0). Row r=0 has (0,0),(3,0)
    # -> count 2 -> (3,0) slides 2 to (1,0), adjacent to (0,0): all connected.
    board = {(0, 0): 0, (0, 1): 0, (3, 0): 0,
             (-4, 1): 1, (-4, 3): 1, (-3, -1): 1}  # blue: 3 non-adjacent pieces
    s = _st(board, to_move=0)
    assert "3,0>1,0" in set(G._raw_moves(s)), G._raw_moves(s)
    ns = G.apply_move(s, "3,0>1,0")
    assert ns.winner == 0, ns.winner
    assert G.is_terminal(ns)
    assert G.returns(ns) == [1.0, -1.0]
    print("ok win by uniting all pieces into one group")


def test_non_win_move():
    board = {(0, 0): 0, (0, 1): 0, (3, 0): 0,
             (-4, 1): 1, (-4, 3): 1, (-3, -1): 1}
    s = _st(board, to_move=0)
    # move that leaves pieces scattered: (0,1) -> (0,3)
    assert "0,1>0,3" in set(G._raw_moves(s))
    ns = G.apply_move(s, "0,1>0,3")
    assert ns.winner is None, ns.winner   # not connected -> no win
    print("ok a non-connecting move does not win")


def test_simultaneous_is_mover_win():
    # Mover completes its group on a board where the opponent is already a single
    # connected group -> mover still wins (simultaneous connection = mover win).
    board = {(0, 0): 0, (0, 1): 0, (3, 0): 0,
             (-4, 0): 1, (-4, 1): 1}       # blue already connected (adjacent)
    s = _st(board, to_move=0)
    ns = G.apply_move(s, "3,0>1,0")
    assert ns.winner == 0, ns.winner
    print("ok simultaneous connection is a win for the mover")


# --- 4. termination -----------------------------------------------------------
def test_termination():
    rng = random.Random(12345)
    for _ in range(30):
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s) and steps <= PLY_CAP + 5:
            mv = G.legal_moves(s)
            assert mv, "no moves but not terminal"
            s = G.apply_move(s, rng.choice(mv))
            steps += 1
        assert G.is_terminal(s), "did not terminate within the ply cap"
        r = G.returns(s)
        assert abs(r[0] + r[1]) < 1e-9, r   # zero-sum
    print("ok random playouts always terminate (zero-sum)")


if __name__ == "__main__":
    test_setup()
    test_basic_distance()
    test_jump_friendly()
    test_blocked_by_enemy()
    test_capture_on_landing()
    test_win_by_connection()
    test_non_win_move()
    test_simultaneous_is_mover_win()
    test_termination()
    print("all alveole selftests passed")
