"""Standalone correctness anchor for Gonnect.

Run: PYTHONPATH=. python3 games/gonnect/selftest.py

Pure stdlib + the agp package only. Asserts conformance plus rule-specific
positions: Go-style group capture (zero-liberty enemy groups removed), illegal
suicide, positional superko, and the win-by-connection check (a player linking
their two opposite board edges with a 4-orthogonal chain). Prints "SELFTEST OK"
and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ENGINE))

from agp import check, load  # noqa: E402

GAME_DIR = ENGINE / "games" / "gonnect"


def _new(size=9, options=None):
    _manifest, game = load(GAME_DIR)
    st = game.initial_state(options=options or {"size": size})
    return game, st


def _ascii(game, st):
    size = st.size
    rows = []
    for r in range(size):
        row = []
        for c in range(size):
            v = st.board.get((c, r))
            row.append("." if v is None else ("B" if v == 0 else "W"))
        rows.append(" ".join(row))
    return "\n".join(rows)


def _place(game, st, moves):
    """Apply a sequence of "c,r" moves, asserting each is legal first."""
    for m in moves:
        assert m in game.legal_moves(st), (
            f"expected {m!r} legal in:\n{_ascii(game, st)}"
        )
        st = game.apply_move(st, m)
    return st


def test_conformance():
    manifest, game = load(GAME_DIR)
    res = check(game, manifest, games=40)
    assert res.ok, f"conformance failed: {getattr(res, 'errors', res)}"


def test_initial():
    game, st = _new(9)
    assert game.current_player(st) == 0, "Black moves first"
    assert not game.is_terminal(st)
    assert len(game.legal_moves(st)) == 81, "all 81 points legal at start"


def test_connect_helper():
    """Direct check of the connection predicate (edge assignment)."""
    from games.gonnect.game import _connects, BLACK, WHITE  # noqa: E402

    size = 5
    # A vertical Black column c=2 from r=0 to r=4 connects top<->bottom.
    bcol = {(2, r): BLACK for r in range(size)}
    assert _connects(bcol, BLACK, size), "Black vertical column connects top-bottom"
    assert not _connects(bcol, WHITE, size), "that column is not a White win"
    # A horizontal White row r=2 from c=0 to c=4 connects left<->right.
    wrow = {(c, 2): WHITE for c in range(size)}
    assert _connects(wrow, WHITE, size), "White horizontal row connects left-right"
    assert not _connects(wrow, BLACK, size), "that row is not a Black win"
    # A broken Black column (missing one cell) does NOT connect.
    bbroken = {(2, r): BLACK for r in range(size) if r != 2}
    assert not _connects(bbroken, BLACK, size), "broken column must not connect"
    # Diagonal-only does not connect (4-orthogonal adjacency required).
    diag = {(i, i): BLACK for i in range(size)}
    assert not _connects(diag, BLACK, size), "diagonal must not connect"


def test_win_by_connection():
    """Black wins by completing a top-to-bottom orthogonal chain.

    On a 5x5 board, Black builds a vertical column at c=2 while White plays
    harmless moves far away. The move that completes the chain wins immediately.
    """
    game, st = _new(5)
    # Black aims to fill column c=2 (r=0..4). White plays along col c=4 (its own
    # edge, but never completes a left-right chain). Interleave B/W.
    # B(2,0) W(4,0) B(2,1) W(4,1) B(2,2) W(4,2) B(2,3) W(4,3) -> Black to play (2,4).
    st = _place(game, st, ["2,0", "4,0", "2,1", "4,1", "2,2", "4,2", "2,3", "4,3"])
    assert st.winner is None, "no winner before the chain is complete"
    assert game.current_player(st) == 0
    st2 = game.apply_move(st, "2,4")  # completes top->bottom chain
    assert st2.winner == 0, "Black wins by connection"
    assert game.is_terminal(st2)
    assert game.returns(st2) == [1.0, -1.0]


def test_white_win_by_connection():
    """White wins by completing a left-to-right orthogonal chain."""
    game, st = _new(5)
    # Black moves first, so White's 5th (winning) placement is the 10th move:
    # it needs 5 Black + 4 White moves before it. Black plays harmless stones on
    # row r=0; White builds row r=2 (c=0..3), then completes left->right at (4,2).
    # B(0,0) W(0,2) B(1,0) W(1,2) B(2,0) W(2,2) B(3,0) W(3,2) B(4,0) -> W to play (4,2)
    st = _place(game, st, [
        "0,0", "0,2", "1,0", "1,2", "2,0", "2,2", "3,0", "3,2", "4,0",
    ])
    assert st.winner is None
    assert game.current_player(st) == 1, "White to move"
    st2 = game.apply_move(st, "4,2")  # completes left->right chain
    assert st2.winner == 1, "White wins by connection"
    assert game.returns(st2) == [-1.0, 1.0]


def test_group_capture():
    """A multi-stone enemy group with zero liberties is removed as a unit."""
    game, st = _new(9)
    # White vertical group (4,4)-(4,5). Black fills all surrounding liberties.
    # Liberties: (3,4)(5,4)(4,3)(3,5)(5,5)(4,6).
    st = _place(game, st, [
        "3,4", "4,4", "5,4", "4,5", "4,3", "0,0",
        "3,5", "0,1", "5,5", "0,2",
    ])
    assert game.current_player(st) == 0
    st2 = game.apply_move(st, "4,6")  # fills the last liberty -> capture group
    assert (4, 4) not in st2.board and (4, 5) not in st2.board, "whole group captured"
    # Capture alone does NOT win in Gonnect (no connection formed yet).
    assert st2.winner is None, "capturing does not win Gonnect"
    assert not game.is_terminal(st2)


def test_suicide_illegal():
    """Placing into an enclosed point that captures nothing is illegal."""
    game, st = _new(9)
    # Build a Black ring around empty point (2,2): (1,2)(3,2)(2,1)(2,3).
    st = _place(game, st, ["1,2", "8,8", "3,2", "7,8", "2,1", "6,8", "2,3", "5,8"])
    st = _place(game, st, ["0,0"])  # one more Black move -> White to play
    assert game.current_player(st) == 1, "White to move"
    assert "2,2" not in game.legal_moves(st), "White suicide at (2,2) must be illegal"


def test_capture_beats_suicide():
    """A move that self-fills but captures an enemy group is legal (capture first)."""
    game, st = _new(9)
    # White stone at (0,1); liberties (0,0),(1,1),(0,2). Black fills (1,1),(0,2),
    # leaving (0,0). Black plays (0,0): captures White -> legal (not suicide).
    st = _place(game, st, ["1,1", "0,1", "0,2", "8,8"])
    assert game.current_player(st) == 0
    assert "0,0" in game.legal_moves(st), "capturing move must be legal"
    st2 = game.apply_move(st, "0,0")
    assert (0, 1) not in st2.board, "White captured"


def test_positional_superko():
    """A legal move never recreates any prior whole-board position."""
    from games.gonnect.game import _board_key  # noqa: E402

    g, fresh = _new(9)
    k_empty = _board_key(fresh.board, fresh.size)
    assert k_empty in fresh.history, "empty position seeded in history"
    after = g.apply_move(fresh, "4,4")
    # History accumulates prior boards.
    assert k_empty in after.history
    assert _board_key(after.board, after.size) in after.history
    # No legal move from `after` lands on a board already in history.
    for m in g.legal_moves(after):
        nb = g.apply_move(after, m)
        assert _board_key(nb.board, nb.size) not in after.history, (
            f"move {m} repeats a prior position (superko violated)"
        )


def test_superko_blocks_recapture():
    """Directly verify a position-repeating recapture is rejected by superko.

    Construct a board where White could recapture back to an earlier whole-board
    position; that exact prior key sits in history, so the move is illegal.
    """
    from games.gonnect.game import GonnectState, _board_key, _resolve  # noqa: E402

    g, _ = _new(7)
    size = 7
    # Ko shape near a corner:
    #   row0:  . B W .
    #   row1:  B W . W
    #   row2:  . B W .
    # Black at (1,0),(0,1),(1,2);  White at (2,0),(1,1),(3,1),(2,2).
    # Empty ko point: (2,1).
    # If Black plays (2,1): it captures W(1,1) (its only liberty was (2,1)),
    # producing board_after. Then White playing (1,1) would recapture B(2,1) and
    # return to the board BEFORE Black's capture (= board_before) — forbidden.
    black = {(1, 0), (0, 1), (1, 2)}
    white = {(2, 0), (1, 1), (3, 1), (2, 2)}
    board_before = {}
    for cell in black:
        board_before[cell] = 0
    for cell in white:
        board_before[cell] = 1
    key_before = _board_key(board_before, size)

    # Sanity: Black at (2,1) captures the lone White (1,1).
    after_board, captured = _resolve(board_before, 2, 1, 0, size)
    assert captured, "Black (2,1) should capture White (1,1)"
    assert (1, 1) not in after_board, "captured White stone removed"
    assert (2, 1) in after_board, "Black stone remains"

    # White to move on `after_board`, with the pre-capture board in history.
    st = GonnectState(
        size=size,
        board=after_board,
        to_move=1,
        history=frozenset({key_before, _board_key(after_board, size)}),
    )
    # White (1,1) would recapture B(2,1) and restore board_before -> superko-illegal.
    recap_board, recap_captured = _resolve(after_board, 1, 1, 1, size)
    assert recap_captured, "White (1,1) recaptures Black (2,1)"
    assert _board_key(recap_board, size) == key_before, "recapture repeats prior board"
    assert "1,1" not in g.legal_moves(st), "superko must forbid the repeating recapture"


def main():
    test_conformance()
    test_initial()
    test_connect_helper()
    test_win_by_connection()
    test_white_win_by_connection()
    test_group_capture()
    test_suicide_illegal()
    test_capture_beats_suicide()
    test_positional_superko()
    test_superko_blocks_recapture()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
