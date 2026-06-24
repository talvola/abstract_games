"""Pure-stdlib selftest for Backgammon.

Anchors (all deterministic; rng seeded / forced):
  * standard starting position: exact per-point counts, 15 checkers a side;
  * dice are uniform pairs 1..6; a double expands to FOUR moves of that value;
  * a hit sends an enemy blot to the bar (constructed via apply_move);
  * a player on the bar MUST enter first (no other move is offered);
  * bearing off from the home quadrant, incl. the overshoot-from-highest rule;
  * the "must use both dice if possible" rule on a constructed position;
  * the win at 15 borne off, reached via apply_move;
  * serialize round-trip (incl. dice / bar / off);
  * a seeded random playout terminates with a winner.

Run: PYTHONPATH=. python3 games/backgammon/selftest.py
"""

import json
import random
import sys

from games.backgammon.game import (
    Backgammon, BgState, WHITE, BLACK, NCHK, _start_points,
)


class FixedDice(random.Random):
    """rng whose randint(1,6) cycles a forced list (so rolls are deterministic)."""
    def __new__(cls, *a, **k):
        return super().__new__(cls)

    def __init__(self, values):
        super().__init__()
        self._vals = list(values)
        self._i = 0

    def randint(self, a, b):
        v = self._vals[self._i % len(self._vals)]
        self._i += 1
        return v


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


def st(board, dice, to_move=WHITE, bar=None, off=None, roll=None):
    return BgState(
        board=dict(board),
        bar=bar or {WHITE: 0, BLACK: 0},
        off=off or {WHITE: 0, BLACK: 0},
        roll=tuple(roll if roll is not None else dice),
        dice=tuple(dice),
        to_move=to_move, ply=0, winner=None,
    )


def main():
    g = Backgammon()

    # --- 1. standard starting position ------------------------------------
    s0 = g.initial_state(rng=random.Random(7))
    cnt = {WHITE: 0, BLACK: 0}
    for p, (o, n) in s0.board.items():
        cnt[o] += n
    check(cnt[WHITE] == NCHK and cnt[BLACK] == NCHK, "15 checkers per side")
    white = {p: n for p, (o, n) in s0.board.items() if o == WHITE}
    check(white == {24: 2, 13: 5, 8: 3, 6: 5}, f"white start {white}")
    black = {p: n for p, (o, n) in s0.board.items() if o == BLACK}
    check(black == {1: 2, 12: 5, 17: 3, 19: 5}, f"black start {black}")
    check(s0.to_move == WHITE, "White moves first")

    # --- 2. dice distribution & doubles -----------------------------------
    counts = {}
    rng = random.Random(123)
    for _ in range(60000):
        r = g._roll(rng)
        counts[r] = counts.get(r, 0) + 1
    check(len(counts) == 36, f"36 ordered pairs seen, got {len(counts)}")
    lo, hi = min(counts.values()), max(counts.values())
    check(hi < lo * 1.4, f"pairs roughly uniform ({lo}..{hi})")
    check(g._expand((3, 3)) == (3, 3, 3, 3), "double -> four moves")
    check(g._expand((6, 2)) == (6, 2), "non-double -> two moves")

    # --- 3. a hit sends a blot to the bar ---------------------------------
    # White on point 6, a lone Black blot on point 3; White plays 6>3, die 3.
    s = st({6: (WHITE, 1), 3: (BLACK, 1)}, dice=(3, 4))
    check("6>3" in g.legal_moves(s), "6>3 legal (hitting a blot)")
    s2 = g.apply_move(s, "6>3", rng=FixedDice([1, 1]))
    check(s2.board.get(3) == (WHITE, 1), "White now holds point 3")
    check(s2.bar[BLACK] == 1, "Black blot sent to the bar")
    check(s2.to_move == WHITE and s2.dice == (4,), "same player, die 4 remains")

    # --- 4. on the bar MUST enter first -----------------------------------
    # White has a checker on the bar AND one on point 13; only entry is offered.
    s = st({13: (WHITE, 1)}, dice=(2, 5), bar={WHITE: 1, BLACK: 0})
    lm = g.legal_moves(s)
    # White enters into Black's home (points 19..24): die 2 -> 23, die 5 -> 20.
    check(set(lm) == {"bar>23", "bar>20"}, f"only bar entries offered: {lm}")
    check(all(m.startswith("bar>") for m in lm), "every move enters from bar")

    # entry blocked when the entry point is held by 2+ enemy checkers.
    s = st({23: (BLACK, 2), 13: (WHITE, 1)}, dice=(2, 6),
           bar={WHITE: 1, BLACK: 0})
    lm = g.legal_moves(s)
    # die 2 -> 23 is blocked; die 6 -> 19 is open.
    check(lm == ["bar>19"], f"blocked entry filtered: {lm}")

    # --- 5. bearing off, incl. overshoot from the highest point -----------
    # All 15 White home: build an exact-bearing position.
    home = {6: (WHITE, 5), 5: (WHITE, 3), 4: (WHITE, 2),
            3: (WHITE, 2), 2: (WHITE, 2), 1: (WHITE, 1)}
    s = st(home, dice=(6, 1))
    check(g._all_home(s, WHITE), "all White checkers home")
    lm = g.legal_moves(s)
    check("6>off" in lm, "exact bear-off of point 6 with a 6")
    check("1>off" in lm, "exact bear-off of point 1 with a 1")

    # overshoot: highest occupied point is 4, roll a 6 -> may bear off from 4.
    s = st({4: (WHITE, 1), 2: (WHITE, 1)}, dice=(6, 3))
    lm = g.legal_moves(s)
    check("4>off" in lm, f"overshoot bear-off from highest point: {lm}")
    # but a 6 may NOT bear off the point-2 checker while point 4 is occupied.
    check("2>off" not in lm, "cannot overshoot from a lower point")
    s2 = g.apply_move(s, "4>off", rng=FixedDice([1, 1]))
    check(s2.off[WHITE] == 1, "one checker borne off")
    check(s2.dice == (3,), "the 6 was consumed, 3 remains")
    # now point 2 is highest; the 3 may overshoot-bear-off point 2.
    check("2>off" in g.legal_moves(s2), "3 now overshoots point 2")

    # --- 6. must use both dice if possible --------------------------------
    # Classic case: only ONE checker, dice (6,5). Playing the 6 first strands the
    # 5; playing the 5 first lets the 6 follow. The rule must force the order that
    # uses BOTH. White checker on point 13: 13->8 (5), 8->2 (6) works;
    # 13->7 (6) then 7->2 (5) also works, so both orders use both here -- choose a
    # position where only one order works.
    # White on point 8, Black walls on 2 (point 8-6) and 3 (point 8-5):
    #   die 6: 8->2 blocked (Black holds 2). die 5: 8->3 blocked.
    # Use a cleaner forced-order case:
    # White on 13; Black holds point 8 (2 checkers) and point 2 (2 checkers).
    #   dice (5,6): 13->8 (5) BLOCKED, 13->7 (6) ok then 7->2 (5) BLOCKED.
    # So with this checker neither full sequence works -> only the 6 is usable,
    # and the rule says play the larger (the 6) when only one die can be played.
    s = st({13: (WHITE, 1), 8: (BLACK, 2), 2: (BLACK, 2)}, dice=(5, 6))
    target = g._max_usable(s, WHITE, s.dice)
    check(target == 1, f"only one die usable here, got max={target}")
    lm = g.legal_moves(s)
    # 13->8 is blocked (die 5); the only legal play is the 6: 13->7.
    check(lm == ["13>7"], f"must play the larger (only) die: {lm}")

    # And a position where BOTH dice are usable forbids a 1-die play:
    s = st({13: (WHITE, 2)}, dice=(5, 6))
    check(g._max_usable(s, WHITE, s.dice) == 2, "both dice usable -> max 2")

    # --- 7. the win, reached via apply_move -------------------------------
    # White has 14 off and a single checker on point 1; rolling any die bears it
    # off for the win.
    s = st({1: (WHITE, 1)}, dice=(1, 1), off={WHITE: 14, BLACK: 0},
           roll=(1, 1))
    check(g._all_home(s, WHITE), "the last checker is home")
    s2 = g.apply_move(s, "1>off", rng=FixedDice([2, 3]))
    check(s2.winner == WHITE, "White wins on bearing off the 15th")
    check(g.is_terminal(s2), "terminal after the win")
    check(g.returns(s2) == [1.0, -1.0], "returns +1/-1")

    # --- 8. serialize round-trip ------------------------------------------
    s = st({13: (WHITE, 3), 6: (BLACK, 2)}, dice=(4, 2),
           bar={WHITE: 1, BLACK: 2}, off={WHITE: 5, BLACK: 1}, roll=(4, 2))
    blob = json.dumps(g.serialize(s))
    s_rt = g.deserialize(json.loads(blob))
    check(g.serialize(s_rt) == g.serialize(s), "serialize round-trips")
    check(s_rt.bar == s.bar and s_rt.off == s.off and s_rt.dice == s.dice,
          "bar/off/dice survive round-trip")

    # --- 9. a seeded random playout terminates with a winner --------------
    rng = random.Random(2024)
    s = g.initial_state(rng=rng)
    steps = 0
    while not g.is_terminal(s) and steps < 20000:
        m = rng.choice(g.legal_moves(s))
        s = g.apply_move(s, m, rng=rng)
        steps += 1
    check(g.is_terminal(s), "random playout terminates")
    check(s.winner in (WHITE, BLACK), "playout has a winner")
    check(s.off[s.winner] >= NCHK or s.ply >= 4000, "winner bore off 15 (or cap)")

    # render shouldn't crash and must produce polygons cells incl. bar/off.
    spec = g.render(g.initial_state(rng=random.Random(1)))
    ids = {c["id"] for c in spec["board"]["cells"]}
    check({"bar", "off"} <= ids, "render has bar + off cells")
    check(len([c for c in spec["board"]["cells"] if c["id"].isdigit()]) == 24,
          "render has 24 point cells")

    print("all tests passed")


if __name__ == "__main__":
    main()
