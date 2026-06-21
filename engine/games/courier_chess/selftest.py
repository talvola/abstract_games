#!/usr/bin/env python3
"""Standalone correctness anchor for Courier Chess.

Run from the engine root with::

    PYTHONPATH=. python3 games/courier_chess/selftest.py

Asserts:
  * a self-computed perft regression baseline from the opening position
    (no published Courier perft exists; these are our own reproducible
    node counts and must stay stable across refactors);
  * the movement of each unusual piece -- Courier (= modern bishop),
    Ferz/Queen (one-step diagonal), Wazir/Schleich (one-step orthogonal),
    Alfil/Bishop ((2,2) leaper), and Mann/Sage (king's move, NOT royal);
  * that the Mann is not subject to check (only the King is royal);
  * a forced checkmate position.

Prints "SELFTEST OK" and exits 0 on success, nonzero on any failure.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import CourierChess  # noqa: E402
from agp.chesslike import CState, WHITE, BLACK  # noqa: E402

G = CourierChess()


def fail(msg: str):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def perft(state, depth: int) -> int:
    if depth == 0:
        return 1
    n = 0
    for m in G.legal_moves(state):
        n += perft(G.apply_move(state, m), depth - 1)
    return n


def state_from(pieces: dict, to_move=WHITE) -> CState:
    """Build a bare position: ``pieces`` maps (col,row) -> (player, letter)."""
    board = dict(pieces)
    return CState(board=board, to_move=to_move, castling=frozenset(), ep=None,
                  reps={G._poskey(board, to_move, frozenset(), None): 1})


def targets(state, src):
    """Set of destination cells the piece on ``src`` can legally move to.

    Uses the engine's king-safety-filtered move generator (``_legal``)
    directly, so it is not short-circuited by the insufficient-material /
    draw gate -- these are deliberately sparse test positions.
    """
    return {to for (frm, to) in G._legal(state) if frm == src}


# --------------------------------------------------------------------------- #
# 1. Board geometry & opening array
# --------------------------------------------------------------------------- #
def test_setup():
    s = G.initial_state()
    if (G.WIDTH, G.HEIGHT) != (12, 8):
        fail(f"board must be 12x8, got {G.WIDTH}x{G.HEIGHT}")
    # 12 back-rank pieces + 12 pawns per side -> 48 pieces total.
    if len(s.board) != (12 + 12) * 2:
        fail(f"expected 48 pieces at start, got {len(s.board)}")
    # White King on e1 (col 4, row 0); Black King mirrored on h8 (col 7, row 7).
    if s.board.get((4, 0)) != (WHITE, "K"):
        fail("White King not on e1 (col 4, row 0)")
    if s.board.get((7, 7)) != (BLACK, "K"):
        fail("Black King not on h8 (col 7, row 7)")
    # Couriers (modern bishops) on d1/i1 for White.
    if s.board.get((3, 0)) != (WHITE, "C") or s.board.get((8, 0)) != (WHITE, "C"):
        fail("White Couriers not on d1/i1")
    # Pawns on the third rank (row 2 / row 5).
    for c in range(12):
        if s.board.get((c, 2)) != (WHITE, "P"):
            fail(f"White pawn missing on col {c}, row 2")
        if s.board.get((c, 5)) != (BLACK, "P"):
            fail(f"Black pawn missing on col {c}, row 5")


# --------------------------------------------------------------------------- #
# 2. Perft regression baseline (self-computed, reproducible)
# --------------------------------------------------------------------------- #
def test_perft():
    s = G.initial_state()
    expected = {1: 29, 2: 841, 3: 25561}
    for d, want in expected.items():
        got = perft(s, d)
        if got != want:
            fail(f"perft({d}) = {got}, expected {want}")


# --------------------------------------------------------------------------- #
# 3. The Courier moves exactly like a modern bishop (diagonal slider)
# --------------------------------------------------------------------------- #
def test_courier_is_bishop():
    # Lone Courier on e4 (col 4, row 3) on an otherwise empty board (+ kings).
    s = state_from({
        (4, 3): (WHITE, "C"),
        (0, 0): (WHITE, "K"),
        (11, 7): (BLACK, "K"),
    })
    t = targets(s, (4, 3))
    # All four diagonals to the board edge.
    expect = set()
    for dc, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        c, r = 4 + dc, 3 + dr
        while 0 <= c < 12 and 0 <= r < 8:
            expect.add((c, r))
            c += dc
            r += dr
    if t != expect:
        fail(f"Courier diagonal reach wrong: {sorted(t)} != {sorted(expect)}")
    # It must NOT move orthogonally.
    if any(c == 4 or r == 3 for (c, r) in t):
        fail("Courier moved orthogonally (should be a pure diagonal slider)")
    # It must be a SLIDER (reaches a far square), not a one-step Ferz.
    if (0, 7) not in t:
        fail("Courier failed to slide to a far diagonal square (a8/col0,row7)")
    # And it is blocked by an intervening piece (cannot jump).
    s2 = state_from({
        (4, 3): (WHITE, "C"),
        (6, 5): (BLACK, "P"),     # blocker on the up-right diagonal
        (0, 0): (WHITE, "K"),
        (11, 7): (BLACK, "K"),
    })
    t2 = targets(s2, (4, 3))
    if (6, 5) not in t2:
        fail("Courier should capture the blocker on (6,5)")
    if (7, 6) in t2:
        fail("Courier jumped past a blocker (must be a slider)")


# --------------------------------------------------------------------------- #
# 4. Ferz / Queen: one step diagonally only
# --------------------------------------------------------------------------- #
def test_ferz():
    s = state_from({
        (4, 3): (WHITE, "F"),
        (0, 0): (WHITE, "K"),
        (11, 7): (BLACK, "K"),
    })
    t = targets(s, (4, 3))
    expect = {(5, 4), (3, 4), (5, 2), (3, 2)}
    if t != expect:
        fail(f"Ferz one-step-diagonal wrong: {sorted(t)} != {sorted(expect)}")


# --------------------------------------------------------------------------- #
# 5. Wazir / Schleich: one step orthogonally only
# --------------------------------------------------------------------------- #
def test_wazir():
    s = state_from({
        (4, 3): (WHITE, "W"),
        (0, 0): (WHITE, "K"),
        (11, 7): (BLACK, "K"),
    })
    t = targets(s, (4, 3))
    expect = {(5, 3), (3, 3), (4, 4), (4, 2)}
    if t != expect:
        fail(f"Wazir one-step-orthogonal wrong: {sorted(t)} != {sorted(expect)}")


# --------------------------------------------------------------------------- #
# 6. Alfil / Bishop: the Shatranj (2,2) leaper
# --------------------------------------------------------------------------- #
def test_alfil():
    s = state_from({
        (4, 3): (WHITE, "A"),
        (5, 4): (BLACK, "P"),     # adjacent diagonal -- must be JUMPED over
        (0, 0): (WHITE, "K"),
        (11, 7): (BLACK, "K"),
    })
    t = targets(s, (4, 3))
    expect = {(6, 5), (2, 5), (6, 1), (2, 1)}
    if t != expect:
        fail(f"Alfil (2,2)-leap wrong: {sorted(t)} != {sorted(expect)}")
    # It leaps OVER the adjacent piece (does not capture or stop on it).
    if (5, 4) in t:
        fail("Alfil should leap over (not land on) the adjacent (5,4) piece")


# --------------------------------------------------------------------------- #
# 7. Mann / Sage: moves like a king but is NOT royal
# --------------------------------------------------------------------------- #
def test_mann():
    # Movement: all 8 one-step directions.
    s = state_from({
        (4, 3): (WHITE, "M"),
        (0, 0): (WHITE, "K"),
        (11, 7): (BLACK, "K"),
    })
    t = targets(s, (4, 3))
    expect = {(c, r) for c in (3, 4, 5) for r in (2, 3, 4)} - {(4, 3)}
    if t != expect:
        fail(f"Mann king-move wrong: {sorted(t)} != {sorted(expect)}")

    # NON-royal: a Mann attacked by an enemy slider is NOT 'in check'; the side
    # is free to make any legal move (including leaving the Mann en prise).
    s2 = state_from({
        (4, 3): (WHITE, "M"),     # Mann attacked along the rank...
        (0, 3): (BLACK, "R"),     # ...by this rook
        (5, 0): (WHITE, "K"),     # King is safe and has moves
        (11, 7): (BLACK, "K"),
    }, to_move=WHITE)
    if G.in_check(s2.board, WHITE):
        fail("Mann attack registered as check (Mann must not be royal)")
    # The Mann may even stay put while another piece moves: King moves exist.
    if not any(m.startswith("5,0>") for m in G.legal_moves(s2)):
        fail("King should have legal moves while Mann is merely attacked")
    # And the only royal piece is the King: putting the King in a rook's line
    # WITH no escape/block must be check (sanity that check still works).
    s3 = state_from({
        (4, 3): (WHITE, "K"),
        (0, 3): (BLACK, "R"),
        (11, 7): (BLACK, "K"),
    }, to_move=WHITE)
    if not G.in_check(s3.board, WHITE):
        fail("King on a rook's line should be in check")


# --------------------------------------------------------------------------- #
# 8. Pawns: single step only, promote to Ferz on the last rank
# --------------------------------------------------------------------------- #
def test_pawns():
    s = G.initial_state()
    # No double step: a home pawn (col 0, row 2) reaches only row 3.
    t = targets(s, (0, 2))
    if t != {(0, 3)}:
        fail(f"home pawn should have only the single step, got {sorted(t)}")

    # Promotion: a White pawn on row 6 stepping to row 7 must promote to F.
    s2 = state_from({
        (5, 6): (WHITE, "P"),
        (0, 0): (WHITE, "K"),
        (11, 0): (BLACK, "K"),
    }, to_move=WHITE)
    promo = [m for m in G.legal_moves(s2) if m.startswith("5,6>5,7")]
    if promo != ["5,6>5,7=F"]:
        fail(f"pawn should promote to Ferz only, got {promo}")
    after = G.apply_move(s2, "5,6>5,7=F")
    if after.board.get((5, 7)) != (WHITE, "F"):
        fail("promoted pawn is not a Ferz")


# --------------------------------------------------------------------------- #
# 9. A forced checkmate (back-rank mate by two Couriers + Rook support)
# --------------------------------------------------------------------------- #
def test_checkmate():
    # Classic back-rank mate.  Black King in the a8 corner (col 0, row 7); a
    # White Rook checks along the 8th rank from (11,7); the King's two forward
    # flight squares are sealed by its own pawns, the sideways square (1,7) is
    # covered by the same rook, and the rook is out of reach -- so checkmate.
    board = {
        (11, 7): (WHITE, "R"),    # checking rook on the back rank
        (0, 7): (BLACK, "K"),     # cornered Black king
        (0, 6): (BLACK, "P"),     # own pawn seals (0,6)
        (1, 6): (BLACK, "P"),     # own pawn seals (1,6)
        (0, 0): (WHITE, "K"),
    }
    s = state_from(board, to_move=BLACK)
    if not G.in_check(s.board, BLACK):
        fail("checkmate position: Black should be in check")
    if G.legal_moves(s):
        fail(f"checkmate position has legal moves: {G.legal_moves(s)}")
    if not G.is_terminal(s):
        fail("checkmate position should be terminal")
    if G.returns(s) != [1.0, -1.0]:
        fail(f"checkmate should be a White win, got {G.returns(s)}")


def main():
    test_setup()
    test_perft()
    test_courier_is_bishop()
    test_ferz()
    test_wazir()
    test_alfil()
    test_mann()
    test_pawns()
    test_checkmate()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
