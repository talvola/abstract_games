"""Rolit correctness anchor (pure stdlib) — the platform's first 4-player game.
Checks the 4-seat structure, the Reversi flip (including a line of mixed opponent
colours flipping to the mover), the adjacent-placement requirement, strict turn
cycling, deterministic board-fill termination, and sole-leader-wins / tie-draw."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.rolit.game import Rolit, RolitState, _flips  # noqa: E402

G = Rolit()


def main():
    # --- 4-seat structure -------------------------------------------------
    assert G.num_players == 4
    s = G.initial_state()
    assert s.board == {(3, 3): 0, (4, 3): 1, (4, 4): 2, (3, 4): 3}, s.board
    assert len(G.returns(s)) == 4 and s.to_move == 0

    # --- flip brackets opponents (single) ---------------------------------
    assert _flips(s.board, 5, 3, 0) == [(4, 3)]        # P1 trapped between two P0
    s2 = G.apply_move(s, "5,3")
    assert s2.board[(4, 3)] == 0 and s2.to_move == 1

    # --- a line of MIXED opponent colours all flips to the mover ----------
    board = {(0, 0): 0, (1, 0): 1, (2, 0): 2, (3, 0): 3}
    st = RolitState(board=dict(board), to_move=0)
    assert set(_flips(st.board, 4, 0, 0)) == {(1, 0), (2, 0), (3, 0)}
    st2 = G.apply_move(st, "4,0")
    assert all(st2.board[(c, 0)] == 0 for c in range(5)), "mixed line should all flip to P0"

    # --- placement must touch an existing ball ----------------------------
    legal = set(G.legal_moves(s))
    assert "7,7" not in legal, "far-corner placement should be illegal (not adjacent)"
    assert all(any((c + dc, r + dr) in s.board for dc in (-1, 0, 1) for dr in (-1, 0, 1))
               for (c, r) in (tuple(int(x) for x in m.split(",")) for m in legal))

    # --- strict turn cycling 0,1,2,3 --------------------------------------
    s = G.initial_state()
    order = []
    for _ in range(8):
        order.append(s.to_move)
        s = G.apply_move(s, G.legal_moves(s)[0])
    assert order == [0, 1, 2, 3, 0, 1, 2, 3], order

    # --- deterministic termination + scoring ------------------------------
    import random
    rng = random.Random(7)
    s = G.initial_state()
    n = 0
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        n += 1
    assert n == 60 and len(s.board) == 64, (n, len(s.board))   # board fills in 60 moves
    assert sum(G._scores(s.board)) == 64

    # sole leader wins; a tie for first is a draw
    win = RolitState(board={(c, r): (0 if (c, r) == (0, 0) else 1)
                            for r in range(8) for c in range(8)}, to_move=0)
    assert G.returns(win) == [-1.0, 1.0, -1.0, -1.0]           # P2 has 63, sole leader
    tie = RolitState(board={(c, r): (0 if c < 4 else 1) for r in range(8) for c in range(8)}, to_move=0)
    assert G.returns(tie) == [0.0, 0.0, 0.0, 0.0]              # 32-32 tie -> draw

    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)
    print("rolit selftest OK")


if __name__ == "__main__":
    main()
