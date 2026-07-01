"""Pure-stdlib selftest for Nard (Long Nardy).

Anchors (all deterministic; rng seeded / forced):
  * the all-on-the-head starting position (15 on each head, diagonally opposite);
  * dice are uniform pairs 1..6; a double expands to FOUR moves of that value;
  * NO HITTING: a move onto an opponent-occupied point is ILLEGAL (the key
    distinguishing rule vs backgammon), and no bar / re-entry exists;
  * the head cap: at most one checker off the head per turn (two on the first
    turn), and the emergent forced-two-off-head on an opening double 3/4/6;
  * the "must use both dice if possible" rule on a constructed position;
  * bearing off from the home quadrant, incl. the overshoot-from-highest rule;
  * the win at 15 borne off, reached via apply_move, for BOTH players;
  * serialize round-trip (incl. dice / off / first_turn / head_moved);
  * a seeded random playout terminates with a winner.

Run: PYTHONPATH=. python3 games/nard/selftest.py
"""

import json
import random
import sys

from games.nard.game import (
    Nard, NardState, WHITE, BLACK, NCHK, HEAD, PATHS, INDEX,
)


class FixedDice(random.Random):
    """rng whose randint(1,6) cycles a forced list (deterministic rolls)."""
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


def st(board, dice, to_move=WHITE, off=None, roll=None,
       first_turn=None, head_moved=0):
    return NardState(
        board=dict(board),
        off=off or {WHITE: 0, BLACK: 0},
        roll=tuple(roll if roll is not None else dice),
        dice=tuple(dice),
        to_move=to_move,
        first_turn=first_turn or {WHITE: False, BLACK: False},
        head_moved=head_moved,
        ply=0, winner=None,
    )


def main():
    g = Nard()

    # --- 1. all-on-the-head starting position -----------------------------
    s0 = g.initial_state(rng=random.Random(7))
    cnt = {WHITE: 0, BLACK: 0}
    for p, (o, n) in s0.board.items():
        cnt[o] += n
    check(cnt[WHITE] == NCHK and cnt[BLACK] == NCHK, "15 checkers per side")
    check(s0.board == {24: (WHITE, 15), 12: (BLACK, 15)},
          f"both heads fully stacked, opposite corners: {s0.board}")
    check(HEAD[WHITE] == 24 and HEAD[BLACK] == 12, "heads 24 / 12")
    check(s0.to_move == WHITE, "White moves first")
    check(s0.first_turn == {WHITE: True, BLACK: True}, "both first turns")

    # geometry: both paths trace the SAME cyclic direction (p -> p-1 wrap).
    check(PATHS[WHITE][0] == 24 and PATHS[WHITE][-1] == 1, "white path")
    check(PATHS[BLACK][0] == 12 and PATHS[BLACK][-1] == 13, "black path")
    # White home = pip 1..6 = points 1..6; Black home = points 13..18.
    check([g._pip(WHITE, p) for p in (1, 6)] == [1, 6], "white home pips")
    check([g._pip(BLACK, p) for p in (13, 18)] == [1, 6], "black home pips")

    # --- 2. dice distribution & doubles -----------------------------------
    counts = {}
    rng = random.Random(123)
    for _ in range(60000):
        r = g._roll(rng)
        counts[r] = counts.get(r, 0) + 1
    check(len(counts) == 36, f"36 ordered pairs, got {len(counts)}")
    lo, hi = min(counts.values()), max(counts.values())
    check(hi < lo * 1.4, f"pairs roughly uniform ({lo}..{hi})")
    check(g._expand((3, 3)) == (3, 3, 3, 3), "double -> four moves")
    check(g._expand((6, 2)) == (6, 2), "non-double -> two moves")

    # --- 3. NO HITTING (the crux) -----------------------------------------
    # White on 20; a LONE Black checker on 17. White die 3 -> 17 must be ILLEGAL.
    check(PATHS[WHITE][INDEX[WHITE][20] + 3] == 17, "sanity: 20 +3 -> 17")
    s = st({20: (WHITE, 1), 17: (BLACK, 1)}, dice=(3, 4))
    lm = g.legal_moves(s)
    check("20>17" not in lm, f"landing on a lone enemy is ILLEGAL: {lm}")
    check(g._blocked(s.board, WHITE, 17), "17 is blocked for White (any enemy)")
    # the OTHER die (4 -> 16, empty) is fine, and landing on OWN is fine.
    check(PATHS[WHITE][INDEX[WHITE][20] + 4] == 16, "sanity 20 +4 -> 16")
    check("20>16" in lm, f"empty point is legal: {lm}")
    s2 = g.apply_move(s, "20>16", rng=FixedDice([2, 3]))
    check(s2.board.get(17) == (BLACK, 1), "enemy checker NOT hit / removed")
    check(not hasattr(s2, "bar"), "no bar concept in state")

    # fully-blocked -> pass, and passing does not move any checker.
    s = st({8: (WHITE, 1), 5: (BLACK, 1), 2: (BLACK, 1)}, dice=(3, 6))
    # 8 +3 -> 5 (enemy), 8 +6 -> 2 (enemy); both blocked.
    check(g.legal_moves(s) == ["pass"], "no move -> pass")
    s2 = g.apply_move(s, "pass", rng=FixedDice([1, 2]))
    check(s2.board.get(8) == (WHITE, 1), "checker unchanged after pass")
    check(s2.to_move == BLACK, "pass ends the turn")

    # --- 4. head cap ------------------------------------------------------
    # First turn: up to TWO off the head allowed (non-double 3-4).
    s = st({24: (WHITE, 15), 12: (BLACK, 15)}, dice=(3, 4),
           first_turn={WHITE: True, BLACK: True})
    s1 = g.apply_move(s, "24>21", rng=FixedDice([1, 1]))  # 1st off head (die 3)
    check(s1.head_moved == 1 and s1.to_move == WHITE, "one off head, continues")
    check("24>20" in g.legal_moves(s1), "second checker MAY leave head (turn 1)")

    # Non-first turn: only ONE off the head per turn.
    s = st({24: (WHITE, 15), 12: (BLACK, 15)}, dice=(3, 4),
           first_turn={WHITE: False, BLACK: False})
    s1 = g.apply_move(s, "24>21", rng=FixedDice([1, 1]))
    lm = g.legal_moves(s1)
    check(all(not m.startswith("24>") for m in lm),
          f"no second checker off head (non-first turn): {lm}")
    check("21>17" in lm, f"the moved checker keeps going instead: {lm}")

    # Emergent forced-two-off-head on an opening double 3/4/6:
    # a single checker is blocked at the opponent's full head (12 pips away),
    # so using all four dice requires bringing a SECOND checker off the head.
    for d, exp in ((6, 2), (4, 4), (3, 4)):
        s = st({24: (WHITE, 15), 12: (BLACK, 15)}, dice=(d, d, d, d),
               roll=(d, d), first_turn={WHITE: True, BLACK: True})
        check(g._max_usable(s, WHITE, s.dice, 0) == exp,
              f"double {d}: max dice usable = {exp}")
    # double 6: the only opening play is two men 24->18 (18->12 is blocked).
    s = st({24: (WHITE, 15), 12: (BLACK, 15)}, dice=(6, 6, 6, 6),
           roll=(6, 6), first_turn={WHITE: True, BLACK: True})
    check(g.legal_moves(s) == ["24>18"], "double-6 opening: forced 24>18")

    # --- 5. must use both dice if possible --------------------------------
    # White on 22; Black holds 19 (die-3 dest) and 16 (die-6 dest from 22).
    #   die 3: 22->19 BLOCKED; die 6: 22->16 BLOCKED; via 22->? only one path.
    # Simpler forced case: two spare checkers, both dice usable -> max 2.
    s = st({22: (WHITE, 1), 15: (WHITE, 1)}, dice=(2, 5))
    check(g._max_usable(s, WHITE, s.dice, 0) == 2, "both dice usable -> max 2")
    # only-one-usable: single checker whose second step is always blocked.
    #   White on 8; Black walls on 8-3=... use pips: 8 +? Let's block both dests.
    s = st({8: (WHITE, 1), 5: (BLACK, 1), 3: (BLACK, 1)}, dice=(3, 5))
    # 8 +3 -> 5 (enemy) blocked; 8 +5 -> 3 (enemy) blocked; nothing playable.
    check(g._max_usable(s, WHITE, s.dice, 0) == 0, "both blocked -> 0")

    # --- 6. bearing off, incl. overshoot from the highest point -----------
    home = {6: (WHITE, 5), 5: (WHITE, 3), 4: (WHITE, 2),
            3: (WHITE, 2), 2: (WHITE, 2), 1: (WHITE, 1)}
    s = st(home, dice=(6, 1))
    check(g._all_home(s, WHITE), "all White checkers home")
    lm = g.legal_moves(s)
    check("6>off" in lm, "exact bear-off of point 6 with a 6")
    check("1>off" in lm, "exact bear-off of point 1 with a 1")

    # overshoot: highest occupied pip is 4, roll a 6 -> bear off from point 4.
    s = st({4: (WHITE, 1), 2: (WHITE, 1)}, dice=(6, 3))
    lm = g.legal_moves(s)
    check("4>off" in lm, f"overshoot bear-off from highest point: {lm}")
    check("2>off" not in lm, "cannot overshoot from a lower point")
    s2 = g.apply_move(s, "4>off", rng=FixedDice([1, 1]))
    check(s2.off[WHITE] == 1, "one checker borne off")
    check(s2.dice == (3,), "the 6 was consumed, 3 remains")
    check("2>off" in g.legal_moves(s2), "3 now overshoots point 2")

    # --- 7. the win, reached via apply_move (both players) -----------------
    s = st({1: (WHITE, 1)}, dice=(1, 1), off={WHITE: 14, BLACK: 0}, roll=(1, 1))
    check(g._all_home(s, WHITE), "White's last checker is home")
    s2 = g.apply_move(s, "1>off", rng=FixedDice([2, 3]))
    check(s2.winner == WHITE, "White wins on bearing off the 15th")
    check(g.is_terminal(s2) and g.returns(s2) == [1.0, -1.0], "White +1/-1")

    # Black bears off from point 13 (Black's pip-1 point) -> verifies direction.
    check(g._pip(BLACK, 13) == 1, "Black point 13 is pip 1")
    s = st({13: (BLACK, 1)}, dice=(1, 1), to_move=BLACK,
           off={WHITE: 0, BLACK: 14}, roll=(1, 1))
    check(g._all_home(s, BLACK), "Black's last checker is home")
    s2 = g.apply_move(s, "13>off", rng=FixedDice([2, 3]))
    check(s2.winner == BLACK, "Black wins on bearing off the 15th")
    check(g.returns(s2) == [-1.0, 1.0], "Black -1/+1")

    # --- 8. serialize round-trip ------------------------------------------
    s = st({13: (WHITE, 3), 6: (BLACK, 2)}, dice=(4, 2),
           off={WHITE: 5, BLACK: 1}, roll=(4, 2),
           first_turn={WHITE: False, BLACK: True}, head_moved=1)
    blob = json.dumps(g.serialize(s))
    s_rt = g.deserialize(json.loads(blob))
    check(g.serialize(s_rt) == g.serialize(s), "serialize round-trips")
    check(s_rt.first_turn == s.first_turn and s_rt.head_moved == s.head_moved,
          "first_turn / head_moved survive round-trip")

    # --- 9. a seeded random playout terminates with a winner --------------
    for seed in (2024, 7, 99):
        rng = random.Random(seed)
        s = g.initial_state(rng=rng)
        steps = 0
        while not g.is_terminal(s) and steps < 20000:
            m = rng.choice(g.legal_moves(s))
            s = g.apply_move(s, m, rng=rng)
            steps += 1
        check(g.is_terminal(s), f"random playout terminates (seed {seed})")
        check(s.winner in (WHITE, BLACK), "playout has a winner")
        check(s.off[s.winner] >= NCHK or s.ply >= PLY_CAP_OK,
              "winner bore off 15 (or hit the cap)")

    # render sanity: 24 point cells + off, no crash.
    spec = g.render(g.initial_state(rng=random.Random(1)))
    ids = {c["id"] for c in spec["board"]["cells"]}
    check("off" in ids, "render has an off cell")
    check(len([c for c in spec["board"]["cells"] if c["id"].isdigit()]) == 24,
          "render has 24 point cells")

    print("SELFTEST OK")


PLY_CAP_OK = 4000

if __name__ == "__main__":
    main()
