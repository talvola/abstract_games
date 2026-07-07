"""Pex selftest — pure stdlib. Anchors the type-11 board construction + Hex rules.

Run standalone or via tests/test_games.py::test_package_selftests. Asserts:
  (a) board construction: 128 cells (64 yellow + 64 green), interior cells of
      degree 5 AND 7 both exist, adjacency is symmetric & connected, and the
      four edge sets are the right size / on the right rows & columns;
  (b) a hand-built winning chain connects Red's two edges (win for Red, not Blue);
  (c) NO DRAWS: many random full fills each yield exactly one winner;
  (d) the pie rule (swap) is offered exactly at ply 1 and transfers correctly;
  (e) random self-play always terminates with a winner.
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
    from games.pex import game as M  # static board data

    # ---- (a) board construction ----
    cells = M.CELL_IDS
    assert len(cells) == 128, f"expected 128 cells, got {len(cells)}"
    yellow = [c for c in cells if M.TERRAIN[c] == "Y"]
    green = [c for c in cells if M.TERRAIN[c] == "G"]
    assert len(yellow) == 64 and len(green) == 64, (len(yellow), len(green))

    deg = {c: len(M.ADJ[c]) for c in cells}
    degs = sorted(set(deg.values()))
    assert 5 in degs and 7 in degs, f"missing 5/7-degree cells: {degs}"
    assert max(degs) == 7, f"no cell may exceed 7 neighbours: {degs}"
    # type-11 signature: the maximal (interior) degree is 7 and only YELLOW cells
    # reach it; GREEN interior cells top out at 5. (Boundary cells of either
    # colour have reduced degree, so degree-5 alone is a mix of interior green +
    # boundary yellow — hence we check the two colours' MAXIMA.)
    assert all(M.TERRAIN[c] == "Y" for c in cells if deg[c] == 7)
    assert max(deg[c] for c in yellow) == 7
    assert max(deg[c] for c in green) == 5
    assert any(deg[c] == 5 and M.TERRAIN[c] == "G" for c in cells)
    # exactly the counts we extracted from the official board
    from collections import Counter
    dh = Counter(deg.values())
    assert dh == {2: 3, 3: 14, 4: 13, 5: 56, 7: 42}, dict(dh)

    # adjacency symmetric
    for c in cells:
        for n in M.ADJ[c]:
            assert c in M.ADJ[n], f"asymmetric edge {c}-{n}"
    # adjacency connected (single component)
    seen = {cells[0]}
    stack = [cells[0]]
    while stack:
        cur = stack.pop()
        for n in M.ADJ[cur]:
            if n not in seen:
                seen.add(n)
                stack.append(n)
    assert len(seen) == 128, f"board not connected: {len(seen)}"

    # edge sets: 12 cells each; red on rows 1 & 8, blue on cols A & H
    assert len(M.TOP) == len(M.BOTTOM) == len(M.LEFT) == len(M.RIGHT) == 12
    assert all(c[1:].startswith("1") for c in M.TOP)       # row 1
    assert all(c[1] == "8" for c in M.BOTTOM)              # row 8
    assert all(c[0] == "A" for c in M.LEFT)                # col A
    assert all(c[0] == "H" for c in M.RIGHT)               # col H
    # the four corners belong to one red edge and one blue edge
    corners = (M.TOP | M.BOTTOM) & (M.LEFT | M.RIGHT)
    assert len(corners) == 4, sorted(corners)

    # ---- (b) hand-built Red winning chain ----
    # Build a red path from some top cell to some bottom cell via BFS through the
    # adjacency graph, place those stones, and check Red (and only Red) connects.
    def a_path(src_set, dst_set):
        import collections
        q = collections.deque((c, [c]) for c in src_set)
        seen_ = set(src_set)
        while q:
            cur, path = q.popleft()
            if cur in dst_set:
                return path
            for n in M.ADJ[cur]:
                if n not in seen_:
                    seen_.add(n)
                    q.append((n, path + [n]))
        return None

    path = a_path(M.TOP, M.BOTTOM)
    assert path, "no top->bottom path exists?!"
    board = {c: M.RED for c in path}
    assert M._connects(board, M.RED), "hand-built red chain should connect"
    assert not M._connects(board, M.BLUE), "red-only board must not connect blue"

    # ---- (c) NO DRAWS: random full fills -> exactly one winner ----
    rng = random.Random(12345)
    for _ in range(1500):
        board = {c: rng.randint(0, 1) for c in cells}
        red = M._connects(board, M.RED)
        blue = M._connects(board, M.BLUE)
        assert red != blue, "a filled board must have exactly one winner (no draw)"

    # ---- (d) pie rule offered exactly at ply 1 ----
    s = G.initial_state()
    assert "swap" not in G.legal_moves(s)                  # ply 0: no swap
    s1 = G.apply_move(s, "D4G")
    assert "swap" in G.legal_moves(s1)                     # ply 1: swap offered
    # after swap: opener (seat 0) is back on the move, seat 1 now plays RED and
    # owns the first stone; the stone colour is unchanged.
    s2 = G.apply_move(s1, "swap")
    assert G.current_player(s2) == 0
    assert s2.red_seat == 1
    assert s2.board["D4G"] == M.RED and s2.colour_of_seat(1) == M.RED
    assert "swap" not in G.legal_moves(s2)                 # only once
    s3 = G.apply_move(s2, "E4Y")                           # seat 0 places, as BLUE
    assert s3.board["E4Y"] == M.BLUE
    assert "swap" not in G.legal_moves(s3)

    # ---- (e) random self-play always terminates with a winner ----
    for seed in range(40):
        rr = random.Random(seed)
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s):
            mv = rr.choice(G.legal_moves(s))
            s = G.apply_move(s, mv)
            steps += 1
            assert steps <= 200, "self-play did not terminate"
        assert s.winner is not None
        r = G.returns(s)
        assert sorted(r) == [-1.0, 1.0], r

    # render shape sanity: polygons list of {id, points}, tints present
    s = G.apply_move(G.initial_state(), "D4G")
    spec = G.render(s)
    b = spec["board"]
    assert b["type"] == "polygons"
    assert isinstance(b["cells"], list)
    assert all("points" in c and "id" in c for c in b["cells"])
    ids = {c["id"] for c in b["cells"]}
    assert ids == set(cells)
    assert set(b["tints"]) <= ids

    print("pex selftest OK")


if __name__ == "__main__":
    main()
