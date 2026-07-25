"""Standalone correctness anchor for Layli Goobalay.

Run with:  PYTHONPATH=. python3 games/layli_goobalay/selftest.py

Pure stdlib + this game only.  Prints "SELFTEST OK" and exits 0 on success.

THE ANCHOR
==========
*Abstract Games* issue 13 (Spring 2003) prints one endgame problem (printed
page 14) with a full published solution (printed page 29).  The problem is a
FIGURE, so the position below was pixel-read from the PDF at 600 dpi:

    page TOP row,    left -> right:  3 0 3 0 1 2 0 1 5 2 2 2     "=24" captured
    page BOTTOM row, left -> right:  3 0 1 0 0 0 0 0 0 0 2 1     "=44" captured
    a "U" sits over page column 10 (0-indexed); the Uur is that WHOLE COLUMN
    (both holes hold 2), and the caption says NORTH made it.

Conservation check on the pixel-read: 21 + 7 on the board + 24 + 44 captured
= 96 = 24 holes x 4 balls.  (An off-by-one misread would break this.)

Published solution, verbatim:

    South to move: 10/9*/1U/8/12/1/11.  North must play into South's Uur, so
    South wins by one point.  *If 1 (instead of 9), then 11U/2/1/1, and South
    wins.  North to move: 1/12/4 (x2)/10(x3)/1, and North wins by two points.

THREE conventions are NOT stated by the article and are brute-forced here
(test_pin_conventions): the sowing direction relative to the printed diagram,
the hole-numbering origin ("1 = each player's right" -- but which printed end is
whose right?), and which printed row is South.  All 2x2x2 = 8 combinations (=
all four reflections of the diagram x both row labellings) are replayed against
all three published lines; EXACTLY ONE survives, and it is the one this package
implements.

ERRATUM (see rules.md): the published "South wins by one point" is impossible --
96 balls are conserved, so every margin is even.  Under the surviving convention
South wins by TWO.  The other two published claims ("North wins by two points",
and every North reply being forced into South's Uur) reproduce EXACTLY.
"""

from __future__ import annotations

import random
import sys

from games.layli_goobalay.game import (
    LayliGoobalay, LayliState, SOUTH, NORTH, SEEDS_PER_HOLE,
    hole_number, pit_of_number, ring,
)

G = LayliGoobalay()
W = 12

# --- the pixel-read problem position, in PAGE orientation --------------------
PAGE_TOP = [3, 0, 3, 0, 1, 2, 0, 1, 5, 2, 2, 2]
PAGE_BOT = [3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 2, 1]
PAGE_TOP_CAPTURED = 24
PAGE_BOT_CAPTURED = 44
UUR_PAGE_COL = 10          # 0-indexed; the "U" marks this column, both rows

# --- the published solution, as (player, hole, expected annotation) ----------
# player 0 = South (the side the article labels South), 1 = North.
SOUTH_LINE = [(0, 10, None), (1, 9, None), (0, 1, "U"), (1, 8, None),
              (0, 12, None), (1, 1, None), (0, 11, None)]
SOUTH_VAR = [(0, 10, None), (1, 1, None), (0, 11, "U"), (1, 2, None),
             (0, 1, None), (1, 1, None)]
NORTH_LINE = [(1, 1, None), (0, 12, None), (1, 4, "x2"), (0, 10, "x3"),
              (1, 1, None)]


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


# ---------------------------------------------------------------------------
# Convention machinery.  `mirror_rows` picks which printed row is South;
# `numbering` picks the hole-numbering origin; `direction` is the game option.
# ---------------------------------------------------------------------------
def problem_state(mirror_rows: bool, direction: str, to_move: int) -> LayliState:
    """Build the printed position with South placed on engine row 0."""
    if not mirror_rows:                     # South = printed BOTTOM row
        south_row, north_row = PAGE_BOT, PAGE_TOP
        captured = [PAGE_BOT_CAPTURED, PAGE_TOP_CAPTURED]
        uur_owner = NORTH                   # the Uur sits on the printed TOP side
    else:                                   # South = printed TOP row
        south_row, north_row = PAGE_TOP, PAGE_BOT
        captured = [PAGE_TOP_CAPTURED, PAGE_BOT_CAPTURED]
        uur_owner = SOUTH
    board = {}
    for c in range(W):
        board[(c, SOUTH)] = south_row[c]
        board[(c, NORTH)] = north_row[c]
    uur = {(UUR_PAGE_COL, SOUTH): uur_owner, (UUR_PAGE_COL, NORTH): uur_owner}
    return LayliState(board=board, uur=uur, captured=list(captured),
                      to_move=to_move, width=W, direction=direction,
                      ply=40, no_progress=0)


def decode(player: int, hole: int, numbering: int):
    """hole 1..12 -> engine pit, under numbering convention 0 (the package's
    own: each player counts from HIS right) or 1 (the mirror image)."""
    if numbering == 0:
        return pit_of_number(player, hole, W)
    return (hole - 1, SOUTH) if player == SOUTH else (W - hole, NORTH)


def replay(line, mirror_rows, direction, numbering):
    """Returns (state, log) or raises AssertionError-ish via a returned error."""
    s = problem_state(mirror_rows, direction, line[0][0])
    log = []
    for (pl, hole, expect) in line:
        if s.to_move != pl:
            return None, log, "side to move %d, expected %d" % (s.to_move, pl)
        pit = decode(pl, hole, numbering)
        mv = "%d,%d" % pit
        if mv not in G.legal_moves(s):
            return None, log, "illegal move %s%d (%s)" % ("SN"[pl], hole, mv)
        kind = G.describe_move(s, mv).split(" ", 2)[-1]
        kind = kind[len(str(hole)):] if kind.startswith(str(hole)) else kind
        s = G.apply_move(s, mv)
        log.append(("SN"[pl] + str(hole) + kind))
        total = sum(s.board.values()) + sum(s.captured)
        if total != 2 * W * SEEDS_PER_HOLE:
            return None, log, "balls not conserved: %d" % total
        if expect is not None and kind != expect:
            return None, log, "%s%d gave %r, published %r" % (
                "SN"[pl], hole, kind, expect)
    return s, log, None


# ---------------------------------------------------------------------------
# 1.  Pin the three undocumented conventions by brute force.
# ---------------------------------------------------------------------------
def test_pin_conventions():
    survivors = []
    for mirror_rows in (False, True):
        for direction in ("clockwise", "anticlockwise"):
            for numbering in (0, 1):
                ok = True
                for line in (SOUTH_LINE, SOUTH_VAR, NORTH_LINE):
                    _, _, err = replay(line, mirror_rows, direction, numbering)
                    if err:
                        ok = False
                        break
                if ok:
                    survivors.append((mirror_rows, direction, numbering))
    check(survivors == [(False, "clockwise", 0)],
          "convention brute force: expected exactly the package's own "
          "convention to survive all 8, got %r" % (survivors,))


# ---------------------------------------------------------------------------
# 2.  Replay the published solution under that convention.
# ---------------------------------------------------------------------------
CONV = dict(mirror_rows=False, direction="clockwise", numbering=0)


def test_south_line():
    s, log, err = replay(SOUTH_LINE, **CONV)
    check(err is None, "South line: %s (log %s)" % (err, log))
    check(log == ["S10", "N9", "S1U", "N8", "S12", "N1", "S11"],
          "South line notation mismatch: %s" % (log,))
    # "North must play into South's Uur"
    check(s.to_move == NORTH, "North should be to move")
    moves = G.legal_moves(s)
    check(len(moves) == 8, "expected 8 North replies, got %d" % len(moves))
    south_uur = {p for p, o in s.uur.items() if o == SOUTH}
    check(len(south_uur) == 2, "South should own exactly one Uur (2 holes)")
    for mv in moves:
        after = G.apply_move(s, mv)
        # every reply must (a) capture nothing, (b) leave more balls in South's
        # Uur than before -- i.e. it died inside South's Uur.
        check(after.captured == s.captured, "North reply %s captured!" % mv)
        gain = (sum(after.board[p] for p in south_uur)
                - sum(s.board[p] for p in south_uur))
        check(gain > 0, "North reply %s did not feed South's Uur" % mv)
    # margin
    sc = G.scores(s)
    check(sc == [49, 47], "score after the South line = %s, expected [49, 47]" % sc)
    check(sc[0] - sc[1] == 2,
          "South's margin should be 2 (the magazine's 'one point' is impossible: "
          "96 balls are conserved so every margin is even)")


def test_south_variation():
    s, log, err = replay(SOUTH_VAR, **CONV)
    check(err is None, "South variation: %s (log %s)" % (err, log))
    check(log == ["S10", "N1", "S11U", "N2", "S1", "N1"],
          "South variation notation mismatch: %s" % (log,))
    check(G.is_terminal(s), "South variation should end the game")
    check(s.to_move == SOUTH and G.legal_moves(s) == [],
          "South should be the player left without a move")
    sc = G.scores(s)
    check(sc == [49, 47], "variation score %s, expected [49, 47]" % sc)
    check(G.returns(s) == [1.0, -1.0], "'South wins' not reproduced")


def test_north_line():
    s, log, err = replay(NORTH_LINE, **CONV)
    check(err is None, "North line: %s (log %s)" % (err, log))
    check(log == ["N1", "S12", "N4x2", "S10x3", "N1"],
          "North line notation mismatch: %s" % (log,))
    check(G.is_terminal(s), "North line should end the game")
    check(s.to_move == SOUTH and G.legal_moves(s) == [],
          "South should be the player left without a move")
    sc = G.scores(s)
    check(sc == [47, 49], "North line score %s, expected [47, 49]" % sc)
    check(sc[1] - sc[0] == 2, "'North wins by two points' not reproduced")
    check(G.returns(s) == [-1.0, 1.0], "returns wrong at the North line's end")


# ---------------------------------------------------------------------------
# 3.  Second, independent anchor: the opening analysis on Mancala World
#     (Ralf Gering's own fuller write-up of the same article).
#       "After he started with 1, which captures 6 stones ... the opening player
#        can play 5, followed by the forced sequence 3-4-8-11.  After that ...
#        8 makes a Qur, 10 captures 12 stones."
# ---------------------------------------------------------------------------
def test_opening_line():
    s = G.initial_state()
    seq = [(SOUTH, 1, "x6"), (NORTH, 5, ""), (SOUTH, 5, ""), (NORTH, 3, "x9"),
           (SOUTH, 4, "x9"), (NORTH, 8, "x11"), (SOUTH, 11, "x13")]
    for pl, hole, expect in seq:
        check(s.to_move == pl, "opening line: wrong side to move")
        mv = "%d,%d" % pit_of_number(pl, hole, W)
        check(mv in G.legal_moves(s), "opening line: %s%d illegal" % ("SN"[pl], hole))
        kind = G.describe_move(s, mv).split(" ")[-1][len(str(hole)):]
        check(kind == expect, "opening %s%d gave %r, expected %r"
              % ("SN"[pl], hole, kind, expect))
        s = G.apply_move(s, mv)
    # "After that North has no good follow-up, while South has numerous threats
    #  (e.g. 8 makes a Qur, 10 captures 12 stones)" -- these are South THREATS
    #  measured at the position reached, so evaluate them out of turn.
    s = LayliState(board=dict(s.board), uur=dict(s.uur), captured=list(s.captured),
                   to_move=SOUTH, width=s.width, direction=s.direction,
                   ply=s.ply, no_progress=s.no_progress)
    for hole, expect in ((8, "U"), (10, "x12")):
        mv = "%d,%d" % pit_of_number(SOUTH, hole, W)
        check(mv in G.legal_moves(s), "opening line: South %d illegal" % hole)
        kind = G.describe_move(s, mv).split(" ")[-1][len(str(hole)):]
        check(kind == expect,
              "opening alternative South %d gave %r, expected %r" % (hole, kind, expect))


# ---------------------------------------------------------------------------
# 4.  Rule-branch unit tests.
# ---------------------------------------------------------------------------
def blank(width=W, direction="clockwise"):
    return {(c, r): 0 for r in (SOUTH, NORTH) for c in range(width)}


def state(board, uur=None, captured=None, to_move=SOUTH, direction="clockwise"):
    return LayliState(board=dict(board), uur=dict(uur or {}),
                      captured=list(captured or [0, 0]), to_move=to_move,
                      width=W, direction=direction, ply=10, no_progress=0)


def test_ring_geometry():
    cw = ring(W, "clockwise")
    ccw = ring(W, "anticlockwise")
    check(len(cw) == 2 * W and len(set(cw)) == 2 * W, "ring is not a permutation")
    check(cw == list(reversed(ccw)), "the two directions are not reverses")
    # clockwise = North's row left->right, then South's row right->left
    check(cw[:W] == [(c, NORTH) for c in range(W)], "clockwise ring wrong (north)")
    check(cw[W:] == [(c, SOUTH) for c in range(W - 1, -1, -1)],
          "clockwise ring wrong (south)")
    # each player sows his OWN holes in increasing own-hole-number order
    for player in (SOUTH, NORTH):
        nums = [hole_number(p, W) for p in cw if p[1] == player]
        check(nums == list(range(1, W + 1)),
              "hole numbering/direction disagree for player %d: %s" % (player, nums))
    for player in (SOUTH, NORTH):
        for n in range(1, W + 1):
            check(hole_number(pit_of_number(player, n, W), W) == n,
                  "hole_number/pit_of_number are not inverses")


def test_capture_branches():
    # last ball into an empty hole on own side, opposite holds 1/2/4+ -> capture
    for k, want in ((1, 2), (2, 3), (4, 5), (7, 8)):
        b = blank()
        b[(5, SOUTH)] = 1          # sowing clockwise from South 7 (col 5) -> col 4
        b[(4, NORTH)] = k
        s = state(b)
        mv = "5,0"
        check(mv in G.legal_moves(s), "setup: %s not legal" % mv)
        t = G.apply_move(s, mv)
        check(t.captured[SOUTH] == want,
              "opposite=%d should capture %d, got %d" % (k, want, t.captured[SOUTH]))
        check(t.board[(4, SOUTH)] == 0 and t.board[(4, NORTH)] == 0,
              "both holes should be emptied by a capture")
    # opposite empty -> abar, the ball stays put
    b = blank()
    b[(5, SOUTH)] = 1
    t = G.apply_move(state(b), "5,0")
    check(t.captured == [0, 0] and t.board[(4, SOUTH)] == 1, "abar mishandled")
    # last ball into an empty hole on the OPPONENT's side -> abar
    b = blank()
    b[(0, SOUTH)] = 1               # clockwise: (0,S) -> (0,N)?  check via ring
    order = ring(W, "clockwise")
    nxt = order[(order.index((0, SOUTH)) + 1) % (2 * W)]
    check(nxt[1] == NORTH, "expected the next hole to be on North's side")
    b[nxt] = 0
    t = G.apply_move(state(b), "0,0")
    check(t.captured == [0, 0] and t.board[nxt] == 1, "abar on opponent side wrong")


def test_uur_creation_and_freeze():
    b = blank()
    b[(5, SOUTH)] = 1
    b[(4, NORTH)] = 3
    t = G.apply_move(state(b), "5,0")
    check(t.uur == {(4, SOUTH): SOUTH, (4, NORTH): SOUTH},
          "Uur not created on both holes for the mover: %s" % (t.uur,))
    check(t.board[(4, SOUTH)] == 2 and t.board[(4, NORTH)] == 2,
          "an Uur's two holes must hold 2 balls each")
    check(t.captured == [0, 0], "creating an Uur captures nothing")
    # neither player may start a move from an Uur hole
    u = {(4, SOUTH): NORTH, (4, NORTH): NORTH}
    b = blank()
    b[(4, SOUTH)] = 9
    b[(4, NORTH)] = 9
    b[(0, SOUTH)] = 1
    b[(0, NORTH)] = 1
    for pl in (SOUTH, NORTH):
        s = state(b, uur=u, to_move=pl)
        check("4,%d" % pl not in G.legal_moves(s),
              "player %d was allowed to empty an Uur" % pl)
    # sowing DOES drop balls into an Uur, and carries straight on past it
    b = blank()
    b[(6, SOUTH)] = 3               # clockwise: 6,S -> 5,S -> 4,S -> 3,S
    u = {(4, SOUTH): NORTH, (4, NORTH): NORTH}
    b[(4, SOUTH)] = 2
    b[(4, NORTH)] = 2
    t = G.apply_move(state(b, uur=u), "6,0")
    check(t.board[(5, SOUTH)] == 1, "the hole before the Uur missed its ball")
    check(t.board[(4, SOUTH)] == 3, "the Uur did not receive its ball")
    check(t.board[(3, SOUTH)] == 1, "sowing did not carry on past the Uur")
    check(t.captured == [0, 0] and t.to_move == NORTH, "should be a plain abar")
    b2 = blank()
    b2[(5, SOUTH)] = 1
    b2[(4, SOUTH)] = 2
    b2[(4, NORTH)] = 2
    t2 = G.apply_move(state(b2, uur=u), "5,0")
    check(t2.board[(4, SOUTH)] == 3 and t2.captured == [0, 0],
          "landing in an Uur must simply end the move")
    check(t2.to_move == NORTH, "landing in an Uur must end the move")
    # an Uur opposite an own empty landing hole cannot be plundered
    b3 = blank()
    b3[(5, SOUTH)] = 1
    b3[(4, NORTH)] = 3
    u3 = {(4, NORTH): NORTH, (7, NORTH): NORTH}
    t3 = G.apply_move(state(b3, uur=u3), "5,0")
    check(t3.captured == [0, 0] and t3.board[(4, NORTH)] == 3,
          "an Uur opposite the landing hole must be untouchable")
    check(len(t3.uur) == 2, "must not build a new Uur out of an existing one")


def test_relay():
    # a chain: 2 balls from South 12 (col 0) land on a hole of 1 -> relay
    b = blank()
    order = ring(W, "clockwise")
    i = order.index((0, SOUTH))
    a, bb = order[(i + 1) % (2 * W)], order[(i + 2) % (2 * W)]
    b[(0, SOUTH)] = 2
    b[bb] = 1                        # occupied -> relay lifts 2 from there
    t = G.apply_move(state(b), "0,0")
    check(t.board[bb] == 0, "the relayed hole should have been emptied")
    check(t.board[a] == 1, "the first sown hole should hold its ball")
    check(sum(t.board.values()) + sum(t.captured) == 3, "relay lost balls")


def test_endless_relay():
    """A relay chain that never dies must be an abar, and the result must NOT
    depend on the value of any lap cap.

    This 2x6 position was found by random play; South's hole 6 (column 0) starts
    a chain that is periodic from its very first lap, so the balls end up exactly
    where they started -- the move resolves to a null move.  The assertions below
    fail if the engine ever goes back to "sow N laps and stop wherever you are".
    """
    from games.layli_goobalay.game import RELAY_WATCH, LAP_CAP
    board = {}
    south = [8, 1, 8, 1, 2, 3]
    north = [0, 1, 0, 3, 0, 1]
    for c in range(6):
        board[(c, SOUTH)] = south[c]
        board[(c, NORTH)] = north[c]
    s = LayliState(board=board, uur={}, captured=[12, 8], to_move=SOUTH,
                   width=6, direction="clockwise", ply=8, no_progress=1)
    check(sum(s.board.values()) + sum(s.captured) == 2 * 6 * SEEDS_PER_HOLE,
          "endless-relay fixture is not ball-conserving")
    mv = "0,0"
    check(mv in G.legal_moves(s), "endless-relay fixture: %s is not legal" % mv)
    t = G.apply_move(s, mv)
    check(t.captured == s.captured, "an endless relay must capture nothing (abar)")
    check(t.uur == {}, "an endless relay must not create an Uur")
    check(t.board == s.board,
          "the endless chain is periodic from lap 0, so the balls must end up "
          "exactly where they started; got %s" % (t.board,))
    check(t.to_move == NORTH and t.no_progress == s.no_progress + 1,
          "an endless relay still consumes a ply and makes no progress")
    check(G.describe_move(s, mv) == "South 6", "endless relay should log as a bare abar")
    check(RELAY_WATCH < LAP_CAP,
          "the cycle watch must fire before the hard lap guard")
    # ...and the game still terminates from here.
    n = 0
    while not G.is_terminal(t):
        t = G.apply_move(t, G.legal_moves(t)[0])
        n += 1
        check(n < 4100, "game did not terminate after an endless relay")


def test_scoring_and_draw():
    # a genuine tie must be an honest draw
    b = blank()
    b[(0, NORTH)] = 4                # North to move; South has nothing
    s = state(b, captured=[46, 46], to_move=SOUTH)
    check(G.is_terminal(s), "South with no ball should be terminal")
    check(G.scores(s) == [46, 50], "scores wrong")
    b2 = blank()
    s2 = state(b2, captured=[48, 48], to_move=SOUTH)
    check(G.is_terminal(s2) and G.returns(s2) == [0.0, 0.0],
          "a tie must be an honest DRAW")
    # Uur balls score for the Uur's OWNER, wherever the hole sits
    b3 = blank()
    b3[(3, SOUTH)] = 5
    s3 = state(b3, uur={(3, SOUTH): NORTH, (3, NORTH): NORTH},
               captured=[0, 0], to_move=SOUTH)
    check(G.scores(s3) == [0, 5], "Uur balls must score for their owner")


def test_serialize_and_render():
    s = G.initial_state()
    check(G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s),
          "serialize does not round-trip")
    spec = G.render(s)
    check(spec["board"]["type"] == "square", "board type")
    check(spec["board"]["width"] == W and spec["board"]["height"] == 2, "board size")
    check(len(spec["pieces"]) == 2 * W, "expected one label per hole")
    for p in spec["pieces"]:
        c, r = p["cell"].split(",")
        check(0 <= int(c) < W and int(r) in (0, 1), "bad cell id %r" % p["cell"])
        check(p["owner"] in (0, 1) and p["label"] == str(SEEDS_PER_HOLE),
              "bad piece %r" % p)
    check(spec["board"].get("tints") == {}, "no Uur yet -> no tints")
    s2, _, _ = replay(SOUTH_LINE, **CONV)
    spec2 = G.render(s2)
    check(len(spec2["board"]["tints"]) == 4, "two Uurs -> four tinted holes")
    check("Uur" in spec2["caption"], "caption should mention the Uurs")
    for size in (6, 8, 12):
        sp = G.render(G.initial_state(options={"size": size}))
        check(sp["board"]["width"] == size, "size option ignored")


def test_random_termination():
    rnd = random.Random(20030313)
    total_draws = 0
    for size in (6, 8, 12):
        for direction in ("clockwise", "anticlockwise"):
            for _ in range(12):
                s = G.initial_state(options={"size": size, "direction": direction})
                n = 0
                while not G.is_terminal(s):
                    moves = G.legal_moves(s)
                    check(moves, "non-terminal state with no legal move")
                    for mv in moves:
                        pit = tuple(int(x) for x in mv.split(","))
                        check(pit[1] == s.to_move, "move on the wrong side")
                        check(pit not in s.uur, "an Uur hole was offered as a move")
                    s = G.apply_move(s, rnd.choice(moves))
                    check(sum(s.board.values()) + sum(s.captured)
                          == 2 * size * SEEDS_PER_HOLE, "balls not conserved")
                    for p in s.uur:
                        check(s.board[p] >= 2, "an Uur hole was emptied")
                    n += 1
                    check(n < 1000, "game did not terminate")
                r = G.returns(s)
                check(r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]),
                      "bad returns %r" % (r,))
                if r == [0.0, 0.0]:
                    total_draws += 1
    check(total_draws > 0, "no draw ever occurred -- ties should be reachable")


def main():
    test_ring_geometry()
    test_pin_conventions()
    test_south_line()
    test_south_variation()
    test_north_line()
    test_opening_line()
    test_capture_branches()
    test_uur_creation_and_freeze()
    test_relay()
    test_endless_relay()
    test_scoring_and_draw()
    test_serialize_and_render()
    test_random_termination()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
