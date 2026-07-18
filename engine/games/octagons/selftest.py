"""Standalone correctness anchor for Octagons (pure stdlib: agp + this game).

Anchors (against Kerry Handscomb's full rules restatement in Abstract Games
magazine #7 pp. 12-13, Diagram 1 read at 600-1200 dpi):
  * board integrity: 8x8 octagons split checkerboard-wise into 128
    half-octagons + 49 interstitial squares = 177 spaces; 484 shared-side
    adjacencies; every square degree 4 with its neighbours a 4-cycle of
    half-octagons (the Onyx-grid local structure the article describes);
    interior half-octagons degree 7; each board side touched by exactly 12
    spaces; corner spaces serve both adjacent sides;
  * the article's no-draw argument's premise: except on the edges, exactly
    THREE pairwise-adjacent spaces meet at every intersection of the board's
    lines (all 308 interior intersections checked from exact geometry);
  * the pie swap: a 90-degree rotation proven to be a graph automorphism that
    exchanges the two players' goal side-pairs, preserves space kind
    (half vs square), and has order 4; state-level swap = rotate + recolour;
  * move protocol: one half-octagon or two distinct empty squares (both
    click orders), the lone-last-square ruling, illegal-move rejection;
  * minimal constructed wins for both colours REACHED via apply_move (win
    detected the moment the chain completes, not before), including a win
    whose decisive move is a two-square double move bridging via a square;
  * no-draw oracle: thousands of random full colourings have EXACTLY one
    winner; hundreds of protocol games always end in a win and never pass
    through a doubly-connected state;
  * serialize round-trip, render shape, describe_move, heuristic payoff
    shape under a forced MCTS rollout cutoff.
"""

import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.octagons.game import (  # noqa: E402
    BLUE, RED, N, PITCH, SIZE, Octagons, OctagonsState,
    _ADJ, _HALVES, _KIND, _ORDER, _POLY, _ROT, _SIDES, _SQUARES, _TWIN,
    _connects, _elem_segments, _split,
)

G = Octagons()


def test_board_integrity():
    assert len(_POLY) == 177 and len(_HALVES) == 128 and len(_SQUARES) == 49
    assert N == 8 and SIZE == 32
    # split pattern anchors (Diagram 1: top-left octagon a8 is horizontally
    # cut, its right neighbour b8 vertically; bottom-left a1 vertically)
    assert _split(0, 7) == "H" and _split(1, 7) == "V" and _split(0, 0) == "V"
    assert {"a8n", "a8s", "b8w", "b8e", "a1w", "a1e", "b1n", "b1s"} <= set(_HALVES)
    # symmetric adjacency + handshake edge count
    for a, nbs in _ADJ.items():
        assert a not in nbs
        for b in nbs:
            assert a in _ADJ[b], (a, b)
    n_edges = sum(len(v) for v in _ADJ.values()) // 2
    # 64 octagon-cut twins + 49*4 square sides + 2 per orthogonal octagon
    # pair (2 * 2*7*8 = 224) = 484
    assert n_edges == 484, n_edges
    assert sum(len(_ADJ[q]) for q in _SQUARES) == 196
    assert len(_TWIN) == 128 and all(_TWIN[_TWIN[h]] == h for h in _TWIN)
    # every square: degree 4, all half-octagons, forming a 4-cycle (the Onyx
    # square-with-midpoint local structure of the points representation)
    for q in _SQUARES:
        nbs = sorted(_ADJ[q])
        assert len(nbs) == 4 and all(_KIND[x] == "half" for x in nbs), q
        adj_pairs = sum(1 for i in range(4) for j in range(i + 1, 4)
                        if nbs[j] in _ADJ[nbs[i]])
        assert adj_pairs == 4, (q, nbs)   # cycle: 4 of the 6 pairs adjacent
    # degree distribution of half-octagons (frozen from the build):
    # 4 corner-outer halves deg 2, 12 edge deg 3, 28 edge deg 5, 84 interior
    # deg 7 (twin + 2 side-neighbour halves + 2 above/below halves + 2 sqs)
    dist = {}
    for h in _HALVES:
        dist[len(_ADJ[h])] = dist.get(len(_ADJ[h]), 0) + 1
    assert dist == {2: 4, 3: 12, 5: 28, 7: 84}, dist
    border = set().union(*_SIDES.values())
    for h in _HALVES:
        if h not in border:
            assert len(_ADJ[h]) == 7, h
    # frozen local anchors
    assert _ADJ["a1w"] == frozenset({"a1e", "a2s"})
    assert _ADJ["a1x"] == frozenset({"a1e", "a2s", "b1n", "b2w"})
    assert _ADJ["d4x"] == frozenset({"d4e", "d5s", "e4n", "e5w"})
    assert _ADJ["d3n"] == frozenset(
        {"c3e", "c3x", "d3s", "d3x", "d4e", "d4w", "e3w"})
    # goal sides: 12 spaces each (4 H-split octagons contribute 1 half, 4
    # V-split contribute both halves, per side); squares touch no side
    for k in "NSWE":
        assert len(_SIDES[k]) == 12 and all(_KIND[c] == "half"
                                            for c in _SIDES[k]), k
    assert _SIDES["S"] == frozenset(
        {"a1e", "a1w", "b1s", "c1e", "c1w", "d1s",
         "e1e", "e1w", "f1s", "g1e", "g1w", "h1s"})
    # a corner space connects to both sides meeting at that corner
    assert "a1w" in _SIDES["S"] and "a1w" in _SIDES["W"]
    assert "h1s" in _SIDES["S"] and "h1s" in _SIDES["E"]
    assert "a8n" in _SIDES["N"] and "a8n" in _SIDES["W"]
    assert "h8e" in _SIDES["N"] and "h8e" in _SIDES["E"]


def _angle_at(poly, p):
    n = len(poly)
    for i, v in enumerate(poly):
        if v == p:
            ax, ay = poly[(i - 1) % n]
            bx, by = poly[(i + 1) % n]
            a1 = math.atan2(ay - p[1], ax - p[0])
            a2 = math.atan2(by - p[1], bx - p[0])
            return math.degrees(abs((a1 - a2 + math.pi) % (2 * math.pi)
                                    - math.pi))
    return 180.0   # p lies in the interior of an edge (all cells convex)


def test_three_spaces_meet():
    """Article: "except on the edges, it is always the case that three spaces
    meet where the lines of the board intersect" — the no-draw premise."""
    pt_cells, vertex_pts = {}, set()
    for cid, poly in _POLY.items():
        vertex_pts.update(poly)
        for a, b in _elem_segments(poly):
            pt_cells.setdefault(a, set()).add(cid)
            pt_cells.setdefault(b, set()).add(cid)
    n3 = 0
    for p, cs in pt_cells.items():
        total = sum(_angle_at(_POLY[c], p) for c in cs)
        if total < 359.9:
            continue   # touches the frame: an edge point, excluded
        assert abs(total - 360.0) < 0.1, (p, total)
        if p in vertex_pts:   # a true intersection of drawn lines
            trio = sorted(cs)
            assert len(trio) == 3, (p, trio)
            assert all(trio[j] in _ADJ[trio[i]]
                       for i in range(3) for j in range(i + 1, 3)), (p, trio)
            n3 += 1
        else:                 # a point along a shared side, no intersection
            a, b = sorted(cs)
            assert b in _ADJ[a], (p, a, b)
    assert n3 == 308, n3


def test_rotation_swap_automorphism():
    """The pie swap's 90-degree rotation is a graph automorphism exchanging
    the two goals — the proof that swap is value-preserving."""
    assert set(_ROT) == set(_POLY)
    assert len(set(_ROT.values())) == len(_POLY)          # bijection
    for p, q in _ROT.items():
        assert _KIND[q] == _KIND[p], p                    # halves<->halves
        assert _ADJ[q] == frozenset(_ROT[x] for x in _ADJ[p]), p
    assert {_ROT[p] for p in _SIDES["N"]} == _SIDES["E"]
    assert {_ROT[p] for p in _SIDES["E"]} == _SIDES["S"]
    assert {_ROT[p] for p in _SIDES["S"]} == _SIDES["W"]
    assert {_ROT[p] for p in _SIDES["W"]} == _SIDES["N"]
    for p in _POLY:                                       # order 4
        assert _ROT[_ROT[_ROT[_ROT[p]]]] == p
    assert _ROT["a1w"] == "a8n" and _ROT["b3n"] == "c7e"
    assert _ROT["a1x"] == "a7x" and _ROT["d4x"] == "d4x"  # centre square fixed
    # state level: swap after a half-octagon first move
    s = G.apply_move(G.initial_state(), "b3n")
    assert "swap" in G.legal_moves(s)
    s2 = G.apply_move(s, "swap")
    assert s2.stones == {"c7e": BLUE}
    assert G.current_player(s2) == RED and s2.ply == 2
    assert "swap" not in G.legal_moves(s2)
    # swap after a two-squares first move rotates both stones
    s = G.apply_move(G.initial_state(), "c3x>d5x")
    s2 = G.apply_move(s, "swap")
    assert s2.stones == {_ROT["c3x"]: BLUE, _ROT["d5x"]: BLUE}
    # swap is only available on move 2
    assert "swap" not in G.legal_moves(G.initial_state())
    try:
        G.apply_move(G.initial_state(), "swap")
        raise AssertionError("swap accepted on move 1")
    except ValueError:
        pass


def test_move_protocol():
    e = G.initial_state()
    moves = G.legal_moves(e)
    assert len(moves) == 128 + 49 * 48                    # halves + sq pairs
    assert "a1x" not in moves                             # no lone square yet
    assert "a1x>a1x" not in moves
    s = G.apply_move(e, "d3n")
    assert len(G.legal_moves(s)) == 127 + 49 * 48 + 1     # + swap
    for bad in ("a1x", "a1x>a1x", "a1x>b2n", "d3n", "d3n>d3s", "zz9",
                "a1x>b2x>c3x"):
        try:
            G.apply_move(s, bad)
            raise AssertionError(f"accepted {bad!r}")
        except ValueError:
            pass
    # a pair's two click orders are the same move
    s1 = G.apply_move(s, "a1x>g7x")
    s2 = G.apply_move(s, "g7x>a1x")
    assert G.serialize(s1) == G.serialize(s2)
    assert s1.stones["a1x"] == BLUE and s1.stones["g7x"] == BLUE
    # pair with one occupied square is rejected
    try:
        G.apply_move(s1, "a1x>b2x")
        raise AssertionError("occupied square accepted")
    except ValueError:
        pass
    # lone-last-square ruling: colouring the single remaining empty square
    # is a legal turn (documented interpretation; see rules.md)
    stones = {q: (i % 2) for i, q in enumerate(_SQUARES) if q != "g7x"}
    s = OctagonsState(stones=stones, to_move=RED, ply=48)
    moves = G.legal_moves(s)
    assert "g7x" in moves
    assert not any(">" in m for m in moves)
    s2 = G.apply_move(s, "g7x")
    assert s2.stones["g7x"] == RED


def _play(state, moves):
    for m in moves:
        assert m in G.legal_moves(state), m
        state = G.apply_move(state, m)
    return state


def test_minimal_red_win():
    # Red column-a chain S->N: a1w (corner: South AND West) up to a8n; win
    # must appear exactly on the 12th red move, never earlier.
    red = ["a1w", "a2s", "a2n", "a3w", "a4s", "a4n",
           "a5w", "a6s", "a6n", "a7w", "a8s", "a8n"]
    blue = ["h1s", "h1n", "h2e", "h2w", "h3s", "h3n",
            "h4e", "h4w", "h5s", "h5n", "h6e"]
    s = G.initial_state()
    for i, rm in enumerate(red):
        s = G.apply_move(s, rm)
        if i < len(red) - 1:
            assert s.winner is None and not G.is_terminal(s), rm
            s = G.apply_move(s, blue[i])
            assert s.winner is None
    assert s.winner == RED and G.is_terminal(s)
    assert G.returns(s) == [1.0, -1.0]
    assert set(s.conn_path) <= set(red)
    assert s.conn_path[0] in _SIDES["N"] | _SIDES["S"]
    assert s.conn_path[-1] in _SIDES["N"] | _SIDES["S"]
    assert not _connects(s.stones, BLUE)
    assert G.legal_moves(s) == []


def test_minimal_blue_win():
    # Blue row-1 chain W->E ending on the corner space h1s, which serves the
    # East side (corner rule); Red fills row 8 (touches only North: harmless).
    blue = ["a1w", "a1e", "b1s", "c1w", "c1e", "d1s",
            "e1w", "e1e", "f1s", "g1w", "g1e", "h1s"]
    red = ["a8n", "a8s", "b8w", "b8e", "c8n", "c8s",
           "d8w", "d8e", "e8n", "e8s", "f8w", "f8e"]
    s = G.initial_state()
    for i, bm in enumerate(blue):
        s = G.apply_move(s, red[i])
        assert s.winner is None
        s = G.apply_move(s, bm)
        if i < len(blue) - 1:
            assert s.winner is None, bm
    assert s.winner == BLUE
    assert G.returns(s) == [-1.0, 1.0]
    assert set(s.conn_path) <= set(blue)
    assert "a1w" in _SIDES["W"] and "h1s" in _SIDES["E"]


def test_double_move_win():
    # The decisive move is a TWO-SQUARE move: a1x bridges a1e (South) to the
    # column-b chain reaching b8w (North); without a1x they are disconnected.
    red = ["a1e", "b2w", "b3s", "b3n", "b4w", "b5s",
           "b5n", "b6w", "b7s", "b7n", "b8w"]
    blue = ["h1s", "h1n", "h2e", "h2w", "h3s", "h3n",
            "h4e", "h4w", "h5s", "h5n", "h6e"]
    seq = []
    for i, rm in enumerate(red):
        seq.append(rm)
        seq.append(blue[i])
    s = _play(G.initial_state(), seq)
    assert s.winner is None
    assert not _connects(dict(s.stones), RED)
    for pair in ("a1x>g7x", "g7x>a1x"):
        s2 = G.apply_move(s, pair)
        assert s2.winner == RED, pair
        assert "a1x" in s2.conn_path and "g7x" not in s2.conn_path


def test_no_draw_oracle():
    rng = random.Random(2026)
    # (a) plain random FULL colourings: exactly one player is connected
    for _ in range(4000):
        stones = {c: rng.randint(0, 1) for c in _ORDER}
        r = bool(_connects(stones, RED))
        b = bool(_connects(stones, BLUE))
        assert r != b, "full board must have exactly one winner"
    # (b) partial random colourings: never BOTH connected
    for _ in range(1500):
        stones = {c: rng.randint(0, 1) for c in _ORDER if rng.random() < 0.6}
        assert not (_connects(stones, RED) and _connects(stones, BLUE))
    # (c) the move-protocol way: every random game ends in a win (never a
    # draw, never stuck), the loser is unconnected, and no intermediate
    # state is doubly connected
    wins = [0, 0, 0]
    for i in range(400):
        s = G.initial_state()
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            assert ms, "non-terminal state with no moves"
            s = G.apply_move(s, rng.choice(ms))
            assert not (_connects(s.stones, RED) and _connects(s.stones, BLUE))
            assert s.ply <= 178
        assert s.winner is not None, "protocol game ended drawn"
        assert not _connects(s.stones, 1 - s.winner)
        assert G.returns(s)[s.winner] == 1.0
        wins[s.winner] += 1
    assert wins[0] > 50 and wins[1] > 50, wins
    print(f"  no-draw oracle: 4000 full + 1500 partial colourings OK; "
          f"400 protocol games red={wins[0]} blue={wins[1]} draws=0")


def test_serialize_roundtrip():
    s = _play(G.initial_state(), ["d3n", "c3x>d3x", "e4n", "a1w"])
    d = G.serialize(s)
    s2 = G.deserialize(json.loads(json.dumps(d)))
    assert G.serialize(s2) == d
    assert G.legal_moves(s2) == G.legal_moves(s)
    # roundtrip through a swap state too
    s = G.apply_move(G.apply_move(G.initial_state(), "b3n"), "swap")
    d = G.serialize(s)
    assert G.serialize(G.deserialize(json.loads(json.dumps(d)))) == d


def test_describe_move():
    e = G.initial_state()
    assert G.describe_move(e, "d3n") == "d3n"
    assert G.describe_move(e, "a1x>b2x") == "a1x+b2x"
    s = G.apply_move(e, "d3n")
    assert G.describe_move(s, "swap") == "swap (pie)"
    stones = {q: (i % 2) for i, q in enumerate(_SQUARES) if q != "g7x"}
    s = OctagonsState(stones=stones, to_move=RED, ply=48)
    assert G.describe_move(s, "g7x") == "g7x (last square)"


def test_render_shape():
    s = _play(G.initial_state(), ["d3n", "a1x>b2x"])
    spec = G.render(s)
    b = spec["board"]
    assert b["type"] == "polygons"
    assert isinstance(b["cells"], list) and len(b["cells"]) == 177
    for c in b["cells"]:
        assert set(c) == {"id", "points"}
        assert len(c["points"]) in (4, 6)      # squares / half-octagons
    assert len(b["lines"]) == 4                # the four goal borders
    assert len(spec["pieces"]) == 3
    assert all(p["shape"] == "fill" for p in spec["pieces"])
    assert spec["actionNames"]["swap"] == "Swap (pie rule)"
    json.dumps(spec)
    # winning chain overlay appears
    red = ["a1w", "a2s", "a2n", "a3w", "a4s", "a4n",
           "a5w", "a6s", "a6n", "a7w", "a8s", "a8n"]
    blue = ["h1s", "h1n", "h2e", "h2w", "h3s", "h3n",
            "h4e", "h4w", "h5s", "h5n", "h6e"]
    seq = []
    for i, rm in enumerate(red):
        seq.append(rm)
        if i < len(blue):
            seq.append(blue[i])
    s = _play(G.initial_state(), seq)
    spec = G.render(s)
    assert "overlay" in spec["board"] and len(spec["board"]["overlay"]) == 1
    assert "wins" in spec["caption"]
    json.dumps(spec)


def test_heuristic_and_bot_cutoff():
    from agp.mcts import MCTSBot
    s = G.initial_state()
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2
    assert abs(h[0]) < 1e-9 and abs(h[1]) < 1e-9          # symmetric start
    s2 = _play(s, ["a4s", "h4e", "a4n", "h4w"])
    h2 = G.heuristic(s2)
    assert len(h2) == 2 and abs(h2[0] + h2[1]) < 1e-9
    # force the rollout cutoff so a malformed heuristic would raise
    m = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(G, s)
    assert m in G.legal_moves(s)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok {t.__name__}")
    print("octagons selftest: all tests passed")


if __name__ == "__main__":
    main()
