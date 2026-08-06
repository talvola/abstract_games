#!/usr/bin/env python3
"""Carnac correctness anchors -- pure stdlib, run by tests/test_games.py.

PRIMARY ANCHOR: the publisher's own worked final scoring, printed on page 3 of
the HUCH! 2014 rulebook ("Beispiel einer Abschlusswertung").  The figure shows
a finished LARGE-board game and states six things about it:

    Spieler Rot und Spieler Weiss haben in dieser Partie jeweils 5 Dolmen
    erbaut.  ...  Groesster weisser Dolmen = 8 Symbole.  Groesster roter
    Dolmen = 8 Symbole.  ...  Zweitgroesster weisser Dolmen = 6 Symbole.
    Zweitgroesster roter Dolmen = 5 Symbole.  Weiss gewinnt das Spiel.

The board was read off that figure square by square (offline, from the PDF's
embedded 419x801 raster: the printed grid was located by detecting its rule
lines, giving 9 columns x 14 rows at 137.5px pitch, and each of the 126 cells
was classified red / white / empty).  The transcription below reproduces ALL
SIX printed facts exactly -- red dolmens (8,5,4,4,4) and white (8,6,4,3,3),
five each, and White the winner -- which is what makes it a self-checking
decode rather than a hand-drawn position.  It pins, in one shot: bird's-eye
scoring, ORTHOGONAL-only adjacency, the >= 3 threshold, the descending-size
tie-break chain, and which seat is which colour (the two size multisets differ,
so the figure itself decides the mapping -- not this file).

MEASURED DISCRIMINATING POWER OF THAT ANCHOR: it is BLIND to the game's most
important scoring rule.  Both players have five dolmens, so "most dolmens
first" and "compare sizes lexicographically" pick the same winner here.  A
size-only reading disagrees with the rulebook on 19.8% / 30.8% / 42.5% of
random games (14x9 / 10x7 / 8x5) -- and AbstractPlay's `carnac.ts` ships
exactly that reading.  Section 2 below covers the gap with constructed
positions and with the rulebook's own strategy tip.

SECONDARY ANCHOR: the differential against AbstractPlay `gameslib` (manual /
one-time, needs node -- it lives in the build scratch dir, not in the package).
40+ random games per board size, comparing the phase, the seat on turn, the
stock, the pending stone, the set of empty cells offered, the (cell -> colour)
effect of every topple offered, the whole top-view colour map after every move,
and both dolmen size lists at the end: 0 mismatches, and every move our engine
chose was accepted by the oracle.  Its 280-move opening on 10x7 is re-checked
in section 8.  Only the WINNER RULE diverges (see above).
"""

import dataclasses
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                              # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
M = sys.modules[type(G).__module__]        # the LIVE module object
CState = M.CState
RED, BLUE, STOCK = M.RED, M.BLUE, M.STOCK
BOARDS = M.BOARDS

FAILS = []


def ok(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


def idx(w, c, r):
    return r * w + c


def build(rows, w, h, reserve=0, phase="place", pend=None, to_move=RED,
          transpose=False):
    """A state from strings, TOP row first: 'R' red on top, 'B' blue, '.' empty.

    Every stone is modelled as STANDING (partner -1).  Scoring reads only the
    top-view colour of each cell, which is exactly what the rulebook's figure
    prints, so the standing/lying split (undecodable from a bird's-eye figure)
    cannot affect any assertion made about it.
    """
    board = []
    for i, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == ".":
                continue
            fr = len(rows) - 1 - i                 # row 0 is the BOTTOM
            cc, rr = (fr, c) if transpose else (c, fr)
            board.append((idx(w, cc, rr), RED if ch == "R" else BLUE, -1))
    return CState(w=w, h=h, board=M._sorted_board(board), reserve=reserve,
                  phase=phase, pend=pend, to_move=to_move, last=())


# =========================================================================
# 1. The rulebook's worked final scoring (page 3 figure)
# =========================================================================
# Read off the figure in the orientation it is PRINTED (portrait: 9 wide,
# 14 tall).  `transpose=True` lays it onto the real 14x9 large board; a
# transpose preserves orthogonal adjacency, so every dolmen is preserved,
# and nothing here depends on the north/south vs east/west distinction.
FIG = [
    ".........",
    "...R.....",
    "...RRR...",
    "...BB....",
    "R.B.B..B.",
    "RRBBR..B.",
    ".R.BRR.BB",
    ".R...RRB.",
    ".RRR.BBB.",
    "..BBB....",
    "...BB..B.",
    "...BRRRB.",
    "RR....RB.",
    "RR.......",
]
fig = build(FIG, 14, 9, reserve=0, transpose=True)

cells = len(fig.board)
ok(cells == 49, f"figure: 49 occupied squares transcribed (got {cells})")
# The figure must be a legal FINAL position: the stock of 28 is spent, and a
# standing/lying split exists that accounts for exactly 28 megaliths.
lying = cells - STOCK
ok(STOCK <= cells <= 2 * STOCK,
   f"figure: {cells} squares is consistent with exactly {STOCK} megaliths "
   f"({STOCK - lying} standing + {lying} lying); {STOCK}..{2 * STOCK} is the "
   f"coverable range")

red, blue = G.scores(fig)
ok(red == (8, 5, 4, 4, 4), f"figure: red dolmen sizes (8,5,4,4,4) (got {red})")
ok(blue == (8, 6, 4, 3, 3), f"figure: white dolmen sizes (8,6,4,3,3) (got {blue})")
# The six facts the figure PRINTS, asserted one by one.
ok(len(red) == 5, f'figure prints "5 Dolmen" for Rot (got {len(red)})')
ok(len(blue) == 5, f'figure prints "5 Dolmen" for Weiss (got {len(blue)})')
ok(red[0] == 8, 'figure prints "Groesster roter Dolmen = 8 Symbole"')
ok(blue[0] == 8, 'figure prints "Groesster weisser Dolmen = 8 Symbole"')
ok(red[1] == 5, 'figure prints "Zweitgroesster roter Dolmen = 5 Symbole"')
ok(blue[1] == 6, 'figure prints "Zweitgroesster weisser Dolmen = 6 Symbole"')
ok(G.is_terminal(fig), "figure: the stock is spent, so the game is over")
ok(G.returns(fig) == [-1.0, 1.0],
   f'figure: "Weiss gewinnt das Spiel" (got {G.returns(fig)})')

# The four dolmens the figure OUTLINES, as drawn (their shapes, not just sizes).
def component_of(state, c, r):
    w, h = state.w, state.h
    top = dict((e[0], e[1]) for e in state.board)
    start = idx(w, c, r)
    seat = top[start]
    seen, todo = {start}, [start]
    while todo:
        cur = todo.pop()
        cc, rr = cur % w, cur // w
        for dc, dr in M.DIRS:
            c2, r2 = cc + dc, rr + dr
            if 0 <= c2 < w and 0 <= r2 < h:
                j = idx(w, c2, r2)
                if top.get(j) == seat and j not in seen:
                    seen.add(j)
                    todo.append(j)
    return seen


def fig_cells(pairs):
    """figure (col, row-from-top) -> our transposed cell indices.

    `build` maps figure column `c` and figure row-from-top `r` to board column
    `13 - r` and board row `c` (bottom-first row index `13 - r`, transposed).
    """
    return {idx(14, 13 - r, c) for c, r in pairs}


OUTLINED = {
    "red 8": [(0, 4), (0, 5), (1, 5), (1, 6), (1, 7), (1, 8), (2, 8), (3, 8)],
    "red 5": [(4, 5), (4, 6), (5, 6), (5, 7), (6, 7)],
    "white 8": [(7, 4), (7, 5), (7, 6), (8, 6), (7, 7), (7, 8), (6, 8), (5, 8)],
    "white 6": [(2, 9), (3, 9), (4, 9), (3, 10), (4, 10), (3, 11)],
}
for name, pairs in OUTLINED.items():
    want = fig_cells(pairs)
    c0, r0 = pairs[0]
    got = component_of(fig, 13 - r0, c0)
    ok(got == want,
       f"figure outline '{name}': the drawn region is exactly one dolmen "
       f"(size {len(want)}; got size {len(got)})")

# =========================================================================
# 2. MOST dolmens comes FIRST -- the part the figure cannot see
# =========================================================================
# "Der Spieler mit den meisten Dolmen gewinnt das Spiel" / "Bei CARNAC zaehlt
# die Anzahl der Dolmen und nicht unbedingt deren Groesse" (rulebook, page 2
# SPIELTIPPS).  Red owns ONE dolmen of 8, Blue THREE of 3: Blue wins on count
# even though Red owns the largest dolmen on the board.
COUNT = [
    "RRRRRRRR",
    "........",
    "BBB..BBB",
    "........",
    "BBB.....",
]
cnt = build(COUNT, 8, 5, reserve=0)
r2, b2 = G.scores(cnt)
ok(r2 == (8,) and b2 == (3, 3, 3), f"count test: sizes {r2} vs {b2}")
ok(G.returns(cnt) == [-1.0, 1.0],
   "MOST dolmens wins: Blue's 3x3 beats Red's single 8 "
   f"(got {G.returns(cnt)})")
ok(G.compare(r2, b2) < 0, "compare(): a longer dolmen list wins outright")
# and the same board scored size-first (the reading gameslib ships) would hand
# it to Red -- so this test is exactly the discriminator.
ok(r2[0] > b2[0], "count test premise: Red really does own the LARGEST dolmen")

# The rulebook's strategy tip, as an assertion: "Durch das Zusammenwachsen
# gleichfarbiger Dolmen werden also bereits erreichte Siegpunkte wieder
# minimiert" -- merging two of your own dolmens into one COSTS you.
SPLIT = ["RRR.RRR", ".......", "BBB.BBB"]
MERGED = ["RRRRRRR", ".......", "BBB.BBB"]
sp, mg = build(SPLIT, 7, 3, reserve=0), build(MERGED, 7, 3, reserve=0)
ok(G.scores(sp)[0] == (3, 3) and G.scores(mg)[0] == (7,),
   f"merge test: {G.scores(sp)[0]} -> {G.scores(mg)[0]}")
ok(G.returns(sp) == [0.0, 0.0],
   f"merge test: two 3s each is a genuine tie -> honest DRAW (got {G.returns(sp)})")
ok(G.returns(mg) == [-1.0, 1.0],
   "merge test: joining your own two dolmens into one LOSES the game "
   f"(got {G.returns(mg)})")

# A genuine tie is an honest draw, and it really happens (measured: 0.2% of
# random 10x7 games, 1.5% at 14x9), so this is not a dead branch.
ok(G.compare((4, 3), (4, 3)) == 0 and G.compare((), ()) == 0,
   "compare(): identical dolmen lists are a tie")
ok(G.returns(build(["...", "...", "..."], 3, 3, reserve=0)) == [0.0, 0.0],
   "an empty board scores 0-0 as a draw, not a fabricated win")

# =========================================================================
# 3. Diagonal contact does NOT connect
# =========================================================================
# Rulebook: "Diagonal benachbarte Megalithen gelten nicht als
# aneinandergrenzend", illustrated by the page-1 "Kein Dolmen" figure: a
# standing stone diagonally touching a toppled pair is NOT a dolmen.
DIAG = ["R..", ".RR", "..."]
dg = build(DIAG, 3, 3, reserve=0)
ok(G.scores(dg)[0] == (),
   f"diagonal chain of 3 is NOT a dolmen (got {G.scores(dg)[0]})")
ok(G.scores(build(["RRR", "...", "..."], 3, 3, reserve=0))[0] == (3,),
   "three in an orthogonal line IS the smallest dolmen")
ok(G.scores(build(["RR.", ".R.", "..."], 3, 3, reserve=0))[0] == (3,),
   "an orthogonal L of 3 is a dolmen")
ok(G.scores(build(["RR.", "...", "..."], 3, 3, reserve=0))[0] == (),
   "two adjacent squares are not yet a dolmen")

# =========================================================================
# 4. The piece: which colour a topple brings up
# =========================================================================
# BGG 103061 (the designer's own component note): "three faces (one square and
# two OPPOSED rectangular ones) of one color and the other three faces of the
# other color".  Opposite long faces therefore share a colour, so a topple
# north or south reveals one pair and east or west the other -- and the two
# pairs are different colours.
for ns in (RED, BLUE):
    st = CState(w=10, h=7, board=((idx(10, 5, 3), RED, -1),), reserve=20,
                phase="tip", pend=(idx(10, 5, 3), RED, ns), to_move=BLUE)
    got = {}
    for m in G.legal_moves(st):
        if m == "pass":
            continue
        nxt = G.apply_move(st, m)
        new = [(i, t, p) for i, t, p in nxt.board if p >= 0]
        ok(len(new) == 2 and new[0][1] == new[1][1],
           "a toppled megalith covers 2 cells showing the SAME colour")
        near = int(m.split(">")[1].split(",")[0]), int(m.split(">")[1].split(",")[1])
        d = (near[0] - 5, near[1] - 3)
        got[d] = new[0][1]
    ok(got[(0, 1)] == ns and got[(0, -1)] == ns,
       f"topple north and south both reveal the N/S pair ({ns}); got {got}")
    ok(got[(1, 0)] == 1 - ns and got[(-1, 0)] == 1 - ns,
       f"topple east and west both reveal the other pair ({1 - ns}); got {got}")
    ok(len(set(got.values())) == 2,
       "the two long-face pairs are opposite colours, so the toppler always "
       "has a real colour choice")
# All four orientations are offered for every empty square, and they are the
# 2x2 product (colour up) x (colour on the N/S axis).
s0 = G.initial_state()
per = {}
for m in G.legal_moves(s0):
    per.setdefault(m.split("=")[0], set()).add(m.split("=")[1])
ok(all(v == {"RR", "RB", "BR", "BB"} for v in per.values()),
   "every empty square offers exactly the four orientations")

# =========================================================================
# 5. Turn structure ("I cut, you choose")
# =========================================================================
s = G.initial_state()                                  # 10x7
ok(G.current_player(s) == RED and s.phase == "place",
   "Red places first from the place phase")
s1 = G.apply_move(s, "4,3=RB")
ok(s1.phase == "tip" and s1.to_move == BLUE and s1.pend[0] == idx(10, 4, 3),
   "after a placement the OPPONENT decides whether to topple it")
ok(s1.reserve == STOCK - 1, "a placement spends one megalith from the stock")
ok("pass" in G.legal_moves(s1), "declining to topple is always offered")

# (ii) DECLINING hands the turn straight BACK to the placer, who places again.
sp1 = G.apply_move(s1, "pass")
ok(sp1.phase == "place" and sp1.to_move == RED,
   "rulebook (ii): after a decline it is the PLACER's turn again "
   f"(got seat {sp1.to_move})")
ok(sp1.reserve == s1.reserve and sp1.pend is None,
   "a decline spends nothing and clears the pending stone")

# (i) TOPPLING is followed by the toppler's OWN placement, same seat.
st1 = G.apply_move(s1, "4,3>4,4")
ok(st1.phase == "place" and st1.to_move == BLUE,
   f"rulebook (i): the toppler places next, so the seat is unchanged "
   f"(got seat {st1.to_move})")
ok(st1.reserve == s1.reserve, "toppling itself spends no megalith")
occ = {e[0] for e in st1.board}
ok(idx(10, 4, 3) not in occ, "rulebook: the square it stood on is FREE again")
ok(idx(10, 4, 4) in occ and idx(10, 4, 5) in occ,
   "a topple lays the stone on the two squares beyond it")
ok(f"4,3={'RR'}" in G.legal_moves(st1) or "4,3=RB" in G.legal_moves(st1),
   "the vacated square is immediately available for the follow-up placement")
st2 = G.apply_move(st1, "4,3=BR")
ok(st2.to_move == RED and st2.phase == "tip",
   "and then it is the other seat's turn to decide")

# A stone that cannot be toppled at all: the opponent gets no choice but still
# takes their turn ("if your opponent is not able to tilt the last placed
# megalith, then it is still his turn and he may place a new megalith").
# Boxed in on an 8x5 board: nothing two squares away in any direction is free.
BOX = [
    "........",
    "...B....",
    "..B.B...",
    "........",
    "...B....",
]
boxed = build(BOX, 8, 5, reserve=10, to_move=RED)
free = idx(8, 3, 2)
ok(free not in {e[0] for e in boxed.board}, "boxed test premise: c3 is empty")
nb = G.apply_move(boxed, "3,2=RR")
ok(G.topple_options(nb, free) == [],
   f"boxed test premise: no topple direction is available (got "
   f"{G.topple_options(nb, free)})")
ok(nb.phase == "place" and nb.to_move == BLUE and nb.pend is None,
   "an untippable stone gives the opponent a plain placement turn "
   f"(got phase {nb.phase}, seat {nb.to_move})")
# ... and that clause really is reachable in play (not a dead branch):
rng = random.Random(4)
untippable = 0
for _ in range(60):
    t = G.initial_state(options={"board": "8x5"})
    prev = None
    while not G.is_terminal(t):
        if prev == "place" and t.phase == "place":
            untippable += 1
        prev = t.phase
        t = G.apply_move(t, rng.choice(G.legal_moves(t)))
ok(untippable > 0,
   f"the untippable-stone clause is reachable in real play ({untippable} hits)")

# =========================================================================
# 6. End of the game, and the 28th megalith
# =========================================================================
# "Das Spiel endet sofort, wenn der gemeinsame Vorrat an Megalithen
# aufgebraucht ist" -- so the last stone placed is never toppled.
last = CState(w=10, h=7, board=(), reserve=1, phase="place", to_move=RED)
after = G.apply_move(last, "4,3=RB")
ok(G.is_terminal(after) and after.reserve == 0,
   "the game ends the instant the stock is empty")
ok(after.phase == "place" and after.pend is None and G.legal_moves(after) == [],
   "the 28th megalith is never offered for toppling")
# ... and the board-full ending, only reachable on the small board (28
# megaliths can cover at most 56 squares, and 8x5 = 40 < 56).
full = CState(w=3, h=3, reserve=5, phase="place", to_move=RED,
              board=M._sorted_board([(i, RED, -1) for i in range(8)]))
fin = G.apply_move(full, "2,2=BR")
ok(G.is_terminal(fin) and fin.reserve == 4,
   "the game also ends when the last empty square is filled")
ok(len(BOARDS["8x5"]) == 2 and BOARDS["8x5"][0] * BOARDS["8x5"][1] < 2 * STOCK,
   "board-full is reachable on 8x5 (40 squares < 56 coverable)")
for key in ("10x7", "14x9"):
    w, h = BOARDS[key]
    ok(w * h > 2 * STOCK,
       f"{key} ({w}x{h}) cannot fill up, so it always ends on the stock")

# =========================================================================
# 7. Opening move counts (the AbstractPlay differential's anchor)
# =========================================================================
for key, (w, h) in BOARDS.items():
    n = len(G.legal_moves(G.initial_state(options={"board": key})))
    ok(n == 4 * w * h,
       f"{key}: {4 * w * h} opening placements = 4 orientations x {w * h} "
       f"squares (got {n})")
ok(len(G.legal_moves(G.initial_state(options={"board": "10x7"}))) == 280,
   "10x7 opens with 280 moves (matches AbstractPlay gameslib exactly)")
ok(G.initial_state(options={"board": "zzz"}).w == 10,
   "an unknown board option falls back to the default 10x7")

# =========================================================================
# 8. Termination: every step of the proof, checked on live positions
# =========================================================================
# plies <= 2 * STOCK - 1, because every "place" ply spends one megalith, every
# "tip" ply is immediately followed by a "place" ply, and the FIRST ply of the
# game is a placement (so there is one fewer tip ply than placements).
PLY_BOUND = 2 * STOCK - 1
rng = random.Random(17)
longest = 0
for key in BOARDS:
    for _ in range(40):
        t = G.initial_state(options={"board": key})
        n = places = tips = 0
        prev_phase = None
        while not G.is_terminal(t):
            ms = G.legal_moves(t)
            ok(bool(ms), f"{key}: non-terminal state with NO legal move at ply {n}")
            if not ms:
                break
            # invariant: the pending stone exists in exactly the tip phase
            ok((t.phase == "tip") == (t.pend is not None),
               f"{key}: phase {t.phase} with pend {t.pend} at ply {n}")
            # proof step: the tip phase always has at least one topple + a pass
            if t.phase == "tip":
                opts = G.topple_options(t, t.pend[0])
                ok(len(opts) >= 1,
                   f"{key}: tip phase with no topple option at ply {n}")
                ok(len(ms) == len(opts) + 1,
                   f"{key}: tip moves != topples + pass at ply {n}")
                ok(t.pend[0] not in {e[0] for e in t.board if e[2] >= 0},
                   f"{key}: the pending stone must be standing at ply {n}")
                empt = t.w * t.h - len(t.board)
                ok(empt >= 2,
                   f"{key}: tip phase needs >= 2 empty squares (got {empt})")
                for _d, near, far in opts:
                    ok(near != t.pend[0] and far != t.pend[0],
                       f"{key}: a topple target is never the stone's own square")
                tips += 1
            else:
                places += 1
            # proof step: a tip ply is always followed by a place ply
            if prev_phase == "tip":
                ok(t.phase == "place",
                   f"{key}: the ply after a tip ply is not a placement")
            prev_phase = t.phase
            before = t
            snap = dataclasses.astuple(before)
            t = G.apply_move(t, rng.choice(ms))
            ok(dataclasses.astuple(before) == snap,
               f"{key}: apply_move mutated the state it was given at ply {n}")
            ok(before == G.deserialize(G.serialize(before)),
               f"{key}: serialize/deserialize round trip at ply {n}")
            n += 1
        longest = max(longest, n)
        ok(n <= PLY_BOUND, f"{key}: game ran {n} plies, bound is {PLY_BOUND}")
        ok(places <= STOCK, f"{key}: {places} placements exceeds the stock")
        ok(tips <= places - 1 if places else tips == 0,
           f"{key}: {tips} tip plies vs {places} placements")
        ok(t.reserve == STOCK - places, f"{key}: stock accounting off")
ok(longest >= 40, f"the sweep reached long games (longest {longest} plies)")

# =========================================================================
# 9. serialize / deserialize -- compared as STATES, swept over whole games
# =========================================================================
KEYS = {"w", "h", "board", "reserve", "phase", "pend", "to_move", "last"}
rng = random.Random(23)
seen_phases, seen_pend, seen_last = set(), set(), set()
for key in BOARDS:
    for _ in range(8):
        t = G.initial_state(options={"board": key})
        while True:
            d = G.serialize(t)
            ok(set(d) == KEYS, f"serialize keys {set(d)} != {KEYS}")
            ok(json.loads(json.dumps(d)) == d, "serialize() is not JSON-able")
            back = G.deserialize(json.loads(json.dumps(d)))
            ok(back == t, f"serialize/deserialize lost state:\n  {t}\n  {back}")
            ok(dataclasses.asdict(back) == dataclasses.asdict(t),
               "serialize/deserialize changed a field")
            seen_phases.add(t.phase)
            seen_pend.add(t.pend is None)
            seen_last.add(len(t.last))
            if G.is_terminal(t):
                break
            t = G.apply_move(t, rng.choice(G.legal_moves(t)))
ok(seen_phases == {"place", "tip"}, f"round-trip sweep saw phases {seen_phases}")
ok(seen_pend == {True, False}, "round-trip sweep saw pend both set and None")
ok(seen_last == {0, 1, 2}, f"round-trip sweep saw last of every shape {seen_last}")
# Every field must be load-bearing: dropping any one from serialize() must be
# visible in the STATE comparison above (the classic vacuous round-trip bug).
p_tip = G.apply_move(G.initial_state(options={"board": "8x5"}), "2,2=RB")
p_lie = G.apply_move(p_tip, "2,2>2,3")
for k in KEYS:
    bites = False
    for probe in (p_tip, p_lie):
        d = G.serialize(probe)
        del d[k]
        try:
            bites = bites or G.deserialize(d) != probe
        except Exception:
            bites = True                       # a hard failure is fine too
    ok(bites, f"serialize() key {k!r} is not load-bearing on any probe state")

# =========================================================================
# 10. render() declares a board that CONTAINS its pieces, at EVERY size
# =========================================================================
def drive_to_corners(key):
    """Reach a position with stones on all four corners, via apply_move."""
    w, h = BOARDS[key]
    t = G.initial_state(options={"board": key})
    # a topple that LANDS on the far corner, then the other three corners
    plan = [f"{w - 3},{h - 1}=RR", f"{w - 3},{h - 1}>{w - 2},{h - 1}",
            "0,0=BB", f"0,{h - 1}=RB", f"{w - 1},0=BR"]
    for m in plan:
        while t.phase == "tip" and m not in G.legal_moves(t):
            t = G.apply_move(t, "pass")
        ok(m in G.legal_moves(t), f"{key}: corner plan move {m} is illegal")
        t = G.apply_move(t, m)
    return t


for key, (w, h) in BOARDS.items():
    t = drive_to_corners(key)
    spec = G.render(t)
    b = spec["board"]
    ok((b["width"], b["height"]) == (w, h),
       f"{key}: render declares {b['width']}x{b['height']}, want {w}x{h}")
    occ = {M.cell_id(w, i) for i, _, _ in t.board}
    got = {p["cell"] for p in spec["pieces"]}
    ok(got == occ, f"{key}: render pieces != occupied squares "
                   f"({sorted(occ - got)} missing)")
    for p in spec["pieces"]:
        c, r = (int(x) for x in p["cell"].split(","))
        ok(0 <= c < w and 0 <= r < h,
           f"{key}: rendered piece {p['cell']} is outside the declared board")
        ok(p["owner"] in (RED, BLUE), f"{key}: bad piece owner {p!r}")
    for seg in spec["board"].get("overlay", []):
        for pt in seg:
            if isinstance(pt, str):
                continue
            ok(-0.6 <= pt[0] <= w - 0.4 and -0.6 <= pt[1] <= h - 0.4,
               f"{key}: overlay point {pt} is outside the declared board")
    # the far corners really are occupied (otherwise this check is vacuous)
    for corner in (f"0,0", f"{w - 1},0", f"0,{h - 1}", f"{w - 1},{h - 1}"):
        ok(corner in occ, f"{key}: corner {corner} not reached, check is vacuous")
    # a toppled megalith draws ONE bar over its two cells; a standing one a diamond
    bars = [s for s in spec["board"]["overlay"] if len(s) == 3]
    pairs = len({tuple(sorted((i, p))) for i, _, p in t.board if p >= 0})
    ok(len(bars) == pairs, f"{key}: {len(bars)} overlay bars for {pairs} "
                           f"toppled megaliths")
    ok(pairs >= 1, f"{key}: no toppled megalith in the render check (vacuous)")

# =========================================================================
# 10b. render() CONTENT, not just its dimensions
# =========================================================================
# Checking only that every `owner` is "in (RED, BLUE)" is vacuous: a global
# colour flip passes it, and in Carnac the bird's-eye colour map IS the score,
# so a flipped board is unreadable.  The owner of every square is therefore
# pinned to the RULEBOOK'S OWN FIGURE: each region the figure outlines must be
# drawn as one solid block of the colour the figure prints for it.
figspec = G.render(fig)
own = {p["cell"]: p["owner"] for p in figspec["pieces"]}
ok(all(p.get("shape") == "fill" for p in figspec["pieces"]),
   "every occupied square is flooded, so a dolmen reads as one block of colour")
for name, pairs in OUTLINED.items():
    want = RED if name.startswith("red") else BLUE
    ids = {M.cell_id(14, i) for i in fig_cells(pairs)}
    got = {own.get(c) for c in ids}
    ok(got == {want},
       f"render: the figure's outlined '{name}' must be drawn as one block of "
       f"{M.SEAT_NAMES[want]} (got owners {got})")
ok(sum(1 for v in own.values() if v == RED) == sum(r.count("R") for r in FIG)
   and sum(1 for v in own.values() if v == BLUE) == sum(r.count("B") for r in FIG),
   "render: the whole bird's-eye map matches the figure square for square")

# The orientation picker is what the placer reads BEFORE choosing, so each of
# its labels is pinned to what that choice ACTUALLY does on the board.
pick = G.render(G.initial_state())
cn = pick["choiceNames"]
ok(set(cn) == {"RR", "RB", "BR", "BB"}, f"the picker offers four orientations: {set(cn)}")
for k, label in cn.items():
    stp = G.apply_move(G.initial_state(), f"4,3={k}")
    stood = {p["cell"]: p["owner"] for p in G.render(stp)["pieces"]}["4,3"]
    ok(label.startswith(M.SEAT_NAMES[stood] + " up"),
       f"picker label {k!r} says {label!r} but standing it shows "
       f"{M.SEAT_NAMES[stood]}")
    layp = G.apply_move(stp, "4,3>4,4")                       # a NORTH topple
    nsc = {p["owner"] for p in G.render(layp)["pieces"]}
    ok(len(nsc) == 1, f"a toppled megalith shows one colour (got {nsc})")
    nsc = nsc.pop()
    i, j = label.index("N/S"), label.index("E/W")
    ns_part, ew_part = label[i:j], label[j:]
    ok(M.SEAT_NAMES[nsc] in ns_part and M.SEAT_NAMES[1 - nsc] not in ns_part,
       f"picker label {k!r}: the N/S arrow must name {M.SEAT_NAMES[nsc]}, the "
       f"colour a north topple really brings up ({label!r})")
    ok(M.SEAT_NAMES[1 - nsc] in ew_part and M.SEAT_NAMES[nsc] not in ew_part,
       f"picker label {k!r}: the E/W arrow must name the OTHER colour ({label!r})")

# The board's two cues: which stone is the decision about, and standing vs lying.
tipv = G.apply_move(G.initial_state(), "4,3=RB")
sptip = G.render(tipv)
hl = {h["cell"]: h["kind"] for h in sptip.get("highlights", [])}
ok(hl.get("4,3") == "goal",
   f"the stone awaiting the topple decision is marked on the board: {hl}")
dias = [s for s in sptip["board"]["overlay"] if len(s) == 6]
ok(len(dias) == 1 and dias[0][-1] == G.PEND and G.PEND != G.BAR,
   f"a standing menhir draws a diamond, GOLD while it can still be toppled: {dias}")
decl = G.apply_move(tipv, "pass")
dias = [s for s in G.render(decl)["board"]["overlay"] if len(s) == 6]
ok(len(dias) == 1 and dias[0][-1] == G.BAR,
   f"once the moment has passed the same menhir wears the dark diamond: {dias}")
layv = G.apply_move(tipv, "4,3>4,4")
spl = G.render(layv)
ok([len(s) for s in spl["board"]["overlay"]] == [3],
   f"a toppled menhir draws one bar and no diamond: {spl['board']['overlay']}")
ok({h["cell"]: h["kind"] for h in spl.get("highlights", [])}
   == {"4,4": "last-move", "4,5": "last-move"},
   f"the two squares it fell onto are the last-move highlight: {spl.get('highlights')}")

# =========================================================================
# 11. Captions, pinned to ground truth OUTSIDE the engine
# =========================================================================
# web/src/colors.js: SEAT_FILL[0] = '#d23b3b' (red), SEAT_FILL[1] = '#3b6fd2'
# (blue).  Seat 0 therefore IS the red player and seat 1 the blue one, and the
# rulebook's figure says its WHITE player -- our seat 1 -- wins.
ok(M.SEAT_NAMES == ("Red", "Blue"),
   f"seat 0 renders red and seat 1 blue (colors.js); got {M.SEAT_NAMES}")
cap = G.render(fig)["caption"]
ok(cap.startswith("Blue wins"),
   f'figure: the terminal caption must announce Blue (= the figure\'s "Weiss") '
   f"as the winner, got {cap!r}")
ok("Red wins" not in cap, f"figure: caption must NOT credit Red: {cap!r}")
ok("Red 5" in cap and "Blue 5" in cap,
   f"figure caption reports both tallies as 5: {cap!r}")

# A decisive position the OTHER way round, so a swapped winner cannot pass both.
redwin = build(["RRR.....", "........", "........", "........", "........"],
               8, 5, reserve=0)
ok(G.render(redwin)["caption"].startswith("Red wins"),
   f"Red's lone dolmen wins: {G.render(redwin)['caption']!r}")
ok(G.returns(redwin) == [1.0, -1.0], "and Red's payoff is +1")
ok(G.render(sp)["caption"].startswith("Draw"),
   f"a genuine tie captions as a Draw: {G.render(sp)['caption']!r}")

# The IN-PLAY caption names the seat actually on turn, in both phases and for
# both seats -- a `1 - to_move` mutant must fail here.
for seat, name in ((RED, "Red"), (BLUE, "Blue")):
    live = CState(w=10, h=7, board=(), reserve=10, phase="place", to_move=seat)
    c = G.render(live)["caption"]
    ok(c.startswith(f"{name} to move"),
       f"place-phase caption must name seat {seat} as {name}: {c!r}")
    ok(M.SEAT_NAMES[1 - seat] + " to move" not in c,
       f"place-phase caption names the wrong seat: {c!r}")
    tipst = CState(w=10, h=7, board=((idx(10, 4, 3), RED, -1),), reserve=10,
                   phase="tip", pend=(idx(10, 4, 3), RED, BLUE), to_move=seat)
    c = G.render(tipst)["caption"]
    ok(c.startswith(f"{name} to move") and "topple" in c and "e4" in c,
       f"tip-phase caption must name {name} and the stone on e4: {c!r}")
# The tally must be reported Red-first: an unequal position pins the order.
tally = build(["RRR.....", "........", "..BBB...", "..B.....", "..B....."],
              8, 5, reserve=4, to_move=RED)
tr, tb = G.scores(tally)
ok((len(tr), len(tb)) == (1, 1) and tr == (3,) and tb == (5,),
   f"tally premise: Red {tr}, Blue {tb}")
c = G.render(tally)["caption"]
ok("Red 1 (3)" in c and "Blue 1 (5)" in c,
   f"caption reports each seat's own dolmen sizes, Red first: {c!r}")
ok("stock 4" in c, f"caption reports the remaining stock: {c!r}")

# =========================================================================
# 12. Notation, and the deliberate absence of a heuristic
# =========================================================================
rng = random.Random(31)
for _ in range(6):
    t = G.initial_state(options={"board": "8x5"})
    while not G.is_terminal(t):
        for m in G.legal_moves(t):
            d = G.describe_move(t, m)
            ok(isinstance(d, str) and d, f"describe_move({m!r}) -> {d!r}")
        t = G.apply_move(t, rng.choice(G.legal_moves(t)))
s1 = G.apply_move(G.initial_state(), "4,3=RB")
ok(G.describe_move(G.initial_state(), "4,3=RB")
   == "stand e4 (Red up, N/S Blue, E/W Red)",
   f"placement notation: {G.describe_move(G.initial_state(), '4,3=RB')!r}")
ok(G.describe_move(s1, "4,3>4,4")
   == "topple e4 north onto e5-e6 (Blue up)",
   f"topple notation: {G.describe_move(s1, '4,3>4,4')!r}")
ok(G.describe_move(s1, "pass") == "leave e4 standing",
   f"pass notation: {G.describe_move(s1, 'pass')!r}")

# No heuristic is shipped, deliberately.  A game lasts at most 2*28-1 = 55
# plies while MCTSBot's default rollout budget is 50, so a rollout is cut off
# on 0.00% / 1.59% / 7.49% of plies over COMPLETE games (8x5 / 10x7 / 14x9,
# 400 games each) -- almost every rollout reaches a real terminal and is scored
# by returns(), which beats any eval.  This assertion exists so that "no
# heuristic" cannot silently become "a broken heuristic".
ok(not hasattr(G, "heuristic") or type(G).heuristic is M.Game.heuristic,
   "no heuristic is shipped (see the measurement above); if one is added it "
   "MUST return a list of 2 payoffs and be measured through MCTSBot")
# ... and the rollout cutoff really is harmless without one: max_rollout=4
# forces `_evaluate` on every rollout, which must not raise or return junk.
from agp.mcts import MCTSBot                                      # noqa: E402
for key in BOARDS:
    st = G.initial_state(options={"board": key})
    mv = MCTSBot(random.Random(5), iterations=20, max_rollout=4).select(G, st)
    ok(mv in G.legal_moves(st),
       f"{key}: MCTSBot with max_rollout=4 (forcing the cutoff) returns a "
       f"legal move (got {mv!r})")

print(f"carnac selftest: {len(FAILS)} failure(s)")
if FAILS:
    sys.exit(1)
