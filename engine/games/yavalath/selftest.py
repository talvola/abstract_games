"""Standalone correctness anchor for Yavalath.

Run from the engine dir:  PYTHONPATH=. python3 games/yavalath/selftest.py

There is no published perft for Yavalath; the anchor is a set of baked rule
assertions, played out through ``apply_move`` so "win as event" is exercised:

  (1) hexhex board of side 5 = 61 cells with axial 'q,r' 6-neighbour adjacency;
  (2) placement only (every empty cell is a legal move, plus the optional swap);
  (3) making FOUR-or-more in a row of your colour is an immediate WIN;
  (4) making EXACTLY THREE in a row (not part of a four) is an immediate LOSS
      (the misère twist);
  (5) FOUR-takes-precedence: a move making both a 3 and a 4 is a WIN;
  (6) a full board with no decision is a draw;
  (7) the three hex axes are the line directions; off-axis triples don't trip;
  (8) the pie/swap rule;
  (9) serialize round-trips.

Pure stdlib: imports only ``agp`` and this game. Fast (no game loops besides a
short conformance sample). Prints "SELFTEST OK" and exits 0 on success.
"""

from __future__ import annotations

import json
import os
import sys

from games.yavalath.game import (
    Yavalath, YavalathState, WHITE, BLACK,
    _cells, _cell_set, _neighbors, _max_run, AXES, SIDE,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def play(g, moves, side=SIDE, pie=False):
    """Apply a sequence of move strings from a fresh state; return final state."""
    s = g.initial_state(options={"size": side, "pie": pie})
    for mv in moves:
        if g.is_terminal(s):
            fail(f"game ended before applying {mv!r}")
        s = g.apply_move(s, mv)
    return s


def main():
    g = Yavalath()

    # ---- (1) board geometry: side 5 = 61 cells, axial adjacency -----------
    cells = _cells(SIDE)
    if SIDE != 5:
        fail(f"expected side 5, got {SIDE}")
    if len(cells) != 61:
        fail(f"expected 61 cells for a side-5 hexhex, got {len(cells)}")
    # 3*n^2 - 3*n + 1 for n cells-per-side
    if len(cells) != 3 * 5 * 5 - 3 * 5 + 1:
        fail("cell count disagrees with hexhex formula")
    onboard = _cell_set(SIDE)
    # center has 6 neighbours, all on board
    nbrs = _neighbors(0, 0)
    if len(nbrs) != 6 or any(c not in onboard for c in nbrs):
        fail(f"centre should have 6 on-board neighbours, got {nbrs}")
    # a corner (4,0) has only 3 on-board neighbours
    corner_nbrs = [c for c in _neighbors(4, 0) if c in onboard]
    if len(corner_nbrs) != 3:
        fail(f"corner (4,0) should have 3 on-board neighbours, got {corner_nbrs}")
    # exactly 3 line axes
    if len(AXES) != 3:
        fail(f"expected 3 hex axes, got {AXES}")

    # ---- (2) placement only: legal moves = empty cells (+ no swap, pie off)
    s0 = g.initial_state(options={"pie": False})
    if len(g.legal_moves(s0)) != 61:
        fail(f"opening should have 61 legal placements, got {len(g.legal_moves(s0))}")
    if "swap" in g.legal_moves(s0):
        fail("swap offered with pie off")

    # ---- (3) FOUR-in-a-row WINS -------------------------------------------
    # White builds a row of 4 along the q axis. We must NOT pass through an
    # exactly-3 state mid-build (that would lose first), so we fill the run with
    # a GAP and close it: (0,0),(1,0),(3,0) [no 3 yet: gap at 2,0], then (2,0)
    # completes the four. Black plays harmless off-axis cells far away.
    line4 = [(0, 0), (1, 0), (3, 0), (2, 0)]
    # Scattered Black cells that never form three-in-a-row on any axis.
    blacks = [(-4, 0), (-2, 3), (-4, 4)]
    moves = []
    for i, wc in enumerate(line4):
        moves.append(f"{wc[0]},{wc[1]}")
        if i < len(blacks):
            moves.append(f"{blacks[i][0]},{blacks[i][1]}")
    s = play(g, moves)
    if s.winner != WHITE:
        fail(f"four-in-a-row should win for White, winner={s.winner}")
    if g.returns(s) != [1.0, -1.0]:
        fail(f"returns for White win wrong: {g.returns(s)}")
    # The winning placement (2,0) closed the gap -> run >= 4
    if _max_run(s.board, (2, 0), WHITE) < 4:
        fail("max_run did not see the four")

    # ---- (4) EXACTLY THREE LOSES (misère twist) ---------------------------
    # White makes three in a row (0,0),(1,0),(2,0) and no four -> White LOSES,
    # so Black (seat 1) is the winner.
    line3 = [(0, 0), (1, 0), (2, 0)]
    blacks3 = [(-4, 0), (-4, 1)]  # harmless
    moves = []
    for i, wc in enumerate(line3):
        moves.append(f"{wc[0]},{wc[1]}")
        if i < len(blacks3):
            moves.append(f"{blacks3[i][0]},{blacks3[i][1]}")
    s = play(g, moves)  # ends on White's 3rd stone
    if s.winner != BLACK:
        fail(f"three-in-a-row should LOSE for White (Black wins), winner={s.winner}")
    if g.returns(s) != [-1.0, 1.0]:
        fail(f"returns for White's losing three wrong: {g.returns(s)}")
    if _max_run(s.board, (2, 0), WHITE) != 3:
        fail("losing position should have a run of exactly 3")

    # A three on a DIFFERENT axis (r axis) also loses.
    line3r = [(0, 0), (0, 1), (0, 2)]
    moves = []
    for i, wc in enumerate(line3r):
        moves.append(f"{wc[0]},{wc[1]}")
        if i < len(blacks3):
            moves.append(f"{blacks3[i][0]},{blacks3[i][1]}")
    s = play(g, moves)
    if s.winner != BLACK:
        fail(f"three on r-axis should lose for White, winner={s.winner}")

    # ---- (5) FOUR TAKES PRECEDENCE ----------------------------------------
    # White holds (0,0),(1,0),(3,0); a 3-run already? No: (0,0),(1,0) is a 2-run
    # and (3,0) is isolated. Filling (2,0) makes (0,0),(1,0),(2,0),(3,0) = FOUR
    # in one shot, which contains a sub-run of three -> must be a WIN, not loss.
    # Order moves so the gap (2,0) is the LAST White move.
    # White: (0,0),(1,0),(3,0),(2,0) ; Black harmless between.
    whites = [(0, 0), (1, 0), (3, 0), (2, 0)]
    blacksP = [(-4, 0), (-2, 3), (-4, 4)]
    moves = []
    for i, wc in enumerate(whites):
        moves.append(f"{wc[0]},{wc[1]}")
        if i < len(blacksP):
            moves.append(f"{blacksP[i][0]},{blacksP[i][1]}")
    s = play(g, moves)
    if s.winner != WHITE:
        fail(f"simultaneous 3-and-4 must be a WIN for White, winner={s.winner}")
    # Sanity: before the gap fill, White had no losing three.
    # Reconstruct the pre-gap board: whites[:3] placed.
    pre = {(0, 0): WHITE, (1, 0): WHITE, (3, 0): WHITE}
    if _max_run(pre, (3, 0), WHITE) >= 3:
        fail("pre-gap White should not yet have a 3-run")
    # After the gap, run through (2,0) is >= 4.
    if _max_run(s.board, (2, 0), WHITE) < 4:
        fail("gap-fill should produce a run of >= 4")

    # ---- (7) off-axis triple does NOT count -------------------------------
    # Three White stones that form a small triangle (NOT collinear on any axis):
    # (0,0), (1,0), (0,1). Pairwise adjacent but not a straight line.
    tri = {(0, 0): WHITE, (1, 0): WHITE, (0, 1): WHITE}
    for c in tri:
        if _max_run(tri, c, WHITE) >= 3:
            fail(f"triangle cell {c} wrongly read as a 3-in-a-row run")

    # ---- (6) full board can be a draw -------------------------------------
    # We don't fill 61 cells by hand; instead assert the draw plumbing: a state
    # with a full board and no winner is terminal and scores [0,0].
    full = {c: (i % 2) for i, c in enumerate(_cells(SIDE))}
    sdraw = YavalathState(side=SIDE, board=full, to_move=WHITE, winner=None,
                          last=None, ply=61, pie=False)
    if not g.is_terminal(sdraw):
        fail("full board should be terminal")
    if g.returns(sdraw) != [0.0, 0.0]:
        fail(f"full-board no-winner should score a draw, got {g.returns(sdraw)}")
    if g.legal_moves(sdraw) != []:
        fail("terminal state should have no legal moves")

    # ---- (8) pie / swap ---------------------------------------------------
    sp = g.initial_state(options={"pie": True})
    sp = g.apply_move(sp, "0,0")  # White opens
    if "swap" not in g.legal_moves(sp):
        fail("swap not offered to second player with pie on")
    after = g.apply_move(sp, "swap")
    if after.board.get((0, 0)) != BLACK:
        fail(f"after swap the opening stone should be Black, got {after.board}")
    if after.to_move != WHITE:
        fail("after swap it should be White to move")
    # swap not offered later
    later = g.apply_move(after, "1,0")
    if "swap" in g.legal_moves(later):
        fail("swap offered after the second player's first move")

    # ---- (9) serialize round-trip -----------------------------------------
    rt = g.deserialize(g.serialize(s))
    if g.serialize(rt) != g.serialize(s):
        fail("serialize round-trip mismatch")

    # ---- conformance (a placement game; sample a few random games) --------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check_conformance(g, manifest, games=6, seed=1)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
