"""Odd-Y correctness anchor (pure stdlib: agp + this game only).

Asserts:
  * (a) the precomputed winning-triple tables for m = 5 and m = 7 match a
    brute-force GEOMETRIC check (triangle of side midpoints contains the board
    centre), with the published counts (pentagon 5/10, heptagon 14/35) and the
    pentagon's losing triples = the 5 rotations of 3 consecutive sides;
  * geometry: cell counts m*n^2+m*n+1, m corners, symmetric adjacency, each
    corner on exactly its two adjacent sides;
  * placement legality + the pie/swap move;
  * (b) a hand-built pentagon winning line (two spokes joined by the centre,
    touching sides {0,1,2,3}) is detected EXACTLY when completed, and a group
    touching only 3 CONSECUTIVE sides does NOT win;
  * (d) corner cells count for BOTH adjacent sides: a group whose only contact
    with sides 0 and 1 is corner 1 wins the {0,1,3} triple the moment the
    corner is placed;
  * (c) full random playouts (pentagon and heptagon) reach a terminal state
    with a single winner and +1/-1 returns;
  * serialize round-trips and render emits the polygons list format.

Run directly:  PYTHONPATH=. python3 games/odd_y/selftest.py
"""
import math
import os
import random
import sys
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from games.odd_y.game import (  # noqa: E402
    OddY, BLACK, WHITE,
    _cells, _adj, _corners, _sides, _winning_triples,
    _group_sides, _key,
)


# ---------------------------------------------------------------------------
# (a) geometric brute force: midpoint triangle contains the centre?
# ---------------------------------------------------------------------------

def _geometric_winning_triples(m):
    """Winning triples straight from the published rule: the triangle between
    the midpoints of the three sides contains the board's centre (origin)."""
    mids = []
    for k in range(m):
        th = 2.0 * math.pi * (k + 0.5) / m      # side k's midpoint direction
        mids.append((math.cos(th), math.sin(th)))

    def cross(p, q):
        return p[0] * q[1] - p[1] * q[0]

    win = set()
    for tri in combinations(range(m), 3):
        a, b, c = (mids[t] for t in tri)
        s1, s2, s3 = cross(a, b), cross(b, c), cross(c, a)
        # strictly inside (m odd -> the degenerate through-centre case cannot
        # occur, verified below)
        assert s1 != 0 and s2 != 0 and s3 != 0, ("degenerate triple", m, tri)
        if (s1 > 0) == (s2 > 0) == (s3 > 0):
            win.add(frozenset(tri))
    return win


def _fill_alternating(game, state, black_cells, white_cells):
    """Play black_cells / white_cells strictly alternating (Black first),
    asserting the game is NOT over before the final black stone."""
    assert len(white_cells) == len(black_cells) - 1
    for t in range(len(black_cells) + len(white_cells)):
        assert not game.is_terminal(state), ("early terminal at ply", t)
        assert state.winner is None
        cell = black_cells[t // 2] if t % 2 == 0 else white_cells[t // 2]
        state = game.apply_move(state, _key(cell))
    return state


def main():
    g = OddY()

    # ---- (a) winning-triple tables vs geometric brute force ---------------
    for m, expect_win, expect_total in ((5, 5, 10), (7, 14, 35)):
        table = _winning_triples(m)
        geo = _geometric_winning_triples(m)
        assert table == geo, (m, sorted(map(sorted, table ^ geo)))
        assert len(table) == expect_win, (m, len(table))
        assert len(list(combinations(range(m), 3))) == expect_total
    # pentagon: losing triples are exactly the 5 rotations of 3-consecutive
    losing5 = {frozenset((k % 5, (k + 1) % 5, (k + 2) % 5)) for k in range(5)}
    all5 = {frozenset(t) for t in combinations(range(5), 3)}
    assert all5 - _winning_triples(5) == losing5
    # heptagon: losing = fits within 4 consecutive sides (max cyclic gap >= 4)
    for tri in combinations(range(7), 3):
        a, b, c = tri
        fits4 = max(b - a, c - b, 7 - c + a) >= 4
        assert (frozenset(tri) in _winning_triples(7)) == (not fits4), tri

    # ---- geometry ----------------------------------------------------------
    for m in (5, 7):
        for n in (3, 4):
            cells = _cells(m, n)
            adj = _adj(m, n)
            corners = _corners(m, n)
            sides = _sides(m, n)
            assert len(cells) == m * n * n + m * n + 1, (m, n, len(cells))
            assert len(set(cells)) == len(cells)
            assert len(corners) == m and len(sides) == m
            for c in cells:
                for d in adj[c]:
                    assert c in adj[d] and d != c, ("asymmetric", c, d)
            for k in range(m):
                assert len(sides[k]) == 2 * n + 1, (m, n, k)
                cor = corners[k]
                belongs = sorted(x for x in range(m) if cor in sides[x])
                assert belongs == sorted([(k - 1) % m, k]), (m, k, belongs)

    # ---- placement + pie ---------------------------------------------------
    s0 = g.initial_state(options={"sides": 5, "size": 4})
    assert s0.to_move == BLACK
    lm = g.legal_moves(s0)
    assert len(lm) == 101 and "swap" not in lm
    s1 = g.apply_move(s0, "c")
    assert s1.to_move == WHITE and s1.board[("c",)] == BLACK
    assert "swap" in g.legal_moves(s1)
    s2 = g.apply_move(s1, "swap")
    assert s2.board[("c",)] == WHITE and s2.to_move == BLACK
    assert "swap" not in g.legal_moves(s2)
    for bad in ("c", "f,0,99,99"):
        try:
            g.apply_move(s1, bad)
            assert False, ("expected illegal", bad)
        except ValueError:
            pass
    # pie off -> no swap offered
    s_nopie = g.apply_move(g.initial_state(options={"pie": False}), "c")
    assert "swap" not in g.legal_moves(s_nopie)

    # ---- (b) hand-built pentagon win, detected exactly when completed ------
    n = 4
    black = ([("s", 1, i) for i in range(1, n + 1)]        # spoke 1 (corner 1: sides 0,1)
             + [("s", 3, i) for i in range(1, n + 1)]      # spoke 3 (corner 3: sides 2,3)
             + [("c",)])                                   # centre joins them LAST
    white = [("f", 0, i, j) for i in range(1, 4) for j in range(1, 4)][:len(black) - 1]
    st = _fill_alternating(g, g.initial_state(options={"pie": False}), black, white)
    assert st.over and st.winner == BLACK, (st.over, st.winner)
    assert g.returns(st) == [1.0, -1.0]
    touched = _group_sides(st.board, _adj(5, n), _sides(5, n), ("c",))
    assert touched == {0, 1, 2, 3}, touched
    assert set(st.win_triple) <= touched and frozenset(st.win_triple) in _winning_triples(5)

    # control: a group touching ONLY 3 consecutive sides does NOT win.
    sides5 = _sides(5, n)
    arc = set().union(sides5[0], sides5[1], sides5[2])
    arc -= {("s", 0, n), ("s", 3, n)}          # drop the end corners (sides 4|0 and 3)
    black = sorted(arc, key=_key)
    interior = [c for c in _cells(5, n)
                if not any(c in sides5[k] for k in range(5)) and c not in black]
    white = [c for c in interior if c != ("c",)][:len(black) - 1]
    st = _fill_alternating(g, g.initial_state(options={"pie": False}), black, white)
    assert not st.over and st.winner is None, "3 consecutive sides must not win"
    tb = _group_sides(st.board, _adj(5, n), sides5, black[0])
    assert tb == {0, 1, 2}, tb

    # ---- (d) the corner counts for BOTH its sides ---------------------------
    # Group: side-3 cell f,3,4,3 -> up sector 3 -> centre -> spoke 1 -> corner 1
    # placed LAST. Before the corner it touches only side 3 (no win); the corner
    # alone contributes sides 0 AND 1, completing the winning triple {0,1,3}.
    black = ([("f", 3, 4, 3), ("f", 3, 3, 3), ("f", 3, 3, 2), ("f", 3, 3, 1)]
             + [("s", 3, i) for i in (3, 2, 1)] + [("c",)]
             + [("s", 1, i) for i in (1, 2, 3)]
             + [("s", 1, 4)])                              # corner 1 LAST
    white = ([("f", 1, i, j) for i in range(1, 4) for j in range(1, 4)]
             + [("f", 0, 1, 1), ("f", 0, 2, 1)])[:len(black) - 1]
    st = _fill_alternating(g, g.initial_state(options={"pie": False}), black, white)
    assert st.over and st.winner == BLACK
    assert tuple(sorted(st.win_triple)) == (0, 1, 3), st.win_triple
    cor = ("s", 1, 4)
    assert cor in sides5[0] and cor in sides5[1]           # dual membership
    touched = _group_sides(st.board, _adj(5, n), sides5, cor)
    assert touched == {0, 1, 3}, touched                   # sides 0,1 ONLY via the corner

    # ---- (c) random playouts terminate with a single winner ----------------
    for m, n, games in ((5, 3, 6), (5, 4, 3), (7, 3, 4)):
        rng = random.Random(1000 * m + n)
        total = len(_cells(m, n))
        for _ in range(games):
            s = g.initial_state(options={"sides": m, "size": n})
            plies = 0
            while not g.is_terminal(s):
                s = g.apply_move(s, rng.choice(g.legal_moves(s)))
                plies += 1
                assert plies <= total + 2, "did not terminate"
            assert s.winner in (BLACK, WHITE), ("drawless violated", m, n)
            r = g.returns(s)
            assert sorted(r) == [-1.0, 1.0] and r[s.winner] == 1.0

    # ---- serialize round-trip + render shape --------------------------------
    for m in (5, 7):
        s = g.initial_state(options={"sides": m, "size": 3})
        s = g.apply_move(s, _key(_corners(m, 3)[0]))
        s = g.apply_move(s, "c")
        d = g.serialize(s)
        s2 = g.deserialize(d)
        assert g.serialize(s2) == d
        import json
        json.dumps(d)
        r = g.render(s)
        assert r["board"]["type"] == "polygons"
        assert isinstance(r["board"]["cells"], list)
        assert all("points" in c and "id" in c for c in r["board"]["cells"])
        ids = {c["id"] for c in r["board"]["cells"]}
        assert ids == {_key(c) for c in _cells(m, 3)}      # ids match move strings
        assert g.describe_move(g.initial_state(options={"sides": m}),
                               _key(_corners(m, 4)[2])).endswith("*")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
