"""Standalone correctness anchor for Ataxx.

Run with:  PYTHONPATH=. python3 games/ataxx/selftest.py
Pure stdlib + the agp package only. Prints SELFTEST OK and exits 0 on success.
"""

from __future__ import annotations

import sys

from games.ataxx.game import Ataxx, AtaxxState


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def board_of(g, s):
    return dict(s.board)


def main():
    g = Ataxx()

    # ---- starting position --------------------------------------------------
    s0 = g.initial_state()
    assert g.num_players == 2
    if s0.board != {(0, 0): 0, (6, 6): 0, (6, 0): 1, (0, 6): 1}:
        fail(f"bad start board {s0.board}")
    if g.current_player(s0) != 0:
        fail("Red (0) should move first")
    a, b = g._counts(s0)
    if (a, b) != (2, 2):
        fail(f"start counts {a},{b}")
    if g.is_terminal(s0):
        fail("start should not be terminal")
    # round-trip
    if g.serialize(g.deserialize(g.serialize(s0))) != g.serialize(s0):
        fail("serialize does not round-trip")

    # ---- (1) GROW: distance-1 clone adds a NEW piece, source stays ----------
    # Hand-built: a single Red piece in the middle, nothing else.
    s = AtaxxState(board={(3, 3): 0}, to_move=0, ply=0)
    moves = set(g.legal_moves(s))
    if "3,3>4,4" not in moves:
        fail("grow move 3,3>4,4 not offered")
    s2 = g.apply_move(s, "3,3>4,4")
    if (3, 3) not in s2.board or s2.board[(3, 3)] != 0:
        fail("grow must KEEP the source piece")
    if s2.board.get((4, 4)) != 0:
        fail("grow must place a NEW Red piece on the target")
    if len(s2.board) != 2:
        fail(f"grow should yield 2 pieces, got {len(s2.board)}")
    if g._counts(s2)[0] != 2:
        fail("grow: Red should gain a piece (1 -> 2)")

    # ---- (2) JUMP: distance-2 MOVES the piece, source becomes empty ---------
    s = AtaxxState(board={(3, 3): 0}, to_move=0, ply=0)
    if "3,3>5,3" not in set(g.legal_moves(s)):
        fail("jump move 3,3>5,3 (distance 2) not offered")
    s2 = g.apply_move(s, "3,3>5,3")
    if (3, 3) in s2.board:
        fail("jump must VACATE the source cell")
    if s2.board.get((5, 3)) != 0:
        fail("jump must place the piece on the target")
    if len(s2.board) != 1:
        fail(f"jump must not change piece count, got {len(s2.board)}")

    # ---- distance-3 is NOT a legal target -----------------------------------
    s = AtaxxState(board={(0, 0): 0}, to_move=0, ply=0)
    for mv in g.legal_moves(s):
        sc, dc = mv.split(">")
        c, r = map(int, sc.split(","))
        tc, tr = map(int, dc.split(","))
        d = max(abs(tc - c), abs(tr - r))
        if d not in (1, 2):
            fail(f"illegal-distance move offered: {mv} (dist {d})")

    # ---- (3) infection: every adjacent enemy flips; non-adjacent does not ---
    # Red grows into (3,3); Blue pieces all around it flip; a Blue 2 cells away stays.
    board = {
        (2, 2): 1, (2, 3): 1, (2, 4): 1,
        (3, 2): 1, (3, 4): 1,
        (4, 2): 1, (4, 3): 1, (4, 4): 1,   # 8 neighbours of (3,3), all Blue
        (1, 3): 1,                          # 2 cells from (3,3): must NOT flip
        (3, 1): 0,                          # the Red piece that will grow into (3,3)
    }
    s = AtaxxState(board=board, to_move=0, ply=0)
    # (3,1) -> (3,3) is a jump (distance 2) landing in the middle of the 8 Blues
    s2 = g.apply_move(s, "3,1>3,3")
    for nb in [(2, 2), (2, 3), (2, 4), (3, 2), (3, 4), (4, 2), (4, 3), (4, 4)]:
        if s2.board.get(nb) != 0:
            fail(f"infection failed to flip adjacent enemy at {nb}")
    if s2.board.get((1, 3)) != 1:
        fail("infection wrongly flipped a NON-adjacent enemy at (1,3)")
    if s2.board.get((3, 3)) != 0:
        fail("destination should hold the moved Red piece")
    # net: Red flipped 8 blues + landed; count Red
    if g._counts(s2)[0] != 9:
        fail(f"infection multi-flip count wrong: Red={g._counts(s2)[0]}")

    # ---- (4a) pass: a player with no move passes, opponent keeps playing ----
    # Red boxed into the corner by Blue so Red has no empty target; Blue can move.
    # Fill the whole board except give Blue some empties far away.
    board = {}
    for c in range(7):
        for r in range(7):
            board[(c, r)] = 1  # all Blue
    board[(0, 0)] = 0          # one Red, fully surrounded by Blue, no empty cell
    # remove a couple of cells far from Red so Blue still has a move
    del board[(6, 6)]
    del board[(5, 6)]
    s = AtaxxState(board=board, to_move=0, ply=0)
    if g.is_terminal(s):
        fail("not terminal: Blue still has a move")
    lm = g.legal_moves(s)
    if lm != ["pass"]:
        fail(f"Red boxed in should only have pass, got {lm}")
    s2 = g.apply_move(s, "pass")
    if g.current_player(s2) != 1:
        fail("after Red passes it should be Blue's move")
    if g.legal_moves(s2) == ["pass"] or not g.legal_moves(s2):
        fail("Blue should have real moves after Red passes")

    # ---- (4b) most pieces wins / tie = draw ---------------------------------
    # terminal full-board: Red 25, Blue 24 -> Red wins
    board = {}
    n = 0
    for c in range(7):
        for r in range(7):
            board[(c, r)] = 0 if n < 25 else 1
            n += 1
    s = AtaxxState(board=board, to_move=0, ply=0)
    if not g._board_full(s) or not g.is_terminal(s):
        fail("full board should be terminal")
    if g.returns(s) != [1.0, -1.0]:
        fail(f"Red 25 vs Blue 24 should be Red win, got {g.returns(s)}")
    if g.legal_moves(s) != []:
        fail("terminal state must have no legal moves")
    # tie
    board = {}
    n = 0
    for c in range(7):
        for r in range(7):
            board[(c, r)] = 0 if n < 24 else (1 if n < 48 else 0)
            n += 1
    # 48 cells assigned above leaves one; make it explicit 24/24 by trimming one
    del board[(6, 6)]  # 48 cells: 24 Red, 24 Blue
    s = AtaxxState(board=board, to_move=0, ply=0)
    a, b = g._counts(s)
    if (a, b) != (24, 24):
        fail(f"tie setup wrong: {a},{b}")
    if g.returns(s) != [0.0, 0.0]:
        fail(f"24-24 should be a draw, got {g.returns(s)}")

    # ---- (5) fill-to-end count via real apply_move from start ---------------
    # Play a deterministic random-ish game to a terminal and check counts sum.
    import random
    rng = random.Random(12345)
    for seed in range(20):
        rng.seed(seed)
        st = g.initial_state()
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
        if a + b > 49 or a < 0 or b < 0:
            fail(f"bad terminal counts {a},{b}")
        ret = g.returns(st)
        if len(ret) != 2 or not all(x in (-1.0, 0.0, 1.0) for x in ret):
            fail(f"bad returns {ret}")
        # returns consistent with counts
        if a > b and ret != [1.0, -1.0]:
            fail("returns disagree with counts (Red more)")
        if b > a and ret != [-1.0, 1.0]:
            fail("returns disagree with counts (Blue more)")
        if a == b and ret != [0.0, 0.0]:
            fail("returns disagree with counts (tie)")

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
