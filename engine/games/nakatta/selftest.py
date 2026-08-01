#!/usr/bin/env python3
"""Correctness anchors for Nakatta (Luis Bolanos Mures & Mark Steere, 2024).

Pure stdlib.  The strongest anchors are the official rule sheet's own three
figures, transcribed from the VECTOR artwork of Nakatta_rules.pdf (every disc
and red dot parsed out of `pdftocairo -svg` output, not read off pixels):

  * FIGURE 1 "Black wins" — a 9x9 position with 25 stones.  Its load-bearing
    PREMISE is that it is a LEGAL, actually-played position, so it must contain
    ZERO hard corners and ZERO naked attachments.  It also pins the
    colour<->edge convention to ground truth OUTSIDE the engine: the DARK discs
    (= seat 0) are the ones forming the chain that spans the TOP and BOTTOM
    edges, and the printed caption calls that player "Black".
  * FIGURE 2 "6 hard corners" — a 9x9 position stated to hold exactly six.
    Its 5 red dots are exactly the union of those six patterns' empty points
    (asserted: a mis-transcription breaks that before it breaks the count).
    NOTE the figure is deliberately ILLEGAL — it also holds 11 naked
    attachments, which it does not claim to illustrate.
  * FIGURE 3 "7 naked attachments" — a 9x9 position stated to hold exactly
    seven, with 12 red dots that are exactly the union of their empty points.

DISCRIMINATING POWER (measured, not assumed — see the "wrong readings" section):
Figure 2's count of 6 kills only 5 of the 7 wrong hard-corner readings tried;
the two survivors are killed by FIGURE 1's legality premise instead.  Figure 3's
count of 7 kills only 4 of the 5 wrong naked-attachment readings, and Figure 1
does NOT close that gap — the survivor ("empties in any arrangement, diagonal
included") is killed here by a CONSTRUCTED position, justified by the sheet's
explicit word "orthogonally".

Plus: the local-vs-global legality equivalence, the crosscut-impossibility step
of the drawlessness argument, a complete enumeration of every reachable 3x3
position (which reaches the skip clause but never a stall), the skip clause
driven to fire at 5x5 through apply_move, the pie swap (which the AbstractPlay oracle cannot cover at all — it
implements pie as a site-level flag outside the game class), serialization
compared as STATE OBJECTS, render bounds at every offered board size, and the
exact ply bound.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json                                                     # noqa: E402
import random                                                   # noqa: E402
from games.nakatta.game import (                                # noqa: E402
    BLACK, WHITE, Nakatta, NakattaState, max_plies,
    _hard_corner_at, _naked_attachment_at, connects, forms_pattern,
    has_placement, patterns_on_board, placements, _QUAD,
)

G = Nakatta()
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)
    return cond


# ==========================================================================
# the three figures, transcribed from the vector artwork
# ==========================================================================
# Rows are given TOP-first exactly as the sheet prints them; `parse` flips them
# so that r = 0 is the bottom row (this package's, and the renderer's,
# convention).  'B' = a dark disc, 'W' = a white disc, 'r' = a RED DOT (an
# unoccupied point the figure marks), '.' = an unmarked unoccupied point.
FIG1 = [".....B...",          # "Black wins"
        ".....B...",
        "...BBB...",
        "...BB....",
        "WWWB..WWW",
        "..WBWWW..",
        "...B.....",
        "...BB.WW.",
        "....B...."]
FIG2 = [".........",          # "6 hard corners"
        "......Wr.",
        ".WB...BW.",
        ".Br......",
        ".........",
        ".........",
        ".rWB..BWB",
        "BWBr..WrW",
        "........."]
FIG3 = [".BW......",          # "7 naked attachments"
        ".rr......",
        ".....rBr.",
        ".....rWr.",
        ".........",
        ".rrr.....",
        ".WBW.....",
        ".rrr.....",
        "........."]
N9 = 9


def parse(rows):
    """(board dict, set of red-dotted empty points).  Row 0 of `rows` is the
    TOP row of the printed figure; the returned coordinates use r = 0 = bottom."""
    board, dots = {}, set()
    h = len(rows)
    for i, row in enumerate(rows):
        r = h - 1 - i
        for c, ch in enumerate(row):
            if ch == "B":
                board[(c, r)] = BLACK
            elif ch == "W":
                board[(c, r)] = WHITE
            elif ch == "r":
                dots.add((c, r))
    return board, dots


F1, F1DOTS = parse(FIG1)
F2, F2DOTS = parse(FIG2)
F3, F3DOTS = parse(FIG3)

check(all(len(row) == N9 for row in FIG1 + FIG2 + FIG3) and
      len(FIG1) == len(FIG2) == len(FIG3) == N9,
      "all three figures are transcribed as 9x9 boards")
for name, bd, dots in (("1", F1, F1DOTS), ("2", F2, F2DOTS), ("3", F3, F3DOTS)):
    check(not (set(bd) & dots), f"Figure {name}: no red dot sits on a stone")

# --------------------------------------------------------------------------
# FIGURE 1 — the legality PREMISE, and the colour<->edge pin
# --------------------------------------------------------------------------
check(len(F1) == 25, f"Figure 1 holds 25 stones, got {len(F1)}")
check(F1DOTS == set(), "Figure 1 prints no red dots")
# the premise the whole figure relies on: it is a position reached by legal
# play, so the two illegal patterns must BOTH be absent.
check(patterns_on_board(F1, N9) == [],
      f"Figure 1 is a LEGAL position: no hard corner, no naked attachment "
      f"(found {patterns_on_board(F1, N9)})")
# ground truth OUTSIDE the engine: the DARK discs are the ones spanning the top
# and bottom edges, and the sheet captions that player "Black".
check(connects(F1, BLACK, N9), "Figure 1: the DARK stones span the top and bottom edges")
check(not connects(F1, WHITE, N9), "Figure 1: the WHITE stones do NOT span left to right")
# the same fact recomputed without using `connects` at all (an independent BFS),
# so the pin does not lean on the predicate it is meant to validate.


def spans(board, owner, size, vertical):
    starts = [(c, 0) for c in range(size)] if vertical else [(0, r) for r in range(size)]
    stack = [p for p in starts if board.get(p) == owner]
    seen = set(stack)
    while stack:
        c, r = stack.pop()
        if (r == size - 1) if vertical else (c == size - 1):
            return True
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = (c + dc, r + dr)
            if p not in seen and board.get(p) == owner:
                seen.add(p)
                stack.append(p)
    return False


check(spans(F1, BLACK, N9, vertical=True) and not spans(F1, BLACK, N9, vertical=False),
      "Figure 1 (independent BFS): the dark chain spans ROWS, not columns")
ROW_JOINER = BLACK if spans(F1, BLACK, N9, vertical=True) else WHITE
check(ROW_JOINER == BLACK, "seat 0 is the row-joiner, i.e. the sheet's Black")
# and the printed caption for that player is "Black wins"
cap = G.render(NakattaState(size=N9, board=dict(F1), winner=ROW_JOINER))["caption"]
check(cap == "Black wins", f"the row-joiner is captioned 'Black wins', got {cap!r}")
cap = G.render(NakattaState(size=N9, board=dict(F1), winner=1 - ROW_JOINER))["caption"]
check(cap == "White wins", f"the column-joiner is captioned 'White wins', got {cap!r}")

# --------------------------------------------------------------------------
# FIGURE 2 — exactly six hard corners; the red dots are their empty points
# --------------------------------------------------------------------------
hc2 = [(c, r) for (k, c, r) in patterns_on_board(F2, N9) if k == "hard"]
check(len(hc2) == 6, f"Figure 2 shows exactly 6 hard corners, got {len(hc2)}")
holes = set()
for (c, r) in hc2:
    for dc, dr in _QUAD:
        if (c + dc, r + dr) not in F2:
            holes.add((c + dc, r + dr))
check(holes == F2DOTS,
      f"Figure 2's 5 red dots are exactly the six hard corners' empty points "
      f"({sorted(holes)} vs {sorted(F2DOTS)})")
check(len(F2DOTS) == 5, f"Figure 2 prints 5 red dots, got {len(F2DOTS)}")
# the figure is an ILLUSTRATION, not a legal position: it also holds naked
# attachments it never claims.  Asserting this stops a future reader from
# "fixing" the transcription to make the position legal.
na2 = [(c, r) for (k, c, r) in patterns_on_board(F2, N9) if k == "naked"]
check(len(na2) == 11, f"Figure 2 is not a legal position (11 naked attachments), got {len(na2)}")

# --------------------------------------------------------------------------
# FIGURE 3 — exactly seven naked attachments; the red dots are their empties
# --------------------------------------------------------------------------
na3 = [(c, r) for (k, c, r) in patterns_on_board(F3, N9) if k == "naked"]
hc3 = [(c, r) for (k, c, r) in patterns_on_board(F3, N9) if k == "hard"]
check(len(na3) == 7, f"Figure 3 shows exactly 7 naked attachments, got {len(na3)}")
check(len(hc3) == 0, f"Figure 3 shows no hard corners, got {len(hc3)}")
holes = set()
for (c, r) in na3:
    for dc, dr in _QUAD:
        if (c + dc, r + dr) not in F3:
            holes.add((c + dc, r + dr))
check(holes == F3DOTS,
      f"Figure 3's 12 red dots are exactly the seven attachments' empty points "
      f"({sorted(holes)} vs {sorted(F3DOTS)})")
check(len(F3DOTS) == 12, f"Figure 3 prints 12 red dots, got {len(F3DOTS)}")

# ==========================================================================
# how much do those counts actually DISCRIMINATE?  (measured, then the gap
# is closed deliberately)
# ==========================================================================
def scan(board, size, pred):
    return sum(1 for c in range(size - 1) for r in range(size - 1)
               if pred([board.get((c + dc, r + dr)) for dc, dr in _QUAD]))


def true_hc(v):
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 1:
        return False
    h = h[0]
    p = [v[i] for i in range(4) if i not in (h, 3 - h)]
    return p[0] == p[1] and p[0] != v[3 - h]


def true_na(v):
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 2 or h[0] + h[1] == 3:
        return False
    st = [v[i] for i in range(4) if i not in h]
    return st[0] != st[1]


# the shipped predicates must agree with these literal readings of the prose
for bd in (F1, F2, F3):
    for c in range(N9 - 1):
        for r in range(N9 - 1):
            v = [bd.get((c + dc, r + dr)) for dc, dr in _QUAD]
            check(_hard_corner_at(bd, c, r) == true_hc(v),
                  f"_hard_corner_at agrees with the prose at {(c, r)}")
            check(_naked_attachment_at(bd, c, r) == true_na(v),
                  f"_naked_attachment_at agrees with the prose at {(c, r)}")

WRONG_HC = {}
def _hc_orthopair(v):        # the like pair ORTHOGONALLY adjacent, not diagonally
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 1:
        return False
    h = h[0]; opp = {0: 1, 1: 0, 2: 3, 3: 2}[h]
    p = [v[i] for i in range(4) if i not in (h, opp)]
    return p[0] == p[1] and p[0] != v[opp]
def _hc_nocolour(v):         # drop the "one stone of the opposite color" clause
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 1:
        return False
    p = [v[i] for i in range(4) if i not in (h[0], 3 - h[0])]
    return p[0] == p[1]
def _hc_allsame(v):          # read it as all three stones sharing a colour
    h = [i for i in range(4) if v[i] is None]
    st = [x for x in v if x is not None]
    return len(h) == 1 and st[0] == st[1] == st[2]
def _hc_anythree(v):         # any three stones with both colours present
    st = [x for x in v if x is not None]
    return len(st) == 3 and len(set(st)) == 2
def _hc_twostone(v):         # two diagonally adjacent like stones + two empties
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 2 or h[0] + h[1] != 3:
        return False
    st = [v[i] for i in range(4) if i not in h]
    return st[0] == st[1]
def _hc_full(v):             # a crosscut (no empty point at all)
    return None not in v and v[0] == v[3] and v[1] == v[2] and v[0] != v[1]
def _hc_loneorth(v):         # the lone stone ORTHOGONAL to the empty point
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 1:
        return False
    h = h[0]
    for opp in [i for i in range(4) if i not in (h, 3 - h)]:
        rest = [v[i] for i in range(4) if i not in (h, opp)]
        if rest[0] == rest[1] and rest[0] != v[opp]:
            return True
    return False
WRONG_HC = {"orthogonal like-pair": _hc_orthopair, "no opposite-colour clause": _hc_nocolour,
            "all three stones alike": _hc_allsame, "any 3 stones, both colours": _hc_anythree,
            "2 like stones + 2 empties": _hc_twostone, "crosscut (full 2x2)": _hc_full,
            "lone stone orthogonal to the hole": _hc_loneorth}

def _na_diagempty(v):        # empties DIAGONAL instead of orthogonal
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 2 or h[0] + h[1] != 3:
        return False
    st = [v[i] for i in range(4) if i not in h]
    return st[0] != st[1]
def _na_anyempty(v):         # empties in ANY arrangement
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 2:
        return False
    st = [v[i] for i in range(4) if i not in h]
    return st[0] != st[1]
def _na_samecolour(v):       # two stones of the SAME colour
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 2 or h[0] + h[1] == 3:
        return False
    st = [v[i] for i in range(4) if i not in h]
    return st[0] == st[1]
def _na_oneempty(v):
    h = [i for i in range(4) if v[i] is None]
    if len(h) != 1:
        return False
    st = [v[i] for i in range(4) if i not in h]
    return len(set(st)) == 2
def _na_threeempty(v):
    return sum(1 for x in v if x is None) == 3
WRONG_NA = {"empties diagonal": _na_diagempty, "empties in any arrangement": _na_anyempty,
            "two SAME-colour stones": _na_samecolour, "one empty point": _na_oneempty,
            "three empty points": _na_threeempty}

killed_by_fig2 = {n for n, f in WRONG_HC.items() if scan(F2, N9, f) != 6}
killed_by_fig1 = {n for n, f in WRONG_HC.items() if scan(F1, N9, f) != 0}
check(len(killed_by_fig2) == 5,
      f"Figure 2's '6' kills 5 of the {len(WRONG_HC)} wrong hard-corner readings, "
      f"got {len(killed_by_fig2)}: {sorted(killed_by_fig2)}")
check(set(WRONG_HC) - killed_by_fig2 == {"no opposite-colour clause", "any 3 stones, both colours"},
      "the two readings Figure 2 cannot see are the ones named in the docstring")
check(set(WRONG_HC) <= killed_by_fig2 | killed_by_fig1,
      "Figure 1's legality PREMISE closes Figure 2's blind spot: together they "
      "kill every wrong hard-corner reading tried")

killed_by_fig3 = {n for n, f in WRONG_NA.items() if scan(F3, N9, f) != 7}
na_fig1 = {n for n, f in WRONG_NA.items() if scan(F1, N9, f) != 0}
check(len(killed_by_fig3) == 4,
      f"Figure 3's '7' kills 4 of the {len(WRONG_NA)} wrong naked-attachment readings, "
      f"got {len(killed_by_fig3)}: {sorted(killed_by_fig3)}")
check(set(WRONG_NA) - killed_by_fig3 == {"empties in any arrangement"},
      "the one reading Figure 3 cannot see is 'empties in any arrangement'")
# A THIRD mistake shape, orthogonal to the glyph readings above: treating
# points OFF the board as empty, so 2x2 areas hanging over the edge count.
# Measured: Figure 2 is completely blind to it (still 6 hard corners) and so is
# Figure 1 (still zero) -- only FIGURE 3 kills it (8 naked attachments, not 7).
def scan_over_edge(board, size, pred):
    return sum(1 for c in range(-1, size) for r in range(-1, size)
               if pred([board.get((c + dc, r + dr)) for dc, dr in _QUAD]))
check(scan_over_edge(F2, N9, true_hc) == 6,
      "over-the-edge scanning is INVISIBLE to Figure 2's hard-corner count")
check(scan_over_edge(F1, N9, true_hc) == 0 and scan_over_edge(F1, N9, true_na) == 0,
      "...and invisible to Figure 1 as well")
check(scan_over_edge(F3, N9, true_na) == 8,
      "...but Figure 3 kills it: 8 naked attachments instead of the printed 7")
check(sum(1 for (k, c, r) in patterns_on_board(F3, N9) if k == "naked") == 7,
      "the shipped scan only considers 2x2 areas wholly on the board")
# ...and areas that merely TOUCH an edge do count -- exactly one in each figure
# (a claim rules.md makes, so it is pinned here rather than left to prose).
edge2 = [(c, r) for (k, c, r) in patterns_on_board(F2, N9)
         if k == "hard" and (c in (0, N9 - 2) or r in (0, N9 - 2))]
edge3 = [(c, r) for (k, c, r) in patterns_on_board(F3, N9)
         if k == "naked" and (c in (0, N9 - 2) or r in (0, N9 - 2))]
check(len(edge2) == 1 and len(edge3) == 1,
      f"exactly one border-touching pattern in each figure, got {edge2} / {edge3}")

check("empties in any arrangement" not in na_fig1,
      "Figure 1 does NOT close that gap either — it must be closed by construction")
# closing it deliberately, on the sheet's explicit word "ORTHOGONALLY adjacent":
# a 2x2 whose two empties are DIAGONAL and whose two stones differ in colour is
# NOT a naked attachment, and the placement that leaves it is legal.
diag = {(0, 1): BLACK, (1, 0): WHITE}                # empties at (0,0) and (1,1)
check(not _naked_attachment_at(diag, 0, 0),
      "two DIAGONAL empties + one black + one white is NOT a naked attachment")
check(_na_anyempty([diag.get((dc, dr)) for dc, dr in _QUAD]),
      "...and the rejected 'any arrangement' reading really would flag it "
      "(so this test is not vacuous)")
base = {(1, 0): WHITE}
check("0,1" in G.legal_moves(NakattaState(size=4, board=dict(base), to_move=BLACK)),
      "Black may legally place diagonally-empty-opposite a white stone")

# ==========================================================================
# legality: the LOCAL test used by legal_moves == the GLOBAL condition the
# sheet states ("after your placement there must be no ... on the board")
# ==========================================================================
rng = random.Random(20240424)
positions = 0
for gi in range(12):
    size = 7
    s = G.initial_state({"size": size})
    while not G.is_terminal(s):
        check(patterns_on_board(s.board, size) == [],
              "no legal position ever contains a hard corner or naked attachment")
        # no crosscut either — the step the drawlessness argument leans on
        for c in range(size - 1):
            for r in range(size - 1):
                v = [s.board.get((c + dc, r + dr)) for dc, dr in _QUAD]
                check(not (None not in v and v[0] == v[3] and v[1] == v[2] and v[0] != v[1]),
                      f"no reachable position contains a crosscut (at {(c, r)})")
        legal = {m for m in G.legal_moves(s) if m != "swap"}
        me = G.current_player(s)
        for c in range(size):
            for r in range(size):
                if (c, r) in s.board:
                    continue
                after = dict(s.board)
                after[(c, r)] = me
                globally_ok = patterns_on_board(after, size) == []
                check(globally_ok == (f"{c},{r}" in legal),
                      f"local legality == global scan at {(c, r)} for seat {me}")
                positions += 1
        check(len(legal) > 0, "legal_moves is non-empty on every non-terminal state")
        # `has_placement` is a SEPARATE short-circuiting copy of `placements`
        # and it is what drives the skip rule, so the two must never drift.
        for who in (BLACK, WHITE):
            check(has_placement(s.board, size, who) == bool(placements(s.board, size, who)),
                  f"has_placement agrees with placements for seat {who}")
        check({f"{c},{r}" for (c, r) in placements(s.board, size, me)} == legal,
              "legal_moves is exactly placements() for the side to move")
        s = G.apply_move(s, rng.choice(sorted(legal)))
check(positions > 2000, f"the local==global equivalence was checked on {positions} placements")

# the crosscut-impossibility step, proved directly rather than sampled: a
# crosscut can only appear when its FOURTH stone is placed, and every 3-stone
# precursor of a crosscut is a hard corner -- a position no legal game can be
# in.  (The completing placement itself forms no pattern, because a full 2x2 has
# no empty point; what is impossible is ever standing in front of it.)
for a in (BLACK, WHITE):
    b = 1 - a
    cross = {(0, 0): a, (1, 1): a, (1, 0): b, (0, 1): b}
    for drop in list(cross):
        pre = {k: v for k, v in cross.items() if k != drop}
        check(_hard_corner_at(pre, 0, 0),
              f"a crosscut minus {drop} is a hard corner, so it is unreachable")
        # and the placement that would CREATE that hard corner is itself illegal
        for third in list(pre):
            two = {k: v for k, v in pre.items() if k != third}
            check(forms_pattern(two, 4, third[0], third[1], pre[third]),
                  f"creating the crosscut precursor by playing {third} is illegal")
# and the checkerboard (the classic winner-less full board) is unreachable for
# exactly that reason: checkerboard-minus-one-point is a hard corner.
cb = {(c, r): (c + r) % 2 for c in range(4) for r in range(4)}
del cb[(1, 1)]
check(any(_hard_corner_at(cb, c, r) for c in range(3) for r in range(3)),
      "a checkerboard missing one point contains a hard corner (so it is unreachable)")

# ==========================================================================
# every reachable 3x3 position: no draw, no stall, exactly one winner
# ==========================================================================
seen = {}
stats = {"terminals": 0, "draws": 0, "stalls": 0, "skips": 0, "both": 0, "maxply": 0}


def walk(s):
    key = (tuple(sorted(s.board.items())), s.to_move, s.ply, s.swapped)
    if key in seen:
        return
    seen[key] = True
    stats["maxply"] = max(stats["maxply"], s.ply)
    if connects(s.board, BLACK, 3) and connects(s.board, WHITE, 3):
        stats["both"] += 1
    if G.is_terminal(s):
        stats["terminals"] += 1
        if s.winner is None:
            stats["draws"] += 1
        if s.stalled:
            stats["stalls"] += 1
        return
    check(bool(G.legal_moves(s)), "3x3: every non-terminal state has a legal move")
    for m in G.legal_moves(s):
        nxt = G.apply_move(s, m)
        if nxt.skips > s.skips:
            stats["skips"] += 1
        check(nxt.ply == len(nxt.board) + (1 if nxt.swapped else 0),
              "ply == stones placed + the at-most-one swap ply")
        walk(nxt)


walk(G.initial_state({"size": 3}))
check(stats["draws"] == 0, f"3x3 exhaustive: no reachable draw, got {stats['draws']}")
check(stats["stalls"] == 0, f"3x3 exhaustive: no reachable stall, got {stats['stalls']}")
check(stats["both"] == 0, "3x3 exhaustive: the two players are never both connected")
check(stats["terminals"] > 500, f"3x3 exhaustive reached {stats['terminals']} terminals")
check(stats["maxply"] <= max_plies(3), "3x3 exhaustive: the ply bound holds")
# the skip clause IS reachable on 3x3 (measured, not assumed) -- but a STALL
# (both players stuck) is not, so 3x3 gives the draw branch zero coverage.  It
# is driven at 5x5 below and reasoned about in rules.md.
check(stats["skips"] > 0,
      f"3x3 does exercise the skip clause ({stats['skips']} skipped turns)")

# ==========================================================================
# the skip clause, driven to fire at 5x5 through apply_move
# ==========================================================================
skip_state = None
full_win = None
rng = random.Random(5150)
for gi in range(240):
    s = G.initial_state({"size": 5})
    while not G.is_terminal(s):
        before = s
        s = G.apply_move(s, rng.choice([m for m in G.legal_moves(s) if m != "swap"]))
        if s.skips > before.skips and skip_state is None and not G.is_terminal(s):
            skip_state = (before, s)
        check(not (s.winner is not None and s.stalled),
              "a decisive result and the stall flag are never both set")
        check(not (connects(s.board, BLACK, 5) and connects(s.board, WHITE, 5)),
              "the two players are never both connected (5x5 random play)")
        check(s.ply == len(s.board) + (1 if s.swapped else 0), "ply accounting holds")
    check(s.ply <= max_plies(5), "the ply bound holds in random play")
    check(G.returns(s) in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]), "returns is well formed")
    check(s.winner is not None, "5x5 random play never produced a draw")
    if s.winner is not None and len(s.board) == 25 and full_win is None:
        full_win = s
check(skip_state is not None, "a real forced skip was reached at 5x5 through apply_move")
if skip_state:
    before, after = skip_state
    mover = before.to_move
    check(after.to_move == mover,
          "after the opponent is skipped the same player moves again")
    check(not has_placement(after.board, 5, 1 - mover),
          "the skipped player really had no legal placement")
    check(has_placement(after.board, 5, mover), "the player given the turn back does have one")
    check(after.skips == before.skips + 1, "the skip counter advanced by one")
    prev_mv = f"{after.last[0]},{after.last[1]}"
    check(G.describe_move(before, prev_mv).endswith("(opponent skipped)"),
          f"describe_move flags the skip, got {G.describe_move(before, prev_mv)!r}")
# a decisive result must outrank the stall test: winning with the LAST stone
# leaves nobody able to place, and must still be scored as a win.
check(full_win is not None, "a game was won with the final stone of a full board")
if full_win:
    check(full_win.winner is not None and not full_win.stalled,
          "winning on a full board is a WIN, not a stall/draw")
    check(G.returns(full_win) != [0.0, 0.0], "...and it scores decisively")
    check(spans(full_win.board, full_win.winner, 5, vertical=(full_win.winner == ROW_JOINER)),
          "the declared winner really spans their own two edges")

# ==========================================================================
# the pie rule  (the oracle's structural blind spot: AbstractPlay implements
# pie as a site-level flag OUTSIDE the game class, so it gets zero differential
# coverage; everything here is a constructed input)
# ==========================================================================
MAN_SIZES = json.loads((Path(__file__).resolve().parent / "manifest.json").read_text())["options"]["size"]["choices"]
s0 = G.initial_state({"size": 5})
check("swap" not in G.legal_moves(s0), "swap is not offered before Black has played")
s1 = G.apply_move(s0, "1,3")                        # deliberately asymmetric point
check("swap" in G.legal_moves(s1), "swap is offered on White's first turn")
s2 = G.apply_move(s1, "swap")
check(s2.board == {(3, 1): WHITE},
      f"the swap transposes the stone and recolours it, got {s2.board}")
check(s2.to_move == BLACK and s2.swapped, "after the swap seat 0 is on move")
check("swap" not in G.legal_moves(s2), "swap cannot be played twice")
s3 = G.apply_move(s2, "0,0")
check("swap" not in G.legal_moves(s3), "swap is not offered on move 3")
check("swap" not in G.legal_moves(G.apply_move(s1, "0,0")),
      "declining the pie on move 2 removes the option")
# the swap is value-preserving because Nakatta is symmetric under
# (transpose + colour reversal): White's options before the swap, transposed,
# are exactly Black's options after it.
before_opts = {tuple(int(x) for x in m.split(","))
               for m in G.legal_moves(s1) if m != "swap"}
after_opts = {tuple(int(x) for x in m.split(",")) for m in G.legal_moves(s2)}
check({(r, c) for (c, r) in before_opts} == after_opts,
      "the swap maps White's move set onto Black's by transposition")
check(G.describe_move(s1, "swap") == "swap (pie)", "describe_move labels the swap")
# `legal_moves` offers the swap on the strength of (ply == 1, one stone on the
# board).  That can only ever be WHITE's turn -- a one-stone position can never
# leave White with no placement -- so the offer can never reach the wrong seat.
# Proved here on every offered board size rather than guarded defensively.
for size in MAN_SIZES:
    probe = G.apply_move(G.initial_state({"size": size}), "0,0")
    check(probe.to_move == WHITE and probe.ply == 1 and probe.skips == 0,
          f"after Black's opening on {size}x{size} it is always White's turn")
    check("swap" in G.legal_moves(probe), f"...and the pie is offered ({size}x{size})")
    mid = size // 2
    probe = G.apply_move(G.initial_state({"size": size}), f"{mid},{mid}")
    check(probe.to_move == WHITE and "swap" in G.legal_moves(probe),
          f"...from a central opening too ({size}x{size})")
check("swap (pie rule)" in G.render(s1)["caption"], "the swap is offered in the caption")
check("swap" not in G.render(s2)["caption"], "...and not after it has been used")

# after a swap the caption and the winner must still name the right colour --
# pinned to Figure 1's ground truth (seat ROW_JOINER = "Black" = rows), never to
# the engine's own naming.
found = {}
rng = random.Random(770)
for gi in range(400):
    s = G.apply_move(G.apply_move(G.initial_state({"size": 5}), "1,3"), "swap")
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice([m for m in G.legal_moves(s) if m != "swap"]))
    if s.winner is not None and s.winner not in found:
        found[s.winner] = s
    if len(found) == 2:
        break
check(len(found) == 2, f"both seats were seen winning a post-swap game, got {sorted(found)}")
for seat, s in found.items():
    check(s.swapped, "the post-swap flag survived to the end of the game")
    vertical = (seat == ROW_JOINER)
    check(spans(s.board, seat, 5, vertical=vertical),
          f"post-swap winner seat {seat} really spans their own edges")
    want = "Black wins" if seat == ROW_JOINER else "White wins"
    check(G.render(s)["caption"] == want,
          f"post-swap caption names the right colour: want {want!r}, "
          f"got {G.render(s)['caption']!r}")
    check(G.returns(s)[seat] == 1.0 and G.returns(s)[1 - seat] == -1.0,
          "post-swap returns credit the right seat")

# ==========================================================================
# serialization: compare STATE OBJECTS, pin the key set, sweep a whole game
# ==========================================================================
KEYS = {"size", "board", "to_move", "last", "winner", "stalled", "ply", "skips", "swapped"}
seen_shapes = {"swap": False, "skip": False, "winner": False, "last_none": False}
rng = random.Random(31337)
for gi in range(20):
    s = G.initial_state({"size": 5})
    while True:
        d = G.serialize(s)
        check(set(d) == KEYS, f"serialize emits exactly {sorted(KEYS)}, got {sorted(d)}")
        json.dumps(d)
        check(G.deserialize(d) == s, "deserialize(serialize(s)) == s (STATE OBJECTS)")
        if s.swapped:
            seen_shapes["swap"] = True
        if s.skips:
            seen_shapes["skip"] = True
        if s.winner is not None:
            seen_shapes["winner"] = True
        if s.last is None:
            seen_shapes["last_none"] = True
        if G.is_terminal(s):
            break
        ms = G.legal_moves(s)
        s = G.apply_move(s, "swap" if ("swap" in ms and gi % 2 == 0) else
                         rng.choice([m for m in ms if m != "swap"]))
check(all(seen_shapes.values()),
      f"the round-trip sweep covered every field shape: {seen_shapes}")

# ==========================================================================
# render(): declared dimensions honoured at EVERY offered board size, from a
# FAR-CORNER position reached through apply_move (a fresh state is vacuous)
# ==========================================================================
MAN = json.loads((Path(__file__).resolve().parent / "manifest.json").read_text())
SIZES = MAN_SIZES
check(MAN["options"]["size"]["default"] in SIZES, "the default size is one of the choices")
for size in SIZES:
    s = G.initial_state({"size": size})
    # Black then White in opposite far corners; both placements are legal on an
    # (almost) empty board because neither pattern can exist with < 2 stones in
    # the same 2x2.
    s = G.apply_move(s, f"{size - 1},{size - 1}")
    s = G.apply_move(s, "0,0")
    spec = G.render(s)
    b = spec["board"]
    check(b["type"] == "square" and b["width"] == size and b["height"] == size,
          f"render declares a {size}x{size} square board")
    check(b["edges"] == {"top": BLACK, "bottom": BLACK, "left": WHITE, "right": WHITE},
          "render marks the black rows and the white columns")
    check(len(spec["pieces"]) == 2, "both far-corner stones are rendered")
    for p in spec["pieces"]:
        c, r = (int(x) for x in p["cell"].split(","))
        check(0 <= c < b["width"] and 0 <= r < b["height"],
              f"rendered piece {p['cell']} lies inside the declared {size}x{size} board")
    check(spec["highlights"] and spec["highlights"][0]["kind"] == "last-move",
          "the last move is highlighted")

# ==========================================================================
# describe_move, the ply bound, and the deliberate absence of a heuristic
# ==========================================================================
s = G.initial_state({"size": 5})
check(G.describe_move(s, "0,0") == "a1", "describe_move uses algebraic coordinates")
check(G.describe_move(s, "4,4") == "e5", "...at the far corner too")
win = NakattaState(size=5, board={(2, r): BLACK for r in range(4)}, to_move=BLACK)
check(G.describe_move(win, "2,4") == "c5#", "a winning placement is marked with '#'")
check(max_plies(5) == 5 * 5 + 1 and max_plies(9) == 9 * 9 + 1,
      "max_plies = size*size + 1 (all placements, plus the one swap ply)")

# ==========================================================================
# heuristic: SHAPE, ZERO-SUM, and -- separately -- DIRECTION pinned to
# measured values.  A sign-flipped eval (the bot plays to LOSE) and a
# constant-zero eval both pass every shape/range/zero-sum check, so direction
# has to be asserted on its own.
# ==========================================================================
st = G.initial_state({"size": 9})
h = G.heuristic(st)
check(isinstance(h, list) and len(h) == 2, "heuristic returns a LIST of 2 payoffs")
check(all(isinstance(x, float) for x in h), "heuristic payoffs are floats")
check(abs(h[0] + h[1]) < 1e-9, "heuristic is zero-sum")
check(abs(h[0]) < 1e-9, f"the empty board is even, got {h}")
# a near-complete BLACK ladder up the middle: Black needs 2 more stones, White 9
ahead = NakattaState(size=9, board={(4, r): BLACK for r in range(7)})
behind = NakattaState(size=9, board={(r, 4): WHITE for r in range(7)})
check(G.heuristic(ahead)[0] > 0.5,
      f"a near-complete Black chain scores high for Black, got {G.heuristic(ahead)}")
check(G.heuristic(behind)[0] < -0.5,
      f"a near-complete White chain scores low for Black, got {G.heuristic(behind)}")
check(G.heuristic(ahead)[0] > G.heuristic(st)[0] > G.heuristic(behind)[0],
      "DIRECTION: the better Black position scores higher for Black")
# ...and pinned to the actual distances, so a rescaling cannot pass silently
check(G._edge_distance(ahead, BLACK) == 2 and G._edge_distance(ahead, WHITE) == 9,
      f"edge distances on the ladder position: "
      f"{G._edge_distance(ahead, BLACK)} / {G._edge_distance(ahead, WHITE)}")
check(abs(G.heuristic(ahead)[0] - 0.985216917311436) < 1e-9,
      f"pinned heuristic value, got {G.heuristic(ahead)[0]!r}")
check(G._edge_distance(NakattaState(size=9, board={(4, r): BLACK for r in range(9)}),
                       WHITE) >= 9 * 9,
      "a completed Black wall makes White's edge distance unreachable")
# the shape bug that only fires when the rollout cutoff is REACHED (SPEC.md):
# force it with a deliberately tiny max_rollout.
from agp.mcts import MCTSBot                                    # noqa: E402
mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(
    G, G.initial_state({"size": 5}))
check(mv in G.legal_moves(G.initial_state({"size": 5})),
      "MCTSBot survives the rollout cutoff (heuristic shape is usable)")

# ==========================================================================
# `connects`: the GOAL EDGES and the ADJACENCY SET, pinned on constructed
# chains.  Everything above only ever reaches `connects` through wins that
# random play happens to produce, and Figure 1's chain both spans every row AND
# is orthogonal -- so it stays true if the goal row is moved in by one, or if
# diagonal steps are allowed.  Mutation testing confirmed both of those wrong
# readings survive the rest of this file.  Ground truth is Figure 1's artwork:
# the DARK stones (seat ROW_JOINER) join the TOP and BOTTOM edges, orthogonally.
# ==========================================================================
NC = 6
_col = 2
_full_col = {(_col, r): BLACK for r in range(NC)}
check(connects(_full_col, BLACK, NC), "a black column touching every row connects")
for _missing in (0, NC - 1):
    _part = {k: v for k, v in _full_col.items() if k != (_col, _missing)}
    check(not connects(_part, BLACK, NC),
          f"a black column missing row {_missing} does NOT connect: the goal edges "
          f"are exactly rows 0 and {NC - 1}, neither moved in by one")
_full_row = {(c, _col): WHITE for c in range(NC)}
check(connects(_full_row, WHITE, NC), "a white row touching every column connects")
for _missing in (0, NC - 1):
    _part = {k: v for k, v in _full_row.items() if k != (_missing, _col)}
    check(not connects(_part, WHITE, NC),
          f"a white row missing column {_missing} does NOT connect")
# diagonal adjacency must NOT connect (the sheet: "orthogonally (horizontally
# or vertically) interconnected"), in either diagonal direction and for either
# colour -- a chain that touches both goal edges but only diagonally.
for _name, _chain in (("main", {(r, r): BLACK for r in range(NC)}),
                      ("anti", {(NC - 1 - r, r): BLACK for r in range(NC)})):
    check(not connects(_chain, BLACK, NC),
          f"a purely {_name}-diagonal black chain does NOT connect (orthogonal only)")
    _w = {k: WHITE for k in _chain}
    check(not connects(_w, WHITE, NC),
          f"a purely {_name}-diagonal white chain does NOT connect either")
# and a diagonal chain becomes connected as soon as one elbow is filled in
_elbow = {(r, r): BLACK for r in range(NC)}
_elbow.update({(r, r + 1): BLACK for r in range(NC - 1)})
check(connects(_elbow, BLACK, NC),
      "...but filling the elbows of that diagonal DOES connect it "
      "(so the test above is not vacuous)")

# ==========================================================================
# the STALL branch, on CONSTRUCTED inputs.  Nothing can reach it: it is absent
# from every reachable position of the 2x2/3x3/4x4 solves and from every random
# and adversarial game, so random play, the differential and the exhaustive
# enumerations ALL skip it -- which is exactly why it needs a constructed test.
# Mutation testing confirmed that without this block, "the draw pays the mover"
# and "is_terminal ignores the stall" both survive the whole file.
# ==========================================================================
stall = NakattaState(size=5, board={(0, 0): BLACK, (2, 2): WHITE},
                     to_move=BLACK, stalled=True)
check(G.is_terminal(stall), "a stalled state is TERMINAL")
check(G.legal_moves(stall) == [], "a stalled state offers no moves")
check(G.returns(stall) == [0.0, 0.0],
      f"a stall is an HONEST DRAW scored 0-0, never a fabricated tiebreak, "
      f"got {G.returns(stall)}")
check("Draw" in G.render(stall)["caption"],
      f"the stall caption says Draw, got {G.render(stall)['caption']!r}")
check(G.deserialize(G.serialize(stall)) == stall, "a stalled state round-trips")
# ...and a decisive result outranks the flag even when both are set, in
# is_terminal, in returns AND in the caption (colours pinned to Figure 1).
for _seat in (BLACK, WHITE):
    _st = NakattaState(size=5, board=dict(stall.board), to_move=BLACK,
                       winner=_seat, stalled=True)
    check(G.is_terminal(_st), "a decisive+stalled state is terminal")
    check(G.returns(_st) == ([1.0, -1.0] if _seat == BLACK else [-1.0, 1.0]),
          f"a decisive result outranks the stall flag for seat {_seat}, "
          f"got {G.returns(_st)}")
    check(G.render(_st)["caption"] == ("Black wins" if _seat == ROW_JOINER else "White wins"),
          f"...and in the caption, got {G.render(_st)['caption']!r}")

print(("FAILED: %d" % len(FAILS)) if FAILS else "nakatta selftest: all checks passed")
sys.exit(1 if FAILS else 0)
