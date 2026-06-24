#!/usr/bin/env python3
"""Standalone self-test for Extinction Chess.

Run from the engine dir with:
    PYTHONPATH=. python3 games/extinction_chess/selftest.py

Pure-stdlib (imports only ``agp`` + this game).  Asserts:

  * the opening setup;
  * the ENGINE-DERIVED opening perft (frozen as a regression lock).  Depths 1-3
    coincide with standard chess (20 / 400 / 8902) because no king-safety filter
    ever removes a move that shallow; depth 4 DIVERGES (197742 vs the standard
    197281), proving the royalty filter is genuinely disabled;
  * moving "into check" is LEGAL (a king may step onto / stay on an attacked
    square -- no move is removed for king safety);
  * capturing the opponent's LAST knight / bishop / pawn / king WINS (reached via
    apply_move);
  * the promotion set is exactly {Q,R,B,N,K} (king promotion is legal);
  * a capturing last-pawn promotion that empties BOTH sides' types: the MOVER
    wins (mutual-extinction tiebreak);
  * serialize round-trips the winner field.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from game import ExtinctionChess, ECState, TYPES, WHITE, BLACK  # noqa: E402


def perft(g, state, depth):
    if depth == 0:
        return 1
    return sum(perft(g, g.apply_move(state, m), depth - 1) for m in g.legal_moves(state))


def mk(board, to_move=WHITE):
    g = ExtinctionChess()
    s = ECState(board=dict(board), to_move=to_move, castling=frozenset(), ep=None)
    s.reps = {g._poskey_state(s): 1}
    return g, s


def test_setup():
    g = ExtinctionChess()
    s = g.initial_state()
    assert len(s.board) == 32, len(s.board)
    assert s.board[(4, 0)] == (WHITE, "K")
    assert s.board[(4, 7)] == (BLACK, "K")
    assert s.board[(3, 0)] == (WHITE, "Q")
    assert all(s.board[(c, 1)] == (WHITE, "P") for c in range(8))
    assert s.winner is None
    print("  setup OK")


def test_perft_anchor():
    """ENGINE-DERIVED opening perft, frozen as a regression lock."""
    g = ExtinctionChess()
    s = g.initial_state()
    # d1-d3 equal standard chess (no king-safety prune that shallow); d4 diverges.
    for depth, expect in ((1, 20), (2, 400), (3, 8902), (4, 197742)):
        got = perft(g, s, depth)
        assert got == expect, f"perft({depth}) = {got}, expected {expect}"
    print("  perft anchor OK: 20 / 400 / 8902 / 197742 (engine-derived; "
          "d4 != std chess 197281 -> royalty filter is off)")


def test_into_check_is_legal():
    """The king is not royal: a move that leaves one's own king attacked, or
    steps the king onto an attacked square, is LEGAL."""
    g = ExtinctionChess()
    # Black king e8; White rook on e1 -> the whole e-file is 'check' on the black
    # king, yet Black has its full legal move set (nothing is pruned for safety).
    board = {
        (4, 0): (WHITE, "K"), (3, 0): (WHITE, "Q"), (0, 0): (WHITE, "R"),
        (7, 0): (WHITE, "R"), (2, 0): (WHITE, "B"), (5, 0): (WHITE, "N"),
        (0, 1): (WHITE, "P"),
        (4, 7): (BLACK, "K"), (3, 7): (BLACK, "Q"), (0, 7): (BLACK, "R"),
        (7, 7): (BLACK, "R"), (2, 7): (BLACK, "B"), (5, 7): (BLACK, "N"),
        (0, 6): (BLACK, "P"),
        (4, 3): (WHITE, "R"),   # rook on e4 attacks the black king on e8
    }
    g, s = mk(board, to_move=BLACK)
    assert g.attacked(s.board, 4, 7, WHITE), "black king should be attacked"
    legal = g.legal_moves(s)
    # A move that does NOT resolve the attack on e8 (e.g. moving the a8 rook) is
    # still legal -- standard chess would forbid it.
    assert "0,7>0,6" not in legal  # blocked by own pawn; pick a real one:
    assert "3,7>3,6" in legal or "3,7>4,6" in legal, legal  # queen can move freely
    # And the black king may step from e8 onto e7 -- STILL on the attacked file
    # (i.e. "into check") -- which orthodox chess forbids.
    assert s.board.get((4, 6)) is None
    assert "4,7>4,6" in legal, "king must be allowed to stay on the attacked file"
    print("  moving into/through check is legal OK")


def test_extinct_last_knight_wins():
    g, s = mk({
        (0, 0): (WHITE, "K"), (1, 0): (WHITE, "Q"), (2, 0): (WHITE, "R"),
        (3, 0): (WHITE, "B"), (4, 0): (WHITE, "N"), (5, 0): (WHITE, "P"),
        (0, 7): (BLACK, "K"), (1, 7): (BLACK, "Q"), (2, 7): (BLACK, "R"),
        (3, 7): (BLACK, "B"), (5, 7): (BLACK, "P"),
        (3, 5): (BLACK, "N"),          # Black's ONLY knight
        (4, 4): (WHITE, "B"),          # White bishop on e5 attacks d6 knight
    }, to_move=WHITE)
    mv = "4,4>3,5"                      # Bxd6 captures the last black knight
    assert mv in g.legal_moves(s)
    s2 = g.apply_move(s, mv)
    assert s2.winner == WHITE
    assert g.is_terminal(s2)
    assert g.returns(s2) == [1.0, -1.0]
    assert g.legal_moves(s2) == []
    assert "N" not in g._present_types(s2.board, BLACK)
    print("  capturing last knight wins OK")


def test_extinct_last_king_wins():
    g, s = mk({
        (0, 0): (WHITE, "K"), (1, 0): (WHITE, "Q"), (2, 0): (WHITE, "R"),
        (3, 0): (WHITE, "B"), (4, 0): (WHITE, "N"), (5, 0): (WHITE, "P"),
        (1, 7): (BLACK, "Q"), (2, 7): (BLACK, "R"), (3, 7): (BLACK, "B"),
        (4, 7): (BLACK, "N"), (5, 7): (BLACK, "P"),
        (3, 5): (BLACK, "K"),          # Black's only king (one per side)
        (4, 4): (WHITE, "R"),          # white rook e5 -> d5? use rook on d-file
        (3, 4): (WHITE, "R"),          # rook on d5 attacks the king on d6
    }, to_move=WHITE)
    mv = "3,4>3,5"                      # Rxd6 captures the black king
    assert mv in g.legal_moves(s)
    s2 = g.apply_move(s, mv)
    assert s2.winner == WHITE, s2.winner
    assert g.is_terminal(s2)
    assert "K" not in g._present_types(s2.board, BLACK)
    print("  capturing the king wins OK")


def test_promotion_set_is_qrbnk():
    """Last-rank promotion offers exactly {Q,R,B,N,K} (king promotion legal)."""
    g, s = mk({
        (0, 0): (WHITE, "K"), (1, 0): (WHITE, "Q"), (2, 0): (WHITE, "R"),
        (3, 0): (WHITE, "B"), (4, 0): (WHITE, "N"),
        (0, 7): (BLACK, "K"), (1, 7): (BLACK, "Q"), (2, 7): (BLACK, "R"),
        (3, 7): (BLACK, "B"), (4, 7): (BLACK, "N"), (5, 7): (BLACK, "P"),
        (6, 6): (WHITE, "P"),          # white pawn g7 promotes on g8
    }, to_move=WHITE)
    promos = sorted(m.split("=")[1] for m in g.legal_moves(s)
                    if m.startswith("6,6>6,7") and "=" in m)
    assert promos == ["B", "K", "N", "Q", "R"], promos
    # And promoting to a KING actually works.
    s2 = g.apply_move(s, "6,6>6,7=K")
    assert s2.board[(6, 7)] == (WHITE, "K")
    print("  promotion set {Q,R,B,N,K} incl. king OK")


def test_mutual_extinction_mover_wins():
    """A capturing last-pawn promotion that empties BOTH sides' types: the side
    that MADE the move wins (the published bxc8=Q example)."""
    # White's last pawn on b7 (1,6); Black's last bishop on c8 (2,7).
    # bxc8=Q empties White's pawns AND Black's bishops simultaneously.
    g, s = mk({
        (0, 0): (WHITE, "K"), (3, 0): (WHITE, "Q"), (2, 0): (WHITE, "R"),
        (4, 0): (WHITE, "N"),
        (0, 7): (BLACK, "K"), (3, 5): (BLACK, "Q"), (5, 5): (BLACK, "R"),
        (6, 5): (BLACK, "N"), (7, 6): (BLACK, "P"),
        (1, 6): (WHITE, "P"),          # White's ONLY pawn on b7
        (2, 7): (BLACK, "B"),          # Black's ONLY bishop on c8
    }, to_move=WHITE)
    # White pawn b7 captures the bishop on c8 and promotes.
    mv = "1,6>2,7=Q"
    assert mv in g.legal_moves(s), g.legal_moves(s)
    s2 = g.apply_move(s, mv)
    # White's pawns are now extinct AND Black's bishops are now extinct.
    assert "P" not in g._present_types(s2.board, WHITE)
    assert "B" not in g._present_types(s2.board, BLACK)
    # Mover (White) is ruled the winner.
    assert s2.winner == WHITE, s2.winner
    assert g.returns(s2) == [1.0, -1.0]
    print("  mutual extinction -> mover wins OK")


def test_self_extinction_is_a_loss():
    """If a move empties ONLY the mover's own type (no opponent extinction), the
    mover loses.  E.g. promoting your last pawn to a piece you... actually that
    only triggers if you have no other pawns; here we promote the last pawn to a
    type that does NOT capture, leaving the opponent intact -> self-loss."""
    g, s = mk({
        (0, 0): (WHITE, "K"), (3, 0): (WHITE, "Q"), (2, 0): (WHITE, "R"),
        (4, 0): (WHITE, "B"), (5, 0): (WHITE, "N"),
        (0, 7): (BLACK, "K"), (3, 7): (BLACK, "Q"), (5, 7): (BLACK, "R"),
        (6, 7): (BLACK, "B"), (7, 7): (BLACK, "N"), (7, 6): (BLACK, "P"),
        (1, 6): (WHITE, "P"),          # White's ONLY pawn on b7, promotes on b8
    }, to_move=WHITE)
    mv = "1,6>1,7=Q"                    # promote last pawn (no capture)
    assert mv in g.legal_moves(s)
    s2 = g.apply_move(s, mv)
    assert "P" not in g._present_types(s2.board, WHITE)
    # Opponent still has every type, so this is a pure self-extinction -> Black wins.
    assert s2.winner == BLACK, s2.winner
    assert g.returns(s2) == [-1.0, 1.0]
    print("  pure self-extinction -> mover loses OK")


def test_serialize_roundtrip():
    g = ExtinctionChess()
    s = g.initial_state()
    s = g.apply_move(s, "4,1>4,3")
    d = g.serialize(s)
    assert d["winner"] is None, d
    s2 = g.deserialize(d)
    assert isinstance(s2, ECState)
    assert s2.winner is None
    assert g.serialize(s2) == d
    # Round-trip a state that carries a winner.
    s3 = ECState(board=s.board, to_move=s.to_move, castling=s.castling, ep=s.ep,
                 halfmove=s.halfmove, ply=s.ply, reps=s.reps, winner=WHITE)
    d3 = g.serialize(s3)
    assert d3["winner"] == WHITE
    assert g.deserialize(d3).winner == WHITE
    print("  serialize round-trip OK")


def main():
    test_setup()
    test_perft_anchor()
    test_into_check_is_legal()
    test_extinct_last_knight_wins()
    test_extinct_last_king_wins()
    test_promotion_set_is_qrbnk()
    test_mutual_extinction_mover_wins()
    test_self_extinction_is_a_loss()
    test_serialize_roundtrip()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
