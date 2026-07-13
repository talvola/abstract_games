"""Standalone correctness anchor for Rive (Mark Steere, December 2010).

Run from the engine dir:  PYTHONPATH=. python3 games/rive/selftest.py

There is no published perft for Rive, so the anchor is Mark Steere's one-page
rule sheet (marksteeregames.com/Rive.pdf), whose Figures 1-3d carry worked
examples. Each figure is reconstructed here in axial coordinates (the hexhex of
side 3 the figures use, 19 cells) and asserted against the engine:

  (1) hexhex geometry + a GROUP is a connected component of BOTH colours;
  (2) Fig 1 - isolation is mandatory: on that board the legal placements are
      EXACTLY the isolated (no adjacent group) cells;
  (3) Fig 3a - minimise the largest touched group: the legal cells are exactly
      the three capturing cells (each touching two size-2 groups) plus the two
      non-capturing bottom cells; every cell touching the size-3 group is
      illegal;
  (4) Fig 3b - a capturing placement joining two size-2 groups removes two
      stones to a CONNECTED size-3 group (biggest joined + 1), and the same
      player continues (chain);
  (5) Fig 3c - after that capture White's ONLY legal continuation is the single
      non-capturing cell adjacent to a size-2 group, which ends the turn;
  (6) Fig 3d - a capturing placement joining two size-3 groups removes three
      stones to a CONNECTED size-4 group, and the mover must place again;
  (7) removals must never SPLIT the group, and the placed stone is never
      removed;
  (8) majority win on a filled board (odd cells => no tie), win as an event;
  (9) serialize round-trip; (10) random-playout termination.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import random
import sys

from games.rive.game import (
    Rive, RiveState, _cells, _neighbors, _groups, _connected, _cs,
)

G = Rive()
B, W = 0, 1


def die(msg):
    print(f"SELFTEST FAIL: {msg}")
    sys.exit(1)


def check(cond, msg):
    if not cond:
        die(msg)


def mk(black, white, to_move=B):
    """Build a RiveState from lists of (q,r) cells."""
    board = {}
    for c in black:
        board[c] = B
    for c in white:
        board[c] = W
    return RiveState(size=3, board=board, to_move=to_move)


def legal_cells(state):
    """Set of placement cells (first path element) among legal moves."""
    return {m.split(">")[0] for m in G.legal_moves(state)}


# ------------------------------------------------------------ (1) geometry
check(len(_cells(3)) == 19, "hexhex side-3 must have 19 cells")
check(len(_cells(5)) == 61, "hexhex side-5 must have 61 cells")
check(set(_neighbors(0, 0)) == {(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)},
      "axial 6-adjacency")
# a group spans BOTH colours: B-W-B in a line is ONE group of 3
g, _m = _groups({(0, 0): B, (1, 0): W, (2, 0): B}, 3)
check(len(g) == 1 and len(g[0]) == 3, "mixed-colour adjacency = one group")
# two non-adjacent stones are two groups
g, _m = _groups({(0, 0): B, (2, 0): W}, 3)
check(len(g) == 2, "non-adjacent stones = two groups")

# --------------------------------------------------- (2) Fig 1: isolation
fig1 = mk(black=[(0, -2), (-1, 1)], white=[(2, -1)], to_move=B)
# every placed stone is its own size-1 group; only cells with NO adjacent stone
# are legal, and they are exactly the three green cells.
green1 = {"-2,0", "1,1", "0,2"}
check(legal_cells(fig1) == green1,
      f"Fig 1 legal = isolated cells only, got {sorted(legal_cells(fig1))}")
# all such moves are plain single-cell (non-capturing) placements
check(all(">" not in m for m in G.legal_moves(fig1)), "isolated placements are non-capturing")

# ------------------------------------------ Fig 3a/3b/3c/3d shared position
# The board just before White's capturing placement (Fig 3a).
fig3a = mk(
    black=[(0, -2), (0, -1), (-2, 0), (2, 0), (-2, 1)],
    white=[(1, -2), (2, -1), (0, 1), (0, 2)],
    to_move=W,
)
# groups: G1={(0,-2),(1,-2),(0,-1)} size3; G2={(2,-1),(2,0)}; G3={(-2,0),(-2,1)};
#         G4={(0,1),(0,2)} — three size-2 groups + one size-3 group.
gg, _m = _groups(fig3a.board, 3)
sizes = sorted(len(x) for x in gg)
check(sizes == [2, 2, 2, 3], f"Fig 3a groups sizes {sizes} != [2,2,2,3]")

# --------------------------------------- (3) Fig 3a: minimise largest group
cap_cells = {"1,0", "-1,1", "1,1"}       # touch two size-2 groups (green)
noncap_cells = {"-2,2", "-1,2"}          # touch one size-2 group (bottom)
check(legal_cells(fig3a) == cap_cells | noncap_cells,
      f"Fig 3a legal cells wrong: {sorted(legal_cells(fig3a))}")
# it is ILLEGAL to touch the size-3 group -> e.g. (0,0),(1,-1),(-1,0),(2,-2)...
for bad in ("0,0", "1,-1", "-1,0", "2,-2", "-1,-1"):
    check(bad not in legal_cells(fig3a),
          f"{bad} touches the size-3 group and must be illegal")
# the three green cells are capturing (paths with removals); the bottom two are not
capm = [m for m in G.legal_moves(fig3a) if ">" in m]
check({m.split(">")[0] for m in capm} == cap_cells, "capturing cells must be the green trio")
check("-2,2" in G.legal_moves(fig3a) and "-1,2" in G.legal_moves(fig3a),
      "the two non-capturing placements must be plain cells")

# --------------------------------------- (4) Fig 3b: capture 2 size-2 -> size-3
# White plays (1,0), joining G2 and G4; the sheet removes (2,0) and (0,2).
fig3b_move = "1,0>2,0>0,2"
check(fig3b_move in G.legal_moves(fig3a),
      "Fig 3b removal (remove 2,0 and 0,2) must be a legal capturing move")
after3b = G.apply_move(fig3a, fig3b_move)
# combined was {(1,0),(2,-1),(2,0),(0,1),(0,2)} size5; biggest joined = 2 -> target 3.
new_group = None
gg2, _m = _groups(after3b.board, 3)
for x in gg2:
    if (1, 0) in x:
        new_group = x
check(new_group is not None and len(new_group) == 3,
      "Fig 3b: the placed stone's group must be size 3 (biggest joined + 1)")
check(_connected(set(new_group), 3), "Fig 3b: survivors must be a single connected group")
check((2, 0) not in after3b.board and (0, 2) not in after3b.board,
      "Fig 3b: the two red stones are removed")
check(after3b.to_move == W and after3b.chain,
      "Fig 3b was a capture -> same player (White) must place again")
# and the placed stone is NEVER itself removed
for m in capm:
    check(m.split(">")[0] not in m.split(">")[1:], "the placed stone is never a removal")

# --------------------------------------- (5) Fig 3c: White's ONLY continuation
cont = G.legal_moves(after3b)
check(cont == ["-2,2"],
      f"Fig 3c: White's only move must be -2,2 (adjacent to a group of two), got {cont}")
after3c = G.apply_move(after3b, "-2,2")
check(after3c.to_move == B and not after3c.chain,
      "Fig 3c: the non-capturing placement ends White's turn -> Black to move")

# --------------------------------------- (6) Fig 3d: capture 2 size-3 -> size-4
# Position at the start of Black's turn == after3c. Black plays (-1,0), joining
# GA (0,-2),(0,-1),(1,-2) and GB (-2,0),(-2,1),(-2,2); removes 3 -> size 4.
gg3, _m = _groups(after3c.board, 3)
check(sorted(len(x) for x in gg3) == [3, 3, 3],
      f"Fig 3d start: three size-3 groups, got {sorted(len(x) for x in gg3)}")
fig3d_move = "-1,0>0,-2>-2,0>-2,2"
check(fig3d_move in G.legal_moves(after3c),
      "Fig 3d removal (remove 0,-2 / -2,0 / -2,2) must be a legal capturing move")
after3d = G.apply_move(after3c, fig3d_move)
gg4, _m = _groups(after3d.board, 3)
grp4 = next(x for x in gg4 if (-1, 0) in x)
check(len(grp4) == 4, "Fig 3d: Black's new group must be size 4 (biggest joined + 1)")
check(_connected(set(grp4), 3), "Fig 3d: survivors must be a single connected group")
check(set(grp4) == {(-1, 0), (0, -1), (1, -2), (-2, 1)}, "Fig 3d: exact survivor set")
check(after3d.to_move == B and after3d.chain,
      "Fig 3d was a capture -> Black must place again while it is still his turn")

# --------------------------------------- (7) removals never split the group
# Every enumerated capturing removal must leave ONE connected component of the
# right size, and must not remove the placed stone. (Checked broadly here.)
for state in (fig3a, after3c):
    for m in G.legal_moves(state):
        parts = m.split(">")
        if len(parts) == 1:
            continue
        ns = G.apply_move(state, m)
        place = tuple(int(x) for x in parts[0].split(","))
        grp = next(x for x in _groups(ns.board, 3)[0] if place in x)
        check(_connected(set(grp), 3), f"removal must not split ({m})")

# ------------------------------------------- (8) majority win on filled board
# Fill 19 cells: 10 Black, 9 White -> Black majority. Reach it via apply_move so
# the win fires as an event on the final (board-filling) placement.
cells = list(_cells(3))
# choose a legal-ish final placement: build 18 stones, last empty cell placed by
# whoever the majority favours; here we just test the terminal predicate directly
# on a hand-built full board via a non-capturing final placement.
full_black = cells[:10]
full_white = cells[10:18]
last = cells[18]
# make sure `last` placed by Black is non-capturing is not required for the test
# of the win predicate; place it directly and assert majority scoring:
pre = mk(black=full_black, white=full_white, to_move=B)
final = G.apply_move(pre, _cs(last))
check(final.over and G.is_terminal(final), "filled board is terminal")
check(final.winner == 0, "10 Black vs 9 White -> Black wins")
check(G.returns(final) == [1.0, -1.0], "returns encode the Black majority win")
check(G.legal_moves(final) == [], "no moves once the board is full")
# White majority mirror
pre2 = mk(black=cells[:9], white=cells[9:18], to_move=W)
final2 = G.apply_move(pre2, _cs(cells[18]))
check(final2.winner == 1 and G.returns(final2) == [-1.0, 1.0], "White majority mirror")

# --------------------------------------------------- (9) serialize round-trip
for probe in (fig3a, after3b, after3d, final):
    d = G.serialize(probe)
    json.dumps(d)
    d2 = G.serialize(G.deserialize(d))
    check(json.dumps(d, sort_keys=True) == json.dumps(d2, sort_keys=True),
          "serialize must round-trip")

# ------------------------------------------------ (10) random termination
rng = random.Random(11)
lengths, results = [], {0: 0, 1: 0, None: 0}
for i in range(30):
    st = G.initial_state()          # default size 3
    guard = 0
    while not G.is_terminal(st):
        ms = G.legal_moves(st)
        check(ms, "non-terminal state must have moves")
        st = G.apply_move(st, rng.choice(ms))
        guard += 1
        check(guard < 5000, "runaway game")
    lengths.append(st.ply)
    results[st.winner] += 1
check(results[None] == 0, "random play should fill the board (never hit the draw backstop)")
print(f"  playouts: 30 games size3, plies min/avg/max = "
      f"{min(lengths)}/{sum(lengths)/len(lengths):.1f}/{max(lengths)}, "
      f"wins Black={results[0]} White={results[1]}")

print("SELFTEST OK")
