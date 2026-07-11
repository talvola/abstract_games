"""Standalone correctness self-test for Bobail (run from ``engine``):

    PYTHONPATH=. python3 games/bobail/selftest.py

Pure-stdlib (imports only ``agp`` + this game). Anchors (all rules cross-checked
against BGA's Gamehelpbobail, the French rule sheet PDF, dragono.fr and 1234.pm):

  1. Setup: 5 pieces per player on rows 0/4, Bobail on the centre, Red first.
  2. First-turn exception: the opening turn is a piece slide ONLY (no Bobail step).
  3. Bobail step: exactly one king-step to an EMPTY square; sub-move encoding is
     unambiguous (bobail-phase moves start on the Bobail square, piece-phase
     moves never do).
  4. Slides are exact: a piece moves as far as it can go — the full-distance
     square is legal, stopping early is not; edge / piece / Bobail all block.
  5. Immediate win: stepping the Bobail onto your own home row ends the game
     mid-turn (no piece slide happens), row owner wins.
  6. Win attribution: forced to step the Bobail onto the OPPONENT's home row
     -> the OPPONENT wins.
  7. Trapped Bobail reached via apply_move: after a full turn that surrounds the
     Bobail, the opponent (to move, unable to step it) loses.
  8. Honest-draw backstops: threefold repetition of a turn-start position and
     the PLY_CAP both end in a [0,0] draw.
  9. serialize/deserialize round-trips.
 10. 500 random playouts all terminate within the cap; result stats printed.

Prints "SELFTEST OK" and exits 0 on success; raises on failure.
"""

import random

from games.bobail.game import Bobail, BobState, PLY_CAP, _poskey


def state(pieces, bobail, to_move, phase, ply=10, seen=None, draw=False):
    return BobState(pieces=dict(pieces), bobail=bobail, to_move=to_move,
                    phase=phase, ply=ply, seen=dict(seen or {}), draw=draw)


def main():
    g = Bobail()

    # --- 1. setup ----------------------------------------------------------
    s0 = g.initial_state()
    assert s0.bobail == (2, 2)
    assert s0.to_move == 0 and s0.phase == "piece"
    for c in range(5):
        assert s0.pieces[(c, 0)] == 0 and s0.pieces[(c, 4)] == 1
    assert len(s0.pieces) == 10
    assert not g.is_terminal(s0)

    # --- 2. first-turn exception: piece slides only ------------------------
    ms = g.legal_moves(s0)
    assert ms, "opening turn must have moves"
    for m in ms:
        frm = tuple(map(int, m.split(">")[0].split(",")))
        assert frm != s0.bobail, f"first turn must not move the Bobail: {m}"
        assert s0.pieces.get(frm) == 0, f"first turn must slide a Red piece: {m}"

    # --- 3. Bobail one-step + unambiguous encoding ------------------------
    s1 = g.apply_move(s0, ms[0])
    assert s1.to_move == 1 and s1.phase == "bobail" and not g.is_terminal(s1)
    bms = g.legal_moves(s1)
    assert bms
    occ = set(s1.pieces) | {s1.bobail}
    for m in bms:
        frm, to = (tuple(map(int, x.split(","))) for x in m.split(">"))
        assert frm == s1.bobail, f"bobail-phase move must start on the Bobail: {m}"
        assert max(abs(to[0] - frm[0]), abs(to[1] - frm[1])) == 1, m
        assert to not in occ, f"Bobail must step to an EMPTY square: {m}"
    s2 = g.apply_move(s1, bms[0])
    assert s2.to_move == 1 and s2.phase == "piece", "same player slides a piece next"
    for m in g.legal_moves(s2):
        frm = tuple(map(int, m.split(">")[0].split(",")))
        assert frm != s2.bobail and s2.pieces.get(frm) == 1

    # --- 4. slide exactness -------------------------------------------------
    # Red piece a1=(0,0); Blue piece a5=(0,4); Bobail c3=(2,2). Slides from a1:
    #   N  blocked by the Blue piece  -> lands (0,3), not (0,1)/(0,2)
    #   E  clear to the edge          -> lands (4,0)
    #   NE blocked by the Bobail      -> lands (1,1)
    s = state({(0, 0): 0, (0, 4): 1}, (2, 2), 0, "piece")
    got = set(g.legal_moves(s))
    assert got == {"0,0>0,3", "0,0>4,0", "0,0>1,1"}, got
    assert "0,0>0,1" not in got and "0,0>2,2" not in got

    # --- 5. immediate win on own home row (mid-turn) ------------------------
    s = state({(0, 3): 0, (4, 4): 1}, (2, 1), 0, "bobail")
    assert "2,1>2,0" in g.legal_moves(s)
    t = g.apply_move(s, "2,1>2,0")
    assert g.is_terminal(t), "Bobail on Red's home row ends the game instantly"
    assert t.phase == "piece" and not g.legal_moves(t), "no piece slide happens"
    assert g.returns(t) == [1.0, -1.0]

    # --- 6. forced onto the OPPONENT's row -> opponent wins ------------------
    # Red to step the Bobail at c4=(2,3); every non-row-4 neighbour is occupied,
    # so Red must deliver it to Blue's home row.
    s = state({(1, 3): 0, (3, 3): 1, (1, 2): 0, (2, 2): 1, (3, 2): 0,
               (0, 0): 0, (4, 0): 1}, (2, 3), 0, "bobail")
    ms = g.legal_moves(s)
    assert ms and all(m.split(">")[1].endswith(",4") for m in ms), ms
    t = g.apply_move(s, ms[0])
    assert g.is_terminal(t) and g.returns(t) == [-1.0, 1.0], \
        "row owner (Blue) wins even though Red moved the Bobail"

    # --- 7. trapped Bobail via apply_move ------------------------------------
    # Red steps the Bobail b3->a3, then slides e3 west (full distance) to b3,
    # sealing the Bobail against the edge: a2/a4/b2/b3/b4 all occupied.
    s = state({(0, 1): 1, (0, 3): 1, (1, 1): 0, (1, 3): 0,
               (4, 2): 0, (4, 4): 1}, (1, 2), 0, "bobail")
    assert "1,2>0,2" in g.legal_moves(s)
    t = g.apply_move(s, "1,2>0,2")
    assert not g.is_terminal(t)
    assert "4,2>1,2" in g.legal_moves(t), g.legal_moves(t)
    u = g.apply_move(t, "4,2>1,2")
    assert u.to_move == 1 and u.phase == "bobail"
    assert g.is_terminal(u), "Blue cannot step the Bobail -> game over"
    assert g.returns(u) == [1.0, -1.0], "the trapper (Red) wins"

    # --- 8a. threefold repetition -> honest draw -----------------------------
    base = state({(0, 0): 0, (0, 4): 1, (4, 0): 0, (4, 4): 1}, (2, 2), 0, "bobail")
    probe = g.apply_move(g.apply_move(base, "2,2>2,1"), "0,0>3,3")
    key = _poskey(probe)
    assert probe.seen == {key: 1} and not g.is_terminal(probe)
    seeded = state(base.pieces, base.bobail, 0, "bobail", ply=base.ply,
                   seen={key: 2})
    rep = g.apply_move(g.apply_move(seeded, "2,2>2,1"), "0,0>3,3")
    assert rep.draw and g.is_terminal(rep) and g.returns(rep) == [0.0, 0.0]

    # --- 8b. ply cap -> honest draw ------------------------------------------
    s = state({(0, 0): 0, (0, 4): 1}, (2, 2), 0, "piece", ply=PLY_CAP - 1)
    t = g.apply_move(s, "0,0>4,0")
    assert t.ply == PLY_CAP and t.draw and g.is_terminal(t)
    assert g.returns(t) == [0.0, 0.0]

    # --- 9. serialize round-trip ---------------------------------------------
    for st in (s0, s1, s2, probe, rep):
        d = g.serialize(st)
        assert g.serialize(g.deserialize(d)) == d

    # --- 10. termination + stats ----------------------------------------------
    rng = random.Random(20260711)
    results = {"red": 0, "blue": 0, "draw": 0}
    by_how = {"home": 0, "trapped": 0}
    lengths = []
    for _ in range(500):
        st = g.initial_state()
        while not g.is_terminal(st):
            assert st.ply <= PLY_CAP
            mvs = g.legal_moves(st)
            assert mvs, "non-terminal state must have moves"
            st = g.apply_move(st, rng.choice(mvs))
        r = g.returns(st)
        lengths.append(st.ply)
        if r[0] > 0:
            results["red"] += 1
        elif r[1] > 0:
            results["blue"] += 1
        else:
            results["draw"] += 1
        if r[0] != r[1]:
            by_how["home" if st.bobail[1] in (0, 4) else "trapped"] += 1
    print(f"playouts: {results}, wins by {by_how}, "
          f"plies min/avg/max = {min(lengths)}/{sum(lengths)/len(lengths):.1f}/{max(lengths)}")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
