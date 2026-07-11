#!/usr/bin/env python3
"""Standalone correctness anchor for Tamerlane Chess (Persia, c. 1400).

Run from the engine dir with::

    PYTHONPATH=. python3 games/tamerlane_chess/selftest.py

Pure stdlib + this game only. Prints ``SELFTEST OK`` and exits 0 on success.

It asserts:

* the 112-cell geometry (11x10 field at c 1..11 / r 1..10 plus the two
  citadels (12,2) White / (0,9) Black) and the full CVP opening setup
  (56 men, kings facing on the f-file, each vizier on its owner's right,
  pawn of pawns a3/k8, pawn of kings f3/f8);
* the opening **perft** baseline d1=24, d2=576, d3=14518. No published node
  counts exist; d1 is fully hand-verified against the CVP rules (11 pawn
  steps, 3+3 knight, 2 general, 1 king, 2+2 camel -- and NOT the i1 camel's
  (12,2) jump, which is barred because no piece but a king may enter a
  citadel), and d2=576 is hand-provable as 24x24 (no first-move interaction);
* exact move-target sets for camel/elephant/war engine (jumping proven over
  blockers), the **giraffe** (1 diagonal + minimum THREE straight, both
  outward continuations, blocked on every passed square incl. the diagonal
  one -- the CVP a1 example), and the **picket** (bishop, minimum two);
* pawns: single step only, diagonal capture, no double step;
* promotion of every pawn type to its own piece (pawn of kings -> Prince);
* the **pawn of pawns** three-stage rule: freeze + capture immunity on the
  last rank, fork/trapped-piece placements (positive and negative cases),
  the second-arrival teleport to f3 (blocked when f3 is occupied), and the
  third arrival becoming an adventitious king;
* **citadels**: the acting king's draw entry (and Wikipedia's ranking rule:
  a lower royal may not enter), non-royals barred, the adventitious king
  sheltering in its own citadel (blocking the enemy king) and Bodlaender's
  forced relocation when it becomes the sole royal inside;
* the once-per-game **royal exchange** (only while checked, must resolve the
  check, consumed after use);
* checkmate AND stalemate as losses for the player to move, multi-royal
  no-check play (king capturable while a prince exists);
* threefold repetition, the ply cap, and the only-royals dead draw;
* serialize round-trips and the polygons render spec (112 cells, list of
  {id, points}, labels <= 2 chars, JSON-serialisable);
* 8 seeded random playouts terminate within the ply cap (a separate 300-game
  gate was run during development: all terminated, avg 712 plies, 283 draws /
  11 White wins / 6 Black wins, 11 ply-cap hits).
"""

import json
import random
import sys

from agp.chesslike import CState, WHITE, BLACK
from games.tamerlane_chess.game import (
    TamerlaneChess, PAWN_PROMO, CITADEL, POK_START, MAIN_CELLS,
)

G = TamerlaneChess()


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def mk(pieces, to_move=WHITE, castling=""):
    st = CState(board=dict(pieces), to_move=to_move,
                castling=frozenset(castling))
    st.reps = {G._poskey_state(st): 1}
    return st


def targets(state, frm):
    out = set()
    fs = f"{frm[0]},{frm[1]}"
    for m in G.legal_moves(state):
        raw = m.split("=")[0]
        a, b = raw.split(">")
        if a == fs:
            out.add(tuple(int(x) for x in b.split(",")))
    return out


def perft(state, d):
    if d == 0:
        return 1
    return sum(perft(G.apply_move(state, m), d - 1) for m in G.legal_moves(state))


KINGS = {(6, 1): (WHITE, "K"), (6, 10): (BLACK, "K")}

# ---- 1. setup ---------------------------------------------------------------
s0 = G.initial_state()
check(len(s0.board) == 56, "56 men at start")
exp = {}
for c, t in ((1, "E"), (3, "C"), (5, "W"), (7, "W"), (9, "C"), (11, "E")):
    exp[(c, 1)] = (WHITE, t)
    exp[(c, 10)] = (BLACK, t)
for c in range(1, 12):
    exp[(c, 2)] = (WHITE, "RNTGFKVGTNR"[c - 1])
    exp[(c, 3)] = (WHITE, "pwcefkvgtnr"[c - 1])
    exp[(c, 9)] = (BLACK, "RNTGVKFGTNR"[c - 1])
    exp[(c, 8)] = (BLACK, "rntgvkfecwp"[c - 1])
check(s0.board == exp, "CVP opening setup")
check(s0.castling == frozenset("Ss"), "both swap rights at start")
check(s0.board[POK_START[WHITE]] == (WHITE, "k"), "pawn of kings on f3")
check(s0.board[POK_START[BLACK]] == (BLACK, "k"), "pawn of kings on f8")

# ---- 2. perft ---------------------------------------------------------------
check(perft(s0, 1) == 24, "perft d1 = 24 (hand-verified)")
check(perft(s0, 2) == 576, "perft d2 = 576 (= 24x24, hand-proved)")
check(perft(s0, 3) == 14518, "perft d3 = 14518 (frozen)")
check("9,1>12,2" not in G.legal_moves(s0), "camel may not jump into the citadel")

# ---- 3. piece geometry ------------------------------------------------------
# Camel: (3,1) leaper, jumps a full ring of friends.
ring = {(c, r): (WHITE, "v") for c in (5, 6, 7) for r in (4, 5, 6) if (c, r) != (6, 5)}
st = mk({**KINGS, (6, 5): (WHITE, "C"), **ring})
check(targets(st, (6, 5)) == {(7, 8), (5, 8), (7, 2), (5, 2),
                              (9, 6), (9, 4), (3, 6), (3, 4)}, "camel = (3,1) leaper, jumping")
st = mk({**KINGS, (6, 5): (WHITE, "E"), (7, 6): (WHITE, "v")})
check(targets(st, (6, 5)) == {(8, 7), (4, 7), (8, 3), (4, 3)}, "elephant = (2,2) jump")
st = mk({**KINGS, (6, 5): (WHITE, "W"), (6, 6): (WHITE, "v")})
check(targets(st, (6, 5)) == {(8, 5), (4, 5), (6, 7), (6, 3)}, "war engine = (2,0) jump")
st = mk({**KINGS, (4, 4): (WHITE, "V")})
check(targets(st, (4, 4)) == {(5, 4), (3, 4), (4, 5), (4, 3)}, "vizier = wazir")
st = mk({**KINGS, (4, 4): (WHITE, "F")})
check(targets(st, (4, 4)) == {(5, 5), (3, 5), (5, 3), (3, 3)}, "general = ferz")

# Giraffe from a1 (the CVP worked example): via b2 to b5.. and e2.. only.
st = mk({**KINGS, (1, 1): (WHITE, "G")})
check(targets(st, (1, 1)) ==
      {(2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10),
       (5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (10, 2), (11, 2)},
      "giraffe a1: b5-b10 and e2-k2 (min 3 straight, both continuations)")
st = mk({**KINGS, (1, 1): (WHITE, "G"), (2, 2): (WHITE, "v")})
check(targets(st, (1, 1)) == set(), "giraffe blocked on the diagonal square")
st = mk({**KINGS, (1, 1): (WHITE, "G"), (2, 4): (WHITE, "v")})
check(targets(st, (1, 1)) == {(5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (10, 2), (11, 2)},
      "giraffe blocked on a passed straight square (b4 kills the b-file line)")
st = mk({**KINGS, (1, 1): (WHITE, "G"), (2, 6): (BLACK, "R")})
check(targets(st, (1, 1)) == {(2, 5), (2, 6),
                              (5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (10, 2), (11, 2)},
      "giraffe captures the first blocker at range >= 3")

# Picket: bishop that must move at least two.
st = mk({**KINGS, (4, 4): (WHITE, "T")})
check(targets(st, (4, 4)) == {(6, 6), (7, 7), (8, 8), (9, 9), (10, 10),
                              (2, 6), (1, 7), (6, 2), (7, 1), (2, 2), (1, 1)},
      "picket = bishop min 2 (never one step)")
st = mk({**KINGS, (4, 4): (WHITE, "T"), (5, 5): (WHITE, "v")})
check((5, 5) not in targets(st, (4, 4)) and (6, 6) not in targets(st, (4, 4)),
      "picket cannot pass an occupied first square")
st = mk({**KINGS, (4, 4): (WHITE, "T"), (6, 6): (BLACK, "R")})
check((6, 6) in targets(st, (4, 4)) and (7, 7) not in targets(st, (4, 4)),
      "picket captures at range 2, blocked beyond")

# Pawns: single step + diagonal capture, no double step.
st = mk({**KINGS, (5, 4): (WHITE, "f"), (4, 5): (BLACK, "g")})
check(targets(st, (5, 4)) == {(5, 5), (4, 5)}, "pawn: step + diagonal capture")
st = mk({**KINGS, (2, 3): (WHITE, "r")})
check(targets(st, (2, 3)) == {(2, 4)}, "no pawn double step")

# ---- 4. promotion: every pawn to its own piece ------------------------------
for L, P in sorted(PAWN_PROMO.items()):
    st = mk({**KINGS, (2, 9): (WHITE, L)})
    s2 = G.apply_move(st, "2,9>2,10")
    check(s2.board[(2, 10)] == (WHITE, P), f"white pawn '{L}' promotes to {P}")
st = mk({**KINGS, (2, 2): (BLACK, "n")}, to_move=BLACK)
check(G.apply_move(st, "2,2>2,1").board[(2, 1)] == (BLACK, "N"),
      "black promotes on rank 1")

# ---- 5. pawn of pawns -------------------------------------------------------
# Stage 1: freeze on the last rank, immune from capture.
st = mk({**KINGS, (3, 9): (WHITE, "p"), (3, 5): (BLACK, "R")})
s2 = G.apply_move(st, "3,9>3,10")
check(s2.board[(3, 10)] == (WHITE, "q"), "PoP freezes on first arrival")
bt = targets(s2, (3, 5))
check((3, 10) not in bt and (3, 9) in bt, "frozen PoP is immune from capture")

# Placements: fork of two enemy pieces.
st = mk({**KINGS, (3, 10): (WHITE, "q"), (5, 5): (BLACK, "R"), (7, 5): (BLACK, "N")})
mv = G.legal_moves(st)
check("3,10>6,4" in mv, "frozen PoP may be placed to fork two pieces")
check("3,10>2,2" not in mv, "no placement without fork/trap")
s2 = G.apply_move(st, "3,10>6,4")
check(s2.board[(6, 4)] == (WHITE, "q") and (3, 10) not in s2.board,
      "placement moves the pawn off the last rank")
# Placement may displace a (non-royal) occupant, which is removed.
st = mk({**KINGS, (3, 10): (WHITE, "q"), (5, 5): (BLACK, "R"), (7, 5): (BLACK, "N"),
         (6, 4): (BLACK, "W")})
check("3,10>6,4" in G.legal_moves(st), "placement onto an occupied square")
s2 = G.apply_move(st, "3,10>6,4")
check(s2.board[(6, 4)] == (WHITE, "q"), "occupant displaced and removed")
# Trapped single piece: elephant hemmed in by its own pawns.
trap = {**KINGS, (9, 10): (WHITE, "q"), (1, 8): (BLACK, "E"),
        (3, 10): (BLACK, "n"), (3, 6): (BLACK, "n")}
check("9,10>2,7" in G.legal_moves(mk(trap)),
      "placement attacking a trapped piece")
open_ = dict(trap)
del open_[(3, 6)]
check("9,10>2,7" not in G.legal_moves(mk(open_)),
      "not a trap when the piece has an escape square")
guarded = dict(trap)
guarded[(2, 10)] = (BLACK, "R")
check("9,10>2,7" not in G.legal_moves(mk(guarded)),
      "not a trap when the placed pawn can be captured")

# Stage 2: second arrival teleports to the pawn of kings' start (f3).
st = mk({**KINGS, (3, 9): (WHITE, "q")})
check("3,9>3,10" in G.legal_moves(st), "second promotion available")
s2 = G.apply_move(st, "3,9>3,10")
check(s2.board[POK_START[WHITE]] == (WHITE, "z") and (3, 10) not in s2.board,
      "PoP teleports to f3 as stage 3")
st = mk({**KINGS, (3, 9): (WHITE, "q"), POK_START[WHITE]: (WHITE, "N")})
check("3,9>3,10" not in G.legal_moves(st),
      "second promotion barred while f3 is occupied")
# Stage 3: third arrival becomes an adventitious king.
st = mk({**KINGS, (3, 9): (WHITE, "z")})
s2 = G.apply_move(st, "3,9>3,10")
check(s2.board[(3, 10)] == (WHITE, "A"), "third promotion -> adventitious king")

# ---- 6. citadels ------------------------------------------------------------
st = mk({(1, 1): (WHITE, "K"), (2, 1): (WHITE, "W"),
         (11, 3): (BLACK, "K")}, to_move=BLACK)
check("11,3>12,2" in G.legal_moves(st), "enemy king may enter the citadel")
check("citadel" in G.describe_move(st, "11,3>12,2"), "citadel entry notation")
s2 = G.apply_move(st, "11,3>12,2")
check(G.is_terminal(s2) and G.returns(s2) == [0.0, 0.0],
      "king in the opponent's citadel: draw")
# Ranking: only the highest royal may enter; a sole acting royal qualifies.
st = mk({(1, 8): (WHITE, "K"), (5, 1): (WHITE, "A"), (11, 10): (BLACK, "K")})
check("1,8>0,9" in G.legal_moves(st), "the shah (top royal) may enter")
check(G.returns(G.apply_move(st, "1,8>0,9")) == [0.0, 0.0], "citadel draw for White")
st = mk({(1, 8): (WHITE, "A"), (5, 1): (WHITE, "K"), (11, 10): (BLACK, "K")})
check("1,8>0,9" not in G.legal_moves(st), "a lower royal may NOT enter")
st = mk({(1, 8): (WHITE, "A"), (10, 5): (BLACK, "E"), (11, 10): (BLACK, "K")})
check("1,8>0,9" in G.legal_moves(st), "a sole adventitious king acts as king")
# Own citadel: only a non-sole adventitious king; it blocks the enemy king.
st = mk({(1, 1): (WHITE, "K"), (11, 3): (WHITE, "A"), (6, 10): (BLACK, "K")})
check("11,3>12,2" in G.legal_moves(st), "adv. king may shelter in its own citadel")
s2 = G.apply_move(st, "11,3>12,2")
check(not G.is_terminal(s2), "own-citadel shelter does not end the game")
st = mk({(1, 1): (WHITE, "K"), (11, 3): (BLACK, "K"),
         (12, 2): (WHITE, "A")}, to_move=BLACK)
check("11,3>12,2" not in G.legal_moves(st), "sheltering AK blocks the draw entry")
st = mk({(11, 3): (WHITE, "A"), (2, 5): (BLACK, "E"), (6, 10): (BLACK, "K")})
check(G.legal_moves(st) and "11,3>12,2" not in G.legal_moves(st),
      "a sole royal may not enter its own citadel")
# Bodlaender: sole royal AK inside its citadel must relocate immediately.
st = mk({(12, 2): (WHITE, "A"), (5, 5): (WHITE, "K"),
         (5, 8): (BLACK, "R"), (11, 10): (BLACK, "K")}, to_move=BLACK)
check("5,8>5,5" in G.legal_moves(st), "spare royal: the king is simply capturable")
s2 = G.apply_move(st, "5,8>5,5")
mv = G.legal_moves(s2)
check(mv and all(m.startswith("12,2>") for m in mv),
      "sole-royal AK in the citadel: forced relocation")
check("12,2>1,1" in mv and "12,2>5,6" not in mv,
      "relocation must not land in check")
s3 = G.apply_move(s2, "12,2>1,1")
check(s3.board[(1, 1)] == (WHITE, "A") and (12, 2) not in s3.board, "AK relocated")

# ---- 7. royal exchange (king swap) ------------------------------------------
swap_pos = {(6, 1): (WHITE, "K"), (6, 8): (BLACK, "R"), (9, 5): (WHITE, "R"),
            (2, 2): (WHITE, "F"), (2, 8): (WHITE, "W"), (11, 10): (BLACK, "K")}
st = mk(swap_pos, castling="Ss")
check(G.in_check(st.board, WHITE), "swap test: king is checked")
mv = G.legal_moves(st)
check("6,1>9,5=SWAP" in mv and "6,1>2,2=SWAP" in mv,
      "checked king may swap with any friendly piece")
check("6,1>2,8=SWAP" not in mv, "swap must resolve the check")
s2 = G.apply_move(st, "6,1>9,5=SWAP")
check(s2.board[(9, 5)] == (WHITE, "K") and s2.board[(6, 1)] == (WHITE, "R"),
      "swap exchanges the two pieces")
check(s2.castling == frozenset("s"), "swap right consumed")
st = mk(swap_pos, castling="s")
check(not any(m.endswith("=SWAP") for m in G.legal_moves(st)),
      "no second swap")
nochk = dict(swap_pos)
del nochk[(6, 8)]
check(not any(m.endswith("=SWAP") for m in G.legal_moves(mk(nochk, castling="Ss"))),
      "no swap when not in check")

# ---- 8. mate / stalemate / multi-royal --------------------------------------
st = mk({(1, 1): (WHITE, "K"), (1, 8): (BLACK, "R"), (2, 8): (BLACK, "R"),
         (6, 10): (BLACK, "K")})
check(G.legal_moves(st) == [] and G.is_terminal(st) and G.returns(st) == [-1.0, 1.0],
      "checkmate: the mated player loses")
st = mk({(1, 1): (WHITE, "K"), (2, 8): (BLACK, "R"), (8, 2): (BLACK, "R"),
         (6, 10): (BLACK, "K")})
check(not G.in_check(st.board, WHITE), "stalemate position: not in check")
check(G.legal_moves(st) == [] and G.returns(st) == [-1.0, 1.0],
      "STALEMATE ALSO LOSES in Tamerlane chess")
check("stalemate" in G.render(st)["caption"], "stalemate caption")
st = mk({(1, 1): (WHITE, "K"), (3, 3): (WHITE, "S"), (1, 8): (BLACK, "R"),
         (11, 10): (BLACK, "K")})
check(not G.in_check(st.board, WHITE), "no check while a prince is on the board")
check("1,1>1,2" in G.legal_moves(st), "the king may stay/move en prise")
s2 = G.apply_move(st, "3,3>3,4")                     # White ignores the 'check'
check("1,8>1,1" in G.legal_moves(s2), "the spare king is capturable")
s3 = G.apply_move(s2, "1,8>1,1")
check(G._royals(s3.board, WHITE) == [((3, 4), "S")], "the prince takes over as king")
check(not G.is_terminal(s3), "game continues with the prince as royal")

# ---- 9. draws / termination rules -------------------------------------------
rep = {(1, 1): (WHITE, "K"), (11, 10): (BLACK, "K"),
       (5, 5): (WHITE, "R"), (7, 6): (BLACK, "R")}
st = mk(rep)
for m in ("5,5>5,4", "7,6>7,7", "5,4>5,5", "7,7>7,6") * 2:
    check(not G.is_terminal(st), "repetition: not terminal early")
    st = G.apply_move(st, m)
check(G.is_terminal(st) and G.returns(st) == [0.0, 0.0], "threefold repetition draws")
st = mk(rep)
st.ply = G.PLY_CAP
check(G.is_terminal(st) and G.returns(st) == [0.0, 0.0], "ply cap draws")
st = mk({(1, 1): (WHITE, "K"), (11, 10): (BLACK, "K")})
check(G.is_terminal(st) and G.returns(st) == [0.0, 0.0],
      "bare royal vs bare royal: dead draw")
st = mk({(1, 1): (WHITE, "K"), (3, 3): (WHITE, "S"), (11, 10): (BLACK, "K")})
check(not G._draw(st), "K+Prince vs K is NOT dead (stalemate wins exist)")

# ---- 10. serialize round-trip + render spec ----------------------------------
frozen = mk({**KINGS, (3, 10): (WHITE, "q"), (5, 5): (BLACK, "R")}, castling="s")
for st in (s0, frozen):
    d = json.loads(json.dumps(G.serialize(st)))
    st2 = G.deserialize(d)
    check(G._poskey_state(st2) == G._poskey_state(st), "serialize round-trip")
    check(sorted(G.legal_moves(st2)) == sorted(G.legal_moves(st)),
          "legal moves survive round-trip")
spec = json.loads(json.dumps(G.render(s0)))
check(spec["board"]["type"] == "polygons", "polygons render")
cells = spec["board"]["cells"]
check(isinstance(cells, list) and len(cells) == 112, "112 cells (110 + 2 citadels)")
check(all(set(c) >= {"id", "points"} for c in cells), "cells carry id + points")
ids = {c["id"] for c in cells}
check("12,2" in ids and "0,9" in ids, "citadel cells rendered")
check(len(spec["pieces"]) == 56, "56 pieces rendered")
check(all(1 <= len(p["label"]) <= 2 for p in spec["pieces"]), "labels <= 2 chars")
for m in G.legal_moves(s0)[:6]:
    check(isinstance(G.describe_move(s0, m), str), "describe_move works")

# ---- 11. playout termination -------------------------------------------------
rng = random.Random(7)
for i in range(8):
    st = G.initial_state()
    while True:
        mv = G.legal_moves(st)          # empty iff terminal (draws return [])
        if not mv:
            break
        st = G.apply_move(st, rng.choice(mv))
    check(G.is_terminal(st), "playout reached a terminal state")
    check(st.ply <= G.PLY_CAP, "playout within the ply cap")
    check(G.returns(st) in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0]), "valid result")

print("SELFTEST OK")
