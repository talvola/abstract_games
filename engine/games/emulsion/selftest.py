"""Emulsion correctness anchors (pure stdlib: agp + this game only).

Anchored on the designer's own Zillions edition (submission id=3089): the
bundled ReadMe.txt ruleset (identical to the submission-page blurb and the
.zrf description). Key anchors:
  * checkered full-board start, White on the centre of odd boards, Black first;
  * swap legality = the mover's piece's value strictly increases
    (value = own-colour orthogonal neighbours + half adjacent board edges);
  * the designer's stated invariant: both players always share the SAME set of
    available swaps (a swap changes both pieces' values equally);
  * monotone potential: every move strictly increases the number of
    monochromatic orthogonal adjacencies -> provable termination;
  * scoring: largest group, then second-largest, etc.; even-board full tie ->
    last mover wins.

Run standalone:  cd engine && PYTHONPATH=. python3 games/emulsion/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.emulsion.game import (
    EmulsionState, _checkered, _compare_scores, _delta2, _edges, _group_sizes,
    BLACK, WHITE, ORTH,
)

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _value2(board, n, x):
    """Reference (brute force): twice the value of the piece at x."""
    col = board[x]
    cn = sum(1 for dc, dr in ORTH if board.get((x[0] + dc, x[1] + dr)) == col)
    return 2 * cn + _edges(n, x[0], x[1])


def _brute_delta2(board, n, a, b):
    """Reference: recompute the mover's piece value from scratch after the swap."""
    before = _value2(board, n, a)
    nb = dict(board)
    nb[a], nb[b] = nb[b], nb[a]
    return _value2(nb, n, b) - before


def _mono_adjacencies(board, n):
    m = 0
    for c in range(n):
        for r in range(n):
            if c + 1 < n and board[(c, r)] == board[(c + 1, r)]:
                m += 1
            if r + 1 < n and board[(c, r)] == board[(c, r + 1)]:
                m += 1
    return m


def _pairs(moves):
    out = set()
    for mv in moves:
        a, b = mv.split(">")
        out.add(frozenset((a, b)))
    return out


def test_initial_position():
    """Full checkered board; odd boards: centre (and corners) White; Black first."""
    for n in (7, 8, 9):
        s = G.initial_state({"size": n})
        assert len(s.board) == n * n
        assert s.to_move == BLACK
        for (c, r), pl in s.board.items():
            assert pl == (WHITE if (c + r) % 2 == 0 else BLACK)
        if n % 2:
            m = n // 2
            assert s.board[(m, m)] == WHITE
            assert s.board[(0, 0)] == WHITE
            assert sum(1 for v in s.board.values() if v == WHITE) == (n * n + 1) // 2
        else:
            assert sum(1 for v in s.board.values() if v == WHITE) == n * n // 2
    # Serialize round-trip.
    s = G.initial_state({"size": 8})
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)


def test_initial_moves():
    """From the start, every orthogonally adjacent pair is a legal swap
    (delta = 3 - (edges_a+edges_b)/2 > 0) and no diagonal pair is even
    opposite-coloured -> exactly 2*n*(n-1) moves."""
    for n in (7, 8, 9):
        s = G.initial_state({"size": n})
        moves = G.legal_moves(s)
        assert len(moves) == 2 * n * (n - 1), (n, len(moves))
        for mv in moves:
            a, b = mv.split(">")
            ac, ar = map(int, a.split(","))
            bc, br = map(int, b.split(","))
            assert abs(ac - bc) + abs(ar - br) == 1          # orthogonal only
            assert s.board[(ac, ar)] == BLACK                 # mover's piece first
            assert s.board[(bc, br)] == WHITE


def test_delta_formula_and_shared_move_sets():
    """On random reachable positions: the closed-form delta matches a brute-force
    recompute, the swap changes BOTH pieces' values by the same amount, and the
    two players' legal swap sets are identical (the designer's invariant)."""
    rng = random.Random(42)
    for n in (5, 6, 7):
        s = G.initial_state({"size": n})
        for step in range(60):
            board = s.board
            for (c, r), pl in board.items():
                for dc, dr in ((0, 1), (1, 0), (1, 1), (1, -1)):
                    b = (c + dc, r + dr)
                    if board.get(b) is not None and board[b] != pl:
                        d_a = _delta2(board, n, (c, r), b)
                        assert d_a == _brute_delta2(board, n, (c, r), b)
                        assert d_a == _delta2(board, n, b, (c, r))   # symmetry
            black = _pairs(G._raw_moves(board, n, BLACK))
            white = _pairs(G._raw_moves(board, n, WHITE))
            assert black == white
            moves = G.legal_moves(s)
            if not moves:
                break
            s = G.apply_move(s, rng.choice(moves))


def test_legality_anchors():
    """Hand-computed swaps on a 3x3 start: b1<->a1 raises Black's piece value
    0.5 -> 2.0 (legal); the fully-curdled 3x3 split position is terminal and
    every candidate swap there is value-decreasing."""
    s = G.initial_state({"size": 3})
    assert _delta2(s.board, 3, (0, 1), (0, 0)) == 3          # +1.5 value, legal
    assert "0,1>0,0" in G.legal_moves(s)

    # B B W        (rows listed top r=2 .. bottom r=0)
    # B B W   Black: left block of 5; White: right block of 4. No legal swaps.
    # B W W
    board = {}
    for c in range(3):
        for r in range(3):
            board[(c, r)] = BLACK if (c == 0 or (c == 1 and r >= 1)) else WHITE
    st = EmulsionState(n=3, board=board, to_move=BLACK, ply=7)
    assert _delta2(board, 3, (1, 1), (2, 1)) == -3           # 2.0 -> 0.5, illegal
    assert G.legal_moves(st) == []
    assert G.is_terminal(st)
    assert _group_sizes(board, BLACK) == [5]
    assert _group_sizes(board, WHITE) == [4]
    assert G.returns(st) == [1.0, -1.0]                       # Black wins 5 v 4


def test_scoring_tiebreaks():
    """Recursive group-size comparison + the even-board last-mover rule."""
    assert _compare_scores([5, 3], [5, 2]) > 0
    assert _compare_scores([6], [6, 1]) < 0                   # second: 0 vs 1
    assert _compare_scores([4, 4], [4, 4]) == 0
    # 4x4 split down the middle: two 8-groups, full tie, position is terminal.
    board = {(c, r): (BLACK if c < 2 else WHITE)
             for c in range(4) for r in range(4)}
    st = EmulsionState(n=4, board=board, to_move=WHITE, ply=17)
    assert G.legal_moves(st) == [] and G.is_terminal(st)
    assert G.returns(st) == [1.0, -1.0]                       # last mover = Black
    st2 = EmulsionState(n=4, board=board, to_move=BLACK, ply=18)
    assert G.returns(st2) == [-1.0, 1.0]                      # last mover = White
    st3 = EmulsionState(n=4, board=board, to_move=BLACK, ply=0)
    assert G.returns(st3) == [0.0, 0.0]                       # no last mover: draw


def test_monotone_potential_and_termination():
    """Every move strictly increases the monochromatic-adjacency count M
    (bounded by 2*n*(n-1)), so games are finite well inside the ply cap."""
    rng = random.Random(7)
    for n in (5, 8):
        for g in range(8):
            s = G.initial_state({"size": n})
            m_prev = _mono_adjacencies(s.board, n)
            plies = 0
            while not G.is_terminal(s):
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
                m_now = _mono_adjacencies(s.board, n)
                assert m_now > m_prev, "potential must strictly increase"
                m_prev = m_now
                plies += 1
                assert plies <= 2 * n * (n - 1)
            assert not s.drawn                                # real end, not ply cap
            ret = G.returns(s)
            assert ret in ([1.0, -1.0], [-1.0, 1.0])          # even/odd n: winner


if __name__ == "__main__":
    test_initial_position()
    test_initial_moves()
    test_delta_formula_and_shared_move_sets()
    test_legality_anchors()
    test_scoring_tiebreaks()
    test_monotone_potential_and_termination()
    print("emulsion selftest: OK")
