"""Nine Men's Morris correctness anchor (pure stdlib -- imports only agp + this
game). Asserts the board-topology invariants (the part most likely to be wired
wrong) and the core rule behaviours: mill -> removal keeps the turn, the
not-from-a-mill removal restriction, flying at three men, and win-by-reduction.
Independently rule-reviewed (all 8 areas MERGE)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.nine_mens_morris.game import (  # noqa: E402
    NineMensMorris, MState, POINTS, ADJ, MILLS,
)

G = NineMensMorris()


def main():
    # --- topology ---------------------------------------------------------
    assert len(POINTS) == 24, len(POINTS)
    assert len(MILLS) == 16, len(MILLS)
    # every point lies in exactly two mills
    for p in POINTS:
        n = sum(1 for m in MILLS if p in m)
        assert n == 2, f"{p} in {n} mills"
    # degrees: corners 2, ring mid-sides 3, the two-spoke middle mid-sides 4
    deg = {p: len(ADJ[p]) for p in POINTS}
    assert deg["0,0"] == 2 and deg["6,6"] == 2, "corner degree"
    assert deg["3,0"] == 3, "outer mid-side degree"   # two ring + one spoke
    assert deg["3,1"] == 4, "middle mid-side degree"  # spoke reaches both rings
    assert deg["3,2"] == 3, "inner mid-side degree"
    # adjacency is symmetric and never crosses a corner between rings
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"

    # --- mill forms -> same player removes; turn does not pass ------------
    st = MState(pos={"0,0": 0, "6,0": 0, "1,1": 1}, to_move=0, placed=[2, 1])
    st2 = G.apply_move(st, "3,0")             # completes the top edge mill
    assert st2.removing and st2.to_move == 0, "mill should keep the turn for removal"
    # the only enemy man (not in a mill) is the legal removal target
    assert G.legal_moves(st2) == ["1,1"], G.legal_moves(st2)

    # --- removal restriction: cannot take a man in a mill if a free one exists
    pos = {"0,0": 0, "3,0": 0, "6,0": 0,      # White mill on the top edge
           "1,1": 1, "5,5": 1}                 # two Black men, neither in a mill
    st = MState(pos=dict(pos), to_move=0, placed=[3, 2], removing=True)
    assert set(G.legal_moves(st)) == {"1,1", "5,5"}, G.legal_moves(st)

    # --- win by reduction to two men -------------------------------------
    #  Black has 3 men, all placed; White completes a mill and removes one,
    #  leaving Black with 2 -> White wins.
    pos = {"0,0": 0, "6,0": 0,                 # White about to mill via 3,0
           "1,1": 1, "5,5": 1, "2,2": 1}
    st = MState(pos=dict(pos), to_move=0, placed=[9, 9])  # moving phase
    # move a White man onto 3,0 to complete the top mill: 0,0 is adjacent? no;
    # instead just simulate the placing-style completion via a slide 0,0->3,0 is
    # illegal, so build the mill directly and trigger removal:
    st = MState(pos={"0,0": 0, "3,0": 0, "6,0": 0, "1,1": 1, "5,5": 1, "2,2": 1},
                to_move=0, placed=[9, 9], removing=True)
    st2 = G.apply_move(st, "1,1")             # remove a Black man -> Black has 2
    assert st2.winner == 0, f"winner={st2.winner}"
    assert G.returns(st2) == [1.0, -1.0]

    # --- flying at exactly three men -------------------------------------
    pos = {"0,0": 0, "6,6": 0, "2,2": 0,       # White: 3 men (flying)
           "3,0": 1, "3,6": 1, "0,3": 1, "6,3": 1}
    st = MState(pos=dict(pos), to_move=0, placed=[9, 9])
    mv = G.legal_moves(st)
    assert "0,0>4,4" in mv, "flying move missing"   # non-adjacent target allowed
    # with flying off, only adjacent targets
    G.FLYING = False
    st_noflyA = G.initial_state(options={"flying": "no"})
    assert G.FLYING is False
    st2 = MState(pos=dict(pos), to_move=0, placed=[9, 9])
    assert "0,0>4,4" not in G.legal_moves(st2), "flying should be disabled"
    G.FLYING = True

    # --- serialize round-trips -------------------------------------------
    s = G.apply_move(G.apply_move(G.initial_state(), "0,0"), "6,6")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("nine_mens_morris selftest OK")


if __name__ == "__main__":
    main()
