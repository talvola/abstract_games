"""Poly-Y correctness anchor (pure stdlib: agp + this game only).

Asserts, for the pentagon board:
  * geometry: cell count, 5 corners, 5 sides, corner-on-two-sides rule, symmetric
    adjacency, the corner-counts-as-part-of-both-sides property;
  * placement legality and the pie/swap move;
  * the corner-ownership rule on a hand-built FULL board reached via apply_move
    (an all-Black fill -> Black owns all 5 corners -> Black wins);
  * a mixed full board where Black owns exactly 3 corners -> Black wins (majority);
  * drawlessness: over many random full boards every corner resolves to exactly
    one player and the majority is always broken;
  * serialize round-trips.

Run directly:  PYTHONPATH=. python3 games/poly_y/selftest.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from games.poly_y.game import (  # noqa: E402
    PolyY, PolyYState, BLACK, WHITE, NSIDES,
    _cells, _cell_set, _adj, _corners, _sides, _corner_counts,
    _corner_owner, _key, _cell,
)


def _fill_to_win(game, n, board):
    """Reach a terminal state by placing the given full-board colouring via
    apply_move (placing one cell last), so winner is set inside apply_move."""
    cells = list(board.keys())
    last = cells[-1]
    # Set the board for all-but-one cell, then apply the final move with the
    # correct mover so apply_move scores the corners and sets the winner.
    s = PolyYState(n=n, pie=False)
    s.board = {c: board[c] for c in cells[:-1]}
    s.ply = len(s.board)
    s.to_move = board[last]
    return game.apply_move(s, _key(last))


def main():
    g = PolyY()
    for n in (3, 4, 5):
        
        cells = _cells(n)
        adj = _adj(n)
        corners = _corners(n)
        sides = _sides(n)

        # ---- geometry ----
        expected = 5 * n * n + 5 * n + 1
        assert len(cells) == expected, (n, len(cells), expected)
        assert len(set(cells)) == len(cells), "duplicate cells"
        assert len(corners) == NSIDES == 5
        assert len(sides) == 5
        for c in corners:
            assert c in _cell_set(n), c
        # symmetric adjacency
        for c in cells:
            for d in adj[c]:
                assert c in adj[d], ("asymmetric", c, d)
                assert d != c
        # each side has 2n+1 boundary cells
        for k in range(5):
            assert len(sides[k]) == 2 * n + 1, (k, len(sides[k]))
        # corner k belongs to exactly the two adjacent sides k-1 and k
        for k in range(5):
            cor = corners[k]
            belongs = sorted(s for s in range(5) if cor in sides[s])
            assert belongs == sorted([(k - 1) % 5, k]), (k, belongs)
        # every corner cell is on two sides; every non-corner boundary cell on one
        for k in range(5):
            for c in sides[k]:
                cnt = sum(1 for s in range(5) if c in sides[s])
                assert cnt in (1, 2), (c, cnt)
                if c in corners:
                    assert cnt == 2

        # ---- placement + pie ----
        s0 = g.initial_state(options={"size": n})
        assert s0.to_move == BLACK
        lm = g.legal_moves(s0)
        assert len(lm) == len(cells) and "swap" not in lm
        # first move then swap available
        first = _key(cells[len(cells) // 2])
        s1 = g.apply_move(s0, first)
        assert s1.to_move == WHITE and s1.board[_cell(first)] == BLACK
        assert "swap" in g.legal_moves(s1)
        s2 = g.apply_move(s1, "swap")
        assert s2.board[_cell(first)] == WHITE and s2.to_move == BLACK
        # illegal: occupied / off-board
        try:
            g.apply_move(s1, first)
            assert False, "expected illegal (occupied)"
        except ValueError:
            pass
        try:
            g.apply_move(s1, "f,0,99,99")
            assert False, "expected illegal (off board)"
        except ValueError:
            pass

        # ---- all-Black full board: Black owns all 5 corners, Black wins ----
        all_black = {c: BLACK for c in cells}
        bl, wh, owners = _corner_counts(all_black, n)
        assert bl == 5 and wh == 0, (bl, wh)
        term = _fill_to_win(g, n, all_black)
        assert term.over and term.winner == BLACK
        assert g.is_terminal(term)
        assert g.returns(term) == [1.0, -1.0]

    # ---- mixed full board where Black owns EXACTLY 3 corners -> Black wins ----
    # Build it by random search at n=4 until Black holds exactly 3 corners, then
    # verify the win is reached through apply_move.
    
    cells4 = _cells(4)
    rng = random.Random(12345)
    found = None
    for _ in range(2000):
        order = list(cells4)
        rng.shuffle(order)
        board = {c: i % 2 for i, c in enumerate(order)}  # ~balanced colouring
        bl, wh, owners = _corner_counts(board, 4)
        assert None not in owners, "undecided corner on full board!"
        assert bl + wh == 5
        if bl == 3:
            found = board
            break
    assert found is not None, "could not build a 3-corner Black position"
    bl, wh, owners = _corner_counts(found, 4)
    assert bl == 3 and wh == 2
    term = _fill_to_win(g, 4, found)
    assert term.over and term.winner == BLACK, (term.winner, bl, wh)
    assert g.returns(term) == [1.0, -1.0]

    # ---- drawlessness: many random full boards always break the majority ----
    for n in (3, 4, 5):
        cells = _cells(n)
        rng = random.Random(n * 7 + 1)
        for _ in range(300):
            order = list(cells)
            rng.shuffle(order)
            board = {c: i % 2 for i, c in enumerate(order)}
            bl, wh, owners = _corner_counts(board, n)
            assert None not in owners, ("undecided", n)
            assert bl + wh == 5
            assert bl != wh, ("tie!", n, bl, wh)  # odd corners -> never a tie

    # ---- serialize round-trips ----
    s = g.initial_state(options={"size": 4})
    s = g.apply_move(s, _key(_corners(4)[0]))
    s = g.apply_move(s, _key(_cells(4)[3]))
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d
    import json
    json.dumps(d)  # JSON-able

    # render is well-formed polygons
    r = g.render(s)
    assert r["board"]["type"] == "polygons"
    assert isinstance(r["board"]["cells"], list)
    assert all("points" in c and "id" in c for c in r["board"]["cells"])

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
