"""Battle Sheep correctness anchor -- pure-stdlib, fast.

No published perft exists, so the anchor is a set of baked rule assertions:
 (1) a fixed hex board (32 hexes, 8 four-hex tiles, connected, 180-symmetric);
 (2) each player starts with a single 16-sheep stack on a perimeter edge hex;
 (3) a move SPLITS a stack -- take 1..h-1 off the TOP, leaving >=1, and slide
     in one of 6 straight hex directions AS FAR as it goes (last empty hex
     before an edge or another stack); height-1 cannot move;
 (4) no captures (total sheep on board is conserved, enemy stacks untouched);
 (5) the game ends when nobody can move; winner = MOST hexes, tie-break =
     largest single connected herd;
 plus a hand-built split-and-slide and an end-count.

Run:  PYTHONPATH=. python3 games/battle_sheep/selftest.py
"""

import sys

from games.battle_sheep.game import (
    BattleSheep, BSState, BOARD, DIRS, WIDTH, HEIGHT, SHEEP, START,
)


def main():
    g = BattleSheep()

    # (1) Fixed board: 32 hexes, 8 tiles of 4, connected, 180-symmetric.
    assert len(BOARD) == 32, len(BOARD)
    assert len(BOARD) % 4 == 0 and len(BOARD) // 4 == 8
    assert all((q, r) in BOARD for q in range(WIDTH) for r in range(HEIGHT))
    # connectivity
    start = next(iter(BOARD))
    seen, stk = {start}, [start]
    while stk:
        q, r = stk.pop()
        for dq, dr in DIRS:
            nb = (q + dq, r + dr)
            if nb in BOARD and nb not in seen:
                seen.add(nb)
                stk.append(nb)
    assert seen == set(BOARD), "board not connected"
    # 180-deg rotational symmetry about centre (3.5, 1.5)
    assert all((7 - q, 3 - r) in BOARD for (q, r) in BOARD), "not symmetric"

    # (2) Setup: each player one 16-stack on a perimeter (edge) hex.
    s0 = g.initial_state()
    assert s0.board[START[0]] == [0, SHEEP]
    assert s0.board[START[1]] == [1, SHEEP]
    assert sum(h for (_o, h) in s0.board.values()) == 2 * SHEEP
    for seat in (0, 1):
        sq = START[seat]
        deg = sum((sq[0] + dq, sq[1] + dr) in BOARD for dq, dr in DIRS)
        assert deg < 6, f"start {sq} is interior, not an edge hex"
    assert g.current_player(s0) == 0
    assert not g.is_terminal(s0)

    # (3) Split + slide-as-far. From (0,0) the +q direction (1,0) is clear to (7,0).
    dest = g._slide_dest(s0.board, (0, 0), (1, 0))
    assert dest == (7, 0), dest          # slides all the way to the far edge
    # legal moves include splitting any count 1..15 along that ray
    moves = g.legal_moves(s0)
    assert "0,0>7,0=1" in moves and "0,0>7,0=15" in moves
    assert "0,0>7,0=16" not in moves     # cannot take the whole stack (leave >=1)
    assert "0,0>7,0=0" not in moves      # must take >=1

    s1 = g.apply_move(s0, "0,0>7,0=5")
    assert s1.board[(0, 0)] == [0, 11]   # 11 left behind
    assert s1.board[(7, 0)] == [0, 5]    # 5 moved to the far hex
    assert g.current_player(s1) == 1
    # (4) no captures: total sheep conserved, enemy stack untouched
    assert sum(h for (_o, h) in s1.board.values()) == 2 * SHEEP
    assert s1.board[START[1]] == [1, SHEEP]

    # slide stops just before an occupied hex: put a blocker, slide into it.
    bst = BSState(board={(0, 1): [0, 4], (3, 1): [1, 2]}, to_move=0)
    d = g._slide_dest(bst.board, (0, 1), (1, 0))
    assert d == (2, 1), d                 # stops at (2,1), the hex before (3,1)
    # a height-1 stack cannot move
    one = BSState(board={(0, 0): [0, 1], (7, 3): [1, 16]}, to_move=0)
    assert g._has_move(one.board, 0) is False
    # blocked direction (first step off-board / occupied) yields no slide
    blocked = BSState(board={(0, 0): [0, 3], (1, 0): [1, 2]}, to_move=0)
    assert g._slide_dest(blocked.board, (0, 0), (1, 0)) is None   # (1,0) occupied
    assert g._slide_dest(blocked.board, (0, 0), (-1, 0)) is None  # off-board

    # round-trip serialise
    assert g.deserialize(g.serialize(s1)).board == s1.board

    # (5) End-count: hand-built terminal, most hexes wins.
    # Orange occupies 3 hexes, Blue 2 -- nobody can move (all height 1) -> Orange.
    term_board = {
        (0, 0): [0, 1], (2, 0): [0, 1], (4, 0): [0, 1],
        (7, 3): [1, 1], (5, 3): [1, 1],
    }
    assert g._hex_count(term_board, 0) == 3
    assert g._hex_count(term_board, 1) == 2
    assert g._has_move(term_board, 0) is False
    assert g._has_move(term_board, 1) is False
    assert g._score_winner(term_board) == 0

    # tie-break: equal hex count (2 each), larger connected herd wins.
    # Orange herd of 2 connected; Blue 2 hexes but disconnected (herd size 1).
    tie_board = {
        (0, 0): [0, 1], (1, 0): [0, 1],     # connected pair  -> herd 2
        (5, 0): [1, 1], (7, 3): [1, 1],     # separated       -> herd 1
    }
    assert g._hex_count(tie_board, 0) == g._hex_count(tie_board, 1) == 2
    assert g._largest_herd(tie_board, 0) == 2
    assert g._largest_herd(tie_board, 1) == 1
    assert g._score_winner(tie_board) == 0

    # genuine draw: equal hexes AND equal herds.
    draw_board = {
        (0, 0): [0, 1], (1, 0): [0, 1],
        (6, 3): [1, 1], (7, 3): [1, 1],
    }
    assert g._score_winner(draw_board) == -1

    # winner reachable via apply_move (not a hand-set terminal): play a tiny game
    # on a contrived state where one move ends it.
    almost = BSState(board={(0, 0): [0, 2], (7, 3): [1, 1]}, to_move=0)
    # Orange splits 1 off, slides somewhere; afterwards all stacks height 1 ->
    # neither can move -> terminal with Orange ahead on hexes.
    mv = g.legal_moves(almost)
    assert mv and "pass" not in mv
    end = g.apply_move(almost, mv[0])
    assert g.is_terminal(end)
    assert end.winner == 0           # Orange now has 2 hexes vs Blue 1
    r = g.returns(end)
    assert r == [1.0, -1.0], r

    # pass handling: a player with no move but opponent can move -> "pass".
    pass_board = {(0, 0): [0, 1], (3, 1): [1, 3]}
    ps = BSState(board=pass_board, to_move=0)   # Orange (height 1) cannot move
    assert g.legal_moves(ps) == ["pass"]

    print("SELFTEST OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("SELFTEST FAILED:", e)
        sys.exit(1)
