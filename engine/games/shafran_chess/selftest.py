"""Selftest for Shafran's Hexagonal Chess (pure stdlib; run from engine/):

    PYTHONPATH=. python3 games/shafran_chess/selftest.py

Correctness anchors
-------------------
1. PERFT from the initial position: 42 / 1,706 / 75,494 (depths 1-3). No
   published Shafran perft series exists, so these were frozen after two
   one-time cross-checks (2026-07-25, not rerun here):
     * the JOCLY reference model (AGPL, read as an oracle only) -- its own board
       geometry, the complete per-cell target graphs of all 11 piece types, the
       starting array, the promotion table and the castling tables: 0 mismatches
       over all 70 cells;
     * a from-scratch reimplementation in file/rank (not axial) coordinates,
       driven in lockstep over 89,303 positions from random games,
       en-passant-biased games and randomly constructed positions (including
       9,700+ with live castling rights and 2,300+ with a live en-passant
       right): 0 legal-move-set mismatches, and equal perft to depth 3.
   Perft(4) from this package is 3,310,230 (too slow for the suite).
   Depth 1 = 42 is also hand-derived: 19 pawn moves (1+2+2+3+3+3+2+2+1 by file),
   7 knight (Nb1: a3 c4 d4 e3; Ng3: e4 f5 h6), 12 bishop (4 each from c1/f2/h4),
   4 queen (d1: e3 f5 g7 xh9), 0 king, 0 rook.
2. Wikipedia's en-passant study on the black d8 pawn, all four lines.
3. Wikipedia's castling diagram: black Q-0-0-0 to h10 and B-0-0 to c8, plus the
   other two castlings and the standard restrictions.
4. The variable-length first move per file, the no-leaping rule, promotion
   cells and choices, checkmate, stalemate = DRAW, threefold, 50-move.
5. A proof by exhaustion that "on its first move" == "standing on its own
   starting cell" (no pawn can ever re-enter a starting cell).
6. Duniho's own en-passant diagram, and the material the *Junyj texnik* report
   published (via Derzhanski): sample games #1 ("Kindermatt", mate in 3), #3
   (59 half-moves) and #4 (44 half-moves, including a real 6. Q-0-0-0 and a
   final mate), E. A. Baum's eight checkmating studies, and the Rostovcev /
   Rudenko problems #1, #3 and #5 with every printed line.  Problem #3's
   printed key "1. Kd7-c10" names a cell that does not exist; the unique key
   is 1. Kd7-c8 (see rules.md for the two other transcription errata).
7. Derzhanski's structural counts: three cell colours 23/23/24, two corners of
   each colour; and short castling as "the opposite procedure".
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
cell_name = mod.cell_name
WHITE, BLACK = mod.WHITE, mod.BLACK
ORTHO, DIAG, KNIGHT = mod.ORTHO, mod.DIAG, mod.KNIGHT

t0 = time.time()
checks = 0


def ok(cond, msg):
    global checks
    assert cond, msg
    checks += 1


AX = {cell_name(c): c for c in mod.CELLS}


def mv(frm_name, to_name, promo=None):
    q1, r1 = AX[frm_name]
    q2, r2 = AX[to_name]
    return f"{q1},{r1}>{q2},{r2}" + (f"={promo}" if promo else "")


def state(white, black, to_move=WHITE, halfmove=0, castling=(), ep=None):
    board = {}
    for nm, letter in white.items():
        q, r = AX[nm]
        board[f"{q},{r}"] = [WHITE, letter]
    for nm, letter in black.items():
        q, r = AX[nm]
        board[f"{q},{r}"] = [BLACK, letter]
    ep_s = None
    if ep is not None:
        pawn, crossed = ep
        ep_s = [f"{AX[pawn][0]},{AX[pawn][1]}"] + \
               [f"{AX[c][0]},{AX[c][1]}" for c in crossed]
    return g.deserialize({"board": board, "to_move": to_move, "ep": ep_s,
                          "castling": list(castling), "halfmove": halfmove,
                          "ply": 0, "reps": {}, "last": None})


def labels(s):
    return sorted(g.describe_move(s, x) for x in g.legal_moves(s))


# --- board geometry ---------------------------------------------------------
ok(len(mod.CELLS) == 70, "70 cells")
lens = {mod.FILES[q + 4]: mod._file_len(q) for q in range(-4, 5)}
ok(lens == {"a": 6, "b": 7, "c": 8, "d": 9, "e": 10, "f": 9, "g": 8, "h": 7,
            "i": 6}, f"file lengths {lens}")
# the six sides of the irregular hexagon: 5,5,6,5,5,6
ok(len([c for c in mod.CELLS if c[1] == 4]) == 5, "bottom-left side a1-e1 = 5")
ok(len([c for c in mod.CELLS if c[0] + c[1] == 4]) == 5, "bottom-right e1-i5 = 5")
ok(len([c for c in mod.CELLS if c[0] == 4]) == 6, "right side i5-i10 = 6")
ok(len([c for c in mod.CELLS if c[1] == -5]) == 5, "top-right e10-i10 = 5")
ok(len([c for c in mod.CELLS if c[0] + c[1] == -5]) == 5, "top-left a6-e10 = 5")
ok(len([c for c in mod.CELLS if c[0] == -4]) == 6, "left side a1-a6 = 6")
# notation round-trip, and the landmark cells of Duniho's description
ok(AX["a1"] == (-4, 4) and AX["e1"] == (0, 4) and AX["i5"] == (4, 0), "rank 1 map")
ok(AX["e10"] == (0, -5) and AX["a6"] == (-4, -1) and AX["i10"] == (4, -5), "rank 10")
ok("f1" not in AX, "f1 is NOT a cell (Duniho's 'Bishop on f1' is a typo for f2)")
ok(all(cell_name(c) in AX for c in mod.CELLS), "names round-trip")
# a rank runs SE; a file runs N; e1-f2-g3-h4-i5 is a straight NE side
ok(all(AX["abcde"[i] + "1"] == (i - 4, 4) for i in range(5)), "rank 1 runs SE")
ok(all(AX["e" + str(n)] == (0, 5 - n) for n in range(1, 11)), "e-file runs N")
ok([AX[n] for n in ("e1", "f2", "g3", "h4", "i5")]
   == [(0, 4), (1, 3), (2, 2), (3, 1), (4, 0)], "bottom-right side is straight")

# --- direction invariants ---------------------------------------------------
ok(all((dq - dr) % 3 == 0 for dq, dr in DIAG), "bishop dirs colour-preserving")
ok(all((dq - dr) % 3 != 0 for dq, dr in KNIGHT), "knight always changes colour")
ok(len(set(KNIGHT)) == 12 and len(set(DIAG)) == 6 and len(set(ORTHO)) == 6,
   "direction counts")
# Duniho's knight definition: the third ring minus everything a queen reaches
ring3 = {(q, r) for q in range(-4, 5) for r in range(-4, 5)
         if (abs(q) + abs(r) + abs(q + r)) // 2 == 3}
queen3 = {(d[0] * k, d[1] * k) for d in ORTHO + DIAG for k in (1, 2, 3)}
ok(set(KNIGHT) == ring3 - queen3, "knight = 3rd ring a queen cannot reach")
ok(mod.PAWN_CAPS[WHITE] == [d for d in DIAG if d in
                            [(ORTHO[0][0] + ORTHO[i][0], ORTHO[0][1] + ORTHO[i][1])
                             for i in (1, 5)]],
   "white pawn captures = the two diagonals adjacent to 'forward'")

# --- setup ------------------------------------------------------------------
s0 = g.initial_state()
ok(len(s0.board) == 36, "36 pieces at start")
by = {}
for cell, (o, t) in s0.board.items():
    by.setdefault((o, t), set()).add(cell_name(cell))
ok(by[(WHITE, "R")] == {"a1", "i5"} and by[(WHITE, "N")] == {"b1", "g3"}, "W R/N")
ok(by[(WHITE, "B")] == {"c1", "f2", "h4"}, "white bishops c1/f2/h4 (NOT f1)")
ok(by[(WHITE, "Q")] == {"d1"} and by[(WHITE, "K")] == {"e1"}, "W Q/K")
ok(by[(WHITE, "P")] == {"a2", "b2", "c2", "d2", "e2", "f3", "g4", "h5", "i6"},
   "white pawns")
ok(by[(BLACK, "R")] == {"a6", "i10"} and by[(BLACK, "N")] == {"c8", "h10"}, "B R/N")
ok(by[(BLACK, "B")] == {"b7", "d9", "g10"}, "black bishops")
ok(by[(BLACK, "Q")] == {"f10"} and by[(BLACK, "K")] == {"e10"}, "B Q/K")
ok(by[(BLACK, "P")] == {"a5", "b6", "c7", "d8", "e9", "f9", "g9", "h9", "i9"},
   "black pawns")
# Black is the exact 180° rotation of White
ok(all(s0.board.get((-q, -1 - r)) == (1 - o, t)
       for (q, r), (o, t) in s0.board.items()), "180-degree symmetric array")
for side in (WHITE, BLACK):
    cols = {(q - r) % 3 for (q, r), (o, t) in s0.board.items()
            if o == side and t == "B"}
    ok(len(cols) == 3, "three bishops on the three colours")

# --- the pawn's variable-length first move ----------------------------------
steps = {mod.FILES[q + 4]: mod.PAWN_STEPS[q] for q in range(-4, 5)}
ok(steps == {"a": 1, "b": 2, "c": 2, "d": 3, "e": 3, "f": 3, "g": 2, "h": 2,
             "i": 1}, f"first-move table {steps}")
pushes = {}
for m in g.legal_moves(s0):
    frm = mod._cell(m.split(">")[0])
    if s0.board[frm][1] == "P":
        pushes[cell_name(frm)] = pushes.get(cell_name(frm), 0) + 1
ok(pushes == {"a2": 1, "b2": 2, "c2": 2, "d2": 3, "e2": 3, "f3": 3, "g4": 2,
              "h5": 2, "i6": 1}, f"initial pawn mobility {pushes}")
ok(labels(s0).count("e2-e5") == 1 and "e2-e6" not in labels(s0),
   "e-pawn reaches e5 (midway) but no further")
# no leaping over an occupied cell; the multi-step must land on a vacant cell
s = state({"e1": "K", "e2": "P"}, {"e10": "K", "e4": "N"})
ok([x for x in labels(s) if x.startswith("e2")] == ["e2-e3"],
   "triple step is blocked by a piece two cells ahead")
s = state({"e1": "K", "e2": "P"}, {"e10": "K", "e3": "N"})
ok([x for x in labels(s) if x.startswith("e2")] == [], "blocked immediately")
# only from its OWN starting cell
s = state({"e1": "K", "e3": "P"}, {"e10": "K"})
ok([x for x in labels(s) if x.startswith("e3")] == ["e3-e4"], "no multi-step off home")
s = state({"e1": "K", "e9": "P"}, {"a1": "K"})
ok([x for x in labels(s) if x.startswith("e9")] == ["e9-e10=B", "e9-e10=N",
                                                    "e9-e10=Q", "e9-e10=R"],
   "a white pawn on Black's starting cell gets no multi-step")

# "on its first move" == "on its own starting cell": no pawn can ever re-enter
# one, because every cell from which a pawn could arrive there is that side's
# BACK rank, and a pawn can never be on its own back rank (it starts in front
# of it and its every move goes strictly forward).
for p in (WHITE, BLACK):
    sgn = mod.PAWN_FWD[p][1]
    ok(all((d[1] > 0) == (sgn > 0) for d in mod.PAWN_CAPS[p] + [mod.PAWN_FWD[p]]),
       "every pawn move goes strictly forward")
    back = set(mod.HOME[p].values())
    ok(not (back & set(mod.PAWN_START[p])), "no pawn starts on its own back rank")
    for c in mod.PAWN_START[p]:
        src = set()
        for k in range(1, 4):
            x = (c[0] - k * mod.PAWN_FWD[p][0], c[1] - k * mod.PAWN_FWD[p][1])
            if mod.on_board(*x):
                src.add(x)
        for d in mod.PAWN_CAPS[p]:
            x = (c[0] - d[0], c[1] - d[1])
            if mod.on_board(*x):
                src.add(x)
        ok(src <= back, f"only the back rank leads to {cell_name(c)}: "
                        f"{sorted(cell_name(x) for x in src - back)}")

# --- pawn captures are DIAGONAL (bishop-wise), not orthogonal ---------------
s = state({"a1": "K", "e6": "P"}, {"i10": "K", "d7": "R", "f8": "R", "e7": "R",
                                   "f7": "R", "d6": "R"})
caps = sorted(x for x in labels(s) if x.startswith("e6"))
ok(caps == ["e6xd7", "e6xf8"], f"pawn captures d7/f8 only, got {caps}")
s = state({"a1": "K", "c4": "P"}, {"i10": "K", "b5": "R", "d6": "R", "c5": "R",
                                   "d5": "R", "b4": "R"})
caps = sorted(x for x in labels(s) if x.startswith("c4"))
ok(caps == ["c4xb5", "c4xd6"], f"pawn captures b5/d6 only, got {caps}")

# --- Wikipedia's en-passant study -------------------------------------------
# "the black pawn on d8 has three possible moves, but none is safe: after
#  1...d7 it can be captured 2.exd7; after 1...d6 it can be captured
#  2.exd7 e.p. or 2.cxd6; after 1...d5 it can be captured en passant by either
#  pawn."   (White pawns c4 and e6.)
base = state({"a1": "K", "c4": "P", "e6": "P"}, {"i10": "K", "d8": "P"},
             to_move=BLACK)
ok([x for x in labels(base) if x.startswith("d8")] == ["d8-d5", "d8-d6", "d8-d7"],
   "the d8 pawn has exactly three moves")
s = g.apply_move(base, mv("d8", "d7"))
ok([x for x in labels(s) if "x" in x] == ["e6xd7"], "1...d7 2.exd7")
s = g.apply_move(base, mv("d8", "d6"))
ok([x for x in labels(s) if "x" in x] == ["c4xd6", "e6xd7 e.p."],
   "1...d6 2.exd7 e.p. or 2.cxd6")
s3 = g.apply_move(base, mv("d8", "d5"))
ok([x for x in labels(s3) if "x" in x] == ["c4xd6 e.p.", "e6xd7 e.p."],
   "1...d5 is capturable e.p. by BOTH pawns (every crossed cell counts)")
# the e.p. target set is EXACTLY the crossed cells: not the destination, and
# NOT the cell the pawn started from
ok(s3.ep[0] == AX["d5"] and sorted(cell_name(c) for c in s3.ep[1]) == ["d6", "d7"],
   f"e.p. targets are exactly d6/d7: {s3.ep}")
# the e.p. capture really removes the multi-stepped pawn
s4 = g.apply_move(s3, mv("e6", "d7"))
ok(AX["d5"] not in s4.board and s4.board[AX["d7"]] == (WHITE, "P"),
   "e.p. removes the pawn that made the triple move")
s4 = g.apply_move(s3, mv("c4", "d6"))
ok(AX["d5"] not in s4.board and s4.board[AX["d6"]] == (WHITE, "P"),
   "e.p. on the second crossed cell works too")
# ... but the right lapses after one move
s5 = g.apply_move(s3, mv("a1", "a2"))
s5 = g.apply_move(s5, mv("i10", "i9"))
ok(not [x for x in labels(s5) if "e.p." in x], "en passant right lapses")
# a single-step move creates no e.p. right at all
s6 = g.apply_move(base, mv("d8", "d7"))
ok(s6.ep is None, "one-cell moves offer no en passant")
# Duniho's OWN en-passant diagram: White d5 + f7, Black's centre pawn triples
# e9-e6.  "White's d Pawn can move directly behind it [e7], and White's f Pawn
# can move two spaces directly behind it [e8]. ... the f Pawn may also capture
# Black's g Pawn [g9]."  The f7xg9 line pins the "+1 file / +2 ranks" diagonal.
dun = state({"e1": "K", "d5": "P", "f7": "P"},
            {"e10": "K", "e9": "P", "g9": "P"}, to_move=BLACK)
dun = g.apply_move(dun, mv("e9", "e6"))
ok([x for x in labels(dun) if "x" in x] == ["d5xe7 e.p.", "f7xe8 e.p.", "f7xg9"],
   f"Duniho's e.p. diagram: {[x for x in labels(dun) if 'x' in x]}")

# --- castling ---------------------------------------------------------------
# Wikipedia's castling diagram: Black's king on h10 has castled long queenside
# (Q-0-0-0) and on c8 short bishopside (B-0-0).
s = state({"e1": "K"}, {"e10": "K", "a6": "R", "i10": "R"}, to_move=BLACK,
          castling=["1a", "1i"])
kmoves = sorted(x for x in labels(s) if x.startswith(("K", "Q-", "B-")))
ok(kmoves == ["B-0-0", "B-0-0-0", "Ke10-d8", "Ke10-d9", "Ke10-e9", "Ke10-f10",
              "Ke10-f9", "Q-0-0", "Q-0-0-0"], f"four castlings offered: {kmoves}")
after = g.apply_move(s, mv("e10", "h10"))
ok(after.board[AX["h10"]] == (BLACK, "K") and after.board[AX["g10"]] == (BLACK, "R")
   and AX["i10"] not in after.board, "Q-0-0-0 gives Kh10 / Rg10")
after = g.apply_move(s, mv("e10", "c8"))
ok(after.board[AX["c8"]] == (BLACK, "K") and after.board[AX["d9"]] == (BLACK, "R")
   and AX["a6"] not in after.board, "B-0-0 gives Kc8 / Rd9")
ok(not after.castling, "castling consumes both of that side's rights")
# White's four, with Pritchard's Kb1/Rc1 and Kh1(=h4)/Rg1(=g3) long forms
w = state({"e1": "K", "a1": "R", "i5": "R"}, {"e10": "K"}, castling=["0a", "0i"])
ok(sorted(x for x in labels(w) if x.startswith(("Q-", "B-")))
   == ["B-0-0", "B-0-0-0", "Q-0-0", "Q-0-0-0"], "White has four castlings")
aft = g.apply_move(w, mv("e1", "b1"))
ok(aft.board[AX["b1"]] == (WHITE, "K") and aft.board[AX["c1"]] == (WHITE, "R"),
   "White Q-0-0-0 = Kb1 Rc1 (Pritchard)")
aft = g.apply_move(w, mv("e1", "h4"))
ok(aft.board[AX["h4"]] == (WHITE, "K") and aft.board[AX["g3"]] == (WHITE, "R"),
   "White B-0-0-0 = Kh4 Rg3 (Pritchard's 'Kh1 Rg1')")
aft = g.apply_move(w, mv("e1", "c1"))
ok(aft.board[AX["c1"]] == (WHITE, "K") and aft.board[AX["d1"]] == (WHITE, "R"),
   "White Q-0-0 = Kc1 Rd1")
# restrictions
blocked = state({"e1": "K", "a1": "R", "i5": "R", "c1": "N"}, {"e10": "K"},
                castling=["0a", "0i"])
ok(sorted(x for x in labels(blocked) if x.startswith(("Q-", "B-")))
   == ["B-0-0", "B-0-0-0"], "a piece between king and rook forbids that side")
# ALL THREE cells between king and rook must be empty for BOTH lengths -- the
# rook travels over all of them even when the king stops short.  b1/h4 are the
# far ones, occupied by neither piece after a short castling.
for occupied, left in (("b1", ["B-0-0", "B-0-0-0"]), ("h4", ["Q-0-0", "Q-0-0-0"])):
    far = state({"e1": "K", "a1": "R", "i5": "R", occupied: "N"}, {"e10": "K"},
                castling=["0a", "0i"])
    ok(sorted(x for x in labels(far) if x.startswith(("Q-", "B-"))) == left,
       f"a piece on {occupied} forbids BOTH lengths on that flank")
incheck = state({"e1": "K", "a1": "R", "i5": "R"}, {"e10": "K", "e5": "R"},
                castling=["0a", "0i"])
ok(not [x for x in labels(incheck) if x.startswith(("Q-", "B-"))],
   "no castling out of check")
# an attacked FIRST transit cell (d1) forbids both lengths on that side
thru = state({"e1": "K", "a1": "R", "i5": "R"}, {"e10": "K", "d9": "R"},
             castling=["0a", "0i"])
ok(sorted(x for x in labels(thru) if x.startswith(("Q-", "B-")))
   == ["B-0-0", "B-0-0-0"], "no castling through an attacked cell")
# an attacked long DESTINATION (b1) leaves the short form legal
thru2 = state({"e1": "K", "a1": "R", "i5": "R"}, {"e10": "K", "b7": "R"},
              castling=["0a", "0i"])
ok(sorted(x for x in labels(thru2) if x.startswith(("Q-", "B-")))
   == ["B-0-0", "B-0-0-0", "Q-0-0"], "attacked long destination leaves 0-0")
# rights are lost by moving the rook, even if it comes back
r = state({"e1": "K", "a1": "R", "i5": "R"}, {"e10": "K"}, castling=["0a", "0i"])
r = g.apply_move(r, mv("a1", "a2"))
r = g.apply_move(r, mv("e10", "e9"))
r = g.apply_move(r, mv("a2", "a1"))
r = g.apply_move(r, mv("e9", "e10"))
ok(sorted(x for x in labels(r) if x.startswith(("Q-", "B-"))) == ["B-0-0", "B-0-0-0"],
   "a rook that moved and returned may not castle")
# ... and by the rook being captured at home
c = state({"e1": "K", "a1": "R", "i5": "R"}, {"e10": "K", "a4": "R"},
          to_move=BLACK, castling=["0a", "0i"])
c = g.apply_move(c, mv("a4", "a1"))
ok((WHITE, "a") not in c.castling and (WHITE, "i") in c.castling,
   "capturing a rook at home kills only that flank's right")

# --- promotion --------------------------------------------------------------
wp = sorted(cell_name(c) for c in mod.CELLS if mod._is_promo(WHITE, c))
bp = sorted(cell_name(c) for c in mod.CELLS if mod._is_promo(BLACK, c))
ok(wp == ["a6", "b7", "c8", "d9", "e10", "f10", "g10", "h10", "i10"],
   f"white promotion cells {wp}")
ok(bp == ["a1", "b1", "c1", "d1", "e1", "f2", "g3", "h4", "i5"],
   f"black promotion cells {bp}")
s = state({"e1": "K", "a5": "P"}, {"i10": "K"})
lm = g.legal_moves(s)
ok(sorted(x for x in lm if x.startswith(mv("a5", "a6")))
   == sorted(mv("a5", "a6", p) for p in "QRBN"), "promotion offers Q/R/B/N")
ok(mv("a5", "a6") not in lm, "promotion is forced")
ok(g.apply_move(s, mv("a5", "a6", "N")).board[AX["a6"]] == (WHITE, "N"),
   "promotes to a knight")
s = state({"e1": "K", "a5": "P"}, {"i10": "K", "b7": "R"})
ok(mv("a5", "b7", "Q") in g.legal_moves(s), "capture-promotion a5xb7=Q")

# --- checkmate / stalemate --------------------------------------------------
mate = state({"a4": "K", "b3": "Q"}, {"a1": "K"}, to_move=BLACK)
ok(g.is_terminal(mate) and g.returns(mate) == [1.0, -1.0], "checkmate = +1/-1")
# reached by a real move, not hand-built
s = state({"a4": "K", "b6": "Q"}, {"a1": "K"})
s = g.apply_move(s, mv("b6", "b3"))
ok(g.is_terminal(s) and g.returns(s) == [1.0, -1.0], "checkmate reached in play")
stale = state({"a4": "K", "a5": "Q"}, {"a1": "K"})
stale = g.apply_move(stale, mv("a5", "d2"))
ok(not mod._in_check(stale.board, BLACK), "black is not in check")
ok(g.legal_moves(stale) == [] and g.is_terminal(stale), "stalemate is terminal")
ok(g.returns(stale) == [0.0, 0.0], "STALEMATE IS A DRAW (not Glinski's 3/4-1/4)")
mirror = state({"i10": "K"}, {"i7": "K", "f9": "Q"}, to_move=WHITE)
ok(g.legal_moves(mirror) == [] and g.returns(mirror) == [0.0, 0.0],
   "stalemate scores 0-0 for either side")

# --- draw rules -------------------------------------------------------------
s = g.initial_state()
cycle = [mv("b1", "c4"), mv("h10", "g7"), mv("c4", "b1"), mv("g7", "h10")]
for _ in range(2):
    for m in cycle:
        ok(not g.is_terminal(s), "not terminal mid-cycle")
        s = g.apply_move(s, m)
ok(g.is_terminal(s) and g.returns(s) == [0.0, 0.0], "threefold repetition draw")
# a live en-passant right makes a position DIFFERENT for repetition purposes:
# after e2-e5 the board can be restored by a knight cycle, but that position no
# longer carries the e.p. right, so it is a first occurrence, not a repeat.
s = g.initial_state()
s = g.apply_move(s, mv("e2", "e5"))
ok(len(s.ep[1]) == 2 and max(s.reps.values()) == 1, "clock reset by the pawn move")
for x in (mv("h10", "g7"), mv("b1", "c4"), mv("g7", "h10"), mv("c4", "b1")):
    s = g.apply_move(s, x)
ok(s.ep is None and len(s.reps) == 5 and max(s.reps.values()) == 1,
   f"the e.p. right distinguishes the position for repetition: {sorted(s.reps.values())}")
s = state({"e1": "K", "a1": "R"}, {"e10": "K"}, halfmove=99)
s = g.apply_move(s, mv("a1", "a2"))
ok(s.halfmove == 100 and g.is_terminal(s) and g.returns(s) == [0.0, 0.0],
   "50-move rule draw")
s = state({"e1": "K", "a1": "R"}, {"e10": "K", "a2": "N"}, halfmove=99)
s = g.apply_move(s, mv("a1", "a2"))
ok(s.halfmove == 0 and not g.is_terminal(s), "a capture resets the clock")
s = state({"e1": "K", "e2": "P"}, {"e10": "K"}, halfmove=99)
s = g.apply_move(s, mv("e2", "e3"))
ok(s.halfmove == 0, "a pawn move resets the clock")

# --- the Junyj texnik report, via Derzhanski --------------------------------
# math.bas.bg/~iad/tyalie/shegra/ (Wayback) reprints the sample games, E. A.
# Baum's endgame studies and the Rostovcev/Rudenko problems from the Soviet
# magazine report on Shafran's game.  Replaying them end to end is the
# strongest available anchor: it exercises the array, every piece, castling,
# promotion and checkmate detection against published play.
import re  # noqa: E402

_TOK = re.compile(r"^(?:([KQRBN])?([a-i](?:10|[1-9]))[-:x]([a-i](?:10|[1-9]))([QRBN])?"
                  r"|([QB]-0-0(?:-0)?))$")


def play(s, tok):
    """Play one move written in Shafran's/Derzhanski's notation."""
    t = tok.rstrip("+#!?")
    mm = _TOK.match(t)
    ok(mm is not None, f"parsed {tok!r}")
    if mm.group(5):                      # Q-0-0 / Q-0-0-0 / B-0-0 / B-0-0-0
        me = s.to_move
        qf = mod.QUEEN_FLANK[me]
        flank = qf if t[0] == "Q" else ("i" if qf == "a" else "a")
        betw = mod.CASTLE_BETWEEN[(me, flank)]
        dest = betw[2] if t.endswith("0-0-0") else betw[1]
        m = f"{mod.KING_START[me][0]},{mod.KING_START[me][1]}>{dest[0]},{dest[1]}"
    else:
        m = mv(mm.group(2), mm.group(3), mm.group(4))
    ok(m in g.legal_moves(s), f"{tok} is legal")
    return g.apply_move(s, m)


def line(s, moves, mate=False, tag=""):
    for t in moves.split():
        s = play(s, t)
    if mate:
        ok(g.is_terminal(s) and mod._in_check(s.board, s.to_move)
           and g.returns(s) in ([1.0, -1.0], [-1.0, 1.0]), f"{tag}: checkmate")
    return s


# Sample game #1, "Kindermatt" — the shortest game ever: the knight forks the
# king, the queen and the bishops' rook while the e9 pawn is pinned by Qe3.
k = line(g.initial_state(), "Nb1-c4 Nc8-d6 Qd1-e3 b6-b5 Nc4-d7",
         mate=True, tag="Kindermatt")
ok(all(mod._attacked(k.board, AX[c], WHITE) for c in ("e10", "f10", "a6")),
   "the d7 knight forks K, Q and the bishops' rook")

# Sample game #4 — 22 moves with a real 6. Q-0-0-0, ending in 22...Qg4-a4#.
s = line(g.initial_state(), """
    e2-e4 e9-e7 Bc1-e2 Qf10-e9 Be2:i10 Qe9:i5 Nb1-e3 Bd9:h5 Qd1-e2 b6-b5
    Q-0-0-0""")
ok(s.board[AX["b1"]] == (WHITE, "K") and s.board[AX["c1"]] == (WHITE, "R")
   and AX["e1"] not in s.board and AX["a1"] not in s.board,
   "6. Q-0-0-0 gives Kb1 / Rc1, as the score's later 15.Rc1:c2 and 20...Kb1-a1 confirm")
line(s, """
    Nh10-g7 Ng3-h6 Bh5-f7 Nh6:f7 g9:f7 Bi10:c7 Ra6-c6 Bc7-f4 d8-d5
    e4:d5 Ng7:d5 Bh4-f6 Nd5:f4 Qe2:f4 Qi5:f2 Bf6-h4 Bg10:c2 Ne3-c4 b5:c4
    Rc1:c2 Qf2:h4 Qf4-i10+ Ke10-e9 Qi10-e2 c4:b2 Rc2:b2 Rc6-g6+ Kb1-a1 Qh4:g4+
    Ka1-b3 Nc8-d6+ Kb3-a3 Qg4-a4""", mate=True, tag="game #4")

# Sample game #3 — 30 moves, Black resigns a move before mate.
line(g.initial_state(), """
    Bf2-e3 e9-e7 h5-h6 a5-a4 Ri5-g5 f9-f7 Bc1-d3 b6-b5 i6-i7 Bg10:e9
    b2-b3 a4:b3 c2:b3 Bb7-d5 Nb1-d4 c7-c5 Nd4-c1 Ra6-a3 b3-c5 Bd9-c7
    Bd3-f4 Bc7:f4 Rg5:f4 Be9:c5 Nc1-d4 Bc5-b3 Qd1-c1 Ra3-c5 Ra1-c3 Bd5:c3
    d2:c3 Bb3:d4 Rf4:d4 Rc5-i5 Bh4-i6+ Ke10-d9 Ke1-f2 i9-i8 Qc1-d3 i8:h6
    g4:h6 Ri5:g3+ Kf2:g3 Ri10:i7 Bi6-h4 Ri7:h6 Be3-g4 Rh6-g6 Qd3-h5 Nh10-i8
    Qh5-c5 Qf10-e9 Rd4-d7 Ni8-f6 Bh4:f6 Rg6:f6 Qc5-c7+ Kd9-e10 Rd7-e8""")

# E. A. Baum's checkmating studies (a lone king; mates in 1 and 2).
for tag, w, b, moves in [
        ("Q", {"a4": "K", "b2": "Q"}, {"e10": "K"}, "Qb2-e8"),
        ("K+Q", {"d6": "K", "b2": "Q"}, {"e10": "K"}, "Kd6-e7 Ke10-d9 Qb2-e8"),
        ("K+Q'", {"d6": "K", "b2": "Q"}, {"e10": "K"}, "Kd6-e7 Ke10-e9 Qb2-e8"),
        ("K+R", {"f8": "K", "g3": "R"}, {"f10": "K"}, "Rg3-g9 Kf10-e10 Rg9-e9"),
        ("K+2N", {"d7": "K", "a5": "N", "i10": "N"}, {"e10": "K"},
         "Na5-c8 Ke10-d9 Ni10-f8"),
        ("K+N+B", {"d7": "K", "c4": "N", "i9": "B"}, {"d9": "K"},
         "Nc4-e7+ Kd9-e10 Bi9-g8"),
        ("K+N+B'", {"d7": "K", "c4": "N", "i9": "B"}, {"d9": "K"},
         "Nc4-e7+ Kd9-e10 Bi9-h7"),
        ("K+2B", {"d7": "K", "b2": "B", "d2": "B"}, {"d9": "K"},
         "Bb2-e8+ Kd9-e10 Bd2-g8")]:
    line(state(w, b), moves, mate=True, tag=f"Baum study {tag}")

# Rostovcev's problem #1 (promotion + a bishop sacrifice) ...
line(state({"a1": "K", "f3": "N", "e5": "B", "d3": "P", "d8": "P"},
           {"b5": "K", "i9": "Q", "a4": "P", "b4": "P", "d6": "P"}),
     "d8-d9Q+ Qi9:d9 Be5-a3+ Kb5:a3 Nf3-d4", mate=True, tag="problem #1")
# ... and #3, whose printed key "1. Kd7-c10" names a cell that does not exist
# (the c-file ends at c8).  1. Kd7-c8 is the unique mate in 2.
p3w, p3b = {"d7": "K", "a4": "R", "b4": "P"}, {"a6": "K", "b7": "B", "c7": "P",
                                               "a5": "P"}
for defence, mate in [("c7-c6", "b4-b5"), ("Bb7-c6", "Ra4:c6"),
                      ("Bb7-f3", "Ra4:a5"), ("Bb7-d8", "Ra4:a5")]:
    line(state(p3w, p3b), f"Kd7-c8 {defence} {mate}", mate=True,
         tag=f"problem #3 ({defence})")
ok("c10" not in AX, "the printed key 1.Kd7-c10 names a non-existent cell")
# Rudenko's problem #5: 1.Ba2-b4! threatens 2.Bb4-a5#; four rook defences.
p5w = {"f10": "K", "f6": "R", "i7": "R", "e10": "N", "h6": "N", "a2": "B",
       "g3": "B", "g10": "B", "d7": "P", "f9": "P", "g5": "P", "g8": "P"}
p5b = {"e7": "K", "d5": "R", "h7": "N", "c1": "B", "c2": "B", "b5": "P",
       "c5": "P", "d2": "P", "d6": "P", "d8": "P", "g9": "P"}
for defence, mate in [("Rd5-d4", "Rf6-e6"), ("Rd5-e6", "Rf6-f8"),
                      ("Rd5-d3", "Rf6-g7"), ("Rd5-e5", "Ri7:h7")]:
    line(state(p5w, p5b), f"Ba2-b4 {defence} {mate}", mate=True,
         tag=f"problem #5 ({defence})")

# Derzhanski's structural counts for the board itself.
colours = {}
for c in mod.CELLS:
    colours[(c[0] - c[1]) % 3] = colours.get((c[0] - c[1]) % 3, 0) + 1
ok(sorted(colours.values()) == [23, 23, 24],
   f"70 cells in three colours 23/23/24 (Derzhanski): {sorted(colours.values())}")
corner_cols = {}
for n in ("a1", "e1", "i5", "i10", "e10", "a6"):
    corner_cols.setdefault((AX[n][0] - AX[n][1]) % 3, []).append(n)
ok(sorted(len(v) for v in corner_cols.values()) == [2, 2, 2],
   f"two corners of each colour (Derzhanski): {corner_cols}")

# Short castling is "the opposite procedure" (Derzhanski): the ROOK steps next
# to the king and the KING jumps over it -- so the king ends 2 cells from home
# and the rook 1, which is exactly Wikipedia's diagram (black Kc8 / Rd9).
for (p, flank), betw in sorted(mod.CASTLE_BETWEEN.items()):
    w = {"e1": "K", "a1": "R", "i5": "R"} if p == WHITE else {"e1": "K"}
    b = {"e10": "K", "a6": "R", "i10": "R"} if p == BLACK else {"e10": "K"}
    base = state(w, b, to_move=p, castling=[f"{p}a", f"{p}i"])
    for length, kdst, rdst in ((2, betw[1], betw[0]), (3, betw[2], betw[1])):
        after = g.apply_move(base, mv(cell_name(mod.KING_START[p]), cell_name(kdst)))
        ok(after.board[kdst] == (p, "K") and after.board[rdst] == (p, "R")
           and mod.ROOK_START[(p, flank)] not in after.board,
           f"{'long' if length == 3 else 'short'} castling {p}{flank}: "
           f"K{cell_name(kdst)} R{cell_name(rdst)}")

# --- bishop colour invariance ----------------------------------------------
s = g.initial_state()
bishop_moves = 0
for m in g.legal_moves(s):
    frm = mod._cell(m.split("=")[0].split(">")[0])
    to = mod._cell(m.split("=")[0].split(">")[1])
    if s.board[frm][1] == "B":
        bishop_moves += 1
        ok((frm[0] - frm[1]) % 3 == (to[0] - to[1]) % 3, "bishop stays on colour")
ok(bishop_moves == 12, "12 bishop moves at start")

# --- perft ------------------------------------------------------------------
def perft(s, d):
    if d == 0:
        return 1
    return sum(perft(g.apply_move(s, m), d - 1) for m in g.legal_moves(s))


s0 = g.initial_state()
ok(len(g.legal_moves(s0)) == 42, "initial mobility 42 (hand-derived + 2 oracles)")
ok(perft(s0, 2) == 1706, "perft(2) = 1706")
ok(perft(s0, 3) == 75494, "perft(3) = 75494")

# --- notation ---------------------------------------------------------------
ok(g.describe_move(s0, mv("e2", "e5")) == "e2-e5", "pawn notation")
ok(g.describe_move(s0, mv("b1", "c4")) == "Nb1-c4", "knight notation")
ok(g.describe_move(s0, mv("c1", "g9")) == "Bc1xg9", "capture notation")

# --- renderer sanity (format only; the browser is the real check) ----------
spec = g.render(s0)
ok(spec["board"]["type"] == "hex", "hex board")
ok(isinstance(spec["board"]["cells"], list) and len(spec["board"]["cells"]) == 70
   and all(isinstance(x, str) for x in spec["board"]["cells"]),
   "board.cells is a flat list of 70 axial id STRINGS")
ok(set(spec["board"]["tints"]) == set(spec["board"]["cells"]), "tints cover the board")
ok(len(set(spec["board"]["tints"].values())) == 3, "three cell colours")
ok({p["cell"] for p in spec["pieces"]} <= set(spec["board"]["cells"]),
   "every piece sits on a real cell")

# --- serialize round-trip & purity ------------------------------------------
s = g.initial_state()
for m in [mv("e2", "e5"), mv("d8", "d5"), mv("b1", "c4")]:
    before = g.serialize(s)
    s2 = g.apply_move(s, m)
    ok(g.serialize(s) == before, "apply_move is pure")
    ok(g.serialize(g.deserialize(g.serialize(s2))) == g.serialize(s2), "round-trip")
    s = s2

# --- random playout terminates ----------------------------------------------
import random  # noqa: E402

rng = random.Random(11)
s = g.initial_state()
plies = 0
while not g.is_terminal(s):
    s = g.apply_move(s, rng.choice(g.legal_moves(s)))
    plies += 1
    ok(plies <= mod.PLY_CAP, "terminates within the ply cap")
ok(g._draw_reason(s) != "move limit", "the ply cap is never what ends a game")
ret = g.returns(s)
ok(len(ret) == 2 and all(-1.0 <= x <= 1.0 for x in ret), "well-formed returns")

# --- heuristic returns per-seat payoffs (MCTS contract) ---------------------
h = g.heuristic(g.initial_state())
ok(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9,
   "heuristic is a zero-sum pair")
from agp.mcts import MCTSBot  # noqa: E402

MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(g, g.initial_state())
checks += 1

print(f"shafran_chess selftest OK ({checks} checks, {time.time() - t0:.1f}s)")
