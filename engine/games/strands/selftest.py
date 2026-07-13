"""Strands correctness anchors (pure-stdlib: agp + this game only).

Run: cd engine && PYTHONPATH=. python3 games/strands/selftest.py
Also exercised by tests/test_games.py::test_package_selftests.
"""

from __future__ import annotations

import random
from pathlib import Path

from agp.loader import load_from_dir

_man, G = load_from_dir(Path(__file__).resolve().parent)
mod = __import__("games.strands.game", fromlist=["*"])
_cells = mod._cells
_setup = mod._setup
_cid = mod._cid
compute_winner = mod.compute_winner


def anchor_layout():
    """The number layout matches AbstractPlay/igGameCenter's fixed boards."""
    from collections import Counter
    expected = {
        5: {"cells": 61, "counts": {1: 1, 2: 22, 3: 14, 4: 18, 6: 6}},
        6: {"cells": 91, "counts": {1: 1, 2: 36, 3: 24, 4: 24, 6: 6}},
        7: {"cells": 127, "counts": {1: 5, 2: 50, 3: 28, 4: 8, 5: 18, 6: 18}},
    }
    for size, exp in expected.items():
        setup = _setup(size)
        assert len(setup) == exp["cells"] == 3 * size * size - 3 * size + 1
        assert setup[(0, 0)] == 1, f"centre must be 1 (size {size})"
        counts = dict(Counter(setup.values()))
        assert counts == exp["counts"], (size, counts)
        # Six geometric corners are all "6".
        n = size - 1
        corners = [(n, 0), (-n, 0), (0, n), (0, -n), (n, -n), (-n, n)]
        assert all(setup[c] == 6 for c in corners), f"corners must be 6 (size {size})"
    print("  layout: 5/6/7 fixed boards match; centre=1, corners=6  OK")


def anchor_opening_must_be_a_two():
    s = G.initial_state({"size": 6})
    setup = _setup(6)
    moves = G.legal_moves(s)
    assert moves, "opening has moves"
    assert all(setup[mod._cell(m)] == 2 for m in moves), "opening only on 2s"
    assert len(moves) == 36, ("all 36 '2' cells openable", len(moves))
    # A non-2 opening is rejected.
    corner = _cid((5, 0))  # a "6" cell
    assert setup[(5, 0)] == 6
    try:
        G.apply_move(s, corner)
        raise AssertionError("opening on a 6 should be illegal")
    except ValueError:
        pass
    # A legal opening covers exactly one stone and passes to White.
    two = next(m for m in moves)
    s2 = G.apply_move(s, two)
    assert len(s2.board) == 1 and s2.to_move == 1 and not s2.turn_cells
    print("  opening: only '2' cells, covers exactly one, hands to White  OK")


def anchor_cover_up_to_x():
    """Cover up to X of number X; may cover fewer; can't exceed X or mix nums."""
    s = G.initial_state({"size": 6})
    setup = _setup(6)
    # Do the opening, then it's White's normal turn.
    s = G.apply_move(s, next(iter(G.legal_moves(s))))
    # Find three empty "3" cells and start covering them.
    threes = sorted(c for c in _cells(6) if setup[c] == 3 and c not in s.board)
    assert len(threes) >= 3
    s1 = G.apply_move(s, _cid(threes[0]))           # commit to "3", 1 placed
    assert s1.to_move == 1 and len(s1.turn_cells) == 1  # same player continues
    lm = G.legal_moves(s1)
    assert "done" in lm, "may stop early (up to X)"
    # Continuations are only higher-sorted empty "3" cells (same number).
    cont = [m for m in lm if m != "done"]
    assert all(setup[mod._cell(m)] == 3 and mod._cell(m) > threes[0] for m in cont)
    assert threes[1] and _cid(threes[1]) in cont

    # Cover a 2nd and 3rd "3": after the 3rd the turn auto-ends (X reached).
    s2 = G.apply_move(s1, _cid(threes[1]))
    assert s2.to_move == 1 and len(s2.turn_cells) == 2
    s3 = G.apply_move(s2, _cid(threes[2]))
    assert s3.to_move == 0 and not s3.turn_cells, "3rd '3' ends the turn (max X)"
    assert set(s3.last) == {threes[0], threes[1], threes[2]}

    # "Cover fewer": start a fresh "3" turn, place one, then 'done'.
    empt = sorted(c for c in _cells(6) if setup[c] == 3 and c not in s3.board)
    t = G.apply_move(s3, _cid(empt[0]))
    t = G.apply_move(t, "done")
    assert t.to_move == 1 and t.last == [empt[0]], "covering a single '3' is legal"

    # Can't mix numbers: a "2" cell is never a continuation of a "3" turn.
    u = G.apply_move(t, _cid(sorted(c for c in _cells(6)
                                    if setup[c] == 3 and c not in t.board)[0]))
    a_two = _cid(next(c for c in _cells(6) if setup[c] == 2 and c not in u.board))
    try:
        G.apply_move(u, a_two)
        raise AssertionError("mixing a '2' into a '3' turn must fail")
    except ValueError:
        pass
    print("  placement: up to X, may cover fewer, can't exceed X or mix nums  OK")


def anchor_scoring_and_draw():
    """Largest-group comparison, including an honest identical-lists draw."""
    # Two connected triangles of equal size => draw (winner None).
    p0 = {(0, 0): 0, (1, 0): 0, (0, 1): 0}      # size-3 group for seat 0
    p1 = {(-1, 0): 1, (-2, 0): 1, (-1, -1): 1}  # size-3 group for seat 1
    draw_board = {**p0, **p1}
    assert compute_winner(draw_board, 6) is None, "identical group lists = draw"
    # Seat 0's group is larger => seat 0 wins.
    win_board = {**p0, (-1, 0): 1, (-2, 0): 1}   # seat 1 only has size-2
    assert compute_winner(win_board, 6) == 0
    # More-groups-of-that-size tie-break: 0 has [2,2], 1 has [2].
    tb = {(0, 0): 0, (1, 0): 0, (3, 0): 0, (4, 0): 0, (-1, 0): 1, (-2, 0): 1}
    assert compute_winner(tb, 6) == 0, "more groups of the top size wins"
    # returns() matches the winner.
    st = G.deserialize({"size": 6, "board": {_cid(c): o for c, o in win_board.items()},
                        "to_move": 0, "turn_cells": [], "last": [],
                        "winner": 0, "over": True})
    assert G.returns(st) == [1.0, -1.0]
    print("  scoring: largest-group chain + honest identical-lists draw  OK")


def anchor_board_fills_and_render():
    """A full game reaches a terminal full board; render carries number labels."""
    # Render probe on the initial (empty) board: every cell is a neutral
    # labelled disc (number, no owner); nothing is owned yet.
    s0 = G.initial_state({"size": 5})
    spec = G.render(s0)
    setup5 = _setup(5)
    assert spec["board"] == {"type": "hex", "shape": "hexagon", "size": 5}
    assert len(spec["pieces"]) == len(_cells(5))
    for p in spec["pieces"]:
        assert "owner" not in p, "empty cell must be owner-less"
        assert p["label"] == str(setup5[mod._cell(p["cell"])]), "label = number"
    # Cover the centre-adjacent region via one opening move; that cell becomes
    # an owned piece with no number label.
    two = next(m for m in G.legal_moves(s0))
    s1 = G.apply_move(s0, two)
    covered = next(p for p in G.render(s1)["pieces"] if p["cell"] == two)
    assert covered.get("owner") in (0, 1) and "label" not in covered, \
        "covered cell = owned stone, no number"

    # Deterministic self-play to a full board (always fills; no captures).
    rng = random.Random(7)
    s = G.initial_state({"size": 5})
    plies = 0
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        plies += 1
        assert plies < 5000, "must terminate"
    assert len(s.board) == len(_cells(5)), "board is full at game end"
    r = G.returns(s)
    assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)
    # Serialize round-trip on the terminal state.
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)
    print(f"  termination: full board reached ({plies} plies), render probe OK")


if __name__ == "__main__":
    anchor_layout()
    anchor_opening_must_be_a_two()
    anchor_cover_up_to_x()
    anchor_scoring_and_draw()
    anchor_board_fills_and_render()
    print("strands: all selftests passed")
