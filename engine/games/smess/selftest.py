"""Pure-stdlib correctness anchor for Smess. Run by tests/test_games.py and
standalone:  cd engine && PYTHONPATH=. python3 games/smess/selftest.py

Anchors (official Parker Brothers rulebook + chessvariants.com board diagram):
  * the full 56-square arrow map, asserted as DATA + proven 180deg-symmetric
    (the symmetry independently corroborates the transcription);
  * setup = 12 pieces/side (1 Brain, 4 Numskulls, 7 Ninnies) on the right squares;
  * opening legal-move count = 12 (hand-derived from the arrow map);
  * Ninny = 1 step; Numskull slides + is blocked (stop at own, capture enemy);
  * arrow-direction enforcement (no move against the arrows);
  * Brain capture ends the game; two-Brains-only = draw; promotion on the
    opponent's Numskull squares only; deadlock generator returns no moves;
  * serialize round-trip; random playouts terminate; heuristic shape.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.smess.game import (  # noqa: E402
    ARROWS, DIRS, REV, PROMO, NUMSKULL_START, Smess, SState,
)


def _mv(frm, to):
    return f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"


def test_arrow_map_data():
    # Spot-check squares read directly off the official board image.
    def A(c, r):
        return set(ARROWS[(c, r)])
    assert A(0, 0) == {"N"}, A(0, 0)                    # a1 = pointing hand, up
    assert A(6, 7) == {"S"}, A(6, 7)                    # g8 = pointing hand, down
    assert A(1, 4) == {"E"}, A(1, 4)                    # b5 = hand, right
    assert A(5, 3) == {"W"}, A(5, 3)                    # f4 = hand, left
    assert A(3, 3) == set(DIRS), A(3, 3)                # d4 = all 8
    assert A(3, 4) == set(DIRS), A(3, 4)                # d5 = all 8
    assert A(1, 1) == {"N", "SE"}, A(1, 1)             # b2 (diagonal square)
    assert A(5, 1) == {"N", "W", "SE"}, A(5, 1)        # f2
    assert A(0, 7) == {"S", "E"}, A(0, 7)              # a8 corner
    assert A(2, 5) == {"NE", "NW", "SE", "SW"}, A(2, 5)  # c6 = 4 diagonals
    assert len(ARROWS) == 56
    assert all(len(v) >= 1 for v in ARROWS.values())   # every square has >=1 arrow


def test_arrow_map_symmetry():
    # The board is exactly 180deg point-symmetric: reversing every arrow on
    # cell (c,r) reproduces the arrows on (6-c, 7-r). This is the primary
    # transcription check (halves read independently and must agree).
    for (c, r), s in ARROWS.items():
        rev = {REV[d] for d in s}
        assert rev == set(ARROWS[(6 - c, 7 - r)]), ((c, r), s)


def test_no_square_is_arrow_unattacked():
    # Justifies the "deadlock is unreachable" ruling: every square has some
    # neighbour whose arrow points at it, so an enemy Brain is always capturable.
    for (xc, xr) in ARROWS:
        attacked = False
        for d, (dc, dr) in DIRS.items():
            yc, yr = xc - dc, xr - dr
            if 0 <= yc < 7 and 0 <= yr < 8 and d in ARROWS[(yc, yr)]:
                attacked = True
                break
        assert attacked, (xc, xr)


def test_setup():
    g = Smess()
    s = g.initial_state()
    counts = {0: {}, 1: {}}
    for owner, ptype in s.board.values():
        counts[owner][ptype] = counts[owner].get(ptype, 0) + 1
    for p in (0, 1):
        assert counts[p] == {"ninny": 7, "numskull": 4, "brain": 1}, counts[p]
    assert s.board[(3, 0)] == (0, "brain")
    assert s.board[(3, 7)] == (1, "brain")
    for c in (1, 2, 4, 5):
        assert s.board[(c, 0)] == (0, "numskull")
        assert s.board[(c, 7)] == (1, "numskull")
    assert (0, 0) not in s.board and (6, 0) not in s.board   # a1, g1 empty
    assert g.current_player(s) == 0


def test_opening_move_count():
    g = Smess()
    s = g.initial_state()
    moves = g.legal_moves(s)
    assert len(moves) == 12, (len(moves), sorted(moves))
    # a2 Ninny (arrows N,S) has exactly its two one-steps, and no 2-step.
    a2 = {m for m in moves if m.startswith("0,1>")}
    assert a2 == {"0,1>0,2", "0,1>0,0"}, a2
    assert "0,1>0,3" not in moves           # Ninny cannot move two squares


def test_ninny_one_step_and_arrow_enforcement():
    g = Smess()
    # A lone Ninny on a1 (arrow {N} only) may step only to a2 — never E/W/S.
    s = SState(board={(0, 0): (0, "ninny"), (3, 0): (0, "brain"),
                      (3, 7): (1, "brain")}, to_move=0)
    frm_moves = [m for m in g.legal_moves(s) if m.startswith("0,0>")]
    assert frm_moves == ["0,0>0,1"], frm_moves


def test_numskull_slide_and_blocking():
    g = Smess()
    # Numskull on a1 (arrows {N}) slides the whole open a-file, only northwards.
    s = SState(board={(0, 0): (0, "numskull"), (6, 0): (0, "brain"),
                      (6, 7): (1, "brain")}, to_move=0)
    afile = sorted(m for m in g.legal_moves(s) if m.startswith("0,0>"))
    assert afile == [f"0,0>0,{r}" for r in range(1, 8)], afile

    # Numskull on d4 (all 8 arrows): blocked by own piece, captures enemy.
    board = {(3, 3): (0, "numskull"),          # d4
             (3, 5): (0, "ninny"),             # own on d6 -> N blocked before it
             (5, 3): (1, "ninny"),             # enemy on f4 -> E stops with capture
             (0, 0): (0, "brain"), (6, 7): (1, "brain")}
    s = SState(board=board, to_move=0)
    ms = set(g.legal_moves(s))
    assert "3,3>3,4" in ms                     # N to d5 (empty)
    assert "3,3>3,5" not in ms                 # cannot land on own d6
    assert "3,3>3,6" not in ms                 # cannot jump own piece
    assert "3,3>4,3" in ms                     # E to e4 (empty)
    assert "3,3>5,3" in ms                     # E captures enemy f4
    assert "3,3>6,3" not in ms                 # cannot pass the captured piece


def test_brain_capture_wins():
    g = Smess()
    # Red Ninny on c5 (arrows include E) captures the Blue Brain on d5.
    s = SState(board={(2, 4): (0, "ninny"), (3, 4): (1, "brain"),
                      (0, 0): (0, "brain")}, to_move=0)
    assert "2,4>3,4" in g.legal_moves(s)
    s2 = g.apply_move(s, "2,4>3,4")
    assert g.is_terminal(s2)
    assert g.returns(s2) == [1.0, -1.0]        # Red wins
    assert g.legal_moves(s2) == []


def test_two_brains_draw():
    g = Smess()
    # Red Brain on c5 captures the last non-Brain (Blue Ninny on d5); only the
    # two Brains remain -> official tie.
    s = SState(board={(2, 4): (0, "brain"), (3, 4): (1, "ninny"),
                      (0, 7): (1, "brain")}, to_move=0)
    s2 = g.apply_move(s, "2,4>3,4")            # capture the Ninny
    assert set(v[1] for v in s2.board.values()) == {"brain"}
    assert len(s2.board) == 2
    assert g.is_terminal(s2)
    assert g.returns(s2) == [0.0, 0.0]


def test_promotion():
    g = Smess()
    # Red Ninny a8 (arrows S,E) steps E onto b8 = a Blue Numskull start -> promotes.
    s = SState(board={(0, 7): (0, "ninny"), (3, 7): (1, "brain"),
                      (3, 0): (0, "brain")}, to_move=0)
    assert (1, 7) in PROMO[0]
    s2 = g.apply_move(s, "0,7>1,7")
    assert s2.board[(1, 7)] == (0, "numskull"), s2.board[(1, 7)]
    assert s2.no_progress == 0                 # promotion counts as progress

    # A Ninny landing on its OWN Numskull start does NOT promote. Red Ninny on
    # c1 (arrows include W) steps to b1 (a Red Numskull start).
    s = SState(board={(2, 0): (0, "ninny"), (3, 0): (0, "brain"),
                      (3, 7): (1, "brain")}, to_move=0)
    assert (1, 0) in NUMSKULL_START[0] and (1, 0) not in PROMO[0]
    s2 = g.apply_move(s, "2,0>1,0")
    assert s2.board[(1, 0)] == (0, "ninny"), s2.board[(1, 0)]


def test_deadlock_generator():
    g = Smess()
    # A board completely filled with one player's Ninnies leaves that player no
    # legal move (every target is own; no enemy to capture). Exercises the
    # no-move branch that guards the legal_moves invariant.
    board = {(c, r): (0, "ninny") for c in range(7) for r in range(8)}
    s = SState(board=board, to_move=0)
    assert g._raw_moves(s) == []


def test_serialize_roundtrip():
    g = Smess()
    s = g.initial_state()
    for mv in ["0,1>0,2", "0,6>0,5", "5,1>6,0"]:
        s = g.apply_move(s, mv)
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d
    # JSON-able
    import json
    json.loads(json.dumps(d))


def test_heuristic_shape():
    g = Smess()
    s = g.initial_state()
    h = g.heuristic(s)
    assert isinstance(h, list) and len(h) == 2
    assert abs(h[0] + h[1]) < 1e-9             # zero-sum
    # Force the rollout cutoff to catch a bare-float heuristic (payoffs[p]).
    from agp.mcts import MCTSBot
    MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(g, s)


def test_conformance_playouts():
    g = Smess()
    rng = random.Random(12345)
    for _ in range(120):
        s = g.initial_state()
        steps = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            assert moves, "non-terminal state with no legal moves"
            s = g.apply_move(s, rng.choice(moves))
            steps += 1
            assert steps <= 500
        assert g.legal_moves(s) == []
        ret = g.returns(s)
        assert len(ret) == 2 and all(x in (-1.0, 0.0, 1.0) for x in ret)
        assert ret in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0])


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("smess selftest: all tests passed")


if __name__ == "__main__":
    run()
