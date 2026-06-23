"""YINSH correctness anchor -- pure stdlib, fast.

Run:  PYTHONPATH=. python3 games/yinsh/selftest.py

No published perft exists for YINSH; the anchor is a set of baked rule
assertions verified against the official Kris Burm / Rio Grande rules and the
authoritative 85-point board geometry (Wikipedia, gipf.com, boardspace.net, and
the sharkdp Yinsh reference implementation):

  (1) the 85-point hexagonal lattice + the 3 line directions;
  (2) 5 rings/player, alternating ring-placement setup (10 placements);
  (3) a play move = drop a marker in your ring, slide the ring, jumping the
      first contiguous marker run and FLIPPING every jumped marker; rings block;
  (4) a row of 5 same-colour markers -> remove 5 markers + 1 of your rings;
  (5) WIN = first to remove THREE rings (reached via apply_move).
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from games.yinsh.game import (
    Yinsh, YState, POINTS, POINT_IDS, AXES, _ring_moves, _find_rows, ID,
)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    g = Yinsh()

    # (1) board geometry -----------------------------------------------------
    check(len(POINTS) == 85, f"expected 85 points, got {len(POINTS)}")
    check(len(set(POINTS)) == 85, "points not distinct")
    # column lengths along the three axes are the canonical YINSH profile
    from collections import defaultdict
    byx = defaultdict(int)
    for (x, y) in POINTS:
        byx[x] += 1
    profile = [byx[x] for x in range(-5, 6)]
    check(profile == [4, 7, 8, 9, 10, 9, 10, 9, 8, 7, 4],
          f"column profile wrong: {profile}")
    check(len(AXES) == 3, "must have exactly 3 line directions")
    # the central point exists, the four corners (length-4 column ends) too
    check("0,0" in POINT_IDS, "centre missing")

    # (2) setup phase --------------------------------------------------------
    check(g.RINGS == 5, "5 rings per player")
    st = g.initial_state()
    check(st.phase == "setup" and g.current_player(st) == 0, "white places first")
    check(len(g.legal_moves(st)) == 85, "all 85 points legal for first ring")
    # play 10 alternating placements, check alternation + transition to play
    seq = ["0,0", "1,0", "0,1", "1,1", "0,2", "1,2", "0,3", "1,3", "0,-1", "1,-1"]
    seat = 0
    for i, mv in enumerate(seq):
        check(g.current_player(st) == seat, f"placement {i}: wrong seat")
        st = g.apply_move(st, mv)
        seat = 1 - seat
    check(st.phase == "play", "should be in play phase after 10 placements")
    check(st.placed == [5, 5], "5 rings each placed")
    check(g.current_player(st) == 0, "white moves first in play")
    check(len(st.rings) == 10 and len(st.markers) == 0, "10 rings, no markers")

    # (3a) basic ring slide over empties (no markers => no flips) -------------
    st2 = YState(rings={"0,0": 0}, phase="play", to_move=0)
    dests = set(_ring_moves(st2, "0,0"))
    # a lone ring at centre can reach every other point on its 3 lines
    check("0,1" in dests and "1,0" in dests and "1,1" in dests, "axis slides")
    # move it: a marker is dropped at src, ring goes to dst, nothing flipped
    ns = g.apply_move(st2, "0,0>0,3")
    check(ns.markers.get("0,0") == 0, "marker dropped at source")
    check(ns.rings.get("0,3") == 0 and "0,0" not in ns.rings, "ring moved")
    check(len(ns.markers) == 1, "no extra markers flipped on an empty slide")

    # (3b) jump-and-flip + rings block ---------------------------------------
    # vertical line x=0: ring at 0,0 ; markers (black=1) at 0,1 and 0,2 ; empty 0,3
    st3 = YState(rings={"0,0": 0}, markers={"0,1": 1, "0,2": 1},
                 phase="play", to_move=0)
    md = set(_ring_moves(st3, "0,0"))
    # going +y from 0,0: must jump the run 0,1..0,2 and land on 0,3 ONLY
    check("0,3" in md, "must be able to land just past the marker run")
    check("0,1" not in md and "0,2" not in md, "cannot stop on a marker")
    check("0,4" not in md, "cannot continue sliding after a jump")
    ns3 = g.apply_move(st3, "0,0>0,3")
    check(ns3.markers.get("0,1") == 0 and ns3.markers.get("0,2") == 0,
          "jumped markers must flip 1->0")
    check(ns3.markers.get("0,0") == 0, "dropped marker is the mover's colour")
    # rings block: put an enemy ring beyond the run -> still land 0,3, but a ring
    # at 0,3 must block landing entirely on that axis.
    st4 = YState(rings={"0,0": 0, "0,3": 1}, markers={"0,1": 1, "0,2": 1},
                 phase="play", to_move=0)
    md4 = set(_ring_moves(st4, "0,0"))
    check("0,3" not in md4 and "0,4" not in md4,
          "a ring blocks landing/passing past the run")

    # a ring directly adjacent blocks even an empty slide in that direction
    st5 = YState(rings={"0,0": 0, "0,1": 1}, phase="play", to_move=0)
    md5 = set(_ring_moves(st5, "0,0"))
    check("0,1" not in md5 and "0,2" not in md5, "adjacent ring blocks the line")

    # (4) row of 5 -> remove 5 markers + 1 ring ------------------------------
    # five white markers in a row on x=0 (y=-1..3), a white ring to spend at 1,1
    row_markers = {"0,-1": 0, "0,0": 0, "0,1": 0, "0,2": 0, "0,3": 0}
    check(any(set(r) == set(row_markers) for r in _find_rows(row_markers, 0)),
          "five-in-line not detected as a row")
    check(_find_rows(row_markers, 1) == [], "opponent has no row here")
    st6 = YState(rings={"1,1": 0}, markers=dict(row_markers),
                 phase="play", to_move=0, resolver=0, next_player=1)
    rms = g.legal_moves(st6)
    check(rms, "resolver must have removal moves")
    mv = "R:0,-1>0,0>0,1>0,2>0,3|1,1"
    check(mv in rms, f"expected removal move {mv} in {rms}")
    ns6 = g.apply_move(st6, mv)
    check(all(c not in ns6.markers for c in row_markers), "5 markers removed")
    check("1,1" not in ns6.rings, "one ring removed")
    check(ns6.removed[0] == 1, "removed-ring count incremented")
    check(ns6.resolver is None and ns6.to_move == 1, "turn passes after resolve")

    # six-in-a-line offers multiple windows of five
    six = {f"0,{y}": 0 for y in range(-1, 5)}   # y=-1..4, six markers
    runs = _find_rows(six, 0)
    check(runs and len(runs[0]) == 6, "six-run detected")
    st7 = YState(rings={"3,3": 0}, markers=dict(six),
                 phase="play", to_move=0, resolver=0, next_player=1)
    windows = {tuple(m.split("|")[0][2:].split(">")) for m in g.legal_moves(st7)}
    check(len(windows) == 2, f"six-run should offer 2 windows of five, got {windows}")

    # (5) third-ring-removal WIN reached via apply_move ----------------------
    # White already removed 2 rings; complete a 3rd row to win.
    st8 = YState(rings={"2,2": 0}, markers=dict(row_markers),
                 phase="play", to_move=0, resolver=0, next_player=1,
                 removed=[2, 0])
    ns8 = g.apply_move(st8, "R:0,-1>0,0>0,1>0,2>0,3|2,2")
    check(ns8.removed[0] == 3, "white should have 3 removed rings")
    check(g.is_terminal(ns8), "game must be terminal at 3 rings")
    check(ns8.winner == 0, "white wins")
    check(g.returns(ns8) == [1.0, -1.0], "returns reflect white win")

    # full integration: a complete move that itself forms a row, mover resolves
    # ring at 0,4 ; white markers already at 0,-1..0,2 ; dropping at 0,4 then
    # NOT needed -- instead verify apply_play sets resolver when a row forms.
    st9 = YState(rings={"0,3": 0}, markers={"0,-1": 0, "0,0": 0, "0,1": 0, "0,2": 0},
                 phase="play", to_move=0)
    # drop marker at 0,3 (completes 0,-1..0,3) then slide the ring away up the
    # x=3 ... must move; pick a destination on another axis that doesn't disturb.
    ns9 = g.apply_move(st9, "0,3>3,3")
    check(ns9.markers.get("0,3") == 0, "marker dropped to complete the row")
    check(ns9.resolver == 0, "mover must resolve their freshly-formed row")

    # serialize round-trips
    blob = g.serialize(ns6)
    again = g.serialize(g.deserialize(blob))
    check(blob == again, "serialize must round-trip")

    print("SELFTEST OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("SELFTEST FAILED:", e)
        sys.exit(1)
