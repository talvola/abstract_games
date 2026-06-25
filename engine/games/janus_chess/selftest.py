#!/usr/bin/env python3
"""Standalone correctness anchor for Janus Chess.

Run with:  PYTHONPATH=. python3 games/janus_chess/selftest.py

Asserts:
  * the opening legal-move count (hand-derived 28) and a self-computed perft
    regression (depths 1-3 from the opening);
  * the exact 10x8 starting array (R J N B K Q B N J R, King e / Queen f, two
    Januses on b/i, ten pawns);
  * the Janus (B+N) compound move pattern from a constructed position;
  * pawn promotion to Q/R/B/N/J;
  * Janus asymmetric castling target squares (king e->b queenside, e->i kingside;
    both colours) and that castling through an attacked square is forbidden;
  * serialize / deserialize round-trip;
  * a checkmate (terminal + correct winner) and a stalemate (terminal draw).

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.

NOTE on the perft anchor: no published Janus perft table was found, so the
deeper node counts are a *self-computed* regression baseline pinning the move
generator against future edits. The depth-1 value (28) is hand-derived below.
"""

from __future__ import annotations

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.janus_chess.game import JanusChess, BACK_RANK

G = JanusChess()


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
# 1. Setup: exact array, dimensions, counts.
# --------------------------------------------------------------------------- #
def test_setup():
    check((G.WIDTH, G.HEIGHT) == (10, 8), "board must be 10x8")
    check(BACK_RANK == ["R", "J", "N", "B", "K", "Q", "B", "N", "J", "R"],
          f"back rank wrong: {BACK_RANK}")
    s = G.initial_state()
    b = s.board
    # King on e (4,0), Queen on f (5,0); mirrored for Black.
    check(b[(4, 0)] == (WHITE, "K"), "White King not on e1 (4,0)")
    check(b[(5, 0)] == (WHITE, "Q"), "White Queen not on f1 (5,0)")
    check(b[(4, 7)] == (BLACK, "K"), "Black King not on e8 (4,7)")
    check(b[(5, 7)] == (BLACK, "Q"), "Black Queen not on f8 (5,7)")
    # Two Januses per side on b (1) and i (8).
    for col in (1, 8):
        check(b[(col, 0)] == (WHITE, "J"), f"White Janus missing on file {col}")
        check(b[(col, 7)] == (BLACK, "J"), f"Black Janus missing on file {col}")
    # Counts: 2 Januses, 10 pawns, 2 rooks, 2 knights, 2 bishops, 1 K, 1 Q each.
    for pl, prank, brank in ((WHITE, 1, 0), (BLACK, 6, 7)):
        cnt = {}
        for (c, r), (p, t) in b.items():
            if p == pl:
                cnt[t] = cnt.get(t, 0) + 1
        check(cnt == {"P": 10, "R": 2, "N": 2, "B": 2, "J": 2, "K": 1, "Q": 1},
              f"piece counts for player {pl}: {cnt}")
    print("  Setup (R J N B K Q B N J R, K=e, Q=f, 2 Januses, 10 pawns) OK")


# --------------------------------------------------------------------------- #
# 2. Opening count (hand-derived) + perft regression.
# --------------------------------------------------------------------------- #
def test_perft():
    s = G.initial_state()
    # Hand-derived opening: 10 pawns x 2 = 20; the two knights (c1,h1) have 2 legal
    # moves each (b3/d3, g3/f3) = 4; each Janus (b1,i1) has 2 knight jumps onto the
    # 3rd rank = 4. 20+4+4 = 28. Bishops/rooks/queen/king all blocked at the start.
    check(len(G.legal_moves(s)) == 28, "opening legal-move count must be 28")
    expected = {1: 28, 2: 782, 3: 24747}
    for d, want in expected.items():
        got = perft(s, d)
        check(got == want, f"perft({d}) = {got}, expected {want}")
    print(f"  Opening count 28 + perft anchor OK: {expected}")


# --------------------------------------------------------------------------- #
# 3. Janus = Bishop + Knight (and NOT a rook).
# --------------------------------------------------------------------------- #
def test_janus_move():
    # Lone white Janus on e4 (4,3); kings tucked in corners, far away.
    board = {(4, 3): (WHITE, "J"), (0, 0): (WHITE, "K"), (9, 7): (BLACK, "K")}
    s = st(board, WHITE)
    dest = moves_from(s, "4,3")

    # Knight component: 8 leaps from (4,3).
    knight = {(5, 5), (6, 4), (6, 2), (5, 1), (3, 1), (2, 2), (2, 4), (3, 5)}
    for (c, r) in knight:
        check(f"{c},{r}" in dest, f"Janus missing knight move to {c},{r}")

    # Bishop component: full diagonals (board is 10 wide, 8 tall).
    bishop = {(5, 4), (6, 5), (7, 6), (8, 7),    # NE
              (3, 4), (2, 5), (1, 6), (0, 7),    # NW
              (5, 2), (6, 1), (7, 0),            # SE
              (3, 2), (2, 1), (1, 0)}            # SW
    for (c, r) in bishop:
        check(f"{c},{r}" in dest, f"Janus missing bishop move to {c},{r}")

    # The Janus is Bishop UNION Knight, nothing more, nothing less.
    expected = {f"{c},{r}" for (c, r) in (knight | bishop)}
    check(dest == expected, f"Janus reaches unexpected squares: {dest - expected}")

    # Must NOT move like a rook (no straight, non-knight orthogonal slide).
    for bad in ("4,4", "4,5", "5,3", "6,3", "4,2", "4,0", "0,3"):
        check(bad not in dest, f"Janus wrongly reaches rook square {bad}")
    print("  Janus (B union N) move set OK")


# --------------------------------------------------------------------------- #
# 4. Promotion to Q/R/B/N/J.
# --------------------------------------------------------------------------- #
def test_promotion():
    # White pawn on a7 (0,6) about to promote on a8 (0,7).
    board = {(0, 6): (WHITE, "P"), (0, 0): (WHITE, "K"), (9, 0): (BLACK, "K")}
    s = st(board, WHITE)
    promos = {m.split("=")[1] for m in G.legal_moves(s)
              if m.startswith("0,6>0,7=")}
    check(promos == {"Q", "R", "B", "N", "J"}, f"promotion choices = {promos}")

    s2 = G.apply_move(s, "0,6>0,7=J")
    check(s2.board.get((0, 7)) == (WHITE, "J"), "pawn did not become a Janus")
    print("  Promotion to Q/R/B/N/J OK")


# --------------------------------------------------------------------------- #
# 5. Janus asymmetric castling.
# --------------------------------------------------------------------------- #
def test_castling():
    # Clean back rank for White: K e1(4,0), R a1(0,0), R j1(9,0); black king far.
    base = {(4, 0): (WHITE, "K"), (0, 0): (WHITE, "R"), (9, 0): (WHITE, "R"),
            (4, 7): (BLACK, "K")}
    s = st(base, WHITE, castling="KQ")
    dests = moves_from(s, "4,0")
    check("8,0" in dests, "White kingside castle target i1 (8,0) missing")
    check("1,0" in dests, "White queenside castle target b1 (1,0) missing")

    # Execute kingside: king e1->i1, rook j1->h1.
    s_k = G.apply_move(s, "4,0>8,0")
    check(s_k.board.get((8, 0)) == (WHITE, "K"), "kingside king not on i1 (8,0)")
    check(s_k.board.get((7, 0)) == (WHITE, "R"), "kingside rook not on h1 (7,0)")
    check((9, 0) not in s_k.board, "kingside rook still on j1")
    check((4, 0) not in s_k.board, "king still on e1 after kingside castle")

    # Execute queenside: king e1->b1, rook a1->c1.
    s_q = G.apply_move(s, "4,0>1,0")
    check(s_q.board.get((1, 0)) == (WHITE, "K"), "queenside king not on b1 (1,0)")
    check(s_q.board.get((2, 0)) == (WHITE, "R"), "queenside rook not on c1 (2,0)")
    check((0, 0) not in s_q.board, "queenside rook still on a1")

    # Notation: kingside = O-O, queenside = O-O-O.
    check(G.describe_move(s, "4,0>8,0") == "O-O", "kingside should describe as O-O")
    check(G.describe_move(s, "4,0>1,0") == "O-O-O",
          "queenside should describe as O-O-O")

    # Black castling targets mirror (i8 = 8,7 / b8 = 1,7).
    bbase = {(4, 7): (BLACK, "K"), (0, 7): (BLACK, "R"), (9, 7): (BLACK, "R"),
             (4, 0): (WHITE, "K")}
    sb = st(bbase, BLACK, castling="kq")
    bd = moves_from(sb, "4,7")
    check("8,7" in bd and "1,7" in bd, f"Black castle targets missing: {bd}")
    s_bk = G.apply_move(sb, "4,7>8,7")
    check(s_bk.board.get((8, 7)) == (BLACK, "K"), "black kingside king not on i8")
    check(s_bk.board.get((7, 7)) == (BLACK, "R"), "black kingside rook not on h8")

    # Cannot castle through an attacked square: a black rook on g8 attacks g1(6,0),
    # which the king crosses on the kingside path -> kingside illegal; queenside ok.
    blocked = dict(base)
    blocked[(6, 7)] = (BLACK, "R")     # rook on g-file hits g1 (6,0)
    sB = st(blocked, WHITE, castling="KQ")
    kd = moves_from(sB, "4,0")
    check("8,0" not in kd, "castling through attacked square g1 was allowed")
    check("1,0" in kd, "queenside castling wrongly blocked")

    # And the king may not land in check: black rook on the b-file forbids
    # queenside (king lands on b1).
    blocked2 = dict(base)
    blocked2[(1, 7)] = (BLACK, "R")    # rook on b-file attacks b1 (1,0)
    sB2 = st(blocked2, WHITE, castling="KQ")
    kd2 = moves_from(sB2, "4,0")
    check("1,0" not in kd2, "castling into check on b1 was allowed")
    print("  Janus asymmetric castling (e->b / e->i) OK")


# --------------------------------------------------------------------------- #
# 6. Serialize round-trip.
# --------------------------------------------------------------------------- #
def test_serialize():
    s = G.initial_state()
    s = G.apply_move(s, "0,1>0,3")     # a-pawn double step (sets ep)
    d = G.serialize(s)
    s2 = G.deserialize(d)
    check(s2.board == s.board, "board did not round-trip")
    check(s2.to_move == s.to_move, "to_move did not round-trip")
    check(s2.castling == s.castling, "castling did not round-trip")
    check(s2.ep == s.ep, "ep did not round-trip")
    check(G._poskey_state(s2) == G._poskey_state(s), "poskey mismatch after round-trip")
    print("  Serialize round-trip OK")


# --------------------------------------------------------------------------- #
# 7. Checkmate and stalemate.
# --------------------------------------------------------------------------- #
def test_checkmate():
    # Black king a8 (0,7) boxed: White queen b7 (1,6) supported by king b6 (1,5).
    board = {(0, 7): (BLACK, "K"), (1, 6): (WHITE, "Q"), (1, 5): (WHITE, "K")}
    s = st(board, BLACK)
    check(G.in_check(s.board, BLACK), "expected Black king in check")
    check(G.legal_moves(s) == [], "expected no legal moves (mate)")
    check(G.is_terminal(s), "checkmate position not terminal")
    check(G.returns(s) == [1.0, -1.0], "checkmate should be a White win")
    print("  Checkmate OK")


def test_stalemate():
    # Black king a8 (0,7); White queen c7 (2,6) covers b8/b7/a7 but NOT a8.
    board = {(0, 7): (BLACK, "K"), (2, 6): (WHITE, "Q"), (4, 0): (WHITE, "K")}
    s = st(board, BLACK)
    check(not G.in_check(s.board, BLACK), "stalemate king should not be in check")
    check(G.legal_moves(s) == [], "expected no legal moves (stalemate)")
    check(G.is_terminal(s), "stalemate not terminal")
    check(G.returns(s) == [0.0, 0.0], "stalemate should be a draw")
    print("  Stalemate OK")


def main():
    test_setup()
    test_perft()
    test_janus_move()
    test_promotion()
    test_castling()
    test_serialize()
    test_checkmate()
    test_stalemate()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
