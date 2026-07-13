"""Squadro selftest — pure stdlib, deterministic where possible.

Anchors:
  * exact outbound/return speeds per line for both players (complementary);
  * deterministic obstacle-free movement by exact speed;
  * turnaround at the far edge (stops early, speed switches to return);
  * jump over a single enemy; over a contiguous group; jump-during-advance that
    forfeits remaining speed;
  * jumped enemies return to the correct base (outbound->start, returning->far);
  * finish + 4-of-5 win via apply_move;
  * honest draw backstops (threefold repetition; ply cap);
  * serialize round-trip;
  * 500 random playouts all terminate (+ result/length stats).

Run: PYTHONPATH=. python3 games/squadro/selftest.py
"""

import random

from games.squadro.game import (
    Squadro, SquadroState, WHITE_OUT, BLACK_OUT, FAR, WIN, PLY_CAP, REP_LIMIT,
)


def W(col, row, ret=False, fin=False):
    return {"col": col, "row": row, "ret": ret, "fin": fin}


def base_state(white, black, to_move=0):
    s = SquadroState(white=white, black=black, to_move=to_move)
    s.reps = {Squadro._sig(s): 1}
    return s


def main():
    g = Squadro()

    # ---- setup + speeds ------------------------------------------------
    s = g.initial_state()
    assert g.num_players == 2
    assert len(s.white) == 5 and len(s.black) == 5
    assert s.to_move == 0 and not g.is_terminal(s)
    # White on rows 1..5 at col 0; Black on cols 1..5 at row 0.
    assert [(p["col"], p["row"]) for p in s.white] == [(0, r) for r in range(1, 6)]
    assert [(p["col"], p["row"]) for p in s.black] == [(c, 0) for c in range(1, 6)]

    # speed table (outbound + complementary return) verified per line
    assert WHITE_OUT == {1: 3, 2: 1, 3: 2, 4: 1, 5: 3}
    assert BLACK_OUT == {1: 1, 2: 3, 3: 2, 4: 3, 5: 1}
    for k in range(1, 6):
        assert WHITE_OUT[k] + BLACK_OUT[k] == 4         # complementary
    for r in range(1, 6):
        wp = W(0, r)
        assert g._speed(0, wp) == WHITE_OUT[r]
        wp["ret"] = True
        assert g._speed(0, wp) == 4 - WHITE_OUT[r]
    for c in range(1, 6):
        bp = W(c, 0)
        assert g._speed(1, bp) == BLACK_OUT[c]
        bp["ret"] = True
        assert g._speed(1, bp) == 4 - BLACK_OUT[c]

    # opening: 5 legal moves, each a unique source cell
    lm = g.legal_moves(s)
    assert len(lm) == 5 and len(set(lm)) == 5, lm
    assert set(lm) == {f"0,{r}" for r in range(1, 6)}

    # ---- deterministic obstacle-free movement --------------------------
    # White row 1 (speed 3): 0 -> 3
    s1 = g.apply_move(s, "0,1")
    assert (s1.white[0]["col"], s1.white[0]["row"]) == (3, 1) and not s1.white[0]["ret"]
    assert s1.to_move == 1
    # Black col 2 (speed 3): row 0 -> 3
    s2 = g.apply_move(s1, "2,0")
    assert (s2.black[1]["col"], s2.black[1]["row"]) == (2, 3) and not s2.black[1]["ret"]
    # White row 2 (speed 1): 0 -> 1 ; row 3 (speed 2): 0 -> 2
    assert g.apply_move(s, "0,2").white[1]["col"] == 1
    assert g.apply_move(s, "0,3").white[2]["col"] == 2

    # ---- turnaround: stop at far edge, switch to return speed ----------
    # White row 1 (out 3): 0->3, then 3->6 (turns around, stops), speed becomes 1.
    t = base_state([W(0, 1)] + [W(0, r) for r in range(2, 6)],
                   [W(c, 0) for c in range(1, 6)], to_move=0)
    t1 = g.apply_move(t, "0,1")               # -> col 3
    assert t1.white[0]["col"] == 3 and not t1.white[0]["ret"]
    t1.to_move = 0
    t2 = g.apply_move(t1, "3,1")              # 3->6, turn around, stop
    p = t2.white[0]
    assert p["col"] == FAR and p["ret"] is True, p
    assert g._speed(0, p) == 4 - WHITE_OUT[1] == 1
    t2.to_move = 0
    t3 = g.apply_move(t2, f"{FAR},1")         # return speed 1: 6 -> 5
    assert t3.white[0]["col"] == 5 and t3.white[0]["ret"] is True

    # ---- jump a single enemy (outbound -> back to START base) ----------
    # White row 3 at col 1 (out speed 2); Black on col 2 at row 3 (outbound).
    st = base_state([W(0, 1), W(0, 2), W(1, 3), W(0, 4), W(0, 5)],
                    [W(1, 0), W(2, 3), W(3, 0), W(4, 0), W(5, 0)], to_move=0)
    r = g.apply_move(st, "1,3")
    assert (r.white[2]["col"], r.white[2]["row"]) == (3, 3), r.white[2]   # hopped to col 3
    assert (r.black[1]["col"], r.black[1]["row"]) == (2, 0)               # sent to start
    assert r.black[1]["ret"] is False

    # ---- jump-during-advance forfeits remaining speed ------------------
    # White row 5 (out 3) at col 1; enemy adjacent at col 2 -> lands col 3 (not 4).
    st = base_state([W(0, 1), W(0, 2), W(0, 3), W(0, 4), W(1, 5)],
                    [W(1, 0), W(2, 5), W(3, 0), W(4, 0), W(5, 0)], to_move=0)
    r = g.apply_move(st, "1,5")
    assert r.white[4]["col"] == 3, ("forfeit failed", r.white[4])         # 3, not 1+3=4
    assert (r.black[1]["col"], r.black[1]["row"]) == (2, 0)

    # ---- jump a CONTIGUOUS group (both knocked back, move stops) -------
    # White row 1 (out 3) at col 1; enemies at col 2 and col 3 (contiguous).
    st = base_state([W(1, 1), W(0, 2), W(0, 3), W(0, 4), W(0, 5)],
                    [W(1, 0), W(2, 1), W(3, 1), W(4, 0), W(5, 0)], to_move=0)
    r = g.apply_move(st, "1,1")
    assert r.white[0]["col"] == 4, r.white[0]                             # first free cell
    assert (r.black[1]["col"], r.black[1]["row"]) == (2, 0)               # both -> start
    assert (r.black[2]["col"], r.black[2]["row"]) == (3, 0)

    # ---- jumped enemy that was RETURNING -> back to TURNAROUND base ----
    # Black on col 2 is returning at row 3; White row 3 (out 2) at col 1 hops it.
    st = base_state([W(0, 1), W(0, 2), W(1, 3), W(0, 4), W(0, 5)],
                    [W(1, 0), W(2, 3, ret=True), W(3, 0), W(4, 0), W(5, 0)], to_move=0)
    r = g.apply_move(st, "1,3")
    assert (r.black[1]["col"], r.black[1]["row"]) == (2, FAR)             # far base, not 0
    assert r.black[1]["ret"] is True

    # ---- finish + 4-of-5 win via apply_move ----------------------------
    white = [W(0, 1, fin=True), W(0, 2, fin=True), W(0, 3, fin=True),
             W(1, 4, ret=True), W(0, 5)]          # 3 done; row-4 piece returning at col 1
    st = base_state(white, [W(c, 0) for c in range(1, 6)], to_move=0)
    assert not g.is_terminal(st)
    r = g.apply_move(st, "1,4")                   # returning: col 1 -> 0 -> finish
    assert r.white[3]["fin"] is True
    assert sum(1 for p in r.white if p["fin"]) == WIN
    assert r.winner == 0 and g.is_terminal(r)
    assert g.returns(r) == [1.0, -1.0]
    # finished piece drops out of legal moves for its owner
    st.to_move = 0
    assert "0,1" not in g.legal_moves(st) and "0,3" not in g.legal_moves(st)

    # ---- honest draw backstops ----------------------------------------
    # repetition: seed the resulting signature at REP_LIMIT-1 -> next apply draws.
    base = g.initial_state()
    nxt = g.apply_move(base, "0,1")
    seeded = g.initial_state()
    seeded.reps = {Squadro._sig(seeded): 1, Squadro._sig(nxt): REP_LIMIT - 1}
    drawn = g.apply_move(seeded, "0,1")
    assert drawn.draw is True and drawn.winner is None
    assert g.returns(drawn) == [0.0, 0.0]
    # ply cap: a move on the last allowed ply forces a draw.
    cap = base_state([W(0, r) for r in range(1, 6)],
                     [W(c, 0) for c in range(1, 6)], to_move=0)
    cap.plies = PLY_CAP - 1
    capped = g.apply_move(cap, "0,1")
    assert capped.draw is True and capped.plies == PLY_CAP

    # ---- serialize round-trip -----------------------------------------
    for probe in (g.initial_state(), s2, r, drawn):
        d = g.serialize(probe)
        back = g.serialize(g.deserialize(d))
        assert back == d, (d, back)
        import json
        json.loads(json.dumps(d))            # JSON-able

    # ---- 500 random playouts all terminate (+ stats) -------------------
    rng = random.Random(2024)
    wins = {0: 0, 1: 0}
    draws = 0
    lengths = []
    for _ in range(500):
        st = g.initial_state()
        n = 0
        while not g.is_terminal(st):
            mv = rng.choice(g.legal_moves(st))
            st = g.apply_move(st, mv)
            n += 1
            assert n <= PLY_CAP + 2, "did not terminate"
        lengths.append(n)
        if st.winner is None:
            draws += 1
        else:
            wins[st.winner] += 1
        # sanity: returns well-formed
        rr = g.returns(st)
        assert len(rr) == 2 and abs(sum(rr)) < 1e-9

    print("all tests passed")
    print(f"playouts=500  White={wins[0]} Black={wins[1]} draws={draws}")
    print(f"length: min={min(lengths)} max={max(lengths)} "
          f"avg={sum(lengths)/len(lengths):.1f}")


if __name__ == "__main__":
    main()
