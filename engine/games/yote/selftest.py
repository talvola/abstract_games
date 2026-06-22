"""Yote correctness anchor (pure stdlib): drops from hand, the orthogonal
step/jump, the signature bonus removal after every capture (and the resulting
annihilation), capture being optional, and the win conditions including the
subtlety that an opponent with men still in hand is not yet annihilated."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.yote.game import Yote, YoteState  # noqa: E402

G = Yote()


def main():
    s = G.initial_state()
    assert s.hands == [12, 12] and not s.board
    assert len(G.legal_moves(s)) == 30 and all(">" not in m for m in G.legal_moves(s))

    # drop decrements the hand and passes the turn
    s2 = G.apply_move(s, "2,2")
    assert s2.board[(2, 2)] == 0 and s2.hands[0] == 11 and s2.to_move == 1

    # a plain step (distance 1) just passes the turn, no removal
    st = YoteState(board={(0, 0): 0}, hands=[0, 0], to_move=0)
    st2 = G.apply_move(st, "0,0>0,1")
    assert st2.board[(0, 1)] == 0 and not st2.removing and st2.to_move == 1

    # jump-capture -> bonus removal: same player must remove a second enemy
    st = YoteState(board={(1, 1): 0, (2, 1): 1, (4, 4): 1}, hands=[0, 0], to_move=0)
    st2 = G.apply_move(st, "1,1>3,1")
    assert (2, 1) not in st2.board and st2.removing and st2.to_move == 0
    assert G.legal_moves(st2) == ["4,4"]                 # only enemy men are removal targets
    st3 = G.apply_move(st2, "4,4")
    assert (4, 4) not in st3.board and st3.winner == 0   # bonus removal annihilates -> win

    # a capture that removes the enemy's last on-board man wins immediately (no
    # bonus removal needed, opponent has nothing in hand either)
    st = YoteState(board={(1, 1): 0, (2, 1): 1}, hands=[0, 0], to_move=0)
    assert G.apply_move(st, "1,1>3,1").winner == 0

    # capturing is OPTIONAL: when a jump exists, drops/steps are still offered
    st = YoteState(board={(1, 1): 0, (2, 1): 1}, hands=[5, 5], to_move=0)
    lm = G.legal_moves(st)
    assert "1,1>3,1" in lm and any(">" not in m for m in lm) and "1,1>1,2" in lm

    # opponent with 0 men on board but men still in hand is NOT annihilated
    st = YoteState(board={(0, 0): 0}, hands=[0, 3], to_move=1)   # P2 to move, can drop
    assert not G.is_terminal(st) and G.legal_moves(st)

    # win by leaving the opponent with no move (reached via apply_move, since the
    # winner is set as an event, not inferred from a hand-built position). P2's
    # lone man is boxed in (steps and jump-landings all blocked) with an empty
    # hand; after P1 makes any move, P2 is stuck and loses.
    board = {(0, 0): 1, (1, 0): 0, (0, 1): 0, (2, 0): 0, (0, 2): 0, (4, 5): 0}
    st = YoteState(board=board, hands=[0, 0], to_move=0)
    st2 = G.apply_move(st, "4,5>4,4")
    assert st2.winner == 0 and G.returns(st2) == [1.0, -1.0]

    assert G.serialize(G.deserialize(G.serialize(st3))) == G.serialize(st3)
    print("yote selftest OK")


if __name__ == "__main__":
    main()
