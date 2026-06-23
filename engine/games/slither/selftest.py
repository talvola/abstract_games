"""Standalone correctness anchor for Slither (Corey Clark, 2010).

Run: PYTHONPATH=. python3 games/slither/selftest.py

Pure stdlib + the agp package only. Asserts conformance plus the rule-specific
anchor:
  (1) a square board where Black connects top<->bottom and White left<->right;
  (2) a turn = OPTIONAL king-step slide of an own stone to an empty cell, then a
      MANDATORY placement, subject to the no-bare-diagonal restriction (a
      diagonal same-colour pair must share a common orthogonal same-colour
      stone);
  (3) connection = an ORTHOGONAL chain of own stones joining the two edges; win
      = connect your edges.
Plus: a hand-built legal slide+place, an illegal bare-diagonal placement
rejected, a diagonal-with-common-stone accepted, and a connection win.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ENGINE))

from agp import check, load  # noqa: E402

GAME_DIR = ENGINE / "games" / "slither"


def _new(size=8, options=None):
    _manifest, game = load(GAME_DIR)
    st = game.initial_state(options=options or {"size": size})
    return game, st


def test_conformance():
    manifest, game = load(GAME_DIR)
    res = check(game, manifest, games=20)
    assert res.ok, f"conformance failed: {getattr(res, 'errors', res)}"


def test_initial():
    game, st = _new(8)
    assert game.current_player(st) == 0, "Black moves first"
    assert not game.is_terminal(st)
    # First turn: board empty, no slide possible, every empty placement is legal
    # (a lone stone has no diagonal pair). So 64 placement moves on 8x8.
    moves = game.legal_moves(st)
    assert len(moves) == 64, f"expected 64 opening placements, got {len(moves)}"
    assert all(">" not in m for m in moves), "no slide possible with no stones"


def test_connect_helper():
    from games.slither.game import _connects, BLACK, WHITE  # noqa: E402

    size = 5
    bcol = {(2, r): BLACK for r in range(size)}
    assert _connects(bcol, BLACK, size), "Black vertical column connects top-bottom"
    assert not _connects(bcol, WHITE, size)
    wrow = {(c, 2): WHITE for c in range(size)}
    assert _connects(wrow, WHITE, size), "White horizontal row connects left-right"
    assert not _connects(wrow, BLACK, size)
    # Diagonal-only chain must NOT connect (orthogonal connection required).
    diag = {(i, i): BLACK for i in range(size)}
    assert not _connects(diag, BLACK, size), "diagonal chain must not win"
    broken = {(2, r): BLACK for r in range(size) if r != 2}
    assert not _connects(broken, BLACK, size), "broken column must not connect"


def test_no_bare_diagonal_rule():
    """The legality predicate itself: a bare diagonal is illegal; a diagonal
    sharing a common orthogonal stone is legal."""
    from games.slither.game import _legal_position, BLACK  # noqa: E402

    size = 5
    # Bare diagonal: two Black stones touching only at a corner, no common
    # orthogonal Black neighbour -> illegal.
    bare = {(1, 1): BLACK, (2, 2): BLACK}
    assert not _legal_position(bare, BLACK, size), "bare diagonal must be illegal"
    # Add a common orthogonal stone (2,1) adjacent to both (1,1) and (2,2) -> legal.
    fixed = {(1, 1): BLACK, (2, 2): BLACK, (2, 1): BLACK}
    assert _legal_position(fixed, BLACK, size), "diagonal with shared orthogonal ok"
    # The OTHER shared corner cell (1,2) also legalises it.
    fixed2 = {(1, 1): BLACK, (2, 2): BLACK, (1, 2): BLACK}
    assert _legal_position(fixed2, BLACK, size), "either shared corner cell works"
    # Orthogonal adjacency alone is always fine.
    ortho = {(1, 1): BLACK, (1, 2): BLACK, (1, 3): BLACK}
    assert _legal_position(ortho, BLACK, size), "orthogonal adjacency is allowed"
    # A diagonal pair of DIFFERENT colours is irrelevant to Black's check.
    mixed = {(1, 1): BLACK, (2, 2): 1}
    assert _legal_position(mixed, BLACK, size), "opponent diagonal does not matter"


def test_illegal_bare_diagonal_placement_rejected():
    """A placement that creates a bare diagonal is not in legal_moves; a slide
    that fixes it (or a different placement) is."""
    from games.slither.game import SlitherState, BLACK  # noqa: E402

    game, _ = _new(5)
    # Black has a lone stone at (1,1); Black to move.
    st = SlitherState(size=5, board={(1, 1): BLACK}, to_move=BLACK)
    moves = set(game.legal_moves(st))
    # Placing at (2,2) would make a bare diagonal with (1,1) -> illegal as a
    # plain placement.
    assert "2,2" not in moves, "bare-diagonal placement must be rejected"
    # But a placement that fills a shared corner is fine, e.g. (2,1) then... no:
    # (2,1) is orthogonal to (1,1) only -> always legal.
    assert "2,1" in moves, "orthogonal placement is legal"
    # And we CAN reach the (2,2) diagonal legally by a slide+place that also
    # supplies the common stone: e.g. there exists some slide+place move whose
    # final board has both (1,1) and (2,2) Black plus a shared orthogonal stone.
    # Simpler: a slide+place that ends at (2,2) is legal only with a shared
    # corner present. Verify at least one slide+place move exists.
    slide_moves = [m for m in moves if ">" in m]
    assert slide_moves, "slide+place moves should be available"


def test_legal_slide_then_place():
    """A hand-built legal slide+place move applies correctly and is in
    legal_moves."""
    from games.slither.game import SlitherState, BLACK  # noqa: E402

    game, _ = _new(5)
    # Black stones at (0,0) and (2,2). (0,0)-(2,2) are not adjacent (fine).
    # Move (2,2) by a king step to (1,1): now (0,0) and (1,1) are a bare
    # diagonal -> that final board would be illegal UNLESS the placement supplies
    # a common stone. Place at (1,0): orthogonal to (0,0) and (1,1) -> legal.
    st = SlitherState(size=5, board={(0, 0): BLACK, (2, 2): BLACK}, to_move=BLACK)
    move = "2,2>1,1>1,0"
    assert move in game.legal_moves(st), "the slide+place fix-up move must be legal"
    st2 = game.apply_move(st, move)
    assert st2.board.get((1, 1)) == BLACK, "stone slid to (1,1)"
    assert (2, 2) not in st2.board, "source vacated"
    assert st2.board.get((1, 0)) == BLACK, "new stone placed"
    assert st2.board.get((0, 0)) == BLACK, "old stone unchanged"
    assert game.current_player(st2) == 1, "turn passes to White"
    # Without the corner stone, the same slide+place ending bare-diagonal must be
    # illegal: slide (2,2)->(1,1) and place far away at (4,4).
    bad = "2,2>1,1>4,4"
    assert bad not in game.legal_moves(st), "bare-diagonal slide+place must be illegal"


def test_win_by_connection():
    """Black wins by completing a top-to-bottom orthogonal chain."""
    from games.slither.game import SlitherState, BLACK  # noqa: E402

    game, _ = _new(5)
    # Black already has column c=2 at r=0..3; White has a harmless far stone.
    # Black to move; placing (2,4) completes the orthogonal top->bottom chain.
    board = {(2, 0): BLACK, (2, 1): BLACK, (2, 2): BLACK, (2, 3): BLACK, (4, 0): 1}
    st = SlitherState(size=5, board=board, to_move=BLACK)
    assert st.winner is None
    assert "2,4" in game.legal_moves(st), "completing placement must be legal"
    st2 = game.apply_move(st, "2,4")
    assert st2.winner == BLACK, "Black wins by orthogonal connection"
    assert game.is_terminal(st2)
    assert game.returns(st2) == [1.0, -1.0]


def test_white_win_by_connection():
    from games.slither.game import SlitherState, WHITE  # noqa: E402

    game, _ = _new(5)
    board = {(0, 2): WHITE, (1, 2): WHITE, (2, 2): WHITE, (3, 2): WHITE, (0, 0): 0}
    st = SlitherState(size=5, board=board, to_move=WHITE)
    assert "4,2" in game.legal_moves(st)
    st2 = game.apply_move(st, "4,2")
    assert st2.winner == WHITE, "White wins by orthogonal connection"
    assert game.returns(st2) == [-1.0, 1.0]


def test_diagonal_does_not_win():
    """A diagonal-only path joining the edges is NOT a win."""
    from games.slither.game import SlitherState, BLACK, _connects  # noqa: E402

    size = 5
    # A staircase of Black stones touching only diagonally from top to bottom.
    # Make each diagonal pair legal by adding a shared orthogonal stone, but the
    # connection check (orthogonal) must still fail to reach the far edge.
    # Simpler: directly assert _connects rejects a pure diagonal.
    diag = {(i, i): BLACK for i in range(size)}
    assert not _connects(diag, BLACK, size), "diagonal staircase is not a connection"


def main():
    test_conformance()
    test_initial()
    test_connect_helper()
    test_no_bare_diagonal_rule()
    test_illegal_bare_diagonal_placement_rejected()
    test_legal_slide_then_place()
    test_win_by_connection()
    test_white_win_by_connection()
    test_diagonal_does_not_win()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
