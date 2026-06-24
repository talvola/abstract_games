"""Standalone correctness self-test for Spartan Chess (run from ``engine``):

    PYTHONPATH=. python3 games/spartan_chess/selftest.py

Pure-stdlib (imports only ``agp`` + this game).  It asserts:

  1. Setup: the verified opening array (Persian FIDE army; Spartan L G K C C K W L
     back rank + Hoplites), two Spartan Kings, White to move.
  2. Opening perft (engine-derived regression lock).  Depth 1 = 20 (the orthodox
     Persian opening); after any White move the Spartan always has 32 replies, so
     depth 2 = 20 * 32 = 640.
  3. Hoplite: diagonal-forward (non-capture) move, straight-forward capture, no
     straight non-capture, and its straight-ahead attack square.
  4. Captain (WD jump) and Lieutenant (FA diagonal jump + sideways non-capture).
  5. Two-King CHECK IMMUNITY: a Spartan King may step onto an attacked square
     while the other King is safe; a single attack on one of two Kings is not
     binding.
  6. DUPLE-CHECK & MATE reached via apply_move (White completes a simultaneous
     attack on BOTH Spartan Kings with no escape) -> Persians win.
  7. The Persian may CAPTURE a Spartan King (two -> one); the remaining lone King
     then reverts to an orthodox royal (ordinary check applies).
  8. Hoplite promotion: G/W/C/L always; King only when the Spartan has exactly one
     King in play (regaining a second King), verified via apply_move.
  9. Orthodox checkmate of the Persian King (a Spartan win) via apply_move.
 10. serialize / deserialize round-trips with two Spartan Kings + Spartan pieces.

Prints "SELFTEST OK" and exits 0 on success; raises on failure.
"""

import sys

from games.spartan_chess.game import SpartanChess, WHITE, BLACK
from agp.chesslike import CState


PERFT = {1: 20, 2: 640, 3: 14244}


def perft(g, state, depth):
    if depth == 0:
        return 1
    if g.is_terminal(state):
        return 0
    return sum(perft(g, g.apply_move(state, m), depth - 1)
               for m in g.legal_moves(state))


def st(pieces, to_move=WHITE, castling=""):
    return CState(board=dict(pieces), to_move=to_move,
                  castling=frozenset(castling), ep=None, reps={})


def n_kings(board, player):
    return len([1 for (_, (pl, t)) in board.items() if pl == player and t == "K"])


def main(deep=False):
    g = SpartanChess()
    s0 = g.initial_state()
    b = s0.board

    # ---- 1. setup -----------------------------------------------------------
    assert s0.to_move == WHITE, "Persians (White) move first"
    persian_back = ["R", "N", "B", "Q", "K", "B", "N", "R"]
    for c in range(8):
        assert b[(c, 0)] == (WHITE, persian_back[c]), f"Persian back rank file {c}"
        assert b[(c, 1)] == (WHITE, "P"), "Persian pawns on rank 2"
        assert b[(c, 6)] == (BLACK, "H"), "Hoplites on rank 7"
    spartan_back = ["L", "G", "K", "C", "C", "K", "W", "L"]
    for c in range(8):
        assert b[(c, 7)] == (BLACK, spartan_back[c]), f"Spartan back rank file {c}"
    assert b[(2, 7)] == (BLACK, "K") and b[(5, 7)] == (BLACK, "K"), "Spartan kings c8/f8"
    assert b[(1, 7)] == (BLACK, "G") and b[(6, 7)] == (BLACK, "W"), "General b8, Warlord g8"
    assert n_kings(b, BLACK) == 2 and n_kings(b, WHITE) == 1, "two Spartan kings, one Persian"

    # ---- 2. opening perft ---------------------------------------------------
    depths = (1, 2, 3) if deep else (1, 2)
    for d in depths:
        got = perft(g, s0, d)
        assert got == PERFT[d], f"perft({d}) = {got}, expected {PERFT[d]}"
    assert len(g.legal_moves(s0)) == 20, "Persian opening = 20 moves (orthodox)"

    # ---- 3. Hoplite ---------------------------------------------------------
    # Black Hoplite d5=(3,4) advancing toward row 0.
    hp = st({(3, 4): (BLACK, "H"), (3, 3): (WHITE, "P"), (4, 3): (WHITE, "N"),
             (2, 7): (BLACK, "K"), (5, 7): (BLACK, "K"), (7, 0): (WHITE, "K")}, BLACK)
    hm = {m for m in g.legal_moves(hp) if m.startswith("3,4>")}
    assert "3,4>3,3" in hm, "Hoplite captures STRAIGHT ahead (onto the enemy pawn)"
    assert "3,4>4,3" not in hm, "Hoplite may NOT capture diagonally (enemy on e4)"
    assert "3,4>2,3" in hm, "Hoplite moves one square diagonally forward (empty c4)"
    assert hm == {"3,4>3,3", "3,4>2,3"}, "Hoplite has no straight non-capture move"
    assert g.attacked({(4, 1): (BLACK, "H")}, 4, 0, BLACK), "Hoplite attacks square directly ahead"
    assert not g.attacked({(4, 1): (BLACK, "H")}, 3, 0, BLACK), "Hoplite does NOT attack diagonally"
    # First-move two-square diagonal jump (a7 Hoplite -> down-right 1 or 2).
    open_h = {m for m in g.legal_moves(st(dict(b), BLACK)) if m.startswith("0,6>")}
    assert open_h == {"0,6>1,5", "0,6>2,4"}, f"a7 Hoplite opening jumps: {open_h}"

    # ---- 4. Captain & Lieutenant -------------------------------------------
    cap = st({(3, 3): (BLACK, "C"), (2, 3): (BLACK, "H"),
              (2, 7): (BLACK, "K"), (5, 7): (BLACK, "K"), (7, 0): (WHITE, "K")}, BLACK)
    cm = {m for m in g.legal_moves(cap) if m.startswith("3,3>")}
    assert "3,3>1,3" in cm, "Captain jumps over a friendly piece to the 2nd square"
    assert "3,3>4,3" in cm and "3,3>5,3" in cm, "Captain moves 1 or 2 squares orthogonally"
    assert "3,3>2,3" not in cm, "Captain may not land on a friendly piece"

    lt = st({(3, 3): (BLACK, "L"), (2, 4): (BLACK, "H"),
             (2, 7): (BLACK, "K"), (5, 7): (BLACK, "K"), (7, 0): (WHITE, "K")}, BLACK)
    lm = {m for m in g.legal_moves(lt) if m.startswith("3,3>")}
    assert "3,3>1,5" in lm, "Lieutenant jumps over a friendly diagonal piece to the 2nd square"
    assert "3,3>4,3" in lm and "3,3>2,3" in lm, "Lieutenant steps one square sideways (non-capture)"
    lt2 = st({(3, 3): (BLACK, "L"), (4, 3): (WHITE, "P"),
              (2, 7): (BLACK, "K"), (5, 7): (BLACK, "K"), (7, 0): (WHITE, "K")}, BLACK)
    assert "3,3>4,3" not in {m for m in g.legal_moves(lt2) if m.startswith("3,3>")}, \
        "Lieutenant may NOT capture sideways"

    # ---- 5. two-King check immunity ----------------------------------------
    imm = st({(2, 7): (BLACK, "K"), (5, 7): (BLACK, "K"),
              (4, 5): (WHITE, "R"), (0, 0): (WHITE, "K")}, BLACK)
    assert not g._in_danger(imm.board, BLACK), "one of two kings attacked is NOT danger"
    assert "5,7>4,7" in set(g.legal_moves(imm)), \
        "a Spartan King MAY step onto an attacked square while the other King is safe"

    # ---- 6. duple-check & mate via apply_move ------------------------------
    pre = st({
        (1, 0): (WHITE, "R"),                                  # rook b1 (checks a1 king only)
        (2, 2): (WHITE, "N"), (1, 2): (WHITE, "N"), (3, 2): (WHITE, "N"),
        (1, 4): (WHITE, "N"),                                  # b5 knight -> a3 completes the mate
        (0, 0): (BLACK, "K"), (2, 0): (BLACK, "K"),
        (4, 4): (WHITE, "K"),
    }, WHITE)
    # The move Nb5-a3 seals the mate (defends b1 / covers the last escape square):
    # if Black could move from the pre-position it would still have escapes.
    assert len(g.legal_moves(st(dict(pre.board), BLACK))) > 0, "pre-mate: Spartan still has escapes"
    assert "1,4>0,2" in g.legal_moves(pre), "Nb5-a3 should be legal"
    post = g.apply_move(pre, "1,4>0,2")
    assert post.to_move == BLACK
    assert g._in_danger(post.board, BLACK), "BOTH Spartan kings now attacked (duple-check)"
    assert g.legal_moves(post) == [], "duple-check & mate: no Spartan move removes a king from attack"
    assert g.is_terminal(post) and g.returns(post) == [1.0, -1.0], "Persians win the duple-mate"
    assert "duple-check" in g.render(post)["caption"] or "Persians win" in g.render(post)["caption"]

    # ---- 7. Persian captures a Spartan King (two -> one) -------------------
    kc = st({(6, 6): (BLACK, "K"), (7, 7): (BLACK, "K"),
             (5, 5): (WHITE, "Q"), (7, 0): (WHITE, "K"), (6, 0): (WHITE, "R")}, WHITE)
    assert "5,5>6,6" in set(g.legal_moves(kc)), "Persian Queen may capture a Spartan King"
    after = g.apply_move(kc, "5,5>6,6")
    assert n_kings(after.board, BLACK) == 1, "one Spartan King remains"
    assert g._in_danger(after.board, BLACK), "the lone King now obeys orthodox check"

    # ---- 8. Hoplite promotion (regain a King) ------------------------------
    # Two kings -> NO promote-to-King option.
    two = st({(1, 1): (BLACK, "H"), (2, 7): (BLACK, "K"), (5, 7): (BLACK, "K"),
              (7, 4): (WHITE, "K")}, BLACK)
    pmoves = [m for m in g.legal_moves(two) if m.startswith("1,1>")]
    assert pmoves and not any("=K" in m for m in pmoves), "two kings: Hoplite may NOT promote to King"
    assert all(m.split("=")[1] in ("G", "W", "C", "L") for m in pmoves), "promo to G/W/C/L only"
    # One king -> promote-to-King allowed; apply it and confirm two kings result.
    one = st({(1, 1): (BLACK, "H"), (2, 7): (BLACK, "K"),
              (7, 4): (WHITE, "K"), (0, 5): (WHITE, "R")}, BLACK)
    one_moves = [m for m in g.legal_moves(one) if m.startswith("1,1>")]
    king_promo = [m for m in one_moves if m.endswith("=K")]
    assert king_promo, "one king: Hoplite MAY promote to a King"
    regained = g.apply_move(one, king_promo[0])
    assert n_kings(regained.board, BLACK) == 2, "promoting to a King regains the second King"

    # ---- 9. orthodox checkmate of the Persian (Spartan win) ----------------
    pm = st({(7, 0): (WHITE, "K"), (6, 1): (WHITE, "P"), (7, 1): (WHITE, "P"),
             (0, 3): (BLACK, "G"), (2, 7): (BLACK, "K"), (5, 7): (BLACK, "K")}, BLACK)
    assert "0,3>0,0" in g.legal_moves(pm), "General a4-a1 should be legal"
    mated = g.apply_move(pm, "0,3>0,0")
    assert g._in_danger(mated.board, WHITE), "Persian King is in check"
    assert g.legal_moves(mated) == [] and g.is_terminal(mated)
    assert g.returns(mated) == [-1.0, 1.0], "Spartans win the Persian checkmate"

    # ---- 10. serialize round-trip ------------------------------------------
    s = g.initial_state()
    for m in ["4,1>4,3", "0,6>1,5", "3,1>3,3", "6,7>5,5"]:
        s = g.apply_move(s, m)
    again = g.deserialize(g.serialize(s))
    assert again.board == s.board and again.to_move == s.to_move
    assert again.castling == s.castling and again.ep == s.ep
    assert n_kings(again.board, BLACK) == 2, "both Spartan kings survive the round-trip"

    print("SELFTEST OK")
    print(f"opening legal moves = {len(g.legal_moves(s0))} (Persians)")
    shown = (1, 2, 3) if deep else (1, 2)
    print("opening perft:", {d: PERFT[d] for d in shown})


if __name__ == "__main__":
    main(deep=True)
    sys.exit(0)
