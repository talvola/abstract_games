"""Connect6 self-test — run with: PYTHONPATH=. python3 games/connect6/selftest.py

Pure stdlib + the agp package only. Fast (a few seconds): a short conformance
check plus rule-specific positions. Asserts the correctness anchor:

  * Black plays exactly ONE stone on the very first move of the game.
  * Every turn thereafter (BOTH colours) places exactly TWO stones, on two
    distinct empty intersections.
  * A line of SIX OR MORE of one colour wins immediately (overlines win too).
  * The two-stone move is a `>`-path of two cells; the opening is a single cell.

No published constant is asserted (Connect6 has no canonical perft number); the
anchor is the rule structure itself, verified directly.
"""

import sys

from agp.conformance import check
from games.connect6.game import Connect6, Connect6State


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


# Minimal manifest stub for the conformance harness (it only reads players).
MANIFEST = {"players": {"min": 2, "max": 2}}


def main():
    g = Connect6()

    # --- conformance (purity, serialize round-trip, termination, etc.) -------
    # Default board (19x19) via the shared harness; a few random self-play games.
    rep = check(g, MANIFEST, games=2, seed=7)
    if not rep.ok:
        fail("conformance failed:\n" + rep.summary())

    # --- ANCHOR 1: opening move places exactly ONE stone --------------------
    s0 = g.initial_state({"size": 19})
    if g.current_player(s0) != 0:
        fail("Black (player 0) must move first")
    if g._stones_this_turn(s0) != 1:
        fail("first turn must place exactly one stone")
    opening = g.legal_moves(s0)
    # opening list is single cells (no '>'), one per empty cell
    if any(">" in m for m in opening):
        fail("opening moves must be single cells (one stone)")
    if len(opening) != 19 * 19:
        fail("opening should offer every empty intersection")
    s1 = g.apply_move(s0, "9,9")
    if len(s1.board) != 1 or s1.board.get((9, 9)) != 0:
        fail("opening move must place one Black stone")
    if g.current_player(s1) != 1:
        fail("after Black's opening, White is to move")

    # --- ANCHOR 2: every later turn places exactly TWO stones ---------------
    if g._stones_this_turn(s1) != 2:
        fail("White's first turn must place two stones")
    later = g.legal_moves(s1)
    if not later or any(m.count(">") != 1 for m in later):
        fail("two-stone moves must be a >-path of exactly two cells")
    s2 = g.apply_move(s1, "0,0>18,18")  # any two distinct empty cells
    if len(s2.board) != 3:
        fail("a two-stone turn must add two stones to the board")
    if s2.board.get((0, 0)) != 1 or s2.board.get((18, 18)) != 1:
        fail("both placed stones must belong to the mover (White)")
    if g.current_player(s2) != 0:
        fail("turns alternate after White's two-stone turn")

    # also confirm Black's SECOND turn (ply 2) is two stones, not one
    if g._stones_this_turn(s2) != 2:
        fail("Black's second turn must place two stones (only the opening is one)")

    # order of the two cells must not matter (same resulting board)
    a = g.apply_move(s1, "3,3>5,5")
    b = g.apply_move(s1, "5,5>3,3")
    if g.serialize(a)["board"] != g.serialize(b)["board"]:
        fail("two-stone move must be order-independent")

    # distinct-cell requirement enforced
    try:
        g.apply_move(s1, "7,7>7,7")
        fail("placing two stones on the same cell must be rejected")
    except ValueError:
        pass

    # occupied cell rejected
    try:
        g.apply_move(s1, "9,9>4,4")  # (9,9) holds Black's opening stone
        fail("placing on an occupied cell must be rejected")
    except ValueError:
        pass

    # wrong stone count rejected (one stone on a two-stone turn)
    try:
        g.apply_move(s1, "4,4")
        fail("a single stone on a two-stone turn must be rejected")
    except ValueError:
        pass

    # --- ANCHOR 3: SIX in a row wins (and overline wins) --------------------
    # Build a position where Black already has five in a row and it is Black's
    # turn; Black completes six with one of the two placed stones.
    board = {(c, 5): 0 for c in range(5)}        # Black at (0..4, 5)
    board[(10, 0)] = 1                            # a White stone somewhere
    s = Connect6State(size=19, board=board, to_move=0, ply=4)
    if g.is_terminal(s):
        fail("five in a row should NOT be terminal in Connect6")
    win = g.apply_move(s, "5,5>12,12")           # (5,5) completes six
    if win.winner != 0:
        fail("six Black stones in a row must win for Black")
    if not g.is_terminal(win):
        fail("a completed six-line must be terminal")
    if g.returns(win) != [1.0, -1.0]:
        fail("returns must reward the winner")

    # vertical six
    vb = {(7, r): 1 for r in range(6)}
    sv = Connect6State(size=19, board=dict(vb), to_move=1, ply=5)
    # remove one to make it a 5-then-complete scenario
    del sv.board[(7, 5)]
    wv = g.apply_move(sv, "7,5>1,1")
    if wv.winner != 1:
        fail("vertical six must win for White")

    # diagonal six
    db = {(i, i): 0 for i in range(5)}
    sd = Connect6State(size=19, board=db, to_move=0, ply=6)
    wd = g.apply_move(sd, "5,5>9,1")
    if wd.winner != 0:
        fail("diagonal six must win for Black")

    # overline (seven) also wins
    ob = {(c, 9): 0 for c in range(6)}           # already six? build five+gap
    ob = {(c, 9): 0 for c in [0, 1, 2, 3, 5]}    # gap at 4
    so = Connect6State(size=19, board=ob, to_move=0, ply=7)
    # placing at (4,9) and (6,9) makes a run of seven (0..6)
    wo = g.apply_move(so, "4,9>6,9")
    if wo.winner != 0:
        fail("an overline (seven in a row) must also win")

    # five in a row with NO sixth is not a win
    nb = {(c, 12): 0 for c in range(4)}
    sn = Connect6State(size=19, board=nb, to_move=0, ply=8)
    nn = g.apply_move(sn, "4,12>16,16")          # makes five at row 12, plus stray
    if nn.winner is not None:
        fail("five in a row must NOT win in Connect6")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
