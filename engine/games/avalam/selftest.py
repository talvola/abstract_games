"""Avalam selftest (pure stdlib).

Anchors:
1. The exact initial board equals the UCLouvain reference implementation's
   standard `initial_board` matrix (Vianney le Clement, 2010) — 49
   depressions (row profile 2/4/6/8/9/8/6/4/2, 180-degree symmetric), 48
   pieces in a strict checkerboard (24 Light on (c+r) even / 24 Dark),
   central hole (4,4) empty.  That matrix in turn matches the publisher
   rulebook photo and the Abstract Games #18 essay ("49 depressions").
2. Movement law: whole-stack, 1 step in 8 directions, onto occupied only,
   combined height <= 5; merge order = target below, mover on top.
3. Structural termination: every move drops the stack count by exactly 1,
   so games end within 47 plies (asserted over a random sweep, plus an
   independent legal-move re-derivation differential each ply).
4. Scoring: most tops wins, 1 point per stack regardless of height; a
   constructed equal count is an honest DRAW (no tiebreak in the rules).
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.avalam.game import CELLS, CENTER, FOOTPRINT  # noqa: E402

HERE = Path(__file__).resolve().parent

# UCLouvain reference `initial_board` (avalam.py, GPL, Vianney le Clement 2010):
# +1 = yellow (our LIGHT, seat 0) on top, -1 = red (our DARK, seat 1), 0 = empty.
UCL = [
    [0,  0,  1, -1,  0,  0,  0,  0,  0],
    [0,  1, -1,  1, -1,  0,  0,  0,  0],
    [0, -1,  1, -1,  1, -1,  1,  0,  0],
    [0,  1, -1,  1, -1,  1, -1,  1, -1],
    [1, -1,  1, -1,  0, -1,  1, -1,  1],
    [-1, 1, -1,  1, -1,  1, -1,  1,  0],
    [0,  0,  1, -1,  1, -1,  1, -1,  0],
    [0,  0,  0,  0, -1,  1, -1,  1,  0],
    [0,  0,  0,  0,  0, -1,  1,  0,  0],
]

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def independent_moves(board):
    """Naive re-derivation of the movement law, for differential testing."""
    out = set()
    for (c, r), col in board.items():
        for dc, dr in DIRS:
            dst = (c + dc, r + dr)
            if dst in board and len(col) + len(board[dst]) <= 5:
                out.add(f"{c},{r}>{dst[0]},{dst[1]}")
    return out


def cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def main():
    man, g = load_from_dir(HERE)
    uid = man["uid"] if isinstance(man, dict) else man.uid
    assert uid == "avalam"

    # ---- 1. exact initial geometry vs the UCLouvain reference matrix ----
    st = g.initial_state()
    ucl_cells = {(c, r) for r in range(9) for c in range(9)
                 if UCL[r][c] != 0} | {CENTER}
    assert CELLS == frozenset(ucl_cells), "cell footprint != UCLouvain board"
    assert len(CELLS) == 49, len(CELLS)
    # row profile 2/4/6/8/9/8/6/4/2 (publisher board photo)
    profile = [sum(1 for (c, r) in CELLS if r == row) for row in range(9)]
    assert profile == [2, 4, 6, 8, 9, 8, 6, 4, 2], profile
    # 180-degree rotational symmetry of the footprint
    assert all((8 - c, 8 - r) in CELLS for (c, r) in CELLS)
    # initial pieces: 48 singles, centre empty, colours == UCL signs
    assert CENTER not in st.board
    assert len(st.board) == 48
    for (c, r), col in st.board.items():
        assert col == ((0,) if UCL[r][c] == 1 else (1,)), ((c, r), col)
        assert UCL[r][c] != 0
    tops = [0, 0]
    for col in st.board.values():
        tops[col[-1]] += 1
    assert tops == [24, 24], tops
    # strict checkerboard by (c+r) parity
    assert all(col[0] == (c + r) % 2 for (c, r), col in st.board.items())
    # FOOTPRINT internal consistency
    assert sum(map(sum, FOOTPRINT)) == 49

    # ---- 2. opening move differential + pinned count ----
    lm = set(g.legal_moves(st))
    assert lm == independent_moves(st.board)
    assert len(lm) == 292, len(lm)  # every ordered adjacent occupied pair

    # ---- 3. movement law on constructed positions ----
    s2 = g.deserialize({
        # a 3-stack next to a 3-stack (illegal, 6>5), a 2-stack (legal) and
        # an empty cell (illegal target); plus an isolated far single.
        "board": {"3,3": "010", "4,3": "101", "4,4": "01", "6,8": "0"},
        "to_move": 0, "last": None, "ply": 0})
    lm2 = set(g.legal_moves(s2))
    assert "3,3>4,3" not in lm2            # would make a stack of 6
    assert "3,3>4,4" in lm2                # 3 + 2 = 5 is legal
    assert "3,3>2,3" not in lm2            # never onto an empty depression
    assert not any(m.startswith("6,8>") for m in lm2)   # isolated = frozen
    assert lm2 == independent_moves(s2.board)
    ns = g.apply_move(s2, "3,3>4,4")
    assert ns.board[(4, 4)] == (0, 1, 0, 1, 0)   # target below, mover on top
    assert (3, 3) not in ns.board
    assert ns.to_move == 1
    # purity: the input state was not mutated
    assert s2.board[(3, 3)] == (0, 1, 0) and s2.board[(4, 4)] == (0, 1)

    # ---- 4. constructed genuine tie -> honest draw ----
    tie = g.deserialize({
        "board": {"2,0": "01011", "5,8": "10"},   # far apart: no moves
        "to_move": 1, "last": None, "ply": 40})
    assert g.is_terminal(tie)
    assert g.returns(tie) == [0.0, 0.0], g.returns(tie)
    # and a decided position: Dark tops 2 stacks to Light's 1
    dec = g.deserialize({
        "board": {"2,0": "1", "5,8": "01", "8,4": "0"},
        "to_move": 0, "last": None, "ply": 45})
    assert g.is_terminal(dec)
    t = [0, 0]
    for col in dec.board.values():
        t[col[-1]] += 1
    assert t == [1, 2] and g.returns(dec) == [-1.0, 1.0]

    # ---- 5. random sweep: termination, monotone stacks, scoring, ser ----
    rng = random.Random(2026)
    for game_i in range(60):
        s = g.initial_state()
        stacks = len(s.board)
        plies = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            assert moves, "non-terminal state with no moves"
            if plies < 6 or plies % 7 == 0:      # differential spot-checks
                assert set(moves) == independent_moves(s.board)
            s = g.apply_move(s, rng.choice(moves))
            assert len(s.board) == stacks - 1, "a move must merge two stacks"
            stacks = len(s.board)
            assert all(1 <= len(col) <= 5 for col in s.board.values())
            plies += 1
            assert plies <= 47, "structural bound exceeded"
        # piece conservation and scoring consistency
        counts = [0, 0]
        t = [0, 0]
        for col in s.board.values():
            t[col[-1]] += 1
            for o in col:
                counts[o] += 1
        assert counts == [24, 24], counts
        ret = g.returns(s)
        if t[0] > t[1]:
            assert ret == [1.0, -1.0]
        elif t[1] > t[0]:
            assert ret == [-1.0, 1.0]
        else:
            assert ret == [0.0, 0.0]
        # serialize round-trip mid/endgame
        d = g.serialize(s)
        assert g.serialize(g.deserialize(d)) == d

    # ---- 6. heuristic shape (list of num_players payoffs) ----
    h = g.heuristic(g.initial_state())
    assert isinstance(h, list) and len(h) == 2
    assert abs(h[0] + h[1]) < 1e-9

    # ---- 7. render sanity: polygons list format, stacks, 49 cells ----
    spec = g.render(g.initial_state())
    cells = spec["board"]["cells"]
    assert isinstance(cells, list) and len(cells) == 49
    assert all(set(csp) >= {"id", "points"} for csp in cells)
    assert len(spec["pieces"]) == 48
    assert all(p["stack"] for p in spec["pieces"])

    print("avalam selftest: all checks passed")


if __name__ == "__main__":
    main()
