"""Standalone correctness anchor for Pentalath.

Run: PYTHONPATH=. python3 games/pentalath/selftest.py

Pure stdlib + the agp package only (no third-party deps, no thousand-game
loops). Pentalath has no published perft, so the anchor is a set of baked rule
assertions:

  (1) hex board — a hexhex with 5 hexes per side (61 cells) and 6-neighbour
      axial adjacency;
  (2) placement of your stone;
  (3) Go-style CAPTURE: a connected enemy group with NO freedom (no adjacent
      empty on-board cell) is removed after placing; enemy groups resolve
      BEFORE your own, so a move is illegal if your group would have no freedom
      and captures nothing (no suicide) — but a capturing move that gains
      freedom IS legal; the board edge grants no freedom;
  (4) WIN = FIVE in a row of your colour along a hex axis (checked post-capture).

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ENGINE))

from agp import check, load  # noqa: E402

GAME_DIR = ENGINE / "games" / "pentalath"


def _new(options=None):
    _manifest, game = load(GAME_DIR)
    st = game.initial_state(options=options)
    return game, st


def test_conformance():
    manifest, game = load(GAME_DIR)
    res = check(game, manifest, games=30)
    assert res.ok, f"conformance failed: {getattr(res, 'errors', res)}"


def test_board_shape():
    """Hexhex, side 5 => 61 cells; 6-neighbour adjacency; corners present."""
    from games.pentalath.game import _cells, _neighbors, _on_board  # noqa: E402

    cells = _cells(5)
    assert len(cells) == 61, f"expected 61 cells, got {len(cells)}"
    # Centre has all 6 neighbours on-board.
    assert all(_on_board(nb, 5) for nb in _neighbors(0, 0)), "centre has 6 nbrs"
    # A corner of the hexagon is present and on the edge (fewer on-board nbrs).
    corner = (4, 0)
    assert _on_board(corner, 5), "corner cell present (not clipped)"
    on = sum(1 for nb in _neighbors(*corner) if _on_board(nb, 5))
    assert on == 3, f"corner should have 3 on-board neighbours, got {on}"
    # Out-of-bounds cells excluded.
    assert not _on_board((5, 0), 5) and not _on_board((3, 3), 5)


def test_initial():
    game, st = _new()
    assert game.current_player(st) == 0, "Black moves first"
    assert not game.is_terminal(st)
    # 61 placements at the start (swap not yet available — Black to move).
    assert len(game.legal_moves(st)) == 61, "all 61 cells legal at start"


def test_place():
    game, st = _new({"swap": False})
    assert "0,0" in game.legal_moves(st)
    st2 = game.apply_move(st, "0,0")
    assert st2.board.get((0, 0)) == 0, "Black stone placed"
    assert game.current_player(st2) == 1, "White to move next"


def test_freedom_helper_edge_no_liberty():
    """The board edge grants NO freedom — only empty on-board cells do."""
    from games.pentalath.game import _has_freedom  # noqa: E402

    # A single Black stone at the corner (4,0): on-board empty neighbours give
    # freedom. Fill all on-board neighbours with enemy stones -> no freedom,
    # even though the corner touches the (off-board) edge on its other sides.
    from games.pentalath.game import _neighbors, _on_board  # noqa: E402

    board = {(4, 0): 0}
    for nb in _neighbors(4, 0):
        if _on_board(nb, 5):
            board[nb] = 1
    assert not _has_freedom(board, {(4, 0)}, 5), "edge stone surrounded = no freedom"
    # Remove one enemy neighbour -> freedom returns (an empty on-board cell).
    onb = [nb for nb in _neighbors(4, 0) if _on_board(nb, 5)]
    del board[onb[0]]
    assert _has_freedom(board, {(4, 0)}, 5), "an empty on-board neighbour gives freedom"


def test_group_capture():
    """A multi-stone enemy group with zero freedom is removed as a unit."""
    from games.pentalath.game import PentalathState, _neighbors, _on_board  # noqa: E402

    # White group {(0,0),(1,0)} (axis-(1,0) line). Its freedoms are all on-board
    # empty neighbours of the two stones. Black surrounds all but one, then
    # plays the last one to capture the whole group.
    white = {(0, 0), (1, 0)}
    lib_cells = set()
    for cell in white:
        for nb in _neighbors(*cell):
            if _on_board(nb, 5) and nb not in white:
                lib_cells.add(nb)
    lib_cells = sorted(lib_cells)
    board = {c: 1 for c in white}
    for c in lib_cells[:-1]:
        board[c] = 0
    last = lib_cells[-1]

    game, _ = _new({"swap": False})
    st = PentalathState(size=5, board=board, to_move=0)
    assert f"{last[0]},{last[1]}" in game.legal_moves(st), "filling last liberty is legal"
    st2 = game.apply_move(st, f"{last[0]},{last[1]}")
    assert (0, 0) not in st2.board and (1, 0) not in st2.board, "whole White group captured"
    assert st2.board.get(last) == 0, "Black stone remains"


def test_suicide_illegal():
    """A placement that self-fills and captures nothing is illegal (no suicide)."""
    from games.pentalath.game import PentalathState, _neighbors, _on_board  # noqa: E402

    # Surround empty cell (0,0) entirely with Black, all other cells empty.
    # White playing into (0,0) would have no freedom and capture nothing.
    board = {}
    for nb in _neighbors(0, 0):
        if _on_board(nb, 5):
            board[nb] = 0  # Black ring
    game, _ = _new({"swap": False})
    st = PentalathState(size=5, board=board, to_move=1)  # White to move
    assert "0,0" not in game.legal_moves(st), "White suicide at (0,0) must be illegal"
    # And Black (same colour as the ring) playing (0,0): it joins the ring, which
    # has plenty of outer freedoms -> legal.
    st_b = PentalathState(size=5, board=board, to_move=0)
    assert "0,0" in game.legal_moves(st_b), "filling own enclosed point (with freedom) is legal"


def test_capture_gives_freedom():
    """A move that fills its own last liberty but captures an enemy group is legal."""
    from games.pentalath.game import PentalathState, _neighbors, _on_board  # noqa: E402

    # Lone White stone at (0,0). Black fills all its on-board neighbours but one,
    # call it X. Now Black plays X: the White stone at (0,0) loses its last
    # freedom and is captured; Black's stone at X then borders the freshly-empty
    # (0,0) -> Black gains freedom by capture. Legal.
    onb = [nb for nb in _neighbors(0, 0) if _on_board(nb, 5)]
    x = onb[-1]
    board = {(0, 0): 1}
    for nb in onb[:-1]:
        board[nb] = 0
    game, _ = _new({"swap": False})
    st = PentalathState(size=5, board=board, to_move=0)
    assert f"{x[0]},{x[1]}" in game.legal_moves(st), "capturing move must be legal"
    st2 = game.apply_move(st, f"{x[0]},{x[1]}")
    assert (0, 0) not in st2.board, "White stone captured"
    assert st2.board.get(x) == 0, "Black stone remains (gained freedom via capture)"


def test_five_helper():
    """The five-in-a-row predicate fires only on a 5-length line on a hex axis."""
    from games.pentalath.game import _has_five  # noqa: E402

    line = {(q, 0): 0 for q in range(-2, 3)}  # (-2,0)..(2,0): 5 along axis (1,0)
    assert _has_five(line, 0), "five along axis (1,0) wins"
    assert not _has_five(line, 1), "not a win for the other colour"
    four = {(q, 0): 0 for q in range(-2, 2)}  # only 4
    assert not _has_five(four, 0), "four in a row does not win"
    # Five along the (1,-1) axis.
    diag = {(q, -q): 0 for q in range(-2, 3)}
    assert _has_five(diag, 0), "five along axis (1,-1) wins"
    # A broken run of 4 + gap + 1 is not five.
    broken = {(q, 0): 0 for q in range(-2, 2)}
    broken[(3, 0)] = 0  # gap at (2,0)
    assert not _has_five(broken, 0), "gap breaks the line"


def test_win_by_five():
    """Black completes a 5-in-a-row and wins immediately (checked post-capture)."""
    from games.pentalath.game import PentalathState  # noqa: E402

    # Black at (-2,0),(-1,0),(1,0),(2,0); empty (0,0) completes the five.
    board = {(-2, 0): 0, (-1, 0): 0, (1, 0): 0, (2, 0): 0}
    # A few harmless White stones somewhere far that keep groups alive.
    board[(-2, 3)] = 1
    board[(-1, 3)] = 1
    game, _ = _new({"swap": False})
    st = PentalathState(size=5, board=board, to_move=0)
    assert st.winner is None
    assert "0,0" in game.legal_moves(st)
    st2 = game.apply_move(st, "0,0")
    assert st2.winner == 0, "Black wins by five in a row"
    assert game.is_terminal(st2)
    assert game.returns(st2) == [1.0, -1.0]


def test_swap():
    """Pie rule: White may swap on its first turn; stones recolour to White."""
    game, st = _new()  # swap defaults on
    st = game.apply_move(st, "0,0")  # Black places
    assert "swap" in game.legal_moves(st), "swap offered to White on first turn"
    st2 = game.apply_move(st, "swap")
    assert st2.board.get((0, 0)) == 1, "stone recoloured to White after swap"
    assert game.current_player(st2) == 0, "play hands back to Black"
    assert "swap" not in game.legal_moves(st2), "swap no longer available"


def main():
    test_conformance()
    test_board_shape()
    test_initial()
    test_place()
    test_freedom_helper_edge_no_liberty()
    test_group_capture()
    test_suicide_illegal()
    test_capture_gives_freedom()
    test_five_helper()
    test_win_by_five()
    test_swap()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
