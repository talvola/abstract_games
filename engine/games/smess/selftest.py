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
  * serialize round-trip; random playouts terminate; heuristic shape;
  * the complete AG#9 Favel-Handscomb sample game (89 plies) + opening trap
    replayed move-by-move (captures exactly on the ':' moves);
  * a full 3,080-state Brain-vs-Brain retrograde solve asserting the exact
    48 non-trivial forced-win classes (AG#9 puzzle p.29 prints 47 — see the
    errata comment at test_brain_vs_brain_solver_anchor).
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
    # b2/f7 are right-angle ELBOWS, not diagonals — verified 2026-07-18 from
    # AG#9 Diagram 1 at 600/1200 dpi AND chessvariants.com smess73.png: both
    # sources draw b2 with a vertical N shaft + horizontal E shaft (compare
    # b7/f2, whose NW/SE arrows have genuinely diagonal shafts).
    assert A(1, 1) == {"N", "E"}, A(1, 1)              # b2 (elbow: up + right)
    assert A(5, 6) == {"W", "S"}, A(5, 6)              # f7 (elbow: left + down)
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


# --------------------------------------------------------------------------
# Anchor 1: full replay of the AG#9 sample game (Rob Favel vs Kerry
# Handscomb, Abstract Games issue 9 p.8-9) plus the article's opening-trap
# line. Every published move must be legal in the engine, and a capture must
# occur exactly on the moves the article marks with ':' ('+' is annotation
# only). The game ends 45.c6:e8 Resign — resignation, so the engine position
# is NOT terminal; Blue still has his Brain (b8) plus two Ninnies. No move in
# either line triggers the official Ninny promotion rule, so the magazine
# score needs no reinterpretation under the full Parker Brothers rules.

_AG9_GAME = (
    "e2e3 a7a6 b2b3 a6b6 c2c3 c7c6 e3d4 e7e6 d2d3 c6d5 d3e3 g7g6 "
    "f2f3 g6f6 c1c2 d7c7 e1e2 c7c6 e2d2 e8e7 d4:d5 c6:d5 e3d4 b6c6 "
    "d4:d5 e6:d5 c3d4 f6e6 f1e1 c8c7 b1c1 c7d7 d4:d5 c6:d5 b3c3 b7c7 "
    "f3e3 c7c6 g2g3 f8g8 c3d4 g8:g3 d4:d5 g3g4+ e1e2 e6:d5 e3d4 e7:e2 "
    "d2:e2 d5:d4 d1e1 d7d5 c2:c6 b8c8 c6:d5 d4:d5 c1:c8 d8:c8 e2e8+ c8c7 "
    "a2a3 g4f3 a3a4 d5d4 e8d8 d4c3 a4a5 f7f6 a5b6 f6e6 d8e8 e6d5 "
    "e8e7+ c7c8 b6b7 f3f8 e7d7 d5d4 b7c7+ c8b8 d7d6 f8e8+ e1f1 d4e3 "
    "d6b6+ b8a8 b6c6+ a8b8 c6:e8"
)
_AG9_TRAP = "g2g3 c7c6 g3f3 e7e6 f1g1 f8g8"


def _replay(tokens):
    g = Smess()
    s = g.initial_state()
    promos = 0
    for i, tok in enumerate(tokens.split()):
        t = tok.rstrip("+")
        capture = ":" in t
        frm, to = t.split(":") if capture else (t[:2], t[2:])
        fc, fr = ord(frm[0]) - 97, int(frm[1]) - 1
        tc, tr = ord(to[0]) - 97, int(to[1]) - 1
        mv = f"{fc},{fr}>{tc},{tr}"
        assert mv in g.legal_moves(s), (i + 1, tok, mv)
        assert ((tc, tr) in s.board) == capture, (i + 1, tok, "capture flag")
        ptype = s.board[(fc, fr)][1]
        s = g.apply_move(s, mv)
        if ptype == "ninny" and s.board[(tc, tr)][1] == "numskull":
            promos += 1
    return g, s, promos


def test_ag9_sample_game_replay():
    g, s, promos = _replay(_AG9_GAME)
    assert promos == 0
    assert not g.is_terminal(s)                    # ended by resignation
    assert s.board[(1, 7)] == (1, "brain")         # Blue Brain on b8, doomed
    blue = sorted(p for o, p in s.board.values() if o == 1)
    assert blue == ["brain", "ninny", "ninny"], blue
    g, s, promos = _replay(_AG9_TRAP)
    assert promos == 0 and not g.is_terminal(s)
    assert s.board[(6, 7)] == (1, "numskull")      # trapped Numskull on g8


# --------------------------------------------------------------------------
# Anchor 2: full Brain-vs-Brain retrograde solve at the raw arrow-table
# level. Because BOTH Brains step one square along ABSOLUTE arrows, a
# position is just (mover's square, opponent's square): 56*55 = 3080 ordered
# states. Win = capture the enemy Brain; loopy/infinite play = not a win
# (this deliberately ignores the package's two-Brains-tie terminal so the
# anchor tests only the arrow table + one-step movement). Backward induction
# to a fixed point yields 266 mover-win states, of which 96 are NON-TRIVIAL
# (no immediate capture available); the board's only automorphism is 180 deg
# rotation and no state is self-symmetric, so that is exactly 48 classes.
#
# The AG#9 puzzle solution (p.29) prints 47 positions, hunted-Brain square
# first, then the winning mover's square. Solved here from scratch
# (2026-07-18, corrected b2={N,E}/f7={W,S} board), the true answer is 48
# classes and the printed list has three errata:
#   * MISSING b1b2 (mover b2 beats a Brain on b1). Forced 9-ply win, only
#     legal at all because b2's second arrow is E (not the misprinted SE):
#     1.b2c2 b1a1 2.c2b2 a1a2 3.b2b3 a2a1 4.b3a3 a1a2 5.a3xa2.
#   * MISSING b1d2 (also a 9-ply forced win).
#   * WRONGLY INCLUDES f4e3: the mover on e3 (four diagonal arrows) can
#     capture f4 immediately via NE, so the position is TRIVIAL by the
#     puzzle's own definition ("without an immediate capture"); and read the
#     other way round (mover f4, arrows {W} only) it is a dead draw.
# We assert the EXACT canonical class list, not just the count: the count
# alone is a weak anchor (the old misread-arrow board also yields a
# 47/48-ish count), while the exact list is a function of every arrow on the
# board. Canonical form: each class is written hunted-then-mover using the
# lexicographically smaller of the pair and its 180 deg rotation, which maps
# the printed f4* representatives to their b5* mirror images (f4c3=b5e6,
# f4c5=b5e4, f4c6=b5e3, f4d4=b5d5, f4d5=b5d4, f4e4=b5c5, f4e6=b5c3).

_BVB_CLASSES = (
    "a1a3 a1a4 a1a5 a1a7 a1b2 a1b3 a1b4 a1b5 a1b6 a1c1 a1c2 a1c3 a1c4 "
    "a1c5 a1c6 a1d2 a1d4 a1d5 a1e3 a1e4 a1e6 a2a4 a2a6 a2b2 a2b3 a2b4 "
    "a2c2 a2c4 a2c5 a2d3 a2d4 a2d5 a3a5 a3c3 a3c4 b1b2 b1d2 b5c3 b5c5 "
    "b5d4 b5d5 b5e3 b5e4 b5e6 d3c3 d3d5 d3e3 d3e4"
).split()


def test_brain_vs_brain_solver_anchor():
    squares = sorted(ARROWS)

    def on(c, r):
        return 0 <= c < 7 and 0 <= r < 8

    states = [(m, o) for m in squares for o in squares if m != o]
    succ, cap = {}, {}
    for m, o in states:
        nxt, c = [], False
        for d in ARROWS[m]:
            dc, dr = DIRS[d]
            mp = (m[0] + dc, m[1] + dr)
            if not on(*mp):
                continue
            if mp == o:
                c = True
            else:
                nxt.append((o, mp))
        cap[(m, o)] = c
        succ[(m, o)] = nxt

    WIN, LOSS = 1, -1
    val, dist = {}, {}
    for s in states:
        if cap[s]:
            val[s], dist[s] = WIN, 1
    changed = True
    while changed:
        changed = False
        for s in states:
            if cap[s] or not succ[s]:
                continue
            ns = succ[s]
            if any(val.get(n) == LOSS for n in ns):
                d = 1 + min(dist[n] for n in ns if val.get(n) == LOSS)
                if (val.get(s), dist.get(s)) != (WIN, d):
                    val[s], dist[s] = WIN, d
                    changed = True
            elif all(val.get(n) == WIN for n in ns):
                d = 1 + max(dist[n] for n in ns)
                if (val.get(s), dist.get(s)) != (LOSS, d):
                    val[s], dist[s] = LOSS, d
                    changed = True

    wins = [s for s in states if val.get(s) == WIN]
    nontriv = [s for s in states if val.get(s) == WIN and not cap[s]]
    assert len(states) == 3080
    assert len(wins) == 266, len(wins)
    assert len(nontriv) == 96, len(nontriv)

    def rot(sq):
        return (6 - sq[0], 7 - sq[1])

    def alg(sq):
        return f"{chr(97 + sq[0])}{sq[1] + 1}"

    classes = set()
    for m, o in nontriv:
        o2, m2 = min((o, m), (rot(o), rot(m)))
        classes.add(alg(o2) + alg(m2))
    assert sorted(classes) == _BVB_CLASSES, sorted(classes)

    # The errata positions, explicitly.
    b1, b2, d2 = (1, 0), (1, 1), (3, 1)
    assert val.get((b2, b1)) == WIN and dist[(b2, b1)] == 9   # 5.a3xa2
    assert val.get((d2, b1)) == WIN and dist[(d2, b1)] == 9
    e3, f4 = (4, 2), (5, 3)
    assert cap[(e3, f4)]                      # printed f4e3 is a TRIVIAL win
    assert val.get((f4, e3)) is None          # ...and mover-f4 is a dead draw


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("smess selftest: all tests passed")


if __name__ == "__main__":
    run()
