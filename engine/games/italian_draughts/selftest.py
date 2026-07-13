"""Standalone correctness anchors for Italian Draughts (pure stdlib).

Run: PYTHONPATH=. python3 games/italian_draughts/selftest.py
Also executed by tests/test_games.py::test_package_selftests.

Anchors the load-bearing Italian rules (FID Regolamento, Capo I):
  * setup + orientation (dark bottom-right / light lower-left),
  * men move & capture forward only,
  * a man may never capture a king,
  * kings are SHORT (non-flying): no multi-square move, no distance capture,
  * the full maximal-capture priority chain 6.6 -> 6.7 -> 6.8 -> 6.9,
  * promotion only when a man ENDS on the last rank,
  * a win reached via apply_move, and termination of a random playout.
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
    from games.italian_draughts.game import DraughtsState
    return DraughtsState(board=dict(board), to_move=to_move)


def legal(board, to_move=0):
    return set(G.legal_moves(S(board, to_move)))


def test_setup_and_orientation():
    s = G.initial_state()
    b = s.board
    assert len([1 for v in b.values() if v[0] == 0]) == 12
    assert len([1 for v in b.values() if v[0] == 1]) == 12
    # every piece on a dark ((c+r) odd) square, correct rows
    for (c, r), (pl, k) in b.items():
        assert (c + r) % 2 == 1 and k == _MAN
        assert (pl == 0 and r in (0, 1, 2)) or (pl == 1 and r in (5, 6, 7))
    # Italian orientation: bottom-right (7,0) is a dark playing square,
    # bottom-left (0,0) is a light square (never used).
    assert (7, 0) in b and (0, 0) not in b
    assert (7 + 0) % 2 == 1 and (0 + 0) % 2 == 0
    assert G.current_player(s) == 0  # White moves first
    print("ok setup/orientation")


def test_man_forward_only():
    # White man at (3,3): may step/capture only toward +row, never backward.
    # Put a black man behind (2,2) with empty (1,1): a backward capture would be
    # (3,3)>(1,1) — it must NOT be offered. A forward black man (4,4)/land (5,5)
    # MUST be capturable.
    b = {(3, 3): (0, _MAN), (2, 2): (1, _MAN), (4, 4): (1, _MAN)}
    mv = legal(b, 0)
    assert "3,3>5,5" in mv            # forward capture required
    assert "3,3>1,1" not in mv        # backward capture forbidden
    # capture is mandatory -> only the forward capture, no quiet move
    assert mv == {"3,3>5,5"}
    print("ok man forward-only capture")


def test_man_cannot_capture_king():
    # A white man with an adjacent-forward enemy KING and empty landing has NO
    # capture (men never take kings); with a MAN instead it DOES.
    king_b = {(3, 3): (0, _MAN), (4, 4): (1, _KING)}
    mvk = legal(king_b, 0)
    assert "3,3>5,5" not in mvk        # cannot jump the king
    # no capture at all -> only quiet forward steps ((4,4) is blocked by the king)
    assert mvk == {"3,3>2,4"}
    man_b = {(3, 3): (0, _MAN), (4, 4): (1, _MAN)}
    assert "3,3>5,5" in legal(man_b, 0)  # a man IS capturable
    print("ok man cannot capture king")


def test_king_is_short_not_flying():
    # A lone white king on a clear diagonal may move only ONE square (non-flying).
    b = {(3, 3): (0, _KING)}
    mv = legal(b, 0)
    assert mv == {"3,3>4,4", "3,3>2,2", "3,3>4,2", "3,3>2,4"}
    assert "3,3>5,5" not in mv        # no multi-square slide
    # A king cannot capture a piece two squares away across a gap (no flying
    # capture): black man at (5,5) with empty (4,4) between -> no capture, and
    # the king may only step one square.
    b2 = {(3, 3): (0, _KING), (5, 5): (1, _MAN)}
    mv2 = legal(b2, 0)
    assert "3,3>6,6" not in mv2 and "3,3>4,4" in mv2  # just a quiet step
    # Adjacent enemy -> a SHORT capture landing immediately beyond.
    b3 = {(3, 3): (0, _KING), (4, 4): (1, _MAN)}
    assert legal(b3, 0) == {"3,3>5,5"}
    print("ok king short (non-flying)")


def test_priority_6_6_most_pieces():
    # A man that can take 2 vs a man that can take 1 -> only the double is legal.
    b = {
        (2, 2): (0, _MAN), (3, 3): (1, _MAN), (5, 5): (1, _MAN),   # double chain
        (0, 2): (0, _MAN), (1, 3): (1, _MAN),                      # single
    }
    assert legal(b, 0) == {"2,2>4,4>6,6"}
    print("ok 6.6 greatest number of pieces")


def test_priority_6_7_capture_with_king():
    # Same count (1) available with a man and with a king -> must use the KING.
    b = {
        (2, 2): (0, _MAN), (3, 3): (1, _MAN),    # man captures 1
        (5, 4): (0, _KING), (6, 5): (1, _MAN),   # king captures 1
    }
    assert legal(b, 0) == {"5,4>7,6"}
    print("ok 6.7 capture with a king over a man")


def test_priority_6_8_most_kings():
    # Two king sequences, both count 2; one takes a king + man, the other man +
    # man -> must take the one capturing the KING (more kings).
    b = {
        (2, 2): (0, _KING), (3, 3): (1, _MAN), (5, 5): (1, _MAN),   # 2 men
        (1, 3): (0, _KING), (2, 4): (1, _KING), (4, 6): (1, _MAN),  # king + man
    }
    assert legal(b, 0) == {"1,3>3,5>5,7"}
    print("ok 6.8 greatest number of kings")


def test_priority_6_9_earliest_king():
    # ONE king with two count-2 branches, each taking exactly one king + one man
    # (same number, same #kings). Left branch takes the KING FIRST, right branch
    # the man first -> the king-first branch is forced.
    b = {
        (4, 1): (0, _KING),
        (3, 2): (1, _KING), (1, 4): (1, _MAN),   # left: king then man  -> (1,0)
        (5, 2): (1, _MAN), (5, 4): (1, _KING),   # right: man then king -> (0,1)
    }
    mv = legal(b, 0)
    assert mv == {"4,1>2,3>0,5"}, mv
    print("ok 6.9 king encountered earliest")


def test_promotion_only_at_end():
    from games.italian_draughts.game import DraughtsState
    # (a) quiet man step onto the last rank promotes.
    s = S({(4, 6): (0, _MAN)}, 0)
    s2 = G.apply_move(s, "4,6>5,7")
    assert s2.board[(5, 7)] == (0, _KING)
    # (b) a man capturing onto the last rank promotes and the sequence ends.
    s = S({(4, 5): (0, _MAN), (5, 6): (1, _MAN)}, 0)
    assert "4,5>6,7" in G.legal_moves(s)
    s2 = G.apply_move(s, "4,5>6,7")
    assert s2.board[(6, 7)] == (0, _KING) and (5, 6) not in s2.board
    # (c) a plain man not reaching the last rank stays a man.
    s = S({(4, 4): (0, _MAN)}, 0)
    assert G.apply_move(s, "4,4>5,5").board[(5, 5)] == (0, _MAN)
    _ = DraughtsState  # silence linters
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
    rng = random.Random(12345)
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
    test_man_cannot_capture_king()
    test_king_is_short_not_flying()
    test_priority_6_6_most_pieces()
    test_priority_6_7_capture_with_king()
    test_priority_6_8_most_kings()
    test_priority_6_9_earliest_king()
    test_promotion_only_at_end()
    test_win_via_apply_move()
    test_serialize_roundtrip()
    test_random_playout_terminates()
    print("all italian_draughts selftests passed")


if __name__ == "__main__":
    main()
