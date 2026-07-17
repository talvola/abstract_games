"""Pure-stdlib selftest for Sáhkku (Vuovdaguoika ruleset).

Anchors: the exact directed tracks for both seats (vuosttut mirrored head-on,
mieđut chasing) incl. never-re-entering the own home row; activation via X
(frontmost-first, advances one sárggis); un-activated soldiers CAN be captured;
king recruitment (ownership flip + push), ramming, recapture-recruit by the
opponent, king uncapturable and moving/capturing as its owner's soldier;
no-cohabitation and the own-army blocking option; blank = move 4; triple-X
rethrow; win by annihilation via apply_move; ply-cap = honest draw [0,0];
serialize round-trip; frozen initial legal-move shape; dice uniformity;
heuristic shape; seeded random playouts to a terminal.

Run: PYTHONPATH=. python3 games/sahkku/selftest.py
"""

import json
import random
import sys

from games.sahkku.game import (Sahkku, SahkkuState, PLY_CAP, FACES, W)

# face indices for FixedDice: 0=X, 1=II, 2=III, 3=blank
X, II, III, B = 0, 1, 2, 3


class FixedDice(random.Random):
    """rng whose randint(0,3) cycles through a forced list of face indices."""

    def __new__(cls, *values):
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


def sld(cell, active=True):
    return {"cell": cell, "active": active}


def stt(g, s0, s1, dice, to_move=0, king=None, ply=0, pattern="vuosttut",
        blocking=True):
    return SahkkuState(
        soldiers={0: [dict(x) for x in s0], 1: [dict(x) for x in s1]},
        king=dict(king or {"cell": (7, 1), "owner": None}),
        roll=tuple(dice), dice=tuple(dice), to_move=to_move, ply=ply,
        winner=None, pattern=pattern, blocking=blocking,
    )


def walk(g, s, pl, start, n):
    out = []
    cur = start
    for _ in range(n):
        cur = g._next_cell(s, pl, cur)
        out.append(cur)
    return out


def main():
    g = Sahkku()

    # --- initial state ------------------------------------------------------
    s = g.initial_state(rng=FixedDice([X, II, III]))
    check(s.roll == ("X", "2", "3"), f"initial roll stored; got {s.roll}")
    check(len(s.soldiers[0]) == 15 and len(s.soldiers[1]) == 15,
          "15 soldiers per side")
    check({x["cell"] for x in s.soldiers[0]} == {(c, 0) for c in range(15)},
          "Red fills home row 0")
    check({x["cell"] for x in s.soldiers[1]} == {(c, 2) for c in range(15)},
          "Blue fills home row 2")
    check(all(not x["active"] for x in s.soldiers[0] + s.soldiers[1]),
          "all soldiers start un-activated")
    check(s.king == {"cell": (7, 1), "owner": None},
          "king starts neutral on the Castle (7,1)")

    # --- frozen initial legal-move shape -----------------------------------
    # dice (X,II,III): nothing is active, so the ONLY move is activating the
    # frontmost soldier (col 14 for Red), which advances it one sárggis into
    # the middle row.
    check(g.legal_moves(s) == ["14,0>14,1"],
          f"initial legal moves = frontmost activation; got {g.legal_moves(s)}")
    # no X and nothing active -> pass
    s2 = g.initial_state(rng=FixedDice([II, III, B]))
    check(g.legal_moves(s2) == ["pass"], "no X + nothing active -> pass only")

    # --- the tracks (vuosttut: mirrored, head-on) ---------------------------
    p0 = walk(g, s, 0, (0, 0), 74)
    exp0 = ([(c, 0) for c in range(1, 15)]            # own home row, rightward
            + [(c, 1) for c in range(14, -1, -1)]     # middle row, leftward
            + [(c, 2) for c in range(0, 15)]          # enemy row, rightward
            + [(c, 1) for c in range(14, -1, -1)]     # loop: middle again
            + [(c, 2) for c in range(0, 15)])         # ... enemy again
    check(p0 == exp0, "Red's directed track is exact")
    check(all(r != 0 for (c, r) in p0[14:]),
          "Red never re-enters its own home row")
    p1 = walk(g, s, 1, (14, 2), 74)
    exp1 = ([(c, 2) for c in range(13, -1, -1)]
            + [(c, 1) for c in range(0, 15)]
            + [(c, 0) for c in range(14, -1, -1)]
            + [(c, 1) for c in range(0, 15)]
            + [(c, 0) for c in range(14, -1, -1)])
    check(p1 == exp1, "Blue's track is the exact mirror (head-on)")
    check(all(r != 2 for (c, r) in p1[14:]),
          "Blue never re-enters its own home row")

    # mieđut: Blue reverses -> both circulate the same way (chase)
    sm = g.initial_state(options={"pattern": "miedut"},
                         rng=FixedDice([X, II, III]))
    pm = walk(g, sm, 1, (0, 2), 44)
    expm = ([(c, 2) for c in range(1, 15)]
            + [(c, 1) for c in range(14, -1, -1)]
            + [(c, 0) for c in range(0, 15)])
    check(pm == expm, "mieđut reverses Blue's directions (chase)")
    check(g.legal_moves(sm) == ["14,0>14,1"], "miedut: Red unchanged")
    sm.to_move = 1
    check(g.legal_moves(sm) == ["14,2>14,1"],
          "miedut: Blue's frontmost is col 14")

    # --- activation: frontmost first, advances one sárggis ------------------
    s = g.initial_state(rng=FixedDice([X, X, X]))
    check(s.dice == ("X", "X", "X"), "forced triple sáhkku")
    check("rethrow" in g.legal_moves(s), "fresh triple X offers rethrow")
    s2 = g.apply_move(s, "14,0>14,1", FixedDice([II, II, II]))
    check(s2.to_move == 0 and s2.dice == ("X", "X"),
          "same player continues; one X consumed")
    check("rethrow" not in g.legal_moves(s2),
          "rethrow only before any die is spent")
    act = [x for x in s2.soldiers[0] if x["active"]]
    check(len(act) == 1 and act[0]["cell"] == (14, 1),
          "activated soldier advanced one sárggis into the middle row")
    mv = g.legal_moves(s2)
    check("13,0>14,0" in mv, "next frontmost (col 13) may now activate")
    check("14,1>13,1" in mv, "an X may instead move an active piece 1")
    check("12,0>13,0" not in mv, "only the frontmost un-activated activates")

    # --- rethrow re-rolls all three dice ------------------------------------
    s3 = g.apply_move(s, "rethrow", FixedDice([II, II, II]))
    check(s3.to_move == 0 and s3.roll == ("2", "2", "2") and
          s3.dice == s3.roll, "rethrow replaced the whole throw")
    check(g.legal_moves(s3) == ["pass"], "the new throw may be unusable")

    # --- blank moves four ---------------------------------------------------
    s = stt(g, [sld((14, 1))], [sld((0, 2), False)], dice=("B",))
    check("14,1>10,1" in g.legal_moves(s), "blank = move 4")

    # --- cohabitation forbidden + blocking option ---------------------------
    s = stt(g, [sld((10, 1)), sld((8, 1))], [sld((0, 2), False)], dice=("2",))
    check("10,1>8,1" not in g.legal_moves(s), "may not land on own soldier")
    s = stt(g, [sld((10, 1)), sld((9, 1))], [sld((0, 2), False)], dice=("2",))
    check("10,1>8,1" not in g.legal_moves(s),
          "blocking on: may not jump an own soldier")
    s.blocking = False
    check("10,1>8,1" in g.legal_moves(s),
          "blocking off (agreed variant): jumping allowed")

    # --- un-activated soldiers CAN be captured ------------------------------
    s = stt(g, [sld((12, 2))], [sld((14, 2), False), sld((0, 2), False)],
            dice=("2",))
    check("12,2>14,2" in g.legal_moves(s), "capture move offered")
    sn = g.apply_move(s, "12,2>14,2", FixedDice([II, II, II]))
    check(len(sn.soldiers[1]) == 1 and sn.soldiers[1][0]["cell"] == (0, 2),
          "a sleeping soldier was captured (Vuovdaguoika)")

    # --- king: recruit + push ----------------------------------------------
    s = stt(g, [sld((9, 1))], [sld((0, 2), False)], dice=("2", "2", "2"))
    check("9,1>7,1" in g.legal_moves(s), "soldier may land on the king")
    sn = g.apply_move(s, "9,1>7,1", FixedDice([II, II, II]))
    check(sn.king == {"cell": (6, 1), "owner": 0},
          "recruited: king now Red's, pushed one sárggis ahead (6,1)")
    check(sn.soldiers[0][0]["cell"] == (7, 1),
          "the recruiting soldier takes the king's old sárggis")
    check(sn.to_move == 0 and sn.dice == ("2", "2"), "turn continues")

    # --- king: ramming ------------------------------------------------------
    s = stt(g, [sld((9, 1))], [sld((6, 1)), sld((0, 2), False)],
            dice=("2",))
    sn = g.apply_move(s, "9,1>7,1", FixedDice([II, II, II]))
    check(sn.king == {"cell": (6, 1), "owner": 0}, "king pushed onto enemy")
    check(len(sn.soldiers[1]) == 1 and sn.soldiers[1][0]["cell"] == (0, 2),
          "the rammed enemy soldier is captured")
    # push target occupied by an OWN soldier -> the recruit move is illegal
    s = stt(g, [sld((9, 1)), sld((6, 1))], [sld((0, 2), False)], dice=("2",))
    check("9,1>7,1" not in g.legal_moves(s),
          "cannot recruit if the push lands on your own soldier")

    # --- king: recapture-recruit by the opponent (and never captured) -------
    s = stt(g, [sld((7, 1)), sld((0, 0), False)], [sld((4, 1))],
            dice=("2",), to_move=1, king={"cell": (6, 1), "owner": 0})
    check("4,1>6,1" in g.legal_moves(s), "Blue may land on Red's king")
    sn = g.apply_move(s, "4,1>6,1", FixedDice([II, II, II]))
    check(sn.king == {"cell": (7, 1), "owner": 1},
          "king recruited BACK by Blue and pushed along Blue's track")
    check(len(sn.soldiers[0]) == 1 and sn.soldiers[0][0]["cell"] == (0, 0),
          "the push rammed Red's soldier on (7,1); king itself never captured")

    # --- king may JUMP own soldiers (soldiers may not) ----------------------
    # "The main exception is that, unlike a normal soldier, it may pass
    # (jump) soldiers of its own army."
    s = stt(g, [sld((9, 1)), sld((5, 1))], [sld((0, 2), False)],
            dice=("2",), king={"cell": (6, 1), "owner": 0})
    mv = g.legal_moves(s)
    check("6,1>4,1" in mv,
          "blocking on: the KING jumps an own soldier at (5,1)")
    s = stt(g, [sld((9, 1)), sld((8, 1))], [sld((0, 2), False)],
            dice=("2",), king={"cell": (6, 1), "owner": 0})
    check("9,1>7,1" not in g.legal_moves(s),
          "blocking on: a SOLDIER may not jump its own soldier at (8,1)")
    # ... but the king may never LAND on an own soldier
    s = stt(g, [sld((9, 1)), sld((4, 1))], [sld((0, 2), False)],
            dice=("2",), king={"cell": (6, 1), "owner": 0})
    check("6,1>4,1" not in g.legal_moves(s),
          "the king may not land on an own soldier")

    # --- king moves (and captures) as its owner's soldier -------------------
    s = stt(g, [sld((0, 0), False)], [sld((3, 1)), sld((0, 2), False)],
            dice=("3",), king={"cell": (6, 1), "owner": 0})
    check("6,1>3,1" in g.legal_moves(s),
          "the recruited king moves by the dice like a soldier")
    sn = g.apply_move(s, "6,1>3,1", FixedDice([II, II, II]))
    check(sn.king == {"cell": (3, 1), "owner": 0} and
          len(sn.soldiers[1]) == 1, "the king captures on exact landing")

    # --- win by annihilation via apply_move ---------------------------------
    s = stt(g, [sld((7, 1))], [sld((5, 1))], dice=("2",))
    sn = g.apply_move(s, "7,1>5,1", FixedDice([II, II, II]))
    check(sn.winner == 0, "removing the last enemy soldier wins")
    check(g.is_terminal(sn) and g.returns(sn) == [1.0, -1.0],
          "terminal + returns for the winner")
    check(g.legal_moves(sn) == [], "no moves at terminal")

    # --- ply cap = honest draw [0, 0] --------------------------------------
    s = stt(g, [sld((7, 1))], [sld((0, 2), False)], dice=("2",),
            ply=PLY_CAP - 1)
    sn = g.apply_move(s, "7,1>5,1", FixedDice([II, II, II]))
    check(sn.winner == "draw", "ply cap reached -> draw")
    check(g.is_terminal(sn) and g.returns(sn) == [0.0, 0.0],
          "the cap is an honest draw, not a fabricated winner")

    # --- serialize round-trip ----------------------------------------------
    s = stt(g, [sld((7, 1)), sld((3, 0), False)],
            [sld((12, 1)), sld((0, 2), False)], dice=("X", "B"),
            to_move=1, king={"cell": (4, 1), "owner": 1})
    d = g.serialize(s)
    check(g.serialize(g.deserialize(d)) == d, "serialize round-trips")
    json.dumps(d)
    sn = g.apply_move(stt(g, [sld((7, 1))], [sld((0, 2), False)],
                          dice=("2",), ply=PLY_CAP - 1),
                      "7,1>5,1", FixedDice([II]))
    d = g.serialize(sn)
    check(g.deserialize(d).winner == "draw", "draw serializes")
    json.dumps(d)

    # --- dice are uniform over the four faces -------------------------------
    rng = random.Random(999)
    counts = {f: 0 for f in FACES}
    N = 20000
    for _ in range(N):
        for f in Sahkku._roll(rng):
            counts[f] += 1
    for f in FACES:
        frac = counts[f] / (3 * N)
        check(abs(frac - 0.25) < 0.01, f"die face {f}: {frac:.4f} ~ 0.25")

    # --- heuristic shape ----------------------------------------------------
    h = g.heuristic(g.initial_state(rng=FixedDice([X, II, III])))
    check(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9,
          "heuristic returns a 2-payoff list")
    check(all(-1.0 <= v <= 1.0 for v in h), "heuristic bounded")

    # --- seeded random playouts terminate -----------------------------------
    for seed in range(20):
        rng = random.Random(seed)
        opts = {"pattern": "miedut"} if seed % 4 == 0 else None
        if seed % 5 == 0:
            opts = {"blocking": "off"}
        s = g.initial_state(options=opts, rng=rng)
        steps = 0
        while not g.is_terminal(s):
            mvs = g.legal_moves(s)
            check(len(mvs) >= 1, "non-terminal always has a move")
            s = g.apply_move(s, rng.choice(mvs), rng)
            steps += 1
            check(steps < PLY_CAP + 10, "playout terminates")
        check(s.winner in (0, 1, "draw"), "playout ends win or honest draw")
        check(len(g.returns(s)) == 2, "returns well-formed")
        check(len(s.soldiers[0]) <= 15 and len(s.soldiers[1]) <= 15,
              "no soldier duplication")
        check(s.king["cell"][1] in (0, 1, 2) and 0 <= s.king["cell"][0] < W,
              "exactly one king, always on the board")

    # --- render spec sanity -------------------------------------------------
    spec = g.render(g.initial_state(rng=FixedDice([X, II, III])))
    check(spec["board"]["type"] == "square" and spec["board"]["width"] == 15
          and spec["board"]["height"] == 3, "3x15 square board")
    check(len(spec["pieces"]) == 31, "30 soldiers + the king")
    kings = [p for p in spec["pieces"] if p.get("glyph") == "♚"]
    check(len(kings) == 1 and "fill" in kings[0],
          "neutral king rendered with a distinct glyph + neutral fill")
    check(sum(1 for p in spec["pieces"] if p.get("label") == "·") == 30,
          "un-activated soldiers carry the sleeping marker")
    json.dumps(spec)

    print("sahkku selftest: all tests passed")


if __name__ == "__main__":
    main()
