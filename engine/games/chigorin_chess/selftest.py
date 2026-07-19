"""Self-test for Chigorin Chess (pure stdlib).

Anchors (all verified ONCE against Fairy-Stockfish's built-in ``chigorin``
variant via pyffish 0.0.89 -- see ``_diff_pyffish.py``, which also compared
7,135 random-game positions' full legal-move sets with zero mismatches):

  (a) perft(1..4) from the start position: 26 / 416 / 11408 / 229973;
  (b) perft(1..3) of a double-promotion position and a full-castling position;
  (c) promotion choice sets are per-army (White C/R/N only, Black Q/R/B only);
  (d) the orthodox fool's mate 1.f3 e5 2.g4 Qh4+ is NOT mate here (White's
      f1-Knight blocks on g3, the forced reply), and a Chancellor back-rank
      checkmate reached via apply_move;
  (e) random playouts terminate.

Run:  cd engine && PYTHONPATH=. python3 games/chigorin_chess/selftest.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir            # noqa: E402
from agp.chesslike import WHITE, BLACK          # noqa: E402

_, GAME = load_from_dir(Path(__file__).resolve().parent)


def perft(state, depth):
    if depth == 0:
        return 1
    return sum(perft(GAME.apply_move(state, m), depth - 1)
               for m in GAME.legal_moves(state))


# --------------------------------------------------------------------------- #
def test_setup():
    s = GAME.initial_state()
    b = s.board
    assert [b[(c, 0)][1] for c in range(8)] == ["R", "N", "N", "C", "K", "N", "N", "R"]
    assert [b[(c, 7)][1] for c in range(8)] == ["R", "B", "B", "Q", "K", "B", "B", "R"]
    assert all(b[(c, 1)] == (WHITE, "P") and b[(c, 6)] == (BLACK, "P")
               for c in range(8))
    assert len(b) == 32
    print("  setup OK (RNNCKNNR vs rbbqkbbr)")


def test_perft_start():
    # Fairy-Stockfish `chigorin` perft, frozen (pyffish 0.0.89).
    s = GAME.initial_state()
    expect = {1: 26, 2: 416, 3: 11408, 4: 229973}
    for d, n in expect.items():
        got = perft(s, d)
        assert got == n, f"start perft({d}): {got} != {n}"
    print(f"  start perft OK {expect}")


# FEN 1bbq1k2/P7/8/8/8/8/p6P/1NNC1K2 w - - 0 1  (both sides one step from promoting)
PROMO_STATE = {
    "board": {"1,7": [1, "B"], "2,7": [1, "B"], "3,7": [1, "Q"], "5,7": [1, "K"],
              "0,6": [0, "P"], "0,1": [1, "P"], "7,1": [0, "P"],
              "1,0": [0, "N"], "2,0": [0, "N"], "3,0": [0, "C"], "5,0": [0, "K"]},
    "to_move": 0, "castling": "", "ep": None, "halfmove": 0, "ply": 0, "reps": {},
}
# FEN r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1
CASTLE_STATE = {
    "board": dict(
        {f"{c},1": [0, "P"] for c in range(8)},
        **{f"{c},6": [1, "P"] for c in range(8)},
        **{"0,0": [0, "R"], "7,0": [0, "R"], "4,0": [0, "K"],
           "0,7": [1, "R"], "7,7": [1, "R"], "4,7": [1, "K"]}),
    "to_move": 0, "castling": "KQkq", "ep": None, "halfmove": 0, "ply": 0, "reps": {},
}


def test_perft_positions():
    s = GAME.deserialize(PROMO_STATE)
    for d, n in {1: 32, 2: 1108, 3: 32097}.items():
        got = perft(s, d)
        assert got == n, f"promo perft({d}): {got} != {n}"
    s = GAME.deserialize(CASTLE_STATE)
    for d, n in {1: 25, 2: 625, 3: 15206}.items():
        got = perft(s, d)
        assert got == n, f"castle perft({d}): {got} != {n}"
    print("  position perft OK (promo 32/1108/32097, castle 25/625/15206)")


def test_promotion_choices():
    s = GAME.deserialize(PROMO_STATE)
    wpro = [m for m in GAME.legal_moves(s) if m.startswith("0,6>")]
    # a7-a8 push + a7xb8 capture, each with exactly White's own army C/R/N.
    assert sorted(wpro) == sorted(
        [f"0,6>0,7={t}" for t in "CRN"] + [f"0,6>1,7={t}" for t in "CRN"]), wpro
    assert not any(m.endswith(("=Q", "=B")) for m in wpro)
    s2 = GAME.apply_move(s, "7,1>7,2")           # quiet White move: h2-h3
    bpro = [m for m in GAME.legal_moves(s2) if m.startswith("0,1>")]
    # a2-a1 push + a2xb1 capture, each with exactly Black's own army Q/R/B.
    assert sorted(bpro) == sorted(
        [f"0,1>0,0={t}" for t in "QRB"] + [f"0,1>1,0={t}" for t in "QRB"]), bpro
    assert not any(m.endswith(("=C", "=N")) for m in bpro)
    print("  promotion choices OK (White C/R/N, Black Q/R/B)")


def test_castling_moves():
    s = GAME.deserialize(CASTLE_STATE)
    ms = GAME.legal_moves(s)
    assert "4,0>6,0" in ms and "4,0>2,0" in ms          # O-O and O-O-O
    assert GAME.describe_move(s, "4,0>6,0") == "O-O"
    s2 = GAME.apply_move(s, "4,0>6,0")
    assert s2.board[(5, 0)] == (WHITE, "R") and s2.board[(6, 0)] == (WHITE, "K")
    ms2 = GAME.legal_moves(s2)
    assert "4,7>6,7" in ms2 and "4,7>2,7" in ms2
    print("  castling OK (both wings, both sides)")


def test_no_fools_mate():
    # 1.f3 e5 2.g4 Qh4+ is the orthodox fool's mate -- but NOT here: White's
    # f1-KNIGHT (a bishop in normal chess) blocks on g3, and the Chancellor
    # knight-leaps d1-f2 to block too.  A neat anchor of the army asymmetry.
    s = GAME.initial_state()
    for mv in ["5,1>5,2", "4,6>4,4", "6,1>6,3", "3,7>7,3"]:
        assert mv in GAME.legal_moves(s), mv
        s = GAME.apply_move(s, mv)
    assert not GAME.is_terminal(s)
    assert sorted(GAME.legal_moves(s)) == ["3,0>5,1", "5,0>6,2"]  # Cd1-f2, Nf1-g3
    print("  fool's mate refuted OK (Nf1-g3 / Cd1-f2 block)")


def test_chancellor_mate():
    # Back-rank mate delivered by the Chancellor: Ce2-e8#.  On e8 it rook-
    # attacks f8 (and h8 once the king unblocks) and knight-attacks g7.
    pre = {
        "board": {"6,7": [1, "K"], "5,6": [1, "P"], "6,6": [1, "P"], "7,6": [1, "P"],
                  "6,0": [0, "K"], "4,1": [0, "C"]},
        "to_move": 0, "castling": "", "ep": None,
        "halfmove": 0, "ply": 0, "reps": {},
    }
    s = GAME.deserialize(pre)
    assert "4,1>4,7" in GAME.legal_moves(s)
    s = GAME.apply_move(s, "4,1>4,7")
    assert GAME.is_terminal(s)
    assert GAME.returns(s) == [1.0, -1.0]
    print("  chancellor back-rank mate OK (White wins by checkmate)")


def test_playouts():
    rng = random.Random(7)
    results = []
    for _ in range(5):
        s = GAME.initial_state()
        while not GAME.is_terminal(s):
            s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
            assert s.ply <= GAME.PLY_CAP
        r = GAME.returns(s)
        assert len(r) == 2 and all(isinstance(x, float) for x in r)
        results.append(r)
    rt = GAME.deserialize(GAME.serialize(s))
    assert GAME.serialize(rt) == GAME.serialize(s)
    print(f"  playouts OK, results {results}")


if __name__ == "__main__":
    test_setup()
    test_perft_start()
    test_perft_positions()
    test_promotion_choices()
    test_castling_moves()
    test_no_fools_mate()
    test_chancellor_mate()
    test_playouts()
    print("chigorin_chess selftest: all tests passed")
