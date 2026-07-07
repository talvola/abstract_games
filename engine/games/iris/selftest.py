"""Iris — standalone correctness anchor (pure stdlib: agp + this game only).

Anchors: (a) board — perimeter/gray counts and the antipodal (180-degree)
pairing (rim->rim, corner->corner); (b) turn protocol — gray-only single
opening; a coloured first stone forces the exact antipode (atomic, both empty);
a gray first stone forbids an adjacent second; the forfeit single fires exactly
when no empty non-adjacent gray exists; (c) scoring counts coloured cells in the
best group + recursive tiebreak + genuine-tie -> draw, on hand-built positions;
(d) double-pass ends the game; (e) random playouts terminate on all sizes; plus
serialize round-trip and a render-shape probe.
"""

import random
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.iris.game import (
    Iris, IrisState, BLACK, WHITE, _DIRS,
    _all_cells, _perim, _gray, _pairs, _pair_hue, _antipode,
    _groups, _score_list, _compare, _radius, _adjacent, _cell, _fmt,
)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_geometry():
    for n, tot, per, gry in ((4, 37, 18, 19), (5, 61, 24, 37), (6, 91, 30, 61)):
        cells = _all_cells(n)
        check(len(cells) == tot, f"hexhex-{n}: {tot} cells, got {len(cells)}")
        check(len(_perim(n)) == per, f"hexhex-{n}: {per} perimeter cells")
        check(len(_gray(n)) == gry, f"hexhex-{n}: {gry} gray cells")
        check(len(_perim(n)) + len(_gray(n)) == tot, "perim + gray == all")
        check(not (_perim(n) & _gray(n)), "perim and gray disjoint")
        # perimeter == radius n-1; gray == radius <= n-2
        check(all(_radius(*c) == n - 1 for c in _perim(n)), "perim on radius n-1")
        check(all(_radius(*c) <= n - 2 for c in _gray(n)), "gray inside")
        # antipodal pairing maps rim -> rim, is an involution, 3(n-1) pairs
        prs = _pairs(n)
        check(len(prs) == 3 * (n - 1), f"hexhex-{n}: {3*(n-1)} pairs")
        covered = set()
        for lo, hi in prs:
            check(lo in _perim(n) and hi in _perim(n), "pair members on rim")
            check(_antipode(lo) == hi and _antipode(hi) == lo, "180-deg involution")
            check(_radius(*lo) == _radius(*hi) == n - 1, "antipode preserves radius")
            covered.add(lo)
            covered.add(hi)
        check(covered == _perim(n), "pairs cover every rim cell exactly once")
        # corners map to the opposite corner (both are perimeter corners)
        corners = {(u * (n - 1), v * (n - 1)) for (u, v) in
                   [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]}
        check(corners <= _perim(n), "corners are perimeter cells")
        for c in corners:
            check(_antipode(c) in corners, "corner antipode is a corner")
        # each rim pair shares a render hue; distinct pairs differ
        hue = _pair_hue(n)
        for lo, hi in prs:
            check(abs(hue[lo] - hue[hi]) < 1e-6, "antipodes share a hue")
        pair_hues = [round(hue[lo], 4) for lo, hi in prs]
        check(len(set(pair_hues)) == len(prs), "distinct pairs have distinct hues")
    print("geometry OK")


def test_opening_protocol():
    g = Iris()
    s = g.initial_state({"size": "5"})
    check(g.current_player(s) == BLACK, "black opens")
    moves = g.legal_moves(s)
    placements = [m for m in moves if m != "pass"]
    # opening = single gray stones only, no pairs, no coloured cells
    check(all(">" not in m for m in placements), "opening moves are singles")
    check({_cell(m) for m in placements} == set(_gray(s.n)),
          "opening offers exactly the empty gray cells")
    check(all(_cell(m) not in _perim(s.n) for m in placements),
          "opening never a coloured cell")
    # a coloured opening is rejected
    rim = next(iter(_perim(s.n)))
    try:
        g.apply_move(s, _fmt(rim))
        raise AssertionError("coloured opening should be illegal")
    except ValueError:
        pass
    # play the opening single; now White is in two-stone mode
    s = g.apply_move(s, "0,0")
    check(s.ply == 1 and s.to_move == WHITE and s.board == {(0, 0): BLACK},
          "opening placed one black gray stone")
    print("opening protocol OK")


def test_coloured_pair_forced():
    g = Iris()
    s = g.initial_state({"size": "5"})
    s = g.apply_move(s, "0,0")  # black opening
    n = s.n
    prs = _pairs(n)
    lo, hi = prs[0]
    # legal_moves contains exactly the atomic pair for that rim colour
    moves = set(g.legal_moves(s))
    check(f"{_fmt(lo)}>{_fmt(hi)}" in moves, "coloured antipodal pair offered")
    # a lone coloured stone (no antipode) is NOT a legal single
    check(_fmt(lo) not in moves, "coloured cell not offered as a single")
    # apply the pair -> both cells owned by White
    s2 = g.apply_move(s, f"{_fmt(lo)}>{_fmt(hi)}")
    check(s2.board[lo] == WHITE and s2.board[hi] == WHITE, "pair placed")
    # a coloured-first move to a WRONG (non-antipode) second is illegal
    other = next((c for c in _perim(n) if c not in (lo, hi, _antipode(lo))), None)
    try:
        g.apply_move(s, f"{_fmt(lo)}>{_fmt(other)}")
        raise AssertionError("wrong second stone must be illegal")
    except ValueError:
        pass
    # if the antipode is occupied, the pair is not offered at all
    s3 = IrisState(n=n, board={hi: BLACK}, to_move=WHITE, ply=2)
    check(f"{_fmt(lo)}>{_fmt(hi)}" not in set(g.legal_moves(s3)),
          "blocked antipode removes the pair")
    print("coloured pair OK")


def test_gray_pair_and_forfeit():
    g = Iris()
    n = 5
    # a gray first stone forbids an ADJACENT gray second
    a = (0, 0)
    nb = (a[0] + _DIRS[0][0], a[1] + _DIRS[0][1])  # a neighbour of the centre
    check(nb in _gray(n) and _adjacent(a, nb), "picked an adjacent gray pair")
    s = IrisState(n=n, to_move=WHITE, ply=2)  # generic two-stone turn
    moves = set(g.legal_moves(s))
    check(f"{_fmt(a)}>{_fmt(nb)}" not in moves, "adjacent gray pair illegal")
    try:
        g.apply_move(s, f"{_fmt(a)}>{_fmt(nb)}")
        raise AssertionError("adjacent gray second must be rejected")
    except ValueError:
        pass
    # a NON-adjacent gray pair is fine
    far = next(c for c in _gray(n) if not _adjacent(a, c) and c != a)
    lo, hi = min(a, far), max(a, far)
    check(f"{_fmt(lo)}>{_fmt(hi)}" in moves, "non-adjacent gray pair legal")
    s2 = g.apply_move(s, f"{_fmt(lo)}>{_fmt(hi)}")
    check(s2.board[a] == WHITE and s2.board[far] == WHITE, "gray pair placed")

    # Forfeit: build a board where the ONLY empty gray cell is the centre, so
    # its "first stone" has no non-adjacent partner -> a legal single stone.
    board = {c: BLACK for c in _gray(n) if c != (0, 0)}
    s3 = IrisState(n=n, board=dict(board), to_move=WHITE, ply=8)
    ms = set(g.legal_moves(s3))
    check("0,0" in ms, "sole empty gray offered as a forfeit single")
    check(not any(m.startswith("0,0>") for m in ms), "no gray pair possible")
    s4 = g.apply_move(s3, "0,0")
    check(s4.board[(0, 0)] == WHITE, "forfeit single placed")

    # Forfeit is ILLEGAL when a legal non-adjacent gray still exists.
    s5 = IrisState(n=n, to_move=WHITE, ply=2)
    try:
        g.apply_move(s5, "0,0")  # single, but many non-adjacent grays remain
        raise AssertionError("forfeit not allowed while a legal second exists")
    except ValueError:
        pass
    print("gray pair / forfeit OK")


def test_scoring_and_tiebreak():
    n = 5
    perim = _perim(n)
    # Grab one antipodal rim pair + a connecting interior chain between them.
    lo, hi = _pairs(n)[0]
    # Black owns the two rim cells joined by a straight interior line so they are
    # one group scoring 2 coloured cells.
    def line(a, b):
        cur, path = a, [a]
        # walk one hex step at a time toward b along a shared axis if collinear
        while cur != b:
            step = min(_DIRS, key=lambda d: _radius(cur[0] + d[0] - b[0],
                                                     cur[1] + d[1] - b[1]))
            cur = (cur[0] + step[0], cur[1] + step[1])
            path.append(cur)
        return path

    path = line(lo, hi)
    board = {c: BLACK for c in path}
    # both rim cells are in the path's single group
    bl = _score_list(board, BLACK, n)
    check(bl and bl[0] == 2, f"connected rim pair scores 2, got {bl}")
    big = max(_groups(board, BLACK, n), key=len)
    check(lo in big and hi in big, "both rim cells in one group")
    # White (no stones) scores nothing
    check(_score_list(board, WHITE, n) == [], "empty player scores nothing")
    # an interior-only stone scores 0 (dropped)
    check(_score_list({(0, 0): WHITE}, WHITE, n) == [], "interior-only == 0")

    # Recursive tiebreak semantics
    check(_compare([6, 3], [6, 2]) == 1, "second-best breaks the tie")
    check(_compare([6, 2], [6, 3]) == -1, "symmetric")
    check(_compare([6, 3], [6, 3, 1]) == -1, "extra group beats missing (0)")
    check(_compare([6, 3, 0], [6, 3]) == 0, "trailing zero == missing")
    check(_compare([4], [4]) == 0, "full tie detected")
    check(_compare([5], [4, 4, 4]) == 1, "single best group wins outright")
    print("scoring / tiebreak OK")


def test_double_pass_draw():
    g = Iris()
    s = g.initial_state({"size": "5"})
    check("pass" in g.legal_moves(s), "pass legal")
    s = g.apply_move(s, "pass")
    check(not g.is_terminal(s), "single pass never ends the game")
    s = g.apply_move(s, "pass")
    check(g.is_terminal(s) and s.winner is None, "empty double pass is a draw")
    check(g.returns(s) == [0.0, 0.0], "draw returns")

    # A decisive result via apply_move: Black connects a rim pair, White passes.
    g = Iris()
    s = g.initial_state({"size": "5"})
    lo, hi = _pairs(s.n)[0]
    # opening on a gray cell adjacent to lo's inbound direction (any gray works)
    s = g.apply_move(s, "0,0")            # black opening (ply0)
    s = g.apply_move(s, "pass")           # white pass
    # black plays the coloured antipodal pair -> owns 2 coloured cells in a group
    s = g.apply_move(s, f"{_fmt(lo)}>{_fmt(hi)}")
    s = g.apply_move(s, "pass")           # white pass
    s = g.apply_move(s, "pass")           # black pass -> double pass ends
    check(g.is_terminal(s), "double pass ends the game")
    check(s.winner == BLACK, "black's coloured group beats white's nothing")
    check(g.returns(s) == [1.0, -1.0], "returns reflect black win")
    print("double-pass / draw OK")


def test_serialize_roundtrip():
    g = Iris()
    s = g.initial_state({"size": "6"})
    s = g.apply_move(s, "0,0")
    lo, hi = _pairs(s.n)[0]
    s = g.apply_move(s, f"{_fmt(lo)}>{_fmt(hi)}")
    s = g.apply_move(s, "pass")
    d = g.serialize(s)
    s2 = g.deserialize(d)
    check(g.serialize(s2) == d, "serialize round-trip stable")
    check(s2.board == s.board and s2.n == s.n and s2.passes == s.passes
          and s2.last == s.last, "state preserved")
    print("serialize OK")


def test_random_playouts_terminate():
    g = Iris()
    rng = random.Random(20260706)
    for n in (4, 5, 6):
        for _ in range(3 if n < 6 else 2):
            s = g.initial_state({"size": str(n)})
            cap = 3 * len(_all_cells(n)) + 8
            plies = 0
            while not g.is_terminal(s):
                moves = g.legal_moves(s)
                check(moves, "non-terminal state must have moves")
                s = g.apply_move(s, rng.choice(moves))
                plies += 1
                check(plies <= cap, f"hexhex-{n} playout exceeded {cap} plies")
            check(s.winner in (BLACK, WHITE, None), "terminal result set")
            want = ([0.0, 0.0] if s.winner is None else
                    [1.0, -1.0] if s.winner == BLACK else [-1.0, 1.0])
            check(g.returns(s) == want, "returns match winner")
    print("random playouts OK")


def test_render_probe():
    g = Iris()
    for n in (4, 5, 6):
        s = g.initial_state({"size": str(n)})
        s = g.apply_move(s, "0,0")
        spec = g.render(s)
        board = spec["board"]
        check(board["type"] == "polygons", "polygons board")
        cells = board["cells"]
        check(isinstance(cells, list), "cells must be a LIST")
        check(all(isinstance(c, dict) and "id" in c and "points" in c
                  for c in cells), "cells are {id, points} dicts")
        ids = {c["id"] for c in cells}
        check(len(ids) == len(cells) == len(_all_cells(n)), "all cells rendered")
        # every legal placement cell has a rendered tile
        lm = g.legal_moves(s)
        cs = set()
        for m in lm:
            if m == "pass":
                continue
            cs |= set(m.split(">"))
        check(cs <= ids, "every legal move cell is rendered")
        # tints well-formed: every cell tinted, perimeter tints are hex colours
        tints = board["tints"]
        check(set(tints) == ids, "every cell has a tint")
        for c in _perim(n):
            t = tints[_fmt(c)]
            check(isinstance(t, str) and t.startswith("#") and len(t) == 7,
                  f"rim tint must be #rrggbb, got {t!r}")
        # antipodal rim cells share a tint
        for lo, hi in _pairs(n):
            check(tints[_fmt(lo)] == tints[_fmt(hi)], "antipodes share a tint")
        check(all(p["owner"] in (0, 1) for p in spec["pieces"]), "owners 0/1")
        h = g.heuristic(s)
        check(len(h) == 2 and abs(h[0] + h[1]) < 1e-9, "heuristic zero-sum")
    print("render probe OK")


def main():
    test_geometry()
    test_opening_protocol()
    test_coloured_pair_forced()
    test_gray_pair_and_forfeit()
    test_scoring_and_tiebreak()
    test_double_pass_draw()
    test_serialize_roundtrip()
    test_random_playouts_terminate()
    test_render_probe()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
