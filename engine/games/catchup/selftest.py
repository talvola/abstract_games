"""Standalone correctness anchor for Catchup (Nick Bentley, 2010).

Run from the engine dir:  PYTHONPATH=. python3 games/catchup/selftest.py

There is no published perft for Catchup, so the anchor is a set of baked rule
assertions plus a few hand-built positions:

  (1) hex-of-hexes board, side 5 -> 61 cells, with correct axial 6-adjacency;
  (2) a turn places 1, 2, or 3 stones of your own colour on empty cells, with
      the catch-up rule governing the cap;
  (3) the FIRST move of the game places exactly ONE stone;
  (4) when the board is full, score = size of each player's LARGEST connected
      group, tie-broken by 2nd-largest, 3rd, ... ; most wins;
  (5) the catch-up placement-count rule (you may place up to 3 only when the
      opponent just increased their score to >= yours) on concrete positions;
  (6) light conformance (purity / round-trip / termination).

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import os
import sys

from games.catchup.game import (
    Catchup, CatchupState, P0, P1,
    _cells, _neighbors, _group_sizes, _score, _compare,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def main():
    g = Catchup()

    # ---- (1) board geometry ----------------------------------------------
    cells = _cells(5)
    if len(cells) != 61:
        fail(f"side-5 hexhex should have 61 cells, got {len(cells)}")
    cset = set(cells)
    # centre has all 6 neighbours on board
    if sum(1 for nb in _neighbors(0, 0) if nb in cset) != 6:
        fail("centre cell should have 6 on-board neighbours")
    # a corner cell (4,0) has only 3 on-board neighbours
    if sum(1 for nb in _neighbors(4, 0) if nb in cset) != 3:
        fail("corner (4,0) should have 3 on-board neighbours")
    # every cell satisfies max(|q|,|r|,|s|)<=4
    for (q, r) in cells:
        if max(abs(q), abs(r), abs(-q - r)) > 4:
            fail(f"cell {(q, r)} should not be on a side-5 board")

    # ---- (4) group-size scoring & tie-break ------------------------------
    # Black: an L of 3 connected + a lone stone -> sizes [3,1]
    board = {
        (0, 0): P0, (1, 0): P0, (1, -1): P0,   # connected triomino
        (-3, 0): P0,                            # lone
        (-1, 1): P1, (-1, 2): P1,               # white pair
    }
    if _group_sizes(board, P0) != [3, 1]:
        fail(f"black group sizes wrong: {_group_sizes(board, P0)}")
    if _group_sizes(board, P1) != [2]:
        fail(f"white group sizes wrong: {_group_sizes(board, P1)}")
    if _score(board, P0) != 3 or _score(board, P1) != 2:
        fail("largest-group score wrong")
    # adjacency really connects (1,0) & (1,-1): they are hex-neighbours
    if (1, -1) not in _neighbors(1, 0):
        fail("(1,0) and (1,-1) should be adjacent")

    # tie-break: equal largest, decide on second-largest
    if _compare([4, 3, 1], [4, 2, 2]) != 1:
        fail("tie-break by 2nd-largest failed (4,3 > 4,2)")
    if _compare([4, 2], [4, 2, 1]) != -1:
        fail("tie-break by group count failed (more groups wins when prefix equal)")
    if _compare([5], [4, 4, 4]) != 1:
        fail("largest group should win outright")

    # ---- (3) first move places exactly one stone -------------------------
    s = g.initial_state()
    lm = g.legal_moves(s)
    if any(">" in m for m in lm):
        fail("first move offered a multi-stone placement")
    if len(lm) != 61:
        fail(f"first move should have 61 single-cell options, got {len(lm)}")
    s1 = g.apply_move(s, "0,0")
    if s1.board != {(0, 0): P0} or s1.to_move != P1:
        fail("after first move: one black stone, white to move")
    try:
        g.apply_move(s, "0,0>1,-1")
        fail("first move accepted two stones")
    except ValueError:
        pass

    # ---- (2)/(5) catch-up placement-count rule ---------------------------
    # After the first (1-stone) move, the cap depends on the rule.
    # White to move on s1: Black's score went 0->1 this past turn (increased),
    # and Black's score (1) >= White's score (0). So White MAY place up to 3.
    if g._max_place(s1) != 3:
        fail("white should be allowed up to 3 after black opened (caught up)")
    counts = {len(m.split(">")) for m in g.legal_moves(s1)}
    if counts != {1, 2, 3}:
        fail(f"white should be able to place 1,2,or 3; got counts {counts}")

    # Normal case: place stones that do NOT increase the mover's score, so the
    # opponent is capped at 2.
    # Black opens 0,0 (score 1). White plays two SEPARATE stones far apart so
    # White's largest group is 1 (white score 1, increased 0->1). Now it's
    # Black's turn: white increased AND white score(1) >= black score(1) -> 3.
    sB = g.apply_move(s1, "3,0>-3,0")  # two disconnected white stones, score 1
    if _score(sB.board, P1) != 1:
        fail("white score should be 1 (two disconnected stones)")
    if g._max_place(sB) != 3:
        fail("black should be allowed 3 (white tied black's score by increasing)")

    # Now make a move where the mover does NOT increase their score: a player
    # places a single stone disconnected from their others -> score unchanged
    # if they already had a bigger group.
    # Build: black has a group of size 2 already, then plays a lone stone.
    board2 = {(0, 0): P0, (1, 0): P0}  # black pair, score 2
    sC = CatchupState(size=5, board=dict(board2), to_move=P0, ply=4, allow3=True)
    # Black plays a lone stone far away: score stays 2 (no increase).
    sD = g.apply_move(sC, "-3, 0".replace(" ", ""))
    if _score(sD.board, P0) != 2:
        fail("black score should remain 2 after a non-growing lone stone")
    # White's cap: black did NOT increase -> white capped at 2.
    if g._max_place(sD) != 2:
        fail("white should be capped at 2 when opponent did not increase score")

    # Increase-but-not-ahead case: opponent increased their score but is still
    # strictly behind -> NO extra stone.
    # White has score 1; black has score 3. White grows to 2 (increase) but
    # 2 < 3, so black is NOT granted 3.
    board3 = {(0, 0): P0, (1, 0): P0, (1, -1): P0,  # black score 3
              (-3, 0): P1}                            # white score 1
    sE = CatchupState(size=5, board=dict(board3), to_move=P1, ply=8, allow3=False)
    sF = g.apply_move(sE, "-3,1")  # white extends to (-3,0)-(-3,1): score 2
    if _score(sF.board, P1) != 2:
        fail("white score should be 2 after extending")
    if g._max_place(sF) != 2:
        fail("black should NOT get 3 when opponent increased but is still behind")

    # ---- a full small play-out to confirm a winner & no draw -------------
    # Force a full board via random-ish legal play and check returns are +/-1.
    import random
    rng = random.Random(7)
    st = g.initial_state()
    guard = 0
    while not g.is_terminal(st) and guard < 200:
        guard += 1
        moves = g.legal_moves(st)
        st = g.apply_move(st, rng.choice(moves))
    if not g.is_terminal(st):
        fail("game did not terminate within ply guard")
    if len(st.board) != 61:
        fail(f"terminal board not full: {len(st.board)} stones")
    ret = g.returns(st)
    if sorted(ret) != [-1.0, 1.0]:
        fail(f"Catchup must not draw; returns were {ret}")
    # winner agrees with group-size comparison
    cmp = _compare(_group_sizes(st.board, P0), _group_sizes(st.board, P1))
    if (ret[0] > ret[1]) != (cmp > 0):
        fail("returns disagree with group-size comparison")

    # ---- serialize round-trip --------------------------------------------
    rt = g.deserialize(g.serialize(sF))
    if g.serialize(rt) != g.serialize(sF):
        fail("serialize round-trip mismatch")

    # ---- (6) light conformance -------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check_conformance(g, manifest, games=2, seed=1)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
