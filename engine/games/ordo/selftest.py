"""Ordo correctness anchors (pure stdlib: agp + this game only).

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/ordo/selftest.py
"""

from pathlib import Path

from agp.loader import load_from_dir
from games.ordo.game import OrdoState, _connected

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _state(c0, c1, to_move=0):
    b = {}
    for c in c0:
        b[c] = 0
    for c in c1:
        b[c] = 1
    return OrdoState(board=b, to_move=to_move)


def test_setup():
    """(a) 10x8 board, two crenellated rows per player, 20 men each, matching the
    published nestorgames / Zillions starting position; both groups connected."""
    s = G.initial_state()
    b = s.board
    assert sum(1 for v in b.values() if v == 0) == 20
    assert sum(1 for v in b.values() if v == 1) == 20
    files = "abcdefghij"
    expect = {(files.index(x[0]), int(x[1]) - 1)
              for x in "a2 a3 b2 b3 c1 c2 d1 d2 e2 e3 f2 f3 g1 g2 h1 h2 i2 i3 j2 j3".split()}
    assert {p for p, pl in b.items() if pl == 0} == expect
    # Dark is the mirror across the middle rank.
    assert {(c, 7 - r) for (c, r) in expect} == {p for p, pl in b.items() if pl == 1}
    assert _connected(p for p, pl in b.items() if pl == 0)
    assert _connected(p for p, pl in b.items() if pl == 1)


def test_singleton_directions():
    """(b) A singleton slides forward / sideways / forward-diagonal; NEVER backward
    while the group is connected."""
    s = _state([(5, 4)], [(0, 0)])  # a lone White man (always a connected group)
    lm = set(G.legal_moves(s))
    assert "5,4>5,5" in lm          # forward
    assert "5,4>6,4" in lm and "5,4>4,4" in lm       # sideways
    assert "5,4>6,5" in lm and "5,4>4,5" in lm       # forward diagonals
    assert "5,4>5,3" not in lm      # backward orthogonal forbidden
    assert "5,4>6,3" not in lm and "5,4>4,3" not in lm   # backward diagonals forbidden
    # long slide over empty squares
    assert "5,4>5,7" in lm


def test_singleton_capture():
    """A singleton captures by ending on an enemy man; it cannot slide past one."""
    s = _state([(4, 3)], [(4, 5), (0, 0)])
    lm = set(G.legal_moves(s))
    assert "4,3>4,5" in lm          # capture the enemy at (4,5)
    assert "4,3>4,6" not in lm      # cannot jump past it
    ns = G.apply_move(s, "4,3>4,5")
    assert (4, 5) in [p for p, pl in ns.board.items() if pl == 0]
    assert not any(pl == 1 and p == (4, 5) for p, pl in ns.board.items())


def test_ordo_moves():
    """(c) A straight line of 2+ men (an ordo) slides together, perpendicular to
    its axis, keeping formation; the destination squares must be empty; it may not
    capture and may not go single-file (along its own axis)."""
    # Horizontal ordo cols 3-5 at row 2 -> moves forward (rank direction).
    s = _state([(3, 2), (4, 2), (5, 2)], [(0, 7)])
    lm = set(G.legal_moves(s))
    assert "3,2>5,2>3,3" in lm          # forward one square
    assert "3,2>5,2>3,6" in lm          # forward several squares
    ns = G.apply_move(s, "3,2>5,2>3,3")
    assert sorted(p for p, pl in ns.board.items() if pl == 0) == [(3, 3), (4, 3), (5, 3)]
    # No single-file (along-axis) horizontal ordo move.
    for mv in lm:
        if mv.count(">") == 2:
            a, _b, dest = mv.split(">")
            assert dest.split(",")[1] != a.split(",")[1]   # rank must change (perpendicular)
    # Ordo may not capture / slide onto an occupied square.
    s2 = _state([(3, 2), (4, 2), (5, 2)], [(4, 3), (0, 7)])
    assert "3,2>5,2>3,3" not in set(G.legal_moves(s2))
    # Vertical ordo (col 2, rows 2-4) slides sideways (file direction), both ways.
    s3 = _state([(2, 2), (2, 3), (2, 4)], [(0, 7)])
    lm3 = set(G.legal_moves(s3))
    assert "2,2>2,4>3,2" in lm3 and "2,2>2,4>1,2" in lm3
    ns3 = G.apply_move(s3, "2,2>2,4>3,2")
    assert sorted(p for p, pl in ns3.board.items() if pl == 0) == [(3, 2), (3, 3), (3, 4)]


def test_connection_rule():
    """(d) After a move the mover's group must stay connected (8-connectivity); a
    move that would split the group is illegal."""
    s = _state([(4, 4), (5, 5)], [(0, 0)])   # two diagonally-connected men
    lm = set(G.legal_moves(s))
    assert "5,5>5,6" not in lm       # would leave (4,4) & (5,6) disconnected -> illegal
    assert "5,5>4,5" in lm           # (4,4)&(4,5) stay adjacent -> legal
    for mv in lm:                    # every legal move keeps the group connected
        ns = G.apply_move(s, mv)
        assert _connected(p for p, pl in ns.board.items() if pl == 0)


def test_reconnection_allows_backward():
    """(d) When the group starts a turn disconnected (split by the opponent's
    capture), backward moves become available and every legal move must reconnect
    the group into one piece."""
    s = _state([(5, 0), (0, 0)], [(0, 7)])   # White split; must reconnect
    assert not _connected([(5, 0), (0, 0)])
    lm = G.legal_moves(s)
    assert lm and "5,0>1,0" in set(lm)       # slide the stray man back beside (0,0)
    for mv in lm:
        ns = G.apply_move(s, mv)
        assert _connected(p for p, pl in ns.board.items() if pl == 0)


def test_win_reach_home_row():
    """(e) Landing a man on the opponent's home row wins immediately."""
    s = _state([(4, 6), (4, 5)], [(0, 0)])
    ns = G.apply_move(s, "4,6>4,7")          # row 7 = Black's home row
    assert ns.winner == 0
    assert G.is_terminal(ns) and G.returns(ns) == [1.0, -1.0]


def test_win_annihilation():
    """(e) Capturing the opponent's last man wins."""
    s = _state([(3, 3)], [(3, 4)])
    ns = G.apply_move(s, "3,3>3,4")
    assert ns.winner == 0
    assert not any(pl == 1 for pl in ns.board.values())


def test_win_cannot_reconnect():
    """(e) If the opponent is left disconnected AND has no move that reconnects
    their group, they lose immediately."""
    white = [(4, 2), (4, 5)]                 # split by a gap of two, fully boxed
    cage = sorted({(3, 2), (5, 2), (4, 1), (4, 3), (3, 1), (5, 1), (3, 3), (5, 3),
                   (3, 5), (5, 5), (4, 4), (4, 6), (3, 4), (5, 4), (3, 6), (5, 6)})
    s = _state(white, cage + [(6, 3)], to_move=1)
    assert not _connected(white)
    assert G._raw_moves(s.board, 0) == []    # White is immobile
    ns = G.apply_move(s, "6,3>6,2")          # Black plays an unrelated man
    assert ns.winner == 1
    assert G.returns(ns) == [-1.0, 1.0]


def test_random_playouts_terminate():
    """(f) Random games always reach a terminal state (the ply cap guarantees it)."""
    import random
    rng = random.Random(12345)
    for _ in range(6):
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            steps += 1
            assert steps <= 400
        assert len(G.returns(s)) == 2


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ordo selftest: all passed")


if __name__ == "__main__":
    run()
