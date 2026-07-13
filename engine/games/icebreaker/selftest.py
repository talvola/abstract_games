"""Icebreaker correctness anchor (pure stdlib + agp + this game).

Run: PYTHONPATH=. python3 games/icebreaker/selftest.py -> prints SELFTEST OK, exit 0.

Anchors:
  * the Fig-1 setup (six corner ships alternating Red/Black, 55 icebergs, majority 28);
  * the move-toward-nearest-iceberg rule and its BFS-around-ships distance
    (a blocker ship diverts the legal step off the straight line);
  * the must-capture rule for an adjacent iceberg;
  * a capture applied via apply_move (score++, iceberg removed, ship relocated);
  * a majority win reached via apply_move;
  * serialize/deserialize round-trip;
  * termination (a greedy-capture playout ends with a genuine result).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.icebreaker.game import Icebreaker, IceState, RED, BLACK, _corners  # noqa: E402


def check(cond, msg):
    if not cond:
        print(f"SELFTEST FAIL: {msg}")
        sys.exit(1)


G = Icebreaker()


def test_setup():
    s = G.initial_state()
    check(len(s.ships) == 6, "6 ships")
    reds = {c for c, seat in s.ships.items() if seat == RED}
    blacks = {c for c, seat in s.ships.items() if seat == BLACK}
    check(reds == {(0, -4), (4, 0), (-4, 4)}, f"red corners {reds}")
    check(blacks == {(4, -4), (0, 4), (-4, 0)}, f"black corners {blacks}")
    # Corners alternate around the ring.
    corners = _corners(5)
    for i, c in enumerate(corners):
        check(s.ships[c] == (RED if i % 2 == 0 else BLACK), f"alt corner {c}")
    check(s.total == 55, f"55 icebergs, got {s.total}")
    check(len(s.icebergs) == 55, "55 iceberg cells")
    check(G._majority(s) == 28, f"majority 28, got {G._majority(s)}")
    check(s.to_move == RED, "Red first")
    check(not s.icebergs & set(s.ships), "ships and icebergs disjoint")


def test_move_direction_bfs():
    # One Red ship at origin, one far iceberg at (2,0). No blocker: the only
    # legal step is straight toward it, onto (1,0).
    base = dict(size=5, total=100, captures=[0, 0], to_move=RED)
    s = IceState(ships={(0, 0): RED}, icebergs=frozenset({(2, 0)}), **base)
    lm = set(G.legal_moves(s))
    check(lm == {"0,0>1,0"}, f"straight step, got {lm}")

    # Now drop a Black blocker on (1,0): the straight route is gone, so the ship
    # must detour. BFS-around-ships distance from (0,0) becomes 3, and the legal
    # steps are the two neighbours on a shortest detour: (1,-1) and (0,1).
    s2 = IceState(ships={(0, 0): RED, (1, 0): BLACK}, icebergs=frozenset({(2, 0)}),
                  **base)
    lm2 = set(G.legal_moves(s2))
    check(lm2 == {"0,0>1,-1", "0,0>0,1"}, f"detour steps, got {lm2}")
    check("0,0>1,0" not in lm2, "cannot step onto the blocker ship")


def test_tie_two_nearest_icebergs():
    # Fig. 2 clause: a ship with two equally-near icebergs may move toward
    # EITHER. One Red ship at origin, icebergs equidistant on opposite sides.
    s = IceState(size=5, total=100, captures=[0, 0], to_move=RED,
                 ships={(0, 0): RED}, icebergs=frozenset({(2, 0), (-2, 0)}))
    check(set(G.legal_moves(s)) == {"0,0>1,0", "0,0>-1,0"},
          f"may move toward either equally-near iceberg, got {G.legal_moves(s)}")
    # And several equal-length shortest paths to a SINGLE (diagonal) iceberg:
    # both first steps that reduce the distance are legal.
    s2 = IceState(size=5, total=100, captures=[0, 0], to_move=RED,
                  ships={(0, 0): RED}, icebergs=frozenset({(2, -1)}))
    check(set(G.legal_moves(s2)) == {"0,0>1,0", "0,0>1,-1"},
          f"both shortest-path first steps legal, got {G.legal_moves(s2)}")


def test_no_move_honest_scoring():
    # Reachable no-legal-move rulings (found by search), driven via apply_move:
    # the mover captures the last reachable iceberg, the opponent then has no
    # move and may not pass -> score by captures. Equal = honest DRAW; unequal
    # -> the majority-holder wins. NEVER a fabricated winner from a tie.
    # DRAW: after Black's forced capture the counts are equal (1:1).
    draw = IceState(size=4, total=100, captures=[1, 0], to_move=BLACK,
                    ships={(-2, -1): RED, (-2, 0): BLACK, (-3, 1): RED,
                           (1, 2): BLACK, (1, -1): RED, (3, -1): BLACK},
                    icebergs=frozenset({(-3, 0)}))
    nd = G.apply_move(draw, "-2,0>-3,0")
    check(nd.over and nd.winner is None, f"tie -> honest draw, got {nd.winner}")
    check(not G._all_moves(nd), "opponent genuinely had no move")
    check(G.returns(nd) == [0.0, 0.0], "draw returns")
    # WIN: after Red's forced capture Red leads 4:3 and Black is stuck.
    win = IceState(size=4, total=100, captures=[3, 3], to_move=RED,
                   ships={(-2, 2): RED, (-2, 3): BLACK, (-1, 1): RED,
                          (-1, 0): BLACK, (1, 0): RED, (-3, 2): BLACK},
                   icebergs=frozenset({(-3, 3)}))
    nw = G.apply_move(win, "-2,2>-3,3")
    check(nw.over and nw.winner == RED, f"more captures wins, got {nw.winner}")
    check(not G._all_moves(nw), "opponent genuinely had no move")
    check(nw.captures == [4, 3], f"scored by captures, got {nw.captures}")


def test_must_capture_adjacent():
    # An adjacent iceberg (1,0) and a far one (3,0): distance is 1, so the ONLY
    # legal move is the capture onto (1,0) — an empty step is illegal.
    s = IceState(size=5, total=100, captures=[0, 0], to_move=RED,
                 ships={(0, 0): RED}, icebergs=frozenset({(1, 0), (3, 0)}))
    lm = set(G.legal_moves(s))
    check(lm == {"0,0>1,0"}, f"must capture adjacent iceberg, got {lm}")


def test_capture_apply():
    # A Black ship (0,3) with a reachable iceberg (0,2) keeps the game alive so
    # the no-legal-move end-rule doesn't fire.
    s = IceState(size=5, total=100, captures=[0, 0], to_move=RED,
                 ships={(0, 0): RED, (0, 3): BLACK},
                 icebergs=frozenset({(1, 0), (3, 0), (0, 2)}))
    ns = G.apply_move(s, "0,0>1,0")
    check(ns.captures[RED] == 1, "score incremented")
    check((1, 0) not in ns.icebergs, "iceberg removed")
    check(ns.ships.get((1, 0)) == RED and (0, 0) not in ns.ships, "ship moved")
    check(ns.to_move == BLACK, "turn passed to Black")
    check(not ns.over, "game continues")


def test_majority_win():
    # total 3 -> majority 2. Red already has 1 capture; capturing an adjacent
    # iceberg reaches 2 and wins, via apply_move.
    s = IceState(size=5, total=3, captures=[1, 0], to_move=RED,
                 ships={(0, 0): RED}, icebergs=frozenset({(1, 0)}))
    ns = G.apply_move(s, "0,0>1,0")
    check(ns.over, "game over on majority")
    check(ns.winner == RED, f"Red wins, got {ns.winner}")
    check(G.returns(ns) == [1.0, -1.0], "returns for Red win")


def test_serialize_roundtrip():
    s = G.initial_state()
    s = G.apply_move(s, G.legal_moves(s)[0])
    d = G.serialize(s)
    s2 = G.deserialize(d)
    check(s2.ships == s.ships, "ships round-trip")
    check(s2.icebergs == s.icebergs, "icebergs round-trip")
    check(s2.captures == s.captures and s2.to_move == s.to_move, "scalars round-trip")
    check(G.serialize(s2) == d, "re-serialize stable")


def test_termination():
    s = G.initial_state()
    cap = G._ply_cap(5)
    steps = 0
    while not G.is_terminal(s) and steps < cap + 5:
        lm = G.legal_moves(s)
        check(lm, "a non-terminal position has legal moves")
        # Greedy: prefer a capturing move so the game makes real progress.
        pick = next((m for m in lm if _cell(m.split(">")[1]) in s.icebergs), lm[0])
        s = G.apply_move(s, pick)
        steps += 1
    check(G.is_terminal(s), "playout reached a terminal state")
    check(steps < cap, f"terminated well under the ply cap ({steps} < {cap})")
    # A real result: a majority winner (greedy capture drives one side to 28).
    if s.winner is not None:
        w = s.winner
        check(s.captures[w] >= G._majority(s) or
              s.captures[w] > s.captures[1 - w], "winner justified")


def test_termination_random_all_sizes():
    # Random legal play on every offered board size terminates well under the
    # cap with an honest, justified result (never a fabricated winner).
    rng = random.Random(2026)
    for size in (4, 5, 6):
        cap = G._ply_cap(size)
        for _ in range(6):
            s = G.initial_state({"size": size})
            steps = 0
            while not G.is_terminal(s):
                lm = G.legal_moves(s)
                check(lm, f"non-terminal has moves (size {size})")
                s = G.apply_move(s, rng.choice(lm))
                steps += 1
                check(steps < cap, f"random play under cap (size {size})")
            check(G.is_terminal(s), f"random playout terminated (size {size})")
            if s.winner is not None:
                w = s.winner
                check(s.captures[w] >= G._majority(s) or
                      s.captures[w] > s.captures[1 - w],
                      f"winner justified (size {size})")
            else:
                check(s.captures[0] == s.captures[1] or
                      s.ply >= cap, "draw only on a tie or the cap")


def _cell(t):
    q, r = t.split(",")
    return int(q), int(r)


def main():
    test_setup()
    test_move_direction_bfs()
    test_tie_two_nearest_icebergs()
    test_no_move_honest_scoring()
    test_must_capture_adjacent()
    test_capture_apply()
    test_majority_win()
    test_serialize_roundtrip()
    test_termination()
    test_termination_random_all_sizes()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
