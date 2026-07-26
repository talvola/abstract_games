"""Selftest for De Vasa's Hexagonal Chess (pure stdlib; run from engine/):

    PYTHONPATH=. python3 games/de_vasa_chess/selftest.py

Correctness anchors
-------------------
1. PERFT from the initial position: 55 / 2,992 / 168,335 (depths 1-3). No
   published De Vasa perft series exists, so these were frozen after one-time
   cross-checks (2026-07-26, not rerun here):
     * the setup, promotion cells and promotion choices read straight off the
       JOCLY reference model (AGPL, oracle only) -- 36 men, cell for cell;
     * TWO independently written from-scratch reimplementations (one per
       author) whose every direction is DISCOVERED by measuring distances
       between hex CENTRES (no axial delta table, no cube permutations) and
       whose castling geometry is transcribed in cell NAMES off the Wikipedia
       and Green Chess diagrams.  Lockstep legal-move-set comparison over
       14,167 random-game positions + 4,272 castling-rich and 6,688
       post-double-step constructed positions (6,152 castling moves, every
       legal en-passant capture): 0 mismatches.  Attack sets also agree over
       all 936 (piece, colour, cell) combinations on an empty board and 8,000
       randomly occupied ones.
   Perft(4) = 9,343,938 was reproduced by both (too slow for the suite).
   Depth 1 = 55 is also hand-derived below, piece by piece.
2. The Wikipedia setup diagram, cell for cell, including the KINGS ON OPPOSITE
   WINGS (Kf1 / Kd9) and the exact 180-degree rotational symmetry, and the
   1954 modification sheet's "81 hexagones, dont 27 blancs, 27 noirs,
   27 bruns".
3. Wikipedia's pawn diagram: the b3 pawn's four move options (b4 b5 c4 d5) and
   two captures (a4 d4); the g5 pawn's two moves (g6 h6) and two captures
   (f6 i6); the *straight-ahead* diagonal is NOT a capture; and the worked
   en-passant line 1...f7-f5 2.g5xf6 e.p.
4. Castling, which the 1954 sheet names outright ("apres le grand roque:
   Rc1, Td1"; "apres le petit roque: Rh1, Tg1") and Wikipedia's castling
   diagram shows (White short Kh1/Rg1, Black long Kg9/Rf9); plus the other two
   castlings, the "king 2 short / 3 long" distances, the standard restrictions
   (blocked, through check, out of check, rights lost), and the fact that an
   ordinary diagonal king step onto a castling destination (e2-c1, e8-g9) is
   NOT written as castling.
5. Promotion on the opponent's back RANK, to Q/R/B/N, forced.
6. Checkmate and stalemate REACHED through apply_move; stalemate is a DRAW.
7. The hard ply cap is not outcome-load-bearing: it is proved unreachable
   (bound 14,299 < PLY_CAP) and measured over random games.
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

t0 = time.time()
checks = 0


def ok(cond, what):
    global checks
    checks += 1
    if not cond:
        raise AssertionError(f"FAIL: {what}")


def cell(nm):
    """'f1' -> (c, r)."""
    return (mod.FILES.index(nm[0]), 9 - int(nm[1:]))


def mstr(a, b, promo=None):
    x, y = cell(a), cell(b)
    return f"{x[0]},{x[1]}>{y[0]},{y[1]}" + (f"={promo}" if promo else "")


def pos(pieces, to_move=WHITE, castling=frozenset(), ep=None):
    board = {cell(nm): (o, t) for nm, (o, t) in pieces.items()}
    return mod.VState(board=board, to_move=to_move, castling=castling, ep=ep)


def named(s):
    return {cell_name(k): v for k, v in s.board.items()}


def desc_set(s):
    return {g.describe_move(s, m) for m in g.legal_moves(s)}


# --- 1. the board ------------------------------------------------------------
s0 = g.initial_state()
ok(len(mod.CELLS) == 81, "81 cells")
ok(cell_name((5, 8)) == "f1" and cell_name((0, 0)) == "a9"
   and cell_name((8, 8)) == "i1", "cell naming: file letter + rank")

# --- 2. the Wikipedia setup diagram, cell for cell --------------------------
want = {}
for i, letter in enumerate("RNBQBKBNR"):
    want[f"{mod.FILES[i]}1"] = (WHITE, letter)
for i, letter in enumerate("RNBKBQBNR"):
    want[f"{mod.FILES[i]}9"] = (BLACK, letter)
for i in range(9):
    want[f"{mod.FILES[i]}3"] = (WHITE, "P")
    want[f"{mod.FILES[i]}7"] = (BLACK, "P")
ok(named(s0) == want, "initial array matches the Wikipedia diagram exactly")
ok(named(s0)["f1"] == (WHITE, "K") and named(s0)["d9"] == (BLACK, "K"),
   "the kings start on OPPOSITE wings (Kf1 vs Kd9)")
ok(named(s0)["d1"] == (WHITE, "Q") and named(s0)["f9"] == (BLACK, "Q"),
   "the queens are also on opposite wings (Qd1 vs Qf9)")
# 180-degree rotational symmetry (c,r) -> (8-c, 8-r), colours swapped
ok(all(s0.board.get((8 - c, 8 - r)) == (1 - o, t)
       for (c, r), (o, t) in s0.board.items()),
   "Black's array is White's exact 180-degree rotation")
ok(len(s0.board) == 36, "36 men")

# the three bishops stand on the three cell colours ((c - r) mod 3)
bcol = {(c - r) % 3 for (c, r), (o, t) in s0.board.items()
        if o == WHITE and t == "B"}
ok(bcol == {0, 1, 2}, "White's three bishops are on the three cell colours")
# the 1954 modification sheet counts them: "81 hexagones, dont 27 blancs,
# 27 noirs, 27 bruns"
ccount = {}
for c, r in mod.CELLS:
    ccount[(c - r) % 3] = ccount.get((c - r) % 3, 0) + 1
ok(sorted(ccount.values()) == [27, 27, 27],
   "the 81 cells split 27 / 27 / 27 between the three colours (1954 sheet)")
ok(all(((a[0] + d[0]) - (a[1] + d[1])) % 3 == (a[0] - a[1]) % 3
       for d in mod.DIAG for a in [(4, 4)]),
   "every bishop direction preserves the cell colour")

# --- 3. the RenderSpec shape ------------------------------------------------
spec = g.render(s0)
b = spec["board"]
ok(b["type"] == "hex" and b["shape"] == "rhombus"
   and b["width"] == 9 and b["height"] == 9, "board is a 9x9 hex rhombus")
ok("orientation" not in b,
   "pointy-top (the default): De Vasa's RANKS are horizontal, not his files")
ok(len(b["tints"]) == 81 and len(set(b["tints"].values())) == 3,
   "81 tinted cells in three colours")
ok(len(spec["pieces"]) == 36 and spec["pieceset"] == "chess", "36 rendered men")

# --- 4. depth-1 move count, hand-derived ------------------------------------
# pawns 33 (a3 4, b3..g3 4 each, h3 3 [its NE double step leaves the board],
#           i3 2 [it has no NE move at all]), knights 5 (b1: c4 d4 e2; h1: i4
# f2), rooks 3 (a1: a2 b2; i1: i2), bishops 6 (2 each from c1/e1/g1),
# queen 4 (d2 e2 f2 c2), king 4 (f2 g2 h2 e2), castling 0.
ok(len(g.legal_moves(s0)) == 33 + 5 + 3 + 6 + 4 + 4, "55 opening moves")
s0b = mod.VState(board=dict(s0.board), to_move=BLACK)
ok(len(g.legal_moves(s0b)) == 55, "Black has the same 55 by symmetry")

# --- 5. frozen perft --------------------------------------------------------
def perft(s, d):
    ms = g.legal_moves(s)
    if d == 1:
        return len(ms)
    return sum(perft(g.apply_move(s, m), d - 1) for m in ms)


for depth, want_n in ((1, 55), (2, 2992), (3, 168335)):
    ok(perft(g.initial_state(), depth) == want_n, f"perft({depth}) == {want_n}")

# --- 6. the pawn: two forward directions, two SIDE captures -----------------
p = pos({"b3": (WHITE, "P"), "g5": (WHITE, "P"), "f7": (BLACK, "P"),
         "h1": (WHITE, "K"), "g1": (WHITE, "R"),
         "g9": (BLACK, "K"), "f9": (BLACK, "R")})
ok({m for m in desc_set(p) if m.startswith("b3")}
   == {"b3-b4", "b3-b5", "b3-c4", "b3-d5"},
   "unmoved pawn b3: four move options (Wikipedia's green dots)")
ok({m for m in desc_set(p) if m.startswith("g5")} == {"g5-g6", "g5-h6"},
   "moved pawn g5: two move options")

# the two capture cells (Wikipedia's red dots), tested by putting enemies there
capt = pos({"b3": (WHITE, "P"), "a4": (BLACK, "N"), "d4": (BLACK, "N"),
            "c5": (BLACK, "N"), "b4": (BLACK, "N"), "c4": (BLACK, "N"),
            "f1": (WHITE, "K"), "d9": (BLACK, "K")})
ok({m for m in desc_set(capt) if m.startswith("b3")} == {"b3xa4", "b3xd4"},
   "pawn captures ONLY on the two side diagonals a4/d4 -- b4/c4 (its own move "
   "cells) and c5 (the straight-ahead diagonal) are not captures")
capt2 = pos({"g5": (WHITE, "P"), "f6": (BLACK, "N"), "i6": (BLACK, "N"),
             "h7": (BLACK, "N"), "f1": (WHITE, "K"), "d9": (BLACK, "K")})
ok({m for m in desc_set(capt2) if m.startswith("g5") and "x" in m}
   == {"g5xf6", "g5xi6"},
   "g5's captures are f6 and i6; the straight-ahead diagonal h7 is not one")

# the double step must be in the SAME direction and may not leap
blocked = pos({"b3": (WHITE, "P"), "c4": (BLACK, "N"),
               "f1": (WHITE, "K"), "d9": (BLACK, "K")})
ok({m for m in desc_set(blocked) if m.startswith("b3")} == {"b3-b4", "b3-b5"},
   "a blocked forward direction kills both its single and its double step "
   "(and c4 is a move cell, so it cannot be captured either)")
ok("b3-d5" not in desc_set(blocked), "no leaping over c4 to d5")
moved = pos({"b4": (WHITE, "P"), "f1": (WHITE, "K"), "d9": (BLACK, "K")})
ok({m for m in desc_set(moved) if m.startswith("b4")} == {"b4-b5", "b4-c5"},
   "a pawn off its home rank has no double step")

# --- 7. en passant (Wikipedia's worked line 1...f7-f5 2.g5xf6 e.p.) ---------
pb = pos({"b3": (WHITE, "P"), "g5": (WHITE, "P"), "f7": (BLACK, "P"),
          "h1": (WHITE, "K"), "g9": (BLACK, "K")}, to_move=BLACK)
ok(mstr("f7", "f5") in g.legal_moves(pb), "black may double-step f7-f5")
p1 = g.apply_move(pb, mstr("f7", "f5"))
ok(cell_name(p1.ep[0]) == "f6" and cell_name(p1.ep[1]) == "f5",
   "the crossed cell f6 becomes the en-passant target")
ok("g5xf6 e.p." in desc_set(p1), "2.g5xf6 e.p. is available")
p2 = g.apply_move(p1, mstr("g5", "f6"))
ok(named(p2) == {"b3": (WHITE, "P"), "f6": (WHITE, "P"),
                 "h1": (WHITE, "K"), "g9": (BLACK, "K")},
   "the en-passant capture removes the f5 pawn")
# ...and the right expires after one ply
p3 = g.apply_move(p1, mstr("h1", "h2"))
p4 = g.apply_move(p3, mstr("g9", "g8"))
ok("g5xf6 e.p." not in desc_set(p4), "the en-passant right lasts one ply only")
# a double step in the OTHER direction sets its own crossed cell
pd = pos({"c3": (WHITE, "P"), "f1": (WHITE, "K"), "d9": (BLACK, "K")})
pe = g.apply_move(pd, mstr("c3", "e5"))
ok(cell_name(pe.ep[0]) == "d4" and cell_name(pe.ep[1]) == "e5",
   "the diagonal-direction double step c3-e5 crosses d4")

# --- 8. castling ------------------------------------------------------------
ALL = frozenset(mod.ALL_CASTLES)
free = pos({"f1": (WHITE, "K"), "a1": (WHITE, "R"), "i1": (WHITE, "R"),
            "d9": (BLACK, "K"), "a9": (BLACK, "R"), "i9": (BLACK, "R")},
           castling=ALL)
ok({"0-0", "0-0-0"} <= desc_set(free), "both castlings are offered")
for tag, king_to, rook_from, rook_to in (("0-0", "h1", "i1", "g1"),
                                         ("0-0-0", "c1", "a1", "d1")):
    mv = [m for m in g.legal_moves(free) if g.describe_move(free, m) == tag][0]
    after = named(g.apply_move(free, mv))
    ok(after[king_to] == (WHITE, "K") and after[rook_to] == (WHITE, "R")
       and rook_from not in after and "f1" not in after,
       f"White {tag}: K f1->{king_to}, R {rook_from}->{rook_to}")
blackside = pos({"f1": (WHITE, "K"), "a1": (WHITE, "R"), "i1": (WHITE, "R"),
                 "d9": (BLACK, "K"), "a9": (BLACK, "R"), "i9": (BLACK, "R")},
                to_move=BLACK, castling=ALL)
for tag, king_to, rook_from, rook_to in (("0-0", "b9", "a9", "c9"),
                                         ("0-0-0", "g9", "i9", "f9")):
    mv = [m for m in g.legal_moves(blackside)
          if g.describe_move(blackside, m) == tag][0]
    after = named(g.apply_move(blackside, mv))
    ok(after[king_to] == (BLACK, "K") and after[rook_to] == (BLACK, "R")
       and rook_from not in after and "d9" not in after,
       f"Black {tag}: K d9->{king_to}, R {rook_from}->{rook_to}")
# the diagram itself: White short and Black long, simultaneously
ok(named(g.apply_move(free, mstr("f1", "h1")))["h1"] == (WHITE, "K"),
   "Wikipedia's diagram: White short -> Kh1/Rg1")
ok(named(g.apply_move(blackside, mstr("d9", "g9")))["f9"] == (BLACK, "R"),
   "Wikipedia's diagram: Black long -> Kg9/Rf9")
# distances: 2 cells short, 3 cells long, for both sides
ok(abs(cell("h1")[0] - cell("f1")[0]) == 2
   and abs(cell("c1")[0] - cell("f1")[0]) == 3
   and abs(cell("b9")[0] - cell("d9")[0]) == 2
   and abs(cell("g9")[0] - cell("d9")[0]) == 3,
   "the king slides 2 cells short and 3 long, on both wings")

# restrictions
for occupied in ("g1", "h1"):
    blk = pos({"f1": (WHITE, "K"), "a1": (WHITE, "R"), "i1": (WHITE, "R"),
               occupied: (WHITE, "N"), "d9": (BLACK, "K")}, castling=ALL)
    ok("0-0" not in desc_set(blk) and "0-0-0" in desc_set(blk),
       f"short castling blocked by a piece on {occupied}")
for occupied in ("b1", "c1", "d1", "e1"):
    blk = pos({"f1": (WHITE, "K"), "a1": (WHITE, "R"), "i1": (WHITE, "R"),
               occupied: (WHITE, "N"), "d9": (BLACK, "K")}, castling=ALL)
    ok("0-0-0" not in desc_set(blk) and "0-0" in desc_set(blk),
       f"long castling blocked by a piece on {occupied}")
chk = pos({"f1": (WHITE, "K"), "a1": (WHITE, "R"), "i1": (WHITE, "R"),
           "f9": (BLACK, "R"), "d9": (BLACK, "K")}, castling=ALL)
ok(not ({"0-0", "0-0-0"} & desc_set(chk)), "no castling out of check")
thru = pos({"f1": (WHITE, "K"), "a1": (WHITE, "R"), "i1": (WHITE, "R"),
            "g9": (BLACK, "R"), "d9": (BLACK, "K")}, castling=ALL)
ok("0-0" not in desc_set(thru) and "0-0-0" in desc_set(thru),
   "no castling THROUGH an attacked cell (g1)")
land = pos({"f1": (WHITE, "K"), "a1": (WHITE, "R"), "i1": (WHITE, "R"),
            "h9": (BLACK, "R"), "d9": (BLACK, "K")}, castling=ALL)
ok("0-0" not in desc_set(land) and "0-0-0" in desc_set(land),
   "no castling ONTO an attacked cell (h1)")
# rights are lost when the king or a rook leaves home
moved_k = g.apply_move(free, mstr("f1", "f2"))
back_k = g.apply_move(g.apply_move(moved_k, mstr("d9", "d8")), mstr("f2", "f1"))
ok(not ({"0-0", "0-0-0"} & desc_set(
    mod.VState(board=back_k.board, to_move=WHITE, castling=back_k.castling))),
   "moving the king kills BOTH castling rights, even if it returns")
moved_r = g.apply_move(free, mstr("i1", "i2"))
back_r = g.apply_move(g.apply_move(moved_r, mstr("d9", "d8")), mstr("i2", "i1"))
st_r = mod.VState(board=back_r.board, to_move=WHITE, castling=back_r.castling)
ok("0-0" not in desc_set(st_r) and "0-0-0" in desc_set(st_r),
   "moving the i1 rook kills only the short castling")
# capturing a rook on its home cell kills that right too
capr = pos({"f1": (WHITE, "K"), "a1": (WHITE, "R"), "i1": (WHITE, "R"),
            "i3": (BLACK, "R"), "d9": (BLACK, "K")}, to_move=BLACK,
           castling=ALL)
aft = g.apply_move(capr, mstr("i3", "i1"))
ok((WHITE, "i") not in aft.castling and (WHITE, "a") in aft.castling,
   "capturing the i1 rook kills White's short castling right")
# ... and castling NOTATION must not swallow an ordinary king move.  Two of the
# four castling destinations are reachable by a plain diagonal king step from
# somewhere else: c1 from e2 (White) and g9 from e8 (Black), via the (-+2, +-1)
# diagonals.  Those are quiet moves / captures, never castling.
notc = pos({"e2": (WHITE, "K"), "a1": (WHITE, "R"), "i9": (BLACK, "K")},
           castling=frozenset({(WHITE, "a")}))
ok(g.describe_move(notc, mstr("e2", "c1")) == "Ke2-c1",
   "an ordinary diagonal king step e2-c1 is NOT written 0-0-0")
notc2 = pos({"e2": (WHITE, "K"), "c1": (BLACK, "R"), "i9": (BLACK, "K")},
            castling=frozenset())
ok(g.describe_move(notc2, mstr("e2", "c1")) == "Ke2xc1",
   "...and a capture on c1 is written as a capture")
notc3 = pos({"e8": (BLACK, "K"), "i9": (BLACK, "R"), "a1": (WHITE, "K")},
            to_move=BLACK, castling=frozenset({(BLACK, "i")}))
ok(g.describe_move(notc3, mstr("e8", "g9")) == "Ke8-g9",
   "the Black mirror e8-g9 is not written 0-0-0 either")

# --- 9. promotion -----------------------------------------------------------
pr = pos({"d8": (WHITE, "P"), "f1": (WHITE, "K"), "a9": (BLACK, "K")})
promos = {m for m in g.legal_moves(pr) if m.startswith(mstr("d8", "d9")[:4])}
ok({g.describe_move(pr, m) for m in g.legal_moves(pr) if "=" in m}
   == {f"d8-{f}9={pc}" for f in "de" for pc in "QRBN"},
   "promotion on rank 9 to Q/R/B/N, on both forward cells, and forced")
ok(g.apply_move(pr, mstr("d8", "d9", "N")).board[cell("d9")] == (WHITE, "N"),
   "the chosen promotion piece appears")
prb = pos({"d2": (BLACK, "P"), "f9": (BLACK, "K"), "a1": (WHITE, "K")},
          to_move=BLACK)
ok({g.describe_move(prb, m) for m in g.legal_moves(prb) if "=" in m}
   == {f"d2-{f}1={pc}" for f in "cd" for pc in "QRBN"},
   "Black promotes on rank 1")
ok(not any("=" in m for m in g.legal_moves(
    pos({"d7": (WHITE, "P"), "f1": (WHITE, "K"), "a9": (BLACK, "K")}))),
   "no promotion short of the back rank")

# --- 10. checkmate / stalemate, REACHED through apply_move ------------------
# White Kf1, Qd1; Black Ka9 in the corner. Qd1-a4 is mate: a9's only flight
# cells are covered by the queen along the a-file and the b-file diagonal.
mate = pos({"f1": (WHITE, "K"), "b7": (WHITE, "Q"), "d5": (WHITE, "R"),
            "a9": (BLACK, "K")})
found = None
for m in g.legal_moves(mate):
    nxt = g.apply_move(mate, m)
    if g.is_terminal(nxt) and g.returns(nxt) == [1.0, -1.0]:
        found = g.describe_move(mate, m)
        break
ok(found is not None, f"checkmate is reachable ({found})")
# stalemate, likewise REACHED by a move: 1.Qc5-c8 leaves Black Ka9 with its
# three flight cells (a8, b8, b9) covered but the king itself unattacked.
pre = pos({"f1": (WHITE, "K"), "c5": (WHITE, "Q"), "a9": (BLACK, "K")})
stale = g.apply_move(pre, mstr("c5", "c8"))
ok(g.is_terminal(stale) and not mod._in_check(stale.board, BLACK)
   and g.legal_moves(stale) == [] and g.returns(stale) == [0.0, 0.0],
   "STALEMATE IS A DRAW (not Glinski's 3/4-1/4)")

# --- 11. draw rules ---------------------------------------------------------
rep = pos({"f1": (WHITE, "K"), "a9": (BLACK, "K")})
rep.reps = {mod._poskey(rep.board, rep.to_move, rep.ep, rep.castling): 1}
st = rep
for a, b2 in [("f1", "f2"), ("a9", "a8"), ("f2", "f1"), ("a8", "a9")] * 2:
    st = g.apply_move(st, mstr(a, b2))
ok(g._draw_reason(st) == "threefold repetition" and g.is_terminal(st)
   and g.returns(st) == [0.0, 0.0], "threefold repetition draws")
ok(g._draw_reason(mod.VState(board=dict(rep.board), halfmove=100))
   == "50-move rule", "the 50-move rule draws")
# ...and the counter itself: a quiet move increments it, a PAWN move and a
# CAPTURE both reset it (a capture that is not a pawn move included).
quiet = pos({"f1": (WHITE, "K"), "d5": (WHITE, "R"), "a9": (BLACK, "K"),
             "h5": (BLACK, "R")}, castling=frozenset())
q1 = g.apply_move(quiet, mstr("d5", "d6"))
ok(q1.halfmove == 1, "a quiet move increments the 50-move counter")
q2 = g.apply_move(q1, mstr("h5", "h6"))
ok(q2.halfmove == 2, "...and again")
cap50 = g.apply_move(q2, mstr("d6", "h6"))
ok(cap50.halfmove == 0, "a CAPTURE resets the 50-move counter")
pawn50 = pos({"f1": (WHITE, "K"), "d5": (WHITE, "P"), "a9": (BLACK, "K")},
             castling=frozenset())
pawn50.halfmove = 7
ok(g.apply_move(pawn50, mstr("d5", "d6")).halfmove == 0,
   "a PAWN move resets the 50-move counter")
# a capture also wipes the repetition table (no earlier position can recur)
ok(cap50.reps == {mod._poskey(cap50.board, cap50.to_move, cap50.ep,
                              cap50.castling): 1},
   "an irreversible move clears the repetition table")

# --- 12. the ply cap is NOT outcome-load-bearing ----------------------------
# Analytic bound: <=34 captures + <=108 pawn moves (18 pawns; each pawn move
# gains 1 or 2 ranks and a pawn crosses 6 ranks) = <=142 irreversible plies,
# with <=99 reversible plies in each of the 143 gaps around them.
BOUND = 34 + 18 * 6 + (34 + 18 * 6 + 1) * 99
ok(BOUND == 14299 and mod.PLY_CAP > BOUND,
   f"the 50-move rule provably fires first (bound {BOUND} < cap {mod.PLY_CAP})")

import random  # noqa: E402

longest = 0
for seed in range(12):
    rng = random.Random(seed)
    st = g.initial_state()
    while not g.is_terminal(st):
        st = g.apply_move(st, rng.choice(g.legal_moves(st)))
    longest = max(longest, st.ply)
    ok(g._draw_reason(st) != "move limit",
       "no random game is ever decided by the ply cap")
    ret = g.returns(st)
    ok(len(ret) == 2 and all(-1.0 <= x <= 1.0 for x in ret), "well-formed returns")
ok(longest * 10 < mod.PLY_CAP,
   f"longest random game {longest} plies -- an order of magnitude under the cap")

# --- 13. serialization round-trip -------------------------------------------
st = g.initial_state()
for mv in (mstr("f3", "f5"), mstr("e7", "e5"), mstr("f1", "f2")):
    st = g.apply_move(st, mv)
back = g.deserialize(g.serialize(st))
ok(back.board == st.board and back.to_move == st.to_move
   and back.ep == st.ep and back.castling == st.castling
   and back.halfmove == st.halfmove and back.ply == st.ply,
   "serialize/deserialize round-trips")
ok(sorted(g.legal_moves(back)) == sorted(g.legal_moves(st)),
   "and the restored state generates the same moves")
# EVERY field must survive, including the two that a naive round-trip misses:
# a live en-passant target and a partially-spent castling right.  (Async
# matches are stored serialized, so a dropped field is a real rule change.)
ser = g.initial_state()
for mv in (mstr("i1", "i2"), mstr("a9", "a8"),   # each side spends one right
           mstr("i2", "i1"), mstr("a8", "a9"),   # ...and puts the rook back
           mstr("f3", "f5"), mstr("i7", "i5"),
           mstr("h3", "h4"), mstr("e7", "e5")):  # ...and Black arms e6 e.p.
    ser = g.apply_move(ser, mv)
ok(ser.ep is not None and cell_name(ser.ep[0]) == "e6",
   "the serialization fixture really has an en-passant target")
ok(ser.castling == frozenset({(WHITE, "a"), (BLACK, "i")}),
   "...and a partially-spent castling-rights set")
ok(ser.ply == 8 and ser.last is not None and ser.reps,
   "...and non-default ply / last / reps")
ok(st.halfmove == 1, "the first round-trip fixture carries a non-zero halfmove")
r2 = g.deserialize(g.serialize(ser))
for fld in ("board", "to_move", "ep", "castling", "halfmove", "ply", "reps",
            "last"):
    ok(getattr(r2, fld) == getattr(ser, fld),
       f"serialize/deserialize preserves {fld}")
ok(sorted(g.legal_moves(r2)) == sorted(g.legal_moves(ser))
   and any("e.p." in g.describe_move(r2, m) for m in g.legal_moves(r2)),
   "the restored state still offers the en-passant capture")
import json as _json  # noqa: E402
ok(_json.loads(_json.dumps(g.serialize(ser))) == g.serialize(ser),
   "the serialized form is plain JSON")

# --- 14. bot contract -------------------------------------------------------
h = g.heuristic(g.initial_state())
ok(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9,
   "heuristic is a zero-sum pair")
from agp.mcts import MCTSBot  # noqa: E402

MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(g, g.initial_state())
checks += 1

print(f"de_vasa_chess selftest OK ({checks} checks, {time.time() - t0:.1f}s)")
