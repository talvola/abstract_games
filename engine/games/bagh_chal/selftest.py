"""Bagh-Chal correctness anchor (pure stdlib). Checks the alquerque topology,
goat placement flow, tiger step + line-jump capture (orthogonal and diagonal),
the two win conditions (5 captures / all tigers trapped), and serialize."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.bagh_chal.game import (  # noqa: E402
    BaghChal, BState, ADJ, GOAT, TIGER, CORNERS,
)

G = BaghChal()


def main():
    # --- topology: strong points carry diagonals, weak points don't -------
    assert (1, 1) in ADJ[(0, 0)], "strong corner missing its diagonal"
    # (1,0) is weak: its diagonal neighbours (0,1)/(2,1) must NOT be connected
    assert (0, 1) not in ADJ[(1, 0)] and (2, 1) not in ADJ[(1, 0)], "weak point has a diagonal"
    assert ADJ[(1, 0)] == frozenset({(0, 0), (2, 0), (1, 1)}), "weak point ortho-only"
    assert ADJ[(2, 2)] == frozenset({(1, 2), (3, 2), (2, 1), (2, 3),
                                     (1, 1), (3, 3), (1, 3), (3, 1)}), "centre degree 8"
    for p in ADJ:                                # adjacency symmetric
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"

    # --- initial position --------------------------------------------------
    s = G.initial_state()
    assert all(s.board[c] == TIGER for c in CORNERS) and len(s.board) == 4
    assert s.in_hand == 20 and s.to_move == GOAT
    assert len(G.legal_moves(s)) == 25 - 4      # any empty point is a placement

    # --- placement decrements hand and passes the turn --------------------
    s2 = G.apply_move(s, "2,2")
    assert s2.board[(2, 2)] == GOAT and s2.in_hand == 19 and s2.to_move == TIGER

    # --- tiger orthogonal jump captures -----------------------------------
    b = {(1, 0): TIGER, (2, 0): GOAT}            # land (3,0) empty
    st = BState(board=dict(b), to_move=TIGER, in_hand=0)
    assert "1,0>3,0" in G.legal_moves(st)
    st2 = G.apply_move(st, "1,0>3,0")
    assert (2, 0) not in st2.board and st2.captured == 1 and st2.board[(3, 0)] == TIGER

    # --- tiger diagonal jump only from a strong point ---------------------
    b = {(0, 0): TIGER, (1, 1): GOAT}            # (0,0) strong, land (2,2) empty
    st = BState(board=dict(b), to_move=TIGER, in_hand=0)
    assert "0,0>2,2" in G.legal_moves(st), "diagonal jump from strong point missing"
    # a tiger on a weak point has no diagonal jump
    b = {(1, 0): TIGER, (2, 1): GOAT}            # (1,0) weak -> no (1,0)->(3,2)
    st = BState(board=dict(b), to_move=TIGER, in_hand=0)
    assert "1,0>3,2" not in G.legal_moves(st)

    # --- tigers win at five captures --------------------------------------
    st = BState(board={(1, 0): TIGER, (2, 0): GOAT}, to_move=TIGER,
                in_hand=0, captured=4)
    st2 = G.apply_move(st, "1,0>3,0")           # 5th capture
    assert st2.winner == TIGER and G.returns(st2) == [-1.0, 1.0]

    # --- goats win by trapping all tigers ---------------------------------
    #  Corner tiger (0,0) boxed: goats on its three neighbours (1,0),(0,1),(1,1)
    #  AND on the squares behind them (2,0),(0,2),(2,2) so no jump escapes.
    board = {(0, 0): TIGER,
             (1, 0): GOAT, (0, 1): GOAT, (1, 1): GOAT,
             (2, 0): GOAT, (0, 2): GOAT, (2, 2): GOAT}
    st = BState(board=board, to_move=TIGER, in_hand=0, captured=0)
    assert G.legal_moves(st) == [], "tiger should be trapped (steps + jumps blocked)"
    # reaching this as a real position sets the winner via _settle:
    st_goat = BState(board=dict(board), to_move=TIGER, in_hand=0)
    G._settle(st_goat)
    assert st_goat.winner == GOAT, "trapped tigers -> goats win"

    # --- serialize round-trips --------------------------------------------
    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)

    print("bagh_chal selftest OK")


if __name__ == "__main__":
    main()
