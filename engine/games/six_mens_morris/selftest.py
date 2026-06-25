"""Six Men's Morris correctness anchor (pure stdlib -- imports only agp + this
game). Asserts the board-topology invariants (the 16-point two-square graph,
which is the part most likely to be wired wrong) and the core rule behaviours:
mill -> removal keeps the turn, the not-from-a-mill removal restriction, NO
flying, and win-by-reduction."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.six_mens_morris.game import (  # noqa: E402
    SixMensMorris, MState, POINTS, ADJ, MILLS,
)

G = SixMensMorris()


def main():
    # --- topology ---------------------------------------------------------
    assert len(POINTS) == 16, len(POINTS)
    assert len(MILLS) == 8, len(MILLS)
    # corners lie in 2 mills (two sides meet there); mid-side points in 1 mill.
    for p in POINTS:
        n = sum(1 for m in MILLS if p in m)
        assert n in (1, 2), f"{p} in {n} mills"
    assert sum(1 for p in POINTS if sum(1 for m in MILLS if p in m) == 2) == 8  # 8 corners
    assert sum(1 for p in POINTS if sum(1 for m in MILLS if p in m) == 1) == 8  # 8 mid-sides
    # degrees: corners 2, mid-side points 3 (two ring neighbours + one spoke).
    deg = {p: len(ADJ[p]) for p in POINTS}
    assert deg["0,0"] == 2 and deg["6,6"] == 2, "outer corner degree"
    assert deg["2,2"] == 2 and deg["4,4"] == 2, "inner corner degree"
    assert deg["3,0"] == 3, "outer mid-side degree (two ring + one spoke)"
    assert deg["3,2"] == 3, "inner mid-side degree (two ring + one spoke)"
    # the spoke links outer mid-side to inner mid-side, and nothing crosses corners
    assert "3,2" in ADJ["3,0"] and "3,0" in ADJ["3,2"], "spoke 3,0--3,2"
    assert "2,2" not in ADJ["0,0"], "corners must not cross between squares"
    # adjacency is symmetric
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"
    # spokes form no mill: no mill contains both an outer and an inner point
    inner = {f"{x},{y}" for (x, y) in
             [(2, 2), (3, 2), (4, 2), (4, 3), (4, 4), (3, 4), (2, 4), (2, 3)]}
    for m in MILLS:
        ins = sum(1 for p in m if p in inner)
        assert ins in (0, 3), f"mixed-ring mill {m}"

    # --- mill forms -> same player removes; turn does not pass ------------
    st = MState(pos={"0,0": 0, "6,0": 0, "2,2": 1}, to_move=0, placed=[2, 1])
    st2 = G.apply_move(st, "3,0")             # completes the top outer edge mill
    assert st2.removing and st2.to_move == 0, "mill should keep the turn for removal"
    # the only enemy man (not in a mill) is the legal removal target
    assert G.legal_moves(st2) == ["2,2"], G.legal_moves(st2)

    # --- removal restriction: cannot take a man in a mill if a free one exists
    pos = {"0,0": 0, "3,0": 0, "6,0": 0,      # White mill on the top outer edge
           "2,2": 1, "4,4": 1}                 # two Black men, neither in a mill
    st = MState(pos=dict(pos), to_move=0, placed=[3, 2], removing=True)
    assert set(G.legal_moves(st)) == {"2,2", "4,4"}, G.legal_moves(st)
    # now make the two Black men into a mill -> any may be taken (all in mills)
    pos2 = {"0,0": 0, "3,0": 0, "6,0": 0,
            "2,2": 1, "3,2": 1, "4,2": 1}      # Black mill on the top inner edge
    st = MState(pos=dict(pos2), to_move=0, placed=[3, 3], removing=True)
    assert set(G.legal_moves(st)) == {"2,2", "3,2", "4,2"}, G.legal_moves(st)

    # --- NO flying: down to three men, only adjacent moves ----------------
    pos = {"0,0": 0, "6,6": 0, "2,2": 0,       # White: 3 men (no flying)
           "3,0": 1, "3,6": 1, "0,3": 1, "6,3": 1}
    st = MState(pos=dict(pos), to_move=0, placed=[6, 6])
    mv = G.legal_moves(st)
    # 2,2 (inner corner) is adjacent to 3,2 and 2,3 only
    assert "2,2>3,2" in mv and "2,2>2,3" in mv, mv
    # a non-adjacent ("flying") target must NOT appear
    assert "0,0>4,4" not in mv, "there is no flying in Six Men's Morris"
    assert "2,2>4,4" not in mv, "there is no flying in Six Men's Morris"

    # --- win by reduction to two men -------------------------------------
    #  Black has 3 men, all placed; White completes a mill and removes one,
    #  leaving Black with 2 -> White wins.
    st = MState(pos={"0,0": 0, "3,0": 0, "6,0": 0, "2,2": 1, "4,4": 1, "0,6": 1},
                to_move=0, placed=[6, 6], removing=True)
    st2 = G.apply_move(st, "2,2")             # remove a Black man -> Black has 2
    assert st2.winner == 0, f"winner={st2.winner}"
    assert G.returns(st2) == [1.0, -1.0]

    # --- serialize round-trips -------------------------------------------
    s = G.apply_move(G.apply_move(G.initial_state(), "0,0"), "6,6")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("six_mens_morris selftest OK")


if __name__ == "__main__":
    main()
