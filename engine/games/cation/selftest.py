"""Cation correctness anchors (pure stdlib: agp + this game only).

Anchors:
  (a) crosscut detection on hand-built 2x2 patterns;
  (b) rule-(a) legality — a placement forming a crosscut with the opponent's
      LATEST stone is illegal, the same crosscut out of older stones is legal;
  (c) the forced pass (designer: "Black couldn't play at the empty point
      because it would form a crosscut with c1, placed by White on their
      latest turn") + the double-pass draw backstop mechanism;
  (d) rule-(b) crosscut resolution: the exact forced move set on a built
      position, and the removal-only fallback on a full board;
  (e) edge-to-edge win detection for both colours (reached via apply_move);
  (f) replay of the designer's own 15-move 4x4 game record (center opening,
      from the Zillions package's "Perfect play on 4x4.zsg"), which exercises
      a legal old-stone crosscut, a forced relocation and a Black win;
  (g) pie-rule swap;
  (h) termination + drawlessness over seeded random playouts.

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/cation/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.cation.game import (BLACK, WHITE, CationState, _crosscut_squares,
                               _is_crosscut)

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _state(size, black, white, to_move=BLACK, last=None, ply=8, passes=0):
    b = {}
    for c in black:
        b[c] = BLACK
    for c in white:
        b[c] = WHITE
    return CationState(size=size, board=b, to_move=to_move, last=last,
                       ply=ply, passes=passes)


def test_crosscut_detection():
    """(a) Both orientations of the 2x2 crosscut; non-crossing 2x2s are not."""
    cut1 = {(0, 0): BLACK, (1, 1): BLACK, (1, 0): WHITE, (0, 1): WHITE}
    cut2 = {(0, 0): WHITE, (1, 1): WHITE, (1, 0): BLACK, (0, 1): BLACK}
    assert _is_crosscut(cut1, 0, 0) and _is_crosscut(cut2, 0, 0)
    # Same colour on both diagonals / stripes / incomplete squares: no crosscut.
    assert not _is_crosscut({(0, 0): BLACK, (1, 1): BLACK,
                             (1, 0): BLACK, (0, 1): BLACK}, 0, 0)
    assert not _is_crosscut({(0, 0): BLACK, (1, 1): WHITE,
                             (1, 0): BLACK, (0, 1): WHITE}, 0, 0)
    assert not _is_crosscut({(0, 0): BLACK, (1, 1): BLACK, (1, 0): WHITE}, 0, 0)
    assert _crosscut_squares(cut1, 4) == [(0, 0)]


def test_rule_a_latest_stone_ban():
    """(b) Placing into a crosscut is banned only when the crosscut would
    contain the opponent's LATEST stone; older stones are fair game (ko)."""
    black, white = [(0, 1)], [(0, 0), (1, 1), (3, 3)]
    # Black at (1,0) would form the crosscut {(0,0),(1,0),(0,1),(1,1)}.
    s_old = _state(4, black, white, to_move=BLACK, last=(3, 3))
    assert "1,0" in G.legal_moves(s_old)      # crosscut of older stones: legal
    s_new = _state(4, black, white, to_move=BLACK, last=(1, 1))
    assert "1,0" not in G.legal_moves(s_new)  # contains latest stone: illegal
    ns = G.apply_move(s_old, "1,0")           # ... and it really is a crosscut
    assert _crosscut_squares(ns.board, 4) == [(0, 0)]


def _forced_pass_state(last):
    """3x3, one empty point (1,0); every Black placement there would form a
    crosscut containing White's latest stone (1,1)."""
    return _state(3,
                  black=[(0, 1), (2, 1), (0, 2), (1, 2), (2, 2)],
                  white=[(0, 0), (1, 1), (2, 0)],
                  to_move=BLACK, last=last)


def test_forced_pass():
    """(c) No legal placement -> the ONLY move is the forced pass."""
    s = _forced_pass_state(last=(1, 1))
    assert _crosscut_squares(s.board, 3) == []
    assert G.legal_moves(s) == ["pass"]
    # After the opponent passed/removed (no latest stone), the same point is
    # playable again — the restriction is strictly about the latest stone.
    s2 = _forced_pass_state(last=None)
    assert "1,0" in G.legal_moves(s2)
    # Pass hands over the turn and clears the latest-stone marker.
    ns = G.apply_move(s, "pass")
    assert ns.to_move == WHITE and ns.last is None and not G.is_terminal(ns)


def test_double_pass_draw_backstop():
    """(c) Two consecutive passes = the documented honest-draw backstop."""
    s = _forced_pass_state(last=(1, 1))
    s = CationState(size=s.size, board=s.board, to_move=s.to_move,
                    last=s.last, ply=s.ply, passes=1)
    ns = G.apply_move(s, "pass")
    assert ns.draw and G.is_terminal(ns) and G.returns(ns) == [0.0, 0.0]


def test_rule_b_resolution_moves():
    """(d) With a crosscut on the board the mover MUST relocate one of their
    two stones in it; destinations creating a new crosscut are excluded."""
    s = _state(4,
               black=[(0, 0), (1, 1), (2, 2), (3, 3)],
               white=[(1, 0), (0, 1), (2, 3)],
               to_move=WHITE, last=(0, 0))
    assert _crosscut_squares(s.board, 4) == [(0, 0)]
    empt = [(2, 0), (3, 0), (2, 1), (3, 1), (0, 2), (1, 2), (3, 2), (0, 3), (1, 3)]
    # (3,2) is banned: W there would form the crosscut {(2,2),(3,2),(2,3),(3,3)}.
    expect = {f"{f[0]},{f[1]}>{q[0]},{q[1]}"
              for f in [(1, 0), (0, 1)] for q in empt if q != (3, 2)}
    assert set(G.legal_moves(s)) == expect
    # Applying one destroys the crosscut, marks the relocated stone as latest.
    ns = G.apply_move(s, "1,0>2,1")
    assert _crosscut_squares(ns.board, 4) == []
    assert ns.last == (2, 1) and ns.board[(2, 1)] == WHITE
    assert (1, 0) not in ns.board and ns.to_move == BLACK


def test_rule_b_removal_fallback():
    """(d) No empty destination at all -> the stone is simply removed."""
    s = _state(3,
               black=[(0, 0), (1, 1), (2, 1), (2, 2)],
               white=[(1, 0), (0, 1), (2, 0), (0, 2), (1, 2)],
               to_move=WHITE, last=(2, 2))
    assert _crosscut_squares(s.board, 3) == [(0, 0)]
    assert set(G.legal_moves(s)) == {"1,0", "0,1"}     # bare-cell removals
    ns = G.apply_move(s, "1,0")
    assert (1, 0) not in ns.board and ns.last is None and ns.to_move == BLACK
    assert not G.is_terminal(ns)
    # The freed point is immediately playable (no latest stone to respect).
    assert "1,0" in G.legal_moves(ns)


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
    s = _play(3, ["0,0", "0,1", "2,2", "1,1", "1,0", "2,1"])
    assert s.winner == WHITE and G.returns(s) == [-1.0, 1.0]


def test_diagonal_does_not_connect():
    """(e) Diagonal adjacency must NOT count as a connection."""
    s = _state(3, black=[(0, 0), (1, 1), (2, 2)], white=[(2, 0)],
               to_move=WHITE, last=(2, 2))
    # A diagonal Black staircase touches both rows but wins nothing:
    # reconstruct via a real placement to trigger the win check.
    s = _state(3, black=[(0, 0), (1, 1)], white=[(2, 0), (2, 1)],
               to_move=BLACK, last=(2, 1))
    ns = G.apply_move(s, "2,2")
    assert ns.winner is None and not G.is_terminal(ns)


def test_designer_4x4_game_replay():
    """(f) The designer's own 15-move 4x4 game (Zillions "Perfect play on
    4x4.zsg", center opening b3): every recorded move is legal here, move 9
    forms a crosscut out of OLD stones, move 10 is White's forced relocation
    c1->b4, and Black wins on move 15 (a4-a3-b3-c3-c2-c1). Zillions aN ->
    (0, N-1) etc.; rows are 0-based from Black's near edge."""
    moves = ["1,2", "1,1", "2,1", "3,0", "2,2", "2,0", "0,0", "0,1",
             "1,0",                       # forms the crosscut b1/c1/b2/c2
             "2,0>1,3",                   # White's forced resolution c1->b4
             "2,0", "2,3", "0,3", "3,3", "0,2"]
    s = G.initial_state({"size": 4})
    for i, mv in enumerate(moves):
        lm = G.legal_moves(s)
        assert mv in lm, f"replay move {i + 1} ({mv}) illegal"
        if i == 9:   # after Black's b1 the position is a rule-(b) turn
            assert _crosscut_squares(s.board, 4) == [(1, 0)]
            assert all(">" in m or ("," in m and _cell_occupied(s, m)) for m in lm)
        s = G.apply_move(s, mv)
    assert s.winner == BLACK and G.returns(s) == [1.0, -1.0]


def _cell_occupied(s, mv):
    c, r = mv.split(",")
    return (int(c), int(r)) in s.board


def test_pie_rule_swap():
    """(g) White may swap on their first turn only; the stone changes hands
    via the value-preserving diagonal transpose (c,r)->(r,c)."""
    s = G.initial_state({"size": 5})
    assert "swap" not in G.legal_moves(s)
    # Off-diagonal opening: the mirrored point must be the transpose.
    s2 = G.apply_move(s, "1,3")
    assert "swap" in G.legal_moves(s2)
    ns = G.apply_move(s2, "swap")
    assert ns.board == {(3, 1): WHITE} and ns.to_move == BLACK
    assert "swap" not in G.legal_moves(ns)
    # Diagonal opening is a fixed point of the mirror.
    sd = G.apply_move(s, "2,2")
    nd = G.apply_move(sd, "swap")
    assert nd.board == {(2, 2): WHITE}
    # ... and swap is not offered on any later ply either.
    ns2 = G.apply_move(G.apply_move(s2, "1,1"), "3,3")
    assert "swap" not in G.legal_moves(ns2)


def test_random_playouts_terminate():
    """(h) Seeded random playouts all terminate; Cation is drawless, so no
    draws (a draw here = the documented backstop, i.e. a bug in normal play)."""
    rng = random.Random(20260710)
    wins = [0, 0]
    for size, n in ((5, 120), (7, 40)):
        for _ in range(n):
            s = G.initial_state({"size": size})
            steps = 0
            while not G.is_terminal(s):
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
                steps += 1
                assert steps <= 8 * size * size
            r = G.returns(s)
            assert r != [0.0, 0.0], "unexpected draw in random play"
            wins[0 if r[0] > 0 else 1] += 1
    assert wins[0] and wins[1]          # both colours win some random games
    # Round-trip a mid-game state through serialize/deserialize.
    s = G.initial_state({"size": 5})
    for _ in range(9):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("cation selftest: all passed")


if __name__ == "__main__":
    run()
