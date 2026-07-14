"""Side Stitch — standalone correctness anchor (pure stdlib: agp + this game).

Anchors: (a) board geometry — 169 cells, 42 perimeter cells = exactly the
PERIM_COLORS keys, each of the 7 colour-sides touched by 7 cells, 7 boundary
cells touching 2; (b) a group's value = distinct colour-sides touched, with a
boundary cell counting for BOTH; (c) the recursive lexicographic tiebreak;
(d) an early double pass is an honest DRAW; (e) seeded playouts terminate,
full-board playouts are decisive; (f) serialize round-trip; (g) pie-swap.
"""

import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.side_stitch.game import (
    SideStitch, SideStitchState, BLACK, WHITE, RAD,
    _cells, _groups, _group_value, _score_list, _compare, _radius,
    PERIM_COLORS, SIDE_COLORS,
)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_geometry():
    cells = _cells()
    check(len(cells) == 169, f"expected 169 cells, got {len(cells)}")
    perim = {c for c in cells if _radius(*c) == RAD}
    check(len(perim) == 42, f"expected 42 perimeter cells, got {len(perim)}")
    # PERIM_COLORS keys are EXACTLY the perimeter cells.
    check(set(PERIM_COLORS) == perim,
          "PERIM_COLORS keys must equal the perimeter cells")
    # Every colour name is a known side.
    for cs in PERIM_COLORS.values():
        for name in cs:
            check(name in SIDE_COLORS, f"unknown colour {name}")
    # Each of the 7 colour-sides is touched by exactly 7 cells.
    counts = {}
    boundary = 0
    for cs in PERIM_COLORS.values():
        if len(cs) == 2:
            boundary += 1
        for name in cs:
            counts[name] = counts.get(name, 0) + 1
    check(len(counts) == 7, f"expected 7 colour-sides, got {len(counts)}")
    for name, n in counts.items():
        check(n == 7, f"side {name} touched by {n} cells (want 7)")
    check(boundary == 7, f"expected 7 boundary cells, got {boundary}")
    check(all(1 <= len(cs) <= 2 for cs in PERIM_COLORS.values()),
          "each perimeter cell touches 1 or 2 sides")
    print("geometry OK")


def test_group_value():
    # A single boundary cell touches BOTH of its sides.
    check(_group_value({(-1, -6)}) == 2, "boundary cell counts for two sides")
    check(PERIM_COLORS[(-1, -6)] == frozenset({"orange", "red"}), "orange/red")
    # A single-colour cell touches one side.
    check(_group_value({(0, -7)}) == 1, "single-colour cell = 1")
    # Union of two boundary cells sharing 'red' = 3 distinct sides.
    check(_group_value({(-1, -6), (-7, 0)}) == 3,
          "orange,red + pink,red = 3 distinct")
    # An interior cell touches no side.
    check(_group_value({(0, 0)}) == 0, "interior cell touches nothing")

    # A real connected edge chain along the 'orange' side that includes both the
    # orange/red boundary cell and the orange/yellow boundary cell: it touches
    # orange, red AND yellow -> value 3 (boundary cells count for two).
    chain = [(-1, -6), (0, -7), (1, -7), (2, -7), (3, -7), (4, -7), (5, -7)]
    for a, b in zip(chain, chain[1:]):
        check((b[0] - a[0], b[1] - a[1]) in
              [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)],
              "chain must be hex-connected")
    board = {c: BLACK for c in chain}
    gs = _groups(board, BLACK)
    check(len(gs) == 1, "chain is one connected group")
    check(_group_value(gs[0]) == 3, "chain touches orange+red+yellow = 3")
    check(_score_list(board, BLACK) == [3], "score list = [3]")
    check(_score_list(board, WHITE) == [], "white has no stones")
    print("group value OK")


def test_recursive_tiebreak():
    check(_compare([6, 3], [6, 2]) == 1, "second-best breaks the tie")
    check(_compare([6, 2], [6, 3]) == -1, "symmetric")
    check(_compare([6, 3], [6, 3, 1]) == -1, "extra group beats missing (0)")
    check(_compare([6, 3, 0], [6, 3]) == 0, "trailing zero == missing")
    check(_compare([4], [4]) == 0, "full tie detected")
    check(_compare([5], [4, 4, 4]) == 1, "single best group wins outright")
    print("tiebreak OK")


def test_double_pass_and_draw():
    g = SideStitch()
    s = g.initial_state({"pie": False})
    check(g.current_player(s) == BLACK, "black starts")
    check("pass" in g.legal_moves(s), "pass legal")
    check("swap" not in g.legal_moves(s), "no swap with pie off")
    # Immediate double pass on the empty board is a genuine tie = DRAW.
    s = g.apply_move(s, "pass")
    check(not g.is_terminal(s), "single pass never ends the game")
    s = g.apply_move(s, "pass")
    check(g.is_terminal(s) and s.winner is None, "total tie is a draw")
    check(g.returns(s) == [0.0, 0.0], "draw returns")

    # A decisive double-pass finish: Black builds a 3-side group, White passes.
    g = SideStitch()
    s = g.initial_state({"pie": False})
    chain = [(-1, -6), (0, -7), (1, -7), (2, -7), (3, -7), (4, -7), (5, -7)]
    for c in chain:
        s = g.apply_move(s, f"{c[0]},{c[1]}")     # black places
        check(not g.is_terminal(s), "game continues")
        s = g.apply_move(s, "pass")               # white passes (reset counter)
    s = g.apply_move(s, "pass")                    # black pass -> double pass
    check(g.is_terminal(s), "double pass ends the game")
    check(s.winner == BLACK, "black's 3-side group beats white's nothing")
    check(g.returns(s) == [1.0, -1.0], "returns reflect black win")
    print("double-pass/draw OK")


def test_swap():
    g = SideStitch()
    s = g.initial_state({"pie": True})
    s = g.apply_move(s, "0,0")
    check("swap" in g.legal_moves(s), "swap offered at ply 1")
    s2 = g.apply_move(s, "swap")
    check(s2.board[(0, 0)] == WHITE, "swap recolours the stone")
    check(g.current_player(s2) == BLACK, "black moves after swap")
    check("swap" not in g.legal_moves(s2), "swap only once")
    # A first-move pass must NOT offer (or crash on) swap.
    s = g.initial_state({"pie": True})
    s = g.apply_move(s, "pass")
    check("swap" not in g.legal_moves(s), "no swap after an opening pass")
    print("swap OK")


def test_serialize_roundtrip():
    g = SideStitch()
    s = g.initial_state({"pie": True})
    s = g.apply_move(s, "0,0")
    s = g.apply_move(s, "swap")
    s = g.apply_move(s, "1,-1")
    s = g.apply_move(s, "pass")
    d = g.serialize(s)
    s2 = g.deserialize(d)
    check(g.serialize(s2) == d, "serialize round-trip stable")
    check(s2.board == s.board and s2.passes == s.passes and s2.pie == s.pie,
          "state preserved")
    print("serialize OK")


def test_random_playouts_terminate():
    g = SideStitch()
    rng = random.Random(20260714)
    # (i) unrestricted playouts terminate (may draw via early double pass).
    for _ in range(2):
        s = g.initial_state({"pie": True})
        cap = 2 * len(_cells()) + 4
        plies = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            check(moves, "non-terminal state must have moves")
            s = g.apply_move(s, rng.choice(moves))
            plies += 1
            check(plies <= cap, f"playout exceeded {cap} plies")
        check(s.winner in (BLACK, WHITE, None), "terminal result set")
    # (ii) full-board playouts (never pass) are decisive.
    for _ in range(2):
        s = g.initial_state({"pie": False})
        while not g.is_terminal(s):
            placements = [m for m in g.legal_moves(s) if m not in ("pass", "swap")]
            check(placements, "board not yet full but no placements")
            s = g.apply_move(s, rng.choice(placements))
        check(s.winner in (BLACK, WHITE), "full board is decisive")
        want = [1.0, -1.0] if s.winner == BLACK else [-1.0, 1.0]
        check(g.returns(s) == want, "returns match winner")
    print("random playouts OK")


def test_render_probe():
    g = SideStitch()
    s = g.initial_state({"pie": True})
    s = g.apply_move(s, "0,-7")
    spec = g.render(s)
    board = spec["board"]
    check(board["type"] == "hex", "hex board")
    check(board["shape"] == "hexagon", "hexagon shape")
    check(board["size"] == 8, "size 8")
    tints = board["tints"]
    check(len(tints) == 42, f"42 perimeter tints, got {len(tints)}")
    check(all(v.startswith("#") for v in tints.values()), "tints are hex colours")
    check(all(p["owner"] in (0, 1) for p in spec["pieces"]), "owners 0/1")
    check(len(spec["pieces"]) == 1, "one stone placed")
    h = g.heuristic(s)
    check(len(h) == 2 and abs(h[0] + h[1]) < 1e-9, "heuristic zero-sum")
    print("render probe OK")


def main():
    test_geometry()
    test_group_value()
    test_recursive_tiebreak()
    test_double_pass_and_draw()
    test_swap()
    test_serialize_roundtrip()
    test_random_playouts_terminate()
    test_render_probe()
    print("SELFTEST OK")
    print("all tests passed")


if __name__ == "__main__":
    main()
