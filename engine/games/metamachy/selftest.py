"""Metamachy selftest -- pure stdlib, anchors the port against the rules at
https://www.chessvariants.com/rules/metamachy (H.G. Muller & J.-L. Cazaux) and
http://history.chess.free.fr/metamachy.htm.

Anchors:
  1. perft(1)=61 from the start position, hand-verified piece by piece
     (P24 N6 B4 R0 Q3 E2 A4 C0 L8 G3 M4 K3); perft(2)=3721 (= 61^2 -- the
     armies cannot interact within one move each on a 12x12 board);
     perft(3)=233126 was additionally frozen at build time (too slow to run
     here).
  2. Exact move-target sets for the non-standard pieces: Eagle (bent rider,
     blocked at the bend / mid-slide), Cannon (screen mechanics + cannon
     check), Lion (leaps over blockers), Elephant, Camel, Prince.
  3. King's one-time 16-direction jump: over occupied squares, never onto an
     occupied square, forbidden while in check, forbidden over a threatened
     square (knight jump needs only ONE of its two intermediates safe), and
     gone after the king moves.
  4. Pawn/Prince double push from ANY square + en passant anywhere (pawn takes
     prince e.p.; prince may NOT take e.p.).
  5. Mandatory promotion of Pawn AND Prince to Q/G/L only.
  6. Checkmate reached via apply_move (and the in-check-forbids-jump rule
     keeping it mate).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agp.chesslike import CState, WHITE, BLACK  # noqa: E402
from games.metamachy.game import Metamachy      # noqa: E402

G = Metamachy()


def st(board, to_move=WHITE, castling="", ep=None):
    return CState(board=dict(board), to_move=to_move,
                  castling=frozenset(castling), ep=ep)


def dests(state, frm):
    """Destination cells of all legal moves from square ``frm``."""
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


# ---- 1. perft from the initial position ------------------------------------
s0 = G.initial_state()
assert perft(s0, 1) == 61, "perft(1) != 61"
assert perft(s0, 2) == 3721, "perft(2) != 3721"

# start-position sanity: 30 pieces per side, kings g1/g12, queen f1, lion f2,
# eagle g2, both king-jump rights present
assert sum(1 for (pl, _) in s0.board.values() if pl == WHITE) == 30
assert sum(1 for (pl, _) in s0.board.values() if pl == BLACK) == 30
assert s0.board[(6, 0)] == (WHITE, "K") and s0.board[(6, 11)] == (BLACK, "K")
assert s0.board[(5, 0)] == (WHITE, "Q") and s0.board[(5, 1)] == (WHITE, "L")
assert s0.board[(6, 1)] == (WHITE, "G")
assert s0.castling == frozenset("WB")

# ---- 2a. Eagle: bend + outward slide, blocking ------------------------------
# White G c3 (2,2). Bends: (3,3) own pawn -> dead; (1,1) enemy pawn -> capture
# at the bend only; (3,1) empty -> slide right (blocked by black R at (5,1),
# capturable) and down; (1,3) empty -> slide up (blocked by own N at (1,6))
# and left.
b = {(2, 2): (WHITE, "G"), (3, 3): (WHITE, "P"), (1, 1): (BLACK, "P"),
     (5, 1): (BLACK, "R"), (1, 6): (WHITE, "N"),
     (11, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
exp = {(1, 1),                       # capture at the bend, no slide beyond
       (3, 1), (4, 1), (5, 1), (3, 0),
       (1, 3), (1, 4), (1, 5), (0, 3)}
assert dests(st(b), (2, 2)) == exp, "eagle geometry wrong"
# and no slide past an occupied bend:
assert (4, 4) not in dests(st(b), (2, 2)) and (0, 0) not in dests(st(b), (2, 2))

# ---- 2b. Cannon: rider without capture, hop capture over one screen ---------
b = {(0, 0): (WHITE, "C"), (0, 3): (WHITE, "P"), (0, 7): (BLACK, "R"),
     (3, 0): (BLACK, "P"), (4, 0): (BLACK, "N"),
     (11, 1): (WHITE, "K"), (11, 11): (BLACK, "K")}
exp = {(0, 1), (0, 2),               # slide up to the screen
       (0, 7),                       # hop capture over own-pawn screen
       (1, 0), (2, 0),               # slide right to the screen
       (4, 0)}                       # hop capture over enemy-pawn screen
assert dests(st(b), (0, 0)) == exp, "cannon geometry wrong"
# cannon check detection: exactly one screen between cannon and king
b = {(0, 0): (WHITE, "C"), (0, 3): (WHITE, "P"), (0, 5): (BLACK, "K"),
     (11, 0): (WHITE, "K")}
assert G.in_check(b, BLACK), "cannon check missed"
b[(0, 4)] = (BLACK, "P")             # second screen breaks the attack
assert not G.in_check(b, BLACK), "cannon attack through two screens"

# ---- 2c. Lion: leaps to all 24 squares within 2 king steps ------------------
b = {(5, 5): (WHITE, "L"), (11, 0): (WHITE, "K"), (11, 11): (BLACK, "K"),
     (7, 7): (BLACK, "P")}
for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
    b[(5 + dc, 5 + dr)] = (WHITE, "P")   # own pieces fill the whole inner ring
ring2 = {(5 + dc, 5 + dr) for dc in (-2, -1, 0, 1, 2) for dr in (-2, -1, 0, 1, 2)
         if max(abs(dc), abs(dr)) == 2}
assert dests(st(b), (5, 5)) == ring2, "lion must leap over blockers to ring 2"

# ---- 2d. Elephant (ferz + alfil leap) and Camel ((1,3) leaper) ---------------
b = {(5, 5): (WHITE, "E"), (6, 6): (WHITE, "P"), (4, 4): (BLACK, "P"),
     (7, 7): (BLACK, "N"),           # alfil leap OVER own pawn at (6,6)
     (11, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
exp = {(4, 4),                       # ferz capture
       (6, 4), (4, 6),               # ferz steps
       (7, 7), (3, 3), (7, 3), (3, 7)}   # alfil leaps (over (6,6) too)
assert dests(st(b), (5, 5)) == exp, "elephant geometry wrong"
b = {(5, 5): (WHITE, "A"), (0, 11): (BLACK, "R"),   # rook so material suffices
     (11, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
exp = {(6, 8), (4, 8), (6, 2), (4, 2), (8, 6), (8, 4), (2, 6), (2, 4)}
assert dests(st(b), (5, 5)) == exp, "camel geometry wrong"
# lone-camel (colourbound leaper) endings are declared dead draws
assert G._insufficient({(5, 5): (WHITE, "A"), (11, 0): (WHITE, "K"),
                        (11, 11): (BLACK, "K")})

# ---- 3. King's one-time jump -------------------------------------------------
# (a) open board: all 9 on-board 2-away squares + 5 normal steps
# (the white rook at (0,5) is padding so material is not "insufficient")
b = {(6, 0): (WHITE, "K"), (11, 11): (BLACK, "K"), (0, 5): (WHITE, "R")}
d = dests(st(b, castling="WB"), (6, 0))
jumps = {(4, 0), (8, 0), (6, 2), (4, 2), (8, 2), (5, 2), (7, 2), (4, 1), (8, 1)}
assert jumps <= d, "open-board king jumps missing"
# (b) without the right, no jumps
d = dests(st(b, castling="B"), (6, 0))
assert not (jumps & d), "king jumped without the right"
# (c) jump OVER an occupied square is fine; onto an occupied square is not
b2 = dict(b)
b2[(5, 0)] = (WHITE, "Q")
d = dests(st(b2, castling="WB"), (6, 0))
assert (4, 0) in d, "king must be able to jump over a piece"
b2[(4, 0)] = (WHITE, "R")
d = dests(st(b2, castling="WB"), (6, 0))
assert (4, 0) not in d, "king jump is non-capturing / needs an empty square"
# (d) threatened intermediate: black R on (7,11) sweeps file 7 -> the D jump
# (8,0) (mid (7,0)), A jump (8,2) (mid (7,1)) and N jump (8,1) (mids (7,0)+(7,1))
# are all forbidden; the left-side jumps stay legal.
b2 = dict(b)
b2[(7, 11)] = (BLACK, "R")
d = dests(st(b2, castling="WB"), (6, 0))
assert (8, 0) not in d and (8, 2) not in d and (8, 1) not in d, \
    "jump over a threatened square allowed"
assert (4, 0) in d and (4, 2) in d and (4, 1) in d and (6, 2) in d
# (e) knight jump with only ONE of its two intermediates threatened is LEGAL:
# black B at (3,4) attacks (6,1) but not (7,1) -> jump (6,0)->(7,2) allowed,
# while the D jump (6,0)->(6,2) (sole mid (6,1)) is forbidden.
b2 = dict(b)
b2[(3, 4)] = (BLACK, "B")
d = dests(st(b2, castling="WB"), (6, 0))
assert (7, 2) in d, "knight jump must need only one safe intermediate"
assert (6, 2) not in d, "jump over the bishop-threatened square allowed"
# (f) no jumping out of check
b2 = dict(b)
b2[(6, 11)] = (BLACK, "R")           # checks the king down file 6
d = dests(st(b2, castling="WB"), (6, 0))
assert not (jumps & d), "king jumped out of check"
# (g) the right disappears the moment the king moves
s = st(b, castling="WB")
s2 = G.apply_move(s, "6,0>6,1")
assert "W" not in s2.castling and "B" in s2.castling

# ---- 4. double pushes + en passant anywhere ----------------------------------
# pawn double push from a NON-home square, then e.p. capture of it
b = {(2, 5): (WHITE, "P"), (3, 7): (BLACK, "P"),
     (11, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
s = st(b)
assert "2,5>2,7" in G.legal_moves(s), "pawn double push must work anywhere"
s2 = G.apply_move(s, "2,5>2,7")
assert s2.ep == ((2, 6), (2, 7))
assert "3,7>2,6" in G.legal_moves(s2), "e.p. capture missing"
s3 = G.apply_move(s2, "3,7>2,6")
assert (2, 7) not in s3.board and s3.board[(2, 6)] == (BLACK, "P")
# prince double push + PAWN captures the prince e.p.
b = {(4, 4): (WHITE, "M"), (3, 6): (BLACK, "P"),
     (11, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
s = st(b)
assert "4,4>4,6" in G.legal_moves(s), "prince double push missing"
s2 = G.apply_move(s, "4,4>4,6")
assert s2.ep == ((4, 5), (4, 6))
assert "3,6>4,5" in G.legal_moves(s2), "e.p. capture of the prince missing"
s3 = G.apply_move(s2, "3,6>4,5")               # e.p. capture
assert (4, 6) not in s3.board, "prince not removed by e.p. capture"
assert s3.board[(4, 5)] == (BLACK, "P")
# prince double push is blocked by an occupied passed square, and never captures
b = {(4, 4): (WHITE, "M"), (4, 5): (BLACK, "P"),
     (11, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
assert "4,4>4,6" not in G.legal_moves(st(b)), "prince double push jumped"
b = {(4, 4): (WHITE, "M"), (4, 6): (BLACK, "P"),
     (11, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
assert "4,4>4,6" not in G.legal_moves(st(b)), "prince double push captured"
# a PRINCE may NOT capture e.p.: after a white pawn double push, the black
# prince stepping onto the passed square does NOT remove the pawn
b = {(4, 4): (WHITE, "P"), (5, 6): (BLACK, "M"),
     (11, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
s2 = G.apply_move(st(b), "4,4>4,6")
s3 = G.apply_move(s2, "5,6>4,5")               # prince onto the e.p. square
assert s3.board.get((4, 6)) == (WHITE, "P"), "prince captured en passant"

# ---- 5. promotion: pawn AND prince, to Q/G/L only, mandatory ------------------
b = {(3, 10): (WHITE, "P"), (7, 10): (WHITE, "M"),
     (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
ms = G.legal_moves(st(b))
assert {"3,10>3,11=Q", "3,10>3,11=G", "3,10>3,11=L"} <= set(ms)
assert "3,10>3,11" not in ms and "3,10>3,11=R" not in ms
assert {"7,10>7,11=Q", "7,10>7,11=G", "7,10>7,11=L"} <= set(ms)
assert "7,10>7,11" not in ms, "prince promotion must be mandatory"
s2 = G.apply_move(st(b), "7,10>7,11=L")
assert s2.board[(7, 11)] == (WHITE, "L")
# a pawn double push onto the last rank also promotes
b = {(3, 9): (WHITE, "P"), (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
ms = G.legal_moves(st(b))
assert "3,9>3,11=Q" in ms and "3,9>3,11" not in ms

# ---- 6. checkmate via apply_move (jump may not save a checked king) -----------
b = {(5, 11): (BLACK, "K"), (0, 10): (WHITE, "R"), (1, 5): (WHITE, "R"),
     (11, 0): (WHITE, "K")}
s = st(b, to_move=WHITE, castling="B")         # black still holds its jump right
s2 = G.apply_move(s, "1,5>1,11")
assert G.in_check(s2.board, BLACK)
assert G.legal_moves(s2) == [], "king escaped (jump out of check?)"
assert G.is_terminal(s2)
assert G.returns(s2) == [1.0, -1.0], "white checkmate not scored"
# same position but WITHOUT the back-rank rook cut-off is not mate
b2 = dict(b)
del b2[(0, 10)]
s2 = G.apply_move(st(b2, to_move=WHITE, castling="B"), "1,5>1,11")
assert not G.is_terminal(s2)

# ---- serialize round-trip with ep + jump rights --------------------------------
b = {(4, 4): (WHITE, "M"), (3, 7): (BLACK, "P"),
     (6, 0): (WHITE, "K"), (11, 11): (BLACK, "K")}
s2 = G.apply_move(st(b, castling="WB"), "4,4>4,6")
s3 = G.deserialize(G.serialize(s2))
assert s3.ep == s2.ep and s3.castling == s2.castling and s3.board == s2.board
assert sorted(G.legal_moves(s3)) == sorted(G.legal_moves(s2))

print("metamachy selftest: all checks passed")
