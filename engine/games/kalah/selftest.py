"""Kalah correctness anchor (pure stdlib): seed conservation, sowing that skips
the opponent's store, the extra-turn and capture bonus rules (and when capture
does NOT happen), and the end-of-game sweep + scoring."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.kalah.game import Kalah, KalahState, SOUTH, NORTH  # noqa: E402

G = Kalah()

EMPTY = {(c, r): 0 for r in (0, 1) for c in range(6)}


def main():
    s = G.initial_state()
    assert sum(s.board.values()) == 48 and all(v == 4 for v in s.board.values())
    assert s.stores == [0, 0] and s.to_move == SOUTH

    # --- sowing skips the OPPONENT's store --------------------------------
    #  12 seeds from (0,0): five own pits, own store, then all six North pits
    #  (last seed in a North pit, so no capture/extra turn). South drops into its
    #  own store but never North's.
    b = dict(EMPTY); b[(0, 0)] = 12
    st = KalahState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "0,0")
    assert st2.stores[SOUTH] == 1 and st2.stores[NORTH] == 0, st2.stores
    assert all(st2.board[(c, 1)] == 1 for c in range(6)), "North's pits each got a seed"
    assert st2.to_move == NORTH                 # last seed in a North pit -> turn passes

    # --- last seed in your own store -> extra turn ------------------------
    st2 = G.apply_move(s, "2,0")               # 4 seeds: 3,0 / 4,0 / 5,0 / store
    assert st2.stores[SOUTH] == 1 and st2.to_move == SOUTH, "store landing = extra turn"

    # --- capture: last seed in your own EMPTY pit, opposite non-empty -----
    b = dict(EMPTY); b[(0, 0)] = 1; b[(1, 1)] = 5
    st = KalahState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "0,0")              # lands in empty (1,0); captures (1,1)
    assert st2.stores[SOUTH] == 6 and st2.board[(1, 0)] == 0 and st2.board[(1, 1)] == 0
    assert st2.to_move == NORTH

    # --- NO capture when the opposite pit is empty ------------------------
    b = dict(EMPTY); b[(0, 0)] = 1            # opposite (1,1) is empty
    st = KalahState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "0,0")
    assert st2.stores[SOUTH] == 0 and st2.board[(1, 0)] == 1, "no capture into an empty opposite"

    # --- NO capture when the landing pit was NOT empty --------------------
    b = dict(EMPTY); b[(0, 0)] = 1; b[(1, 0)] = 3; b[(1, 1)] = 5
    st = KalahState(board=b, stores=[0, 0], to_move=SOUTH)
    st2 = G.apply_move(st, "0,0")             # (1,0) becomes 4, not a fresh pit
    assert st2.stores[SOUTH] == 0 and st2.board[(1, 1)] == 5

    # --- end-of-game sweep + scoring --------------------------------------
    b = dict(EMPTY); b[(3, 1)] = 2; b[(4, 1)] = 3      # South side empty
    st = KalahState(board=b, stores=[10, 9], to_move=SOUTH)
    assert G.is_terminal(st)
    assert G._final_scores(st) == [10, 14] and G.returns(st) == [-1.0, 1.0]

    # --- seed conservation across a full random game ----------------------
    import random
    rng = random.Random(3)
    st = G.initial_state()
    while not G.is_terminal(st):
        st = G.apply_move(st, rng.choice(G.legal_moves(st)))
        assert sum(st.board.values()) + sum(st.stores) == 48, "seeds not conserved"
    assert sum(G._final_scores(st)) == 48

    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)
    print("kalah selftest OK")


if __name__ == "__main__":
    main()
