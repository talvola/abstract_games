"""Akimbo correctness anchors (pure stdlib: agp + this game only).

Rules per the designer's reference JavaScript `Akimbo.html` (author luigi87 =
Luis Bolaños Mures) — the definitive oracle. Anchors:

  (a) naked-diagonal detection — a diagonal friendly pair is naked iff NEITHER
      of its two shared orthogonal corners holds a friendly stone (an enemy
      stone there does NOT rescue it); mirrors the reference `recheckSquare`;
  (b) legality (`isValidAkimboMove`): a placement is legal iff, on the raw
      post-placement board BEFORE removal, count_naked <= 1 for EACH colour
      separately. A placement creating two same-colour naked diagonals is
      illegal — even when a later crosscut removal would reduce it (the bound
      holds "not even momentarily before removing");
  (c) a placement that COMPLETES a crosscut is legal (one naked diagonal of each
      colour) and its resolution removes exactly YOUR OTHER stone in the
      crosscut — the placed stone survives and enemy stones are never removed;
      a double-crosscut placement removes both your partners at once;
  (d) edge-to-edge win detection for both colours (reached via apply_move);
      diagonal adjacency does not connect;
  (e) pie-rule swap (White's first turn only), transpose+recolour;
  (f) termination + drawlessness + the crosscut-free-at-turn-start invariant
      over seeded random playouts, plus a serialize round-trip.

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/akimbo/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.akimbo.game import (BLACK, WHITE, AkimboState, _count_naked,
                               _crosscut_squares, _naked_diagonals)

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _state(size, black, white, to_move=BLACK, last=None, ply=8):
    b = {}
    for c in black:
        b[c] = BLACK
    for c in white:
        b[c] = WHITE
    return AkimboState(size=size, board=b, to_move=to_move, last=last, ply=ply)


def test_naked_diagonal_detection():
    """(a) Nakedness = no friendly stone on either shared orthogonal corner."""
    assert _naked_diagonals({(0, 0): BLACK, (1, 1): BLACK}, BLACK) == [((0, 0), (1, 1))]
    assert _naked_diagonals({(0, 1): BLACK, (1, 0): BLACK}, BLACK) == [((0, 1), (1, 0))]
    # A friendly stone adjacent to both kills the nakedness...
    assert _naked_diagonals({(0, 0): BLACK, (1, 1): BLACK, (1, 0): BLACK}, BLACK) == []
    # ...but an ENEMY stone there does not.
    assert _naked_diagonals({(0, 0): BLACK, (1, 1): BLACK, (1, 0): WHITE},
                            BLACK) == [((0, 0), (1, 1))]
    # Orthogonal pairs and enemy diagonals are never naked diagonals.
    assert _naked_diagonals({(0, 0): BLACK, (0, 1): BLACK}, BLACK) == []
    assert _naked_diagonals({(0, 0): BLACK, (1, 1): WHITE}, BLACK) == []


def test_legality_two_same_colour_naked_illegal():
    """(b) A placement leaving two naked diagonals of your colour is illegal."""
    # Placing Black at (1,1) makes (0,0)-(1,1) AND (1,1)-(2,2) both naked -> 2.
    s = _state(5, black=[(0, 0), (2, 2)], white=[], to_move=BLACK)
    assert "1,1" not in G.legal_moves(s)
    # A distant placement leaving each colour <= 1 naked is legal.
    assert "4,0" in G.legal_moves(s)


def test_legality_bound_before_removal():
    """(b) The bound is judged BEFORE crosscut removal ('not even momentarily').
    Placing Black at (1,1) here makes a crosscut at square (0,0) (whose removal
    of (0,0) would later leave only one Black naked diagonal) BUT also a second
    Black naked diagonal (1,1)-(2,2). Pre-removal that is two Black naked
    diagonals -> ILLEGAL, even though post-removal it would be one."""
    s = _state(5, black=[(0, 0), (2, 2)], white=[(1, 0), (0, 1)], to_move=BLACK)
    # Verify the raw post-placement counts the ref would see.
    b = dict(s.board); b[(1, 1)] = BLACK
    assert _count_naked(b, BLACK) == 2 and _count_naked(b, WHITE) == 1
    assert "1,1" not in G.legal_moves(s)


def test_crosscut_completion_legal_and_removes_your_stone():
    """(c) Completing a crosscut is legal (1 naked per colour) and removes YOUR
    OTHER stone; the placed stone survives and enemy stones stay."""
    s = _state(5, black=[(0, 0)], white=[(1, 0), (0, 1)], to_move=BLACK,
               last=(0, 1))
    # Raw post-placement board is a crosscut: exactly one naked diagonal each.
    b = dict(s.board); b[(1, 1)] = BLACK
    assert _count_naked(b, BLACK) == 1 and _count_naked(b, WHITE) == 1
    assert "1,1" in G.legal_moves(s)
    ns = G.apply_move(s, "1,1")
    assert ns.board.get((1, 1)) == BLACK       # placed stone survives
    assert (0, 0) not in ns.board              # your other stone is removed
    assert ns.board.get((1, 0)) == WHITE       # enemy stones never removed
    assert ns.board.get((0, 1)) == WHITE
    assert _crosscut_squares(ns.board, 5) == []
    assert ns.to_move == WHITE and ns.winner is None


def test_double_crosscut_completion_illegal():
    """(c) Unlike Rhode, Akimbo can NEVER complete two crosscuts with one
    placement: doing so would create two naked diagonals of your colour (one
    per crosscut), which the ≤1-per-colour bound forbids. So a legal placement
    completes at most one crosscut."""
    s = _state(5, black=[(0, 0), (2, 2)], white=[(1, 0), (0, 1), (2, 1), (1, 2)],
               to_move=BLACK, last=(1, 2))
    b = dict(s.board); b[(1, 1)] = BLACK
    assert _count_naked(b, BLACK) == 2      # one naked diagonal per crosscut
    assert "1,1" not in G.legal_moves(s)


def _play(size, moves):
    s = G.initial_state({"size": size})
    for mv in moves:
        assert mv in G.legal_moves(s), f"{mv} not legal at ply {s.ply}"
        s = G.apply_move(s, mv)
    return s


def test_win_black_top_bottom():
    """(d) Black wins by orthogonally chaining row 0 to row size-1."""
    s = _play(3, ["0,0", "2,2", "0,1", "2,1", "0,2"])
    assert s.winner == BLACK and G.is_terminal(s)
    assert G.returns(s) == [1.0, -1.0] and G.legal_moves(s) == []


def test_win_white_left_right():
    """(d) White wins by orthogonally chaining col 0 to col size-1."""
    s = _play(3, ["0,0", "0,1", "2,2", "1,1", "2,0", "2,1"])
    assert s.winner == WHITE and G.returns(s) == [-1.0, 1.0]


def test_diagonal_does_not_connect():
    """(d) A diagonal staircase touches both Black edges but does NOT win —
    only orthogonal chains connect. (It is also illegal to BUILD in Akimbo,
    since each new diagonal link is a naked diagonal; here we hand-build it and
    confirm the win test rejects it.)"""
    s = _state(4, black=[(0, 0), (1, 1), (2, 2), (3, 3)], white=[(3, 0)],
               to_move=WHITE, last=(3, 3), ply=8)
    assert s.winner is None
    from games.akimbo.game import _connects
    assert not _connects(s.board, BLACK, 4)


def test_pie_rule_swap():
    """(e) White may swap on their first turn only; Black's lone stone is
    reflected across the main diagonal and recoloured."""
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
    # After White plays a real move, swap is gone.
    ns2 = G.apply_move(G.apply_move(s1, "1,1"), "3,3")
    assert "swap" not in G.legal_moves(ns2)


def test_random_playouts_terminate():
    """(f) Seeded random playouts all terminate well under the ply cap with
    zero draws; the turn-start invariant holds: the board is always crosscut-
    free, and the ≤1-per-colour bound holds for the position reached."""
    rng = random.Random(20260713)
    wins = [0, 0]
    total = 0
    for size, n in ((5, 300), (7, 150), (9, 40)):
        for _ in range(n):
            s = G.initial_state({"size": size})
            steps = 0
            while not G.is_terminal(s):
                assert _crosscut_squares(s.board, size) == []
                assert _count_naked(s.board, BLACK) <= 1
                assert _count_naked(s.board, WHITE) <= 1
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
                steps += 1
                assert steps < 8 * size * size
            r = G.returns(s)
            assert r != [0.0, 0.0], "unexpected draw in random play"
            wins[0 if r[0] > 0 else 1] += 1
            total += 1
    assert total == 490 and wins[0] and wins[1]
    # Round-trip a mid-game state through serialize/deserialize.
    s = G.initial_state({"size": 5})
    for _ in range(9):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("akimbo selftest: all passed")


if __name__ == "__main__":
    run()
