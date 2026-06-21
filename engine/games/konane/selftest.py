"""Standalone self-test for Kōnane (Hawaiian checkers).

Run with:  PYTHONPATH=. python3 games/konane/selftest.py

Asserts the correctness anchor:
  * conformance (random self-play, purity, serialize round-trip, termination),
  * rule positions:
      - the initial board is COMPLETELY FILLED with the alternating pattern,
      - the two opening single-stone removals (Black corner/center, then White
        an orthogonally-adjacent stone),
      - an orthogonal jump-capture removes the jumped enemy stone and lands two
        squares away (and there are NO diagonal jumps),
      - a multi-jump continues only in the SAME straight-line direction (a turn
        is illegal),
      - the LAST-PLAYER-TO-MOVE-WINS terminal: a player with no capture loses.

There is no widely-published perft for Kōnane, so the anchor is conformance plus
these hand-built rule positions. Prints "SELFTEST OK" and exits 0 on success,
nonzero on failure.
"""

from __future__ import annotations

import json
import os
import sys

from agp import conformance
from games.konane.game import (
    Konane, KonaneState, P_OPEN1, P_OPEN2, P_PLAY, _start_board,
)


def fail(msg: str):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


G = Konane()


def play_state(n, pieces, to_move=0):
    """A normal-play state with an explicit sparse board.
    pieces: {(c, r): player}."""
    return KonaneState(n=n, board=dict(pieces), to_move=to_move,
                       phase=P_PLAY, first_empty=(0, 0))


# ---------------------------------------------------------------------------
# 1. Initial board: completely filled, alternating, Black=even parity
# ---------------------------------------------------------------------------
def test_initial_board():
    for n in (6, 8, 10):
        s = G.initial_state(options={"size": n})
        if len(s.board) != n * n:
            fail(f"n={n}: board not completely filled ({len(s.board)} != {n*n})")
        for (c, r), p in s.board.items():
            if p != (c + r) % 2:
                fail(f"n={n}: cell ({c},{r}) wrong color {p}")
        if s.phase != P_OPEN1 or s.to_move != 0:
            fail("initial state should be Black's opening removal")


# ---------------------------------------------------------------------------
# 2. Opening move 1: Black removes a corner or center stone
# ---------------------------------------------------------------------------
def test_opening1():
    s = G.initial_state(options={"size": 8})
    moves = set(G.legal_moves(s))
    # corners of 8x8: parity even -> black: (0,0),(7,7) even; (7,0),(0,7) odd (white).
    # center 2x2 of 8x8 = {(3,3),(3,4),(4,3),(4,4)}; black ones (even) = (3,3),(4,4).
    expected = {"0,0", "7,7", "3,3", "4,4"}
    if moves != expected:
        fail(f"opening1 moves: got {sorted(moves)}, expected {sorted(expected)}")
    # apply one and check phase advances to White's removal
    s2 = G.apply_move(s, "0,0")
    if s2.phase != P_OPEN2 or s2.to_move != 1:
        fail("after Black's removal it should be White's opening removal")
    if (0, 0) in s2.board:
        fail("Black's removed stone is still on the board")
    if s2.first_empty != (0, 0):
        fail("first_empty not recorded")


# ---------------------------------------------------------------------------
# 3. Opening move 2: White removes a stone orthogonally adjacent to the gap
# ---------------------------------------------------------------------------
def test_opening2():
    s = G.initial_state(options={"size": 8})
    s = G.apply_move(s, "0,0")  # Black removes corner (0,0)
    moves = set(G.legal_moves(s))
    # orthogonal neighbours of (0,0): (1,0) parity odd -> white, (0,1) odd -> white.
    expected = {"1,0", "0,1"}
    if moves != expected:
        fail(f"opening2 moves: got {sorted(moves)}, expected {sorted(expected)}")
    s2 = G.apply_move(s, "1,0")
    if s2.phase != P_PLAY or s2.to_move != 0:
        fail("after White's removal normal play should begin with Black")
    if (1, 0) in s2.board:
        fail("White's removed stone is still on the board")

    # center opening: Black removes (3,3); White's neighbours that are white.
    s = G.initial_state(options={"size": 8})
    s = G.apply_move(s, "3,3")
    moves = set(G.legal_moves(s))
    # neighbours of (3,3): (4,3) odd->white, (2,3) odd->white, (3,4) odd->white,
    # (3,2) odd->white. All four are white.
    if moves != {"4,3", "2,3", "3,4", "3,2"}:
        fail(f"center opening2 moves wrong: {sorted(moves)}")


# ---------------------------------------------------------------------------
# 4. Orthogonal jump-capture; no diagonal jumps
# ---------------------------------------------------------------------------
def test_jump_capture():
    # Black at (2,0), White at (1,0), empty (0,0). Black jumps left to (0,0).
    s = play_state(8, {(2, 0): 0, (1, 0): 1}, to_move=0)
    moves = set(G.legal_moves(s))
    if moves != {"2,0>0,0"}:
        fail(f"single jump: got {sorted(moves)}, expected {{'2,0>0,0'}}")
    s2 = G.apply_move(s, "2,0>0,0")
    if (1, 0) in s2.board:
        fail("jump did not remove the jumped white stone")
    if s2.board.get((0, 0)) != 0 or (2, 0) in s2.board:
        fail("jumper did not move from (2,0) to (0,0)")
    if s2.to_move != 1:
        fail("turn did not pass to White")

    # No diagonal jump: Black at (2,2), White diagonally at (1,1), empty (0,0).
    s = play_state(8, {(2, 2): 0, (1, 1): 1}, to_move=0)
    if G.legal_moves(s):
        fail("diagonal jump was wrongly allowed / spurious move generated")

    # No move when landing square occupied: Black (2,0),White (1,0),Black (0,0).
    s = play_state(8, {(2, 0): 0, (1, 0): 1, (0, 0): 0}, to_move=0)
    # (2,0) cannot jump left (landing occupied); (0,0) cannot jump (no enemy adj
    # with empty beyond -> (1,0) enemy but (2,0) occupied). No black moves.
    if G.legal_moves(s):
        fail(f"blocked landing wrongly produced moves: {G.legal_moves(s)}")


# ---------------------------------------------------------------------------
# 5. Multi-jump: same straight-line direction only; may stop early; no turning
# ---------------------------------------------------------------------------
def test_multi_jump_straight_line():
    # Black at (6,0); whites at (5,0) and (3,0); empties at (4,0) and (2,0).
    #   jump 1: over (5,0) -> land (4,0)
    #   jump 2: over (3,0) -> land (2,0)
    # Legal moves: stop after first (6,0>4,0) OR continue (6,0>4,0>2,0).
    s = play_state(8, {(6, 0): 0, (5, 0): 1, (3, 0): 1}, to_move=0)
    moves = set(G.legal_moves(s))
    if moves != {"6,0>4,0", "6,0>4,0>2,0"}:
        fail(f"straight multi-jump: got {sorted(moves)}, "
             "expected stop-or-continue {'6,0>4,0','6,0>4,0>2,0'}")
    s2 = G.apply_move(s, "6,0>4,0>2,0")
    if (5, 0) in s2.board or (3, 0) in s2.board:
        fail("double jump failed to remove both jumped stones")
    if s2.board.get((2, 0)) != 0 or (6, 0) in s2.board:
        fail("double jumper not at final landing (2,0)")

    # No TURNING: after jumping up to (3,2) a sideways enemy must NOT be chained.
    # Black at (3,0); White at (3,1) (empty (3,2) beyond); White at (4,2)
    # (empty (5,2) beyond). A turn 3,0>3,2>5,2 must be illegal.
    s = play_state(8, {(3, 0): 0, (3, 1): 1, (4, 2): 1}, to_move=0)
    moves = set(G.legal_moves(s))
    if "3,0>3,2>5,2" in moves:
        fail("multi-jump illegally turned a corner")
    if moves != {"3,0>3,2"}:
        fail(f"turn position should allow only the straight jump: {sorted(moves)}")


# ---------------------------------------------------------------------------
# 6. Last-player-to-move-wins terminal (no-move = loss)
# ---------------------------------------------------------------------------
def test_no_move_loses():
    # Black to move with no possible jump (lone black stone, no enemies) -> Black
    # loses; White (last to move) wins.
    s = play_state(8, {(4, 4): 0}, to_move=0)
    if not G.is_terminal(s):
        fail("position with no Black move should be terminal")
    if G.returns(s) != [-1.0, 1.0]:
        fail(f"no-move-for-Black returns wrong: {G.returns(s)}")

    # White to move with no jump -> White loses, Black wins.
    s = play_state(8, {(4, 4): 1}, to_move=1)
    if not G.is_terminal(s):
        fail("position with no White move should be terminal")
    if G.returns(s) != [1.0, -1.0]:
        fail(f"no-move-for-White returns wrong: {G.returns(s)}")

    # A position where the mover DOES have a capture is NOT terminal.
    s = play_state(8, {(2, 0): 0, (1, 0): 1}, to_move=0)
    if G.is_terminal(s):
        fail("position with an available capture should not be terminal")


# ---------------------------------------------------------------------------
# 7. serialize round-trip
# ---------------------------------------------------------------------------
def test_serialize_roundtrip():
    for setup in (
        G.initial_state(options={"size": 6}),
        G.apply_move(G.initial_state(options={"size": 8}), "0,0"),
        play_state(10, {(2, 0): 0, (1, 0): 1}, to_move=0),
    ):
        d = G.serialize(setup)
        json.dumps(d)  # JSON-able
        s2 = G.deserialize(d)
        if json.dumps(G.serialize(s2), sort_keys=True) != json.dumps(d, sort_keys=True):
            fail("serialize/deserialize did not round-trip")


# ---------------------------------------------------------------------------
# 8. Conformance (random self-play harness) across the board sizes
# ---------------------------------------------------------------------------
def test_conformance():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as f:
        manifest = json.load(f)
    rep = conformance.check(G, manifest, games=40, seed=11)
    if not rep.ok:
        print(rep.summary())
        fail("conformance check failed")


def main():
    test_initial_board()
    test_opening1()
    test_opening2()
    test_jump_capture()
    test_multi_jump_straight_line()
    test_no_move_loses()
    test_serialize_roundtrip()
    test_conformance()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
