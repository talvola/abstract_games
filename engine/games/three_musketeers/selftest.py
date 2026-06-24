"""Pure-stdlib selftest for Three Musketeers. Run: python3 selftest.py

Anchors:
- exact starting position + opening legal-move count (8, hand-derived);
- a Musketeer capture removes the enemy and relocates the Musketeer;
- an enemy move only goes to an empty square;
- a constructed near-line position where a Musketeer is forced to align ->
  ENEMY wins (reached via apply_move);
- the Musketeers-win (no capture available, not collinear) reached via apply_move;
- a full random playout terminates with a decisive (or capped) result;
- serialize round-trips.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from games.three_musketeers.game import (  # noqa: E402
    ThreeMusketeers, TMState, MUSK, ENEMY, _musketeers_in_line,
)


def _musk_cells(s):
    return sorted(c for c, p in s.board.items() if p == MUSK)


def main():
    g = ThreeMusketeers()
    assert g.num_players == 2

    # --- starting position ----------------------------------------------------
    s0 = g.initial_state()
    assert len(s0.board) == 25, "all 25 squares occupied"
    assert sum(1 for p in s0.board.values() if p == MUSK) == 3
    assert sum(1 for p in s0.board.values() if p == ENEMY) == 22
    assert _musk_cells(s0) == [(0, 0), (2, 2), (4, 4)], "two opposite corners + centre"
    assert g.current_player(s0) == MUSK, "Musketeers move first"
    assert not g.is_terminal(s0)
    assert not _musketeers_in_line(s0.board)

    # opening legal-move count: (0,0)->2, (2,2)->4, (4,4)->2 = 8 captures
    moves = g.legal_moves(s0)
    assert len(moves) == 8, f"expected 8 opening moves, got {len(moves)}: {moves}"
    assert "2,2>3,2" in moves and "0,0>1,0" in moves and "4,4>3,4" in moves

    # --- a Musketeer capture removes the enemy & relocates the Musketeer ------
    s1 = g.apply_move(s0, "2,2>3,2")
    assert s1.board.get((3, 2)) == MUSK, "Musketeer moved onto target square"
    assert (2, 2) not in s1.board, "old Musketeer square now empty"
    assert len(s1.board) == 24, "one enemy captured (25 -> 24)"
    assert g.current_player(s1) == ENEMY

    # --- an enemy move only goes to an empty square ---------------------------
    e_moves = g.legal_moves(s1)
    assert e_moves, "enemy has moves"
    for m in e_moves:
        frm, to = m.split(">")
        fc = tuple(int(x) for x in frm.split(","))
        tc = tuple(int(x) for x in to.split(","))
        assert s1.board.get(fc) == ENEMY, "enemy moves an enemy piece"
        assert tc not in s1.board, "enemy only moves to an EMPTY square"
    # the now-empty (2,2) must be a legal enemy destination from a neighbour
    assert any(m.endswith(">2,2") for m in e_moves)

    # --- forced line -> ENEMY wins (via apply_move) ---------------------------
    # Two Musketeers already share row 0 at (0,0) and (4,0); third at (2,1) sits
    # above an enemy at (2,0). The only Musketeer with a capture is the one at
    # (2,1) capturing (2,0) -> all three land in row 0 -> enemy wins.
    board = {}
    musk = {(0, 0), (4, 0), (2, 1)}
    occupied = musk | {(2, 0)}  # the single enemy adjacent to a Musketeer
    for cc in musk:
        board[cc] = MUSK
    board[(2, 0)] = ENEMY
    # surround the two row-0 Musketeers and (2,1) so they have NO captures:
    # (0,0) neighbours (1,0),(0,1); (4,0) neighbours (3,0),(4,1); (2,1) others
    # leave all their other neighbours EMPTY so only (2,1)x(2,0) is legal.
    sf = TMState(board=board, to_move=MUSK)
    lm = g.legal_moves(sf)
    assert lm == ["2,1>2,0"], f"only one forced capture expected, got {lm}"
    sf2 = g.apply_move(sf, "2,1>2,0")
    assert _musketeers_in_line(sf2.board), "three Musketeers now share row 0"
    assert g.is_terminal(sf2)
    assert sf2.winner == ENEMY
    assert g.returns(sf2) == [-1.0, 1.0], "enemy wins"

    # --- Musketeers win: no capture available, not collinear (via apply_move) -
    # Set up a board where after the enemy's move it is the Musketeers' turn and
    # NO Musketeer has an adjacent enemy. Musketeers at (0,0),(2,2),(4,4) with a
    # lone enemy far from all of them; enemy moves it away to empty its only
    # adjacency to nothing... simplest: enemy at (0,4) (adjacent to no Musketeer),
    # to_move=ENEMY, enemy steps to (1,4); then Musketeers have zero captures.
    wb = {(0, 0): MUSK, (2, 2): MUSK, (4, 4): MUSK, (0, 4): ENEMY}
    sw = TMState(board=wb, to_move=ENEMY)
    assert not _musketeers_in_line(sw.board)
    # enemy steps to an empty square not adjacent to any Musketeer
    sw2 = g.apply_move(sw, "0,4>1,4")
    assert g.current_player(sw2) == MUSK
    assert g.legal_moves(sw2) == [], "no Musketeer capture available"
    assert g.is_terminal(sw2)
    assert not _musketeers_in_line(sw2.board)
    assert g.returns(sw2) == [1.0, -1.0], "Musketeers win on no-move"

    # --- serialize round-trip -------------------------------------------------
    for s in (s0, s1, sf2, sw2):
        d = s.serialize() if hasattr(s, "serialize") else g.serialize(s)
        s_re = g.deserialize(g.serialize(s))
        assert g.serialize(s_re) == g.serialize(s), "serialize round-trips"

    # render shape sanity
    rs = g.render(s0)
    assert rs["board"]["type"] == "square"
    assert rs["board"]["width"] == 5 and rs["board"]["height"] == 5

    # --- random playouts terminate decisively (or capped draw) ----------------
    rng = random.Random(12345)
    decisive = 0
    for _ in range(200):
        s = g.initial_state()
        steps = 0
        while not g.is_terminal(s):
            ms = g.legal_moves(s)
            assert ms, "non-terminal must have legal moves"
            s = g.apply_move(s, rng.choice(ms))
            steps += 1
            assert steps <= 1000, "playout should terminate well within cap"
        ret = g.returns(s)
        assert len(ret) == 2 and ret[0] == -ret[1]
        if ret != [0.0, 0.0]:
            decisive += 1
    assert decisive > 0, "random playouts should reach decisive terminals"

    print("three_musketeers selftest OK "
          f"(opening moves=8; {decisive}/200 random playouts decisive)")


if __name__ == "__main__":
    main()
