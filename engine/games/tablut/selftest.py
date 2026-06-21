"""Standalone correctness anchor for Tablut.

Run from engine/:  PYTHONPATH=. python3 games/tablut/selftest.py

Asserts:
  * conformance: random games always terminate with well-formed returns;
  * a custodial capture of an attacker soldier;
  * the King captured by being surrounded on all four sides;
  * the King escaping to an edge square to win.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import random
import sys

from games.tablut.game import (
    Tablut, TaflState, ATTACKERS, DEFENDERS, THRONE, N, PLY_CAP,
)

G = Tablut()


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def roundtrip(s: TaflState):
    """serialize must round-trip identically and stay JSON-able."""
    import json
    d = G.serialize(s)
    json.dumps(d)
    d2 = G.serialize(G.deserialize(d))
    if d != d2:
        fail(f"serialize round-trip mismatch: {d} != {d2}")


# ---------------------------------------------------------------- conformance
def test_conformance(n_games: int = 200):
    rng = random.Random(12345)
    saw_atk_win = saw_def_win = 0
    for g in range(n_games):
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s):
            roundtrip(s)
            moves = G.legal_moves(s)
            if not moves:
                fail("empty legal_moves on a non-terminal state")
            s = G.apply_move(s, rng.choice(moves))
            steps += 1
            if steps > PLY_CAP + 5:
                fail("game ran past the ply cap without terminating")
        ret = G.returns(s)
        if len(ret) != 2 or any(x != x or abs(x) == float("inf") for x in ret):
            fail(f"ill-formed returns {ret}")
        if ret[0] > 0:
            saw_atk_win += 1
        elif ret[1] > 0:
            saw_def_win += 1
    if saw_atk_win == 0 or saw_def_win == 0:
        fail(f"expected both sides to win across random games "
             f"(atk={saw_atk_win}, def={saw_def_win})")
    print(f"  conformance: {n_games} random games terminated "
          f"(atk wins={saw_atk_win}, def wins={saw_def_win}).")


# -------------------------------------------------- custodial capture of attacker
def test_capture_attacker():
    # An attacker 'A' at (4,0). A defender already flanks from one side at (3,0);
    # the defender at (5,1) moves to (5,0) to complete the sandwich along the row,
    # so the attacker at (4,0) is captured between (3,0) and (5,0).
    board = {
        (3, 0): "D",
        (4, 0): "A",
        (5, 1): "D",
        THRONE: "K",
    }
    s = TaflState(board=board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "5,1>5,0")
    if (4, 0) in s2.board:
        fail("attacker should have been custodially captured at (4,0)")
    if s2.board.get((5, 0)) != "D" or s2.board.get((3, 0)) != "D":
        fail("flanking defenders not where expected after capture")
    print("  custodial capture of an attacker soldier: OK")

    # Active-capture negative: a defender moving BETWEEN two attackers is safe.
    board2 = {
        (3, 0): "A",
        (5, 0): "A",
        (4, 2): "D",
        THRONE: "K",
    }
    s3 = TaflState(board=board2, to_move=DEFENDERS)
    s4 = G.apply_move(s3, "4,2>4,0")
    if (4, 0) not in s4.board:
        fail("a piece moving between two enemies must be safe (no suicide capture)")
    print("  moving between two enemies is safe: OK")

    # The King helps capture: an attacker sandwiched between the King and a
    # moving defender is removed (Cyningstan / common Tablut rule).
    board3 = {(2, 2): "K", (2, 3): "A", (2, 8): "D", (8, 8): "A"}
    s5 = TaflState(board=board3, to_move=DEFENDERS)
    s6 = G.apply_move(s5, "2,8>2,4")
    if (2, 3) in s6.board:
        fail("the King must pair with a defender to capture an attacker")
    print("  King pairs with a defender to capture: OK")


# --------------------------------------------------- king surrounded -> capture
def test_king_surrounded():
    # King at (2,2) with attackers on three sides; the fourth attacker slides in.
    board = {
        (2, 1): "A",   # above
        (2, 3): "A",   # below
        (1, 2): "A",   # left
        (3, 5): "A",   # will slide to (3,2) on the right
        (2, 2): "K",
    }
    s = TaflState(board=board, to_move=ATTACKERS)
    # Before the closing move the king must NOT be considered captured.
    if G.is_terminal(s):
        fail("king with an open side should not yet be terminal")
    s2 = G.apply_move(s, "3,5>3,2")
    if s2.winner != ATTACKERS:
        fail(f"king should be captured (surrounded on 4 sides); winner={s2.winner}")
    if not G.is_terminal(s2):
        fail("state after king surround should be terminal")
    print("  king captured by four-side surround: OK")

    # Capture aided by the empty throne: king beside the throne, attackers on the
    # other three sides; the empty throne acts as the fourth wall.
    board_t = {
        (5, 4): "K",   # king orthogonally adjacent to the throne at (4,4)
        (5, 3): "A",   # above
        (5, 5): "A",   # below
        (6, 7): "A",   # slides to (6,4) on the right
    }
    s3 = TaflState(board=board_t, to_move=ATTACKERS)
    s4 = G.apply_move(s3, "6,7>6,4")
    if s4.winner != ATTACKERS:
        fail(f"king should be captured using the empty throne as a wall; winner={s4.winner}")
    print("  king captured using the empty throne as a wall: OK")


# ----------------------------------------------------- king escapes to the edge
def test_king_escape():
    # King at (4,1); a clear file to the top edge (4,0).
    board = {(4, 1): "K"}
    s = TaflState(board=board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "4,1>4,0")
    if s2.winner != DEFENDERS:
        fail(f"king reaching an edge must win for defenders; winner={s2.winner}")
    if not G.is_terminal(s2):
        fail("state after king escape should be terminal")
    print("  king escapes to an edge to win: OK")

    # Sanity: the king on (4,1) is NOT already a win one step before the edge.
    s_pre = TaflState(board={(4, 2): "K"}, to_move=DEFENDERS)
    if G.is_terminal(s_pre):
        fail("king not yet on an edge should not be terminal")


def main():
    test_conformance()
    test_capture_attacker()
    test_king_surrounded()
    test_king_escape()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
