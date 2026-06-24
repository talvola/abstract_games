"""Standalone correctness anchor for Legan Chess (pure stdlib).

Asserts the exact canonical starting position, the Legan pawn move/capture
geometry for both colours, the enemy-corner promotion zone, the absence of
castling, a simple checkmate, a serialize round-trip, and an engine-derived,
frozen opening perft (d1/d2/d3 -- there is no published Legan perft, so these
are derived from this move generator and frozen as a regression guard).

Run directly (``python3 selftest.py``) or via ``tests/test_games.py``.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from agp.chesslike import CState, WHITE, BLACK
from games.legan_chess.game import LeganChess


def _moves(g, s):
    return {m.split("=")[0] for m in g.legal_moves(s)}


def main():
    g = LeganChess()
    s0 = g.initial_state()
    b = s0.board

    # --- exact canonical starting position -------------------------------- #
    expect = {
        # White (corner h1)
        (7, 0): (WHITE, "K"), (6, 1): (WHITE, "Q"),
        (5, 0): (WHITE, "B"), (7, 1): (WHITE, "B"),
        (6, 0): (WHITE, "N"), (7, 2): (WHITE, "N"),
        (4, 0): (WHITE, "R"), (7, 3): (WHITE, "R"),
        (3, 0): (WHITE, "P"), (4, 1): (WHITE, "P"), (4, 3): (WHITE, "P"),
        (5, 1): (WHITE, "P"), (5, 2): (WHITE, "P"), (6, 2): (WHITE, "P"),
        (6, 3): (WHITE, "P"), (7, 4): (WHITE, "P"),
        # Black (corner a8) -- 180-degree rotation of White
        (0, 7): (BLACK, "K"), (1, 6): (BLACK, "Q"),
        (2, 7): (BLACK, "B"), (0, 6): (BLACK, "B"),
        (1, 7): (BLACK, "N"), (0, 5): (BLACK, "N"),
        (3, 7): (BLACK, "R"), (0, 4): (BLACK, "R"),
        (4, 7): (BLACK, "P"), (3, 6): (BLACK, "P"), (3, 4): (BLACK, "P"),
        (2, 6): (BLACK, "P"), (2, 5): (BLACK, "P"), (1, 5): (BLACK, "P"),
        (1, 4): (BLACK, "P"), (0, 3): (BLACK, "P"),
    }
    assert b == expect, "starting position mismatch"

    # --- Legan pawn geometry: WHITE moves up-left, captures left/up -------- #
    # White pawn on f3=(5,2): step e4=(4,3); captures e3=(4,2) or f4=(5,3).
    wb = {(5, 2): (WHITE, "P"), (4, 2): (BLACK, "P"), (5, 3): (BLACK, "P"),
          (7, 0): (WHITE, "K"), (0, 7): (BLACK, "K")}
    wm = _moves(g, CState(board=wb, to_move=WHITE))
    assert "5,2>4,3" in wm, "white pawn diagonal move (toward a8) missing"
    assert "5,2>4,2" in wm and "5,2>5,3" in wm, "white pawn orthogonal captures missing"
    # The diagonal step is a non-capturing move only: blocked by any occupant.
    wb2 = dict(wb); wb2[(4, 3)] = (BLACK, "P")
    assert "5,2>4,3" not in _moves(g, CState(board=wb2, to_move=WHITE)), \
        "white pawn must not 'capture' on its diagonal move square"

    # BLACK moves down-right, captures right/down.
    bb = {(2, 5): (BLACK, "P"), (3, 5): (WHITE, "P"), (2, 4): (WHITE, "P"),
          (7, 0): (WHITE, "K"), (0, 7): (BLACK, "K")}
    bm = _moves(g, CState(board=bb, to_move=BLACK))
    assert "2,5>3,4" in bm, "black pawn diagonal move (toward h1) missing"
    assert "2,5>3,5" in bm and "2,5>2,4" in bm, "black pawn orthogonal captures missing"

    # --- pawn attack / check (it attacks its capture squares) ------------- #
    chk = {(5, 2): (WHITE, "P"), (4, 2): (BLACK, "K"), (7, 0): (WHITE, "K")}
    assert g.in_check(chk, BLACK), "white pawn should give check on its capture square"
    nochk = {(5, 2): (WHITE, "P"), (3, 2): (BLACK, "K"), (7, 0): (WHITE, "K")}
    assert not g.in_check(nochk, BLACK), "false check from pawn"

    # --- promotion at the enemy-corner edges ------------------------------ #
    # White promotes on the a-file (col 0) OR the 8th rank (row 7).
    pr_a = g.legal_moves(CState(board={(1, 1): (WHITE, "P"), (7, 0): (WHITE, "K"),
                                       (0, 7): (BLACK, "K")}, to_move=WHITE))
    assert set(m for m in pr_a if m.startswith("1,1")) == \
        {"1,1>0,2=Q", "1,1>0,2=R", "1,1>0,2=B", "1,1>0,2=N"}, "white a-file promotion"
    pr_8 = g.legal_moves(CState(board={(2, 6): (WHITE, "P"), (7, 0): (WHITE, "K"),
                                       (0, 7): (BLACK, "K")}, to_move=WHITE))
    assert any(m.endswith("=Q") for m in pr_8 if m.startswith("2,6")), "white 8th-rank promotion"
    # A non-edge advance does NOT promote.
    npr = g.legal_moves(CState(board={(5, 2): (WHITE, "P"), (7, 0): (WHITE, "K"),
                                      (0, 7): (BLACK, "K")}, to_move=WHITE))
    assert "5,2>4,3" in npr and not any("=" in m for m in npr if m.startswith("5,2")), \
        "interior advance must not promote"

    # --- no castling ------------------------------------------------------ #
    assert s0.castling == frozenset(), "no castling rights"
    assert not any(g.describe_move(s0, m).startswith("O-O") for m in g.legal_moves(s0)), \
        "no castling move should ever be generated"

    # --- a simple checkmate (Black king cornered at a8) ------------------- #
    mate = {(0, 7): (BLACK, "K"), (0, 6): (WHITE, "Q"), (0, 0): (WHITE, "R"),
            (7, 0): (WHITE, "K")}
    sm = CState(board=mate, to_move=BLACK)
    assert g.in_check(mate, BLACK) and g.legal_moves(sm) == [] and g.is_terminal(sm)
    assert g.returns(sm) == [1.0, -1.0], "checkmate should be a White win"

    # --- serialize round-trip --------------------------------------------- #
    rt = g.deserialize(json.loads(json.dumps(g.serialize(s0))))
    assert rt.board == s0.board and rt.to_move == s0.to_move, "serialize round-trip"

    # --- frozen, engine-derived opening perft ----------------------------- #
    def perft(state, depth):
        if depth == 0:
            return 1
        return sum(perft(g.apply_move(state, m), depth - 1) for m in g.legal_moves(state))

    d1 = len(g.legal_moves(s0))
    assert d1 == 8, f"opening d1 expected 8, got {d1}"
    assert perft(s0, 2) == 64, "opening perft d2"
    assert perft(s0, 3) == 724, "opening perft d3"

    print("SELFTEST OK  (legan_chess: setup, pawn geometry, promotion, no-castle, "
          "mate, serialize; perft d1=8 d2=64 d3=724)")


if __name__ == "__main__":
    main()
