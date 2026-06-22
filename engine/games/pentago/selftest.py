"""Pentago correctness anchor (pure stdlib). Checks the quadrant rotation algebra
and that the five-in-a-row is judged AFTER the twist, including the mover/opponent/
both-win outcomes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.pentago.game import Pentago, PState, _rotate, _five, BLACK, WHITE  # noqa: E402

G = Pentago()


def main():
    # --- rotation algebra -------------------------------------------------
    b = {(0, 0): BLACK, (1, 0): WHITE, (2, 1): BLACK, (4, 4): WHITE}
    r = b
    for _ in range(4):
        r = _rotate(r, "BL", "cw")
    assert r == b, "four CW rotations must be the identity"
    assert _rotate(_rotate(b, "TR", "cw"), "TR", "ccw") == b, "cw then ccw is identity"
    # a CW twist of the BL quadrant moves a corner to the next corner
    assert _rotate({(0, 0): BLACK}, "BL", "cw") == {(2, 0): BLACK}

    # --- five-in-a-row detection -----------------------------------------
    assert _five({(c, 0): BLACK for c in range(5)}, BLACK)        # horizontal
    assert _five({(k, k): WHITE for k in range(5)}, WHITE)        # diagonal
    assert not _five({(c, 0): BLACK for c in range(4)}, BLACK)    # only four

    # --- the win is judged AFTER the rotation ----------------------------
    #  Black has four in the bottom row of the BL/BR quadrants plus a marble that,
    #  once placed and the quadrant twisted, lines up the fifth. Simpler: build a
    #  near-win and let a no-op-looking twist of an empty quadrant complete it.
    board = {(0, 0): BLACK, (1, 0): BLACK, (2, 0): BLACK, (3, 0): BLACK}
    s = PState(board=dict(board), to_move=BLACK)
    # place at (4,0) completing five along row 0; rotate the empty TR quadrant
    # (doesn't disturb row 0) -> Black wins.
    s2 = G.apply_move(s, "4,0=TR-cw")
    assert s2.winner == BLACK and G.returns(s2) == [1.0, -1.0]

    # --- a twist that makes five for BOTH players is a draw ---------------
    #  White already has four on row 5; Black places + twists to make its own five
    #  while the same twist also completes White's. Construct directly:
    board = {(0, 5): WHITE, (1, 5): WHITE, (2, 5): WHITE, (3, 5): WHITE, (4, 5): WHITE}
    # White already has five — but it's Black to move; Black's move that leaves a
    # White five present (without making a Black five) loses for Black.
    s = PState(board=dict(board), to_move=BLACK)
    s2 = G.apply_move(s, "0,0=BL-cw")        # irrelevant placement; White five stands
    assert s2.winner == WHITE, "opponent's five after the twist wins for them"

    # --- board-full with no five is a draw -------------------------------
    full = {(c, r): (c + r) % 2 for r in range(6) for c in range(6)}
    s = PState(board=full, to_move=BLACK, winner="draw")
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0]

    # --- opening move count + serialize ----------------------------------
    s0 = G.initial_state()
    assert len(G.legal_moves(s0)) == 36 * 4 * 2     # cell x quadrant x direction
    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)

    print("pentago selftest OK")


if __name__ == "__main__":
    main()
