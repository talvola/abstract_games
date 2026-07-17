#!/usr/bin/env python3
"""Standalone correctness anchor for the Chaturanga package.

Run from the engine root:  PYTHONPATH=. python3 games/chaturanga/selftest.py

There is no published perft for Chaturanga, so the anchor is:

  (1) a frozen perft from the initial position -- 16 / 256 / 4176 at depths
      1..3 (depth 4 = 68122, computed once, too slow for the suite).  These
      numbers EQUAL our shatranj package's perft at the same depths, which is
      exactly what the rules predict: the two games share every piece movement
      (rook, knight, alfil, ferz, king, single-step pawn), and Chaturanga's
      only array difference -- Black's Raja/Mantri swapped to d8/e8 -- is a
      left-right MIRROR of Shatranj's Black array, under which every piece's
      move count is invariant;

  (2) a differential against the shatranj package (loaded via agp.loader):
      random playouts from the Chaturanga opening, asserting the FULL legal-
      move sets of the two games are identical position-by-position (movement
      and promotion are shared; only terminal rules differ, and short playouts
      stay clear of them);

  (3) rule positions for everything that DIFFERS from Shatranj: the crossed
      setup (Rajas e1/d8), stalemate as a WIN for the STALEMATED player
      (opposite of Shatranj), and baring as an OUTRIGHT win with no
      "bare-back -> draw" exception (contrasted against Shatranj's draw on
      the very same position); plus the shared-but-essential rules (alfil
      leap, ferz step, no double step, promotion to Mantri only, checkmate);

  (4) the engine's conformance harness (random self-play to terminal).

Prints "SELFTEST OK" and exits 0 on success; raises / exits non-zero on failure.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from agp.chesslike import CState, WHITE, BLACK
from agp.conformance import check
from agp.loader import load_from_dir

_, G = load_from_dir(Path("games/chaturanga"))
_, SHATRANJ = load_from_dir(Path("games/shatranj"))


def cs(pieces, to_move=WHITE, ply=0):
    """Build a CState from {"c,r": (player, letter)}."""
    board = {}
    for k, (pl, t) in pieces.items():
        c, r = (int(x) for x in k.split(","))
        board[(c, r)] = (pl, t)
    return CState(board=board, to_move=to_move, castling=frozenset(), ep=None,
                  reps={}, ply=ply)


def moves_from(state, frm):
    out = set()
    for m in G.legal_moves(state):
        f, t = m.split("=")[0].split(">")
        if f == frm:
            out.add(t)
    return out


def expect(cond, msg):
    if not cond:
        raise AssertionError("FAILED: " + msg)
    print("  ok:", msg)


# --------------------------------------------------------------------------- #
# (1) Perft anchor
# --------------------------------------------------------------------------- #
def perft(g, st, d):
    if d == 0:
        return 1
    if g.is_terminal(st):
        return 0
    return sum(perft(g, g.apply_move(st, m), d - 1) for m in g.legal_moves(st))


def test_perft():
    print("[perft]")
    s0 = G.initial_state()
    got = [perft(G, s0, d) for d in (1, 2, 3)]
    expect(got == [16, 256, 4176],
           f"perft(1..3) from the initial position = 16/256/4176 (got {got})")
    # Cross-check the justification: shatranj (shared movement, mirrored Black
    # array) must produce the same counts at these depths.
    sh = [perft(SHATRANJ, SHATRANJ.initial_state(), d) for d in (1, 2, 3)]
    expect(sh == got, "shatranj package's perft(1..3) matches (mirror symmetry)")


# --------------------------------------------------------------------------- #
# (2) Movement differential vs the shatranj package
# --------------------------------------------------------------------------- #
def test_shatranj_differential():
    print("[shatranj-differential]")
    rng = random.Random(11)
    checked = 0
    for _ in range(6):
        st = G.initial_state()
        for _ply in range(36):
            if G.is_terminal(st):
                break
            a, b = set(G.legal_moves(st)), set(SHATRANJ.legal_moves(st))
            if a != b:
                raise AssertionError(
                    f"legal-move sets diverge from shatranj: {sorted(a ^ b)}")
            expect_quiet = G.in_check(st.board, st.to_move) == \
                SHATRANJ.in_check(st.board, st.to_move)
            if not expect_quiet:
                raise AssertionError("in_check diverges from shatranj")
            checked += 1
            st = G.apply_move(st, rng.choice(sorted(a)))
    expect(checked >= 150,
           f"legal moves + in_check identical to shatranj on {checked} positions")


# --------------------------------------------------------------------------- #
# (3a) Setup: crossed Rajas (White e1, Black d8), Mantris d1/e8.
# --------------------------------------------------------------------------- #
def test_setup():
    print("[setup]")
    b = G.initial_state().board
    expect(b[(4, 0)] == (WHITE, "K") and b[(3, 0)] == (WHITE, "F"),
           "White: Raja on e1, Mantri on d1")
    expect(b[(3, 7)] == (BLACK, "K") and b[(4, 7)] == (BLACK, "F"),
           "Black: Raja on d8, Mantri on e8 (Rajas do NOT face each other)")
    expect(b[(2, 0)] == (WHITE, "A") and b[(5, 7)] == (BLACK, "A"),
           "Gajas on c/f files")
    expect(all(b[(c, 1)] == (WHITE, "P") and b[(c, 6)] == (BLACK, "P")
               for c in range(8)), "full pawn ranks on ranks 2 and 7")
    # The two Mantris start on same-coloured diagonals (they can meet).
    expect((3 + 0) % 2 == (4 + 7) % 2, "Mantris share a square colour")


# --------------------------------------------------------------------------- #
# (3b) Piece movement spot checks (also covered by the differential).
# --------------------------------------------------------------------------- #
def test_mantri_gaja():
    print("[mantri+gaja]")
    st = cs({"4,4": (WHITE, "F"), "4,0": (WHITE, "K"), "4,7": (BLACK, "K"),
             "7,1": (WHITE, "P"), "7,6": (BLACK, "P")})
    expect(moves_from(st, "4,4") == {"5,5", "5,3", "3,5", "3,3"},
           "Mantri moves exactly one square diagonally")

    st2 = cs({
        "4,4": (WHITE, "A"),
        "5,5": (WHITE, "P"), "3,3": (WHITE, "P"),
        "5,3": (WHITE, "P"), "3,5": (BLACK, "P"),   # enemy blocker too
        "4,0": (WHITE, "K"), "4,7": (BLACK, "K"),
        "7,6": (BLACK, "P"),
    })
    expect(moves_from(st2, "4,4") == {"6,6", "2,2", "6,2", "2,6"},
           "Gaja leaps exactly two diagonally, over friend and enemy blockers")


def test_pawn():
    print("[pawn]")
    st = cs({"3,1": (WHITE, "P"), "4,0": (WHITE, "K"), "4,7": (BLACK, "K"),
             "7,6": (BLACK, "P")})
    expect(moves_from(st, "3,1") == {"3,2"},
           "Padati on its home rank steps one square only (no double step)")

    st2 = cs({"3,6": (WHITE, "P"), "0,0": (WHITE, "K"), "7,7": (BLACK, "K"),
              "0,5": (BLACK, "P")})
    promos = {m for m in G.legal_moves(st2) if m.startswith("3,6>3,7")}
    expect(promos == {"3,6>3,7=F"},
           "Padati promotes only to a Mantri (=F) on the last rank")


def test_no_castling():
    print("[no-castling]")
    st = cs({"4,0": (WHITE, "K"), "7,0": (WHITE, "R"), "0,0": (WHITE, "R"),
             "4,7": (BLACK, "K"), "7,6": (BLACK, "P")})
    kd = moves_from(st, "4,0")
    expect("6,0" not in kd and "2,0" not in kd, "Raja has no castling move")


# --------------------------------------------------------------------------- #
# (3c) Stalemate is a WIN for the STALEMATED player (opposite of Shatranj).
# --------------------------------------------------------------------------- #
def test_stalemate_win_for_stalemated():
    print("[stalemate=win-for-stalemated]")
    # Black to move, Black king a8 (0,7), not in check, no legal move; a blocked
    # Black h-pawn keeps Black off the bare-king rule.
    st = cs({"0,7": (BLACK, "K"), "1,6": (WHITE, "R"), "6,6": (WHITE, "R"),
             "4,0": (WHITE, "K"), "7,3": (BLACK, "P"), "7,2": (WHITE, "P")},
            to_move=BLACK)
    expect(not G._lone_king(st.board, BLACK), "Black still has a piece (not bared)")
    expect(G.legal_moves(st) == [], "Black (to move) has no legal move")
    expect(not G.in_check(st.board, BLACK), "Black king is NOT in check -> stalemate")
    expect(G.is_terminal(st), "stalemate position is terminal")
    expect(G.returns(st) == [-1.0, 1.0],
           "the STALEMATED player (Black) WINS in Chaturanga")
    expect(SHATRANJ.returns(st) == [1.0, -1.0],
           "contrast: the same position is a WHITE win in Shatranj")


def test_checkmate():
    print("[checkmate]")
    st = cs({"0,7": (BLACK, "K"), "0,0": (WHITE, "R"), "1,0": (WHITE, "R"),
             "4,4": (WHITE, "K"), "7,3": (BLACK, "P"), "7,2": (WHITE, "P")},
            to_move=BLACK)
    expect(G.in_check(st.board, BLACK), "Black king is in check")
    expect(G.legal_moves(st) == [], "Black has no legal move -> checkmate")
    expect(G.returns(st) == [1.0, -1.0], "checkmate is a win for White")


# --------------------------------------------------------------------------- #
# (3d) Baring wins OUTRIGHT -- no Shatranj "bare back -> draw" exception.
# --------------------------------------------------------------------------- #
def test_bare_king_outright():
    print("[bare-king-outright]")
    st = cs({"2,6": (WHITE, "R"), "2,7": (BLACK, "F"),
             "4,0": (WHITE, "K"), "7,7": (BLACK, "K")}, to_move=WHITE)
    expect(not G.is_terminal(st), "position before the baring capture is not terminal")
    expect("2,6>2,7" in G.legal_moves(st), "the baring rook capture is legal")
    after = G.apply_move(st, "2,6>2,7")
    expect(G.is_terminal(after) and G.returns(after) == [1.0, -1.0],
           "White wins immediately by baring the Black king")

    # Black is bared but the Black king could capture White's last piece next
    # move: in Shatranj that is a DRAW; in Chaturanga the first barer WINS.
    st2 = cs({"0,7": (BLACK, "K"), "1,7": (WHITE, "R"), "4,0": (WHITE, "K")},
             to_move=BLACK)
    expect(G.is_terminal(st2), "the bared position is terminal at once")
    expect(G.returns(st2) == [1.0, -1.0],
           "White wins outright: NO bare-back exception in Chaturanga")
    expect(SHATRANJ.returns(st2) == [0.0, 0.0],
           "contrast: the same position is a DRAW in Shatranj (bares back)")

    # Both kings bare (hand-built only; unreachable in play) is an honest draw.
    st3 = cs({"0,7": (BLACK, "K"), "4,0": (WHITE, "K")}, to_move=BLACK)
    expect(G.is_terminal(st3) and G.returns(st3) == [0.0, 0.0],
           "two lone kings is a draw")


# --------------------------------------------------------------------------- #
# (4) Conformance harness
# --------------------------------------------------------------------------- #
def test_conformance():
    print("[conformance]")
    manifest = json.load(open("games/chaturanga/manifest.json"))
    rep = check(G, manifest, games=60, seed=7)
    print(rep.summary())
    expect(rep.ok, "conformance harness reports OK (random self-play)")
    expect(rep.games_played >= 1, "at least one full random game terminated")


def main():
    test_perft()
    test_shatranj_differential()
    test_setup()
    test_mantri_gaja()
    test_pawn()
    test_no_castling()
    test_stalemate_win_for_stalemated()
    test_checkmate()
    test_bare_king_outright()
    test_conformance()
    print("SELFTEST OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print("SELFTEST FAILED:", e, file=sys.stderr)
        sys.exit(1)
