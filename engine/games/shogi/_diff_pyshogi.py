"""One-time differential verification of our Shogi against python-shogi (the
gold-standard reference). NOT shipped to the suite (imports python-shogi); run
manually with the project's .venv:

    PYTHONPATH=. ../../.venv/bin/python games/shogi/_diff_pyshogi.py

Coordinate map: our (col,row) <-> python-shogi square = (8-row)*9 + col, so
file_index = col and rank_index = 8 - row. USI file digit = 9 - col, rank letter
= chr('a' + 8 - row). Sente (Black, our player 0) moves first in both.

Checks: (1) perft from the start to depth 4 matches python-shogi; (2) a
synchronized random walk where, at every ply, the two engines' legal-move *sets*
must be equal (so promotion, drops, nifu/last-rank/uchifuzume all agree).
"""
import random
import sys

import shogi

sys.path.insert(0, ".")
from games.shogi.game import Shogi  # noqa: E402
from agp.shogilike import cell  # noqa: E402

G = Shogi()


def usi_sq(c, r):
    return f"{9 - c}{chr(ord('a') + (8 - r))}"


def my_to_usi(move):
    if "@" in move:
        letter, cs = move.split("@")
        return f"{letter}*{usi_sq(*cell(cs))}"
    promote = move.endswith("=+")
    raw = move[:-2] if promote else move
    fs, ts = raw.split(">")
    return usi_sq(*cell(fs)) + usi_sq(*cell(ts)) + ("+" if promote else "")


def my_set(state):
    return {my_to_usi(m) for m in G.legal_moves(state)}


def pc_set(board):
    return {m.usi() for m in board.legal_moves}


def my_perft(state, d):
    if d == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(my_perft(G.apply_move(state, m), d - 1) for m in G.legal_moves(state))


def pc_perft(board, d):
    if d == 0:
        return 1
    n = 0
    for m in board.legal_moves:
        board.push(m)
        n += pc_perft(board, d - 1)
        board.pop()
    return n


def perft_check(maxd=4):
    print("== perft (start position) ==")
    known = {1: 30, 2: 900, 3: 25470, 4: 719731}
    out = []
    for d in range(1, maxd + 1):
        mine = my_perft(G.initial_state(), d)
        ref = pc_perft(shogi.Board(), d)
        ok = "OK" if mine == ref == known.get(d, ref) else "MISMATCH"
        print(f"  depth {d}: mine={mine:>9} pyshogi={ref:>9} known={known.get(d,'?'):>9}  {ok}")
        assert mine == ref, f"perft mismatch d{d}"
        out.append(mine)
    return out


def walk_check(games=300, max_ply=140, seed=99):
    print(f"== synchronized random walk ({games} games) ==")
    rng = random.Random(seed)
    total = 0
    for g in range(games):
        state = G.initial_state()
        board = shogi.Board()
        for _ in range(max_ply):
            over_mine = G.is_terminal(state)
            over_ref = board.is_game_over()
            if over_mine or over_ref:
                # both must agree the game is over (modulo our ply/rep draw caps,
                # which python-shogi does not impose -- only assert when neither
                # cap could explain it)
                if over_mine and not over_ref and not G._draw(state):
                    assert False, f"mine terminal early g{g}\n{board.sfen()}"
                if over_ref and not over_mine:
                    assert False, f"pyshogi terminal but mine not g{g}\n{board.sfen()}"
                break
            mine, ref = my_set(state), pc_set(board)
            if mine != ref:
                raise AssertionError(
                    f"move-set mismatch g{g} ply{board.move_number}\n"
                    f"SFEN: {board.sfen()}\n"
                    f"only mine:    {sorted(mine - ref)}\n"
                    f"only pyshogi: {sorted(ref - mine)}")
            uci = rng.choice(sorted(mine))
            my_mv = next(m for m in G.legal_moves(state) if my_to_usi(m) == uci)
            state = G.apply_move(state, my_mv)
            board.push_usi(uci)
            total += 1
    print(f"  OK -- {total} plies, 0 mismatches")


if __name__ == "__main__":
    perft_check(4)
    walk_check()
    print("\nALL DIFFERENTIAL CHECKS PASSED")
