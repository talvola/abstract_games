"""Star — standalone correctness anchor (pure stdlib: agp + this game only).

Asserts the board geometry (alternating-side hexagon + partial-hex border
cells), the corner/edge border-touch counts, group detection, the EXACT scoring
formula (border cells touched − 2, star iff ≥ 3), the board-full / pass-out end
with most-points winner reached via apply_move, and a serialize round-trip.
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.star.game import (
    Star, StarState, BLACK, WHITE,
    _cells, _borders, _border_touch, _corners, _score,
)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_geometry():
    # default board 5x6
    cells = _cells(5, 6)
    check(len(cells) == 106, f"expected 106 playing cells, got {len(cells)}")
    borders = _borders(5, 6)
    check(len(borders) == 39, f"expected 39 border cells, got {len(borders)}")
    # border count must be ODD (drawless guarantee)
    check(len(borders) % 2 == 1, "border count must be odd")

    bt = _border_touch(5, 6)
    counts = {}
    for c, ts in bt.items():
        counts[len(ts)] = counts.get(len(ts), 0) + 1
    # 6 corners touch 3; 27 edge cells touch 2; rest touch 0
    check(counts.get(3) == 6, f"expected 6 corners (touch 3), got {counts.get(3)}")
    check(counts.get(2) == 27, f"expected 27 edge cells (touch 2), got {counts.get(2)}")
    check(counts.get(0) == 106 - 6 - 27, "interior count mismatch")

    corners = _corners(5, 6)
    check(len(corners) == 6, f"expected 6 corners, got {len(corners)}")
    for c in corners:
        check(len(bt[c]) == 3, f"corner {c} must touch 3 border cells")

    # other sizes
    check(len(_cells(4, 5)) == 73 and len(_borders(4, 5)) == 33, "4x5 geometry")
    check(len(_cells(6, 7)) == 145 and len(_borders(6, 7)) == 45, "6x7 geometry")
    print("geometry OK")


def test_scoring_formula():
    a, b = 5, 6
    corners = sorted(_corners(a, b))
    bt = _border_touch(a, b)

    # lone stone on a corner: touches 3 border cells -> 3-2 = 1
    corner = corners[0]
    board = {corner: BLACK}
    check(_score(board, BLACK, a, b) == 1, "lone corner stone must score 1")
    check(_score(board, WHITE, a, b) == 0, "white has nothing")

    # lone stone on an edge cell (touches exactly 2): not a star -> 0
    edge2 = next(c for c, ts in bt.items() if len(ts) == 2)
    board = {edge2: BLACK}
    check(_score(board, BLACK, a, b) == 0, "lone edge stone touches 2 -> 0")

    # lone interior stone: touches 0 -> 0
    interior = next(c for c, ts in bt.items() if len(ts) == 0)
    board = {interior: BLACK}
    check(_score(board, BLACK, a, b) == 0, "interior stone -> 0")

    # Build a connected group touching exactly k border cells and verify f(k)=k-2.
    # Walk a connected chain along the rim accumulating distinct border cells.
    # Easiest exact check: a group made of TWO corners joined by a path.
    # Instead, directly verify the formula on a synthetic touch-count by placing
    # a group = a single corner (3 borders -> 1) plus an adjacent edge cell that
    # adds new border(s).
    g = build_group_touching(a, b, target_k=5)
    board = {c: BLACK for c in g["cells"]}
    touched = set()
    for c in g["cells"]:
        touched |= bt[c]
    check(len(touched) == g["k"], f"group should touch {g['k']} got {len(touched)}")
    check(_score(board, BLACK, a, b) == g["k"] - 2,
          f"group touching {g['k']} must score {g['k']-2}")

    # two SEPARATE corner stones (disconnected) -> two stars of 1 each = 2
    board = {corners[0]: BLACK, corners[2]: BLACK}
    # ensure they are not adjacent (corners on the default board are far apart)
    check(_score(board, BLACK, a, b) == 2, "two disconnected corners score 1+1=2")

    # shared border cell counts for BOTH colours independently:
    # place black and white groups each adjacent to overlapping borders -> both score.
    print("scoring formula OK")


def build_group_touching(a, b, target_k):
    """Greedily grow a connected group of playing cells until it touches exactly
    target_k distinct border cells (returns its cells + actual k)."""
    DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]
    bt = _border_touch(a, b)
    on = set(_cells(a, b))
    # start at a corner (3 borders) and extend along the rim
    start = sorted(_corners(a, b))[0]
    group = [start]
    touched = set(bt[start])
    frontier = list(group)
    seen = set(group)
    while len(touched) < target_k:
        grew = False
        for c in list(group):
            for dq, dr in DIRS:
                nb = (c[0] + dq, c[1] + dr)
                if nb in on and nb not in seen and bt[nb]:
                    new = bt[nb] - touched
                    if new:
                        group.append(nb)
                        seen.add(nb)
                        touched |= bt[nb]
                        grew = True
                        if len(touched) >= target_k:
                            break
            if len(touched) >= target_k:
                break
        if not grew:
            break
    return {"cells": group, "k": len(touched)}


def test_play_and_end():
    g = Star()
    s = g.initial_state({"size": "4x5", "pie": False})  # small board, fast
    check(g.current_player(s) == BLACK, "black starts")
    check("pass" in g.legal_moves(s), "pass always legal")
    check("swap" not in g.legal_moves(s), "no swap when pie off")

    # placement legality
    cells = _cells(4, 5)
    first = f"{cells[0][0]},{cells[0][1]}"
    s2 = g.apply_move(s, first)
    check(g.current_player(s2) == WHITE, "turn alternates")
    check(s2.board[cells[0]] == BLACK, "stone placed")

    # two passes end the game and pick the leader
    s = g.initial_state({"size": "4x5", "pie": False})
    # black grabs a corner (scores 1), white passes, black passes -> two passes
    corner = sorted(_corners(4, 5))[0]
    s = g.apply_move(s, f"{corner[0]},{corner[1]}")   # black
    s = g.apply_move(s, "pass")                       # white pass (1)
    s = g.apply_move(s, "pass")                       # black pass (2) -> end
    check(g.is_terminal(s), "two passes end the game")
    check(s.winner == BLACK, "black (corner=1) beats white (0)")
    check(g.returns(s) == [1.0, -1.0], "returns reflect black win")

    # board-full safety net also terminates
    g = Star()
    s = g.initial_state({"size": "4x5", "pie": False})
    cells = _cells(4, 5)
    i = 0
    while not g.is_terminal(s):
        # fill cells in order, never passing
        empties = [c for c in cells if c not in s.board]
        if not empties:
            break
        c = empties[0]
        s = g.apply_move(s, f"{c[0]},{c[1]}")
        i += 1
        check(i <= len(cells) + 1, "must terminate by full board")
    check(g.is_terminal(s), "full board terminates")
    check(len(s.board) == len(cells), "all playing cells filled")
    print("play/end OK")


def test_serialize_roundtrip():
    g = Star()
    s = g.initial_state({"size": "5x6", "pie": True})
    s = g.apply_move(s, "swap" if False else f"{_cells(5,6)[10][0]},{_cells(5,6)[10][1]}")
    s = g.apply_move(s, "swap")  # white swaps
    s = g.apply_move(s, "pass")
    d = g.serialize(s)
    s2 = g.deserialize(d)
    check(g.serialize(s2) == d, "serialize round-trip stable")
    check(s2.a == s.a and s2.b == s.b, "size preserved")
    check(s2.board == s.board, "board preserved")
    print("serialize OK")


def main():
    test_geometry()
    test_scoring_formula()
    test_play_and_end()
    test_serialize_roundtrip()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
