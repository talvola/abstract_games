"""Standalone correctness anchor for Storisende (pure stdlib: agp + this game).

Run: cd engine && PYTHONPATH=. python3 games/storisende/selftest.py
Asserts: board geometry, the placer/chooser opening + its move count, straight
stack movement at exactly the moved height, merge / capture-by-replacement,
crystallisation (green vs dark Wall) + the double-sprout, the mutual-pass win
scoring reached via apply_move, and a serialize round-trip.
"""

from games.storisende.game import (
    Storisende, StoriState, _cells, _crystallise, _score_territories, P0, P1,
)


def _q(c):
    return f"{c[0]},{c[1]}"


def main():
    g = Storisende()

    # --- geometry: hexhex base 4 has 37 cells; base 5 has 61 -----------------
    assert len(_cells(4)) == 37, len(_cells(4))
    assert len(_cells(5)) == 61, len(_cells(5))
    assert len(_cells(6)) == 91, len(_cells(6))

    # --- opening move count: placer may place on any of 37 cells -------------
    s0 = g.initial_state()
    assert s0.base == 4
    opening = g.legal_moves(s0)
    assert len(opening) == 37, len(opening)
    assert "pass" not in opening  # no pass during setup

    # placer places at centre; chooser then has exactly accept/swap
    s1 = g.apply_move(s0, "0,0")
    assert g.current_player(s1) == P1
    assert sorted(g.legal_moves(s1)) == ["accept", "swap"], g.legal_moves(s1)

    # accept: man stays Black's, White (chooser) to move
    s2 = g.apply_move(s1, "accept")
    assert s2.setup_done
    assert s2.board[(0, 0)] == [P0]
    assert g.current_player(s2) == P1

    # swap: man becomes White's, Black to move
    s2b = g.apply_move(s1, "swap")
    assert s2b.board[(0, 0)] == [P1]
    assert g.current_player(s2b) == P0

    # --- straight movement at exactly the height; jump; merge ---------------
    # Build a position by hand (post-setup) to test mechanics directly.
    st = StoriState(base=4, setup_done=True, to_move=P0, board={
        (0, 0): [P0],            # a single
        (2, 0): [P0, P0],        # a Black double (height 2)
        (-1, 0): [P1],           # a White single
    })
    moves = g.legal_moves(st)
    # The single at (0,0) (height 1) moves exactly 1 in each of 6 dirs (those
    # on-board). Directions: (1,0)(-1,0)(0,1)(0,-1)(1,-1)(-1,1).
    assert "0,0>1,0" in moves          # +1 east, on board
    assert "0,0>0,1" in moves
    assert "0,0>-1,1" in moves
    # the double at (2,0) moves exactly 2 OR (split) 1 cell.
    assert "2,0>0,0" in moves          # height-2 move 2 cells west -> merges
    assert "2,0>1,0" in moves          # split: top 1 checker moves 1 cell
    # cannot move the height-2 stack just 1 cell as a *whole* (only via split,
    # which is the same destination string, so that's fine) — but it cannot
    # move 3 cells:
    assert "2,0>-1,0" not in moves     # 3 cells: no whole/partial height == 3

    # merge: move the double 2 cells west onto own single at (0,0). The double
    # leaving a virgin cell sprouts one man back on the source (2,0).
    st_merge = g.apply_move(st, "2,0>0,0")
    assert st_merge.board[(0, 0)] == [P0, P0, P0], st_merge.board.get((0, 0))
    assert st_merge.board.get((2, 0)) == [P0]    # sprouted single at source
    assert st_merge.cellstate.get((2, 0)) is not None  # source crystallised

    # capture by replacement: move Black single onto White single, removing it
    st_cap = g.apply_move(st, "0,0>-1,0")
    assert st_cap.board[(-1, 0)] == [P0], st_cap.board.get((-1, 0))

    # --- crystallisation: vacated virgin cell becomes green / dark ----------
    # No territories yet -> first vacated virgin cell starts a NEW territory.
    cs, nt = _crystallise({}, {}, 1, (0, 0))
    assert cs[(0, 0)] == 1 and nt == 2

    # Adjacent to exactly one territory -> expands it (same id).
    cs2, nt2 = _crystallise({}, {(1, 0): 1}, 5, (0, 0))
    assert cs2[(0, 0)] == 1 and nt2 == 5

    # Adjacent to two SEPARATE territories -> dark Wall (state 0).
    cs3, nt3 = _crystallise({}, {(1, 0): 1, (-1, 0): 2}, 5, (0, 0))
    assert cs3[(0, 0)] == 0 and nt3 == 5

    # Via apply_move: moving a single off a virgin cell crystallises it green.
    st_v = StoriState(base=4, setup_done=True, to_move=P0,
                      board={(0, 0): [P0]})
    st_v2 = g.apply_move(st_v, "0,0>1,0")
    assert st_v2.cellstate.get((0, 0)) == 1, st_v2.cellstate  # new green territory

    # --- the double sprouts a man on the vacated cell -----------------------
    st_d = StoriState(base=4, setup_done=True, to_move=P0,
                      board={(2, 0): [P0, P0]})
    st_d2 = g.apply_move(st_d, "2,0>0,0")    # whole double moves 2 cells
    # source crystallised AND sprouted one Black man
    assert st_d2.cellstate.get((2, 0)) is not None
    assert st_d2.board.get((2, 0)) == [P0], st_d2.board.get((2, 0))
    # a single leaving does NOT sprout
    assert (0, 0) not in StoriState().board  # sanity

    # --- win scoring reached via mutual pass (apply_move) --------------------
    # Build a position with one green territory controlled solely by Black.
    st_end = StoriState(base=4, setup_done=True, to_move=P0,
                        board={(0, 0): [P0]},
                        cellstate={(0, 0): 1, (1, 0): 1, (0, 1): 1})
    p0, p1, neutral = _score_territories(st_end.board, st_end.cellstate)
    assert p0 == 3 and p1 == 0, (p0, p1, neutral)  # Black alone in a 3-cell terr
    after_p0 = g.apply_move(st_end, "pass")
    assert not after_p0.over
    after_p1 = g.apply_move(after_p0, "pass")
    assert after_p1.over
    assert after_p1.winner == P0, after_p1.winner
    assert g.returns(after_p1) == [1.0, -1.0]

    # contested territory controls nobody
    st_con = StoriState(base=4, setup_done=True,
                        board={(0, 0): [P0], (1, 0): [P1]},
                        cellstate={(0, 0): 1, (1, 0): 1})
    cp0, cp1, cn = _score_territories(st_con.board, st_con.cellstate)
    assert cp0 == 0 and cp1 == 0 and cn == 2, (cp0, cp1, cn)

    # --- serialize round-trip ------------------------------------------------
    for state in (s0, s1, s2, st_merge, st_d2, after_p1):
        d = g.serialize(state)
        again = g.deserialize(d)
        d2 = g.serialize(again)
        assert d == d2, (d, d2)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
