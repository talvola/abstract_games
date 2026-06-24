"""Standalone correctness anchor for Hexxagon (3-player).

Run with:  PYTHONPATH=. python3 games/hexxagon3/selftest.py
Pure stdlib + the agp package only. Prints SELFTEST OK and exits 0 on success.
"""

from __future__ import annotations

import sys

from games.hexxagon3.game import (
    Hexxagon3, Hexxagon3State, STANDARD_HOLES, _all_cells, _hex_dist,
    _grow_targets, _jump_targets, _playable, CORNERS_CYCLIC, CORNER_OWNER,
    PLAYER_CORNERS, NUM_PLAYERS,
)


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def main():
    g = Hexxagon3()

    # ---- num_players -----------------------------------------------------------
    if g.num_players != 3:
        fail(f"num_players must be 3, got {g.num_players}")

    # ---- geometry: 61-cell hexhex, 3 holes, 58 playable -----------------------
    if len(_all_cells()) != 61:
        fail(f"hexhex should have 61 cells, got {len(_all_cells())}")
    if len(STANDARD_HOLES) != 3:
        fail(f"should be exactly 3 holes, got {len(STANDARD_HOLES)}")
    if len(_playable(STANDARD_HOLES)) != 58:
        fail(f"should be 58 playable cells, got {len(_playable(STANDARD_HOLES))}")
    for h in STANDARD_HOLES:
        if _hex_dist((0, 0), h) != 1:
            fail(f"hole {h} should be adjacent to center")
    if (0, 0) in STANDARD_HOLES:
        fail("center (0,0) must stay playable")

    # ---- starting position: 6 corners owned P0,P1,P2,P0,P1,P2 -----------------
    if len(CORNERS_CYCLIC) != 6:
        fail("should be 6 corners")
    expected = [0, 1, 2, 0, 1, 2]
    got = [CORNER_OWNER[c] for c in CORNERS_CYCLIC]
    if got != expected:
        fail(f"corner owners should be {expected}, got {got}")
    # each player holds exactly 2 corners
    for p in range(NUM_PLAYERS):
        if len(PLAYER_CORNERS[p]) != 2:
            fail(f"player {p} should own 2 corners, got {PLAYER_CORNERS[p]}")
        # the two corners are opposite (max hex distance apart on the hexhex)
        c1, c2 = PLAYER_CORNERS[p]
        if _hex_dist(c1, c2) != 2 * (5 - 1):
            fail(f"player {p}'s corners should be opposite (dist 8), "
                 f"got {_hex_dist(c1, c2)}")
    # adjacent corners (cyclically) always differ in owner
    for i in range(6):
        a = CORNERS_CYCLIC[i]
        b = CORNERS_CYCLIC[(i + 1) % 6]
        if CORNER_OWNER[a] == CORNER_OWNER[b]:
            fail(f"cyclically-adjacent corners {a},{b} share an owner")

    s0 = g.initial_state()
    c0 = g._counts(s0)
    if c0 != [2, 2, 2]:
        fail(f"start counts should be 2-2-2, got {c0}")
    if len(s0.board) != 6:
        fail(f"start should have 6 pieces, got {len(s0.board)}")
    if g.current_player(s0) != 0:
        fail("P0 should move first")
    for p in range(NUM_PLAYERS):
        if set(c for c, q in s0.board.items() if q == p) != set(PLAYER_CORNERS[p]):
            fail(f"player {p} should hold its 2 corners at start")
    if g.is_terminal(s0):
        fail("start should not be terminal")
    if g.serialize(g.deserialize(g.serialize(s0))) != g.serialize(s0):
        fail("serialize does not round-trip at start")
    r0 = g.returns(s0)
    if len(r0) != 3 or any(not isinstance(x, float) for x in r0):
        fail(f"returns must be a length-3 float vector, got {r0}")

    playable = _playable(STANDARD_HOLES)

    # ---- GROW: distance-1 = 6 neighbours; clone keeps source -------------------
    grows_full = list(_grow_targets(-3, 0, playable))
    if len(grows_full) != 6:
        fail(f"interior grow targets should be 6, got {len(grows_full)}")
    s = Hexxagon3State(board={(-3, 0): 0}, holes=STANDARD_HOLES, to_move=0, ply=0)
    s2 = g.apply_move(s, "-3,0>-2,0")
    if s2.board.get((-3, 0)) != 0 or s2.board.get((-2, 0)) != 0:
        fail("grow must KEEP source and place a new piece")

    # ---- JUMP: distance-2 ring = 12; source vacated ----------------------------
    jumps_full = set(_jump_targets(0, 0, _playable(frozenset())))
    if len(jumps_full) != 12:
        fail(f"distance-2 ring should be 12 cells, got {len(jumps_full)}")
    s = Hexxagon3State(board={(0, 0): 0}, holes=frozenset(), to_move=0, ply=0)
    s2 = g.apply_move(s, "0,0>2,0")
    if (0, 0) in s2.board or s2.board.get((2, 0)) != 0 or len(s2.board) != 1:
        fail("jump must vacate source, place piece, keep count")

    # ---- 3-PLAYER INFECTION: a landing flips BOTH opponents' adjacent pieces ---
    # P0 jumps into (0,0). Real (non-hole) neighbours of (0,0) are
    # (-1,0),(0,1),(1,-1).  Put a P1 and a P2 piece among them -> BOTH flip to P0.
    board = {
        (-1, 0): 1,   # Blue (P1) adjacent
        (0, 1): 2,    # Green (P2) adjacent
        (1, -1): 1,   # another Blue adjacent
        (2, 0): 2,    # Green two cells away: must NOT flip
        (2, -2): 0,   # P0 piece that jumps to (0,0) (dist 2)
    }
    s = Hexxagon3State(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    if _hex_dist((2, -2), (0, 0)) != 2:
        fail("test setup: (2,-2)->(0,0) should be a jump")
    s2 = g.apply_move(s, "2,-2>0,0")
    for nb in [(-1, 0), (0, 1), (1, -1)]:
        if s2.board.get(nb) != 0:
            fail(f"3-player infection failed to flip adjacent enemy at {nb}")
    if s2.board.get((2, 0)) != 2:
        fail("infection wrongly flipped a NON-adjacent enemy at (2,0)")
    if s2.board.get((0, 0)) != 0:
        fail("destination should hold the moved P0 piece")
    # P0 had 1, now 1 (landed) + 3 flipped = 4; P1 had 2->0; P2 had 2->1
    cc = g._counts(s2)
    if cc[0] != 4 or cc[1] != 0 or cc[2] != 1:
        fail(f"3-player infection counts wrong: {cc}")

    # ---- holes never a neighbour / target --------------------------------------
    for h in STANDARD_HOLES:
        if h in set(_grow_targets(0, 0, playable)):
            fail(f"hole {h} offered as a grow target")
        if h in set(_jump_targets(0, 0, playable)):
            fail(f"hole {h} offered as a jump target")

    # ---- turn order SKIPS an eliminated player ---------------------------------
    # Construct: P0 to move; P1 has NO pieces (eliminated). After P0 moves,
    # current_player must skip P1 and become P2.
    board = {(-4, 4): 0, (4, 0): 2, (-4, 0): 2}  # no P1 anywhere
    s = Hexxagon3State(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    if g._has_pieces(s.board, 1):
        fail("test setup: P1 should be eliminated")
    # P0 makes a simple grow far from any P2 (no infection of P2)
    mv = None
    for m in g.legal_moves(s):
        dst = tuple(map(int, m.split(">")[1].split(",")))
        # avoid landing adjacent to a P2 piece (keep both P2 alive so not a survivor case)
        adj_p2 = any((dst[0] + dq, dst[1] + dr) in {(4, 0), (-4, 0)}
                     for dq, dr in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)])
        if not adj_p2:
            mv = m
            break
    if mv is None:
        fail("could not find a P0 move that doesn't touch P2")
    s2 = g.apply_move(s, mv)
    if g._has_pieces(s2.board, 2) and g._has_pieces(s2.board, 0):
        if g.current_player(s2) != 2:
            fail(f"turn order should skip eliminated P1 -> P2, "
                 f"got {g.current_player(s2)}")

    # ---- LAST-SURVIVOR auto-fill + win -----------------------------------------
    # P0 jumps onto (0,0) flipping the lone P1 at (-1,0) and lone P2 at (0,1):
    # both opponents wiped in one move -> P0 auto-fills and wins.
    board = {(2, -2): 0, (-1, 0): 1, (0, 1): 2}
    s = Hexxagon3State(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    before_alive = sum(1 for p in range(3) if g._has_pieces(s.board, p))
    if before_alive != 3:
        fail("test setup: all three players should be alive before the move")
    s2 = g.apply_move(s, "2,-2>0,0")
    if g._has_pieces(s2.board, 1) or g._has_pieces(s2.board, 2):
        fail("both opponents should be wiped out by the landing")
    if len(s2.board) != len(playable):
        fail(f"auto-fill should fill all {len(playable)} cells, "
             f"got {len(s2.board)}")
    if not all(p == 0 for p in s2.board.values()):
        fail("auto-fill should make every cell P0")
    if not g.is_terminal(s2):
        fail("post-survivor full board should be terminal")
    ret = g.returns(s2)
    if len(ret) != 3:
        fail("returns must be length 3")
    if ret[0] != max(ret) or ret != [1.0, -1.0, -1.0]:
        fail(f"last survivor P0 should have the highest payoff, got {ret}")

    # auto-fill guard: a synthetic single-colour position must NOT auto-fill.
    board = {(0, 0): 0}  # only P0 ever present
    s = Hexxagon3State(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    s2 = g.apply_move(s, "0,0>2,0")  # a normal jump
    if len(s2.board) != 1:
        fail("guard: single-colour position must not auto-fill")

    # ---- MOST-PIECES winner at a full board ------------------------------------
    cells = list(playable)  # 58 cells
    # 20 P0, 19 P1, 19 P2 -> P0 sole leader
    def colour(i):
        return 0 if i < 20 else (1 if i < 39 else 2)
    board = {c: colour(i) for i, c in enumerate(cells)}
    s = Hexxagon3State(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    if not g._board_full(s) or not g.is_terminal(s):
        fail("full board should be terminal")
    cnt = g._counts(s)
    if cnt != [20, 19, 19]:
        fail(f"full-board count setup wrong: {cnt}")
    if g.returns(s) != [1.0, -1.0, -1.0]:
        fail(f"20-19-19 should be a P0 win, got {g.returns(s)}")
    if g.legal_moves(s) != []:
        fail("terminal full board must have no legal moves")
    # tie for the lead -> draw (all 0)
    def colour2(i):
        return 0 if i < 20 else (1 if i < 40 else 2)  # 20-20-18
    board = {c: colour2(i) for i, c in enumerate(cells)}
    s = Hexxagon3State(board=board, holes=STANDARD_HOLES, to_move=0, ply=0)
    if g._counts(s) != [20, 20, 18]:
        fail(f"tie setup wrong: {g._counts(s)}")
    if g.returns(s) != [0.0, 0.0, 0.0]:
        fail(f"20-20-18 tie for lead should be a draw, got {g.returns(s)}")

    # ---- holes:"none" option ---------------------------------------------------
    sn = g.initial_state(options={"holes": "none"})
    if sn.holes:
        fail("holes:none should have no holes")
    if len(_playable(sn.holes)) != 61:
        fail("holes:none should have 61 playable cells")

    # ---- full random games terminate; returns consistent & finite -------------
    import random
    rng = random.Random(0)
    for seed in range(30):
        rng.seed(seed)
        st = g.initial_state(options={"holes": "standard" if seed % 2 else "none"})
        steps = 0
        while not g.is_terminal(st) and steps < 8000:
            lm = g.legal_moves(st)
            if not lm:
                fail("non-terminal state returned no legal moves")
            st = g.apply_move(st, rng.choice(lm))
            steps += 1
        if not g.is_terminal(st):
            fail("game did not terminate within step budget")
        cnt = g._counts(st)
        cap = 61 if not st.holes else 58
        if sum(cnt) > cap or any(x < 0 for x in cnt):
            fail(f"bad terminal counts {cnt}")
        ret = g.returns(st)
        if len(ret) != 3 or any(x != x or abs(x) == float("inf") for x in ret):
            fail(f"returns must be a length-3 finite vector, got {ret}")
        best = max(cnt)
        leaders = [i for i, v in enumerate(cnt) if v == best]
        if len(leaders) == 1:
            if ret != [1.0 if i == leaders[0] else -1.0 for i in range(3)]:
                fail(f"sole leader returns mismatch: {cnt} -> {ret}")
        else:
            if ret != [0.0, 0.0, 0.0]:
                fail(f"tie returns should be draw: {cnt} -> {ret}")
        if g.serialize(g.deserialize(g.serialize(st))) != g.serialize(st):
            fail("serialize round-trip failed on reached state")

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
