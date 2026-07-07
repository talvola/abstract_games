"""Standalone correctness anchor for Lotus (pure stdlib: agp + this game only).

Asserts:
  (a) board structure — 72 vertices (degree 3 or 4), symmetric adjacency, 7
      hexagons each a genuine 6-cycle (the lotus sites), and ``_has_lotus``;
  (b) flip-capture — an enemy group with no liberty is REVERSED to the mover's
      colour (not removed), with no cascade when the new group has a liberty;
  (c) cascading re-reversal — a capture that leaves the new group liberty-less
      is suicidal, so a SECOND reversal flips the whole group back;
  (d) legal suicide — a liberty-less own group (no capture) flips to the opponent;
  (e) lotus immunity — a group holding all 6 points of a hexagon is never flipped
      even at zero liberties;
  (f) the pass marker — passes nudge it toward the passer, it is capped at 7 per
      side, and it is added to the score of the side it rests on;
  (g) double-pass end + area scoring, with a genuine tie scored as a DRAW;
  (h) random playouts always terminate (stone count strictly increases).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.lotus.game import (  # noqa: E402
    Lotus, LState, WHITE, BLACK,
    POINTS, VERTS, ADJ, HEXES, MARKER_CAP,
    _group, _has_liberty, _has_lotus, _resolve, _score,
)


# --------------------------------------------------------------------------- #
def test_structure():
    assert len(POINTS) == 72 == len(set(POINTS)), len(POINTS)
    # every vertex has degree 3 or 4 (24 rim, 48 interior)
    degs = sorted(len(ADJ[p]) for p in POINTS)
    assert degs.count(3) == 24 and degs.count(4) == 48, degs
    # adjacency symmetric
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], (p, q)
    # exactly 7 lotus sites, each 6 distinct points forming a 6-cycle
    assert len(HEXES) == 7, len(HEXES)
    import math
    for h in HEXES:
        vs = list(h)
        assert len(vs) == 6, vs
        cx = sum(VERTS[v][0] for v in vs) / 6
        cy = sum(VERTS[v][1] for v in vs) / 6
        vs.sort(key=lambda v: math.atan2(VERTS[v][1] - cy, VERTS[v][0] - cx))
        for i in range(6):
            assert vs[(i + 1) % 6] in ADJ[vs[i]], vs
    # _has_lotus: a full hexagon is a lotus; any 5 of it is not
    h = next(iter(HEXES))
    assert _has_lotus(set(h))
    assert not _has_lotus(set(list(h)[:5]))


def test_flip_capture():
    """(b) White stone v21 hemmed to a single liberty v13; Black plays v13 ->
    v21 is REVERSED to Black (not removed) and unites — no cascade (the new
    group keeps a liberty)."""
    pos = {"v21": WHITE, "v25": BLACK, "v29": BLACK}
    after = _resolve(pos, "v13", BLACK)
    assert after["v21"] == BLACK, "captured stone must flip, not vanish"
    assert after["v13"] == BLACK
    assert WHITE not in after.values()          # the only white stone was reversed
    # v13 joined its capturers into one group with a liberty (no re-reversal)
    assert _has_liberty(after, _group(after, "v13"))


def test_cascade_re_reversal():
    """(c) Black plays v53, capturing the lone white v45 (its last liberty) — but
    the resulting united Black group has NO liberty, so the capture was suicidal
    and a SECOND reversal flips the whole group back to White."""
    pos = {v: WHITE for v in ("v29", "v33", "v41", "v45", "v57", "v61")}
    pos.update({"v37": BLACK, "v49": BLACK})
    # sanity: playing v53 genuinely captures white v45 (it loses its last liberty)
    probe = dict(pos); probe["v53"] = BLACK
    assert not _has_liberty(probe, _group(probe, "v45"))
    g = Lotus()
    st = LState(pos=dict(pos), to_move=BLACK)
    st2 = g.apply_move(st, "v53")
    # second reversal fired: the mover's own point ended up the ENEMY colour and
    # the whole united group (incl. the pre-existing black stones) flipped white
    assert st2.pos["v53"] == WHITE, st2.pos.get("v53")
    assert BLACK not in st2.pos.values(), "all stones re-reversed to White"


def test_legal_suicide():
    """(d) Black plays v36, fully ringed by (living) White with no capture -> the
    move is suicide, and suicide is legal: the stone flips to White."""
    pos = {v: WHITE for v in ("v28", "v32", "v40", "v44")}
    after = _resolve(pos, "v36", BLACK)
    assert after["v36"] == WHITE, "legal suicide flips own stone to opponent"
    assert all(after[v] == WHITE for v in ("v28", "v32", "v40", "v44"))


def test_lotus_immunity():
    """(e) A White hexagon (a lotus) is immune: reducing it to zero liberties by
    playing its last liberty does NOT flip it."""
    hexset = frozenset(("v27", "v28", "v35", "v36", "v43", "v44"))
    assert hexset in HEXES                        # a real lotus site
    ext = sorted({q for v in hexset for q in ADJ[v] if q not in hexset},
                 key=lambda s: int(s[1:]))
    p, others = ext[0], ext[1:]                   # leave one liberty (p), fill the rest
    pos = {v: WHITE for v in hexset}
    pos.update({x: BLACK for x in others})
    after = _resolve(pos, p, BLACK)               # Black fills the last liberty
    assert all(after[v] == WHITE for v in hexset), "lotus group must never flip"


def test_marker():
    g = Lotus()
    st = g.initial_state()
    assert st.marker == 0 and st.to_move == WHITE
    st = g.apply_move(st, "pass")                 # White passes -> toward White (+1)
    assert st.marker == 1 and st.to_move == BLACK and st.passes == 1
    st = g.apply_move(st, "pass")                 # Black passes -> back to 0, double pass
    assert st.marker == 0 and st.passes == 2 and g.is_terminal(st)
    # cap at +/-7
    capped = g.apply_move(LState(to_move=WHITE, marker=MARKER_CAP), "pass")
    assert capped.marker == MARKER_CAP
    capped = g.apply_move(LState(to_move=BLACK, marker=-MARKER_CAP), "pass")
    assert capped.marker == -MARKER_CAP
    # the marker is added to the resting side's score
    pos = {"v0": WHITE, "v1": WHITE, "v70": BLACK, "v71": BLACK}   # 2 stones each
    w0, b0 = _score(pos, 0)
    w5, b5 = _score(pos, 5)                        # +5 toward White
    assert w5 - w0 == 5 and b5 == b0, (w0, b0, w5, b5)


def test_double_pass_scoring_and_draw():
    g = Lotus()
    # genuine tie: one White + one Black stone, board otherwise a single neutral
    # empty region touching both colours -> territory 0/0, stones 1/1, marker 0.
    tie = LState(pos={"v0": WHITE, "v71": BLACK}, marker=0, passes=2)
    assert g.is_terminal(tie)
    assert g.returns(tie) == [0.0, 0.0], "an exact tie is a DRAW"
    # White ahead on stones -> White wins
    win = LState(pos={"v0": WHITE, "v1": WHITE, "v71": BLACK}, marker=0, passes=2)
    assert g.returns(win) == [1.0, -1.0]
    # marker can decide it: equal stones, marker toward Black
    mk = LState(pos={"v0": WHITE, "v71": BLACK}, marker=-2, passes=2)
    assert g.returns(mk) == [-1.0, 1.0]


def test_serialize_roundtrip():
    g = Lotus()
    st = g.initial_state()
    for mv in ("v0", "v1", "pass", "v10", "v20"):
        st = g.apply_move(st, mv)
    d = g.serialize(st)
    import json
    json.dumps(d)
    assert g.serialize(g.deserialize(d)) == d


def test_termination_random():
    g = Lotus()
    for seed in range(30):
        rng = random.Random(seed)
        st = g.initial_state()
        for _ in range(5000):
            if g.is_terminal(st):
                break
            mvs = g.legal_moves(st)
            assert mvs, "non-terminal with no moves"
            st = g.apply_move(st, rng.choice(mvs))
        assert g.is_terminal(st), f"seed {seed} did not terminate"
        r = g.returns(st)
        assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)


if __name__ == "__main__":
    test_structure()
    test_flip_capture()
    test_cascade_re_reversal()
    test_legal_suicide()
    test_lotus_immunity()
    test_marker()
    test_double_pass_scoring_and_draw()
    test_serialize_roundtrip()
    test_termination_random()
    print("lotus selftest: all tests passed")
