"""Standalone correctness anchor for Domineering.

Run with:  PYTHONPATH=. python3 games/domineering/selftest.py

Pure-stdlib: imports only `agp` (transitively) and this game. No third-party
deps, no long random loops. Anchor = baked rule asserts + small-board CGT
outcomes obtained by full game-tree search (cheap for boards <= 4x4).

There is no published perft for Domineering, so the anchor is:
 1. rectangular grid (default 8x8) + a size option;
 2. player 0 (Vertical) covers (c,r)+(c,r+1); player 1 (Horizontal) covers
    (c,r)+(c+1,r); both cells must be empty and on-board;
 3. no captures (placing never removes/moves a piece);
 4. normal play: the player who cannot place a domino loses (last to move wins);
 5. a few small-board forced-win outcomes verified by exhaustive search and
    baked here as plain assertions.
"""

import sys

from games.domineering.game import Domineering, DomState, VERTICAL, HORIZONTAL


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


g = Domineering()


# ---- (1) default board is 8x8; size option works ---------------------------
s0 = g.initial_state()
check((s0.width, s0.height) == (8, 8), f"default board not 8x8: {s0.width}x{s0.height}")
check(len(s0.board) == 0, "initial board not empty")
check(g.current_player(s0) == VERTICAL, "Vertical (player 0) must move first")

s6 = g.initial_state(options={"size": "6x6"})
check((s6.width, s6.height) == (6, 6), "size 6x6 option failed")
s86 = g.initial_state(options={"size": "8x6"})
check((s86.width, s86.height) == (8, 6), "size 8x6 (cols x rows) option failed")


# ---- (2) orientation: Vertical covers (c,r)+(c,r+1) ------------------------
# (use a 3x3 built directly: 3x3 isn't an offered size option)
s = DomState(width=3, height=3)
moves = set(g.legal_moves(s))
check("0,0>0,1" in moves, "Vertical should be able to place (0,0)+(0,1)")
check("0,0>1,0" not in moves, "Vertical must NOT place a horizontal domino")
# every Vertical legal move is a vertical pair
for m in moves:
    a, b = m.split(">")
    ac = tuple(int(x) for x in a.split(","))
    bc = tuple(int(x) for x in b.split(","))
    check(bc == (ac[0], ac[1] + 1), f"non-vertical move for player 0: {m}")

# After Vertical plays, it's Horizontal's turn -> horizontal pairs only.
s1 = g.apply_move(s, "0,0>0,1")
check(g.current_player(s1) == HORIZONTAL, "turn must pass to Horizontal")
hmoves = set(g.legal_moves(s1))
check("1,0>2,0" in hmoves, "Horizontal should place (1,0)+(2,0)")
for m in hmoves:
    a, b = m.split(">")
    ac = tuple(int(x) for x in a.split(","))
    bc = tuple(int(x) for x in b.split(","))
    check(bc == (ac[0] + 1, ac[1]), f"non-horizontal move for player 1: {m}")


# ---- (3) no captures; placement fills two empty cells, never removes -------
check(s1.board.get((0, 0)) == VERTICAL and s1.board.get((0, 1)) == VERTICAL,
      "Vertical domino not recorded on both cells")
check(len(s1.board) == 2, "a domino must fill exactly two cells")
s2 = g.apply_move(s1, "1,0>2,0")
check(len(s2.board) == 4, "placement must not remove existing pieces (no captures)")
for cell in [(0, 0), (0, 1), (1, 0), (2, 0)]:
    check(cell in s2.board, f"cell {cell} should still be occupied after next placement")


# ---- overlap rejection ------------------------------------------------------
overlapped = False
try:
    g.apply_move(s1, "0,0>0,1")  # both cells already occupied
except ValueError:
    overlapped = True
check(overlapped, "overlapping domino should be rejected")
# overlap of a single shared cell
overlapped2 = False
try:
    g.apply_move(s1, "0,1>0,2")  # (0,1) is occupied
except ValueError:
    overlapped2 = True
check(overlapped2, "domino overlapping one occupied cell should be rejected")


# ---- off-board rejection ----------------------------------------------------
offboard = False
try:
    g.apply_move(s, "2,2>2,3")  # (2,3) is off a 3x3 board
except ValueError:
    offboard = True
check(offboard, "off-board domino should be rejected")


# ---- (4) normal play: player who cannot place loses ------------------------
# 1x2 column: only Vertical can place; after it does, Horizontal has no move.
sc = g.initial_state()
sc = DomState(width=1, height=2)
check(g.legal_moves(sc) == ["0,0>0,1"], "1x2: Vertical has exactly one move")
sc1 = g.apply_move(sc, "0,0>0,1")
check(g.is_terminal(sc1), "1x2 should be terminal after the one vertical domino")
ret = g.returns(sc1)
# Horizontal (player 1) is to move and cannot -> loses; Vertical wins.
check(ret == [1.0, -1.0], f"1x2 normal-play result wrong: {ret}")

# 2x1 row: Vertical cannot place at all -> Vertical (player 0) loses immediately.
sr = DomState(width=2, height=1)
check(g.legal_moves(sr) == [], "2x1: Vertical has no vertical placement")
check(g.is_terminal(sr), "2x1 with Vertical to move and no move is terminal")
check(g.returns(sr) == [-1.0, 1.0], "2x1: Vertical to move with no move should lose")


# ---- (5) small-board forced-win outcomes via exhaustive search -------------
def first_player_wins(state):
    """True iff the player to move has a winning strategy (normal play)."""
    moves = g.legal_moves(state)
    if not moves:
        return False  # mover cannot move -> mover loses
    for m in moves:
        if not first_player_wins(g.apply_move(state, m)):
            return True
    return False


# Known results (first player = Vertical, who moves first):
EXPECT = {
    (1, 1): (0, False),   # no cell pair fits -> Vertical loses
    (2, 1): (0, False),   # row board, no vertical space -> Vertical loses
    (1, 2): (1, True),    # column -> Vertical wins
    (2, 2): (2, True),    # Vertical wins
    (3, 3): (6, True),    # Vertical wins
    (2, 3): (4, True),    # Vertical wins
    (3, 2): (3, True),    # Vertical wins
    (4, 4): (12, True),   # Vertical wins
}
for (w, h), (n_moves, vert_wins) in EXPECT.items():
    st = DomState(width=w, height=h)
    check(len(g.legal_moves(st)) == n_moves,
          f"{w}x{h}: expected {n_moves} Vertical moves, got {len(g.legal_moves(st))}")
    check(first_player_wins(st) == vert_wins,
          f"{w}x{h}: expected Vertical-wins={vert_wins}")


# ---- serialize round-trips --------------------------------------------------
import json
snap = g.serialize(s2)
json.dumps(snap)  # must be JSON-able
again = g.serialize(g.deserialize(snap))
check(again == snap, "serialize/deserialize does not round-trip")


print("SELFTEST OK")
