#!/usr/bin/env python3
"""Standalone correctness self-test for the Racing Kings module.

Run from the engine directory:

    PYTHONPATH=. python3 games/racing_kings/selftest.py

Asserts:

1. The PUBLISHED Racing Kings opening perft (move-generation node counts) from
   the standard start: 21 / 421 / 11264 / 296242 at depths 1..4. These numbers
   are the external correctness anchor -- they appear in shakmaty's
   ``tests/racingkings.perft`` (id ``racingkings-start``, epd
   ``8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - -``) and in the Fairy-Stockfish test
   suite (``expect perft.exp racingkings startpos 4 296242``). Both already
   account for the "check is forbidden" rule, so matching them confirms the
   no-check move filter as well as ordinary move generation.

   A second published position is also checked: the "occupied goal" perft from
   shakmaty (epd ``4brn1/2K2k2/8/8/8/8/8/8 w - -``): 6 / 33 / 178 / 3151 /
   12981 / 265932 at depths 1..6.

2. Rule-specific positions: no legal move gives or leaves a check; a king
   reaching the eighth rank wins (and the White-reaches / Black-replies draw).

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.chesslike import CState, WHITE, BLACK  # noqa: E402

# Import the game module directly (package layout games/<uid>/game.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game import RacingKings, GOAL_ROW  # noqa: E402

G = RacingKings()


# --------------------------------------------------------------------------- #
# FEN helper: build a CState from a Racing-Kings FEN (board + side to move).
# --------------------------------------------------------------------------- #
def state_from_fen(fen: str) -> CState:
    parts = fen.split()
    board_part = parts[0]
    to_move = WHITE if (len(parts) < 2 or parts[1] == "w") else BLACK
    board = {}
    ranks = board_part.split("/")  # rank 8 first
    assert len(ranks) == 8, fen
    for i, rank in enumerate(ranks):
        row = 7 - i  # FEN lists rank 8 first; our row 7 == rank 8
        col = 0
        for ch in rank:
            if ch.isdigit():
                col += int(ch)
                continue
            player = WHITE if ch.isupper() else BLACK
            board[(col, row)] = (player, ch.upper())
            col += 1
        assert col == 8, f"bad rank {rank!r} in {fen}"
    key = G._poskey(board, to_move, frozenset(), None)
    return CState(board=board, to_move=to_move, castling=frozenset(), ep=None,
                  reps={key: 1})


# --------------------------------------------------------------------------- #
# Perft (counts leaf nodes, ignoring repetition / ply-cap draws so it matches a
# pure move-generation perft).
# --------------------------------------------------------------------------- #
def perft(state: CState, depth: int) -> int:
    if depth == 0:
        return 1
    moves = [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for f, t in G._legal(state)]
    if depth == 1:
        return len(moves)
    total = 0
    for mv in moves:
        total += perft(G.apply_move(state, mv), depth - 1)
    return total


def check(label, got, want):
    status = "ok" if got == want else "FAIL"
    print(f"  [{status}] {label}: got {got}, want {want}")
    if got != want:
        raise AssertionError(f"{label}: expected {want}, got {got}")


def main():
    print("Racing Kings selftest")

    # ----- 1. Published opening perft (the external anchor) -----------------
    start = G.initial_state()
    # Sanity: our initial_state matches the published FEN start.
    fen_start = state_from_fen("8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1")
    assert start.board == fen_start.board, "initial_state board != published start FEN"
    assert start.to_move == WHITE

    print("Published opening perft (shakmaty / Fairy-Stockfish):")
    check("perft(1)", perft(start, 1), 21)
    check("perft(2)", perft(start, 2), 421)
    check("perft(3)", perft(start, 3), 11264)
    check("perft(4)", perft(start, 4), 296242)

    # Second published position (shakmaty id "occupied-goal").
    print("Published 'occupied goal' perft (shakmaty):")
    occ = state_from_fen("4brn1/2K2k2/8/8/8/8/8/8 w - - 0 1")
    check("perft(1)", perft(occ, 1), 6)
    check("perft(2)", perft(occ, 2), 33)
    check("perft(3)", perft(occ, 3), 178)
    check("perft(4)", perft(occ, 4), 3151)
    check("perft(5)", perft(occ, 5), 12981)
    check("perft(6)", perft(occ, 6), 265932)

    # ----- 2. Rule-specific positions ---------------------------------------
    print("Rule checks:")

    # (a) No legal move leaves OWN king in check, and none GIVES check.
    for st in (start, occ, state_from_fen("8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - -")):
        for f, t in G._legal(st):
            nb = G._apply_board(st.board, f, t, st.ep)
            assert not G.in_check(nb, st.to_move), "a legal move left own king in check"
            assert not G.in_check(nb, 1 - st.to_move), "a legal move gave check"
    print("  [ok] no legal move gives or leaves a check")

    # (b) "May not give check." White rook on e2, Black king on e7 (open e-file;
    #     neither king on the goal row so the race is still live). Sliding the
    #     rook up the e-file to e3..e6 would check the Black king and must be
    #     forbidden; sliding it sideways (off the e-file) is fine.
    chk = state_from_fen("8/4k3/8/8/8/8/4R3/K7 w - -")
    assert not G.is_terminal(chk)
    legal = G.legal_moves(chk)
    for forbidden in ("4,1>4,2", "4,1>4,3", "4,1>4,4", "4,1>4,5"):  # e3,e4,e5,e6
        assert forbidden not in legal, f"check-giving rook move {forbidden} was allowed"
    # Rook sliding sideways (off the e-file) is fine, e.g. e2->a2.
    assert "4,1>0,1" in legal, "a harmless rook move was wrongly filtered"
    print("  [ok] check-giving moves are forbidden (no-check rule)")

    # (c) A king reaching the eighth rank wins. Black king a7 -> a8 wins for Black.
    bwin = state_from_fen("8/k7/8/8/8/8/8/7K b - -")
    assert not G.is_terminal(bwin)
    s2 = G.apply_move(bwin, "0,6>0,7")  # a7 -> a8 (row 7)
    assert G._king_row(s2.board, BLACK) == GOAL_ROW
    assert G.is_terminal(s2), "black king on rank 8 should be terminal"
    check("returns after Black reaches rank 8", G.returns(s2), [-1.0, 1.0])

    # (d) White reaches rank 8 while Black's king is one step from rank 8 ->
    #     NOT yet terminal: Black gets the equalising reply. White king g7 -> g8,
    #     Black king a7 (a8/b8 empty and unattacked) can still dash to rank 8.
    wstep = state_from_fen("8/k5K1/8/8/8/8/8/8 w - -")
    s3 = G.apply_move(wstep, "6,6>6,7")  # g7 -> g8
    assert G._king_row(s3.board, WHITE) == GOAL_ROW
    assert s3.to_move == BLACK
    assert not G.is_terminal(s3), "White-home with Black able to reply must not be terminal"

    # (d1) If Black CANNOT reach rank 8 on the reply, White wins immediately --
    #      the game is over the instant White arrives (no idle Black reply). Black
    #      king on a1 is far from rank 8 -> White wins as soon as it lands.
    wfar = state_from_fen("8/7K/8/8/8/8/8/k7 w - -")
    s4 = G.apply_move(wfar, "7,6>7,7")  # h7 -> h8; Black king a1 can't reach rank 8
    assert s4.to_move == BLACK
    assert G.is_terminal(s4), "White wins at once when Black cannot match"
    check("returns: White home, Black cannot match", G.returns(s4), [1.0, -1.0])

    # (d2) If Black CAN reach rank 8 on the reply -> draw (both kings home).
    #      Continue from (d): Black king a7 -> a8.
    s5 = G.apply_move(s3, "0,6>0,7")  # black a7 -> a8
    assert G._king_row(s5.board, BLACK) == GOAL_ROW
    assert G.is_terminal(s5)
    check("returns: both kings on rank 8 (draw)", G.returns(s5), [0.0, 0.0])
    print("  [ok] race win/draw conditions (incl. White-reaches / Black-replies)")

    # (e) serialize round-trips.
    for st in (start, occ, s3):
        again = G.deserialize(G.serialize(st))
        assert G.serialize(again) == G.serialize(st), "serialize did not round-trip"
    print("  [ok] serialize round-trips")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
