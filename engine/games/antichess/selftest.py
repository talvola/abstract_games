"""Standalone correctness self-test for Antichess (run with PYTHONPATH=. from the
``engine`` dir):

    PYTHONPATH=. python3 games/antichess/selftest.py

It asserts:

  1. The PUBLISHED Antichess / Giveaway opening perft (node counts of the full
     move tree from the standard starting array) at depths 1-3. These are the
     values published by lichess/shakmaty (the variant board) and reproduced by
     python-chess's ``AntichessBoard``:
        depth 1 = 20, depth 2 = 400, depth 3 = 8067.
     Depths 1-2 coincide with ordinary chess (no capture is possible yet, so the
     forced-capture rule does not bite); depth 3 already diverges from standard
     chess's 8902 because some replies are captures that, being compulsory,
     suppress the other moves in that subtree.

  2. Rule-specific positions: compulsory capture, win-by-no-pieces,
     win-by-no-legal-move (stalemate is a win), promotion to a king.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

import sys

from games.antichess.game import Antichess, AState, WHITE, BLACK


# Published Antichess opening perft (lichess / shakmaty / python-chess Antichess).
PERFT = {1: 20, 2: 400, 3: 8067}


def perft(game, state, depth):
    if depth == 0:
        return 1
    if game.is_terminal(state):
        return 0
    total = 0
    for mv in game.legal_moves(state):
        total += perft(game, game.apply_move(state, mv), depth - 1)
    return total


def board_from(pieces, to_move):
    """pieces: {"c,r": (player, letter)}."""
    b = {}
    for k, v in pieces.items():
        c, r = k.split(",")
        b[(int(c), int(r))] = v
    return AState(board=b, to_move=to_move, ep=None,
                  reps={})


def main():
    g = Antichess()

    # ---- 1. perft anchor ------------------------------------------------
    s0 = g.initial_state()
    for d in (1, 2, 3):
        got = perft(g, s0, d)
        assert got == PERFT[d], f"perft({d}) = {got}, expected {PERFT[d]}"
    print(f"perft 1/2/3 = {PERFT[1]}/{PERFT[2]}/{PERFT[3]} OK")

    # ---- 2a. compulsory capture ----------------------------------------
    # White rook a1 can capture a black pawn on a4; white also has many quiet
    # moves, but the capture is forced so EVERY legal move must be a capture.
    s = board_from({"0,0": (WHITE, "R"), "0,3": (BLACK, "P"),
                    "7,0": (WHITE, "K"), "7,7": (BLACK, "K")}, WHITE)
    moves = g.legal_moves(s)
    assert moves == ["0,0>0,3"], f"forced capture failed: {moves}"
    # And the capturing move is legal / applies cleanly.
    ns = g.apply_move(s, "0,0>0,3")
    assert ns.board.get((0, 3)) == (WHITE, "R")
    print("compulsory capture OK")

    # ---- 2b. multiple captures: player may choose which ----------------
    s = board_from({"1,0": (WHITE, "N"), "0,2": (BLACK, "P"), "2,2": (BLACK, "P"),
                    "7,0": (WHITE, "K"), "7,7": (BLACK, "K")}, WHITE)
    moves = set(g.legal_moves(s))
    assert moves == {"1,0>0,2", "1,0>2,2"}, f"choice of captures failed: {moves}"
    print("choice among captures OK")

    # ---- 2c. win by losing all your pieces -----------------------------
    # White has only a rook that must capture black's last pawn; afterwards Black
    # to move has no pieces -> Black wins (Black gave everything away first... here
    # White is forced to capture Black's last unit, leaving Black with no pieces).
    s = board_from({"0,0": (WHITE, "R"), "0,3": (BLACK, "P")}, WHITE)
    # Only legal move is the capture (forced); it removes Black's last piece.
    assert g.legal_moves(s) == ["0,0>0,3"]
    ns = g.apply_move(s, "0,0>0,3")
    assert g._no_pieces(ns.board, BLACK)
    assert g.is_terminal(ns), "no-pieces state must be terminal"
    assert g.returns(ns) == [-1.0, 1.0], (
        f"win-by-no-pieces wrong: {g.returns(ns)}")
    print("win by losing all pieces OK")

    # A state where the side to move itself has no pieces (constructed directly).
    s = board_from({"4,4": (WHITE, "K")}, BLACK)   # Black to move, Black has none
    assert g.is_terminal(s)
    assert g.returns(s) == [-1.0, 1.0], f"got {g.returns(s)}"
    print("no-pieces-on-turn is a win OK")

    # ---- 2d. win by having no legal move (stalemate is a WIN) -----------
    # A blocked-in side with no legal move is the WINNER. Construct Black to move
    # with a single black pawn on its own last rank (row 0): it cannot advance
    # (off the board) and has no diagonal capture, so Black has no legal move and
    # therefore wins. (There is no king-safety, so "no move" only happens when
    # every piece is genuinely stuck.)
    s = board_from({
        "0,0": (BLACK, "P"),    # black pawn a1, on Black's last rank: stuck
        "7,7": (WHITE, "K"),    # lone white king elsewhere
    }, BLACK)
    assert g.legal_moves(s) == [], f"expected no moves, got {g.legal_moves(s)}"
    assert g.is_terminal(s)
    assert g.returns(s) == [-1.0, 1.0], f"stalemate-is-win wrong: {g.returns(s)}"
    print("no-legal-move (stalemate) is a win OK")

    # ---- 2e. promotion to a king is allowed ----------------------------
    s = board_from({"0,6": (WHITE, "P"), "7,7": (BLACK, "R")}, WHITE)
    # White pawn a7 -> a8 promotes; forced? black rook h8 is not capturable by the
    # pawn, and pawn push is the only move -> no capture, so quiet promotion legal.
    moves = set(g.legal_moves(s))
    assert "0,6>0,7=K" in moves, f"promote-to-king missing: {moves}"
    assert "0,6>0,7=Q" in moves and "0,6>0,7=N" in moves
    ns = g.apply_move(s, "0,6>0,7=K")
    assert ns.board.get((0, 7)) == (WHITE, "K"), "pawn did not become a king"
    print("promotion to king OK")

    # ---- 2f. en passant is a (forced) capture --------------------------
    # White pawn b5, black plays a7-a5 creating ep on a6; white must capture e.p.
    s = board_from({"1,4": (WHITE, "P"), "0,6": (BLACK, "P"),
                    "7,0": (WHITE, "K"), "7,7": (BLACK, "K")}, BLACK)
    ns = g.apply_move(s, "0,6>0,4")          # a7-a5 double step
    assert ns.ep == ((0, 5), (0, 4)), f"ep not set: {ns.ep}"
    moves = g.legal_moves(ns)                 # White to move, ep capture available
    assert moves == ["1,4>0,5"], f"ep not forced: {moves}"
    ns2 = g.apply_move(ns, "1,4>0,5")
    assert (0, 4) not in ns2.board and ns2.board.get((0, 5)) == (WHITE, "P")
    print("en passant forced capture OK")

    # ---- 3. serialize round-trips --------------------------------------
    s = g.initial_state()
    assert g.serialize(g.deserialize(g.serialize(s))) == g.serialize(s)
    print("serialize round-trip OK")

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
