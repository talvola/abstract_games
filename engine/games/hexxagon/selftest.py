"""Standalone correctness anchor for Hexxagon.

Run with:  PYTHONPATH=. python3 games/hexxagon/selftest.py
Pure stdlib + the agp package only. Prints SELFTEST OK and exits 0 on success.
"""

from __future__ import annotations

import sys

from games.hexxagon.game import (
    Hexxagon, HexxagonState, STANDARD_HOLES, _all_cells, _hex_dist,
    _grow_targets, _jump_targets, _playable, P0_CORNERS, P1_CORNERS,
)


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def main():
    g = Hexxagon()

    # ---- geometry: 61-cell hexhex, 3 holes, 58 playable -----------------------
    if len(_all_cells()) != 61:
        fail(f"hexhex should have 61 cells, got {len(_all_cells())}")
    if len(STANDARD_HOLES) != 3:
        fail(f"should be exactly 3 holes, got {len(STANDARD_HOLES)}")
    if len(_playable(STANDARD_HOLES)) != 58:
        fail(f"should be 58 playable cells, got {len(_playable(STANDARD_HOLES))}")
    # holes are near-center (distance 1 from origin) and 3-fold symmetric
    for h in STANDARD_HOLES:
        if _hex_dist((0, 0), h) != 1:
            fail(f"hole {h} should be adjacent to center")
    if (0, 0) in STANDARD_HOLES:
        fail("center (0,0) must stay playable")

    # ---- starting position: 3 each on alternating corners, opposite enemies ---
    s0 = g.initial_state()
    if g.num_players != 2:
        fail("num_players must be 2")
    a, b = g._counts(s0)
    if (a, b) != (3, 3):
        fail(f"start counts should be 3-3, got {a},{b}")
    if g.current_player(s0) != 0:
        fail("Red (0) should move first")
    if set(c for c, p in s0.board.items() if p == 0) != set(P0_CORNERS):
        fail("P0 should hold its 3 corners")
    if set(c for c, p in s0.board.items() if p == 1) != set(P1_CORNERS):
        fail("P1 should hold its 3 corners")
    # every piece sits opposite an enemy (nearest enemy at max hex distance 4)
    for c in P0_CORNERS:
        if min(_hex_dist(c, e) for e in P1_CORNERS) != 4:
            fail(f"P0 corner {c} not opposite an enemy")
    # corners are non-adjacent within a side (no two same-colour corners adjacent)
    for c1 in P0_CORNERS:
        for c2 in P0_CORNERS:
            if c1 != c2 and _hex_dist(c1, c2) < 2:
                fail("two same-colour corners are adjacent")
    if g.is_terminal(s0):
        fail("start should not be terminal")
    # round-trip
    if g.serialize(g.deserialize(g.serialize(s0))) != g.serialize(s0):
        fail("serialize does not round-trip")

    playable = _playable(STANDARD_HOLES)

    # ---- (1) GROW: distance-1 has exactly 6 neighbours; clone keeps source ----
    # A single Red piece at center (0,0): 6 neighbours, but (1,0),(-1,1),(0,-1)
    # are holes -> only 3 grow targets available.
    grows = list(_grow_targets(0, 0, playable))
    if len(grows) != 3:
        fail(f"center grow targets (holes blocking) should be 3, got {len(grows)}")
    # at a hole-free spot, all 6 neighbours present ((-3,0) has all 6 playable)
    grows_full = list(_grow_targets(-3, 0, playable))
    if len(grows_full) != 6:
        fail(f"interior grow targets should be 6, got {len(grows_full)}")
    s = HexxagonState(board={(-3, 0): 0}, holes=STANDARD_HOLES, to_move=0, ply=0)
    if "-3,0>-2,0" not in set(g.legal_moves(s)):
        fail("grow move -3,0>-2,0 not offered")
    s2 = g.apply_move(s, "-3,0>-2,0")
    if s2.board.get((-3, 0)) != 0:
        fail("grow must KEEP the source piece")
    if s2.board.get((-2, 0)) != 0:
        fail("grow must place a NEW Red piece on the target")
    if len(s2.board) != 2 or g._counts(s2)[0] != 2:
        fail("grow should yield 2 Red pieces (1 -> 2)")

    # ---- (2) JUMP: distance-2 ring is 12 cells (interior); source vacated ------
    jumps_full = set(_jump_targets(0, 0, _playable(frozenset())))  # holeless
    if len(jumps_full) != 12:
        fail(f"distance-2 ring should be 12 cells, got {len(jumps_full)}")
    s = HexxagonState(board={(0, 0): 0}, holes=frozenset(), to_move=0, ply=0)
    if "0,0>2,0" not in set(g.legal_moves(s)):
        fail("jump move 0,0>2,0 (distance 2) not offered")
    s2 = g.apply_move(s, "0,0>2,0")
    if (0, 0) in s2.board:
        fail("jump must VACATE the source cell")
    if s2.board.get((2, 0)) != 0:
        fail("jump must place the piece on the target")
    if len(s2.board) != 1:
        fail(f"jump must not change piece count, got {len(s2.board)}")

    # ---- only distance 1 or 2 are ever offered --------------------------------
    s = HexxagonState(board={(0, 1): 0}, holes=STANDARD_HOLES, to_move=0, ply=0)
    for mv in g.legal_moves(s):
        sc, dc = mv.split(">")
        src = tuple(map(int, sc.split(",")))
        dst = tuple(map(int, dc.split(",")))
        if _hex_dist(src, dst) not in (1, 2):
            fail(f"illegal-distance move offered: {mv}")

    # ---- (3) infection: every adjacent enemy flips; non-adjacent does not -----
    # Red jumps into (0,0); surround it with 6 Blues (skip the 3 holes -> only 3
    # real neighbour cells are non-holes). Put Blues there and a Blue 2 away.
    # Neighbours of (0,0): (1,0),(-1,0),(0,1),(0,-1),(1,-1),(-1,1).
    # Holes are (1,0),(-1,1),(0,-1) -> real neighbours: (-1,0),(0,1),(1,-1).
    board = {
        (-1, 0): 1, (0, 1): 1, (1, -1): 1,   # 3 non-hole neighbours, all Blue
        (2, 0): 1,                            # 2 cells from (0,0): must NOT flip
        (2, -2): 0,                           # Red that jumps to (0,0) (dist 2)
    }
    s = HexxagonState(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    if _hex_dist((2, -2), (0, 0)) != 2:
        fail("test setup: (2,-2)->(0,0) should be a jump")
    s2 = g.apply_move(s, "2,-2>0,0")
    for nb in [(-1, 0), (0, 1), (1, -1)]:
        if s2.board.get(nb) != 0:
            fail(f"infection failed to flip adjacent enemy at {nb}")
    if s2.board.get((2, 0)) != 1:
        fail("infection wrongly flipped a NON-adjacent enemy at (2,0)")
    if s2.board.get((0, 0)) != 0:
        fail("destination should hold the moved Red piece")
    if g._counts(s2)[0] != 4:
        fail(f"infection multi-flip count wrong: Red={g._counts(s2)[0]}")

    # ---- holes are never a neighbour / target ---------------------------------
    for h in STANDARD_HOLES:
        if h in set(_grow_targets(0, 0, playable)):
            fail(f"hole {h} offered as a grow target")
        if h in set(_jump_targets(0, 0, playable)):
            fail(f"hole {h} offered as a jump target")
    # a Red at a cell adjacent to a hole must not be able to move onto it
    s = HexxagonState(board={(0, 0): 0}, holes=STANDARD_HOLES, to_move=0, ply=0)
    for mv in g.legal_moves(s):
        dst = tuple(map(int, mv.split(">")[1].split(",")))
        if dst in STANDARD_HOLES:
            fail(f"move onto a hole was offered: {mv}")
    # and a Blue sitting where a hole is can't be infected (holes excluded);
    # construct a Red landing adjacent to a (would-be) hole position is moot since
    # holes never hold a piece, so just assert infection respects `playable`.

    # ---- (4a) pass: a player with no move passes ------------------------------
    # Fill the whole playable board with Blue except trap one Red with no empty
    # neighbour and leave a couple of empties far away for Blue.
    board = {c: 1 for c in playable}
    board[(0, 0)] = 0  # one Red boxed in by Blue (its neighbours all occupied)
    # free two cells far from center so Blue still has a move
    del board[(4, 0)]
    del board[(3, 0)]
    s = HexxagonState(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    if g.is_terminal(s):
        fail("not terminal: Blue still has a move")
    if g.legal_moves(s) != ["pass"]:
        fail(f"Red boxed in should only have pass, got {g.legal_moves(s)}")
    s2 = g.apply_move(s, "pass")
    if g.current_player(s2) != 1:
        fail("after Red passes it should be Blue's move")
    if not g.legal_moves(s2) or g.legal_moves(s2) == ["pass"]:
        fail("Blue should have real moves after Red passes")

    # ---- (4b) most pieces wins / tie = draw -----------------------------------
    cells = list(playable)
    # 58 cells -> 30 Red, 28 Blue => Red win
    board = {c: (0 if i < 30 else 1) for i, c in enumerate(cells)}
    s = HexxagonState(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    if not g._board_full(s) or not g.is_terminal(s):
        fail("full board should be terminal")
    if g.returns(s) != [1.0, -1.0]:
        fail(f"30 vs 28 should be Red win, got {g.returns(s)}")
    if g.legal_moves(s) != []:
        fail("terminal state must have no legal moves")
    # tie: 29-29
    board = {c: (0 if i < 29 else 1) for i, c in enumerate(cells)}
    s = HexxagonState(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    if g._counts(s) != (29, 29):
        fail(f"tie setup wrong: {g._counts(s)}")
    if g.returns(s) != [0.0, 0.0]:
        fail(f"29-29 should be a draw, got {g.returns(s)}")

    # ---- (5) auto-fill-on-elimination: wiping the opponent fills the board -----
    # Red at (0,0) with Blue's ONLY piece adjacent at (0,1). Red grows into (1,-1)
    # which is adjacent to (0,1)? No — pick a landing that flips the lone Blue.
    # Red jumps onto a cell adjacent to the lone Blue, flipping it -> Blue wiped.
    board = {(0, 0): 0, (0, 1): 1}
    s = HexxagonState(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    # Red grows from (0,0) to (-1,0); is (-1,0) adjacent to (0,1)? neighbours of
    # (-1,0): (0,0),(-2,0),(-1,1)[hole],(-1,-1),(0,-1)[hole],(-2,1). Not (0,1).
    # Instead jump Red onto (1,1): neighbours of (1,1) include (0,1)? neighbours:
    # (2,1),(0,1),(1,2),(1,0)[hole],(2,0),(0,2). Yes (0,1) is adjacent.
    if _hex_dist((0, 0), (1, 1)) != 2:
        fail("test setup: (0,0)->(1,1) should be a jump")
    s2 = g.apply_move(s, "0,0>1,1")
    if any(p == 1 for p in s2.board.values()):
        fail("Blue should have been wiped out (flipped) by the landing")
    # auto-fill: every playable cell now Red, board full, Red wins
    if len(s2.board) != len(playable):
        fail(f"auto-fill should fill all {len(playable)} cells, got {len(s2.board)}")
    if not all(p == 0 for p in s2.board.values()):
        fail("auto-fill should make every cell Red")
    if not g.is_terminal(s2):
        fail("post-elimination full board should be terminal")
    if g.returns(s2) != [1.0, -1.0]:
        fail(f"elimination should be a Red win, got {g.returns(s2)}")

    # auto-fill guard: a synthetic one-colour position must NOT trigger fill.
    board = {(0, 0): 0}  # no Blue ever present
    s = HexxagonState(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    s2 = g.apply_move(s, "0,0>2,0")  # a normal jump
    if len(s2.board) != 1:
        fail("guard: one-colour position must not auto-fill")

    # ---- holes:"none" option works --------------------------------------------
    s = g.initial_state(options={"holes": "none"})
    if s.holes:
        fail("holes:none should have no holes")
    if len(_playable(s.holes)) != 61:
        fail("holes:none should have 61 playable cells")
    # center now has 6 grow targets
    if len(list(_grow_targets(0, 0, _playable(s.holes)))) != 6:
        fail("holes:none center should have 6 grow targets")

    # ---- (6) full random games terminate with consistent returns --------------
    import random
    rng = random.Random(0)
    for seed in range(20):
        rng.seed(seed)
        st = g.initial_state(options={"holes": "standard" if seed % 2 else "none"})
        steps = 0
        while not g.is_terminal(st) and steps < 5000:
            lm = g.legal_moves(st)
            if not lm:
                fail("non-terminal state returned no legal moves")
            st = g.apply_move(st, rng.choice(lm))
            steps += 1
        if not g.is_terminal(st):
            fail("game did not terminate within step budget")
        a, b = g._counts(st)
        cap = 61 if not st.holes else 58
        if a + b > cap or a < 0 or b < 0:
            fail(f"bad terminal counts {a},{b}")
        ret = g.returns(st)
        if (a > b and ret != [1.0, -1.0]) or (b > a and ret != [-1.0, 1.0]) \
                or (a == b and ret != [0.0, 0.0]):
            fail(f"returns disagree with counts: {a},{b} -> {ret}")
        # serialize round-trip on a real reached state
        if g.serialize(g.deserialize(g.serialize(st))) != g.serialize(st):
            fail("serialize round-trip failed on reached state")

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
