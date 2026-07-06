"""Exo-Hex — standalone correctness anchor (pure stdlib: agp + this game only).

Anchors: (a) board construction — exo-stone counts, 12 alternating strings of
(n-1)/2 (6 per colour), empty corner gaps; (b) connectivity THROUGH exo-stones
(a group linking two of its strings scores their sum); (c) the corner gap does
NOT connect adjacent strings; (d) scoring + the recursive tiebreak on
hand-built positions; (e) double-pass ends the game and scores (reached via
apply_move); (f) random playouts terminate on all sizes; plus pie-swap,
serialize round-trip and a render-shape probe.
"""

import random
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.exo_hex.game import (
    ExoHex, BLACK, WHITE, _DIRS,
    _cells, _exo, _ring_corners, _groups, _score_list, _compare, _radius,
)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def _strings(n, player):
    """Maximal same-colour ring strings of the exo arrangement."""
    exo = _exo(n)
    mine = {c for c, p in exo.items() if p == player}
    comps, seen = [], set()
    for cell in mine:
        if cell in seen:
            continue
        comp, stack = {cell}, [cell]
        seen.add(cell)
        while stack:
            cq, cr = stack.pop()
            for dq, dr in _DIRS:
                nb = (cq + dq, cr + dr)
                if nb in mine and nb not in seen:
                    seen.add(nb)
                    comp.add(nb)
                    stack.append(nb)
        comps.append(comp)
    return comps


def test_geometry():
    for n, ncells in ((5, 61), (7, 127), (9, 217)):
        cells = _cells(n)
        check(len(cells) == ncells, f"hexhex-{n}: expected {ncells} cells")
        exo = _exo(n)
        check(len(exo) == 6 * (n - 1), f"hexhex-{n}: expected {6*(n-1)} exo-stones")
        for p in (BLACK, WHITE):
            mine = [c for c, q in exo.items() if q == p]
            check(len(mine) == 3 * (n - 1), f"hexhex-{n}: {3*(n-1)} exo per colour")
            strs = _strings(n, p)
            check(len(strs) == 6, f"hexhex-{n}: 6 strings per colour, got {len(strs)}")
            check(all(len(s) == (n - 1) // 2 for s in strs),
                  f"hexhex-{n}: strings of {(n-1)//2}")
        # every exo cell is on the ring at radius n; corners are empty gaps
        check(all(_radius(q, r) == n for (q, r) in exo), "exo must sit on ring n")
        for c in _ring_corners(n):
            check(c not in exo, f"ring corner {c} must be an empty gap")
        # each exo-stone touches exactly 2 interior cells
        on = set(cells)
        for (q, r) in exo:
            k = sum(1 for dq, dr in _DIRS if (q + dq, r + dr) in on)
            check(k == 2, f"exo {q},{r} must touch 2 interior cells, got {k}")
        # alternation: every string's ring-continuations are either the corner
        # gap or the OTHER colour (so the 12 strings alternate B,W,B,W,...).
        exo_or_gap = set(exo) | _ring_corners(n)
        for p in (BLACK, WHITE):
            for s in _strings(n, p):
                for (q, r) in s:
                    for dq, dr in _DIRS:
                        nb = (q + dq, r + dr)
                        if nb in exo_or_gap and nb not in s:
                            check(_exo(n).get(nb, 1 - p) == 1 - p,
                                  "same-colour exo neighbour outside its string")
    print("geometry OK")


def test_corner_gap():
    # The two exo-stones flanking each corner gap are NOT hex-adjacent.
    for n in (5, 7, 9):
        exo = _exo(n)
        for (cq, cr) in _ring_corners(n):
            flank = [(cq + dq, cr + dr) for dq, dr in _DIRS
                     if (cq + dq, cr + dr) in exo]
            check(len(flank) == 2, "corner gap flanked by 2 exo-stones")
            (aq, ar), (bq, br) = flank
            check((bq - aq, br - ar) not in _DIRS, "gap must break adjacency")
        # On an empty interior, each colour's groups are exactly its 6 strings.
        for p in (BLACK, WHITE):
            gs = _groups({}, p, n)
            check(len(gs) == 6, f"empty board: 6 groups per colour, got {len(gs)}")
            check(_score_list({}, p, n) == [(n - 1) // 2] * 6, "initial scores")
    print("corner gaps OK")


def test_connectivity_and_scoring():
    # hexhex-5: black string on side 0 = {(4,1),(3,2)}, on side 5 = {(5,-4),(5,-3)}.
    # The interior chain (4,0)..(4,-4) down the right edge links the two black
    # strings -> one group containing 2+2 = 4 exo-stones.
    n = 5
    exo = _exo(n)
    check(exo[(4, 1)] == BLACK and exo[(3, 2)] == BLACK, "side-0 black string")
    check(exo[(5, -4)] == BLACK and exo[(5, -3)] == BLACK, "side-5 black string")
    board = {(4, r): BLACK for r in range(-4, 1)}
    bl = _score_list(board, n=n, player=BLACK)
    check(bl == [4, 2, 2, 2, 2], f"linked strings must score 4, got {bl}")
    big = max(_groups(board, BLACK, n), key=len)
    check({(4, 1), (3, 2), (5, -4), (5, -3)} <= big, "group contains both strings")
    # White untouched: still six 2-strings.
    check(_score_list(board, WHITE, n) == [2] * 6, "white unaffected")

    # A stone on the interior corner cell (4,0) alone joins ONLY the black
    # string across it — never the (white) string on the far side of the gap.
    board = {(4, 0): BLACK}
    gs = [g for g in _groups(board, BLACK, n) if (4, 0) in g]
    check(len(gs) == 1 and gs[0] == {(4, 0), (4, 1), (3, 2)},
          "corner cell joins exactly the adjacent own-colour string")
    # An interior-only group scores 0 and is dropped from the list.
    board = {(0, 0): BLACK}
    check(_score_list(board, BLACK, n) == [2] * 6, "exo-less group scores 0")
    print("connectivity/scoring OK")


def test_recursive_tiebreak():
    check(_compare([6, 3], [6, 2]) == 1, "second-best breaks the tie")
    check(_compare([6, 2], [6, 3]) == -1, "symmetric")
    check(_compare([6, 3], [6, 3, 1]) == -1, "extra group beats missing (0)")
    check(_compare([6, 3, 0], [6, 3]) == 0, "trailing zero == missing")
    check(_compare([4], [4]) == 0, "full tie detected")
    check(_compare([5], [4, 4, 4]) == 1, "single best group wins outright")
    print("tiebreak OK")


def test_double_pass_and_swap():
    g = ExoHex()
    s = g.initial_state({"size": "5", "pie": False})
    check(g.current_player(s) == BLACK, "black starts")
    check("pass" in g.legal_moves(s), "pass legal")
    check("swap" not in g.legal_moves(s), "no swap with pie off")

    # Black links two of his strings while White only passes; the pass counter
    # resets on each placement, then a genuine double pass ends the game.
    for i, r in enumerate(range(-4, 1)):
        s = g.apply_move(s, f"4,{r}")          # black placement
        check(not g.is_terminal(s), "game continues")
        s = g.apply_move(s, "pass")            # white pass
        check(not g.is_terminal(s), "single pass never ends the game")
    s = g.apply_move(s, "pass")                # black pass -> double pass
    check(g.is_terminal(s), "double pass ends the game")
    check(s.winner == BLACK, "black's 4-group beats white's 2s")
    check(g.returns(s) == [1.0, -1.0], "returns reflect black win")

    # Pie swap: second player takes over the first stone.
    s = g.initial_state({"size": "5", "pie": True})
    s = g.apply_move(s, "0,0")
    check("swap" in g.legal_moves(s), "swap offered at ply 1")
    s2 = g.apply_move(s, "swap")
    check(s2.board[(0, 0)] == WHITE, "swap recolours the stone")
    check(g.current_player(s2) == BLACK, "black moves after swap")
    check("swap" not in g.legal_moves(s2), "swap only once")
    # A first-move pass must NOT offer (or crash on) swap.
    s = g.initial_state({"size": "5", "pie": True})
    s = g.apply_move(s, "pass")
    check("swap" not in g.legal_moves(s), "no swap after an opening pass")

    # Immediate double pass on the untouched start: both players' groups are
    # six strings of (n-1)/2 — a genuine tie all the way down = a DRAW.
    s = g.initial_state({"size": "5", "pie": False})
    s = g.apply_move(s, "pass")
    s = g.apply_move(s, "pass")
    check(g.is_terminal(s) and s.winner is None, "total tie is a draw")
    check(g.returns(s) == [0.0, 0.0], "draw returns")
    print("double-pass/swap OK")


def test_serialize_roundtrip():
    g = ExoHex()
    s = g.initial_state({"size": "7", "pie": True})
    s = g.apply_move(s, "0,0")
    s = g.apply_move(s, "swap")
    s = g.apply_move(s, "1,-1")
    s = g.apply_move(s, "pass")
    d = g.serialize(s)
    s2 = g.deserialize(d)
    check(g.serialize(s2) == d, "serialize round-trip stable")
    check(s2.board == s.board and s2.n == s.n and s2.passes == s.passes,
          "state preserved")
    print("serialize OK")


def test_random_playouts_terminate():
    g = ExoHex()
    rng = random.Random(20260705)
    for n in (5, 7, 9):
        for trial in range(3 if n < 9 else 1):
            s = g.initial_state({"size": str(n), "pie": True})
            cap = 2 * len(_cells(n)) + 4
            plies = 0
            while not g.is_terminal(s):
                moves = g.legal_moves(s)
                check(moves, "non-terminal state must have moves")
                s = g.apply_move(s, rng.choice(moves))
                plies += 1
                check(plies <= cap, f"hexhex-{n} playout exceeded {cap} plies")
            # random play may double-pass into a genuinely tied position (a
            # draw); played-out boards are decisive.
            check(s.winner in (BLACK, WHITE, None), "terminal result set")
            want = ([0.0, 0.0] if s.winner is None else
                    [1.0, -1.0] if s.winner == BLACK else [-1.0, 1.0])
            check(g.returns(s) == want, "returns match winner")
    print("random playouts OK")


def test_render_probe():
    g = ExoHex()
    for n in (5, 7):
        s = g.initial_state({"size": str(n), "pie": True})
        spec = g.render(s)
        board = spec["board"]
        check(board["type"] == "polygons", "polygons board")
        cells = board["cells"]
        check(isinstance(cells, list), "cells must be a LIST")
        check(all(isinstance(c, dict) and "id" in c and "points" in c
                  for c in cells), "cells are {id, points} dicts")
        ids = {c["id"] for c in cells}
        check(len(ids) == len(cells), "cell ids unique")
        legal_cells = {m for m in g.legal_moves(s) if m not in ("pass", "swap")}
        check(legal_cells <= ids, "every legal move has a rendered cell")
        exo_ids = {i for i in ids if i.startswith("x:")}
        check(len(exo_ids) == 6 * (n - 1), "exo cells rendered")
        check(not (exo_ids & legal_cells), "exo cells never legal moves")
        check(len(ids - exo_ids) == len(_cells(n)), "interior cell count")
        exo_pieces = [p for p in spec["pieces"] if p["cell"].startswith("x:")]
        check(len(exo_pieces) == 6 * (n - 1), "exo-stones drawn as pieces")
        check(all(p["owner"] in (0, 1) for p in spec["pieces"]), "owners 0/1")
        h = g.heuristic(s)
        check(len(h) == 2 and abs(h[0] + h[1]) < 1e-9, "heuristic zero-sum")
    print("render probe OK")


def main():
    test_geometry()
    test_corner_gap()
    test_connectivity_and_scoring()
    test_recursive_tiebreak()
    test_double_pass_and_swap()
    test_serialize_roundtrip()
    test_random_playouts_terminate()
    test_render_probe()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
