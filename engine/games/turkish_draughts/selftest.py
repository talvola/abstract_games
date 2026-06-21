"""Standalone self-test for Turkish Draughts.

Run with:  PYTHONPATH=. python3 games/turkish_draughts/selftest.py

Asserts the correctness anchor:
  * conformance (random self-play, purity, serialize round-trip, termination),
  * rule positions: a man moving / capturing ORTHOGONALLY (forward + sideways,
    never diagonal, never backward), a flying king capturing along a rank/file,
    and the MAXIMUM-capture rule.

There is no widely-published perft for Turkish draughts, so the anchor is
conformance + these hand-built rule positions. Prints "SELFTEST OK" and exits 0
on success, nonzero on failure.
"""

from __future__ import annotations

import json
import sys

from agp import conformance
from games.turkish_draughts.game import TurkishDraughts, DamaState


def fail(msg: str):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def parse_moves(moves):
    """Normalize a list of move strings to a set for comparison."""
    return set(moves)


def make(pieces: dict, to_move: int = 0) -> DamaState:
    """pieces: {(c, r): (player, kind)}"""
    return DamaState(board=dict(pieces), to_move=to_move)


G = TurkishDraughts()


# ---------------------------------------------------------------------------
# 1. MAN simple movement: orthogonal forward + sideways, never diagonal/backward
# ---------------------------------------------------------------------------
def test_man_movement():
    # Lone White man (player 0, moves toward +r) in the middle of an open board.
    s = make({(3, 3): (0, "m")})
    moves = parse_moves(G.legal_moves(s))
    expected = {"3,3>3,4", "3,3>2,3", "3,3>4,3"}  # forward (+r), left, right
    if moves != expected:
        fail(f"White man moves: got {sorted(moves)}, expected {sorted(expected)}")
    # explicitly: no backward, no diagonal
    forbidden = {"3,3>3,2", "3,3>4,4", "3,3>2,2", "3,3>4,2", "3,3>2,4"}
    if moves & forbidden:
        fail(f"White man has illegal diagonal/backward moves: {moves & forbidden}")

    # Lone Black man (player 1, moves toward -r): forward is -r.
    s = make({(3, 3): (1, "m")}, to_move=1)
    moves = parse_moves(G.legal_moves(s))
    expected = {"3,3>3,2", "3,3>2,3", "3,3>4,3"}
    if moves != expected:
        fail(f"Black man moves: got {sorted(moves)}, expected {sorted(expected)}")


# ---------------------------------------------------------------------------
# 2. MAN capture: orthogonal forward + sideways; never backward / diagonal
# ---------------------------------------------------------------------------
def test_man_capture_forward_and_side():
    # White man at (3,3); enemy directly forward at (3,4), empty (3,5) beyond.
    s = make({(3, 3): (0, "m"), (3, 4): (1, "m")})
    moves = parse_moves(G.legal_moves(s))
    if moves != {"3,3>3,5"}:
        fail(f"forward capture: got {sorted(moves)}, expected {{'3,3>3,5'}}")
    s2 = G.apply_move(s, "3,3>3,5")
    if (3, 4) in s2.board:
        fail("forward capture did not remove the jumped piece")
    if s2.board.get((3, 5)) != (0, "m"):
        fail("forward capture did not land the man on (3,5)")

    # Sideways capture (to the right).
    s = make({(3, 3): (0, "m"), (4, 3): (1, "m")})
    moves = parse_moves(G.legal_moves(s))
    if moves != {"3,3>5,3"}:
        fail(f"sideways capture: got {sorted(moves)}, expected {{'3,3>5,3'}}")


def test_man_no_backward_capture():
    # White man at (3,3); enemy BEHIND at (3,2), empty (3,1) beyond.
    # A man may not capture backward, so the only legal acts are simple moves.
    s = make({(3, 3): (0, "m"), (3, 2): (1, "m")})
    moves = parse_moves(G.legal_moves(s))
    if "3,3>3,1" in moves:
        fail("man illegally captured backward")
    # no capture available => simple forward/side moves only
    if moves != {"3,3>3,4", "3,3>2,3", "3,3>4,3"}:
        fail(f"no-backward-capture position moves wrong: {sorted(moves)}")


def test_man_no_diagonal_capture():
    # Enemy on a diagonal must never be capturable by a man.
    s = make({(3, 3): (0, "m"), (4, 4): (1, "m")})
    moves = parse_moves(G.legal_moves(s))
    # (4,4) is diagonal: no capture; simple moves only.
    if any(m.endswith("5,5") for m in moves):
        fail("man illegally captured diagonally")


# ---------------------------------------------------------------------------
# 3. FLYING KING capture along a rank / file, landing at variable distance
# ---------------------------------------------------------------------------
def test_king_capture_file():
    # White king at (0,0); enemy at (0,4) up the file; empties (0,5),(0,6),(0,7) beyond.
    s = make({(0, 0): (0, "k"), (0, 4): (1, "m")})
    moves = parse_moves(G.legal_moves(s))
    expected = {"0,0>0,5", "0,0>0,6", "0,0>0,7"}
    if moves != expected:
        fail(f"king file capture landings: got {sorted(moves)}, expected {sorted(expected)}")
    s2 = G.apply_move(s, "0,0>0,7")
    if (0, 4) in s2.board:
        fail("king capture did not remove the jumped piece")
    if s2.board.get((0, 7)) != (0, "k"):
        fail("king did not land on (0,7)")


def test_king_capture_rank():
    # White king at (1,2); enemy at (5,2) along the rank; empties (6,2),(7,2) beyond.
    s = make({(1, 2): (0, "k"), (5, 2): (1, "m")})
    moves = parse_moves(G.legal_moves(s))
    expected = {"1,2>6,2", "1,2>7,2"}
    if moves != expected:
        fail(f"king rank capture landings: got {sorted(moves)}, expected {sorted(expected)}")


def test_king_blocked_by_own():
    # Own piece behind the enemy: king may still land between enemy and own piece.
    # King at (0,0), enemy at (0,3), own piece at (0,6). Landings: (0,4),(0,5).
    s = make({(0, 0): (0, "k"), (0, 3): (1, "m"), (0, 6): (0, "m")})
    moves = parse_moves(G.legal_moves(s))
    # The man at (0,6) also has its own (non-capturing) moves; isolate king captures.
    king_caps = {m for m in moves if m.startswith("0,0>")}
    if king_caps != {"0,0>0,4", "0,0>0,5"}:
        fail(f"king landings near own piece wrong: {sorted(king_caps)}")
    # Two adjacent enemies in a row cannot be jumped (a king jumps exactly one,
    # and here there is no empty landing square beyond the first enemy). The king
    # may still make non-capturing slides up to the first enemy, but must not land
    # beyond row 3 on the file.
    s = make({(0, 0): (0, "k"), (0, 3): (1, "m"), (0, 4): (1, "m")})
    moves = parse_moves(G.legal_moves(s))
    file_moves = {m for m in moves if m.startswith("0,0>0,")}
    if file_moves != {"0,0>0,1", "0,0>0,2"}:
        fail(f"king illegally jumped/slid through two adjacent enemies: {sorted(file_moves)}")


# ---------------------------------------------------------------------------
# 4. MAXIMUM-capture rule
# ---------------------------------------------------------------------------
def test_maximum_capture():
    # White man at (3,1). A double-capture path exists going up:
    #   enemy at (3,2) -> land (3,3); enemy at (3,4) -> land (3,5).
    # Also a single sideways capture: enemy at (4,1) -> land (5,1).
    # Maximum rule: only the 2-capture sequence is legal.
    s = make({
        (3, 1): (0, "m"),
        (3, 2): (1, "m"),
        (3, 4): (1, "m"),
        (4, 1): (1, "m"),
    })
    moves = parse_moves(G.legal_moves(s))
    if moves != {"3,1>3,3>3,5"}:
        fail(f"maximum-capture: got {sorted(moves)}, expected the 2-jump {{'3,1>3,3>3,5'}}")
    # Apply it and verify BOTH enemies on the file are removed, the side one stays.
    s2 = G.apply_move(s, "3,1>3,3>3,5")
    if (3, 2) in s2.board or (3, 4) in s2.board:
        fail("max-capture chain failed to remove both jumped pieces")
    if (4, 1) not in s2.board:
        fail("max-capture chain wrongly removed the un-jumped side piece")


def test_immediate_removal():
    # Turkish rule: captured pieces vacate immediately, so a man can turn and
    # use a square that an earlier capture in the same chain cleared.
    # White man at (1,1): jump up over (1,2) to (1,3), then jump right over
    # (2,3) to (3,3). Two captures.
    s = make({
        (1, 1): (0, "m"),
        (1, 2): (1, "m"),
        (2, 3): (1, "m"),
    })
    moves = parse_moves(G.legal_moves(s))
    if moves != {"1,1>1,3>3,3"}:
        fail(f"turn-during-chain: got {sorted(moves)}, expected {{'1,1>1,3>3,3'}}")


# ---------------------------------------------------------------------------
# 5. Promotion ends the turn (no king continuation on the promoting move)
# ---------------------------------------------------------------------------
def test_promotion_ends_turn():
    # White man at (0,5): jump up over (0,6) to (0,7) -> promotes. Even if a
    # further capture would be geometrically available, the turn ends.
    # Put an enemy at (2,7) that a king could otherwise jump from (0,7).
    s = make({
        (0, 5): (0, "m"),
        (0, 6): (1, "m"),
        (2, 7): (1, "m"),
    })
    moves = parse_moves(G.legal_moves(s))
    if moves != {"0,5>0,7"}:
        fail(f"promotion move: got {sorted(moves)}, expected {{'0,5>0,7'}}")
    s2 = G.apply_move(s, "0,5>0,7")
    if s2.board.get((0, 7)) != (0, "k"):
        fail("man did not promote on the last rank")
    if s2.to_move != 1:
        fail("promotion did not end the turn")


# ---------------------------------------------------------------------------
# 6. Win conditions
# ---------------------------------------------------------------------------
def test_win_conditions():
    # Opponent has no pieces -> mover to follow has no move -> loss.
    # Set up: it's Black to move with no Black pieces at all.
    s = make({(3, 3): (0, "k")}, to_move=1)
    if not G.is_terminal(s):
        fail("position with no pieces for mover should be terminal")
    ret = G.returns(s)
    if ret != [1.0, -1.0]:
        fail(f"no-move loss returns wrong: {ret}")

    # Blocked: Black man hemmed so it has no legal move.
    # Black man at (0,0): forward is -r (off board), sides (1,0) blocked, (-1,0) off.
    s = make({(0, 0): (1, "m"), (1, 0): (0, "m"), (1, 1): (0, "m")}, to_move=1)
    # (0,0) black: dirs = forward DOWN (off), LEFT (off), RIGHT->(1,0) occupied by own? no, white.
    # capture? enemy at (1,0) sideways, land (2,0) empty -> capture IS available.
    # So this is NOT a blocked position; adjust to truly block.
    s = make({(0, 0): (1, "m"), (1, 0): (1, "m"), (0, 1): (1, "m")}, to_move=1)
    # Black at (0,0): DOWN off, LEFT off, RIGHT->(1,0) own. No move for (0,0).
    # But other black men may move; ensure game not necessarily terminal — just
    # confirm (0,0) contributes no move by checking it's absent from sources.
    srcs = {m.split(">")[0] for m in G.legal_moves(s)}
    if "0,0" in srcs:
        fail("fully blocked man should have no move")


# ---------------------------------------------------------------------------
# 7. serialize round-trip
# ---------------------------------------------------------------------------
def test_serialize_roundtrip():
    s = G.initial_state()
    d = G.serialize(s)
    json.dumps(d)  # must be JSON-able
    s2 = G.deserialize(d)
    if json.dumps(G.serialize(s2), sort_keys=True) != json.dumps(d, sort_keys=True):
        fail("serialize/deserialize did not round-trip")
    # initial setup sanity: 16 men each, back ranks empty.
    white = [p for p, k in s.board.items() if k[0] == 0]
    black = [p for p, k in s.board.items() if k[0] == 1]
    if len(white) != 16 or len(black) != 16:
        fail(f"initial counts wrong: white={len(white)} black={len(black)}")
    if any(r == 0 for (_, r) in s.board) or any(r == 7 for (_, r) in s.board):
        fail("initial back ranks (row 0 / row 7) should be empty")


# ---------------------------------------------------------------------------
# 8. Conformance (random self-play harness)
# ---------------------------------------------------------------------------
def test_conformance():
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as f:
        manifest = json.load(f)
    rep = conformance.check(G, manifest, games=60, seed=7)
    if not rep.ok:
        print(rep.summary())
        fail("conformance check failed")


def main():
    test_man_movement()
    test_man_capture_forward_and_side()
    test_man_no_backward_capture()
    test_man_no_diagonal_capture()
    test_king_capture_file()
    test_king_capture_rank()
    test_king_blocked_by_own()
    test_maximum_capture()
    test_immediate_removal()
    test_promotion_ends_turn()
    test_win_conditions()
    test_serialize_roundtrip()
    test_conformance()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
