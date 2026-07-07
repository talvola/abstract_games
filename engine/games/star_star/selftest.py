"""Standalone correctness anchor for *Star.

Run from the engine dir:  PYTHONPATH=. python3 games/star_star/selftest.py

There is no published perft for *Star; the anchor is a set of rule asserts taken
from the official Kadon *STAR rulebook (https://gamepuzzles.com/starbook-final.pdf,
pp.4-5 scoring + pp.14-15/20 board) and Wikipedia ("*Star"), PLUS the game's own
built-in correctness theorem verified empirically:

  (a) BOARD  -- 275 cells; 50 EDGE cells (ring 10) and 5 CORNER cells (ring 10,
      offset 0); corners have exactly 3 neighbours; the bridge links the five
      ring-1 cells to each other yet is not itself a playable cell.
  (b) STAR   -- a group needs >= 2 edge cells to be a star; a lone corner stone
      is NOT a star and owns nothing.
  (c) SURROUND -- a star owns an edge cell it does not occupy but encloses.
  (d) CORNER bonus -- owning >= 3 of the 5 corners gives +1.
  (e) AWARD  -- the player with FEWER stars gets +2*(difference), the other -2*.
  (f) INVARIANT (the crux) -- on MANY random FULL boards the two scores sum to
      exactly 51 (= 50 edge cells + 1), always odd => *Star is DRAWLESS.
  (g) DOUBLE *Star -- two stones per turn, but only ONE on White's first move.
  (h) conformance (random self-play terminates) + serialize round-trip.

Pure stdlib: imports only `agp` + this game.  Fast.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import os
import random
import sys

from games.star_star.game import (
    StarStar, StarStarState, WHITE, BLACK,
    _cells, _cell_set, _adj, _edge_cells, _corner_cells,
    _groups, _analyze, _score, _str,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def main():
    g = StarStar()

    # ---- (a) board geometry ----------------------------------------------
    cells = list(_cells())
    if len(cells) != 275:
        fail(f"expected 275 cells, got {len(cells)}")
    edges = _edge_cells()
    if len(edges) != 50:
        fail(f"expected 50 edge cells, got {len(edges)}")
    corners = _corner_cells()
    if len(corners) != 5:
        fail(f"expected 5 corner cells, got {len(corners)}")
    if not (corners <= edges):
        fail("every corner must also be an edge cell")
    adj = _adj()
    # symmetry
    for c in cells:
        for nb in adj[c]:
            if c not in adj[nb]:
                fail(f"adjacency not symmetric: {c}~{nb}")
    # corners have exactly 3 neighbours (star tips)
    for c in corners:
        if len(adj[c]) != 3:
            fail(f"corner {c} should have 3 neighbours, got {len(adj[c])}")
    # bridge: the five ring-1 cells are mutually adjacent
    ring1 = [(s, 1, 0) for s in range(5)]
    for i in range(5):
        for j in range(i + 1, 5):
            if ring1[j] not in adj[ring1[i]]:
                fail("the five ring-1 cells must all be linked by the bridge")
    # connected
    start = cells[0]
    seen = {start}
    stack = [start]
    while stack:
        x = stack.pop()
        for nb in adj[x]:
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    if len(seen) != len(cells):
        fail("board is not connected")

    # opening: every cell is a legal placement (no bridge cell exists) + pass
    s0 = g.initial_state()
    lm = g.legal_moves(s0)
    placements = [m for m in lm if m != "pass"]
    if len(placements) != 275:
        fail(f"opening should offer 275 placements, got {len(placements)}")
    if "pass" not in lm:
        fail("pass must be legal")
    s1 = g.apply_move(s0, _str((0, 5, 2)))
    if s1.board.get((0, 5, 2)) != WHITE or s1.to_move != BLACK:
        fail("first placement bookkeeping wrong (White moves first, single stone)")

    # ---- (b) STAR requires >= 2 edge cells --------------------------------
    corner = (0, 10, 0)
    info = _analyze({corner: WHITE})
    if info["star_count"][WHITE] != 0:
        fail("a lone corner stone must NOT be a star")
    if info["edge_pts"][WHITE] != 0:
        fail("a lone corner stone (not a star) owns nothing")
    # two adjacent edge stones form a star owning >= 2 edge cells
    e_a, e_b = (0, 10, 1), (0, 10, 2)
    if e_b not in adj[e_a]:
        fail("test edge cells must be adjacent")
    info = _analyze({e_a: WHITE, e_b: WHITE})
    if info["star_count"][WHITE] != 1:
        fail("two adjacent edge stones must be one star")
    if info["edge_pts"][WHITE] < 2:
        fail("a star must own at least its two edge cells")

    # ---- (c) SURROUND: own an edge cell you do not occupy -----------------
    # e1 empty, walled by a Black star touching e0 and e2 and behind e1.
    e0, e1, e2 = (0, 10, 1), (0, 10, 2), (0, 10, 3)
    behind = [(0, 9, 1), (0, 9, 2)]
    # e1's neighbours are exactly {e0, e2, (0,9,1), (0,9,2)}
    if set(adj[e1]) != {e0, e2, behind[0], behind[1]}:
        fail(f"unexpected neighbours for surround test: {sorted(adj[e1])}")
    board = {e0: BLACK, e2: BLACK, behind[0]: BLACK, behind[1]: BLACK}
    info = _analyze(board)
    if e1 in board:
        fail("surround test: e1 must be empty")
    if info["edge_owner"][e1] != BLACK:
        fail(f"Black must SURROUND (own) the empty edge cell e1, got {info['edge_owner'][e1]}")

    # ---- (d) CORNER bonus (>= 3 corners => +1) ----------------------------
    board = {}
    for i in range(3):                       # make 3 corners into 2-edge stars
        board[(i, 10, 0)] = WHITE
        board[(i, 10, 1)] = WHITE
    info = _analyze(board)
    if info["corner_own"][WHITE] < 3:
        fail(f"White should own >= 3 corners, got {info['corner_own'][WHITE]}")
    # White score includes the +1 corner bonus (edge pts + 1 - award)
    # (award: White has 3 stars, Black 0 -> Black gets +6, White -6)
    if info["score"][WHITE] != info["edge_pts"][WHITE] + 1 - 6:
        fail("corner bonus / award not applied as expected")

    # ---- (e) AWARD favours FEWER stars ------------------------------------
    board = {
        (0, 10, 1): WHITE, (0, 10, 2): WHITE,           # White: 1 star
        (2, 10, 1): BLACK, (2, 10, 2): BLACK,           # Black: star A
        (3, 10, 5): BLACK, (3, 10, 6): BLACK,           # Black: star B
    }
    info = _analyze(board)
    if info["star_count"] != {WHITE: 1, BLACK: 2}:
        fail(f"star-count setup wrong: {info['star_count']}")
    base_w = info["edge_pts"][WHITE] + (1 if info["corner_own"][WHITE] >= 3 else 0)
    base_b = info["edge_pts"][BLACK] + (1 if info["corner_own"][BLACK] >= 3 else 0)
    # diff 1 -> White (fewer) +2, Black -2
    if info["score"][WHITE] != base_w + 2 or info["score"][BLACK] != base_b - 2:
        fail(f"award wrong: score={info['score']} base_w={base_w} base_b={base_b}")

    # ---- (f) THE COMBINED-SCORE INVARIANT (drawless) ----------------------
    rng = random.Random(12345)
    for _ in range(1500):
        board = {c: rng.randint(0, 1) for c in cells}   # full board
        sc = _score(board)
        combined = sc[WHITE] + sc[BLACK]
        if combined != 51:
            info = _analyze(board)
            unowned = [e for e in edges if info["edge_owner"][e] is None]
            fail(f"combined score must be 51 on a full board, got {combined} "
                 f"(unowned peris: {len(unowned)})")
        if combined % 2 == 0:
            fail("combined score must be odd (drawless)")
        if sc[WHITE] == sc[BLACK]:
            fail("full-board scores must never tie")

    # ---- (g) DOUBLE *Star: 2 stones/turn, 1 on the first move -------------
    d0 = g.initial_state({"stones_per_turn": 2})
    if d0.per_turn != 2 or d0.moves_left != 1:
        fail("Double *Star: White's first turn must place only ONE stone")
    d1 = g.apply_move(d0, _str((0, 5, 2)))   # White's single first stone
    if d1.to_move != BLACK:
        fail("Double *Star: after White's one-stone first move it is Black's turn")
    if d1.moves_left != 2:
        fail("Double *Star: Black should now have TWO stones to place")
    d2 = g.apply_move(d1, _str((1, 5, 2)))   # Black stone 1 of 2
    if d2.to_move != BLACK or d2.moves_left != 1:
        fail("Double *Star: Black keeps the move for the second stone")
    d3 = g.apply_move(d2, _str((2, 5, 2)))   # Black stone 2 of 2
    if d3.to_move != WHITE or d3.moves_left != 2:
        fail("Double *Star: after two Black stones it is White's turn with 2 stones")
    # single-*Star always places one stone per turn
    a = g.apply_move(g.initial_state({"stones_per_turn": 1}), _str((0, 5, 2)))
    if a.to_move != BLACK or a.moves_left != 1:
        fail("*Star: exactly one stone per turn")

    # ---- (h) conformance + serialize round-trip ---------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check_conformance(g, manifest, games=3, seed=2)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    st = g.apply_move(g.apply_move(g.initial_state({"stones_per_turn": 2}),
                                   _str((0, 10, 0))), _str((1, 6, 3)))
    rt = g.deserialize(json.loads(json.dumps(g.serialize(st))))
    if (rt.board != st.board or rt.to_move != st.to_move
            or rt.per_turn != st.per_turn or rt.moves_left != st.moves_left):
        fail("serialize round-trip mismatch")

    # double-pass ends the game and yields a winner (drawless default)
    s = StarStarState(board={(0, 10, 1): WHITE, (0, 10, 2): WHITE}, to_move=BLACK, ply=20)
    s = g.apply_move(s, "pass")
    s = g.apply_move(s, "pass")
    if not g.is_terminal(s):
        fail("two successive passes must end the game")
    if s.winner is None:
        fail("*Star is drawless: a finished game must have a winner")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
