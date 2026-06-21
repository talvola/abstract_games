#!/usr/bin/env python3
"""Standalone correctness self-test for Horde Chess.

Run from the engine dir:  PYTHONPATH=. python3 games/horde_chess/selftest.py

Anchor: the PUBLISHED Horde opening perft (node counts of the full legal-move
tree from the lichess Horde starting position
``rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1``).
These are the values from the Stockfish / lichess variant perft suite:

    depth 1 = 8        (only 8 of the 36 horde pawns are unblocked)
    depth 2 = 128
    depth 3 = 1274
    depth 4 = 23310

(perft(1) = 8 is independently verifiable by eye: the horde is packed solid, so
only the four rank-5 pawns and the four rank-4 pawns beneath the rank-5 gaps can
move.) We compute perft with this engine's own legal-move generator and assert a
match at depths 1-4. We also check a handful of rule-specific positions:

  * White's first-rank pawns get the double step (and create an e.p. target),
  * White is never "in check" and has no king,
  * Black wins the instant the last White piece is captured,
  * Black can still be checkmated (White win) and stalemated (draw).

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.horde_chess.game import HordeChess

G = HordeChess()

# Published Horde opening perft (lichess / Stockfish variant suite).
EXPECTED_PERFT = {1: 8, 2: 128, 3: 1274, 4: 23310}


def perft(state: CState, depth: int) -> int:
    if depth == 0:
        return 1
    moves = G.legal_moves(state)
    if depth == 1:
        return len(moves)
    total = 0
    for m in moves:
        total += perft(G.apply_move(state, m), depth - 1)
    return total


def check(label, cond):
    if not cond:
        raise AssertionError("FAILED: " + label)
    print("  ok:", label)


def main() -> int:
    # --- Anchor: published opening perft ----------------------------------
    s0 = G.initial_state()
    # Sanity on the start position itself.
    white = sum(1 for (_, (pl, _)) in s0.board.items() if pl == WHITE)
    black = sum(1 for (_, (pl, _)) in s0.board.items() if pl == BLACK)
    check("start has 36 White pawns", white == 36 and all(
        t == "P" for (_, (pl, t)) in s0.board.items() if pl == WHITE))
    check("start has 16 Black pieces", black == 16)
    check("White has no king", G._king(s0.board, WHITE) is None)
    check("Black has a king", G._king(s0.board, BLACK) is not None)

    print("Perft from the Horde opening position:")
    for depth, expected in sorted(EXPECTED_PERFT.items()):
        got = perft(s0, depth)
        print(f"  depth {depth}: got {got}, expected {expected}")
        check(f"perft({depth}) == {expected}", got == expected)

    # --- Rule: White is never in check ------------------------------------
    check("White never in check at start", not G.in_check(s0.board, WHITE))

    # --- Rule: first-rank White pawn double step + en passant -------------
    # A lone White pawn on a1 (r=0) must be able to step to a2 AND a3.
    s = CState(board={(0, 0): (WHITE, "P"), (4, 7): (BLACK, "K")}, to_move=WHITE,
               reps={})
    mvs = set(G.legal_moves(s))
    check("first-rank pawn can single-step (0,0>0,1)", "0,0>0,1" in mvs)
    check("first-rank pawn can double-step (0,0>0,2)", "0,0>0,2" in mvs)

    # After the double step, an en-passant target must be set at (0,1).
    s2 = G.apply_move(s, "0,0>0,2")
    check("double step from rank 1 sets e.p. target at (0,1)",
          s2.ep is not None and s2.ep[0] == (0, 1) and s2.ep[1] == (0, 2))

    # A black pawn beside the double-stepped white pawn can capture en passant.
    s = CState(board={(0, 0): (WHITE, "P"), (1, 2): (BLACK, "P"),
                      (4, 7): (BLACK, "K"), (4, 0): (WHITE, "B")},
               to_move=WHITE, reps={})
    s = G.apply_move(s, "0,0>0,2")          # white double-steps a1->a3, ep at a2
    bmvs = set(G.legal_moves(s))
    check("black can capture en passant onto the e.p. square (1,2>0,1)",
          "1,2>0,1" in bmvs)
    s_ep = G.apply_move(s, "1,2>0,1")
    check("e.p. capture removes the white pawn", (0, 2) not in s_ep.board and
          s_ep.board.get((0, 1)) == (BLACK, "P"))

    # --- Win: Black annihilates the horde ---------------------------------
    # White has a single pawn; Black queen captures it -> White has no pieces.
    s = CState(board={(0, 0): (WHITE, "P"), (1, 1): (BLACK, "Q"),
                      (4, 7): (BLACK, "K")}, to_move=BLACK, reps={})
    s = G.apply_move(s, "1,1>0,0")          # Qxa1 -- last white pawn gone
    check("horde gone -> terminal", G.is_terminal(s))
    check("horde gone -> Black wins", G.returns(s) == [-1.0, 1.0])
    check("no White pieces remain", not G._white_has_pieces(s.board))

    # --- Win: White checkmates Black --------------------------------------
    # Black king a8, White queen b6 + rook supporting -> back-rank-ish mate.
    # Set up a simple mate: Black Kh8; White Qg7 protected by Kh.. (no white king),
    # so protect the queen with a pawn on f6. Black to move, mated.
    s = CState(board={(7, 7): (BLACK, "K"), (6, 6): (WHITE, "Q"),
                      (5, 5): (WHITE, "P")}, to_move=BLACK, reps={})
    check("checkmated Black is in check", G.in_check(s.board, BLACK))
    check("checkmate -> terminal", G.is_terminal(s))
    check("checkmate -> White wins", G.returns(s) == [1.0, -1.0])

    # --- Draw: Black stalemate (not in check, no moves) -------------------
    # Black Kh8; White Qf7 (covers g8/g7/h7 but NOT h8), White pawn g6 guards f7.
    s = CState(board={(7, 7): (BLACK, "K"), (5, 6): (WHITE, "Q"),
                      (6, 5): (WHITE, "P")}, to_move=BLACK, reps={})
    check("stalemated Black is NOT in check", not G.in_check(s.board, BLACK))
    check("stalemate -> terminal", G.is_terminal(s))
    check("stalemate -> draw", G.returns(s) == [0.0, 0.0])

    # --- Draw: White stalemate (White has pieces but no legal move) -------
    # White has a single pawn fully blocked; White to move, no moves -> draw.
    s = CState(board={(0, 1): (WHITE, "P"), (0, 2): (BLACK, "R"),
                      (4, 7): (BLACK, "K")}, to_move=WHITE, reps={})
    # white pawn a2 blocked by black rook a3; no diagonal captures available.
    check("blocked White has no legal moves", len(G.legal_moves(s)) == 0)
    check("White stalemate -> terminal", G.is_terminal(s))
    check("White stalemate -> draw (horde survives)", G.returns(s) == [0.0, 0.0])

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(e)
        sys.exit(1)
