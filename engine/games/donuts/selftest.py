"""Donuts correctness anchor (pure stdlib). Checks the randomness-in-state board,
the forced-direction rule + the all-occupied fallback, BOTH insertion patterns
(O_O and OXX_O) flipping the bracketing opponent rings, a 5-in-a-row win reached
via apply_move, an honest full-board draw + its tiebreak, and termination."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.donuts.game import Donuts, DonutState, N, TOTAL  # noqa: E402

G = Donuts()


def st(linemap=None, board=None, to_move=0, last=None, placed=(0, 0), winner=None):
    return DonutState(linemap=linemap or {}, board=dict(board or {}),
                      to_move=to_move, last=last, placed=placed, winner=winner)


def uniform(orient):
    return {(c, r): orient for r in range(N) for c in range(N)}


def main():
    # --- randomness lives in state: two seeds -> different line maps ----------
    a = G.initial_state(rng=random.Random(1))
    b = G.initial_state(rng=random.Random(7))
    assert len(a.linemap) == 36 and set(a.linemap.values()) <= {"H", "V", "S", "B"}
    assert a.linemap != b.linemap, "two seeds should deal different boards"
    # same seed -> identical board (deterministic deal)
    assert G.initial_state(rng=random.Random(1)).linemap == a.linemap
    assert not a.board and a.to_move == 0 and a.placed == (0, 0)

    # --- forced direction: opponent must play on the last ring's line --------
    # last ring at (2,2) marked 'H' -> opponent restricted to row r=2.
    lm = uniform("V")
    lm[(2, 2)] = "H"
    s = st(linemap=lm, board={(2, 2): 0}, to_move=1, last=(2, 2), placed=(1, 0))
    moves = set(G.legal_moves(s))
    assert moves == {f"{c},2" for c in range(N) if c != 2}, moves

    # --- all-occupied fallback: play anywhere when the forced line is full ----
    lm = uniform("V")
    lm[(0, 0)] = "H"
    board = {(c, 0): (c % 2) for c in range(N)}          # row 0 fully occupied
    s = st(linemap=lm, board=board, to_move=1, last=(0, 0), placed=(3, 3))
    empties = {f"{c},{r}" for r in range(1, N) for c in range(N)}
    assert set(G.legal_moves(s)) == empties

    # --- opening move: anywhere ---------------------------------------------
    s0 = st(linemap=uniform("H"))
    assert len(G.legal_moves(s0)) == 36

    # --- insertion pattern O_O : fill a gap, both flankers flip --------------
    # player 0 plays (2,0) between opp rings at (1,0) and (3,0) -> both flip to 0.
    s = st(linemap=uniform("H"), board={(1, 0): 1, (3, 0): 1}, to_move=0,
           last=(5, 5), placed=(1, 2))
    s2 = G.apply_move(s, "2,0")
    assert s2.board[(1, 0)] == 0 and s2.board[(3, 0)] == 0 and s2.board[(2, 0)] == 0
    assert s2.winner is None

    # --- insertion pattern O X X _ O : complete a bracket -> flip + WIN -------
    # O at (0,0); own X at (1,0),(2,0); play (3,0); O at (4,0) -> XXXXX wins.
    s = st(linemap=uniform("H"),
           board={(0, 0): 1, (1, 0): 0, (2, 0): 0, (4, 0): 1},
           to_move=0, last=(5, 5), placed=(3, 2))
    s2 = G.apply_move(s, "3,0")
    for c in range(5):
        assert s2.board[(c, 0)] == 0, (c, s2.board)
    assert s2.winner == 0 and G.is_terminal(s2)
    assert G.returns(s2) == [1.0, -1.0]

    # --- a bracket needs BOTH ends opponent (one-sided => no flip) -----------
    s = st(linemap=uniform("H"), board={(1, 0): 1}, to_move=0, last=(5, 5))
    s2 = G.apply_move(s, "2,0")
    assert s2.board[(1, 0)] == 1, "single flanker must not flip"

    # --- plain 5-in-a-row by placement (diagonal) wins -----------------------
    diag = {(i, i): 0 for i in range(4)}                 # (0,0)..(3,3)
    s = st(linemap=uniform("H"), board=diag, to_move=0, last=(5, 5), placed=(4, 4))
    s2 = G.apply_move(s, "4,4")
    assert s2.winner == 0 and G.is_terminal(s2)

    # --- honest draw: 30 rings placed, no 5-line, equal largest groups -------
    # Left half player 0, right half player 1, row r=2 left empty. Each side has
    # 15 rings split into a 3x2 block (rows 0-1) + a 3x3 block (rows 3-5); the
    # empty row breaks all vertical 5s, the 3-wide halves break horizontal ones.
    # Largest orthogonal group = 9 for each colour -> honest draw.
    board = _draw_board()
    assert sum(1 for v in board.values() if v == 0) == 15
    assert sum(1 for v in board.values() if v == 1) == 15
    s = st(linemap=uniform("H"), board=board, to_move=0, placed=(15, 15))
    assert G.is_terminal(s)
    assert not G._has_five(board, 0) and not G._has_five(board, 1)
    assert G._largest_group(board, 0) == 9 and G._largest_group(board, 1) == 9
    assert G._result(s) is None and G.returns(s) == [0.0, 0.0]

    # --- tiebreak: bigger orthogonal group wins ------------------------------
    # Flip one player-1 ring adjacent to player 0's 3x3 block -> group 10 vs 8.
    b2 = _draw_board()
    b2[(3, 3)] = 0                      # was player 1, now joins player 0's block
    s = st(linemap=uniform("H"), board=b2, to_move=0, placed=(15, 15))
    assert G._largest_group(b2, 0) == 10 and G._largest_group(b2, 1) == 8
    assert G._result(s) == 0 and G.returns(s) == [1.0, -1.0]

    # --- serialize round-trips ----------------------------------------------
    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)
    ser = G.serialize(a)
    assert G.serialize(G.deserialize(ser)) == ser

    # --- termination: random self-play always ends within 30 placements ------
    for seed in range(30):
        s = G.initial_state(rng=random.Random(seed))
        n = 0
        while not G.is_terminal(s):
            s = G.apply_move(s, random.Random(seed * 97 + n).choice(G.legal_moves(s)))
            n += 1
            assert n <= TOTAL, n
        assert G.is_terminal(s) and (s.winner is not None or sum(s.placed) == TOTAL)
        rr = G.returns(s)
        assert len(rr) == 2 and all(x in (-1.0, 0.0, 1.0) for x in rr)

    print("donuts selftest OK")


def _draw_board():
    """A 30-ring board (15 each) with no 5-line and equal largest orthogonal
    groups (9 each). Left half = player 0, right half = player 1; row r=2 empty."""
    board = {}
    for r in range(N):
        if r == 2:
            continue
        for c in range(N):
            board[(c, r)] = 0 if c < 3 else 1
    return board


if __name__ == "__main__":
    main()
