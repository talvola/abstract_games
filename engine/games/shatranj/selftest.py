#!/usr/bin/env python3
"""Standalone correctness anchor for the Shatranj package.

Run from the engine root:  PYTHONPATH=. python3 games/shatranj/selftest.py

There is no standard published perft for Shatranj, so the anchor is:

  (1) the engine's own conformance harness (random self-play honouring the Game
      contract -- it must report OK / the runs QUEUE through without error), and
  (2) a set of rule-specific positions that pin down what makes Shatranj
      Shatranj: the Firzan's one-square diagonal move, the Alfil's two-square
      diagonal LEAP (jumping an intervening piece), no castling, no pawn double
      step, promotion to Firzan only, stalemate counting as a WIN, and winning by
      BARING the enemy king (capturing its last non-king piece) -- including the
      "bares back -> draw" exception.

Prints "SELFTEST OK" and exits 0 on success; raises / exits non-zero on failure.
"""

from __future__ import annotations

import json
import sys

from agp.chesslike import CState, WHITE, BLACK
from agp.conformance import check
from games.shatranj.game import Shatranj

G = Shatranj()


def cs(pieces, to_move=WHITE, ply=0):
    """Build a CState from {"c,r": (player, letter)}."""
    board = {}
    for k, (pl, t) in pieces.items():
        c, r = (int(x) for x in k.split(","))
        board[(c, r)] = (pl, t)
    return CState(board=board, to_move=to_move, castling=frozenset(), ep=None,
                  reps={}, ply=ply)


def moves_from(state, frm):
    """Set of destination 'c,r' strings for legal moves originating at frm."""
    out = set()
    for m in G.legal_moves(state):
        base = m.split("=")[0]
        f, t = base.split(">")
        if f == frm:
            out.add(t)
    return out


def expect(cond, msg):
    if not cond:
        raise AssertionError("FAILED: " + msg)
    print("  ok:", msg)


# --------------------------------------------------------------------------- #
# (1) Conformance harness
# --------------------------------------------------------------------------- #
def test_conformance():
    print("[conformance]")
    manifest = json.load(open("games/shatranj/manifest.json"))
    rep = check(G, manifest, games=60, seed=7)
    print(rep.summary())
    expect(rep.ok, "conformance harness reports OK (random self-play, QUEUE)")
    expect(rep.games_played >= 1, "at least one full random game terminated")


# --------------------------------------------------------------------------- #
# (2a) Firzan: exactly one square diagonally, nothing more.
# --------------------------------------------------------------------------- #
def test_firzan():
    print("[firzan]")
    # Spare pieces (h-pawns) keep both sides off the bare-king rule.
    st = cs({"4,4": (WHITE, "F"), "4,0": (WHITE, "K"), "4,7": (BLACK, "K"),
             "7,1": (WHITE, "P"), "7,6": (BLACK, "P")})
    dests = moves_from(st, "4,4")
    expect(dests == {"5,5", "5,3", "3,5", "3,3"},
           "Firzan moves exactly one square diagonally (4 squares)")
    expect("4,5" not in dests and "5,4" not in dests,
           "Firzan does NOT move orthogonally")
    expect("6,6" not in dests, "Firzan does NOT move two squares diagonally")


# --------------------------------------------------------------------------- #
# (2b) Alfil: leaps exactly two squares diagonally, jumping any piece between.
# --------------------------------------------------------------------------- #
def test_alfil_leaps():
    print("[alfil]")
    # Friendly pawns on all four adjacent diagonals -> the Alfil must JUMP them.
    st = cs({
        "4,4": (WHITE, "A"),
        "5,5": (WHITE, "P"), "3,3": (WHITE, "P"),
        "5,3": (WHITE, "P"), "3,5": (WHITE, "P"),
        "4,0": (WHITE, "K"), "4,7": (BLACK, "K"),
        "7,6": (BLACK, "P"),
    })
    dests = moves_from(st, "4,4")
    expect(dests == {"6,6", "2,2", "6,2", "2,6"},
           "Alfil leaps to the four squares two diagonals away, over the blockers")
    expect("5,5" not in dests, "Alfil does NOT stop one square diagonally")

    # The leap ignores an ENEMY blocker too, and may capture on the landing square.
    st2 = cs({
        "4,4": (WHITE, "A"),
        "5,5": (BLACK, "P"),       # enemy in the way -- ignored (leaper)
        "6,6": (BLACK, "P"),       # enemy on the landing square -- capturable
        "4,0": (WHITE, "K"), "4,7": (BLACK, "K"),
    })
    d2 = moves_from(st2, "4,4")
    expect("6,6" in d2, "Alfil captures on its landing square, leaping the piece between")


# --------------------------------------------------------------------------- #
# (2c) No castling, no pawn double step, promotion to Firzan only.
# --------------------------------------------------------------------------- #
def test_no_castling():
    print("[no-castling]")
    st = cs({"4,0": (WHITE, "K"), "7,0": (WHITE, "R"), "0,0": (WHITE, "R"),
             "4,7": (BLACK, "K"), "7,6": (BLACK, "P")})
    kd = moves_from(st, "4,0")
    expect("6,0" not in kd and "2,0" not in kd,
           "Shah has no two-square castling move")


def test_pawn():
    print("[pawn]")
    st = cs({"3,1": (WHITE, "P"), "4,0": (WHITE, "K"), "4,7": (BLACK, "K"),
             "7,6": (BLACK, "P")})
    pd = moves_from(st, "3,1")
    expect(pd == {"3,2"}, "Baidaq on its home rank steps one square only (no double step)")

    # Promotion to a Firzan only.
    st2 = cs({"3,6": (WHITE, "P"), "0,0": (WHITE, "K"), "7,7": (BLACK, "K"),
              "0,5": (BLACK, "P")})
    promos = {m for m in G.legal_moves(st2) if m.startswith("3,6>3,7")}
    expect(promos == {"3,6>3,7=F"},
           "Baidaq promotes only to a Firzan (=F) on the last rank")


# --------------------------------------------------------------------------- #
# (2d) Stalemate is a WIN for the side that produced it.
# --------------------------------------------------------------------------- #
def test_stalemate_is_win():
    print("[stalemate=win]")
    # Black to move, Black king on a8 (0,7), not in check, but with no legal move.
    # White Rook on b-file (1,6) covers b7/b8; White Rook on g7 (6,6) covers a7.
    # A Black pawn on h4 (7,3) is blocked by a White pawn on h3 (7,2) and has no
    # capture, so Black is genuinely stalemated (not just bared).
    st = cs({"0,7": (BLACK, "K"), "1,6": (WHITE, "R"), "6,6": (WHITE, "R"),
             "4,0": (WHITE, "K"), "7,3": (BLACK, "P"), "7,2": (WHITE, "P")},
            to_move=BLACK)
    expect(not G._lone_king(st.board, BLACK), "Black still has a piece (not bared)")
    expect(G.legal_moves(st) == [], "Black (to move) has no legal move")
    expect(not G.in_check(st.board, BLACK), "Black king is NOT in check -> stalemate")
    expect(G.is_terminal(st), "stalemate position is terminal")
    expect(G.returns(st) == [1.0, -1.0],
           "stalemate is a WIN for White (the stalemating side), not a draw")


def test_checkmate():
    print("[checkmate]")
    # Back-rank mate: Black king a8 (0,7) checked along the a-file by a rook on
    # a1 (0,0); the b-file rook on b1 (1,0) covers the b7/b8 escape squares; a7
    # is covered by the checking rook.  A blocked Black h-pawn keeps Black off the
    # bare-king rule.
    st = cs({"0,7": (BLACK, "K"), "0,0": (WHITE, "R"), "1,0": (WHITE, "R"),
             "4,4": (WHITE, "K"), "7,3": (BLACK, "P"), "7,2": (WHITE, "P")},
            to_move=BLACK)
    expect(not G._lone_king(st.board, BLACK), "Black still has a piece (not bared)")
    expect(G.in_check(st.board, BLACK), "Black king is in check")
    expect(G.legal_moves(st) == [], "Black has no legal move -> checkmate")
    expect(G.returns(st) == [1.0, -1.0], "checkmate is a win for White")


# --------------------------------------------------------------------------- #
# (2e) Baring the enemy king -- the anchor's headline rule.
# --------------------------------------------------------------------------- #
def test_bare_king():
    print("[bare-king]")
    # White rook on c7 (2,6) can capture Black's lone remaining piece, a Firzan on
    # c8 (2,7), leaving Black with only their king -> White wins by baring.
    st = cs({"2,6": (WHITE, "R"), "2,7": (BLACK, "F"),
             "4,0": (WHITE, "K"), "7,7": (BLACK, "K")}, to_move=WHITE)
    expect(not G.is_terminal(st), "position before the baring capture is not terminal")
    capture = "2,6>2,7"
    expect(capture in G.legal_moves(st), "the baring rook capture is legal")
    after = G.apply_move(st, capture)
    expect(G._lone_king(after.board, BLACK), "after the capture Black has a lone king")
    expect(G.is_terminal(after), "baring the enemy king ends the game")
    expect(G.returns(after) == [1.0, -1.0],
           "White wins by baring the Black king (captured its last non-king piece)")


def test_bare_back_is_draw():
    print("[bare-back=draw]")
    # White has just bared Black (Black: lone king). It is Black to move, and
    # Black's king can immediately capture White's last non-king piece (a rook
    # adjacent to the Black king), baring White in return -> DRAW.
    st = cs({"0,7": (BLACK, "K"), "1,7": (WHITE, "R"), "4,0": (WHITE, "K")},
            to_move=BLACK)
    expect(G._lone_king(st.board, BLACK), "Black has a lone king (just bared)")
    expect(G._can_bare_back(st, BLACK),
           "Black king can capture White's last piece, baring White in reply")
    expect(G.is_terminal(st), "the bared-but-can-bare-back position is terminal")
    expect(G.returns(st) == [0.0, 0.0],
           "baring is a DRAW when the bared side can bare back next move")

    # Double bare (both lone kings) is a draw.
    st2 = cs({"0,7": (BLACK, "K"), "4,0": (WHITE, "K")}, to_move=BLACK)
    expect(G.is_terminal(st2) and G.returns(st2) == [0.0, 0.0],
           "two lone kings is a draw")


def main():
    test_conformance()
    test_firzan()
    test_alfil_leaps()
    test_no_castling()
    test_pawn()
    test_stalemate_is_win()
    test_checkmate()
    test_bare_king()
    test_bare_back_is_draw()
    print("SELFTEST OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print("SELFTEST FAILED:", e, file=sys.stderr)
        sys.exit(1)
