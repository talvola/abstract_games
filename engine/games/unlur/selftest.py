"""Standalone correctness anchor for Unlur (pure stdlib: agp + this game only).

Asserts: hexhex geometry, the six sides' ownership/opposite/non-adjacent
structure, the contract opening protocol (place black off-border, pass assigns
Black to the passer and White to the other, White moves next), BOTH asymmetric
win conditions reached via apply_move (a Black-Y win and a White-line win) plus
the self-loss rules (Black completing a line loses; White completing a Y loses),
and serialize/deserialize round-trip.

Run: PYTHONPATH=. python3 games/unlur/selftest.py   ->  prints "SELFTEST OK".
"""

from __future__ import annotations

import sys

from games.unlur.game import (
    Unlur, UnlurState, BLACK, WHITE,
    _cells, _side_id, _border, _has_y, _has_line,
)


def _ids(cells):
    return [f"{q},{r}" for (q, r) in cells]


def test_geometry():
    g = Unlur()
    for size in (6, 7, 8):
        cells = _cells(size)
        # hexhex cell count = 3N^2 - 3N + 1
        assert len(cells) == 3 * size * size - 3 * size + 1, size
        # Six sides each of length N (N-2 non-corner + 2 corners), 6 corners,
        # border = 6*(N-1) cells.
        border = _border(size)
        assert len(border) == 6 * (size - 1), (size, len(border))
        side_of = _side_id(size)
        # Every side index 0..5 appears; corners belong to exactly two sides.
        appearing = set()
        corner_count = 0
        for c, ids in side_of.items():
            appearing |= ids
            if len(ids) == 2:
                corner_count += 1
        assert appearing == {0, 1, 2, 3, 4, 5}, appearing
        assert corner_count == 6, corner_count
        # Each side has exactly N cells (counting the two shared corners).
        per_side = {i: 0 for i in range(6)}
        for ids in side_of.values():
            for i in ids:
                per_side[i] += 1
        assert all(v == size for v in per_side.values()), per_side


def test_contract_protocol():
    g = Unlur()
    s = g.initial_state({"size": 6})
    assert s.phase == "contract" and s.black_seat is None
    # Border cells are NOT legal placements during the contract; pass is.
    moves = set(g.legal_moves(s))
    assert "pass" in moves
    border_ids = set(_ids(_border(6)))
    assert not (border_ids & moves), "border cells must be illegal in contract"
    # A contract placement is BLACK regardless of seat.
    s1 = g.apply_move(s, "0,0")          # seat 0 places
    assert s1.board[(0, 0)] == BLACK and s1.phase == "contract"
    assert s1.to_move == 1 and s1.black_seat is None
    # Seat 1 now passes -> seat 1 becomes Black, seat 0 becomes White, White moves.
    s2 = g.apply_move(s1, "pass")
    assert s2.phase == "play"
    assert s2.black_seat == 1, "passer becomes Black"
    assert s2.to_move == 0, "the OTHER seat (White) moves next"
    # The colour each seat now places:
    assert g._colour_of_seat(s2, 1) == BLACK
    assert g._colour_of_seat(s2, 0) == WHITE


def _play(g, s, color_seq):
    """Apply a list of (seat-agnostic) cell strings, trusting to_move ordering."""
    for mv in color_seq:
        s = g.apply_move(s, mv)
    return s


def test_black_y_win():
    """Hand-build a contract+play sequence where Black connects three
    non-adjacent sides (a Y) and wins. We drive entirely through apply_move."""
    g = Unlur()
    size = 6
    s = g.initial_state({"size": size})
    # Resolve the contract immediately: seat 0 passes -> seat 0 = Black, seat 1 = White.
    s = g.apply_move(s, "pass")
    assert s.black_seat == 0 and s.to_move == 1  # White to move first

    side_of = _side_id(size)
    # Pick one cell on each of sides 0, 2, 4 (the {0,2,4} non-adjacent triple) and
    # a connecting path. Easiest: build a Black chain across the board by listing
    # a connected set of cells that touches sides 0, 2 and 4, then verify _has_y.
    # We just need SOME black group hitting {0,2,4}; place black on a star of
    # cells from centre (0,0) out to one cell of each of sides 0,2,4.
    def a_cell_on(side):
        for c, ids in side_of.items():
            if side in ids and len(ids) == 1:  # non-corner cell of that side
                return c
        for c, ids in side_of.items():
            if side in ids:
                return c
        raise AssertionError(side)

    # Build straight rays of black from centre to each target side using a BFS
    # path so the group is connected. We place black (seat 0) and filler white
    # (seat 1) alternately; white plays harmless corners-free interior cells far
    # away to avoid forming a line.
    targets = [a_cell_on(0), a_cell_on(2), a_cell_on(4)]

    # Compute connected paths centre->target via simple greedy stepping in axial.
    def path(dst):
        from games.unlur.game import _neighbors
        # BFS over the hexhex to get a shortest path of on-board cells.
        cells = set(_cells(size))
        start = (0, 0)
        prev = {start: None}
        frontier = [start]
        while frontier:
            nxt = []
            for cur in frontier:
                for nb in _neighbors(*cur):
                    if nb in cells and nb not in prev:
                        prev[nb] = cur
                        nxt.append(nb)
            frontier = nxt
        chain = []
        cur = dst
        while cur is not None:
            chain.append(cur)
            cur = prev[cur]
        return list(reversed(chain))

    black_cells = []
    for t in targets:
        for c in path(t):
            if c not in black_cells:
                black_cells.append(c)

    # Interleave: White (to move first) plays a throwaway, then Black plays a
    # chain cell, repeat. Throwaway whites are interior cells not on the chain
    # and chosen to avoid an accidental opposite-side line.
    cells = list(_cells(size))
    border = _border(size)
    interior_pool = [c for c in cells if c not in border and c not in black_cells]
    wi = 0
    won = False
    for bc in black_cells:
        # White move (throwaway interior, never building toward a line edge)
        while wi < len(interior_pool):
            wcell = interior_pool[wi]; wi += 1
            if wcell not in s.board:
                break
        s = g.apply_move(s, f"{wcell[0]},{wcell[1]}")
        if s.winner is not None:
            break
        # Black move (chain cell)
        if (bc) in s.board:
            continue
        s = g.apply_move(s, f"{bc[0]},{bc[1]}")
        if s.winner is not None:
            won = True
            break

    assert s.winner == 0, f"Black (seat 0) should win the Y, got {s.winner} ({s.win_reason})"
    assert "Y" in (s.win_reason or ""), s.win_reason
    # Direct predicate check too.
    assert _has_y(s.board, size, BLACK)


def test_white_line_win():
    """White connects two opposite sides (a line) and wins, via apply_move."""
    g = Unlur()
    size = 6
    s = g.initial_state({"size": size})
    # seat 1 passes -> seat 1 = Black, seat 0 = White; White (seat 0) moves first.
    s = g.apply_move(s, "2,1")          # contract: seat 0 places black interior (off the line)
    s = g.apply_move(s, "pass")         # seat 1 passes -> Black=1, White=0
    assert s.black_seat == 1 and s.to_move == 0

    from games.unlur.game import _neighbors
    side_of = _side_id(size)
    # A vertical line of white from a cell on side 1 (r=-(N-1)) to side 4 (r=N-1):
    # step r from -(N-1) to N-1 at q=0 (all on-board: |q|<=n, |s|=|q+r|<=n holds
    # for q=0 since |r|<=n). That chain touches sides 1 and 4 (opposite pair).
    n = size - 1
    white_cells = [(0, r) for r in range(-n, n + 1)]
    # sanity: endpoints on opposite sides
    assert 1 in side_of[white_cells[0]] and 4 in side_of[white_cells[-1]]

    cells = list(_cells(size))
    border = _border(size)
    black_pool = [c for c in cells
                  if c not in white_cells and c != (0, 0)]
    bi = 0
    for wc in white_cells:
        if wc in s.board:
            # White already there (e.g. via prior); skip its turn? Instead place
            # any other white-safe cell — but to keep parity, only skip if filled.
            pass
        s = g.apply_move(s, f"{wc[0]},{wc[1]}")   # White move
        if s.winner is not None:
            break
        # Black throwaway far from forming a Y.
        while bi < len(black_pool) and (black_pool[bi] in s.board or black_pool[bi] in white_cells):
            bi += 1
        if bi < len(black_pool):
            bc = black_pool[bi]; bi += 1
            s = g.apply_move(s, f"{bc[0]},{bc[1]}")
            if s.winner is not None:
                break

    assert s.winner == 0, f"White (seat 0) should win the line, got {s.winner} ({s.win_reason})"
    assert "line" in (s.win_reason or ""), s.win_reason
    assert _has_line(s.board, size, WHITE)


def test_self_loss_rules():
    """Black completing a LINE (opponent's goal) without a Y loses; White
    completing a Y without a line loses. Reached via apply_move."""
    g = Unlur()
    size = 6
    n = size - 1

    # --- Black makes a line -> Black loses (White wins) ---
    s = g.initial_state({"size": size})
    s = g.apply_move(s, "pass")            # Black = seat 0, White = seat 1; White moves first
    assert s.black_seat == 0 and s.to_move == 1
    from games.unlur.game import _neighbors
    side_of = _side_id(size)
    black_line = [(0, r) for r in range(-n, n + 1)]   # sides 1 & 4 (opposite)
    cells = list(_cells(size)); border = _border(size)
    white_pool = [c for c in cells if c not in black_line]
    wi = 0
    # White moves first; alternate W, B.
    for bc in black_line:
        # White throwaway
        while wi < len(white_pool) and (white_pool[wi] in s.board or white_pool[wi] in black_line):
            wi += 1
        wc = white_pool[wi]; wi += 1
        s = g.apply_move(s, f"{wc[0]},{wc[1]}")
        if s.winner is not None:
            break
        if bc in s.board:
            continue
        s = g.apply_move(s, f"{bc[0]},{bc[1]}")    # Black builds toward a line
        if s.winner is not None:
            break
    assert s.winner == 1, f"Black's line must hand the win to White, got {s.winner} ({s.win_reason})"
    assert "loses" in (s.win_reason or "")
    assert not _has_y(s.board, size, BLACK), "guard: black must NOT also have a Y"

    # --- White makes a Y -> White loses (Black wins) ---
    s = g.initial_state({"size": size})
    s = g.apply_move(s, "0,0")             # contract black
    s = g.apply_move(s, "pass")            # passer seat1 = Black, seat0 = White; White moves
    assert s.black_seat == 1 and s.to_move == 0
    # Build a white Y touching sides {0,2,4}. Reuse the path builder.
    def a_cell_on(side):
        for c, ids in side_of.items():
            if side in ids and len(ids) == 1:
                return c
        for c, ids in side_of.items():
            if side in ids:
                return c
        raise AssertionError(side)
    def path(dst):
        cells_s = set(_cells(size)); start = (0, 0)
        prev = {start: None}; frontier = [start]
        while frontier:
            nxt = []
            for cur in frontier:
                for nb in _neighbors(*cur):
                    if nb in cells_s and nb not in prev:
                        prev[nb] = cur; nxt.append(nb)
            frontier = nxt
        chain = []; cur = dst
        while cur is not None:
            chain.append(cur); cur = prev[cur]
        return list(reversed(chain))
    white_cells = []
    for t in (a_cell_on(0), a_cell_on(2), a_cell_on(4)):
        for c in path(t):
            if c not in white_cells:
                white_cells.append(c)
    # (0,0) is already a black contract stone; drop it from the white chain and
    # rebuild connectivity from its neighbours (the star still meets at centre's
    # neighbours). Simplest: shift the hub to (1,0) by re-pathing from (1,0).
    if (0, 0) in white_cells:
        white_cells = []
        hub = (1, 0)
        def path2(dst):
            cells_s = set(_cells(size)); start = hub
            prev = {start: None}; frontier = [start]
            while frontier:
                nxt = []
                for cur in frontier:
                    for nb in _neighbors(*cur):
                        if nb in cells_s and nb not in prev and nb != (0, 0):
                            prev[nb] = cur; nxt.append(nb)
                frontier = nxt
            if dst not in prev:
                return None
            chain = []; cur = dst
            while cur is not None:
                chain.append(cur); cur = prev[cur]
            return list(reversed(chain))
        for t in (a_cell_on(0), a_cell_on(2), a_cell_on(4)):
            p = path2(t)
            assert p is not None, t
            for c in p:
                if c not in white_cells:
                    white_cells.append(c)
    cells = list(_cells(size)); border = _border(size)
    black_pool = [c for c in cells if c not in white_cells and c != (0, 0)]
    bi = 0
    for wc in white_cells:    # White to move first
        if wc not in s.board:
            s = g.apply_move(s, f"{wc[0]},{wc[1]}")
            if s.winner is not None:
                break
        while bi < len(black_pool) and (black_pool[bi] in s.board or black_pool[bi] in white_cells):
            bi += 1
        if bi < len(black_pool):
            bc = black_pool[bi]; bi += 1
            s = g.apply_move(s, f"{bc[0]},{bc[1]}")
            if s.winner is not None:
                break
    assert s.winner == 1, f"White's Y must hand the win to Black, got {s.winner} ({s.win_reason})"
    assert "loses" in (s.win_reason or "")
    assert not _has_line(s.board, size, WHITE), "guard: white must NOT also have a line"


def test_serialize_roundtrip():
    g = Unlur()
    s = g.initial_state({"size": 7})
    s = g.apply_move(s, "0,0")
    s = g.apply_move(s, "1,0")
    s = g.apply_move(s, "pass")          # into play phase, black_seat set
    s = g.apply_move(s, "2,0")
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d
    assert s2.board == s.board
    assert s2.black_seat == s.black_seat
    assert s2.phase == s.phase and s2.to_move == s.to_move


def main():
    test_geometry()
    test_contract_protocol()
    test_black_y_win()
    test_white_line_win()
    test_self_loss_rules()
    test_serialize_roundtrip()
    print("SELFTEST OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("SELFTEST FAILED:", e)
        sys.exit(1)
