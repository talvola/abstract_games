"""Standalone correctness anchor for Progressive Chess (pure stdlib + agp).

Asserts the progressive turn structure and the Italian check rules rather than
perft:

  * the series lengths 1, 2, 3, ... and when ``to_move`` flips;
  * "a check may be given only on the LAST move of the series";
  * "a check must be escaped on the FIRST move";
  * a progressive checkmate reached by construction (right winner);
  * a checkmate delivered via ``apply_move`` (right winner);
  * serialize/deserialize round-trips ``moves_left`` / ``turn_no``;
  * a batch of random games terminate and never strand a non-terminal state
    without a legal move.

Run:  PYTHONPATH=. python3 games/progressive_chess/selftest.py
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.chesslike import WHITE, BLACK  # noqa: E402
from games.progressive_chess.game import ProgressiveChess, PState  # noqa: E402

G = ProgressiveChess()


def st(board, to_move, moves_left, turn_no, ep=None):
    """A hand-built state (no castling rights, fresh rep table)."""
    s = PState(board=dict(board), to_move=to_move, castling=frozenset(), ep=ep,
               moves_left=moves_left, turn_no=turn_no)
    s.reps = {G._poskey_state(s): 1}
    return s


def test_progression():
    s = G.initial_state()
    assert s.to_move == WHITE and s.moves_left == 1 and s.turn_no == 1

    # turn 1: exactly ONE white move, then it flips to Black with a 2-move series.
    s = G.apply_move(s, G.legal_moves(s)[0])
    assert s.to_move == BLACK and s.moves_left == 2 and s.turn_no == 2

    # turn 2: two black moves -- Black stays to move after the 1st, flips after 2nd.
    s = G.apply_move(s, G.legal_moves(s)[0])
    assert s.to_move == BLACK and s.moves_left == 1 and s.turn_no == 2
    s = G.apply_move(s, G.legal_moves(s)[0])
    assert s.to_move == WHITE and s.moves_left == 3 and s.turn_no == 3

    # turn 3: three white moves, then flip to Black with a 4-move series.
    for _ in range(3):
        assert s.to_move == WHITE
        s = G.apply_move(s, G.legal_moves(s)[0])
    assert s.to_move == BLACK and s.moves_left == 4 and s.turn_no == 4
    print("  progression 1,2,3,4 ok")


def test_check_only_on_last_move():
    # White Ra5 (0,4) can go to e5 (4,4) giving check to the Black king e8 (4,7).
    board = {(7, 0): (WHITE, "K"), (0, 4): (WHITE, "R"), (4, 7): (BLACK, "K")}
    checking = "0,4>4,4"

    # As the FIRST move of a 2-move series (non-final) the check is ILLEGAL.
    s2 = st(board, WHITE, moves_left=2, turn_no=2)
    assert checking not in G.legal_moves(s2), "check must be illegal on a non-final move"

    # As a single-move series (last move) the same check is LEGAL.
    s1 = st(board, WHITE, moves_left=1, turn_no=1)
    assert checking in G.legal_moves(s1), "check must be legal on the last move"
    print("  check only on last move ok")


def test_escape_on_first_move():
    # White king e4 (4,3) in check from a Black rook e8 (4,7); safe flights exist.
    board = {(4, 3): (WHITE, "K"), (4, 7): (BLACK, "R"), (0, 0): (BLACK, "K")}
    s = st(board, WHITE, moves_left=3, turn_no=3)
    assert G.in_check(s.board, WHITE)
    lm = G.legal_moves(s)
    assert lm, "there must be an escape"
    for mv in lm:
        f, t = mv.split(">")
        nb = G._board_after_move(s, tuple(int(x) for x in f.split(",")),
                                 tuple(int(x) for x in t.split(",")), None)
        assert not G.in_check(nb, WHITE), "every legal first move must escape check"
    print("  escape on first move ok")


def test_progressive_checkmate():
    # White Kh1 (7,0) is checked by the Black Rh4 (7,3).  The ONLY way out is
    # Be1xh4 (4,0)->(7,3), but that bishop then checks the Black Kd8 (3,7) along
    # the long diagonal -- illegal on a non-final move.  King flights g1/g2 are
    # covered by the Black Rg8 (6,7).  => no legal first move => progressive mate.
    board = {
        (7, 0): (WHITE, "K"),   # h1
        (4, 0): (WHITE, "B"),   # e1
        (7, 3): (BLACK, "R"),   # h4  (checks the white king)
        (6, 7): (BLACK, "R"),   # g8  (covers g1, g2)
        (3, 7): (BLACK, "K"),   # d8
    }
    escape = "4,0>7,3"          # Be1xh4 (removes the check but gives check)

    # First move of a >=2 series: no legal move -> checkmate, White (mover) loses.
    s = st(board, WHITE, moves_left=3, turn_no=3)
    assert G.in_check(s.board, WHITE)
    assert G.legal_moves(s) == [], "progressive checkmate: no legal first move"
    assert G.is_terminal(s)
    assert G.returns(s) == [-1.0, 1.0], "White (to move, mated) must lose"

    # But as the LAST move of a series the very same capture is legal (check ok).
    s_last = st(board, WHITE, moves_left=1, turn_no=3)
    assert escape in G.legal_moves(s_last)
    assert not G.is_terminal(s_last)
    print("  progressive checkmate ok")


def test_mate_via_apply_move():
    # White to deliver mate on the last move: Rd1->d8 mates the boxed-in Black king.
    board = {
        (0, 7): (BLACK, "K"), (0, 6): (BLACK, "P"), (1, 6): (BLACK, "P"),  # a8,a7,b7
        (3, 0): (WHITE, "R"),   # d1
        (7, 0): (WHITE, "K"),   # h1
    }
    s = st(board, WHITE, moves_left=1, turn_no=1)
    assert "3,0>3,7" in G.legal_moves(s)
    s2 = G.apply_move(s, "3,0>3,7")
    assert s2.to_move == BLACK and s2.moves_left == 2 and s2.turn_no == 2
    assert G.in_check(s2.board, BLACK)
    assert G.is_terminal(s2), "Black should be checkmated"
    assert G.returns(s2) == [1.0, -1.0], "Black must lose"
    print("  mate via apply_move ok")


def test_stalemate_is_draw():
    # Black to move, not in check, but no legal move -> progressive stalemate (draw).
    # Black Kh8 (7,7); White Qf7 (5,6) covers g8/g7/h7; White Kf6 (5,5).
    board = {(7, 7): (BLACK, "K"), (5, 6): (WHITE, "Q"), (5, 5): (WHITE, "K")}
    s = st(board, BLACK, moves_left=2, turn_no=2)
    assert not G.in_check(s.board, BLACK)
    assert G.legal_moves(s) == []
    assert G.is_terminal(s)
    assert G.returns(s) == [0.0, 0.0], "stalemate is a draw"
    print("  stalemate is a draw ok")


def test_serialize_roundtrip():
    s = G.initial_state()
    s = G.apply_move(s, G.legal_moves(s)[0])   # moves_left=2, turn_no=2
    d = G.serialize(s)
    r = G.deserialize(d)
    assert r.moves_left == s.moves_left == 2
    assert r.turn_no == s.turn_no == 2
    assert r.to_move == s.to_move
    assert r.board == s.board
    assert G._poskey_state(r) == G._poskey_state(s)
    print("  serialize round-trip ok")


def test_random_games_terminate():
    for seed in range(8):
        rng = random.Random(seed)
        s = G.initial_state(rng=rng)
        for _ in range(20000):
            if G.is_terminal(s):
                break
            lm = G.legal_moves(s)
            assert lm, "non-terminal state with no legal move (should be pass/terminal)"
            s = G.apply_move(s, rng.choice(lm))
        assert G.is_terminal(s), f"game (seed {seed}) did not terminate"
    print("  random games terminate ok")


def main():
    test_progression()
    test_check_only_on_last_move()
    test_escape_on_first_move()
    test_progressive_checkmate()
    test_mate_via_apply_move()
    test_stalemate_is_draw()
    test_serialize_roundtrip()
    test_random_games_terminate()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
