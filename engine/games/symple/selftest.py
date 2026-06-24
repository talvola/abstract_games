"""Pure-stdlib selftest for Symple. Asserts the board, new-group placement,
the grow-all-groups mechanic (incl. a merge), scoring = stones - P*groups, the
end condition, most-points win reached via apply_move, and serialize round-trip.

Run standalone:  PYTHONPATH=. python3 games/symple/selftest.py
"""

from games.symple.game import (
    Symple, SympleState, BLACK, WHITE, _groups, _new_group_cells,
)


def _st(board, **kw):
    return SympleState(size=kw.pop("size", 5), P=kw.pop("P", 4), board=dict(board), **kw)


def test_board_and_options():
    g = Symple()
    s = g.initial_state({"size": 19, "penalty": 8})
    assert s.size == 19 and s.P == 8
    # even size bumped to odd; odd P bumped to even
    s2 = g.initial_state({"size": 14, "penalty": 7})
    assert s2.size == 15 and s2.P == 8
    s3 = g.initial_state({"size": 13, "penalty": 4})
    assert s3.size == 13 and s3.P == 4
    assert g.num_players == 2


def test_new_group_placement():
    g = Symple()
    # 5x5, Black has a stone at (2,2). A new group must NOT touch it orthogonally.
    s = _st({(2, 2): BLACK}, to_move=BLACK)
    cells = set(_new_group_cells(s.board, BLACK, s.size))
    # orthogonal neighbours of (2,2) are forbidden
    for nb in [(1, 2), (3, 2), (2, 1), (2, 3)]:
        assert nb not in cells, nb
    # (2,2) itself occupied
    assert (2, 2) not in cells
    # a diagonal like (3,3) is allowed (only orthogonal adjacency forbidden)
    assert (3, 3) in cells
    # apply a placement and confirm a new size-1 group exists
    ns = g.apply_move(s, "0,0")
    assert ns.board[(0, 0)] == BLACK
    assert len(_groups(ns.board, BLACK, ns.size)) == 2  # (2,2) and (0,0)
    # placing on a forbidden (own-adjacent) cell is illegal
    try:
        g.apply_move(s, "3,2")
        assert False, "expected illegal placement"
    except ValueError:
        pass


def test_grow_all_groups():
    g = Symple()
    # Black has TWO separate single-stone groups, far apart on a 5x5.
    s = _st({(0, 0): BLACK, (4, 4): BLACK}, to_move=BLACK)
    grp = _groups(s.board, BLACK, s.size)
    assert len(grp) == 2
    # Enter grow-mode.
    assert "grow" in g.legal_moves(s)
    s1 = g.apply_move(s, "grow")
    assert s1.growing and s1.to_move == BLACK  # same player keeps moving
    # First growth: legal cells should be neighbours of the lowest group (0,0).
    moves1 = set(g.legal_moves(s1))
    assert moves1 == {"1,0", "0,1"}, moves1
    s2 = g.apply_move(s1, "1,0")  # grow group at (0,0)
    assert s2.growing and (1, 0) in s2.board
    # Second growth: now the OTHER group (4,4) must grow; (0,0) group already grew.
    moves2 = set(g.legal_moves(s2))
    assert moves2 == {"3,4", "4,3"}, moves2
    s3 = g.apply_move(s2, "3,4")
    # Now every group grew exactly once -> turn auto-ends, hand to White.
    assert not s3.growing
    assert s3.to_move == WHITE
    assert s3.grown_ever
    # Each original group gained exactly one stone.
    sizes = sorted(len(x) for x in _groups(s3.board, BLACK, s3.size))
    assert sizes == [2, 2], sizes
    # Stones total = 4 (2 original + 2 growth), groups = 2.
    assert sum(1 for v in s3.board.values() if v == BLACK) == 4


def test_grow_merge():
    g = Symple()
    # Two single stones one cell apart horizontally on row 0: (0,0) and (2,0).
    # The empty cell (1,0) is orthogonally adjacent to BOTH groups.
    s = _st({(0, 0): BLACK, (2, 0): BLACK}, to_move=BLACK)
    assert len(_groups(s.board, BLACK, s.size)) == 2
    s1 = g.apply_move(s, "grow")
    moves = set(g.legal_moves(s1))
    # (1,0) is a legal growth cell for the first (lowest) group and would merge.
    assert "1,0" in moves
    s2 = g.apply_move(s1, "1,0")
    # One stone bridged both groups -> both are "grown", they merge into one.
    # The turn should auto-end (no ungrown growable group remains).
    assert not s2.growing, "merge stone should grow both groups -> turn ends"
    assert s2.to_move == WHITE
    grp = _groups(s2.board, BLACK, s2.size)
    assert len(grp) == 1 and len(grp[0]) == 3, grp  # (0,0)(1,0)(2,0) one group of 3


def test_no_regrow_already_grown():
    g = Symple()
    # A single horizontal group of 3 at (0,0)(1,0)(2,0). Growing it once must
    # add exactly ONE stone, then the turn ends (only one group).
    s = _st({(0, 0): BLACK, (1, 0): BLACK, (2, 0): BLACK}, to_move=BLACK)
    assert len(_groups(s.board, BLACK, s.size)) == 1
    s1 = g.apply_move(s, "grow")
    # pick a growth cell
    cell = g.legal_moves(s1)[0]
    s2 = g.apply_move(s1, cell)
    # only one group -> after one growth the turn auto-ends
    assert not s2.growing and s2.to_move == WHITE
    assert sum(1 for v in s2.board.values() if v == BLACK) == 4  # grew by exactly 1


def test_balancing_rule():
    g = Symple()
    # Before any growth, it's White's (seat 1) turn with an existing White group.
    # White may use grow_place (grow all + place one new stone) in one turn.
    s = _st({(2, 2): WHITE}, to_move=WHITE, grown_ever=False)
    moves = g.legal_moves(s)
    assert "grow_place" in moves, moves
    s1 = g.apply_move(s, "grow_place")
    assert s1.growing and s1.balancing_place and s1.to_move == WHITE
    # grow the single group
    gcell = [m for m in g.legal_moves(s1) if m not in ("growdone",)][0]
    s2 = g.apply_move(s1, gcell)
    # No more groups to grow; now a NEW-group placement is owed (plus growdone).
    lm = g.legal_moves(s2)
    assert "growdone" in lm
    place_cells = set(_new_group_cells(s2.board, WHITE, s2.size))
    assert place_cells, "should have somewhere to place the balancing stone"
    chosen = f"{next(iter(sorted(place_cells)))[0]},{next(iter(sorted(place_cells)))[1]}"
    s3 = g.apply_move(s2, chosen)
    assert s3.to_move == BLACK and not s3.growing
    # White now has 3 stones: original + 1 growth + 1 new placement.
    assert sum(1 for v in s3.board.values() if v == WHITE) == 3
    # Once grown_ever is True, the balancing option is gone.
    s_after = _st({(2, 2): WHITE}, to_move=WHITE, grown_ever=True)
    assert "grow_place" not in g.legal_moves(s_after)


def test_scoring_formula_and_P():
    g = Symple()
    P = 6
    # Black: a group of 4 + a lone stone = 5 stones, 2 groups.
    # White: a group of 3 = 3 stones, 1 group.
    board = {
        (0, 0): BLACK, (1, 0): BLACK, (2, 0): BLACK, (3, 0): BLACK,  # group of 4
        (0, 4): BLACK,                                               # lone
        (4, 2): WHITE, (4, 3): WHITE, (4, 4): WHITE,                 # group of 3
    }
    s = _st(board, P=P)
    # score = stones - P * groups
    assert g.score(s.board, BLACK, s.size, P) == 5 - P * 2  # 5 - 12 = -7
    assert g.score(s.board, WHITE, s.size, P) == 3 - P * 1  # 3 - 6  = -3
    # White has the higher (less negative) score -> White wins.
    assert g._winner_by_score(s.board, s.size, P) == WHITE


def test_end_condition_and_win_via_apply():
    g = Symple()
    # 3x3 board, P=2. Fill all but one cell, then the last placement ends the game.
    # Layout chosen so Black ends with more points.
    # Black: a connected L of 5 (1 group). White: 3 stones in 1 group.
    # Pre-fill 8 of 9 cells; Black to place the final cell as a NEW group.
    board = {
        (0, 0): BLACK, (1, 0): BLACK, (2, 0): BLACK, (0, 1): BLACK,  # Black group
        (2, 1): WHITE, (1, 2): WHITE, (2, 2): WHITE,                 # White group (3)
        (0, 2): WHITE,                                               # extends White? (0,2)-(1,2) adj -> still 1 group of 4
    }
    # Empty cell is (1,1). It is orthogonally adjacent to Black (1,0),(0,1) and
    # White (2,1),(1,2) -> Black cannot place a NEW group there (touches own).
    # Instead test a clean fill: make (1,1) a Black GROWTH that completes the board.
    s = _st(board, size=3, P=2, to_move=BLACK)
    assert not g.is_terminal(s)
    # (1,1) touches Black -> growth target. Grow.
    s1 = g.apply_move(s, "grow")
    assert "1,1" in g.legal_moves(s1)
    s2 = g.apply_move(s1, "1,1")
    # Board now full -> terminal.
    assert g.is_terminal(s2), "board should be full"
    assert len(s2.board) == 9
    # Black: stones now 5, 1 group -> 5 - 2 = 3. White: 4 stones, 1 group -> 4-2=2.
    assert g.score(s2.board, BLACK, 3, 2) == 3
    assert g.score(s2.board, WHITE, 3, 2) == 2
    assert s2.winner == BLACK
    assert g.returns(s2) == [1.0, -1.0]


def test_serialize_round_trip():
    g = Symple()
    s = _st({(0, 0): BLACK, (2, 0): BLACK, (4, 4): WHITE}, size=5, P=8,
            to_move=WHITE, grown_ever=True, ply=3,
            growing=True, grown_cells=((1, 0),), balancing_place=False,
            last=((1, 0),))
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d
    # JSON-able
    import json
    json.dumps(d)


def run():
    test_board_and_options()
    test_new_group_placement()
    test_grow_all_groups()
    test_grow_merge()
    test_no_regrow_already_grown()
    test_balancing_rule()
    test_scoring_formula_and_P()
    test_end_condition_and_win_via_apply()
    test_serialize_round_trip()
    print("SELFTEST OK")


if __name__ == "__main__":
    run()
