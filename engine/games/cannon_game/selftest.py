"""Cannon correctness anchors (pure stdlib: agp + this game only).

Anchored on the official nestorgames rulebook (CANNON_EN.pdf), the author's
Zillions Cannont.zrf (submission id=150: exact opening array, move macros) and
boardspace.net/iggamecenter rule pages.

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/cannon_game/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.cannon_game.game import CNState, PLY_CAP, N

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _state(s0=(), s1=(), t0=(1, 0), t1=(8, 9), to_move=0, ply=10):
    """A mid-game state: soldiers per seat + both towns already placed."""
    b = {c: (0, "S") for c in s0}
    b.update({c: (1, "S") for c in s1})
    if t0:
        b[t0] = (0, "T")
    if t1:
        b[t1] = (1, "T")
    return CNState(board=b, to_move=to_move, ply=ply)


def test_setup_and_town_placement():
    """(zrf board-setup) Black: a2-a4,c,e,g,i; Red: b7-b9,d,f,h,j; towns placed
    on the back ranks excluding corners as the first two moves, Black first."""
    s = G.initial_state()
    black = {p for p, v in s.board.items() if v == (0, "S")}
    red = {p for p, v in s.board.items() if v == (1, "S")}
    assert black == {(c, r) for c in (0, 2, 4, 6, 8) for r in (1, 2, 3)}
    assert red == {(c, r) for c in (1, 3, 5, 7, 9) for r in (6, 7, 8)}
    assert len(s.board) == 30                      # no towns yet
    assert G.current_player(s) == 0                # Black (dark) moves first

    lm = G.legal_moves(s)
    assert sorted(lm) == sorted(f"{c},0" for c in range(1, 9))   # b1..i1, no corners
    assert "0,0" not in lm and "9,0" not in lm

    s = G.apply_move(s, "4,0")                     # Black town e1
    assert s.board[(4, 0)] == (0, "T")
    lm = G.legal_moves(s)
    assert sorted(lm) == sorted(f"{c},{N - 1}" for c in range(1, 9))
    s = G.apply_move(s, "5,9")                     # Red town f10
    assert s.board[(5, 9)] == (1, "T")
    assert G.current_player(s) == 0 and s.ply == 2
    assert not G.is_terminal(s)


def test_soldier_step_and_capture():
    """Step forward straight/diagonal to empty; capture forward + SIDEWAYS only
    (never backward, never a sideways step to an empty point)."""
    s = _state(s0=[(4, 4)], s1=[(9, 9)])
    lm = set(G.legal_moves(s))
    from_44 = {m for m in lm if m.startswith("4,4>")}
    assert from_44 == {"4,4>3,5", "4,4>4,5", "4,4>5,5"}      # steps only

    # enemies all around: forward 3 + sideways 2 are captures; backward is not
    ring = [(3, 3), (4, 3), (5, 3), (3, 4), (5, 4), (3, 5), (4, 5), (5, 5)]
    s = _state(s0=[(4, 4)], s1=ring)
    lm = {m for m in set(G.legal_moves(s)) if m.startswith("4,4>")
          and max(abs(int(m.split(">")[1].split(",")[0]) - 4),
                  abs(int(m.split(">")[1].split(",")[1]) - 4)) == 1}
    assert lm == {"4,4>3,5", "4,4>4,5", "4,4>5,5", "4,4>3,4", "4,4>5,4"}

    # Red's forward is -r
    s = _state(s0=[(9, 0)], s1=[(4, 4)], to_move=1)
    from_44 = {m for m in G.legal_moves(s) if m.startswith("4,4>")}
    assert from_44 == {"4,4>3,3", "4,4>4,3", "4,4>5,3"}

    # capture applies: enemy removed, mover lands there
    s = _state(s0=[(4, 4)], s1=[(5, 4), (9, 9)])
    s2 = G.apply_move(s, "4,4>5,4")
    assert s2.board[(5, 4)] == (0, "S") and (4, 4) not in s2.board


def test_retreat():
    """Two points straight/diagonal back, only when adjacent to an ENEMY piece
    (Town counts), both points empty."""
    s = _state(s0=[(4, 4)])                        # no enemy adjacent
    assert not any(m.startswith("4,4>") and m.endswith(",2") for m in G.legal_moves(s))

    s = _state(s0=[(4, 4)], s1=[(4, 5)])           # enemy adjacent
    rets = {m for m in G.legal_moves(s) if m.startswith("4,4>")
            and int(m.split(">")[1].split(",")[1]) == 2}
    assert rets == {"4,4>2,2", "4,4>4,2", "4,4>6,2"}

    # blocked intermediate or landing point kills that retreat only
    s = _state(s0=[(4, 4), (4, 3)], s1=[(4, 5)])       # own man on the mid point
    assert "4,4>4,2" not in G.legal_moves(s)
    s = _state(s0=[(4, 4), (2, 2)], s1=[(4, 5)])       # own man on the landing
    lm = G.legal_moves(s)
    assert "4,4>2,2" not in lm and "4,4>4,2" in lm

    # adjacency to the enemy TOWN also triggers the retreat (rulebook: "piece")
    s = _state(s0=[(7, 8)], s1=[(1, 6)], t1=(8, 9))
    assert "7,8>7,6" in G.legal_moves(s)

    # a retreat is never a capture: enemy on the landing blocks it
    s = _state(s0=[(4, 4)], s1=[(4, 5), (4, 2)])
    assert "4,4>4,2" not in G.legal_moves(s)


def test_cannon_detection_all_8_directions():
    """A 3-in-line cannon slides its rear soldier past the front in both
    directions along the line — all 4 orientations x 2 directions."""
    for d, line in [((0, 1), [(4, 3), (4, 4), (4, 5)]),
                    ((1, 0), [(3, 4), (4, 4), (5, 4)]),
                    ((1, 1), [(3, 3), (4, 4), (5, 5)]),
                    ((1, -1), [(3, 5), (4, 4), (5, 3)])]:
        s = _state(s0=line, s1=[(9, 9) if (9, 9) not in line else (9, 8)], t1=(8, 9))
        lm = set(G.legal_moves(s))
        rear_f, rear_b = line[0], line[2]
        to_f = (line[2][0] + d[0], line[2][1] + d[1])
        to_b = (line[0][0] - d[0], line[0][1] - d[1])
        assert f"{rear_f[0]},{rear_f[1]}>{to_f[0]},{to_f[1]}" in lm, (d, "fwd slide")
        assert f"{rear_b[0]},{rear_b[1]}>{to_b[0]},{to_b[1]}" in lm, (d, "back slide")

    # a Town never forms part of a cannon
    s = _state(s0=[(4, 1), (4, 2)], t0=(4, 0), s1=[(9, 9)])
    assert not any(m in G.legal_moves(s) for m in ("4,0>4,3", "4,1>4,4", "4,2>4,-1"))

    # slide target occupied -> no slide (and no shot through it)
    s = _state(s0=[(4, 2), (4, 3), (4, 4), (4, 5)], s1=[(4, 7)])
    lm = G.legal_moves(s)
    assert "4,2>4,5" not in lm and "4,2>4,6" not in lm and "4,2>4,7" not in lm


def test_cannon_shot_geometry():
    """Shot = capture at 2 or 3 points beyond the muzzle; the point directly in
    front must be EMPTY; the long shot may pass over an occupied middle point;
    the shooter does not move (rulebook + zrf cannon-shot-short/-long)."""
    # cannon 4,2-4,3-4,4 firing up: front point (4,5) empty
    s = _state(s0=[(4, 2), (4, 3), (4, 4)], s1=[(4, 6), (4, 7)])
    lm = set(G.legal_moves(s))
    assert "4,2>4,6" in lm                          # short shot (front+2)
    assert "4,2>4,7" in lm                          # long shot  (front+3)
    assert "4,2>4,5" in lm                          # (that string is the SLIDE — dist 3)
    # a shot can never land at front+1: with an enemy there both the slide and
    # every shot in that direction disappear (asserted below)

    # shot applies: target removed, all three soldiers stay put
    s2 = G.apply_move(s, "4,2>4,7")
    assert (4, 7) not in s2.board
    for c in [(4, 2), (4, 3), (4, 4)]:
        assert s2.board[c] == (0, "S")

    # front point occupied (even by the enemy) -> no shot in that direction
    s = _state(s0=[(4, 2), (4, 3), (4, 4)], s1=[(4, 5), (4, 7)])
    lm = set(G.legal_moves(s))
    assert "4,2>4,7" not in lm and "4,2>4,5" not in lm

    # long shot over an occupied MIDDLE point (friend there) is legal
    s = _state(s0=[(4, 2), (4, 3), (4, 4), (4, 6)], s1=[(4, 7)])
    assert "4,2>4,7" in G.legal_moves(s)

    # diagonal shot
    s = _state(s0=[(1, 1), (2, 2), (3, 3)], s1=[(5, 5), (6, 6)], t0=(1, 0))
    lm = set(G.legal_moves(s))
    assert "1,1>5,5" in lm and "1,1>6,6" in lm

    # a shot needs an enemy target: friendly piece at range is not shootable
    s = _state(s0=[(4, 2), (4, 3), (4, 4), (4, 7)], s1=[(9, 9)])
    assert "4,2>4,7" not in G.legal_moves(s)


def test_win_by_town_capture_and_shot():
    """Winner is an EVENT set by apply_move: soldier capture of the Town, and a
    cannon shot on the Town, both end the game immediately."""
    # soldier walks onto the Red town (sideways capture)
    s = _state(s0=[(7, 9)], s1=[(1, 5)], t1=(8, 9))
    s2 = G.apply_move(s, "7,9>8,9")
    assert s2.winner == 0 and G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0]

    # cannon shoots the Black town (Red to move): rear (4,5), muzzle (4,3),
    # front point (4,2) empty, town at (4,0) = long shot
    s = _state(s0=[(9, 5)], s1=[(4, 3), (4, 4), (4, 5)], t0=(4, 0), t1=(8, 9), to_move=1)
    assert "4,5>4,0" in G.legal_moves(s)
    s2 = G.apply_move(s, "4,5>4,0")
    assert s2.winner == 1 and G.is_terminal(s2) and G.returns(s2) == [-1.0, 1.0]
    for c in [(4, 3), (4, 4), (4, 5)]:
        assert s2.board[c] == (1, "S")             # shooters stayed
    assert (4, 0) not in s2.board                  # town destroyed


def test_stalemate_and_annihilation():
    """No legal move -> the stuck player loses (all sources). A player whose
    soldiers are all gone has no move at all (the Town cannot move)."""
    # reach annihilation via apply_move: Black's last soldier is captured
    s = _state(s0=[(4, 4)], s1=[(4, 5)], to_move=1)
    s2 = G.apply_move(s, "4,5>4,4")                # Red captures the last soldier
    assert G.current_player(s2) == 0 and G.legal_moves(s2) == []
    assert G.is_terminal(s2) and G.returns(s2) == [-1.0, 1.0]

    # fully blocked player loses too (soldier on the last rank, boxed in)
    s = _state(s0=[(0, 9)], s1=[(1, 8), (0, 8), (9, 0)], t0=(1, 0), t1=(8, 9))
    # Black soldier at a10: no forward (off board), captures? (1,9) empty,
    # sideways (1,9) empty -> no capture; retreat needs both points empty but
    # (0,8)/(1,8) hold enemies -> no move.
    assert G.current_player(s) == 0
    assert G.legal_moves(s) == []
    assert G.is_terminal(s) and G.returns(s) == [-1.0, 1.0]


def test_threefold_repetition_draw():
    """Two cannons sliding to and fro repeat the position -> honest draw."""
    s = _state(s0=[(0, 2), (0, 3), (0, 4)], s1=[(9, 5), (9, 6), (9, 7)])
    cycle = ["0,2>0,5", "9,7>9,4",                 # both cannons slide
             "0,5>0,2", "9,4>9,7"]                 # ... and slide back
    moves = 0
    for _ in range(4):
        for m in cycle:
            assert m in G.legal_moves(s), (m, moves)
            s = G.apply_move(s, m)
            moves += 1
            if G.is_terminal(s):
                assert G.returns(s) == [0.0, 0.0], "repetition must be a DRAW"
                assert s.repeats >= 3
                return
    raise AssertionError("threefold repetition never triggered")


def test_serialize_roundtrip():
    s = G.initial_state()
    for m in ("3,0", "6,9", "0,3>0,4"):
        s = G.apply_move(s, m)
    d = G.serialize(s)
    s2 = G.deserialize(d)
    assert G.serialize(s2) == d
    assert s2.board == s.board and s2.reps == s.reps and s2.repeats == s.repeats


def test_playout_stats():
    """500 random playouts: all terminate; report length + outcome stats."""
    rng = random.Random(20260711)
    lens, outcomes, reasons = [], {0: 0, 1: 0, "draw": 0}, {}
    for _ in range(500):
        s = G.initial_state()
        n = 0
        while not G.is_terminal(s):
            lm = G.legal_moves(s)
            assert lm, "non-terminal state with no moves"
            assert len(set(lm)) == len(lm), "duplicate move strings"
            s = G.apply_move(s, rng.choice(lm))
            n += 1
            assert n <= PLY_CAP + 2, "playout exceeded the ply cap"
        lens.append(n)
        ret = G.returns(s)
        assert len(ret) == 2 and all(isinstance(x, float) for x in ret)
        if s.winner is not None:
            outcomes[s.winner] += 1
            reasons["town captured"] = reasons.get("town captured", 0) + 1
        elif s.repeats >= 3:
            outcomes["draw"] += 1
            reasons["repetition"] = reasons.get("repetition", 0) + 1
        elif s.ply >= PLY_CAP:
            outcomes["draw"] += 1
            reasons["ply cap"] = reasons.get("ply cap", 0) + 1
        else:
            outcomes[1 - s.to_move] += 1
            reasons["stalemate"] = reasons.get("stalemate", 0) + 1
    print(f"  playouts: 500  len avg={sum(lens) / len(lens):.1f} "
          f"min={min(lens)} max={max(lens)}")
    print(f"  outcomes: Black={outcomes[0]} Red={outcomes[1]} draw={outcomes['draw']}")
    print(f"  reasons:  {reasons}")


def main():
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        fn()
        print(f"ok {name}")
    print(f"cannon_game selftest: {len(tests)} checks passed")


if __name__ == "__main__":
    main()
