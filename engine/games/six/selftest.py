#!/usr/bin/env python3
"""Correctness anchor for SIX (Steffen Mühlhäuser, Steffen-Spiele 2003).

There is no third-party rule-enforcing implementation of Six to differential
against, so the anchor is the publisher's own rule sheet plus exhaustive /
constructed work:

 1. THE THREE WINNING FORMATIONS are pinned to the figure printed in
    `Six_EN.pdf` ("Object of the game").  The figure is a raster picture whose
    42 tiles are individually placed images; the axial coordinates below were
    recovered by measuring the tile centres at 600 dpi and fitting the hex
    lattice (residuals < 0.03 cell).  Both the figure's OUTCOME and its
    PREMISES are asserted, and the formation predicate is cross-checked against
    an INDEPENDENT geometric predicate (cube-coordinate half-planes / a
    constant cube coordinate / "equals some cell's neighbour set") over every
    6-cell subset of a 21-cell region.

 2. THE CAPTURE RULE is pinned to the sheet's "Chance to beat" figure, a real
    16-token position with five tiles crossed out.  Its cell/colour assignment
    was decoded the same way.  It settles four separate readings at once
    (below), including the crossed-out RED tile that proves captures are
    colour-blind.

 3. EVERY CLAUSE RANDOM PLAY CANNOT BE TRUSTED TO REACH is tested on
    constructed input: the equal-split tie-break (and that the choice flips the
    winner), three-way splits, both-players-below-six, a mover cutting ITSELF
    below six, and the ordering "captures resolve BEFORE the token is laid
    down".

Pure stdlib; run directly or via tests/test_games.py::test_package_selftests.
"""
import random
import sys
from dataclasses import replace
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.six.game import (                                    # noqa: E402
    Six, SState, RED, BLACK, SEAT_NAMES, DIRS, SHAPES,
    TOKENS_PER_PLAYER, START_TOKENS_PER_PLAYER, HAND_SIZE, PLACEMENT_PLIES,
    MIN_FORMATION, NO_CAPTURE_DRAW, MAX_CAPTURE_EVENTS, MAX_ROUND2_PLIES,
    PLY_CAP, _cell, _cstr, _components, _frontier, _normalise, _split_options,
    _win_shape,
)

G = Six()
CHECKS = 0


def ok(cond, msg):
    global CHECKS
    CHECKS += 1
    if not cond:
        raise AssertionError(msg)


def eq(a, b, msg):
    ok(a == b, f"{msg}: {a!r} != {b!r}")


# ==========================================================================
# Fixture helpers
# ==========================================================================
def state(red, black, to_move, **kw):
    """A round-two position (both hands empty) from two cell sets."""
    board = {c: RED for c in red}
    board.update({c: BLACK for c in black})
    kw.setdefault("ply", PLACEMENT_PLIES)
    return SState(board=board, hands=[0, 0], to_move=to_move,
                  since_capture=0, winner="none", last=[], **kw)


def line(a, b, r=0):
    return [(i, r) for i in range(a, b + 1)]


def paint(cells, pattern):
    red = [c for c, ch in zip(cells, pattern) if ch == "R"]
    blk = [c for c, ch in zip(cells, pattern) if ch == "B"]
    ok(len(red) + len(blk) == len(cells), "pattern must cover every cell")
    return red, blk


def captured_by(s, move):
    """Which cells the move takes off the table (excluding the lifted token)."""
    before = set(s.board)
    ns = G.apply_move(s, move)
    gone = before - set(ns.board)
    gone.discard(_cell(move.partition("=")[0].split(">")[0]))
    return gone, ns


def near_formation(cells, spare=True):
    """A CONNECTED, live position in which the mover (Red) holds five of the six
    cells of `cells` and can complete it by laying a token on the sixth.

    Six black tokens are grown onto the cluster (never onto the gap, never
    completing a formation for Black), then -- if `spare` -- one more red token
    is added as the token Red will pick up in round two.  Adding a cell to a
    connected field keeps it connected, so lifting that last cell again splits
    nothing: the round-two fixture captures nothing and isolates the win check.
    """
    gap = sorted(cells)[-1]
    have = [c for c in sorted(cells) if c != gap]
    field = set(have)
    ok(len(_components(field)) == 1, "the five-token core must be connected")
    blk = []
    while len(blk) < MIN_FORMATION:
        for c in sorted(_frontier(field) - {gap}):
            if not _win_shape(set(blk) | {c}):
                blk.append(c)
                field.add(c)
                break
        else:
            raise AssertionError("cannot grow a formation-free black group")
    red = list(have)
    extra = None
    if spare:
        for c in sorted(_frontier(field) - {gap}):
            if not _win_shape(set(red) | {c}):
                extra = c
                red.append(c)
                field.add(c)
                break
        ok(extra is not None, "need a spare red token")
    ok(len(_components(field)) == 1, "fixture must be one cluster")
    ok(_win_shape(set(red)) is None, "Red must not already hold a formation")
    ok(_win_shape(set(blk)) is None, "Black must not hold a formation")
    ok(gap not in field, "the gap must still be empty")
    return red, blk, gap, extra


def all_shapes(own):
    """Every winning formation inside `own` (the game only needs the first)."""
    out = []
    for template, kind in SHAPES:
        for q, r in own:
            cells = frozenset((q + dq, r + dr) for dq, dr in template)
            if cells <= own:
                out.append((kind, cells))
    return out


# ==========================================================================
# 1. THE THREE WINNING FORMATIONS
# ==========================================================================
# Decoded from Six_EN.pdf, "Object of the game" (three red figures).  The row
# is drawn rotated 90 degrees (a vertical column of flat-top tiles); the circle
# and triangle are drawn pointy-top, as is every other figure in the sheet.
FIG_CIRCLE = {(0, 0), (1, -1), (0, 1), (2, -1), (1, 1), (2, 0)}
FIG_TRIANGLE = {(0, 0), (1, 0), (2, 0), (1, -1), (2, -1), (2, -2)}
FIG_ROW = set(line(0, 5))


def test_shape_templates():
    kinds = {}
    for template, kind in SHAPES:
        kinds[kind] = kinds.get(kind, 0) + 1
        eq(len(template), MIN_FORMATION, f"{kind} template size")
        eq(len(set(template)), MIN_FORMATION, f"{kind} template has no duplicates")
        ok((0, 0) in template, f"{kind} template must contain its anchor")
        eq(min(template), (0, 0), f"{kind} anchor must be the lexicographic minimum")
        eq(_normalise(template), tuple(sorted(template)), f"{kind} already normalised")
    eq(kinds, {"row": 3, "circle": 1, "triangle": 2}, "formation template census")
    eq(len(SHAPES), 6, "six templates in total")


def test_figure_formations():
    # --- the figures' PREMISES, not only their outcome -------------------
    # circle: exactly the six neighbours of one cell, which is itself EMPTY in
    # the drawing (the sheet says its contents are irrelevant).
    centre = (1, 0)
    eq(FIG_CIRCLE, {(centre[0] + dq, centre[1] + dr) for dq, dr in DIRS},
       "circle figure = the six neighbours of (1,0)")
    ok(centre not in FIG_CIRCLE, "the circle figure's centre is not one of the six")
    # triangle: three rows of 3 / 2 / 1 tiles.
    rows = {}
    for q, r in FIG_TRIANGLE:
        rows[r] = rows.get(r, 0) + 1
    eq(sorted(rows.values(), reverse=True), [3, 2, 1], "triangle figure row sizes")
    # row: six cells on one lattice line, consecutive.
    ok(all((q, 0) in FIG_ROW for q in range(6)), "row figure is six consecutive cells")

    # --- the outcome ----------------------------------------------------
    for cells, kind in ((FIG_CIRCLE, "circle"), (FIG_TRIANGLE, "triangle"),
                        (FIG_ROW, "row")):
        got = _win_shape(cells)
        ok(got is not None, f"the printed {kind} must be a winning formation")
        eq(got[0], kind, f"the printed {kind} is classified")
        eq(set(got[1]), cells, f"the printed {kind} matches exactly its own cells")

    # a circle whose centre is filled by EITHER colour is still a win, and one
    # extra token never destroys a formation (containment, not equality).
    for extra in (centre, (3, 0), (-1, 0)):
        ok(_win_shape(FIG_CIRCLE | {extra}), f"circle + {extra} is still a win")
    ok(_win_shape(FIG_ROW | {(6, 0)}), "a row of seven contains a row of six")


def test_figure_discriminating_power():
    """Which WRONG readings of the three formations does the figure exclude?"""
    wrong = {
        # a solid 6-cell blob (a cell plus five of its six neighbours)
        "hexagon block": {(0, 0)} | {(0 + d[0], 0 + d[1]) for d in DIRS[:5]},
        # the ring with the centre filled but one arm missing
        "ring minus one plus centre": (FIG_CIRCLE - {(2, 0)}) | {(1, 0)},
        # five in a row plus a stray
        "five in a row + stray": set(line(0, 4)) | {(0, 3)},
        # a bent line of six
        "bent line": {(0, 0), (1, 0), (2, 0), (3, -1), (4, -2), (5, -3)},
        # a 2x3 parallelogram
        "parallelogram": {(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)},
        # a side-3 triangle with its apex displaced by one cell
        "triangle, apex moved": (FIG_TRIANGLE - {(2, -2)}) | {(3, -2)},
        # a "Y" of six
        "Y of six": {(0, 0), (1, 0), (2, 0), (1, -1), (1, 1), (3, 0)},
    }
    killed = [name for name, cells in wrong.items() if not _win_shape(cells)]
    for name, cells in wrong.items():
        eq(len(cells), MIN_FORMATION, f"{name} must be a 6-cell set")
        ok(_win_shape(cells) is None, f"{name} must NOT be a winning formation")
    eq(len(killed), len(wrong), "every wrong reading rejected")
    ok(len(killed) >= 7, "the anchor excludes at least seven wrong readings")


def test_independent_formation_predicate():
    """Cross-check `_win_shape` against a predicate written from a completely
    different description: cube coordinates and half-planes, never the offset
    templates or the lexicographic anchor."""
    def cube(c):
        q, r = c
        return (q, -q - r, r)

    def dist(a, b):
        ax, ay, az = cube(a)
        bx, by, bz = cube(b)
        return max(abs(ax - bx), abs(ay - by), abs(az - bz))

    def indep_row(cs):
        # all six share one cube coordinate and span exactly five steps
        for i in range(3):
            if len({cube(c)[i] for c in cs}) == 1:
                if max(dist(a, b) for a in cs for b in cs) == MIN_FORMATION - 1:
                    return True
        return False

    def indep_circle(cs):
        # equals the neighbour set of some cell
        for c in cs:
            for dq, dr in DIRS:
                mid = (c[0] + dq, c[1] + dr)
                if cs == {(mid[0] + a, mid[1] + b) for a, b in DIRS}:
                    return True
        return False

    # side of the triangular number MIN_FORMATION: 3, since 3*4/2 == 6
    side = next(n for n in range(1, 20) if n * (n + 1) // 2 == MIN_FORMATION)
    eq(side, 3, "a six-token triangle has side three")

    def indep_triangle(cs):
        # A side-3 triangle is the intersection of three cube half-planes:
        # {x >= x0, y >= y0, z >= z0} with x0 + y0 + z0 = -2 (or the same with
        # all three inequalities reversed).  Built on the INFINITE lattice, so
        # no region boundary can flatter a non-triangle into passing.
        cub = [cube(c) for c in cs]
        for sign in (1, -1):
            lo = [min(sign * v[i] for v in cub) for i in range(3)]
            if sum(lo) != -(side - 1):                  # -2 for a side-3 triangle
                continue
            region = set()
            for dx in range(side):
                for dy in range(side - dx):
                    x = sign * (lo[0] + dx)
                    z = sign * (lo[2] + (side - 1 - dx - dy))
                    region.add((x, z))                  # axial (q, r) = (x, z)
            if region == cs:
                return True
        return False

    # a 7x3 rhombus: big enough to hold rows of six, full circles and both
    # triangle orientations.
    W, H = 7, 3
    ALL = {(q, r) for q in range(W) for r in range(H)}
    seen = {"row": 0, "circle": 0, "triangle": 0}
    n = 0
    for combo in combinations(sorted(ALL), MIN_FORMATION):
        cs = set(combo)
        n += 1
        mine = _win_shape(cs)
        hits = [k for k, f in (("row", indep_row), ("circle", indep_circle),
                               ("triangle", indep_triangle)) if f(cs)]
        ok(len(hits) <= 1, f"{sorted(cs)} classified as {hits}")
        theirs = hits[0] if hits else None
        eq(None if mine is None else mine[0], theirs,
           f"independent predicate disagrees on {sorted(cs)}")
        if theirs:
            seen[theirs] += 1
    eq(n, 54264, "every 6-subset of the 21-cell region was checked")
    for kind, count in seen.items():
        ok(count > 0, f"the sweep must actually contain a {kind} (got {count})")
    # pinned counts, so a silent change to the shape set is caught
    # Hand-derived for the 7x3 rhombus (q 0..6, r 0..2), independently of any
    # code: rows -- only the constant-r direction fits six cells, 2 offsets x 3
    # rows = 6; circles -- a centre needs all six neighbours inside, so (q,1)
    # with 1 <= q <= 5 = 5; triangles -- each spans exactly 3 rows (forced) and
    # 3 columns, 5 anchor columns x 2 orientations = 10.
    eq(seen, {"row": 6, "circle": 5, "triangle": 10}, "formation census in the region")


# ==========================================================================
# 2. SETUP AND ROUND ONE
# ==========================================================================
def test_setup():
    s = G.initial_state()
    eq(len(s.board), 2 * START_TOKENS_PER_PLAYER, "two starting tokens")
    eq(sorted(s.board.values()), [RED, BLACK], "one starting token of each colour")
    (a, b) = sorted(s.board)
    ok((b[0] - a[0], b[1] - a[1]) in DIRS, "the starting tokens touch")
    eq(s.hands, [HAND_SIZE, HAND_SIZE], "each player holds 20 tokens")
    eq(HAND_SIZE, TOKENS_PER_PLAYER - START_TOKENS_PER_PLAYER, "hand size derivation")
    eq([G._stock(s, p) for p in (RED, BLACK)],
       [TOKENS_PER_PLAYER, TOKENS_PER_PLAYER], "21 tokens per colour in the game")
    eq(s.to_move, RED, "Red opens")
    ok(not G.is_terminal(s), "the opening position is not terminal")
    eq(G.legal_moves(s), sorted(_cstr(c) for c in _frontier(set(s.board))),
       "round one: every empty cell touching the cluster")
    eq(len(G.legal_moves(s)), 2 * 2 + 4, "the two-token cluster has eight free sides")


def test_round_one_touches_enemy():
    """The 2008 sheet is explicit: "Es darf an eigene und gegnerische Steine
    angelegt werden" -- you may lay a token against an enemy token."""
    s = G.initial_state()
    (red_cell,) = [c for c, o in s.board.items() if o == RED]
    (blk_cell,) = [c for c, o in s.board.items() if o == BLACK]
    enemy_only = [c for c in _frontier(set(s.board))
                  if blk_cell in [(c[0] + d[0], c[1] + d[1]) for d in DIRS]
                  and red_cell not in [(c[0] + d[0], c[1] + d[1]) for d in DIRS]]
    ok(enemy_only, "the fixture needs a cell touching only the enemy token")
    for c in enemy_only:
        ok(_cstr(c) in G.legal_moves(s), f"Red may lay a token at {c} (enemy contact)")


def play_avoiding_wins(rng, stop_after_round_one=False):
    """Play round one without completing a formation, so round two is reached."""
    s = G.initial_state()
    while not G.is_terminal(s):
        if stop_after_round_one and s.hands[s.to_move] == 0:
            return s
        ms = G.legal_moves(s)
        if s.hands[s.to_move] > 0:
            own = G._own(s, s.to_move)
            safe = [m for m in ms if not _win_shape(own | {_cell(m)})]
            ms = safe or ms
        s = G.apply_move(s, rng.choice(ms))
    return s


def test_round_one_length():
    rng = random.Random(11)
    reached = 0
    for _ in range(15):
        s = play_avoiding_wins(rng, stop_after_round_one=True)
        if s.hands == [0, 0] and not G.is_terminal(s):
            reached += 1
            eq(s.ply, PLACEMENT_PLIES, "round one is exactly 40 plies")
            eq([G._stock(s, p) for p in (RED, BLACK)],
               [TOKENS_PER_PLAYER, TOKENS_PER_PLAYER],
               "no token can be captured during round one")
            eq(len(s.board), 2 * TOKENS_PER_PLAYER, "42 tokens on the table")
            eq(len(_components(set(s.board))), 1, "the cluster is always connected")
            ok(all(">" in m for m in G.legal_moves(s)),
               "round two offers only pick-up-and-re-lay moves")
    ok(reached >= 12, f"round two should be reachable by avoiding wins (got {reached}/15)")


# ==========================================================================
# 3. THE CAPTURE FIGURE  ("Schlagmöglichkeit für schwarz / für rot")
# ==========================================================================
# Six_EN.pdf, right-hand column.  16 tiles; five are crossed out.  Decoded from
# the tile-centre lattice (spacing 162 x 139.5 px at 600 dpi, residuals < 0.03).
FIG_RED = {(0, 0), (1, -1), (2, -1), (3, -2), (2, -3), (5, -2), (5, 0)}
FIG_BLACK = {(1, 0), (2, 0), (2, -2), (3, -1), (4, -3), (4, -2),
             (4, 0), (5, -1), (6, -1)}
# the arrow labelled "Chance to beat for black" points at this crossed-out tile
FIG_BLACK_TAKES = {(2, -3)}
# the arrow labelled "Chance to beat for red" points at this crossed-out group
FIG_RED_TAKES = {(4, 0), (5, 0), (5, -1), (6, -1)}
FIG_BLACK_LIFTS = "2,-2"
FIG_RED_LIFTS = "5,-2"


def fig_state(to_move):
    return state(FIG_RED, FIG_BLACK, to_move)


def test_capture_figure_premises():
    ok(FIG_RED.isdisjoint(FIG_BLACK), "no cell holds two tokens")
    eq(len(FIG_RED), 7, "the figure shows seven red tiles")
    eq(len(FIG_BLACK), 9, "the figure shows nine black tiles")
    eq(len(FIG_RED | FIG_BLACK), 16, "sixteen tiles in total")
    eq(len(_components(FIG_RED | FIG_BLACK)), 1,
       "the figure is ONE cluster -- otherwise it could not illustrate a split")
    ok(_win_shape(FIG_RED) is None, "no red formation, or the game would be over")
    ok(_win_shape(FIG_BLACK) is None, "no black formation, or the game would be over")
    # both crossed-out targets lie in the figure and are cut off by one lift
    ok(FIG_BLACK_TAKES <= FIG_RED, "black's target tile is a RED tile")
    ok(_cell(FIG_BLACK_LIFTS) in FIG_BLACK, "black lifts a BLACK tile")
    ok(_cell(FIG_RED_LIFTS) in FIG_RED, "red lifts a RED tile")
    ok(FIG_RED_TAKES <= (FIG_RED | FIG_BLACK), "red's target group is in the figure")


def test_capture_figure_outcomes():
    # --- Black's advertised capture: one lone RED tile -------------------
    s = fig_state(BLACK)
    moves = [m for m in G.legal_moves(s) if m.startswith(FIG_BLACK_LIFTS + ">")]
    ok(moves, "black must be able to lift 2,-2")
    for m in moves:
        gone, _ = captured_by(s, m)
        eq(gone, FIG_BLACK_TAKES, f"lifting 2,-2 must capture exactly {FIG_BLACK_TAKES}")

    # --- Red's advertised capture: a group of four, INCLUDING a red tile --
    s = fig_state(RED)
    moves = [m for m in G.legal_moves(s) if m.startswith(FIG_RED_LIFTS + ">")]
    ok(moves, "red must be able to lift 5,-2")
    for m in moves:
        gone, ns = captured_by(s, m)
        eq(gone, FIG_RED_TAKES, f"lifting 5,-2 must capture exactly {FIG_RED_TAKES}")
        # THE colour-blindness discriminator: (5,0) is a RED tile and the sheet
        # crosses it out, so a capture takes your own tokens too.
        own_lost = gone & FIG_RED
        eq(own_lost, {(5, 0)}, "red loses its own crossed-out tile 5,0")
        ok(_cell(FIG_RED_LIFTS) not in gone,
           "the LIFTED token is in hand, never captured (it is not crossed out)")
        eq(len(gone & FIG_BLACK), 3, "three black tiles are crossed out")

    # the figure kills the "larger group is captured" reading
    rest = (FIG_RED | FIG_BLACK) - {_cell(FIG_RED_LIFTS)}
    comps = sorted(_components(rest), key=len)
    eq([len(c) for c in comps], [4, 11], "the lift splits 4 against 11")
    eq(comps[0], FIG_RED_TAKES, "the SMALLER group is the crossed-out one")
    ok(comps[1] != FIG_RED_TAKES, "'capture the larger group' contradicts the figure")


def test_capture_figure_marks_the_profitable_lifts():
    """The sheet marks exactly ONE "chance to beat" per colour, although black
    has three capturing lifts.  The marked ones are precisely the lifts with a
    strictly positive net gain -- which is what "chance to beat" means."""
    expect = {RED: {FIG_RED_LIFTS}, BLACK: {FIG_BLACK_LIFTS}}
    for seat in (RED, BLACK):
        s = fig_state(seat)
        profitable, capturing = set(), set()
        for m in G.legal_moves(s):
            frm = m.split(">")[0]
            gone, _ = captured_by(s, m)
            if not gone:
                continue
            capturing.add(frm)
            mine = len(gone & (FIG_RED if seat == RED else FIG_BLACK))
            if (len(gone) - mine) - mine > 0:
                profitable.add(frm)
        eq(profitable, expect[seat],
           f"seat {seat}: the profitable lifts are the figure's marked ones")
        ok(expect[seat] <= capturing, "the marked lift does capture something")
    # black really does have unmarked (losing) capture options -- so the figure
    # is NOT claiming to enumerate every capture.
    s = fig_state(BLACK)
    capturing = {m.split(">")[0] for m in G.legal_moves(s) if captured_by(s, m)[0]}
    eq(capturing, {"2,-2", "4,-2", "5,-1"}, "black's three capturing lifts")


def test_captions_pinned_to_the_figure():
    """The seat names are pinned OUTSIDE game.py: web/src/colors.js paints seat 0
    with SEAT_FILL[0] = '#d23b3b' (red), so seat 0 is the sheet's RED player;
    and the figure's own tile colours say which cells those are.  A swapped
    SEAT_NAMES tuple therefore fails here."""
    # seat 1 holds the nine tiles the sheet draws BLACK -- and is the seat that
    # can legally lift 2,-2, which the sheet draws black.
    s = fig_state(BLACK)
    eq(sorted(G._own(s, BLACK)), sorted(FIG_BLACK), "seat 1 holds the black tiles")
    ok(any(m.startswith(FIG_BLACK_LIFTS + ">") for m in G.legal_moves(s)),
       "seat 1 can lift the sheet's black tile 2,-2 (you lift your own colour)")
    cap = G.render(s)["caption"]
    ok(cap.startswith("Black"), f"in-play caption must name Black, got {cap!r}")
    ok("Red" not in cap, f"in-play caption must not name Red, got {cap!r}")

    s = fig_state(RED)
    eq(sorted(G._own(s, RED)), sorted(FIG_RED), "seat 0 holds the red tiles")
    ok(any(m.startswith(FIG_RED_LIFTS + ">") for m in G.legal_moves(s)),
       "seat 0 can lift the sheet's red tile 5,-2")
    cap = G.render(s)["caption"]
    ok(cap.startswith("Red"), f"in-play caption must name Red, got {cap!r}")
    ok("Black" not in cap, f"in-play caption must not name Black, got {cap!r}")

    # TERMINAL captions, pinned the same way.  Red completes the sheet's own
    # printed row figure; Black completes its printed circle.
    for seat, cells, kind, other in ((RED, FIG_ROW, "row", "Black"),
                                     (BLACK, FIG_CIRCLE, "circle", "Red")):
        mine, theirs, gap, _ = near_formation(cells, spare=False)
        red_cells = mine if seat == RED else theirs
        blk_cells = theirs if seat == RED else mine
        s = replace(state(red_cells, blk_cells, seat), hands=[2, 2], ply=6)
        ns = G.apply_move(s, _cstr(gap))
        eq(ns.winner, seat, f"seat {seat} wins by completing the printed {kind}")
        cap = G.render(ns)["caption"]
        ok(cap.startswith(SEAT_NAMES[seat]), f"terminal caption: {cap!r}")
        ok(kind in cap, f"terminal caption names the formation: {cap!r}")
        ok(other not in cap, f"terminal caption must not name the loser: {cap!r}")


# ==========================================================================
# 4. SPLITS AND CAPTURES ON CONSTRUCTED INPUT
# ==========================================================================
# A 21-cell straight line.  Lifting the red token in the middle leaves two
# groups of exactly ten -- the sheet's "two groups of equal size" clause -- and
# the two choices give OPPOSITE winners, so the clause is outcome-load-bearing.
TIE_LINE = line(0, 20)
TIE_PATTERN = "RRRBRRRBBB" "R" "BBBRBBBRRR"


def test_equal_split_choice_flips_the_winner():
    red, blk = paint(TIE_LINE, TIE_PATTERN)
    s = state(red, blk, RED)
    ok(not G.is_terminal(s), "fixture is a live position")
    ok(_win_shape(set(red)) is None and _win_shape(set(blk)) is None,
       "fixture holds no formation (max same-colour run is 3)")
    eq([G._stock(s, p) for p in (RED, BLACK)], [11, 10], "fixture stocks")
    choice_moves = [m for m in G.legal_moves(s) if "=" in m]
    eq({m.split(">")[0] for m in choice_moves}, {"10,0"},
       "exactly one lift splits the line into equal halves")
    eq({m.split("=")[1] for m in choice_moves}, {"0,0", "11,0"},
       "the two surviving-group choices, named by their smallest cell")
    outcomes = {}
    for token in ("0,0", "11,0"):
        m = next(m for m in choice_moves if m.endswith("=" + token))
        gone, ns = captured_by(s, m)
        eq(len(gone), 10, f"keeping {token} captures the other ten tokens")
        ok(_cell(token) in ns.board, f"the chosen group at {token} survived")
        outcomes[token] = ns.winner
    eq(outcomes, {"0,0": RED, "11,0": BLACK},
       "the tie-break choice decides who wins -- it is a real decision")
    # the choice must be OFFERED to the renderer
    spec = G.render(s)
    eq(set(spec["choiceNames"]), {"0,0", "11,0"}, "renderer offers both groups")
    ok(spec.get("choiceTitle"), "the picker has a heading")
    # a wrong or missing choice token is rejected
    for bad in ("10,0>-1,0", "10,0>-1,0=5,0"):
        try:
            G.apply_move(s, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad} must be rejected (ambiguous split)")
    # …and a spurious choice on a lift that splits nothing is rejected too
    quiet = next(m for m in G.legal_moves(s) if m.startswith("0,0>"))
    ok("=" not in quiet, "the fixture's other lifts split nothing")
    try:
        G.apply_move(s, quiet + "=0,0")
    except ValueError:
        pass
    else:
        raise AssertionError("a choice on a non-splitting lift must be rejected")


def star(a1, a2, a3):
    """A hub at (0,0) with three arms along pairwise non-adjacent directions."""
    arms = [[(i, 0) for i in range(1, a1 + 1)],
            [(0, -i) for i in range(1, a2 + 1)],
            [(-i, i) for i in range(1, a3 + 1)]]
    for x, y in ((0, 1), (0, 2), (1, 2)):
        for c in arms[x]:
            for d in arms[y]:
                ok((d[0] - c[0], d[1] - c[1]) not in DIRS,
                   f"arms {x}/{y} must not touch ({c} vs {d})")
    return arms


def test_three_way_split():
    """A hex has six neighbours, so ONE lift can create THREE groups.  The
    printed rules only describe two, so this is a documented generalisation:
    the largest group stays, every other group is captured."""
    arms = star(4, 3, 2)
    hub = (0, 0)
    s = state([hub] + arms[0], arms[1] + arms[2], RED)
    rest = set(s.board) - {hub}
    eq(sorted(len(c) for c in _components(rest)), [2, 3, 4], "three groups")
    moves = [m for m in G.legal_moves(s) if m.startswith("0,0>")]
    ok(moves, "the hub is liftable")
    ok(all("=" not in m for m in moves), "a unique largest group needs no choice")
    gone, ns = captured_by(s, moves[0])
    eq(gone, set(arms[1]) | set(arms[2]), "both smaller groups are captured")
    ok(set(arms[0]) <= set(ns.board), "the largest group survives")

    # three EQUAL groups: three choices, each keeping its own arm
    arms = star(3, 3, 3)
    s = state([hub] + arms[0], arms[1] + arms[2], RED)
    moves = [m for m in G.legal_moves(s) if m.startswith("0,0>")]
    tokens = {m.split("=")[1] for m in moves if "=" in m}
    eq(tokens, {_cstr(min(a)) for a in arms}, "three surviving-group choices")
    for arm in arms:
        token = _cstr(min(arm))
        m = next(m for m in moves if m.endswith("=" + token))
        gone, ns = captured_by(s, m)
        eq(gone, {c for a in arms if a is not arm for c in a},
           f"keeping {token} captures the other two arms")


# Captures resolve BEFORE the lifted token is laid down.  A five-token red arm
# hangs off the bridge (4,1); lifting the bridge dooms the arm.  The cell (5,0)
# touches the SURVIVING group, so laying the token there is legal -- and an
# engine that placed first and captured afterwards would see the row 0,0..5,0
# and wrongly declare Red the winner.
ORD_MAIN = [(i, 2) for i in range(4, 15)] + [(6, 1), (6, 0)]
ORD_ARM = line(0, 4)
ORD_BRIDGE = (4, 1)
ORD_MAIN_RED = [(4, 2), (6, 2), (8, 2), (10, 2), (12, 2), (14, 2)]


def test_captures_resolve_before_placement():
    red = ORD_ARM + [ORD_BRIDGE] + ORD_MAIN_RED
    blk = [c for c in ORD_MAIN if c not in ORD_MAIN_RED]
    s = state(red, blk, RED)
    ok(not G.is_terminal(s), "fixture is live")
    ok(_win_shape(set(red)) is None, "Red has no formation yet")
    ok(_win_shape(set(blk)) is None, "Black has no formation")
    rest = set(s.board) - {ORD_BRIDGE}
    eq(sorted(len(c) for c in _components(rest)), [5, 13], "the bridge lift dooms the arm")
    ok(set(ORD_ARM) | {(5, 0)} == set(line(0, 5)),
       "the arm plus 5,0 is exactly a row of six")
    m = "4,1>5,0"
    ok(m in G.legal_moves(s), "laying the token at 5,0 is legal (it touches 6,0)")
    gone, ns = captured_by(s, m)
    eq(gone, set(ORD_ARM), "the whole arm is captured")
    eq(ns.winner, "none",
       "no win: the row's other five tokens were captured before the token landed")
    ok(not _win_shape(G._own(ns, RED)), "Red holds no formation afterwards")
    eq([G._stock(ns, p) for p in (RED, BLACK)], [7, 7], "both sides stay above five")


def test_destinations_touch_the_surviving_field():
    red, blk = paint(line(0, 14), "RBRBRBRBB" "R" "RBRBR")
    s = state(red, blk, RED)
    moves = [m for m in G.legal_moves(s) if m.startswith("9,0>")]
    kept = max(_components(set(s.board) - {(9, 0)}), key=len)
    eq({m.split(">")[1] for m in moves},
       {_cstr(c) for c in _frontier(kept)} - {"9,0"},
       "destinations are exactly the surviving group's free sides")
    ok("9,0>10,0" not in moves,
       "a cell whose only neighbours are captured tokens is not a destination")
    ok("9,0>12,1" not in moves, "nor a cell beside the doomed group")
    ok("9,0>9,0" not in moves, "a token must be laid down somewhere ELSE")
    ok(all(m.split(">")[0] != m.split(">")[1] for m in G.legal_moves(s)),
       "no null move anywhere")
    # you may only lift YOUR OWN colour
    eq({_cell(m.split(">")[0]) for m in G.legal_moves(s)}, set(red),
       "only the mover's own tokens can be lifted")


def test_helper_predicates():
    """Predicates that are not on the legality path get their own tests."""
    eq(_components(set()), [], "no components in an empty field")
    eq([len(c) for c in _components({(0, 0)})], [1], "one cell, one component")
    eq(sorted(len(c) for c in _components({(0, 0), (5, 5)})), [1, 1], "two islands")
    eq(len(_frontier({(0, 0)})), 6, "a lone token has six free sides")
    eq(_frontier({(0, 0)}), {(d[0], d[1]) for d in DIRS}, "and they are its neighbours")
    eq(_frontier(set()), set(), "an empty field has no frontier")
    # a straight line of n hexes has 2n + 4 free sides (6, 8, 10, ...)
    for n in range(1, 7):
        eq(len(_frontier(set(line(0, n - 1)))), 2 * n + 4,
           f"a row of {n} has {2 * n + 4} free sides")
    # normalisation is translation invariant and idempotent
    for shift in ((0, 0), (7, -3), (-100, 40)):
        moved = {(q + shift[0], r + shift[1]) for q, r in FIG_TRIANGLE}
        eq(_normalise(moved), _normalise(FIG_TRIANGLE), f"normalise invariant under {shift}")
    eq(_normalise(_normalise(FIG_TRIANGLE)), _normalise(FIG_TRIANGLE), "idempotent")
    # a non-splitting lift yields exactly one option, with no choice token
    eq(_split_options(set(line(0, 5))), [(set(line(0, 5)), None)],
       "a connected remainder is a single forced option")
    # and _win_shape is a CONTAINMENT test, not equality
    ok(_win_shape(set(line(0, 4))) is None, "five in a row is not enough")
    ok(_win_shape(set(line(0, 5))) is not None, "six in a row is")


# ==========================================================================
# 5. HOW THE GAME ENDS
# ==========================================================================
def test_attrition_endings():
    # (a) BOTH players fall below six -> an honest DRAW (neither can ever win)
    red, blk = paint(line(0, 14), "RBRBRBRBB" "R" "RBRBR")
    s = state(red, blk, RED)
    eq([G._stock(s, p) for p in (RED, BLACK)], [8, 7], "fixture stocks")
    m = next(m for m in G.legal_moves(s) if m.startswith("9,0>"))
    ns = G.apply_move(s, m)
    eq([G._stock(ns, p) for p in (RED, BLACK)], [5, 5], "both fall to five")
    eq(ns.winner, "draw", "neither player can form a six -> draw")
    eq(G.returns(ns), [0.0, 0.0], "a genuine tie pays nothing to either side")
    ok("Draw" in G.render(ns)["caption"], "draw caption")

    # (b) the MOVER cuts ITSELF below six -> the opponent wins.  The 2013/2022
    # sheets only say "has taken so many of the OPPONENT's tokens", but the 2024
    # sheet's tie clause ("in the rare case that BOTH of you end up with fewer
    # than 6 tiles after a capture") only makes sense if the count is read for
    # both players; Yucata's independent implementation states it symmetrically
    # too; and either reading gives the SAME winner, because the win is awarded
    # "as soon as" the other player is under six.  See rules.md.
    red, blk = paint(line(0, 14), "BBRBBRBBR" "R" "RRRBR")
    s = state(red, blk, RED)
    eq([G._stock(s, p) for p in (RED, BLACK)], [8, 7], "fixture stocks")
    m = next(m for m in G.legal_moves(s) if m.startswith("9,0>"))
    ns = G.apply_move(s, m)
    eq([G._stock(ns, p) for p in (RED, BLACK)], [4, 6], "Red cut itself to four")
    eq(ns.winner, BLACK, "the player who can still form a six wins")
    cap = G.render(ns)["caption"]
    ok(cap.startswith("Black") and "Red" in cap, f"attrition caption: {cap!r}")
    # The COUNT in that caption must be the LOSER's, pinned to the fixture's own
    # stocks (asserted above), not to anything the caption code derives: a
    # mutant printing the WINNER's count says "only 6" here and is otherwise
    # invisible.
    ok("only 4 tokens" in cap, f"caption must state the loser's count: {cap!r}")

    # (c) the mover cuts the OPPONENT below six -> the mover wins
    red, blk = paint(line(0, 14), "RRBRRBRRB" "R" "BBBRB")
    s = state(red, blk, RED)
    m = next(m for m in G.legal_moves(s) if m.startswith("9,0>"))
    ns = G.apply_move(s, m)
    eq([G._stock(ns, p) for p in (RED, BLACK)], [7, 3], "Black cut to three")
    ok(G._stock(ns, BLACK) < MIN_FORMATION <= G._stock(ns, RED), "only Black is short")
    eq(ns.winner, RED, "the mover wins by attrition")
    cap = G.render(ns)["caption"]
    ok(cap.startswith("Red") and "Black" in cap, f"attrition caption: {cap!r}")
    ok("only 3 tokens" in cap, f"caption must state the loser's count: {cap!r}")


def test_each_formation_can_be_completed():
    """Complete each printed formation by a round-one placement and by a
    round-two re-lay, so the win check is exercised on both move kinds."""
    for cells, kind in ((FIG_ROW, "row"), (FIG_CIRCLE, "circle"),
                        (FIG_TRIANGLE, "triangle")):
        # round one: place the sixth token from hand
        red, blk, gap, _ = near_formation(cells, spare=False)
        s = replace(state(red, blk, RED), hands=[3, 3], ply=4)
        ok(not G.is_terminal(s), f"{kind}: fixture is live")
        ok(_cstr(gap) in G.legal_moves(s), f"{kind}: the gap is a legal placement")
        ns = G.apply_move(s, _cstr(gap))
        eq(ns.winner, RED, f"{kind} completed from hand wins")
        got = _win_shape(G._own(ns, RED))
        eq(got[0], kind, f"{kind} is the formation reported")
        ok(any(gap in set(c) for _k, c in all_shapes(G._own(ns, RED))),
           "the formation contains the token just laid")
        ok(G.is_terminal(ns) and G.returns(ns) == [1.0, -1.0], f"{kind}: Red wins")

        # round two: pick a token up and lay it into the gap (nothing captured)
        red, blk, gap, spare = near_formation(cells, spare=True)
        s2 = state(red, blk, RED)
        eq([G._stock(s2, p) for p in (RED, BLACK)], [MIN_FORMATION, MIN_FORMATION],
           f"{kind}: both sides hold exactly six tokens")
        ok(not G.is_terminal(s2), f"{kind}: round-two fixture is live")
        m = f"{_cstr(spare)}>{_cstr(gap)}"
        ok(m in G.legal_moves(s2), f"{kind}: re-laying into the gap is legal")
        gone, ns2 = captured_by(s2, m)
        eq(gone, set(), f"{kind}: the re-lay captures nothing")
        eq(ns2.winner, RED, f"{kind} completed by a re-lay wins")
        eq(_win_shape(G._own(ns2, RED))[0], kind, f"{kind} reported after a re-lay")


def test_decisive_result_outranks_the_counters():
    """A win must survive every draw counter being tripped."""
    cases = []
    # a formation win
    red, blk, gap, _ = near_formation(FIG_ROW, spare=False)
    s = replace(state(red, blk, RED), hands=[3, 3], ply=4)
    cases.append(("row win", G.apply_move(s, _cstr(gap)), RED))
    # an attrition win
    red, blk = paint(line(0, 14), "RRBRRBRRB" "R" "BBBRB")
    s = state(red, blk, RED)
    m = next(m for m in G.legal_moves(s) if m.startswith("9,0>"))
    cases.append(("attrition win", G.apply_move(s, m), RED))
    # a self-inflicted attrition loss
    red, blk = paint(line(0, 14), "BBRBBRBBR" "R" "RRRBR")
    s = state(red, blk, RED)
    m = next(m for m in G.legal_moves(s) if m.startswith("9,0>"))
    cases.append(("self attrition", G.apply_move(s, m), BLACK))
    # the both-short draw must ALSO survive (it is a real result, not a counter)
    red, blk = paint(line(0, 14), "RBRBRBRBB" "R" "RBRBR")
    s = state(red, blk, RED)
    m = next(m for m in G.legal_moves(s) if m.startswith("9,0>"))
    cases.append(("both short", G.apply_move(s, m), "draw"))

    for tag, ns, winner in cases:
        eq(ns.winner, winner, f"{tag}: baseline result")
        base = G.returns(ns)
        for poisoned in (replace(ns, ply=10 ** 9),
                         replace(ns, since_capture=10 ** 9),
                         replace(ns, ply=PLY_CAP, since_capture=NO_CAPTURE_DRAW),
                         replace(ns, ply=10 ** 9, since_capture=10 ** 9)):
            ok(G.is_terminal(poisoned), f"{tag}: still terminal")
            eq(poisoned.winner, winner, f"{tag}: winner unchanged by the counters")
            eq(G.returns(poisoned), base, f"{tag}: payoffs unchanged by the counters")
            cap = G.render(poisoned)["caption"]
            ok("no capture" not in cap,
               f"{tag}: a decisive caption must not become a counter draw ({cap!r})")


def test_no_capture_draw_rule():
    """The added draw rule itself: it fires, it is symmetric, and it is the
    only draw mechanism that CAN fire (PLY_CAP is provably unreachable)."""
    red, blk = paint(line(0, 14), "RBRBRBRBB" "R" "RBRBR")
    s = replace(state(red, blk, RED), since_capture=NO_CAPTURE_DRAW - 1)
    ok(not G.is_terminal(s), "one ply short of the no-capture draw")
    s2 = replace(s, since_capture=NO_CAPTURE_DRAW)
    ok(G.is_terminal(s2), "the no-capture draw fires")
    eq(G.returns(s2), [0.0, 0.0], "and it is a draw")
    ok("no capture" in G.render(s2)["caption"], "and says so")
    eq(G.legal_moves(s2), [], "a terminal state offers no move")
    # arithmetic: derived, not pinned
    eq(MAX_CAPTURE_EVENTS, 2 * TOKENS_PER_PLAYER - 2 * MIN_FORMATION + 1,
       "capture-event bound derivation")
    eq(MAX_CAPTURE_EVENTS, 31, "…which is 31 for the shipped component count")
    eq(MAX_ROUND2_PLIES,
       MAX_CAPTURE_EVENTS + (MAX_CAPTURE_EVENTS + 1) * NO_CAPTURE_DRAW,
       "round-two length bound derivation")
    ok(PLY_CAP > PLACEMENT_PLIES + MAX_ROUND2_PLIES,
       "PLY_CAP must be strictly above the provable maximum, i.e. dead code")


# ==========================================================================
# 6. STATE PLUMBING
# ==========================================================================
SER_KEYS = {"board", "hands", "to_move", "ply", "since_capture", "winner", "last"}


def test_serialize_round_trip():
    rng = random.Random(707)
    n = 0
    for _ in range(6):
        s = G.initial_state()
        while True:
            d = G.serialize(s)
            eq(set(d), SER_KEYS, "serialize emits exactly the state's fields")
            eq(G.deserialize(d), s, "deserialize(serialize(s)) must equal s")
            # every key is load-bearing: dropping one must NOT silently default
            for k in SER_KEYS:
                trimmed = {kk: vv for kk, vv in d.items() if kk != k}
                try:
                    G.deserialize(trimmed)
                except KeyError:
                    pass
                else:
                    raise AssertionError(f"{k} silently re-defaults on deserialize")
            n += 1
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    ok(n > 200, f"swept {n} states through serialize")


def test_render_contains_its_pieces():
    """Board.jsx joins pieces to the DECLARED cell set by id, so a piece outside
    it is silently dropped.  The playing area here is UNBOUNDED and drifts, so
    check it at a far-offset position reached THROUGH apply_move."""
    rng = random.Random(31337)
    shift = (-137, 88)
    red, blk = paint([(q + shift[0], r + shift[1]) for q, r in line(0, 14)],
                     "RBRBRBRBB" "R" "RBRBR")
    s = state(red, blk, RED)
    checked = 0
    for m in G.legal_moves(s)[:6]:
        ns = G.apply_move(s, m)
        spec = G.render(ns)
        cells = set(spec["board"]["cells"])
        for p in spec["pieces"]:
            ok(p["cell"] in cells, f"piece at {p['cell']} outside the declared board")
        for h in spec["highlights"]:
            ok(h["cell"] in cells, "highlight outside the declared board")
        ok(any(int(c.split(",")[0]) < -100 for c in cells), "the board really drifted")
        checked += 1
    ok(checked == 6, "checked several far-offset positions")

    # and over whole games, both rounds
    for _ in range(3):
        s = G.initial_state()
        while True:
            spec = G.render(s)
            cells = set(spec["board"]["cells"])
            eq(spec["board"]["type"], "hex", "hex board")
            ok(isinstance(spec["board"]["cells"], list), "cells is a LIST of id strings")
            for p in spec["pieces"]:
                ok(p["cell"] in cells, "piece inside the declared board")
            eq(len(spec["pieces"]), len(s.board), "every token is rendered")
            if not G.is_terminal(s):
                for m in G.legal_moves(s):
                    dest = m.partition("=")[0].split(">")[-1]
                    ok(dest in cells, f"legal target {dest} must be clickable")
                if any(s.hands):
                    ok("reserve" in spec, "round one shows the hand trays")
                else:
                    ok("reserve" not in spec, "round two has no tray to show")
            if G.is_terminal(s):
                break
            s = G.apply_move(s, random.Random(s.ply + 5).choice(G.legal_moves(s)))


def test_describe_move():
    s = G.initial_state()
    m = G.legal_moves(s)[0]
    d = G.describe_move(s, m)
    ok(d.startswith("Red") and m in d, f"placement description: {d!r}")
    red, blk = paint(line(0, 14), "RBRBRBRBB" "R" "RBRBR")
    s2 = state(red, blk, RED)
    m2 = next(m for m in G.legal_moves(s2) if m.startswith("9,0>"))
    d2 = G.describe_move(s2, m2)
    ok("captures 5" in d2, f"a capturing move should say so: {d2!r}")
    m3 = next(m for m in G.legal_moves(s2) if m.startswith("0,0>"))
    ok("captures" not in G.describe_move(s2, m3), "a quiet move says nothing")
    # THE MOVE LOG NAMES THE MOVER, pinned the same way as the captions: the
    # seat that can lift the sheet's black tile 2,-2 must be logged as "Black".
    for seat, name, other, lift in ((BLACK, "Black", "Red", FIG_BLACK_LIFTS),
                                    (RED, "Red", "Black", FIG_RED_LIFTS)):
        sf = fig_state(seat)
        mv = next(m for m in G.legal_moves(sf) if m.startswith(lift + ">"))
        d = G.describe_move(sf, mv)
        ok(d.startswith(name), f"move log must name the mover ({name}): {d!r}")
        ok(other not in d, f"move log must not name the other player: {d!r}")


# ==========================================================================
# 7. WHOLE-GAME INVARIANTS
# ==========================================================================
def test_game_invariants():
    rng = random.Random(20260805)
    max_since = 0
    max_ply = 0
    endings = {}
    tie_plies = 0
    max_events = 0
    for i in range(70):
        s = G.initial_state()
        events = 0
        while not G.is_terminal(s):
            before = G.serialize(s)
            ms = G.legal_moves(s)
            ok(ms, f"a non-terminal state must offer a move (ply {s.ply})")
            ok(len(set(ms)) == len(ms), "legal_moves has no duplicates")
            # STEP 1 OF THE TERMINATION PROOF, checked against live positions:
            # while the game is still running BOTH players hold at least
            # MIN_FORMATION tokens (else `_result` would have ended it), so at
            # least 2*MIN_FORMATION tokens are still in the game.
            for p in (RED, BLACK):
                ok(G._stock(s, p) >= MIN_FORMATION,
                   f"live position with {G._stock(s, p)} tokens for seat {p}")
            ok(len(s.board) + sum(s.hands) >= 2 * MIN_FORMATION,
               "at least twelve tokens remain while the game runs")
            mover = s.to_move
            if s.hands[mover] == 0:
                tie_plies += sum(1 for m in ms if "=" in m)
            m = rng.choice(ms)
            ns = G.apply_move(s, m)
            eq(G.serialize(s), before, "apply_move must not mutate its input")
            eq(ns.to_move, 1 - mover, "the turn passes")
            eq(ns.ply, s.ply + 1, "ply advances by one")
            # stocks never grow, and never shrink during round one
            for p in (RED, BLACK):
                ok(G._stock(ns, p) <= G._stock(s, p), "stocks never grow")
                if s.hands[mover] > 0:
                    eq(G._stock(ns, p), G._stock(s, p), "round one captures nothing")
            # THE LEMMA behind checking only the mover: the non-mover can never
            # newly hold a formation (placements only add the mover's token, and
            # a capture only ever DELETES tokens).
            if _win_shape(G._own(ns, 1 - mover)):
                ok(_win_shape(G._own(ns, mover)),
                   f"non-mover formation appeared alone at ply {ns.ply}")
            # the field is one cluster at all times
            if ns.board:
                eq(len(_components(set(ns.board))), 1, "the field stays connected")
            # STEP 2 OF THE PROOF: a capture event removes at least one token
            # from the game, and the counter resets exactly then.
            total_before = len(s.board) + sum(s.hands)
            total_after = len(ns.board) + sum(ns.hands)
            if ns.since_capture == 0 and s.hands[mover] == 0:
                events += 1
                ok(total_after < total_before,
                   "a capture event must take at least one token out of the game")
            elif s.hands[mover] == 0:
                eq(total_after, total_before, "a quiet round-two ply takes nothing")
                eq(ns.since_capture, s.since_capture + 1, "…and advances the counter")
            max_since = max(max_since, ns.since_capture)
            s = ns
        max_ply = max(max_ply, s.ply)
        max_events = max(max_events, events)
        # STEP 3: the number of capture events is bounded
        ok(events <= MAX_CAPTURE_EVENTS,
           f"{events} capture events exceeds the bound {MAX_CAPTURE_EVENTS}")
        ok(s.ply <= PLACEMENT_PLIES + MAX_ROUND2_PLIES, "within the proven bound")
        r = G.returns(s)
        eq(len(r), 2, "two payoffs")
        eq(sum(r), 0.0, "zero sum")
        if s.winner in (RED, BLACK):
            shape = _win_shape(G._own(s, s.winner))
            endings["shape" if shape else "attrition"] = \
                endings.get("shape" if shape else "attrition", 0) + 1
            if not shape:
                ok(G._stock(s, 1 - s.winner) < MIN_FORMATION, "the loser is short")
        else:
            endings["draw"] = endings.get("draw", 0) + 1
    # the sweep must actually exercise round two and the tie clause
    ok(endings.get("shape", 0) > 0, "some games end on a formation")
    ok(endings.get("attrition", 0) > 0, "some games end on attrition")
    ok(max_ply > PLACEMENT_PLIES, f"some games reach round two (max ply {max_ply})")
    ok(tie_plies > 0, f"the equal-split clause is reached ({tie_plies} plies)")
    # the added draw rule never fires under random play: measured margin
    ok(max_since < NO_CAPTURE_DRAW,
       f"no-capture counter reached {max_since} of {NO_CAPTURE_DRAW}")
    ok(max_since * 2 < NO_CAPTURE_DRAW,
       f"and with margin to spare (reached {max_since})")
    ok(0 < max_events <= MAX_CAPTURE_EVENTS,
       f"captures happen, and stay inside the bound (most seen: {max_events})")


def test_no_heuristic_is_shipped():
    """Six ships NO `heuristic`.  The rollout cutoff DOES fire (19% of rollouts
    measured over complete games), so an eval here would not be inert -- but a
    candidate's strength through `MCTSBot`, the consumer, was never measured to a
    conclusion, and an unmeasured eval is worse than none (a sign-flipped or
    worthless one passes every shape check).  See rules.md.  Assert the absence,
    so adding one forces the measurement."""
    ok(not hasattr(G, "heuristic"),
       "Six must not ship a heuristic without a measurement through MCTSBot")


# ==========================================================================
def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"six selftest: {len(tests)} tests, {CHECKS} checks passed")


if __name__ == "__main__":
    main()
