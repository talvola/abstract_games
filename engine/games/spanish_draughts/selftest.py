"""Standalone correctness anchors for Spanish Draughts (pure stdlib).

Run: PYTHONPATH=. python3 games/spanish_draughts/selftest.py
Also executed by tests/test_games.py::test_package_selftests.

Anchors the load-bearing Spanish rules (damas españolas) and, crucially, the
points that DISTINGUISH Spanish from its 8x8 siblings:
  * setup + orientation (12 men each, (c+r) even playing squares),
  * men move & capture FORWARD only (no backward capture),
  * a man CAN capture a king  (the OPPOSITE of Italian),
  * kings are FLYING: capture across a gap, forward AND backward
        (the OPPOSITE of Italian's short king),
  * mandatory MAXIMUM capture, quantity (most pieces) then quality (most kings),
  * a man is SHORT (cannot fly): no distance capture,
  * promotion only when a man ENDS on the last rank,
  * a win reached via apply_move, serialize round-trip, and termination.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir  # noqa: E402

_MAN, _KING = "m", "k"
_, G = load_from_dir(Path(__file__).resolve().parent)


def S(board, to_move=0):
    from games.spanish_draughts.game import DraughtsState
    return DraughtsState(board=dict(board), to_move=to_move)


def legal(board, to_move=0):
    return set(G.legal_moves(S(board, to_move)))


def starts(board, to_move=0):
    return {m.split(">")[0] for m in legal(board, to_move)}


def test_setup_and_orientation():
    s = G.initial_state()
    b = s.board
    assert len([1 for v in b.values() if v[0] == 0]) == 12
    assert len([1 for v in b.values() if v[0] == 1]) == 12
    for (c, r), (pl, k) in b.items():
        assert (c + r) % 2 == 0 and k == _MAN
        assert (pl == 0 and r in (0, 1, 2)) or (pl == 1 and r in (5, 6, 7))
    # Spanish orientation (mirror of Italian): (0,0) is a dark playing square,
    # (7,0) — the near-right square — is a light non-playing square.
    assert (0, 0) in b and (7, 0) not in b
    assert G.current_player(s) == 0  # White moves first
    print("ok setup/orientation")


def test_man_forward_only():
    # White man at (3,3): a backward enemy (2,2)/land (1,1) must NOT be offered;
    # a forward enemy (4,4)/land (5,5) MUST be, and capture is mandatory.
    b = {(3, 3): (0, _MAN), (2, 2): (1, _MAN), (4, 4): (1, _MAN)}
    mv = legal(b, 0)
    assert "3,3>5,5" in mv            # forward capture required
    assert "3,3>1,1" not in mv        # backward capture forbidden
    assert mv == {"3,3>5,5"}          # mandatory, no quiet move
    print("ok man forward-only capture")


def test_man_CAN_capture_king():
    # THE defining difference from Italian: a white man with an adjacent-forward
    # enemy KING and empty landing MUST capture it (Italian forbids this).
    king_b = {(3, 3): (0, _MAN), (4, 4): (1, _KING)}
    assert legal(king_b, 0) == {"3,3>5,5"}   # the man jumps the king
    # and after the capture the king is gone
    s2 = G.apply_move(S(king_b, 0), "3,3>5,5")
    assert (4, 4) not in s2.board and s2.board[(5, 5)] == (0, _MAN)
    print("ok man CAN capture a king")


def test_king_is_flying():
    # THE defining difference from Italian's short king: a king captures a piece
    # any distance away across a gap, landing on ANY empty square beyond it.
    b = {(0, 0): (0, _KING), (3, 3): (1, _MAN)}   # gap (1,1),(2,2) empty
    mv = legal(b, 0)
    assert mv == {"0,0>4,4", "0,0>5,5", "0,0>6,6", "0,0>7,7"}
    # a lone flying king with a clear diagonal slides any distance (quiet)
    q = legal({(3, 3): (0, _KING)}, 0)
    assert "3,3>7,7" in q and "3,3>0,0" in q
    # kings capture BACKWARD too: king at (5,5) takes the man at (3,3) (toward
    # row 0) and lands beyond it.
    back = legal({(5, 5): (0, _KING), (3, 3): (1, _MAN)}, 0)
    assert back == {"5,5>2,2", "5,5>1,1", "5,5>0,0"}
    print("ok king is flying (long, both directions)")


def test_man_is_short_not_flying():
    # A man is NOT flying: an enemy two squares away across a gap is not
    # capturable, and the man only steps one square.
    mv = legal({(1, 1): (0, _MAN), (4, 4): (1, _MAN)}, 0)
    assert mv == {"1,1>0,2", "1,1>2,2"}   # quiet steps only, no distance capture
    print("ok man is short (non-flying)")


def test_priority_quantity_most_pieces():
    # A man that can take 2 vs a man that can take 1 -> only the double is legal.
    b = {
        (2, 2): (0, _MAN), (3, 3): (1, _MAN), (5, 5): (1, _MAN),   # double chain
        (0, 2): (0, _MAN), (1, 3): (1, _MAN),                      # single
    }
    assert legal(b, 0) == {"2,2>4,4>6,6"}
    print("ok quantity: greatest number of pieces")


def test_priority_quality_most_kings():
    # Two flying-king sequences, both capturing exactly 2 pieces: one takes two
    # MEN (2 pieces, 0 kings), the other a KING + a man (2 pieces, 1 king) -> the
    # quality rule forces the king-capturing sequence.
    b = {
        (2, 2): (0, _KING), (3, 3): (1, _MAN), (5, 5): (1, _MAN),   # 2 men
        (1, 3): (0, _KING), (2, 4): (1, _KING), (4, 6): (1, _MAN),  # king + man
    }
    # sanity: the (2,2) king really CAN take 2 men on its own (a genuine tie in
    # piece-count), so the choice is decided purely by quality.
    assert starts({(2, 2): (0, _KING), (3, 3): (1, _MAN), (5, 5): (1, _MAN)}) == {"2,2"}
    # in the combined position only the king-capturing king (1,3) is legal
    assert starts(b, 0) == {"1,3"}
    # and every legal move actually removes the enemy king
    for m in legal(b, 0):
        assert (2, 4) not in G.apply_move(S(b, 0), m).board
    print("ok quality: greatest number of kings breaks a count tie")


def test_promotion_only_at_end():
    # (a) quiet man step onto the last rank promotes.
    assert G.apply_move(S({(4, 6): (0, _MAN)}, 0), "4,6>5,7").board[(5, 7)] == (0, _KING)
    # (b) a man capturing onto the last rank promotes and the sequence ends.
    s = S({(4, 5): (0, _MAN), (5, 6): (1, _MAN)}, 0)
    assert "4,5>6,7" in G.legal_moves(s)
    s2 = G.apply_move(s, "4,5>6,7")
    assert s2.board[(6, 7)] == (0, _KING) and (5, 6) not in s2.board
    # (c) a plain man not reaching the last rank stays a man.
    assert G.apply_move(S({(4, 4): (0, _MAN)}, 0), "4,4>5,5").board[(5, 5)] == (0, _MAN)
    print("ok promotion only when ending on last rank")


def test_win_via_apply_move():
    # White captures Black's last piece -> terminal, White (player 0) wins.
    b = {(2, 2): (0, _KING), (3, 3): (1, _MAN)}
    s = S(b, 0)
    assert not G.is_terminal(s)
    s2 = G.apply_move(s, "2,2>4,4")
    assert len([1 for v in s2.board.values() if v[0] == 1]) == 0
    assert G.is_terminal(s2)
    assert G.returns(s2) == [1.0, -1.0]  # Black (to move) has no piece -> loses
    print("ok win reached via apply_move")


def test_serialize_roundtrip():
    s = G.initial_state()
    for m in list(G.legal_moves(s))[:1]:
        s = G.apply_move(s, m)
    d = G.serialize(s)
    assert G.serialize(G.deserialize(d)) == d
    print("ok serialize round-trip")


def test_random_playout_terminates():
    rng = random.Random(2024)
    for _ in range(30):
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s) and steps < 1000:
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            steps += 1
        assert G.is_terminal(s)
        assert len(G.returns(s)) == 2
    print("ok random playouts terminate")


def main():
    test_setup_and_orientation()
    test_man_forward_only()
    test_man_CAN_capture_king()
    test_king_is_flying()
    test_man_is_short_not_flying()
    test_priority_quantity_most_pieces()
    test_priority_quality_most_kings()
    test_promotion_only_at_end()
    test_win_via_apply_move()
    test_serialize_roundtrip()
    test_random_playout_terminates()
    print("all spanish_draughts selftests passed")


if __name__ == "__main__":
    main()
