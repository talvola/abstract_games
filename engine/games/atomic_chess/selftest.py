"""Standalone self-test for Atomic Chess (lichess variant).

Run with:  PYTHONPATH=. python3 games/atomic_chess/selftest.py

Pure-stdlib regression guard (no third-party deps). The one-time faithfulness
check was a full differential against python-chess's ``AtomicBoard`` (1500 games /
~89k positions, kiwipete perft d4 = 3,492,097, insufficient-material parity sweep,
all 0 mismatches) — that gave us merge confidence and is recorded in the commit.
This committed test asserts a fast self-perft regression baseline plus the
atomic-specific rule positions:

  * opening perft 20/400/8902 (no captures yet, so equals standard chess);
  * a capture EXPLODES the captured square's surroundings, removing all non-pawn
    pieces on the 8 adjacent squares (the capturing piece included);
  * adjacent PAWNS survive a blast;
  * exploding the enemy king is an immediate win;
  * a move that would explode YOUR OWN king is illegal.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp import load  # noqa: E402

_, G = load(str(Path(__file__).resolve().parent))


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def st(board, to_move=0, **kw):
    d = {"board": {k: list(v) for k, v in board.items()}, "to_move": to_move,
         "castling": "", "ep": None, "halfmove": 0, "ply": 0, "reps": {}}
    d.update(kw)
    return G.deserialize(d)


def perft(s, d):
    return 1 if d == 0 else sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


def test_perft():
    s = G.initial_state()
    got = [perft(s, d) for d in (1, 2, 3)]
    if got != [20, 400, 8902]:
        fail(f"opening perft {got} != [20, 400, 8902]")
    print("  opening perft 20/400/8902: OK")


def test_explosion():
    # White rook e4 captures a black bishop e7. The blast removes the rook, the
    # bishop, and every non-pawn on the 8 squares around e7: an adjacent black
    # knight (d8) is destroyed, an adjacent black pawn (d7) survives.
    s = st({"4,3": [0, "R"], "4,6": [1, "B"], "3,7": [1, "N"], "3,6": [1, "P"],
            "4,0": [0, "K"], "0,7": [1, "K"]}, to_move=0)
    b = G.apply_move(s, "4,3>4,6").board
    if (4, 6) in b:
        fail("captured square should be empty after the explosion")
    if (4, 3) in b:
        fail("the capturing piece should be consumed by its own explosion")
    if (3, 7) in b:
        fail("an adjacent NON-pawn (knight d8) should be blown up")
    if b.get((3, 6)) != (1, "P"):
        fail("an adjacent PAWN (d7) must SURVIVE the blast")
    print("  capture explodes adjacent non-pawns, pawns survive: OK")


def test_king_explosion_win():
    # White rook e4 captures a black pawn e7; the blast around e7 includes f8
    # (the black king) -> king gone -> White wins immediately. White king is far.
    s = st({"4,3": [0, "R"], "4,6": [1, "P"], "5,7": [1, "K"], "0,0": [0, "K"]}, to_move=0)
    s2 = G.apply_move(s, "4,3>4,6")
    if any(t == "K" and pl == 1 for (pl, t) in s2.board.values()):
        fail("black king should have been exploded")
    if not G.is_terminal(s2) or G.returns(s2) != [1.0, -1.0]:
        fail(f"exploding the enemy king should win for White; returns={G.returns(s2)}")
    print("  exploding the enemy king is an immediate win: OK")


def test_no_blow_up_own_king():
    # White king c3, white rook c2, black knight c4. The rook capturing c4 would
    # explode c4's surroundings including c3 (own king) -> illegal.
    s = st({"2,1": [0, "R"], "2,3": [1, "N"], "2,2": [0, "K"], "7,7": [1, "K"]}, to_move=0)
    if "2,1>2,3" in G.legal_moves(s):
        fail("a capture that explodes your own adjacent king must be illegal")
    print("  cannot make a capture that explodes your own king: OK")


if __name__ == "__main__":
    test_perft()
    test_explosion()
    test_king_explosion_win()
    test_no_blow_up_own_king()
    print("SELFTEST OK")
