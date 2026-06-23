"""Sygo correctness anchor (pure stdlib, fast).

No published perft exists for Sygo, so the anchor is a set of baked rule asserts
pinning the parts that define the game (mindsports rules):
  (1) the board starts empty;
  (2) othelloanian capture: a surrounded enemy GROUP is REVERSED to the mover's
      colour and STAYS on the board (not removed) -- the whole connected group
      flips together (this is the Sygo twist vs Go's removal / Othello's line);
  (3) suicide is illegal, but a placement that captures (reverses) an enemy group
      and ends up alive IS legal;
  (4) territory scoring = stones + surrounded vacant points; two passes end the
      game and the majority decides; equal territory draws.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.sygo.game import (  # noqa: E402
    Sygo, SygoState, _score, _board_key, _resolve, WHITE, BLACK,
)

G = Sygo()


def main():
    # (1) empty start, White to move, pass always available --------------------
    s0 = G.initial_state(options={"size": 9})
    assert s0.board == {} and s0.to_move == WHITE
    assert "pass" in G.legal_moves(s0)

    # (2) othelloanian capture: a surrounded group FLIPS and stays --------------
    #  A 2-stone White group (1,0)-(1,1) with one remaining liberty at (1,2);
    #  it is otherwise ringed by Black. Black plays (1,2) -> White group has no
    #  liberty -> the WHOLE connected White group reverses to Black, on board.
    board = {
        (1, 0): WHITE, (1, 1): WHITE,             # the doomed White group
        (0, 0): BLACK, (2, 0): BLACK,
        (0, 1): BLACK, (2, 1): BLACK,
    }
    s = SygoState(size=9, board=dict(board), to_move=BLACK)
    s.history = frozenset({_board_key(board, 9)})
    assert "1,2" in G.legal_moves(s)
    s2 = G.apply_move(s, "1,2")
    # both former White stones are now Black, still present (reversed, not removed)
    assert s2.board.get((1, 0)) == BLACK and s2.board.get((1, 1)) == BLACK
    assert (1, 0) in s2.board and (1, 1) in s2.board, "group must stay on board"
    assert s2.board.get((1, 2)) == BLACK
    # connected-GROUP conversion: a stone NOT bracketed in a straight Othello line
    # (here (1,0), which is "behind" (1,1) relative to the played (1,2)) still flips
    assert s2.board.get((1, 0)) == BLACK

    # group reversal also flips a stone that Othello's line rule would NOT --------
    #  an L-shaped White group: (3,3)-(3,4)-(4,4). Black surrounds it; the bend at
    #  (4,4) is connected but off the straight line from the capturing stone.
    Lb = {
        (3, 3): WHITE, (3, 4): WHITE, (4, 4): WHITE,
        (2, 3): BLACK, (4, 3): BLACK, (3, 2): BLACK,
        (2, 4): BLACK, (5, 4): BLACK, (4, 5): BLACK, (3, 5): BLACK,
    }
    # last White liberty is (4,5)? recompute: vacant nbrs of the group =
    #  (3,3): (3,2)B,(2,3)B,(4,3)B,(3,4)W -> none vacant
    #  (3,4): (2,4)B,(3,3)W,(3,5)B,(4,4)W -> none vacant
    #  (4,4): (4,3)B,(3,4)W,(5,4)B,(4,5)B -> none vacant  => already dead, bad setup.
    #  Give it exactly one liberty at (4,5):
    Lb = {
        (3, 3): WHITE, (3, 4): WHITE, (4, 4): WHITE,
        (2, 3): BLACK, (4, 3): BLACK, (3, 2): BLACK,
        (2, 4): BLACK, (5, 4): BLACK, (3, 5): BLACK,
    }
    s = SygoState(size=9, board=dict(Lb), to_move=BLACK)
    s.history = frozenset({_board_key(Lb, 9)})
    s3 = G.apply_move(s, "4,5")
    for sq in [(3, 3), (3, 4), (4, 4)]:
        assert s3.board.get(sq) == BLACK, f"{sq} should have flipped to Black"

    # (3a) suicide is illegal --------------------------------------------------
    #  Black rings the empty point (0,0); White may not self-immolate there.
    ring = {(1, 0): BLACK, (0, 1): BLACK}
    s = SygoState(size=9, board=dict(ring), to_move=WHITE)
    s.history = frozenset({_board_key(ring, 9)})
    assert "0,0" not in G.legal_moves(s), "suicide must be illegal"

    # (3b) ...but the same shape IS legal when it captures (reverses) -----------
    #  A lone Black stone at (1,1) in atari; White rings it except (2,1). White
    #  plays (2,1): the placed stone alone has no liberty, but it reverses the
    #  Black stone, and the resulting White group is alive -> legal.
    cap = {(1, 1): BLACK, (0, 1): WHITE, (1, 0): WHITE, (1, 2): WHITE}
    s = SygoState(size=9, board=dict(cap), to_move=WHITE)
    s.history = frozenset({_board_key(cap, 9)})
    assert "2,1" in G.legal_moves(s), "capturing move must be legal despite atari"
    s4 = G.apply_move(s, "2,1")
    assert s4.board.get((1, 1)) == WHITE and (1, 1) in s4.board   # reversed, not gone

    # capturing-move legality is decided AFTER reversal (the source's exception)
    nb, rev, legal = _resolve(cap, 2, 1, WHITE, 9)
    assert legal and rev == 1

    # (4) territory scoring: stones + surrounded vacant points ------------------
    assert _score({}, 9) == (0, 0)
    assert _score({(2, 2): WHITE}, 5) == (25, 0)        # one stone owns all of 5x5
    split = {}
    for r in range(5):
        split[(0, r)] = split[(1, r)] = WHITE
        split[(3, r)] = split[(4, r)] = BLACK
    assert _score(split, 5) == (10, 10)                  # middle column is neutral

    # two passes end the game; the majority decides ----------------------------
    s = G.initial_state(options={"size": 5})
    s = G.apply_move(s, "2,2")                            # a lone White stone -> all White
    s = G.apply_move(s, "pass")
    s = G.apply_move(s, "pass")
    assert G.is_terminal(s) and G.returns(s) == [1.0, -1.0]

    # equal territory -> draw
    s = G.initial_state(options={"size": 5})
    s.board = dict(split)
    s.passes = 2
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0]

    # serialize round-trips -----------------------------------------------------
    s = G.apply_move(G.apply_move(G.initial_state(options={"size": 9}), "4,4"), "pass")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
