"""One-time differential verification of our Crazyhouse against python-chess's
gold-standard chess.variant.CrazyhouseBoard. NOT shipped to the suite (it imports
python-chess); run manually with the project's .venv:

    PYTHONPATH=. ../../.venv/bin/python games/crazyhouse/_diff_pychess.py

Checks: (1) perft node counts match to depth 4 from the start; (2) a synchronized
random walk where, at every ply, the two engines' legal-move *sets* must be equal
(converting our moves to UCI), so castling/ep/promotion/drops/mate-in-hand all
agree.
"""
import random
import sys

import chess
import chess.variant

sys.path.insert(0, ".")
from games.crazyhouse.game import Crazyhouse  # noqa: E402
from agp.chesslike import cell  # noqa: E402

G = Crazyhouse()


def sq_name(c, r):
    return chess.square_name(chess.square(c, r))


def my_move_to_uci(move):
    """Our move string -> python-chess UCI (matches CrazyhouseBoard.uci())."""
    if "@" in move:
        letter, cs = move.split("@")
        c = cell(cs)
        return f"{letter.upper()}@{sq_name(*c)}"
    raw, _, promo = move.partition("=")
    fs, ts = raw.split(">")
    frm, to = cell(fs), cell(ts)
    u = sq_name(*frm) + sq_name(*to)
    return u + (promo.lower() if promo else "")


def my_legal_uci(state):
    return {my_move_to_uci(m) for m in G.legal_moves(state)}


def pc_legal_uci(board):
    return {board.uci(m) for m in board.legal_moves}


# ---------------------------------------------------------------- perft
def my_perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    n = 0
    for m in G.legal_moves(state):
        n += my_perft(G.apply_move(state, m), depth - 1)
    return n


def pc_perft(board, depth):
    if depth == 0:
        return 1
    n = 0
    for m in board.legal_moves:
        board.push(m)
        n += pc_perft(board, depth - 1)
        board.pop()
    return n


def perft_check(max_depth=4):
    print("== perft (start position) ==")
    counts = []
    for d in range(1, max_depth + 1):
        mine = my_perft(G.initial_state(), d)
        theirs = pc_perft(chess.variant.CrazyhouseBoard(), d)
        ok = "OK" if mine == theirs else "MISMATCH"
        print(f"  depth {d}: mine={mine:>10}  pychess={theirs:>10}  {ok}")
        counts.append(mine)
        assert mine == theirs, f"perft mismatch at depth {d}"
    return counts


# --------------------------------------------------- synchronized random walk
def walk_check(games=400, max_ply=120, seed=12345):
    print(f"== synchronized random walk ({games} games) ==")
    rng = random.Random(seed)
    total_ply = 0
    for g in range(games):
        state = G.initial_state()
        board = chess.variant.CrazyhouseBoard()
        for _ in range(max_ply):
            if G.is_terminal(state) or board.is_game_over():
                # both must agree on game-over
                assert G.is_terminal(state) == board.is_game_over(), (
                    f"terminal disagreement game {g}: mine={G.is_terminal(state)} "
                    f"pychess={board.is_game_over()}\n{board.fen()}")
                break
            mine, theirs = my_legal_uci(state), pc_legal_uci(board)
            assert mine == theirs, (
                f"move-set mismatch game {g} ply {board.ply()}\n"
                f"FEN: {board.fen()}\n"
                f"only mine:   {sorted(mine - theirs)}\n"
                f"only pychess:{sorted(theirs - mine)}")
            uci = rng.choice(sorted(mine))
            # apply to mine
            my_mv = next(m for m in G.legal_moves(state) if my_move_to_uci(m) == uci)
            state = G.apply_move(state, my_mv)
            board.push_uci(uci)
            total_ply += 1
    print(f"  OK -- {total_ply} plies, 0 mismatches")


if __name__ == "__main__":
    perft_check(4)
    walk_check()
    print("\nALL DIFFERENTIAL CHECKS PASSED")
