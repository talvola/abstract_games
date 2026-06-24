"""Standalone self-test for Cylinder Chess (pure stdlib).

Run from the engine dir with:
    PYTHONPATH=. python3 games/cylinder_chess/selftest.py

Asserts:
  * the FROZEN, engine-derived opening perft 20 / 392 / 9162 at depths 1/2/3
    (d1 is exactly 20 -- identical to standard chess, because in the *opening*
    the back rank is full and no slider/leaper actually wraps onto a new square;
    the wrap geometry diverges only deeper, hence d2/d3 differ from chess's
    400 / 8902);
  * the opening legal moves are byte-for-byte standard chess;
  * a rook on an empty rank wraps to the FAR file (a4 reaches h4), reaching each
    of the other 7 files exactly once (no duplicate from the two horizontal
    rays) and NOT revisiting its own square;
  * a bishop wraps diagonally; a knight on the a-file reaches the h-file by wrap;
  * a wrapped ray STOPS at the first blocker (no bypass);
  * check works AROUND the cylinder (a rook gives check via the wrap), and a
    lone rook does not "attack itself" by looping the whole board;
  * serialize round-trips.

Prints "SELFTEST OK" and exits 0 on success, nonzero on any failure.
"""

import sys
import os
import importlib.util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.chesslike import CState, WHITE, BLACK  # noqa: E402

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("cyl_game", os.path.join(_here, "game.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
CylinderChess = _mod.CylinderChess

_cspec = importlib.util.spec_from_file_location(
    "ref_chess", os.path.join(_here, "..", "chess", "game.py"))
_cmod = importlib.util.module_from_spec(_cspec)
_cspec.loader.exec_module(_cmod)
Chess = _cmod.Chess


def perft(game, state, depth):
    if depth == 0:
        return 1
    return sum(perft(game, game.apply_move(state, m), depth - 1)
               for m in game.legal_moves(state))


def mk(g, board, to_move=WHITE):
    return CState(board=dict(board), to_move=to_move, castling=frozenset(), ep=None,
                  reps={g._poskey(board, to_move, frozenset(), None): 1})


def main():
    g = CylinderChess()
    ref = Chess()

    # --- Anchor 1: FROZEN engine-derived opening perft. ----------------------
    s0 = g.initial_state()
    expected = {1: 20, 2: 392, 3: 9162}        # engine-derived (cylinder wrap)
    for d, want in expected.items():
        got = perft(g, s0, d)
        assert got == want, f"perft({d}) = {got}, expected {want}"
    print(f"perft 20/392/9162 matched (got "
          f"{perft(g, s0, 1)}/{perft(g, s0, 2)}/{perft(g, s0, 3)})")

    # --- Anchor 1b: opening legal moves identical to standard chess. ---------
    assert sorted(g.legal_moves(s0)) == sorted(ref.legal_moves(ref.initial_state())), \
        "opening legal moves should equal standard chess (no wrap in the opening)"
    assert not g.is_terminal(s0)

    # --- Anchor 2: rook on an empty rank wraps to the far file. --------------
    b = {(0, 3): (WHITE, "R"), (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")}
    dests = [t for f, t in g._legal(mk(g, b)) if f == (0, 3)]
    rank3 = sorted(d for d in dests if d[1] == 3)
    assert (7, 3) in rank3, "rook a4 must wrap left to h4 (7,3)"
    assert rank3 == [(c, 3) for c in range(1, 8)], \
        f"rook a4 must reach each other file once, got {rank3}"
    assert len(dests) == len(set(dests)), "rook moves must not be duplicated by the two rays"
    assert (0, 3) not in dests, "rook must not loop back onto its own square"

    # --- Anchor 3: bishop wraps diagonally; knight a-file reaches h-file. -----
    bb = {(0, 3): (WHITE, "B"), (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")}
    bd = {t for f, t in g._legal(mk(g, bb)) if f == (0, 3)}
    assert (7, 4) in bd and (7, 2) in bd, "bishop a4 must wrap diagonally to the h-file"
    bn = {(0, 3): (WHITE, "N"), (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")}
    nd = {t for f, t in g._legal(mk(g, bn)) if f == (0, 3)}
    assert any(d[0] == 7 for d in nd), "knight a4 must reach the h-file (col 7) by wrap"

    # --- Anchor 4: a wrapped ray stops at the first blocker. -----------------
    # Box the a4 rook on its rank with enemy pawns at c4 (reached going right)
    # and g4 (reached going left -- via the wrap). It may capture either blocker
    # but the three squares BEHIND them (d4/e4/f4) are unreachable: the wrap does
    # not let it pass through a blocker.
    bk = {(0, 3): (WHITE, "R"), (2, 3): (BLACK, "P"), (6, 3): (BLACK, "P"),
          (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")}
    dk = {t for f, t in g._legal(mk(g, bk)) if f == (0, 3)}
    assert (2, 3) in dk and (6, 3) in dk, "wrapped rook must capture both blockers"
    assert (1, 3) in dk and (7, 3) in dk, "rook reaches b4 (right) and h4 (left wrap)"
    for blocked in [(3, 3), (4, 3), (5, 3)]:
        assert blocked not in dk, f"wrapped rook must not pass through a blocker to {blocked}"

    # --- Anchor 5: check around the cylinder; no self-attack loop. ------------
    chk = {(7, 3): (WHITE, "R"), (0, 3): (BLACK, "K"), (4, 0): (WHITE, "K")}
    assert g.in_check(chk, BLACK), "rook on h4 must check the black king on a4 via the wrap"
    anti = {(0, 3): (WHITE, "R"), (4, 3): (BLACK, "K"), (4, 0): (WHITE, "K")}
    assert g.in_check(anti, BLACK), "rook must check an antipodal king via the wrap"
    lone = {(0, 3): (WHITE, "R"), (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")}
    assert not g.attacked(lone, 0, 3, WHITE), \
        "a lone rook must not 'attack' its own square by looping the whole board"

    # --- Anchor 6: serialize round-trips. ------------------------------------
    rt = g.deserialize(g.serialize(s0))
    assert g.serialize(rt) == g.serialize(s0), "serialize must round-trip"

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"SELFTEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
