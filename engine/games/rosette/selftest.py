"""Rosette correctness anchor (pure stdlib, fast).

Pins: (a) the honeycomb-vertex board (6*n^2 points, interior degree 3, boundary
degree 2, consistent hex faces); (b) liberty capture, illegal suicide, and
legal capturing-suicide; (c) the ROSETTE immunity rule (a group holding a full
hexagon is never captured, even at zero liberties); (d) situational superko
(a ko may not be recaptured into a repeated position); (e) Chinese/area scoring
with komi; (f) termination on every board size.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.rosette.game import (  # noqa: E402
    Rosette, RosetteState, _geo, _group, _has_liberty, _has_rosette,
    _resolve, _score, _board_key, BLACK, WHITE)

G = Rosette()


def _seed(board, to_move):
    geo = _geo(5)
    s = RosetteState(size=5, komi=4.5, board=dict(board), to_move=to_move)
    s.history = frozenset({(_board_key(board, geo), to_move)})
    return s


def main():
    # ---- (a) board geometry ------------------------------------------------
    for n in (5, 6, 7):
        geo = _geo(n)
        assert geo.N == 6 * n * n, (n, geo.N)
        degs = [len(geo.neigh[v]) for v in range(geo.N)]
        assert all(d in (2, 3) for d in degs)
        assert sum(1 for d in degs if d == 3) == 6 * (n - 1) * n  # interior count
        assert len(geo.hexes) == 3 * (n - 1) ** 2 + 3 * (n - 1) + 1
        # adjacency is symmetric; every hex is a 6-cycle of real edges
        for v in range(geo.N):
            for w in geo.neigh[v]:
                assert v in geo.neigh[w]
        for h in geo.hexes:
            assert len(set(h)) == 6
            for i in range(6):
                assert h[(i + 1) % 6] in geo.neigh[h[i]]

    geo = _geo(5)

    # ---- (b) capture: a stone at a degree-3 point has 3 liberties ----------
    #  BLACK victim at 3 (neigh 0,2,8); WHITE on 0,2 then plays 8 -> capture.
    s = _seed({3: BLACK, 0: WHITE, 2: WHITE}, WHITE)
    s2 = G.apply_move(s, "8")
    assert 3 not in s2.board and s2.board.get(8) == WHITE, "surround must capture"

    # ---- suicide is illegal ------------------------------------------------
    s = _seed({0: WHITE, 2: WHITE, 8: WHITE}, BLACK)   # empty 3 ringed by white
    assert "3" not in G.legal_moves(s), "suicide must be illegal"

    # ---- capturing-suicide is legal ---------------------------------------
    #  BLACK plays 8 (its own neighbours 3,9,15 all occupied) but captures the
    #  lone WHITE at 3 -> legal despite otherwise being self-atari.
    s = _seed({3: WHITE, 9: WHITE, 15: WHITE, 0: BLACK, 2: BLACK}, BLACK)
    assert "8" in G.legal_moves(s), "capturing-suicide must be legal"
    s2 = G.apply_move(s, "8")
    assert 3 not in s2.board and s2.board.get(8) == BLACK

    # ---- (c) ROSETTE immunity ---------------------------------------------
    hexv = list(_geo(5).hexes[6])            # (42,52,51,41,31,32), interior
    outward = [21, 22, 40, 43, 61, 62]        # the six external liberties
    # Build a rosette THROUGH apply_move (place the 6th stone), then let the
    # enemy fill every liberty and confirm the group is never removed.
    pre = {v: BLACK for v in hexv[:-1]}       # 5 of 6 black
    s = _seed(pre, BLACK)
    s = G.apply_move(s, str(hexv[-1]))        # complete the rosette
    assert all(s.board.get(v) == BLACK for v in hexv)
    for i, w in enumerate(outward):
        s = G.apply_move(s, str(w))           # WHITE fills a liberty
        assert all(s.board.get(v) == BLACK for v in hexv), "rosette must survive"
        if i < len(outward) - 1:
            s = G.apply_move(s, "pass")       # BLACK passes
    grp = _group(s.board, hexv[0], _geo(5))
    assert grp == set(hexv)
    assert not _has_liberty(s.board, grp, _geo(5))   # zero liberties...
    assert _has_rosette(grp, _geo(5))                # ...but alive by rosette

    # direct contrast: the same zero-liberty board -- immune iff a full hexagon
    surround = {v: BLACK for v in hexv}
    surround.update({w: WHITE for w in outward[:-1]})
    nb, cap = _resolve(surround, outward[-1], WHITE, _geo(5))  # would-be kill
    assert all(v in nb for v in hexv) and cap == 0, "rosette exempt from capture"
    assert _has_rosette(set(hexv), _geo(5))
    assert not _has_rosette(set(hexv[:-1]), _geo(5))   # 5/6 is not a rosette

    # ---- (d) situational superko ------------------------------------------
    #  P0: WHITE{3,9,15} BLACK{0,2}, BLACK to move. Black 8 captures white-3;
    #  White recapturing at 3 would recreate P0 (BLACK to move) -> forbidden.
    s0 = _seed({3: WHITE, 9: WHITE, 15: WHITE, 0: BLACK, 2: BLACK}, BLACK)
    s1 = G.apply_move(s0, "8")                # black takes the ko
    assert s1.to_move == WHITE and 3 not in s1.board
    _, cap = _resolve(s1.board, 3, WHITE, _geo(5))  # white-3 captures black-8
    assert cap == 1, "ko recapture is a real capture (not suicide)"
    assert "3" not in G.legal_moves(s1), "ko recapture must be superko-illegal"

    # ---- (e) area scoring + komi ------------------------------------------
    assert _score({}, geo, 4.5) == (0, 4.5)                 # empty board
    assert _score({0: BLACK}, geo, 4.5) == (150, 4.5)       # one stone owns all
    assert _score({0: BLACK, 149: WHITE}, geo, 4.5) == (1, 5.5)  # rest is dame
    # terminal + returns via a genuine double-pass
    t = G.initial_state(options={"size": 5, "komi": 4.5})
    t = G.apply_move(t, "0")                                # a lone black stone
    t = G.apply_move(t, "pass")
    t = G.apply_move(t, "pass")
    assert G.is_terminal(t) and G.returns(t) == [1.0, -1.0]  # black controls all
    # komi 0 permits a draw
    d = G.initial_state(options={"size": 5, "komi": 0})
    d = G.apply_move(d, "pass")
    d = G.apply_move(d, "pass")
    assert G.is_terminal(d) and G.returns(d) == [0.0, 0.0]
    assert "pass" in G.legal_moves(G.initial_state())

    # ---- serialize round-trips --------------------------------------------
    s = G.apply_move(G.apply_move(G.initial_state(), "40"), "pass")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    # ---- (f) termination on every size ------------------------------------
    #  ply cap forces a terminal even without passes
    for n in (5, 6, 7):
        cap_state = RosetteState(size=n, ply=_geo(n).N * 2)
        assert G.is_terminal(cap_state)
    #  a full random game on the default size reaches a terminal
    rng = random.Random(7)
    st = G.initial_state(options={"size": 5, "komi": 4.5})
    steps = 0
    while not G.is_terminal(st):
        st = G.apply_move(st, rng.choice(G.legal_moves(st)))
        steps += 1
        assert steps <= _geo(5).N * 2 + 2
    assert G.is_terminal(st)
    #  bigger boards: exercise gameplay + confirm cap-driven termination cheaply
    for n in (6, 7):
        st = G.initial_state(options={"size": n})
        for _ in range(40):
            st = G.apply_move(st, rng.choice(G.legal_moves(st)))
        assert not G.is_terminal(st)

    print("rosette selftest OK")


if __name__ == "__main__":
    main()
