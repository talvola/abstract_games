"""Anchor selftest — pure stdlib.

Anchors:
1. Figure 2 of the Abstract Games #5 article (exact position, extracted from
   the magazine scan): the four discussed groups classify exactly as the text
   says — three anchors, plus the away-corner group, the "rare case" white
   group and its cut-off black stone all dead.
2. Figure 3 (the completed worked game, exact position): our scorer reproduces
   Black territory 30 exactly and the printed 9-point White win. (Strict
   totals are B 33 / W 42 vs the printed 32/41: the article's prose overlooked
   one isolated — hence dead — white stone at (4,0) deep inside White's
   territory, which adds one to both sides and leaves the margin unchanged.
   See rules.md.)
3. Unit tests: corner/side classification, home vs away corner anchors,
   non-adjacent-side anchors, swap (recolour + central reflection), double
   pass ends + scores, honest draw, neutral regions.
4. Random playouts terminate within the ply cap.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

PKG = Path(__file__).resolve().parent
_, G = load_from_dir(PKG)

from games.anchor.game import (  # noqa: E402
    BLACK, WHITE, _cells, _groups, _home_corners, _is_anchor, _pair_corner,
    _sides_of, score,
)


def cells(text):
    return {tuple(map(int, t.split(","))) for t in text.split()}


def board_of(black, white):
    b = {c: BLACK for c in cells(black)}
    b.update({c: WHITE for c in cells(white)})
    return b


# --------------------------------------------------------------------------
# Geometry units: sides and corners (size 8, n = 7)
# --------------------------------------------------------------------------
def test_sides_and_corners():
    sides = _sides_of(8)
    # Corner cells belong to exactly two sides; their side pairs are adjacent.
    for corner, pair in [((7, 0), {0, 5}), ((7, -7), {0, 1}), ((0, -7), {1, 2}),
                         ((-7, 0), {2, 3}), ((-7, 7), {3, 4}), ((0, 7), {4, 5})]:
        assert sides[corner] == frozenset(pair), (corner, sides[corner])
        assert _pair_corner(8)[frozenset(pair)] == corner
    # A non-corner edge cell belongs to exactly one side.
    assert sides[(7, -3)] == frozenset({0})
    assert sides[(3, -7)] == frozenset({1})
    # Interior cells have no side.
    assert (0, 0) not in sides
    # Home corners: alternating, disjoint, and swapped exactly by the central
    # reflection (which is what makes the pie-rule implementation sound).
    for size in (6, 7, 8):
        bh, wh = _home_corners(size)
        assert len(bh) == len(wh) == 3 and not (bh & wh)
        assert {(-q, -r) for (q, r) in bh} == set(wh)
    bh, wh = _home_corners(8)
    assert bh == {(7, -7), (-7, 0), (0, 7)} and wh == {(7, 0), (0, -7), (-7, 7)}


def test_anchor_units():
    # Lone stone in a HOME corner is an anchor; in an AWAY corner it is not.
    assert _is_anchor({(7, -7)}, BLACK, 8)
    assert not _is_anchor({(7, -7)}, WHITE, 8)
    assert _is_anchor({(-7, 7)}, WHITE, 8)
    assert not _is_anchor({(-7, 7)}, BLACK, 8)
    # A lone edge (non-corner) stone touches one side: not an anchor.
    assert not _is_anchor({(7, -3)}, BLACK, 8)
    # Interior group: no sides, never an anchor.
    assert not _is_anchor({(0, 0), (1, 0)}, BLACK, 8)
    # Two NON-adjacent sides -> anchor for either colour (chain across the
    # board from side 0 (q=7) to side 3 (q=-7)).
    chain = {(q, 0) for q in range(-7, 8)}
    assert _is_anchor(chain, BLACK, 8) and _is_anchor(chain, WHITE, 8)
    # Two adjacent sides not through the corner cell itself: home-corner
    # dependent. Sides 0 (q=7) and 1 (r=-7) meet at (7,-7), Black's home.
    elbow = {(7, -6), (6, -6), (6, -7)}  # touches sides 0 and 1, corner empty
    assert _is_anchor(elbow, BLACK, 8)
    assert not _is_anchor(elbow, WHITE, 8)
    # Occupying the away corner itself still does not make an anchor.
    assert not _is_anchor({(7, 0)}, BLACK, 8)  # (7,0) is White's home
    # Three or more sides: always an anchor (top edge + both upper corners).
    top = {(q, -7) for q in range(0, 8)}  # sides 1, 2 (corner (0,-7)) and 0
    assert _is_anchor(top, BLACK, 8) and _is_anchor(top, WHITE, 8)


# --------------------------------------------------------------------------
# Figure 2 — "Anchor formation" (exact position from the magazine)
# --------------------------------------------------------------------------
FIG2_B = ("-1,5 -1,7 -2,5 -3,6 -4,7 -6,6 -6,7 -7,0 -7,6 0,5 1,5 2,5 "
          "6,-1 6,-2 6,-3 6,-4 6,-5 6,-6 6,-7 6,0 6,1")
FIG2_W = "-1,-4 -1,-5 -1,6 -2,-5 -2,6 -3,7 0,-4 0,-6 0,6 0,7 1,-7"


def test_figure2():
    board = board_of(FIG2_B, FIG2_W)
    # The four groups discussed in the article:
    groups = {frozenset(g): _is_anchor(g, BLACK, 8) for g in _groups(board, BLACK)}
    groups.update({frozenset(g): _is_anchor(g, WHITE, 8) for g in _groups(board, WHITE)})
    # 1. single black stone in the upper left (home corner (-7,0)) — anchor
    assert groups[frozenset({(-7, 0)})] is True
    # 2. black group running down the right side — anchor (touches the top
    #    side at (6,-7) and the lower-right side at (6,1): non-adjacent)
    right = frozenset({(6, r) for r in range(-7, 2)})
    assert right in groups and groups[right] is True
    # 3. white group at the top — anchor (two adjacent sides meeting at the
    #    top corner (0,-7), White's home; the corner cell itself is empty)
    wtop = frozenset(cells("1,-7 0,-6 -2,-5 -1,-5 -1,-4 0,-4"))
    assert wtop in groups and groups[wtop] is True
    # 4. small black group on the lower left — NOT an anchor (two adjacent
    #    sides straddling the away corner (-7,7))
    lowleft = frozenset(cells("-7,6 -6,6 -6,7"))
    assert lowleft in groups and groups[lowleft] is False
    # The "rare case" at the bottom: the white group (touching sides 4 and 5
    # around Black's home corner (0,7)) is dead, and so is the black stone it
    # cuts off — explicit connection only, no removal-then-reconnect.
    wbottom = frozenset(cells("-3,7 -2,6 -1,6 0,6 0,7"))
    assert wbottom in groups and groups[wbottom] is False
    assert groups[frozenset({(-1, 7)})] is False
    # The overarching black group at the bottom IS an anchor (home corner (0,7)).
    bbottom = frozenset(cells("-4,7 -3,6 -2,5 -1,5 0,5 1,5 2,5"))
    assert bbottom in groups and groups[bbottom] is True
    # Full dead accounting.
    dead, _, pris, _ = score(board, 8)
    assert dead[BLACK] == set(lowleft) | {(-1, 7)}
    assert dead[WHITE] == set(wbottom)
    assert pris == [5, 4]  # Black takes 5 white prisoners, White 4 black


# --------------------------------------------------------------------------
# Figure 3 — the completed worked game (exact position from the magazine)
# --------------------------------------------------------------------------
FIG3_B = ("-1,-3 -1,1 -1,4 -1,5 -2,-2 -2,1 -2,2 -2,3 -2,4 -3,-1 -3,-2 -3,0 "
          "-3,1 -3,4 -3,5 -3,6 -4,-1 -4,1 -4,7 -5,-1 -5,1 -5,2 -5,3 -5,7 "
          "-6,0 -6,3 -7,0 -7,3 0,-1 0,-2 0,-3 0,0 0,1 0,5 1,-5 1,-6 1,-7 "
          "1,0 1,4 2,-1 2,-6 2,3 3,-6 3,3 4,-5 4,-6 4,3 5,-5 5,0 6,-6 7,-7")
FIG3_W = ("-1,-4 -1,2 -1,3 -2,-3 -2,0 -3,-3 -3,2 -3,3 -4,-2 -4,0 -4,2 -4,3 "
          "-4,4 -4,5 -4,6 -5,-2 -5,4 -5,6 -6,-1 -6,4 -6,7 -7,4 0,-4 0,-5 "
          "0,-6 0,-7 0,2 0,3 0,4 1,-1 1,-2 1,-3 1,-4 1,1 1,3 2,-2 2,-5 2,0 "
          "2,2 3,-1 3,-2 3,-4 3,-5 3,2 4,-4 4,0 4,2 5,-4 5,2 6,-5 7,-6")


def test_figure3():
    board = board_of(FIG3_B, FIG3_W)
    assert len(board) == 102  # 51 black + 51 white
    dead, terr, pris, totals = score(board, 8)
    # The article names one dead black stone; strict rules also find three
    # isolated (anchorless) white singletons — the prose counted only two,
    # overlooking (4,0) inside White's own territory.
    assert dead[BLACK] == {(5, 0)}
    assert dead[WHITE] == {(4, 0), (-4, 0), (-2, 0)}
    # Black territory matches the printed count exactly.
    assert terr[BLACK] == 30
    # White territory = printed 40 + the hex vacated by the overlooked stone.
    assert terr[WHITE] == 41
    assert pris == [3, 1]
    assert totals == [33, 42]
    # The printed result is preserved: White wins by exactly 9.
    assert totals[WHITE] - totals[BLACK] == 9
    # Every empty hex ends up as someone's territory in this position.
    assert terr[BLACK] + terr[WHITE] == len(_cells(8)) - len(board) + 4


def test_figure3_endgame_flow():
    # Reach the terminal state through the engine: replay the position via
    # apply_move (padding with a pass when one colour runs out), then double
    # pass; White must win.
    g = G
    s = g.initial_state({"size": 8, "pie": False})
    blacks = sorted(FIG3_B.split())
    whites = sorted(FIG3_W.split())
    for i in range(max(len(blacks), len(whites))):
        s = g.apply_move(s, blacks[i] if i < len(blacks) else "pass")
        s = g.apply_move(s, whites[i] if i < len(whites) else "pass")
    assert not g.is_terminal(s)
    s = g.apply_move(s, "pass")
    s = g.apply_move(s, "pass")
    assert g.is_terminal(s)
    assert g.returns(s) == [-1.0, 1.0]
    cap = g.render(s)["caption"]
    assert "White wins" in cap and "42" in cap and "33" in cap


# --------------------------------------------------------------------------
# Engine-level units
# --------------------------------------------------------------------------
def test_pass_and_draw():
    g = G
    s = g.initial_state({"size": 8})
    assert g.legal_moves(s).count("pass") == 1
    assert "swap" not in g.legal_moves(s)  # not on Black's first move
    s = g.apply_move(s, "pass")
    assert "swap" not in g.legal_moves(s)  # no stone to adopt
    s = g.apply_move(s, "pass")
    assert g.is_terminal(s)
    assert g.returns(s) == [0.0, 0.0]  # empty board: honest draw


def test_neutral_regions_and_honest_draw():
    g = G
    s = g.initial_state({"size": 6, "pie": False})
    # Black takes his home corner (5,-5); White takes hers ((-5,5)); both are
    # anchors (alive), and the single empty region touches both colours -> all
    # neutral: a genuine 0-0 tie, scored as an honest draw.
    s = g.apply_move(s, "5,-5")
    s = g.apply_move(s, "-5,5")
    s2 = g.apply_move(g.apply_move(s, "pass"), "pass")
    assert g.is_terminal(s2) and g.returns(s2) == [0.0, 0.0]
    _, terr, pris, _ = score(s2.board, 6)
    assert terr == [0, 0] and pris == [0, 0]


def test_enclosed_territory_and_prisoner():
    g = G
    s = g.initial_state({"size": 6, "pie": False})
    # Black walls off his home corner (5,-5) with (4,-5), (4,-4), (5,-4):
    # the wall touches sides 1 and 0 — adjacent, meeting at the home corner
    # (5,-5) — so it is an anchor even though the corner cell stays empty.
    # White wastes moves: a pair on the bottom side ((0,5) is even Black's
    # home corner) and a stone on (5,-5) itself — a lone stone in the
    # OPPONENT's home corner is anchorless, hence dead.
    seq = [("4,-5", "0,5"), ("4,-4", "-1,5"), ("5,-4", "5,-5")]
    for bm, wm in seq:
        s = g.apply_move(s, bm)
        s = g.apply_move(s, wm)
    s = g.apply_move(s, "pass")
    s = g.apply_move(s, "pass")
    assert g.is_terminal(s)
    dead, terr, pris, totals = score(s.board, 6)
    assert dead[BLACK] == set()
    # (0,5)+(-1,5): sides {4,5} straddling Black's home corner (0,5) -> dead;
    # (5,-5): lone stone in Black's home corner -> dead.
    assert dead[WHITE] == {(5, -5), (0, 5), (-1, 5)}
    # After removal only the black wall remains: the vacated corner (walled
    # off) and the whole outside region border only Black -> all 88 empty
    # hexes are Black territory, plus 3 prisoners.
    assert terr == [88, 0] and pris == [3, 0]
    assert totals == [91, 0]
    assert g.returns(s) == [1.0, -1.0]


def test_swap():
    g = G
    s = g.initial_state({"size": 8, "pie": True})
    s = g.apply_move(s, "7,-7")  # Black takes his own home corner
    assert "swap" in g.legal_moves(s)
    s2 = g.apply_move(s, "swap")
    # Recoloured AND centrally reflected: White now owns (-7,7) — which is
    # WHITE's home corner, mirroring Black's original home-corner stone.
    assert s2.board == {(-7, 7): WHITE}
    assert g.current_player(s2) == BLACK
    assert "swap" not in g.legal_moves(s2)  # once only
    # With pie off there is no swap.
    s3 = g.initial_state({"size": 8, "pie": False})
    s3 = g.apply_move(s3, "0,0")
    assert "swap" not in g.legal_moves(s3)
    # describe_move
    assert g.describe_move(s, "swap") == "swap (pie)"
    assert g.describe_move(s, "pass") == "pass"
    assert g.describe_move(s, "1,-2") == "1,-2"


def test_random_playouts():
    g = G
    for seed in (1, 2, 3):
        rng = random.Random(seed)
        for size in (6, 8):
            s = g.initial_state({"size": size})
            cap = 2 * len(_cells(size)) + 16
            n = 0
            while not g.is_terminal(s):
                s = g.apply_move(s, rng.choice(g.legal_moves(s)))
                n += 1
                assert n <= cap + 2
            r = g.returns(s)
            assert len(r) == 2 and r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0])
            # heuristic contract: list of per-player payoffs
            h = g.heuristic(s)
            assert len(h) == 2 and abs(h[0] + h[1]) < 1e-9


def test_serialize_roundtrip():
    g = G
    rng = random.Random(7)
    s = g.initial_state({"size": 8})
    for _ in range(40):
        if g.is_terminal(s):
            break
        s = g.apply_move(s, rng.choice(g.legal_moves(s)))
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d
    assert g.render(s)["caption"] == g.render(s2)["caption"]


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok {t.__name__}")
    print(f"anchor selftest: all {len(tests)} tests passed")


if __name__ == "__main__":
    main()
