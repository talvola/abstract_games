"""Correctness anchors for Crazy 38's (pure stdlib).

Anchors:
  (a) the 38-cell board set, asserted as DATA with documented labels;
  (b) perft(1)=16 and perft(2)=256 from the setup, hand-justified below;
  (c) rule positions for every board-edge quirk (pawn paths, promotion,
      tip-bridged rook loop, bishop quiet step, drops, king-home win);
  (d) move-string uniqueness, serialize round-trip, and random playouts.

Run:  cd engine && PYTHONPATH=. python3 games/crazy_38s/selftest.py
"""
import random

from games.crazy_38s.game import (
    Crazy38s, CState, CELLS, FILE_NUMS, LETTERS, WHITE, BLACK,
    KNIGHT_TABLE, _piece_moves, _all_legal, _in_check, _label,
)

g = Crazy38s()


def lbl_set(board, cell, owner, pt):
    return sorted(_label(c) for c, _f in _piece_moves(board, cell, owner, pt))


def cell_of(s):     # "a8" -> (8, 1)
    return (int(s[1:]), LETTERS.index(s[0]) + 1)


# -- (a) board set -----------------------------------------------------------
def test_board():
    assert len(CELLS) == 38
    # exact transcription (letter -> numbers) from 38squares.notation.gif
    expect = {
        "a": [3, 5, 6, 8], "b": [5, 6], "c": [1, 3, 4, 5, 6, 7, 8],
        "d": [3, 4, 5, 6, 7, 8], "e": [1, 2, 3, 4, 5, 6],
        "f": [1, 2, 3, 4, 5, 6, 8], "g": [3, 4], "h": [1, 3, 4, 6],
    }
    for letter, nums in expect.items():
        l = LETTERS.index(letter) + 1
        assert FILE_NUMS[l] == nums, (letter, FILE_NUMS[l])
        for n in nums:
            assert (n, l) in CELLS
    assert sum(len(v) for v in expect.values()) == 38


# -- initial setup -----------------------------------------------------------
def test_setup():
    s = g.initial_state()
    b = s.board
    assert len(b) == 20
    # counts per side
    for o in (WHITE, BLACK):
        kinds = sorted(pt for c, (ow, pt) in b.items() if ow == o)
        assert kinds == sorted(["K", "P", "P", "P", "P", "S", "G", "N", "B", "R"]), (o, kinds)
    # specific kings on the two home tips
    assert b[(1, 8)] == (WHITE, "K")   # h1
    assert b[(8, 1)] == (BLACK, "K")   # a8
    # a few transcribed placements
    assert b[(3, 6)] == (WHITE, "R")   # Rf3
    assert b[(4, 7)] == (WHITE, "B")   # Bg4
    assert b[(6, 3)] == (BLACK, "R")   # Rc6
    # 180-degree symmetry (n,l) -> (9-n,9-l), colours swapped
    for (n, l), (o, pt) in b.items():
        m = b[(9 - n, 9 - l)]
        assert m == (1 - o, pt)


# -- (b) perft ---------------------------------------------------------------
def test_perft():
    s = g.initial_state()
    lm = g.legal_moves(s)
    # hand count: e1->c1(1) e3->{e4,d3}(2) f4->{f5,e4}(2) h4->h6(1)  [pawns=6]
    #  Ne2->{c3,d4}(2)  Bg4->{f5,e6,xd7,h3}(4)  Rf3 boxed(0)
    #  Sg3->h3(1)  Gf2->f1(1)  Kh1->{h3,f1}(2)   total = 16
    # (the curved-geometry Knight on e2 reaches {c3,d4,f4,g3,h1}; f4/g3/h1 are
    #  own pieces, so 2 legal — the flat-lattice knight wrongly listed e2->c1.)
    assert len(lm) == 16, len(lm)
    assert len(set(lm)) == 16
    tot = sum(len(g.legal_moves(g.apply_move(s, m))) for m in lm)
    assert tot == 256, tot


# -- (c) pawn geometry & promotion ------------------------------------------
def test_pawn():
    E = {}
    assert lbl_set(E, (3, 5), WHITE, "P") == ["d3", "e4"]   # White forward = +number / -letter
    assert lbl_set(E, (3, 5), BLACK, "P") == ["e2", "f3"]   # Black forward = -number / +letter
    # promotion: a White pawn stepping onto a8 (Black's home) becomes a Queen
    b = {(6, 1): (WHITE, "P"), (1, 8): (WHITE, "K"), (5, 3): (BLACK, "K")}
    s = CState(board=b, to_move=WHITE)
    lm = g.legal_moves(s)
    assert "6,1>8,1" in lm                  # a6 -> a8
    s2 = g.apply_move(s, "6,1>8,1")
    assert s2.board[(8, 1)] == (WHITE, "Q")


# -- generals / knight / king geometry --------------------------------------
def test_steppers():
    E = {}
    assert lbl_set(E, (4, 5), WHITE, "S") == ["d3", "d4", "e3", "e5", "f4", "f5"]
    assert lbl_set(E, (4, 5), WHITE, "G") == ["d4", "d5", "e3", "e5", "f3", "f4"]
    assert lbl_set(E, (4, 5), WHITE, "K") == ["d3", "d4", "d5", "e3", "e5", "f3", "f4", "f5"]
    # deep-interior knight (no tip in reach) == the ordinary chess leap targets
    assert lbl_set(E, (4, 5), WHITE, "N") == ["c3", "c5", "d6", "f2", "f6", "g3"]
    # colour independence of the generals
    assert lbl_set(E, (4, 5), BLACK, "S") == lbl_set(E, (4, 5), WHITE, "S")
    assert lbl_set(E, (4, 5), BLACK, "G") == lbl_set(E, (4, 5), WHITE, "G")


def test_knight_geometry():
    # The two knight.gif ground truths, reproduced EXACTLY by the curved table.
    assert lbl_set({}, cell_of("a8"), BLACK, "N") == ["b5", "c6", "d7"]
    assert lbl_set({}, cell_of("f3"), WHITE, "N") == ["d4", "e1", "e5", "h1", "h4"]
    # the flat-lattice knight's spurious bridge-moves are gone
    assert cell_of("c1") not in KNIGHT_TABLE[cell_of("e2")]   # e2 !-> c1
    assert cell_of("f8") not in KNIGHT_TABLE[cell_of("d7")]   # d7 !-> f8
    # a knight leap must never ROUTE THROUGH a tip square (that walks around the
    # loop and overshoots to a non-knight cell ~2x too far); these are the
    # spurious long-range moves produced when a tip is an intermediate step.
    for src, bad in (("a5", "c8"), ("a5", "c1"), ("a6", "d8"), ("d8", "h6"),
                     ("c3", "f1"), ("e1", "h3"), ("f8", "h4")):
        assert cell_of(bad) not in KNIGHT_TABLE[cell_of(src)], (src, bad)
    # the over-the-tip leaps the flat knight missed are present
    assert cell_of("h1") in KNIGHT_TABLE[cell_of("f3")]
    assert cell_of("a8") in KNIGHT_TABLE[cell_of("d7")]
    # the move relation is symmetric across all 38 cells (x attacks y <=> y attacks x)
    for c in CELLS:
        for t in KNIGHT_TABLE[c]:
            assert c in KNIGHT_TABLE[t], (c, t)
        assert c not in KNIGHT_TABLE[c]        # never targets itself


# -- (c) rook loop-effect across tip-bridged gaps ---------------------------
def test_rook_loop():
    E = {}
    # a rook on a5 slides up the a-file THROUGH the missing a7 (bridged by tip a8)
    # and down through the missing a4 (bridged by tip a3); plus all of rank 5.
    assert lbl_set(E, (5, 1), WHITE, "R") == \
        ["a3", "a6", "a8", "b5", "c5", "d5", "e5", "f5"]


# -- (c) bishop diagonal slide + conditional quiet orthogonal step -----------
def test_bishop():
    # friend on orth neighbour e4 -> quiet non-capturing steps to empty orth
    # cells c4,d3 appear; enemy on orth neighbour d5 can NOT be taken orthogonally
    b = {(4, 4): (WHITE, "B"), (4, 5): (WHITE, "P"), (5, 4): (BLACK, "P")}
    with_friend = lbl_set(b, (4, 4), WHITE, "B")
    assert "c4" in with_friend and "d3" in with_friend
    assert "d5" not in with_friend                 # bishop never captures orthogonally
    # remove the friend -> the quiet orthogonal steps vanish, diagonals remain
    b2 = {(4, 4): (WHITE, "B"), (5, 4): (BLACK, "P")}
    no_friend = lbl_set(b2, (4, 4), WHITE, "B")
    assert "c4" not in no_friend and "d3" not in no_friend
    assert "e5" in no_friend and "c3" in no_friend  # diagonals unaffected


# -- (c) drops ---------------------------------------------------------------
def test_drops():
    # captured Queen banks as a Pawn
    b = {(4, 4): (WHITE, "R"), (4, 6): (BLACK, "Q"),
         (1, 8): (BLACK, "K"), (8, 3): (WHITE, "K")}
    s = CState(board=b, to_move=WHITE)
    s2 = g.apply_move(s, "4,4>4,6")
    assert s2.hands[WHITE] == {"P": 1}

    # a Pawn may NOT be dropped on the opponent's home square (a8 for White)
    b = {(1, 8): (WHITE, "K"), (8, 1): (BLACK, "K"), (5, 5): (WHITE, "R")}
    s = CState(board=b, hands={WHITE: {"P": 1}, BLACK: {}}, to_move=WHITE)
    lm = g.legal_moves(s)
    assert "P@8,1" not in lm
    assert "S@8,1" not in lm  # (S not in hand anyway) sanity
    # but a non-home empty cell is a legal pawn drop
    assert any(m.startswith("P@") for m in lm)


def test_pawn_drop_no_mate():
    # A found position (random self-play) where dropping a Pawn on c8 (=8,3)
    # would checkmate Black. The mate rule must forbid exactly that drop while
    # the "loose" generation (rule off) still lists it.
    b = {(8, 1): (BLACK, "K"), (1, 8): (WHITE, "K"), (2, 6): (WHITE, "G"),
         (3, 5): (WHITE, "P"), (4, 3): (BLACK, "N"), (2, 5): (WHITE, "P"),
         (7, 4): (WHITE, "B"), (4, 4): (BLACK, "P"), (4, 6): (WHITE, "P"),
         (4, 7): (WHITE, "S"), (5, 4): (WHITE, "R"), (5, 1): (BLACK, "B"),
         (4, 5): (WHITE, "N"), (3, 3): (BLACK, "P"), (6, 8): (BLACK, "P"),
         (6, 1): (BLACK, "S"), (5, 5): (WHITE, "G"), (5, 2): (BLACK, "R")}
    hands = {WHITE: {"P": 2}, BLACK: {}}
    strict = set(_all_legal(b, hands, WHITE, pawn_mate=True))
    loose = set(_all_legal(b, hands, WHITE, pawn_mate=False))
    assert "P@8,3" in loose
    assert "P@8,3" not in strict
    # confirm it really is mate: after the drop Black is in check with no reply
    s = CState(board=b, hands=hands, to_move=WHITE)
    s2 = g.apply_move(s, "P@8,3")
    assert s2.winner == WHITE and g.is_terminal(s2)


# -- king-to-home win --------------------------------------------------------
def test_home_win():
    b = {(6, 1): (WHITE, "K"), (1, 8): (BLACK, "K")}   # White K on a6, next to a8
    s = CState(board=b, to_move=WHITE)
    assert "6,1>8,1" in g.legal_moves(s)
    s2 = g.apply_move(s, "6,1>8,1")
    assert s2.winner == WHITE and g.is_terminal(s2)
    assert g.returns(s2) == [1.0, -1.0]


# -- (d) serialize round-trip ------------------------------------------------
def test_serialize():
    s = g.initial_state()
    r = random.Random(7)
    for _ in range(30):
        if g.is_terminal(s):
            break
        s = g.apply_move(s, r.choice(g.legal_moves(s)))
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d
    # heuristic well-formed (list of 2, bounded)
    h = g.heuristic(s)
    assert isinstance(h, list) and len(h) == 2 and all(-1.001 <= x <= 1.001 for x in h)


# -- (d) termination + uniqueness over random games --------------------------
def test_random_games():
    r = random.Random(11)
    for i in range(40):
        s = g.initial_state()
        steps = 0
        while not g.is_terminal(s) and steps < 1000:
            lm = g.legal_moves(s)
            assert lm, "non-terminal with no legal moves"
            assert len(set(lm)) == len(lm), "duplicate legal move"
            s = g.apply_move(s, r.choice(lm))
            steps += 1
        assert g.is_terminal(s), "game did not terminate under the cap"
        rr = g.returns(s)
        assert len(rr) == 2 and abs(rr[0] + rr[1]) < 1e-9  # zero-sum


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("crazy_38s selftest: all passed")


if __name__ == "__main__":
    run()
