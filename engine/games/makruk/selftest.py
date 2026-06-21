#!/usr/bin/env python3
"""Correctness anchor for Makruk.

No standard published perft exists for Makruk, so the anchor is *conformance*
(random games terminate, with legal moves at every non-terminal node) plus a set
of hand-built **rule positions** that pin down the Makruk-specific movement and
win rules:

  * the Met moves exactly one square diagonally (a ferz);
  * the Khon moves to the four diagonals plus one square straight *forward*
    (colour-dependent), and not straight back/sideways;
  * a Bia promotes to a Met on reaching the sixth rank;
  * checkmate ends the game with the right result, and stalemate is a draw.

Run with:  PYTHONPATH=. python3 games/makruk/selftest.py
Prints "SELFTEST OK" and exits 0 on success; raises / exits non-zero on failure.
"""

from __future__ import annotations

import random
import sys

from agp.chesslike import CState, WHITE, BLACK
from games.makruk.game import Makruk

G = Makruk()


def st(board, to_move=WHITE):
    return CState(board=dict(board), to_move=to_move, castling=frozenset(),
                  ep=None, reps={})


def dests_from(state, frm):
    """Set of destination cells (ignoring promotion suffix) for the piece on `frm`."""
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


# --------------------------------------------------------------------------- #
# Conformance: random games terminate, always with legal moves until terminal.
# --------------------------------------------------------------------------- #
def test_conformance():
    rng = random.Random(20260620)
    for g in range(40):
        s = G.initial_state()
        plies = 0
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            check(len(ms) > 0, f"empty legal_moves at non-terminal (game {g})")
            # round-trip serialize at a few points
            if plies % 37 == 0:
                check(G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s),
                      "serialize did not round-trip")
            s = G.apply_move(s, rng.choice(ms))
            plies += 1
            check(plies <= G.PLY_CAP + 2, "exceeded ply cap (non-termination)")
        ret = G.returns(s)
        check(len(ret) == 2 and all(isinstance(x, float) for x in ret),
              "returns malformed")
        check(ret in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0]),
              f"unexpected returns {ret}")


# --------------------------------------------------------------------------- #
# Met (queen) = ferz: exactly one square diagonally.
# --------------------------------------------------------------------------- #
def test_met_is_ferz():
    # A spare Ruea for each side keeps the position out of the insufficient-
    # material draw so legal_moves is populated.
    s = st({(3, 3): (WHITE, "M"), (7, 7): (WHITE, "K"), (7, 5): (WHITE, "R"),
            (0, 0): (BLACK, "K"), (0, 5): (BLACK, "R")})
    d = dests_from(s, (3, 3))
    check(d == {(2, 2), (4, 2), (2, 4), (4, 4)},
          f"Met should reach only the 4 adjacent diagonals, got {sorted(d)}")


# --------------------------------------------------------------------------- #
# Khon (silver general): 4 diagonals + one square straight forward.
# --------------------------------------------------------------------------- #
def test_khon_white():
    s = st({(3, 3): (WHITE, "S"), (7, 7): (WHITE, "K"), (7, 5): (WHITE, "R"),
            (0, 0): (BLACK, "K"), (0, 5): (BLACK, "R")})
    d = dests_from(s, (3, 3))
    expect = {(2, 2), (4, 2), (2, 4), (4, 4),  # diagonals
              (3, 4)}                            # straight FORWARD (up for White)
    check(d == expect,
          f"White Khon dests wrong: got {sorted(d)} want {sorted(expect)}")
    # It must NOT move straight backward or sideways.
    check((3, 2) not in d and (2, 3) not in d and (4, 3) not in d,
          "Khon moved straight back/sideways")


def test_khon_black():
    s = st({(3, 3): (BLACK, "s"), (0, 0): (BLACK, "K"), (0, 5): (BLACK, "R"),
            (7, 7): (WHITE, "K"), (7, 5): (WHITE, "R")},
           to_move=BLACK)
    d = dests_from(s, (3, 3))
    expect = {(2, 2), (4, 2), (2, 4), (4, 4),  # diagonals
              (3, 2)}                            # straight FORWARD (down for Black)
    check(d == expect,
          f"Black Khon dests wrong: got {sorted(d)} want {sorted(expect)}")


# --------------------------------------------------------------------------- #
# Bia promotion to Met on the sixth rank (row 5 White / row 2 Black). No double
# step from the home (third) rank.
# --------------------------------------------------------------------------- #
def test_pawn_no_double_step():
    s = st({(0, 2): (WHITE, "P"), (7, 7): (WHITE, "K"), (0, 0): (BLACK, "K")})
    d = dests_from(s, (0, 2))
    check(d == {(0, 3)}, f"Bia should step one square only, got {sorted(d)}")


def test_pawn_promotes_to_met():
    # White Bia on row 4 stepping to row 5 must promote, and only to a Met.
    s = st({(0, 4): (WHITE, "P"), (7, 7): (WHITE, "K"), (0, 0): (BLACK, "K")})
    promos = [m for m in G.legal_moves(s) if m.startswith("0,4>0,5")]
    check(promos == ["0,4>0,5=M"],
          f"Bia must promote only to Met on 6th rank, got {promos}")
    s2 = G.apply_move(s, "0,4>0,5=M")
    check(s2.board[(0, 5)] == (WHITE, "M"), "promoted piece is not a Met")
    # Black Bia on row 3 stepping to row 2 must promote to a Met.
    sb = st({(0, 3): (BLACK, "P"), (0, 0): (BLACK, "K"), (7, 7): (WHITE, "K")},
            to_move=BLACK)
    bpromos = [m for m in G.legal_moves(sb) if m.startswith("0,3>0,2")]
    check(bpromos == ["0,3>0,2=M"],
          f"Black Bia must promote to Met on row 2, got {bpromos}")


# --------------------------------------------------------------------------- #
# Checkmate ends the game; stalemate is a draw.
# --------------------------------------------------------------------------- #
def test_checkmate():
    # Black king a8 (0,7); White rook a1 (0,0) gives check up the a-file, White
    # rook b-file (1,?) covers the b-file escape. Construct a back-rank mate.
    # Black Khun on (0,7); White Ruea on (0,0) checks along file a; White Ruea on
    # (1,1) controls file b (squares (1,6),(1,7)). White Khun far away.
    board = {
        (0, 7): (BLACK, "K"),
        (0, 0): (WHITE, "R"),   # checks the king along the a-file
        (1, 1): (WHITE, "R"),   # covers b7,b8 escape squares
        (7, 0): (WHITE, "K"),
    }
    s = st(board, to_move=BLACK)
    check(G.in_check(s.board, BLACK), "expected Black to be in check")
    check(G.legal_moves(s) == [], "expected no legal moves (checkmate)")
    check(G.is_terminal(s), "checkmate position should be terminal")
    check(G.returns(s) == [1.0, -1.0], f"White should win the mate, got {G.returns(s)}")


def test_stalemate_is_draw():
    # Black Khun on a8 (0,7), not in check, but every move is illegal.
    # White Ruea on g7 (6,6) controls rank 8 except a8 area? Build a clean one:
    # Black king a8; White king c7 (2,6) controls b8,b7,a7; White Met on (1,5)?
    # Simpler: king a8, White Ruea b1 controls file b (b7,b8); White Ruea h7
    # controls rank 7 (a7) ... that would also be along rank giving the king a7
    # blocked. King a8 escapes: a7 (covered by rook on rank7), b8 (file b), b7
    # (file b & rank7). Not in check. -> stalemate.
    board = {
        (0, 7): (BLACK, "K"),
        (1, 0): (WHITE, "R"),   # file b -> covers b7 (1,6) and b8 (1,7)
        (7, 6): (WHITE, "R"),   # rank 7 -> covers a7 (0,6)
        (7, 0): (WHITE, "K"),
    }
    s = st(board, to_move=BLACK)
    check(not G.in_check(s.board, BLACK), "stalemate position must NOT be in check")
    check(G.legal_moves(s) == [], "expected no legal moves (stalemate)")
    check(G.is_terminal(s), "stalemate position should be terminal")
    check(G.returns(s) == [0.0, 0.0], f"stalemate must be a draw, got {G.returns(s)}")


def main():
    test_conformance()
    test_met_is_ferz()
    test_khon_white()
    test_khon_black()
    test_pawn_no_double_step()
    test_pawn_promotes_to_met()
    test_checkmate()
    test_stalemate_is_draw()
    print("SELFTEST OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"SELFTEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
