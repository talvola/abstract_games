"""Standalone correctness anchor for Knight Relay Chess.

Pure stdlib (imports only ``agp`` + this game).  Run directly or via
``tests/test_games.py::test_package_selftests``.  Asserts:

* the engine-derived opening perft (d1/d2/d3) -- frozen anchors;
* a pawn guarded by a friendly knight gains knight-moves; an unguarded one does not;
* a knight cannot capture, and cannot be captured (by a normal OR a relayed move);
* a relayed knight-check is real check; a lone knight gives no check;
* the king does NOT relay even when guarded;
* a pawn may not relay onto its own last rank (no relayed promotion);
* no en passant;
* a relayed checkmate is reached via apply_move and scored correctly;
* serialize round-trips.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.chesslike import CState, WHITE, BLACK  # noqa: E402
from games.knight_relay.game import KnightRelayChess  # noqa: E402

G = KnightRelayChess()

# Frozen engine-derived anchors (the start is symmetric: perft(2) = 28*28).
PERFT = {1: 28, 2: 784, 3: 24044}


def _mk(board, to_move=WHITE):
    st = CState(board=dict(board), to_move=to_move, castling=frozenset(), ep=None)
    st.reps = {G._poskey_state(st): 1}
    return st


def _lm(st):
    return set(G.legal_moves(st))


def _perft(st, depth):
    if depth == 0:
        return 1
    if G.is_terminal(st):
        return 0
    return sum(_perft(G.apply_move(st, m), depth - 1) for m in G.legal_moves(st))


def test_perft():
    st = G.initial_state()
    assert len(G.legal_moves(st)) == 28, "opening move count"
    for d, n in PERFT.items():
        got = _perft(st, d)
        assert got == n, f"perft({d}) = {got}, expected {n}"


def test_relay_grants_knight_moves():
    # Unguarded pawn: no knight leaps.
    base = {(4, 4): (WHITE, "P"), (4, 0): (WHITE, "K"), (0, 7): (BLACK, "K")}
    assert "4,4>5,6" not in _lm(_mk(base)), "unguarded pawn must not leap"
    # Guard it with a knight (N at (2,3) leaps onto (4,4)).
    g = dict(base); g[(2, 3)] = (WHITE, "N")
    ms = _lm(_mk(g))
    assert "4,4>5,6" in ms and "4,4>6,5" in ms, "guarded pawn gains knight leaps"


def test_knight_cannot_capture():
    b = {(3, 3): (WHITE, "N"), (5, 4): (BLACK, "P"),
         (4, 0): (WHITE, "K"), (0, 7): (BLACK, "K")}
    ms = _lm(_mk(b))
    assert "3,3>5,4" not in ms, "knight must not capture"
    assert "3,3>5,2" in ms, "knight still moves to empty leap squares"


def test_knight_cannot_be_captured():
    # by a normal slider
    b = {(0, 0): (WHITE, "R"), (5, 0): (BLACK, "N"),
         (4, 4): (WHITE, "K"), (0, 7): (BLACK, "K")}
    assert "0,0>5,0" not in _lm(_mk(b)), "rook must not capture a knight"
    # by a relayed knight-move
    b = {(4, 4): (WHITE, "B"), (2, 3): (WHITE, "N"), (5, 6): (BLACK, "N"),
         (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K")}
    ms = _lm(_mk(b))
    assert "4,4>5,6" not in ms, "relayed move must not capture a knight"
    assert "4,4>6,5" in ms, "relayed move to empty is fine"


def test_relayed_check():
    # White bishop guarded by a white knight gives a relayed knight-check.
    b = {(4, 4): (WHITE, "B"), (2, 3): (WHITE, "N"), (5, 6): (BLACK, "K"),
         (0, 0): (WHITE, "K")}
    assert G.in_check(b, BLACK), "relayed knight-check must be check"
    nob = dict(b); del nob[(2, 3)]
    assert not G.in_check(nob, BLACK), "no guard -> no relay -> no check"
    # A lone enemy knight a leap away never checks.
    lone = {(3, 4): (WHITE, "N"), (5, 5): (BLACK, "K"), (0, 0): (WHITE, "K")}
    assert not G.in_check(lone, BLACK), "a knight never gives check by itself"


def test_king_does_not_relay():
    b = {(4, 4): (WHITE, "K"), (2, 3): (WHITE, "N"), (0, 7): (BLACK, "K")}
    for m in _lm(_mk(b)):
        if not m.startswith("4,4>"):
            continue
        tc, tr = (int(x) for x in m.split(">")[1].split(","))
        assert sorted((abs(tc - 4), abs(tr - 4))) != [1, 2], "king must not relay"


def test_pawn_no_relay_to_last_rank():
    b = {(4, 6): (WHITE, "P"), (2, 5): (WHITE, "N"),
         (0, 0): (WHITE, "K"), (7, 0): (BLACK, "K")}
    ms = _lm(_mk(b))
    assert "4,6>5,7" not in ms, "pawn must not relay onto its last rank"
    assert "4,6>6,5" in ms, "a relayed leap to a middle rank is fine"


def test_no_en_passant():
    b = {(3, 4): (WHITE, "P"), (4, 6): (BLACK, "P"),
         (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K")}
    after = G.apply_move(_mk(b, BLACK), "4,6>4,4")
    assert after.ep is None, "no ep target may be created"
    assert "3,4>4,5" not in _lm(after), "no en passant capture"


def test_relayed_mate_reached():
    """Reach a relayed checkmate via apply_move and verify the score.

    Black king a1=(0,0); White queen b3=(1,2) and king h1=(7,0).  The queen
    alone gives NO check (b3 is neither adjacent nor aligned to a1).  White plays
    Nf1-d2 (5,0)->(3,1): the knight now GUARDS the queen, so the queen RELAYS a
    knight-leap to a1 -- a check with no escape (a2/b1/b2 all covered by the
    queen, and the queen is un-reachable by the king).  Verified entirely by the
    engine; ``winner``/terminality is reached the proper way (via apply_move),
    not by hand-building the dead board.
    """
    pre = {(0, 0): (BLACK, "K"), (1, 2): (WHITE, "Q"),
           (5, 0): (WHITE, "N"), (7, 0): (WHITE, "K")}
    assert not G.in_check(pre, BLACK), "queen alone (no guard) must not check"
    st = _mk(pre, WHITE)
    assert "5,0>3,1" in _lm(st), "Nf1-d2 (creating the guard) must be legal"
    after = G.apply_move(st, "5,0>3,1")
    assert G.is_terminal(after), "the relayed knight-check must be mate"
    assert G.returns(after) == [1.0, -1.0], "White wins the relayed mate"


def test_serialize_roundtrip():
    st = G.initial_state()
    st2 = G.deserialize(G.serialize(st))
    assert _lm(st) == _lm(st2), "serialize round-trip"


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("SELFTEST OK")


if __name__ == "__main__":
    run()
