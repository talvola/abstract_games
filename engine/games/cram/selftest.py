"""Standalone correctness anchor for Cram.

Run with:  PYTHONPATH=. python3 games/cram/selftest.py

Pure-stdlib: imports only `agp` (transitively) and this game. No third-party
deps, no long random loops. Anchor = baked rule asserts + small-board CGT
outcomes obtained by full game-tree search (cheap for boards up to ~3x4).

There is no published perft for Cram, so the anchor is:
 1. rectangular grid (default 6x6) + a size option;
 2. EITHER player may place a domino covering two empty orthogonally-adjacent
    cells in EITHER orientation (horizontal OR vertical) — impartial, unlike
    Domineering where each player has a fixed orientation;
 3. no captures (placing never removes/moves a piece);
 4. normal play: the player who cannot place a domino loses (last to move wins);
 5. the parity result, verified by EXHAUSTIVE SEARCH on small boards and baked
    here as a literal outcome table. The one rigorously-proven theorem is:
    BOTH dimensions even -> SECOND player wins (centre-symmetry mirror strategy).
    Beyond that Cram has NO simple closed-form winner -- the popular "both-even
    -> 2nd, otherwise 1st" statement is incomplete (it is wrong for odd-by-odd
    boards, e.g. 3x3 is a 2nd-player win). We therefore assert the searched
    outcomes directly rather than a parity formula.
"""

import sys
import json

from games.cram.game import Cram, CramState


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


g = Cram()


# ---- (1) default board is 6x6; size option works ---------------------------
s0 = g.initial_state()
check((s0.width, s0.height) == (6, 6), f"default board not 6x6: {s0.width}x{s0.height}")
check(len(s0.board) == 0, "initial board not empty")
check(g.current_player(s0) == 0, "Player 0 must move first")

s4 = g.initial_state(options={"size": "4x4"})
check((s4.width, s4.height) == (4, 4), "size 4x4 option failed")
s46 = g.initial_state(options={"size": "4x6"})
check((s46.width, s46.height) == (4, 6), "size 4x6 (cols x rows) option failed")
s64 = g.initial_state(options={"size": "6x4"})
check((s64.width, s64.height) == (6, 4), "size 6x4 (cols x rows) option failed")


# ---- (2) IMPARTIAL: both orientations available to the player to move -------
# On an empty 3x3 board the player to move can place horizontal AND vertical.
s = CramState(width=3, height=3)
moves = set(g.legal_moves(s))
check("0,0>1,0" in moves, "horizontal domino (0,0)+(1,0) must be legal")
check("0,0>0,1" in moves, "vertical domino (0,0)+(0,1) must be legal")
# every move is an orthogonally-adjacent pair, no duplicates
seen = set()
for m in moves:
    a_s, b_s = m.split(">")
    a = tuple(int(x) for x in a_s.split(","))
    b = tuple(int(x) for x in b_s.split(","))
    dc, dr = abs(a[0] - b[0]), abs(a[1] - b[1])
    check((dc, dr) in ((1, 0), (0, 1)), f"non-adjacent move listed: {m}")
    key = frozenset((a, b))
    check(key not in seen, f"duplicate domino listed: {m}")
    seen.add(key)
# Exact count on an empty 3x3: horizontals 2 per row * 3 rows = 6;
# verticals 2 per col * 3 cols = 6; total 12.
check(len(moves) == 12, f"empty 3x3 should have 12 legal dominoes, got {len(moves)}")

# Hand-built: the SAME player places a horizontal then (a different) player a
# vertical -> both orientations are genuinely available in play (impartiality).
sH = g.apply_move(s, "0,0>1,0")          # player 0 plays HORIZONTAL
check(g.current_player(sH) == 1, "turn must pass to player 1")
check("2,1>2,2" in set(g.legal_moves(sH)), "player 1 should be able to play a VERTICAL domino")
sHV = g.apply_move(sH, "2,1>2,2")        # player 1 plays VERTICAL
check(sHV.board.get((2, 1)) == 1 and sHV.board.get((2, 2)) == 1, "vertical domino not recorded")
# And confirm a player can play a vertical right after the empty board too:
sV = g.apply_move(s, "0,0>0,1")          # player 0 plays VERTICAL on a fresh board
check(sV.board.get((0, 0)) == 0 and sV.board.get((0, 1)) == 0, "vertical placement failed")


# ---- (3) no captures; placement fills two empty cells, never removes -------
check(sH.board.get((0, 0)) == 0 and sH.board.get((1, 0)) == 0, "domino not on both cells")
check(len(sH.board) == 2, "a domino must fill exactly two cells")
check(len(sHV.board) == 4, "placement must not remove existing pieces (no captures)")
for cell in [(0, 0), (1, 0), (2, 1), (2, 2)]:
    check(cell in sHV.board, f"cell {cell} should still be occupied (no captures)")


# ---- overlap rejection ------------------------------------------------------
def rejects(state, move):
    try:
        g.apply_move(state, move)
        return False
    except ValueError:
        return True


check(rejects(sH, "0,0>1,0"), "fully overlapping domino should be rejected")
check(rejects(sH, "1,0>2,0"), "domino overlapping one occupied cell should be rejected")
check(rejects(sH, "0,0>0,1"), "domino sharing one occupied cell should be rejected")


# ---- off-board / non-adjacent rejection -------------------------------------
check(rejects(s, "2,2>3,2"), "off-board domino should be rejected")
check(rejects(s, "0,0>2,0"), "non-adjacent (gap) domino should be rejected")
check(rejects(s, "0,0>1,1"), "diagonal domino should be rejected")


# ---- (4) normal play: player who cannot place loses ------------------------
# 1x1: no domino fits -> player 0 (to move) loses immediately.
s11 = CramState(width=1, height=1)
check(g.legal_moves(s11) == [], "1x1 has no legal domino")
check(g.is_terminal(s11), "1x1 is terminal")
check(g.returns(s11) == [-1.0, 1.0], "1x1: player to move with no move should lose")

# 1x2: exactly one domino; after it is placed, the other player cannot move.
s12 = CramState(width=1, height=2)
check(g.legal_moves(s12) == ["0,0>0,1"], "1x2 has exactly one (vertical) domino")
s12a = g.apply_move(s12, "0,0>0,1")
check(g.is_terminal(s12a), "1x2 terminal after the one domino")
check(g.returns(s12a) == [1.0, -1.0], "1x2: placer (player 0) wins, opponent loses")

# 2x1: exactly one (horizontal) domino — confirms both orientations win likewise.
s21 = CramState(width=2, height=1)
check(g.legal_moves(s21) == ["0,0>1,0"], "2x1 has exactly one (horizontal) domino")
check(g.returns(g.apply_move(s21, "0,0>1,0")) == [1.0, -1.0], "2x1: placer wins")


# ---- (5) parity theorem via exhaustive search ------------------------------
def first_player_wins(state):
    """True iff the player to move has a winning strategy (normal play)."""
    moves = g.legal_moves(state)
    if not moves:
        return False  # mover cannot move -> mover loses
    for m in moves:
        if not first_player_wins(g.apply_move(state, m)):
            return True
    return False


# The one rigorously-PROVEN theorem (Gardner / Winning Ways): on a board with
# BOTH dimensions even the SECOND player wins, by the centre-symmetry mirror
# strategy (every domino has a distinct 180-deg-reflected partner). Assert that
# directly against the exhaustive search for the even-by-even boards we can
# afford to search.
for (w, h) in [(2, 2), (2, 4), (4, 2), (4, 4)]:
    st = CramState(width=w, height=h)
    check(first_player_wins(st) is False,
          f"{w}x{h} (both even): mirror strategy => SECOND player must win")

# Full exhaustive-search ground-truth table for small boards. NOTE: Cram has no
# simple closed-form winner for general boards -- the popular "both-even -> 2nd,
# else 1st" statement is INCOMPLETE (it is wrong for odd-by-odd boards such as
# 3x3, which is a 2nd-player win). So we bake the *searched* outcomes literally
# rather than a parity formula. Each value is first_player_wins (True = the
# player to move / Player 1 wins; False = Player 2 wins). The illustrative cases
# the task names: 2x2 is a SECOND-player win, 2x3 is a FIRST-player win.
EXPECT = {
    # (w, h): first_player_wins (verified by exhaustive search)
    (1, 1): False,   # no domino fits -> mover loses
    (2, 1): True,    # single horizontal domino -> placer (P1) wins
    (1, 2): True,    # single vertical domino   -> placer (P1) wins
    (3, 1): True,    # 3x1 strip                -> P1 wins
    (1, 3): True,
    (2, 2): False,   # both even (mirror)       -> P2 wins
    (3, 2): True,
    (2, 3): True,    # the task's first-player example
    (3, 3): False,   # both ODD                 -> P2 wins (the formula exception)
    (4, 2): False,   # both even                -> P2 wins
    (2, 4): False,
    (3, 4): True,
    (4, 4): False,   # both even                -> P2 wins
}
for (w, h), expected in EXPECT.items():
    st = CramState(width=w, height=h)
    got = first_player_wins(st)
    check(got == expected,
          f"{w}x{h}: expected first_player_wins={expected}, got {got}")


# ---- serialize round-trips --------------------------------------------------
snap = g.serialize(sHV)
json.dumps(snap)  # must be JSON-able
again = g.serialize(g.deserialize(snap))
check(again == snap, "serialize/deserialize does not round-trip")


print("SELFTEST OK")
