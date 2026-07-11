"""Urbino correctness anchors (pure stdlib: agp + this game only).

Anchored on the designer's official rules and their worked scoring examples:
https://spielstein.com/games/urbino/rules  (+ /rules/monuments)

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/urbino/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.urbino.game import (UState, DARK, LIGHT, SIZE, KIND_VALUE,
                               SUPPLY0, PLY_CAP)

_M, G = load_from_dir(Path(__file__).resolve().parent)

ALL = [(c, r) for r in range(SIZE) for c in range(SIZE)]


def _state(board=None, arch=None, to_move=DARK, phase="MOVE",
           supply=None, skips=0, monuments=False):
    """board: {(c,r): (owner, kind)}; arch: [(c,r),(c,r)]."""
    if supply is None:
        supply = [dict(SUPPLY0), dict(SUPPLY0)]
    return UState(board=dict(board or {}), arch=list(arch or []),
                  supply=[dict(supply[0]), dict(supply[1])], to_move=to_move,
                  phase=phase, skips=skips, monuments=monuments)


def _sight_ref(board, arch, a):
    """Independent sight implementation (different formulation from game.py):
    x is seen by `a` iff x is empty, queen-aligned with a, and every square
    strictly between is unoccupied (buildings AND architects block)."""
    occ = set(board) | set(arch)
    out = set()
    for x in ALL:
        if x == a or x in occ:
            continue
        dc, dr = x[0] - a[0], x[1] - a[1]
        if not (dc == 0 or dr == 0 or abs(dc) == abs(dr)):
            continue
        sc = (dc > 0) - (dc < 0)
        sr = (dr > 0) - (dr < 0)
        c, r = a[0] + sc, a[1] + sr
        clear = True
        while (c, r) != x:
            if (c, r) in occ:
                clear = False
                break
            c, r = c + sc, r + sr
        if clear:
            out.add(x)
    return out


# --------------------------------------------------------------------------
def test_sight_rule_exhaustive():
    """Rule 2.1 -- lots = intersection of both architects' clear queen-lines.
    Differential vs an independent implementation on 250 random boards."""
    rng = random.Random(20180909)
    for _ in range(250):
        nb = rng.randrange(0, 25)
        cells = rng.sample(ALL, nb + 2)
        arch = cells[:2]
        board = {xy: (rng.randrange(2), rng.choice("HPT")) for xy in cells[2:]}
        want = _sight_ref(board, arch, arch[0]) & _sight_ref(board, arch, arch[1])
        assert G._lots(board, arch) == want


def test_sight_collinear_special_case():
    """'If the two architects are standing in one line, with no building
    between them, all the squares between them are intersection points.'"""
    lots = G._lots({}, [(0, 0), (0, 5)])
    assert {(0, 1), (0, 2), (0, 3), (0, 4)} <= lots
    # a building between them blocks the shared file (and (0,1)/(0,2)/(0,4)
    # are on no other line of the far architect)
    lots = G._lots({(0, 3): (DARK, "H")}, [(0, 0), (0, 5)])
    assert not ({(0, 1), (0, 2), (0, 4)} & lots)
    # architects can NOT look over each other either (occupied square)
    lots = G._lots({}, [(0, 0), (4, 4)])
    assert (5, 5) not in lots and (3, 3) in lots


def test_opening_protocol():
    """Dark places architect 1, Light architect 2 (distinct squares), Dark
    chooses the first builder; the first turn is build-only (no reposition)."""
    s = G.initial_state()
    assert s.to_move == DARK and s.phase == "ARCH"
    assert len(G.legal_moves(s)) == 81
    s = G.apply_move(s, "4,4")
    assert s.to_move == LIGHT and len(s.arch) == 1
    lm = G.legal_moves(s)
    assert len(lm) == 80 and "4,4" not in lm
    s = G.apply_move(s, "2,3")
    assert s.phase == "CHOOSE" and s.to_move == DARK
    assert sorted(G.legal_moves(s)) == ["dark-starts", "light-starts"]
    s = G.apply_move(s, "light-starts")
    assert s.to_move == LIGHT and s.phase == "BUILD"
    lm = G.legal_moves(s)
    assert lm and all("=" in m and ">" not in m for m in lm)   # build only
    assert "pass" not in lm and "skip" not in lm
    # every offered lot is seen by both architects
    lots = G._lots(s.board, s.arch)
    for m in lm:
        cell = tuple(int(x) for x in m.split("=")[0].split(","))
        assert cell in lots
    # ... and erecting flips the turn to Dark's MOVE phase
    s2 = G.apply_move(s, lm[0])
    assert s2.to_move == DARK and s2.phase == "MOVE"
    k = lm[0].split("=")[1]
    assert s2.supply[LIGHT][k] == SUPPLY0[k] - 1


def test_adjacency_rule():
    """Rule 2.3: no tower orthogonally next to a tower, no palace next to a
    palace (either colour); houses unrestricted."""
    b = {(4, 4): (DARK, "T"), (1, 1): (LIGHT, "P")}
    assert not G._ok_adjacent(b, (4, 3), "T")     # T next to T (same colour)
    assert not G._ok_adjacent(b, (1, 2), "P")     # P next to P (cross colour)
    assert G._ok_adjacent(b, (4, 3), "P")         # P next to T is fine
    assert G._ok_adjacent(b, (1, 2), "T")         # T next to P is fine
    assert G._ok_adjacent(b, (4, 3), "H")         # houses unrestricted
    assert G._ok_adjacent(b, (5, 5), "T")         # diagonal does not count
    b2 = {(4, 4): (LIGHT, "T")}                   # colour irrelevant
    assert not G._ok_adjacent(b2, (5, 4), "T")


def test_district_block_rule():
    """Rule 2.2 (the official illustration's A/B/C/D cases): a placement may
    not leave any colour split into two blocks within one district."""
    # case C: bridging two dark districts with a LIGHT house would leave the
    # dark buildings disconnected -- illegal; DARK bridging its own is fine
    b = {(2, 2): (DARK, "H"), (4, 2): (DARK, "H")}
    assert not G._ok_district(b, (3, 2), LIGHT)
    assert G._ok_district(b, (3, 2), DARK)
    # cases A/B: merging two mixed districts must keep BOTH colours connected
    b2 = {(2, 2): (DARK, "H"), (2, 3): (LIGHT, "H"),
          (4, 2): (DARK, "H"), (4, 3): (LIGHT, "H")}
    assert not G._ok_district(b2, (3, 2), DARK)    # light would split
    assert not G._ok_district(b2, (3, 3), LIGHT)   # dark would split
    # case D: a merge where every colour stays one block is legal
    b3 = {(2, 2): (DARK, "H"), (2, 3): (LIGHT, "H"), (4, 2): (DARK, "H")}
    assert G._ok_district(b3, (3, 2), DARK)
    # diagonal does not connect: a diagonal neighbour is its own district
    b4 = {(2, 2): (DARK, "H")}
    assert G._ok_district(b4, (3, 3), LIGHT) and G._ok_district(b4, (3, 3), DARK)
    # end-to-end: architects collinear on the empty c-file see every square
    # between them (special sight case); the district-illegal lots are
    # nonetheless absent from legal_moves while a legal lot is offered
    s = _state(board=b2, arch=[(3, 0), (3, 8)], to_move=DARK, phase="BUILD")
    lm = set(G.legal_moves(s))
    lots = G._lots(b2, s.arch)
    assert {(3, 1), (3, 2), (3, 3), (3, 6)} <= lots    # seen by both...
    assert not any(m.startswith("3,2=") or m.startswith("3,3=") for m in lm)
    assert "3,6=H" in lm                               # ...and buildable here


def test_reposition_semantics():
    """Architects teleport to any unoccupied square, and every offered
    choice (including 'pass') leaves at least one build."""
    b = {(4, 4): (DARK, "H"), (4, 5): (LIGHT, "H")}
    s = _state(board=b, arch=[(0, 0), (8, 8)], to_move=DARK, phase="MOVE")
    lm = G.legal_moves(s)
    assert "pass" in lm and "skip" not in lm
    occ = set(b) | set(s.arch)
    repos = [m for m in lm if ">" in m]
    assert repos
    for m in repos:
        frm, to = m.split(">")
        src = tuple(int(x) for x in frm.split(","))
        dst = tuple(int(x) for x in to.split(","))
        assert src in s.arch and dst not in occ and src != dst
    # teleport: a far, non-queen-line target must be offered (e.g. a1 -> b8
    # is no queen move; both squares empty, and builds clearly remain)
    assert "0,0>1,7" in lm
    # sub-turn: after any reposition (sampled) a build MUST exist
    rng = random.Random(7)
    for m in rng.sample(repos, min(12, len(repos))) + ["pass"]:
        s2 = G.apply_move(s, m)
        assert s2.phase == "BUILD" and s2.to_move == DARK
        blm = G.legal_moves(s2)
        assert blm and all("=" in x for x in blm)


def _terminal(st):
    """Drive a constructed position to game end via two forced skips."""
    st = _state(board=st.board, arch=st.arch, to_move=st.to_move,
                phase="MOVE", supply=[{"H": 0, "P": 0, "T": 0}] * 2,
                monuments=st.monuments)
    for _ in range(2):
        assert G.legal_moves(st) == ["skip"]
        st = G.apply_move(st, "skip")
    assert G.is_terminal(st)
    return st


def test_official_scoring_examples():
    """The four worked examples from the official rules page."""
    # 1) White(Light) 4H+2P=8 vs Black(Dark) 2H+1P+1T=7 -> Light gets 8
    b = {(0, 4): (LIGHT, "H"), (1, 4): (LIGHT, "P"), (2, 4): (LIGHT, "H"),
         (3, 4): (LIGHT, "P"), (4, 4): (LIGHT, "H"), (5, 4): (LIGHT, "H"),
         (6, 4): (DARK, "H"), (7, 4): (DARK, "H"), (8, 4): (DARK, "P"),
         (8, 5): (DARK, "T")}
    totals, _ = G._score(_state(board=b, arch=[(0, 0), (1, 0)]))
    assert totals == [0, 8]
    # 2) Light 1H+2P=5 vs Dark 2H+1T=5 -> tie on value, Dark has the tower
    b = {(0, 2): (LIGHT, "P"), (1, 2): (LIGHT, "H"), (2, 2): (LIGHT, "P"),
         (3, 2): (DARK, "H"), (4, 2): (DARK, "H"), (5, 2): (DARK, "T")}
    totals, _ = G._score(_state(board=b, arch=[(0, 0), (1, 0)]))
    assert totals == [5, 0]
    # 3) 1H+1P each -> full tie, NOBODY scores the district
    b3 = {(0, 0): (LIGHT, "H"), (1, 0): (LIGHT, "P"),
          (2, 0): (DARK, "H"), (3, 0): (DARK, "P")}
    totals, _ = G._score(_state(board=b3, arch=[(0, 8), (1, 8)]))
    assert totals == [0, 0]
    # 4) one-colour district and a stand-alone building score nothing
    b = {(0, 0): (LIGHT, "H"), (1, 0): (LIGHT, "H"), (2, 0): (LIGHT, "T"),
         (5, 5): (DARK, "H")}
    totals, _ = G._score(_state(board=b, arch=[(0, 8), (1, 8)]))
    assert totals == [0, 0]
    # example 3 is a genuine reachable dead heat -> an honest DRAW
    end = _terminal(_state(board=b3, arch=[(0, 8), (1, 8)]))
    assert G.returns(end) == [0.0, 0.0]


def test_overall_winner_and_tiebreak():
    """Highest total wins; a tied total falls to the scored towers, then
    palaces, then houses; a full tie is a draw."""
    # Light wins district A with 1P (2 pts), Dark wins district B with 2H
    # (2 pts): totals 2-2, but a scored palace outranks two scored houses.
    b = {(0, 0): (LIGHT, "P"), (0, 1): (DARK, "H"),          # A: 2 vs 1
         (5, 5): (DARK, "H"), (6, 5): (DARK, "H"), (7, 5): (LIGHT, "H")}  # B: 2 vs 1
    end = _terminal(_state(board=b, arch=[(4, 0), (8, 8)]))
    totals, tb = G._score(end)
    assert totals == [2, 2] and tb[1] > tb[0]
    assert G.returns(end) == [-1.0, 1.0]                     # Light wins
    # fully symmetric scored districts -> honest draw
    b = {(0, 0): (LIGHT, "H"), (1, 0): (LIGHT, "H"), (2, 0): (DARK, "H"),
         (6, 8): (DARK, "H"), (7, 8): (DARK, "H"), (8, 8): (LIGHT, "H")}
    end = _terminal(_state(board=b, arch=[(4, 4), (5, 4)]))
    totals, tb = G._score(end)
    assert totals == [2, 2] and tb[0] == tb[1]
    assert G.returns(end) == [0.0, 0.0]


def test_monuments_variant():
    """Official monuments example: Light = ducal palace + tower + 3 houses
    = 16; Dark = cathedral + house = 17 -> Dark takes the district. Without
    the house it is 16-16 and 'the more valuable monument prevails'. Only
    ONE monument per block may be scored."""
    light = {(0, 3): (LIGHT, "P"), (1, 3): (LIGHT, "H"), (2, 3): (LIGHT, "P"),
             (3, 3): (LIGHT, "T"), (4, 3): (LIGHT, "H"), (5, 3): (LIGHT, "H"),
             (6, 3): (LIGHT, "H")}
    dark = {(7, 3): (DARK, "T"), (7, 2): (DARK, "P"), (7, 1): (DARK, "T"),
            (7, 0): (DARK, "H")}
    b = dict(light)
    b.update(dark)
    st = _state(board=b, arch=[(0, 8), (1, 8)], monuments=True)
    totals, _ = G._score(st)
    # Light holds BOTH a ducal palace (P-H-P) and a town wall (H-H-H) but may
    # score only the better one: 11 base + 5 = 16, not 19. Dark: 9 + 8 = 17.
    assert totals == [17, 0]
    # monuments OFF: plain values, Light 11 vs Dark 9 -> Light 11
    st_off = _state(board=b, arch=[(0, 8), (1, 8)], monuments=False)
    assert G._score(st_off)[0] == [0, 11]
    # drop Dark's house: 16-16 tie -> cathedral (rank 3) beats ducal (rank 2)
    del b[(7, 0)]
    st = _state(board=b, arch=[(0, 8), (1, 8)], monuments=True)
    assert G._score(st)[0] == [16, 0]


def test_skip_and_end():
    """Voluntary passing of the turn is impossible; a buildless player must
    skip; two skips IN A ROW end the game; a build in between resets."""
    b = {(4, 4): (DARK, "H"), (4, 5): (LIGHT, "H")}
    empty = {"H": 0, "P": 0, "T": 0}
    # Dark out of buildings -> forced skip is the ONLY move
    s = _state(board=b, arch=[(0, 0), (8, 8)], to_move=DARK, phase="MOVE",
               supply=[dict(empty), dict(SUPPLY0)])
    assert G.legal_moves(s) == ["skip"]
    s = G.apply_move(s, "skip")
    assert s.skips == 1 and s.to_move == LIGHT and not G.is_terminal(s)
    # Light can still build -> skip not offered, and building resets the count
    lm = G.legal_moves(s)
    assert "skip" not in lm and "pass" in lm
    s = G.apply_move(s, "pass")
    s = G.apply_move(s, G.legal_moves(s)[0])
    assert s.skips == 0 and s.to_move == DARK
    # Dark must skip again; then make Light buildless too -> second skip ends
    assert G.legal_moves(s) == ["skip"]
    s = G.apply_move(s, "skip")
    s.supply[LIGHT] = dict(empty)
    assert G.legal_moves(s) == ["skip"]
    s = G.apply_move(s, "skip")
    assert G.is_terminal(s) and G.legal_moves(s) == []


def _check_final_invariants(st):
    """Global board invariants at game end: supplies consistent, adjacency
    rule and one-block-per-colour-per-district hold everywhere."""
    used = [{"H": 0, "P": 0, "T": 0}, {"H": 0, "P": 0, "T": 0}]
    for (c, r), (o, k) in st.board.items():
        used[o][k] += 1
        if k in "PT":                          # rule 2.3 as a board invariant
            for dc, dr in ((1, 0), (0, 1)):
                nb = st.board.get((c + dc, r + dr))
                assert nb is None or nb[1] != k
    for p in (DARK, LIGHT):
        for k in "HPT":
            assert used[p][k] + st.supply[p][k] == SUPPLY0[k]
    # rule 2.2 as a board invariant, via an independent flood fill
    left = set(st.board)
    while left:
        start = left.pop()
        comp, stack = {start}, [start]
        while stack:
            c, r = stack.pop()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c + dc, r + dr)
                if n in st.board and n not in comp:
                    comp.add(n)
                    left.discard(n)
                    stack.append(n)
        for col in (DARK, LIGHT):
            cells = {x for x in comp if st.board[x][0] == col}
            if not cells:
                continue
            blk, stack = {next(iter(cells))}, [next(iter(cells))]
            while stack:
                c, r = stack.pop()
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (c + dc, r + dr)
                    if n in cells and n not in blk:
                        blk.add(n)
                        stack.append(n)
            assert blk == cells


def test_playouts():
    """500 random playouts terminate well under the ply cap with legal moves
    at every non-terminal state and all board invariants intact at the end.

    440 use a fast policy (prefer 'pass' when it is provably legal -- the
    exact condition legal_moves uses -- else draw from full legal_moves);
    60 draw every move from full legal_moves."""
    rng = random.Random(2018)
    stats = {"dark": 0, "light": 0, "draw": 0}
    plies, skipped_turns, scores = [], 0, [0, 0]
    for i in range(500):
        full = i < 60
        st = G.initial_state({"monuments": i % 5 == 0})
        while not G.is_terminal(st):
            mv = None
            if not full and st.phase == "MOVE" and rng.random() < 0.85:
                lots = G._lots(st.board, st.arch)
                bl = G._buildable(st.board, st.to_move, st.supply[st.to_move])
                if any(l in bl for l in lots):
                    mv = "pass"                # exactly legal_moves' condition
            if mv is None:
                lm = G.legal_moves(st)
                assert lm, f"no legal moves at ply {st.ply} ({st.phase})"
                mv = rng.choice(lm)
            if mv == "skip":
                skipped_turns += 1
            st = G.apply_move(st, mv)
        assert st.ply < PLY_CAP, "hit the ply cap (should end by skips)"
        assert st.skips >= 2
        _check_final_invariants(st)
        plies.append(st.ply)
        totals, _ = G._score(st)
        scores[0] += totals[0]
        scores[1] += totals[1]
        w = G._winner(st)
        r = G.returns(st)
        if w is None:
            assert r == [0.0, 0.0]
            stats["draw"] += 1
        else:
            assert r[w] == 1.0 and r[1 - w] == -1.0
            stats["dark" if w == DARK else "light"] += 1
    print(f"  playouts: 500 -> {stats}, plies avg {sum(plies)/len(plies):.1f} "
          f"(min {min(plies)}, max {max(plies)}), skips/game "
          f"{skipped_turns/500:.2f}, avg score {scores[0]/500:.1f}-{scores[1]/500:.1f}")


def test_serialize_roundtrip():
    rng = random.Random(3)
    st = G.initial_state({"monuments": True})
    for _ in range(30):
        if G.is_terminal(st):
            break
        st = G.apply_move(st, rng.choice(G.legal_moves(st)))
    d = G.serialize(st)
    st2 = G.deserialize(d)
    assert G.serialize(st2) == d
    assert sorted(G.legal_moves(st2)) == sorted(G.legal_moves(st))
    assert st2.monuments is True


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
    print("urbino selftest: all tests passed")
