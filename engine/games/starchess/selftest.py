"""Selftest for Starchess (pure stdlib; run from engine/):

    PYTHONPATH=. python3 games/starchess/selftest.py

Correctness anchors (all from polgarstarchess.com — the official rules sheet
"Polgar Superstar Chess Rules.doc", the 16-image rules gallery
/Rules/images/1..16.jpg, and the published problem set /MateIn1/images/1..12.jpg)
--------------------------------------------------------------------------
1. The board: 37 cells, nine files of heights 1 2 7 6 5 6 7 2 1, numbered
   bottom-to-top within a file and left to right — checked against the numbered
   board diagram and against the closed form "union of two triangles".
2. The movement tables, cell by cell, from rules images 1-6 and 11-14: a piece
   alone on cell 19 reaches exactly the cells the official diagrams asterisk
   (king 6, queen 12, bishop 8, rook 4, knight 12), the pawn diagrams (image 6
   is the one that pins the two capture cells: own rook on 13, enemy knight on
   24), the five promotion cells, the two pawn-capture-geometry diagrams 13/14,
   and the limping pawn. "No en passant" is prose-only — the gallery has no
   such diagram — but it is exercised here anyway.
3. Rules image 9 is a CHECKMATE and rules image 10 a STALEMATE (they differ
   only in the black king's cell) — the pair pins the bishop's direction set
   and the stalemate-is-a-draw rule at the same time.
4. Every one of the 56 published problems. All TWELVE "mate in 1" problems have
   EXACTLY ONE mating move, and it is the one recorded here (problem 5 is an
   underpromotion, 26-27=N); all SIXTEEN "mate in 2" and SIXTEEN "mate in 3"
   problems are forced mates in exactly two / exactly three; and all TWELVE
   "Moremovers" are forced mates in exactly 4-6, none of them in three or fewer.
5. The setup phase: 25/25/16/16/9/9/4/4/1/1 placement choices, every one of the
   5! = 120 back-rank arrangements reachable for each side (= the official
   "1 of 14400"), no arrangement leaves either king in check, and White always
   has a move afterwards.
6. A frozen perft series from the example arrangement of rules image 8.
7. The clocks: a capture resets the 50-move counter and clears the repetition
   table, the double-step right really is per-cell-and-shrinking, and CHECKMATE
   OUTRANKS the 50-move counter (published mate-in-1 #4 played at halfmove 99).
8. RenderSpec shape on a setup-phase AND a decorated mid-game position: hex
   board with an explicit 37-id cell LIST, and pieces/tints/labels/highlights
   all keyed by those cell ids (a printed-number key would draw nothing).

The board geometry is additionally diffed, one-time and offline, against Árpád
Rusz's Zillions rules file (zillions-of-games.com submission 1822, linked from
the official Downloads page): all 168 orthogonal + 216 knight directed edges and
all six zones agree exactly. That file also settles the placement order.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agp.loader import load_from_dir  # noqa: E402

HERE = Path(__file__).resolve().parent
man, g = load_from_dir(HERE)
mod = sys.modules[type(g).__module__]
SState = mod.SState
NUM, BY_NUM, CELLS = mod.NUM, mod.BY_NUM, mod.CELLS

t0 = time.time()
checks = 0


def ok(cond, msg):
    global checks
    checks += 1
    if not cond:
        raise AssertionError(msg)


def pos(spec, to_move=0, unmoved=()):
    """Build a position from {cell_number: 'wK'/'bP'/...}."""
    board = {BY_NUM[n]: (0 if c[0] == "w" else 1, c[1]) for n, c in spec.items()}
    return SState(board=board, to_move=to_move, hands={0: {}, 1: {}},
                  unmoved=frozenset(BY_NUM[n] for n in unmoved), reps={})


def froms(move):
    return NUM[mod._cell(move.split(">")[0])]


def tonum(move):
    return NUM[mod._cell(move.split("=")[0].split(">")[1])]


def targets(state, frm):
    return sorted({tonum(m) for m in g.legal_moves(state) if froms(m) == frm})


# =========================================================================
# 1. Board geometry and the printed 1-37 numbering
# =========================================================================
ok(len(CELLS) == 37 and len(set(CELLS)) == 37, "37 distinct cells")
heights = {}
for (q, r) in CELLS:
    heights[q] = heights.get(q, 0) + 1
ok([heights[q] for q in range(-4, 5)] == [1, 2, 7, 6, 5, 6, 7, 2, 1],
   "file heights 1 2 7 6 5 6 7 2 1")
# numbering: files left to right, bottom (large r) to top (small r) within a file
order = sorted(CELLS, key=lambda c: (c[0], -c[1]))
ok([NUM[c] for c in order] == list(range(1, 38)), "numbering runs bottom-up, left to right")
# closed form: hexagram = union of the two triangles max/min of the cube coords
tri = {(q, r) for q in range(-6, 7) for r in range(-6, 7)
       if (q <= 2 and -q - r <= 2 and r <= 2) or (q >= -2 and -q - r >= -2 and r >= -2)}
ok(tri == set(CELLS), "cell set == union of the two size-2 triangles (hexagram)")
# the printed board diagram: pawn cells, back ranks and the six empty points
ok(mod.PAWN_NUMS[0] == (5, 12, 18, 23, 29) and mod.PAWN_NUMS[1] == (9, 15, 20, 26, 33),
   "pawn start cells")
ok(mod.BACK_NUMS[0] == (4, 11, 17, 22, 28) and mod.BACK_NUMS[1] == (10, 16, 21, 27, 34),
   "back rank cells")
s0 = g.initial_state()
ok(sorted(NUM[c] for c in s0.board) == [5, 9, 12, 15, 18, 20, 23, 26, 29, 33],
   "only the ten pawns start on the board")
# the six star tips have two neighbours each; cells 1/37 have the extreme shape
tips = [1, 4, 10, 28, 34, 37]
ok(all(len(mod._STEPS[BY_NUM[n]]) == 2 for n in tips), "star tips have 2 neighbours")
ok(len(mod._STEPS[BY_NUM[19]]) == 6, "the centre cell 19 has 6 neighbours")

# =========================================================================
# 2. Movement tables — official rules gallery images 1-6, 11-14
# =========================================================================
# images 1-5: a single white piece on cell 19 (plus distant kings so the
# position is legal); the asterisked cells in each diagram.
IMAGES = {
    "K": [13, 14, 18, 20, 24, 25],                                  # image 1
    "Q": [6, 8, 13, 14, 17, 18, 20, 21, 24, 25, 30, 32],            # image 2
    "B": [6, 8, 13, 14, 24, 25, 30, 32],                            # image 3
    "R": [17, 18, 20, 21],                                          # image 4
    "N": [2, 3, 5, 9, 11, 16, 22, 27, 29, 33, 35, 36],              # image 5
}
for letter, cells in IMAGES.items():
    if letter == "K":
        p = pos({19: "wK", 34: "bK", 4: "wR"})
    else:
        p = pos({19: "w" + letter, 4: "wK", 34: "bK"})
    ok(targets(p, 19) == cells, f"rules image: {letter} on 19 -> {cells}")
ok(sorted(IMAGES["B"] + IMAGES["R"]) == IMAGES["Q"],
   "queen = bishop + rook (no hex-diagonal move exists in Starchess)")

# image 6: white pawn 18 (unmoved), own rook 13, black knight 24. The diagram
# asterisks 19 and 20; 13 is own (never capturable) and 24 is the enemy knight.
p = pos({18: "wP", 13: "wR", 24: "bN", 4: "wK", 34: "bK"}, unmoved=(18,))
ok(targets(p, 18) == [19, 20, 24], "image 6: pawn 18 -> 19, 20 (double), x24")

# image 14: a white pawn on 12 with a black pawn on its forward-oblique cell 18
p = pos({12: "wP", 18: "bP", 4: "wK", 34: "bK"}, unmoved=(12,))
ok(18 in targets(p, 12), "image 14: pawn 12 captures the pawn on 18")
# image 13: the same enemy pawn one cell further round (on the hex DIAGONAL 14)
# is NOT capturable -- and after the double step 18-20 there is no en passant.
p = pos({18: "wP", 14: "bP", 4: "wK", 34: "bK"}, unmoved=(18, 14))
ok(14 not in targets(p, 18), "image 13: no capture along a hex diagonal")
after = g.apply_move(p, mod.Starchess._mstr(BY_NUM[18], BY_NUM[20], None))
# prose-only rule (the gallery has no en-passant diagram): the black pawn on 14
# may not answer the double step 18-20 by taking "in passing" on 19.
ok(19 not in targets(after, 14), "no en passant after the double step")

# image 11: the five promotion cells of a white pawn = Black's back rank
promo_reached = set()
for start, step in ((9, 10), (15, 16), (20, 21), (26, 27), (33, 34)):
    p = pos({start: "wP", 4: "wK", 28: "bK"})
    ms = [m for m in g.legal_moves(p) if froms(m) == start]
    ok(sorted(m.split("=")[1] for m in ms) == ["B", "N", "Q", "R"],
       f"pawn {start}->{step} promotes to exactly Q/R/B/N")
    promo_reached.add(step)
ok(promo_reached == {10, 16, 21, 27, 34}, "image 11: promotion cells 10/16/21/27/34")

# image 12: "dead pawn" on 3 (must capture to 8 before it can ever promote) and
# "mummy" on 1; neither has a forward move at all.
p = pos({3: "wP", 8: "bN", 4: "wK", 34: "bK"})
ok(targets(p, 3) == [8], "dead pawn on 3: only the capture to 8")
p = pos({1: "wP", 3: "bN", 4: "wK", 34: "bK"})
ok(targets(p, 1) == [3], "mummy on 1: only the capture to 3")

# "limping pawn": a pawn that reached a start cell by capturing keeps no double step
p = pos({12: "wP", 18: "bN", 4: "wK", 34: "bK"}, unmoved=(12,))
ok(targets(p, 12) == [18], "pawn 12 is blocked forward by nothing but has the capture")
after = g.apply_move(p, mod.Starchess._mstr(BY_NUM[12], BY_NUM[18], None))
lp = SState(board=after.board, to_move=0, hands={0: {}, 1: {}},
            unmoved=after.unmoved, reps={})
ok(targets(lp, 18) == [19], "limping pawn on 18 has NO double step")
p = pos({18: "wP", 4: "wK", 34: "bK"}, unmoved=(18,))
ok(targets(p, 18) == [19, 20], "an unmoved pawn on 18 does have the double step")

# no castling: a king next to its own rook has only its six step moves
p = pos({19: "wK", 18: "wR", 34: "bK"})
ok(targets(p, 19) == [13, 14, 20, 24, 25], "no castling (18 is the king's own rook)")

# =========================================================================
# 3. Rules images 9 (checkmate) and 10 (stalemate)
# =========================================================================
mate = pos({15: "wB", 32: "wK", 34: "bK"}, to_move=1)
ok(g.is_terminal(mate) and g.returns(mate) == [1.0, -1.0],
   "rules image 9: black king on 34 is checkmated")
stale = pos({15: "wB", 32: "wK", 37: "bK"}, to_move=1)
ok(g.is_terminal(stale) and g.returns(stale) == [0.0, 0.0],
   "rules image 10: black king on 37 is stalemated -> DRAW")
ok(not mod._in_check(stale.board, 1), "stalemate: the king is not in check")

# =========================================================================
# 4. The twelve published "mate in 1" problems (White to move)
# =========================================================================
MATE_IN_1 = [
    ({5: "wR", 8: "wK", 10: "bK"}, "K8-15"),      # discovered check up the file
    ({5: "wB", 8: "wK", 10: "bK"}, "B5-36"),
    ({5: "wN", 8: "wK", 10: "bK"}, "N5-3"),
    ({8: "wK", 10: "bK", 28: "wQ"}, "Q28-32"),
    ({10: "bK", 21: "wK", 26: "wP"}, "26-27=N"),  # underpromotion
    ({9: "wQ", 21: "wK", 33: "bK"}, "Q9-31"),
    ({25: "wQ", 30: "wK", 36: "bK"}, "Q25-26"),
    ({25: "wB", 30: "wK", 37: "bK"}, "B25-32"),
    ({4: "bK", 17: "wK", 37: "wB"}, "K17-12"),    # discovered check
    ({1: "wB", 30: "wK", 36: "bK"}, "B1-21"),
    ({19: "wN", 30: "wK", 37: "bK"}, "N19-29"),
    ({19: "wN", 28: "bK", 30: "wK"}, "N19-35"),
]
for i, (spec, answer) in enumerate(MATE_IN_1, 1):
    p = pos(spec, to_move=0)
    ok(not g.is_terminal(p), f"mate-in-1 #{i}: the position is live")
    mates = []
    for m in g.legal_moves(p):
        nxt = g.apply_move(p, m)
        if g.is_terminal(nxt) and g.returns(nxt) == [1.0, -1.0]:
            mates.append(g.describe_move(p, m))
    ok(mates == [answer], f"mate-in-1 #{i}: unique mate {answer} (got {mates})")


# 4b. The sixteen "mate in 2" and sixteen "mate in 3" problems. These positions
# were read off the diagrams by template matching rather than by eye, so the
# "forced in exactly N" property below is itself the check that they were read
# correctly: a single mis-read man would almost never preserve it.
def white_mates_in(state, n):
    """White to move: can White force mate within n of its own moves?"""
    if g.is_terminal(state):
        return g.returns(state) == [1.0, -1.0]
    if n == 0:
        return False
    for m in g.legal_moves(state):
        after = g.apply_move(state, m)
        if g.is_terminal(after):
            if g.returns(after) == [1.0, -1.0]:
                return True
            continue
        if all(white_mates_in(g.apply_move(after, r), n - 1)
               for r in g.legal_moves(after)):
            return True
    return False


MATE_IN_2 = [
    {1: "bK", 13: "wK", 14: "wQ"}, {9: "wK", 21: "bK", 33: "wB"},
    {26: "wP", 28: "bK", 30: "wK"}, {3: "wB", 19: "bK", 23: "wK", 26: "wQ"},
    {6: "wK", 7: "wQ", 24: "bK", 35: "wB"}, {1: "wQ", 6: "wB", 16: "wK", 33: "bK"},
    {25: "wK", 27: "bK", 31: "wB", 37: "wQ"}, {13: "wK", 15: "wQ", 24: "wN", 26: "bK"},
    {11: "wK", 13: "wQ", 22: "wN", 24: "bK"}, {11: "wK", 15: "wQ", 30: "bK", 37: "wN"},
    {5: "wN", 11: "wQ", 18: "bK", 32: "wK"}, {1: "wQ", 15: "wR", 25: "wK", 27: "bK"},
    {4: "wQ", 14: "wK", 16: "bK", 17: "wR"}, {4: "wR", 13: "wK", 15: "bK", 26: "wQ"},
    {11: "wK", 14: "wQ", 18: "bK", 22: "wR"}, {6: "wK", 18: "bK", 23: "wR", 25: "wQ"},
]
MATE_IN_3 = [
    {10: "bK", 15: "wB", 20: "wK"}, {3: "bK", 5: "wK", 20: "wB"},
    {18: "wB", 22: "bK", 24: "wK"}, {7: "wB", 8: "wQ", 14: "wK", 16: "bK"},
    {5: "wK", 11: "wB", 12: "wQ", 19: "bK"}, {2: "wK", 4: "wQ", 14: "bK", 30: "wN"},
    {2: "wK", 9: "bK", 12: "wQ", 20: "wN"}, {2: "wK", 9: "bK", 10: "wN", 37: "wQ"},
    {1: "wK", 7: "wN", 12: "wQ", 19: "bK"}, {1: "wK", 8: "wN", 12: "wQ", 19: "bK"},
    {1: "wK", 12: "wQ", 15: "wN", 19: "bK"}, {1: "wK", 12: "wQ", 19: "bK", 21: "wN"},
    {4: "wR", 8: "wK", 20: "bK", 32: "wQ"}, {1: "wK", 10: "wQ", 13: "bK", 21: "wR"},
    {15: "wK", 19: "bK", 23: "wB", 28: "wN"}, {14: "wN", 19: "bK", 23: "wK", 26: "wB"},
]
for i, spec in enumerate(MATE_IN_2, 1):
    p = pos(spec, to_move=0)
    ok(white_mates_in(p, 2) and not white_mates_in(p, 1),
       f"mate-in-2 #{i}: forced mate in exactly two")
for i, spec in enumerate(MATE_IN_3, 1):
    p = pos(spec, to_move=0)
    ok(white_mates_in(p, 3) and not white_mates_in(p, 2),
       f"mate-in-3 #{i}: forced mate in exactly three")

# 4c. The twelve "Moremovers" problems (/Moremovers/images/1..12.jpg) — the
# published set of mates in MORE than three. Every one must be a forced win and
# none may be a mate in <= 3, which is what separates this section from the one
# above. Two of them (#3, #4) are K+B vs K, so they also prove that a lone
# bishop FORCES mate on this board — the reason "insufficient material" here is
# narrowed to bare king vs bare king. The depths are memoised (the plain
# recursion above would not finish at depth 6).
MOREMOVERS = [                        # (position, forced mate in exactly N)
    ({18: "wQ", 28: "wK", 37: "bK"}, 4),
    ({3: "wQ", 14: "bK", 25: "wK"}, 5),
    ({3: "bK", 14: "wB", 15: "wK"}, 5),
    ({8: "wB", 20: "bK", 32: "wK"}, 6),
    ({14: "wK", 15: "wR", 18: "bK", 26: "wQ"}, 4),
    ({1: "wK", 8: "wQ", 16: "bK", 20: "wR"}, 4),
    ({3: "wK", 4: "wR", 6: "wQ", 14: "bK"}, 4),
    ({16: "wQ", 18: "wK", 20: "bK", 27: "wR"}, 4),
    ({7: "wQ", 9: "wR", 16: "bK", 19: "wK"}, 4),
    ({8: "wQ", 13: "wK", 20: "bK", 22: "wR"}, 4),
    ({8: "wK", 18: "wN", 20: "bK", 32: "wB"}, 4),
    ({9: "wK", 19: "wN", 21: "bK", 33: "wB"}, 4),
]


def mates_in(state, n, memo):
    k = ((state.to_move, tuple(sorted(state.board.items()))), n)
    if k in memo:
        return memo[k]
    if g.is_terminal(state):
        r = g.returns(state) == [1.0, -1.0]
    elif n == 0:
        r = False
    else:
        r = False
        for m in g.legal_moves(state):
            after = g.apply_move(state, m)
            if g.is_terminal(after):
                if g.returns(after) == [1.0, -1.0]:
                    r = True
                    break
                continue
            if all(mates_in(g.apply_move(after, x), n - 1, memo)
                   for x in g.legal_moves(after)):
                r = True
                break
    memo[k] = r
    return r


for i, (spec, depth) in enumerate(MOREMOVERS, 1):
    p = pos(spec, to_move=0)
    memo = {}
    ok(mates_in(p, depth, memo) and not mates_in(p, depth - 1, memo),
       f"moremover #{i}: forced mate in exactly {depth}")
    ok(depth >= 4, f"moremover #{i} really needs more than three moves")

# =========================================================================
# 5. The opening setup phase
# =========================================================================
s = g.initial_state()
counts = []
while mod.Starchess.in_setup(s):
    ms = g.legal_moves(s)
    counts.append(len(ms))
    ok(all("@" in m for m in ms), "setup moves use the drop syntax")
    s = g.apply_move(s, ms[0])
ok(counts == [25, 25, 16, 16, 9, 9, 4, 4, 1, 1], f"setup branching {counts}")
ok(s.ply == 10 and s.to_move == 0, "White moves first after ten placement plies")
ok(len(s.board) == 20, "20 men on the board once the setup ends")

# every one of the 5! arrangements is reachable, for each side independently
def arrangements(side):
    """All final back-rank assignments `side` can reach (opponent plays fixed)."""
    out = set()

    def rec(st):
        if not mod.Starchess.in_setup(st):
            out.add(tuple(sorted((NUM[c], t) for c, (o, t) in st.board.items()
                                 if o == side and t != "P")))
            return
        ms = g.legal_moves(st)
        if st.to_move != side:
            ms = ms[:1]                      # opponent: one fixed continuation
        for m in ms:
            rec(g.apply_move(st, m))
    rec(g.initial_state())
    return out

wa, ba = arrangements(0), arrangements(1)
ok(len(wa) == 120 and len(ba) == 120, "5! = 120 back-rank arrangements per side")
ok(len(wa) * len(ba) == 14400, "(5!)^2 = 14400 openings, as the official sheet states")

# no arrangement can leave a king in check, and White always has a move
import itertools  # noqa: E402
base = dict(g.initial_state().board)
perms = list(itertools.permutations(mod.SETUP_PIECES))
worst = 99
for wp in perms:
    for bp in perms:
        b = dict(base)
        for c, L in zip(mod.BACK_RANK[0], wp):
            b[c] = (0, L)
        for c, L in zip(mod.BACK_RANK[1], bp):
            b[c] = (1, L)
        assert not mod._in_check(b, 0) and not mod._in_check(b, 1), \
            "no opening arrangement may leave a king in check"
        st = SState(board=b, to_move=0, hands={0: {}, 1: {}},
                    unmoved=frozenset(mod.PAWN_START[0]) | frozenset(mod.PAWN_START[1]),
                    reps={})
        n = len(g.legal_moves(st))
        worst = min(worst, n)
ok(worst >= 5, f"White always has a move after any of the 14400 setups (min {worst})")
checks += 1

# =========================================================================
# 6. Perft from the example arrangement of rules image 8
# =========================================================================
IMAGE8 = ([("K", 4), ("N", 11), ("B", 17), ("Q", 22), ("R", 28)],
          [("R", 10), ("Q", 16), ("B", 21), ("N", 27), ("K", 34)])
s = g.initial_state()
for (wl, wn), (bl, bn) in zip(*IMAGE8):
    for L, n in ((wl, wn), (bl, bn)):
        c = BY_NUM[n]
        m = f"{L}@{c[0]},{c[1]}"
        ok(m in g.legal_moves(s), f"placement {m} is legal")
        s = g.apply_move(s, m)
ok({NUM[c]: t for c, (o, t) in s.board.items() if t != "P"} ==
   {4: "K", 11: "N", 17: "B", 22: "Q", 28: "R",
    10: "R", 16: "Q", 21: "B", 27: "N", 34: "K"}, "rules image 8 arrangement reached")


def perft(st, d):
    if d == 0:
        return 1
    return sum(perft(g.apply_move(st, m), d - 1) for m in g.legal_moves(st))


for depth, expect in ((1, 13), (2, 159), (3, 2302), (4, 31696)):
    ok(perft(s, depth) == expect, f"perft({depth}) == {expect}")

# =========================================================================
# 7. Draws, notation, serialization, bot contract
# =========================================================================
# bare kings: the only material that provably cannot mate here
bare = pos({19: "wK", 34: "bK"})
ok(g.is_terminal(bare) and g.returns(bare) == [0.0, 0.0], "K vs K is a draw")
# ... but K+B and K+N are NOT insufficient (mate-in-1 problems 2 and 3 prove it)
ok(not g.is_terminal(pos({5: "wB", 8: "wK", 10: "bK"})), "K+B vs K is live")
ok(not g.is_terminal(pos({5: "wN", 8: "wK", 10: "bK"})), "K+N vs K is live")

# 50-move rule fires long before the ply cap (the cap is never outcome-bearing)
p = pos({19: "wK", 34: "bK", 4: "wR"})
p.halfmove = 99
p2 = g.apply_move(p, [m for m in g.legal_moves(p) if froms(m) == 19][0])
ok(p2.halfmove == 100 and g.is_terminal(p2) and g.returns(p2) == [0.0, 0.0],
   "50-move rule draws")
ok(mod.PLY_CAP >= 20000, "ply cap is a pure backstop, far above any legal game")

# ...but CHECKMATE OUTRANKS the 50-move rule (FIDE 5.1.1/9.6): published
# mate-in-1 #4 delivered on the very ply that trips the counter is still 1-0.
p = pos({8: "wK", 10: "bK", 28: "wQ"})
p.halfmove = 99
mate = [m for m in g.legal_moves(p) if g.describe_move(p, m) == "Q28-32"][0]
p2 = g.apply_move(p, mate)
ok(p2.halfmove == 100 and g._draw_reason(p2) is None and g.is_terminal(p2)
   and g.returns(p2) == [1.0, -1.0], "checkmate beats the 50-move counter")

# a capture resets the 50-move counter AND clears the repetition table
p = pos({19: "wK", 34: "bK", 4: "wR", 10: "bR"})
p.halfmove = 77
p.reps = {"junk": 2}
p2 = g.apply_move(p, mod.Starchess._mstr(BY_NUM[4], BY_NUM[10], None))
ok(p2.halfmove == 0 and len(p2.reps) == 1 and "junk" not in p2.reps,
   "a capture resets halfmove and clears the repetition table")
p3 = g.apply_move(p, mod.Starchess._mstr(BY_NUM[4], BY_NUM[5], None))
ok(p3.halfmove == 78 and p3.reps.get("junk") == 2,
   "a quiet move increments halfmove and keeps the repetition table")
# a PAWN move is irreversible too
p = pos({19: "wK", 34: "bK", 12: "wP"}, unmoved=(12,))
p.halfmove = 40
ok(g.apply_move(p, mod.Starchess._mstr(BY_NUM[12], BY_NUM[13], None)).halfmove == 0,
   "a pawn move resets halfmove")

# The double-step right is tracked per CELL and the set only ever SHRINKS: once
# a start cell has been vacated it never comes back, so a DIFFERENT pawn that
# later lands on it gets no double step either. Played out, not introspected:
# 18x24 empties the start cell 18, then 12x18 brings another pawn to it.
s2 = pos({18: "wP", 12: "wP", 24: "bN", 4: "wK", 34: "bK"}, unmoved=(18, 12))
s2 = g.apply_move(s2, mod.Starchess._mstr(BY_NUM[18], BY_NUM[24], None))
ok(18 not in {NUM[c] for c in s2.unmoved}, "a pawn that moves leaves `unmoved`")
b2 = dict(s2.board)
b2[BY_NUM[18]] = (1, "N")                           # a black knight steps onto 18
s2 = g.apply_move(SState(board=b2, to_move=0, hands={0: {}, 1: {}},
                         unmoved=s2.unmoved, reps={}),
                  mod.Starchess._mstr(BY_NUM[12], BY_NUM[18], None))
lp2 = SState(board=s2.board, to_move=0, hands={0: {}, 1: {}},
             unmoved=s2.unmoved, reps={})
ok(targets(lp2, 18) == [19],
   "a pawn arriving on a VACATED start cell has no double step (19 only, not 20)")

# threefold repetition
s = pos({19: "wK", 4: "wR", 34: "bK", 10: "bR"})
s.reps = {mod._poskey(s.board, s.to_move, s.unmoved): 1}
cycle = [(19, 20), (34, 33), (20, 19), (33, 34)]
for rep in range(2):
    for frm, to in cycle:
        s = g.apply_move(s, mod.Starchess._mstr(BY_NUM[frm], BY_NUM[to], None))
ok(g.is_terminal(s) and g.returns(s) == [0.0, 0.0], "threefold repetition draws")

# describe_move: official numeric notation
p = pos({5: "wR", 8: "wK", 10: "bK"})
ok(g.describe_move(p, mod.Starchess._mstr(BY_NUM[8], BY_NUM[15], None)) == "K8-15",
   "notation: K8-15")
p = pos({26: "wP", 27: "bN", 21: "wK", 10: "bK"})
ok(g.describe_move(p, mod.Starchess._mstr(BY_NUM[26], BY_NUM[27], "N")) == "26x27=N",
   "notation: 26x27=N")
p = g.initial_state()
ok(g.describe_move(p, g.legal_moves(p)[0]).startswith("K@"), "notation: setup drop K@4")

# serialize/deserialize round-trips (setup phase, mid-game, a mid-file pawn whose
# double-step right is the ONLY difference -- so `unmoved` must survive the trip)
import json  # noqa: E402
free = pos({18: "wP", 21: "wK", 10: "bK"})
freeu = pos({18: "wP", 21: "wK", 10: "bK"}, unmoved=(18,))
ok(targets(free, 18) == [19] and targets(freeu, 18) == [19, 20],
   "the double-step right really does change the move list")
for st in (g.initial_state(), s, free, freeu,
           pos({26: "wP", 21: "wK", 10: "bK"}, unmoved=(26,))):
    d = json.loads(json.dumps(g.serialize(st)))     # must survive real JSON
    r = g.deserialize(d)
    ok(g.serialize(r) == g.serialize(st), "serialize round-trip")
    ok(r.unmoved == st.unmoved and r.halfmove == st.halfmove and r.ply == st.ply
       and r.reps == st.reps and r.last == st.last and r.board == st.board
       and {p: dict(h) for p, h in r.hands.items()}
           == {p: dict(h) for p, h in st.hands.items()}, "round-trip keeps every field")
    ok(sorted(g.legal_moves(r)) == sorted(g.legal_moves(st)), "round-trip keeps moves")

# render spec shape (the renderer itself is browser-verified, not here).
# Board.jsx keys pieces/tints/labels/highlights by CELL ID, so every key has to
# be one of the ids in board.cells -- a printed-number key would silently draw
# nothing at all.
_decorated = pos({18: "wP", 21: "wK", 10: "bK", 24: "bN"}, unmoved=(18,))
_decorated.last = (BY_NUM[12], BY_NUM[18])
for st, tag in ((g.initial_state(), "setup"), (_decorated, "mid-game")):
    spec = json.loads(json.dumps(g.render(st)))     # must be JSON-able
    b = spec["board"]
    ok(b["type"] == "hex" and len(b["cells"]) == 37 and len(set(b["cells"])) == 37,
       f"render[{tag}]: explicit 37-cell hex list")
    ids = set(b["cells"])
    ok(all(isinstance(c, str) and "," in c for c in b["cells"]),
       f"render[{tag}]: hex cells are axial id STRINGS (not polygons objects)")
    ok(set(b["labels"]) == ids and b["labels"]["0,0"] == "19",
       f"render[{tag}]: a printed number on every cell, 19 in the centre")
    ok(set(b["tints"]) == ids, f"render[{tag}]: tints keyed by cell id")
    ok({p["cell"] for p in spec["pieces"]} <= ids,
       f"render[{tag}]: piece cells keyed by cell id")
    ok({h["cell"] for h in spec["highlights"]} <= ids,
       f"render[{tag}]: highlight cells keyed by cell id")
    ok(spec.get("pieceset") == "chess", f"render[{tag}]: chess glyphs")
spec = g.render(g.initial_state())
ok(len(spec["reserve"]["0"]) == 5 and len(spec["reserve"]["1"]) == 5,
   "render: both reserves full during the setup phase")
# the last-move highlight really tracks the move that was just played
st = g.initial_state()
st = g.apply_move(st, [m for m in g.legal_moves(st) if m.startswith("Q@")][0])
mid = g.render(st)
ok([h["cell"] for h in mid["highlights"]] == [f"{c[0]},{c[1]}" for c in (st.last[0],)],
   "render: the placement is highlighted")
st = pos({18: "wP", 21: "wK", 10: "bK"}, unmoved=(18,))
st = g.apply_move(st, mod.Starchess._mstr(BY_NUM[18], BY_NUM[20], None))
ok(sorted(NUM[mod._cell(h["cell"])] for h in g.render(st)["highlights"]) == [18, 20],
   "render: from- and to-cell of the last move are highlighted")

# random playout terminates
import random  # noqa: E402
rng = random.Random(11)
st = g.initial_state()
plies = 0
while not g.is_terminal(st):
    st = g.apply_move(st, rng.choice(g.legal_moves(st)))
    plies += 1
    assert plies <= mod.PLY_CAP, "random playout exceeded the ply cap"
ok(plies < mod.PLY_CAP, "random playout terminates well inside the ply cap")
ret = g.returns(st)
ok(len(ret) == 2 and abs(ret[0] + ret[1]) < 1e-9, "well-formed zero-sum returns")

# heuristic contract: a LIST of num_players payoffs
h = g.heuristic(g.initial_state())
ok(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9,
   "heuristic is a zero-sum pair")
from agp.mcts import MCTSBot  # noqa: E402
MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(g, g.initial_state())
checks += 1

print(f"starchess selftest OK ({checks} checks, {time.time() - t0:.1f}s)")
