"""Stigmergy correctness anchors (pure stdlib: agp + this game only).

Anchored on the designer's revised rules (Zillions submission id 3126,
updated 2021-07-03; identical to the bundled ReadMe).

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/stigmergy/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.stigmergy.game import (
    BLACK, WHITE, StigmergyState,
    _adj, _cells, _scores, _seen_counts,
)

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _state(black=(), white=(), size=5, to_move=BLACK, **kw):
    b = {}
    for c in black:
        b[c] = BLACK
    for c in white:
        b[c] = WHITE
    return StigmergyState(size=size, board=b, to_move=to_move, **kw)


def test_board_geometry():
    """Hexhex side 8: 169 cells; 6 corners (3 neighbours), 36 edge cells (4),
    127 interior (6)."""
    assert len(_cells(8)) == 169
    adj = _adj(8)
    from collections import Counter
    counts = Counter(adj.values())
    assert counts == {3: 6, 4: 36, 6: 127}, counts
    # the six corners really are the corners
    assert adj[(7, 0)] == 3 and adj[(0, -7)] == 3 and adj[(-7, 7)] == 3


def test_seen_counts_blocking():
    """Only the FIRST stone per direction is seen; stones behind it are blocked;
    the cell's own occupant is neither seen nor blocking."""
    # Black at (1,0) blocks black at (3,0); black at (-1,1); white at (0,2)
    # behind an empty (0,1).
    s = _state(black=[(1, 0), (3, 0), (-1, 1)], white=[(0, 2)])
    seen = _seen_counts(s.board, s.size)
    assert seen[(0, 0)] == [2, 1], seen[(0, 0)]
    # (2,0) sits between the two black stones: sees both (one per ray);
    # it also sees the white stone along its (-1,1) diagonal.
    assert seen[(2, 0)] == [2, 1], seen[(2, 0)]
    # A stone's own cell: occupant not counted. (1,0) sees (3,0)? blocked by
    # nothing — (2,0) is empty — so yes, 1 black; plus (-1,1)? not on a line
    # through (1,0)... check white (0,2): not on a line either.
    assert seen[(1, 0)] == [1, 0], seen[(1, 0)]


def test_control_placement_and_flip():
    """Interior cell (6 neighbours) needs 4+ seen stones for control: the
    controller may place/flip there, the opponent may not place there."""
    ring4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    # 4 black stones see (0,0): black controls it.
    s = _state(black=ring4, to_move=WHITE)
    assert "0,0" not in G.legal_moves(s)          # White can't place there
    s = _state(black=ring4, to_move=BLACK)
    assert "0,0" in G.legal_moves(s)              # Black can (own control is fine)
    # Only 3 seers: NOT controlled -> White may place.
    s = _state(black=ring4[:3], to_move=WHITE)
    assert "0,0" in G.legal_moves(s)

    # FLIP: white stone on (0,0), black controls -> black may flip it.
    s = _state(black=ring4, white=[(0, 0)], to_move=BLACK)
    assert "0,0" in G.legal_moves(s)
    assert G.describe_move(s, "0,0") == "flip 0,0"
    ns = G.apply_move(s, "0,0")
    assert ns.board[(0, 0)] == BLACK and len(ns.board) == 5
    # NON-flip: only 3 black seers -> no control -> no flip.
    s = _state(black=ring4[:3], white=[(0, 0)], to_move=BLACK)
    assert "0,0" not in G.legal_moves(s)
    # White can never "flip" its own stone.
    s = _state(black=ring4, white=[(0, 0)], to_move=WHITE)
    assert "0,0" not in G.legal_moves(s)


def test_corner_and_edge_thresholds():
    """Corner cells (3 neighbours) are controlled by 2 seen stones; edge cells
    (4 neighbours) need 3."""
    corner = (4, 0)  # size-5 corner: neighbours (3,0),(4,-1),(3,1)
    s = _state(black=[(3, 0), (4, -1)], size=5, to_move=WHITE)
    seen = _seen_counts(s.board, s.size)
    assert _adj(5)[corner] == 3 and seen[corner][BLACK] == 2
    assert "4,0" not in G.legal_moves(s)          # controlled by Black
    s = _state(black=[(3, 0)], size=5, to_move=WHITE)
    assert "4,0" in G.legal_moves(s)              # one seer isn't control
    edge = (4, -2)  # size-5 edge cell (4 neighbours)
    assert _adj(5)[edge] == 4
    s = _state(black=[(3, -2), (4, -3), (4, -1)], size=5, to_move=WHITE)
    seen = _seen_counts(s.board, s.size)
    assert seen[edge][BLACK] == 3
    assert "4,-2" not in G.legal_moves(s)         # 3 of 4: controlled


def test_pass_rules():
    """Pass is legal only when no empty cells remain or every empty cell is
    controlled by some player; never at the start."""
    s = G.initial_state()
    ms = G.legal_moves(s)
    assert "pass" not in ms and len(ms) == 169    # every cell placeable
    # Full board -> pass legal; double pass ends and scores stones.
    cells = _cells(3)
    black = list(cells[:10])
    white = list(cells[10:])
    s = _state(black=black, white=white, size=3)
    ms = G.legal_moves(s)
    assert "pass" in ms                           # board full -> pass is legal
    s2 = G.apply_move(G.apply_move(s, "pass"), "pass")
    assert G.is_terminal(s2)
    assert s2.winner == BLACK and G.returns(s2) == [1.0, -1.0]


def test_scoring_territory_and_komi():
    """Score = stones + controlled empty cells (+ komi to White)."""
    ring6 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
    s = _state(black=ring6, size=3)
    # Black: 6 stones + the centre (sees 6 black). No ring-2 cell is
    # controlled (corners see 1, edges see 2 — below their thresholds).
    assert _scores(s.board, 3, 0, None) == [7.0, 0.0]
    assert _scores(s.board, 3, 2, None) == [7.0, 2.0]


def test_button_and_odd_komi():
    """Odd komi: nobody may pass until someone takes the button; the holder
    gets half a point."""
    s = G.initial_state(options={"komi": 1})
    ms = G.legal_moves(s)
    assert "button" in ms and "pass" not in ms
    # Full board, komi 1, button untaken: pass still barred, button available.
    cells = _cells(3)
    s = _state(black=cells[:10], white=cells[10:], size=3, komi=1)
    ms = G.legal_moves(s)
    assert "button" in ms and "pass" not in ms    # button bars passing
    s = G.apply_move(s, "button")                 # Black takes the button
    assert s.button == BLACK and "button" not in G.legal_moves(s)
    s2 = G.apply_move(G.apply_move(s, "pass"), "pass")
    assert G.is_terminal(s2)
    # Black 10 + 0.5 button = 10.5 vs White 9 + 1 komi = 10 -> Black wins.
    assert _scores(s2.board, 3, 1, s2.button) == [10.5, 10.0]
    assert s2.winner == BLACK


def test_ply_cap_honest_draw():
    """A backstop (ply-cap) ending scores the position as-is; a symmetric tie
    is an honest draw."""
    cap = G._ply_cap(3)
    s = _state(black=[(1, 0)], white=[(-1, 0), (0, 1)], size=3,
               to_move=BLACK, ply=cap - 1)
    ns = G.apply_move(s, "0,-1")                  # 2 stones each, symmetric
    assert G.is_terminal(ns)
    assert ns.winner is None and G.returns(ns) == [0.0, 0.0]


def test_random_playouts_terminate():
    """Random games reach a terminal state; a double-pass ending awards every
    cell (base scores sum to the odd cell total -> drawless at even komi)."""
    rng = random.Random(7)
    for _ in range(3):
        s = G.initial_state(options={"size": 5})
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            assert ms, "non-terminal state with no legal moves"
            s = G.apply_move(s, rng.choice(ms))
        if s.passes >= 2:  # ended by double pass, not a backstop
            b, w = _scores(s.board, 5, 0, None)
            assert b + w == len(_cells(5))        # every cell awarded
            assert s.winner is not None           # drawless at komi 0
        # serialize round-trip on the final state
        assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("stigmergy selftest: all OK")
