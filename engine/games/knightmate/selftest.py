"""Standalone correctness self-test for Knightmate (run with PYTHONPATH=. from the
``engine`` dir):

    PYTHONPATH=. python3 games/knightmate/selftest.py

Pure-stdlib (imports only ``agp`` + this game). It asserts:

  1. The opening perft (full move-tree node counts from the standard Knightmate
     array) at depths 1-4. These are ENGINE-DERIVED (no published Knightmate
     perft is standard) and frozen here as a regression lock. Depth 1 = 18 is
     hand-verified below.
  2. The setup: royal knight (letter "K") on e1/e8; Commoners ("C") on the
     knights' squares b1/g1, b8/g8.
  3. The royal knight moves as a knight AND is royal: in a "check" position the
     side to move is restricted to escaping check; checkmate of the royal knight
     is terminal with the right winner.
  4. A Commoner is an ordinary, NON-royal piece: attacking a Commoner does NOT
     restrict the owner's moves, and a Commoner can be captured.
  5. A Commoner moves like a king (8 one-square directions).
  6. Pawn promotion offers Q/R/B/Commoner but NOT a (royal) knight.
  7. Castling exists (royal knight + rook), and serialize round-trips.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

import sys

from games.knightmate.game import Knightmate
from agp.chesslike import CState, WHITE, BLACK


# Engine-derived Knightmate opening perft (frozen regression lock).
#   depth 1 = 18  (hand-verified: 8 pawns x 2 steps = 16, plus the royal knight on
#                  e1 reaching d3 and f3 = 2; commoners/bishops/rooks/queen all
#                  blocked by their own pawns/pieces).
PERFT = {1: 18, 2: 324, 3: 6765, 4: 139774}


def perft(game, state, depth):
    if depth == 0:
        return 1
    if game.is_terminal(state):
        return 0
    total = 0
    for mv in game.legal_moves(state):
        total += perft(game, game.apply_move(state, mv), depth - 1)
    return total


def board_from(pieces, to_move=WHITE, castling=""):
    """pieces: {(c,r): (player, letter)}."""
    return CState(board=dict(pieces), to_move=to_move,
                  castling=frozenset(castling), ep=None, reps={})


def cellset(moves):
    """Set of (from, to) tuples from move strings (drop the promotion suffix)."""
    out = set()
    for m in moves:
        raw = m.split("=")[0]
        fs, ts = raw.split(">")
        fc, fr = (int(x) for x in fs.split(","))
        tc, tr = (int(x) for x in ts.split(","))
        out.add(((fc, fr), (tc, tr)))
    return out


def main(deep=False):
    g = Knightmate()
    s0 = g.initial_state()

    # ---- 1. perft anchor -------------------------------------------------
    # Depths 1-3 always run (fast, <1s); depth 4 (the full 139774-node freeze) is
    # opt-in (run the file directly) so the aggregate selftest suite stays quick.
    depths = (1, 2, 3, 4) if deep else (1, 2, 3)
    for d in depths:
        got = perft(g, s0, d)
        assert got == PERFT[d], f"perft({d}) = {got}, expected {PERFT[d]}"
    assert len(g.legal_moves(s0)) == 18, "opening should have 18 legal moves"

    # ---- 2. setup: royal knight on e1/e8, commoners on b/g files ---------
    b = s0.board
    assert b[(4, 0)] == (WHITE, "K"), "white royal knight should be on e1 (4,0)"
    assert b[(4, 7)] == (BLACK, "K"), "black royal knight should be on e8 (4,7)"
    for sq in [(1, 0), (6, 0)]:
        assert b[sq] == (WHITE, "C"), f"white commoner expected on {sq}"
    for sq in [(1, 7), (6, 7)]:
        assert b[sq] == (BLACK, "C"), f"black commoner expected on {sq}"
    # piece movement: K leaps as a knight, C steps as a king
    assert g.PIECES["K"][1] and not g.PIECES["K"][0], "K must be a leaper (knight)"
    assert set(g.PIECES["K"][1]) == {(1, 2), (2, 1), (-1, 2), (-2, 1),
                                     (1, -2), (2, -1), (-1, -2), (-2, -1)}
    assert g.PIECES["C"][1] and not g.PIECES["C"][0], "C must be a leaper (king)"
    assert set(g.PIECES["C"][1]) == {(1, 0), (-1, 0), (0, 1), (0, -1),
                                     (1, 1), (1, -1), (-1, 1), (-1, -1)}

    # ---- 3. the royal knight IS royal: knight-check restricts moves ------
    # White royal knight on d4 (3,3); a Black ENEMY knight ("K") on e6 (4,5)
    # attacks it via the (1,2) leap. White must respond to check.
    chk = board_from({(3, 3): (WHITE, "K"), (4, 5): (BLACK, "K"),
                      (0, 0): (WHITE, "R")}, to_move=WHITE)
    assert g.in_check(chk.board, WHITE), "white royal knight should be in check"
    legal = cellset(g.legal_moves(chk))
    # The far-away rook on a1 may NOT shuffle while ignoring the check; every legal
    # move must resolve the check (move the royal knight or capture the attacker).
    for (frm, to) in legal:
        nb = dict(chk.board)
        pl, t = nb.pop(frm)
        nb[to] = (pl, t)
        assert not g.in_check(nb, WHITE), f"move {frm}->{to} leaves the royal knight in check"
    # capturing the attacking enemy knight is one legal escape (d4 knight -> e6)
    assert ((3, 3), (4, 5)) in legal, "royal knight should be able to capture its attacker"

    # ---- 3b. checkmate of the royal knight is terminal with the right winner
    # Black royal knight cornered on a8 (0,7). The White royal knight on c7 (2,6)
    # delivers a KNIGHT check (a8 is a (2,1)/(1,2) leap from c7). The black knight's
    # only leaps from a8 are b6 (1,5) and c7 (2,6): c7 is occupied by the checking
    # White knight, and b6 holds the White queen DEFENDED by a White rook on b1
    # (1,0), so a8->b6 is an illegal capture. No legal move -> checkmate.
    mate = board_from({
        (0, 7): (BLACK, "K"),          # black royal knight, cornered on a8
        (2, 6): (WHITE, "K"),          # white royal knight c7 -> knight-checks a8
        (1, 5): (WHITE, "Q"),          # white queen b6 -> covers the b6 escape
        (1, 0): (WHITE, "R"),          # white rook b1 -> defends the b6 queen
    }, to_move=BLACK)
    assert g.in_check(mate.board, BLACK), "black royal knight should be in check (knight on c7)"
    assert g.legal_moves(mate) == [], "checkmate: black royal knight has no legal move"
    assert g.is_terminal(mate), "checkmate position must be terminal"
    ret = g.returns(mate)
    assert ret == [1.0, -1.0], f"White should win the checkmate, got {ret}"

    # ---- 4. a Commoner is NON-royal: attacking it does NOT restrict moves
    # White: royal knight a1 (safe), a Commoner on d4 attacked by a Black rook on
    # d8. White is NOT in check (the royal knight is unattacked); White may freely
    # make a move that leaves the Commoner hanging.
    cm = board_from({(0, 0): (WHITE, "K"), (3, 3): (WHITE, "C"),
                     (3, 7): (BLACK, "R"), (7, 7): (BLACK, "K")}, to_move=WHITE)
    assert not g.in_check(cm.board, WHITE), "a Commoner under attack is NOT check"
    legal = cellset(g.legal_moves(cm))
    # White royal knight a1 may leap to b3(1,2) or c2(2,1), ignoring the threatened
    # Commoner -> the Commoner is not royal.
    assert ((0, 0), (1, 2)) in legal or ((0, 0), (2, 1)) in legal, \
        "royal knight free to move while a Commoner is attacked"
    # And the Black rook can actually capture the Commoner (ordinary piece).
    cm2 = board_from({(0, 0): (WHITE, "K"), (3, 3): (WHITE, "C"),
                      (3, 7): (BLACK, "R"), (7, 7): (BLACK, "K")}, to_move=BLACK)
    assert ((3, 7), (3, 3)) in cellset(g.legal_moves(cm2)), "rook should capture the Commoner"
    after = g.apply_move(cm2, "3,7>3,3")
    assert after.board[(3, 3)] == (BLACK, "R"), "Commoner should be captured"

    # ---- 5. a Commoner moves like a king (8 single steps) ----------------
    king_test = board_from({(3, 3): (WHITE, "C"), (0, 0): (WHITE, "K"),
                            (7, 7): (BLACK, "K")}, to_move=WHITE)
    cmoves = {to for (frm, to) in cellset(g.legal_moves(king_test)) if frm == (3, 3)}
    expected = {(3, 4), (3, 2), (4, 3), (2, 3), (4, 4), (4, 2), (2, 4), (2, 2)}
    assert cmoves == expected, f"Commoner king-moves wrong: {cmoves}"

    # ---- 6. promotion offers Q/R/B/Commoner but NOT a knight -------------
    # A White pawn on g7 (6,6) one step from promotion on g8 (6,7).
    promo = board_from({(6, 6): (WHITE, "P"), (0, 0): (WHITE, "K"),
                        (7, 7): (BLACK, "K")}, to_move=WHITE)
    suffixes = sorted({m.split("=")[1] for m in g.legal_moves(promo) if "=" in m})
    assert suffixes == ["B", "C", "Q", "R"], f"promotion targets wrong: {suffixes}"
    assert "K" not in suffixes and "N" not in suffixes, "must NOT promote to a (royal) knight"

    # ---- 7. castling exists (royal knight two-square jump + rook) --------
    # White royal knight e1 + h1 rook, empty f1/g1: king-side castle is "4,0>6,0".
    cast = board_from({(4, 0): (WHITE, "K"), (7, 0): (WHITE, "R"),
                       (4, 7): (BLACK, "K")}, to_move=WHITE, castling="K")
    castle_mv = "4,0>6,0"
    assert castle_mv in g.legal_moves(cast), "king-side castling should be legal"
    castled = g.apply_move(cast, castle_mv)
    assert castled.board[(6, 0)] == (WHITE, "K"), "royal knight should land on g1 after O-O"
    assert castled.board[(5, 0)] == (WHITE, "R"), "rook should land on f1 after O-O"
    assert (4, 0) not in castled.board and (7, 0) not in castled.board

    # a (2,1) knight leap from the home square must NOT be mistaken for a castle:
    leap = board_from({(4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")}, to_move=WHITE)
    nb = g.apply_move(leap, "4,0>6,1")     # e1 -> g2, a genuine knight move
    assert nb.board.get((6, 1)) == (WHITE, "K"), "knight leap e1->g2 should just move the knight"
    assert (7, 0) not in nb.board, "knight leap must NOT trigger a phantom rook move"

    # ---- serialize round-trip --------------------------------------------
    st = g.initial_state()
    st = g.apply_move(st, g.legal_moves(st)[0])
    again = g.deserialize(g.serialize(st))
    assert again.board == st.board and again.to_move == st.to_move
    assert again.castling == st.castling

    print("SELFTEST OK")
    print(f"opening legal moves = {len(g.legal_moves(s0))}")
    shown = (1, 2, 3, 4) if deep else (1, 2, 3)
    print("opening perft:", {d: PERFT[d] for d in shown})


if __name__ == "__main__":
    # Direct run does the full depth-4 perft freeze; the suite imports main().
    main(deep=True)
    sys.exit(0)
