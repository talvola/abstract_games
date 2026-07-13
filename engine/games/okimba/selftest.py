"""Okimba correctness anchors (pure stdlib: agp + this game only).

Rules per the designer's BGG description (item 468749) and cross-checked
against his reference implementation Okimba.html (functions recheckSquare,
isValidOkimbaMove, checkWin, play):

  (a) naked-diagonal detection — a diagonal friendly pair is naked iff NEITHER
      of its two shared orthogonal points holds a friendly stone (an enemy
      stone there does not rescue it; a friendly one does);
  (b) the legality rule: a placement is legal iff, immediately after placing,
      the TOTAL number of naked diagonals over BOTH colours is <= 1
      (isValidOkimbaMove: nakedDiags[0].size + nakedDiags[1].size <= 1);
  (c) a crosscut-completing placement is ILLEGAL in Okimba (a crosscut is two
      interlocking naked diagonals at once = a total of 2 > 1); and there is NO
      removal — the placed stone is simply added;
  (d) edge-to-edge win detection for both colours (reached via apply_move);
      diagonal adjacency does not connect;
  (e) pie-rule swap (White's first turn only, transpose + recolour);
  (f) termination, the "<=1 naked diagonal" turn-start invariant, both colours
      winning over seeded random playouts, an honest-draw double-pass, and a
      serialize round-trip.

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/okimba/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.okimba.game import (BLACK, WHITE, OkimbaState, _connects,
                               _naked_count, _naked_diagonals)

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _state(size, black, white, to_move=BLACK, last=None, ply=8):
    b = {}
    for c in black:
        b[c] = BLACK
    for c in white:
        b[c] = WHITE
    return OkimbaState(size=size, board=b, to_move=to_move, last=last, ply=ply)


def test_naked_diagonal_detection():
    """(a) Nakedness = no friendly stone on either shared orthogonal point."""
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
    # A crosscut is TWO naked diagonals at once (one of each colour).
    cc = {(0, 0): BLACK, (1, 1): BLACK, (1, 0): WHITE, (0, 1): WHITE}
    assert _naked_diagonals(cc, BLACK) == [((0, 0), (1, 1))]
    assert _naked_diagonals(cc, WHITE) == [((0, 1), (1, 0))]
    assert _naked_count(cc) == 2


def test_legal_placement_at_most_one_naked_total():
    """(b) A placement is legal iff the resulting board has <= 1 naked
    diagonal summed over BOTH colours."""
    # Creating the FIRST naked diagonal is fine (total becomes 1).
    s = _state(5, black=[(1, 1)], white=[], to_move=BLACK)
    assert _naked_count(s.board) == 0
    assert "2,2" in G.legal_moves(s)          # makes 1 naked black -> legal
    ns = G.apply_move(s, "2,2")
    assert _naked_count(ns.board) == 1

    # A second naked diagonal (same colour) would make total 2 -> illegal.
    s2 = _state(5, black=[(1, 1), (2, 2)], white=[], to_move=BLACK)
    assert _naked_count(s2.board) == 1
    # placing black at (3,3) leaves (1,1)-(2,2) naked AND makes (2,2)-(3,3)
    # naked -> 2 total -> illegal; a distant safe point stays legal.
    moves = set(G.legal_moves(s2))
    assert "3,3" not in moves
    assert "0,4" in moves and "4,0" in moves
    # Every offered placement really does keep the total <= 1.
    for mv in moves:
        if mv in ("swap", "pass"):
            continue
        assert _naked_count(G.apply_move(s2, mv).board) <= 1

    # A placement that RESOLVES the existing naked diagonal (fills a shared
    # orthogonal point) is legal even while another naked diagonal exists.
    s3 = _state(6, black=[(1, 1), (2, 2)], white=[(4, 4), (5, 5)], to_move=BLACK)
    assert _naked_count(s3.board) == 2  # constructed over-the-limit position...
    # ...black to move: filling (2,1) kills the black naked pair, leaving only
    # white's -> total 1 -> legal.
    assert "2,1" in G.legal_moves(s3)
    assert _naked_count(G.apply_move(s3, "2,1").board) == 1


def test_crosscut_completing_move_illegal_and_no_removal():
    """(c) Completing a crosscut is ILLEGAL (it makes 2 naked diagonals), and
    Okimba never removes a stone."""
    # Three corners of a 2x2: black (1,1); white (2,1) & (1,2). One naked
    # (white) diagonal exists -> board is valid. Placing black at (2,2)
    # completes the crosscut -> a black naked diagonal too -> total 2.
    s = _state(5, black=[(1, 1)], white=[(2, 1), (1, 2)], to_move=BLACK)
    assert _naked_count(s.board) == 1
    assert "2,2" not in G.legal_moves(s)
    # A harmless placement elsewhere is legal and simply adds the stone
    # (nothing is ever removed).
    ns = G.apply_move(s, "4,4")
    assert ns.board.get((4, 4)) == BLACK
    assert ns.board.get((1, 1)) == BLACK          # placed-earlier stone stays
    assert ns.board.get((2, 1)) == WHITE and ns.board.get((1, 2)) == WHITE
    assert len(ns.board) == len(s.board) + 1      # exactly one stone added


def _play(size, moves):
    s = G.initial_state({"size": size})
    for mv in moves:
        assert mv in G.legal_moves(s), f"{mv} not legal at ply {s.ply}"
        s = G.apply_move(s, mv)
    return s


def test_win_black_top_bottom():
    """(d) Black wins by orthogonally chaining row 0 to row size-1 (a straight
    column creates no naked diagonals, so every move is legal)."""
    s = _play(3, ["0,0", "2,0", "0,1", "2,2", "0,2"])
    assert s.winner == BLACK and G.is_terminal(s)
    assert G.returns(s) == [1.0, -1.0] and G.legal_moves(s) == []


def test_win_white_left_right():
    """(d) White wins by orthogonally chaining col 0 to col size-1 (a straight
    row across the columns). Black fills a harmless separate row meanwhile."""
    s = _play(3, ["0,2", "0,0", "1,2", "1,0", "2,2", "2,0"])
    assert s.winner == WHITE and G.returns(s) == [-1.0, 1.0]


def test_diagonal_does_not_connect():
    """(d) Diagonal adjacency does not connect the edges."""
    # A single black diagonal pair touching neither... just verify _connects
    # requires orthogonality: a black diagonal staircase on 3x3 does not win.
    board = {(0, 0): BLACK, (1, 1): BLACK, (2, 2): BLACK}
    assert not _connects(board, BLACK, 3)
    # but a straight orthogonal column does.
    assert _connects({(0, 0): BLACK, (0, 1): BLACK, (0, 2): BLACK}, BLACK, 3)


def test_pie_rule_swap():
    """(e) White may swap on their first turn only; Black's lone stone is
    reflected across the main diagonal and recoloured White."""
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
    # Swap no longer offered after White's first turn passes.
    ns2 = G.apply_move(G.apply_move(s1, "1,1"), "3,3")
    assert "swap" not in G.legal_moves(ns2)


def test_double_pass_is_honest_draw():
    """(f) A constructed position where BOTH players are stuck (no legal
    placement) resolves to an honest draw via a double pass, never a
    fabricated winner. We only need the pass mechanics to score [0,0]."""
    # Force the stuck path directly: an empty-ish board can always place, so
    # exercise pass accounting on a state flagged as having no placements is
    # awkward to build; instead verify pass -> pass -> draw bookkeeping.
    s = OkimbaState(size=3, board={}, to_move=BLACK, ply=5, passes=0)
    p1 = G.apply_move(s, "pass")
    assert p1.passes == 1 and not p1.draw
    p2 = G.apply_move(p1, "pass")
    assert p2.passes == 2 and p2.draw and G.is_terminal(p2)
    assert G.returns(p2) == [0.0, 0.0]


def test_random_playouts_terminate():
    """(f) Seeded random playouts all terminate under the ply cap; the
    "<= 1 naked diagonal" invariant holds at every turn start; both colours
    win at least once; and a mid-game state round-trips through serialize."""
    rng = random.Random(20260713)
    wins = [0, 0]
    draws = 0
    total = 0
    for size, n in ((5, 200), (7, 120), (9, 50)):
        for _ in range(n):
            s = G.initial_state({"size": size})
            steps = 0
            while not G.is_terminal(s):
                assert _naked_count(s.board) <= 1, "invariant broken pre-move"
                mv = rng.choice(G.legal_moves(s))
                s = G.apply_move(s, mv)
                if mv not in ("pass", "swap"):
                    assert _naked_count(s.board) <= 1, "invariant broken post-move"
                steps += 1
                assert steps < 8 * size * size
            r = G.returns(s)
            if r == [0.0, 0.0]:
                draws += 1
            else:
                wins[0 if r[0] > 0 else 1] += 1
            total += 1
    assert total == 370
    assert wins[0] > 0 and wins[1] > 0, "expected both colours to win sometimes"
    # Round-trip a mid-game state through serialize/deserialize.
    s = G.initial_state({"size": 5})
    for _ in range(9):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("okimba selftest: all passed")


if __name__ == "__main__":
    run()
