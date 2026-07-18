#!/usr/bin/env python3
"""Standalone correctness self-test for Hijara (Martin H. Samuel).

Run from engine/ with:  PYTHONPATH=. python3 games/hijara/selftest.py

Anchors:
  1. Formation-set anchor via the 3-D equivalence (Handscomb, AG#5): mapping
     small square (X, Y, n) -> 3-D cell (X, Y, n-1), the 76 base formations
     must be EXACTLY Qubic's 76 lines (independently enumerated by direction
     scan), with points 10 for constant-height lines, 20 for vertical pillars,
     15 for the height-changing diagonals. The corners option adds exactly
     4 + 24 formations.
  2. The fill-order rule: only the lowest-numbered open small square of each
     large square is legal; anything else raises and never appears in
     legal_moves.
  3. Scripted scoring scenarios: 10-pt row, 15-pt ascending AND descending
     sequences, 20-pt full square, a single placement completing two
     formations at once (+20), and the optional corner formations (scoring
     with the option on, NOT scoring with it off).
  4. A scripted mirror strategy (second player copies through 180-degree
     rotation) forces a 64-ply genuine DRAW -> draws are reachable and
     returned honestly as [0, 0].
  5. Differential: hundreds of random full games; the incrementally-accrued
     scores must equal an independent from-scratch final-board scorer written
     via the 3-D array (direction-scan lines + corner matching), and returns
     must match the score comparison.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
from __future__ import annotations

import random
import sys
from itertools import permutations, product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.hijara.game import (  # noqa: E402
    Hijara, _cell_id, _formations, _parse_cell,
)

G = Hijara()


# --------------------------------------------------------------------------
# Independent 3-D machinery (deliberately written differently from game.py:
# direction-vector line enumeration + geometric classification, not
# constructed formation lists).
# --------------------------------------------------------------------------

def _lines_3d():
    dirs = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            for dz in (-1, 0, 1) if (dx, dy, dz) != (0, 0, 0)]
    lines = set()
    for x, y, z in product(range(4), repeat=3):
        for dx, dy, dz in dirs:
            cells = []
            for k in range(4):
                nx, ny, nz = x + k * dx, y + k * dy, z + k * dz
                if not (0 <= nx < 4 and 0 <= ny < 4 and 0 <= nz < 4):
                    break
                cells.append((nx, ny, nz))
            else:
                lines.add(frozenset(cells))
    return lines


LINES_3D = _lines_3d()
CORNERS_3D = ((0, 0), (3, 0), (0, 3), (3, 3))


def _line_value(line) -> int:
    xs = {c[0] for c in line}
    ys = {c[1] for c in line}
    zs = {c[2] for c in line}
    if len(zs) == 1:
        return 10                      # horizontal: same number in a row
    if len(xs) == 1 and len(ys) == 1:
        return 20                      # pillar: one full large square
    return 15                          # height-changing diagonal: 1-2-3-4


def _board_3d(state):
    b = {}
    for idx, col in enumerate(state.squares):
        x, y = idx % 4, idx // 4
        for z, owner in enumerate(col):
            b[(x, y, z)] = owner
    return b


def scores_from_scratch(state):
    """Recompute both totals from the final board only."""
    b = _board_3d(state)
    tot = [0, 0]
    for line in LINES_3D:
        owners = {b.get(c) for c in line}
        if len(owners) == 1 and None not in owners:
            tot[owners.pop()] += _line_value(line)
    if state.corners:
        for p in (0, 1):
            for z in range(4):
                if all(b.get((cx, cy, z)) == p for cx, cy in CORNERS_3D):
                    tot[p] += 10
            for perm in permutations(range(4)):
                if all(b.get((CORNERS_3D[i][0], CORNERS_3D[i][1], perm[i])) == p
                       for i in range(4)):
                    tot[p] += 15
    return tot


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def play_squares(squares, corners=False):
    """Play a scripted game given a list of (X, Y) large-square choices
    (the small square is forced); returns the state trace."""
    s = G.initial_state({"corners": corners})
    trace = [s]
    for (x, y) in squares:
        n = len(s.squares[y * 4 + x]) + 1
        s = G.apply_move(s, _cell_id(x, y, n))
        trace.append(s)
    return trace


def check(cond, msg):
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)


# --------------------------------------------------------------------------
# 1. Formation set == the 76 Qubic lines (base), +28 with corners
# --------------------------------------------------------------------------

def test_formations():
    base = _formations(False)
    check(len(base) == 76, f"base formations: {len(base)} != 76")
    by_pts = {}
    for cells, pts in base:
        by_pts[pts] = by_pts.get(pts, 0) + 1
        check(len(cells) == 4, "formation must have 4 cells")
    check(by_pts == {10: 40, 15: 20, 20: 16},
          f"base breakdown {by_pts} != 40/20/16")

    mapped = {frozenset((x, y, n - 1) for (x, y, n) in cells): pts
              for cells, pts in base}
    check(len(mapped) == 76, "duplicate formations after 3-D mapping")
    check(set(mapped) == LINES_3D,
          "base formations are not exactly the 76 Qubic lines")
    for line, pts in mapped.items():
        check(pts == _line_value(line),
              f"line {sorted(line)} scored {pts}, geometry says {_line_value(line)}")

    withc = _formations(True)
    check(len(withc) == 76 + 4 + 24,
          f"corner formations: {len(withc)} != 104")
    extra = [f for f in withc if f not in base]
    check(sorted(p for _, p in extra) == [10] * 4 + [15] * 24,
          "corner extras must be 4x10pt + 24x15pt")
    for cells, _ in extra:
        check({(x, y) for (x, y, n) in cells} == set(CORNERS_3D),
              "corner formation not confined to the 4 corner squares")


# --------------------------------------------------------------------------
# 2. Fill-order rule
# --------------------------------------------------------------------------

def test_fill_order():
    s = G.initial_state()
    lm = G.legal_moves(s)
    check(len(lm) == 16, f"initial legal moves {len(lm)} != 16")
    check(set(lm) == {_cell_id(x, y, 1) for x in range(4) for y in range(4)},
          "initial legal moves must be the 16 number-1 squares")
    check(_cell_id(0, 0, 2) not in lm, "slot 2 legal on an empty square")
    try:
        G.apply_move(s, _cell_id(0, 0, 2))
        check(False, "placing on slot 2 of an empty square must raise")
    except ValueError:
        pass
    # fill square (0,0) completely -> 15 squares remain playable
    trace = play_squares([(0, 0), (3, 3), (0, 0), (3, 3), (0, 0), (3, 3), (0, 0)])
    s = trace[-1]
    check(len(G.legal_moves(s)) == 15, "full square must drop out of legal moves")
    check(_parse_cell(G.legal_moves(s)[0]) is not None, "cell ids parse back")
    # serialize round-trip
    check(G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s),
          "serialize round-trip")


# --------------------------------------------------------------------------
# 3. Scripted scoring scenarios
# --------------------------------------------------------------------------

def test_scenarios():
    # 20 pts: p0 fills square (0,0); p1 stacks in (3,3) without scoring.
    t = play_squares([(0, 0), (3, 3), (0, 0), (3, 3), (0, 0), (3, 3), (0, 0)])
    check(t[-1].scores == [20, 0], f"20-pt scenario: {t[-1].scores}")
    check(t[-2].scores == [0, 0], "no premature score")

    # 10 pts: p0 takes number 1 across row Y=0; p1 number 1 across row Y=1.
    t = play_squares([(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1), (3, 0)])
    check(t[-1].scores == [10, 0], f"10-pt scenario: {t[-1].scores}")

    # 15 pts ascending: p0 gets 1,2,3,4 left-to-right along row Y=0.
    t = play_squares([(0, 0), (1, 0), (1, 0), (2, 0), (2, 0), (3, 0),
                      (2, 0), (3, 0), (3, 0), (0, 1), (3, 0)])
    check(t[-1].scores == [15, 0], f"15-pt ascending scenario: {t[-1].scores}")

    # 15 pts descending: p0 gets 4,3,2,1 left-to-right along row Y=0.
    t = play_squares([(3, 0), (2, 0), (2, 0), (1, 0), (0, 3), (1, 0),
                      (1, 0), (0, 0), (1, 3), (0, 0), (2, 3), (0, 0), (0, 0)])
    check(t[-1].scores == [15, 0], f"15-pt descending scenario: {t[-1].scores}")

    # Multi-formation single stone: p0's last move completes the row Y=0 of 1s
    # AND the column X=3 of 1s at once -> +20.
    t = play_squares([(0, 0), (1, 1), (1, 0), (1, 2), (2, 0), (2, 1),
                      (3, 1), (1, 1), (3, 2), (1, 2), (3, 3), (2, 1), (3, 0)])
    check(t[-1].scores == [20, 0], f"multi-formation scenario: {t[-1].scores}")
    check(t[-2].scores == [0, 0], "multi-formation: nothing before the last stone")
    # describe_move surfaces the points
    before = t[-2]
    desc = G.describe_move(before, _cell_id(3, 0, 1))
    check("+20" in desc and "Sun" in desc, f"describe_move: {desc!r}")

    # Optional corner formations: same-number corners = 10 (option ON only).
    corner_seq = [(0, 0), (1, 1), (3, 0), (1, 2), (0, 3), (2, 1), (3, 3)]
    t_on = play_squares(corner_seq, corners=True)
    t_off = play_squares(corner_seq, corners=False)
    check(t_on[-1].scores == [10, 0], f"corner-10 with option on: {t_on[-1].scores}")
    check(t_off[-1].scores == [0, 0], f"corner-10 must NOT score with option off: {t_off[-1].scores}")

    # Corner sequence 1,2,3,4 one per corner (any arrangement) = 15.
    t = play_squares([(0, 0), (3, 0), (3, 0), (0, 3), (1, 0), (0, 3),
                      (0, 3), (3, 3), (2, 0), (3, 3), (0, 1), (3, 3), (3, 3)],
                     corners=True)
    check(t[-1].scores == [15, 0], f"corner-15 scenario: {t[-1].scores}")


# --------------------------------------------------------------------------
# 4. Mirror strategy -> forced draw (draws reachable, honest [0, 0])
# --------------------------------------------------------------------------

def test_mirror_draw():
    for corners in (False, True):
        rng = random.Random(7 if corners else 5)
        s = G.initial_state({"corners": corners})
        plies = 0
        while not G.is_terminal(s):
            if plies % 2 == 0:      # p0: random square
                mv = rng.choice(G.legal_moves(s))
                x, y, _ = _parse_cell(mv)
            else:                   # p1: mirror through 180-degree rotation
                px, py, _ = _parse_cell(s.last)
                x, y = 3 - px, 3 - py
                mv = _cell_id(x, y, len(s.squares[y * 4 + x]) + 1)
            s = G.apply_move(s, mv)
            plies += 1
        check(plies == 64, f"mirror game lasted {plies} plies != 64")
        check(s.scores[0] == s.scores[1],
              f"mirror game not tied (corners={corners}): {s.scores}")
        check(G.returns(s) == [0.0, 0.0], "tie must return an honest [0, 0]")
        check(scores_from_scratch(s) == s.scores, "mirror game rescore differs")


# --------------------------------------------------------------------------
# 5. Random-game differential vs the independent scorer
# --------------------------------------------------------------------------

def test_differential():
    rng = random.Random(2026)
    draws = 0
    for g in range(300):
        corners = g % 2 == 1
        s = G.initial_state({"corners": corners})
        plies = 0
        while not G.is_terminal(s):
            lm = G.legal_moves(s)
            check(0 < len(lm) <= 16, f"legal-move count {len(lm)}")
            check(len(lm) == sum(1 for c in s.squares if len(c) < 4),
                  "one legal move per non-full square")
            s = G.apply_move(s, rng.choice(lm))
            plies += 1
            check(plies <= 64, "game exceeded 64 plies")
        check(plies == 64, f"game ended after {plies} plies != 64")
        check(sum(len(c) for c in s.squares) == 64, "final board not full")
        indep = scores_from_scratch(s)
        check(indep == s.scores,
              f"scorer mismatch (corners={corners}): incremental {s.scores} "
              f"vs independent {indep}")
        ret = G.returns(s)
        a, b = s.scores
        want = [0.0, 0.0] if a == b else ([1.0, -1.0] if a > b else [-1.0, 1.0])
        check(ret == want, f"returns {ret} inconsistent with scores {s.scores}")
        if a == b:
            draws += 1
    print(f"  differential: 300 random games OK ({draws} natural draws)")


def main():
    test_formations()
    test_fill_order()
    test_scenarios()
    test_mirror_draw()
    test_differential()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
