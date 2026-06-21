"""Standalone correctness anchor for Havannah.

Run from the engine dir:  PYTHONPATH=. python3 games/havannah/selftest.py

Asserts:
  * conformance (a placement game with no real draws),
  * a constructed RING (a friendly loop enclosing a cell),
  * a constructed BRIDGE (a chain joining two corners),
  * a constructed FORK (a chain joining three edges),
  * a few rule-specific checks (corner/edge classification, pie swap,
    enemy-filled ring interior still counts, non-winning shapes don't trip).

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import os
import sys

from games.havannah.game import (
    Havannah, HavannahState, RED, BLUE,
    _cells, _corners, _edge_id, _neighbors, _win_for, _has_ring, _group,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def board_win(size, stones, player, last=None):
    """stones: dict cell->player. Returns win kind for `player`."""
    return _win_for(stones, size, player, last)


def main():
    g = Havannah()

    # ---- conformance ------------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check_conformance(g, manifest, games=6, seed=1)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    # ---- geometry sanity --------------------------------------------------
    N = 8
    n = N - 1
    corners = set(_corners(N))
    if len(corners) != 6:
        fail(f"expected 6 corners, got {len(corners)}")
    # Each corner: two cube coords extreme.
    for (q, r) in corners:
        s = -q - r
        extremes = sum(1 for v in (q, r, s) if abs(v) == n)
        if extremes != 2:
            fail(f"corner {(q, r)} should pin two extremes, got {extremes}")
    edge_of = _edge_id(N)
    # Corners must NOT be classified as edge cells.
    for c in corners:
        if c in edge_of:
            fail(f"corner {c} wrongly classified onto an edge")
    # Edge cells have exactly one extreme coord and 6 distinct edges exist.
    for (q, r), eid in edge_of.items():
        s = -q - r
        extremes = sum(1 for v in (q, r, s) if abs(v) == n)
        if extremes != 1:
            fail(f"edge cell {(q, r)} should have exactly one extreme, got {extremes}")
    if set(edge_of.values()) != set(range(6)):
        fail(f"expected 6 edge ids, got {sorted(set(edge_of.values()))}")

    # ---- RING -------------------------------------------------------------
    # Six neighbours of the centre form a closed loop enclosing (0,0).
    ring_cells = _neighbors(0, 0)
    stones = {c: RED for c in ring_cells}
    if not _has_ring(stones, N, _group(stones, ring_cells[0], RED)):
        fail("ring around centre not detected by _has_ring")
    if board_win(N, stones, RED) != "ring":
        fail("ring not detected as a win")
    # Centre is empty here; it should still be a ring.
    # Enemy stone INSIDE the ring must still count as a ring.
    stones2 = dict(stones)
    stones2[(0, 0)] = BLUE
    if board_win(N, stones2, RED) != "ring":
        fail("ring enclosing an enemy stone not detected")
    # A straight line of 6 stones (no enclosure) is NOT a ring.
    line = {(q, 0): RED for q in range(-3, 3)}
    if board_win(N, line, RED) == "ring":
        fail("straight line wrongly reported as a ring")

    # Build the ring through real play to confirm winner is set on placement.
    s = g.initial_state(options={"size": N, "pie": False})
    # Red plays ring cells; Blue plays harmless faraway cells between.
    far = [(n, 0), (n, -1), (n, -2), (n, -3), (n, -4), (n, -5)]  # a corner + edge run
    order = []
    for i, rc in enumerate(ring_cells):
        order.append(f"{rc[0]},{rc[1]}")
        if i < len(ring_cells) - 1:
            order.append(f"{far[i][0]},{far[i][1]}")
    moved = s
    for i, mv in enumerate(order):
        # Stop if game already terminal (shouldn't be until last Red move).
        if g.is_terminal(moved):
            fail(f"game ended early before ring complete at move {i}")
        moved = g.apply_move(moved, mv)
    if moved.winner != RED or moved.win_kind != "ring":
        fail(f"played-out ring: winner={moved.winner} kind={moved.win_kind}")

    # ---- BRIDGE -----------------------------------------------------------
    # A chain of adjacent cells from corner (n,0) to corner (n,-n) along the
    # q=n edge: (n, 0), (n, -1), ..., (n, -n). Endpoints are two corners.
    bridge_cells = [(n, -k) for k in range(0, n + 1)]
    bstones = {c: RED for c in bridge_cells}
    # sanity: it's connected
    grp = _group(bstones, bridge_cells[0], RED)
    if len(grp) != len(bridge_cells):
        fail("bridge chain is not connected")
    if (n, 0) not in corners or (n, -n) not in corners:
        fail("bridge endpoints are not both corners")
    if board_win(N, bstones, RED) != "bridge":
        fail("bridge between two corners not detected")
    # A chain touching only ONE corner is not a bridge.
    one_corner = {(n, -k): RED for k in range(0, n)}  # excludes (n,-n)
    if board_win(N, one_corner, RED) == "bridge":
        fail("single-corner chain wrongly reported as a bridge")

    # ---- FORK -------------------------------------------------------------
    # A small chain from the centre out to three different edges.
    # Pick concrete non-corner edge cells from three different edges.
    by_edge = {}
    for c, eid in _edge_id(N).items():
        by_edge.setdefault(eid, []).append(c)
    chosen = [by_edge[0][len(by_edge[0]) // 2],
              by_edge[2][len(by_edge[2]) // 2],
              by_edge[4][len(by_edge[4]) // 2]]
    # Connect the three chosen edge cells through the centre with a path each.

    def path(a, b):
        """Greedy hex path from a to b stepping to reduce cube distance."""
        cur = a
        cells = [cur]
        guard = 0
        while cur != b and guard < 200:
            guard += 1
            best, bestd = None, None
            for nb in _neighbors(*cur):
                # cube distance
                dq = nb[0] - b[0]
                dr = nb[1] - b[1]
                ds = (-nb[0] - nb[1]) - (-b[0] - b[1])
                d = (abs(dq) + abs(dr) + abs(ds)) // 2
                if bestd is None or d < bestd:
                    bestd, best = d, nb
            cur = best
            cells.append(cur)
        return cells

    fstones = {}
    center = (0, 0)
    for ec in chosen:
        for c in path(center, ec):
            fstones[c] = RED
    # all chosen edge cells must be on board
    onboard = set(_cells(N))
    for ec in chosen:
        if ec not in onboard:
            fail(f"chosen edge cell {ec} off board")
    edges_touched = {_edge_id(N)[c] for c in fstones if c in _edge_id(N)}
    if len(edges_touched) < 3:
        fail(f"fork construction only touched edges {edges_touched}")
    if board_win(N, fstones, RED) != "fork":
        fail("fork joining three edges not detected")
    # Two edges only -> not a fork.
    two = {}
    for ec in chosen[:2]:
        for c in path(center, ec):
            two[c] = RED
    res = board_win(N, two, RED)
    if res == "fork":
        fail("two-edge chain wrongly reported as a fork")

    # ---- pie / swap -------------------------------------------------------
    sp = g.initial_state(options={"size": 6, "pie": True})
    sp = g.apply_move(sp, "1,0")  # Red opens
    if "swap" not in g.legal_moves(sp):
        fail("swap not offered to second player with pie on")
    after = g.apply_move(sp, "swap")
    if list(after.board.values()) != [BLUE] and list(after.board.values()) != [RED]:
        # after swap the single stone belongs to the swapper (was Blue to move)
        pass
    if after.board.get((1, 0)) != BLUE:
        fail(f"after swap the opening stone should be Blue, got {after.board}")
    if after.to_move != RED:
        fail("after swap it should be Red to move")
    # pie off -> no swap.
    sp2 = g.initial_state(options={"size": 6, "pie": False})
    sp2 = g.apply_move(sp2, "1,0")
    if "swap" in g.legal_moves(sp2):
        fail("swap offered though pie is off")

    # ---- serialize round-trip --------------------------------------------
    rt = g.deserialize(g.serialize(moved))
    if g.serialize(rt) != g.serialize(moved):
        fail("serialize round-trip mismatch")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
