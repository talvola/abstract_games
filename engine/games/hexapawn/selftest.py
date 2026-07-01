#!/usr/bin/env python3
"""Standalone correctness anchor for Hexapawn (Martin Gardner, 1962).

Run from the engine dir with::

    PYTHONPATH=. python3 games/hexapawn/selftest.py

Pure stdlib + this game only. Fast. Prints ``SELFTEST OK`` and exits 0 on
success, nonzero on any failure.

It asserts:

* the setup: 3 White pawns on row 0, 3 Black pawns on row 2, empty middle;
* the opening legal-move count (3 single pushes, no captures available);
* diagonal moves are CAPTURE-ONLY (no diagonal onto an empty square);
* reaching the far rank wins via apply_move; a stalemated side loses;
* serialize round-trips;
* the **game-theoretic result**: with perfect play the SECOND player (Black)
  wins — verified by exact minimax on the initial position (value = a LOSS for
  the player to move, i.e. White).
"""

import sys

from games.hexapawn.game import Hexapawn, HexState

G = Hexapawn()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def test_setup():
    s = G.initial_state()
    check(len(s.board) == 6, "expected 6 pawns")
    check(all(s.board[(c, 0)] == 0 for c in range(3)), "White home rank")
    check(all(s.board[(c, 2)] == 1 for c in range(3)), "Black home rank")
    check(all((c, 1) not in s.board for c in range(3)), "middle rank empty")
    check(G.current_player(s) == 0, "White moves first")
    check(not G.is_terminal(s), "opening not terminal")


def test_opening_moves():
    s = G.initial_state()
    lm = set(G.legal_moves(s))
    # Only the three straight pushes to the empty middle rank; no captures yet.
    expected = {"0,0>0,1", "1,0>1,1", "2,0>2,1"}
    check(lm == expected, f"opening moves wrong: {sorted(lm)}")


def test_diagonal_is_capture_only():
    # White pawn at 0,0; enemy diagonally at 1,1 -> capture legal.
    # Also a pawn with only an empty diagonal must NOT get a diagonal move.
    s = HexState(board={(0, 0): 0, (1, 1): 1}, to_move=0)
    lm = set(G.legal_moves(s))
    check("0,0>1,1" in lm, "diagonal capture must be legal")
    # straight push blocked? 0,1 is empty so push legal:
    check("0,0>0,1" in lm, "straight push should be legal")
    # No enemy diagonal -> no diagonal move.
    s2 = HexState(board={(0, 0): 0}, to_move=0)
    lm2 = set(G.legal_moves(s2))
    check(lm2 == {"0,0>0,1"}, f"diagonal onto empty must be illegal: {sorted(lm2)}")


def test_reach_far_rank_wins():
    # White pawn one step from row 2.
    s = HexState(board={(0, 1): 0, (2, 2): 1}, to_move=0)
    s2 = G.apply_move(s, "0,1>0,2")
    check(G.is_terminal(s2), "reaching far rank must be terminal")
    check(s2.winner == 0, "White should win by reaching far rank")
    check(G.returns(s2) == [1.0, -1.0], "returns wrong for White win")


def test_stalemate_loses():
    # Black to move but has no legal move -> Black loses.
    # Black pawn at 0,2 blocked ahead (0,1 occupied by own? no, must be enemy-
    # blocked straight + no capture). Put White pawn directly in front and no
    # diagonal targets.
    s = HexState(board={(0, 2): 1, (0, 1): 0}, to_move=1)
    check(G.legal_moves(s) == [], "Black should have no move")
    check(G.is_terminal(s), "no-move position is terminal")
    check(G.returns(s) == [1.0, -1.0], "stalemated Black loses -> White wins")


def test_serialize_roundtrip():
    s = G.initial_state()
    s = G.apply_move(s, "1,0>1,1")
    d = G.serialize(s)
    s2 = G.deserialize(d)
    check(G.serialize(s2) == d, "serialize must round-trip")


# --- exact minimax on the full game tree (tiny) ----------------------------
_cache = {}


def _key(s):
    return (tuple(sorted(s.board.items())), s.to_move)


def minimax(s):
    """Return payoff [white, black] under perfect play from state s."""
    if G.is_terminal(s):
        return tuple(G.returns(s))
    k = _key(s)
    if k in _cache:
        return _cache[k]
    mover = G.current_player(s)
    best = None
    for mv in G.legal_moves(s):
        val = minimax(G.apply_move(s, mv))
        # each player maximizes their own payoff
        if best is None or val[mover] > best[mover]:
            best = val
    _cache[k] = best
    return best


def test_second_player_wins():
    s = G.initial_state()
    val = minimax(s)
    # White = player 0 is the FIRST player and to move at the root.
    check(val == (-1.0, 1.0),
          f"perfect play must be a Black (2nd-player) win; got {val}")


def main():
    test_setup()
    test_opening_moves()
    test_diagonal_is_capture_only()
    test_reach_far_rank_wins()
    test_stalemate_loses()
    test_serialize_roundtrip()
    test_second_player_wins()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
