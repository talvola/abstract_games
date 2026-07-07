"""Standalone correctness anchor for Superstar.

Run from the engine dir:  PYTHONPATH=. python3 games/superstar/selftest.py

There is no published perft for Superstar; the anchor is a set of baked rule
asserts derived from Freeling's official rules and the official board diagram
(https://mindsports.nl/index.php/the-pit/552-superstar):

  (a) BOARD  -- 217 playable cells; a 60-cell EDGE ring; 12 outward corners
      (each adjacent to exactly 3 edge cells) + 6 inward corners (each adjacent
      to exactly 1); the 12 five-cell SIDES partition the 54 boundary cells with
      every inward corner in exactly 2 sides and every outward corner in 1.
  (b) STAR       value = (edge cells touched) - 2 (>= 3 to count); a lone outward
      corner = 1-point star.
  (c) SUPERSTAR  value = 5*(S-2) (S >= 3 to count); a lone inward corner connects
      2 sides; two inward corners connect 4 sides = 10 points while touching only
      2 edge cells (NOT a star), exactly Freeling's example.
  (d) LOOP       1 per enclosed vacant cell + 5 per enclosed opponent stone;
      enclosed friendly stones score 0.
  (e) a single chain scoring as a star AND a superstar AND a loop at once.
  (f) END + KOMI + DRAW -- two successive passes end the game; highest total
      wins; Black's komi is added; a genuine tie is an honest DRAW (winner None,
      returns [0, 0]).  Reached via apply_move (winner set only there).
  (g) engine conformance (random self-play terminates) + serialize round-trip.

Pure stdlib: imports only `agp` + this game.  Fast.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import os
import sys
from collections import deque

from games.superstar.game import (
    Superstar, SuperstarState, WHITE, BLACK,
    _cells, _cell_set, _edge, _edge_touch, _outward, _inward, _boundary,
    _sides, _side_of, _chains, _star_value, _superstar_value, _loop_value,
    _raw_score, _score, _DIRS,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


# The 18 corners, read off the official diagram (12 outward + 6 inward).
EXPECTED_OUTWARD = {
    (-9, 3), (-9, 6), (-6, -3), (-6, 9), (-3, -6), (-3, 9),
    (3, -9), (3, 6), (6, -9), (6, 3), (9, -6), (9, -3),
}
EXPECTED_INWARD = {
    (-6, 0), (-6, 6), (0, -6), (0, 6), (6, -6), (6, 0),
}

# One explicit side (flat_mid, outward corner, slant, slant, inward corner).
EXPECTED_SIDE = frozenset({(-9, 5), (-9, 6), (-8, 6), (-7, 6), (-6, 6)})


def _nbrs_on(c):
    on = _cell_set()
    return [(c[0] + dq, c[1] + dr) for dq, dr in _DIRS
            if (c[0] + dq, c[1] + dr) in on]


def _interior_path(start, target, forbidden):
    """Shortest path (BFS) from start to target through playable cells, avoiding
    BOUNDARY cells (except the target) and any `forbidden` cell.  Used to wire up
    corners through the interior without touching other side cells."""
    on = _cell_set()
    bnd = _boundary()
    prev = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        if c == target:
            break
        for dq, dr in _DIRS:
            n = (c[0] + dq, c[1] + dr)
            if n in prev or n not in on or n in forbidden:
                continue
            if n in bnd and n != target:   # stay interior except at the target
                continue
            prev[n] = c
            q.append(n)
    if target not in prev:
        raise RuntimeError(f"no interior path {start}->{target}")
    out, c = [], target
    while c is not None:
        out.append(c)
        c = prev[c]
    return out


def main():
    g = Superstar()

    # ---- (g) conformance --------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check_conformance(g, manifest, games=4, seed=1)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    # ---- (a) board geometry ----------------------------------------------
    cells = set(_cells())
    if len(cells) != 217:
        fail(f"expected 217 playable cells, got {len(cells)}")

    edge = set(_edge())
    if len(edge) != 60:
        fail(f"expected a 60-cell edge ring, got {len(edge)}")
    if edge & cells:
        fail("edge cells must not overlap the playing area")

    outward = set(_outward())
    inward = set(_inward())
    if outward != EXPECTED_OUTWARD:
        fail(f"outward corner mismatch: extra={sorted(outward-EXPECTED_OUTWARD)} "
             f"missing={sorted(EXPECTED_OUTWARD-outward)}")
    if inward != EXPECTED_INWARD:
        fail(f"inward corner mismatch: extra={sorted(inward-EXPECTED_INWARD)} "
             f"missing={sorted(EXPECTED_INWARD-inward)}")
    if len(outward) != 12 or len(inward) != 6:
        fail(f"expected 12 outward + 6 inward, got {len(outward)} + {len(inward)}")

    et = _edge_touch()
    for c in outward:
        if len(et[c]) != 3:
            fail(f"outward corner {c} should touch 3 edge cells, got {len(et[c])}")
    for c in inward:
        if len(et[c]) != 1:
            fail(f"inward corner {c} should touch 1 edge cell, got {len(et[c])}")

    # sides: 12, each 5 cells, partition the 54 boundary cells, IC in 2 / OC in 1
    sides = _sides()
    if len(sides) != 12:
        fail(f"expected 12 sides, got {len(sides)}")
    for i, sd in enumerate(sides):
        if len(sd) != 5:
            fail(f"side {i} should have 5 cells, got {len(sd)}: {sorted(sd)}")
    bnd = set(_boundary())
    if len(bnd) != 54:
        fail(f"expected 54 boundary cells, got {len(bnd)}")
    union = set()
    for sd in sides:
        union |= set(sd)
    if union != bnd:
        fail("the 12 sides must exactly partition the 54 boundary cells")
    so = _side_of()
    for c in inward:
        if len(so[c]) != 2:
            fail(f"inward corner {c} must belong to 2 sides, got {len(so[c])}")
    for c in outward:
        if len(so[c]) != 1:
            fail(f"outward corner {c} must belong to 1 side, got {len(so[c])}")
    if EXPECTED_SIDE not in set(sides):
        fail(f"expected side {sorted(EXPECTED_SIDE)} not found among sides")

    # ---- placement / legal moves -----------------------------------------
    s0 = g.initial_state()
    lm = g.legal_moves(s0)
    placements = [m for m in lm if m != "pass"]
    if len(placements) != 217:
        fail(f"opening should offer 217 placements, got {len(placements)}")
    if "pass" not in lm:
        fail("pass must be legal")
    if "swap" in lm:
        fail("Superstar has no swap rule")
    s1 = g.apply_move(s0, "0,0")
    if s1.board.get((0, 0)) != WHITE or s1.to_move != BLACK:
        fail("first placement bookkeeping wrong (White moves first)")
    if "0,0" in g.legal_moves(s1):
        fail("an occupied cell is still offered")

    # ---- (b) STAR ---------------------------------------------------------
    oc = (-9, 6)
    if _star_value({oc}) != 1:
        fail(f"lone outward corner should be a 1-point star, got {_star_value({oc})}")
    # the whole arm tip touches len(union of edge-touch)-2 edge cells
    tip = {(-9, 3), (-9, 4), (-9, 5), (-9, 6)}
    touched = set()
    for c in tip:
        touched |= et[c]
    if _star_value(tip) != len(touched) - 2:
        fail("star value must equal (edge cells touched) - 2")

    # ---- (c) SUPERSTAR ----------------------------------------------------
    ic = (-6, 6)
    if len(so[ic]) != 2 or _superstar_value({ic}) != 0:
        fail("a lone inward corner connects 2 sides -> superstar value 0")
    # two adjacent inward corners joined through the interior: 4 sides = 10 pts,
    # touching only 2 edge cells (NOT a star) -- Freeling's worked example.
    ic2 = (0, 6)
    path = _interior_path(ic, ic2, forbidden=set())
    chain = set(path)
    if len(so_union(chain, so)) != 4:
        fail(f"two inward corners must connect 4 sides, got {len(so_union(chain, so))}")
    if _superstar_value(chain) != 10:
        fail(f"two inward corners => 10-point superstar, got {_superstar_value(chain)}")
    if _star_value(chain) != 0:
        fail(f"the two-inward-corner chain must NOT be a star, got {_star_value(chain)}")
    # a chain reaching 3 sides = 5-point superstar
    three = set(_interior_path((-9, 6), (9, -3), forbidden=set()))
    three |= set(_interior_path((-9, 6), (3, 6), forbidden=set()))
    S3 = len(so_union(three, so))
    if S3 < 3:
        fail(f"3-corner chain should connect >=3 sides, got {S3}")
    if _superstar_value(three) != 5 * (S3 - 2):
        fail("superstar value must equal 5*(S-2)")

    # ---- (d) LOOP ---------------------------------------------------------
    ring = set(_nbrs_on((0, 0)))          # the six neighbours of the centre
    if len(ring) != 6:
        fail("centre should have 6 neighbours for the ring test")
    # empty centre -> 1 point
    board = {c: WHITE for c in ring}
    if _loop_value(board, WHITE, ring) != 1:
        fail(f"ring around one empty cell => loop 1, got {_loop_value(board, WHITE, ring)}")
    # opponent stone trapped -> 5 points
    board2 = dict(board); board2[(0, 0)] = BLACK
    if _loop_value(board2, WHITE, ring) != 5:
        fail(f"ring trapping an enemy stone => loop 5, got {_loop_value(board2, WHITE, ring)}")
    # friendly stone enclosed -> 0 points
    board3 = dict(board); board3[(0, 0)] = WHITE
    if _loop_value(board3, WHITE, ring) != 0:
        fail(f"ring enclosing a friendly stone => loop 0, got {_loop_value(board3, WHITE, ring)}")
    # a chain that does NOT surround anything scores no loop
    if _loop_value({oc: WHITE}, WHITE, {oc}) != 0:
        fail("a lone stone surrounds nothing => loop 0")

    # ---- (e) one chain scoring in all three capacities --------------------
    # ring around the centre + interior arms out to 3 outward corners.
    allthree = set(ring)
    for corner in [(-9, 6), (9, -3), (3, 6)]:
        start = min(ring)  # any ring cell is connected to the rest of the ring
        allthree |= set(_interior_path(start, corner, forbidden={(0, 0)}))
    if (0, 0) in allthree:
        fail("the enclosed centre must stay vacant")
    board_all = {c: WHITE for c in allthree}
    # confirm it is a single connected chain
    comps = _chains(board_all, WHITE)
    if len(comps) != 1:
        fail(f"the all-three construction must be one chain, got {len(comps)}")
    ch = comps[0]
    sv, ssv, lv = _star_value(ch), _superstar_value(ch), _loop_value(board_all, WHITE, ch)
    if not (sv > 0 and ssv > 0 and lv > 0):
        fail(f"one chain should score all three: star={sv} superstar={ssv} loop={lv}")

    # ---- (f) END + KOMI + genuine DRAW ------------------------------------
    ocw, ocb = (-9, 6), (9, -3)   # two far-apart outward corners: each a 1-pt star
    # tie with komi 0 -> draw
    s = SuperstarState(board={ocw: WHITE, ocb: BLACK}, to_move=WHITE, ply=10, komi=0)
    s = g.apply_move(s, "pass")
    s = g.apply_move(s, "pass")
    if not g.is_terminal(s):
        fail("two successive passes must end the game")
    if _score(s.board, WHITE, 0) != 1 or _score(s.board, BLACK, 0) != 1:
        fail("tie setup wrong (each side a lone 1-point star)")
    if s.winner is not None:
        fail(f"a genuine tie must be a DRAW (winner None), got {s.winner}")
    if g.returns(s) != [0.0, 0.0]:
        fail(f"a draw must return [0,0], got {g.returns(s)}")
    # same position, komi 3 for Black -> Black wins
    s = SuperstarState(board={ocw: WHITE, ocb: BLACK}, to_move=WHITE, ply=10, komi=3)
    s = g.apply_move(s, "pass")
    s = g.apply_move(s, "pass")
    if _score(s.board, WHITE, 3) != 1 or _score(s.board, BLACK, 3) != 4:
        fail(f"komi setup wrong: W={_score(s.board, WHITE, 3)} B={_score(s.board, BLACK, 3)}")
    if s.winner != BLACK:
        fail(f"Black (1 + komi 3 = 4) should beat White (1), winner={s.winner}")
    if g.returns(s) != [-1.0, 1.0]:
        fail(f"returns wrong for Black win: {g.returns(s)}")

    # ---- serialize round-trip --------------------------------------------
    st = g.apply_move(g.apply_move(g.initial_state({"komi": 2}), "0,0"), "6,3")
    rt = g.deserialize(json.loads(json.dumps(g.serialize(st))))
    if rt.board != st.board or rt.to_move != st.to_move or rt.komi != st.komi:
        fail("serialize round-trip mismatch")

    print("SELFTEST OK")


def so_union(chain, so):
    sides = set()
    for c in chain:
        sides |= so[c]
    return sides


if __name__ == "__main__":
    main()
