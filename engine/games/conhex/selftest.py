"""Standalone correctness anchor for ConHex (pure stdlib: agp + this game only).

Asserts:
  * board structure: 69 points, 41 cells, the per-cell border-point counts,
    every point used, a symmetric / valid cell-adjacency graph, the side lines;
  * the claiming rule (reaching ceil(n/2) of a cell's points claims it, first
    to the threshold wins the cell);
  * the connection win, REACHED via apply_move (build a Red top->bottom chain);
  * serialize / deserialize round-trip.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.conhex.game import (  # noqa: E402
    ConHex, RED, YELLOW,
    _all_points, _space_points, _point_spaces, _neighbours, _lines,
    _threshold, _space_type, _sp_xy, _cell_polygon,
)


def test_structure():
    pts = _all_points()
    assert len(pts) == 69, len(pts)
    assert len(set(pts)) == 69
    sp = _space_points()
    assert len(sp) == 41, len(sp)
    # all points fall on the 11x11 grid
    for p in pts:
        x, y = (int(t) for t in p.split(","))
        assert 0 <= x <= 10 and 0 <= y <= 10
    # border-point counts: 16 rim cells (3 pts), 24 interior (6 pts), 1 centre (5)
    sizes = sorted(len(v) for v in sp.values())
    assert sizes.count(3) == 16
    assert sizes.count(6) == 24
    assert sizes.count(5) == 1
    # thresholds
    for cid, verts in sp.items():
        n = len(verts)
        assert _threshold(cid) == (n + 1) // 2
    # every point borders >=1 cell, and the union covers all 69 points
    used = set()
    for v in sp.values():
        used.update(v)
    assert used == set(pts)
    inv = _point_spaces()
    assert set(inv) == set(pts)
    # adjacency graph: symmetric, references only real cells
    for cid in sp:
        for nb in _neighbours(cid):
            assert nb in sp, (cid, nb)
            assert cid in _neighbours(nb), (cid, nb)
    # side lines: 5 cells each; corners are shared between adjacent sides
    (na, nb), (wa, wb) = _lines()
    for line in (na, nb, wa, wb):
        assert len(line) == 5
    # the NW corner cell s0,0 sits on both the top line and the left line
    assert "s0,0" in na and "s0,0" in wa
    # every cell polygon is a non-degenerate (>=3 vertex) outline
    for cid in sp:
        assert len(_cell_polygon(cid)) >= 3


def test_claiming():
    g = ConHex()
    s = g.initial_state()
    # The corner cell s0,0 borders points 0,0 / 1,2 / 2,1 (threshold 2).
    # Red pegs 0,0 (no claim yet); Yellow pegs an unrelated far point;
    # Red pegs 1,2 -> now owns 2 of 3 -> claims s0,0.
    s = g.apply_move(s, "0,0")        # Red
    assert "s0,0" not in s.spaces
    s = g.apply_move(s, "9,5")        # Yellow elsewhere (no swap)
    s = g.apply_move(s, "1,2")        # Red -> claim
    assert s.spaces.get("s0,0") == RED, s.spaces
    # "first to the threshold owns it": Yellow holds 1 point of s0,0 (none here),
    # but cannot take an already-claimed cell. Peg the third point as Yellow and
    # confirm ownership does not change.
    s = g.apply_move(s, "2,1")        # Yellow pegs the last s0,0 point
    assert s.spaces.get("s0,0") == RED


def test_centre_claim():
    # Centre cell s5,5-id has 5 points, threshold 3 ("any three").
    g = ConHex()
    s = g.initial_state()
    centre_id = None
    for cid in _space_points():
        if _space_type(*_sp_xy(cid)) == "centre":
            centre_id = cid
    cpts = list(_space_points()[centre_id])
    # Red takes three of the centre points (Yellow plays away each time).
    away = [p for p in _all_points() if p not in cpts]
    ai = 0
    for i, p in enumerate(cpts[:3]):
        s = g.apply_move(s, p)            # Red
        if i < 2:
            s = g.apply_move(s, away[ai]); ai += 1   # Yellow elsewhere
    assert s.spaces.get(centre_id) == RED, s.spaces


def test_connection_win():
    """Build a Red top->bottom chain of 5 left-rim cells, reached via moves."""
    g = ConHex()
    s = g.initial_state()
    chain = ["s0,0", "s15,0", "s14,0", "s13,0", "s12,0"]
    # Distinct Red points that, once all placed, give Red the threshold on each
    # chain cell. Place every bordering point of each chain cell as Red.
    red_targets = []
    seen = set()
    for cid in chain:
        for p in _space_points()[cid]:
            if p not in seen:
                seen.add(p)
                red_targets.append(p)
    yellow_pool = [p for p in _all_points() if p not in seen]
    yi = 0
    # Skip the pie: Yellow must NOT swap. Interleave Red target / Yellow filler.
    for i, rp in enumerate(red_targets):
        assert s.winner is None
        s = g.apply_move(s, rp)              # Red
        if s.winner is not None:
            break
        # Yellow plays a harmless far point (never the pie on its 1st move here).
        s = g.apply_move(s, yellow_pool[yi]); yi += 1
    assert s.winner == RED, (s.winner, s.spaces)
    # All chain cells are Red-owned and the stored connection path is valid.
    for cid in chain:
        assert s.spaces.get(cid) == RED
    assert len(s.conn_path) >= 2
    assert s.conn_path[0] in _lines()[0][0]      # starts on Red's top line
    assert s.conn_path[-1] in _lines()[0][1]     # ends on Red's bottom line
    assert g.returns(s) == [1.0, -1.0]


def test_serialize_roundtrip():
    g = ConHex()
    s = g.initial_state()
    for mv in ["0,0", "9,5", "1,2", "8,5"]:
        s = g.apply_move(s, mv)
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert s2.points == s.points
    assert s2.spaces == s.spaces
    assert s2.to_move == s.to_move
    assert s2.winner == s.winner
    assert g.serialize(s2) == d


def test_swap():
    g = ConHex()
    s = g.initial_state()
    s = g.apply_move(s, "3,2")           # Red opens
    assert "swap" in g.legal_moves(s)    # Yellow may swap
    s2 = g.apply_move(s, "swap")
    # The opening peg is now Yellow's; back to Red, ply advanced.
    assert s2.points == {"3,2": YELLOW}
    assert s2.to_move == RED
    assert "swap" not in g.legal_moves(s2)


def main():
    test_structure()
    test_claiming()
    test_centre_claim()
    test_connection_win()
    test_serialize_roundtrip()
    test_swap()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
