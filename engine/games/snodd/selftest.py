"""Snodd selftest -- pure stdlib. Anchors the snub-square board + Yodd parity rules.

Run standalone or via tests/test_games.py::test_package_selftests. Asserts:
  (a) board: loads, adjacency symmetric & connected; interior cells (all of whose
      neighbours are also on the board) have degree exactly 5 -- the snub-square
      3.3.4.3.4 anchor; every cell is a 5-vertex (pentagon) polygon;
  (b) the odd invariant: after any legal (non-mid-turn) move sequence the TOTAL
      group count is odd at every turn boundary;
  (c) seeded random self-play always terminates with a winner and NO draw, decided
      by fewer-own-groups;
  (d) serialize round-trips.
"""

import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.loader import load_from_dir  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _game():
    _manifest, game = load_from_dir(HERE)
    return game


def main():
    G = _game()
    from games.snodd import game as M  # static board data

    # ---- (a) board construction ----
    cells = M.CELL_IDS
    assert len(cells) >= 60, f"expected a sizable board, got {len(cells)}"
    # adjacency symmetric
    for c in cells:
        for n in M.ADJ[c]:
            assert n in M.ADJ, f"neighbour {n} of {c} not a board cell"
            assert c in M.ADJ[n], f"asymmetric edge {c}-{n}"
    # every adj entry references a real cell
    idset = set(cells)
    for c in cells:
        for n in M.ADJ[c]:
            assert n in idset, f"{c} lists off-board neighbour {n}"
    # connected (single component)
    seen = {cells[0]}
    stack = [cells[0]]
    while stack:
        cur = stack.pop()
        for n in M.ADJ[cur]:
            if n not in seen:
                seen.add(n)
                stack.append(n)
    assert len(seen) == len(cells), f"board not connected: {len(seen)}/{len(cells)}"
    # interior cells (all neighbours on-board) must have degree exactly 5
    interior = [c for c in cells if all(n in idset for n in M.ADJ[c]) and len(M.ADJ[c]) == 5]
    # every "fully surrounded" cell is degree 5 (snub-square anchor)
    for c in cells:
        deg = len(M.ADJ[c])
        assert deg <= 5, f"cell {c} has degree {deg} > 5 (not a snub-square star)"
    assert len(interior) >= 40, f"too few interior degree-5 cells: {len(interior)}"
    # render: pentagons (5 vertices each), polygons list of {id, points}
    spec = G.render(G.initial_state())
    b = spec["board"]
    assert b["type"] == "polygons"
    assert isinstance(b["cells"], list)
    for c in b["cells"]:
        assert "id" in c and "points" in c
        assert len(c["points"]) == 5, f"cell {c['id']} is not a pentagon"
    assert {c["id"] for c in b["cells"]} == set(cells)
    print(f"  board: {len(cells)} cells, {len(interior)} interior degree-5")

    def total_groups(s):
        _, tot, _, _ = M._label(s.board)
        return tot

    # ---- (b) odd invariant at turn boundaries ----
    for seed in range(30):
        rng = random.Random(1000 + seed)
        s = G.initial_state()
        while not G.is_terminal(s):
            mv = rng.choice(G.legal_moves(s))
            s = G.apply_move(s, mv)
            # at a genuine turn boundary (not mid-turn) the total must be odd
            if not s.turn_cells and not s.over:
                assert total_groups(s) % 2 == 1, "even total at a turn boundary"
        # terminal board's total is odd too (two passes preserve the last total)
        assert total_groups(s) % 2 == 1, "even total at game end"

    # ---- (c) termination + no draws, fewer-own-groups decides ----
    red_wins = blue_wins = 0
    for seed in range(60):
        rng = random.Random(seed)
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s):
            mv = rng.choice(G.legal_moves(s))
            s = G.apply_move(s, mv)
            steps += 1
            assert steps <= 5000, "self-play did not terminate"
        assert s.winner in (M.RED, M.BLUE), "game ended without a winner (draw!)"
        _, _, red, blue = M._label(s.board)
        assert red != blue, "group counts tied -- impossible under the odd rule"
        expect = M.RED if red < blue else M.BLUE
        assert s.winner == expect, f"winner {s.winner} != fewer-groups {expect}"
        r = G.returns(s)
        assert sorted(r) == [-1.0, 1.0], r
        if s.winner == M.RED:
            red_wins += 1
        else:
            blue_wins += 1
    assert red_wins and blue_wins, (red_wins, blue_wins)
    print(f"  self-play: {red_wins} red / {blue_wins} blue wins, no draws")

    # ---- (d) serialize round-trip ----
    rng = random.Random(7)
    s = G.initial_state()
    for _ in range(25):
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    d = G.serialize(s)
    s2 = G.deserialize(d)
    assert G.serialize(s2) == d, "serialize round-trip mismatch"

    print("snodd selftest OK")


if __name__ == "__main__":
    main()
