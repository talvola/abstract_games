#!/usr/bin/env python3
"""Standalone correctness anchor for Elven Chess (H. G. Muller, 2014).

Run from the engine root with::

    PYTHONPATH=. python3 games/elven_chess/selftest.py

Pure stdlib (imports only ``agp`` + this game), ~15s. Asserts:

* the exact opening array (CVP rules-page setup: Warlock e2/f9, Queen f2/e9);
* frozen self-computed **perft** d1=61, d2=3721, d3=227398. d1 is fully
  hand-verified piece-by-piece against the source diagram (P 20, R 7, N 6,
  B 4, Elf 3, Warlock 11 [7 leaps + 2 adjacent steps + 2 passes], Q 2,
  Goblin 2, D 2, K 2 + 2 castles = 61); d2 = 61^2 exactly (the armies provably
  cannot interact at depth 2), an independent structural cross-check;
* exact legal-target sets for Goblin (R+K step), Elf (B+K step), Dwarf
  (commoner) and the full Warlock/Lion move set (5x5 leaps, adjacent steps as
  ``f>m>m``, first-leg-capture double moves incl. igui return, turn passes);
* the **royal rule**: a Warlock may capture the enemy Warlock directly only
  onto a king-safe square, but may still grab a defended Warlock *in passing*
  when its final square is safe;
* the **iron rule** lifecycle via apply_move: NxW makes the survivor
  uncapturable for exactly one turn (capture absent from legal_moves, then
  available again), with the flag surviving a serialize round-trip;
* mandatory last-3-ranks pawn promotion to Q/N/R/B (both colours);
* three-square castling (both wings available in the opening; rook placement);
* igui (capture-and-return) and turn-pass board effects;
* a checkmate reached via apply_move.

Prints "SELFTEST OK" and exits 0 on success, nonzero on any failure.
"""

from __future__ import annotations

import sys

from agp.chesslike import WHITE, BLACK
from games.elven_chess.game import ElvenChess, WState

G = ElvenChess()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def mk(pieces, to_move=WHITE, iron=None, rights=frozenset()):
    st = WState(board=dict(pieces), to_move=to_move, castling=rights,
                ep=None, iron=iron)
    st.reps = {G._poskey_state(st): 1}
    return st


def targets_from(state, frm):
    """Destination-or-path suffixes of legal moves starting at ``frm``."""
    pre = f"{frm[0]},{frm[1]}>"
    return {m for m in G.legal_moves(state) if m.startswith(pre)}


def perft(state, depth):
    if depth == 0:
        return 1
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


# ---- 1. setup ---------------------------------------------------------------
s0 = G.initial_state()
b = s0.board
check(len(b) == 46, f"expected 46 men, got {len(b)}")
for sq, want in {(5, 0): (WHITE, "K"), (0, 0): (WHITE, "R"), (9, 0): (WHITE, "R"),
                 (3, 1): (WHITE, "E"), (4, 1): (WHITE, "W"), (5, 1): (WHITE, "Q"),
                 (6, 1): (WHITE, "G"), (0, 1): (WHITE, "D"), (9, 1): (WHITE, "D"),
                 (4, 9): (BLACK, "K"), (0, 9): (BLACK, "R"), (9, 9): (BLACK, "R"),
                 (6, 8): (BLACK, "E"), (5, 8): (BLACK, "W"), (4, 8): (BLACK, "Q"),
                 (3, 8): (BLACK, "G"), (0, 8): (BLACK, "D"), (9, 8): (BLACK, "D")}.items():
    check(b.get(sq) == want, f"setup: {sq} = {b.get(sq)}, want {want}")
for c in range(10):
    check(b[(c, 2)] == (WHITE, "P") and b[(c, 7)] == (BLACK, "P"), "pawn ranks")
check(s0.castling == frozenset("KQkq"), "initial castling rights")

# ---- 2. perft ---------------------------------------------------------------
check(perft(s0, 1) == 61, "perft(1) != 61")
check(perft(s0, 2) == 3721, "perft(2) != 3721 (= 61^2)")
check(perft(s0, 3) == 227398, "perft(3) != 227398")

# ---- 3. piece move-target sets ---------------------------------------------
# Goblin = Rook + King step.
s = mk({(0, 0): (WHITE, "K"), (9, 0): (BLACK, "K"), (4, 4): (WHITE, "G")})
want = {f"4,4>{c},4" for c in range(10) if c != 4}
want |= {f"4,4>4,{r}" for r in range(10) if r != 4}
want |= {"4,4>3,3", "4,4>5,5", "4,4>3,5", "4,4>5,3"}
check(targets_from(s, (4, 4)) == want, "Goblin move set")

# Elf = Bishop + King step (SW ray blocked by the own King on a1).
s = mk({(0, 0): (WHITE, "K"), (9, 0): (BLACK, "K"), (4, 4): (WHITE, "E")})
want = ({f"4,4>{4+i},{4+i}" for i in range(1, 6)}          # NE to j10
        | {f"4,4>{4-i},{4+i}" for i in range(1, 5)}        # NW to a9
        | {f"4,4>{4+i},{4-i}" for i in range(1, 5)}        # SE to i1
        | {f"4,4>{4-i},{4-i}" for i in range(1, 4)}        # SW, K blocks a1
        | {"4,4>5,4", "4,4>3,4", "4,4>4,5", "4,4>4,3"})    # king steps
check(targets_from(s, (4, 4)) == want, "Elf move set")

# Dwarf = Commoner (all 8 king steps).
s = mk({(0, 0): (WHITE, "K"), (9, 0): (BLACK, "K"), (4, 4): (WHITE, "D")})
want = {f"4,4>{4+dc},{4+dr}" for dc in (-1, 0, 1) for dr in (-1, 0, 1)
        if (dc, dr) != (0, 0)}
check(targets_from(s, (4, 4)) == want, "Dwarf move set")

# Warlock/Lion: own pawn d5, enemy pawn e6 -> leaps, f>m>m adjacent steps,
# double moves through the captured pawn (incl. igui return), and passes.
s = mk({(0, 0): (WHITE, "K"), (9, 9): (BLACK, "K"), (4, 4): (WHITE, "W"),
        (3, 4): (WHITE, "P"), (4, 5): (BLACK, "P")})
adj = [(3, 3), (4, 3), (5, 3), (5, 4), (3, 5), (4, 5), (5, 5)]   # not own (3,4)
box = {(c, r) for c in range(2, 7) for r in range(2, 7)} - {(4, 4)}
far = box - set(adj) - {(3, 4)}
want = {f"4,4>{c},{r}>{c},{r}" for (c, r) in adj}                 # adjacent steps
want |= {f"4,4>{c},{r}" for (c, r) in far}                        # 16 direct leaps
want |= {f"4,4>4,5>{c},{r}" for (c, r) in                         # capture + go on
         [(4, 4), (5, 4), (3, 5), (5, 5), (3, 6), (4, 6), (5, 6)]}
want |= {f"4,4>{c},{r}>4,4" for (c, r) in adj if (c, r) != (4, 5)}  # passes
check(targets_from(s, (4, 4)) == want, "Warlock move set")

# Igui: capture the e6 pawn and return -- pawn gone, Warlock back home.
s1 = G.apply_move(s, "4,4>4,5>4,4")
check(s1.board.get((4, 4)) == (WHITE, "W") and (4, 5) not in s1.board
      and s1.to_move == BLACK and s1.halfmove == 0, "igui capture-and-return")
# Pass: board unchanged, turn switches, halfmove counts up.
s1 = G.apply_move(s, "4,4>3,3>4,4")
check(s1.board == s.board and s1.to_move == BLACK and s1.halfmove == 1,
      "Warlock turn pass")

# ---- 4. royal rule (WxW only onto a king-safe square) ------------------------
pos = {(0, 0): (WHITE, "K"), (9, 9): (BLACK, "K"),
       (4, 4): (WHITE, "W"), (5, 5): (BLACK, "W"), (6, 6): (BLACK, "P")}
s = mk(pos)
lm = G.legal_moves(s)
check("4,4>5,5>5,5" not in lm, "WxW onto a defended square must be illegal")
check("4,4>5,5>4,5" in lm, "WxW in passing to a safe square must be legal")
del pos[(6, 6)]                                   # remove the defender
lm = G.legal_moves(mk(pos))
check("4,4>5,5>5,5" in lm, "WxW of an undefended Warlock must be legal")

# ---- 5. iron rule lifecycle --------------------------------------------------
s = mk({(0, 0): (WHITE, "K"), (2, 2): (WHITE, "N"), (6, 1): (WHITE, "W"),
        (9, 9): (BLACK, "K"), (4, 3): (BLACK, "W"), (6, 8): (BLACK, "R")})
check("6,8>6,1" in {m for m in G.legal_moves(
    mk(dict(s.board), to_move=BLACK))}, "sanity: RxW available without iron")
s1 = G.apply_move(s, "2,2>4,3")                   # knight takes the Black Warlock
check(s1.iron == (6, 1), f"iron flag not set (got {s1.iron})")
lm = G.legal_moves(s1)
check("6,8>6,1" not in lm, "capturing the iron Warlock must be illegal")
check("6,8>6,5" in lm, "unrelated rook moves must remain legal")
d = G.serialize(s1)                               # the flag round-trips
s1b = G.deserialize(d)
check(s1b.iron == (6, 1) and G.serialize(s1b) == d, "iron serialize round-trip")
check(set(G.legal_moves(s1b)) == set(lm), "round-tripped state moves differ")
s2 = G.apply_move(s1, "6,8>6,5")                  # Black plays something else
check(s2.iron is None, "iron must expire after one turn")
s3 = G.apply_move(s2, "0,0>0,1")                  # any White move
check("6,5>6,1" in G.legal_moves(s3), "Warlock must be capturable again")

# ---- 6. pawn promotion (mandatory on entering the last 3 ranks, Q/N/R/B) -----
s = mk({(0, 0): (WHITE, "K"), (9, 9): (BLACK, "K"),
        (0, 6): (WHITE, "P"), (5, 4): (WHITE, "P")})
lm = set(G.legal_moves(s))
check({f"0,6>0,7={t}" for t in "QNRB"} <= lm, "white promotion choices on rank 8")
check("0,6>0,7" not in lm, "promotion on entering the zone is mandatory")
check("5,4>5,5" in lm and "5,4>5,5=Q" not in lm, "no promotion outside the zone")
s = mk({(0, 0): (WHITE, "K"), (9, 9): (BLACK, "K"), (3, 3): (BLACK, "P")},
       to_move=BLACK)
lm = set(G.legal_moves(s))
check({f"3,3>3,2={t}" for t in "QNRB"} <= lm and "3,3>3,2" not in lm,
      "black promotion on rank 3")
sp = G.apply_move(s, "3,3>3,2=Q")
check(sp.board[(3, 2)] == (BLACK, "Q"), "promoted piece placed")

# ---- 7. castling (king slides three squares) ---------------------------------
lm = set(G.legal_moves(s0))
check("5,0>8,0" in lm and "5,0>2,0" in lm, "both castles available at move 1")
check(G.describe_move(s0, "5,0>8,0") == "O-O", "castle notation")
sc = G.apply_move(s0, "5,0>8,0")
check(sc.board.get((8, 0)) == (WHITE, "K") and sc.board.get((7, 0)) == (WHITE, "R")
      and (9, 0) not in sc.board and (5, 0) not in sc.board, "kingside castle result")
check(sc.castling == frozenset("kq"), "white rights spent")
check("4,9>7,9" in set(G.legal_moves(sc)), "black j-side castle available")

# ---- 8. checkmate via apply_move ---------------------------------------------
s = mk({(0, 0): (WHITE, "K"), (0, 8): (WHITE, "R"), (1, 0): (WHITE, "R"),
        (9, 9): (BLACK, "K")})
sm = G.apply_move(s, "1,0>1,9")                   # rook-ladder mate
check(G.is_terminal(sm), "mate position must be terminal")
check(G.returns(sm) == [1.0, -1.0], "White must win the mate")
check("wins" in G.render(sm)["caption"], "mate caption")

print("SELFTEST OK")
