"""Zanzibar-XL selftest -- pure stdlib, anchors the port against the rules at
https://ftp.chessvariants.com/rules/zanzibar-xl (Cazaux; incl. H.G. Muller's
Interactive Diagram with the exact Betza moves and default array).

Anchors:
  1. The opening arrangement (setup) phase: Black places its eight chiefs one at a
     time; illegal placements are rejected; the mirror is applied automatically
     and White then moves.  Serialize round-trips mid-placement.
  2. perft(1)=48 from a canonical arrangement, hand-verified piece by piece
     (P24 A4 Z2 E2 N4 W2 M2 L1 D1 F6); perft(2)=2304 (= 48^2 -- the armies cannot
     interact within one move each on a 12x12 board).
  3. Exact move-target sets for every non-standard piece: Eagle, Rhinoceros,
     Lion, Elephant, Camel, Giraffe, Buffalo, Machine, Duchess, Cannon, Archer,
     Sorceress and Prince (each hand-verified).
  4. The King's one-time 16-direction jump (over occupied squares, never onto one,
     forbidden while in check, forbidden over a threatened square with the
     knight-jump one-safe-intermediate rule, gone after the king moves).
  5. Pawn / Prince double push from ANY square + en passant (pawn takes prince
     e.p.; prince may NOT take e.p.) and mandatory promotion of both to a chief
     (Q/G/L/D/O/U/F) only.
  6. Checkmate reached via apply_move.
  7. Serialize round-trips mid-game (with e.p.) and mid-placement.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agp.chesslike import CState, WHITE, BLACK        # noqa: E402
from games.zanzibar_xl.game import ZanzibarXL          # noqa: E402

G = ZanzibarXL()


def st(board, to_move=WHITE, castling="", ep=None):
    s = CState(board=dict(board), to_move=to_move, castling=frozenset(castling),
               ep=ep, hands={})
    s.reps = {}
    return s


def dests(state, frm):
    out = set()
    for m in G.legal_moves(state):
        raw = m.split("=")[0]
        f, t = raw.split(">")
        if tuple(int(x) for x in f.split(",")) == frm:
            out.add(tuple(int(x) for x in t.split(",")))
    return out


def perft(state, d):
    if d == 0:
        return 1
    return sum(perft(G.apply_move(state, m), d - 1) for m in G.legal_moves(state))


# Kings parked in opposite corners, plus a harmless enemy filler, so lone-leaper
# geometry tests are never scored "insufficient" and no king is in check.
KINGS = {(11, 0): (WHITE, "K"), (0, 11): (BLACK, "K")}
FILL = {(1, 10): (BLACK, "N")}


def geo(pieces, frm):
    b = dict(pieces)
    b.update(KINGS)
    b.update(FILL)
    return dests(st(b), frm)


# --- 1. setup (arrangement) phase --------------------------------------------
s0 = G.initial_state()
assert s0.to_move == BLACK, "Black arranges first"
assert G._in_setup(s0)
assert len(s0.board) == 64, "16 pawns + 20 paired pieces per side = 64 fixed"
assert s0.hands[BLACK] == {"K": 1, "Q": 1, "G": 1, "L": 1,
                           "D": 1, "O": 1, "U": 1, "F": 1}
assert not G.is_terminal(s0)

# Only drop moves are offered, and only onto the correct group of squares.
setup_moves = set(G.legal_moves(s0))
assert "K@5,11" in setup_moves and "K@6,10" in setup_moves        # King -> centre
assert "K@4,11" not in setup_moves, "King may not go on a flank square"
assert "D@4,11" in setup_moves and "D@7,10" in setup_moves        # Duchess -> flank
assert "D@5,11" not in setup_moves, "Duchess may not go on a centre square"
assert "0,0>0,1" not in setup_moves, "no board moves during arrangement"

# Canonical arrangement (mirrors Metamachy's default: Q f, K g, Lion f, Eagle g).
PLACE = ["Q@5,11", "K@6,11", "L@5,10", "G@6,10",
         "D@4,11", "O@7,11", "U@4,10", "F@7,10"]
s = s0
for i, m in enumerate(PLACE):
    assert m in G.legal_moves(s), f"placement {m} not offered"
    # cannot place onto an already-filled chief square
    if i > 0:
        prev = PLACE[i - 1].split("@")[1]
        assert not any(mv.endswith("@" + prev) for mv in G.legal_moves(s)), \
            "placed square still offered"
    s = G.apply_move(s, m)
    if i < 7:
        assert s.to_move == BLACK, "Black keeps arranging until all 8 are placed"

# After the 8th placement: mirror applied, White to move, no reserve left.
assert not G._in_setup(s) and s.to_move == WHITE
assert len(s.board) == 80, "40 pieces per side after the mirror"
assert sum(1 for pl, _ in s.board.values() if pl == WHITE) == 40
assert sum(1 for pl, _ in s.board.values() if pl == BLACK) == 40
# mirror correctness: Black chief on (c,r) -> White chief of the SAME type on (c,11-r)
for (c, r), (pl, t) in list(s.board.items()):
    if pl == BLACK and (c, r) in G.CHIEF_SQUARES:
        assert s.board.get((c, 11 - r)) == (WHITE, t), f"mirror wrong for {t} at {(c, r)}"
assert s.board[(6, 11)] == (BLACK, "K") and s.board[(6, 0)] == (WHITE, "K")
assert s.board[(4, 11)] == (BLACK, "D") and s.board[(4, 0)] == (WHITE, "D")
assert s.castling == frozenset("WB"), "both kings still hold the jump right"

# --- 2. perft (frozen) -------------------------------------------------------
assert perft(s, 1) == 48, "perft(1) != 48"
assert perft(s, 2) == 2304, "perft(2) != 48^2"

# --- 3. exact geometry of every non-standard piece ---------------------------
assert geo({(2, 2): (WHITE, "G"), (3, 3): (WHITE, "P"), (1, 1): (BLACK, "P"),
            (5, 1): (BLACK, "R"), (1, 6): (WHITE, "N")}, (2, 2)) == {
    (1, 1), (3, 1), (3, 0), (4, 1), (5, 1), (1, 3), (0, 3), (1, 4), (1, 5)}, "Eagle"

assert geo({(2, 2): (WHITE, "U"), (2, 3): (WHITE, "P"), (2, 1): (BLACK, "P"),
            (4, 4): (BLACK, "R")}, (2, 2)) == {
    (3, 2), (4, 3), (5, 4), (6, 5), (7, 6), (8, 7), (9, 8), (10, 9), (11, 10),
    (4, 1), (5, 0), (1, 2), (0, 3), (0, 1), (2, 1)}, "Rhinoceros"

lb = {(5, 5): (WHITE, "L")}
for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
    lb[(5 + dc, 5 + dr)] = (WHITE, "P")            # inner ring blocked
assert geo(lb, (5, 5)) == {(5 + dc, 5 + dr) for dc in (-2, -1, 0, 1, 2)
                           for dr in (-2, -1, 0, 1, 2) if max(abs(dc), abs(dr)) == 2}, "Lion"

assert geo({(5, 5): (WHITE, "E"), (6, 6): (WHITE, "P"), (4, 4): (BLACK, "P"),
            (7, 7): (BLACK, "N")}, (5, 5)) == {
    (4, 4), (6, 4), (4, 6), (7, 7), (3, 3), (7, 3), (3, 7)}, "Elephant"

assert geo({(5, 5): (WHITE, "A")}, (5, 5)) == {
    (2, 4), (2, 6), (4, 2), (4, 8), (6, 2), (6, 8), (8, 4), (8, 6)}, "Camel"

assert geo({(5, 5): (WHITE, "Z")}, (5, 5)) == {
    (2, 3), (2, 7), (3, 2), (3, 8), (7, 2), (7, 8), (8, 3), (8, 7)}, "Giraffe"

assert geo({(5, 5): (WHITE, "F")}, (5, 5)) == {
    (2, 3), (2, 4), (2, 6), (2, 7), (3, 2), (3, 4), (3, 6), (3, 8), (4, 2), (4, 3),
    (4, 7), (4, 8), (6, 2), (6, 3), (6, 7), (6, 8), (7, 2), (7, 4), (7, 6), (7, 8),
    (8, 3), (8, 4), (8, 6), (8, 7)}, "Buffalo"

assert geo({(5, 5): (WHITE, "W"), (6, 5): (WHITE, "P"), (5, 6): (BLACK, "P")},
           (5, 5)) == {(4, 5), (5, 6), (5, 4), (7, 5), (3, 5), (5, 7), (5, 3)}, "Machine"

# Duchess: leaps 1/2/3 along the 8 queen rays; own P at (7,5) blocks landing on
# dist-2 (7,5) but the dist-3 (8,5) is still reachable by LEAPING over it.
assert geo({(5, 5): (WHITE, "D"), (7, 5): (WHITE, "P"), (5, 8): (BLACK, "P")},
           (5, 5)) == {
    (6, 5), (8, 5), (4, 5), (3, 5), (2, 5), (5, 6), (5, 7), (5, 8), (5, 4), (5, 3),
    (5, 2), (6, 6), (7, 7), (8, 8), (4, 6), (3, 7), (2, 8), (6, 4), (7, 3), (8, 2),
    (4, 4), (3, 3), (2, 2)}, "Duchess"
assert (7, 5) not in geo({(5, 5): (WHITE, "D"), (7, 5): (WHITE, "P")}, (5, 5))

assert geo({(0, 0): (WHITE, "C"), (0, 3): (WHITE, "P"), (0, 7): (BLACK, "R"),
            (3, 0): (BLACK, "P"), (4, 0): (BLACK, "N")}, (0, 0)) == {
    (0, 1), (0, 2), (0, 7), (1, 0), (2, 0), (4, 0)}, "Cannon"

assert geo({(0, 0): (WHITE, "V"), (2, 2): (WHITE, "P"), (5, 5): (BLACK, "R")},
           (0, 0)) == {(1, 1), (5, 5)}, "Archer"

assert geo({(2, 2): (WHITE, "O"), (2, 5): (WHITE, "P"), (2, 8): (BLACK, "R"),
            (5, 2): (WHITE, "P"), (8, 2): (BLACK, "N"), (4, 4): (WHITE, "P"),
            (6, 6): (BLACK, "B")}, (2, 2)) == {
    (2, 3), (2, 4), (2, 8), (2, 1), (2, 0), (3, 2), (4, 2), (8, 2), (1, 2), (0, 2),
    (3, 3), (6, 6), (1, 3), (0, 4), (3, 1), (4, 0), (1, 1), (0, 0)}, "Sorceress"

assert geo({(4, 4): (WHITE, "M"), (5, 5): (BLACK, "P")}, (4, 4)) == {
    (3, 3), (3, 4), (3, 5), (4, 3), (4, 5), (5, 3), (5, 4), (5, 5), (4, 6)}, "Prince"

# --- 4. King's one-time jump -------------------------------------------------
kb = {(6, 0): (WHITE, "K"), (11, 11): (BLACK, "K"), (0, 5): (WHITE, "R")}
d = dests(st(kb, castling="WB"), (6, 0))
jumps = {(4, 0), (8, 0), (6, 2), (4, 2), (8, 2), (5, 2), (7, 2), (4, 1), (8, 1)}
assert jumps <= d, "open-board king jumps missing"
assert not (jumps & dests(st(kb, castling="B"), (6, 0))), "jumped without the right"
# jump OVER an occupied square is fine; ONTO an occupied square is not
kb2 = dict(kb); kb2[(5, 0)] = (WHITE, "Q")
assert (4, 0) in dests(st(kb2, castling="WB"), (6, 0)), "must jump over a piece"
kb2[(4, 0)] = (WHITE, "R")
assert (4, 0) not in dests(st(kb2, castling="WB"), (6, 0)), "jump is non-capturing"
# threatened intermediate: a black rook down file 7 forbids the right-side jumps
kb2 = dict(kb); kb2[(7, 11)] = (BLACK, "R")
d = dests(st(kb2, castling="WB"), (6, 0))
assert (8, 0) not in d and (8, 2) not in d and (8, 1) not in d, "jumped over a threat"
assert {(4, 0), (4, 2), (4, 1), (6, 2)} <= d
# knight jump with only ONE of its two intermediates threatened is LEGAL
kb2 = dict(kb); kb2[(3, 4)] = (BLACK, "B")     # attacks (6,1) but not (7,1)
d = dests(st(kb2, castling="WB"), (6, 0))
assert (7, 2) in d and (6, 2) not in d, "knight-jump one-safe-intermediate rule"
# no jumping out of check
kb2 = dict(kb); kb2[(6, 11)] = (BLACK, "R")
assert not (jumps & dests(st(kb2, castling="WB"), (6, 0))), "jumped out of check"
# the right disappears once the king moves
s2 = G.apply_move(st(kb, castling="WB"), "6,0>6,1")
assert "W" not in s2.castling and "B" in s2.castling

# --- 5. double pushes, en passant, promotion ---------------------------------
b = {(2, 5): (WHITE, "P"), (3, 7): (BLACK, "P"), (11, 0): (WHITE, "K"),
     (11, 11): (BLACK, "K")}
s2 = G.apply_move(st(b), "2,5>2,7")            # pawn double push from a non-home square
assert s2.ep == ((2, 6), (2, 7))
s3 = G.apply_move(s2, "3,7>2,6")              # e.p. capture
assert (2, 7) not in s3.board and s3.board[(2, 6)] == (BLACK, "P")
# prince double push + a PAWN captures the prince e.p.
b = {(4, 4): (WHITE, "M"), (3, 6): (BLACK, "P"), (11, 0): (WHITE, "K"),
     (11, 11): (BLACK, "K")}
s2 = G.apply_move(st(b), "4,4>4,6")
assert s2.ep == ((4, 5), (4, 6))
s3 = G.apply_move(s2, "3,6>4,5")
assert (4, 6) not in s3.board and s3.board[(4, 5)] == (BLACK, "P")
# a PRINCE may NOT capture e.p.
b = {(4, 4): (WHITE, "P"), (5, 6): (BLACK, "M"), (11, 0): (WHITE, "K"),
     (11, 11): (BLACK, "K")}
s2 = G.apply_move(st(b), "4,4>4,6")
s3 = G.apply_move(s2, "5,6>4,5")
assert s3.board.get((4, 6)) == (WHITE, "P"), "prince captured e.p."
# mandatory promotion of pawn AND prince to a chief (Q/G/L/D/O/U/F) only
b = {(3, 10): (WHITE, "P"), (7, 10): (WHITE, "M"), (0, 0): (WHITE, "K"),
     (11, 11): (BLACK, "K")}
ms = set(G.legal_moves(st(b)))
for ch in ("Q", "G", "L", "D", "O", "U", "F"):
    assert f"3,10>3,11={ch}" in ms and f"7,10>7,11={ch}" in ms, f"promo to {ch} missing"
assert "3,10>3,11" not in ms and "3,10>3,11=R" not in ms and "3,10>3,11=N" not in ms
assert "7,10>7,11" not in ms, "prince promotion must be mandatory"
s2 = G.apply_move(st(b), "7,10>7,11=F")
assert s2.board[(7, 11)] == (WHITE, "F")

# --- 6. checkmate via apply_move ---------------------------------------------
b = {(5, 11): (BLACK, "K"), (0, 10): (WHITE, "R"), (1, 5): (WHITE, "R"),
     (11, 0): (WHITE, "K")}
s2 = G.apply_move(st(b, to_move=WHITE, castling="B"), "1,5>1,11")
assert G.in_check(s2.board, BLACK)
assert G.legal_moves(s2) == [], "king escaped (jump out of check?)"
assert G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0], "white checkmate not scored"
# without the back-rank cut-off it is not mate
b2 = dict(b); del b2[(0, 10)]
assert not G.is_terminal(G.apply_move(st(b2, to_move=WHITE, castling="B"), "1,5>1,11"))

# --- 7. serialize round-trips ------------------------------------------------
# mid-game (with e.p. + jump rights)
b = {(4, 4): (WHITE, "M"), (3, 7): (BLACK, "P"), (6, 0): (WHITE, "K"),
     (11, 11): (BLACK, "K")}
s2 = G.apply_move(st(b, castling="WB"), "4,4>4,6")
s3 = G.deserialize(G.serialize(s2))
assert s3.ep == s2.ep and s3.castling == s2.castling and s3.board == s2.board
assert sorted(G.legal_moves(s3)) == sorted(G.legal_moves(s2))
# mid-placement (reserve + Black to move)
mid = G.apply_move(G.apply_move(s0, "Q@5,11"), "K@6,11")
md = G.deserialize(G.serialize(mid))
assert md.board == mid.board and md.hands == mid.hands and md.to_move == mid.to_move
assert sorted(G.legal_moves(md)) == sorted(G.legal_moves(mid))

print("zanzibar_xl selftest: all checks passed")
