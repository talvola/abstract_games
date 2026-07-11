#!/usr/bin/env python3
"""One-time differential anchor for Duck Chess against Fairy-Stockfish (pyffish).

NOT part of the stdlib selftest (needs `pip install pyffish` in .venv). Run:

    cd engine && PYTHONPATH=. ../.venv/bin/python3 games/duck_chess/_diff_pyffish.py

Compares, in FSF's combined turn notation ``<uci-chess-move>,<dest><duck>``:

* the full legal-TURN set at every position of N random games (played to the
  end or a turn cap), plus board/side/castling FEN agreement after every turn;
* perft(1) and perft(2) turn counts from the start position and from several
  fixed mid-game positions.

FSF quirks handled:
* FSF pairs even a king-capturing chess move with every duck square (the game
  ends immediately after); our engine ends the turn without a duck sub-move,
  so king-capture turns are expanded to all duck targets for comparison.
* FSF's FEN shows the duck as ``*`` and omits the e.p. field unless a capture
  is actually possible, so the e.p. field is not compared (the move sets
  cover e.p. behaviour).
"""

import random
import sys
from pathlib import Path

import pyffish as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

V = "duck"
FILES = "abcdefgh"
_, G = load_from_dir(Path(__file__).resolve().parent)


def alg(c, r):
    return f"{FILES[c]}{r + 1}"


def cellp(s):
    c, r = s.split(",")
    return int(c), int(r)


def chess_uci(move):
    raw, promo = (move.split("=") + [None])[:2]
    fs, ts = raw.split(">")
    f, t = cellp(fs), cellp(ts)
    return alg(*f) + alg(*t) + (promo.lower() if promo else "")


def my_turns(state):
    """All legal full turns as FSF strings, and a map back to my sub-moves."""
    out = {}
    for cm in G.legal_moves(state):
        uci = chess_uci(cm)
        raw = cm.split("=")[0]
        dest = cellp(raw.split(">")[1])
        s1 = G.apply_move(state, cm)
        if s1.winner is not None:
            # FSF still enumerates every duck target on a king-capture turn.
            ducks = [f"{c},{r}" for r in range(8) for c in range(8)
                     if (c, r) not in s1.board and (c, r) != s1.duck]
            for dm in ducks:
                out[f"{uci},{alg(*dest)}{alg(*cellp(dm))}"] = (cm, None)
        else:
            for dm in G.legal_moves(s1):
                out[f"{uci},{alg(*dest)}{alg(*cellp(dm))}"] = (cm, dm)
    return out


def my_fen_fields(state):
    """(placement, side, castling) in FEN terms, duck as '*'."""
    rows = []
    for r in range(7, -1, -1):
        row, run = "", 0
        for c in range(8):
            if (c, r) == state.duck:
                ch = "*"
            else:
                occ = state.board.get((c, r))
                if occ is None:
                    run += 1
                    continue
                pl, t = occ
                ch = t.upper() if pl == 0 else t.lower()
            if run:
                row += str(run)
                run = 0
            row += ch
        if run:
            row += str(run)
        rows.append(row)
    cas = "".join(sorted(state.castling, key="KQkq".index)) or "-"
    return "/".join(rows), "wb"[state.to_move], cas


fails = 0


def check(cond, msg):
    global fails
    if not cond:
        fails += 1
        print("DIFF FAIL:", msg)


# --------------------------------------------------------------------------- #
# 1. perft(1) / perft(2) from the start
# --------------------------------------------------------------------------- #
start = sf.start_fen(V)


def fsf_perft2(fen, moves):
    lm = sf.legal_moves(V, fen, moves)
    total = 0
    for m in lm:
        total += len(sf.legal_moves(V, fen, moves + [m]))
    return len(lm), total


def my_perft2(state):
    turns = my_turns(state)
    total = 0
    for fsf_m, (cm, dm) in turns.items():
        s1 = G.apply_move(state, cm)
        if dm is None:            # king captured: game over, 0 replies
            continue
        s2 = G.apply_move(s1, dm)
        if s2.winner is not None or G.is_terminal(s2):
            continue
        total += len(my_turns(s2))
    return len(turns), total


s0 = G.initial_state()
f1, f2 = fsf_perft2(start, [])
m1, m2 = my_perft2(s0)
print(f"start perft1: FSF={f1} mine={m1}   perft2: FSF={f2} mine={m2}")
check(f1 == m1 and f2 == m2, "start perft mismatch")

# --------------------------------------------------------------------------- #
# 2. fixed mid positions: perft(1) after known openings
# --------------------------------------------------------------------------- #
FIXED = [
    ["e2e4,e4d5", "e7e5,e5d4"],
    ["g1f3,f3h3", "g8f6,f6h6", "g2g3,g3g6", "b8c6,c6b6", "f1g2,g2g5",
     "e7e6,e6e5"],                                   # White may castle
    ["e2e4,e4e3", "d7d5,d5d4"],                      # duck on e3/d4 in the centre
    ["b1c3,c3c6", "d7d5,d5d4", "c3d5,d5e3"],         # knight takes with duck near
]


def replay_mine(fsf_moves):
    st = G.initial_state()
    for m in fsf_moves:
        turns = my_turns(st)
        check(m in turns, f"replay: FSF move {m} not in my set")
        cm, dm = turns[m]
        st = G.apply_move(st, cm)
        if dm is not None:
            st = G.apply_move(st, dm)
    return st


for seq in FIXED:
    st = replay_mine(seq)
    fl = set(sf.legal_moves(V, start, seq))
    ml = set(my_turns(st))
    check(fl == ml, f"fixed pos {seq}: FSF {len(fl)} vs mine {len(ml)}; "
                    f"only-FSF {sorted(fl - ml)[:5]} only-mine {sorted(ml - fl)[:5]}")
    print(f"fixed pos ({len(seq)} turns in): {len(fl)} turns, sets equal={fl == ml}")

# --------------------------------------------------------------------------- #
# 3. random-game replay with full move-set + FEN comparison every turn
# --------------------------------------------------------------------------- #
rng = random.Random(20260711)
N_GAMES, TURN_CAP = 8, 90
for gi in range(N_GAMES):
    moves = []
    st = G.initial_state()
    for ti in range(TURN_CAP):
        fl = set(sf.legal_moves(V, start, moves))
        mine = my_turns(st)
        ml = set(mine)
        check(fl == ml, f"game {gi} turn {ti}: set mismatch "
                        f"only-FSF {sorted(fl - ml)[:5]} only-mine {sorted(ml - fl)[:5]}")
        if not fl:
            break
        m = rng.choice(sorted(fl))
        cm, dm = mine[m]
        st = G.apply_move(st, cm)
        ended_mine = dm is None
        if dm is not None:
            st = G.apply_move(st, dm)
        moves.append(m)
        end, _val = sf.is_immediate_game_end(V, start, moves)
        check(end == ended_mine or (end and st.winner is not None),
              f"game {gi} turn {ti}: end disagreement FSF={end} mine_winner={st.winner}")
        if end or st.winner is not None:
            check(st.winner is not None, f"game {gi}: FSF ended, mine didn't")
            break
        fen = sf.get_fen(V, start, moves).split()
        mp, ms, mc = my_fen_fields(st)
        check(fen[0] == mp, f"game {gi} turn {ti}: placement {fen[0]} vs {mp}")
        check(fen[1] == ms, f"game {gi} turn {ti}: side {fen[1]} vs {ms}")
        check(fen[2] == mc, f"game {gi} turn {ti}: castling {fen[2]} vs {mc}")
    print(f"game {gi}: {len(moves)} turns, winner={st.winner}")

print("ALL DIFF CHECKS PASSED" if fails == 0 else f"{fails} FAILURES")
sys.exit(0 if fails == 0 else 1)
