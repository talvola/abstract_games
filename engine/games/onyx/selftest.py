"""Standalone correctness anchor for Onyx (pure stdlib: agp + this game only).

Anchors (all against Larry Back's AG#4 article, "The Official Rules of Onyx"):
  * board graph invariants: 204 points = 144 grid + 60 checkerboard square
    midpoints; 565 edges = 264 grid + 240 midpoint spokes + 61 triangle
    diagonals; midpoint degree exactly 4 (its square's corners); interior
    corner-point degree 7; the article's notation examples (a5-b6 chain edge
    of Diagram 12, midpoint DE910's corners);
  * the official Diagram-9 setup;
  * the midpoint restriction (Diagram 8): blocked by ANY occupied corner,
    either colour;
  * capture (Diagram 10), the midpoint-occupied shield, the no-capture
    adjacent 2-2, and the double capture (Diagram 11) — all REACHED via
    apply_move;
  * connection wins for both colours incl. corner points serving both edges;
  * pie swap = transpose + recolour; transpose is a graph automorphism that
    exchanges the two goals and fixes the official setup;
  * official notation via describe_move (F6 / DE910 / trailing '*');
  * serialize round-trip and 200-random-playout termination.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.onyx.game import (  # noqa: E402
    BLACK, WHITE, PLY_CAP, N, Onyx, OnyxState,
    _ADJ, _MID_CORNERS, _OFFICIAL, _PT_SQUARES, _SQUARES, _TRANSPOSE,
    _BOTTOM, _LEFT, _RIGHT, _TOP, _pt,
)

G = Onyx()


def test_graph():
    corner_pts = [p for p in _ADJ if p not in _MID_CORNERS]
    assert len(corner_pts) == 144
    assert len(_MID_CORNERS) == 60
    assert len(_ADJ) == 204
    assert len(_SQUARES) == 60
    # symmetric adjacency + handshake edge count
    for a, nbs in _ADJ.items():
        for b in nbs:
            assert a in _ADJ[b], (a, b)
    n_edges = sum(len(v) for v in _ADJ.values()) // 2
    assert n_edges == 264 + 240 + 61, n_edges  # grid + midpoint spokes + diagonals
    # midpoints: degree exactly 4 = their square's corners
    for mid, cs in _MID_CORNERS.items():
        assert _ADJ[mid] == frozenset(cs), mid
    # interior corner points have degree 7 (4 grid + 2 midpoints + 1 diagonal)
    for c in range(1, N - 1):
        for r in range(1, N - 1):
            assert len(_ADJ[_pt(c, r)]) == 7, (c, r)
    # board corners (from the Diagram 9 lattice): a1/l12 keep their cell's
    # short diagonal (degree 3), l1/a12 are cut off by it (degree 2)
    assert _ADJ["a1"] == frozenset({"a2", "b1", "b2"})
    assert _ADJ["l1"] == frozenset({"k1", "l2"})
    assert _ADJ["a12"] == frozenset({"a11", "b12"})
    assert _ADJ["l12"] == frozenset({"l11", "k12", "k11"})
    # notation anchors from the article
    assert "b6" in _ADJ["a5"]          # Diagram 12's White chain edge a5-b6
    assert "b2" in _ADJ["a1"]          # "/" diagonal, even column cell
    assert "b3" in _ADJ["c2"]          # "\" diagonal, odd column cell
    assert "l2" in _ADJ["k1"]
    assert "k2" not in _ADJ["l1"]
    # square DE910: opposite corners are NOT directly joined, only via the mid
    assert "b4" not in _ADJ["a5"]
    assert "a4m" in _ADJ["a5"] and "a4m" in _ADJ["b4"]
    assert _ADJ["d9m"] == frozenset({"d9", "e9", "e10", "d10"})
    # every square's corner really corners it, and PT_SQUARES inverts SQUARES
    for i, (cs, mid) in enumerate(_SQUARES):
        assert mid in _MID_CORNERS
        for c in cs:
            assert i in _PT_SQUARES[c]


def test_transpose_automorphism():
    assert set(_TRANSPOSE) == set(_ADJ)
    for p, q in _TRANSPOSE.items():
        assert _TRANSPOSE[q] == p
        assert _ADJ[q] == frozenset(_TRANSPOSE[x] for x in _ADJ[p]), p
    assert {_TRANSPOSE[p] for p in _TOP} == _RIGHT
    assert {_TRANSPOSE[p] for p in _BOTTOM} == _LEFT
    # the official setup is fixed by transpose + recolour
    assert {_TRANSPOSE[p]: 1 - o for p, o in _OFFICIAL.items()} == _OFFICIAL


def test_setup_and_midpoint_rule():
    s = G.initial_state({"setup": "official"})
    assert s.stones == {"a6": BLACK, "a7": BLACK, "l6": BLACK, "l7": BLACK,
                        "f1": WHITE, "g1": WHITE, "f12": WHITE, "g12": WHITE}
    assert G.current_player(s) == BLACK and s.ply == 0
    moves = set(G.legal_moves(s))
    # midpoints of the four setup squares are blocked (two corners occupied)
    for m in ("a6m", "k6m", "f1m", "f11m"):
        assert m in _MID_CORNERS and m not in moves, m
    assert "d5m" in moves and "d5" in moves
    # placing on any corner of a square blocks its midpoint(s), either colour
    s2 = G.apply_move(s, "d5")
    m2 = set(G.legal_moves(s2))
    assert "d5m" not in m2 and "c4m" not in m2          # d5 corners both squares
    s3 = G.apply_move(s2, "e5")                          # White stone also blocks
    assert "d5m" not in set(G.legal_moves(s3))
    # empty setup
    e = G.initial_state({"setup": "empty"})
    assert e.stones == {} and "a6m" in set(G.legal_moves(e))


def _play(state, moves):
    for m in moves:
        assert m in G.legal_moves(state), m
        state = G.apply_move(state, m)
    return state


def test_capture():
    # Diagram 10 pattern on square d5/e5/e6/d6 (midpoint empty): White's d6
    # completes the 2-2 crosscut and captures Black's diagonal pair.
    e = G.initial_state({"setup": "empty"})
    s = _play(e, ["d5", "e5", "e6"])
    assert G.describe_move(s, "d6") == "D6*"
    s = G.apply_move(s, "d6")
    assert s.stones == {"e5": WHITE, "d6": WHITE}
    assert s.captured == ("d5", "e6") and s.winner is None
    # an occupied midpoint shields the square (rule amendment in the article)
    s = _play(e, ["d5m", "e5", "e6", "a1", "d5"])
    assert G.describe_move(s, "d6") == "D6"
    s = G.apply_move(s, "d6")
    assert len(s.stones) == 6 and s.captured == ()
    assert s.stones["d5"] == BLACK and s.stones["e6"] == BLACK
    # 2-2 but ADJACENT (not diagonal) pairs: no capture
    s = _play(e, ["d5", "e6", "e5", "d6"])
    assert len(s.stones) == 4 and s.captured == ()


def test_double_capture():
    # Diagram 11: e6 corners BOTH squares d5/e5/e6/d6 and e6/f6/f7/e7; Black's
    # e6 completes a crosscut on each -> all four White stones come off.
    e = G.initial_state({"setup": "empty"})
    s = _play(e, ["d5", "e5", "f7", "d6", "a12", "f6", "k1", "e7"])
    assert G.describe_move(s, "e6") == "E6**"
    s = G.apply_move(s, "e6")
    assert s.captured == ("d6", "e5", "e7", "f6")
    assert s.stones == {"d5": BLACK, "f7": BLACK, "a12": BLACK, "k1": BLACK,
                        "e6": BLACK}
    assert s.winner is None


def test_connection_wins():
    # Black: column a, a1 up to a12 (both ends are board corners -> they count
    # for the top/bottom edges even though they also sit on the left edge).
    e = G.initial_state({"setup": "empty"})
    seq = []
    for r in range(1, 13):
        seq.append(f"a{r}")
        if r < 12:
            seq.append(f"k{r}")
    s = _play(e, seq)
    assert s.winner == BLACK and G.is_terminal(s)
    assert G.returns(s) == [1.0, -1.0]
    assert s.conn_path and s.conn_path[0][0] == "a"
    assert set(s.conn_path) == {f"a{r}" for r in range(1, 13)}
    # White: row 1, a1 across to l1 (a1 serves the LEFT edge here, l1 the
    # RIGHT — the same corner points counting for their other edge).
    e = G.initial_state({"setup": "empty"})
    seq = []
    for c in "abcdefghijkl":
        seq.append(f"{c}8")   # Black filler row (horizontal = not Black's goal)
        seq.append(f"{c}1")
    s = _play(e, seq)
    assert s.winner == WHITE
    assert G.returns(s) == [-1.0, 1.0]
    assert set(s.conn_path) == {f"{c}1" for c in "abcdefghijkl"}
    # a chain THROUGH a midpoint: White a2 - a2m - b3 - ... is connected
    e = G.initial_state({"setup": "empty"})
    s = _play(e, ["k9", "a2m"])
    assert s.stones["a2m"] == WHITE
    assert "a2" in _ADJ["a2m"] and "b3" in _ADJ["a2m"]


def test_swap():
    # empty board: swap = transpose + recolour the lone opening stone
    e = G.initial_state({"setup": "empty"})
    s = G.apply_move(e, "c4")
    assert "swap" in G.legal_moves(s)
    s2 = G.apply_move(s, "swap")
    assert s2.stones == {"d3": WHITE}
    assert G.current_player(s2) == BLACK and s2.ply == 2
    assert "swap" not in G.legal_moves(s2)
    # official setup: the eight setup stones map onto themselves
    o = G.initial_state({"setup": "official"})
    s = G.apply_move(o, "c4")
    s2 = G.apply_move(s, "swap")
    want = dict(_OFFICIAL)
    want["d3"] = WHITE
    assert s2.stones == want
    assert G.current_player(s2) == BLACK


def test_serialize_roundtrip():
    e = G.initial_state({"setup": "official"})
    s = _play(e, ["d5", "e5", "e6", "d6", "f5"])
    d = G.serialize(s)
    json.dumps(d)
    s2 = G.deserialize(json.loads(json.dumps(d)))
    assert G.serialize(s2) == d
    assert G.legal_moves(s2) == G.legal_moves(s)


def test_render_shape():
    s = G.initial_state({"setup": "official"})
    spec = G.render(s)
    b = spec["board"]
    assert b["type"] == "polygons"
    assert isinstance(b["cells"], list) and len(b["cells"]) == 204
    for c in b["cells"][:5]:
        assert set(c) == {"id", "points"} and len(c["points"]) == 8
    assert len(b["lines"]) == 565 + 4  # lattice segments + 4 goal borders
    assert len(spec["pieces"]) == 8
    json.dumps(spec)


def test_random_playouts():
    rng = random.Random(2026)
    wins = [0, 0, 0]  # black, white, draw
    for i in range(200):
        s = G.initial_state({"setup": "official" if i % 2 else "empty"})
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            assert ms, "non-terminal state with no moves"
            s = G.apply_move(s, rng.choice(ms))
            assert s.ply <= PLY_CAP
        r = G.returns(s)
        assert len(r) == 2
        if s.winner is None:
            wins[2] += 1
        else:
            wins[s.winner] += 1
    assert wins[0] > 0 and wins[1] > 0, wins
    print(f"  playouts: black={wins[0]} white={wins[1]} draw={wins[2]}")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok {t.__name__}")
    print("onyx selftest: all tests passed")


if __name__ == "__main__":
    main()
