"""Standalone correctness anchor for Meridians (Kanare Kato, 2021).

Run from the engine dir:  PYTHONPATH=. python3 games/meridians/selftest.py

Pure stdlib (imports only `agp` + this game).  Asserts:
  * conformance (terminates under random self-play),
  * board GEOMETRY: 114 points at standard size with the exact 6..12..6 row
    widths and 6/7 side counts (matches the AiAi "Board Size 114" anchor); the
    standard opening has 114 legal placements,
  * PLACEMENT line-of-sight: sees past a friendly stone, blocked by an enemy,
  * PATH / life: a clear empty line to a DIFFERENT friendly group keeps a group
    alive; an enemy in the gap kills it; a lone stone has no path,
  * CAPTURE: the opponent's dead groups are removed at the start of a turn,
  * WIN by annihilation, REACHED via apply_move,
  * serialize round-trip.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import os
import sys

from games.meridians.game import (
    Meridians, MeridiansState, LIGHT, DARK,
    _board_cells, _cell_set, _sees_friendly, _has_path, _group_id_map,
    _dead_groups, _remove_dead,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def main():
    g = Meridians()

    # ---- conformance ------------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    # Use the smallest board for speed; conformance plays random games.
    rep = check_conformance(g, manifest, games=4, seed=3)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    # ---- geometry (the quantitative anchor: 114 points, sides 6/7) --------
    cells = _board_cells(7)
    if len(cells) != 114:
        fail(f"standard board should have 114 points, got {len(cells)}")
    rows = {}
    for (q, r) in cells:
        rows.setdefault(r, 0)
        rows[r] += 1
    widths = [rows[r] for r in sorted(rows)]
    if widths != [6, 7, 8, 9, 10, 11, 12, 11, 10, 9, 8, 7, 6]:
        fail(f"unexpected row widths {widths}")
    # Two short sides of 6 (top & bottom rows), four long sides of 7.
    if widths[0] != 6 or widths[-1] != 6:
        fail("top/bottom short sides should each have 6 points")
    # Beginner / expert totals.
    if len(_board_cells(6)) != 80 or len(_board_cells(8)) != 154:
        fail("beginner/expert board sizes wrong "
             f"({len(_board_cells(6))}, {len(_board_cells(8))})")
    # Opening: any of the 114 points is legal.
    s0 = g.initial_state()
    if len(g.legal_moves(s0)) != 114:
        fail(f"standard opening should have 114 moves, got {len(g.legal_moves(s0))}")

    # ---- PLACEMENT line of sight -----------------------------------------
    # Light stone at (0,0); the empty (2,0) is 2 apart on the q-axis.
    if not _sees_friendly({(0, 0): LIGHT}, (2, 0), LIGHT, 7):
        fail("placement: should see a friendly stone across empty points")
    if _sees_friendly({(0, 0): LIGHT, (1, 0): DARK}, (2, 0), LIGHT, 7):
        fail("placement: an enemy stone in between must block sight")
    if not _sees_friendly({(0, 0): LIGHT, (1, 0): LIGHT}, (2, 0), LIGHT, 7):
        fail("placement: a friendly stone in between must NOT block sight")
    # A point that sees no friendly stone at all is not a legal placement.
    if _sees_friendly({(5, 0): LIGHT}, (-6, 6), LIGHT, 7):
        fail("placement: far corner should not see a single distant stone "
             "across two axes")

    # ---- PATH / life ------------------------------------------------------
    # Two separate Light groups with empty points between -> both alive.
    b_alive = {(0, 0): LIGHT, (3, 0): LIGHT}
    gid = _group_id_map(b_alive, LIGHT)
    if gid[(0, 0)] == gid[(3, 0)]:
        fail("(0,0) and (3,0) should be DIFFERENT groups")
    if not _has_path(b_alive, (0, 0), LIGHT, 7, gid):
        fail("path: a clear empty line to a different friendly group = alive")
    if _dead_groups(b_alive, LIGHT, 7):
        fail("path: neither group should be dead")
    # An enemy stone in the gap breaks the path (empties-only requirement).
    b_block = {(0, 0): LIGHT, (3, 0): LIGHT, (1, 0): DARK}
    gid2 = _group_id_map(b_block, LIGHT)
    if _has_path(b_block, (0, 0), LIGHT, 7, gid2):
        fail("path: an enemy stone in the connecting line must break the path")
    dead = _dead_groups(b_block, LIGHT, 7)
    # With the only line cut, the (0,0) singleton is dead (no other sightline
    # to a different group here).
    if {(0, 0)} not in [set(g_) for g_ in dead]:
        fail(f"path: cut group (0,0) should be dead, dead={dead}")
    # A lone stone has no path.
    if _has_path({(0, 0): LIGHT}, (0, 0), LIGHT, 7,
                 _group_id_map({(0, 0): LIGHT}, LIGHT)):
        fail("path: a single lone stone must have no path")

    # ---- CAPTURE removal --------------------------------------------------
    # Dark has a lone dead stone; removing Dark's dead groups clears it.
    b_cap = {(0, 0): LIGHT, (3, 0): LIGHT, (-3, 3): DARK}
    after = _remove_dead(b_cap, DARK, 7)
    if (-3, 3) in after:
        fail("capture: Dark's lone dead stone should be removed")
    if (0, 0) not in after or (3, 0) not in after:
        fail("capture: Light's living stones must NOT be removed")

    # ---- WIN by annihilation, reached via apply_move ---------------------
    st = MeridiansState(
        size=7,
        board={(0, 0): LIGHT, (3, 0): LIGHT, (-3, 3): DARK},
        to_move=LIGHT, turns=(2, 2), ply=10,
    )
    if g.is_terminal(st):
        fail("win: pre-move state should not be terminal")
    mv = g.legal_moves(st)[0]
    won = g.apply_move(st, mv)
    if won.winner != LIGHT:
        fail(f"win: Light should win by annihilation, winner={won.winner}")
    if not g.is_terminal(won):
        fail("win: terminal flag not set after annihilation")
    if any(v == DARK for v in won.board.values()):
        fail("win: Dark should have no stones after annihilation")
    if g.returns(won) != [1.0, -1.0]:
        fail(f"win: returns wrong, got {g.returns(won)}")

    # Capture step is SKIPPED while opponent has < 2 turns: a lone first stone
    # is not annihilated before it can be paired.
    early = MeridiansState(size=7, board={(0, 0): DARK}, to_move=LIGHT,
                           turns=(0, 1), ply=1)
    le = g.legal_moves(early)
    if "pass" in le or not le:
        fail("early: Light's 2nd-from-empty turn should have placements")
    e2 = g.apply_move(early, le[0])
    if e2.winner is not None:
        fail("early: no win should fire before turn 2 each")

    # ---- serialize round-trip --------------------------------------------
    for state in (s0, st, won, e2):
        rt = g.deserialize(g.serialize(state))
        if g.serialize(rt) != g.serialize(state):
            fail("serialize round-trip mismatch")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
