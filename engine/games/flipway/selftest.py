"""Flipway correctness anchors (pure stdlib: agp + this game only).

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/flipway/selftest.py

Anchors:
  (a) opening = single stone anywhere (Black);
  (b) DROP maximality — a 2-empty column pair next to a fully empty window is
      ILLEGAL, the fuller window is legal; 3-cell L-drops next to a lone stone
      are legal;
  (c) differential oracle — an INDEPENDENT implementation of the designer's
      *iterative* drop phrasing (BGG thread) must produce exactly the same
      drop sets as the maximality rule on hundreds of random positions;
  (d) crosscut FLIP resolution both ways on a hand-built crosscut;
  (e) edge-connection wins in both directions, reached via apply_move;
  (f) random playouts terminate with a winner (drawless oracle) on the plain,
      checkered and bicheckered setups.
"""

from __future__ import annotations

import random
from itertools import product
from pathlib import Path

from agp.loader import load_from_dir
from games.flipway.game import (
    BLACK,
    WHITE,
    FlipwayState,
    _connects,
    _encode,
    _flip_pairs,
    _legal_drop_sets,
)

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _state(black, white, to_move, size=4, ply=1):
    b = {}
    for c in black:
        b[c] = BLACK
    for c in white:
        b[c] = WHITE
    return FlipwayState(size=size, board=b, to_move=to_move, ply=ply)


def test_opening_single_stone():
    s = G.initial_state({"size": 6})
    moves = G.legal_moves(s)
    assert len(moves) == 36 and all(">" not in m for m in moves)
    s2 = G.apply_move(s, "3,3")
    assert s2.board == {(3, 3): BLACK} and s2.to_move == WHITE
    # White's reply is now drops (no flips possible yet), all multi-stone.
    replies = G.legal_moves(s2)
    assert replies and all(m.count(">") in (2, 3) for m in replies)


def test_drop_maximality():
    # 4x4 board with a full 2x2 block of stones at the origin. The window at
    # (1,0) has exactly the column pair {(2,0),(2,1)} empty — but the window
    # at (2,0) contains that pair plus two more empties, so the pair drop is
    # ILLEGAL; the full 4-point window drop is legal.
    s = _state([(0, 0), (0, 1)], [(1, 0), (1, 1)], to_move=BLACK)
    moves = set(G.legal_moves(s))
    assert "2,0>2,1" not in moves
    assert _encode([(2, 0), (3, 0), (2, 1), (3, 1)]) in moves
    # A 3-cell L next to a lone stone IS legal (only its own window contains
    # all three of those points).
    s = _state([(1, 1)], [], to_move=WHITE)
    moves = set(G.legal_moves(s))
    assert _encode([(0, 0), (1, 0), (0, 1)]) in moves
    # ... and the lone-stone window's empty set is NOT extendable sideways:
    # every legal drop has 3 or 4 stones here.
    assert all(m.count(">") in (2, 3) for m in moves)
    # Lone empty point surrounded by stones -> a single-point drop is legal.
    b = {(c, r): (c + r) % 2 for c, r in product(range(4), range(4))}
    del b[(1, 2)]
    s = FlipwayState(size=4, board=b, to_move=BLACK, ply=5)
    drops = _legal_drop_sets(s.board, 4)
    assert frozenset({(1, 2)}) in drops
    assert all(E == frozenset({(1, 2)}) for E in drops)


def _reference_drops(board, n):
    """Independent oracle: the designer's ITERATIVE drop phrasing (BGG thread
    2466735): select any 2x2 area with an empty point and fill it; while all
    stones placed so far also fit in a different 2x2 area having an empty
    point, fill that area too; at most four stones per turn. Enumerates every
    terminal fill-set over all starting windows and extension orders."""
    windows = [
        frozenset({(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)})
        for x in range(n - 1) for y in range(n - 1)
    ]
    empt = {w: frozenset(c for c in w if c not in board) for w in windows}
    results = set()
    seen = set()
    stack = [empt[w] for w in windows if empt[w]]
    while stack:
        S = stack.pop()
        if S in seen:
            continue
        seen.add(S)
        exts = [empt[w] for w in windows if S <= w and empt[w] - S]
        if exts:
            stack.extend(e | S for e in exts)  # e | S == e (S subset of empties)
        else:
            results.add(S)
        assert len(S) <= 4
    return results


def test_drop_differential_oracle():
    rng = random.Random(20200713)
    for _ in range(300):
        n = rng.choice([4, 5, 6])
        density = rng.random()
        board = {
            (c, r): rng.randint(0, 1)
            for c, r in product(range(n), range(n))
            if rng.random() < density
        }
        got = set(_legal_drop_sets(board, n))
        want = _reference_drops(board, n)
        assert got == want, (n, sorted(board), sorted(map(sorted, got)),
                             sorted(map(sorted, want)))


def test_flip():
    # Hand-built crosscut at the (1,1) window of a 4x4 board, plus decoys.
    black = [(1, 1), (2, 2)]
    white = [(2, 1), (1, 2)]
    s = _state(black, white, to_move=BLACK, ply=6)
    assert _encode([(2, 1), (1, 2)]) in G.legal_moves(s)
    s2 = G.apply_move(s, _encode([(2, 1), (1, 2)]))
    assert all(s2.board[c] == BLACK for c in [(1, 1), (2, 2), (2, 1), (1, 2)])
    # White flips the OTHER diagonal of the same crosscut.
    s = _state(black, white, to_move=WHITE, ply=6)
    assert _encode([(1, 1), (2, 2)]) in G.legal_moves(s)
    s2 = G.apply_move(s, _encode([(1, 1), (2, 2)]))
    assert all(s2.board[c] == WHITE for c in [(1, 1), (2, 2), (2, 1), (1, 2)])
    # A monochrome 2x2 block is NOT a crosscut.
    s = _state([(1, 1), (2, 2), (2, 1), (1, 2)], [(0, 0)], to_move=WHITE, ply=6)
    assert not _flip_pairs(s.board, 4, WHITE)
    # A crosscut window must be FULL: 2v2 diagonal with an empty corner is not one.
    s = _state([(1, 1)], [(2, 1), (1, 2)], to_move=BLACK, ply=6)
    assert not _flip_pairs(s.board, 4, BLACK)


def test_wins_both_directions():
    # Black completes a top-bottom column via the forced single-point drop.
    black = [(1, 0), (1, 1), (1, 2)]
    white = [(c, r) for c, r in product(range(4), range(4))
             if c != 1 and (c, r) != (1, 3)]
    s = _state(black, white, to_move=BLACK, ply=9)
    assert G.legal_moves(s) == ["1,3"]
    s2 = G.apply_move(s, "1,3")
    assert s2.winner == BLACK and G.is_terminal(s2)
    assert G.returns(s2) == [1.0, -1.0]
    # White mirror: left-right row.
    white2 = [(0, 1), (1, 1), (2, 1)]
    black2 = [(c, r) for c, r in product(range(4), range(4))
              if r != 1 and (c, r) != (3, 1)]
    s = _state(black2, white2, to_move=WHITE, ply=9)
    assert G.legal_moves(s) == ["3,1"]
    s2 = G.apply_move(s, "3,1")
    assert s2.winner == WHITE and G.returns(s2) == [-1.0, 1.0]
    # Orthogonal-only: a DIAGONAL chain does not connect.
    diag = {(i, i): BLACK for i in range(4)}
    assert not _connects(diag, BLACK, 4)


def test_checkered_setups():
    s = G.initial_state({"size": 6, "setup": "checkered"})
    assert len(s.board) == 36 and s.board[(0, 0)] == WHITE
    assert not _connects(s.board, BLACK, 6) and not _connects(s.board, WHITE, 6)
    s = G.initial_state({"size": 6, "setup": "bicheckered"})
    assert len(s.board) == 36 and s.board[(0, 0)] == WHITE
    assert s.board[(2, 0)] == BLACK and s.board[(2, 2)] == WHITE
    assert not _connects(s.board, BLACK, 6) and not _connects(s.board, WHITE, 6)
    # Opening on the full-board setups (designer's BGG description): Black
    # replaces any single WHITE stone; from White on, normal turns = flips.
    for setup in ("checkered", "bicheckered"):
        s = G.initial_state({"size": 6, "setup": setup})
        moves = G.legal_moves(s)
        whites = {c for c, p in s.board.items() if p == WHITE}
        assert set(moves) == {_encode([c]) for c in whites}, setup
        s2 = G.apply_move(s, moves[0])
        cell = tuple(int(v) for v in moves[0].split(","))
        assert s2.board[cell] == BLACK and len(s2.board) == 36
        assert s2.to_move == WHITE
        replies = G.legal_moves(s2)
        assert replies and all(m.count(">") == 1 for m in replies), setup


def _playout(rng, options):
    s = G.initial_state(options)
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    return s


def test_random_playouts_drawless():
    rng = random.Random(314559)
    for options, count in (
        ({"size": 6, "setup": "plain"}, 1500),
        ({"size": 6, "setup": "checkered"}, 400),
        ({"size": 6, "setup": "bicheckered"}, 300),
        ({"size": 12, "setup": "plain"}, 60),
    ):
        wins = {BLACK: 0, WHITE: 0}
        max_ply = 0
        for _ in range(count):
            end = _playout(rng, options)
            assert end.winner is not None, f"DRAW reached: {options}"
            wins[end.winner] += 1
            max_ply = max(max_ply, end.ply)
        assert wins[BLACK] + wins[WHITE] == count
        # generous sanity margin below the defensive ply cap
        assert max_ply < 4 * options["size"] ** 2


if __name__ == "__main__":
    test_opening_single_stone()
    test_drop_maximality()
    test_drop_differential_oracle()
    test_flip()
    test_wins_both_directions()
    test_checkered_setups()
    test_random_playouts_drawless()
    print("flipway selftest: all tests passed")
