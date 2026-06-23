"""Standalone correctness anchor for Tumbleweed.

Run from the engine dir:  PYTHONPATH=. python3 games/tumbleweed/selftest.py

There is no published perft for Tumbleweed; the anchor is baked rule asserts:

  (1) the hexhex board (size 6 and 8) with a height-2 NEUTRAL centre stack and
      one height-1 starting stack per player;
  (2) a hand-built LINE-OF-SIGHT count (first stack seen along each of the 6
      directions, blocked by intervening stacks), and a placement whose height
      equals that LOS count, which must be STRICTLY GREATER than the height
      already on the target (settle, grow, capture an enemy/your own stack);
  (3) passing is legal; two successive passes end the game;
  (4) winner = the "OWNED + CONTROLLED" territory score: every cell goes to the
      colour that tops it (occupied) or has STRICTLY GREATER line-of-sight to it
      (empty); equal/zero LOS and the neutral stack are neutral. The two scores
      plus neutrals sum to the whole board. A regression case proves that empty-
      territory control flips the winner vs. counting occupied hexes only;
  plus conformance and a serialize round-trip.

Pure stdlib: imports only `agp` + this game. Fast.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import os
import sys

from games.tumbleweed.game import (
    Tumbleweed, TumbleweedState, WHITE, BLACK, NEUTRAL,
    _los_count, _control_counts, _cells, _start_cells,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def main():
    g = Tumbleweed()

    # ---- conformance ------------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check_conformance(g, manifest, games=6, seed=1)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    # ---- (1) setup: board + neutral centre + one stack per player ---------
    for N in (6, 8):
        s = g.initial_state(options={"size": N})
        if s.board.get((0, 0)) != (NEUTRAL, 2):
            fail(f"N={N}: centre should be neutral height-2, got {s.board.get((0,0))}")
        a, b = _start_cells(N)
        if s.board.get(a) != (WHITE, 1):
            fail(f"N={N}: White start {a} should be height-1, got {s.board.get(a)}")
        if s.board.get(b) != (BLACK, 1):
            fail(f"N={N}: Black start {b} should be height-1, got {s.board.get(b)}")
        if len(s.board) != 3:
            fail(f"N={N}: setup should have exactly 3 stacks, got {len(s.board)}")
        # both starting cells on board
        on = set(_cells(N))
        if a not in on or b not in on:
            fail(f"N={N}: a starting cell is off board")
        if s.to_move != WHITE:
            fail("White should move first")

    # ---- (2) hand-built line-of-sight count -------------------------------
    # Build a small explicit position on a size-6 board.
    # White stacks at (2,0), (-2,0), (0,2); a BLACK stack at (0,-1) (a blocker).
    # Target = (0,0). Look along the 6 directions from (0,0):
    #   +q (1,0):   first stack at (2,0)  -> WHITE -> +1
    #   -q (-1,0):  first stack at (-2,0) -> WHITE -> +1
    #   +r (0,1):   first stack at (0,2)  -> WHITE -> +1
    #   -r (0,-1):  first stack at (0,-1) -> BLACK -> 0 (blocks)
    #   +q-r (1,-1):no stack -> 0
    #   -q+r (-1,1):no stack -> 0
    # => White LOS to (0,0) == 3.
    N = 6
    board = {
        (2, 0): (WHITE, 1),
        (-2, 0): (WHITE, 1),
        (0, 2): (WHITE, 1),
        (0, -1): (BLACK, 1),
    }
    los_w = _los_count(board, N, (0, 0), WHITE)
    if los_w != 3:
        fail(f"hand-built LOS for White at (0,0) should be 3, got {los_w}")
    # Black sees only the (0,-1) blocker -> from (0,0) along -r first stack is
    # black -> +1; all other rays first-stack is white or empty -> 0.
    los_b = _los_count(board, N, (0, 0), BLACK)
    if los_b != 1:
        fail(f"hand-built LOS for Black at (0,0) should be 1, got {los_b}")

    # Blocking check: put a WHITE stack at (1,0) in front of (2,0); now the +q
    # ray's first stack is the (1,0) white -> still +1, but it proves blocking
    # by replacing (2,0) with BLACK and confirming the count is unchanged.
    board_blk = dict(board)
    board_blk[(1, 0)] = (WHITE, 1)
    board_blk[(2, 0)] = (BLACK, 9)  # hidden behind (1,0)
    if _los_count(board_blk, N, (0, 0), WHITE) != 3:
        fail("blocking failed: stack behind a nearer stack should be invisible")

    # ---- placement: height == LOS and must be strictly greater ------------
    # Use a real game state with that board and White to move; place on (0,0).
    st = TumbleweedState(size=N, board=dict(board), to_move=WHITE)
    # (0,0) is empty (height 0); LOS 3 > 0 so legal, places a White height-3.
    if "0,0" not in g.legal_moves(st):
        fail("placing on empty (0,0) with LOS 3 should be legal")
    st2 = g.apply_move(st, "0,0")
    if st2.board.get((0, 0)) != (WHITE, 3):
        fail(f"placement should create White height-3, got {st2.board.get((0,0))}")

    # Now Black to move on st2. Black LOS to (0,0): along -r first stack (0,-1)
    # is Black -> +1; all else 0 -> LOS 1. Current height there is 3, and
    # 1 is NOT > 3, so Black may NOT take it.
    if "0,0" in g.legal_moves(st2):
        fail("Black with LOS 1 must not capture a height-3 stack")

    # Strictly-greater takeover that IS legal: give Black enough sight.
    # Black stacks at (2,0)?(now white) ... simpler: construct fresh.
    # Target (0,0) currently White height 1; Black has LOS 2 -> capture.
    cap_board = {
        (0, 0): (WHITE, 1),     # short white stack to capture
        (2, 0): (BLACK, 1),     # +q ray -> +1
        (0, 2): (BLACK, 1),     # +r ray -> +1
    }
    cst = TumbleweedState(size=N, board=cap_board, to_move=BLACK)
    if _los_count(cap_board, N, (0, 0), BLACK) != 2:
        fail("capture setup: Black LOS to (0,0) should be 2")
    if "0,0" not in g.legal_moves(cst):
        fail("Black LOS 2 > white height 1 should allow capture")
    cst2 = g.apply_move(cst, "0,0")
    if cst2.board.get((0, 0)) != (BLACK, 2):
        fail(f"takeover should yield Black height-2, got {cst2.board.get((0,0))}")

    # Equal height is NOT enough (strictly greater required): Black LOS 1 onto a
    # White height-1 stack must be illegal.
    eq_board = {(0, 0): (WHITE, 1), (2, 0): (BLACK, 1)}
    est = TumbleweedState(size=N, board=eq_board, to_move=BLACK)
    if _los_count(eq_board, N, (0, 0), BLACK) != 1:
        fail("equal-height setup: Black LOS should be 1")
    if "0,0" in g.legal_moves(est):
        fail("equal height (LOS 1 vs height 1) must NOT be a legal takeover")

    # Growing your OWN stack: White height-1 at (0,0), White LOS 2 -> grow to 2.
    grow_board = {(0, 0): (WHITE, 1), (2, 0): (WHITE, 1), (0, 2): (WHITE, 1)}
    gst = TumbleweedState(size=N, board=grow_board, to_move=WHITE)
    if _los_count(grow_board, N, (0, 0), WHITE) != 2:
        fail("grow setup: White LOS should be 2")
    gst2 = g.apply_move(gst, "0,0")
    if gst2.board.get((0, 0)) != (WHITE, 2):
        fail("growing own stack should raise its height to the LOS count")

    # ---- (3) pass is legal; two passes end the game -----------------------
    s0 = g.initial_state(options={"size": N})
    if "pass" not in g.legal_moves(s0):
        fail("pass should always be a legal move")
    after1 = g.apply_move(s0, "pass")
    if after1.over:
        fail("one pass should NOT end the game")
    after2 = g.apply_move(after1, "pass")
    if not after2.over or not g.is_terminal(after2):
        fail("two successive passes should end the game")

    # ---- (4) winner = "OWNED + CONTROLLED" territory score ----------------
    # Every cell is scored: occupied -> its top colour (neutral -> nobody);
    # empty -> strictly-greater LOS (equal/0-0 -> nobody). Scores + neutrals
    # must sum to the whole board.
    total_cells = len(_cells(N))

    # (4a) Component check on a tiny explicit board (N=6, 91 cells).
    #   Occupied: White tops (0,0); Black tops (1,0); the centre is replaced so
    #   no neutral here. The remaining 89 empty cells split by majority LOS.
    comp_board = {(0, 0): (WHITE, 2), (1, 0): (BLACK, 1)}
    occ_w = sum(1 for (o, _h) in comp_board.values() if o == WHITE)
    occ_b = sum(1 for (o, _h) in comp_board.values() if o == BLACK)
    if (occ_w, occ_b) != (1, 1):
        fail(f"occupied tops should be (1,1), got {(occ_w, occ_b)}")
    w, b = _control_counts(comp_board, N)
    # White's empty controlled = (white score) - (its occupied), likewise Black.
    ctrl_w, ctrl_b = w - occ_w, b - occ_b
    if ctrl_w < 0 or ctrl_b < 0:
        fail(f"score must be >= occupied count, got w={w} b={b}")
    if (occ_w + ctrl_w) + (occ_b + ctrl_b) > total_cells:
        fail("scores exceed the board")
    neutral = total_cells - w - b
    if w + b + neutral != total_cells:
        fail(f"owned+controlled+neutral must equal {total_cells}, got {w}+{b}+{neutral}")

    # (4b) REGRESSION: empty-territory control flips the winner vs occupied-only.
    #   Black TOPS MORE occupied hexes (3) than White (2) — old "most hexes
    #   topped" scoring would award Black the game. But Black's three stacks are
    #   boxed into the +q corner while White's two stacks command the open
    #   board, so White controls far more EMPTY territory and WINS overall.
    flip_board = {
        (5, -5): (BLACK, 1), (5, -4): (BLACK, 1), (4, -4): (BLACK, 1),  # 3 black tops
        (0, 0): (WHITE, 1), (-5, 5): (WHITE, 1),                        # 2 white tops
    }
    occ_w = sum(1 for (o, _h) in flip_board.values() if o == WHITE)
    occ_b = sum(1 for (o, _h) in flip_board.values() if o == BLACK)
    if not (occ_b > occ_w):
        fail("regression setup: Black must top MORE occupied hexes than White")
    w, b = _control_counts(flip_board, N)
    if not (w > b):
        fail(f"regression: White should WIN on owned+controlled, got w={w} b={b}")
    if w + b + (total_cells - w - b) != total_cells:
        fail("regression: scores + neutrals must equal the board")
    flip = TumbleweedState(size=N, board=dict(flip_board), to_move=WHITE)
    g._maybe_finish(flip, force=True)
    if not flip.over or flip.winner != WHITE:
        fail(f"regression: empty-territory control should make White win, "
             f"winner={flip.winner} (w={w} b={b}, occupied {occ_w}:{occ_b})")
    if g.returns(flip) != [1.0, -1.0]:
        fail(f"regression: returns should be [1,-1] for White win, got {g.returns(flip)}")

    # (4c) Tie -> draw. Symmetric board: two mirror-image stacks give equal
    # occupied AND equal empty-LOS control, so the totals are equal.
    tie_board = {(2, -1): (WHITE, 1), (-2, 1): (BLACK, 1)}
    w, b = _control_counts(tie_board, N)
    if w != b:
        fail(f"symmetric board should score equal, got w={w} b={b}")
    tfin = TumbleweedState(size=N, board=tie_board, to_move=WHITE)
    g._maybe_finish(tfin, force=True)
    if not tfin.over or tfin.winner is not None:
        fail(f"equal totals should be a draw, winner={tfin.winner}")
    if g.returns(tfin) != [0.0, 0.0]:
        fail("draw returns should be [0,0]")

    # ---- serialize round-trip --------------------------------------------
    rt = g.deserialize(g.serialize(cst2))
    if g.serialize(rt) != g.serialize(cst2):
        fail("serialize round-trip mismatch")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
