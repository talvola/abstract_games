"""Standalone correctness anchor for Tsoro Yematatu.

Pure stdlib: imports only ``agp`` + this game. Run with::

    PYTHONPATH=. python3 games/tsoro_yematatu/selftest.py

There is no published perft for Tsoro Yematatu, so the anchor is a set of baked
rule assertions: the seven-point board adjacency / line set, the place-then-move
phase structure, the three-in-a-row win along a board LINE, a hand-built winning
line, and a legal jump-over-a-piece move (friend and foe). Prints "SELFTEST OK"
and exits 0 on success; raises (nonzero exit) on any failure.
"""

from __future__ import annotations

import sys

from games.tsoro_yematatu.game import (
    TsoroYematatu, TState, ADJ, JUMPS, LINES, POINTS,
)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    g = TsoroYematatu()
    g.initial_state()   # sets PLACEMENT_WIN default

    # (1) Board: exactly 7 points, 5 lines of 3.
    check(len(POINTS) == 7, f"expected 7 points, got {len(POINTS)}")
    check(set(POINTS) == {"0", "1", "2", "3", "4", "5", "6"}, "unexpected point ids")
    check(len(LINES) == 5, f"expected 5 lines, got {len(LINES)}")
    for ln in LINES:
        check(len(ln) == 3, f"line {ln} is not a triple")
        check(len(set(ln)) == 3, f"line {ln} has a repeat")

    # Adjacency baked from the canonical figure:
    #   apex 0 -> 1,2,3 ; centre 2 -> 0,1,3,5 ; base corner 4 -> 1,5
    expected_adj = {
        "0": {"1", "2", "3"},
        "1": {"0", "2", "4"},
        "2": {"0", "1", "3", "5"},
        "3": {"0", "2", "6"},
        "4": {"1", "5"},
        "5": {"2", "4", "6"},
        "6": {"3", "5"},
    }
    for p in POINTS:
        check(set(ADJ[p]) == expected_adj[p],
              f"adjacency of {p} wrong: {set(ADJ[p])} != {expected_adj[p]}")
    # apex really connects to the two upper-mid points (1 and 3) and the axis (2)
    check({"1", "3"} <= set(ADJ["0"]), "apex must connect to the two upper-mid points")
    # adjacency is symmetric
    for p in POINTS:
        for q in ADJ[p]:
            check(p in ADJ[q], f"adjacency not symmetric: {p}-{q}")

    # (2) Placement phase: each player places exactly 3 men, alternating, before
    #     any movement is possible.
    st = g.initial_state()
    check(g.current_player(st) == 0, "player 0 should start")
    # A neutral filling that leaves NEITHER side with a completed line (so the
    # game continues into the movement phase). P0 -> {0,4,6}, P1 -> {1,2,5}.
    seq = ["0", "1", "4", "2", "6", "5"]
    movers = []
    for mv in seq:
        movers.append(g.current_player(st))
        # during placement every legal move is a single empty point (no '>')
        legal = g.legal_moves(st)
        check(all(">" not in m for m in legal), "placement legal moves must be single points")
        check(mv in legal, f"placement {mv} should be legal")
        st = g.apply_move(st, mv)
    check(movers == [0, 1, 0, 1, 0, 1], f"placement turn order wrong: {movers}")
    check(st.placed == [3, 3], f"each player should have placed 3, got {st.placed}")
    check(g._both_placed(st), "both should be fully placed")
    # now we are in the movement phase: moves are from>to
    legal = g.legal_moves(st)
    check(legal, "movement phase should have legal moves")
    check(all(">" in m for m in legal), "movement moves should be from>to")
    check(not g.is_terminal(st), "not terminal mid-game")

    # (3) Three-in-a-row along a board LINE wins (formed in movement phase).
    #     Hand-build a movement position where P0 completes the midline 1-2-3.
    #     P0 at 1 and 3, with a man at 0 that can slide down the axis to 2.
    #     P1 men parked off the line.
    st = TState(pos={"1": 0, "3": 0, "0": 0, "4": 1, "6": 1, "5": 1},
                to_move=0, placed=[3, 3], plies=6, no_progress=0, winner=None)
    check(not g.is_terminal(st), "constructed movement state should not be terminal yet")
    check(not g._has_line({"1": 0, "3": 0, "0": 0}, 0), "no line yet for P0")
    # 0>2 slides apex down the axis to the centre, completing 1-2-3
    check("0>2" in g.legal_moves(st), "0>2 slide should be legal")
    ns = g.apply_move(st, "0>2")
    check(ns.winner == 0, f"P0 should win by completing the midline, winner={ns.winner}")
    check(g.is_terminal(ns), "win state must be terminal")
    check(g.returns(ns) == [1.0, -1.0], f"returns wrong: {g.returns(ns)}")
    # win-line detection covers every board line
    for line in LINES:
        pos = {p: 0 for p in line}
        check(g._has_line(pos, 0), f"{line} should be a recognised win line")

    # (4a) A legal JUMP over an ENEMY piece (no capture): from 4, over 5(enemy),
    #      land on empty 6.
    st = TState(pos={"4": 0, "5": 1}, to_move=0, placed=[3, 3],
                plies=6, no_progress=2, winner=None)
    check("4>6" in g.legal_moves(st), "jump 4 over enemy 5 to 6 should be legal")
    ns = g.apply_move(st, "4>6")
    check(ns.pos.get("6") == 0, "jumper should land on 6")
    check(ns.pos.get("5") == 1, "jumped ENEMY man must remain (no capture)")
    check("4" not in ns.pos, "jumper vacates its start")

    # (4b) A legal JUMP over a FRIENDLY piece: from 4, over 5(friend), land on 6.
    st = TState(pos={"4": 0, "5": 0}, to_move=0, placed=[3, 3],
                plies=6, no_progress=2, winner=None)
    check("4>6" in g.legal_moves(st), "jump over friendly piece should be legal")
    ns = g.apply_move(st, "4>6")
    check(ns.pos.get("5") == 0, "jumped FRIENDLY man must remain (no capture)")

    # (4c) Jump is illegal when the landing point is occupied; slide illegal into
    #      an occupied point.
    st = TState(pos={"4": 0, "5": 1, "6": 1}, to_move=0, placed=[3, 3],
                plies=6, no_progress=2, winner=None)
    check("4>6" not in g.legal_moves(st), "jump onto an occupied point must be illegal")
    check("4>5" not in g.legal_moves(st), "slide onto an occupied point must be illegal")
    # and a jump needs an occupied middle: 4 cannot jump to 6 over an EMPTY 5
    st = TState(pos={"4": 0}, to_move=0, placed=[3, 3], plies=6, no_progress=2)
    check("4>6" not in g.legal_moves(st), "cannot 'jump' over an empty point")
    check("4>5" in g.legal_moves(st), "4 should slide to adjacent empty 5")

    # JUMPS table consistency: only the two endpoints of each line jump over the
    # middle, and onto each other.
    check(JUMPS["4"].get("5") == "6" and JUMPS["6"].get("5") == "4",
          "base line jumps wrong")
    check(JUMPS["0"].get("2") == "5" and JUMPS["5"].get("2") == "0",
          "axis jumps wrong")

    # (5) Placement-phase line does NOT win under the standard (default) rule.
    g2 = TsoroYematatu()
    g2.initial_state({"placement_win": "no"})
    st = g2.initial_state({"placement_win": "no"})
    for mv in ["1", "5", "2", "4", "3"]:   # P0 about to complete 1-2-3 on placement
        st = g2.apply_move(st, mv)
    check(st.winner is None, "standard rule: completing a line during placement must NOT win")
    check(st.placed == [3, 2], "P0 placed all three, P1 two")

    # And with the option ON, the same placement line wins immediately.
    g3 = TsoroYematatu()
    g3.initial_state({"placement_win": "yes"})
    st = g3.initial_state({"placement_win": "yes"})
    for mv in ["1", "5", "2", "4"]:
        st = g3.apply_move(st, mv)
    check(st.winner is None, "no line completed yet")
    st = g3.apply_move(st, "3")            # completes 1-2-3 for P0 during placement
    check(st.winner == 0, "placement_win=yes: completing a line during placement should win")

    # (6) serialize / deserialize round-trips.
    st = TState(pos={"4": 0, "5": 1}, to_move=1, placed=[3, 3],
                plies=7, no_progress=1, winner=None)
    again = g.deserialize(g.serialize(st))
    check(g.serialize(again) == g.serialize(st), "serialize must round-trip")

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
