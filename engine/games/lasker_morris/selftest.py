"""Lasker Morris correctness anchor (pure stdlib -- imports only agp + this game).

Asserts the board topology (shared with Nine Men's Morris) plus the rules that
make Lasker Morris what it is: ten men in hand at the start, the signature
interleaved place-OR-slide legality from move one (a slide is legal *while men
remain in hand* -- the exact thing that distinguishes it from Nine Men's
Morris), mill -> enemy removal, win-by-reduction below three men, and that a
random game terminates (the no-progress safety)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.lasker_morris.game import (  # noqa: E402
    LaskerMorris, MState, POINTS, ADJ, MILLS,
)

G = LaskerMorris()


def main():
    # --- topology (identical board to Nine Men's Morris) ------------------
    assert len(POINTS) == 24, len(POINTS)
    assert len(MILLS) == 16, len(MILLS)
    for p in POINTS:                                   # every point in exactly two mills
        assert sum(1 for m in MILLS if p in m) == 2, p
    for p in POINTS:                                   # symmetric adjacency
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"

    # --- ten men in hand at the start -------------------------------------
    st = G.initial_state()
    assert G.MEN == 10
    assert G._in_hand(st, 0) == 10 and G._in_hand(st, 1) == 10
    assert G._count(st, 0) == 10

    # --- Lasker's signature: slide legal WHILE men remain in hand ---------
    st = G.apply_move(st, "0,0")           # p0 places (9 in hand, 1 on board)
    st = G.apply_move(st, "6,6")           # p1 places
    assert G._in_hand(st, 0) == 9 and st.to_move == 0
    mv = G.legal_moves(st)
    assert "0,0>3,0" in mv, "slide must be legal while men remain in hand (Lasker rule)"
    assert "2,2" in mv, "placement must also be legal (interleaved)"
    # sanity: applying that slide moves the man and keeps 9 in hand
    st_slid = G.apply_move(st, "0,0>3,0")
    assert "3,0" in st_slid.pos and "0,0" not in st_slid.pos
    assert G._in_hand(st_slid, 0) == 9, "sliding must NOT consume a man from hand"

    # --- mill forms -> same player removes; the turn does not pass --------
    st = MState(pos={"0,0": 0, "6,0": 0, "1,1": 1}, to_move=0, placed=[2, 1])
    st2 = G.apply_move(st, "3,0")          # completes the top edge mill
    assert st2.removing and st2.to_move == 0, "mill should keep the turn for removal"
    assert G.legal_moves(st2) == ["1,1"], G.legal_moves(st2)

    # --- removal restriction: cannot take a man in a mill if a free one exists
    st = MState(pos={"0,0": 0, "3,0": 0, "6,0": 0, "1,1": 1, "5,5": 1},
                to_move=0, placed=[3, 2], removing=True)
    assert set(G.legal_moves(st)) == {"1,1", "5,5"}, G.legal_moves(st)

    # --- win by reduction below three men ---------------------------------
    #  Black has 3 men on board, hand empty (placed=10); White mills and removes
    #  one -> Black has 2 total -> White wins.
    st = MState(pos={"0,0": 0, "3,0": 0, "6,0": 0, "1,1": 1, "5,5": 1, "2,2": 1},
                to_move=0, placed=[10, 10], removing=True)
    st2 = G.apply_move(st, "1,1")          # remove a Black man
    assert st2.winner == 0, f"winner={st2.winner}"
    assert G.returns(st2) == [1.0, -1.0]
    assert G.is_terminal(st2)

    # --- flying at exactly three men (hand empty) -------------------------
    pos = {"0,0": 0, "6,6": 0, "2,2": 0,          # White: 3 men, hand empty -> flying
           "3,0": 1, "3,6": 1, "0,3": 1, "6,3": 1}
    st = MState(pos=dict(pos), to_move=0, placed=[10, 10])
    assert "0,0>4,4" in G.legal_moves(st), "flying move missing"
    G.FLYING = False
    assert "0,0>4,4" not in G.legal_moves(st), "flying should be disabled"
    G.FLYING = True

    # --- serialize round-trips --------------------------------------------
    s = G.apply_move(G.apply_move(G.initial_state(), "0,0"), "6,6")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    # --- a random game terminates (no-progress / repetition safety) -------
    rng = random.Random(20260630)
    for seed in range(30):
        rng = random.Random(seed)
        st = G.initial_state()
        for _ in range(5000):
            if G.is_terminal(st):
                break
            moves = G.legal_moves(st)
            assert moves, "non-terminal state with no legal moves"
            st = G.apply_move(st, rng.choice(moves))
        assert G.is_terminal(st), f"game seed={seed} did not terminate"

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
