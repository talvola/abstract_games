"""One-time differential verification of Shatar against Fairy-Stockfish (pyffish).

NOT part of the test suite (needs pyffish from .venv). Run manually:

    cd engine && PYTHONPATH=. ../.venv/bin/python games/shatar/_diff_pyffish.py

Checks, against FSF's ``shatar`` variant:
  1. perft(1..4) node counts from the initial position;
  2. full legal-move-set agreement at every position of N random games;
  3. terminal / result agreement, including the shatar-specific mate
     classifications (shak-chain mate, niol, forbidden knight mate, robado);
  4. the hand-crafted mate-classification scenarios from selftest.py.
"""

import random
import sys
from pathlib import Path

import pyffish as pf

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

V = "shatar"
START = pf.start_fen(V)
FILES = "abcdefgh"

man, G = load_from_dir(Path(__file__).resolve().parent)


def to_uci(move):
    raw, promo = (move.split("=") + [None])[:2]
    fs, ts = raw.split(">")
    fc, fr = (int(x) for x in fs.split(","))
    tc, tr = (int(x) for x in ts.split(","))
    u = f"{FILES[fc]}{fr + 1}{FILES[tc]}{tr + 1}"
    return u + ("j" if promo else "")


def my_perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(my_perft(G.apply_move(state, m), depth - 1)
               for m in G.legal_moves(state))


def pf_perft(fen, depth):
    moves = pf.legal_moves(V, fen, [])
    if depth == 1:
        return len(moves)
    total = 0
    for m in moves:
        total += pf_perft(pf.get_fen(V, fen, [m]), depth - 1)
    return total


def run_perft(max_depth=4):
    st = G.initial_state()
    for d in range(1, max_depth + 1):
        mine, theirs = my_perft(st, d), pf_perft(START, d)
        status = "OK" if mine == theirs else "MISMATCH"
        print(f"perft({d}): mine={mine} pyffish={theirs} {status}")
        assert mine == theirs, f"perft({d}) mismatch"


def result_sign_pf(fen, hist):
    """FSF terminal result as +1 (side to move wins) / -1 / 0, or None if the
    game is not over for FSF."""
    imm, val = pf.is_immediate_game_end(V, fen, hist)
    if imm:
        return (val > 0) - (val < 0)
    if not pf.legal_moves(V, fen, hist):
        val = pf.game_result(V, fen, hist)
        return (val > 0) - (val < 0)
    return None


def run_random_games(n_games=300, seed=20260711):
    """Per ply: compare full legal-move sets (via an advancing FEN — cheap).
    At a terminal: verify the result with the FULL move history, which FSF
    needs for the shak chain and repetition/50-move claims."""
    rng = random.Random(seed)
    stats = {"positions": 0, "mate": 0, "niol": 0, "knightmate": 0,
             "robado": 0, "stalemate": 0, "rep_or_50": 0, "plycap": 0}
    for g in range(n_games):
        st = G.initial_state()
        fen, hist = START, []
        while True:
            my_moves = G.legal_moves(st)
            mine = sorted(to_uci(m) for m in my_moves)
            imm, _ = pf.is_immediate_game_end(V, fen, [])
            theirs = [] if imm else sorted(pf.legal_moves(V, fen, []))
            if G.is_terminal(st):
                ret = G.returns(st)
                stm = st.to_move
                my_sign = (0 if ret == [0.0, 0.0]
                           else (1 if ret[stm] > 0 else -1))
                if st.ply >= G.PLY_CAP and st.halfmove < 100 \
                        and not G._bared(st.board):
                    stats["plycap"] += 1          # ours only; FSF has no cap
                    break
                if (st.halfmove >= 100
                        or st.reps.get(G._poskey_state(st), 0) >= 3) \
                        and not G._bared(st.board) and G._legal(st):
                    stats["rep_or_50"] += 1
                    opt, val = pf.is_optional_game_end(V, START, hist)
                    assert opt and val == 0, \
                        f"game {g}: 50-move/rep draw not optional-end in FSF"
                    break
                pf_sign = result_sign_pf(START, hist)
                assert pf_sign is not None, \
                    f"game {g}: mine terminal, FSF not ({hist})"
                assert pf_sign == my_sign, \
                    f"game {g}: result mismatch mine={my_sign} pf={pf_sign}"
                if G._bared(st.board):
                    stats["robado"] += 1
                elif not G._checker_types(st.board, stm):
                    stats["stalemate"] += 1
                elif G._checker_types(st.board, stm) <= {"N"}:
                    stats["knightmate"] += 1
                elif my_sign == -1:
                    stats["mate"] += 1
                else:
                    stats["niol"] += 1
                break
            assert mine == theirs, (
                f"game {g} ply {st.ply}: move sets differ\n"
                f" mine-only: {set(mine) - set(theirs)}\n"
                f" pf-only:   {set(theirs) - set(mine)}\n hist={hist}")
            stats["positions"] += 1
            mv = rng.choice(my_moves)
            u = to_uci(mv)
            hist.append(u)
            fen = pf.get_fen(V, fen, [u])
            st = G.apply_move(st, mv)
        if (g + 1) % 50 == 0:
            print(f"  ... {g + 1}/{n_games} games, {stats}")
    print(f"random games: {n_games} finished, {stats}")


def run_scenarios():
    """The crafted classification scenarios, verified against FSF."""
    scenarios = [
        # (name, FEN, uci moves, expected sign for side to move at the end)
        ("shak-chain bishop mate = win",
         "6k1/8/7K/p7/8/B7/8/R7 w - - 0 1",
         ["a1g1", "g8h8", "a3b2"], -1),
        ("niol bishop mate = draw",
         "7k/8/7K/p7/8/B7/8/6R1 w - - 0 1",
         ["g1g2", "a5a4", "a3b2"], 0),
        ("knight-only mate = mated side wins",
         "k7/2N5/8/8/3B4/7p/7P/1R5K b - - 0 1", [], 1),
        ("stalemate = draw",
         "k7/p1K5/P7/8/8/8/8/8 b - - 0 1", [], 0),
        ("knight mate delivered by a move = mated side wins",
         "k7/8/8/1N6/3B4/7p/7P/1R5K w - - 0 1", ["b5c7"], 1),
    ]
    for name, fen, moves, want in scenarios:
        hist = []
        for m in moves:
            assert m in pf.legal_moves(V, fen, hist), (name, m)
            hist.append(m)
        got = result_sign_pf(fen, hist)
        assert got == want, (name, got, want)
        print(f"scenario OK (pyffish): {name}")
    # robado precedence: the baring capture ends the game as a draw even
    # though the position would otherwise be mate
    imm, val = pf.is_immediate_game_end(V, "k7/1p5J/1K6/8/8/8/8/8 w - - 0 1",
                                        ["h7b7"])
    assert imm and val == 0
    print("scenario OK (pyffish): robado capture = immediate draw")


if __name__ == "__main__":
    print(f"pyffish {pf.version()}, variant start: {START}")
    run_scenarios()
    run_perft(4)
    run_random_games(300)
    print("ALL DIFFERENTIAL CHECKS PASSED")
