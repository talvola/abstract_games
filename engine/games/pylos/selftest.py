"""Pure-stdlib selftest for Pylos. Run: PYTHONPATH=. python3 games/pylos/selftest.py"""

from __future__ import annotations

import sys

from games.pylos.game import (
    Pylos, PylosState, BALLS_PER_PLAYER, APEX,
    _all_positions, _supporters, _key, _squares,
)


def _count(state):
    """Total spheres accounted for: on board + both reserves == 30."""
    return len(state.board) + sum(state.reserve)


def main():
    g = Pylos()

    # --- the 30 positions across 4 levels (16+9+4+1) -----------------------
    positions = _all_positions()
    assert len(positions) == 30, len(positions)
    by_level = {L: [p for p in positions if p[0] == L] for L in range(4)}
    assert [len(by_level[L]) for L in range(4)] == [16, 9, 4, 1]
    assert APEX == (3, 0, 0)

    # support sets: each level-L>=1 position rests on a 2x2 of level L-1.
    sup = _supporters(1, 0, 0)
    assert set(sup) == {(0, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1)}, sup
    assert _supporters(3, 0, 0) == ((2, 0, 0), (2, 1, 0), (2, 0, 1), (2, 1, 1))
    assert _supporters(0, 2, 3) == ()

    # --- supply conservation in the opening --------------------------------
    s = g.initial_state()
    assert s.reserve == [BALLS_PER_PLAYER, BALLS_PER_PLAYER]
    assert _count(s) == 30
    # opening = 16 base placements (no raise possible, both reserves full).
    opening = g.legal_moves(s)
    assert sorted(opening) == sorted(_key(0, c, r) for c in range(4) for r in range(4)), opening
    assert len(opening) == 16, len(opening)

    # --- a level-1 placement is illegal until its 4 supporters are present --
    # Fill three of the four supporters of (1,0,0); placing on it must be illegal.
    st = g.initial_state()
    for cell in ["0,0,0", "0,1,0", "0,0,1"]:
        # alternate players are fine; we just need the cells filled.
        st = _force_place(g, st, cell)
    assert "1,0,0" not in g.legal_moves(st), "level-1 target valid with only 3 supporters"
    st = _force_place(g, st, "0,1,1")        # 4th supporter
    assert "1,0,0" in g.legal_moves(st), "level-1 target not valid with all 4 supporters"
    assert _count(st) == 30

    # --- a square-completing placement enables a take-back of 1-2 free own ---
    # Build a same-colour 2x2 at level 0 for player 0, completed by the 4th ball.
    st = PylosState(board={"0,0,0": 0, "0,1,0": 0, "0,0,1": 0},
                    reserve=[BALLS_PER_PLAYER - 3, BALLS_PER_PLAYER], to_move=0)
    assert not st.pending
    ns = g.apply_move(st, "0,1,1")           # completes the all-0 square
    assert ns.pending, "square did not trigger take-back sub-turn"
    assert ns.to_move == 0, "take-back must stay with the same player"
    tb = g.legal_moves(ns)
    assert "done" in tb
    # all four square balls are free (nothing above) -> 4 take options.
    take_opts = sorted(m for m in tb if m.startswith("take:"))
    assert len(take_opts) == 4, take_opts
    # take back one, then a second is offered, then 'done' ends the turn.
    after1 = g.apply_move(ns, "take:0,1,1")
    assert after1.pending and after1.to_move == 0 and after1.taken == 1
    assert "0,1,1" not in after1.board       # returned to reserve
    after2 = g.apply_move(after1, "take:0,0,0")
    assert not after2.pending and after2.to_move == 1 and after2.taken == 0
    assert "0,0,0" not in after2.board
    assert _count(after2) == 30
    # taking exactly two ends the turn automatically (no 'done' needed).
    again = g.apply_move(ns, "take:0,1,1")
    again = g.apply_move(again, "take:0,1,0")
    assert again.to_move == 1 and not again.pending
    # or end early with 'done' after one take.
    early = g.apply_move(g.apply_move(ns, "take:0,1,1"), "done")
    assert early.to_move == 1 and not early.pending
    # take-back is fully optional: 'done' immediately keeps all four.
    keep = g.apply_move(ns, "done")
    assert keep.to_move == 1 and not keep.pending and len(keep.board) == 4

    # --- a non-square placement does NOT trigger a take-back ----------------
    st2 = PylosState(board={"0,0,0": 0, "0,1,0": 1, "0,0,1": 0},
                     reserve=[BALLS_PER_PLAYER - 2, BALLS_PER_PLAYER - 1], to_move=0)
    ns2 = g.apply_move(st2, "0,1,1")         # square is NOT all-0
    assert not ns2.pending and ns2.to_move == 1

    # --- a RAISE: a free own sphere up a level, not a supporter -------------
    # Fill a 2x2 of level-0 (mixed owners), plus an extra free own sphere to raise.
    board = {"0,0,0": 0, "0,1,0": 1, "0,0,1": 1, "0,1,1": 0, "0,2,0": 0}
    st3 = PylosState(board=dict(board), reserve=[BALLS_PER_PLAYER - 3,
                     BALLS_PER_PLAYER - 2], to_move=0)
    moves = g.legal_moves(st3)
    # (0,2,0) is player 0's, free, and NOT a supporter of (1,0,0) -> can raise it.
    assert "0,2,0>1,0,0" in moves, [m for m in moves if ">" in m]
    # (0,0,0) IS a supporter of (1,0,0) -> may not raise itself onto it.
    assert "0,0,0>1,0,0" not in moves
    raised = g.apply_move(st3, "0,2,0>1,0,0")
    assert "0,2,0" not in raised.board and raised.board.get("1,0,0") == 0
    # a raise does not change reserve counts.
    assert raised.reserve == st3.reserve
    assert _count(raised) == 30

    # --- the apex placement WINS (reached via apply_move) -------------------
    # Stack a full sub-pyramid under the apex, owned by player 0, then place apex.
    full = {}
    for (L, c, r) in _all_positions():
        if L < 3:                            # fill levels 0,1,2 entirely
            full[_key(L, c, r)] = 0
    used = len(full)
    st4 = PylosState(board=full, reserve=[BALLS_PER_PLAYER, BALLS_PER_PLAYER],
                     to_move=0)
    assert "3,0,0" in g.legal_moves(st4)
    win = g.apply_move(st4, "3,0,0")
    assert g.is_terminal(win), "apex placement not terminal"
    assert win.winner == 0, win.winner
    assert g.returns(win) == [1.0, -1.0]

    # winning by RAISING onto the apex also works.
    full2 = dict(full)
    # free a level-0 own sphere to raise: remove one level-1 stack? Instead place
    # an extra owned free sphere is impossible (board full); raise a free level-2
    # sphere... level-2 are supporters of apex, so use a free level-0 corner that
    # is not under anything occupied. Easiest: clear one level-1 to free a level-0.
    del full2["1,0,0"]                        # frees its four level-0 supporters
    st5 = PylosState(board=full2, reserve=[1, 1], to_move=0)
    # (0,0,0) is now free and is NOT a supporter of the apex (apex supporters are
    # level-2). Raising it onto the apex must win.
    assert "0,0,0>3,0,0" in g.legal_moves(st5), [m for m in g.legal_moves(st5) if ">" in m]
    win2 = g.apply_move(st5, "0,0,0>3,0,0")
    assert g.is_terminal(win2) and win2.winner == 0

    # --- serialize round-trip ----------------------------------------------
    for state in (s, ns, after2, raised, win):
        d = g.serialize(state)
        again2 = g.deserialize(d)
        assert g.serialize(again2) == d, "serialize did not round-trip"
        # JSON-able
        import json
        json.dumps(d)

    print("pylos selftest: all tests passed")


def _force_place(g, st, cell):
    """Place ``cell`` for the current mover regardless of square side effects,
    advancing to a clean (non-pending) state for the next placement test."""
    ns = g.apply_move(st, cell)
    if ns.pending:                            # if it made a square, just 'done'
        ns = g.apply_move(ns, "done")
    return ns


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("pylos selftest FAILED:", e)
        sys.exit(1)
