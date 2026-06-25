"""Shobu correctness anchor — pure stdlib (imports only agp + this game).

Run: PYTHONPATH=. python3 games/shobu/selftest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.shobu.game import (  # noqa: E402
    Shobu, ShobuState, _key, _is_dark, _opp_colour_boards, _aggressive_result,
    HOME, DARK_BOARDS, SIZE, NBOARDS,
)

G = Shobu()


def _count(s, board, player):
    return sum(1 for v in s.boards[board].values() if v == player)


def _set_board(cells_spec):
    """cells_spec: dict (c,r)->player -> a board dict."""
    return dict(cells_spec)


def _state(boards, to_move=0, pending=None):
    return ShobuState(boards=tuple(boards), to_move=to_move, pending=pending)


def main() -> None:
    # --- Anchor 1: setup — 16 stones/side, 4 per board, correct rows. -------
    s0 = G.initial_state()
    assert G.current_player(s0) == 0
    for b in range(NBOARDS):
        assert _count(s0, b, 0) == 4, f"board {b} player0"
        assert _count(s0, b, 1) == 4, f"board {b} player1"
        # player 0 on row 0, player 1 on row 3
        for c in range(SIZE):
            assert s0.boards[b][(c, 0)] == 0
            assert s0.boards[b][(c, 3)] == 1
    total0 = sum(_count(s0, b, 0) for b in range(NBOARDS))
    total1 = sum(_count(s0, b, 1) for b in range(NBOARDS))
    assert total0 == 16 and total1 == 16

    # board colours: dark = {0,3}, each player owns one dark + one light home
    for p in (0, 1):
        home = HOME[p]
        assert len([b for b in home if _is_dark(b)]) == 1
        assert len([b for b in home if not _is_dark(b)]) == 1

    # --- Anchor 2: opening passive-move count + has full turns. -------------
    moves = G.legal_moves(s0)
    assert len(moves) > 0
    assert G._has_any_full_turn(s0)
    # Record the opening passive count for the report (printed at the end).
    opening_passive = len(moves)

    # --- Anchor 3: a legal passive move (no-push, empty path). --------------
    # On board 0, move a player-0 stone from (1,0) forward to (1,1) [+r].
    s = G.initial_state()
    pmove = f"{_key(0,1,0)}>{_key(0,1,1)}"
    assert pmove in G.legal_moves(s)
    s1 = G.apply_move(s, pmove)
    assert s1.pending is not None
    assert s1.to_move == 0  # same player keeps the turn
    assert s1.boards[0].get((1, 0)) is None
    assert s1.boards[0].get((1, 1)) == 0
    dc, dr, dist, pb = s1.pending
    assert (dc, dr, dist) == (0, 1, 1)
    assert pb == 0

    # --- Anchor 4: rejection of a passive move that would PUSH. -------------
    # Construct a board where (1,0)->(1,1) is blocked by a stone at (1,1).
    b0 = {(1, 0): 0, (1, 1): 1}            # home board (dark)
    b1 = {(0, 0): 0, (0, 3): 1}            # light home board, has own + enemy
    b2 = {(2, 1): 1}
    b3 = {(2, 1): 1}
    st = _state([b0, b1, b2, b3], to_move=0)
    try:
        G.apply_move(st, f"{_key(0,1,0)}>{_key(0,1,1)}")
        raise AssertionError("passive push should be rejected")
    except ValueError:
        pass

    # --- Anchor 5: a matching aggressive move on opposite-colour board. -----
    # passive on board 0 (DARK) => aggressive must be on a LIGHT board (1 or 2).
    assert _is_dark(0) and not _is_dark(1)
    s2 = s1  # pending = (0,1,1), passive board 0 (dark)
    agg_moves = G.legal_moves(s2)
    assert agg_moves, "should have aggressive moves"
    # every aggressive move is on a light board, same dir+dist
    for m in agg_moves:
        fb = int(m.split(">")[0].split(",")[0])
        assert not _is_dark(fb), f"aggressive on wrong colour board {fb}"
    # apply one: move a player-0 stone (0,0)->(0,1) on board 1 (light) [+r,1].
    am = f"{_key(1,0,0)}>{_key(1,0,1)}"
    assert am in agg_moves
    s3 = G.apply_move(s2, am)
    assert s3.pending is None
    assert s3.to_move == 1  # turn passes
    assert s3.boards[1].get((0, 0)) is None
    assert s3.boards[1].get((0, 1)) == 0

    # --- Anchor 6: a PUSH of a single opponent stone. -----------------------
    # Aggressive board (light=1): own stone at (0,0), opponent at (0,1).
    # Move +r dist1: pushes opponent (0,1)->(0,2); mover lands (0,1).
    b0p = {(1, 0): 0}                       # passive done conceptually
    b1p = {(0, 0): 0, (0, 1): 1}           # aggressive board
    res = _aggressive_result(b1p, 0, 0, 0, 1, 1, 0)
    assert res is not None
    dest, pushed_from, pushed_to = res
    assert dest == (0, 1)
    assert pushed_from == (0, 1)
    assert pushed_to == (0, 2)

    # apply via apply_move with proper pending
    st2 = _state([b0p, b1p, {(2, 2): 0}, {(2, 2): 0}], to_move=0,
                 pending=(0, 1, 1, 0))
    s_push = G.apply_move(st2, f"{_key(1,0,0)}>{_key(1,0,1)}")
    assert s_push.boards[1].get((0, 1)) == 0       # mover
    assert s_push.boards[1].get((0, 2)) == 1       # pushed opponent
    assert s_push.boards[1].get((0, 0)) is None

    # --- Anchor 6b: a 2-square push carries the opponent in front. ----------
    # mover (0,0) -> (0,2); opponent anywhere in the path ends ONE beyond the
    # destination, at (0,3).
    assert _aggressive_result({(0, 0): 0, (0, 1): 1}, 0, 0, 0, 1, 2, 0) == (
        (0, 2), (0, 1), (0, 3))
    assert _aggressive_result({(0, 0): 0, (0, 2): 1}, 0, 0, 0, 1, 2, 0) == (
        (0, 2), (0, 2), (0, 3))
    # if the landing square (0,3) is occupied, the 2-push is illegal.
    assert _aggressive_result(
        {(0, 0): 0, (0, 1): 1, (0, 3): 0}, 0, 0, 0, 1, 2, 0) is None
    # a 2-square push that shoves the opponent off the top edge.
    assert _aggressive_result({(0, 1): 0, (0, 2): 1}, 0, 1, 0, 1, 2, 0) == (
        (0, 3), (0, 2), None)

    # --- Anchor 7: rejection of pushing TWO stones. -------------------------
    # opponent at (0,1) AND a stone at (0,2): pushing (0,1)->(0,2) blocked.
    b1_two = {(0, 0): 0, (0, 1): 1, (0, 2): 1}
    assert _aggressive_result(b1_two, 0, 0, 0, 1, 1, 0) is None
    # two stones inside a dist-2 path also illegal
    b1_pathtwo = {(0, 0): 0, (0, 1): 1, (0, 2): 0}
    assert _aggressive_result(b1_pathtwo, 0, 0, 0, 1, 2, 0) is None

    # --- Anchor 8: rejection of pushing your OWN stone. ---------------------
    b1_own = {(0, 0): 0, (0, 1): 0}
    assert _aggressive_result(b1_own, 0, 0, 0, 1, 1, 0) is None

    # --- Anchor 9: a push that shoves an opponent stone OFF the board. ------
    # own stone at (0,2), opponent at (0,3) (top edge), move +r dist1:
    # opponent shoved to (0,4) which is off-board -> removed.
    b1_off = {(0, 2): 0, (0, 3): 1}
    res = _aggressive_result(b1_off, 0, 2, 0, 1, 1, 0)
    assert res is not None
    dest, pf, pt = res
    assert dest == (0, 3) and pf == (0, 3) and pt is None
    st3 = _state([{(1, 0): 0}, b1_off, {(2, 2): 0}, {(2, 2): 0}],
                 to_move=0, pending=(0, 1, 1, 0))
    s_off = G.apply_move(st3, f"{_key(1,0,2)}>{_key(1,0,3)}")
    assert s_off.boards[1].get((0, 3)) == 0        # mover landed
    # opponent removed entirely from board 1
    assert not any(v == 1 for v in s_off.boards[1].values())

    # --- Anchor 10: per-board ELIMINATION win via apply_move. ---------------
    # Board 1 (light): player 1 has exactly ONE stone at (0,3); pushing it off
    # empties player 1 from that board -> player 0 wins.
    # Set up a full passive+aggressive turn reaching this.
    home_dark = {(0, 0): 0}                 # board 0 (dark) home, passive here
    agg_light = {(0, 2): 0, (0, 3): 1}      # board 1 (light), only one P1 stone
    other2 = {(1, 1): 0, (1, 1): 0}         # board 2 — give P1 a stone so only b1 empties
    # ensure other boards still have player-1 stones (so the win is specifically board 1)
    b2 = {(0, 0): 0, (3, 3): 1}
    b3 = {(0, 0): 0, (3, 3): 1}
    start = _state([home_dark, agg_light, b2, b3], to_move=0)
    # passive: board 0 (0,0)->(0,1) [+r dist1]
    s_a = G.apply_move(start, f"{_key(0,0,0)}>{_key(0,0,1)}")
    assert s_a.pending == (0, 1, 1, 0)
    # aggressive: board 1 (0,2)->(0,3) pushing P1 off
    s_b = G.apply_move(s_a, f"{_key(1,0,2)}>{_key(1,0,3)}")
    assert not any(v == 1 for v in s_b.boards[1].values()), "board1 P1 emptied"
    assert G.is_terminal(s_b)
    assert s_b.winner == 0
    assert G.returns(s_b) == [1.0, -1.0]

    # --- Anchor 11: serialize round-trip (incl. pending). -------------------
    import json
    for st_ in (s0, s1, s_b):
        d = G.serialize(st_)
        json.dumps(d)
        st_rt = G.deserialize(d)
        assert G.serialize(st_rt) == d
    # also a pending state round-trips its pending tuple
    d1 = G.serialize(s1)
    assert d1["pending"] == [0, 1, 1, 0]
    assert G.deserialize(d1).pending == (0, 1, 1, 0)

    print(f"shobu selftest: all checks passed "
          f"(opening passive moves = {opening_passive})")


if __name__ == "__main__":
    main()
