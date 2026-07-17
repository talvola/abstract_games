"""Selftest for Gliński's Hexagonal Chess (pure stdlib; run from engine/):

    PYTHONPATH=. python3 games/glinski_chess/selftest.py

Correctness anchors
-------------------
1. PERFT from the initial position: 51 / 2,586 / 137,858 (depths 1-3).
   No published Gliński perft series was found, so these numbers were frozen
   after an EXHAUSTIVE cross-check against the independent open-source
   reference implementation @bedard/hexchess v2.5.1 (hexchess.club,
   github.com/scottbedard/hexchess): full legal-move-set equality on every
   node to depth 3 (perft 51/2586/137858 identical), plus 40 seeded random
   full games = 19,708 positions with ZERO move-set mismatches (2026-07-17,
   one-time, not rerun here). Depth 1 = 51 is additionally hand-derived
   square by square from the Wikipedia/chessvariants rules:
   P 17 (9 single + 8 double; f5's double is blocked by the f7 pawn),
   N 8 (d1: c3,b2,f4,g2 + mirror h1), B 12 (f1: e2,g2; f2: 4+4 long
   diagonals; f3: d2,h2), Q 6 (e1: e2,e3 + d2,c3,b4,a5), K 2 (g1: g2,h2),
   R 6 (c1: d2,e3,f4 + mirror i1).
2. The Wikipedia rule examples: e4xf5 regaining the double-step option
   (f5-f7), and c7-c5 answered by b5xc6 en passant.
3. Constructed positions: promotion choices, pawn capture directions,
   checkmate, stalemate scoring 3/4-1/4 (as +0.5/-0.5), K vs K stalemate,
   threefold repetition, 50-move rule, bishop colour-class invariance.
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
GState = mod.GState
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
    """Gliński name -> axial, built by inverting cell_name over the board."""
    out = {}
    for q in range(-5, 6):
        for r in range(-5, 6):
            if mod.on_board(q, r):
                out[cell_name((q, r))] = (q, r)
    return out


AX = name2ax()
ok(len(AX) == 91, "91 cells")
ok(AX["f1"] == (0, 5) and AX["f6"] == (0, 0) and AX["f11"] == (0, -5), "f-file map")
ok(AX["a1"] == (-5, 5) and AX["l1"] == (5, 0) and AX["a6"] == (-5, 0), "corner map")


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
# Bishop directions are exactly the colour-preserving unit diagonals; the
# knight leap NEVER stays on its colour (colour class = (q - r) mod 3).
ok(all((dq - dr) % 3 == 0 for dq, dr in DIAG), "bishop dirs colour-preserving")
ok(all((dq - dr) % 3 != 0 for dq, dr in KNIGHT), "knight always changes colour")
ok(len(set(KNIGHT)) == 12 and len(set(DIAG)) == 6 and len(set(ORTHO)) == 6, "dir counts")

# --- setup ------------------------------------------------------------------
s0 = g.initial_state()
ok(len(s0.board) == 36, "36 pieces at start")
by = {}
for cell, (o, t) in s0.board.items():
    by.setdefault((o, t), set()).add(cell_name(cell))
ok(by[(WHITE, "K")] == {"g1"} and by[(BLACK, "K")] == {"g10"}, "kings g1/g10")
ok(by[(WHITE, "Q")] == {"e1"} and by[(BLACK, "Q")] == {"e10"}, "queens e1/e10")
ok(by[(WHITE, "B")] == {"f1", "f2", "f3"} and by[(BLACK, "B")] == {"f9", "f10", "f11"},
   "bishops f1-f3 / f9-f11")
ok(by[(WHITE, "N")] == {"d1", "h1"} and by[(BLACK, "N")] == {"d9", "h9"}, "knights")
ok(by[(WHITE, "R")] == {"c1", "i1"} and by[(BLACK, "R")] == {"c8", "i8"}, "rooks")
ok(by[(WHITE, "P")] == {"b1", "c2", "d3", "e4", "f5", "g4", "h3", "i2", "k1"},
   "white pawns")
ok(by[(BLACK, "P")] == {"b7", "c7", "d7", "e7", "f7", "g7", "h7", "i7", "k7"},
   "black pawns")
# the three bishops start on three DIFFERENT colours
for side in (WHITE, BLACK):
    cols = {(q - r) % 3 for (q, r), (o, t) in s0.board.items()
            if o == side and t == "B"}
    ok(len(cols) == 3, "bishops on 3 colours")

# --- perft ------------------------------------------------------------------
def perft(s, d):
    if d == 0:
        return 1
    total = 0
    for m in g.legal_moves(s):
        total += perft(g.apply_move(s, m), d - 1)
    return total


ok(len(g.legal_moves(s0)) == 51, "initial mobility 51 (hand-derived + oracle)")
ok(perft(s0, 2) == 2586, "perft(2) = 2586 (matches @bedard/hexchess)")
ok(perft(s0, 3) == 137858, "perft(3) = 137858 (matches @bedard/hexchess)")

# --- Wikipedia pawn examples ------------------------------------------------
# 1) e4xf5 lands on a friendly-pawn start cell -> regains the double step f5-f7.
s = state({"g1": "K", "e4": "P"}, {"g10": "K", "f5": "R"})
lm = g.legal_moves(s)
ok(mv("e4", "f5") in lm, "pawn captures 60-deg forward (e4xf5)")
ok(mv("e4", "d4") not in lm, "no capture onto empty d4")
ok(mv("e4", "e5") in lm and mv("e4", "e6") in lm, "e4 push + double (own start)")
s = g.apply_move(s, mv("e4", "f5"))
s = g.apply_move(s, mv("g10", "g9"))          # any black reply
lm = g.legal_moves(s)
ok(mv("f5", "f6") in lm and mv("f5", "f7") in lm,
   "capturing onto f5 regains the double-step (Wikipedia example)")
# a pawn NOT on a start cell has no double step
s = state({"g1": "K", "e5": "P"}, {"g10": "K"})
lm = g.legal_moves(s)
ok(mv("e5", "e6") in lm and mv("e5", "e7") not in lm, "no double off start cells")
# straight-ahead is never a capture
s = state({"g1": "K", "e4": "P"}, {"g10": "K", "e5": "R"})
ok(mv("e4", "e5") not in g.legal_moves(s), "no straight-forward capture")

# 2) En passant (Wikipedia example): after c7-c5, b5 pawn may capture on c6.
s = state({"g1": "K", "b5": "P"}, {"g10": "K", "c7": "P"}, to_move=BLACK)
ok(mv("c7", "c5") in g.legal_moves(s), "black double c7-c5")
s = g.apply_move(s, mv("c7", "c5"))
lm = g.legal_moves(s)
ok(mv("b5", "c6") in lm, "bxc6 en passant available")
s2 = g.apply_move(s, mv("b5", "c6"))
ok(AX["c5"] not in s2.board and s2.board[AX["c6"]] == (WHITE, "P"),
   "en passant removes the double-stepped pawn")
# ... but only immediately: after another move the right lapses.
s3 = g.apply_move(s, mv("g1", "g2"))
s3 = g.apply_move(s3, mv("g10", "g9"))
ok(mv("b5", "c6") not in g.legal_moves(s3), "en passant right lapses")

# 3) Promotion at the end of any file, four choices.
s = state({"g1": "K", "b6": "P"}, {"g10": "K"})
lm = g.legal_moves(s)
promos = [m for m in lm if m.startswith(mv("b6", "b7"))]
ok(sorted(promos) == sorted(mv("b6", "b7", p) for p in "QRBN"),
   "b7 promotion offers Q/R/B/N")
ok(mv("b6", "b7") not in lm, "promotion is forced (no plain push to last cell)")
s2 = g.apply_move(s, mv("b6", "b7", "N"))
ok(s2.board[AX["b7"]] == (WHITE, "N"), "promoted to knight")
# capture-promotion onto the edge (a6 is the end of the a-file)
s = state({"g1": "K", "b6": "P"}, {"g10": "K", "a6": "R"})
ok(mv("b6", "a6", "Q") in g.legal_moves(s), "capture-promotion b6xa6=Q")

# --- checkmate --------------------------------------------------------------
s = state({"f9": "K", "f10": "Q"}, {"f11": "K"}, to_move=BLACK)
ok(g.is_terminal(s), "Qf10/Kf9 vs Kf11 is terminal")
ok(g.returns(s) == [1.0, -1.0], "checkmate scores +1/-1")

# --- stalemate scores 3/4 - 1/4 (as +0.5 / -0.5) ---------------------------
# K vs K stalemate IS reachable on the hexboard: white Kf9 covers all five
# cells a king on f11 could move to, without giving check.
s = state({"f9": "K"}, {"f11": "K"}, to_move=BLACK)
ok(g.legal_moves(s) == [] and g.is_terminal(s), "K vs K stalemate is terminal")
ok(g.returns(s) == [0.5, -0.5], "stalemater +0.5, stalemated -0.5")
mirror = state({"f11": "K"}, {"f9": "K"}, to_move=WHITE)
ok(g.returns(mirror) == [-0.5, 0.5], "stalemate scoring is side-symmetric")

# --- threefold repetition ---------------------------------------------------
s = g.initial_state()
cycle = [mv("d1", "c3"), mv("d9", "g9"), mv("c3", "d1"), mv("g9", "d9")]
for _ in range(2):
    for m in cycle:
        ok(not g.is_terminal(s), "not terminal mid-cycle")
        s = g.apply_move(s, m)
ok(g.is_terminal(s) and g.returns(s) == [0.0, 0.0], "threefold repetition draw")

# --- 50-move rule -----------------------------------------------------------
s = state({"g1": "K", "c1": "R"}, {"g10": "K"}, halfmove=99)
s = g.apply_move(s, mv("c1", "d2"))
ok(s.halfmove == 100 and g.is_terminal(s) and g.returns(s) == [0.0, 0.0],
   "50-move rule draw")
s = state({"g1": "K", "c1": "R"}, {"g10": "K", "d2": "N"}, halfmove=99)
s = g.apply_move(s, mv("c1", "d2"))   # a capture resets the clock
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
ok(seen_bishop_moves == 12, "12 bishop moves at start")

# --- notation ---------------------------------------------------------------
s = g.initial_state()
ok(g.describe_move(s, mv("f5", "f6")) == "f5-f6", "pawn notation")
ok(g.describe_move(s, mv("d1", "c3")) == "Nd1-c3", "knight notation")

# --- serialize round-trip & purity ------------------------------------------
s = g.initial_state()
for m in [mv("e4", "e6"), mv("c7", "c5"), mv("d1", "f4")]:
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

print(f"glinski_chess selftest OK ({checks} checks, {time.time() - t0:.1f}s)")
