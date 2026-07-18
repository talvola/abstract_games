"""Selftest for Circular Chess -- pure stdlib, fast.

Anchors:
  (a) perft: perft(1) hand-derived piece-by-piece from the published setup
      (16 pawn moves + 4 knight moves = 20, with the double first step; 12
      without it), plus frozen self-perft(1..3).
  (b) rule positions: null-move / full-circle slider exclusion, promotion at the
      meeting squares from BOTH directions, wrapped knight & bishop moves across
      the 15->0 seam, a checkmate and a stalemate.
  (c) conformance: random games run to a terminal with well-formed returns.

Run:  cd engine && PYTHONPATH=. python3 games/circular_chess/selftest.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # engine/ on path

from agp.loader import load_from_dir  # noqa: E402

MAN, G = load_from_dir(Path(__file__).resolve().parent)
State = type(G.initial_state())
WHITE, BLACK = 0, 1


def perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


def mk(board, to_move=WHITE, double_step=True):
    return State(board=dict(board), to_move=to_move, double_step=double_step)


def test_perft():
    s = G.initial_state()  # double_step default True
    assert perft(s, 1) == 20, perft(s, 1)         # hand-derived: 16 pawn + 4 knight
    assert perft(s, 2) == 400, perft(s, 2)        # frozen
    assert perft(s, 3) == 8584, perft(s, 3)       # frozen
    s0 = G.initial_state(options={"double_step": False})
    assert perft(s0, 1) == 12, perft(s0, 1)       # hand-derived: 8 pawn + 4 knight
    assert perft(s0, 2) == 144, perft(s0, 2)
    print("perft OK (1=20, 2=400, 3=8584; no-double 1=12, 2=144)")


def test_null_move_full_circle():
    # A lone rook on an otherwise-empty ring 2. It may reach the 15 OTHER sectors
    # of the ring but NEVER its own square (the full-circle null move is banned).
    board = {(0, 2): (WHITE, "R"), (0, 0): (WHITE, "K"), (8, 0): (BLACK, "K")}
    s = mk(board, WHITE)
    moves = G.legal_moves(s)
    # no move returns a piece to its origin
    assert all(m.split(">")[0] != m.split(">")[1].split("=")[0] for m in moves), moves
    ring2_targets = {m.split(">")[1] for m in moves
                     if m.startswith("0,2>") and m.split(">")[1].endswith(",2")}
    assert ring2_targets == {f"{sec},2" for sec in range(1, 16)}, sorted(ring2_targets)
    assert "0,2>0,2" not in moves
    print(f"null-move OK (rook reaches 15 sectors, not its own; {len(ring2_targets)} circular targets)")


def test_promotion_both_directions():
    # White +sector pawn (sector 6 -> promo sector 7)
    s = mk({(6, 1): (WHITE, "P"), (0, 0): (WHITE, "K"), (8, 3): (BLACK, "K")}, WHITE)
    ms = [m for m in G.legal_moves(s) if m.startswith("6,1>7,1")]
    assert sorted(ms) == ["6,1>7,1=B", "6,1>7,1=N", "6,1>7,1=Q", "6,1>7,1=R"], ms
    # White -sector pawn (sector 9 -> promo sector 8)
    s = mk({(9, 1): (WHITE, "P"), (0, 0): (WHITE, "K"), (2, 3): (BLACK, "K")}, WHITE)
    ms = [m for m in G.legal_moves(s) if m.startswith("9,1>8,1")]
    assert sorted(ms) == ["9,1>8,1=B", "9,1>8,1=N", "9,1>8,1=Q", "9,1>8,1=R"], ms
    # Black +sector pawn (sector 14 -> promo sector 15)
    s = mk({(14, 1): (BLACK, "P"), (8, 0): (BLACK, "K"), (4, 3): (WHITE, "K")}, BLACK)
    ms = [m for m in G.legal_moves(s) if m.startswith("14,1>15,1")]
    assert sorted(ms) == ["14,1>15,1=B", "14,1>15,1=N", "14,1>15,1=Q", "14,1>15,1=R"], ms
    # Black -sector pawn (sector 1 -> promo sector 0)
    s = mk({(1, 1): (BLACK, "P"), (8, 0): (BLACK, "K"), (5, 3): (WHITE, "K")}, BLACK)
    ms = [m for m in G.legal_moves(s) if m.startswith("1,1>0,1")]
    assert sorted(ms) == ["1,1>0,1=B", "1,1>0,1=N", "1,1>0,1=Q", "1,1>0,1=R"], ms
    # and a promotion actually produces the chosen piece
    s2 = G.apply_move(mk({(6, 1): (WHITE, "P"), (0, 0): (WHITE, "K"),
                          (8, 3): (BLACK, "K")}, WHITE), "6,1>7,1=Q")
    assert s2.board[(7, 1)] == (WHITE, "Q"), s2.board.get((7, 1))
    print("promotion OK (Q/R/B/N at the meeting squares from both directions)")


def test_wrap_across_seam():
    # Knight on the 15|0 seam wraps to sector 0.
    s = mk({(15, 1): (WHITE, "N"), (0, 0): (WHITE, "K"), (8, 3): (BLACK, "K")}, WHITE)
    tos = {m.split(">")[1] for m in G.legal_moves(s) if m.startswith("15,1>")}
    assert "0,3" in tos, sorted(tos)                   # (15,1) +(1,+2) -> (0,3)
    assert any(t.startswith("0,") for t in tos), sorted(tos)
    # Bishop on the seam wraps diagonally onto sector 0.
    s = mk({(15, 1): (WHITE, "B"), (5, 0): (WHITE, "K"), (10, 3): (BLACK, "K")}, WHITE)
    tos = {m.split(">")[1] for m in G.legal_moves(s) if m.startswith("15,1>")}
    assert "0,2" in tos and "0,0" in tos, sorted(tos)   # (+1,+1) and (+1,-1)
    print("wrap OK (knight & bishop cross the 15->0 seam)")


def test_checkmate():
    # Black king boxed on the inner ring: Qe covers every flight, protected by K.
    board = {(0, 0): (BLACK, "K"), (0, 1): (WHITE, "Q"), (0, 2): (WHITE, "K")}
    s = mk(board, BLACK)
    assert G.legal_moves(s) == [], G.legal_moves(s)
    assert G._in_check(s.board, BLACK) is True
    assert G._compute_result(s) == "W0"
    print("checkmate OK (White mates)")


def test_stalemate():
    # Black king (outer ring) not in check but every flight is covered.
    board = {
        (0, 3): (BLACK, "K"),
        (8, 2): (WHITE, "R"),   # sweeps ring 2 -> covers (15,2),(0,2),(1,2)
        (1, 0): (WHITE, "R"),   # radial up sector 1 -> covers (1,3)
        (15, 0): (WHITE, "R"),  # radial up sector 15 -> covers (15,3)
        (8, 0): (WHITE, "K"),
    }
    s = mk(board, BLACK)
    assert G._in_check(s.board, BLACK) is False
    assert G.legal_moves(s) == [], G.legal_moves(s)
    assert G._compute_result(s) == "D"
    print("stalemate OK (honest draw)")


def test_conformance():
    for seed in range(8):
        rng = random.Random(seed)
        s = G.initial_state(options={"double_step": bool(seed % 2)})
        steps = 0
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            steps += 1
            assert steps <= 600, "game failed to terminate"
        r = G.returns(s)
        assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r), r
        assert r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]), r
        # serialize round-trip at the terminal
        assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)
    print("conformance OK (8 random games to terminal, returns well-formed)")


def test_heuristic_shape():
    # heuristic must be a per-seat list even when the rollout cutoff is reached.
    from agp.mcts import MCTSBot
    s = G.initial_state()
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2, h
    MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(G, s)
    print("heuristic OK (per-seat list; MCTS with low max_rollout runs)")


if __name__ == "__main__":
    test_perft()
    test_null_move_full_circle()
    test_promotion_both_directions()
    test_wrap_across_seam()
    test_checkmate()
    test_stalemate()
    test_conformance()
    test_heuristic_shape()
    print("all circular_chess selftests passed")
