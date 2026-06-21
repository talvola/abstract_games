"""Standalone self-test for King of the Hill.

Run from the engine dir with:  PYTHONPATH=. python3 games/king_of_the_hill/selftest.py

Asserts:
  * the correctness anchor -- chess opening perft 20 / 400 / 8902 at depths
    1/2/3 (the legal moves must be byte-for-byte identical to standard chess);
  * the centre-king win (a king legally reaching d4/d5/e4/e5 ends the game and
    wins for that side, and the result is correct for both colours);
  * the win does NOT fire spuriously from the opening, and ordinary chess
    checkmate / stalemate / draws still resolve correctly.

Prints "SELFTEST OK" and exits 0 on success, nonzero on any failure.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.chesslike import CState, WHITE, BLACK  # noqa: E402

import importlib.util  # noqa: E402

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("koth_game", os.path.join(_here, "game.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
KingOfTheHill = _mod.KingOfTheHill

# Standard chess, for the "moves identical to chess" cross-check.
_cspec = importlib.util.spec_from_file_location(
    "ref_chess", os.path.join(_here, "..", "chess", "game.py"))
_cmod = importlib.util.module_from_spec(_cspec)
_cspec.loader.exec_module(_cmod)
Chess = _cmod.Chess


def perft(game, state, depth):
    if depth == 0:
        return 1
    total = 0
    for mv in game.legal_moves(state):
        total += perft(game, game.apply_move(state, mv), depth - 1)
    return total


def main():
    g = KingOfTheHill()
    ref = Chess()

    # --- Anchor 1: opening perft must be exactly 20 / 400 / 8902. -------------
    s0 = g.initial_state()
    expected = {1: 20, 2: 400, 3: 8902}
    for d, want in expected.items():
        got = perft(g, s0, d)
        assert got == want, f"perft({d}) = {got}, expected {want}"
    print(f"perft 20/400/8902 matched (got "
          f"{perft(g, s0, 1)}/{perft(g, s0, 2)}/{perft(g, s0, 3)})")

    # --- Anchor 1b: legal moves identical to standard chess at the root. -----
    assert sorted(g.legal_moves(s0)) == sorted(ref.legal_moves(ref.initial_state())), \
        "opening legal moves differ from standard chess"
    # And one ply deep, for every reply.
    for mv in g.legal_moves(s0):
        ks = g.apply_move(s0, mv)
        cs = ref.apply_move(ref.initial_state(), mv)
        assert sorted(g.legal_moves(ks)) == sorted(ref.legal_moves(cs)), \
            f"legal moves diverge from chess after {mv}"

    # The opening is NOT terminal and nobody has won.
    assert not g.is_terminal(s0), "opening should not be terminal"

    # --- Anchor 2: a king legally reaching a central square wins. ------------
    # White king on e3 (4,2), black king far away. Ke3-e4 puts the king on the
    # hill (e4 = (4,3)). The move is a legal, non-self-check king step. (A
    # spare white pawn keeps it off the insufficient-material draw.)
    b = {(4, 2): (WHITE, "K"), (0, 7): (BLACK, "K"), (0, 1): (WHITE, "P")}
    st = CState(board=dict(b), to_move=WHITE, castling=frozenset(), ep=None,
                reps={g._poskey(b, WHITE, frozenset(), None): 1})
    assert not g.is_terminal(st), "pre-hill position should not be terminal yet"
    assert "4,2>4,3" in g.legal_moves(st), "Ke3-e4 should be legal"
    after = g.apply_move(st, "4,2>4,3")
    assert g.is_terminal(after), "king reaching e4 must end the game"
    assert g.returns(after) == [1.0, -1.0], \
        f"White king on the hill must win for White, got {g.returns(after)}"

    # Same for Black: black king e6 (4,5) -> e5 (4,4) is on the hill.
    b2 = {(4, 5): (BLACK, "K"), (0, 0): (WHITE, "K"), (7, 6): (BLACK, "P")}
    st2 = CState(board=dict(b2), to_move=BLACK, castling=frozenset(), ep=None,
                 reps={g._poskey(b2, BLACK, frozenset(), None): 1})
    assert "4,5>4,4" in g.legal_moves(st2), "Ke6-e5 should be legal for Black"
    after2 = g.apply_move(st2, "4,5>4,4")
    assert g.is_terminal(after2), "black king reaching e5 must end the game"
    assert g.returns(after2) == [-1.0, 1.0], \
        f"Black king on the hill must win for Black, got {g.returns(after2)}"

    # --- The hill win must NOT let a king move INTO check. -------------------
    # White king d3 (3,2); black rook on e1 (4,0) guards the e-file. Kd3-e4
    # ((4,3), on the hill) would step onto a square attacked by the rook, so it
    # must be ILLEGAL -- you cannot win by moving into check.
    b3 = {(3, 2): (WHITE, "K"), (4, 0): (BLACK, "R"), (0, 7): (BLACK, "K")}
    st3 = CState(board=dict(b3), to_move=WHITE, castling=frozenset(), ep=None,
                 reps={g._poskey(b3, WHITE, frozenset(), None): 1})
    assert "3,2>4,3" not in g.legal_moves(st3), \
        "king must not be able to move into check to reach the hill"
    # But the OTHER hill square d4 ((3,3)) is safe -> legal and winning.
    assert "3,2>3,3" in g.legal_moves(st3), "Kd3-d4 (safe hill square) should be legal"
    won = g.apply_move(st3, "3,2>3,3")
    assert g.is_terminal(won) and g.returns(won) == [1.0, -1.0]

    # --- Checkmate still wins (back-rank mate, no king near the hill). -------
    # Black: Kg8 (6,7) boxed by own pawns f7/g7/h7; White Rook delivers mate on
    # the 8th rank from a8 (0,7) with the king's escape squares covered by pawns.
    bm = {
        (6, 7): (BLACK, "K"),
        (5, 6): (BLACK, "P"), (6, 6): (BLACK, "P"), (7, 6): (BLACK, "P"),
        (0, 7): (WHITE, "R"),
        (4, 0): (WHITE, "K"),
    }
    sm = CState(board=dict(bm), to_move=BLACK, castling=frozenset(), ep=None,
                reps={g._poskey(bm, BLACK, frozenset(), None): 1})
    assert g.in_check(sm.board, BLACK), "black king should be in check"
    assert g.is_terminal(sm), "back-rank position should be checkmate (terminal)"
    assert g.returns(sm) == [1.0, -1.0], \
        f"checkmate of Black must win for White, got {g.returns(sm)}"

    # --- Stalemate is still a draw. -----------------------------------------
    # Classic: Black Kh8 (7,7), White Qf7 (5,6) controlling escape, White Kf6
    # (5,5). Black to move, not in check, no legal move -> stalemate.
    bs = {(7, 7): (BLACK, "K"), (5, 6): (WHITE, "Q"), (5, 5): (WHITE, "K")}
    ss = CState(board=dict(bs), to_move=BLACK, castling=frozenset(), ep=None,
                reps={g._poskey(bs, BLACK, frozenset(), None): 1})
    assert not g.in_check(ss.board, BLACK), "stalemate: black not in check"
    assert g.legal_moves(ss) == [], "stalemate: black has no legal move"
    assert g.is_terminal(ss) and g.returns(ss) == [0.0, 0.0], \
        f"stalemate must be a draw, got {g.returns(ss)}"

    # --- serialize round-trips through a centre-win position. ----------------
    rt = g.deserialize(g.serialize(after))
    assert g.serialize(rt) == g.serialize(after), "serialize must round-trip"
    assert g.is_terminal(rt) and g.returns(rt) == [1.0, -1.0]

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"SELFTEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
