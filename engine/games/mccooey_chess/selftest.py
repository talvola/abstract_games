"""Selftest for McCooey's Hexagonal Chess (pure stdlib; run from engine/):

    PYTHONPATH=. python3 games/mccooey_chess/selftest.py

Correctness anchors
-------------------
1. PERFT from the initial position: 31 / 947 / 33,307 (depths 1-3;
   depth 4 = 1,157,856 was computed once and is not rerun here). No
   published McCooey perft series exists and no open-source McCooey engine
   was found (@bedard/hexchess, the Glinski oracle, is Glinski-only), so
   depth 1 = 31 is hand-derived piece by piece from McCooey's own rules
   page and asserted per piece type below:
   P 13 (7 singles c2 d3 e4 f5 g4 h3 i2 + 6 doubles -- the centre pawn f4
   is denied its double step), N 10 (e2: b1,c3,d4,f5,g4; g2: e4,f5,h4,i3,j1),
   B 8 (f1, f2: 0 -- boxed in; f3: g4,h5,i6,j7 + e4,d5,c6,b7), and R/Q/K 0
   (the array has no unoccupied cells behind the pawns, so all heavy pieces
   start with zero moves). Depths 2-3 frozen after cross-checking the whole
   ruleset against anchor 2.
2. FULL REPLAY of seven of McCooey's published sample games (the games he
   and Billy Haynie / Tim O'Lena played, from his own chessvariants.com
   sample-games page) through a strict SAN reader: every move must resolve
   to exactly one legal move, every "+" must be a real check, every
   unannotated move must NOT give check, and the three "mate" games and
   one "#" game must end in genuine checkmate for the right side. This
   exercises setup, both diagonal pawn-capture directions, double steps,
   blocks, pins, long slides, disambiguation and mate detection on ~340
   plies of real play.
3. Constructed positions: diagonal (not Glinski-orthogonal) pawn captures,
   the centre-pawn double-step exclusion, the Wikipedia en-passant example
   (e8-e6 answered by d5xe7 e.p.), forced promotion choices, checkmate,
   STALEMATE = DRAW (McCooey's rule, vs Glinski's 3/4-1/4), McCooey's
   "knight on f4 is checkmate and a triple fork" remark, threefold
   repetition, the 50-move rule, and bishop colour invariance.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agp.loader import load_from_dir  # noqa: E402

HERE = Path(__file__).resolve().parent
man, g = load_from_dir(HERE)
mod = sys.modules[type(g).__module__]
MState = mod.MState
cell_name = mod.cell_name
WHITE, BLACK = mod.WHITE, mod.BLACK
DIAG, KNIGHT, ORTHO = mod.DIAG, mod.KNIGHT, mod.ORTHO

t0 = time.time()
checks = 0


def ok(cond, msg):
    global checks
    assert cond, msg
    checks += 1


def name2ax():
    """McCooey name -> axial, built by inverting cell_name over the board."""
    out = {}
    for q in range(-5, 6):
        for r in range(-5, 6):
            if mod.on_board(q, r):
                out[cell_name((q, r))] = (q, r)
    return out


AX = name2ax()
ok(len(AX) == 91, "91 cells")
ok(AX["f1"] == (0, 5) and AX["f6"] == (0, 0) and AX["f11"] == (0, -5), "f-file map")
ok(AX["a1"] == (-5, 5) and AX["k1"] == (5, 0) and AX["j7"] == (4, -5), "corner map")
ok("j3" in AX and "l1" not in AX, "files include j (unlike Glinski)")


def mv(frm_name, to_name, promo=None):
    q1, r1 = AX[frm_name]
    q2, r2 = AX[to_name]
    return f"{q1},{r1}>{q2},{r2}" + (f"={promo}" if promo else "")


def state(white, black, to_move=WHITE, halfmove=0):
    """Build a state from {'f9': 'K', ...} piece maps via deserialize."""
    board = {}
    for nm, letter in white.items():
        q, r = AX[nm]
        board[f"{q},{r}"] = [WHITE, letter]
    for nm, letter in black.items():
        q, r = AX[nm]
        board[f"{q},{r}"] = [BLACK, letter]
    return g.deserialize({"board": board, "to_move": to_move, "ep": None,
                          "halfmove": halfmove, "ply": 0, "reps": {}, "last": None})


# --- geometry invariants ----------------------------------------------------
ok(all((dq - dr) % 3 == 0 for dq, dr in DIAG), "bishop dirs colour-preserving")
ok(all((dq - dr) % 3 != 0 for dq, dr in KNIGHT), "knight always changes colour")
ok(len(set(KNIGHT)) == 12 and len(set(DIAG)) == 6 and len(set(ORTHO)) == 6, "dir counts")
# pawn captures are DIAGONAL (bishop-wise) -- McCooey's key difference
for side in (WHITE, BLACK):
    ok(all(d in DIAG for d in mod.PAWN_CAPS[side]), "pawn captures are diagonal")

# --- setup (chessvariants.com page + sample games + Zillions ZRF) -----------
s0 = g.initial_state()
ok(len(s0.board) == 32, "32 pieces at start (7 pawns per side)")
by = {}
for cell, (o, t) in s0.board.items():
    by.setdefault((o, t), set()).add(cell_name(cell))
ok(by[(WHITE, "K")] == {"g1"} and by[(BLACK, "K")] == {"g10"}, "kings g1/g10")
ok(by[(WHITE, "Q")] == {"e1"} and by[(BLACK, "Q")] == {"e10"}, "queens e1/e10")
ok(by[(WHITE, "B")] == {"f1", "f2", "f3"} and by[(BLACK, "B")] == {"f9", "f10", "f11"},
   "bishops f1-f3 / f9-f11")
ok(by[(WHITE, "N")] == {"e2", "g2"} and by[(BLACK, "N")] == {"e9", "g9"}, "knights")
ok(by[(WHITE, "R")] == {"d1", "h1"} and by[(BLACK, "R")] == {"d9", "h9"}, "rooks")
ok(by[(WHITE, "P")] == {"c1", "d2", "e3", "f4", "g3", "h2", "i1"}, "white pawns")
ok(by[(BLACK, "P")] == {"c8", "d8", "e8", "f8", "g8", "h8", "i8"}, "black pawns")
# the three bishops start on three DIFFERENT colours
for side in (WHITE, BLACK):
    cols = {(q - r) % 3 for (q, r), (o, t) in s0.board.items()
            if o == side and t == "B"}
    ok(len(cols) == 3, "bishops on 3 colours")
# every pawn is exactly 7 straight steps from its promotion hex (McCooey's
# design note: "the pawns are all seven hexes from promotion")
for (q, r), (o, t) in s0.board.items():
    if t != "P":
        continue
    fq, fr = mod.PAWN_FWD[o]
    steps = 0
    c = (q, r)
    while not mod._is_promo(o, c):
        c = (c[0] + fq, c[1] + fr)
        steps += 1
    ok(steps == 7, "pawn 7 hexes from promotion")
# McCooey's remark: the centre pawn begins the game UNPROTECTED
ok(not mod._attacked(s0.board, AX["f4"], WHITE), "f4 unprotected at start")
ok(not mod._attacked(s0.board, AX["f8"], BLACK), "f8 unprotected at start")

# --- perft ------------------------------------------------------------------
def perft(s, d):
    if d == 0:
        return 1
    total = 0
    for m in g.legal_moves(s):
        total += perft(g.apply_move(s, m), d - 1)
    return total


lm0 = g.legal_moves(s0)
ok(len(lm0) == 31, "initial mobility 31 (hand-derived)")
per_piece = {}
for m in lm0:
    frm = tuple(int(x) for x in m.split("=")[0].split(">")[0].split(","))
    per_piece[s0.board[frm][1]] = per_piece.get(s0.board[frm][1], 0) + 1
ok(per_piece == {"P": 13, "N": 10, "B": 8},
   "perft(1) breakdown P13 N10 B8, R/Q/K 0 (no room behind the pawns)")
ok(mv("f4", "f5") in lm0 and mv("f4", "f6") not in lm0,
   "centre pawn: single step only, NO double step")
ok(mv("c1", "c3") in lm0 and mv("i1", "i3") in lm0, "wing pawns keep the double")
# the position is mirror-symmetric: Black to move also has 31 moves
s0b = g.deserialize({**g.serialize(s0), "to_move": BLACK})
ok(len(g.legal_moves(s0b)) == 31 and mv("f8", "f6") not in g.legal_moves(s0b),
   "mirror: black 31 moves, centre pawn f8 no double")
ok(perft(s0, 2) == 947, "perft(2) = 947 (frozen)")
ok(perft(s0, 3) == 33307, "perft(3) = 33307 (frozen)")

# --- replay of McCooey's published sample games -----------------------------
# From https://www.chessvariants.com/hexagonal.dir/sample1.html (games played
# by Dave McCooey, Billy Haynie and Tim O'Lena; McCooey's own notation).
GAMES = [
    # (name, movetext, expected end: 'resigns' | 'white-mates' | 'black-mates')
    ("A", """1. Nh4 f7 2. f5 Ne7 3. Nd4 Bj3 4. Rg2 Bxh4 5. gxh4 c6 6. Ng4 Ng5
     7. h3 Bi3+ 8. Kh1 Nxf3 9. Qxf3 Bxg4 10. Qxg4 i6 11. Bd3 Qh5 12. Qxh5 ixh5
     13. Rdg3 Rk6 14. e4 Ng7 15. Rj2 Nxf5 16. Rg6 Ni3+ 17. Kg1 Nxg6 18. hxg6
     Rxg6+""", "resigns"),
    ("B", """1. f5 g6 2. Nd4 Bh6 3. fxg6 fxg6 4. Ne4 Nd6 5. Bd3 Nxe4 6. Bxe4
     Bf7 7. Bxf7 Nxf7 8. Nxf7 exf7 9. Kf1 Qe5 10. g4 Bb3 11. Rdf3 Be7 12. Bg3
     Ra4 13. Rhg2 Ra1 14. Kg1 Ri6 15. i2 Rj5 16. Rh1 Rxe4 17. Qg2? Rc4""",
     "resigns"),
    ("C", """1. g5 f7 2. Ne4 fxg5? 3. Ng6! Ne7 4. Ni7+ Kg9 5. Bi5+ h7
     6. Be6+ Kh8 7. Bj7+ Kg7 8. Qh5#""", "white-mates"),
    ("D", """1. d4 f7 2. e5 fxe5 3. fxe5 Nh6 4. Ne4 Ng7 5. Be3 e6 6. d5 Nxe5
     7. Bj5 Rg9 8. g5 Nxf3 9. Qxf3 Nf5 10. Ng6 Nxe2? 11. Ni7+ Kh9 12. Nf8#""",
     "white-mates"),
    ("1", """1. g5 Ne7 2. Nh4 d6 3. Nk3 Bh7 4. Ng4 g6 5. c3 Bg8 6. Ra1 f7
     7. Bg3 fxg5 8. Bd5 Nh6 9. fxg5 Bxd5+ 10. cxd5 Nxg4 11. Qxg4 Qg7
     12. Qe7+ Kg9 13. Be6+ Bf8 14. Bxf8+ Qxf8 15. Qxf8+ Kxf8 16. Nh5+ Kg7
     17. Nxg8 Kxg8 18. Bd3+ Kg7 19. Bxh9 Nxh9 20. h4 gxh4 21. Rh6+ Kg8
     22. R1xh4 Re10 23. Ri4 Ng7 24. Re7+ Kf9 25. Rf6+ Kd8 26. Rff8 Nj5
     27. Rxd6+ Ke9 28. Rg8+""", "resigns"),
    ("2", """1. g5 g6 2. d4 c6 3. Ne4 Ng7 4. Ng4 i6 5. Bd3 Ri8 6. Bg3 Nj7
     7. c3 Ni4 8. Kf2 Ri7 9. Nh3 Ra2+ 10. Be2 Bg8 11. Rg2 Nk4 12. Nh1 Bg7
     13. e5 Bj3 14. Bi5 Bxi5+ 15. Nxi5 Qg9 16. Nh3 Qj3 17. Ng4 Qh4+ 18. Kh1
     Nh5 19. Nd3(?) Nxf4+! 20. Bxf4 Qj3+ 21. i2 Qj1#""", "black-mates"),
    # NOTE: the source's informal "15...Re8" is ambiguous under strict SAN
    # (both rooks stand on rank 9 with clear paths to e8); the continuation
    # 19. Nxh9 proves the h9 rook never moved, so it is written Ree8 here.
    ("email2", """1. g5 f7 2. Ne4 Ng7 3. c3 fg 4. fg Ne7 5. Bh3 Bd7 6. Rg2 Nh7
     7. Ng6 Nf6 8. Bh5 Nxh3+ 9. ixh3 Be9 10. Ni7+ Kf11 11. Bxg7 Bxg7 12. Nh1
     Bd7 13. Nj2 e6 14. Rdf3 Re9 15. Bh4 Ree8 16. Bf8 h6 17. Bxd7+ Rxd7
     18. Nf8 Qe7 19. Nxh9 Rxh9 20. Rgf2 Rg9 21. Rf8 Qc6+ 22. Kh1 Ke10
     23. Qj7 Bk5 24. Qxi8 Bj4 25. Ni5 Qa4 26. Nxg8+ Bxg8 27. Qf11#""",
     "white-mates"),
]

PIECE_RE = re.compile(r"^([KQRBN])([a-k]?)(\d{0,2})(x?)([a-k])(\d{1,2})$")
PAWN_CAP_RE = re.compile(r"^([a-k])(x?)([a-k])(\d{1,2})?$")
PAWN_PUSH_RE = re.compile(r"^([a-k])(\d{1,2})$")


def san_apply(s, tok):
    """Resolve one SAN token to exactly one legal move; assert check marks."""
    raw = tok
    tok = tok.replace("(?)", "").replace("(!)", "").rstrip("!?")
    wants_check = tok.endswith("+") or tok.endswith("#")
    tok = tok.rstrip("+#")
    cands = []
    for m in g.legal_moves(s):
        body = m.split("=")[0]
        promo = m.split("=")[1] if "=" in m else None
        frm = tuple(int(x) for x in body.split(">")[0].split(","))
        to = tuple(int(x) for x in body.split(">")[1].split(","))
        piece = s.board[frm][1]
        fname, tname = cell_name(frm), cell_name(to)
        is_cap = (to in s.board) or (
            piece == "P" and s.ep is not None and to == s.ep[0])
        pm = PIECE_RE.match(tok)
        if pm:
            pc, dfile, drank, x, tf, tr = pm.groups()
            if (piece == pc and tname == tf + tr and is_cap == bool(x)
                    and (not dfile or fname[0] == dfile)
                    and (not drank or fname[1:] == drank) and promo is None):
                cands.append(m)
            continue
        pp = PAWN_PUSH_RE.match(tok)
        if pp and piece == "P" and not is_cap and promo is None \
                and tname == tok and fname[0] == tok[0]:
            cands.append(m)
            continue
        pcm = PAWN_CAP_RE.match(tok)
        if pcm and not PAWN_PUSH_RE.match(tok):
            ff, x, tf, tr = pcm.groups()
            if (piece == "P" and is_cap and fname[0] == ff and promo is None
                    and tname[0] == tf and (not tr or tname[1:] == tr)):
                cands.append(m)
    ok(len(cands) == 1, f"SAN {raw!r} resolves uniquely (got {cands})")
    s2 = g.apply_move(s, cands[0])
    in_chk = mod._in_check(s2.board, s2.to_move)
    ok(in_chk == wants_check, f"SAN {raw!r}: check annotation matches ({in_chk})")
    return s2


for name, text, end in GAMES:
    s = g.initial_state()
    toks = [t for t in text.split() if not re.match(r"^\d+\.$", t)]
    for t in toks:
        ok(not g.is_terminal(s), f"game {name}: not terminal before {t}")
        s = san_apply(s, t)
    if end == "resigns":
        ok(not g.is_terminal(s), f"game {name}: playable at resignation")
    else:
        winner = WHITE if end == "white-mates" else BLACK
        ok(g.is_terminal(s), f"game {name}: final position is mate")
        ok(g.returns(s) == ([1.0, -1.0] if winner == WHITE else [-1.0, 1.0]),
           f"game {name}: {end}")

# --- pawn captures: diagonal, NOT Glinski's forward orthogonals -------------
s = state({"g1": "K", "e4": "P"}, {"g10": "K", "f6": "R", "d5": "N"})
lm = g.legal_moves(s)
ok(mv("e4", "f6") in lm and mv("e4", "d5") in lm, "both diagonal captures")
s2 = g.apply_move(s, mv("e4", "f6"))
ok(s2.board[AX["f6"]] == (WHITE, "P"), "diagonal capture executes")
s = state({"g1": "K", "e4": "P"}, {"g10": "K", "f5": "R", "d4": "N"})
lm = g.legal_moves(s)
ok(mv("e4", "f5") not in lm and mv("e4", "d4") not in lm,
   "Glinski's orthogonal-forward captures are NOT legal here")
s = state({"g1": "K", "e4": "P"}, {"g10": "K", "e5": "R"})
ok(mv("e4", "e5") not in g.legal_moves(s), "no straight-forward capture")
# black's two capture directions
s = state({"g1": "K", "d5": "R", "f6": "N"}, {"g10": "K", "e7": "P"}, to_move=BLACK)
lm = g.legal_moves(s)
ok(mv("e7", "d5") in lm and mv("e7", "f6") in lm, "black diagonal captures")
# a pawn off its start cell has no double step
s = state({"g1": "K", "e5": "P"}, {"g10": "K"})
lm = g.legal_moves(s)
ok(mv("e5", "e6") in lm and mv("e5", "e7") not in lm, "no double off start cells")

# --- en passant (Wikipedia's example: e8-e6 answered by d5xe7) --------------
s = state({"g1": "K", "d5": "P"}, {"g10": "K", "e8": "P"}, to_move=BLACK)
ok(mv("e8", "e6") in g.legal_moves(s), "black double e8-e6")
s = g.apply_move(s, mv("e8", "e6"))
ok(mv("d5", "e7") in g.legal_moves(s), "dxe7 en passant available")
s2 = g.apply_move(s, mv("d5", "e7"))
ok(AX["e6"] not in s2.board and s2.board[AX["e7"]] == (WHITE, "P"),
   "en passant removes the double-stepped pawn")
# ... but only immediately: after another move the right lapses.
s3 = g.apply_move(s, mv("g1", "g2"))
s3 = g.apply_move(s3, mv("g10", "g9"))
ok(mv("d5", "e7") not in g.legal_moves(s3), "en passant right lapses")

# --- promotion at the end of any file, four choices, forced -----------------
s = state({"g1": "K", "b6": "P"}, {"g10": "K"})
lm = g.legal_moves(s)
promos = [m for m in lm if m.startswith(mv("b6", "b7"))]
ok(sorted(promos) == sorted(mv("b6", "b7", p) for p in "QRBN"),
   "b7 promotion offers Q/R/B/N")
ok(mv("b6", "b7") not in lm, "promotion is forced (no plain push to last cell)")
s2 = g.apply_move(s, mv("b6", "b7", "N"))
ok(s2.board[AX["b7"]] == (WHITE, "N"), "promoted to knight")
# capture-promotion onto the edge (c8 is the end of the c-file)
s = state({"g1": "K", "b6": "P"}, {"g10": "K", "c8": "R"})
ok(mv("b6", "c8", "Q") in g.legal_moves(s), "capture-promotion b6xc8=Q")

# --- checkmate --------------------------------------------------------------
s = state({"f9": "K", "f10": "Q"}, {"f11": "K"}, to_move=BLACK)
ok(g.is_terminal(s), "Qf10/Kf9 vs Kf11 is terminal")
ok(g.returns(s) == [1.0, -1.0], "checkmate scores +1/-1")

# --- McCooey's remark: a knight landing on the centre-pawn hex at the start
# is "checkmate and a triple fork, all in one" -------------------------------
s = g.initial_state()
b = {f"{q},{r}": [o, t] for (q, r), (o, t) in s.board.items()}
b[f"{AX['f4'][0]},{AX['f4'][1]}"] = [BLACK, "N"]  # black knight takes f4's place
s = g.deserialize({"board": b, "to_move": WHITE, "ep": None,
                   "halfmove": 0, "ply": 0, "reps": {}, "last": None})
nq, nr = AX["f4"]
ok(all((AX[c][0] - nq, AX[c][1] - nr) in [(-o[0], -o[1]) for o in KNIGHT]
       for c in ("g1", "e1", "d1")), "Nf4 forks K g1, Q e1, R d1")
ok(mod._in_check(s.board, WHITE), "Nf4 gives check")
ok(g.is_terminal(s) and g.returns(s) == [-1.0, 1.0],
   "knight on f4 at the start is checkmate (McCooey's remark)")

# --- STALEMATE IS A DRAW (McCooey's rule; Glinski scores it 3/4-1/4) --------
s = state({"f9": "K"}, {"f11": "K"}, to_move=BLACK)
ok(g.legal_moves(s) == [] and g.is_terminal(s), "K vs K stalemate is terminal")
ok(not mod._in_check(s.board, BLACK), "stalemate, not check")
ok(g.returns(s) == [0.0, 0.0], "stalemate is an honest DRAW (1/2-1/2)")
mirror = state({"f11": "K"}, {"f9": "K"}, to_move=WHITE)
ok(g.returns(mirror) == [0.0, 0.0], "stalemate draw is side-symmetric")

# --- threefold repetition ---------------------------------------------------
s = g.initial_state()
cycle = [mv("e2", "c3"), mv("e9", "c6"), mv("c3", "e2"), mv("c6", "e9")]
for _ in range(2):
    for m in cycle:
        ok(not g.is_terminal(s), "not terminal mid-cycle")
        s = g.apply_move(s, m)
ok(g.is_terminal(s) and g.returns(s) == [0.0, 0.0], "threefold repetition draw")

# --- 50-move rule -----------------------------------------------------------
s = state({"g1": "K", "d1": "R"}, {"g10": "K"}, halfmove=99)
s = g.apply_move(s, mv("d1", "d2"))
ok(s.halfmove == 100 and g.is_terminal(s) and g.returns(s) == [0.0, 0.0],
   "50-move rule draw")
s = state({"g1": "K", "d1": "R"}, {"g10": "K", "d2": "N"}, halfmove=99)
s = g.apply_move(s, mv("d1", "d2"))   # a capture resets the clock
ok(s.halfmove == 0 and not g.is_terminal(s), "capture resets 50-move clock")

# --- bishop colour invariance over real play --------------------------------
s = g.initial_state()
seen_bishop_moves = 0
for m in g.legal_moves(s):
    frm = tuple(int(x) for x in m.split("=")[0].split(">")[0].split(","))
    to = tuple(int(x) for x in m.split("=")[0].split(">")[1].split(","))
    if s.board[frm][1] == "B":
        seen_bishop_moves += 1
        ok((frm[0] - frm[1]) % 3 == (to[0] - to[1]) % 3, "bishop stays on colour")
ok(seen_bishop_moves == 8, "8 bishop moves at start (f3 only; f1/f2 boxed in)")

# --- notation ---------------------------------------------------------------
s = g.initial_state()
ok(g.describe_move(s, mv("f4", "f5")) == "f4-f5", "pawn notation")
ok(g.describe_move(s, mv("e2", "c3")) == "Ne2-c3", "knight notation")

# --- serialize round-trip & purity ------------------------------------------
s = g.initial_state()
for m in [mv("e3", "e5"), mv("c8", "c6"), mv("e2", "f5")]:
    before = g.serialize(s)
    s2 = g.apply_move(s, m)
    ok(g.serialize(s) == before, "apply_move is pure")
    ok(g.serialize(g.deserialize(g.serialize(s2))) == g.serialize(s2), "round-trip")
    s = s2

# --- random playout terminates ----------------------------------------------
import random  # noqa: E402
rng = random.Random(7)
s = g.initial_state()
plies = 0
while not g.is_terminal(s):
    s = g.apply_move(s, rng.choice(g.legal_moves(s)))
    plies += 1
    ok(plies <= mod.PLY_CAP, "terminates within ply cap")
ret = g.returns(s)
ok(len(ret) == 2 and all(-1.0 <= x <= 1.0 for x in ret), "well-formed returns")

# --- heuristic returns per-seat payoffs (MCTS contract) ---------------------
h = g.heuristic(g.initial_state())
ok(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9,
   "heuristic is a zero-sum pair")
from agp.mcts import MCTSBot  # noqa: E402
MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(g, g.initial_state())
checks += 1

print(f"mccooey_chess selftest OK ({checks} checks, {time.time() - t0:.1f}s)")
