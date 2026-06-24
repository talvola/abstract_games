#!/usr/bin/env python3
"""Standalone correctness self-test for Dunsany's Chess.

Run from the engine dir:  PYTHONPATH=. python3 games/dunsany_chess/selftest.py

Dunsany's Chess (Lord Dunsany, 1942) is an asymmetric variant: Black has the
standard army; White has 32 pawns on ranks 1-4 and no king. **Black moves
first.** Only Black's pawns get the two-square first move. Black wins by
capturing all 32 White pawns; White wins by checkmating Black.

There is no published perft suite for Dunsany's, so we freeze this engine's own
opening-position perft as a REGRESSION lock (recomputed at authoring time):

    depth 1 = 20      (the standard Black chess opening: 16 pawn + 4 knight moves)
    depth 2 = 166
    depth 3 = 3550
    depth 4 = 33601

Plus rule-specific positions:

  * setup: 32 White pawns on ranks 1-4, full Black army on 7-8, Black to move;
  * White pawns NEVER double-step (only Black's do);
  * White has no king and is never "in check";
  * Black wins the instant the last White pawn is captured;
  * White can checkmate Black (White win) and stalemate is a draw;
  * serialize round-trip.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.dunsany_chess.game import DunsanyChess

G = DunsanyChess()

# Frozen opening perft (this engine; regression lock, not an external oracle).
EXPECTED_PERFT = {1: 20, 2: 166, 3: 3550, 4: 33601}


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
    s0 = G.initial_state()

    # --- Setup -------------------------------------------------------------
    white = sum(1 for (_, (pl, _)) in s0.board.items() if pl == WHITE)
    black = sum(1 for (_, (pl, _)) in s0.board.items() if pl == BLACK)
    check("start has 32 White pawns", white == 32 and all(
        t == "P" for (_, (pl, t)) in s0.board.items() if pl == WHITE))
    check("White pawns fill ranks 1-4 (r=0..3)",
          all(0 <= r <= 3 for (c, r), (pl, _) in s0.board.items() if pl == WHITE)
          and sum(1 for (c, r), (pl, _) in s0.board.items()
                  if pl == WHITE) == 32)
    check("start has 16 Black pieces", black == 16)
    check("White has no king", G._king(s0.board, WHITE) is None)
    check("Black has a king", G._king(s0.board, BLACK) is not None)
    check("Black moves first", s0.to_move == BLACK)

    # --- Anchor: frozen opening perft -------------------------------------
    print("Perft from the Dunsany opening position:")
    for depth, expected in sorted(EXPECTED_PERFT.items()):
        got = perft(s0, depth)
        print(f"  depth {depth}: got {got}, expected {expected}")
        check(f"perft({depth}) == {expected}", got == expected)
    check("opening move count == 20", len(G.legal_moves(s0)) == 20)

    # --- Rule: White is never in check ------------------------------------
    check("White never in check at start", not G.in_check(s0.board, WHITE))

    # --- Rule: White pawn NEVER double-steps; Black pawn DOES --------------
    # Lone White pawn on a2 (r=1, its "home" rank in ordinary chess): may only
    # single-step to a3, NOT double-step to a4.
    s = CState(board={(0, 1): (WHITE, "P"), (4, 7): (BLACK, "K")}, to_move=WHITE,
               reps={})
    mvs = set(G.legal_moves(s))
    check("White pawn single-steps (0,1>0,2)", "0,1>0,2" in mvs)
    check("White pawn does NOT double-step (0,1>0,3 absent)", "0,1>0,3" not in mvs)
    # A White pawn on the first rank (r=0) also only single-steps.
    s = CState(board={(0, 0): (WHITE, "P"), (4, 7): (BLACK, "K")}, to_move=WHITE,
               reps={})
    mvs = set(G.legal_moves(s))
    check("White rank-1 pawn single-steps (0,0>0,1)", "0,0>0,1" in mvs)
    check("White rank-1 pawn does NOT double-step (0,0>0,2 absent)",
          "0,0>0,2" not in mvs)
    # Black pawn on its home rank 7 (r=6) DOES double-step.
    s = CState(board={(0, 6): (BLACK, "P"), (4, 7): (BLACK, "K"),
                      (0, 0): (WHITE, "P")}, to_move=BLACK, reps={})
    mvs = set(G.legal_moves(s))
    check("Black pawn single-steps (0,6>0,5)", "0,6>0,5" in mvs)
    check("Black pawn DOES double-step (0,6>0,4)", "0,6>0,4" in mvs)

    # --- Rule: White pawn promotes on rank 8 ------------------------------
    s = CState(board={(0, 6): (WHITE, "P"), (4, 7): (BLACK, "K")}, to_move=WHITE,
               reps={})
    mvs = set(G.legal_moves(s))
    check("White pawn can promote to Q (0,6>0,7=Q)", "0,6>0,7=Q" in mvs)
    s_promo = G.apply_move(s, "0,6>0,7=Q")
    check("promotion yields a White queen", s_promo.board.get((0, 7)) == (WHITE, "Q"))

    # --- Win: Black annihilates the pawn army -----------------------------
    s = CState(board={(0, 0): (WHITE, "P"), (1, 1): (BLACK, "Q"),
                      (4, 7): (BLACK, "K")}, to_move=BLACK, reps={})
    s = G.apply_move(s, "1,1>0,0")          # Qxa1 -- last white pawn gone
    check("army gone -> terminal", G.is_terminal(s))
    check("army gone -> Black wins", G.returns(s) == [-1.0, 1.0])
    check("no White pieces remain", not G._white_has_pieces(s.board))

    # Reach near-annihilation via apply_move then capture the LAST pawn. Two
    # White pawns remain; Black's rook captures one, then the other.
    s = CState(board={(2, 2): (WHITE, "P"), (5, 2): (WHITE, "P"),
                      (2, 5): (BLACK, "R"), (4, 7): (BLACK, "K")},
               to_move=BLACK, reps={})
    check("before capture: White still has pawns", G._white_has_pieces(s.board))
    check("before capture: not terminal", not G.is_terminal(s))
    s = G.apply_move(s, "2,5>2,2")          # Rxc3 -- one pawn left (on f3)
    check("after first capture: White still has a pawn",
          G._white_has_pieces(s.board) and not G.is_terminal(s))
    # White's only pawn single-steps; then Black captures the last one.
    s = G.apply_move(s, "5,2>5,3")          # White f3-f4
    s = G.apply_move(s, "2,2>5,2")          # reposition rook onto f-file rank 3
    s = G.apply_move(s, "5,3>5,4")          # White f4-f5 (any white move)
    s = G.apply_move(s, "5,2>5,4")          # Rxf5 -- captures the LAST white pawn
    check("after capturing last pawn -> Black wins", G.returns(s) == [-1.0, 1.0])
    check("after capturing last pawn -> terminal", G.is_terminal(s))

    # --- Win: White checkmates Black --------------------------------------
    # Black Kh8; White Qg7 protected by a White pawn f6 -> mate, Black to move.
    s = CState(board={(7, 7): (BLACK, "K"), (6, 6): (WHITE, "Q"),
                      (5, 5): (WHITE, "P")}, to_move=BLACK, reps={})
    check("checkmated Black is in check", G.in_check(s.board, BLACK))
    check("checkmate -> terminal", G.is_terminal(s))
    check("checkmate -> White wins", G.returns(s) == [1.0, -1.0])

    # --- Draw: Black stalemate (not in check, no moves) -------------------
    s = CState(board={(7, 7): (BLACK, "K"), (5, 6): (WHITE, "Q"),
                      (6, 5): (WHITE, "P")}, to_move=BLACK, reps={})
    check("stalemated Black is NOT in check", not G.in_check(s.board, BLACK))
    check("Black stalemate -> terminal", G.is_terminal(s))
    check("Black stalemate -> draw", G.returns(s) == [0.0, 0.0])

    # --- Draw: White stalemate (White has a pawn but no legal move) -------
    s = CState(board={(0, 1): (WHITE, "P"), (0, 2): (BLACK, "R"),
                      (4, 7): (BLACK, "K")}, to_move=WHITE, reps={})
    check("blocked White has no legal moves", len(G.legal_moves(s)) == 0)
    check("White stalemate -> terminal", G.is_terminal(s))
    check("White stalemate -> draw (army survives)", G.returns(s) == [0.0, 0.0])

    # --- Serialize round-trip ---------------------------------------------
    s0 = G.initial_state()
    d = G.serialize(s0)
    s_back = G.deserialize(d)
    check("serialize round-trips board", s_back.board == s0.board)
    check("serialize round-trips to_move", s_back.to_move == s0.to_move == BLACK)
    check("serialize round-trips castling", s_back.castling == s0.castling)

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(e)
        sys.exit(1)
