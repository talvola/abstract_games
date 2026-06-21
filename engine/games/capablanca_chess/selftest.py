#!/usr/bin/env python3
"""Standalone correctness anchor for Capablanca Chess.

Run with:  PYTHONPATH=. python3 games/capablanca_chess/selftest.py

Asserts:
  * a self-computed perft regression (depths 1-3 from the opening; depth 1 = 28
    matches the widely-cited Capablanca opening move count);
  * the Archbishop (B+N) and Chancellor (R+N) compound move/attack patterns;
  * pawn promotion to the compound pieces;
  * Capablanca three-square castling target squares (both wings, both colors)
    and that castling through an attacked square is forbidden;
  * a checkmate (terminal + correct winner) and a stalemate (terminal draw).

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.

NOTE on the perft anchor: there is no single authoritative published Capablanca
perft table that this verifier could find, so the deeper node counts below are a
*self-computed* regression baseline (they pin the move generator against future
edits). The depth-1 value (28) is the well-known Capablanca opening move count.
"""

from __future__ import annotations

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.capablanca_chess.game import CapablancaChess

G = CapablancaChess()


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


def targets(state):
    """Set of destination squares 'c,r' available in legal_moves (strip promo)."""
    out = set()
    for mv in G.legal_moves(state):
        core = mv.split("=")[0]
        out.add(core.split(">")[1])
    return out


def moves_from(state, src):
    """Destination cells reachable from a given source square."""
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
# 1. Perft regression (self-computed).
# --------------------------------------------------------------------------- #
def test_perft():
    s = G.initial_state()
    expected = {1: 28, 2: 784, 3: 25228}
    for d, want in expected.items():
        got = perft(s, d)
        check(got == want, f"perft({d}) = {got}, expected {want}")
    print(f"  perft anchor OK: {expected}")


# --------------------------------------------------------------------------- #
# 2. Archbishop = Bishop + Knight, on an otherwise empty board.
# --------------------------------------------------------------------------- #
def test_archbishop():
    # Lone white Archbishop on e4 (4,3); kings tucked in corners, far away.
    board = {(4, 3): (WHITE, "A"), (0, 0): (WHITE, "K"), (9, 7): (BLACK, "K")}
    s = st(board, WHITE)
    dest = moves_from(s, "4,3")

    # Knight component: 8 leaps from (4,3).
    knight = {(5, 5), (6, 4), (6, 2), (5, 1), (3, 1), (2, 2), (2, 4), (3, 5)}
    for (c, r) in knight:
        check(f"{c},{r}" in dest, f"Archbishop missing knight move to {c},{r}")

    # Bishop component: full diagonals (board is 10 wide, 8 tall).
    bishop_samples = {(5, 4), (6, 5), (7, 6), (8, 7),   # NE
                      (3, 4), (2, 5), (1, 6), (0, 7),   # NW
                      (5, 2), (6, 1), (7, 0),           # SE
                      (3, 2), (2, 1), (1, 0)}           # SW
    for (c, r) in bishop_samples:
        check(f"{c},{r}" in dest, f"Archbishop missing bishop move to {c},{r}")

    # Must NOT move like a rook (no straight, non-knight orthogonal slide).
    for bad in ("4,4", "4,5", "5,3", "6,3", "4,2", "4,0", "0,3"):
        check(bad not in dest, f"Archbishop wrongly reaches rook square {bad}")
    print("  Archbishop (B+N) move set OK")


# --------------------------------------------------------------------------- #
# 3. Chancellor = Rook + Knight, on an otherwise empty board.
# --------------------------------------------------------------------------- #
def test_chancellor():
    board = {(4, 3): (WHITE, "C"), (0, 0): (WHITE, "K"), (9, 7): (BLACK, "K")}
    s = st(board, WHITE)
    dest = moves_from(s, "4,3")

    knight = {(5, 5), (6, 4), (6, 2), (5, 1), (3, 1), (2, 2), (2, 4), (3, 5)}
    for (c, r) in knight:
        check(f"{c},{r}" in dest, f"Chancellor missing knight move to {c},{r}")

    # Rook component along file 4 and rank 3 (the whole line, minus origin).
    rook = ({(4, r) for r in range(8) if r != 3}
            | {(c, 3) for c in range(10) if c != 4})
    for (c, r) in rook:
        check(f"{c},{r}" in dest, f"Chancellor missing rook move to {c},{r}")

    # Must NOT move like a bishop (no non-knight diagonal slide).
    for bad in ("5,4", "6,5", "3,2", "2,1", "5,2", "3,4"):
        check(bad not in dest, f"Chancellor wrongly reaches bishop square {bad}")
    print("  Chancellor (R+N) move set OK")


# --------------------------------------------------------------------------- #
# 4. Promotion to the compound pieces.
# --------------------------------------------------------------------------- #
def test_promotion():
    # White pawn on a7 (0,6) about to promote on a8 (0,7).
    board = {(0, 6): (WHITE, "P"), (0, 0): (WHITE, "K"), (9, 0): (BLACK, "K")}
    s = st(board, WHITE)
    promos = {m.split("=")[1] for m in G.legal_moves(s)
              if m.startswith("0,6>0,7=")}
    check(promos == {"Q", "R", "B", "N", "A", "C"},
          f"promotion choices = {promos}")

    # Actually promote to an Archbishop and confirm the piece lands.
    s2 = G.apply_move(s, "0,6>0,7=A")
    check(s2.board.get((0, 7)) == (WHITE, "A"), "pawn did not become Archbishop")
    print("  Promotion to Q/R/B/N/A/C OK")


# --------------------------------------------------------------------------- #
# 5. Capablanca three-square castling.
# --------------------------------------------------------------------------- #
def test_castling():
    # Clean back rank for White: K f1(5,0), R a1(0,0), R j1(9,0); black king far.
    base = {(5, 0): (WHITE, "K"), (0, 0): (WHITE, "R"), (9, 0): (WHITE, "R"),
            (5, 7): (BLACK, "K")}
    s = st(base, WHITE, castling="KQ")
    dests = moves_from(s, "5,0")
    check("8,0" in dests, "White kingside castle target i1 (8,0) missing")
    check("2,0" in dests, "White queenside castle target c1 (2,0) missing")

    # Execute kingside: king to i1, rook to h1.
    s_k = G.apply_move(s, "5,0>8,0")
    check(s_k.board.get((8, 0)) == (WHITE, "K"), "kingside king not on i1")
    check(s_k.board.get((7, 0)) == (WHITE, "R"), "kingside rook not on h1 (7,0)")
    check((9, 0) not in s_k.board, "kingside rook still on j1")

    # Execute queenside: king to c1, rook to d1.
    s_q = G.apply_move(s, "5,0>2,0")
    check(s_q.board.get((2, 0)) == (WHITE, "K"), "queenside king not on c1")
    check(s_q.board.get((3, 0)) == (WHITE, "R"), "queenside rook not on d1")
    check((0, 0) not in s_q.board, "queenside rook still on a1")

    # Black castling targets mirror (i8 = 8,7 / c8 = 2,7).
    bbase = {(5, 7): (BLACK, "K"), (0, 7): (BLACK, "R"), (9, 7): (BLACK, "R"),
             (5, 0): (WHITE, "K")}
    sb = st(bbase, BLACK, castling="kq")
    bd = moves_from(sb, "5,7")
    check("8,7" in bd and "2,7" in bd, "Black castle targets missing")

    # Cannot castle through an attacked square: a black rook on g8 attacks g1(6,0),
    # which the king crosses on the kingside path -> kingside illegal, queenside ok.
    blocked = dict(base)
    blocked[(6, 7)] = (BLACK, "R")     # rook on g-file hits g1 (6,0)
    sB = st(blocked, WHITE, castling="KQ")
    kd = moves_from(sB, "5,0")
    check("8,0" not in kd, "castling through attacked square g1 was allowed")
    check("2,0" in kd, "queenside castling wrongly blocked")
    print("  Capablanca three-square castling OK")


# --------------------------------------------------------------------------- #
# 6. Checkmate and stalemate.
# --------------------------------------------------------------------------- #
def test_checkmate():
    # Black king a8 (0,7) boxed: White queen b7 (1,6) supported by king b6 (1,5).
    # Queen covers a8/a7/b8; king covers the corner escape; mate, Black to move.
    board = {(0, 7): (BLACK, "K"), (1, 6): (WHITE, "Q"), (1, 5): (WHITE, "K")}
    s = st(board, BLACK)
    check(G.in_check(s.board, BLACK), "expected Black king in check")
    check(G.legal_moves(s) == [], "expected no legal moves (mate)")
    check(G.is_terminal(s), "checkmate position not terminal")
    ret = G.returns(s)
    check(ret == [1.0, -1.0], f"checkmate returns = {ret}, expected White win")
    print("  Checkmate OK")


def test_stalemate():
    # Black king a8 (0,7); White queen c7 (2,6) takes b8/b7/a7 but NOT a8;
    # White king far. Black to move, not in check, no moves -> stalemate draw.
    board = {(0, 7): (BLACK, "K"), (2, 6): (WHITE, "Q"), (5, 0): (WHITE, "K")}
    s = st(board, BLACK)
    check(not G.in_check(s.board, BLACK), "stalemate king should not be in check")
    check(G.legal_moves(s) == [], "expected no legal moves (stalemate)")
    check(G.is_terminal(s), "stalemate not terminal")
    check(G.returns(s) == [0.0, 0.0], "stalemate should be a draw")
    print("  Stalemate OK")


def main():
    test_perft()
    test_archbishop()
    test_chancellor()
    test_promotion()
    test_castling()
    test_checkmate()
    test_stalemate()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
