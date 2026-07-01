"""Standalone correctness self-test for Marseillais Chess (run from ``engine``):

    PYTHONPATH=. python3 games/marseillais_chess/selftest.py

Pure-stdlib (imports only ``agp`` + this game). Anchors:

  1. Balanced turn structure: White's first turn is a SINGLE move (moves_left=1)
     then flips to Black with moves_left=2.
  2. A normal turn is TWO moves: to_move stays after move 1, flips after move 2.
  3. Opening move counts (standard 20 for White, 20 for Black's first reply).
  4. Giving check ENDS the turn: a first move that gives check forfeits the
     second move (to_move flips even though moves_left was 2).
  5. Must escape check on the FIRST move: when in check, every legal move leaves
     the mover's king safe (and there is at least one).
  6. Own king never in check mid-turn: a pinned piece cannot make an exposing move.
  7. Checkmate reached via apply_move ⇒ the mating side wins (ordinary mate).
  8. En passant across a turn: a double-step on the FIRST sub-move is still
     capturable en passant by the opponent on the opponent's first sub-move.
  9. serialize / deserialize round-trips (incl. moves_left / ep_here / ep_pending).
 10. Random games terminate (PLY_CAP / draw rules hold).

Prints "SELFTEST OK" and exits 0 on success; raises on failure.
"""

import random
import sys

from games.marseillais_chess.game import MarseillaisChess, MState, WHITE, BLACK


def board_of(pairs):
    return {cr: (pl, t) for cr, (pl, t) in pairs.items()}


def main():
    g = MarseillaisChess()

    # --- 1. Balanced: White opens with ONE move ---------------------------
    s0 = g.initial_state()
    assert s0.to_move == WHITE and s0.moves_left == 1, (s0.to_move, s0.moves_left)
    # --- 3a. White opening = 20 legal moves -------------------------------
    assert len(g.legal_moves(s0)) == 20, len(g.legal_moves(s0))

    s1 = g.apply_move(s0, "4,1>4,3")            # 1. e4 (single, no check)
    assert s1.to_move == BLACK and s1.moves_left == 2, (s1.to_move, s1.moves_left)
    # --- 3b. Black's first reply = 20 -------------------------------------
    assert len(g.legal_moves(s1)) == 20, len(g.legal_moves(s1))

    # --- 2. A normal turn is two moves ------------------------------------
    s2 = g.apply_move(s1, "4,6>4,4")            # ...e5 (Black move 1, no check)
    assert s2.to_move == BLACK and s2.moves_left == 1, (s2.to_move, s2.moves_left)
    s3 = g.apply_move(s2, "3,6>3,5")            # ...d6 (Black move 2, no check)
    assert s3.to_move == WHITE and s3.moves_left == 2, (s3.to_move, s3.moves_left)

    # --- 4. Giving check ends the turn (forfeit the second move) ----------
    # White Ra1(h1) safe; White R e2 -> e7 checks Black K e8.
    chk = MState(board=board_of({
        (0, 0): (WHITE, "K"),
        (4, 1): (WHITE, "R"),
        (4, 7): (BLACK, "K"),
    }), to_move=WHITE, castling=frozenset(), ep=None, moves_left=2)
    assert "4,1>4,6" in g.legal_moves(chk)
    after = g.apply_move(chk, "4,1>4,6")        # gives check
    assert g.in_check(after.board, BLACK), "move should give check"
    assert after.to_move == BLACK, "check must end White's turn"
    assert after.moves_left == 2, after.moves_left

    # --- 5. Must escape check on the first move ---------------------------
    # White K e1 in check from Black R e8; Ng1 can block, king can step aside.
    inchk = MState(board=board_of({
        (4, 0): (WHITE, "K"),
        (6, 0): (WHITE, "N"),
        (4, 7): (BLACK, "R"),
        (7, 7): (BLACK, "K"),
    }), to_move=WHITE, castling=frozenset(), ep=None, moves_left=2)
    assert g.in_check(inchk.board, WHITE)
    lm = g.legal_moves(inchk)
    assert lm, "must have an escaping move"
    for m in lm:
        nb = g.apply_move(inchk, m).board
        assert not g.in_check(nb, WHITE), f"illegal: {m} leaves own king in check"
    assert "4,0>4,1" not in lm, "king cannot step onto attacked e2"

    # --- 6. Own king never in check mid-turn (pin) ------------------------
    pin = MState(board=board_of({
        (4, 0): (WHITE, "K"),
        (4, 1): (WHITE, "R"),          # pinned on the e-file
        (4, 7): (BLACK, "R"),
        (7, 7): (BLACK, "K"),
    }), to_move=WHITE, castling=frozenset(), ep=None, moves_left=2)
    assert not g.in_check(pin.board, WHITE)
    plm = g.legal_moves(pin)
    assert "4,1>3,1" not in plm, "pinned rook may not leave the file"
    assert "4,1>4,2" in plm, "rook may move along the pin"

    # --- 7. Checkmate via apply_move (ordinary mate) ----------------------
    matepos = MState(board=board_of({
        (0, 7): (BLACK, "K"),          # a8
        (0, 6): (BLACK, "P"),          # a7
        (1, 6): (BLACK, "P"),          # b7 (to be captured)
        (0, 5): (WHITE, "Q"),          # a6
        (1, 0): (WHITE, "R"),          # b1 defends b7
        (7, 0): (WHITE, "K"),          # h1
    }), to_move=WHITE, castling=frozenset(), ep=None, moves_left=2)
    assert not g.in_check(matepos.board, BLACK)
    assert "0,5>1,6" in g.legal_moves(matepos)
    mate = g.apply_move(matepos, "0,5>1,6")     # Qxb7#
    assert mate.to_move == BLACK
    assert g.in_check(mate.board, BLACK)
    assert g.legal_moves(mate) == [], "should be mate — no escape"
    assert g.is_terminal(mate)
    assert g.returns(mate) == [1.0, -1.0], g.returns(mate)

    # --- 8. En passant survives the double-stepper's own second move ------
    eppos = MState(board=board_of({
        (0, 0): (WHITE, "K"),
        (4, 4): (WHITE, "P"),          # e5
        (3, 6): (BLACK, "P"),          # d7 (will double-step on move 1)
        (7, 6): (BLACK, "P"),          # h7 (Black's harmless second move)
        (0, 7): (BLACK, "K"),
    }), to_move=BLACK, castling=frozenset(), ep=None, moves_left=2)
    e1 = g.apply_move(eppos, "3,6>3,4")         # ...d5 (double, Black move 1)
    assert e1.to_move == BLACK and e1.moves_left == 1
    assert e1.ep_pending and not e1.ep_here     # pending, not yet the opponent's
    e2 = g.apply_move(e1, "7,6>7,5")            # ...h6 (Black move 2) -> turn flips
    assert e2.to_move == WHITE and e2.moves_left == 2
    assert ((3, 5), (3, 4)) in e2.ep_here, e2.ep_here
    epmove = "4,4>3,5"
    assert epmove in g.legal_moves(e2), "en passant must be legal on White's first move"
    assert "e.p." in g.describe_move(e2, epmove)
    e3 = g.apply_move(e2, epmove)               # e5xd6 e.p.
    assert (3, 5) in e3.board and e3.board[(3, 5)] == (WHITE, "P")
    assert (3, 4) not in e3.board, "the double-stepped pawn must be removed"
    # After White's first move, ep_here is cleared (no ep on the second move).
    assert e3.to_move == WHITE and e3.ep_here == ()

    # --- 9. serialize / deserialize round-trip ----------------------------
    for st in (s0, s1, e1, e2, e3, mate):
        d = g.serialize(st)
        r = g.deserialize(d)
        assert r.board == st.board
        assert r.to_move == st.to_move
        assert r.moves_left == st.moves_left
        assert r.castling == st.castling
        assert r.ply == st.ply
        assert r.ep_here == st.ep_here
        assert r.ep_pending == st.ep_pending

    # --- 10. Random games terminate ---------------------------------------
    rng = random.Random(1234)
    for _ in range(6):
        s = g.initial_state()
        steps = 0
        while not g.is_terminal(s) and steps < 4000:
            s = g.apply_move(s, rng.choice(g.legal_moves(s)))
            steps += 1
        assert g.is_terminal(s), "random game did not terminate"

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
