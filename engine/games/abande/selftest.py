#!/usr/bin/env python3
"""Abande selftest -- correctness anchors, pure stdlib.

The strongest anchors are the SIX worked positions PUBLISHED IN THE DESIGNER'S
OWN RULES, each reconstructed from its diagram and checked against the prose
that accompanies it.

From https://spielstein.com/games/abande/rules (figures `enter.png`,
`capture.png`, `finished.png`) -- all hexagonal:

  * figure "enter"    -- the exact set of 11 legal entry points for a given band;
  * figure "capture"  -- the exact 5 legal captures for White and 5 for Black,
                         including the two stacks that may NOT move because
                         moving them would split the band;
  * figure "finished" -- the scored final position, "White 13 - Black 15",
                         which pins the sleeping-stack rule and the
                         score-by-height rule at once.

From the designer's own PDF, "Abande - Rules of Play", (c) 2005 Dieter Stein
(same "This version: December 30, 2005"; mirrored at
https://superdupergames.org/rules/abande.pdf), whose figures the web page has
since dropped or replaced:

  * the "Entering a New Piece" figure on the ORTHOGONAL 7x7 board -- 14 legal
    entry points, the only published anchor for the default board's 8-neighbour
    geometry;
  * the SECOND capture example, also orthogonal -- "There is only one possible
    capture for White: c3-d4 ... Possible captures for Black: e2-e3 and f3-e3.
    The piece on d4 cannot capture at c3 or e3, as this would split the band."
    The web page keeps this prose but strips the diagram; without the PDF the
    position is unrecoverable, and it is the only published check of the
    connectivity-on-a-move rule on the default board;
  * a SECOND scored final position, "Black wins the game by 12-15 points" --
    a different position from `finished.png`, reprinted in the published
    nestorgames edition (https://nestorgames.com/rulebooks/ABANDE_EN.pdf,
    rule book (c) 2009 Nestor Romeral Andres), which re-derives the same
    sleeping/height rules from scratch on 21 stacks instead of 22.

Everything else (opening move counts, the height cap, the movement lock, pass
legality, termination, serialization) is checked constructively.  The
move-for-move differential against the AbstractPlay `gameslib` oracle lives in
`_diff_ap.py` (manual; needs node).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                        # noqa: E402

HERE = Path(__file__).resolve().parent
MAN, GAME = load_from_dir(HERE)
# Resolve the LIVE module object (load_from_dir imports game.py under a
# synthetic name, so `import games.abande.game` would be a different module).
G = sys.modules[type(GAME).__module__]

BLACK, WHITE = G.BLACK, G.WHITE
ok = 0


def check(cond, what):
    global ok
    if not cond:
        raise AssertionError(what)
    ok += 1


# ---------------------------------------------------------------- geometry --
def from_name(kind, name):
    """Algebraic cell name -> cell tuple.  Written independently of
    game.cell_name and cross-checked against it below, so a coordinate-mapping
    error cannot make the published-position anchors pass vacuously."""
    letter = ord(name[0]) - ord("a")
    num = int(name[1:])
    if kind == "square":
        return (letter, num - 1)
    r = 3 - letter
    qmin = max(-3, -3 - r)
    return (qmin + num - 1, r)


def names(kind, cells):
    return sorted(G.cell_name(kind, c) for c in cells)


for kind in ("square", "hex"):
    cells, adj = G.BOARDS[kind]
    # cell_name and from_name are mutual inverses over the whole board
    for c in cells:
        check(from_name(kind, G.cell_name(kind, c)) == c,
              f"{kind}: name round-trip for {c}")
    check(len({G.cell_name(kind, c) for c in cells}) == len(cells),
          f"{kind}: cell names unique")

check(len(G.BOARDS["square"][0]) == 49, "square board has 49 points")
check(len(G.BOARDS["hex"][0]) == 37, "hex board has 37 points")
# "There are up to 8 connections on a square board, ... up to 6 connections on
# a hexagonal board" -- official rules.
check(max(len(v) for v in G.BOARDS["square"][1].values()) == 8, "square degree 8")
check(max(len(v) for v in G.BOARDS["hex"][1].values()) == 6, "hex degree 6")
check(len(G.BOARDS["square"][1][(0, 0)]) == 3, "square corner degree 3")
check(len(G.BOARDS["hex"][1][from_name("hex", "a1")]) == 3, "hex corner degree 3")
# printed row widths of the hexagonal board: a4 b5 c6 d7 e6 f5 g4
widths = {}
for c in G.BOARDS["hex"][0]:
    widths.setdefault(G.cell_name("hex", c)[0], 0)
    widths[G.cell_name("hex", c)[0]] += 1
check(widths == {"a": 4, "b": 5, "c": 6, "d": 7, "e": 6, "f": 5, "g": 4},
      f"hex row widths {widths}")

# ------------------------------------------------------------ opening moves --
# Reproduces the AbstractPlay oracle's opening move counts exactly.
check(len(GAME.legal_moves(GAME.initial_state())) == 49, "square opening = 49")
check(len(GAME.legal_moves(GAME.initial_state({"board": "hex"}))) == 37,
      "hex opening = 37")
check(GAME.initial_state().hands == (18, 18), "18 pieces each")


# ------------------------------------------------------------- state helper --
def pos(kind, board, to_move, hands=(0, 0), passes=0, ply=40):
    """Build a state from {algebraic: 'owners bottom->top'} where owners are
    'B'/'W' characters."""
    b = {}
    for name, col in board.items():
        b[from_name(kind, name)] = tuple(BLACK if ch == "B" else WHITE for ch in col)
    return G.AbState(kind=kind, board=b, hands=hands, to_move=to_move,
                     passes=passes, ply=ply, last=None)


def caps(state):
    return sorted(m for m in GAME.legal_moves(state) if ">" in m)


def cap_names(state):
    kind = state.kind
    out = []
    for m in caps(state):
        a, b = m.split(">")
        out.append(f"{G.cell_name(kind, G._cell(a))}-{G.cell_name(kind, G._cell(b))}")
    return sorted(out)


# ------------------------------------- PUBLISHED FIGURE "enter" (placement) --
# Band = f3(W) e4(B) d4(B) d5(W); the figure marks 11 legal entry points.
ENTER = {"f3": "W", "e4": "B", "d4": "B", "d5": "W"}
st = pos("hex", ENTER, BLACK, hands=(16, 16))
placed = sorted(G.cell_name("hex", G._cell(m[2:]))
                for m in GAME.legal_moves(st) if m.startswith("P@"))
EXPECT_ENTER = sorted(["g2", "g3", "f2", "f4", "e3", "e5", "d3", "d6",
                       "c3", "c4", "c5"])
check(placed == EXPECT_ENTER, f"figure 'enter' placements: {placed}")
check(len(placed) == 11, "figure 'enter' = 11 entry points")

# ------------------------------------- PUBLISHED FIGURE "capture" (moving) ---
# White: e2 e4 f2 c4 (singles).  Black: d3 d4 b3 (singles) and e3 = a
# 2-stack (White under Black).  The rules list the complete capture lists.
CAPTURE = {"e2": "W", "e4": "W", "f2": "W", "c4": "W",
           "d3": "B", "d4": "B", "b3": "B", "e3": "WB"}
w = pos("hex", CAPTURE, WHITE, hands=(0, 0))
b = pos("hex", CAPTURE, BLACK, hands=(0, 0))
check(cap_names(w) == sorted(["e2-d3", "e2-e3", "e4-d4", "e4-e3", "f2-e3"]),
      f"figure 'capture' White: {cap_names(w)}")
check(cap_names(b) == sorted(["b3-c4", "d3-e2", "e3-e2", "e3-e4", "e3-f2"]),
      f"figure 'capture' Black: {cap_names(b)}")
# "The pieces on c4 and d4 cannot be moved because that would split the band."
check(not any(m.startswith("c4-") for m in cap_names(w)), "c4 frozen (band)")
check(not any(m.startswith("d4-") for m in cap_names(b)), "d4 frozen (band)")
# ...and they are frozen by CONNECTIVITY, not by anything else: both have
# adjacent enemy stacks of legal combined height.
adjh = G.BOARDS["hex"][1]
c4, d4 = from_name("hex", "c4"), from_name("hex", "d4")
check(any(n in w.board and w.board[n][-1] == BLACK for n in adjh[c4]),
      "c4 does have an adjacent enemy stack")
check(any(n in b.board and b.board[n][-1] == WHITE for n in adjh[d4]),
      "d4 does have an adjacent enemy stack")
# the whole capture-figure band really is one band
check(GAME._connected(w.board, adjh), "figure 'capture' band is connected")
# and the moving stack carries its whole column ("the complete stack on e3 is
# moved"): e3 (height 2) landing on a single makes a 3-stack, and e3 vacates.
after = GAME.apply_move(b, "%d,%d>%d,%d" % (from_name("hex", "e3") +
                                            from_name("hex", "e4")))
check(from_name("hex", "e3") not in after.board, "e3 vacated by its stack move")
check(len(after.board[from_name("hex", "e4")]) == 3, "e3 stack lands whole")
check(after.board[from_name("hex", "e4")] == (WHITE, WHITE, BLACK),
      "landing keeps piece order, mover on top")

# --------------------------- PUBLISHED FIGURE "finished" (score 13 - 15) -----
# Reconstructed from the diagram; every stack's printed value is its height
# (0 = "sleeping", i.e. touching no enemy-controlled stack).  Composition is
# bottom->top.
FINISHED = {
    "g4": "B", "f4": "B", "f5": "B",
    "e2": "WBW", "e3": "BWB", "e4": "W",
    "d1": "WB", "d3": "B", "d4": "BBW", "d5": "B", "d6": "W", "d7": "B",
    "c1": "B", "c2": "WWB", "c3": "B", "c4": "BW",
    "b1": "W", "b2": "WWB", "b4": "W", "b5": "WBW",
    "a1": "W", "a2": "W",
}
fin = pos("hex", FINISHED, BLACK, hands=(0, 0), passes=2)
# 18 pieces of each colour are accounted for -- the reconstruction is complete
allpieces = [o for col in fin.board.values() for o in col]
check(allpieces.count(BLACK) == 18 and allpieces.count(WHITE) == 18,
      "figure 'finished' uses all 36 pieces")
check(GAME._connected(fin.board, adjh), "figure 'finished' band is connected")
check(GAME.scores(fin) == (15, 13),
      f"figure 'finished' score should be Black 15 - White 13, got {GAME.scores(fin)}")
# Each stack in the diagram carries its point value.  PRINTED is that value;
# the awake ones must equal the drawn stack HEIGHT, so this pins the
# reconstruction stack-by-stack (independent of any rule) and, together with
# the published 15-13 caption above, pins the scoring rule.
PRINTED = {"g4": 0, "f4": 1, "f5": 0, "e2": 3, "e3": 3, "e4": 1, "d1": 0,
           "d3": 1, "d4": 3, "d5": 1, "d6": 1, "d7": 1, "c1": 1, "c2": 3,
           "c3": 1, "c4": 2, "b1": 1, "b2": 3, "b4": 0, "b5": 0, "a1": 1,
           "a2": 1}
SLEEPING = ["g4", "f5", "d1", "b4", "b5"]      # the five stacks printed "0"
for nm, val in PRINTED.items():
    if nm not in SLEEPING:
        check(len(fin.board[from_name("hex", nm)]) == val,
              f"figure 'finished': {nm} is drawn {val} high")
for p, tot in ((BLACK, 15), (WHITE, 13)):
    check(sum(PRINTED[nm] for nm in PRINTED
              if fin.board[from_name("hex", nm)][-1] == p) == tot,
          f"printed values sum to {tot} for seat {p}")
    check(GAME.score(fin, p) == tot, f"engine scores {tot} for seat {p}")
check(sorted(nm for nm in PRINTED if PRINTED[nm] == 0) == sorted(SLEEPING),
      "the diagram's zero-valued stacks are the five listed")
# Dropping the five sleeping stacks from the position leaves both scores
# unchanged -- the rules' own "you may remove them to make scoring easier".
pruned = pos("hex", {nm: col for nm, col in FINISHED.items()
                     if nm not in SLEEPING}, BLACK, hands=(0, 0), passes=2)
check(GAME.scores(pruned) == (15, 13),
      f"removing sleeping stacks does not change the score: {GAME.scores(pruned)}")
check(GAME.is_terminal(fin) and GAME.returns(fin) == [1.0, -1.0],
      "figure 'finished' is a Black win")
# the five stacks the diagram marks "0" are exactly the sleeping ones
sleeping = sorted(G.cell_name("hex", c) for c, col in fin.board.items()
                  if not any(n in fin.board and fin.board[n][-1] != col[-1]
                             for n in adjh[c]))
check(sleeping == sorted(["g4", "f5", "d1", "b4", "b5"]),
      f"figure 'finished' sleeping stacks: {sleeping}")
# per-player: a sleeping stack scores 0 no matter how tall (b5 is 3 high)
check(len(fin.board[from_name("hex", "b5")]) == 3, "b5 is a 3-stack")

# ============================================================================
# A SECOND, INDEPENDENT SET OF PUBLISHED ANCHORS
#
# The designer's own PDF "Abande - Rules of Play" (Copyright (c) 2005 Dieter
# Stein, same "This version: December 30, 2005" as the web page; mirrored at
# https://superdupergames.org/rules/abande.pdf) and the nestorgames rulebook
# (https://nestorgames.com/rulebooks/ABANDE_EN.pdf, rule book (c) 2009 Nestor
# Romeral Andres, rules (c) 2005 Dieter Stein) carry figures the current web
# page does NOT: two worked positions on the ORTHOGONAL 7x7 board (the web page
# only ever illustrates the hexagonal one) and a DIFFERENT scored final
# position.  They pin the square board's 8-neighbour geometry and its
# connectivity rule against published move lists, which nothing else here does.
# ============================================================================

# ---- Stein 2005 PDF, "Entering a New Piece" figure (ORTHOGONAL board) -------
# Band = d4(B) d3(W) e2(B); the figure marks the legal entry points in green.
PDF_ENTER = {"d4": "B", "d3": "W", "e2": "B"}
sq = pos("square", PDF_ENTER, BLACK, hands=(15, 16))
sq_placed = sorted(G.cell_name("square", G._cell(m[2:]))
                   for m in GAME.legal_moves(sq) if m.startswith("P@"))
PDF_ENTER_EXPECT = sorted(["c2", "c3", "c4", "c5", "d1", "d2", "d5",
                           "e1", "e3", "e4", "e5", "f1", "f2", "f3"])
check(sq_placed == PDF_ENTER_EXPECT, f"PDF square 'enter' figure: {sq_placed}")
check(len(sq_placed) == 14, "PDF square 'enter' figure = 14 entry points")

# ---- Stein 2005 PDF, the SECOND capture example (ORTHOGONAL board) ----------
# "There is only one possible capture for White: c3-d4, the stack on e3 cannot
#  move.  Possible captures for Black in the same position: e2-e3 and f3-e3.
#  The piece on d4 cannot capture at c3 or e3, as this would split the band."
# (This example is text-only on the current web page -- its diagram survives
# only in the PDF, where the position is a 7x7 orthogonal board.)
PDF_CAP2 = {"d4": "B", "c3": "W", "e3": "BW", "f3": "B", "e2": "B"}
w2 = pos("square", PDF_CAP2, WHITE, hands=(0, 0))
b2 = pos("square", PDF_CAP2, BLACK, hands=(0, 0))
check(GAME._connected(w2.board, G.BOARDS["square"][1]),
      "PDF square capture figure is one band")
check(cap_names(w2) == ["c3-d4"], f"PDF square: White's only capture: {cap_names(w2)}")
check(cap_names(b2) == sorted(["e2-e3", "f3-e3"]),
      f"PDF square: Black's captures: {cap_names(b2)}")
# ...and the exclusions are BAND exclusions, not height/target ones: the white
# 2-stack on e3 and the black piece on d4 both have adjacent enemy stacks of
# legal combined height, yet neither may move.
adjs = G.BOARDS["square"][1]
e3s, d4s = from_name("square", "e3"), from_name("square", "d4")
check(len(w2.board[e3s]) == 2 and w2.board[e3s][-1] == WHITE, "e3 is a White 2-stack")
check(any(n in w2.board and w2.board[n][-1] == BLACK and len(w2.board[n]) + 2 <= 3
          for n in adjs[e3s]), "e3 does have a legal-height enemy neighbour")
check(not any(m.startswith("e3-") for m in cap_names(w2)), "e3 frozen (band)")
check(any(n in b2.board and b2.board[n][-1] == WHITE for n in adjs[d4s]),
      "d4 does have an adjacent enemy stack")
check(not any(m.startswith("d4-") for m in cap_names(b2)), "d4 frozen (band)")

# ---- Stein 2005 PDF / nestorgames 2009, the scored final position -----------
# "In the above hexagonal example Black wins the game by 12-15 points."  This is
# a DIFFERENT position from the web page's 13-15 figure, so it is a genuinely
# independent test of the same two rules (score = height, sleeping = no adjacent
# enemy-controlled stack).  Six stacks carry the "sleeping" dot.
PDF_FINISHED = {
    "g1": "B", "g4": "B",
    "f2": "W", "f5": "WB",
    "e3": "WB", "e4": "W", "e5": "BW", "e6": "BW",
    "d1": "W", "d3": "B", "d4": "BWB", "d5": "W", "d6": "BBW",
    "c1": "B", "c4": "BBW", "c5": "W",
    "b1": "WB", "b3": "WWB",
    "a1": "B", "a2": "WWB", "a3": "W",
}
pfin = pos("hex", PDF_FINISHED, BLACK, hands=(0, 0), passes=2)
pf_all = [o for col in pfin.board.values() for o in col]
check(pf_all.count(BLACK) == 18 and pf_all.count(WHITE) == 18,
      "PDF 'finished' figure uses all 36 pieces")
check(len(pfin.board) == 21, "PDF 'finished' figure has 21 stacks")
check(GAME._connected(pfin.board, adjh), "PDF 'finished' band is connected")
check(GAME.scores(pfin) == (15, 12),
      f"PDF 'finished' should be Black 15 - White 12, got {GAME.scores(pfin)}")
PDF_SLEEPING = sorted(["a1", "b1", "c5", "d3", "d6", "g4"])
pf_sleep = sorted(G.cell_name("hex", c) for c, col in pfin.board.items()
                  if not any(n in pfin.board and pfin.board[n][-1] != col[-1]
                             for n in adjh[c]))
check(pf_sleep == PDF_SLEEPING, f"PDF 'finished' sleeping stacks: {pf_sleep}")
# the sleeping set is not trivial: it holds stacks of every height, of both
# colours, and leaving them in changes nobody's score.
check({len(pfin.board[from_name("hex", nm)]) for nm in PDF_SLEEPING} == {1, 2, 3},
      "the PDF's sleeping stacks span heights 1-3")
check({pfin.board[from_name("hex", nm)][-1] for nm in PDF_SLEEPING} == {BLACK, WHITE},
      "the PDF's sleeping stacks include both colours")
check(GAME.scores(pos("hex", {nm: col for nm, col in PDF_FINISHED.items()
                             if nm not in PDF_SLEEPING},
                      BLACK, hands=(0, 0), passes=2)) == (15, 12),
      "removing the PDF's sleeping stacks does not change the score")
check(GAME.is_terminal(pfin) and GAME.returns(pfin) == [1.0, -1.0],
      "PDF 'finished' is a Black win")

# ------------------------------------------------------- height cap (max 3) --
# A 2-stack may land on a single (3) but not on another 2-stack (4).
cap_pos = pos("square", {"c3": "WB", "d3": "BW", "d4": "W"}, BLACK)
mv = cap_names(cap_pos)
check("c3-d3" not in mv, f"2+2 > 3 is illegal ({mv})")
check(mv == ["c3-d4"], f"2+1 = 3 is legal ({mv})")
check(all(len(GAME.apply_move(cap_pos, m).board[G._cell(m.split('>')[1])]) <= 3
          for m in caps(cap_pos)), "no stack ever exceeds 3")

# ------------------------------------------ never onto empty / onto friendly --
tgt = pos("square", {"c3": "B", "c4": "B", "d3": "W"}, BLACK)
check(cap_names(tgt) == ["c3-d3", "c4-d3"], f"only enemy targets: {cap_names(tgt)}")
# generic: every generated stack move lands on an enemy-topped stack
for st_ in (tgt, w, b, cap_pos):
    for m in caps(st_):
        src, dst = G._cell(m.split(">")[0]), G._cell(m.split(">")[1])
        check(dst in st_.board, "a stack move never lands on an empty space")
        check(st_.board[dst][-1] != st_.board[src][-1],
              "a stack move never lands on a friendly stack")
        check(st_.board[src][-1] == st_.to_move, "you only move stacks you control")

# ------------------------------------------------ connectivity on a movement --
# A stack move that would split the band is illegal (also proved by the
# published 'capture' figure above; here is a minimal chain a3 b3 c3 d3).
chain = pos("square", {"a3": "B", "b3": "W", "c3": "B", "d3": "W"}, BLACK)
# Only a3-b3 keeps the band whole: c3-d3 would strand a3+b3 from d3, and
# c3-b3 would strand d3.  Without the connectivity rule all three are legal.
check(cap_names(chain) == ["a3-b3"], f"chain captures: {cap_names(chain)}")

# ----------------------------------------------------- the movement lockout --
# "Moving is allowed only after Black has entered the second piece."
s = GAME.initial_state()
seq = []
for mv_ in ["P@3,3", "P@3,4", "P@2,3"]:            # B, W, B
    check(all(">" not in m for m in GAME.legal_moves(s)),
          f"no stack moves before Black's 2nd piece (ply {s.ply})")
    s = GAME.apply_move(s, mv_)
    seq.append(mv_)
check(any(">" in m for m in GAME.legal_moves(s)),
      "stack moves unlock once Black has entered 2 pieces")
check(s.hands == (16, 17), f"hands after B,W,B = {s.hands}")

# --------------------------------------------------------------- pass rules --
withhand = pos("square", {"c3": "B", "d3": "W"}, BLACK, hands=(5, 5))
check("pass" not in GAME.legal_moves(withhand), "cannot pass holding pieces")
empty = pos("square", {"c3": "B", "d3": "W"}, BLACK, hands=(0, 0))
lm = GAME.legal_moves(empty)
check("pass" in lm, "may pass with an empty hand")
check("2,2>3,2" in lm, "passing is optional -- captures still offered")
check(not GAME.is_terminal(empty), "one pass does not end the game")
p1 = GAME.apply_move(empty, "pass")
check(not GAME.is_terminal(p1) and p1.passes == 1, "one pass pending")
p2 = GAME.apply_move(p1, "pass")
check(GAME.is_terminal(p2) and p2.passes == 2, "two passes end the game")
# a non-pass resets the counter
p1b = GAME.apply_move(p1, "3,2>2,2")
check(p1b.passes == 0, "a move resets the pass counter")
check(not GAME.is_terminal(GAME.apply_move(p1b, "pass")), "pass streak reset")

# ---------------------------------------------------- honest draw / scoring --
tie = pos("square", {"c3": "B", "d3": "W"}, BLACK, hands=(0, 0), passes=2)
check(GAME.scores(tie) == (1, 1) and GAME.returns(tie) == [0.0, 0.0],
      "an equal score is an honest draw")
lone = pos("square", {"c3": "B", "b3": "B"}, BLACK, hands=(0, 0), passes=2)
check(GAME.scores(lone) == (0, 0) and GAME.returns(lone) == [0.0, 0.0],
      "stacks touching no enemy score nothing")
tall = pos("square", {"c3": "WWB", "d3": "W"}, BLACK, hands=(0, 0), passes=2)
check(GAME.scores(tall) == (3, 1), "a triple scores 3, a single 1")

# ------------------------------------------------------------- purity / IO ---
base = pos("hex", CAPTURE, WHITE, hands=(3, 4))
snap = GAME.serialize(base)
for m in GAME.legal_moves(base):
    GAME.apply_move(base, m)
check(GAME.serialize(base) == snap, "apply_move does not mutate its input")
# serialize/deserialize must round-trip EVERY field.  Comparing
# serialize(deserialize(d)) == d is NOT enough: deserialize() reads the optional
# fields with .get(..., default), so a field DROPPED from serialize() would be
# re-defaulted and re-omitted, and the comparison would still pass (a dropped
# `passes` would silently make async matches unendable).  Compare the STATES.
SER_KEYS = {"kind", "board", "hands", "to_move", "passes", "ply", "last"}
rt_rng = random.Random(2005)
rt_last = set()
for kind in ("square", "hex"):
    seen_states = 0
    s = GAME.initial_state({"board": kind})
    while True:
        d = GAME.serialize(s)
        check(set(d) == SER_KEYS, f"{kind}: serialize emits exactly {SER_KEYS}, got {set(d)}")
        check(GAME.deserialize(d) == s, f"{kind}: serialize/deserialize round-trips the STATE")
        check(GAME.serialize(GAME.deserialize(d)) == d, f"{kind}: serialize round-trips")
        rt_last.add("none" if s.last is None
                    else ("place" if s.last[0] is None else "move"))
        seen_states += 1
        if GAME.is_terminal(s):
            break
        s = GAME.apply_move(s, rt_rng.choice(GAME.legal_moves(s)))
    check(seen_states > 30, f"{kind}: round-trip sweep covered a whole game")
    check(GAME.deserialize(GAME.serialize(s)).kind == kind,
          f"{kind}: board kind survives a round trip")
# ...and the sweep really did cover all three shapes of `last` (None / a
# placement / a stack move), so none of them can round-trip vacuously.
check(rt_last == {"none", "place", "move"}, f"round-trip covered last={rt_last}")
check(GAME.describe_move(base, "pass") == "pass", "describe pass")
mvx = "%d,%d>%d,%d" % (from_name("hex", "e2") + from_name("hex", "e3"))
check(GAME.describe_move(base, mvx) == "e2-e3 (3)", GAME.describe_move(base, mvx))
check(GAME.describe_move(base, "P@0,0") == "d4", GAME.describe_move(base, "P@0,0"))

# --------------------------------------------------------------- render ------
for kind in ("square", "hex"):
    spec = GAME.render(pos(kind, {}, BLACK, hands=(18, 18), ply=0))
    check(spec["board"]["type"] == ("hex" if kind == "hex" else "square"),
          f"{kind}: board type")
    check(spec["reserve"] == {"0": {"P": 18}, "1": {"P": 18}}, "reserve tray")
spec = GAME.render(fin)
check(all(p["owner"] == p["stack"][-1] for p in spec["pieces"]),
      "render: owner is the top of the stack")
check(len(spec["pieces"]) == 22, "render: 22 stacks in the finished figure")

# ------------------------------------------------------ termination / cap ----
rng = random.Random(20050908)
maxply = 0
draws = 0
kinds = {"square": 0, "hex": 0}
for i in range(220):
    kind = "hex" if i % 2 else "square"
    s = GAME.initial_state({"board": kind})
    while not GAME.is_terminal(s):
        lm = GAME.legal_moves(s)
        check(lm, "legal_moves non-empty on a non-terminal state")
        if s.hands[s.to_move] > 0:
            # holding pieces you are never stuck, and never allowed to pass
            check(any(m.startswith("P@") for m in lm), "an entry is always available")
            check("pass" not in lm, "no passing while holding pieces")
        else:
            check("pass" in lm, "passing is always available with an empty hand")
        s = GAME.apply_move(s, rng.choice(lm))
    check(s.passes == 2, "random games end by a double pass, never by the ply cap")
    check(s.hands == (0, 0), "both hands empty at the end")
    r = GAME.returns(s)
    check(len(r) == 2 and abs(r[0] + r[1]) < 1e-9, "returns are zero-sum")
    draws += (r == [0.0, 0.0])
    maxply = max(maxply, s.ply)
    kinds[kind] += 1
check(maxply < G.PLY_CAP,
      f"random games stay under the ply cap ({maxply} < {G.PLY_CAP})")
check(maxply <= 122, f"observed max ply {maxply} within the proved bound 122")
# The ply cap is a backstop, never a verdict.  Abande's result is a pure
# function of the FINAL POSITION (there is no "win as event" and no draw-by-
# counter), so tripping any counter can neither manufacture a draw nor erase a
# decisive result.  Assert it anyway -- "a draw counter checked before the real
# outcome" is the bug that has recurred 9x elsewhere in this library, and this
# is the assertion that would catch it if scoring ever grew such a branch.
import dataclasses as _dc                                   # noqa: E402
decisive = s                       # the last random game above, played to its end
while GAME.returns(decisive) == [0.0, 0.0]:                  # want a decisive one
    decisive = GAME.initial_state({"board": "hex"})
    while not GAME.is_terminal(decisive):
        decisive = GAME.apply_move(decisive, rng.choice(GAME.legal_moves(decisive)))
want = GAME.returns(decisive)
check(want != [0.0, 0.0], "found a decisive finished position")
for tripped in (_dc.replace(decisive, ply=G.PLY_CAP),
                _dc.replace(decisive, ply=10 ** 9),
                _dc.replace(decisive, passes=99)):
    check(GAME.is_terminal(tripped), "a tripped counter is still terminal")
    check(GAME.returns(tripped) == want,
          "a decisive result outranks every draw/limit counter")
    check(GAME.scores(tripped) == GAME.scores(decisive),
          "the score does not depend on how the game ended")
# ...and the cap really is the thing being tested: shrink it on the LIVE module
# and the same random game now stops early (so the assertions above are not
# passing merely because PLY_CAP is unreachable in this file).
_real_cap = G.PLY_CAP
try:
    G.PLY_CAP = 6
    probe = GAME.initial_state()
    while not GAME.is_terminal(probe):
        probe = GAME.apply_move(probe, rng.choice(GAME.legal_moves(probe)))
    check(probe.ply == 6 and probe.passes < 2,
          f"patching PLY_CAP bites (ply {probe.ply}, passes {probe.passes})")
    check(GAME.legal_moves(probe) == [], "a capped state offers no moves")
finally:
    G.PLY_CAP = _real_cap
check(G.PLY_CAP == 200, "PLY_CAP restored")

# --------------------------------------------------------------- heuristic ---
h = GAME.heuristic(fin)
check(isinstance(h, list) and len(h) == 2 and h[0] == -h[1], f"heuristic shape {h}")
h0 = GAME.heuristic(GAME.initial_state())
check(h0[0] == 0.0 and h0[1] == 0.0, f"empty board is even, got {h0}")
check(GAME.heuristic(fin)[0] > 0, "Black ahead => positive for Black")
from agp.mcts import MCTSBot                                # noqa: E402
# force the rollout cutoff so the heuristic path actually fires
st0 = GAME.initial_state()
for mv_ in ["P@3,3", "P@3,4", "P@2,3", "P@2,4"]:
    st0 = GAME.apply_move(st0, mv_)
pick = MCTSBot(random.Random(1), iterations=40, max_rollout=4).select(GAME, st0)
check(pick in GAME.legal_moves(st0), "MCTS with max_rollout=4 returns a legal move")

print(f"abande selftest OK -- {ok} assertions; "
      f"{sum(kinds.values())} random games ({kinds['square']} square / "
      f"{kinds['hex']} hex), max {maxply} plies (cap {G.PLY_CAP}), {draws} draws")
