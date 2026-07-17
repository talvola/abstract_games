"""Sunjang Baduk selftest — pure stdlib (agp + this game only).

Primary anchor: Bill Spight's worked 9x9 counting example on Sensei's Library
(https://senseis.xmp.net/?SunjangBadukCounting), transcribed directly from the
page's wiki `boarddata` (X=Black, O=White, rows top-to-bottom):

  1) "Board before counting"  -> removal must reproduce 2) "Ready for
     counting" EXACTLY, and score Black 29 / White 31 (W+2).
  Plus the page's two ko-resolution positions from Bill's follow-up:
  "Black wins ko" -> 29/29 (jigo; its post-removal board is the page's
  "5) Territory" diagram) and "White wins ko" -> Black 28 / White 31.

Setup anchor: the 17-stone prescribed layout from the SunjangBaduk page's
boarddata (identical to the Wikipedia Go-variants diagram): White D16 K16 D13
Q13 D7 Q7 K4 Q4, Black G16 N16 Q16 D10 Q10 D4 G4 N4 + tengen K10; White moves
first.  The layout is 180-degree rotation symmetric colour-PRESERVING and (for
the 16 non-tengen stones) 90-degree rotation symmetric colour-SWAPPING.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import games.sunjang_baduk.game as G  # noqa: E402

GAME = G.SunjangBaduk()
BLACK, WHITE, SIZE = G.BLACK, G.WHITE, G.SIZE


def parse(diagram):
    board = {}
    for r, row in enumerate(diagram.split("|")):
        for c, ch in enumerate(row):
            if ch == "X":
                board[(c, r)] = BLACK
            elif ch == "O":
                board[(c, r)] = WHITE
    return board


# --- SL SunjangBadukCounting boarddata, verbatim ---------------------------
BEFORE = parse("...XXO...|...XO.O..|..XXOO...|..XXXO...|...XOO...|"
               "..X.XO...|...XXO.O.|...XOO...|...XOO...")
READY = parse("...XXO...|...XO....|...XO....|...XXO...|...XOO...|"
              "....XO...|....XO...|...XO....|...XO....")
BLACK_WINS_KO = parse("...XXO...|...XO.O..|..XXOO...|..XXXO...|...XOO...|"
                      "..X.XO...|...XXO.O.|...XOO...|...XXO...")
BLACK_WINS_KO_TERR = parse("...XXO...|...XO....|...XO....|...XXO...|...XOO...|"
                           "....XO...|....XO...|...XOO...|...XXO...")
WHITE_WINS_KO = parse("...XXO...|...XO.O..|..XXOO...|..XOOO...|...XOO...|"
                      "..X.XO...|...XXO.O.|...XOO...|...XXO...")


def test_counting_anchor():
    walls = G.remove_interior(BEFORE, 9)
    assert walls == READY, "removal must reproduce SL's 'Ready for counting' diagram"
    b, w = G.sunjang_score(BEFORE, 9, 0.0)
    assert (b, w) == (29, 31), f"expected B29/W31 (W+2), got B{b}/W{w}"

    assert G.remove_interior(BLACK_WINS_KO, 9) == BLACK_WINS_KO_TERR
    assert G.sunjang_score(BLACK_WINS_KO, 9, 0.0) == (29, 29)   # jigo
    assert G.sunjang_score(WHITE_WINS_KO, 9, 0.0) == (28, 31)   # W+3


def test_setup():
    s = GAME.initial_state({})
    assert len(s.board) == 17
    assert sum(1 for v in s.board.values() if v == WHITE) == 8
    assert sum(1 for v in s.board.values() if v == BLACK) == 9   # incl. tengen
    assert s.board[(9, 9)] == BLACK                              # K10 tengen
    assert s.to_move == WHITE                                    # White first
    # corner star points alternate: D16=W, Q16=B, Q4=W, D4=B
    assert s.board[(3, 3)] == WHITE and s.board[(15, 3)] == BLACK
    assert s.board[(15, 15)] == WHITE and s.board[(3, 15)] == BLACK
    # 180-degree rotation, colour-preserving
    for (c, r), v in s.board.items():
        assert s.board[(18 - c, 18 - r)] == v
    # 90-degree rotation, colour-swapping (the 16 non-tengen stones)
    for (c, r), v in s.board.items():
        if (c, r) == (9, 9):
            continue
        assert s.board[(r, 18 - c)] == 1 - v


def test_first_moves_and_notation():
    s = GAME.initial_state({})
    moves = GAME.legal_moves(s)
    assert len(moves) == 361 - 17 + 1        # every empty point + pass
    assert "9,9" not in moves and "pass" in moves
    assert GAME.describe_move(s, "3,3") == "D16"
    assert GAME.describe_move(s, "9,9") == "K10"
    assert GAME.describe_move(s, "15,15") == "Q4"
    # White plays, then it is Black's turn
    s2 = GAME.apply_move(s, "9,7")           # K12
    assert s2.board[(9, 7)] == WHITE and s2.to_move == BLACK


def test_double_pass_is_honest_draw():
    s = GAME.initial_state({})               # komi 0
    s = GAME.apply_move(s, "pass")
    s = GAME.apply_move(s, "pass")
    assert GAME.is_terminal(s)
    # nothing enclosed: the single empty region touches both colours -> 0-0
    assert GAME.returns(s) == [0.0, 0.0]
    # with komi 4.5, the same double-pass is a White win
    s = GAME.initial_state({"komi": 4.5})
    s = GAME.apply_move(s, "pass")
    s = GAME.apply_move(s, "pass")
    assert GAME.returns(s) == [-1.0, 1.0]


def test_capture_and_superko_core_intact():
    # White stone K12 put in atari and captured; K12 becomes empty again.
    s = GAME.initial_state({})
    for mv in ["9,7",            # W K12
               "9,6", "0,0",     # B K13,  W A19 (elsewhere)
               "8,7", "0,1",     # B J12,  W A18
               "10,7", "0,2",    # B L12,  W A17
               "9,8"]:           # B K11 -> captures K12
        s = GAME.apply_move(s, mv)
    assert (9, 7) not in s.board
    assert s.board[(9, 8)] == BLACK


def test_heuristic_is_per_seat_payoffs():
    s = GAME.initial_state({})
    h = GAME.heuristic(s)
    assert isinstance(h, list) and len(h) == 2
    assert abs(h[0] + h[1]) < 1e-9


def main():
    test_counting_anchor()
    test_setup()
    test_first_moves_and_notation()
    test_double_pass_is_honest_draw()
    test_capture_and_superko_core_intact()
    test_heuristic_is_per_seat_payoffs()
    print("sunjang_baduk selftest: all tests passed")


if __name__ == "__main__":
    main()
