#!/usr/bin/env python3
"""Correctness anchor for Almost Chess (Ralph Betza).

Almost Chess is standard chess with the queen replaced by a Chancellor "M"
(Rook + Knight, no diagonals). The anchors are:

  * an opening perft (d1..d4) FROZEN from this engine's own move generator
    (engine-derived, not a published table) -- a regression guard;
  * the setup: a Chancellor on d1/d8 and NO queen anywhere;
  * the Chancellor moves exactly as Rook UNION Knight (rook rays + knight jumps,
    and crucially NO bishop diagonals);
  * a constructed back-rank checkmate (standard check/mate still works);
  * the promotion set offers the Chancellor + R/B/N;
  * serialize round-trips.

NOTE on the opening perft: unlike chess (d1 = 20), Almost Chess has d1 = 22,
because the Chancellor on d1 keeps its KNIGHT component even while its rook lines
are blocked by the pawns -- it leaps to c3 and e3 from the start.

Run with:  PYTHONPATH=. python3 games/almost_chess/selftest.py
Prints "SELFTEST OK" and exits 0 on success; raises / exits non-zero on failure.
"""

from __future__ import annotations

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.almost_chess.game import AlmostChess

G = AlmostChess()

# Opening perft, engine-derived and frozen (see module docstring).
PERFT = {1: 22, 2: 484, 3: 11895, 4: 290522}


def st(board, to_move=WHITE, castling=frozenset(), ep=None):
    return CState(board=dict(board), to_move=to_move, castling=castling,
                  ep=ep, reps={})


def dests_from(state, frm):
    """Destination cells (promotion suffix stripped) for the piece on `frm`."""
    fc, fr = frm
    out = set()
    for m in G.legal_moves(state):
        base = m.split("=")[0]
        a, b = base.split(">")
        if a == f"{fc},{fr}":
            c, r = b.split(",")
            out.add((int(c), int(r)))
    return out


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def perft(s, d):
    if d == 0:
        return 1
    ms = G.legal_moves(s)
    if d == 1:
        return len(ms)
    return sum(perft(G.apply_move(s, m), d - 1) for m in ms)


# --------------------------------------------------------------------------- #
def test_perft():
    s = G.initial_state()
    for d, want in PERFT.items():
        got = perft(s, d)
        check(got == want, f"perft(d{d}) = {got}, expected {want}")


def test_setup():
    s = G.initial_state()
    b = s.board
    # Chancellor on d1 / d8 (file index 3); no queen anywhere on the board.
    check(b[(3, 0)] == (WHITE, "M"), f"White Chancellor not on d1: {b.get((3, 0))}")
    check(b[(3, 7)] == (BLACK, "M"), f"Black Chancellor not on d8: {b.get((3, 7))}")
    check(all(t != "Q" for (_, (_, t)) in b.items()), "a Queen is present (should be none)")
    # Back rank otherwise standard.
    check(b[(0, 0)] == (WHITE, "R") and b[(4, 0)] == (WHITE, "K"),
          "White back rank corrupted")


def test_chancellor_is_rook_plus_knight():
    # Lone Chancellor on a central open square (e5 -> 4,4), with kings far apart.
    s = st({(4, 4): (WHITE, "M"), (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K")})
    d = dests_from(s, (4, 4))
    rook = {(c, 4) for c in range(8) if c != 4} | {(4, r) for r in range(8) if r != 4}
    knight = {(4 + dc, 4 + dr) for dc, dr in
              [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]}
    expect = rook | knight
    check(d == expect,
          f"Chancellor dests wrong.\n got={sorted(d)}\n want={sorted(expect)}")
    # Explicitly: NO bishop diagonal squares.
    diagonals = {(4 + k, 4 + k) for k in range(-4, 4) if k} | \
                {(4 + k, 4 - k) for k in range(-4, 4) if k}
    diagonals = {(c, r) for (c, r) in diagonals if 0 <= c < 8 and 0 <= r < 8}
    check(d.isdisjoint(diagonals),
          f"Chancellor reached diagonal squares (should not): {sorted(d & diagonals)}")
    check(len(d) == 22, f"open-square Chancellor should reach 22 squares, got {len(d)}")


def test_checkmate():
    # Back-rank mate: Black king a8 (0,7); White rook a1 (0,0) checks the a-file;
    # White rook b1 (1,0) covers b7/b8 escapes; White king tucked away.
    board = {
        (0, 7): (BLACK, "K"),
        (0, 0): (WHITE, "R"),
        (1, 0): (WHITE, "R"),
        (7, 0): (WHITE, "K"),
    }
    s = st(board, to_move=BLACK)
    check(G.in_check(s.board, BLACK), "expected Black to be in check")
    check(G.legal_moves(s) == [], "expected no legal moves (checkmate)")
    check(G.is_terminal(s), "checkmate position should be terminal")
    check(G.returns(s) == [1.0, -1.0], f"White should win the mate, got {G.returns(s)}")


def test_stalemate_is_draw():
    # Black king a8; White rook b-file covers b7/b8; White rook rank-7 covers a7.
    board = {
        (0, 7): (BLACK, "K"),
        (1, 0): (WHITE, "R"),
        (7, 6): (WHITE, "R"),
        (7, 0): (WHITE, "K"),
    }
    s = st(board, to_move=BLACK)
    check(not G.in_check(s.board, BLACK), "stalemate position must NOT be in check")
    check(G.legal_moves(s) == [], "expected no legal moves (stalemate)")
    check(G.is_terminal(s), "stalemate position should be terminal")
    check(G.returns(s) == [0.0, 0.0], f"stalemate must be a draw, got {G.returns(s)}")


def test_promotion_set():
    # White pawn on a7 (0,6) about to promote on a8: offers M/R/B/N (no Q).
    s = st({(0, 6): (WHITE, "P"), (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")})
    promos = sorted(m.split("=")[1] for m in G.legal_moves(s) if m.startswith("0,6>0,7="))
    check(promos == ["B", "M", "N", "R"],
          f"promotion set should be M/R/B/N, got {promos}")
    s2 = G.apply_move(s, "0,6>0,7=M")
    check(s2.board[(0, 7)] == (WHITE, "M"), "promoting to M did not yield a Chancellor")


def test_serialize_roundtrip():
    s = G.initial_state()
    check(G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s),
          "serialize did not round-trip on the initial position")
    # And after a few moves.
    for m in ["3,1>3,3", "4,6>4,4", "3,0>4,2"]:   # incl. a Chancellor knight-leap
        s = G.apply_move(s, m)
    check(G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s),
          "serialize did not round-trip after moves")


def main():
    test_perft()
    test_setup()
    test_chancellor_is_rook_plus_knight()
    test_checkmate()
    test_stalemate_is_draw()
    test_promotion_set()
    test_serialize_roundtrip()
    print("SELFTEST OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"SELFTEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
