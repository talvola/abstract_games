"""Selftest for Brusky's Hexagonal Chess (pure stdlib; run from engine/):

    PYTHONPATH=. python3 games/brusky_chess/selftest.py

Correctness anchors
-------------------
1. THE FIVE PIECE DIAGRAMS.  chessvariants.com/rules/bruskyshexagonalchess
   illustrates every piece with a diagram whose position is embedded in the
   page's drawdiagram.php `code=` parameter.  All five are decoded here and
   reproduced cell for cell, and the board SHAPE is re-derived from their
   off-board markers.  The pawn one is

     ---9/--8p1/-2k5!!1/1{b+#}##{r+#}3!1!1/2P3{n+#}1q1#1/6p1##1-/5P2P1--/9---

   = White Pc4 Pf2 Pi2 / Black Kd6 Bb5 Re5 Ng4 Qi4 Pg3 Pk7, with 8 cells marked
   for White's pawns and 4 for Black's k7 pawn.  All 12 marked cells are
   reproduced EXACTLY, together with the four negatives the article calls out:
   c4 does not attack the d6 king, k7 cannot reach j5, f2 can advance to
   NEITHER f3 nor f4 (which is what proves cross-blocking kills the double step
   in the open direction too), and i2 cannot reach i4.
   The King (12 cells), Rook (25) and Knight (12) diagrams match exactly.  The
   Bishop and Queen diagrams each omit ONE cell -- i1, the last cell of the
   fully slanting f4-g3-h2 diagonal -- which contradicts the article's own rules
   text and its Rook diagram; see rules.md.  That erratum is pinned in
   DIAGRAM_ERRATA so a real regression cannot hide behind it.
2. THE PRITCHARD GAME FRAGMENT quoted in the same article (O. Yefimov -
   Ya. Brusky): a white pawn on j2 plays j2-l4 although Black has a pawn on j4,
   and Black answers j4xk3 en passant.
3. DIFFERENTIALS (one-time, 2026-07-25; NOT rerun here -- they need the scratch
   oracles -- the perft numbers below freeze the same behaviour instead).
   (a) vs an independent reimplementation of Jocly's ruleset: 88,821 positions
       (85,939 self-play + 2,882 scrambled), 0 legal-move-set differences once
       Jocly's two documented bugs are corrected; every one of the 43,374 raw
       divergences traced to exactly those two bugs (pawn cross-blocking,
       queen-side castling distance).
   (b) vs a from-scratch QA implementation built only from the article text and
       the decoded diagrams, with its en-passant right derived from the MOVE
       HISTORY rather than this engine's `ep` field: 43,663 positions,
       0 differences, plus an exhaustive sweep of all 228 geometrically
       possible en-passant configurations (76 with a decoy pawn on the other
       cell behind the target), 0 differences.
   (c) geometry re-derived from raw hexagon polygons at the renderer's own
       x = sqrt(3)(q + r/2), y = 1.5r: all of ORTHO / DIAG / KNIGHT identical.
4. PERFT (frozen regression baselines): 61 / 3,583 / 217,683 from the initial
   position, and 46 / 1,155 / 47,625 / 1,376,153 from a constructed endgame
   that exercises castling both ways, promotion and en passant.
5. Constructed positions: castling geometry and rights, castling through
   check, promotion choices, the starting-rank-only vertical capture (for the
   right colour), enemy-vs-friendly blocker asymmetry, checkmate, stalemate =
   draw, bare kings, threefold repetition, the 50-move rule, notation,
   serialization round-trips, and the RenderSpec's exact shape (render() is not
   exercised by `validate`, and a malformed spec white-screens the board).
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
BState = mod.BState
CELLS = mod.CELLS
cn = mod.cell_name
n2c = mod.name_to_cell
WHITE, BLACK = mod.WHITE, mod.BLACK

t0 = time.time()
checks = 0


def ok(cond, msg):
    global checks
    assert cond, msg
    checks += 1


def state(white="", black="", to_move=WHITE, castling="", ep=None):
    """Build a position from "Kf1 Ra1 Pe2"-style strings."""
    board = {}
    for pl, spec in ((WHITE, white), (BLACK, black)):
        for tok in spec.split():
            board[n2c(tok[1:])] = (pl, tok[0])
    epv = None
    if ep:
        epv = (n2c(ep[0]), n2c(ep[1]))
    return BState(board=board, to_move=to_move, castling=frozenset(castling), ep=epv)


def moves(st, frm=None):
    """Legal moves as notation strings, optionally only from cell `frm`."""
    out = []
    for m in g.legal_moves(st):
        body, _, promo = m.partition("=")
        a, b = body.split(">")
        if frm is not None and mod._cell(a) != n2c(frm):
            continue
        out.append(cn(mod._cell(b)) + (f"={promo}" if promo else ""))
    return sorted(out)


def play(st, *names):
    """Play a sequence of "from-to[=P]" moves given in Brusky notation."""
    for n in names:
        body, _, promo = n.partition("=")
        a, b = body.split("-")
        mv = f"{n2c(a)[0]},{n2c(a)[1]}>{n2c(b)[0]},{n2c(b)[1]}" + (f"={promo}" if promo else "")
        assert mv in g.legal_moves(st), f"{n} illegal (have {moves(st, a)})"
        st = g.apply_move(st, mv)
    return st


# --------------------------------------------------------------------------
# 0. Board geometry: 84 cells, the published file lengths, three colours
# --------------------------------------------------------------------------
ok(len(CELLS) == 84, f"board has {len(CELLS)} cells, expected 84")
lens = {}
for q, r in CELLS:
    lens.setdefault(mod.FILES[q], []).append(-r)
expect_files = {"a": (1, 5), "b": (1, 6), "c": (1, 7), "d": (1, 8), "e": (1, 8),
                "f": (1, 8), "g": (1, 8), "h": (1, 8), "i": (1, 8), "j": (2, 8),
                "k": (3, 8), "l": (4, 8)}
ok(set(lens) == set(expect_files), "files a..l")
for f, (lo, hi) in expect_files.items():
    rs = sorted(lens[f])
    ok(rs == list(range(lo, hi + 1)), f"file {f} spans {lo}-{hi}, got {rs}")
ok(len({(q - r) % 3 for q, r in CELLS}) == 3, "three cell colours")
# every orthogonal/diagonal step preserves rank arithmetic sanity: the six
# orthogonals are the six axial neighbours, and each diagonal is the sum of two
# adjacent orthogonals (so diagonals preserve the colour class).
ok(all(((dq - dr) % 3) == 0 for dq, dr in mod.DIAG), "diagonals are colourbound")
ok(sum(1 for d in mod.ORTHO if ((d[0] - d[1]) % 3) == 0) == 0,
   "no orthogonal step keeps the colour class")

# --------------------------------------------------------------------------
# 1. Initial position: setup, symmetry, and the hand-derived move count
# --------------------------------------------------------------------------
s0 = g.initial_state()
back = {cn(c): v[1] for c, v in s0.board.items() if v[0] == WHITE and c[1] == -1}
ok(back == {"a1": "R", "b1": "N", "c1": "B", "d1": "Q", "e1": "B", "f1": "K",
            "g1": "B", "h1": "N", "i1": "R"}, f"White's first rank: {back}")
bback = {cn(c): v[1] for c, v in s0.board.items() if v[0] == BLACK and c[1] == -8}
ok(bback == {"d8": "R", "e8": "N", "f8": "B", "g8": "K", "h8": "B", "i8": "Q",
             "j8": "B", "k8": "N", "l8": "R"}, f"Black's eighth rank: {bback}")
ok(sorted(cn(c) for c, v in s0.board.items() if v == (WHITE, "P"))
   == ["a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2", "i2", "j2"], "White pawns a2-j2")
ok(sorted(cn(c) for c, v in s0.board.items() if v == (BLACK, "P"))
   == ["c7", "d7", "e7", "f7", "g7", "h7", "i7", "j7", "k7", "l7"], "Black pawns c7-l7")
# 180-degree rotational symmetry: (q,r) -> (11-q, -9-r)
ok(all(s0.board.get((11 - q, -9 - r)) == (1 - o, t)
       for (q, r), (o, t) in s0.board.items()), "setup has 180-degree symmetry")
# the kings really do sit on opposite wings
ok(cn(mod._king_cell(s0.board, WHITE)) == "f1"
   and cn(mod._king_cell(s0.board, BLACK)) == "g8", "kings f1 / g8 (opposite wings)")
# three bishops a side, one per colour
for pl in (WHITE, BLACK):
    cols = sorted((q - r) % 3 for (q, r), v in s0.board.items() if v == (pl, "B"))
    ok(cols == [0, 1, 2], f"player {pl} has one bishop of each colour, got {cols}")

n0 = len(g.legal_moves(s0))
ok(n0 == 61, f"61 opening moves (40 pawn + 8 knight + 9 bishop + 3 queen + 1 king), got {n0}")
by = {}
for m in g.legal_moves(s0):
    by[s0.board[mod._cell(m.split(">")[0])][1]] = by.get(
        s0.board[mod._cell(m.split(">")[0])][1], 0) + 1
ok(by == {"P": 40, "N": 8, "B": 9, "Q": 3, "K": 1}, f"opening moves by piece: {by}")
# each pawn has exactly 2 single + 2 double steps; both bishops' and the
# queen's vertical diagonals leap the pawn wall (ranks 1-3-5-7)
ok(moves(s0, "c1") == ["d3", "e5", "f7"], f"c1 bishop: {moves(s0, 'c1')}")
ok(moves(s0, "d1") == ["e3", "f5", "g7"], f"d1 queen: {moves(s0, 'd1')}")
ok(moves(s0, "e2") == ["e3", "e4", "f3", "g4"], f"e2 pawn: {moves(s0, 'e2')}")

# --------------------------------------------------------------------------
# 2. THE PAWN DIAGRAM (chessvariants.com), cell by cell
# --------------------------------------------------------------------------
DIAG_W = "Kb1 Pc4 Pf2 Pi2"          # Kb1 added: the diagram omits White's king
DIAG_B = "Kd6 Bb5 Re5 Ng4 Qi4 Pg3 Pk7"
w = state(DIAG_W, DIAG_B, WHITE)
b = state(DIAG_W, DIAG_B, BLACK)
ok(not mod._in_check(w.board, WHITE) and not mod._in_check(w.board, BLACK),
   "diagram position: neither king is in check (the c4 pawn does NOT attack d6)")
ok(moves(w, "c4") == ["b5", "c5", "d5", "e5"],
   f"c4 pawn: two forward steps + two slant captures, got {moves(w, 'c4')}")
ok("d6" not in moves(w, "c4"), "c4 does not capture vertically (it has left its home rank)")
ok(moves(w, "f2") == ["g4"],
   f"f2 pawn: cross-blocked by the enemy g3 pawn, only the vertical capture "
   f"of the g4 knight, got {moves(w, 'f2')}")
ok(moves(w, "i2") == ["i3", "j3", "k4"],
   f"i2 pawn: i4 blocked by the queen but the k4 double step stands, "
   f"got {moves(w, 'i2')}")
ok(moves(b, "k7") == ["i5", "j6", "k5", "k6"],
   f"k7 pawn: both single steps and both same-direction double steps, "
   f"got {moves(b, 'k7')}")
ok("j5" not in moves(b, "k7"), "k7's double step may not change direction (no j5)")
ok(moves(b, "g3") == [], "g3 pawn: cross-blocked by the enemy f2 pawn, no moves")
marked_white = sorted(set(moves(w, "c4") + moves(w, "f2") + moves(w, "i2")))
ok(marked_white == ["b5", "c5", "d5", "e5", "g4", "i3", "j3", "k4"],
   f"the diagram's 8 '#' cells: {marked_white}")
ok(moves(b, "k7") == ["i5", "j6", "k5", "k6"], "the diagram's 4 '!' cells")
# The double step in the OPEN direction is blocked too.  The diagram proves it:
# f2 is cross-blocked by the enemy g3 pawn and neither f3 (single, open
# direction) NOR f4 (double, open direction) is marked.
ok("f3" not in moves(w, "f2") and "f4" not in moves(w, "f2")
   and "h4" not in moves(w, "f2"),
   f"cross-blocking kills the DOUBLE step in the open direction too: {moves(w, 'f2')}")

# --------------------------------------------------------------------------
# 2b. THE OTHER FOUR PIECE DIAGRAMS on the same page, decoded from their own
#     drawdiagram.php `code=` parameters and checked cell by cell.  Each shows
#     the piece alone on f4.  The board SHAPE is re-derived here from the
#     diagrams' own off-board markers ('-'), independently of on_board().
# --------------------------------------------------------------------------
import re  # noqa: E402

DIAGRAMS = {   # percent-decoding already applied ('%2F'->'/', '%23'->'#')
    "king":   "---9/--10/-5#5/4####4/4#K#5/3####4-/4#5--/9---",
    "rook":   "---2#3#2/--3#2#3/-4#1#4/5##5/#####R######/4##5-/3#1#4--/2#2#3---",
    "bishop": "---4#4/--#8#/-2#2#2#2/4#2#4/5B6/3#2#4-/1#2#2#2--/9---",
    "queen":  "---2#1#1#2/--#2#2#2#/-2#1###1#2/4####4/#####Q######/3####4-/1#1###1#2--/2#2#3---",
    "knight": "---9/--4##4/-3#3#3/3#4#3/5N6/2#4#3-/2#3#3--/3##4---",
}


def decode(code):
    """Game-Courier diagram code -> (pieces, marked cells, off-board cells).
    Rows run rank 8 first; '-' = off board, digits = a run of empty cells,
    '#'/'!' = a marked empty cell, a letter = a piece."""
    rows = code.split("/")
    assert len(rows) == 8, code
    pieces, marks, off = {}, set(), set()
    for ri, row in enumerate(rows):
        rank = 8 - ri
        q = 0
        for tok in re.findall(r"\d+|.", row):
            if tok.isdigit():
                q += int(tok)
            elif tok == "-":
                off.add((q, -rank)); q += 1
            elif tok in "#!":
                marks.add((q, -rank)); q += 1
            else:
                pieces[(q, -rank)] = tok; q += 1
        assert q == 12, f"{rank}: {row!r} -> {q} columns"
    return pieces, marks, off


_, _, off = decode(DIAGRAMS["king"])
ok({(q, -rk) for q in range(12) for rk in range(1, 9)} - off == set(CELLS),
   "the board shape re-derived from the diagrams' off-board markers is our 84 cells")

# The article's BISHOP and QUEEN diagrams each stop the fully-slanting f4-g3-h2
# diagonal one cell short of the board's bottom-right corner: i1 is reachable
# (the rules text says "any number of spaces in any diagonal direction until it
# reaches an occupied space", and the ROOK diagram traces its rays to the edge
# in that same corner) but is left unmarked.  A diagram slip, not a rule -- we
# follow the text, so i1 IS generated.  Recorded so a regression can't hide.
DIAGRAM_ERRATA = {"bishop": {"i1"}, "queen": {"i1"}}

for pname, code in DIAGRAMS.items():
    pieces, marks, _ = decode(code)
    (frm, letter), = [(c, t) for c, t in pieces.items() if t.isupper()]
    ok(cn(frm) == "f4", f"{pname} diagram: the piece stands on f4, got {cn(frm)}")
    if letter == "K":
        # the f4 piece IS White's king; a spare black pawn on l7 keeps the
        # position off the bare-kings auto-draw (its l7 capture cells j6/k5 are
        # nowhere near f4, so the king's 12 steps are untouched)
        st = state(f"K{cn(frm)}", "Kl8 Pl7", WHITE)
    else:
        st = state(f"Ka1 {letter}{cn(frm)}", "Kl8", WHITE)
    got = set(moves(st, cn(frm)))
    want = {cn(c) for c in marks} | DIAGRAM_ERRATA.get(pname, set())
    ok(got == want,
       f"{pname} diagram reproduced cell for cell: engine-only "
       f"{sorted(got - want)}, diagram-only {sorted(want - got)}")
ok(sum(len(decode(c)[1]) for c in DIAGRAMS.values()) == 12 + 25 + 13 + 38 + 12,
   "the five diagrams mark 100 cells in total")

# --------------------------------------------------------------------------
# 3. Enemy-vs-friendly blocker asymmetry (the rule Ludii and Jocly get wrong)
# --------------------------------------------------------------------------
free = state("Kb1 Pe2", "Kd8", WHITE)
ok(moves(free, "e2") == ["e3", "e4", "f3", "g4"], "unobstructed home pawn: 4 moves")
friendly = state("Kb1 Pe2 Nf3", "Kd8", WHITE)          # friend on the NE step
ok(moves(friendly, "e2") == ["e3", "e4"],
   f"a FRIENDLY blocker stops only its own direction, got {moves(friendly, 'e2')}")
enemy = state("Kb1 Pe2", "Kd8 Nf3", WHITE)             # enemy on the NE step
ok(moves(enemy, "e2") == [],
   f"an ENEMY blocker stops BOTH forward directions -- and a pawn never "
   f"captures forward orthogonally, so e2 is frozen, got {moves(enemy, 'e2')}")
enemy2 = state("Kb1 Pe2", "Kd8 Ne3", WHITE)            # enemy on the NW step
ok(moves(enemy2, "e2") == [], f"enemy blocker the other way: {moves(enemy2, 'e2')}")
enemy3 = state("Kb1 Pe2", "Kd8 Nf3 Bf4", WHITE)        # blocked, but a capture exists
ok(moves(enemy3, "e2") == ["f4"],
   f"cross-blocking stops ADVANCES only: the vertical capture e2xf4 survives, "
   f"got {moves(enemy3, 'e2')}")
far = state("Kb1 Pe2", "Kd8 Ne4", WHITE)               # enemy two cells away
ok(moves(far, "e2") == ["e3", "f3", "g4"],
   f"a NON-adjacent enemy blocks only its own cell, got {moves(far, 'e2')}")

# --------------------------------------------------------------------------
# 4. The vertical (fully forward) diagonal capture: home rank only, own colour
# --------------------------------------------------------------------------
home = state("Kb1 Pe2", "Kd8 Nf4", WHITE)
ok("f4" in moves(home, "e2"), "a home-rank white pawn captures straight up (e2xf4)")
moved = state("Kb1 Pe3", "Kd8 Nf5", WHITE)
ok("f5" not in moves(moved, "e3"),
   f"a pawn off its home rank has no vertical capture, got {moves(moved, 'e3')}")
bhome = state("Kb1 Nd5", "Kl4 Pe7", BLACK)
ok("d5" in moves(bhome, "e7"),
   f"a home-rank black pawn (rank 7) captures straight down (e7xd5), "
   f"got {moves(bhome, 'e7')}")
bmoved = state("Kb1 Nc4", "Kl4 Pd6", BLACK)
ok("c4" not in moves(bmoved, "d6"),
   f"...but not once it has left rank 7, got {moves(bmoved, 'd6')}")
# The home rank is COLOUR-specific (White rank 2 / Black rank 7).  The mirror
# cases are geometrically unobservable -- a black pawn on rank 2 would double-
# step or capture vertically onto rank 0, a white pawn on rank 7 onto rank 9 --
# so the distinction can only be asserted structurally:
ok(mod.HOME_RANK[WHITE] == -2 and mod.HOME_RANK[BLACK] == -7,
   "home ranks are per colour")
ok(all((q, 0) not in CELLS and (q, -9) not in CELLS for q in range(12)),
   "ranks 0 and 9 do not exist, so a wrong-colour home rank has no visible effect")
# the vertical direction is also an ATTACK for check purposes, from home only
ok(mod._attacked(state("Pe2", "").board, n2c("f4"), WHITE), "home pawn attacks f4")
ok(not mod._attacked(state("Pe3", "").board, n2c("f5"), WHITE),
   "a moved pawn does not attack vertically")

# --------------------------------------------------------------------------
# 5. Promotion
# --------------------------------------------------------------------------
promo = state("Kb1 Pe7", "Kl4", WHITE)
ok(moves(promo, "e7") == ["e8=B", "e8=N", "e8=Q", "e8=R", "f8=B", "f8=N", "f8=Q",
                          "f8=R"], f"promotion on the far rank: {moves(promo, 'e7')}")
st = play(promo, "e7-f8=N")
ok(st.board[n2c("f8")] == (WHITE, "N"), "promotion piece actually placed")
bpromo = state("Kl4", "Kb8 Pd2", BLACK)
ok(moves(bpromo, "d2") == ["c1=B", "c1=N", "c1=Q", "c1=R", "d1=B", "d1=N", "d1=Q",
                           "d1=R"], f"Black promotes on rank 1: {moves(bpromo, 'd2')}")
# a pawn one step short does NOT get a promotion suffix
ok(moves(state("Kb1 Pe6", "Kl4", WHITE), "e6") == ["e7", "f7"], "no premature promotion")

# --------------------------------------------------------------------------
# 6. En passant -- the Yefimov-Brusky fragment quoted by chessvariants.com:
#    "a White Pawn on j2 moved to l4 even though Black had a Pawn on j4.  After
#     White's move, Black captured White's Pawn by en passant, from j4 to k3."
# --------------------------------------------------------------------------
frag = state("Kb1 Pj2", "Kd8 Pj4", WHITE)
ok("j4" not in moves(frag, "j2"), "j2 cannot double-step into the occupied j4")
ok("l4" in moves(frag, "j2"),
   f"j2-l4 legal: the j4 blocker is not adjacent, so it does not cross-block, "
   f"got {moves(frag, 'j2')}")
after = play(frag, "j2-l4")
ok(after.ep is not None and cn(after.ep[0]) == "k3" and cn(after.ep[1]) == "l4",
   "the skipped cell k3 becomes the en-passant target")
ok("k3" in moves(after, "j4"), f"j4 may capture en passant on k3: {moves(after, 'j4')}")
final = play(after, "j4-k3")
ok(n2c("l4") not in final.board and final.board[n2c("k3")] == (BLACK, "P"),
   "en passant removes the pawn on l4 and lands the capturer on k3")
ok(final.ep is None, "the en-passant right lasts exactly one ply")
# ...and it expires if not taken immediately
lapse = play(state("Kb1 Pj2", "Kd8 Pj4 Rl8", WHITE), "j2-l4", "l8-k8", "b1-c1")
ok("k3" not in moves(lapse, "j4"), "the en-passant chance is gone a move later")
# a double step in the OTHER direction sets a different target cell
other = play(state("Kb1 Pj2", "Kd8", WHITE), "j2-j4")
ok(cn(other.ep[0]) == "j3", "the NW double step skips j3, not k3")
# ...and the VERTICAL-diagonal capture also spans two ranks but is NOT a double
# step, so it must create no en-passant right at all
vert = play(state("Kb1 Pe2", "Kl8 Nf4 Pd4", WHITE), "e2-f4")
ok(vert.ep is None,
   f"a vertical-diagonal capture (e2xf4) creates no en-passant right, got {vert.ep}")
ok("e3" not in moves(vert, "d4"),
   f"...so the d4 pawn cannot 'capture en passant' on e3, got {moves(vert, 'd4')}")
# the victim of an en-passant capture is the recorded pawn, not whichever pawn
# happens to sit behind the target: BOTH cells behind f6 (e5 and f5) can hold a
# black pawn, and g7-e5 makes e5 -- not f5 -- the victim
amb = play(state("Kb1 Pd5", "Kl8 Pg7 Pf5", BLACK), "g7-e5")
ok(cn(amb.ep[0]) == "f6" and cn(amb.ep[1]) == "e5", "ep target f6, victim e5")
amb = play(amb, "d5-f6")
ok(n2c("e5") not in amb.board and amb.board[n2c("f5")] == (BLACK, "P")
   and amb.board[n2c("f6")] == (WHITE, "P"),
   "en passant removes e5 and leaves the unrelated f5 pawn standing")

# --------------------------------------------------------------------------
# 7. Castling: 2 cells king's side, 3 cells queen's side
# --------------------------------------------------------------------------
# (Black is only a lone king here: a black rook on l8 rakes the whole
# l8-k7-j6-i5-h4-g3-f2-e1 orthogonal and would attack White's castling path.)
cas = state("Kf1 Ra1 Ri1", "Kl8", WHITE, "KQ")
ok(moves(cas, "f1") == ["c1", "e1", "e2", "f2", "g1", "g2", "g3", "h1", "h2"],
   f"White king: 7 one-cell steps + O-O (h1) + O-O-O (c1), got {moves(cas, 'f1')}")
oo = play(cas, "f1-h1")
ok(oo.board[n2c("h1")] == (WHITE, "K") and oo.board[n2c("g1")] == (WHITE, "R")
   and n2c("i1") not in oo.board, "O-O: Kf1-h1 (two cells), Ri1-g1")
ooo = play(cas, "f1-c1")
ok(ooo.board[n2c("c1")] == (WHITE, "K") and ooo.board[n2c("d1")] == (WHITE, "R")
   and n2c("a1") not in ooo.board, "O-O-O: Kf1-c1 (three cells), Ra1-d1")
bcas = state("Ka1", "Kg8 Rd8 Rl8", BLACK, "kq")
ok(moves(bcas, "g8") == ["e7", "e8", "f6", "f7", "f8", "g7", "h7", "h8", "j8"],
   f"Black king: 7 steps + O-O (e8) + O-O-O (j8), got {moves(bcas, 'g8')}")
boo = play(bcas, "g8-e8")
ok(boo.board[n2c("e8")] == (BLACK, "K") and boo.board[n2c("f8")] == (BLACK, "R")
   and n2c("d8") not in boo.board, "Black O-O: Kg8-e8, Rd8-f8")
booo = play(bcas, "g8-j8")
ok(booo.board[n2c("j8")] == (BLACK, "K") and booo.board[n2c("i8")] == (BLACK, "R")
   and n2c("l8") not in booo.board, "Black O-O-O: Kg8-j8 (three cells), Rl8-i8")
ok(g.describe_move(cas, "5,-1>7,-1") == "O-O"
   and g.describe_move(cas, "5,-1>2,-1") == "O-O-O", "castling notation")
# rights
ok("c1" not in moves(state("Kf1 Ra1 Ri1", "Kl8", WHITE, "K"), "f1"),
   "no queen's-side castling without the right")
moved_r = play(cas, "a1-b1", "l8-k8", "b1-a1", "k8-l8")
ok("c1" not in moves(moved_r, "f1") and "h1" in moves(moved_r, "f1"),
   "moving the a1 rook and back kills only queen's-side castling")
moved_k = play(cas, "f1-g1", "l8-k8", "g1-f1", "k8-l8")
ok("c1" not in moves(moved_k, "f1") and "h1" not in moves(moved_k, "f1"),
   "a king move kills both rights")
capt = play(state("Kf1 Ra1 Ri1 Pe2", "Kl8 Nb4", WHITE, "KQ"), "e2-e3", "b4-a1")
ok("Q" not in capt.castling and "K" in capt.castling,
   f"a rook captured on its home cell loses that right: {sorted(capt.castling)}")
# blockers and check
ok("c1" not in moves(state("Kf1 Ra1 Ri1 Nb1", "Kl8", WHITE, "KQ"), "f1"),
   "a piece between king and rook forbids castling")
ok("h1" not in moves(state("Kf1 Ra1 Ri1", "Kl8 Rh4", WHITE, "KQ"), "f1"),
   "the king may not pass through an attacked cell (rook on h4 covers h1)")
ok("c1" not in moves(state("Kf1 Ra1 Ri1", "Kl8 Rd4", WHITE, "KQ"), "f1"),
   "queen's-side transit cell d1 attacked -> no castling")
incheck = state("Kf1 Ra1 Ri1", "Kl8 Rf4", WHITE, "KQ")
ok("c1" not in moves(incheck, "f1") and "h1" not in moves(incheck, "f1"),
   "a king in check may not castle")
# the cell the ROOK crosses (b1) being attacked is fine, as in orthodox chess
ok("c1" in moves(state("Kf1 Ra1 Ri1", "Kl8 Rb4", WHITE, "KQ"), "f1"),
   "an attacked b1 (rook transit only) does not forbid queen's-side castling")

# --------------------------------------------------------------------------
# 8. Checkmate, stalemate, bare kings, repetition, 50-move rule
# --------------------------------------------------------------------------
mate = play(state("Kk3 Qb6", "Kl8", WHITE), "b6-j6")
ok(g.is_terminal(mate) and g.returns(mate) == [1.0, -1.0],
   f"Qj6 is checkmate (a lone queen mates in the 5-neighbour corner l8): "
   f"{g.returns(mate)}")
ok(g.describe_move(state("Kk3 Qb6", "Kl8", WHITE), "1,-6>9,-6") == "Qb6-j6#",
   "mate is marked '#' in the move log")
stale = play(state("Kl4 Qi7", "Kl8", WHITE), "l4-l5")
ok(g.is_terminal(stale) and not mod._in_check(stale.board, BLACK),
   "Kl5 stalemates the l8 king")
ok(g.returns(stale) == [0.0, 0.0], f"STALEMATE IS A DRAW: {g.returns(stale)}")
ok(g._draw_reason(mate) is None,
   "a checkmate is not overridden by any draw counter")
# ...specifically: the mating move may also be the 100th reversible ply
late = state("Kk3 Qb6", "Kl8", WHITE)
late.halfmove = 99
late = play(late, "b6-j6")
ok(late.halfmove == 100 and g.is_terminal(late) and g.returns(late) == [1.0, -1.0],
   f"checkmate beats the 50-move rule on the same ply: {g.returns(late)}")
bare = state("Kf1", "Kl8", WHITE)
ok(g.is_terminal(bare) and g.returns(bare) == [0.0, 0.0], "bare kings = draw")
ok(not g.is_terminal(state("Kf1 Ne1", "Kl8", WHITE)), "K+N vs K is still played on")
# ...and it MUST be played on: unlike orthodox chess, K+minor vs K is NOT a dead
# position here -- a corner cell has only five king-neighbours, so a lone knight
# or bishop really can deliver mate.  (Jocly auto-draws these; that is a bug.)
for mater, mate_pos in (("N", "Kc5 Nb3"), ("B", "Kc5 Bb4")):
    m = state(mate_pos, "Ka5", BLACK)
    ok(mod._in_check(m.board, BLACK) and g.is_terminal(m)
       and g.returns(m) == [1.0, -1.0],
       f"K+{mater} vs K checkmate exists on this board ({mate_pos} vs Ka5#): "
       f"{g.returns(m)}")
    ok(g._draw_reason(m) is None,
       f"K+{mater} vs K is not auto-drawn as insufficient material")
# threefold repetition
rep = state("Kf1 Ra1", "Kl8 Rd8", WHITE)
rep.reps = {mod._poskey(rep.board, rep.to_move, rep.castling, rep.ep): 1}
rep = play(rep, "a1-b1", "d8-e8", "b1-a1", "e8-d8",
           "a1-b1", "d8-e8", "b1-a1", "e8-d8")
ok(g.is_terminal(rep) and g._draw_reason(rep) == "threefold repetition",
   f"threefold repetition draws: {g._draw_reason(rep)}")
ok(g.returns(rep) == [0.0, 0.0], "repetition scores 0-0")
# 50-move rule: 100 reversible plies
fifty = state("Kf1 Ra1", "Kl8 Rd8", WHITE)
seq = ["a1-b1", "d8-e8", "b1-a1", "e8-d8"]
st = fifty
for i in range(100):
    st = play(st, seq[i % 4])
    st.reps = {}                      # isolate the 50-move rule from repetition
ok(st.halfmove == 100 and g._draw_reason(st) == "50-move rule",
   f"50-move rule after 100 reversible plies: {st.halfmove} {g._draw_reason(st)}")
ok(g.is_terminal(st) and g.legal_moves(st) == [], "a drawn game has no moves")
# a pawn move / capture resets the counter
resetp = play(state("Kf1 Ra1 Pe2", "Kl8", WHITE), "a1-b1", "l8-k8", "e2-e3")
ok(resetp.halfmove == 0, "a pawn move resets the 50-move counter")
# the hard ply cap is a backstop only: it is far above the 50-move bound
ok(mod.PLY_CAP > 156 + 157 * 100,
   f"PLY_CAP {mod.PLY_CAP} must exceed the 15,856-ply 50-move bound "
   f"(so it can never decide a game)")

# --------------------------------------------------------------------------
# 9. Notation, rendering, serialization
# --------------------------------------------------------------------------
ok(cn(n2c("a1")) == "a1" and cn(n2c("l8")) == "l8" and n2c("c4") == (2, -4),
   "cell-name round trip")
ok(g.describe_move(s0, "4,-2>4,-4") == "e2-e4", "pawn double-step notation")
ok(g.describe_move(w, "5,-2>6,-4") == "f2xg4", "capture notation")
ok(g.describe_move(after, "9,-4>10,-3") == "j4xk3 e.p.", "en-passant notation")
import json  # noqa: E402
# render() is NOT exercised by validate, and a malformed RenderSpec white-screens
# the board, so check the SHAPE of every field -- on the initial position AND on
# a mid-game one that actually carries a last-move highlight.
mid = play(s0, "e2-e4", "k7-k5")
for tag, probe, npieces in (("initial", s0, 38), ("mid-game", mid, 38)):
    spec = g.render(probe)
    board = spec["board"]
    ids = board["cells"]
    ok(board["type"] == "hex" and isinstance(ids, list) and len(ids) == 84
       and all(isinstance(c, str) for c in ids),
       f"render[{tag}]: hex board with an explicit 84-cell axial id LIST")
    ok(set(ids) == {f"{q},{r}" for q, r in CELLS},
       f"render[{tag}]: the id list IS the 84-cell set")
    # a tint/label dict keyed by anything other than a cell id silently vanishes
    # in the browser, so assert the KEYS, not just the count
    ok(set(board["tints"]) == set(ids) and len(set(board["tints"].values())) == 3,
       f"render[{tag}]: tints keyed by cell id, three colours")
    ok(set(board) == {"type", "cells", "tints"},
       f"render[{tag}]: no stray board keys: {sorted(board)}")
    ok(len(spec["pieces"]) == npieces and spec.get("pieceset") == "chess",
       f"render[{tag}]: {npieces} pieces")
    ok(all(set(p) == {"cell", "owner", "label"} and p["cell"] in set(ids)
           and p["owner"] in (0, 1) and p["label"] in "PNBRQK" for p in spec["pieces"]),
       f"render[{tag}]: every piece has a valid cell/owner/label")
    ok(all(h["cell"] in set(ids) and h["kind"] == "last-move" for h in spec["highlights"]),
       f"render[{tag}]: highlights reference real cells")
    ok(isinstance(spec["caption"], str) and spec["caption"], f"render[{tag}]: caption")
    json.dumps(spec)
ok(len(g.render(s0)["highlights"]) == 0 and len(g.render(mid)["highlights"]) == 2,
   "render: the last move is highlighted (2 cells) only once a move has been made")
# Board.jsx draws a hex cell at y = 1.5*r and SVG y grows downwards, so r = -1
# (rank 1) must sit BELOW r = -8 (rank 8): White at the bottom.
ok(1.5 * -1 > 1.5 * -8, "rank 1 renders at the bottom for White")
for probe in (s0, after, mate, stale):
    snap = g.serialize(probe)
    json.dumps(snap)
    ok(g.serialize(g.deserialize(snap)) == snap, "serialize round-trips")
h = g.heuristic(state("Kf1 Qd1", "Kl8", WHITE))
ok(isinstance(h, list) and len(h) == 2 and h[0] > 0 > h[1], f"heuristic shape: {h}")

# --------------------------------------------------------------------------
# 9b. apply_move enforces legality (exhaustive over every from>to pair)
# --------------------------------------------------------------------------
for probe in (s0, w, cas):
    legal = set(g.legal_moves(probe))
    tried = 0
    for a in CELLS:
        for b_ in CELLS:
            for suffix in ("", "=Q", "=R", "=B", "=N"):
                mv = f"{a[0]},{a[1]}>{b_[0]},{b_[1]}{suffix}"
                tried += 1
                try:
                    g.apply_move(probe, mv)
                    accepted = True
                except Exception:
                    accepted = False
                if accepted != (mv in legal):
                    raise AssertionError(f"apply_move mismatch on {mv!r} "
                                         f"(legal={mv in legal})")
    ok(tried == 84 * 84 * 5, f"fuzzed {tried} move strings")
for junk in ("", "pass", "swap", "0,-1", "0,-1>", ">0,-1", "0,-1>0,-1>0,-2",
             "a,b>c,d", "0,-1>0,-2=X", "0,-1>0,-2=", "0,-1,0>0,-2", "99,-1>0,-2"):
    try:
        g.apply_move(s0, junk)
        raise AssertionError(f"apply_move accepted junk {junk!r}")
    except AssertionError:
        raise
    except Exception:
        pass
checks += 1

# --------------------------------------------------------------------------
# 10. PERFT (frozen regression baselines)
# --------------------------------------------------------------------------
def perft(st, d):
    if d == 0:
        return 1
    ms = g.legal_moves(st)
    if d == 1:
        return len(ms)
    return sum(perft(g.apply_move(st, m), d - 1) for m in ms)


for depth, expect in ((1, 61), (2, 3583), (3, 217683)):
    got = perft(s0, depth)
    ok(got == expect, f"perft({depth}) = {got}, expected {expect}")

# an endgame with castling both ways, promotion and en passant in the tree
END = state("Kf1 Ra1 Ri1 Pe2 Pd5 Pi7", "Kg8 Rd8 Rl8 Pc7 Pg3", WHITE, "KQkq")
for depth, expect in ((1, 46), (2, 1155), (3, 47625), (4, 1376153)):
    got = perft(END, depth)
    ok(got == expect, f"endgame perft({depth}) = {got}, expected {expect}")

print(f"brusky_chess selftest: {checks} checks passed in {time.time() - t0:.1f}s")
