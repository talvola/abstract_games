"""Jed selftest — pure stdlib.

Anchors (Abstract Games #22, pp. 24-25 & 34):

1. The J/E/D colouring, extracted pixel-precisely from the "Jed board" figure
   (p. 25), matches type(c,r) = "JED"[(c-r) % 3]: 33/33/33 split, a proper
   3-colouring (adjacent cells always differ), corners A1=J A11=E I1=E I11=D.
2. Addendum-2 protocol facts: the required type never runs out before the
   board fills (99 = 3x33); if J is played first, after 95 placements the
   vacant cells are exactly {J:1, E:1, D:2} (chilling pair = two D's, "a green
   and red space will be left unfilled") and the final fill sequence is
   D-J-E-D.  Likewise E-first -> pair of J's, D-first -> pair of E's.
3. Figure 1 of the Jade article (p. 24, extracted pixel-precisely): a 22-stone
   all-Black position = a Cross win (one group touching all four sides), not
   a Parallel win.  Figure 2: 14 Black + 12 White = a Parallel win (both
   colours span the A/I row pair), not a Cross win.
4. Minimum-stone wins: Parallel's minimum = 18 stones (two straight 9-chains
   row-A..row-I; printed fact, p. 34).  Cross's TRUE minimum = 11 — the
   short-diagonal chain A11-I1, whose two corner cells count for both sides
   (anchor: the pbmserv Jade reference implementation's example diagrams
   adjudicate a bare 7-stone short-diagonal on 7x7 as "Cross wins"; the
   magazine's printed "Cross needs 19" counts the row+column cross shape and
   is an errata).  The printed 19-stone cross shape still wins, and the win
   check must fire at the FIRST completion (11-stone game, regression for a
   len>=18 gating bug found in QA).
5. Mutual exclusivity: Cross and Parallel can never hold at once (the Hex
   crossing lemma; asserted on every random filled board in check 7).
6. Hox-protocol cycle enforcement and modified-pie semantics via the engine.
7. No-draw theorem: 300 random protocol-legal board fills all satisfy exactly
   one objective; 40 random playouts all terminate with a winner correctly
   attributed to the completing role's seat.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir  # noqa: E402

_man, G = load_from_dir(Path(__file__).resolve().parent)
from games.jed.game import (  # noqa: E402
    COLS, ROW_PAIR, ROWS, TYPES,
    _cross_won, _decide, _group_masks, _parallel_won, cell_type, _neighbors,
)

# ---- 1. the extracted J/E/D colouring (rows A..I, columns 1..11) -----------

FIGURE_COLOURING = [
    "JEDJEDJEDJE",   # A
    "DJEDJEDJEDJ",   # B
    "EDJEDJEDJED",   # C
    "JEDJEDJEDJE",   # D
    "DJEDJEDJEDJ",   # E
    "EDJEDJEDJED",   # F
    "JEDJEDJEDJE",   # G
    "DJEDJEDJEDJ",   # H
    "EDJEDJEDJED",   # I
]

counts = {"J": 0, "E": 0, "D": 0}
for r in range(ROWS):
    for c in range(COLS):
        t = TYPES[cell_type(c, r)]
        assert t == FIGURE_COLOURING[r][c], f"colouring mismatch at c={c},r={r}"
        counts[t] += 1
assert counts == {"J": 33, "E": 33, "D": 33}, counts
# proper 3-colouring: neighbours always differ
for r in range(ROWS):
    for c in range(COLS):
        for nc, nr in _neighbors(c, r):
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                assert cell_type(c, r) != cell_type(nc, nr)
# corners (A1, A11, I1, I11)
assert TYPES[cell_type(0, 0)] == "J"
assert TYPES[cell_type(10, 0)] == "E"
assert TYPES[cell_type(0, 8)] == "E"
assert TYPES[cell_type(10, 8)] == "D"
print("1. J/E/D colouring matches the magazine figure (33/33/33, proper)")

# ---- 2. Addendum-2 protocol facts ------------------------------------------

for start in range(3):
    used = [0, 0, 0]
    for ply in range(1, 100):
        t = (start + ply - 1) % 3
        assert used[t] < 33, f"required type ran out at ply {ply} (start {start})"
        used[t] += 1
    assert used == [33, 33, 33][:]
# J first (start=0): after 95 placements the vacant cells are J:1 E:1 D:2
used = [0, 0, 0]
for ply in range(1, 96):
    used[(ply - 1) % 3] += 1
rem = [33 - u for u in used]
assert rem == [1, 1, 2], rem                      # chilling pair = two D's
final_four = [TYPES[(ply - 1) % 3] for ply in range(96, 100)]
assert final_four == ["D", "J", "E", "D"], final_four
# E first -> two J's remain; D first -> two E's
for start, pair in ((1, 0), (2, 1)):
    used = [0, 0, 0]
    for ply in range(1, 96):
        used[(start + ply - 1) % 3] += 1
    rem = [33 - u for u in used]
    assert rem[pair] == 2 and sorted(rem) == [1, 1, 2], (start, rem)
print("2. protocol facts: type never runs out; chill remainders + D-J-E-D tail")

# ---- 3. the Jade article's Figure 1 / Figure 2 -----------------------------

FIG1_BLACK = [(8, 0), (7, 1), (0, 2), (1, 2), (2, 2), (6, 2), (2, 3), (5, 3),
              (2, 4), (5, 4), (2, 5), (3, 5), (4, 5), (5, 5), (5, 6), (6, 6),
              (8, 6), (9, 6), (10, 6), (6, 7), (7, 7), (7, 8)]
FIG2_BLACK = [(2, 0), (2, 1), (2, 2), (1, 3), (1, 4), (1, 5), (0, 6), (3, 6),
              (4, 6), (0, 7), (1, 7), (2, 7), (4, 7), (4, 8)]
FIG2_WHITE = [(7, 0), (6, 1), (6, 2), (5, 3), (5, 4), (6, 4), (6, 5), (7, 5),
              (7, 6), (7, 7), (8, 7), (8, 8)]

fig1 = {cell: "B" for cell in FIG1_BLACK}
assert len(fig1) == 22
assert _decide(fig1) == "C"
assert not _parallel_won(_group_masks(fig1, "B"), _group_masks(fig1, "W"))
# one single group does it
assert len(_group_masks(fig1, "B")) == 1

fig2 = {cell: "B" for cell in FIG2_BLACK}
fig2.update({cell: "W" for cell in FIG2_WHITE})
assert len(fig2) == 26
assert _decide(fig2) == "P"
mb, mw = _group_masks(fig2, "B"), _group_masks(fig2, "W")
assert not _cross_won(mb, mw)
# both colours span the row (A/I) pair, not the column pair together
assert any(m & ROW_PAIR == ROW_PAIR for m in mb)
assert any(m & ROW_PAIR == ROW_PAIR for m in mw)
print("3. Figure 1 = Cross win; Figure 2 = Parallel win (row pair)")

# ---- 4. minimum-stone wins + corner rule -----------------------------------

# Parallel minimum = 18: two straight columns spanning rows A..I
par18 = {(0, r): "B" for r in range(ROWS)}
par18.update({(4, r): "W" for r in range(ROWS)})
assert len(par18) == 18
assert _decide(par18) == "P"
broken = dict(par18)
del broken[(4, 4)]                                # 17 stones: no win
assert _decide(broken) is None

# Cross minimum = 19: full row 4 + full column 5 sharing (5,4)
cr19 = {(c, 4): "B" for c in range(COLS)}
cr19.update({(5, r): "B" for r in range(ROWS)})
assert len(cr19) == 19
assert _decide(cr19) == "C"

# corner cells belong to both adjacent sides: row A + column 1 (an L through
# corners A1/A11; A11 and I1 are this group's ONLY contacts with those sides)
corner_l = {(c, 0): "B" for c in range(COLS)}
corner_l.update({(0, r): "B" for r in range(ROWS)})
assert _decide(corner_l) == "C"

# Cross's TRUE minimum = 11: the short-diagonal chain A11-I1 touches all four
# sides via its two corner cells (pbmserv-anchored; magazine's "19" = errata).
DIAG = [(10, 0), (9, 1), (8, 2), (7, 3), (6, 4), (5, 5), (4, 6), (3, 7),
        (2, 8), (1, 8), (0, 8)]
diag11 = {cell: "B" for cell in DIAG}
assert len(diag11) == 11
assert _decide(diag11) == "C"
for drop_cell in DIAG:                       # any 10-stone sub-set is no win
    sub = dict(diag11)
    del sub[drop_cell]
    assert _decide(sub) is None, drop_cell
print("4. Parallel-18, Cross-19 shape and Cross-11 diagonal minima; corner rule")

# regression (QA 2026-07-19): the win check must fire at the FIRST completion,
# not from stone 18 — protocol-legal 11-ply diagonal Cross win via the engine.
s = G.initial_state()
for mv in ("10,0=BC", "9,1=B", "8,2=B", "7,3=B", "6,4=B", "5,5=B",
           "4,6=B", "3,7=B", "2,8=B", "0,8=B", "1,8=B"):
    assert not G.is_terminal(s)
    assert mv in G.legal_moves(s), mv
    s = G.apply_move(s, mv)
assert s.winner == 0 and s.win_role == "C" and G.is_terminal(s), \
    (s.winner, s.win_role)
assert G.returns(s) == [1.0, -1.0]
print("4b. 11-stone diagonal win terminates the game at first completion")

# ---- 5. Cross and Parallel can never hold at once ---------------------------
# (A Cross group spans BOTH side pairs; Parallel's opposite-coloured spanning
# group would have to cross one of those chains — impossible on a hex board.
# Checked empirically over every random filled board in section 7 below.)

# ---- 6. engine: hox cycle + modified pie ------------------------------------

s0 = G.initial_state()
ms = G.legal_moves(s0)
assert len(ms) == 99 * 4 and "5,4=WC" in ms
s1 = G.apply_move(s0, "5,4=WC")                    # E cell, declares Cross
assert G.current_player(s1) == 1 and s1.cross_seat is None
ms1 = G.legal_moves(s1)
assert "swap" in ms1
placements = [m for m in ms1 if m != "swap"]
assert len(placements) == 33 * 2                   # all vacant D cells x 2 colours
for m in placements:
    c, r = map(int, m.split("=")[0].split(","))
    assert TYPES[cell_type(c, r)] == "D"

# swap branch: seat 1 adopts the move AND the Cross role; play returns to P1
s2 = G.apply_move(s1, "swap")
assert G.current_player(s2) == 0 and s2.cross_seat == 1
assert s2.board == {(5, 4): "W"} and s2.last_type == 1
follow = G.legal_moves(s2)
assert "swap" not in follow and len(follow) == 66  # still D cells due

# reply branch: seat 0 keeps the declared role
s2b = G.apply_move(s1, "2,0=B")                    # a D cell
assert s2b.cross_seat == 0 and s2b.board[(2, 0)] == "B"
ms2b = G.legal_moves(s2b)
assert len(ms2b) == 66
for m in ms2b:
    c, r = map(int, m.split("=")[0].split(","))
    assert TYPES[cell_type(c, r)] == "J"           # D is followed by J

# serialize round-trip
d = G.serialize(s2b)
assert G.serialize(G.deserialize(d)) == d
print("6. cycle enforcement, pie semantics, serialize round-trip")

# ---- 7. no draws: random fills + random playouts ---------------------------

rng = random.Random(20260719)
for trial in range(300):
    cells_by_type = {t: [] for t in range(3)}
    for r in range(ROWS):
        for c in range(COLS):
            cells_by_type[cell_type(c, r)].append((c, r))
    for t in range(3):
        rng.shuffle(cells_by_type[t])
    start = rng.randrange(3)
    board = {}
    for ply in range(99):
        t = (start + ply) % 3
        assert cells_by_type[t], "protocol starved before the board filled"
        board[cells_by_type[t].pop()] = rng.choice("BW")
    mb, mw = _group_masks(board, "B"), _group_masks(board, "W")
    cross, par = _cross_won(mb, mw), _parallel_won(mb, mw)
    assert cross or par, "filled board with no objective met"
    assert not (cross and par), "Cross and Parallel held simultaneously"

wins = {"C": 0, "P": 0}
for seed in range(40):
    prng = random.Random(1000 + seed)
    s = G.initial_state()
    plies = 0
    while not G.is_terminal(s):
        ms = G.legal_moves(s)
        assert ms, "non-terminal state with no legal moves"
        s = G.apply_move(s, prng.choice(ms))
        plies += 1
        assert plies <= 100
    assert s.winner in (0, 1), "random playout ended without a winner"
    assert s.win_role in ("C", "P")
    expected = s.cross_seat if s.win_role == "C" else 1 - s.cross_seat
    assert s.winner == expected
    assert G.returns(s)[s.winner] == 1.0
    wins[s.win_role] += 1
assert wins["C"] > 0 and wins["P"] > 0, wins
print(f"7. 300 random fills all decided; 40 playouts all won (roles {wins})")

# ---- 8. render shape probe ---------------------------------------------------

spec = G.render(s2b)
assert spec["board"]["type"] == "hex" and spec["board"]["shape"] == "rhombus"
assert spec["board"]["width"] == 11 and spec["board"]["height"] == 9
assert len(spec["board"]["tints"]) == 99
assert all("fill" in p and "stroke" in p for p in spec["pieces"])
assert G.describe_move(s0, "5,4=WC") == "White E6 [E] — declares Cross"
assert G.describe_move(s2, "2,0=B") == "Black A3 [D]"
print("8. render spec shape + notation")

print("jed selftest: all checks passed")
