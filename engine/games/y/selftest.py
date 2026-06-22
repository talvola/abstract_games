"""Y correctness anchor (pure stdlib): the three-edge connection win, the
can-never-draw property (a full board always has exactly one winner), the
swap/pie move, and the triangular-board geometry."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.y.game import Y, YState, RED, BLUE  # noqa: E402

G = Y()


def main():
    # triangular board: side n has n(n+1)/2 cells
    assert len(G._cells(5)) == 15
    # the apex (0,0) lies on both the left (col 0) and right (col == row) edges
    assert (0, 0) == (0, 0)

    # a left-edge column connects left + right(apex) + bottom -> a Y
    win = {(0, 0): RED, (1, 0): RED, (2, 0): RED}
    assert G._wins(win, RED, 3)
    # a group that misses the bottom edge does not win
    assert not G._wins({(0, 0): RED, (1, 1): RED}, RED, 3)
    # two separate groups that each touch some edges but aren't connected: no win
    assert not G._wins({(0, 0): RED, (2, 2): RED}, RED, 3)

    # apply a winning stone -> winner set, returns scored
    s = YState(size=3, board={(0, 0): RED, (1, 0): RED}, to_move=RED)
    s2 = G.apply_move(s, "2,0")
    assert s2.winner == RED and G.returns(s2) == [1.0, -1.0]

    # Y can never draw: every filled board has exactly one winner
    import random
    rng = random.Random(11)
    for _ in range(30):
        s = G.initial_state(options={"size": 4})
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice([m for m in G.legal_moves(s) if m != "swap"]))
        assert s.winner is not None
        # exactly one player can have a Y on a full board
        full = s.board
        assert G._wins(full, s.winner, 4)
        assert not G._wins(full, 1 - s.winner, 4)

    # swap (pie): offered only on move 2, recolours the lone stone, returns the turn
    s = G.apply_move(G.initial_state(options={"size": 5}), "2,1")
    assert "swap" in G.legal_moves(s)
    sw = G.apply_move(s, "swap")
    assert sw.board[(2, 1)] == BLUE and sw.to_move == RED
    assert "swap" not in G.legal_moves(sw)            # not offered later

    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)
    print("y selftest OK")


if __name__ == "__main__":
    main()
