"""Qubic correctness anchor — pure stdlib (imports only agp + this game).

Run: PYTHONPATH=. python3 games/qubic/selftest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.qubic.game import Qubic, QubicState, _win_lines, _key  # noqa: E402

G = Qubic()


def _play(cells):
    """Apply the given list of (x,y,z) cells in order (alternating players)."""
    s = G.initial_state()
    for c in cells:
        s = G.apply_move(s, _key(c))
    return s


def main() -> None:
    # --- Anchor 1: exactly 76 winning lines, with the standard breakdown. ----
    lines = _win_lines()
    assert len(lines) == 76, f"expected 76 win lines, got {len(lines)}"
    # every line has 4 distinct cells
    assert all(len(l) == 4 for l in lines)
    assert len(set(lines)) == 76

    # Breakdown 48 axis / 24 face-diag / 4 space-diag (sanity on the geometry).
    def deltas(line):
        cells = sorted(line)
        # direction between consecutive sorted cells is constant for a line
        a, b = cells[0], cells[1]
        return (b[0] - a[0], b[1] - a[1], b[2] - a[2])

    axis = face = space = 0
    for l in lines:
        d = deltas(l)
        nz = sum(1 for v in d if v != 0)
        if nz == 1:
            axis += 1
        elif nz == 2:
            face += 1
        else:
            space += 1
    assert (axis, face, space) == (48, 24, 4), (axis, face, space)

    # --- Anchor 2: opening legal-move count == 64. ---------------------------
    s0 = G.initial_state()
    assert G.current_player(s0) == 0
    assert len(G.legal_moves(s0)) == 64
    assert not G.is_terminal(s0)

    # --- Anchor 3: an AXIS line of 4 -> win (X along x at y=0,z=0). -----------
    # X plays (0,0,0),(1,0,0),(2,0,0),(3,0,0); O plays harmless cells between.
    s = G.initial_state()
    seq = [
        (0, 0, 0), (0, 1, 0),   # X, O
        (1, 0, 0), (0, 2, 0),   # X, O
        (2, 0, 0), (0, 3, 0),   # X, O
        (3, 0, 0),              # X completes the x-axis line
    ]
    for c in seq:
        assert not G.is_terminal(s)
        s = G.apply_move(s, _key(c))
    assert G.is_terminal(s)
    assert s.winner == 0
    assert G.returns(s) == [1.0, -1.0]

    # --- Anchor 4: a FACE diagonal -> win. -----------------------------------
    # X plays the z=0 face main diagonal (0,0,0),(1,1,0),(2,2,0),(3,3,0).
    s = G.initial_state()
    seq = [
        (0, 0, 0), (0, 0, 1),
        (1, 1, 0), (0, 0, 2),
        (2, 2, 0), (0, 0, 3),
        (3, 3, 0),
    ]
    for c in seq:
        assert not G.is_terminal(s)
        s = G.apply_move(s, _key(c))
    assert s.winner == 0, "face diagonal should win"

    # --- Anchor 5: a SPACE diagonal -> win. ----------------------------------
    s = G.initial_state()
    seq = [
        (0, 0, 0), (3, 0, 0),
        (1, 1, 1), (3, 1, 0),
        (2, 2, 2), (3, 2, 0),
        (3, 3, 3),
    ]
    for c in seq:
        assert not G.is_terminal(s)
        s = G.apply_move(s, _key(c))
    assert s.winner == 0, "space diagonal should win"

    # --- Anchor 6: three-in-a-line is NOT a win. -----------------------------
    s = G.initial_state()
    for c in [(0, 0, 0), (0, 1, 0), (1, 0, 0), (0, 2, 0), (2, 0, 0)]:
        s = G.apply_move(s, _key(c))
    assert s.winner is None
    assert not G.is_terminal(s)  # X has 3 in a row but it's not 4

    # --- Anchor 7: a draw IS reachable (constructed full board, no line). ----
    # Use the classic 4-colour "no monochromatic line" colouring of Z_4^3:
    # colour(x,y,z) = (x + 2y + 3z) mod 4, then pair the four colours into two
    # players in a way that breaks every line.  Rather than rely on a clever
    # closed form, search a colouring that fills all 64 with no winning line.
    draw_state = _find_draw()
    assert draw_state is not None, "expected a constructible full-board draw"
    assert len(draw_state.board) == 64
    assert draw_state.winner is None
    assert G.is_terminal(draw_state)
    assert G.returns(draw_state) == [0.0, 0.0]

    # --- Anchor 8: serialize round-trip on a mid-game state. -----------------
    s = _play([(0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 0, 1)])
    d = G.serialize(s)
    s2 = G.deserialize(d)
    assert G.serialize(s2) == d
    # JSON-able
    import json
    json.dumps(d)

    print("qubic selftest: all checks passed (76 lines: 48 axis / 24 face / 4 space)")


def _find_draw():
    """Construct a full board with no winning line by brute-force assignment.

    Greedy + backtracking over the 64 cells, alternating X/O counts (32 each,
    as a real game ends), rejecting any placement that completes a line.  This
    proves a no-line full board exists and exercises the draw-handling path.
    """
    from games.qubic.game import _all_cells, _lines_through

    cells = list(_all_cells())
    n = len(cells)
    board: dict = {}
    lines_through = _lines_through()

    def completes(cell, p):
        # Would placing p at cell finish one of its lines? (cell not yet placed)
        for line in lines_through[cell]:
            if all(board.get(c) == p for c in line if c != cell):
                return True
        return False

    # Need an exact-cover style search; keep it bounded with simple ordering.
    sys.setrecursionlimit(10000)

    def rec(i, cx, co):
        if i == n:
            return True
        cell = cells[i]
        # try the player with more remaining first to keep balance
        order = (0, 1) if cx <= co else (1, 0)
        for p in order:
            if (p == 0 and cx == 0) or (p == 1 and co == 0):
                continue
            if completes(cell, p):
                continue
            board[cell] = p
            if rec(i + 1, cx - (p == 0), co - (p == 1)):
                return True
            del board[cell]
        return False

    if not rec(0, 32, 32):
        return None
    # Re-derive a QubicState (winner None, full).
    return QubicState(board=dict(board), to_move=0, winner=None)


if __name__ == "__main__":
    main()
