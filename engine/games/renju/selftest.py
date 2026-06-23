"""Renju correctness anchor — pure-stdlib, fast (no published perft).

Run:  PYTHONPATH=. python3 games/renju/selftest.py

Anchor = baked rule assertions:
  (1) placement-only alternation on 15x15, Black first;
  (2) WHITE wins with five OR MORE in a row (overlines win for White);
  (3) BLACK wins ONLY with an exact five (an overline of six+ is NOT a win
      for Black — and is a forbidden loss);
  (4) BLACK forbidden moves lose immediately (double-three, double-four,
      overline) unless the move is simultaneously an exact-five win;
  (5) WHITE has no restrictions;
  plus hand-built rule-specific positions.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import sys

from games.renju.game import Renju, RenjuState, BLACK, WHITE, RenjuRules, SIZE


G = Renju()


def board_from(black, white):
    """Build a board dict from lists of (c,r) cells."""
    b = {}
    for (c, r) in black:
        b[(c, r)] = BLACK
    for (c, r) in white:
        b[(c, r)] = WHITE
    return b


def state(black, white, to_move):
    return RenjuState(board=board_from(black, white), to_move=to_move)


def play(s, move):
    return G.apply_move(s, move)


def check(cond, msg):
    if not cond:
        raise AssertionError("FAIL: " + msg)


# ---------------------------------------------------------------------------
# (1) Placement-only alternation, 15x15, Black first.
# ---------------------------------------------------------------------------
def test_basics():
    s = G.initial_state()
    check(G.num_players == 2, "two players")
    check(G.current_player(s) == BLACK, "Black moves first")
    check(len(G.legal_moves(s)) == SIZE * SIZE, "all 225 cells legal at start")
    check(SIZE == 15, "board is 15x15")

    s1 = play(s, "7,7")
    check(G.current_player(s1) == WHITE, "alternates to White")
    check(s1.board[(7, 7)] == BLACK, "Black stone placed")
    check(len(s1.board) == 1, "one stone on board")
    # placement only: previous stones unchanged, none removed
    s2 = play(s1, "0,0")
    check(s2.board[(7, 7)] == BLACK and s2.board[(0, 0)] == WHITE,
          "stones persist, placement only")
    check((7, 7) not in [m for m in G.legal_moves(s2)
                         if RenjuRules is None], "occupied not playable")
    check("7,7" not in G.legal_moves(s2), "occupied cell no longer legal")
    # purity: apply_move did not mutate s1
    check(len(s1.board) == 1, "apply_move is pure (s1 unchanged)")


# ---------------------------------------------------------------------------
# (2) WHITE wins with five OR MORE — overlines win for White.
# ---------------------------------------------------------------------------
def test_white_exact_five():
    # White has 4 in a row at row 5, cols 2..5; plays 6,5 to make five.
    s = state(black=[(0, 0)], white=[(2, 5), (3, 5), (4, 5), (5, 5)],
              to_move=WHITE)
    s2 = play(s, "6,5")
    check(s2.winner == WHITE, "White wins with an exact five")
    check(G.is_terminal(s2), "terminal after White five")
    check(G.returns(s2) == [-1.0, 1.0], "returns: White win")


def test_white_overline_wins():
    # White has cols 2,3,4,5,6 at row 8 (already five), and col 1 empty.
    # White plays 1,8 making a SIX in a row (overline) -> still a win for White.
    s = state(black=[(0, 0)],
              white=[(2, 8), (3, 8), (4, 8), (5, 8), (6, 8)],
              to_move=WHITE)
    s2 = play(s, "1,8")
    check(s2.winner == WHITE, "White overline (six) wins for White")
    check(RenjuRules.makes_overline(s2.board, (1, 8), WHITE),
          "white overline detected")


# ---------------------------------------------------------------------------
# (3) BLACK wins ONLY with an exact five.
# ---------------------------------------------------------------------------
def test_black_exact_five_wins():
    # Black has 4 in a row cols 2..5 row 7, both ends open. Plays 6,7 -> exact 5.
    s = state(black=[(2, 7), (3, 7), (4, 7), (5, 7)], white=[(0, 0)],
              to_move=BLACK)
    s2 = play(s, "6,7")
    check(s2.winner == BLACK, "Black wins with exact five")
    check(G.returns(s2) == [1.0, -1.0], "returns: Black win")
    check(RenjuRules.makes_exact_five(s2.board, (6, 7), BLACK),
          "exact five detected for black")


def test_black_overline_not_a_win_and_forbidden():
    # Black has cols 2,3,4,5 and 7 at row 9 (a gap at col 6). White stone dummy.
    # Black plays 6,9 -> fills the gap -> row of SIX (cols 2..7) = overline.
    # This is NOT an exact five (run is 6) -> NOT a win, and IS forbidden
    # (overline) -> Black loses immediately (White wins).
    s = state(black=[(2, 9), (3, 9), (4, 9), (5, 9), (7, 9)], white=[(0, 0)],
              to_move=BLACK)
    s2 = play(s, "6,9")
    check(not RenjuRules.makes_exact_five(s2.board, (6, 9), BLACK),
          "black six is not an exact five")
    check(RenjuRules.makes_overline(s2.board, (6, 9), BLACK),
          "black overline detected")
    check(s2.winner == WHITE,
          "black overline is a forbidden loss (White wins), not a Black win")


def test_black_six_built_from_five_is_loss():
    # Black already has an exact five cols 2..6 at row 11 (but that five was
    # made on a *previous* move; the position is not terminal in this test
    # because we build it directly). Black extends to col 1 making SIX.
    # The extending move makes an overline, not a new exact five through col 1
    # (the run through col 1 is six) -> forbidden loss.
    s = state(black=[(2, 11), (3, 11), (4, 11), (5, 11), (6, 11)],
              white=[(0, 0)], to_move=BLACK)
    s2 = play(s, "1,11")
    check(s2.winner == WHITE, "extending a black five to six is a forbidden loss")


# ---------------------------------------------------------------------------
# (4) Five takes precedence over a forbidden shape.
# ---------------------------------------------------------------------------
def test_five_overrides_forbidden():
    # Construct a move that makes BOTH an exact five (one direction) AND an
    # overline-or-double in another. Easiest: exact five horizontally + would-be
    # double-four. We make the placed stone complete an exact five on one axis
    # and a four on two other axes is hard to guarantee; instead test the rule
    # directly via makes_exact_five overriding overline:
    #
    # Black has a vertical run that becomes an overline AND a horizontal exact
    # five through the SAME placed stone.
    black = [
        # horizontal: cols 2,3,4,5 at row 7 -> placing 6,7 gives exact five
        (2, 7), (3, 7), (4, 7), (5, 7),
        # vertical at col 6: rows 8,9,10,11,12 -> placing 6,7 gives rows
        # 7..12 = SIX vertically (overline)
        (6, 8), (6, 9), (6, 10), (6, 11), (6, 12),
    ]
    s = state(black=black, white=[(0, 0)], to_move=BLACK)
    s2 = play(s, "6,7")
    check(RenjuRules.makes_exact_five(s2.board, (6, 7), BLACK),
          "placed stone makes an exact five (horizontal)")
    check(RenjuRules.makes_overline(s2.board, (6, 7), BLACK),
          "placed stone also makes an overline (vertical)")
    check(s2.winner == BLACK,
          "five takes precedence over the overline -> Black wins")


# ---------------------------------------------------------------------------
# (5) Double-four forbidden loss.
# ---------------------------------------------------------------------------
def test_double_four_forbidden():
    # Build a classic 4-4 cross. Placed stone at (7,7).
    # Horizontal four: black at cols 5,6,8,9 row 7 (gap at 7). Placing 7,7
    #   makes cols 5,6,7,8,9 = exact five -> that's a five, not what we want.
    # So make the placed stone create two *fours* (each needing one more), not
    # a five. Use shapes that are fours (one completing point each):
    #   Horizontal: black at 4,5,6 row 7 + placed 7,7 -> 4,5,6,7 = four
    #       (completing point 3,7 or 8,7 -> straight four, still a four).
    #   Vertical:   black at 7,8 7,9 7,10 + placed 7,7 -> rows 7,8,9,10 = four.
    black = [
        (4, 7), (5, 7), (6, 7),       # horizontal three -> with placed = four
        (7, 8), (7, 9), (7, 10),      # vertical three -> with placed = four
    ]
    s = state(black=black, white=[(0, 0)], to_move=BLACK)
    # Sanity: the placed move must NOT make an exact five (it makes two fours).
    nb = dict(s.board)
    nb[(7, 7)] = BLACK
    check(not RenjuRules.makes_exact_five(nb, (7, 7), BLACK),
          "the 4-4 move is not itself an exact five")
    check(RenjuRules.count_fours(nb, (7, 7)) >= 2,
          "placed stone makes >= 2 fours (double-four)")
    s2 = play(s, "7,7")
    check(s2.winner == WHITE, "double-four is a forbidden loss for Black")


# ---------------------------------------------------------------------------
# (4b) Double-three forbidden loss + single-three is fine.
# ---------------------------------------------------------------------------
def test_double_three_forbidden():
    # Classic 3-3. Placed stone at (7,7) makes two open threes.
    #   Horizontal open three: black at 5,7 and 6,7; placed 7,7 -> _BBB_
    #       (cols 5,6,7 with 4,7 and 8,7 empty) = open three.
    #   Vertical open three: black at 7,8 and 7,9; placed 7,7 -> rows 7,8,9
    #       with 7,6 and 7,10 empty = open three.
    black = [(5, 7), (6, 7), (7, 8), (7, 9)]
    s = state(black=black, white=[(0, 0)], to_move=BLACK)
    nb = dict(s.board)
    nb[(7, 7)] = BLACK
    check(RenjuRules.count_open_threes(nb, (7, 7)) >= 2,
          "placed stone makes >= 2 open threes (double-three)")
    s2 = play(s, "7,7")
    check(s2.winner == WHITE, "double-three is a forbidden loss for Black")


def test_single_three_is_legal():
    # A single open three is fine — Black does not lose.
    #   Horizontal open three only: black 5,7 6,7; placed 7,7.
    black = [(5, 7), (6, 7)]
    s = state(black=black, white=[(0, 0)], to_move=BLACK)
    nb = dict(s.board)
    nb[(7, 7)] = BLACK
    check(RenjuRules.count_open_threes(nb, (7, 7)) == 1,
          "exactly one open three")
    s2 = play(s, "7,7")
    check(s2.winner is None, "a single open three is not forbidden")
    check(not G.is_terminal(s2), "game continues after a single three")


def test_single_four_is_legal():
    # A single four (no second four, no double-three) is legal.
    black = [(4, 7), (5, 7), (6, 7)]
    s = state(black=black, white=[(0, 0)], to_move=BLACK)
    nb = dict(s.board)
    nb[(7, 7)] = BLACK
    check(RenjuRules.count_fours(nb, (7, 7)) == 1, "exactly one four")
    s2 = play(s, "7,7")
    check(s2.winner is None, "a single four is not forbidden")


def test_four_three_is_legal():
    # REGRESSION (open-three vs straight-four bug): the four-three tesuji.
    # Black {(4,7),(5,7),(6,7),(7,8),(7,9)} plays (7,7). This makes a
    # horizontal STRAIGHT FOUR on row 7 (cols 4,5,6,7, open both ends) PLUS a
    # vertical OPEN THREE (rows 7,8,9). A straight four is a FOUR, never an
    # open three, so this is ONE four + ONE open three = a legal four-three,
    # NOT a forbidden double-three. (The bug counted the straight four as a
    # second open three, ruling this strong legal move a forbidden loss.)
    black = [(4, 7), (5, 7), (6, 7), (7, 8), (7, 9)]
    s = state(black=black, white=[(0, 0)], to_move=BLACK)
    nb = dict(s.board)
    nb[(7, 7)] = BLACK
    check(RenjuRules.count_fours(nb, (7, 7)) == 1,
          "four-three: exactly one four (the horizontal straight four)")
    check(RenjuRules.count_open_threes(nb, (7, 7)) == 1,
          "four-three: exactly one open three (the straight four is NOT a "
          "second open three)")
    check(not RenjuRules.makes_overline(nb, (7, 7), BLACK),
          "four-three: not an overline")
    check(not RenjuRules.makes_exact_five(nb, (7, 7), BLACK),
          "four-three: not itself an exact five")
    s2 = play(s, "7,7")
    check(s2.winner is None,
          "four-three is a LEGAL move (winner None), NOT a forbidden "
          "double-three loss")
    check(not G.is_terminal(s2), "game continues after a legal four-three")


# ---------------------------------------------------------------------------
# (5) White is unrestricted — White may make double-three/four/overline freely.
# ---------------------------------------------------------------------------
def test_white_unrestricted():
    # Same 3-3 shape but for WHITE; White must NOT lose.
    white = [(5, 7), (6, 7), (7, 8), (7, 9), (0, 0)]
    s = state(black=[(1, 1)], white=white, to_move=WHITE)
    s2 = play(s, "7,7")
    check(s2.winner is None, "White double-three is allowed (no restriction)")
    check(not G.is_terminal(s2), "game continues; White is unrestricted")


# ---------------------------------------------------------------------------
# serialize round-trip
# ---------------------------------------------------------------------------
def test_serialize_roundtrip():
    s = G.initial_state()
    s = play(s, "7,7")
    s = play(s, "8,8")
    d = G.serialize(s)
    s2 = G.deserialize(d)
    check(G.serialize(s2) == d, "serialize round-trips")


def main():
    tests = [
        test_basics,
        test_white_exact_five,
        test_white_overline_wins,
        test_black_exact_five_wins,
        test_black_overline_not_a_win_and_forbidden,
        test_black_six_built_from_five_is_loss,
        test_five_overrides_forbidden,
        test_double_four_forbidden,
        test_double_three_forbidden,
        test_single_three_is_legal,
        test_single_four_is_legal,
        test_four_three_is_legal,
        test_white_unrestricted,
        test_serialize_roundtrip,
    ]
    for t in tests:
        t()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
