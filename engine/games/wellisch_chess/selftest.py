"""Correctness anchors for Wellisch's Three-Handed Hexagonal Chess.

There is no perft and no solved value for this game, so the anchors are:

  1. the 1912 starting array, re-derived INDEPENDENTLY from Wellisch's own
     (letter, number) coordinates -- and again from the Ludii `.lud`, whose
     coordinate convention is pinned by re-deriving White's known array first;
  2. the 120 deg rotation invariant on `legal_moves` (White -> Black -> Red -> White);
  3. Wellisch's own worked movement examples, verbatim from the article;
  4. his colour rule (K yellow, Q red, R black, one knight of each colour) and
     the colour-boundness of the knight;
  5. the rules that random play will never reach: army takeover on king
     capture, delayed promotion, and "a decisive result outranks the draw
     counters" -- where the decisive event is KING CAPTURE, not checkmate.

Pure stdlib: imports only `agp` and this package's own `game.py`.
"""

import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                       # noqa: E402
from agp.mcts import MCTSBot                               # noqa: E402

MAN, G = load_from_dir(Path(__file__).resolve().parent)
# The live module object -- `load_from_dir` imports game.py under a SYNTHETIC
# module name, so `import games.wellisch_chess.game` would patch a DIFFERENT
# object and every "patched constant" test would be vacuous.
M = sys.modules[type(G).__module__]

WHITE, RED, BLACK = 0, 1, 2
checks = 0


def ok(cond, msg):
    global checks
    checks += 1
    assert cond, msg


def cid(c):
    return M.cell_id(c)


def blank(board, turn, **kw):
    d = dict(board=board, turn=turn, alive=(True, True, True), out=(),
             pool=((), (), ()), castling=(), reps={})
    d.update(kw)
    return M.WState(**d)


def dest_names(state, src_name):
    """Wellisch-coordinate destinations of every legal move from `src_name`."""
    out = set()
    for m in G.legal_moves(state):
        a, _, b = m.partition(">")
        b = b.split("=")[0]
        if M.cell_name(M.parse_cell(a)) == src_name:
            out.add(M.cell_name(M.parse_cell(b)))
    return sorted(out)


# ==========================================================================
# 1. The board
# ==========================================================================

def test_board():
    ok(len(M.CELLS) == 91, "hexagon of side 6 has 91 cells")
    census = {0: 0, 1: 0, 2: 0}
    for q, r in M.CELLS:
        census[M.cell_colour(q, r)] += 1
    # Wellisch p.324: 30 yellow, 31 black, 30 red.  1 = yellow, 2 = black, 0 = red.
    ok((census[1], census[2], census[0]) == (30, 31, 30), f"colour census {census}")
    ok(M.cell_colour(0, 0) == 2, "the centre cell f6 is black")
    # Wellisch's coordinates: letters a..l with NO 'j', numbers 1..11.
    ok(M.LETTERS == "abcdefghikl", "letter row names skip 'j'")
    ok(M.cell_name((-2, 5)) == "a4" and M.cell_name((5, -3)) == "i11"
       and M.cell_name((-3, -2)) == "h3", "axial -> Wellisch coordinate")
    # Every diagonal step preserves the cell colour (the knight is colour-bound,
    # which is exactly why each player needs three of them).
    for c in M.CELLS:
        for t in M.NB_D[c]:
            ok(M.cell_colour(*t) == M.cell_colour(*c), "diagonal step keeps colour")
        for t in M.NB_O[c]:
            ok(M.cell_colour(*t) != M.cell_colour(*c), "orthogonal step changes colour")


# ==========================================================================
# 2. The starting array -- three independent transcriptions
# ==========================================================================

# (a) Wellisch 1912 p.327 + Fig.5, in HIS OWN coordinates.  Converted here by
#     q = N - 6, r = 5 - L, so this is an independent path to the same array.
WELLISCH_ARRAY = {
    WHITE: "Na1 Ra2 Qa3 Ka4 Ra5 Na6 Pb1 Pb2 Pb3 Nb4 Pb5 Pb6 Pb7 Pc4 Pc5",
    BLACK: "Nf1 Rg2 Kh3 Qi4 Rk5 Nl6 Pe1 Pf2 Pg3 Nh4 Pi5 Pk6 Pl7 Pg4 Ph5",
    RED:   "Nf11 Rg11 Qh11 Ki11 Rk11 Nl11 Pe10 Pf10 Pg10 Nh10 Pi10 Pk10 Pl10 Pg9 Ph9",
}

# (b) Ludii "Wellisch Chess.lud" (Jay M. Coskey, 2020) `(start ...)` block, in
#     LUDII's own coordinates (column letter A..K, row number 1..11).  Ludii's
#     player 1 = North = White, player 2 = ESE = Black, player 3 = WSW = Red.
#     The conversion  q = colIndex - 5,  r = 6 - row  is PINNED by re-deriving
#     White's independently-known array with it first (test_array does that).
LUDII_ARRAY = {
    WHITE: "KD1 QC1 RB1 RE1 NA1 ND2 NF1 PA2 PB2 PC2 PD3 PE3 PE2 PF2 PG2",
    BLACK: "KC8 QD9 RB7 RE10 NA6 ND8 NF11 PA5 PB6 PC7 PD7 PE8 PE9 PF10 PG11",
    RED:   "KK9 QK8 RK10 RK7 NK11 NJ8 NK6 PJ11 PJ10 PJ9 PI8 PI7 PJ7 PJ6 PJ5",
}


def wellisch_cell(name):
    """Wellisch's 'a4' -> axial (q, r):  q = N - 6, r = 5 - L."""
    L = M.LETTERS.index(name[0])
    N = int(name[1:])
    return (N - 6, 5 - L)


def ludii_cell(name):
    """Ludii's 'D1' -> axial (q, r):  q = colIndex - 5, r = 6 - row."""
    col = "ABCDEFGHIJK".index(name[0])
    row = int(name[1:])
    return (col - 5, 6 - row)


def parse_army(spec, conv):
    men = {}
    for tok in spec.split():
        men[conv(tok[1:])] = tok[0]
    return men


def test_array():
    s0 = G.initial_state()
    ok(len(s0.board) == 45, "45 men on the board")
    for seat, spec in WELLISCH_ARRAY.items():
        men = parse_army(spec, wellisch_cell)
        ok(len(men) == 15, "15 men per player")
        ok(sorted(men.values()) == sorted("KQRRNNNPPPPPPPP"),
           "1 K, 1 Q, 2 R, 3 N, 8 P and NO bishops")
        for c, letter in men.items():
            ok(c in M.CELLSET, f"{c} on board")
            ok(s0.board.get(c) == (seat, letter, seat),
               f"seat {seat} {letter} on {M.cell_name(c)}")
    ok(sum(len(parse_army(v, wellisch_cell)) for v in WELLISCH_ARRAY.values()) == 45,
       "the three transcribed armies account for every man")
    # The Ludii array, through its own (independently pinned) coordinate system.
    for seat, spec in LUDII_ARRAY.items():
        for c, letter in parse_army(spec, ludii_cell).items():
            ok(s0.board.get(c) == (seat, letter, seat),
               f"Ludii disagrees on seat {seat} {letter} at {c}")
    # Ludii's three promotion zones, likewise.
    zones = {
        WHITE: [f"{c}11" for c in "ABCDEFGHIJK"[5:]],       # (sites Top) = row 11
        BLACK: ["K6", "J5", "I4", "H3", "G2", "F1"],
        RED:   ["A1", "A2", "A3", "A4", "A5", "A6"],
    }
    for seat, names in zones.items():
        for n in names:
            c = ludii_cell(n)
            if c in M.CELLSET:
                ok(M.is_promo_cell(seat, c), f"promotion zone {seat} {n}")
    # ... and nothing else is in them.
    for seat in (WHITE, RED, BLACK):
        n = sum(1 for c in M.CELLS if M.is_promo_cell(seat, c))
        ok(n == 6, f"promotion row of seat {seat} is 6 cells, got {n}")


def test_colour_rule():
    """Wellisch p.327: King on the YELLOW cell, Queen on the RED cell, both
    Rooks on BLACK cells, and the three Knights one per colour.  This rule is
    an embedding-free determinant of the K/Q handedness -- it is what proves
    the Oxford Companion's mirrored diagram wrong."""
    s0 = G.initial_state()
    YELLOW, BLACK_C, RED_C = 1, 2, 0
    for seat in (WHITE, RED, BLACK):
        cells = {l: [] for l in "KQRNP"}
        for c, (o, l, _h) in s0.board.items():
            if o == seat:
                cells[l].append(c)
        ok(M.cell_colour(*cells["K"][0]) == YELLOW, f"seat {seat} King on yellow")
        ok(M.cell_colour(*cells["Q"][0]) == RED_C, f"seat {seat} Queen on red")
        ok(all(M.cell_colour(*c) == BLACK_C for c in cells["R"]),
           f"seat {seat} Rooks on black")
        ok(sorted(M.cell_colour(*c) for c in cells["N"]) == [0, 1, 2],
           f"seat {seat} has one Knight of each colour")


# ==========================================================================
# 3. The 120 deg rotation invariant
# ==========================================================================

def rot_move(m):
    txt, _, promo = m.partition("=")
    a, _, b = txt.partition(">")
    ra, rb = M.rot120(M.parse_cell(a)), M.rot120(M.parse_cell(b))
    return f"{cid(ra)}>{cid(rb)}" + ("=" + promo if promo else "")


def test_rotation():
    s0 = G.initial_state()
    mv = {p: set(G.legal_moves(replace(s0, turn=p))) for p in (WHITE, RED, BLACK)}
    ok(len(mv[WHITE]) == 20, f"20 opening moves, got {len(mv[WHITE])}")
    # rot120 maps White -> Black -> Red -> White (armies, home edges, pawn
    # directions and therefore the whole legal-move set).
    ok({rot_move(m) for m in mv[WHITE]} == mv[BLACK], "rot120(White) == Black")
    ok({rot_move(m) for m in mv[BLACK]} == mv[RED], "rot120(Black) == Red")
    ok({rot_move(m) for m in mv[RED]} == mv[WHITE], "rot120(Red) == White")
    # ... and the rotation is an involution-free 3-cycle on the men themselves.
    for c, (o, l, h) in s0.board.items():
        rc = M.rot120(c)
        nxt = {WHITE: BLACK, BLACK: RED, RED: WHITE}[o]
        ok(s0.board.get(rc) == (nxt, l, nxt), f"rot120 image of {M.cell_name(c)}")
    for h, nxt in ((WHITE, BLACK), (BLACK, RED), (RED, WHITE)):
        ok({M.rot120(f) for f in M.FORWARD[h]} == set(M.FORWARD[nxt]),
           "pawn forward directions rotate with the armies")


# ==========================================================================
# 4. Wellisch's own worked examples (article pp. 328-329)
# ==========================================================================

def test_turn_order():
    """Wellisch p.329: Weiss opens, then ROT, then SCHWARZ, cyclically.  Ludii
    plays the opposite rotation; this is one of the two places it is wrong, and
    it is invisible to the 120 deg symmetry test, so pin it explicitly."""
    s = G.initial_state()
    seen = []
    for _ in range(7):
        seen.append(G.current_player(s))
        s = G.apply_move(s, G.legal_moves(s)[0])
    ok(seen == [WHITE, RED, BLACK, WHITE, RED, BLACK, WHITE],
       f"White -> Red -> Black, got {seen}")
    ok(M.SEAT_GERMAN == ("Weiss", "Rot", "Schwarz"), "seat names follow the article")


def test_notation():
    s0 = G.initial_state()
    ok(G.describe_move(s0, "-2,4>-3,3") == "Nb4-c3", "knight notation in Wellisch coords")
    ok(G.describe_move(s0, "-5,4>-5,3") == "b1-c1", "pawn notation")
    ok(G.describe_move(replace(s0, turn=RED), "4,-5>3,-5") == "l10-l9",
       "Wellisch's own red-pawn example, in his own notation")
    bd = dict(KINGS)
    bd[(0, 0)] = (WHITE, "R", WHITE)
    bd[(0, 1)] = (RED, "N", RED)
    ok(G.describe_move(blank(bd, WHITE), "0,0>0,1") == "Rf6xe6", "capture notation")


def test_worked_examples():
    s0 = G.initial_state()
    # Knight: "b4 -> c3, c6, d5" and nothing else.
    ok(dest_names(s0, "b4") == ["c3", "c6", "d5"], "knight b4")
    # Knight on the edge: "f11 -> e9" only.
    ok(dest_names(replace(s0, turn=RED), "f11") == ["e9"], "knight f11")
    # Black pawn: "f2 -> e2 or f3".  Two forward directions, 120 deg apart.
    ok(dest_names(replace(s0, turn=BLACK), "f2") == ["e2", "f3"], "black pawn f2")
    # Red pawn: "l10 -> l9 or k9".
    ok(dest_names(replace(s0, turn=RED), "l10") == ["k9", "l9"], "red pawn l10")
    # Rook: "a5 -> d8", sliding through b6 and c7.
    kings = {(-2, 5): (WHITE, "K", WHITE), (5, -3): (RED, "K", RED),
             (-3, -2): (BLACK, "K", BLACK)}
    bd = dict(kings)
    bd[(-1, 5)] = (WHITE, "R", WHITE)                        # a5
    st = blank(bd, WHITE)
    ok("d8" in dest_names(st, "a5"), "rook a5 reaches d8")
    ok(all(x in dest_names(st, "a5") for x in ("b6", "c7")), "through b6 and c7")
    bd2 = dict(bd)
    bd2[(1, 3)] = (BLACK, "P", BLACK)                        # blocker on c7
    st2 = blank(bd2, WHITE)
    ok("d8" not in dest_names(st2, "a5") and "c7" in dest_names(st2, "a5"),
       "a rook does not jump: a blocker on c7 stops it there")
    # No pawn ever moves two rows (no initial double step) and there is no e.p.
    for seat in (WHITE, RED, BLACK):
        st = replace(s0, turn=seat)
        for m in G.legal_moves(st):
            a, _, b = m.partition(">")
            fc, tc = M.parse_cell(a), M.parse_cell(b.split("=")[0])
            if s0.board[fc][1] != "P":
                continue
            ok((tc[0] - fc[0], tc[1] - fc[1]) in M.FORWARD[seat],
               "a pawn step is exactly one of its two forward directions")


def test_open_board_moves():
    """Wellisch's five worked examples all happen to be hemmed in by friendly
    men, so they cannot see a piece that moves too FAR or in too many
    directions.  Pin each piece's full move set on an empty board.

    K = wazir (the 6 orthogonals only -- the diagonal step is a 'Sprung',
    reserved to knight and queen).  N = exactly ONE diagonal step, never an
    orthogonal one.  R = slides the orthogonals, never turns.  Q = R + N, one
    mode per move, so its diagonal reach is exactly one cell (there are no
    bishops and no diagonal SLIDE in this game).
    """
    centre = (0, 0)
    # The two enemy kings sit off every ray, diagonal and double-diagonal of the
    # centre, so they neither block nor absorb any of the moves under test.
    far = {(3, 1): (RED, "K", RED), (-3, -1): (BLACK, "K", BLACK)}
    ortho = {(centre[0] + d[0], centre[1] + d[1]) for d in M.ORTHO}
    diag = {(centre[0] + d[0], centre[1] + d[1]) for d in M.DIAG}
    ok(len(ortho) == 6 and len(diag) == 6 and not (ortho & diag), "6 + 6 directions")
    rays = set()
    for ray in M.RAYS[centre]:
        rays |= set(ray)
    ok(len(rays) == 30, f"a centred rook sees 30 cells, got {len(rays)}")

    def moves_of(letter):
        bd = dict(far)
        bd[centre] = (WHITE, letter, WHITE)
        st = blank(bd, WHITE)
        return {M.parse_cell(m.split(">")[1].split("=")[0])
                for m in G.legal_moves(st) if m.startswith("0,0>")}

    ok(moves_of("K") == ortho, "the King is a wazir: the 6 orthogonals, no more")
    ok(not (moves_of("K") & diag), "the King may NOT make the diagonal 'Sprung'")
    ok(moves_of("N") == diag, "the Knight is exactly ONE diagonal step")
    ok(not (moves_of("N") & ortho), "the Knight never steps orthogonally")
    ok(moves_of("R") == rays, "the Rook slides the orthogonals only")
    ok(not (moves_of("R") & diag), "the Rook has no diagonal move")
    ok(moves_of("Q") == rays | diag, "the Queen is Rook + Knight")
    two_step = {(2, 2), (-2, -2), (4, -2), (-4, 2), (2, -4), (-2, 4)}
    ok(not (moves_of("Q") & two_step),
       "the Queen does NOT slide diagonally -- there are no bishops here")
    # The knight never changes cell colour, from anywhere.
    for c in M.CELLS:
        if c in far:
            continue
        bd = dict(far)
        bd[c] = (WHITE, "N", WHITE)
        st = blank(bd, WHITE)
        for m in G.legal_moves(st):
            if m.startswith(cid(c) + ">"):
                t = M.parse_cell(m.split(">")[1])
                ok(M.cell_colour(*t) == M.cell_colour(*c), "knight stays on its colour")


def test_pawn_captures_the_same_way():
    kings = {(-2, 5): (WHITE, "K", WHITE), (5, -3): (RED, "K", RED),
             (-3, -2): (BLACK, "K", BLACK)}
    bd = dict(kings)
    bd[(0, 0)] = (WHITE, "P", WHITE)                        # f6
    fwd = [(0, -1), (1, -1)]
    for d in M.ORTHO:
        t = (d[0], d[1])
        b2 = dict(bd)
        b2[t] = (BLACK, "P", BLACK)
        st = blank(b2, WHITE)
        got = any(m.startswith("0,0>") and M.parse_cell(m.split(">")[1]) == t
                  for m in G.legal_moves(st))
        ok(got == (d in fwd),
           f"pawn captures on {d} == {d in fwd} (same two directions as its move)")


# ==========================================================================
# 5. Promotion (to a piece the army has already LOST) + delayed promotion
# ==========================================================================

KINGS = {(-2, 5): (WHITE, "K", WHITE), (5, -3): (RED, "K", RED),
         (-3, -2): (BLACK, "K", BLACK)}


def test_promotion():
    bd = dict(KINGS)
    bd[(0, -4)] = (WHITE, "P", WHITE)                       # one step from row l
    st = blank(bd, WHITE)
    ok(sorted(m for m in G.legal_moves(st) if m.startswith("0,-4>"))
       == ["0,-4>0,-5", "0,-4>1,-5"],
       "nothing lost yet: the pawn just steps onto the promotion row")
    st2 = replace(st, pool=(("N", "Q"), (), ()))
    ok(sorted(m for m in G.legal_moves(st2) if m.startswith("0,-4>"))
       == ["0,-4>0,-5=N", "0,-4>0,-5=Q", "0,-4>1,-5=N", "0,-4>1,-5=Q"],
       "promotion is to a piece ALREADY LOST, and is mandatory on arrival")
    # Interpretation 1: delayed promotion.  The parked pawn has NO legal move
    # until a piece becomes available -- note the stalemate interaction.
    bd3 = dict(KINGS)
    bd3[(0, -5)] = (WHITE, "P", WHITE)
    st3 = blank(bd3, WHITE)
    ok([m for m in G.legal_moves(st3) if m.startswith("0,-5>")] == [],
       "a pawn parked on the promotion row with an empty pool cannot move")
    st4 = replace(st3, pool=(("R",), (), ()))
    ok(sorted(m for m in G.legal_moves(st4) if m.startswith("0,-5>")) == ["0,-5>0,-5=R"],
       "delayed promotion becomes available once a piece has been lost")
    ns = G.apply_move(st4, "0,-5>0,-5=R")
    ok(ns.board[(0, -5)] == (WHITE, "R", WHITE), "the parked pawn becomes the rook")
    ok(ns.pool == ((), (), ()), "the promoted man leaves the pool")
    ok("=R" in G.describe_move(st4, "0,-5>0,-5=R"), "delayed promotion notation")
    # A capture banks the man in ITS OWN army's pool, not the captor's.
    bd5 = dict(KINGS)
    bd5[(0, 0)] = (WHITE, "R", WHITE)
    bd5[(0, 1)] = (RED, "N", RED)
    n5 = G.apply_move(blank(bd5, WHITE), "0,0>0,1")
    ok(n5.pool == ((), ("N",), ()), "a captured Red knight joins RED's promotion pool")
    # Captured pawns and kings are not promotion targets.
    bd6 = dict(KINGS)
    bd6[(0, 0)] = (WHITE, "R", WHITE)
    bd6[(0, 1)] = (RED, "P", RED)
    ok(G.apply_move(blank(bd6, WHITE), "0,0>0,1").pool == ((), (), ()),
       "a captured pawn is not a promotion target")


def test_inherited_pawn_keeps_its_own_army():
    """A man taken over keeps its ORIGINAL army: its direction of travel, its
    promotion row, and the pool it promotes from."""
    bd = dict(KINGS)
    bd[(0, 5)] = (RED, "P", BLACK)          # Red commands a Black pawn, on q+r=5
    st = blank(bd, RED, pool=((), (), ("Q",)))
    ok(sorted(m for m in G.legal_moves(st) if m.startswith("0,5>")) == ["0,5>0,5=Q"],
       "an inherited pawn promotes on ITS OWN army's row, from ITS OWN pool")


# ==========================================================================
# 6. Castling (king <-> rook swap)
# ==========================================================================

def test_castling():
    s0 = G.initial_state()
    ok("-2,5>-1,5" in G.legal_moves(s0), "the near rook swap is available at once")
    ok(G.describe_move(s0, "-2,5>-1,5") == "O-O", "castling notation")
    cs = G.apply_move(s0, "-2,5>-1,5")
    ok(cs.board[(-1, 5)] == (WHITE, "K", WHITE) and cs.board[(-2, 5)] == (WHITE, "R", WHITE),
       "king and rook exchange places")
    ok(not any(p == WHITE for p, _rc in cs.castling), "castling spends both rights")
    ok("-2,5>-4,5" not in G.legal_moves(s0), "the far rook is blocked by the Queen")
    # With the Queen gone, the long swap appears.
    bd = dict(KINGS)
    bd[(-4, 5)] = (WHITE, "R", WHITE)
    bd[(-1, 5)] = (WHITE, "R", WHITE)
    rights = tuple(sorted((WHITE, rc) for rc in M.CASTLE[WHITE]["rooks"]))
    st = blank(bd, WHITE, castling=rights)
    ok("-2,5>-4,5" in G.legal_moves(st) and G.describe_move(st, "-2,5>-4,5") == "O-O-O",
       "the long swap over the vacated Queen cell")
    # A rook that leaves home and comes back must NOT regain the right.
    a = G.apply_move(st, "-1,5>-1,4")
    b = G.apply_move(replace(a, turn=WHITE), "-1,4>-1,5")
    ok((WHITE, (-1, 5)) not in b.castling and (WHITE, (-4, 5)) in b.castling,
       "castling rights are never re-granted")
    # A rook CAPTURED ON its home cell must kill that right too -- otherwise the
    # sibling rook could recapture there and inherit a live right.  This is the
    # `to != rc` half of the rights filter; the test above only exercises
    # `frm != rc`, so without this the clause is untested.
    bdc = dict(bd)
    bdc[(-1, 0)] = (BLACK, "R", BLACK)          # bears down the file onto a6
    stc = blank(bdc, BLACK, castling=rights)
    cap = G.apply_move(stc, "-1,0>-1,5")        # Black takes the rook on its home
    ok(cap.board[(-1, 5)] == (BLACK, "R", BLACK), "the home rook is captured")
    ok((WHITE, (-1, 5)) not in cap.castling,
       "a rook captured on its home cell spends that castling right")
    ok((WHITE, (-4, 5)) in cap.castling, "…and only that one")
    # Now the surviving rook recaptures onto the same cell: still no right.
    rec = G.apply_move(replace(cap, turn=WHITE), "-4,5>-1,5")
    ok((WHITE, (-1, 5)) not in rec.castling,
       "recapturing onto a rook home cell does not re-grant the right")
    # May not castle out of, or through, check.
    bd2 = dict(bd)
    bd2[(-3, 0)] = (BLACK, "R", BLACK)       # attacks the a3 cell the king crosses
    st2 = blank(bd2, WHITE, castling=rights)
    ok("-2,5>-4,5" not in G.legal_moves(st2), "no castling through an attacked cell")
    bd3 = dict(bd)
    bd3[(-2, 0)] = (BLACK, "R", BLACK)       # attacks the king itself
    st3 = blank(bd3, WHITE, castling=rights)
    ok(not [m for m in G.legal_moves(st3) if m in ("-2,5>-4,5", "-2,5>-1,5")],
       "no castling out of check")


# ==========================================================================
# 7. King capture, army takeover, and the checkmated player's turn
# ==========================================================================
#
# The mate used below: Black's King is alone in the l6 corner, White's rooks on
# l10 and k10 cover its three neighbours and give check along row l, and Red's
# rook on g6 bears down the same file.  Black is checkmated by WHITE; RED is
# the one who can take the king -- exactly Wellisch's "the player capturing the
# king may or may not be the player who delivered checkmate".

def mate_position(turn=RED):
    bd = {
        (0, -5): (BLACK, "K", BLACK),
        (-5, 1): (BLACK, "P", BLACK), (-5, 0): (BLACK, "N", BLACK),
        (4, -5): (WHITE, "R", WHITE), (4, -4): (WHITE, "R", WHITE),
        (-2, 5): (WHITE, "K", WHITE),
        (0, -1): (RED, "R", RED), (5, -3): (RED, "K", RED),
    }
    return blank(bd, turn)


def test_king_capture_needs_a_standing_mate():
    st = mate_position()
    ok(G._mated(st.board, st.alive, st.pool, st.castling) == frozenset({BLACK}),
       "Black is checkmated")
    ok("0,-1>0,-5" in G.legal_moves(st), "a MATED king may be captured")
    # Lift one of the mating rooks: Black is still in check but no longer mated,
    # and the king instantly becomes untouchable again.
    bd = dict(st.board)
    del bd[(4, -4)]
    st2 = blank(bd, RED)
    ok(G._in_check(st2.board, st2.alive, BLACK), "Black is still in check")
    ok(G._mated(st2.board, st2.alive, st2.pool, st2.castling) == frozenset(),
       "but not mated")
    ok("0,-1>0,-5" not in G.legal_moves(st2),
       "a king that is merely in check may NOT be captured")
    # No king is capturable in the opening position.
    s0 = G.initial_state()
    kings = {cid(c) for c, (_o, l, _h) in s0.board.items() if l == "K"}
    for seat in (WHITE, RED, BLACK):
        for m in G.legal_moves(replace(s0, turn=seat)):
            ok(m.split(">")[1].split("=")[0] not in kings, "no king capture at move 1")


def test_army_takeover():
    st = mate_position()
    before = {c: v for c, v in st.board.items() if v[0] == BLACK}
    ns = G.apply_move(st, "0,-1>0,-5")
    ok(ns.alive == (True, True, False) and ns.out == (BLACK,), "Black is eliminated")
    ok(not ns.over, "with two players left the game goes on")
    # ALL of Black's remaining men now answer to RED -- the CAPTURER, not White,
    # who delivered the mate -- and they keep their original army.
    for c in before:
        if c == (0, -5):
            continue                                   # the captured king
        ok(ns.board[c] == (RED, before[c][1], BLACK),
           f"{M.cell_name(c)} passes to Red but stays a Black man")
    # An inherited pawn keeps its DIRECTION OF TRAVEL: Black's, not Red's.
    st3 = replace(ns, turn=RED)
    got = {M.parse_cell(m.split(">")[1]) for m in G.legal_moves(st3)
           if m.startswith("-5,1>")}
    ok(got == {(-4, 1), (-5, 2)},
       f"inherited pawn moves in BLACK's two forward directions, got {got}")
    ok(got == {(-5 + d[0], 1 + d[1]) for d in M.FORWARD[BLACK]}, "…exactly")
    ok("eliminated" in G.describe_move(st, "0,-1>0,-5")
       and "Red" in G.describe_move(st, "0,-1>0,-5"), "takeover notation")


def test_checkmated_player_is_skipped():
    """Interpretation 2: a player who cannot move passes -- nothing else is
    possible.  Play simply skips him, and he may still be freed later."""
    st = mate_position()
    quiet = [m for m in G.legal_moves(st) if m != "0,-1>0,-5"]
    kept = None
    for m in quiet:
        ns = G.apply_move(st, m)
        if BLACK in G._mated(ns.board, ns.alive, ns.pool, ns.castling):
            kept = ns
            break
    ok(kept is not None, "Red has a move that leaves the mate standing")
    ok(kept.turn == WHITE, f"the mated player is skipped, got seat {kept.turn}")
    ok(not kept.over, "a checkmate is NOT terminal in this game")


def test_mutual_mate_deadlock_resolves():
    """The mate test is self-referential (p's escape may be capturing another
    mated king), so it is computed by iteration -- and that iteration's step is
    ANTI-monotone, i.e. it can 2-cycle instead of converging.  Here both kings
    are boxed in by their own frozen pawns and in check ONLY from each other's
    knight, and each player's ONLY move is to take the other's king (which
    transfers that army and lifts his own check).  Assume-both-mated says
    neither is; assume-neither says both are.  The engine must TERMINATE (this
    test hangs forever if it does not) and settle on the conservative reading:
    neither mate stands, so neither king may be taken."""
    bd = {(5, -5): (WHITE, "K", WHITE),                       # boxed in a corner
          (4, -5): (WHITE, "P", WHITE), (5, -4): (WHITE, "P", WHITE),
          (4, -4): (WHITE, "P", WHITE),
          (-4, 1): (WHITE, "N", WHITE),                       # attacks Red's king
          (-5, 0): (RED, "K", RED),                           # boxed in a corner
          (-4, 0): (RED, "P", RED), (-5, 1): (RED, "P", RED),
          (-4, -1): (RED, "P", RED),
          (3, -4): (RED, "N", RED)}                           # attacks White's king
    st = blank(bd, WHITE, alive=(True, True, False), out=(BLACK,))
    ok(G._in_check(bd, st.alive, WHITE) and G._in_check(bd, st.alive, RED),
       "both players are in check")
    for p in (WHITE, RED):
        other = frozenset({RED if p == WHITE else WHITE})
        ok(len(G._legal(bd, st.alive, p, other, st.pool, st.castling)) == 1,
           "with king-capture allowed, the capture is the player's ONLY move")
        ok(G._legal(bd, st.alive, p, frozenset(), st.pool, st.castling) == [],
           "with king-capture forbidden, he has no move at all")
    ok(G._mated(bd, st.alive, st.pool, st.castling) == frozenset(),
       "a mate that depends on capturing the other mated king does not stand")
    ok(G.legal_moves(st) == [], "so neither player may take a king")


def test_stalemate_in_the_two_handed_endgame_is_a_draw():
    # White's king on l6 has all three neighbours covered by the lone Red rook
    # on k7, which does not attack l6 itself: stalemate, not mate.
    # Only two players are left, so Wellisch p.329 hands this back to
    # two-handed chess ("zu zweit", "Patt stellen") => an honest DRAW, and the
    # "two finalists draw" row of his scoring table (0 / 1.5 / 1.5).
    bd = {(0, -5): (WHITE, "K", WHITE), (1, -4): (RED, "R", RED),
          (5, -3): (RED, "K", RED)}
    st = blank(bd, RED, alive=(True, True, False), out=(BLACK,))
    ok(not G._in_check(st.board, st.alive, WHITE), "White is not in check")
    ok(G.legal_moves(replace(st, turn=WHITE)) == [], "…and has no move")
    ns = G.apply_move(st, "5,-3>5,-2")               # a quiet Red king move
    ok(ns.over and ns.reason == "stalemate",
       f"a two-handed stalemate ends the game, got {ns.reason!r}")
    ok(G.returns(ns) == [1.5, 1.5, 0.0],
       f"…as a draw between the finalists, got {G.returns(ns)}")
    # NON-VACUITY: the same shape must NOT end the game while three are alive --
    # there a stalemated player merely passes (interpretation 2).
    bd3 = dict(bd); bd3[(-5, 0)] = (BLACK, "K", BLACK)
    st3 = blank(bd3, RED, alive=(True, True, True), out=())
    ok(G.legal_moves(replace(st3, turn=WHITE)) == [], "White still has no move")
    ns3 = G.apply_move(st3, "5,-3>5,-2")
    ok(not ns3.over and ns3.turn == BLACK,
       f"with three alive he is skipped, not drawn (turn={ns3.turn}, "
       f"over={ns3.over})")


# ==========================================================================
# 8. A DECISIVE RESULT OUTRANKS THE DRAW COUNTERS
# ==========================================================================
#    In this game the decisive event is KING CAPTURE / last player standing --
#    a checkmate is not even terminal -- so that is what the test attacks.

def conquest_position():
    bd = {(0, -5): (WHITE, "K", WHITE), (-5, 4): (WHITE, "P", WHITE),
          (4, -5): (RED, "R", RED), (4, -4): (RED, "R", RED),
          (0, -1): (RED, "R", RED), (5, -3): (RED, "K", RED)}
    return blank(bd, RED, alive=(True, True, False), out=(BLACK,))


def test_decisive_outranks_counters():
    st = conquest_position()
    ok(G._mated(st.board, st.alive, st.pool, st.castling) == frozenset({WHITE}),
       "White is checkmated")
    plain = G.apply_move(st, "0,-1>0,-5")
    ok(plain.over and plain.reason == "conquest", "king capture ends the game")
    ok(G.returns(plain) == [1.0, 2.0, 0.0], f"payoffs {G.returns(plain)}")
    # Now poison EVERY draw counter and take the king again.
    poisoned = replace(st, halfmove=10 ** 6, ply=10 ** 9, reps={G._key(st): 9})
    dec = G.apply_move(poisoned, "0,-1>0,-5")
    ok(dec.over and dec.reason == "conquest",
       f"a conquest must outrank the draw counters, got {dec.reason!r}")
    ok(G.returns(dec) == [1.0, 2.0, 0.0], "…with the decisive payoffs")
    # NON-VACUITY: from the same poisoned state, any other move IS a draw --
    # so the counters really were live and the test above proves something.
    other = [m for m in G.legal_moves(st) if m != "0,-1>0,-5"]
    ok(other, "there is another legal move")
    drawn = G.apply_move(poisoned, other[0])
    ok(drawn.over and drawn.reason in ("no progress", "repetition", "ply cap"),
       f"the poisoned counters do fire on a quiet move ({drawn.reason!r})")
    ok(G.returns(drawn) == [1.5, 1.5, 0.0], "…and score as a draw")


def test_payoff_table():
    """Wellisch p.329: three points per game, 0/1/2 by elimination order,
    0/1.5/1.5 when the two finalists draw, 1/1/1 when all three draw."""
    st = conquest_position()
    dec = G.apply_move(st, "0,-1>0,-5")
    ok(sum(G.returns(dec)) == 3.0 and sorted(G.returns(dec)) == [0.0, 1.0, 2.0],
       "no draw: 0 / 1 / 2")
    poisoned = replace(st, halfmove=10 ** 6)
    other = [m for m in G.legal_moves(st) if m != "0,-1>0,-5"][0]
    two = G.apply_move(poisoned, other)
    ok(sorted(G.returns(two)) == [0.0, 1.5, 1.5] and sum(G.returns(two)) == 3.0,
       "the two finalists draw: 0 / 1.5 / 1.5")
    s0 = G.initial_state()
    three = G.apply_move(replace(s0, halfmove=M.NOPROGRESS - 1), "-2,5>-1,5")
    ok(three.over and G.returns(three) == [1.0, 1.0, 1.0], "all three draw: 1 / 1 / 1")


# ==========================================================================
# 9. Termination constants -- and proof the patch actually bites
# ==========================================================================

def quiet_game(limit=400):
    """Play only non-progress moves (no captures, no pawn moves) for as long as
    the game allows."""
    s = G.initial_state()
    rng = random.Random(11)
    for _ in range(limit):
        if G.is_terminal(s):
            break
        quiet = [m for m in G.legal_moves(s)
                 if s.board[M.parse_cell(m.split(">")[0])][1] != "P"
                 and M.parse_cell(m.split(">")[1].split("=")[0]) not in s.board]
        s = G.apply_move(s, rng.choice(quiet) if quiet else rng.choice(G.legal_moves(s)))
    return s


def test_termination_constants_bite():
    ok(M.NOPROGRESS < M.PLY_CAP, "the no-progress rule fires long before the cap")
    ok(int(MAN.get("max_random_plies", 3000)) < M.PLY_CAP,
       "manifest max_random_plies sits BELOW the game's own PLY_CAP, so a "
       "termination regression fails loudly as 'did not terminate'")
    base = quiet_game()
    ok(base.over and base.reason in ("no progress", "repetition"),
       f"quiet play draws, got {base.reason!r}")
    # Patch the LIVE module (resolved via sys.modules) and assert the behaviour
    # really changes -- a patch that does not bite proves nothing.
    old_np, old_cap = M.NOPROGRESS, M.PLY_CAP
    try:
        M.NOPROGRESS = 3
        s = G.initial_state()
        s = G.apply_move(s, "-2,5>-1,5")            # castling: a quiet move
        s = G.apply_move(s, "5,-3>5,-4" if "5,-3>5,-4" in G.legal_moves(s)
                         else G.legal_moves(s)[0])
        n = 0
        while not G.is_terminal(s) and n < 40:
            quiet = [m for m in G.legal_moves(s)
                     if s.board[M.parse_cell(m.split(">")[0])][1] != "P"
                     and M.parse_cell(m.split(">")[1].split("=")[0]) not in s.board]
            s = G.apply_move(s, quiet[0] if quiet else G.legal_moves(s)[0])
            n += 1
        ok(s.over and s.reason == "no progress" and s.ply < 12,
           f"NOPROGRESS=3 bites: {s.reason!r} at ply {s.ply}")
        M.NOPROGRESS = old_np
        M.PLY_CAP = 4
        s = G.initial_state()
        while not G.is_terminal(s):
            s = G.apply_move(s, G.legal_moves(s)[0])
        ok(s.over and s.reason == "ply cap" and s.ply == 4,
           f"PLY_CAP=4 bites: {s.reason!r} at ply {s.ply}")
    finally:
        M.NOPROGRESS, M.PLY_CAP = old_np, old_cap
    # ... and with the real constants back, the same opening does NOT end early.
    s = G.initial_state()
    for _ in range(6):
        s = G.apply_move(s, G.legal_moves(s)[0])
    ok(not s.over, "restored constants: the game does not end after 6 plies")


# ==========================================================================
# 10. Platform contract
# ==========================================================================

def test_contract():
    ok(G.num_players == 3, "three seats")
    s = G.initial_state()
    h = G.heuristic(s)
    ok(isinstance(h, list) and len(h) == 3 and all(isinstance(x, float) for x in h),
       "heuristic MUST be a LIST of num_players payoffs")
    # Force the MCTS rollout cutoff, where the heuristic is actually consumed.
    mv = MCTSBot(random.Random(3), iterations=20, max_rollout=2).select(G, s)
    ok(mv in G.legal_moves(s), "MCTS with a forced heuristic cutoff returns a legal move")
    rng = random.Random(5)
    for _ in range(120):
        if G.is_terminal(s):
            break
        moves = G.legal_moves(s)
        ok(moves, "legal_moves is non-empty on a non-terminal state")
        snap = G.serialize(s)
        m = rng.choice(moves)
        G.describe_move(s, m)
        ns = G.apply_move(s, m)
        ok(G.serialize(s) == snap, "apply_move must not mutate its input")
        ok(G.serialize(G.deserialize(snap)) == snap, "serialize round-trips")
        spec = G.render(s)
        ok(spec["board"]["type"] == "hex" and spec["board"]["size"] == 6
           and "orientation" not in spec["board"],
           "91-cell hexhex, POINTY-TOP (Wellisch rejected the flat-top board)")
        ok(len(spec["pieces"]) == len(s.board), "render lists every man")
        s = ns
    if G.is_terminal(s):
        ok(len(G.returns(s)) == 3, "returns has one payoff per seat")


def main():
    for fn in (test_board, test_array, test_colour_rule, test_rotation,
               test_turn_order, test_notation, test_worked_examples,
               test_open_board_moves, test_pawn_captures_the_same_way,
               test_promotion, test_inherited_pawn_keeps_its_own_army,
               test_castling, test_king_capture_needs_a_standing_mate,
               test_army_takeover, test_checkmated_player_is_skipped,
               test_mutual_mate_deadlock_resolves,
               test_stalemate_in_the_two_handed_endgame_is_a_draw,
               test_decisive_outranks_counters, test_payoff_table,
               test_termination_constants_bite, test_contract):
        fn()
    print(f"wellisch_chess selftest: OK ({checks} checks)")


if __name__ == "__main__":
    main()
