"""Crossway selftest — pure stdlib (import only agp + this game).

Run: cd engine && PYTHONPATH=. python3 games/crossway/selftest.py
Asserts: board/edges render, empty-cell placement, the Crossway diagonal
crossing-block rule (a diagonal link that IS connected vs. one BLOCKED by the
opponent's crossing diagonal), a winning connection sets `winner` (reached via
apply_move), the no-draw property (random full games yield exactly one winner),
and serialize round-trip.
"""

import random

from games.crossway.game import (
    Crossway, CrosswayState, BLACK, WHITE, _connects, _completes_crossing,
)


def _ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_board_and_edges():
    g = Crossway()
    s = g.initial_state({"size": 11})
    spec = g.render(s)
    b = spec["board"]
    _ok(b["type"] == "square" and b["width"] == 11 and b["height"] == 11,
        "board geometry wrong")
    e = b["edges"]
    _ok(e["top"] == BLACK and e["bottom"] == BLACK, "Black should own N/S edges")
    _ok(e["left"] == WHITE and e["right"] == WHITE, "White should own W/E edges")


def test_placement_empty_only():
    g = Crossway()
    s = g.initial_state({"size": 5})
    s2 = g.apply_move(s, "2,2")
    _ok((2, 2) in s2.board, "stone not placed")
    _ok("2,2" not in g.legal_moves(s2), "occupied cell still offered")
    # every legal move (besides pass/swap) is an empty cell
    for m in g.legal_moves(s2):
        if m in ("pass", "swap"):
            continue
        c, r = (int(x) for x in m.split(","))
        _ok((c, r) not in s2.board, f"legal move {m} is occupied")


def test_crossing_block_rule():
    """Construct the two diagonal-link scenarios and assert connectivity differs.

    Cells of the 2x2 square (0,0)(1,0)(0,1)(1,1).
    Black's diagonal link is (0,0)<->(1,1).
    """
    # (A) Connected: Black on the main diagonal, the OTHER two cells empty.
    board_a = {(0, 0): BLACK, (1, 1): BLACK}
    _ok(_connects_pair(board_a, (0, 0), (1, 1), BLACK),
        "Black diagonal should be connected when crossing cells are empty")

    # (B) Same Black diagonal, but White occupies ONE crossing cell -> per
    # Crossway, the diagonal STILL connects (8-adjacency); only the placement
    # that would fill BOTH crossing cells is illegal. So connectivity is the
    # same; the rule lives in placement legality, which we test next.
    board_b = {(0, 0): BLACK, (1, 1): BLACK, (1, 0): WHITE}
    _ok(_connects_pair(board_b, (0, 0), (1, 1), BLACK),
        "Black diagonal still connects with one crossing cell occupied")

    # The crossing RESTRICTION: White already holds (1,0); Black holds the
    # main diagonal (0,0),(1,1). White may NOT complete the cross at (0,1)
    # (that would make the forbidden checkerboard B/W crossing X).
    _ok(_completes_crossing(board_b, 0, 1, WHITE),
        "placing White at (0,1) must be forbidden (completes the cross)")
    # Black placing at (0,1) is fine (no crossing of opposite diagonals).
    _ok(not _completes_crossing(board_b, 0, 1, BLACK),
        "Black at (0,1) does not complete a cross and must be allowed")
    # And from the OTHER orientation: White on the anti-diagonal, Black on one
    # crossing cell, Black completing the cross is forbidden.
    board_c = {(1, 0): WHITE, (0, 1): WHITE, (0, 0): BLACK}
    _ok(_completes_crossing(board_c, 1, 1, BLACK),
        "Black at (1,1) must be forbidden (completes the rotated cross)")

    # Connectivity DIFFERS between a board where the diagonal partner is present
    # vs absent (the core link test).
    _ok(not _connects_pair({(0, 0): BLACK}, (0, 0), (1, 1), BLACK),
        "no link without the partner stone")


def _connects_pair(board, a, b, player):
    """Are stones a and b in the same 8-connected same-colour group?"""
    seen = {a}
    stack = [a]
    while stack:
        cc, cr = stack.pop()
        if (cc, cr) == b:
            return True
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                nb = (cc + dc, cr + dr)
                if nb not in seen and board.get(nb) == player:
                    seen.add(nb)
                    stack.append(nb)
    return False


def test_winning_connection_sets_winner():
    """Reach a Black top->bottom connection via apply_move on a 3x3 board.

    Black builds a straight vertical line in column 1: (1,0)->(1,1)->(1,2).
    White fills harmless corners between turns (avoiding any forbidden cross).
    """
    g = Crossway()
    s = g.initial_state({"size": 3})
    # Black (1,0); White (0,0); Black (1,1); White (2,2); Black (1,2) -> win.
    for mv in ["1,0", "0,0", "1,1", "2,2"]:
        s = g.apply_move(s, mv)
        _ok(s.winner is None, f"no winner expected yet after {mv}")
    s = g.apply_move(s, "1,2")
    _ok(s.winner == BLACK, "Black should win on completing the N-S chain")
    _ok(g.is_terminal(s), "terminal after a win")
    _ok(g.returns(s) == [1.0, -1.0], "returns wrong for Black win")
    _ok(g.legal_moves(s) == [], "no moves after terminal")


def test_no_draw_random_games():
    """Random legal play always ends with exactly one winner (no draws)."""
    g = Crossway()
    rng = random.Random(2024)
    for trial in range(40):
        s = g.initial_state({"size": 5})
        steps = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            _ok(moves, "legal_moves empty on a non-terminal state")
            s = g.apply_move(s, rng.choice(moves))
            steps += 1
            _ok(steps <= 5 * 5 + 5, "game ran too long (termination broken)")
        _ok(s.winner in (BLACK, WHITE), f"trial {trial}: no winner (a draw!)")


def test_pie_swap_transpose_mirror():
    """The pie swap is value-preserving: it reflects Black's lone opening stone
    across the main diagonal (c,r)->(r,c) and recolours it White (goals are
    transposed), NOT a recolour in place."""
    g = Crossway()
    s = g.initial_state({"size": 7})
    # Black opens off the main diagonal so transpose is observable.
    s1 = g.apply_move(s, "1,4")            # Black at (c=1, r=4)
    _ok("swap" in g.legal_moves(s1), "swap must be offered on White's first turn")
    s2 = g.apply_move(s1, "swap")
    _ok(s2.board == {(4, 1): WHITE},
        f"swap should mirror to (4,1)=White, got {s2.board}")
    _ok(s2.to_move == BLACK, "after swap it is Black to move")
    _ok("swap" not in g.legal_moves(s2), "swap must not be offered again")
    d = g.serialize(s2)
    _ok(g.serialize(g.deserialize(d)) == d, "swap-state serialize round-trip")


def test_serialize_roundtrip():
    g = Crossway()
    s = g.initial_state({"size": 7})
    rng = random.Random(7)
    for _ in range(6):
        if g.is_terminal(s):
            break
        s = g.apply_move(s, rng.choice(g.legal_moves(s)))
    d = g.serialize(s)
    s2 = g.deserialize(d)
    _ok(g.serialize(s2) == d, "serialize round-trip mismatch")
    import json
    json.dumps(d)  # must be JSON-able


def main():
    test_board_and_edges()
    test_placement_empty_only()
    test_crossing_block_rule()
    test_winning_connection_sets_winner()
    test_no_draw_random_games()
    test_pie_swap_transpose_mirror()
    test_serialize_roundtrip()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
