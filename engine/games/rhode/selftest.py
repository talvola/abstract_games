"""Rhode correctness anchors (pure stdlib: agp + this game only).

Anchors (rules per the designer's BGG thread boardgamegeek.com/thread/1593043,
cross-checked against his Zillions submission id 2501, Rhode.zrf):

  (a) weak-pair detection — a diagonal friendly pair is weak iff NEITHER of
      its two shared orthogonal points holds a friendly stone (an enemy stone
      there does not rescue it; a friendly one does);
  (b) the forced weak-pair completion move set on constructed positions
      (single pair -> both empty completion points; multiple pairs -> union),
      and free placement when no weak pair exists;
  (c) the .zrf priority fallback: weak pairs exist but no empty completion
      point (constructed boards only — unreachable in real play) -> free
      placement, exactly like Zillions' move-priorities falling through;
  (d) post-placement self-removal — the OTHER friendly stone of a crosscut
      created by the placement is removed, the placed stone survives, enemy
      stones are never removed; and a double-crosscut placement removes both
      diagonal partners at once;
  (e) edge-to-edge win detection for both colours (reached via apply_move);
      diagonal adjacency does not connect;
  (f) win-check TIMING: a position where the placement connects the mover's
      edges PRE-removal but the crosscut removal breaks the chain -> no win
      (the .zrf captures inside the move, before the win check), plus the
      positive twin where the removal is irrelevant and the win stands;
  (g) pie-rule swap (White's first turn only);
  (h) termination + drawlessness + the .zrf-derived invariants (boards are
      crosscut-free at every turn start; every weak pair is completable)
      over seeded random playouts, and a serialize round-trip.

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/rhode/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.rhode.game import (BLACK, WHITE, RhodeState, _completion_points,
                              _crosscut_squares, _weak_pairs)

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _state(size, black, white, to_move=BLACK, last=None, ply=8):
    b = {}
    for c in black:
        b[c] = BLACK
    for c in white:
        b[c] = WHITE
    return RhodeState(size=size, board=b, to_move=to_move, last=last, ply=ply)


def test_weak_pair_detection():
    """(a) Weakness = no friendly stone on either shared orthogonal point."""
    # Bare diagonal pair: weak.
    assert _weak_pairs({(0, 0): BLACK, (1, 1): BLACK}, BLACK) == [((0, 0), (1, 1))]
    # Anti-diagonal orientation too.
    assert _weak_pairs({(0, 1): BLACK, (1, 0): BLACK}, BLACK) == [((0, 1), (1, 0))]
    # A friendly stone adjacent to both stones kills the weakness...
    assert _weak_pairs({(0, 0): BLACK, (1, 1): BLACK, (1, 0): BLACK}, BLACK) == []
    # ...but an ENEMY stone there does not.
    assert _weak_pairs({(0, 0): BLACK, (1, 1): BLACK, (1, 0): WHITE},
                       BLACK) == [((0, 0), (1, 1))]
    # Orthogonal pairs and enemy diagonals are never weak pairs.
    assert _weak_pairs({(0, 0): BLACK, (0, 1): BLACK}, BLACK) == []
    assert _weak_pairs({(0, 0): BLACK, (1, 1): WHITE}, BLACK) == []


def test_forced_completion_single_pair():
    """(b) One weak pair -> the move set is exactly its two empty points."""
    s = _state(5, black=[(1, 1), (2, 2)], white=[(4, 4)], to_move=BLACK)
    assert set(G.legal_moves(s)) == {"2,1", "1,2"}
    # An enemy stone on one completion point: only the other remains legal.
    s = _state(5, black=[(1, 1), (2, 2)], white=[(2, 1), (4, 4)], to_move=BLACK)
    assert set(G.legal_moves(s)) == {"1,2"}


def test_forced_completion_multiple_pairs():
    """(b) Several weak pairs -> the union of their completion points."""
    s = _state(7, black=[(0, 0), (1, 1), (4, 0), (5, 1)], white=[(6, 6), (0, 6)],
               to_move=BLACK)
    assert set(G.legal_moves(s)) == {"1,0", "0,1", "5,0", "4,1"}


def test_free_placement_when_no_weak_pairs():
    """(b) No weak pairs -> any empty point; opponent pairs don't constrain."""
    # White has a weak pair, Black doesn't: Black places freely.
    s = _state(5, black=[(0, 0), (1, 0)], white=[(3, 3), (4, 4)], to_move=BLACK)
    moves = G.legal_moves(s)
    assert len(moves) == 25 - 4 and "2,2" in moves and "0,0" not in moves


def test_zrf_fallback_no_empty_completion_point():
    """(c) Weak pair but every completion point occupied (constructed-only:
    this 2x2 is a crosscut, which never survives a turn in real play) ->
    free placement, per the .zrf's move-priorities fallback."""
    s = _state(5, black=[(0, 0), (1, 1)], white=[(1, 0), (0, 1)], to_move=BLACK)
    assert _weak_pairs(s.board, BLACK) == [((0, 0), (1, 1))]
    assert _completion_points(s.board, s.size, BLACK) == set()
    moves = G.legal_moves(s)
    assert len(moves) == 25 - 4 and "4,4" in moves


def test_removal_placed_stone_survives():
    """(d) Placing into a crosscut removes the OTHER friendly stone; the
    placed stone and the enemy stones stay."""
    s = _state(5, black=[(0, 0)], white=[(1, 0), (0, 1)], to_move=BLACK,
               last=(0, 1))
    assert "1,1" in G.legal_moves(s)          # lone stone: no weak pairs
    ns = G.apply_move(s, "1,1")
    assert ns.board.get((1, 1)) == BLACK       # placed stone survives
    assert (0, 0) not in ns.board              # its diagonal partner is removed
    assert ns.board.get((1, 0)) == WHITE       # enemy stones never removed
    assert ns.board.get((0, 1)) == WHITE
    assert _crosscut_squares(ns.board, 5) == []
    assert ns.to_move == WHITE and ns.winner is None


def test_removal_double_crosscut():
    """(d) A placement in two crosscuts at once removes both partners."""
    s = _state(5, black=[(0, 0), (2, 2)], white=[(1, 0), (0, 1), (2, 1), (1, 2)],
               to_move=BLACK, last=(1, 2))
    assert _weak_pairs(s.board, BLACK) == []   # (0,0)/(2,2) aren't adjacent
    assert "1,1" in G.legal_moves(s)
    ns = G.apply_move(s, "1,1")
    assert ns.board.get((1, 1)) == BLACK
    assert (0, 0) not in ns.board and (2, 2) not in ns.board
    assert sum(1 for v in ns.board.values() if v == WHITE) == 4
    assert _crosscut_squares(ns.board, 5) == []


def _play(size, moves):
    s = G.initial_state({"size": size})
    for mv in moves:
        assert mv in G.legal_moves(s), f"{mv} not legal at ply {s.ply}"
        s = G.apply_move(s, mv)
    return s


def test_win_black_top_bottom():
    """(e) Black wins by orthogonally chaining row 0 to row size-1."""
    s = _play(3, ["0,0", "2,2", "0,1", "2,1", "0,2"])
    assert s.winner == BLACK and G.is_terminal(s)
    assert G.returns(s) == [1.0, -1.0] and G.legal_moves(s) == []


def test_win_white_left_right():
    """(e) White wins by orthogonally chaining col 0 to col size-1."""
    s = _play(3, ["0,0", "0,1", "2,2", "1,1", "2,0", "2,1"])
    assert s.winner == WHITE and G.returns(s) == [-1.0, 1.0]


def test_diagonal_does_not_connect():
    """(e) A full diagonal staircase touches both Black edges but does NOT
    win — only orthogonal chains connect (and its every link is a weak pair,
    so the forced move set is exactly the pairs' completion points)."""
    s = _state(4, black=[(0, 0), (1, 1), (2, 2), (3, 3)], white=[(3, 0)],
               to_move=BLACK, last=(3, 0), ply=8)
    assert set(G.legal_moves(s)) == {"1,0", "0,1", "2,1", "1,2", "3,2", "2,3"}
    ns = G.apply_move(s, "1,0")
    assert ns.winner is None and not G.is_terminal(ns)


def test_win_checked_after_removal_negative():
    """(f) The placement connects Black's edges PRE-removal, but removing the
    crosscut partner (2,2) breaks the chain -> NO win (post-removal check,
    matching the .zrf where captures happen inside the move)."""
    black = [(1, 0), (0, 1), (0, 2), (0, 3), (1, 3), (2, 3), (2, 2),
             (3, 2), (4, 2), (4, 3), (4, 4)]
    white = [(2, 1), (1, 2)]
    s = _state(5, black=black, white=white, to_move=BLACK, last=(1, 2), ply=24)
    assert _crosscut_squares(s.board, 5) == []
    assert _weak_pairs(s.board, BLACK) == [((0, 1), (1, 0))]
    assert set(G.legal_moves(s)) == {"0,0", "1,1"}    # forced completion
    ns = G.apply_move(s, "1,1")
    assert ns.board.get((1, 1)) == BLACK and (2, 2) not in ns.board
    assert ns.winner is None and not G.is_terminal(ns)


def test_win_checked_after_removal_positive():
    """(f) Twin case: the same forced completion wins when the removed
    crosscut partner is NOT part of the chain."""
    black = [(1, 0), (0, 1), (0, 2), (0, 3), (2, 2)]
    white = [(2, 1), (1, 2)]
    s = _state(4, black=black, white=white, to_move=BLACK, last=(1, 2), ply=12)
    assert set(G.legal_moves(s)) == {"0,0", "1,1"}
    ns = G.apply_move(s, "1,1")
    assert (2, 2) not in ns.board              # removal still happened
    assert ns.winner == BLACK and G.returns(ns) == [1.0, -1.0]


def test_pie_rule_swap():
    """(g) White may swap on their first turn only; Black's lone stone is
    reflected across the main diagonal and recoloured (value-preserving
    'change sides': Black joins rows, White joins columns)."""
    s = G.initial_state({"size": 5})
    assert "swap" not in G.legal_moves(s)
    s1 = G.apply_move(s, "1,3")            # off-diagonal: mirror must show
    assert "swap" in G.legal_moves(s1)
    ns = G.apply_move(s1, "swap")
    assert ns.board == {(3, 1): WHITE} and ns.to_move == BLACK
    assert ns.last == (3, 1)
    assert "swap" not in G.legal_moves(ns)
    # A diagonal opening maps to itself.
    nd = G.apply_move(G.apply_move(s, "2,2"), "swap")
    assert nd.board == {(2, 2): WHITE}
    ns2 = G.apply_move(G.apply_move(s1, "1,1"), "3,3")
    assert "swap" not in G.legal_moves(ns2)


def test_random_playouts_terminate():
    """(h) Seeded random playouts all terminate well under the ply cap with
    zero draws; the turn-start invariants from the .zrf analysis hold: the
    board is always crosscut-free, and whenever weak pairs exist there is an
    empty completion point (so the obligation is always satisfiable)."""
    rng = random.Random(20260710)
    wins = [0, 0]
    total = 0
    for size, n in ((5, 300), (7, 150), (9, 60)):
        for _ in range(n):
            s = G.initial_state({"size": size})
            steps = 0
            while not G.is_terminal(s):
                assert _crosscut_squares(s.board, size) == []
                if _weak_pairs(s.board, s.to_move):
                    assert _completion_points(s.board, size, s.to_move)
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
                steps += 1
                assert steps < 8 * size * size
            r = G.returns(s)
            assert r != [0.0, 0.0], "unexpected draw in random play"
            wins[0 if r[0] > 0 else 1] += 1
            total += 1
    assert total == 510 and wins[0] and wins[1]
    # Round-trip a mid-game state through serialize/deserialize.
    s = G.initial_state({"size": 5})
    for _ in range(9):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("rhode selftest: all passed")


if __name__ == "__main__":
    run()
