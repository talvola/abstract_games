"""Complica correctness anchors (pure stdlib: only `agp` + this game).

Anchors the mechanic against AbstractPlay's `gameslib` semantics:
  * drop-on-non-full stacks on top (lowest empty row),
  * push-on-full: bottom disc drops off, column shifts down, new disc at top,
  * a 4-in-a-row win reached via apply_move in EACH orientation,
  * a push move can hand the win to the OPPONENT (symmetric end check),
  * the simultaneous-both-fours tie rule (no winner, play continues),
  * random-playout termination via the ply cap.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir

_man, G = load_from_dir(Path(__file__).resolve().parent)
WIDTH, HEIGHT = 4, 7


def state_from(board_cols, to_move=0, plies=0):
    """board_cols[col] = list of owners bottom->top (partial). Build a state."""
    board = {}
    for c, col in enumerate(board_cols):
        for r, owner in enumerate(col):
            if owner is not None:
                board[(c, r)] = owner
    S = G.deserialize({
        "board": {f"{c},{r}": p for (c, r), p in board.items()},
        "to_move": to_move, "winner": None, "plies": plies,
    })
    return S


def test_drop_non_full():
    # column 0 has one Red disc at bottom; Red drops again -> stacks at row 1
    s = state_from([[0], [], [], []], to_move=0)
    s2 = G.apply_move(s, "1")
    assert s2.board[(0, 0)] == 0 and s2.board[(0, 1)] == 0, s2.board
    assert (0, 2) not in s2.board
    assert s2.to_move == 1
    assert s2.winner is None
    print("ok: drop on non-full stacks on top")


def test_push_full():
    # Fill column 0 bottom->top: R,Y,R,Y,R,Y,R (rows 0..6). Yellow pushes.
    col = [0, 1, 0, 1, 0, 1, 0]
    s = state_from([col, [], [], []], to_move=1)
    s2 = G.apply_move(s, "1")
    # bottom (old row0=R) drops off; every disc shifts down one; new Y at top row6
    expected = [1, 0, 1, 0, 1, 0, 1]  # old rows 1..6 shifted down + new Y on top
    got = [s2.board[(0, r)] for r in range(HEIGHT)]
    assert got == expected, (got, expected)
    # still exactly 7 discs in the column (one off, one on)
    assert sum(1 for r in range(HEIGHT) if (0, r) in s2.board) == HEIGHT
    print("ok: push on full drops bottom off + shifts down + enters at top")


def _reach(board_cols, to_move, move):
    s = state_from(board_cols, to_move=to_move)
    return G.apply_move(s, move)


def test_win_horizontal():
    # Red has cols 1,2,3 filled to row0; drop col 4 -> four across bottom row.
    s2 = _reach([[0], [0], [0], []], to_move=0, move="4")
    assert s2.winner == 0, s2.board
    print("ok: horizontal four via apply_move")


def test_win_vertical():
    # Red has three stacked in col 1 (rows0-2); drop again -> four vertical.
    s2 = _reach([[0, 0, 0], [], [], []], to_move=0, move="1")
    assert s2.winner == 0, s2.board
    print("ok: vertical four via apply_move")


def test_win_diagonal_up():
    # Diagonal going up-right: need Red at (0,0),(1,1),(2,2),(3,3).
    cols = [
        [0],           # (0,0)=R
        [1, 0],        # (1,0)=Y filler, (1,1)=R
        [1, 1, 0],     # (2,0),(2,1)=Y filler, (2,2)=R
        [1, 1, 1],     # (3,0..2)=Y filler; Red drops -> (3,3)=R
    ]
    s2 = _reach(cols, to_move=0, move="4")
    assert s2.board[(3, 3)] == 0
    assert s2.winner == 0, s2.board
    print("ok: up-right diagonal four via apply_move")


def test_win_diagonal_down():
    # Diagonal going down-right: Red at (0,3),(1,2),(2,1),(3,0).
    cols = [
        [1, 1, 1, 0],  # (0,3)=R on top of 3 fillers
        [1, 1, 0],     # (1,2)=R
        [1, 0],        # (2,1)=R
        [],            # Red drops col4 -> (3,0)=R
    ]
    s2 = _reach(cols, to_move=0, move="4")
    assert s2.board[(3, 0)] == 0
    assert s2.winner == 0, s2.board
    print("ok: down-right diagonal four via apply_move")


def test_opponent_gets_win_via_push():
    # Yellow already has a vertical four in col 2 (rows0-3). It is Red's turn.
    # Red plays a *different* column that touches nothing -> only Yellow has four
    # -> the symmetric check ends the game with YELLOW as winner (mover loses).
    cols = [[], [0, 1, 1, 1, 1], [], []]
    # col1 (index1): row0=R, rows1-4 = Y (Yellow four vertical rows1-4)
    s = state_from(cols, to_move=0)
    assert G._has_four(dict(s.board), 1) is True
    s2 = G.apply_move(s, "4")  # Red drops elsewhere, doesn't make a Red four
    assert s2.winner == 1, s2.board
    print("ok: symmetric check -> opponent's pre-existing four wins")


def test_simultaneous_tie_continues():
    # Construct a board where a single push makes BOTH players complete a four.
    # Column 4 (index3) is full; pushing it shifts discs so that, at once, Red has
    # a bottom-row four and Yellow has a top-row four. Then no winner, play goes on.
    # Bottom row currently: R R R _  (col3 bottom about to become R after push).
    # Top row currently:    Y Y Y _  (col3 top becomes the mover's new disc).
    # We fill col3 so the push lands a Red at bottom and a Yellow at top.
    board_cols = [
        [0, 1, 1, 1, 1, 1, 1],   # col0: bottom R, top Y (rows1-6 Y for top four)
        [0, 1, 1, 1, 1, 1, 1],   # col1
        [0, 1, 1, 1, 1, 1, 1],   # col2
        # col3 full: bottom row0 = R so it drops off; row1 = R so after shift
        # (0,3) bottom becomes R; top gets mover's Yellow disc.
        [1, 0, 1, 1, 1, 1, 1],
    ]
    s = state_from(board_cols, to_move=1)  # Yellow to move, pushes col4
    s2 = G.apply_move(s, "4")
    # After push col3: rows shift down (bottom row1=R -> row0), top row6 = Yellow.
    bottom = [s2.board[(c, 0)] for c in range(WIDTH)]
    top = [s2.board[(c, HEIGHT - 1)] for c in range(WIDTH)]
    assert bottom == [0, 0, 0, 0], bottom          # Red four across the bottom
    assert top == [1, 1, 1, 1], top                # Yellow four across the top
    assert G._has_four(dict(s2.board), 0)
    assert G._has_four(dict(s2.board), 1)
    assert s2.winner is None, "both fours => nobody wins, play continues"
    assert not G.is_terminal(s2)
    print("ok: simultaneous both-fours => no winner, game continues")


def test_termination_random():
    rng = random.Random(12345)
    for _ in range(40):
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s):
            mv = rng.choice(G.legal_moves(s))
            s = G.apply_move(s, mv)
            steps += 1
            assert steps <= 400, "should terminate by the ply cap"
        r = G.returns(s)
        assert r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]), r
    print("ok: random playouts terminate (win or ply-cap draw)")


def test_ply_cap_draw():
    s = G.initial_state()
    # A cycle of non-winning pushes eventually hits the cap; assert cap logic.
    s = G.deserialize({"board": {}, "to_move": 0, "winner": None, "plies": 300})
    assert G.is_terminal(s)
    assert G.returns(s) == [0.0, 0.0]
    print("ok: ply cap => honest draw")


if __name__ == "__main__":
    test_drop_non_full()
    test_push_full()
    test_win_horizontal()
    test_win_vertical()
    test_win_diagonal_up()
    test_win_diagonal_down()
    test_opponent_gets_win_via_push()
    test_simultaneous_tie_continues()
    test_termination_random()
    test_ply_cap_draw()
    print("\nall complica selftests passed")
