"""Chinese Checkers correctness anchor (pure stdlib). Pins the verified star
geometry (121 points, 61-point hexagon, six 10-point camps, 6-fold symmetric),
the step + chain-jump moves with nothing captured, six-seat turn cycling, and the
fill-the-opposite-point win."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.chinese_checkers.game import (  # noqa: E402
    ChineseCheckers, CCState, CELLS, CELLSET, CAMPS, OPP, _neighbors,
)

G = ChineseCheckers()


def main():
    # --- geometry ---------------------------------------------------------
    assert len(CELLS) == 121
    hexg = [(a, b) for (a, b) in CELLS if max(abs(a), abs(b), abs(-a - b)) <= 4]
    assert len(hexg) == 61
    assert [len(c) for c in CAMPS] == [10] * 6
    assert OPP == [3, 4, 5, 0, 1, 2]
    # opposite-of-opposite is identity; a camp never equals its opposite
    assert all(OPP[OPP[i]] == i and OPP[i] != i for i in range(6))
    # 6-fold + reflection symmetry of the point set
    assert all((b, -a - b) in CELLSET for (a, b) in CELLS)        # rotation
    assert all((-a - b, b) in CELLSET for (a, b) in CELLS)        # reflection

    # --- setup ------------------------------------------------------------
    s = G.initial_state()
    assert G.num_players == 6 and len(s.board) == 60 and len(G.returns(s)) == 6
    for p in range(6):
        assert all(s.board[sq] == p for sq in CAMPS[p])

    # --- step + chain-jump, nothing captured ------------------------------
    b = {(0, 0): 0, (1, -1): 1, (3, -3): 1}
    st = CCState(board=b, to_move=0)
    mv = [m for m in G.legal_moves(st) if m.startswith("0,0>")]
    assert "0,0>0,1" in mv                       # a plain step to an empty neighbour
    assert "0,0>2,-2" in mv and "0,0>4,-4" in mv  # single hop and a two-hop chain
    st2 = G.apply_move(st, "0,0>4,-4")
    assert st2.board.get((4, -4)) == 0           # moved
    assert st2.board.get((1, -1)) == 1 and st2.board.get((3, -3)) == 1  # hopped, not taken

    # --- turn cycling 0..5 ------------------------------------------------
    s = G.initial_state()
    order = []
    for _ in range(7):
        order.append(s.to_move)
        s = G.apply_move(s, G.legal_moves(s)[0])
    assert order == [0, 1, 2, 3, 4, 5, 0], order

    # --- win by filling the opposite point --------------------------------
    target = CAMPS[OPP[0]]
    # leave a target cell that has a free neighbour outside the camp; fill the rest
    tset = set(target)
    base = next(c for c in target if any(n not in tset for n in _neighbors(*c)))
    entry = next(n for n in _neighbors(*base) if n not in tset)
    board = {sq: 0 for sq in target if sq != base}
    board[entry] = 0                             # the tenth marble, just outside
    st = CCState(board=board, to_move=0)
    st2 = G.apply_move(st, f"{entry[0]},{entry[1]}>{base[0]},{base[1]}")
    assert st2.winner == 0 and G.returns(st2)[0] == 1.0 and G.returns(st2)[1] == -1.0

    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)
    print("chinese_checkers selftest OK")


if __name__ == "__main__":
    main()
