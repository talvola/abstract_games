#!/usr/bin/env python3
"""Standalone correctness anchor for Omega Chess (Daniel MacDonald, 1992).

Run from the engine dir with::

    PYTHONPATH=. python3 games/omega_chess/selftest.py

Pure stdlib + this game only, fast (~5s). Prints ``SELFTEST OK`` and exits 0
on success, nonzero on any failure.

It asserts:

* the 104-cell board geometry (10x10 field at 1..10 plus the four wizard
  squares (0,0)/(11,0)/(11,11)/(0,11); everything else off-board);
* the setup (44 men: C R N B Q K B N R C / ten pawns, wizards on the corner
  squares, mirrored);
* the opening **perft** baseline d1=40, d2=1600, d3=67202. No published node
  counts exist for Omega Chess, so d2/d3 are frozen self-computed values, but
  d1=40 is fully hand-verified against the official rules page (30 pawn moves
  incl. the triple step; knights 2+2; champions 2+2 -- exactly the "a2/c2,
  h2/j2" entries the source lists; wizards 1+1 -- exactly the "a2, j2"
  entries the source lists);
* exact move-target sets for the **Champion** (wazir + dabbaba + alfil,
  jumping, incl. INTO and OUT OF a wizard square) and the **Wizard**
  (ferz + camel, jumping, colour-bound, incl. INTO and OUT OF a wizard
  square);
* **pawns**: 1/2/3-step first move, no multi-step after moving, blocked
  multi-steps, and **en passant on BOTH passed squares** of a triple step
  (plus the single passed square of a double step, and e.p. expiry);
* **castling** both sides on rank r=1/r=10 (king f-file two squares, rook to
  the crossed square), refused through an attacked square, rights lost on a
  king move;
* **promotion** on r=10 (White) / r=1 (Black) -- NOT the 12x12 embedding edge
  -- mandatory, to any of Q/C/W/R/B/N;
* two published mating lines reached via apply_move: the Omega Chess
  scholar's mate (1. f4 f5 2. Bc4 Bc5 3. Qj5 Ng7 4. Qxg8#) and fool's mate
  (1. Wa2 Ng7 2. Wb5 Ni6 3. We6#), both from the Wikipedia article;
* serialize round-trips (including a live two-target e.p. state);
* the render spec is the polygons format (a LIST of {id, points}, 104 cells)
  and JSON-serialisable.
"""

import json
import sys

from agp.chesslike import CState, WHITE, BLACK
from games.omega_chess.game import OmegaChess

G = OmegaChess()


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def targets(state, frm):
    """Destination cells of all legal moves from ``frm`` (promo variants merged)."""
    out = set()
    fs = f"{frm[0]},{frm[1]}"
    for m in G.legal_moves(state):
        raw = m.split("=")[0]
        a, b = raw.split(">")
        if a == fs:
            out.add(tuple(int(x) for x in b.split(",")))
    return out


def mk(board, to_move=WHITE, castling=frozenset(), ep=None):
    st = CState(board=dict(board), to_move=to_move, castling=castling, ep=ep)
    st.reps = {G._poskey_state(st): 1}
    return st


def perft(state, d):
    if d == 0:
        return 1
    return sum(perft(G.apply_move(state, m), d - 1) for m in G.legal_moves(state))


# --------------------------------------------------------------------------- #
# 1. geometry
# --------------------------------------------------------------------------- #
valid = [(c, r) for r in range(-1, 14) for c in range(-1, 14) if G.on(c, r)]
check(len(valid) == 104, f"on(): expected 104 valid cells, got {len(valid)}")
for sq in ((0, 0), (11, 0), (11, 11), (0, 11)):
    check(G.on(*sq), f"wizard square {sq} must be on the board")
for c in range(1, 11):
    for r in range(1, 11):
        check(G.on(c, r), f"core square {(c, r)} must be on the board")
for sq in ((0, 1), (1, 0), (11, 1), (10, 0), (0, 10), (5, 0), (0, 5),
           (11, 5), (5, 11), (12, 12), (-1, 0), (11, 10), (10, 11)):
    check(not G.on(*sq), f"{sq} must be OFF the board")

# --------------------------------------------------------------------------- #
# 2. setup
# --------------------------------------------------------------------------- #
st0 = G.initial_state()
check(len(st0.board) == 44, f"setup: expected 44 men, got {len(st0.board)}")
BACK = ["C", "R", "N", "B", "Q", "K", "B", "N", "R", "C"]
for i, t in enumerate(BACK):
    check(st0.board[(i + 1, 1)] == (WHITE, t), f"White back rank at c={i+1}")
    check(st0.board[(i + 1, 10)] == (BLACK, t), f"Black back rank at c={i+1}")
for c in range(1, 11):
    check(st0.board[(c, 2)] == (WHITE, "P"), "White pawns on r=2")
    check(st0.board[(c, 9)] == (BLACK, "P"), "Black pawns on r=9")
check(st0.board[(0, 0)] == (WHITE, "W") and st0.board[(11, 0)] == (WHITE, "W"),
      "White wizards on (0,0)/(11,0)")
check(st0.board[(0, 11)] == (BLACK, "W") and st0.board[(11, 11)] == (BLACK, "W"),
      "Black wizards on (0,11)/(11,11)")
check(st0.castling == frozenset("KQkq"), "initial castling rights")

# opening wizard/champion entries, verbatim from the source page
check(targets(st0, (0, 0)) == {(1, 3)}, "wizard w1 opening move = a2")
check(targets(st0, (11, 0)) == {(10, 3)}, "wizard w2 opening move = j2")
check(targets(st0, (1, 1)) == {(1, 3), (3, 3)}, "champion a0 enters at a2/c2")
check(targets(st0, (10, 1)) == {(10, 3), (8, 3)}, "champion j0 enters at h2/j2")

# --------------------------------------------------------------------------- #
# 3. perft
# --------------------------------------------------------------------------- #
for d, want in ((1, 40), (2, 1600), (3, 67202)):
    got = perft(st0, d)
    check(got == want, f"perft({d}) = {got}, expected {want}")

# --------------------------------------------------------------------------- #
# 4. Champion exact move sets
# --------------------------------------------------------------------------- #
b = {(2, 2): (WHITE, "C"), (6, 6): (WHITE, "K"), (6, 8): (BLACK, "K")}
st = mk(b)
want = {(1, 2), (3, 2), (2, 1), (2, 3),          # wazir
        (4, 2), (2, 4),                          # dabbaba (others off-board)
        (4, 4), (0, 0)}                          # alfil ((0,0) = wizard square!)
check(targets(st, (2, 2)) == want, f"champion at (2,2): {targets(st, (2,2))}")

# champion OUT OF a wizard square: only the alfil jump back to (2,2) exists
b = {(0, 0): (WHITE, "C"), (6, 6): (WHITE, "K"), (6, 8): (BLACK, "K")}
st = mk(b)
check(targets(st, (0, 0)) == {(2, 2)}, "champion on w1 has exactly one exit")

# champion JUMPS: surround it with men; leaps still work, wazir steps blocked
b = {(5, 5): (WHITE, "C"), (4, 5): (WHITE, "P"), (6, 5): (BLACK, "P"),
     (5, 4): (WHITE, "P"), (5, 6): (BLACK, "P"),
     (1, 1): (WHITE, "K"), (10, 10): (BLACK, "K")}
st = mk(b)
got = targets(st, (5, 5))
check((3, 5) in got and (7, 5) in got and (5, 3) in got and (5, 7) in got,
      "champion dabbaba jumps over adjacent men")
check((3, 3) in got and (7, 7) in got and (3, 7) in got and (7, 3) in got,
      "champion alfil jumps")
check((6, 5) in got and (5, 6) in got, "champion captures enemy wazir-step men")
check((4, 5) not in got and (5, 4) not in got, "champion blocked by own men")
check((4, 4) not in got and (6, 6) not in got, "champion has NO diagonal step")

# --------------------------------------------------------------------------- #
# 5. Wizard exact move sets
# --------------------------------------------------------------------------- #
b = {(5, 5): (WHITE, "W"), (1, 1): (WHITE, "K"), (10, 10): (BLACK, "K")}
st = mk(b)
want = {(4, 4), (6, 6), (4, 6), (6, 4),                              # ferz
        (6, 8), (4, 8), (6, 2), (4, 2), (8, 6), (8, 4), (2, 6), (2, 4)}  # camel
check(targets(st, (5, 5)) == want, f"wizard at (5,5): {targets(st, (5,5))}")
# colour-bound: every target keeps the (c+r) parity
check(all((c + r) % 2 == (5 + 5) % 2 for (c, r) in want), "wizard colour-bound")

# wizard INTO a wizard square (ferz from (1,1)) and OUT of one
b = {(1, 1): (WHITE, "W"), (6, 6): (WHITE, "K"), (6, 8): (BLACK, "K")}
st = mk(b)
check(targets(st, (1, 1)) == {(0, 0), (2, 2), (2, 4), (4, 2)},
      f"wizard at (1,1): {targets(st, (1,1))}")
b = {(0, 0): (WHITE, "W"), (6, 6): (WHITE, "K"), (6, 8): (BLACK, "K")}
st = mk(b)
check(targets(st, (0, 0)) == {(1, 1), (1, 3), (3, 1)},
      "wizard on w1 exits to a0/a2/c0")

# wizard jumps + captures: camel over a wall, ferz blocked by own man
b = {(5, 5): (WHITE, "W"), (4, 4): (WHITE, "P"), (6, 6): (BLACK, "P"),
     (5, 6): (WHITE, "P"), (6, 7): (WHITE, "P"),
     (1, 1): (WHITE, "K"), (10, 10): (BLACK, "K")}
st = mk(b)
got = targets(st, (5, 5))
check((6, 8) in got, "wizard camel-jumps over intervening men")
check((6, 6) in got, "wizard captures with the ferz step")
check((4, 4) not in got, "wizard blocked by own man on ferz step")

# --------------------------------------------------------------------------- #
# 6. pawns: 1/2/3-step and en passant on every passed square
# --------------------------------------------------------------------------- #
st = G.initial_state()
check(targets(st, (4, 2)) == {(4, 3), (4, 4), (4, 5)},
      "pawn first move: 1, 2 or 3 straight steps")
# after any move the pawn is single-step only
st1 = G.apply_move(st, "4,2>4,3")
st1 = G.apply_move(st1, "4,9>4,8")
check(targets(st1, (4, 3)) == {(4, 4)}, "moved pawn steps a single square")
# blocked multi-step: a piece two ahead stops both the 2- and 3-step
b = {(4, 2): (WHITE, "P"), (4, 4): (BLACK, "N"),
     (1, 1): (WHITE, "K"), (10, 10): (BLACK, "K")}
st = mk(b)
check(targets(st, (4, 2)) == {(4, 3)}, "pawn multi-step blocked at the 2nd square")

# triple step -> e.p. on BOTH passed squares, and it removes the moved pawn
b = {(4, 2): (WHITE, "P"), (3, 5): (BLACK, "P"), (5, 4): (BLACK, "P"),
     (1, 1): (WHITE, "K"), (10, 10): (BLACK, "K")}
st = mk(b)
st = G.apply_move(st, "4,2>4,5")                       # triple step
check(st.ep == (((4, 3), (4, 4)), (4, 5)), f"3-step e.p. state: {st.ep}")
lm = G.legal_moves(st)
check("3,5>4,4" in lm, "e.p. capture on the 2nd passed square")
check("5,4>4,3" in lm, "e.p. capture on the 1st passed square")
nxt = G.apply_move(st, "3,5>4,4")
check((4, 5) not in nxt.board and nxt.board[(4, 4)] == (BLACK, "P"),
      "e.p. removes the triple-stepped pawn")
nxt = G.apply_move(st, "5,4>4,3")
check((4, 5) not in nxt.board and nxt.board[(4, 3)] == (BLACK, "P"),
      "e.p. on the other passed square removes the pawn too")
check(nxt.halfmove == 0, "e.p. capture resets the 50-move counter")

# double step -> e.p. on the single passed square; and e.p. expires
b = {(4, 2): (WHITE, "P"), (3, 4): (BLACK, "P"),
     (9, 9): (BLACK, "P"),
     (1, 1): (WHITE, "K"), (10, 10): (BLACK, "K")}
st = mk(b)
st = G.apply_move(st, "4,2>4,4")
check(st.ep == (((4, 3),), (4, 4)), f"2-step e.p. state: {st.ep}")
check("3,4>4,3" in G.legal_moves(st), "e.p. capture after a double step")
st = G.apply_move(st, "9,9>9,8")                        # Black plays elsewhere
st = G.apply_move(st, "1,1>1,2")
check(st.ep is None and "3,4>4,3" not in G.legal_moves(st), "e.p. expires")

# a serialize round-trip must preserve a live two-target e.p.
b = {(4, 2): (WHITE, "P"), (3, 5): (BLACK, "P"),
     (1, 1): (WHITE, "K"), (10, 10): (BLACK, "K")}
st = G.apply_move(mk(b), "4,2>4,5")
rt = G.deserialize(json.loads(json.dumps(G.serialize(st))))
check(rt.ep == st.ep and rt.board == st.board and rt.to_move == st.to_move,
      "serialize round-trip with a two-target e.p.")
check(sorted(G.legal_moves(rt)) == sorted(G.legal_moves(st)),
      "round-tripped state generates the same moves")

# --------------------------------------------------------------------------- #
# 7. castling
# --------------------------------------------------------------------------- #
def castle_pos(extra=(), to_move=WHITE):
    b = {(6, 1): (WHITE, "K"), (2, 1): (WHITE, "R"), (9, 1): (WHITE, "R"),
         (6, 10): (BLACK, "K"), (2, 10): (BLACK, "R"), (9, 10): (BLACK, "R")}
    b.update(dict(extra))
    return mk(b, to_move=to_move, castling=frozenset("KQkq"))

st = castle_pos()
lm = G.legal_moves(st)
check("6,1>8,1" in lm and "6,1>4,1" in lm, "White may castle both sides")
nxt = G.apply_move(st, "6,1>8,1")
check(nxt.board[(8, 1)] == (WHITE, "K") and nxt.board[(7, 1)] == (WHITE, "R")
      and (9, 1) not in nxt.board, "kingside castle: Kf0-h0, Ri0-g0")
check(nxt.castling == frozenset("kq"), "White rights gone after castling")
nxt = G.apply_move(st, "6,1>4,1")
check(nxt.board[(4, 1)] == (WHITE, "K") and nxt.board[(5, 1)] == (WHITE, "R")
      and (2, 1) not in nxt.board, "queenside castle: Kf0-d0, Rb0-e0")
st_b = castle_pos(to_move=BLACK)
lm = G.legal_moves(st_b)
check("6,10>8,10" in lm and "6,10>4,10" in lm, "Black may castle both sides")
nxt = G.apply_move(st_b, "6,10>8,10")
check(nxt.board[(8, 10)] == (BLACK, "K") and nxt.board[(7, 10)] == (BLACK, "R"),
      "Black kingside castle")
check(G.describe_move(st, "6,1>8,1") == "O-O"
      and G.describe_move(st, "6,1>4,1") == "O-O-O", "castle notation")

# refused: king would cross an attacked square (rook eyeing g0 = (7,1))
st = castle_pos(extra={(7, 8): (BLACK, "R")})
lm = G.legal_moves(st)
check("6,1>8,1" not in lm, "no castling through an attacked square")
check("6,1>4,1" in lm, "queenside unaffected by the g-file attack")
# refused: a piece between king and rook
st = castle_pos(extra={(8, 1): (WHITE, "N")})
check("6,1>8,1" not in G.legal_moves(st), "no castling over a piece")
# refused: an enemy slider on j0 BEHIND the castling rook -- its attack on the
# king's landing square h0 is blocked by the rook until the rook vacates, so
# this is castling into check (a square that cannot exist behind an 8x8 rook).
st = castle_pos(extra={(10, 1): (BLACK, "R")})
check("6,1>8,1" not in G.legal_moves(st),
      "no castling into a check opened by the rook vacating i0")
check("6,1>4,1" in G.legal_moves(st), "queenside unaffected by the j0 attacker")
st = castle_pos(extra={(1, 1): (BLACK, "Q")})
check("6,1>4,1" not in G.legal_moves(st),
      "no queenside castling into a check opened by the rook vacating b0")
# rights lost after a king move (even back)
st = castle_pos()
st = G.apply_move(st, "6,1>6,2")
st = G.apply_move(st, "6,10>6,9")
st = G.apply_move(st, "6,2>6,1")
st = G.apply_move(st, "6,9>6,10")
check(st.castling == frozenset(), "king moves burn castling rights")
check("6,1>8,1" not in G.legal_moves(st), "no castling after the king moved")

# --------------------------------------------------------------------------- #
# 8. promotion on r=10 / r=1 (not the 12x12 edge)
# --------------------------------------------------------------------------- #
b = {(3, 9): (WHITE, "P"), (1, 1): (WHITE, "K"), (10, 10): (BLACK, "K")}
st = mk(b)
lm = [m for m in G.legal_moves(st) if m.startswith("3,9>3,10")]
check(sorted(lm) == sorted(f"3,9>3,10={t}" for t in ("Q", "C", "W", "R", "B", "N")),
      f"White promotion choices on r=10: {lm}")
check("3,9>3,10" not in G.legal_moves(st), "promotion is mandatory")
nxt = G.apply_move(st, "3,9>3,10=C")
check(nxt.board[(3, 10)] == (WHITE, "C"), "promotes to a Champion")
b = {(3, 2): (BLACK, "P"), (8, 1): (WHITE, "K"), (10, 10): (BLACK, "K")}
st = mk(b, to_move=BLACK)
lm = [m for m in G.legal_moves(st) if m.startswith("3,2>3,1")]
check(sorted(lm) == sorted(f"3,2>3,1={t}" for t in ("Q", "C", "W", "R", "B", "N")),
      f"Black promotion choices on r=1: {lm}")
nxt = G.apply_move(st, "3,2>3,1=W")
check(nxt.board[(3, 1)] == (BLACK, "W"), "Black promotes on r=1")

# --------------------------------------------------------------------------- #
# 9. published mating lines (Wikipedia) reached via apply_move
# --------------------------------------------------------------------------- #
# Scholar's mate: 1. f4 f5 2. Bc4 Bc5 3. Qj5 Ng7 4. Qxg8#
st = G.initial_state()
for mv in ("6,2>6,5", "6,9>6,6",      # 1. f4 f5   (triple steps)
           "7,1>3,5", "7,10>3,6",     # 2. Bc4 Bc5
           "5,1>10,6", "8,10>7,8",    # 3. Qj5 Ng7
           "10,6>7,9"):               # 4. Qxg8#
    check(mv in G.legal_moves(st), f"scholar's mate: {mv} must be legal")
    st = G.apply_move(st, mv)
check(G.is_terminal(st), "scholar's mate position is terminal")
check(G.returns(st) == [1.0, -1.0], "scholar's mate: White wins")
check(G.in_check(st.board, BLACK), "scholar's mate: Black is in check")

# Fool's mate: 1. Wa2 Ng7 2. Wb5 Ni6 3. We6#
st = G.initial_state()
for mv in ("0,0>1,3", "8,10>7,8",     # 1. Wa2 Ng7
           "1,3>2,6", "7,8>9,7",      # 2. Wb5 Ni6
           "2,6>5,7"):                # 3. We6#
    check(mv in G.legal_moves(st), f"fool's mate: {mv} must be legal")
    st = G.apply_move(st, mv)
check(G.is_terminal(st), "fool's mate position is terminal")
check(G.returns(st) == [1.0, -1.0], "fool's mate: White wins")

# and a stalemate is a draw: lone Black king cornered on w3 by Q+K.
# The w3 corner touches the field ONLY at (10,10); a queen on the j-file
# covers that square without checking the king -> stalemate (this is the
# "unassailable corner" endgame peculiarity the Wikipedia article describes).
b = {(11, 11): (BLACK, "K"), (10, 8): (WHITE, "Q"), (1, 1): (WHITE, "K")}
st = mk(b, to_move=BLACK)
check(not G.in_check(st.board, BLACK), "stalemate probe: not in check")
check(G.legal_moves(st) == [], "stalemate probe: no legal moves")
check(G.is_terminal(st) and G.returns(st) == [0.0, 0.0], "stalemate is a draw")

# --------------------------------------------------------------------------- #
# 10. render probe: polygons format
# --------------------------------------------------------------------------- #
spec = G.render(G.initial_state())
board = spec["board"]
check(board["type"] == "polygons", "board.type must be 'polygons'")
check(isinstance(board["cells"], list), "board.cells must be a LIST")
check(len(board["cells"]) == 104, f"expected 104 cells, got {len(board['cells'])}")
for cspec in board["cells"]:
    check(set(cspec.keys()) >= {"id", "points"}, "cells entries need id+points")
    check(isinstance(cspec["points"], list) and len(cspec["points"]) == 4,
          "each cell is a 4-point square")
ids = {cspec["id"] for cspec in board["cells"]}
check("0,0" in ids and "11,11" in ids and "5,5" in ids, "cell ids are 'c,r'")
check(len(spec["pieces"]) == 44, "44 pieces in the opening render")
check(all(p["cell"] in ids for p in spec["pieces"]), "pieces sit on board cells")
json.dumps(spec)                                        # must be JSON-able
check(spec.get("pieceset") == "chess", "chess pieceset hint present")

# move-log notation spot checks (official files a-j, ranks 0-9, w-squares)
st = G.initial_state()
check(G.describe_move(st, "6,2>6,5") == "Pf1-f4", "pawn notation")
check(G.describe_move(st, "0,0>1,3") == "Ww1-a2", "wizard-square notation")

print("SELFTEST OK")
