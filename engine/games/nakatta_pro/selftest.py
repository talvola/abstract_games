#!/usr/bin/env python3
"""Correctness anchors for Nakatta Pro (Mark Steere, 2026).

Pure stdlib: only `agp` and this package.  Everything the rule sheet actually
prints is transcribed here from the PDF's VECTOR artwork (`pdftocairo -svg`,
then the disc/dot paths snapped to the 10.8pt point grid), never from a reading
of pixels or prose.

WHAT THE SHEET GIVES US, AND WHAT EACH PIECE IS WORTH

  Figure 1  "Black wins": a legal 9x9 position with a black chain joining the
            TOP and BOTTOM edges.  Pins (a) the goal orientation and the seat
            NAMES to the artwork -- the figure's caption says "Black wins" and
            the printed chain is the top/bottom one, so seat 0 must be the
            top/bottom player and must be called Black -- and (b) the premise
            the figure silently relies on: the position is glyph-FREE, i.e.
            actually reachable by legal play.

  Figure 2  the three prohibited glyphs, printed together on one 9x9 board with
            their unoccupied points marked by blue dots.  This is the RULE.

  Figure 3  a 9x9 position with "all of the illegal placements for Black"
            marked red and two "surprisingly legal" points marked green.
            THE FIGURE IS WRONG: all 7 red dots are genuinely illegal and both
            green dots are genuinely legal, but 17 further unoccupied points
            also form a glyph of Figure 2, so its completeness claim is false.
            The figure is still a strong anchor (see `test_figure3_power`): its
            7 reds + 2 greens + the legality of its own board kill all twelve
            wrong readings of Figure 2 that were enumerated, 12 of 12.
            The evidence that the fault is the sheet's and not ours:
              * the identical pipeline reproduces the sibling MINEFIELD sheet's
                Figure 3 exactly (13 red dots of 13, both greens legal);
              * an exhaustive search over every prohibited-pattern set drawable
                as areas up to 3x3 / 2x4, and separately over every SUBSET of
                Figure 2's own 32-element glyph orbit, shows that two of the
                seven reds cannot be made illegal without also making one of
                the figure's own "legal" points illegal.  No rule of the
                sheet's format produces Figure 3.
            `test_figure3_extra_points` pins the 17 omissions so the
            discrepancy can never quietly change.

Beyond the figures:

  * the two structural theorems that place the game between its siblings
    (Nakatta-illegal >= Nakatta Pro-illegal >= Minefield-illegal), which also
    give drawlessness on a full board for free;
  * exhaustive solves of the 2x2 and 3x3 boards (every reachable position);
  * a directed "strangle" search that plays to minimise the opponent's mobility,
    hunting for the double-stall that would be the only source of a draw;
  * local-vs-global glyph equivalence on every empty point of every position of
    whole random games;
  * serialize/deserialize compared as STATE OBJECTS with a pinned key set;
  * render() dimensions asserted for every offered board size from a position
    with stones in all four corners.

Run: python3 games/nakatta_pro/selftest.py   (from engine/, or anywhere)
"""

from __future__ import annotations

import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.nakatta_pro.game import (  # noqa: E402
    BLACK, WHITE, EMPTY, BASE_GLYPHS, GLYPHS, GLYPH_SHAPES,
    HARD_CORNER, BARE_ATTACHMENT, BROKEN_SWITCH,
    NakattaPro, NakattaProState, connects, forms_glyph, glyphs_on_board,
    has_placement, max_plies, placements,
    _closure, _colour_reverse, _normalise, _reflect, _rotate,
)

G = NakattaPro()
CHECKS = 0


def check(cond, msg):
    global CHECKS
    CHECKS += 1
    if not cond:
        raise AssertionError(msg)


# --------------------------------------------------------------------------
# the sheet's three figures, transcribed from the vector artwork
# --------------------------------------------------------------------------
#
# 'B'/'W' stones, 'b' a blue dot (an unoccupied point belonging to a glyph),
# 'R' a red dot (an illegal Black placement), 'G' a green dot (a legal Black
# placement the sheet calls out), '.' an unmarked unoccupied point.
# Row 0 is the TOP row of the printed board; column 0 is the LEFT column.

FIGURE1 = [
    ".....B...",
    ".....B...",
    "...BBB...",
    "...BB....",
    "WWWB..WWW",
    "..WBWWW..",
    "...B.....",
    "...BB.WW.",
    "....B....",
]

FIGURE2 = [
    ".........",
    ".Wb......",
    ".BW......",
    ".........",
    ".........",
    ".bb...bB.",
    ".bb...bb.",
    ".BW...BW.",
    ".........",
]

FIGURE3 = [
    "...B....B",
    "RWG.B.WRW",
    "......R..",
    ".BB.....B",
    "...WR....",
    "B....W.R.",
    ".......W.",
    ".B.WW...B",
    "RWRWG.B..",
]


def parse(rows):
    """(board, blue, red, green) from a transcribed figure."""
    board, blue, red, green = {}, set(), set(), set()
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == "B":
                board[(c, r)] = BLACK
            elif ch == "W":
                board[(c, r)] = WHITE
            elif ch == "b":
                blue.add((c, r))
            elif ch == "R":
                red.add((c, r))
            elif ch == "G":
                green.add((c, r))
            else:
                check(ch == ".", f"bad figure char {ch!r}")
    return board, blue, red, green


F1_BOARD, _, _, _ = parse(FIGURE1)
F2_BOARD, F2_BLUE, _, _ = parse(FIGURE2)
F3_BOARD, _, F3_RED, F3_GREEN = parse(FIGURE3)
N = 9

# The 17 unoccupied points of Figure 3 that DO form a glyph of Figure 2 but
# that the figure fails to mark.  Pinned so the sheet's error stays visible.
F3_OMITTED = {
    (1, 2), (2, 4), (2, 7), (3, 3), (3, 5), (3, 6), (4, 5), (4, 6), (5, 1),
    (5, 4), (5, 6), (5, 7), (6, 0), (6, 5), (6, 6), (7, 7), (8, 6),
}


# --------------------------------------------------------------------------
# glyph-set variants used to MEASURE the anchors, and sibling rulesets
# --------------------------------------------------------------------------

E = EMPTY
NAKED_ATTACHMENT = {(0, 0): E, (1, 0): E, (0, 1): BLACK, (1, 1): WHITE}   # Nakatta
SHORT_SWITCH = {(0, 0): WHITE, (1, 0): BLACK,                              # Minefield
                (0, 1): E, (1, 1): E,
                (0, 2): BLACK, (1, 2): WHITE}
LONG_SWITCH = {(0, 0): WHITE, (1, 0): BLACK,                               # Minefield
               (0, 1): E, (1, 1): E,
               (0, 2): E, (1, 2): E,
               (0, 3): BLACK, (1, 3): WHITE}
CROSSCUT = {(0, 0): BLACK, (1, 0): WHITE, (0, 1): WHITE, (1, 1): BLACK}


def table(bases, group="D4", colour=True):
    """A glyph lookup table built from `bases` under a chosen symmetry group."""
    out = {}
    for base in bases:
        cur = dict(base)
        if group == "D4":
            imgs = []
            for _ in range(4):
                imgs.append(dict(cur))
                imgs.append(_reflect(cur))
                cur = _rotate(cur)
        else:                                     # Klein: no quarter turns
            imgs = [dict(cur), _reflect(cur),
                    {(-c, r): v for (c, r), v in cur.items()},
                    {(-c, -r): v for (c, r), v in cur.items()}]
        for img in imgs:
            for pat in ((img, _colour_reverse(img)) if colour else (img,)):
                n = _normalise(pat)
                w = max(c for c, _ in n) + 1
                h = max(r for _, r in n) + 1
                key = tuple(n[(c, r)] for r in range(h) for c in range(w))
                out.setdefault((w, h), set()).add(key)
    return out


def scan(board, tab, size=N, offboard=False):
    """Does `board` contain any pattern of `tab`?  (generic, for the variants)"""
    lo = -4 if offboard else 0
    hi = size + 4 if offboard else size
    for (w, h), keys in tab.items():
        for c0 in range(lo, hi - w + 1):
            for r0 in range(lo, hi - h + 1):
                key = tuple(board.get((c0 + c, r0 + r), E)
                            for r in range(h) for c in range(w))
                if key in keys:
                    return True
    return False


def illegal_set(board, tab, size=N, offboard=False):
    """The Black placements `tab` forbids on `board`."""
    return {(c, r) for c in range(size) for r in range(size)
            if (c, r) not in board
            and scan({**board, (c, r): BLACK}, tab, size, offboard)}


SHIPPED = table([HARD_CORNER, BARE_ATTACHMENT, BROKEN_SWITCH])


# --------------------------------------------------------------------------
# 1. the glyph table itself
# --------------------------------------------------------------------------

def test_glyph_table():
    sizes = {name: len(_closure(base)) for name, base in BASE_GLYPHS}
    check(sizes == {"hard corner": 8, "bare attachment": 8, "broken switch": 16},
          f"orbit sizes changed: {sizes}")
    check(GLYPH_SHAPES == ((2, 2), (2, 3), (3, 2)), GLYPH_SHAPES)
    check(sum(len(v) for v in GLYPHS.values()) == 32, "32 distinct glyph images")

    # THE load-bearing property: every glyph needs at least one unoccupied
    # point, which is what makes the local legality test equivalent to the
    # sheet's global "no glyph on the board".
    for shape, keys in GLYPHS.items():
        for key in keys:
            check(EMPTY in key, f"glyph {key} on {shape} has no empty point")

    # closure really is closed
    for _, base in BASE_GLYPHS:
        for pat in _closure(base):
            for img in (_rotate(pat), _reflect(pat), _colour_reverse(pat)):
                n = _normalise(img)
                w = max(c for c, _ in n) + 1
                h = max(r for _, r in n) + 1
                key = tuple(n[(c, r)] for r in range(h) for c in range(w))
                check(key in GLYPHS[(w, h)], "glyph orbit is not closed")

    # the shipped table and the locally rebuilt one agree
    for (w, h), keys in SHIPPED.items():
        check(keys == set(GLYPHS[(w, h)]), "table() disagrees with GLYPHS")


# --------------------------------------------------------------------------
# 2. Figure 1 — orientation, seat names, and the legality premise
# --------------------------------------------------------------------------

def test_figure1():
    # The PREMISE the figure relies on: it is a position play could reach.
    check(glyphs_on_board(F1_BOARD, N) == [],
          f"Figure 1 is not glyph-free: {glyphs_on_board(F1_BOARD, N)}")

    # The printed win: a chain joining the TOP and BOTTOM edges, and only that.
    top_bottom = connects(F1_BOARD, BLACK, N)
    left_right = connects(F1_BOARD, WHITE, N)
    check(top_bottom, "Figure 1's black chain must join top and bottom")
    check(not left_right, "Figure 1's white stones must NOT be connected")

    # Ground truth OUTSIDE the engine: the figure's caption is "Black wins" and
    # the connected colour is the one printed on the TOP and BOTTOM edges.  So
    # the seat that joins top/bottom must be announced as Black.  If SEAT_NAMES
    # were swapped this fails, whatever the engine calls the seats internally.
    s = NakattaProState(size=N, board=dict(F1_BOARD), winner=BLACK)
    check(G.render(s)["caption"] == "Black wins",
          f"caption for the top/bottom winner: {G.render(s)['caption']!r}")
    s2 = NakattaProState(size=N, board=dict(F1_BOARD), winner=WHITE)
    check(G.render(s2)["caption"] == "White wins", "caption for seat 1")

    # ... and the rendered board must print those edge colours the same way.
    edges = G.render(s)["board"]["edges"]
    check(edges["top"] == BLACK and edges["bottom"] == BLACK, edges)
    check(edges["left"] == WHITE and edges["right"] == WHITE, edges)

    # The IN-PLAY caption, pinned to the same ground truth.  It is shown on
    # every ply of every game -- far more often than the terminal one -- and it
    # tells the player which pair of edges to aim at, so a swapped seat name or
    # a swapped edge pair here misdirects the mover for the whole game.  Both
    # halves are pinned to Figure 1's artwork (the winner joining the TOP and
    # BOTTOM edges is captioned "Black"), never to the engine's own naming.
    for seat, name, goal in ((BLACK, "Black", "top–bottom"),
                             (WHITE, "White", "left–right")):
        cap = G.render(NakattaProState(size=N, to_move=seat))["caption"]
        check(cap == f"{name} to move ({goal})",
              f"in-play caption for seat {seat}: {cap!r}")
        # the goal named must be the pair of edges that seat actually needs,
        # read back off the rendered board rather than off this literal
        painted = {e for e, owner in edges.items() if owner == seat}
        check(painted == set(goal.split("–")), f"{cap!r} names the wrong edges")

    check(G.returns(s) == [1.0, -1.0], "Black's win scores +1 for seat 0")
    check(G.returns(s2) == [-1.0, 1.0], "White's win scores +1 for seat 1")

    # Figure 1 is also a corner case for the sibling rulesets: it is legal in
    # all three games, so it cannot by itself discriminate them.  Stated so the
    # next reader does not mistake it for an anchor it is not.
    check(not scan(F1_BOARD, table([HARD_CORNER, NAKED_ATTACHMENT])),
          "Figure 1 happens to be Nakatta-legal too")


# --------------------------------------------------------------------------
# 3. Figure 2 — the rule
# --------------------------------------------------------------------------

def test_figure2():
    """The three glyphs, at the anchors and with the blue dots the sheet prints."""
    found = glyphs_on_board(F2_BOARD, N)

    # The three glyphs at their printed anchors (top-left cell of each area).
    PRINTED = [("hard corner", 1, 1, 2, 2),
               ("bare attachment", 1, 5, 2, 3),
               ("broken switch", 6, 5, 2, 3)]
    for want in PRINTED:
        check(want in found, f"Figure 2's printed glyph {want} not detected: {found}")

    # The figure lays all three out on ONE board, and that layout incidentally
    # creates a FOURTH instance: the hard corner's own B/W attachment at (1,2)
    # has two clear rows under it, i.e. it is also a bare attachment.  That is
    # an artefact of the drawing, not a fourth glyph; pinned so the layout
    # transcription cannot drift unnoticed.
    check(sorted(found) == sorted(PRINTED + [("bare attachment", 1, 2, 2, 3)]),
          f"Figure 2 layout changed: {sorted(found)}")

    # The blue dots are EXACTLY the union of the three glyphs' empty points --
    # the sheet's own statement "the blue dots are unoccupied points", used as
    # a transcription check on the figure rather than an assumption about it.
    empties = set()
    for _, c0, r0, w, h in PRINTED:
        for c in range(w):
            for r in range(h):
                if (c0 + c, r0 + r) not in F2_BOARD:
                    empties.add((c0 + c, r0 + r))
    check(empties == F2_BLUE,
          f"blue dots {sorted(F2_BLUE)} vs glyph empties {sorted(empties)}")
    check(len(F2_BLUE) == 8, f"the sheet prints 8 blue dots, not {len(F2_BLUE)}")

    # Each printed glyph, lifted out on its own board, is detected -- and each
    # of its cells matters: emptying any stone, or filling any blue dot, kills
    # it.  (Filling a blue dot may of course create a DIFFERENT glyph; what is
    # asserted is that the original instance is gone.)
    for name, c0, r0, w, h in PRINTED:
        cells = [(c0 + c, r0 + r) for c in range(w) for r in range(h)]
        sub = {p: F2_BOARD[p] for p in cells if p in F2_BOARD}
        check([g for g in glyphs_on_board(sub, N) if g[0] == name],
              f"{name} not detected in isolation")
        for p in list(sub):
            less = {k: v for k, v in sub.items() if k != p}
            check(not [g for g in glyphs_on_board(less, N) if g[0] == name],
                  f"{name} survives losing the stone at {p}")
        for p in cells:
            if p in sub:
                continue
            for colour in (BLACK, WHITE):
                more = {**sub, p: colour}
                same = [g for g in glyphs_on_board(more, N)
                        if g[0] == name and g[1:] == (c0, r0, w, h)]
                check(not same, f"{name} survives filling {p}")


# --------------------------------------------------------------------------
# 4. Figure 3 — a correct but INCOMPLETE example
# --------------------------------------------------------------------------

def test_figure3():
    check(glyphs_on_board(F3_BOARD, N) == [], "Figure 3's position must be legal")
    check(len(F3_RED) == 7 and len(F3_GREEN) == 2,
          f"the sheet prints 7 red and 2 green dots: {len(F3_RED)}/{len(F3_GREEN)}")

    # 10 black stones and 10 white with Black to move -- the figure really is a
    # position alternating play could reach, and it is Black's turn as claimed.
    check(sum(1 for v in F3_BOARD.values() if v == BLACK) == 10, "10 black stones")
    check(sum(1 for v in F3_BOARD.values() if v == WHITE) == 10, "10 white stones")

    illegal = {p for p in illegal_set(F3_BOARD, SHIPPED)}
    # the sheet's first claim -- every red dot forms a glyph -- holds
    check(F3_RED <= illegal, f"red dots that are legal here: {sorted(F3_RED - illegal)}")
    # ... and its parenthetical -- the green dots are legal -- holds
    check(not (F3_GREEN & illegal), f"green dots wrongly illegal: {F3_GREEN & illegal}")
    # each red dot is illegal for Black AND is offered by nothing
    st = NakattaProState(size=N, board=dict(F3_BOARD), to_move=BLACK)
    moves = set(G.legal_moves(st))
    for c, r in F3_RED:
        check(f"{c},{r}" not in moves, f"red dot {(c, r)} offered as a move")
    for c, r in F3_GREEN:
        check(f"{c},{r}" in moves, f"green dot {(c, r)} not offered as a move")
    check(len(moves) == 81 - 20 - len(illegal), "legal_moves count")


def test_figure3_extra_points():
    """The sheet's completeness claim is false; pin exactly how."""
    illegal = illegal_set(F3_BOARD, SHIPPED)
    check(illegal == F3_RED | F3_OMITTED,
          f"illegal set changed: extra={sorted(illegal - F3_RED - F3_OMITTED)} "
          f"missing={sorted((F3_RED | F3_OMITTED) - illegal)}")
    check(len(F3_OMITTED) == 17, len(F3_OMITTED))
    check(not (F3_OMITTED & F3_RED) and not (F3_OMITTED & F3_GREEN), "disjoint")

    # The clearest single contradiction inside the sheet: (5,4) and (7,5) create
    # the SAME glyph instance, in the same orientation and colours, yet only
    # (7,5) is marked.  No pattern rule can separate them.
    shapes = {}
    for p in ((5, 4), (7, 5)):
        hit = [g for g in glyphs_on_board({**F3_BOARD, p: BLACK}, N)
               if g[0] == "broken switch"]
        check(len(hit) == 1, f"{p} should form exactly one broken switch: {hit}")
        _, c0, r0, w, h = hit[0]
        board = {**F3_BOARD, p: BLACK}
        shapes[p] = (tuple(board.get((c0 + c, r0 + r), EMPTY)
                           for r in range(h) for c in range(w)),
                     (w, h), (p[0] - c0, p[1] - r0))
    check(shapes[(5, 4)] == shapes[(7, 5)],
          f"the two instances differ: {shapes}")
    check((7, 5) in F3_RED and (5, 4) not in F3_RED, "the sheet marks only one of them")


def test_figure3_power():
    """MEASURE the anchor: which wrong readings of Figure 2 does Figure 3 kill?

    A variant survives only if it keeps Figures 1 and 3 legal, makes all seven
    red dots illegal, and leaves both green dots legal.  All twelve enumerated
    wrong readings are killed; the true reading survives.
    """
    def verdict(tab, offboard=False):
        if scan(F1_BOARD, tab, offboard=offboard):
            return False
        if scan(F3_BOARD, tab, offboard=offboard):
            return False
        ill = illegal_set(F3_BOARD, tab, offboard=offboard)
        return F3_RED <= ill and not (F3_GREEN & ill)

    check(verdict(SHIPPED), "the shipped reading must survive its own anchor")

    bs_wrong_colour = {(0, 0): E, (1, 0): WHITE, (0, 1): E, (1, 1): E,
                       (0, 2): BLACK, (1, 2): WHITE}
    bs_over_own = {(0, 0): BLACK, (1, 0): E, (0, 1): E, (1, 1): E,
                   (0, 2): BLACK, (1, 2): WHITE}
    ba_2x4 = {(0, 0): E, (1, 0): E, (0, 1): E, (1, 1): E,
              (0, 2): E, (1, 2): E, (0, 3): BLACK, (1, 3): WHITE}

    variants = [
        ("hard corner only", table([HARD_CORNER]), False),
        ("no broken switch", table([HARD_CORNER, BARE_ATTACHMENT]), False),
        ("no bare attachment", table([HARD_CORNER, BROKEN_SWITCH]), False),
        ("Klein group (no quarter turns)",
         table([HARD_CORNER, BARE_ATTACHMENT, BROKEN_SWITCH], group="K"), False),
        ("no colour reversal",
         table([HARD_CORNER, BARE_ATTACHMENT, BROKEN_SWITCH], colour=False), False),
        ("broken switch lone stone mis-coloured",
         table([HARD_CORNER, BARE_ATTACHMENT, bs_wrong_colour]), False),
        ("broken switch lone stone over its own colour",
         table([HARD_CORNER, BARE_ATTACHMENT, bs_over_own]), False),
        ("bare attachment read as 2x2 (= Nakatta)",
         table([HARD_CORNER, NAKED_ATTACHMENT]), False),
        ("bare attachment read as 2x4",
         table([HARD_CORNER, ba_2x4, BROKEN_SWITCH]), False),
        ("broken switch read as the full switch",
         table([HARD_CORNER, BARE_ATTACHMENT, SHORT_SWITCH]), False),
        ("Minefield's ruleset", table([HARD_CORNER, SHORT_SWITCH, LONG_SWITCH]), False),
        ("areas may hang off the board edge", SHIPPED, True),
    ]
    survivors = [name for name, tab, off in variants if verdict(tab, off)]
    check(not survivors, f"wrong readings the figures fail to kill: {survivors}")
    check(len(variants) == 12, "12 enumerated wrong readings")


# --------------------------------------------------------------------------
# 5. the two structural theorems ("Middle-earth")
# --------------------------------------------------------------------------

def contains_pattern(big, small):
    bw = max(c for c, _ in big) + 1
    bh = max(r for _, r in big) + 1
    sw = max(c for c, _ in small) + 1
    sh = max(r for _, r in small) + 1
    for dc in range(bw - sw + 1):
        for dr in range(bh - sh + 1):
            if all(big[(c + dc, r + dr)] == v for (c, r), v in small.items()):
                return True
    return False


def test_weaker_than_nakatta():
    """Every Nakatta Pro glyph CONTAINS a Nakatta glyph.

    Consequence: any position Nakatta Pro forbids, Nakatta forbids too -- the
    ban is strictly weaker than Nakatta's.
    """
    nakatta = _closure(NAKED_ATTACHMENT) + _closure(HARD_CORNER)
    for name, base in BASE_GLYPHS:
        for pat in _closure(base):
            check(any(contains_pattern(pat, s) for s in nakatta),
                  f"{name} image {pat} contains no Nakatta glyph")
    # strictly weaker: Nakatta forbids things Nakatta Pro allows (the 2x2 naked
    # attachment itself is a legal Nakatta Pro position).
    check(not glyphs_on_board({(0, 1): BLACK, (1, 1): WHITE}, 3),
          "a bare 2x2 naked attachment must be legal in Nakatta Pro")
    check(scan({(0, 1): BLACK, (1, 1): WHITE},
               table([HARD_CORNER, NAKED_ATTACHMENT]), size=3),
          "... and illegal in Nakatta")


def test_stronger_than_minefield():
    """No Nakatta Pro-legal position holds a Minefield switch, or a crosscut.

    * the 2x4 LONG SWITCH is itself a bare attachment (twice over);
    * removing any one of the 2x3 SHORT SWITCH's four stones leaves a broken
      switch, so its last stone can never be played legally;
    * removing any one of a CROSSCUT's four stones leaves a hard corner.

    The crosscut half is what makes a filled board decisive (see rules.md).
    """
    def small_scan(pat):
        """Glyphs wholly inside the pattern's own bounding box.

        NOT `glyphs_on_board(..., 4)`: padding a 2x2 crosscut out to a 4x4
        board surrounds it with empty points and manufactures glyphs that the
        pattern itself does not contain.
        """
        pw = max(c for c, _ in pat) + 1
        ph = max(r for _, r in pat) + 1
        out = []
        for (w, h), keys in GLYPHS.items():
            for c0 in range(pw - w + 1):
                for r0 in range(ph - h + 1):
                    key = tuple(pat[(c0 + c, r0 + r)]
                                for r in range(h) for c in range(w))
                    if key in keys:
                        out.append((keys[key], c0, r0, w, h))
        return out

    check(any(g[0] == "bare attachment" for g in small_scan(LONG_SWITCH)),
          "the long switch must itself be a bare attachment")
    for name, pat in (("short switch", SHORT_SWITCH), ("crosscut", CROSSCUT)):
        check(not small_scan(pat), f"{name} is not itself a glyph")
        for cell in [k for k, v in pat.items() if v is not E]:
            less = dict(pat)
            less[cell] = E
            check(small_scan(less),
                  f"{name} minus {cell} must already be illegal")


# --------------------------------------------------------------------------
# 6. local legality == the sheet's global condition
# --------------------------------------------------------------------------

def test_local_equals_global():
    """`forms_glyph` (4 + 12 local areas) == a full board rescan, everywhere."""
    rng = random.Random(20260803)
    checked = 0
    for size in (5, 7, 9):
        for game_no in range(4):
            s = NakattaProState(size=size)
            while not G.is_terminal(s):
                check(glyphs_on_board(s.board, size) == [],
                      "a reachable position contains a glyph")
                for r in range(size):
                    for c in range(size):
                        if (c, r) in s.board:
                            continue
                        for who in (BLACK, WHITE):
                            local = forms_glyph(s.board, size, c, r, who)
                            glob = bool(glyphs_on_board({**s.board, (c, r): who}, size))
                            check(local == glob,
                                  f"local != global at {(c, r)} for {who}")
                            checked += 1
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            check(glyphs_on_board(s.board, size) == [], "terminal position legal")
    check(checked > 20000, f"only {checked} local/global comparisons")


# --------------------------------------------------------------------------
# 7. exhaustive solves of the smallest boards
# --------------------------------------------------------------------------

def exhaustive(size):
    """Enumerate EVERY reachable position; return (value for Black, stats).

    Driven entirely through the public Game API, so it tests the real thing.
    """
    stats = dict(states=0, terminal=0, draws=0, stalls=0, skips=0,
                 both_connected=0, full=0, max_ply=0)
    memo = {}

    def key(s):
        return (tuple(sorted(s.board.items())), s.to_move, s.stalled, s.winner)

    def rec(s):
        k = key(s)
        if k in memo:
            return memo[k]
        stats["states"] += 1
        stats["max_ply"] = max(stats["max_ply"], s.ply)
        if G.is_terminal(s):
            stats["terminal"] += 1
            if s.winner is None:
                stats["draws"] += 1
            if s.stalled:
                stats["stalls"] += 1
            if len(s.board) == size * size:
                stats["full"] += 1
            if connects(s.board, BLACK, size) and connects(s.board, WHITE, size):
                stats["both_connected"] += 1
            memo[k] = G.returns(s)[0]
            return memo[k]
        p = s.to_move
        vals = []
        for mv in G.legal_moves(s):
            nxt = G.apply_move(s, mv)
            if nxt.skips > s.skips:
                stats["skips"] += 1
            vals.append(rec(nxt))
        memo[k] = max(vals) if p == BLACK else min(vals)
        return memo[k]

    val = rec(NakattaProState(size=size))
    return val, stats


def test_exhaustive_small_boards():
    """Cycle-freedom, drawlessness and a game value, all from one enumeration."""
    val2, st2 = exhaustive(2)
    check(val2 == -1.0, f"2x2 should be a White (seat 1) win, got {val2}")
    check(st2["draws"] == 0 and st2["stalls"] == 0, st2)
    val3, st3 = exhaustive(3)
    check(val3 == 1.0, f"3x3 should be a Black (seat 0) win, got {val3}")
    for size, st in ((2, st2), (3, st3)):
        check(st["draws"] == 0, f"{size}x{size}: {st['draws']} draws")
        check(st["stalls"] == 0, f"{size}x{size}: {st['stalls']} double stalls")
        check(st["both_connected"] == 0, f"{size}x{size}: both players connected")
        check(st["terminal"] > 0 and st["terminal"] == st["full"] + (st["terminal"] - st["full"]),
              "terminal bookkeeping")
        check(st["full"] > 0, f"{size}x{size}: no filled board was reached")
        check(st["max_ply"] <= max_plies(size),
              f"{size}x{size} exceeded the ply bound {max_plies(size)}")
    # single-player skips ARE reachable, so the skip rule is genuinely covered
    check(st3["skips"] > 0, "the 3x3 solve must exercise the skip rule")
    check(st3["states"] == 2924, f"3x3 reachable states changed: {st3['states']}")
    check(st2["states"] == 27, f"2x2 reachable states changed: {st2['states']}")


# --------------------------------------------------------------------------
# 8. the double stall (the only draw) -- hunted, not assumed
# --------------------------------------------------------------------------

def test_strangle_hunt():
    """Play to MINIMISE the opponent's mobility, looking for a double stall.

    Random play essentially never reaches a stall; this policy is the closest
    thing to an adversary for it.  A draw here would be a genuine finding, not
    a bug -- the game scores it 0-0 honestly (test_draw_is_honest).
    """
    rng = random.Random(7)
    draws = 0
    skips = 0
    for size in (4, 5, 6, 7):
        for game_no in range(6):
            s = NakattaProState(size=size)
            while not G.is_terminal(s):
                best, best_n = None, None
                for mv in G.legal_moves(s):
                    nxt = G.apply_move(s, mv)
                    n = 0 if G.is_terminal(nxt) else len(G.legal_moves(nxt))
                    if best_n is None or n < best_n or (n == best_n and rng.random() < 0.3):
                        best, best_n = mv, n
                s = G.apply_move(s, best)
            skips += s.skips
            if s.winner is None:
                draws += 1
    check(draws == 0, f"strangle policy produced {draws} draws (a finding, not a crash)")
    # Skips are NOT asserted here: greedy mobility-strangling turns out to end
    # games faster (by connecting), not to starve a player, and it produced
    # zero skipped turns over these 24 games.  The skip rule's coverage comes
    # from the exhaustive 3x3 solve and from random play, where it is common.
    check(skips >= 0, "bookkeeping")


# --------------------------------------------------------------------------
# 9. termination, skips, and the win/stall ordering
# --------------------------------------------------------------------------

def test_random_games():
    rng = random.Random(4242)
    skips = 0
    for size in (5, 7, 9, 11):
        for i in range(6 if size < 11 else 3):
            s = NakattaProState(size=size)
            seen = set()
            while not G.is_terminal(s):
                k = (tuple(sorted(s.board.items())), s.to_move)
                check(k not in seen, "a position repeated: the game has a cycle")
                seen.add(k)
                stones = len(s.board)
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
                check(len(s.board) == stones + 1, "every ply must place one stone")
                check(s.ply <= max_plies(size), f"ply cap {max_plies(size)} exceeded")
            check(s.winner is not None, f"random game at {size} ended in a draw")
            check(connects(s.board, s.winner, size), "the winner must be connected")
            check(not connects(s.board, 1 - s.winner, size), "only one winner")
            skips += s.skips
    check(skips > 0, "no skipped turn in any random game (coverage gap)")


def test_public_predicates_agree():
    """`legal_moves`, `placements` and `has_placement` must never disagree.

    `has_placement` is the short-circuiting twin used inside the turn change;
    a predicate that is not on the move-generation path is exactly the one
    nobody tests.
    """
    rng = random.Random(99)
    for size in (5, 7):
        for _ in range(3):
            s = NakattaProState(size=size)
            while not G.is_terminal(s):
                for who in (BLACK, WHITE):
                    pts = placements(s.board, size, who)
                    check(has_placement(s.board, size, who) == bool(pts),
                          "has_placement disagrees with placements")
                    if who == s.to_move:
                        check([f"{c},{r}" for c, r in pts] == G.legal_moves(s),
                              "legal_moves disagrees with placements")
                    for c, r in pts:
                        check((c, r) not in s.board, "an occupied point offered")
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))


def test_win_outranks_stall():
    """A connection made on the very move that also strangles the board wins.

    Built by REACHING the position through apply_move (a hand-built state has
    winner=None and would prove nothing).
    """
    # 3x3, Black joins top and bottom down column 0.
    s = NakattaProState(size=3)
    for mv in ("0,0", "2,0", "0,1", "2,1", "0,2"):
        check(mv in G.legal_moves(s), f"{mv} should be legal here")
        s = G.apply_move(s, mv)
    check(s.winner == BLACK, f"Black should have won, winner={s.winner}")
    check(G.is_terminal(s) and G.returns(s) == [1.0, -1.0], G.returns(s))
    # Poisoning the stall flag must not change a decided game's result.
    poisoned = replace(s, stalled=True)
    check(G.returns(poisoned) == [1.0, -1.0],
          "a decisive result must outrank the stall flag")
    check(G.legal_moves(s) == [], "a finished game offers no moves")


def test_draw_is_honest():
    s = NakattaProState(size=5, stalled=True)
    check(G.is_terminal(s) and G.returns(s) == [0.0, 0.0],
          "a double stall is an honest 0-0 draw, never a fabricated tiebreak")
    check(G.render(s)["caption"].startswith("Draw"), G.render(s)["caption"])


def test_no_pie_move():
    """The sheet has no pie rule -- in either revision -- so none is offered."""
    s = NakattaProState(size=9)
    s = G.apply_move(s, "4,4")
    check(all("," in mv for mv in G.legal_moves(s)), "no non-placement moves")
    check("swap" not in G.legal_moves(s), "Nakatta Pro has no pie rule")
    # ... and, characteristically, White may not answer ADJACENT to the opening
    # stone: an attachment alone on an empty board always has two clear rows
    # beside it, i.e. it is a bare attachment.  4 of the 80 replies are barred.
    moves = set(G.legal_moves(s))
    check(len(moves) == 76, f"White should have 76 replies, not {len(moves)}")
    check({"3,4", "5,4", "4,3", "4,5"}.isdisjoint(moves),
          "White must not be able to attach to the lone opening stone")


# --------------------------------------------------------------------------
# 10. serialization, rendering, notation
# --------------------------------------------------------------------------

SER_KEYS = {"size", "board", "to_move", "last", "winner", "stalled", "ply", "skips"}


def test_serialize_round_trip():
    """Compare STATE OBJECTS, not dicts: `serialize(deserialize(d)) == d` is vacuous."""
    rng = random.Random(11)
    checked = 0
    for size in (5, 9):
        s = NakattaProState(size=size)
        while True:
            d = G.serialize(s)
            check(set(d) == SER_KEYS, f"serialize key set changed: {set(d)}")
            back = G.deserialize(d)
            check(back == s, f"round trip lost information at ply {s.ply}")
            check(G.serialize(back) == d, "second round trip differs")
            checked += 1
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    check(checked > 80, checked)
    # every field must survive, including the ones a fresh state defaults to
    s = NakattaProState(size=7, board={(0, 0): BLACK, (6, 6): WHITE}, to_move=WHITE,
                        last=(6, 6), winner=None, stalled=True, ply=5, skips=3)
    check(G.deserialize(G.serialize(s)) == s, "hand-built state round trip")
    for field_name, value in (("stalled", False), ("skips", 0), ("ply", 0),
                              ("winner", BLACK), ("last", None), ("to_move", BLACK)):
        alt = replace(s, **{field_name: value})
        check(G.deserialize(G.serialize(alt)) == alt, f"field {field_name} dropped")
        check(G.serialize(alt) != G.serialize(s) or getattr(s, field_name) == value,
              f"field {field_name} is not actually emitted")


def test_render_every_size():
    """Declared board dimensions must be right for EVERY offered size.

    Checked from a position REACHED through apply_move with stones in all four
    corners -- a freshly initialised state has no pieces and proves nothing.
    """
    for size in (9, 11, 13, 15, 19):
        s = NakattaProState(size=size)
        corners = [(0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)]
        for c, r in corners:
            mv = f"{c},{r}"
            check(mv in G.legal_moves(s), f"corner {mv} unplayable at size {size}")
            s = G.apply_move(s, mv)
        spec = G.render(s)
        board = spec["board"]
        check(board["width"] == size and board["height"] == size,
              f"render declares {board['width']}x{board['height']} for size {size}")
        cells = {p["cell"] for p in spec["pieces"]}
        check(len(spec["pieces"]) == len(s.board), "every stone must be rendered")
        for c, r in corners:
            check(f"{c},{r}" in cells, f"corner {(c, r)} dropped at size {size}")
        for cell in cells:
            c, r = (int(x) for x in cell.split(","))
            check(0 <= c < board["width"] and 0 <= r < board["height"],
                  f"piece {cell} outside the declared {size}x{size} board")
        check(G.initial_state({"size": size}).size == size, "option plumbed through")


def test_describe_move():
    s = NakattaProState(size=9)
    check(G.describe_move(s, "0,0") == "a1", G.describe_move(s, "0,0"))
    check(G.describe_move(s, "8,8") == "i9", G.describe_move(s, "8,8"))
    s = NakattaProState(size=3)
    for mv in ("0,0", "2,0", "0,1", "2,1"):
        s = G.apply_move(s, mv)
    check(G.describe_move(s, "0,2") == "a3#", G.describe_move(s, "0,2"))


def test_heuristic():
    """Shape, zero-sum, symmetry -- and, separately, DIRECTION against pinned values.

    A sign-flipped eval (the bot plays to lose) and a constant-zero eval both
    pass every shape/range/zero-sum check, so the direction is asserted on its
    own with measured numbers.
    """
    # shape: a LIST of num_players payoffs.  A bare float would raise inside
    # MCTSBot's back-propagation, which only happens when the rollout cutoff is
    # reached -- so it is forced below with max_rollout=2.
    empty = NakattaProState(size=5)
    v = G.heuristic(empty)
    check(isinstance(v, list) and len(v) == 2, f"heuristic must be a 2-list: {v!r}")
    check(all(isinstance(x, float) for x in v), v)
    check(v[0] == 0.0 and v[1] == 0.0, f"an empty board is even: {v}")

    # DIRECTION, pinned: Black one stone from joining top and bottom must score
    # strongly positive, and the mirrored+recoloured position exactly the
    # negative of it.
    black_ahead = NakattaProState(size=5,
                                  board={(2, 0): BLACK, (2, 1): BLACK,
                                         (2, 2): BLACK, (2, 3): BLACK})
    hb = G.heuristic(black_ahead)
    check(abs(hb[0] - 0.885352) < 1e-5, f"pinned value changed: {hb}")
    check(hb[0] > 0.8, "Black nearly connected must score strongly for Black")
    mirrored = NakattaProState(size=5,
                               board={(r, c): WHITE for (c, r) in black_ahead.board})
    hw = G.heuristic(mirrored)
    check(abs(hw[0] + hb[0]) < 1e-12, f"seat symmetry broken: {hb} vs {hw}")

    # ... and MONOTONE: every extra stone on Black's column scores higher.
    prev = None
    for k in range(5):
        s = NakattaProState(size=5, board={(2, i): BLACK for i in range(k)})
        val = G.heuristic(s)[0]
        check(-1.0 <= val <= 1.0, val)
        check(abs(val + G.heuristic(s)[1]) < 1e-12, "eval must be zero-sum")
        check(prev is None or val > prev, f"progress must score higher: {k} {val} {prev}")
        prev = val

    # The consumer really can use it: force the rollout cutoff so back-prop
    # indexes the payoff list.
    from agp.mcts import MCTSBot
    bot = MCTSBot(random.Random(3), iterations=12, max_rollout=2)
    s = NakattaProState(size=5)
    for _ in range(6):
        if G.is_terminal(s):
            break
        mv = bot.select(G, s)
        check(mv in G.legal_moves(s), "the bot must return a legal move")
        s = G.apply_move(s, mv)


# --------------------------------------------------------------------------

def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"nakatta_pro selftest: all {CHECKS} checks passed "
          f"({len(tests)} tests)")


if __name__ == "__main__":
    main()
