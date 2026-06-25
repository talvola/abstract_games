"""Octi selftest — pure stdlib, deterministic. Run: python3 games/octi/selftest.py

Covers: starting setup, add-prong (supply down / prongs up), pronged step (and
NOT stepping a direction it lacks), jump over an adjacent pod with optional enemy
capture, base-reach win, capture-all win, serialize round-trip.
"""

from games.octi.game import (
    Octi, OctiState, BASES, PRONG_SUPPLY, DELTA, NAME_TO_DIR,
)


def _pod(owner, prongs=()):
    return {"owner": owner, "prongs": frozenset(prongs)}


def main():
    g = Octi()

    # --- starting setup ------------------------------------------------
    s = g.initial_state()
    assert g.num_players == 2
    assert len(s.pods) == 8, s.pods
    for cell in BASES[0]:
        assert s.pods[cell]["owner"] == 0 and s.pods[cell]["prongs"] == frozenset()
    for cell in BASES[1]:
        assert s.pods[cell]["owner"] == 1 and s.pods[cell]["prongs"] == frozenset()
    assert s.supply == [PRONG_SUPPLY, PRONG_SUPPLY]
    assert s.to_move == 0 and not g.is_terminal(s)

    # opening legal moves = only add-prong (pods have 0 prongs => can't move/jump).
    # 4 pods * 8 directions = 32 add-prong moves; no steps, no jumps.
    lm = g.legal_moves(s)
    assert len(lm) == 32, len(lm)
    assert all("=" in m and ">" not in m for m in lm), lm

    # --- add a prong: supply decrements, pod gains the direction --------
    s2 = g.apply_move(s, "1,1=N")
    assert s2.supply == [PRONG_SUPPLY - 1, PRONG_SUPPLY]
    assert NAME_TO_DIR["N"] in s2.pods[(1, 1)]["prongs"]
    assert s2.to_move == 1

    # --- pronged step: a pod with prong N (dir 0 => (0,+1)) can step +row,
    #     and CANNOT step a direction it lacks (e.g. E). ------------------
    st = OctiState(pods={(2, 2): _pod(0, {0})}, to_move=0)  # only prong N
    moves = g.legal_moves(st)
    # the one empty-step move is straight up (+row): 2,2 -> 2,3
    assert "2,2>2,3" in moves, moves
    # no eastward step (it lacks an E prong)
    assert "2,2>3,2" not in moves, moves
    after = g.apply_move(st, "2,2>2,3")
    assert (2, 3) in after.pods and (2, 2) not in after.pods

    # --- JUMP with optional enemy capture ------------------------------
    # pod (jumper) at (2,2) with prong N; enemy pod at (2,3); empty (2,4).
    sj = OctiState(pods={(2, 2): _pod(0, {0}), (2, 3): _pod(1, {2, 4})},
                   supply=[5, 5], to_move=0)
    jm = g.legal_moves(sj)
    # jump path 2,2>2,4 over the enemy => CAP and KEEP variants offered
    assert "2,2>2,4=CAP" in jm, jm
    assert "2,2>2,4=KEEP" in jm, jm
    # KEEP: enemy stays, jumper lands beyond
    keep = g.apply_move(sj, "2,2>2,4=KEEP")
    assert (2, 4) in keep.pods and keep.pods[(2, 4)]["owner"] == 0
    assert (2, 3) in keep.pods, "KEEP must leave the jumped enemy"
    assert (2, 2) not in keep.pods
    # CAP: enemy removed, its 2 prongs bank into mover's supply
    cap = g.apply_move(sj, "2,2>2,4=CAP")
    assert (2, 3) not in cap.pods, "CAP must remove the jumped enemy"
    assert cap.supply[0] == 5 + 2, cap.supply  # 2 banked prongs
    # capturing the lone enemy pod => capture-all WIN
    assert cap.winner == 0 and g.is_terminal(cap)
    assert g.returns(cap) == [1.0, -1.0]

    # jumping a FRIENDLY pod is allowed and never captures (no =CAP suffix)
    sf = OctiState(pods={(2, 2): _pod(0, {0}), (2, 3): _pod(0, {0}),
                         (5, 5): _pod(1)}, supply=[5, 5], to_move=0)
    fm = g.legal_moves(sf)
    assert "2,2>2,4" in fm, fm           # plain jump, no capture choice
    assert "2,2>2,4=CAP" not in fm, fm
    after_f = g.apply_move(sf, "2,2>2,4")
    assert (2, 3) in after_f.pods, "friendly jumped pod stays"

    # --- BASE-REACH WIN via apply_move ---------------------------------
    # player 0 pod adjacent to an enemy base, with the right prong, steps onto it.
    target = (5, 2)  # an enemy (player 1) base square
    assert target in BASES[1]
    # place a player-0 pod at (4,2) with an E prong (dir 2 => (+1,0)); base empty.
    sb = OctiState(pods={(4, 2): _pod(0, {2}), (0, 0): _pod(1)},
                   supply=[5, 5], to_move=0)
    win = g.apply_move(sb, "4,2>5,2")
    assert (5, 2) in win.pods and win.pods[(5, 2)]["owner"] == 0
    assert win.winner == 0 and g.is_terminal(win)
    assert g.returns(win) == [1.0, -1.0]

    # --- serialize round-trip (incl. prong sets + supplies) ------------
    s3 = g.apply_move(g.apply_move(s, "1,1=N"), "5,1=S")
    blob = g.serialize(s3)
    import json
    json.dumps(blob)  # must be JSON-able
    s4 = g.deserialize(blob)
    assert g.serialize(s4) == blob
    assert s4.pods[(1, 1)]["prongs"] == s3.pods[(1, 1)]["prongs"]
    assert s4.supply == s3.supply and s4.to_move == s3.to_move

    print("octi selftest: all assertions passed")


if __name__ == "__main__":
    main()
