#!/usr/bin/env python3
"""Standalone correctness anchor for Decimaka (H. G. Muller, 2018).

Run from the engine root with::

    PYTHONPATH=. python3 games/decimaka/selftest.py

Pure stdlib (imports only ``agp`` + this game), ~10s. Asserts:

* the exact opening array from the CVP page's Interactive Diagram (pawns a3-j3,
  tee b2/i2, knight c2/h2, fiancee e1, cross a2/j2, y d1/g1, star f2, lion e2,
  bishop d2/g2, rook a1/j1, king f1; Black = 180-degree rotation, so Black's
  King is on e10);
* frozen self-computed **perft** d1=50, d2=2500, d3=135301. d1 is fully
  hand-verified piece-by-piece against the source diagram (P 20, R 4, Y 4,
  C 2, T 2, N 4, B 2, L 6, S 6, F 0, K 0); d2 = 50^2 exactly (the mirrored
  armies provably cannot interact at depth 2), an independent structural
  cross-check;
* exact legal-target sets for every fairy piece in both colours' frames
  (Tee, Cross, Y, Star, Lion, Fiancee) and for the promoted types
  (Trident's forward-diagonal + full-file slides with blocking, Nightrider
  riding + blocking, Omni's move-orthogonal/capture-diagonal split);
* the capture-promotion lifecycle via apply_move: optional promotion on a
  plain capture (both move strings offered; each lands the right type),
  mandatory promotion when capturing a promoted piece, the Queen-capture
  rule (forced =Q, overriding the capturer's own promotion, except for the
  King), no promotion for R/B or already-promoted capturers, and en-passant
  as a promotable capture;
* pawn "dead wood": no promotion on reaching the last rank, and no moves from it;
* three-square castling for both colours (geometry, rook placement, O-O text);
* directional check detection (Y checks only along its capture directions;
  Omni checks diagonally but NOT orthogonally);
* a checkmate reached via apply_move; a serialize round-trip mid-game.

Prints "SELFTEST OK" and exits 0 on success, nonzero on any failure.
"""

from __future__ import annotations

import sys

from agp.chesslike import CState, WHITE, BLACK, cell
from games.decimaka.game import Decimaka

G = Decimaka()


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def mk(pieces, to_move=WHITE, ep=None, castling=()):
    """Build a state from {(c,r): (player, letter)}."""
    st = CState(board=dict(pieces), to_move=to_move, ep=ep,
                castling=frozenset(castling))
    st.reps = {G._poskey_state(st): 1}
    return st


def targets(st, frm):
    """Set of destination cells reachable from `frm` (promo variants merged)."""
    out = set()
    for mv in G.legal_moves(st):
        raw = mv.split("=")[0]
        f, t = raw.split(">")
        if cell(f) == frm:
            out.add(cell(t))
    return out


def moves_from(st, frm):
    return sorted(m for m in G.legal_moves(st)
                  if cell(m.split("=")[0].split(">")[0]) == frm)


KINGS = {(0, 0): (WHITE, "K"), (9, 9): (BLACK, "K")}   # far-corner kings


# --------------------------------------------------------------------------- #
# 1. Opening array
# --------------------------------------------------------------------------- #
s0 = G.initial_state()
b0 = s0.board
check(len(b0) == 52, "52 men on the board")
exp_white = {(0, 0): "R", (3, 0): "Y", (4, 0): "F", (5, 0): "K", (6, 0): "Y",
             (9, 0): "R"}
for sq, t in exp_white.items():
    check(b0.get(sq) == (WHITE, t), f"white {t} at {sq}")
for c, t in enumerate(["C", "T", "N", "B", "L", "S", "B", "N", "T", "C"]):
    check(b0.get((c, 1)) == (WHITE, t), f"white rank2 {t} at file {c}")
    check(b0.get((9 - c, 8)) == (BLACK, t), f"black rank9 {t}")
for c in range(10):
    check(b0.get((c, 2)) == (WHITE, "P") and b0.get((c, 7)) == (BLACK, "P"),
          "pawn ranks")
check(b0.get((4, 9)) == (BLACK, "K") and b0.get((5, 9)) == (BLACK, "F"),
      "Black King e10 / Fiancee f10 (rotational symmetry)")
check(s0.castling == frozenset("KQkq"), "initial castling rights")

# --------------------------------------------------------------------------- #
# 2. Perft (d1 hand-verified piece-by-piece; d2 = 50^2 structurally exact)
# --------------------------------------------------------------------------- #
def perft(st, d):
    if d == 0:
        return 1
    return sum(perft(G.apply_move(st, m), d - 1) for m in G.legal_moves(st))


by_type = {}
for m in G.legal_moves(s0):
    t = b0[cell(m.split("=")[0].split(">")[0])][1]
    by_type[t] = by_type.get(t, 0) + 1
check(by_type == {"P": 20, "R": 4, "Y": 4, "C": 2, "T": 2, "N": 4, "B": 2,
                  "L": 6, "S": 6},
      f"hand-verified d1 breakdown, got {by_type}")
check(perft(s0, 1) == 50, "perft(1) == 50")
check(perft(s0, 2) == 2500, "perft(2) == 2500 (= 50^2)")
check(perft(s0, 3) == 135301, "perft(3) == 135301 (frozen)")

# --------------------------------------------------------------------------- #
# 3. Exact move-target sets (empty board + far kings), both colours
# --------------------------------------------------------------------------- #
# Tee: 1 fwd/back straight, 1 diagonally forward
st = mk({**KINGS, (4, 4): (WHITE, "T")})
check(targets(st, (4, 4)) == {(4, 5), (4, 3), (3, 5), (5, 5)}, "white Tee")
st = mk({**KINGS, (4, 4): (BLACK, "T")}, to_move=BLACK)
check(targets(st, (4, 4)) == {(4, 3), (4, 5), (3, 3), (5, 3)}, "black Tee")

# Cross: 1-2 orthogonally (jumping)
st = mk({**KINGS, (4, 4): (WHITE, "C"), (4, 5): (WHITE, "P")})
check(targets(st, (4, 4)) == {(3, 4), (5, 4), (4, 3), (2, 4), (6, 4), (4, 2),
                              (4, 6)},
      "Cross jumps over the blocker but cannot land on own pawn")

# Y: leaps 1-3 diagonally forward or straight backward
st = mk({**KINGS, (4, 4): (WHITE, "Y")})
check(targets(st, (4, 4)) == {(5, 5), (3, 5), (6, 6), (2, 6), (7, 7), (1, 7),
                              (4, 3), (4, 2), (4, 1)}, "white Y")
st = mk({**KINGS, (4, 4): (BLACK, "Y")}, to_move=BLACK)
check(targets(st, (4, 4)) == {(5, 3), (3, 3), (6, 2), (2, 2), (7, 1), (1, 1),
                              (4, 5), (4, 6), (4, 7)}, "black Y (rotated)")

# Star: jumps 1-3 all 8 directions (24 targets from the centre)
st = mk({**KINGS, (4, 4): (WHITE, "S")})
exp = {(4 + dc * k, 4 + dr * k)
       for dc in (-1, 0, 1) for dr in (-1, 0, 1) if (dc, dr) != (0, 0)
       for k in (1, 2, 3)}
check(targets(st, (4, 4)) == exp, "Star = 24 jump targets")

# Lion: K + N + A + D
st = mk({**KINGS, (4, 4): (WHITE, "L")})
exp = ({(4 + dc, 4 + dr) for dc in (-1, 0, 1) for dr in (-1, 0, 1)} - {(4, 4)}
       | {(4 + a, 4 + b) for a, b in
          [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2),
           (-2, -1), (2, 2), (-2, 2), (2, -2), (-2, -2), (2, 0), (-2, 0),
           (0, 2), (0, -2)]})
check(targets(st, (4, 4)) == exp, "Lion = KNAD (24 targets)")

# Fiancee: non-royal king (may step into 'attacked' squares freely)
st = mk({**KINGS, (4, 4): (WHITE, "F")})
check(len(targets(st, (4, 4))) == 8, "Fiancee = 8 king steps")

# Trident (+T): file slide both ways + forward-diagonal slides, blockable
st = mk({**KINGS, (4, 4): (WHITE, "+T"), (4, 7): (BLACK, "P"),
         (6, 6): (WHITE, "P")})
exp = ({(4, r) for r in (5, 6, 7)} | {(4, r) for r in (0, 1, 2, 3)}
       | {(5, 5)} | {(3, 5), (2, 6), (1, 7), (0, 8)})
check(targets(st, (4, 4)) == exp,
      "white Trident: file both ways (capture at 4,7), fwd diagonals blocked at 6,6")
st = mk({**KINGS, (4, 4): (BLACK, "+T")}, to_move=BLACK)
check((3, 3) in targets(st, (4, 4)) and (3, 5) not in targets(st, (4, 4)),
      "black Trident diagonals point down-board")

# Nightrider (+N): knight-offset rider, blockable
st = mk({**KINGS, (4, 4): (WHITE, "+N"), (5, 6): (BLACK, "P")})
tg = targets(st, (4, 4))
check((5, 6) in tg and (6, 8) not in tg, "Nightrider blocked by the pawn it can take")
check((6, 5) in tg and (8, 6) in tg, "Nightrider rides two steps on a clear line")
check((3, 2) in tg and (2, 0) in tg, "Nightrider rides backward too")

# Omni: moves 1 orthogonally (never captures there), captures 1 diagonally only
st = mk({**KINGS, (4, 4): (WHITE, "O"), (5, 5): (BLACK, "P"),
         (4, 5): (BLACK, "P"), (3, 3): (WHITE, "P")})
tg = targets(st, (4, 4))
check(tg == {(3, 4), (5, 4), (4, 3), (5, 5)},
      f"Omni: ortho steps to empty, diag capture only (got {sorted(tg)})")

# --------------------------------------------------------------------------- #
# 4. Capture-promotion lifecycle
# --------------------------------------------------------------------------- #
# 4a. optional on a plain capture: both strings offered, each lands right
st = mk({**KINGS, (4, 4): (WHITE, "L"), (5, 5): (BLACK, "P")})
mvs = moves_from(st, (4, 4))
check("4,4>5,5" in mvs and "4,4>5,5=O" in mvs, "Lion x pawn: optional Omni")
check(G.apply_move(st, "4,4>5,5=O").board[(5, 5)] == (WHITE, "O"),
      "=O lands an Omni")
check(G.apply_move(st, "4,4>5,5").board[(5, 5)] == (WHITE, "L"),
      "declining keeps the Lion")

# 4b. mandatory when capturing a promoted piece
st = mk({**KINGS, (3, 4): (WHITE, "N"), (5, 5): (BLACK, "O")})
mvs = moves_from(st, (3, 4))
check("3,4>5,5=+N" in mvs and "3,4>5,5" not in mvs,
      "N x Omni: promotion to Nightrider is forced")
check(G.apply_move(st, "3,4>5,5=+N").board[(5, 5)] == (WHITE, "+N"),
      "forced +N lands")

# 4c. unpromotable capturer of a promoted piece: plain only
st = mk({**KINGS, (4, 4): (WHITE, "R"), (4, 7): (BLACK, "O")})
check(moves_from(st, (4, 4)).count("4,4>4,7") == 1
      and not any("=" in m for m in moves_from(st, (4, 4))),
      "Rook x Omni: no promotion exists, plain move only")

# 4d. already-promoted capturer: plain only
st = mk({**KINGS, (4, 4): (WHITE, "+T"), (4, 7): (BLACK, "O")})
check(not any("=" in m for m in moves_from(st, (4, 4))),
      "Trident x Omni: already promoted, stays a Trident")

# 4e. Queen-capture rule: forced =Q, overriding the capturer's own promotion
st = mk({**KINGS, (4, 4): (WHITE, "T"), (4, 5): (BLACK, "Q")})
mvs = moves_from(st, (4, 4))
check("4,4>4,5=Q" in mvs and "4,4>4,5" not in mvs
      and "4,4>4,5=+T" not in mvs, "Tee x Queen: forced =Q (not +T)")
check(G.apply_move(st, "4,4>4,5=Q").board[(4, 5)] == (WHITE, "Q"),
      "Tee becomes a Queen")
st = mk({**KINGS, (4, 4): (WHITE, "B"), (6, 6): (BLACK, "Q")})
check(moves_from(st, (4, 4)) == sorted(
    m for m in G.legal_moves(st) if m.startswith("4,4>")) and
    "4,4>6,6=Q" in moves_from(st, (4, 4)) and
    "4,4>6,6" not in moves_from(st, (4, 4)),
    "Bishop x Queen: even an unpromotable piece is forced to =Q")

# ... but the King never promotes
st = mk({(4, 4): (WHITE, "K"), (5, 5): (BLACK, "Q"), (9, 9): (BLACK, "K"),
         (5, 6): (WHITE, "R")})   # rook guards 5,5 so KxQ is legal
mvs = moves_from(st, (4, 4))
check("4,4>5,5" in mvs and "4,4>5,5=Q" not in mvs, "King x Queen: no promotion")

# 4f. en passant is a promotable pawn capture
st = mk({**KINGS, (3, 5): (WHITE, "P"), (4, 7): (BLACK, "P")}, to_move=BLACK)
st = G.apply_move(st, "4,7>4,5")            # black double step
mvs = moves_from(st, (3, 5))
check("3,5>4,6" in mvs and "3,5>4,6=O" in mvs, "e.p. offers optional Omni")
ns = G.apply_move(st, "3,5>4,6=O")
check(ns.board[(4, 6)] == (WHITE, "O") and (4, 5) not in ns.board,
      "e.p. =O: Omni lands, doubled pawn removed")

# --------------------------------------------------------------------------- #
# 5. Pawn dead wood on the last rank
# --------------------------------------------------------------------------- #
st = mk({**KINGS, (4, 8): (WHITE, "P")})
check(moves_from(st, (4, 8)) == ["4,8>4,9"], "pawn to last rank: no =O, no zone promo")
ns = G.apply_move(st, "4,8>4,9")
check(ns.board[(4, 9)] == (WHITE, "P"), "still a pawn (dead wood)")
ns2 = G.apply_move(ns, [m for m in G.legal_moves(ns)][0])  # any black reply
check(moves_from(ns2, (4, 9)) == [], "dead wood has no moves")
# ... but a CAPTURE onto the last rank may promote
st = mk({**KINGS, (4, 8): (WHITE, "P"), (5, 9): (BLACK, "N")})
mvs = moves_from(st, (4, 8))
check("4,8>5,9=O" in mvs and "4,8>5,9" in mvs, "capture onto last rank: optional =O")

# --------------------------------------------------------------------------- #
# 6. Three-square castling, both colours
# --------------------------------------------------------------------------- #
st = mk({(0, 0): (WHITE, "R"), (9, 0): (WHITE, "R"), (5, 0): (WHITE, "K"),
         (0, 9): (BLACK, "R"), (9, 9): (BLACK, "R"), (4, 9): (BLACK, "K")},
        castling="KQkq")
mvs = G.legal_moves(st)
check("5,0>8,0" in mvs and "5,0>2,0" in mvs, "White may castle both wings")
ns = G.apply_move(st, "5,0>8,0")
check(ns.board[(8, 0)] == (WHITE, "K") and ns.board[(7, 0)] == (WHITE, "R")
      and (9, 0) not in ns.board, "White O-O: K i1, R h1")
check("K" not in ns.castling and "Q" not in ns.castling, "White rights spent")
check(G.describe_move(st, "5,0>8,0") == "O-O", "O-O notation")
# (After White's O-O the h1 rook attacks h10 through the open file, so Black's
# kingside castle is rightly gone -- test Black from its own position.)
check("4,9>7,9" not in G.legal_moves(ns),
      "Black O-O barred: king would pass through the h-file rook's attack")
stb = mk({(0, 0): (WHITE, "R"), (9, 0): (WHITE, "R"), (5, 0): (WHITE, "K"),
          (0, 9): (BLACK, "R"), (9, 9): (BLACK, "R"), (4, 9): (BLACK, "K")},
         to_move=BLACK, castling="KQkq")
mvs_b = G.legal_moves(stb)
check("4,9>7,9" in mvs_b and "4,9>1,9" in mvs_b, "Black may castle both wings")
nb = G.apply_move(stb, "4,9>1,9")
check(nb.board[(1, 9)] == (BLACK, "K") and nb.board[(2, 9)] == (BLACK, "R"),
      "Black O-O-O: K b10, R c10")

# --------------------------------------------------------------------------- #
# 7. Directional check detection
# --------------------------------------------------------------------------- #
# Black Y attacks diagonally *forward* (down-board): from (5,5) it hits (4,4).
st = mk({(4, 4): (WHITE, "K"), (5, 5): (BLACK, "Y"), (9, 9): (BLACK, "K")})
check(G.in_check(st.board, WHITE), "black Y checks diagonally forward")
# ...from straight above it does not (straight FORWARD is not a Y direction)...
st = mk({(4, 4): (WHITE, "K"), (4, 5): (BLACK, "Y"), (9, 9): (BLACK, "K")})
check(not G.in_check(st.board, WHITE), "black Y has no straight-forward attack")
# ...but from below it does: black's straight-BACKWARD leaps point up-board.
st = mk({(4, 4): (WHITE, "K"), (4, 3): (BLACK, "Y"), (9, 9): (BLACK, "K")})
check(G.in_check(st.board, WHITE), "black Y attacks straight backward (up-board)")
# Omni checks diagonally only.
st = mk({(4, 4): (WHITE, "K"), (5, 5): (BLACK, "O"), (9, 9): (BLACK, "K")})
check(G.in_check(st.board, WHITE), "Omni checks diagonally")
st = mk({(4, 4): (WHITE, "K"), (4, 5): (BLACK, "O"), (9, 9): (BLACK, "K")})
check(not G.in_check(st.board, WHITE), "Omni never checks orthogonally")

# --------------------------------------------------------------------------- #
# 8. Checkmate via apply_move
# --------------------------------------------------------------------------- #
st = mk({(9, 9): (BLACK, "K"), (8, 7): (WHITE, "K"), (0, 5): (WHITE, "R")})
check(not G.is_terminal(st), "not over before the mating move")
ns = G.apply_move(st, "0,5>0,9")
check(G.is_terminal(ns), "back-rank rook mate is terminal")
check(G.returns(ns) == [1.0, -1.0], "White wins")

# Stalemate is a draw: lone black K a10; white K a8 covers a9, Rb2 the b-file.
st = mk({(0, 9): (BLACK, "K"), (0, 7): (WHITE, "K"), (5, 1): (WHITE, "R")})
ns = G.apply_move(st, "5,1>1,1")            # Rb2: a10-king has no move, no check
check(G.is_terminal(ns) and G.returns(ns) == [0.0, 0.0], "stalemate draws")

# --------------------------------------------------------------------------- #
# 9. Serialize round-trip mid-game (after a capture-promotion)
# --------------------------------------------------------------------------- #
st = mk({**KINGS, (4, 4): (WHITE, "L"), (5, 5): (BLACK, "P"),
         (2, 2): (WHITE, "T")})
st = G.apply_move(st, "4,4>5,5=O")
rt = G.deserialize(G.serialize(st))
check(rt.board == st.board and rt.to_move == st.to_move
      and rt.castling == st.castling and rt.ep == st.ep
      and rt.halfmove == st.halfmove and rt.ply == st.ply,
      "serialize round-trip")
check(sorted(G.legal_moves(rt)) == sorted(G.legal_moves(st)),
      "round-tripped state generates identical moves")

print("SELFTEST OK")
