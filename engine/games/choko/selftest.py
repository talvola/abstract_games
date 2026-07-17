"""Choko correctness anchor (pure stdlib): the 5x5 board and 12-stick hands, the
drop-initiative rule (a voluntary drop forces the opponent's reply-drop; the
reply forces nothing; a move lifts the force), drop-or-move freedom mid-game,
the orthogonal step/jump, the signature second removal after every capture,
no capture on plain drops/steps, win by annihilation reached via apply_move,
the draw backstops, serialize round-trip, and seeded random playouts (with the
forced-player-always-has-a-stick invariant checked at every ply)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.choko.game import Choko, ChokoState  # noqa: E402

G = Choko()


def main():
    # ---- frozen opening: empty 5x5 board, 25 placements, nothing else ------
    s = G.initial_state()
    assert s.hands == [12, 12] and not s.board and not s.forced
    lm = G.legal_moves(s)
    assert len(lm) == 25 and all(">" not in m for m in lm)

    # ---- drop initiative --------------------------------------------------
    # P1's voluntary drop forces P2 to reply with a drop (24 bare cells only)
    s2 = G.apply_move(s, "2,2")
    assert s2.board[(2, 2)] == 0 and s2.hands[0] == 11 and s2.to_move == 1
    assert s2.forced
    lm2 = G.legal_moves(s2)
    assert len(lm2) == 24 and all(">" not in m for m in lm2)

    # the forced reply-drop forces NOTHING: P1 is then free to drop or move
    s3 = G.apply_move(s2, "2,3")
    assert s3.board[(2, 3)] == 1 and s3.hands[1] == 11 and not s3.forced
    lm3 = G.legal_moves(s3)
    assert any(">" in m for m in lm3) and any(">" not in m for m in lm3)
    assert "2,2>1,2" in lm3            # a step is offered mid-drop-phase

    # a MOVE (not a drop) leaves the opponent free too
    s4 = G.apply_move(s3, "2,2>1,2")
    assert not s4.forced and any(">" in m for m in G.legal_moves(s4))

    # ...and P2 may now seize the initiative by dropping, forcing P1
    s5 = G.apply_move(s4, "4,4")
    assert s5.forced and s5.to_move == 0
    assert all(">" not in m for m in G.legal_moves(s5))

    # ---- no capture on a plain drop or step -------------------------------
    # after the sequence above P2 has men adjacent to P1's traffic; counts never
    # changed except via hands
    assert len(s5.board) == 3 and s5.hands == [11, 10]
    st = ChokoState(board={(0, 0): 0, (0, 1): 1}, hands=[0, 0], to_move=0)
    st2 = G.apply_move(st, "0,0>1,0")           # step beside an enemy: no removal
    assert len(st2.board) == 2 and not st2.removing and st2.to_move == 1

    # ---- jump + the free second removal (scripted via apply_move) ---------
    a = G.initial_state()
    a = G.apply_move(a, "2,2")                  # P1 voluntary drop (forces P2)
    a = G.apply_move(a, "2,3")                  # P2 forced reply
    a = G.apply_move(a, "0,0")                  # P1 voluntary drop (forces P2)
    a = G.apply_move(a, "4,4")                  # P2 forced reply
    a = G.apply_move(a, "0,0>0,1")              # P1 moves -> P2 free
    a = G.apply_move(a, "4,4>4,3")              # P2 moves -> P1 free
    assert not a.forced
    assert "2,2>2,4" in G.legal_moves(a)        # jump over (2,3) to empty (2,4)
    b = G.apply_move(a, "2,2>2,4")
    assert (2, 3) not in b.board and b.removing and b.to_move == 0
    assert G.legal_moves(b) == ["4,3"]          # only enemy men are removal targets
    c = G.apply_move(b, "4,3")
    assert (4, 3) not in c.board and c.to_move == 1 and not c.removing
    assert c.winner is None                     # P2 still has 10 in hand
    assert G.legal_moves(c)                     # ...and can drop

    # jump that takes the last on-board man: no removal ply, game continues
    st = ChokoState(board={(1, 1): 0, (2, 1): 1}, hands=[0, 5], to_move=0)
    st2 = G.apply_move(st, "1,1>3,1")
    assert not st2.removing and st2.winner is None and st2.to_move == 1

    # ---- win by annihilation, via apply_move ------------------------------
    st = ChokoState(board={(1, 1): 0, (2, 1): 1, (4, 4): 1}, hands=[0, 0], to_move=0)
    st2 = G.apply_move(st, "1,1>3,1")
    assert st2.removing and G.legal_moves(st2) == ["4,4"]
    st3 = G.apply_move(st2, "4,4")
    assert st3.winner == 0 and G.returns(st3) == [1.0, -1.0]

    # capture of the very last enemy stick (board+hand empty) wins at once
    st = ChokoState(board={(1, 1): 0, (2, 1): 1}, hands=[0, 0], to_move=0)
    assert G.apply_move(st, "1,1>3,1").winner == 0

    # opponent with 0 on board but sticks in hand is NOT annihilated
    st = ChokoState(board={(0, 0): 0}, hands=[0, 3], to_move=1)
    assert not G.is_terminal(st) and G.legal_moves(st)

    # win by leaving the opponent with no move (reached via apply_move)
    board = {(0, 0): 1, (1, 0): 0, (0, 1): 0, (2, 0): 0, (0, 2): 0, (4, 4): 0}
    st = ChokoState(board=board, hands=[0, 0], to_move=0)
    st2 = G.apply_move(st, "4,4>4,3")
    assert st2.winner == 0 and G.returns(st2) == [1.0, -1.0]

    # ---- draw backstops ---------------------------------------------------
    st = ChokoState(board={(0, 0): 0, (4, 4): 1}, hands=[0, 0], to_move=0, since=49)
    st2 = G.apply_move(st, "0,0>0,1")           # 50th no-progress ply
    assert G.is_terminal(st2) and st2.winner is None and G.returns(st2) == [0.0, 0.0]
    st = ChokoState(board={(0, 0): 0, (4, 4): 1}, hands=[0, 0], to_move=0, ply=399)
    assert G.is_terminal(G.apply_move(st, "0,0>0,1"))       # hard ply cap

    # ---- serialize round-trip ---------------------------------------------
    assert G.serialize(G.deserialize(G.serialize(st3))) == G.serialize(st3)
    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)

    # ---- seeded random playouts to terminal + invariants ------------------
    rng = random.Random(7)
    results = []
    for _ in range(25):
        s = G.initial_state()
        while not G.is_terminal(s):
            # invariant: a forced player always holds a stick (voluntary drops
            # only happen from equal hands, so the reply is always available)
            if s.forced and not s.removing:
                assert s.hands[s.to_move] > 0
                assert all(">" not in m for m in G.legal_moves(s))
            mv = rng.choice(G.legal_moves(s))
            s = G.apply_move(s, mv)
            assert s.ply <= 402
        r = G.returns(s)
        assert len(r) == 2 and r in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0])
        results.append(tuple(r))
        h = G.heuristic(s)
        assert len(h) == 2 and abs(h[0] + h[1]) < 1e-9
    assert any(r != (0.0, 0.0) for r in results)   # decisive games occur

    print("choko selftest OK")


if __name__ == "__main__":
    main()
