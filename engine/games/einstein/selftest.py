"""EinStein würfelt nicht! correctness anchor (pure stdlib). The platform's first
dice game: checks the random-but-stored die model, the move-the-die-number rule
with the next-higher/next-lower fallback, forward-only movement, capture on
landing (own or enemy), and both win conditions."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.einstein.game import Einstein, EWNState  # noqa: E402

G = Einstein()


def main():
    # --- setup ------------------------------------------------------------
    s = G.initial_state(rng=random.Random(1))
    assert len(s.board) == 12
    for p in (0, 1):
        nums = sorted(n for (pp, n) in s.board.values() if pp == p)
        assert nums == [1, 2, 3, 4, 5, 6]
    assert 1 <= s.die <= 6

    # --- movement is toward the far corner only ---------------------------
    st = EWNState(board={(2, 2): (0, 3), (4, 4): (1, 1)}, die=3, to_move=0)
    dests = {m.split(">")[1] for m in G.legal_moves(st)}
    assert dests == {"3,2", "2,3", "3,3"}, dests           # right / up / up-right

    # --- the die-number rule + nearest fallback ---------------------------
    st = EWNState(board={(0, 0): (0, 1), (1, 0): (0, 3), (2, 0): (0, 5), (4, 4): (1, 2)},
                  die=4, to_move=0)
    assert G._movable_numbers(st, 0) == [3, 5]              # 4 gone -> 3 (lower) or 5 (higher)
    st = EWNState(board={(0, 0): (0, 2), (4, 4): (1, 1)}, die=2, to_move=0)
    assert G._movable_numbers(st, 0) == [2]                 # has the exact number

    # --- capture on landing (enemy and own) -------------------------------
    st = EWNState(board={(2, 2): (0, 3), (3, 3): (1, 5)}, die=3, to_move=0)
    s2 = G.apply_move(st, "2,2>3,3", rng=random.Random(0))
    assert s2.board[(3, 3)] == (0, 3) and (2, 2) not in s2.board   # enemy captured
    st = EWNState(board={(2, 2): (0, 3), (3, 3): (0, 5), (4, 4): (1, 1)}, die=3, to_move=0)
    s2 = G.apply_move(st, "2,2>3,3", rng=random.Random(0))
    assert s2.board[(3, 3)] == (0, 3)                       # may capture your own stone too

    # --- win by reaching the opposite corner ------------------------------
    st = EWNState(board={(3, 3): (0, 2), (0, 0): (1, 1)}, die=2, to_move=0)
    assert G.apply_move(st, "3,3>4,4", rng=random.Random(0)).winner == 0
    st = EWNState(board={(1, 1): (1, 2), (4, 4): (0, 1)}, die=2, to_move=1)
    assert G.apply_move(st, "1,1>0,0", rng=random.Random(0)).winner == 1

    # --- win by capturing every enemy stone -------------------------------
    st = EWNState(board={(2, 2): (0, 3), (3, 3): (1, 5)}, die=3, to_move=0)
    assert G.apply_move(st, "2,2>3,3", rng=random.Random(0)).winner == 0

    # --- the die is re-rolled (and stored) on every move ------------------
    st = EWNState(board={(0, 0): (0, 1), (4, 4): (1, 1)}, die=1, to_move=0)
    s2 = G.apply_move(st, "0,0>1,0", rng=random.Random(7))
    assert 1 <= s2.die <= 6 and s2.to_move == 1

    # --- forward-only movement guarantees termination ---------------------
    s = G.initial_state(rng=random.Random(5))
    n = 0
    while not G.is_terminal(s):
        s = G.apply_move(s, random.Random(n).choice(G.legal_moves(s)), rng=random.Random(n + 1))
        n += 1
        assert n < 200
    assert s.winner is not None

    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)
    print("einstein selftest OK")


if __name__ == "__main__":
    main()
