#!/usr/bin/env python3
"""Standalone correctness anchor for Modern Chess (Ajedrez Moderno).

Run with:  PYTHONPATH=. python3 games/modern_chess/selftest.py

Asserts:
  * the hand-derived opening legal-move count (24) and a self-computed perft
    regression (depths 1-3) that pins the move generator against future edits;
  * the opening setup (piece counts + exact back-rank squares);
  * the Prime Minister (M = bishop + knight) move/attack pattern from a
    constructed position, and that it is NOT a rook;
  * pawn promotion choices (Q/R/B/N/M) and that promotion lands the piece;
  * Modern Chess two-square castling targets (both wings, both colours), the
    rook's destination, and that castling through an attacked square is forbidden;
  * a serialize / deserialize round-trip;
  * a checkmate (terminal + correct winner) and a stalemate (terminal draw).

Pure stdlib (imports only ``agp`` + this game). Prints "SELFTEST OK" / exits 0 on
success; raises / exits nonzero on failure.

NOTE on the perft anchor: there is no published Modern Chess perft table to check
against, so the node counts below are a *self-computed* regression baseline. The
depth-1 value (24) is hand-derived: 9 pawns x 2 single/double steps = 18; the two
knights give 2 moves each = 4; the Prime Minister (knight component only, bishops
blocked) gives 2; everything else on the back rank is blocked by its own pawns.
18 + 4 + 2 = 24.
"""

from __future__ import annotations

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.modern_chess.game import ModernChess, BACK_RANK

G = ModernChess()


def perft(state, depth):
    if depth == 0:
        return 1
    total = 0
    for mv in G.legal_moves(state):
        total += perft(G.apply_move(state, mv), depth - 1)
    return total


def st(board, to_move=WHITE, castling="", ep=None):
    rights = frozenset(castling)
    return CState(board=dict(board), to_move=to_move, castling=rights, ep=ep,
                  reps={G._poskey(board, to_move, rights, ep): 1})


def moves_from(state, src):
    out = set()
    for mv in G.legal_moves(state):
        core = mv.split("=")[0]
        f, t = core.split(">")
        if f == src:
            out.add(t)
    return out


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# --------------------------------------------------------------------------- #
# 1. Opening count + perft regression.
# --------------------------------------------------------------------------- #
def test_perft():
    s = G.initial_state()
    n = len(G.legal_moves(s))
    check(n == 24, f"opening legal-move count = {n}, expected 24")
    expected = {1: 24, 2: 576, 3: 15832}
    for d, want in expected.items():
        got = perft(s, d)
        check(got == want, f"perft({d}) = {got}, expected {want}")
    print(f"  opening count + perft anchor OK: {expected}")


# --------------------------------------------------------------------------- #
# 2. Setup: counts + exact back-rank squares.
# --------------------------------------------------------------------------- #
def test_setup():
    s = G.initial_state()
    b = s.board
    check(len(b) == 36, f"opening board has {len(b)} pieces, expected 36")
    # Back rank a..i for both colours.
    check(BACK_RANK == ["R", "N", "B", "M", "K", "Q", "B", "N", "R"],
          f"BACK_RANK wrong: {BACK_RANK}")
    for c in range(9):
        check(b[(c, 0)] == (WHITE, BACK_RANK[c]), f"white back rank wrong at file {c}")
        check(b[(c, 8)] == (BLACK, BACK_RANK[c]), f"black back rank wrong at file {c}")
        check(b[(c, 1)] == (WHITE, "P"), f"white pawn missing at file {c}")
        check(b[(c, 7)] == (BLACK, "P"), f"black pawn missing at file {c}")
    # King centre (e=4), Queen right (f=5), Minister left (d=3).
    check(b[(4, 0)] == (WHITE, "K"), "white king not on e1")
    check(b[(5, 0)] == (WHITE, "Q"), "white queen not on f1")
    check(b[(3, 0)] == (WHITE, "M"), "white prime minister not on d1")
    # Exactly one Prime Minister and nine pawns per side.
    for pl in (WHITE, BLACK):
        ms = [sq for sq, (p, t) in b.items() if p == pl and t == "M"]
        ps = [sq for sq, (p, t) in b.items() if p == pl and t == "P"]
        check(len(ms) == 1, f"player {pl} has {len(ms)} Ministers, expected 1")
        check(len(ps) == 9, f"player {pl} has {len(ps)} pawns, expected 9")
    print("  Setup (counts + back-rank squares) OK")


# --------------------------------------------------------------------------- #
# 3. Prime Minister = Bishop + Knight, on an otherwise empty board.
# --------------------------------------------------------------------------- #
def test_minister():
    # Lone white Prime Minister on e5 (4,4); kings in far corners.
    board = {(4, 4): (WHITE, "M"), (0, 0): (WHITE, "K"), (8, 8): (BLACK, "K")}
    s = st(board, WHITE)
    dest = moves_from(s, "4,4")

    # Knight component: 8 leaps from (4,4) (all on the 9x9 board).
    knight = {(5, 6), (6, 5), (6, 3), (5, 2), (3, 2), (2, 3), (2, 5), (3, 6)}
    for (c, r) in knight:
        check(f"{c},{r}" in dest, f"Minister missing knight move to {c},{r}")

    # Bishop component: diagonals on the 9x9 board. (8,8) holds the black king
    # and (0,0) the white king, so they are excluded from the sample.
    bishop_samples = {(5, 5), (6, 6), (7, 7),           # NE (stops before (8,8))
                      (3, 5), (2, 6), (1, 7), (0, 8),   # NW
                      (5, 3), (6, 2), (7, 1), (8, 0),   # SE
                      (3, 3), (2, 2), (1, 1)}           # SW (stops before (0,0))
    for (c, r) in bishop_samples:
        check(f"{c},{r}" in dest, f"Minister missing bishop move to {c},{r}")

    # Must NOT move like a rook (straight, non-knight orthogonal slide).
    for bad in ("4,5", "4,6", "5,4", "6,4", "4,3", "4,0", "0,4", "8,4"):
        check(bad not in dest, f"Minister wrongly reaches rook square {bad}")
    print("  Prime Minister (B+N) move set OK")


# --------------------------------------------------------------------------- #
# 4. Promotion choices.
# --------------------------------------------------------------------------- #
def test_promotion():
    # White pawn on a8 (0,7) about to promote on a9 (0,8).
    board = {(0, 7): (WHITE, "P"), (0, 0): (WHITE, "K"), (8, 0): (BLACK, "K")}
    s = st(board, WHITE)
    promos = {m.split("=")[1] for m in G.legal_moves(s)
              if m.startswith("0,7>0,8=")}
    check(promos == {"Q", "R", "B", "N", "M"}, f"promotion choices = {promos}")
    s2 = G.apply_move(s, "0,7>0,8=M")
    check(s2.board.get((0, 8)) == (WHITE, "M"), "pawn did not become Prime Minister")
    print("  Promotion to Q/R/B/N/M OK")


# --------------------------------------------------------------------------- #
# 5. Two-square castling.
# --------------------------------------------------------------------------- #
def test_castling():
    # Clean back rank for White: K e1(4,0), R a1(0,0), R i1(8,0); black king far.
    base = {(4, 0): (WHITE, "K"), (0, 0): (WHITE, "R"), (8, 0): (WHITE, "R"),
            (4, 8): (BLACK, "K")}
    s = st(base, WHITE, castling="KQ")
    dests = moves_from(s, "4,0")
    check("6,0" in dests, "White ministerside castle target g1 (6,0) missing")
    check("2,0" in dests, "White queenside castle target c1 (2,0) missing")

    # Execute ministerside: king e1->g1, rook i1->h1.
    s_k = G.apply_move(s, "4,0>6,0")
    check(s_k.board.get((6, 0)) == (WHITE, "K"), "ministerside king not on g1")
    check(s_k.board.get((7, 0)) == (WHITE, "R"), "ministerside rook not on h1 (7,0)")
    check((8, 0) not in s_k.board, "ministerside rook still on i1")

    # Execute queenside: king e1->c1, rook a1->d1.
    s_q = G.apply_move(s, "4,0>2,0")
    check(s_q.board.get((2, 0)) == (WHITE, "K"), "queenside king not on c1")
    check(s_q.board.get((3, 0)) == (WHITE, "R"), "queenside rook not on d1")
    check((0, 0) not in s_q.board, "queenside rook still on a1")

    # Black castling targets mirror (g9 = 6,8 / c9 = 2,8).
    bbase = {(4, 8): (BLACK, "K"), (0, 8): (BLACK, "R"), (8, 8): (BLACK, "R"),
             (4, 0): (WHITE, "K")}
    sb = st(bbase, BLACK, castling="kq")
    bd = moves_from(sb, "4,8")
    check("6,8" in bd and "2,8" in bd, "Black castle targets missing")

    # Cannot castle through an attacked square: a black rook on f9 attacks f1
    # (5,0), which the king crosses ministerside -> ministerside illegal,
    # queenside ok.
    blocked = dict(base)
    blocked[(5, 8)] = (BLACK, "R")     # rook on f-file hits f1 (5,0)
    sB = st(blocked, WHITE, castling="KQ")
    kd = moves_from(sB, "4,0")
    check("6,0" not in kd, "castling through attacked square f1 was allowed")
    check("2,0" in kd, "queenside castling wrongly blocked")
    print("  Modern two-square castling OK")


# --------------------------------------------------------------------------- #
# 6. Serialize round-trip.
# --------------------------------------------------------------------------- #
def test_serialize():
    s = G.initial_state()
    s = G.apply_move(s, "4,1>4,3")   # a double pawn push to populate ep
    d = G.serialize(s)
    s2 = G.deserialize(d)
    check(s2.board == s.board, "board did not round-trip")
    check(s2.to_move == s.to_move, "to_move did not round-trip")
    check(s2.castling == s.castling, "castling did not round-trip")
    check(s2.ep == s.ep, "ep did not round-trip")
    check(G.serialize(s2) == d, "re-serialize mismatch")
    print("  Serialize round-trip OK")


# --------------------------------------------------------------------------- #
# 7. Checkmate and stalemate.
# --------------------------------------------------------------------------- #
def test_checkmate():
    # Black king a9 (0,8) boxed: White queen b8 (1,7) supported by king b7 (1,6).
    board = {(0, 8): (BLACK, "K"), (1, 7): (WHITE, "Q"), (1, 6): (WHITE, "K")}
    s = st(board, BLACK)
    check(G.in_check(s.board, BLACK), "expected Black king in check")
    check(G.legal_moves(s) == [], "expected no legal moves (mate)")
    check(G.is_terminal(s), "checkmate position not terminal")
    ret = G.returns(s)
    check(ret == [1.0, -1.0], f"checkmate returns = {ret}, expected White win")
    print("  Checkmate OK")


def test_stalemate():
    # Black king a9 (0,8); White queen c8 (2,7) covers b9/b8/a8 but NOT a9;
    # White king far. Black to move, not in check, no moves -> stalemate draw.
    board = {(0, 8): (BLACK, "K"), (2, 7): (WHITE, "Q"), (4, 0): (WHITE, "K")}
    s = st(board, BLACK)
    check(not G.in_check(s.board, BLACK), "stalemate king should not be in check")
    check(G.legal_moves(s) == [], "expected no legal moves (stalemate)")
    check(G.is_terminal(s), "stalemate not terminal")
    check(G.returns(s) == [0.0, 0.0], "stalemate should be a draw")
    print("  Stalemate OK")


def main():
    test_perft()
    test_setup()
    test_minister()
    test_promotion()
    test_castling()
    test_serialize()
    test_checkmate()
    test_stalemate()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
