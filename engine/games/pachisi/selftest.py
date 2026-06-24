"""Pure-stdlib selftest for Pachisi.  Deterministic (seeded rng).  Fast.

Anchors:
  * board / path geometry: 4 rotationally-symmetric paths, length, castles;
  * cowrie throw distribution over many rolls matches the documented mapping;
  * a piece enters (only on a grace) and advances correctly;
  * a capture on a non-castle main-track square sends an enemy home;
  * a piece on a castle square is SAFE (cannot be captured);
  * a grace throw grants an extra turn (same player re-throws);
  * exact-count finishing (overshoot illegal);
  * the win at 4-home reached via apply_move; returns = per-player vector;
  * serialize round-trips (including the stored throw);
  * random self-play always terminates with a winner.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from games.pachisi.game import (   # noqa: E402
    Pachisi, PachisiState, PATH, PATH_LEN, FINISH, CASTLES, MAIN_TRACK,
    HOME_COL, CHARKONI, COWRIE, NPLAYERS, NPIECES,
)


def _fixed_throw(g, state, value):
    """Return a copy of `state` whose stored throw is forced to `value`."""
    s = g.deserialize(g.serialize(state))
    s.roll = value
    return s


def test_geometry():
    assert NPLAYERS == 4 and NPIECES == 4
    assert PATH_LEN == 83, PATH_LEN
    for p in range(4):
        assert len(PATH[p]) == PATH_LEN
        assert PATH[p][FINISH] == CHARKONI
        # all path cells distinct except the middle column (out & in) + Charkoni
        assert len(PATH[p]) == FINISH + 1
    assert len(CASTLES) == 12, len(CASTLES)
    assert len(MAIN_TRACK) == 68
    # the four arm-tip-middle squares are castles
    for tip in [(9, 18), (18, 9), (9, 0), (0, 9)]:
        assert tip in CASTLES
    # home columns are disjoint and not on the main track
    for p in range(4):
        assert HOME_COL[p].isdisjoint(MAIN_TRACK)
    for p in range(4):
        for q in range(4):
            if p != q:
                assert HOME_COL[p].isdisjoint(HOME_COL[q])
    print("ok geometry: 4 paths len 83, 12 castles, 68-cell main track")


def test_cowrie_distribution():
    g = Pachisi()
    rng = random.Random(1234)
    N = 240_000
    counts = {}
    for _ in range(N):
        v = g._throw(rng)
        counts[v] = counts.get(v, 0) + 1
    # expected probabilities from binomial(6, 1/2) mapped through COWRIE
    from math import comb
    exp = {}
    for up, (val, _grace) in COWRIE.items():
        exp[val] = exp.get(val, 0.0) + comb(6, up) / 64.0
    # every documented value appears; frequencies within tolerance
    for val, prob in exp.items():
        got = counts.get(val, 0) / N
        assert abs(got - prob) < 0.01, (val, got, prob)
    # values are exactly the documented set {2,3,4,5,6,10,25}
    assert set(counts) == {2, 3, 4, 5, 6, 10, 25}, set(counts)
    # graces are exactly {6,10,25}
    for v in (6, 10, 25):
        assert g._is_grace(v)
    for v in (2, 3, 4, 5):
        assert not g._is_grace(v)
    print("ok cowrie: distribution matches binomial(6,1/2) mapping; graces 6/10/25")


def test_entry_requires_grace():
    g = Pachisi()
    s = g.initial_state(rng=random.Random(0))
    # non-grace throw (e.g. 4): all pieces in Charkoni -> no entry -> pass only
    s4 = _fixed_throw(g, s, 4)
    assert g.legal_moves(s4) == ["pass"], g.legal_moves(s4)
    # grace throw (e.g. 25): may introduce a piece onto path[0]
    s25 = _fixed_throw(g, s, 25)
    moves = g.legal_moves(s25)
    entry_cell = PATH[0][0]
    assert f"{entry_cell[0]},{entry_cell[1]}" in moves, moves
    s2 = g.apply_move(s25, f"{entry_cell[0]},{entry_cell[1]}", rng=random.Random(7))
    assert 0 in s2.positions[0], s2.positions[0]      # a piece is on path index 0
    # grace => same player to move again
    assert s2.to_move == 0
    print("ok entry: only on a grace throw; grace keeps the same player")


def test_grace_extra_turn():
    g = Pachisi()
    s = g.initial_state(rng=random.Random(0))
    # set a piece on the track for player 0 so a grace move is available
    s = _fixed_throw(g, s, 6)
    s.positions[0][0] = 10
    moves = g.legal_moves(s)
    # advance the on-track piece by 6
    frm = PATH[0][10]; to = PATH[0][16]
    mv = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
    assert mv in moves, (mv, moves)
    s2 = g.apply_move(s, mv, rng=random.Random(3))
    assert s2.to_move == 0, "grace (6) must grant an extra turn (same player)"
    # a non-grace throw passes the turn
    s = _fixed_throw(g, s, 3)
    s.positions[0][0] = 10
    frm = PATH[0][10]; to = PATH[0][13]
    s3 = g.apply_move(s, f"{frm[0]},{frm[1]}>{to[0]},{to[1]}", rng=random.Random(3))
    assert s3.to_move == 1, "non-grace throw must pass the turn on"
    print("ok grace: 6/10/25 grant an extra turn; others pass the turn on")


def test_capture():
    g = Pachisi()
    s = g.initial_state(rng=random.Random(0))
    # find a non-castle main-track index for player 0's path
    target_idx = None
    for i in range(1, FINISH):
        cell = PATH[0][i]
        if cell in MAIN_TRACK and cell not in CASTLES:
            target_idx = i
            break
    assert target_idx is not None
    target_cell = PATH[0][target_idx]
    # place player 1 on that very cell (find its index on player 1's path)
    p1_idx = PATH[1].index(target_cell)
    s.positions[0][0] = target_idx - 3
    s.positions[1][0] = p1_idx
    s = _fixed_throw(g, s, 3)
    frm = PATH[0][target_idx - 3]
    mv = f"{frm[0]},{frm[1]}>{target_cell[0]},{target_cell[1]}"
    assert mv in g.legal_moves(s), (mv, g.legal_moves(s))
    s2 = g.apply_move(s, mv, rng=random.Random(9))
    assert s2.positions[1][0] == -1, "captured enemy must return to the Charkoni"
    assert s2.positions[0][0] == target_idx
    print("ok capture: landing on an enemy on a non-castle main square sends it home")


def test_castle_is_safe():
    g = Pachisi()
    s = g.initial_state(rng=random.Random(0))
    # pick a castle square that is on the main track and on player 0's path
    castle_idx = None
    for i in range(1, FINISH):
        if PATH[0][i] in CASTLES and PATH[0][i] in MAIN_TRACK:
            castle_idx = i
            break
    assert castle_idx is not None
    castle_cell = PATH[0][castle_idx]
    p1_idx = PATH[1].index(castle_cell)
    s.positions[0][0] = castle_idx - 2
    s.positions[1][0] = p1_idx           # enemy sitting safely on the castle
    s = _fixed_throw(g, s, 2)
    frm = PATH[0][castle_idx - 2]
    mv = f"{frm[0]},{frm[1]}>{castle_cell[0]},{castle_cell[1]}"
    s2 = g.apply_move(s, mv, rng=random.Random(9))
    assert s2.positions[1][0] == p1_idx, "a piece on a castle square must be SAFE"
    print("ok castle: a piece on a castle square cannot be captured")


def test_exact_finish():
    g = Pachisi()
    s = g.initial_state(rng=random.Random(0))
    # piece 2 short of home (FINISH-2). Throw 3 overshoots -> not legal.
    s.positions[0][0] = FINISH - 2
    s_over = _fixed_throw(g, s, 3)
    moves = g.legal_moves(s_over)
    assert not any(mv.endswith(">home") for mv in moves), moves
    # exact throw (2) brings it home
    s_exact = _fixed_throw(g, s, 2)
    frm = PATH[0][FINISH - 2]
    mv = f"{frm[0]},{frm[1]}>home"
    assert mv in g.legal_moves(s_exact), (mv, g.legal_moves(s_exact))
    s2 = g.apply_move(s_exact, mv, rng=random.Random(1))
    assert s2.positions[0][0] == FINISH
    print("ok finish: home only on the exact count (overshoot illegal)")


def test_win_and_returns():
    g = Pachisi()
    s = g.initial_state(rng=random.Random(0))
    # three of player 0's pieces home, the last 2 from home
    s.positions[0] = [FINISH, FINISH, FINISH, FINISH - 2]
    s = _fixed_throw(g, s, 2)
    frm = PATH[0][FINISH - 2]
    s2 = g.apply_move(s, f"{frm[0]},{frm[1]}>home", rng=random.Random(0))
    assert g.is_terminal(s2)
    assert s2.winner == 0
    r = g.returns(s2)
    assert r == [1.0, -1.0, -1.0, -1.0], r
    print("ok win: 4 home reached via apply_move; returns = [+1,-1,-1,-1]")


def test_serialize_roundtrip():
    g = Pachisi()
    s = g.initial_state(rng=random.Random(42))
    s.positions[0][0] = 5
    s.positions[2][1] = FINISH
    s.roll = 25
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d
    import json
    json.dumps(d)                     # JSON-able
    assert s2.roll == 25
    print("ok serialize: round-trips (incl. stored throw)")


def test_random_play_terminates():
    g = Pachisi()
    for seed in range(40):
        rng = random.Random(seed)
        s = g.initial_state(rng=rng)
        steps = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            assert moves, "non-terminal state with no legal moves"
            s = g.apply_move(s, rng.choice(moves), rng=rng)
            steps += 1
            assert steps < 100_000
        assert s.winner is not None
        r = g.returns(s)
        assert len(r) == 4 and sum(r) == -2.0   # +1 + three -1
    print("ok playouts: 40 random games all terminate with a winner")


if __name__ == "__main__":
    test_geometry()
    test_cowrie_distribution()
    test_entry_requires_grace()
    test_grace_extra_turn()
    test_capture()
    test_castle_is_safe()
    test_exact_finish()
    test_win_and_returns()
    test_serialize_roundtrip()
    test_random_play_terminates()
    print("\nall tests passed")
