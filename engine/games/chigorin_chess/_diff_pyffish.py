"""One-time differential of chigorin_chess against Fairy-Stockfish (pyffish).

NOT run by the test suite (needs pyffish from the repo .venv). Usage:

    cd engine && PYTHONPATH=. ../.venv/bin/python games/chigorin_chess/_diff_pyffish.py

Plays random games from the start position; at EVERY position compares our
full legal-move set (converted to UCI) with ``pyffish.legal_moves`` for the
built-in ``chigorin`` variant. Also cross-checks perft(1..4) from the start
position and from two hand-picked promotion/castling positions.

Our engine declares draws (50-move / threefold / insufficient material / ply
cap) by returning an empty legal-move list, which pyffish's raw move
generator does not; games simply stop there (positions compared up to that
point are still exact).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyffish as sf                            # noqa: E402
from agp.loader import load_from_dir            # noqa: E402

_, GAME = load_from_dir(Path(__file__).resolve().parent)
VARIANT = "chigorin"
FILES = "abcdefgh"


def to_uci(move: str) -> str:
    raw, promo = (move.split("=") + [None])[:2]
    fs, ts = raw.split(">")
    fc, fr = (int(x) for x in fs.split(","))
    tc, tr = (int(x) for x in ts.split(","))
    out = f"{FILES[fc]}{fr + 1}{FILES[tc]}{tr + 1}"
    return out + (promo.lower() if promo else "")


def compare(state, fen, moves_played, ctx=""):
    ours = sorted(to_uci(m) for m in GAME.legal_moves(state))
    theirs = sorted(sf.legal_moves(VARIANT, fen, moves_played))
    if ours != theirs:
        raise AssertionError(
            f"MISMATCH {ctx} after {moves_played}:\n"
            f"  ours-only:   {sorted(set(ours) - set(theirs))}\n"
            f"  theirs-only: {sorted(set(theirs) - set(ours))}")


def random_games(n_games, max_plies, seed=0):
    rng = random.Random(seed)
    positions = 0
    for g in range(n_games):
        state = GAME.initial_state()
        fen = sf.start_fen(VARIANT)
        played = []
        for ply in range(max_plies):
            ours = GAME.legal_moves(state)
            if not ours:                      # our draw rules or checkmate/stalemate
                theirs = sf.legal_moves(VARIANT, fen, played)
                if theirs and not GAME._draw(state):
                    raise AssertionError(f"we are terminal but FSF has {theirs}")
                break
            compare(state, fen, played, ctx=f"game {g} ply {ply}")
            positions += 1
            mv = rng.choice(ours)
            played.append(to_uci(mv))
            state = GAME.apply_move(state, mv)
    print(f"random games OK: {n_games} games, {positions} positions compared")


def our_perft(state, depth):
    if depth == 0:
        return 1
    n = 0
    for mv in GAME.legal_moves(state):
        n += our_perft(GAME.apply_move(state, mv), depth - 1)
    return n


def sf_perft(fen, moves, depth):
    if depth == 0:
        return 1
    n = 0
    for mv in sf.legal_moves(VARIANT, fen, moves):
        n += sf_perft(fen, moves + [mv], depth - 1)
    return n


# Hand-picked positions (also anchored in selftest.py):
#   promo: both sides one step from promoting, no castling rights.
PROMO_FEN = "1bbq1k2/P7/8/8/8/8/p6P/1NNC1K2 w - - 0 1"
PROMO_STATE = {
    "board": {"1,7": [1, "B"], "2,7": [1, "B"], "3,7": [1, "Q"], "5,7": [1, "K"],
              "0,6": [0, "P"], "0,1": [1, "P"], "7,1": [0, "P"],
              "1,0": [0, "N"], "2,0": [0, "N"], "3,0": [0, "C"], "5,0": [0, "K"]},
    "to_move": 0, "castling": "", "ep": None, "halfmove": 0, "ply": 0, "reps": {},
}
#   castle: both sides retain full castling rights, chancellor/queen off board.
CASTLE_FEN = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
CASTLE_STATE = {
    "board": dict(
        {f"{c},1": [0, "P"] for c in range(8)},
        **{f"{c},6": [1, "P"] for c in range(8)},
        **{"0,0": [0, "R"], "7,0": [0, "R"], "4,0": [0, "K"],
           "0,7": [1, "R"], "7,7": [1, "R"], "4,7": [1, "K"]}),
    "to_move": 0, "castling": "KQkq", "ep": None, "halfmove": 0, "ply": 0, "reps": {},
}


def perft_check():
    for name, fen, sdict, maxd in [
        ("start", sf.start_fen(VARIANT), None, 4),
        ("promo", PROMO_FEN, PROMO_STATE, 3),
        ("castle", CASTLE_FEN, CASTLE_STATE, 3),
    ]:
        state = GAME.initial_state() if sdict is None else GAME.deserialize(sdict)
        for d in range(1, maxd + 1):
            a, b = our_perft(state, d), sf_perft(fen, [], d)
            flag = "OK" if a == b else "MISMATCH"
            print(f"perft {name} d{d}: ours={a} fsf={b} {flag}")
            assert a == b, f"perft mismatch {name} d{d}"


if __name__ == "__main__":
    print("pyffish", sf.version(), "variant", VARIANT)
    perft_check()
    random_games(n_games=60, max_plies=120, seed=20260719)
    print("ALL DIFFERENTIALS PASSED")
