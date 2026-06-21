"""Standalone correctness anchor for Ard Ri.

Run from engine/:  PYTHONPATH=. python3 games/ard_ri/selftest.py

Pure-stdlib, fast (a few seconds). Asserts:
  * conformance: random games always terminate with well-formed returns, and
    both sides win at least once across the sample;
  * a custodial capture of an attacker man (and the active-capture safety rule);
  * the King assisting a custodial capture;
  * the King captured by four-side surround (open-board case);
  * the King captured using the empty throne as the fourth wall;
  * the King escaping to an edge square to win (and corners count as edges);
  * a not-yet-terminal sanity check one step before escape.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import random
import sys

from games.ard_ri.game import (
    ArdRi, TaflState, ATTACKERS, DEFENDERS, THRONE, N, PLY_CAP,
)

G = ArdRi()


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def roundtrip(s: TaflState):
    d = G.serialize(s)
    json.dumps(d)
    d2 = G.serialize(G.deserialize(d))
    if d != d2:
        fail(f"serialize round-trip mismatch: {d} != {d2}")


# -------------------------------------------------------------- setup sanity
def test_setup():
    b = G.initial_state().board
    if b.get(THRONE) != "K":
        fail("King not on the central throne at setup")
    defenders = [c for c, p in b.items() if p == "D"]
    attackers = [c for c, p in b.items() if p == "A"]
    if len(defenders) != 8:
        fail(f"expected 8 defenders, got {len(defenders)}")
    if len(attackers) != 16:
        fail(f"expected 16 attackers, got {len(attackers)}")
    # defenders form the 3x3 ring around the throne (minus the throne)
    ring = {(c, r) for c in (2, 3, 4) for r in (2, 3, 4)} - {THRONE}
    if set(defenders) != ring:
        fail(f"defenders not in the 3x3 ring around the throne: {sorted(defenders)}")
    # attackers move first
    if G.current_player(G.initial_state()) != ATTACKERS:
        fail("attackers must move first")
    print("  setup: King on throne, 8 defenders ringing it, 16 attackers, "
          "attackers to move: OK")


# ---------------------------------------------------------------- conformance
def test_conformance(n_games: int = 200):
    rng = random.Random(20260621)
    saw_atk_win = saw_def_win = 0
    for _ in range(n_games):
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
    # An attacker 'A' at (4,0). A defender already flanks at (3,0); the defender
    # at (5,1) moves to (5,0) to complete the sandwich along the top row.
    board = {(3, 0): "D", (4, 0): "A", (5, 1): "D", THRONE: "K"}
    s = TaflState(board=board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "5,1>5,0")
    if (4, 0) in s2.board:
        fail("attacker should have been custodially captured at (4,0)")
    if s2.board.get((5, 0)) != "D" or s2.board.get((3, 0)) != "D":
        fail("flanking defenders not where expected after capture")
    print("  custodial capture of an attacker man: OK")

    # Active-capture negative: a defender moving BETWEEN two attackers is safe.
    board2 = {(3, 0): "A", (5, 0): "A", (4, 2): "D", THRONE: "K"}
    s3 = TaflState(board=board2, to_move=DEFENDERS)
    s4 = G.apply_move(s3, "4,2>4,0")
    if (4, 0) not in s4.board:
        fail("a piece moving between two enemies must be safe (no suicide capture)")
    print("  moving between two enemies is safe: OK")

    # The King assists capture: an attacker sandwiched between the King and a
    # moving defender is removed.
    board3 = {(1, 1): "K", (1, 2): "A", (1, 6): "D", (6, 6): "A"}
    s5 = TaflState(board=board3, to_move=DEFENDERS)
    s6 = G.apply_move(s5, "1,6>1,3")
    if (1, 2) in s6.board:
        fail("the King must pair with a defender to capture an attacker")
    print("  King assists a custodial capture: OK")


# --------------------------------------------------- king surrounded -> capture
def test_king_surrounded():
    # King at (2,2) with attackers on three sides; the fourth attacker slides in
    # from (3,5) to (3,2) on the right.
    board = {(2, 1): "A", (2, 3): "A", (1, 2): "A", (3, 5): "A", (2, 2): "K"}
    s = TaflState(board=board, to_move=ATTACKERS)
    if G.is_terminal(s):
        fail("king with an open side should not yet be terminal")
    s2 = G.apply_move(s, "3,5>3,2")
    if s2.winner != ATTACKERS:
        fail(f"king should be captured (surrounded on 4 sides); winner={s2.winner}")
    if not G.is_terminal(s2):
        fail("state after king surround should be terminal")
    print("  king captured by four-side surround: OK")

    # Capture aided by the empty throne: king beside the throne (4,3), attackers
    # on the other three sides; the empty throne at (3,3) is the fourth wall.
    board_t = {(4, 3): "K", (4, 2): "A", (4, 4): "A", (5, 6): "A"}
    s3 = TaflState(board=board_t, to_move=ATTACKERS)
    s4 = G.apply_move(s3, "5,6>5,3")
    if s4.winner != ATTACKERS:
        fail(f"king should be captured using the empty throne as a wall; winner={s4.winner}")
    print("  king captured using the empty throne as a wall: OK")

    # Edge safety: a king on the board edge cannot be surrounded (one side is off
    # the board). King at (0,3) with attackers above/below and one sliding to the
    # only on-board orthogonal neighbour (1,3) -> still NOT captured.
    board_e = {(0, 3): "K", (0, 2): "A", (0, 4): "A", (3, 1): "A"}
    s5 = TaflState(board=board_e, to_move=ATTACKERS)
    s6 = G.apply_move(s5, "3,1>1,1")  # harmless move; king already on the edge
    if s6.winner == ATTACKERS:
        fail("king on a board edge must not be capturable by surround")
    print("  king on a board edge is not capturable by surround: OK")


# ----------------------------------------------------- king escapes to the edge
def test_king_escape():
    # King at (3,1); a clear file to the top edge (3,0).
    board = {(3, 1): "K"}
    s = TaflState(board=board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "3,1>3,0")
    if s2.winner != DEFENDERS:
        fail(f"king reaching an edge must win for defenders; winner={s2.winner}")
    if not G.is_terminal(s2):
        fail("state after king escape should be terminal")
    print("  king escapes to an edge to win: OK")

    # A corner is an ordinary edge square here -> also an escape.
    s3 = TaflState(board={(0, 3): "K"}, to_move=DEFENDERS)
    s4 = G.apply_move(s3, "0,3>0,0")
    if s4.winner != DEFENDERS:
        fail(f"king reaching a corner (an edge) must win; winner={s4.winner}")
    print("  corner counts as an edge escape: OK")

    # Sanity: the king on (3,2) is NOT already a win one step before the edge.
    s_pre = TaflState(board={(3, 2): "K"}, to_move=DEFENDERS)
    if G.is_terminal(s_pre):
        fail("king not yet on an edge should not be terminal")


def main():
    test_setup()
    test_conformance()
    test_capture_attacker()
    test_king_surrounded()
    test_king_escape()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
