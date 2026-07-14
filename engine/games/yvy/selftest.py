"""YvY selftest — pure stdlib. Anchors the board + loop/scoring rules.

Run standalone or via tests/test_games.py::test_package_selftests. Asserts:
  (a) board: 147 cells, 21 sprouts (all degree 2), 90 interior degree-6 cells,
      adjacency symmetric & connected, every cell a 6-vertex polygon;
  (b) a hand-built LOOP (6 stones ringing an interior cell) is a sudden-death win
      via apply_move;
  (c) a non-enclosing group (a straight line of stones) is NOT a loop;
  (d) dead-group removal: a group touching no sprout is removed before scoring;
  (e) score = sprouts_controlled − 2×groups, incl. one group controlling TWO
      sprouts beating two single-stone groups; plus the fenced-in enclosure
      machinery (barrier encloses interior cells) and the documented geometry
      fact that no empty sprout is enclosable here;
  (f) an early symmetric double-pass on the empty board is an honest DRAW;
  (g) seeded random self-play always terminates with a valid result;
  (h) serialize round-trips.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.loader import load_from_dir  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _game():
    _manifest, game = load_from_dir(HERE)
    return game


def main():
    G = _game()
    from games.yvy import game as M

    WHITE, BLACK = M.WHITE, M.BLACK
    ADJ = M.ADJ
    CELL_IDS = M.CELL_IDS

    # ---- (a) board construction ----
    assert len(CELL_IDS) == 147, f"expected 147 cells, got {len(CELL_IDS)}"
    assert len(M.SPROUTS) == 21, f"expected 21 sprouts, got {len(M.SPROUTS)}"
    assert all(len(ADJ[s]) == 2 for s in M.SPROUTS), "sprouts must be degree-2 spikes"
    deg = {c: len(ADJ[c]) for c in CELL_IDS}
    assert sum(1 for c in CELL_IDS if deg[c] == 6) == 90, "expected 90 interior deg-6 cells"
    # adjacency symmetric
    for c in CELL_IDS:
        for n in ADJ[c]:
            assert c in ADJ[n], f"asymmetric adjacency {c}-{n}"
    # connected
    seen = {CELL_IDS[0]}
    stack = [CELL_IDS[0]]
    while stack:
        cur = stack.pop()
        for n in ADJ[cur]:
            if n not in seen:
                seen.add(n)
                stack.append(n)
    assert len(seen) == len(CELL_IDS), "board graph is not connected"
    # every cell renders as a 6-vertex polygon
    spec = G.render(G.initial_state())
    assert spec["board"]["type"] == "polygons"
    assert len(spec["board"]["cells"]) == 147
    assert all(len(c["points"]) == 6 for c in spec["board"]["cells"])
    # sprouts tinted green
    assert all(M.SPROUTS.issubset(set(spec["board"]["tints"].keys())) for _ in [0])

    # find an interior degree-6 cell and its 6 neighbours (a minimal loop)
    center = next(c for c in CELL_IDS if deg[c] == 6)
    ring = list(ADJ[center])
    assert len(ring) == 6

    # ---- (b) loop = sudden-death win ----
    board = {ring[i]: WHITE for i in range(5)}      # 5 of 6 ring stones placed
    st = M.YvyState(board=dict(board), to_move=0, white_seat=0, passes=0, ply=6)
    assert not st.over
    st2 = G.apply_move(st, ring[5])                 # complete the ring
    assert st2.over and st2.winner == WHITE and st2.win_by == "loop", \
        "completing a ring must be a sudden-death loop win"
    assert G.returns(st2) == [1.0, -1.0]
    # the machinery: the ring encloses exactly the center cell
    assert M._enclosed_by(set(ring)) == {center}

    # ---- (c) a straight line is NOT a loop ----
    # walk a short path of neighbours that does not close
    a = ring[0]
    b = next(n for n in ADJ[a] if n != center and n not in ring)
    lineboard = {a: WHITE, b: WHITE}
    assert not M._forms_loop(lineboard, b, WHITE), "an open line is not a loop"
    assert M._enclosed_by({a, b}) == set()

    # ---- (d) dead-group removal (no sprout => removed) ----
    # a small interior clump touching no sprout is dead
    clump = {center: BLACK}
    for n in ADJ[center][:2]:
        clump[n] = BLACK
    assert not any(c in M.SPROUTS for c in clump)
    scores, detail = M._score_board(clump)
    assert detail["live"] == {}, "a sprout-less group must be removed before scoring"
    assert scores == [0, 0]

    # ---- (e) score = sprouts − 2×groups ----
    sprouts = sorted(M.SPROUTS)
    # White: ONE connected group touching two sprouts (c0-c4-c3 share cell c4).
    #   c0 & c3 are both sprouts adjacent to c4.
    assert {"c0", "c3"} <= M.SPROUTS
    assert "c4" in ADJ["c0"] and "c4" in ADJ["c3"]
    wboard = {"c0": WHITE, "c4": WHITE, "c3": WHITE}
    # Black: two SEPARATE single-stone sprout groups.
    bs = [s for s in sprouts if s not in ("c0", "c3")][:2]
    board = dict(wboard)
    for s in bs:
        board[s] = BLACK
    scores, detail = M._score_board(board)
    # White: controls {c0,c3}=2 sprouts, 1 group -> 2 - 2 = 0
    assert detail["per"][WHITE] == {"sprouts": 2, "groups": 1, "score": 0}, detail["per"][WHITE]
    # Black: controls 2 sprouts, 2 groups -> 2 - 4 = -2
    assert detail["per"][BLACK] == {"sprouts": 2, "groups": 2, "score": -2}, detail["per"][BLACK]
    assert scores[WHITE] > scores[BLACK], "one big group must beat two small ones here"
    # fenced-in geometry fact: even walling everything, no sprout is enclosable.
    walled = set(CELL_IDS) - {sprouts[0]}
    assert M._enclosed_by(walled) == set(), "sprout spikes are never enclosable"
    # controlled set in scoring came purely from occupation (fenced-in inert here)
    assert (M._enclosed_by({c for c, v in board.items() if v == WHITE}) & M.SPROUTS) == set()

    # ---- (f) early symmetric double-pass = honest DRAW ----
    s0 = G.initial_state()
    s1 = G.apply_move(s0, "pass")
    assert not s1.over and s1.passes == 1
    s2 = G.apply_move(s1, "pass")
    assert s2.over and s2.winner is None, "empty double-pass must be a draw"
    assert G.returns(s2) == [0.0, 0.0]

    # ---- (g) seeded random self-play terminates ----
    for seed in range(6):
        rng = random.Random(seed)
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s):
            moves = G.legal_moves(s)
            assert moves, "non-terminal state must have legal moves"
            s = G.apply_move(s, rng.choice(moves))
            steps += 1
            assert steps <= M._PLY_CAP + 5, "game failed to terminate"
        r = G.returns(s)
        assert r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]), r

    # ---- (h) serialize round-trips ----
    s = G.initial_state()
    rng = random.Random(99)
    for _ in range(12):
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    d = G.serialize(s)
    s_rt = G.deserialize(d)
    assert G.serialize(s_rt) == d, "serialize/deserialize not a round-trip"

    print("SELFTEST OK — all tests passed")


if __name__ == "__main__":
    main()
