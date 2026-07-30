#!/usr/bin/env python3
"""Flume correctness anchor -- pure stdlib (agp + this package only).

Anchors, in order of strength:

1. **The two published worked examples.**  Figures 3 and 4 of
   marksteeregames.com/Flume_Go_rules.pdf are the only worked cascades Steere
   published; both were read off the rendered PDF (200/400 dpi, stone blobs
   mapped onto the 7x7 lattice) and are replayed here placement by placement,
   asserting the connection count the caption states and the exact point at
   which the turn ends.
2. **Opening move counts** cross-checked against the AbstractPlay gameslib
   implementation.  gameslib offers exactly three boards -- grids 7, 9 (its
   default) and 11, i.e. our playable 5, 7 and 9 -- so only those three counts
   (24 / 48 / 80) are oracle-verified; the 11 and 17 rows below are the same
   ``n*n - 1`` arithmetic extended to sizes the oracle does not implement.  The
   full differential (turn enumeration + random games) lives outside the
   package; see rules.md.
3. Property assertions for the green ring, the cascade, the pie rule, the
   anti-mirroring ban, seat/colour conjugation, the render bounds at every
   board size, and the serialize round-trip compared as STATES.
4. The regions QA found unasserted: the "last-move" marks must RESET at the
   start of each new turn, the early-majority stop must be able to fire in the
   middle of a forced continuation, 4 must really be the maximum connection
   count on every board, and Figure 4's stated 6-placement alternative.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                  # noqa: E402

MAN, G = load_from_dir(Path(__file__).resolve().parent)
MOD = sys.modules[type(G).__module__]          # the LIVE module (synthetic name)
FState = MOD.FState
RED, BLUE = 0, 1
checks = 0


def ck(cond, msg):
    global checks
    checks += 1
    assert cond, msg


def cell(t):
    return f"{t[0]},{t[1]}"


def show(s):
    g = s.size + 2
    out = []
    for r in range(g - 1, -1, -1):
        out.append("".join(
            {RED: "R", BLUE: "B"}.get(s.board.get((c, r)),
                                      "G" if MOD.is_green(s.size, c, r) else ".")
            for c in range(g)))
    return "\n".join(out)


def play(s, moves):
    for m in moves:
        s = G.apply_move(s, m)
    return s


# ------------------------------------------------------------------ geometry
def test_board_geometry():
    for n in MOD.SIZES:
        s = G.initial_state({"size": n})
        g = n + 2
        ck(MOD.grid_size(n) == g, "grid size")
        ck(len(MOD.playable_cells(n)) == n * n, "playable count")
        ring = [(c, r) for r in range(g) for c in range(g) if MOD.is_green(n, c, r)]
        ck(len(ring) == 4 * g - 4, f"ring size n={n}: {len(ring)}")
        # every playable point is strictly inside the ring
        for (c, r) in MOD.playable_cells(n):
            ck(not MOD.is_green(n, c, r), "playable point is green")
        # Fig. 1: the ring is the OUTERMOST ring of intersections, so a
        # playable corner touches exactly 2 green stones and a playable edge
        # point exactly 1, on an otherwise empty board.
        ck(MOD.connections({}, n, 1, 1) == 2, "corner green count")
        ck(MOD.connections({}, n, n, 1) == 2, "corner green count")
        ck(MOD.connections({}, n, 1, n) == 2, "corner green count")
        ck(MOD.connections({}, n, n, n) == 2, "corner green count")
        ck(MOD.connections({}, n, 2, 1) == 1, "edge green count")
        ck(MOD.connections({}, n, 1, 2) == 1, "edge green count")
        ck(MOD.connections({}, n, n, 2) == 1, "edge green count")
        ck(MOD.connections({}, n, 2, n) == 1, "edge green count")
        ck(MOD.connections({}, n, 2, 2) == 0, "interior green count")
        ck(MOD.centre(n) == ((n + 1) // 2, (n + 1) // 2), "centre")
        # ... and no placement on an empty board can reach 3, so the FIRST turn
        # of the game is always exactly one stone (the anti-mirroring rule's
        # "first turn" == "first placement").
        ck(max(MOD.connections({}, n, c, r) for (c, r) in MOD.playable_cells(n)) == 2,
           "empty-board max connections must be 2")
        ck(len(G.legal_moves(s)) == n * n - 1, f"opening count n={n}")


def test_connections_bruteforce():
    """`connections` is the single predicate every rule hangs off, so check it
    positively, per point, against an independent recomputation that builds the
    green ring by enumerating the whole grid (a different code path)."""
    rnd = random.Random(4)
    for n in (5, 7):
        g = n + 2
        green = set()
        for r in range(g):
            for c in range(g):
                if c == 0 or r == 0 or c == g - 1 or r == g - 1:
                    green.add((c, r))
        s = G.initial_state({"size": n})
        for _ in range(n * n):
            if G.is_terminal(s):
                break
            for (c, r) in MOD.playable_cells(n):
                want = sum(1 for q in ((c - 1, r), (c + 1, r), (c, r - 1), (c, r + 1))
                           if q in green or q in s.board)
                ck(MOD.connections(s.board, n, c, r) == want,
                   f"connections({c},{r}) n={n}")
                ck(0 <= want <= 4, "connection count in range")
            s = G.apply_move(s, rnd.choice(G.legal_moves(s)))


# ------------------------------------------------- the published worked turns
# Both figures use the grid-7 board (24 green stones) => playable n = 5.
# Figure rows were read TOP-down; internal r counts UP, so r = 6 - r_fig.
FIG3A = {(4, 3): BLUE, (5, 3): RED,
         (3, 2): RED,
         (3, 1): BLUE, (4, 1): BLUE, (5, 1): RED}
FIG4A = {(2, 4): RED, (4, 4): BLUE,
         (2, 3): RED, (4, 3): BLUE,
         (4, 2): BLUE,
         (1, 1): RED, (2, 1): BLUE, (3, 1): RED, (4, 1): RED, (5, 1): BLUE}


def replay(start, seq, tag):
    """seq = [(cell, expected connection count), ...]; the LAST entry must end
    the turn and every earlier one must force a continuation."""
    s = FState(size=5, board=dict(start), to_move=RED, cont=False, turns=6)
    ck(not G.is_terminal(s), f"{tag}: start is not terminal")
    for i, (pt, want) in enumerate(seq):
        ck(G.current_player(s) == RED, f"{tag}: still Red's turn at step {i}")
        ck(cell(pt) in G.legal_moves(s), f"{tag}: {pt} legal at step {i}")
        got = MOD.connections(s.board, 5, *pt)
        ck(got == want, f"{tag} step {i} at {pt}: {got} connections, want {want}")
        last = (i == len(seq) - 1)
        ck((got >= 3) != last, f"{tag} step {i}: continuation flag vs figure")
        s = G.apply_move(s, cell(pt))
        ck(s.board[pt] == RED, f"{tag}: stone placed")
        ck(s.cont is (not last), f"{tag} step {i}: cont={s.cont}")
        ck(s.to_move == (RED if not last else BLUE), f"{tag}: seat after step {i}")
    ck(s.turns == 7, f"{tag}: exactly one turn consumed")
    ck(len(s.marks) == len(seq), f"{tag}: all {len(seq)} stones marked")
    ck(tuple(s.marks) == tuple(pt for pt, _ in seq), f"{tag}: mark order")
    return s


def test_figure3():
    """Fig. 3: 'In 3b Red forms a 3-way connection.  In 3c Red forms a 4-way
    connection.  In 3d Red forms one connection with a green stone.'"""
    ck(len(FIG3A) == 6 and sum(1 for v in FIG3A.values() if v == RED) == 3,
       "Fig 3a census: 3 red + 3 blue")
    s = replay(FIG3A, [((4, 2), 3), ((5, 2), 4), ((3, 5), 1)], "Fig3")
    ck(len(s.board) == 9, "Fig 3d has 9 stones")
    ck(s.board[(5, 2)] == RED and s.board[(3, 5)] == RED, "Fig 3d reds")
    # 3d's single connection really is with a GREEN stone (the point is on the
    # top edge of the playable square and has no coloured neighbour).
    ck(MOD.connections({}, 5, 3, 5) == 1, "Fig 3d connection is the green ring")
    for q in ((2, 5), (4, 5), (3, 4)):
        ck(q not in FIG3A, "Fig 3d neighbourhood is otherwise empty")


def test_figure4():
    """Fig. 4: a four-placement turn; 'Red could have claimed 6 points instead
    of 4' -- i.e. at the last step a continuing alternative existed."""
    ck(len(FIG4A) == 10 and sum(1 for v in FIG4A.values() if v == RED) == 5,
       "Fig 4a census: 5 red + 5 blue")
    s = replay(FIG4A, [((5, 2), 3), ((5, 3), 3), ((5, 4), 3), ((4, 5), 2)], "Fig4")
    ck(len(s.board) == 14, "Fig 4e has 14 stones")
    # the road not taken: (5,5) instead of (4,5) forms 3 and would cascade on
    mid = play(FState(size=5, board=dict(FIG4A), to_move=RED, cont=False, turns=6),
               [cell(p) for p in ((5, 2), (5, 3), (5, 4))])
    ck(MOD.connections(mid.board, 5, 5, 5) == 3, "Fig4 alternative forms 3")
    ck(G.apply_move(mid, "5,5").cont, "Fig4 alternative would cascade on")
    ck(MOD.connections(mid.board, 5, 4, 5) == 2, "Fig4 chosen point forms 2")


# ------------------------------------------------------------ cascade / rules
def test_cascade_mechanics():
    """A cascade is a run of plies by ONE seat; >=3 continues, <=2 ends."""
    n = 5
    # hand-built: Red walks up the right-hand file, each stone touching the
    # green ring + the previous stone + a blue stone => 3 each time.
    board = {(4, 1): BLUE, (4, 2): BLUE, (4, 3): BLUE, (4, 4): BLUE, (5, 1): BLUE}
    s = FState(size=n, board=dict(board), to_move=RED, cont=False, turns=4)
    run = []
    for pt in ((5, 2), (5, 3), (5, 4)):
        ck(MOD.connections(s.board, n, *pt) == 3, f"cascade step {pt}")
        s = G.apply_move(s, cell(pt))
        run.append(pt)
        ck(s.cont and s.to_move == RED, f"cascade continues after {pt}")
        ck(tuple(s.marks) == tuple(run), "marks accumulate through the cascade")
    ck(len(run) >= 3, "cascade of at least 3 placements")
    # (5,5) is a corner: 2 green + the stone below = 3 -> a 4th placement
    ck(MOD.connections(s.board, n, 5, 5) == 3, "corner continues")
    s2 = G.apply_move(s, "5,5")
    ck(s2.cont and len(s2.marks) == 4, "4-placement cascade")
    # ...whereas an isolated interior point ends the turn at 0 connections
    s3 = G.apply_move(s, "2,3")
    ck(MOD.connections(s.board, n, 2, 3) == 0, "isolated point")
    ck(not s3.cont and s3.to_move == BLUE and s3.turns == 5, "turn ends at <=2")
    ck(tuple(s3.marks) == tuple(run) + ((2, 3),), "final mark run")
    # exactly {3,4} triggers -- 2 does not
    board2 = {(2, 2): BLUE, (3, 3): BLUE}
    s4 = FState(size=n, board=board2, to_move=RED, cont=False, turns=4)
    ck(MOD.connections(s4.board, n, 2, 3) == 2, "two connections")
    ck(not G.apply_move(s4, "2,3").cont, "2 connections ends the turn")


def test_anti_mirroring():
    for n in MOD.SIZES:
        s = G.initial_state({"size": n})
        ctr = MOD.centre(n)
        ck(ctr == ((n + 1) // 2,) * 2, "centre point")
        ck(cell(ctr) not in G.legal_moves(s), f"centre banned on move 1 (n={n})")
        ck(len(G.legal_moves(s)) == n * n - 1, "one point fewer than the board")
        ck("swap" not in G.legal_moves(s), "no swap before Red has moved")
        # ...but only on Red's FIRST turn: after Blue replies, it is open again
        s2 = play(s, ["1,1", "1,2"])
        ck(s2.turns == 2 and s2.to_move == RED, "two turns played")
        ck(cell(ctr) in G.legal_moves(s2), "centre open from Red's 2nd turn")
        # and it is open to Blue on Blue's very first turn
        s3 = G.apply_move(s, "1,1")
        ck(cell(ctr) in G.legal_moves(s3), "centre open to Blue immediately")


def test_pie_rule():
    n = 7
    s = G.initial_state({"size": n})
    ck("swap" not in G.legal_moves(s), "swap not offered to Red")
    s1 = G.apply_move(s, "2,3")
    ck(s1.turns == 1 and s1.to_move == BLUE and not s1.cont, "Red's turn was one stone")
    ck("swap" in G.legal_moves(s1), "pie rule offered to Blue")
    sw = G.apply_move(s1, "swap")
    ck(sw.board == {(2, 3): BLUE}, "swap recolours the opening stone")
    ck(sw.to_move == RED and sw.turns == 2 and sw.swapped, "swap hands back the move")
    ck("swap" not in G.legal_moves(sw), "swap is a one-shot")
    ck(cell(MOD.centre(n)) in G.legal_moves(sw), "centre open after the swap")
    ck(G.describe_move(s1, "swap") == "swap (pie)", "swap notation")
    # declining: Blue just places, and the offer lapses
    dec = G.apply_move(s1, "4,4")
    ck("swap" not in G.legal_moves(dec), "offer lapses once Blue places")
    ck(not dec.swapped, "no swap flag")
    # never offered mid-cascade: give Blue a cascading first turn
    board = {(4, 1): RED}
    s2 = FState(size=n, board=dict(board), to_move=BLUE, cont=False, turns=1)
    ck("swap" in G.legal_moves(s2), "swap offered at the start of Blue's 1st turn")
    ck(MOD.connections(s2.board, n, 5, 1) == 2, "setup")
    s3 = FState(size=n, board={(1, 2): RED}, to_move=BLUE, cont=False, turns=1)
    s4 = G.apply_move(s3, "1,1")           # corner: 2 green + (1,2) = 3 -> cascade
    ck(s4.cont and s4.to_move == BLUE and s4.turns == 1, "Blue cascades on turn 1")
    ck("swap" not in G.legal_moves(s4), "swap NOT offered mid-cascade")
    # ... and once the cascade ends the turn is over, so the offer is gone
    s5 = G.apply_move(s4, "4,4")
    ck(not s5.cont and s5.turns == 2 and "swap" not in G.legal_moves(s5),
       "offer gone after Blue's first turn")


def test_swap_is_a_true_colour_swap():
    """Recolouring + handing back the move must reproduce the mirror position."""
    n = 5
    s = G.apply_move(G.initial_state({"size": n}), "2,3")
    sw = G.apply_move(s, "swap")
    ck(sw.board == {(2, 3): BLUE}, "one blue stone")
    ck(sw.to_move == RED, "seat 0 to move")
    # the position is now the colour-conjugate of 'one stone for the player to
    # move's opponent', i.e. exactly what seat 1 faced before -- move sets agree
    ck(set(G.legal_moves(sw)) == set(m for m in G.legal_moves(s) if m != "swap"),
       "post-swap move set")


# ---------------------------------------------------------------- symmetries
def conj(s):
    """Colour conjugation: swap both seats' stones and the seat to move."""
    return FState(size=s.size, board={p: 1 - v for p, v in s.board.items()},
                  to_move=1 - s.to_move, cont=s.cont, turns=s.turns,
                  swapped=s.swapped, marks=s.marks)


def dihedral(n, k):
    """One of the 8 grid symmetries as a (c,r) -> (c,r) map on the full grid."""
    g = n + 2
    hi = g - 1

    def f(p):
        c, r = p
        if k & 4:
            c, r = r, c
        if k & 1:
            c = hi - c
        if k & 2:
            r = hi - r
        return (c, r)
    return f


def test_seat_and_board_symmetry():
    """Neither seat may be untested: colour is irrelevant to Flume's legality,
    so the engine must CONJUGATE exactly under seat swap, and it must commute
    with all 8 symmetries of the square grid."""
    rnd = random.Random(19)
    for n in (5, 7):
        for gi in range(6):
            s = G.initial_state({"size": n})
            step = 0
            while not G.is_terminal(s):
                # (a) colour conjugation
                c = conj(s)
                ck(sorted(x for x in G.legal_moves(s) if x != "swap")
                   == sorted(x for x in G.legal_moves(c) if x != "swap"),
                   f"conjugate move set n={n} step={step}")
                ck(G.current_player(c) == 1 - G.current_player(s), "conjugate seat")
                ck(G.returns(c) == list(reversed(G.returns(s))), "conjugate returns")
                ck(G.heuristic(c) == [-x for x in G.heuristic(s)], "conjugate eval")
                ck(G.is_terminal(c) == G.is_terminal(s), "conjugate terminal")
                # (b) all 8 board symmetries carry the move set over exactly
                for k in range(8):
                    f = dihedral(n, k)
                    t = FState(size=n, board={f(p): v for p, v in s.board.items()},
                               to_move=s.to_move, cont=s.cont, turns=s.turns,
                               swapped=s.swapped, marks=tuple(f(p) for p in s.marks))
                    want = {cell(f(tuple(int(z) for z in m.split(","))))
                            for m in G.legal_moves(s) if m != "swap"}
                    ck({m for m in G.legal_moves(t) if m != "swap"} == want,
                       f"dihedral {k} move set n={n} step={step}")
                mv = rnd.choice(G.legal_moves(s))
                # conjugated state must react identically (cont flag, seat delta)
                if mv != "swap":
                    a, b = G.apply_move(s, mv), G.apply_move(c, mv)
                    ck(a.cont == b.cont and a.turns == b.turns, "conjugate cont")
                    ck(b.board == {p: 1 - v for p, v in a.board.items()},
                       "conjugate board after move")
                s = G.apply_move(s, mv)
                step += 1
            # both seats must be able to win over the sample
    wins = set()
    for seed in range(40):
        rnd2 = random.Random(seed)
        s = G.initial_state({"size": 5})
        while not G.is_terminal(s):
            s = G.apply_move(s, rnd2.choice(G.legal_moves(s)))
        r = G.returns(s)
        wins.add(0 if r[0] > 0 else 1)
    ck(wins == {0, 1}, f"both seats win somewhere in the sample: {wins}")


# ---------------------------------------------- results, termination, no draws
def test_no_draws_and_termination():
    """n is odd => n*n stones is odd => the counts cannot tie.  Every PLACEMENT
    fills a point and points never empty, so a game is at most n*n placements --
    plus the one-shot `swap`, which costs a ply but places nothing.  The bound is
    therefore n*n + 1 plies, NOT n*n: with a swap the board can still fill
    completely (n=5 seed 6 below reaches 26 plies / 25 stones), which the earlier
    `plies <= n*n` form only survived because its 12 seeds never swapped on a
    game that went the distance."""
    for n in MOD.SIZES:
        ck(n % 2 == 1, "playable side must be odd")
        ck(2 * MOD.majority_target(n) == n * n + 1, "target is the strict half")
    for n in (5, 7, 9):
        for seed in range(12 if n < 9 else 4):
            rnd = random.Random(seed * 31 + n)
            s = G.initial_state({"size": n})
            plies = 0
            while not G.is_terminal(s):
                before = len(s.board)
                s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
                ck(len(s.board) == before + 1 or s.swapped, "every ply fills a point")
                plies += 1
                ck(len(s.board) <= n * n, f"placement bound n={n}")
                ck(plies <= n * n + (1 if s.swapped else 0), f"ply bound n={n}")
            r = G.returns(s)
            ck(sorted(r) == [-1.0, 1.0], f"decisive result, got {r} n={n}")
            a, b = G._scores(s)
            ck(a != b, "no tie")
            ck(max(a, b) == MOD.majority_target(n), "ends the instant it is decided")
            ck((r[0] > 0) == (a > b), "winner is the larger army")
            ck(G.legal_moves(s) == [], "no moves at terminal")
    # The exact witness that the bound is n*n + 1 and not n*n: swap on Blue's
    # first turn and play on until the board is completely full.
    for n, seed in ((5, 6), (7, 37)):
        rnd = random.Random(seed)
        s = G.initial_state({"size": n})
        plies = 0
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            mv = "swap" if ("swap" in ms and not s.swapped) else \
                rnd.choice([m for m in ms if m != "swap"])
            s = G.apply_move(s, mv)
            plies += 1
        ck(s.swapped, f"witness n={n} must actually swap")
        ck(len(s.board) == n * n, f"witness n={n} must fill the board: {len(s.board)}")
        ck(plies == n * n + 1, f"witness n={n} plies {plies} != {n * n + 1}")
        ck(sorted(G.returns(s)) == [-1.0, 1.0], "witness is decisive")


def test_full_board_and_early_stop():
    """The early stop is a provably equivalent shortcut, not a rule change: the
    seat that reaches the target already holds more than half the points."""
    n = 5
    t = MOD.majority_target(n)
    ck(t == 13, "5x5 target")
    # a hand-built full board with 13 red / 12 blue is terminal for Red
    board, k = {}, 0
    for p in MOD.playable_cells(n):
        board[p] = RED if k < 13 else BLUE
        k += 1
    s = FState(size=n, board=board, to_move=BLUE, turns=20)
    ck(G.is_terminal(s) and G.returns(s) == [1.0, -1.0], "full board Red win")
    # one stone short of the target is NOT terminal: 12-12 with one point free
    pts = MOD.playable_cells(n)
    board2 = {p: (RED if k < 12 else BLUE) for k, p in enumerate(pts[:24])}
    s2 = FState(size=n, board=board2, to_move=BLUE, turns=20)
    ck(sorted(G._scores(s2)) == [12, 12], "12-12 with one point free")
    ck(not G.is_terminal(s2), "12-12 is not terminal")
    ck(len(G.legal_moves(s2)) == 1, "exactly one point left")
    s3 = G.apply_move(s2, G.legal_moves(s2)[0])
    ck(G.is_terminal(s3) and G.returns(s3) == [-1.0, 1.0], "last point decides")
    # ...and the caption must account for the points honestly: the two counts
    # need NOT sum to n*n, so it may not imply that they do.
    ck("all 25 points played" in G.render(s)["caption"],
       f"full-board caption: {G.render(s)['caption']!r}")
    for seed in range(12):
        rnd = random.Random(seed * 5 + 1)
        g = G.initial_state({"size": 7})
        while not G.is_terminal(g):
            g = G.apply_move(g, rnd.choice(G.legal_moves(g)))
        a, b = G._scores(g)
        cap = G.render(g)["caption"]
        left = 49 - (a + b)
        ck(f"Red {a} / Blue {b}" in cap, f"caption scores: {cap!r}")
        if left:
            ck(f"decided, {left} of 49 points unplayed" in cap,
               f"caption hides {left} unplayed points: {cap!r}")
        else:
            ck("all 49 points played" in cap, f"caption: {cap!r}")


def test_marks_reset_between_turns():
    """`marks` is the set of stones of the CURRENT run only -- it drives the
    "last-move" highlights, so it must RESET when a new turn starts and only
    accumulate inside a cascade.  (Found by mutation testing: making `marks`
    accumulate unconditionally survived every other assertion in this file, and
    would light up the whole board as "last move".)"""
    n = 5
    s = G.initial_state({"size": n})
    # two plain turns in a row, neither cascading
    s = G.apply_move(s, "2,2")
    ck(tuple(s.marks) == ((2, 2),), f"turn 1 marks {s.marks}")
    ck(not s.cont and s.to_move == BLUE, "turn 1 ended")
    s = G.apply_move(s, "4,4")
    ck(tuple(s.marks) == ((4, 4),), f"turn 2 must FORGET turn 1: {s.marks}")
    s = G.apply_move(s, "2,4")
    ck(tuple(s.marks) == ((2, 4),), f"turn 3 marks {s.marks}")
    # a cascade accumulates, and the NEXT turn resets to a single stone
    board = {(4, 1): BLUE, (4, 2): BLUE, (4, 3): BLUE, (5, 1): BLUE}
    c = FState(size=n, board=dict(board), to_move=RED, cont=False, turns=4)
    c = G.apply_move(c, "5,2")
    ck(c.cont and tuple(c.marks) == ((5, 2),), "cascade step 1")
    c = G.apply_move(c, "5,3")
    ck(c.cont and tuple(c.marks) == ((5, 2), (5, 3)), f"cascade grows {c.marks}")
    c = G.apply_move(c, "1,5")               # 2 connections -> turn over
    ck(not c.cont and tuple(c.marks) == ((5, 2), (5, 3), (1, 5)),
       f"the whole run stays marked {c.marks}")
    nxt = G.apply_move(c, "3,3")             # Blue's fresh turn
    ck(tuple(nxt.marks) == ((3, 3),), f"a new turn resets marks: {nxt.marks}")
    # and over a whole random game, marks never exceed the current run
    rnd = random.Random(23)
    s = G.initial_state({"size": 7})
    run = 0
    while not G.is_terminal(s):
        was_cont = s.cont
        s = G.apply_move(s, rnd.choice([m for m in G.legal_moves(s)
                                        if m != "swap"]))
        run = run + 1 if was_cont else 1
        ck(len(s.marks) == run, f"marks {len(s.marks)} != run {run}")
        ck(len(set(s.marks)) == len(s.marks), "marks contain no duplicate")
        for p in s.marks:
            ck(p in s.board, "a marked point holds a stone")
        ck(all(s.board[p] == 1 - s.to_move or s.cont for p in s.marks),
           "marked stones belong to the seat that just played")


def test_mid_cascade_early_stop():
    """The early-majority stop must be able to fire INSIDE a forced
    continuation, and a decided result must outrank the "place again" duty --
    otherwise a cascade would demand a stone after the game is over.  (This
    region is not reachable often in random play, so it is constructed.)"""
    n = 5
    t = MOD.majority_target(n)
    pts = MOD.playable_cells(n)
    rnd = random.Random(101)
    hits = 0
    for _ in range(400):
        red = rnd.sample(pts, t - 1)                 # one stone short
        rest = [p for p in pts if p not in red]
        blue = rnd.sample(rest, rnd.randrange(0, min(len(rest) - 1, t - 1) + 1))
        board = {p: RED for p in red}
        board.update({p: BLUE for p in blue})
        cands = [p for p in pts if p not in board
                 and MOD.connections(board, n, *p) >= 3]
        if not cands:
            continue
        pt = cands[0]
        for seat in (RED, BLUE):
            b = board if seat == RED else {q: 1 - v for q, v in board.items()}
            s = FState(size=n, board=dict(b), to_move=seat, cont=True, turns=9)
            ck(not G.is_terminal(s), "the run has not yet decided the game")
            ck(G._scores(s)[seat] == t - 1, "the mover is one stone short")
            nx = G.apply_move(s, cell(pt))
            ck(G.is_terminal(nx), "reaching the target ends the game at once")
            ck(not nx.cont, "no 'place again' duty after the game is decided")
            ck(G.legal_moves(nx) == [], "no moves once decided")
            want = [1.0, -1.0] if seat == RED else [-1.0, 1.0]
            ck(G.returns(nx) == want, f"returns {G.returns(nx)} seat={seat}")
            ck(not G.describe_move(s, cell(pt)).endswith("+"),
               "the deciding stone must not promise a continuation")
            ck(G.render(nx)["caption"].startswith(
                ("Red wins", "Blue wins")), "terminal caption")
            hits += 1
    ck(hits >= 200, f"only {hits} mid-cascade stops constructed")


def test_max_connections_is_four():
    """rules.md claims "3 or 4" is equivalently "3 or more" because 4 is the
    maximum on a square grid.  Every playable point of every offered board has
    exactly four orthogonal NEIGHBOUR SLOTS (each of them either a green ring
    stone or another playable point), so the count is in 0..4 -- and on a full
    board every point really does reach 4."""
    for n in MOD.SIZES:
        g = n + 2
        full = {p: RED for p in MOD.playable_cells(n)}
        for (c, r) in MOD.playable_cells(n):
            slots = [(c - 1, r), (c + 1, r), (c, r - 1), (c, r + 1)]
            ck(all(0 <= x < g and 0 <= y < g for (x, y) in slots),
               f"({c},{r}) has a neighbour off the whole grid (n={n})")
            green = sum(1 for (x, y) in slots if MOD.is_green(n, x, y))
            inner = sum(1 for (x, y) in slots
                        if not MOD.is_green(n, x, y) and 1 <= x <= n and 1 <= y <= n)
            ck(green + inner == 4, f"({c},{r}) slot census {green}+{inner} (n={n})")
            ck(MOD.connections({}, n, c, r) == green, "empty board = green count")
            ck(green == (2 if c in (1, n) and r in (1, n) else
                         1 if c in (1, n) or r in (1, n) else 0),
               f"green census at ({c},{r}) n={n}")
            # with every other point occupied the count is the maximum, 4
            rest = dict(full)
            del rest[(c, r)]
            ck(MOD.connections(rest, n, c, r) == 4,
               f"max connections at ({c},{r}) is not 4 (n={n})")


def test_figure4_six_point_alternative():
    """"Red could have claimed 6 points instead of 4, but this is a winning
    strategy for Red."  Replaying the alternative from Figure 4a gives exactly
    six placements -- an independent check on the green-ring arithmetic, since
    the 5th and 6th stones only continue because of the ring."""
    line = [(5, 2), (5, 3), (5, 4), (5, 5), (4, 5), (3, 5)]
    s = FState(size=5, board=dict(FIG4A), to_move=RED, cont=False, turns=6)
    for i, pt in enumerate(line):
        last = i == len(line) - 1
        k = MOD.connections(s.board, 5, *pt)
        ck((k >= 3) != last, f"6-point line step {i} at {pt}: {k} connections")
        ck(cell(pt) in G.legal_moves(s), f"6-point step {i} legal")
        s = G.apply_move(s, cell(pt))
        ck(s.cont is (not last), f"6-point step {i}: cont={s.cont}")
    ck(len(s.marks) == 6 and s.turns == 7 and s.to_move == BLUE,
       f"the alternative turn claims exactly 6 points, got {len(s.marks)}")
    ck(G._scores(s) == [11, 5], f"5 + 6 red stones, {G._scores(s)}")
    # the ring is what keeps the last two going: (4,5) and (3,5) each touch it
    ck(MOD.connections({}, 5, 4, 5) == 1 and MOD.connections({}, 5, 3, 5) == 1,
       "the top-edge points touch the green ring")


# ------------------------------------------------------------------ plumbing
KEYS = {"size", "board", "to_move", "cont", "turns", "swapped", "marks"}


def test_serialize_roundtrip():
    """Compare STATES (not dicts): `serialize(deserialize(d)) == d` cannot see a
    dropped field, because deserialize re-defaults it on the way in."""
    import json
    rnd = random.Random(5)
    for n in (5, 7):
        s = G.initial_state({"size": n})
        seen_cont = seen_swap = False
        while True:
            d = G.serialize(s)
            ck(set(d) == KEYS, f"exact key set: {sorted(set(d) ^ KEYS)}")
            json.dumps(d)
            back = G.deserialize(d)
            ck(back == s, f"state round-trip failed\n{d}\n!=\n{G.serialize(back)}")
            ck(type(back.marks) is tuple and all(type(x) is tuple for x in back.marks),
               "marks round-trip as tuples")
            ck(G.serialize(back) == d, "dict round-trip")
            # a state reloaded from the DB must behave identically
            ck(G.legal_moves(back) == G.legal_moves(s), "moves after reload")
            ck(G.current_player(back) == G.current_player(s), "seat after reload")
            ck(G.render(back) == G.render(s), "render after reload")
            if G.is_terminal(s):
                break
            moves = G.legal_moves(s)
            mv = "swap" if ("swap" in moves and not seen_swap and n == 5) \
                else rnd.choice([m for m in moves if m != "swap"])
            s = G.apply_move(s, mv)
            seen_cont = seen_cont or s.cont
            seen_swap = seen_swap or s.swapped
        ck(seen_cont, f"the sweep covered a mid-cascade state (n={n})")
        if n == 5:
            ck(seen_swap, "the sweep covered a swapped state")


def test_purity():
    rnd = random.Random(3)
    s = G.initial_state({"size": 5})
    while not G.is_terminal(s):
        snap = G.serialize(s)
        for mv in G.legal_moves(s):
            G.apply_move(s, mv)
        ck(G.serialize(s) == snap, "apply_move mutated its input")
        s = G.apply_move(s, rnd.choice(G.legal_moves(s)))


def test_render_bounds_every_size():
    """`Board.jsx` builds its clickable cells from board.width/height and joins
    pieces by id, so a piece outside the declared board is silently DROPPED.
    Check each size from a position reached through apply_move that puts stones
    in the far corners (a fresh state is vacuous -- no coloured pieces yet)."""
    for n in MOD.SIZES:
        g = n + 2
        s = G.initial_state({"size": n})
        far = ["1,1", cell((n, n)), cell((1, n)), cell((n, 1))]
        for mv in far:
            while s.cont:                       # finish any forced continuation
                s = G.apply_move(s, next(m for m in G.legal_moves(s)
                                         if m != "swap" and m not in far))
            ck(mv in G.legal_moves(s), f"far corner {mv} legal (n={n})")
            s = G.apply_move(s, mv)
        spec = G.render(s)
        b = spec["board"]
        ck(b["type"] == "square", "square board")
        ck(b["width"] == g and b["height"] == g, f"declared {b['width']}x{b['height']}"
                                                 f" != {g}x{g} (n={n})")
        ids = set()
        for p in spec["pieces"]:
            c, r = (int(z) for z in p["cell"].split(","))
            ck(0 <= c < g and 0 <= r < g, f"piece {p['cell']} outside {g}x{g}")
            ck(p["cell"] not in ids, f"duplicate piece at {p['cell']}")
            ids.add(p["cell"])
        for mv in far:
            ck(mv in ids, f"far-corner stone {mv} present in render (n={n})")
        ring = [p for p in spec["pieces"] if "fill" in p]
        ck(len(ring) == 4 * g - 4, f"green ring rendered (n={n}): {len(ring)}")
        ck(set(b["tints"]) == {p["cell"] for p in ring}, "ring tinted, nothing else")
        for p in ring:
            c, r = (int(z) for z in p["cell"].split(","))
            ck(MOD.is_green(n, c, r), f"fill-overridden piece {p['cell']} is not ring")
            # the ring is ownerless: it must be pinned to seat 0 AND carry both
            # colour overrides, so it can never be drawn in a seat's colour
            ck(p["owner"] == 0, f"ring piece {p['cell']} owner={p['owner']}")
            ck(p["fill"] == "#3aa93f" and p["stroke"] == "#1b6b22", "ring colours")
        stones = [p for p in spec["pieces"] if "fill" not in p]
        ck(len(stones) == len(s.board), "one rendered piece per placed stone")
        for p in stones:
            q = tuple(int(z) for z in p["cell"].split(","))
            ck(p["owner"] == s.board[q] and p["owner"] in (0, 1),
               f"stone {p['cell']} owner")
            ck("stroke" not in p, "player stones keep the seat colour")
        for h in spec["highlights"]:
            c, r = (int(z) for z in h["cell"].split(","))
            ck(1 <= c <= n and 1 <= r <= n, "highlight on a playable point")
        ck(isinstance(spec["caption"], str) and spec["caption"], "caption")
        # the ring must never be offerable as a move
        for mv in G.legal_moves(s):
            if mv == "swap":
                continue
            c, r = (int(z) for z in mv.split(","))
            ck(not MOD.is_green(n, c, r), "green point offered as a move!")


def test_describe_move():
    n = 5
    s = G.initial_state({"size": n})
    ck(G.describe_move(s, "1,1") == "A1", "A1")
    ck(G.describe_move(s, "5,5") == "E5", "E5")
    ck(G.describe_move(s, "3,2") == "C2", "C2")
    s2 = FState(size=n, board={(4, 1): BLUE, (4, 2): BLUE, (4, 3): BLUE,
                               (5, 1): BLUE}, to_move=RED, turns=4)
    ck(G.describe_move(s2, "5,2") == "E2+", "the + marks a forced continuation")
    ck(G.describe_move(s2, "2,3") == "B3", "no + when the turn ends")
    ck("I" not in MOD.GO_LETTERS, "Go lettering skips I")
    # a placement that finishes the game must NOT claim another placement
    board, k = {}, 0
    for p in MOD.playable_cells(n):
        if p == (5, 5):
            continue
        board[p] = RED if k < 12 else BLUE
        k += 1
    s3 = FState(size=n, board=board, to_move=RED, turns=20)
    ck(MOD.connections(s3.board, n, 5, 5) >= 3, "corner has 3 connections")
    ck(G.apply_move(s3, "5,5").cont is False, "no continuation at game end")
    ck(G.describe_move(s3, "5,5") == "E5", "no + on the game-ending stone")


def test_heuristic_shape():
    """Must be a LIST of num_players payoffs -- a bare float crashes MCTS
    back-propagation, and only when the rollout cutoff is actually reached."""
    from agp.mcts import MCTSBot
    s = G.initial_state({"size": 7})
    for _ in range(3):
        v = G.heuristic(s)
        ck(isinstance(v, list) and len(v) == 2, f"heuristic shape {v!r}")
        ck(all(isinstance(x, float) and -1.0 <= x <= 1.0 for x in v), "bounded")
        s = G.apply_move(s, G.legal_moves(s)[0])
    mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(G, s)
    ck(mv in G.legal_moves(s), "bot returns a legal move at a forced cutoff")


def test_oracle_frozen_counts():
    """Frozen from the AbstractPlay gameslib differential (ORACLE ONLY).
    gameslib names its variants by the FULL grid, so its default 9x9 grid is
    our playable 7 (48 opening moves = 49 - the banned centre), its "7x7"
    variant is Figure 1's board (24 = 25 - 1) and its "11x11" variant is our
    playable 9 (80).  Those three are the oracle-verified numbers; 11 and 17
    are the same `n*n - 1` arithmetic on boards gameslib does not offer."""
    for n, want in ((5, 24), (7, 48), (9, 80), (11, 120), (17, 288)):
        s = G.initial_state({"size": n})
        got = len(G.legal_moves(s))
        ck(got == want, f"opening count n={n}: {got} != {want}")
        ck(got == n * n - 1, "n*n minus the banned centre")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"flume selftest: {checks} checks passed")


if __name__ == "__main__":
    main()
