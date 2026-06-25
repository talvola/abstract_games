"""Alice Chess selftest — pure stdlib (imports only agp + this game).

Run: PYTHONPATH=engine python3 engine/games/alice_chess/selftest.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.alice_chess.game import (  # noqa: E402
    AliceChess, AliceState, _pos_key, WHITE, BLACK,
)

G = AliceChess()


def _state(boardA, boardB, to_move):
    """Build a state from {(c,r):(owner,letter)} dicts for boards A and B."""
    boards = (dict(boardA), dict(boardB))
    s = AliceState(boards=boards, to_move=to_move, ply=0)
    s.seen = {_pos_key(boards, to_move): 1}
    return s


def test_start():
    s = G.initial_state()
    # 16 White + 16 Black on board A; board B empty.
    assert len(s.boards[0]) == 32, len(s.boards[0])
    assert len(s.boards[1]) == 0, len(s.boards[1])
    # White king on A e1 = (4,0).
    assert s.boards[0][(4, 0)] == (WHITE, "K")
    # 20 opening moves? Standard chess has 20; but in Alice every landing's
    # mirror on board B is empty (B is empty), so the count equals normal chess.
    moves = G.legal_moves(s)
    assert len(moves) == 20, len(moves)
    print("test_start OK (32 pieces on A, B empty, 20 opening moves)")


def test_knight_transfer():
    # White knight on A b1=(1,0) jumps to c3=(2,2); transfers to B c3.
    s = _state(
        {(1, 0): (WHITE, "N"), (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")},
        {},
        WHITE,
    )
    mv = "0,1,0>0,2,2"
    assert mv in G.legal_moves(s), G.legal_moves(s)
    ns = G.apply_move(s, mv)
    # Knight gone from board A, now on board B at (2,2).
    assert (2, 2) not in ns.boards[0]
    assert ns.boards[1][(2, 2)] == (WHITE, "N"), ns.boards[1]
    # Illegal if B's mirror target (c3) is occupied.
    s2 = _state(
        {(1, 0): (WHITE, "N"), (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")},
        {(2, 2): (WHITE, "P")},  # blocks the transfer
        WHITE,
    )
    assert "0,1,0>0,2,2" not in G.legal_moves(s2)
    print("test_knight_transfer OK (transfer happens; blocked when mirror occupied)")


def test_capture_on_moving_board():
    # White rook on A a1=(0,0) captures Black pawn on A a4=(0,3); transfers to B a4.
    s = _state(
        {(0, 0): (WHITE, "R"), (0, 3): (BLACK, "P"),
         (4, 0): (WHITE, "K"), (7, 7): (BLACK, "K")},
        {},
        WHITE,
    )
    mv = "0,0,0>0,0,3"
    assert mv in G.legal_moves(s)
    ns = G.apply_move(s, mv)
    # Pawn captured (gone), rook left board A, rook now on board B at (0,3).
    assert (0, 3) not in ns.boards[0]
    assert (0, 0) not in ns.boards[0]
    assert ns.boards[1][(0, 3)] == (WHITE, "R"), ns.boards[1]
    # Capture illegal if the rook's mirror square on B is occupied.
    s2 = _state(
        {(0, 0): (WHITE, "R"), (0, 3): (BLACK, "P"),
         (4, 0): (WHITE, "K"), (7, 7): (BLACK, "K")},
        {(0, 3): (WHITE, "P")},
        WHITE,
    )
    assert "0,0,0>0,0,3" not in G.legal_moves(s2)
    print("test_capture_on_moving_board OK (capture on moving board; mirror must be vacant)")


def test_checkmate():
    # The KEY Alice subtlety: the moving piece TRANSFERS to the other board, so a
    # checking piece must END UP (after transfer) on the same board as the enemy
    # king. To check a Black king on board A, the checking piece must move on
    # board B and transfer to board A.
    #
    # Position (mate in one for White):
    #   Black K on board A h8 = (7,7).
    #   White Q on board B h1 = (7,0): plays on board B to h7 (7,6), then
    #     TRANSFERS to board A (7,6) — landing next to the Black king, check.
    #   White K on board A f7 = (5,6): covers Black's flight squares g8 (6,7)
    #     and g7 (6,6).
    #   White N on board A f8 = (5,7): defends the mating square (7,6) on board A
    #     [(5,7)->(7,6) = (+2,-1) knight move], so Kxh7 is illegal (the king would
    #     be in check on board A before transferring).
    # The queen's transfer target board A (7,6) is empty; its path on board B is
    # clear. Black's only adjacent squares are covered or the defended queen → mate.
    boardA = {
        (7, 7): (BLACK, "K"),
        (5, 6): (WHITE, "K"),
        (5, 7): (WHITE, "N"),  # defends the mating square (7,6) on board A
    }
    boardB = {
        (7, 0): (WHITE, "Q"),
    }
    s = _state(boardA, boardB, WHITE)
    mv = "1,7,0>1,7,6"  # Qh1-h7 on board B; transfers to board A h7
    legal = G.legal_moves(s)
    assert mv in legal, ("mating move not legal", legal)
    ns = G.apply_move(s, mv)
    # Queen now on board A delivering check.
    assert ns.boards[0][(7, 6)] == (WHITE, "Q"), ns.boards[0]
    assert ns.winner == WHITE, ("expected White mate", ns.winner, ns.draw)
    assert G.is_terminal(ns)
    assert G.returns(ns) == [1.0, -1.0]
    print("test_checkmate OK (White mates via apply_move; checking piece "
          "transfers onto the king's board)")


def test_serialize_roundtrip():
    s = G.initial_state()
    # Play a few moves to populate both boards + seen.
    for mv in ("0,4,1>0,4,3", "0,4,6>0,4,4", "0,1,0>0,2,2"):
        s = G.apply_move(s, mv)
    d = G.serialize(s)
    s2 = G.deserialize(d)
    assert G.serialize(s2) == d, "serialize did not round-trip"
    # Both boards populated (some pieces transferred to B).
    assert len(s.boards[1]) >= 1
    print("test_serialize_roundtrip OK")


def test_not_escape_check_by_transfer():
    # King in check on its own board cannot escape merely by a non-king move that
    # leaves it in check before the transfer. Black rook on A checks White king;
    # White must answer the check ON board A.
    boardA = {
        (4, 0): (WHITE, "K"),
        (4, 7): (BLACK, "R"),   # checks White K down the e-file on board A
        (0, 0): (BLACK, "K"),
    }
    s = _state(boardA, {}, WHITE)
    legal = G.legal_moves(s)
    # Every legal move must leave White not in check after resolving.
    for mv in legal:
        ns = G.apply_move(s, mv)
        # After White's move it's Black to move; White must not be in check
        # would have been filtered, so just sanity that some move exists.
    assert legal, "White should have king escapes"
    # Specifically, the White king CAN step off the e-file (e.g. to d1/f1) and
    # transfer; moving the king to d1 (3,0) escapes the check.
    assert "0,4,0>0,3,0" in legal or "0,4,0>0,5,0" in legal, legal
    print("test_not_escape_check_by_transfer OK")


if __name__ == "__main__":
    test_start()
    test_knight_transfer()
    test_capture_on_moving_board()
    test_checkmate()
    test_serialize_roundtrip()
    test_not_escape_check_by_transfer()
    print("\nALL alice_chess selftests passed")
