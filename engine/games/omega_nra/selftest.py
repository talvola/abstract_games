"""Pure-stdlib selftest for Omega (Néstor Romeral Andrés, 2010).

Anchors: hexhex board sizes/option clamping; the place-BOTH-colours turn
(phase sub-moves, own colour then opponent's); the end condition ("just
before White's turn" with < 4 free cells) on constructed near-full boards
reached via apply_move; product scoring incl. multi-group boards; the
rulebook tie-break (tie in products = win for the LAST tied player = Black);
serialize round-trip; and 500 random playouts (termination + result stats +
the free-cells-at-end invariant).

Run standalone:  PYTHONPATH=. python3 games/omega_nra/selftest.py
"""

import random

from games.omega_nra.game import (
    Omega, OmegaState, WHITE, BLACK, _cells, _group_sizes, _score,
)


def _sym(c):
    """Central point symmetry — maps a colour-swapped position onto itself."""
    return (-c[0], -c[1])


def test_board_and_options():
    g = Omega()
    assert g.num_players == 2
    # hexhex cell counts: 3n(n-1)+1 for side n
    assert len(_cells(5)) == 61
    assert len(_cells(6)) == 91
    assert len(_cells(10)) == 271
    assert g.initial_state().size == 6                      # default
    assert g.initial_state({"size": 8}).size == 8
    assert g.initial_state({"size": 12}).size == 10         # clamped
    assert g.initial_state({"size": 4}).size == 5           # clamped
    assert g.initial_state({"size": "abc"}).size == 6       # junk -> default
    s = g.initial_state({"size": 5})
    assert len(g.legal_moves(s)) == 61
    assert g.current_player(s) == WHITE and s.phase == 0


def test_turn_places_both_colours():
    g = Omega()
    s = g.initial_state({"size": 5})
    # White's first sub-move places a WHITE stone; White stays to move.
    s1 = g.apply_move(s, "0,0")
    assert s1.board[(0, 0)] == WHITE
    assert s1.to_move == WHITE and s1.phase == 1
    assert not g.is_terminal(s1) and g.legal_moves(s1)
    assert "0,0" not in g.legal_moves(s1)
    # Second sub-move places a BLACK stone (the opponent's colour); turn ends.
    s2 = g.apply_move(s1, "1,0")
    assert s2.board[(1, 0)] == BLACK
    assert s2.to_move == BLACK and s2.phase == 0
    assert s2.last == ((0, 0), (1, 0))
    # Black's turn: own colour (BLACK) first, then WHITE.
    s3 = g.apply_move(s2, "2,0")
    assert s3.board[(2, 0)] == BLACK and s3.to_move == BLACK and s3.phase == 1
    s4 = g.apply_move(s3, "-1,0")
    assert s4.board[(-1, 0)] == WHITE and s4.to_move == WHITE and s4.phase == 0
    assert not g.is_terminal(s4)  # 57 free >= 4
    # illegal placements
    for bad in ("0,0", "9,9"):
        try:
            g.apply_move(s2, bad)
            assert False, f"expected ValueError for {bad}"
        except ValueError:
            pass
    # describe_move names the colour being placed
    assert "White" in g.describe_move(s, "0,0")
    assert "Black" in g.describe_move(s1, "1,0")


def test_product_scoring():
    # White groups of sizes 1, 2, 3 -> product 6; Black one group of 4 -> 4.
    board = {
        (0, 0): WHITE,                                   # group of 1
        (2, 0): WHITE, (3, 0): WHITE,                    # group of 2
        (0, 2): WHITE, (0, 3): WHITE, (1, 2): WHITE,     # group of 3
        (-2, 0): BLACK, (-3, 0): BLACK, (-2, -1): BLACK, (-3, 1): BLACK,
    }
    assert sorted(_group_sizes(board, WHITE)) == [1, 2, 3]
    assert _score(board, WHITE) == 6
    assert _group_sizes(board, BLACK) == [4]
    assert _score(board, BLACK) == 4
    # rulebook example arithmetic: groups 1,5,2,4 -> 40
    assert 1 * 5 * 2 * 4 == 40
    # empty product convention
    assert _score({}, WHITE) == 1


def _near_full_state(size, free_cells):
    """A colour-symmetric board with exactly ``free_cells`` free (must be
    closed under central symmetry, plus (0,0)); White to move, phase 0.
    Symmetric halves get WHITE / BLACK so products are equal by construction."""
    free = set(free_cells)
    board = {}
    for c in _cells(size):
        if c in free or c == (0, 0):
            continue
        if c in board:
            continue
        board[c] = WHITE
        board[_sym(c)] = BLACK
    return OmegaState(size=size, board=board, to_move=WHITE, phase=0)


def test_end_condition_and_tie_goes_to_black():
    g = Omega()
    # 61 cells; free = (0,0) + three symmetric pairs = 7 free cells.
    p1, p2, p3 = (1, 0), (2, 0), (3, 0)
    free = [p1, _sym(p1), p2, _sym(p2), p3, _sym(p3)]
    s = _near_full_state(5, free)
    assert len(s.board) == 54
    assert _score(s.board, WHITE) == _score(s.board, BLACK)  # symmetric base
    # White's turn: 7 free >= 4, game on.
    assert not g.is_terminal(s)
    # Play a colour-symmetric final round: White plays a / sym(a),
    # Black plays b / sym(b).  Not terminal until the round completes.
    s = g.apply_move(s, "1,0")            # WHITE stone at (1,0)
    s = g.apply_move(s, "-1,0")           # BLACK stone at (-1,0)
    assert not g.is_terminal(s)           # 5 free, but mid-round
    s = g.apply_move(s, "2,0")            # BLACK stone at (2,0)
    assert not g.is_terminal(s)
    end = g.apply_move(s, "-2,0")         # WHITE stone at (-2,0) -> round done
    # 3 free (< 4) just before White's turn -> game over.
    assert g.is_terminal(end) and end.done
    sw, sb = _score(end.board, WHITE), _score(end.board, BLACK)
    assert sw == sb                        # a genuine tie in products...
    assert end.winner == BLACK             # ...which the rulebook gives to Black
    assert g.returns(end) == [-1.0, 1.0]
    assert g.legal_moves(end) == []
    try:
        g.apply_move(end, "0,0")
        assert False, "expected ValueError after game end"
    except ValueError:
        pass
    assert "tie" in g.render(end)["caption"].lower()


def test_end_condition_boundary_and_decisive_winner():
    g = Omega()
    # 8 free before White's turn -> the round fits; 4 free after it -> the
    # NEXT round also fits (4 >= 4) and empties the board.
    pairs = [(1, 0), (2, 0), (3, 0)]
    free = [c for p in pairs for c in (p, _sym(p))] + []
    # add one more symmetric pair to reach 8 free (incl. centre = 7 -> need 8):
    free += [(0, 1), (0, -1)]
    s = _near_full_state(5, free)
    assert 61 - len(s.board) == 9  # centre + 4 pairs free
    # Round 1: consumes 4 -> 5 free >= 4 -> not terminal.
    s = g.apply_move(s, "1,0")
    s = g.apply_move(s, "-1,0")
    s = g.apply_move(s, "2,0")
    s = g.apply_move(s, "-2,0")
    assert not g.is_terminal(s) and s.to_move == WHITE
    # Round 2: asymmetric — Black gifts White the centre join; 1 free < 4 -> over.
    s = g.apply_move(s, "3,0")            # WHITE
    s = g.apply_move(s, "-3,0")           # BLACK
    s = g.apply_move(s, "0,-1")           # BLACK's own stone
    end = g.apply_move(s, "0,0")          # WHITE stone at the centre
    assert g.is_terminal(end)
    # winner must be whoever has the higher product (Black on a tie).
    sw, sb = _score(end.board, WHITE), _score(end.board, BLACK)
    assert end.winner == (WHITE if sw > sb else BLACK)
    assert g.returns(end) == ([1.0, -1.0] if sw > sb else [-1.0, 1.0])


def test_serialize_roundtrip():
    g = Omega()
    s = g.initial_state({"size": 7})
    rng = random.Random(42)
    for _ in range(11):                    # ends mid-turn (phase 1)
        s = g.apply_move(s, rng.choice(g.legal_moves(s)))
    assert s.phase == 1
    d = g.serialize(s)
    import json
    s2 = g.deserialize(json.loads(json.dumps(d)))
    assert s2.size == s.size and s2.board == s.board
    assert s2.to_move == s.to_move and s2.phase == s.phase
    assert s2.last == s.last and s2.done == s.done and s2.winner == s.winner
    assert g.serialize(s2) == d


def test_render_shape():
    g = Omega()
    s = g.initial_state({"size": 5})
    s = g.apply_move(s, "0,0")
    spec = g.render(s)
    assert spec["board"] == {"type": "hex", "shape": "hexagon", "size": 5}
    assert spec["pieces"] == [{"cell": "0,0", "owner": WHITE, "label": ""}]
    assert spec["highlights"] == [{"cell": "0,0", "kind": "last-move"}]
    assert "place" in spec["caption"] and "Black" in spec["caption"]


def test_random_playouts():
    g = Omega()
    rng = random.Random(7)
    wins = {WHITE: 0, BLACK: 0}
    tie_broken = 0
    for i in range(500):
        size = rng.choice([5, 5, 6])
        s = g.initial_state({"size": size})
        cells = len(_cells(size))
        plies = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            assert moves, "non-terminal state must have moves"
            s = g.apply_move(s, rng.choice(moves), rng)
            plies += 1
            assert plies <= cells, "game exceeded cell count"
        free = cells - len(s.board)
        # From an empty board a 2p game always ends with (cells mod 4) free.
        assert free == cells % 4 and 1 <= free <= 3
        assert plies == cells - free
        assert s.winner in (WHITE, BLACK)
        r = g.returns(s)
        assert r == ([1.0, -1.0] if s.winner == WHITE else [-1.0, 1.0])
        wins[s.winner] += 1
        # independently recompute the products and check the verdict
        sw, sb = _score(s.board, WHITE), _score(s.board, BLACK)
        if sw == sb:
            tie_broken += 1
            assert s.winner == BLACK
        else:
            assert s.winner == (WHITE if sw > sb else BLACK)
    assert wins[WHITE] + wins[BLACK] == 500
    assert wins[WHITE] + wins[BLACK] - tie_broken > 0  # some decisive games
    print(f"  playouts: 500 games, White {wins[WHITE]} / Black {wins[BLACK]} "
          f"(ties broken to Black: {tie_broken})")


def main():
    for fn in [test_board_and_options, test_turn_places_both_colours,
               test_product_scoring, test_end_condition_and_tie_goes_to_black,
               test_end_condition_boundary_and_decisive_winner,
               test_serialize_roundtrip, test_render_shape,
               test_random_playouts]:
        fn()
        print(f"  ok: {fn.__name__}")
    print("omega_nra selftest: all tests passed")


if __name__ == "__main__":
    main()
