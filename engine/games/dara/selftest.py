"""Dara correctness anchor -- pure stdlib, fast.

No published perft for Dara, so the anchor is a set of baked rule assertions:
 (1) board geometry (6x5 = 30 cells) and 12 pieces per player;
 (2) PLACEMENT: alternate drops; making a three during the drop does NOT capture;
     forming a FOUR during the drop is illegal;
 (3) MOVEMENT: a slide forming an exact orthogonal three removes one enemy piece;
 (4) the no-4-in-a-row rule (a four does not capture and is not a legal move);
 (5) anti-shuffle: sliding a piece out of and back into the same three does not
     re-score; and you may not immediately re-score the identical three;
 (6) WIN: a player reduced below three pieces loses.

Run:  PYTHONPATH=. python3 games/dara/selftest.py
"""

import sys

from games.dara.game import Dara, DState


def ok(cond, msg):
    if not cond:
        print("SELFTEST FAIL:", msg)
        sys.exit(1)


def make(pos, to_move=0, placed=(12, 12), removing=False, w=6, h=5):
    return DState(pos=dict(pos), to_move=to_move, placed=list(placed),
                  removing=removing, width=w, height=h, pieces_each=12)


def main():
    g = Dara()

    # (1) geometry + piece count
    st = g.initial_state()
    ok(st.width == 6 and st.height == 5, "default board is 6x5")
    ok(len(g._cells(st)) == 30, "6x5 board has 30 cells")
    ok(st.pieces_each == 12, "12 pieces per player")
    ok(g.num_players == 2, "two players")

    # initial legal moves = every empty cell (board empty, no 4 possible)
    ok(len(g.legal_moves(st)) == 30, "30 placement moves from empty board")

    # ---- (2) PLACEMENT: a three formed during the drop does NOT capture ----
    # White at (0,0),(1,0); white to drop (2,0) completing a horizontal three.
    pos = {"0,0": 0, "1,0": 0, "3,3": 1, "4,3": 1}
    st = make(pos, to_move=0, placed=[2, 2])
    ns = g.apply_move(st, "2,0")
    ok(not ns.removing, "drop completing a three does NOT trigger a capture")
    ok(ns.to_move == 1, "after a drop the turn passes to the opponent")
    ok(ns.placed[0] == 3, "drop increments placed count")

    # ---- (2b) forming a FOUR during the drop is ILLEGAL --------------------
    pos = {"0,0": 0, "1,0": 0, "2,0": 0, "5,4": 1}
    st = make(pos, to_move=0, placed=[3, 1])
    ok("3,0" not in g.legal_moves(st),
       "dropping a 4th-in-a-row is not a legal placement")
    ok("0,1" in g.legal_moves(st), "an unrelated drop is still legal")

    # ---- (3) MOVEMENT: exact three removes one enemy piece -----------------
    # All placed. White (0,0),(1,0) and a white at (2,1); slide (2,1)->(2,0)
    # completes the horizontal three (0,0)(1,0)(2,0).
    pos = {"0,0": 0, "1,0": 0, "2,1": 0, "5,4": 1, "5,3": 1, "4,4": 1}
    st = make(pos, to_move=0, placed=[12, 12])
    moves = g.legal_moves(st)
    ok("2,1>2,0" in moves, "the three-forming slide is legal")
    ns = g.apply_move(st, "2,1>2,0")
    ok(ns.removing, "forming an exact three triggers removal")
    ok(ns.to_move == 0, "the same player removes after forming a three")
    # removal targets: enemy pieces; (5,4)(5,3) are a vertical enemy pair (not
    # a three), all three enemy pieces are removable here.
    rem = g.legal_moves(ns)
    ok(set(rem) == {"5,4", "5,3", "4,4"}, "all (non-three) enemy pieces removable")
    ns2 = g.apply_move(ns, "4,4")
    ok("4,4" not in ns2.pos, "the chosen enemy piece is removed")
    ok(ns2.to_move == 1, "after removal the turn passes")

    # ---- (4) NO 4-in-a-row: completing a four neither captures nor is legal -
    # White (0,0),(1,0),(2,0) already a three; a white at (3,1) sliding to (3,0)
    # would make a FOUR -> that slide must be ILLEGAL.
    pos = {"0,0": 0, "1,0": 0, "2,0": 0, "3,1": 0, "5,4": 1, "5,3": 1, "4,4": 1}
    st = make(pos, to_move=0, placed=[12, 12])
    ok("3,1>3,0" not in g.legal_moves(st),
       "a slide creating a 4-in-a-row is illegal")

    # A four standing on the board is not a scoring three: build (0,0..3,0) by
    # confirming _exact_three_lines returns nothing for a run of four.
    pos4 = {"0,0": 0, "1,0": 0, "2,0": 0, "3,0": 0}
    ok(g._exact_three_lines(pos4, "1,0", 0) == [],
       "a run of four is not an exact three")
    pos3 = {"0,0": 0, "1,0": 0, "2,0": 0}
    ok(len(g._exact_three_lines(pos3, "1,0", 0)) == 1,
       "a run of exactly three is detected")

    # ---- (5) ANTI-SHUFFLE --------------------------------------------------
    # White three (0,0)(1,0)(2,0). Slide (2,0)->(2,1) breaks it (no score),
    # then (2,1)->(2,0) would re-form the SAME three: must NOT score, because
    # the moved piece comes from within / re-creates the same line.
    pos = {"0,0": 0, "1,0": 0, "2,1": 0, "5,4": 1, "5,3": 1, "4,4": 1, "3,2": 1}
    st = make(pos, to_move=0, placed=[12, 12])
    # First scoring move forms the three:
    ns = g.apply_move(st, "2,1>2,0")
    ok(ns.removing, "first formation of the three scores")
    ns = g.apply_move(ns, "4,4")          # remove an enemy, turn -> black
    ok(ns.to_move == 1, "turn passes to black after removal")
    # Black makes a neutral move (slide 3,2 somewhere harmless).
    bmoves = g.legal_moves(ns)
    ok(bmoves, "black has moves")
    # pick a black move that doesn't form a black three (any 3,2 neighbor empty)
    bmove = next(m for m in bmoves if m.startswith("3,2>"))
    ns = g.apply_move(ns, bmove)
    ok(ns.to_move == 0, "back to white")
    # White slides (2,0)->(2,1) breaking the three (no capture)...
    ns = g.apply_move(ns, "2,0>2,1")
    ok(not ns.removing, "breaking the three does not score")
    ok(ns.to_move == 1, "turn passes after the breaking move")
    # Black neutral move again
    bmoves = g.legal_moves(ns)
    bmove = next((m for m in bmoves if not g.apply_move(ns, m).removing), bmoves[0])
    ns = g.apply_move(ns, bmove)
    # White slides (2,1)->(2,0) re-forming the identical three -> NO score.
    ok(ns.to_move == 0, "white to move")
    ns_re = g.apply_move(ns, "2,1>2,0")
    ok(not ns_re.removing,
       "re-forming the identical just-broken three does not re-score (anti-shuffle)")

    # direct check: entering a three from OUTSIDE the line forms it (scores).
    posx = {"0,0": 0, "1,0": 0, "3,0": 0}
    stx = make(posx, to_move=0)
    formed = g._formed_threes(stx, "3,0", "2,0", 0)
    ok(len(formed) == 1, "entering a three from outside the line forms it")

    # ---- (6) WIN: reduced below three pieces loses -------------------------
    # Black has exactly 3 pieces, two of them a pair; white forms a three and
    # removes one -> black drops to 2 -> black (to move next) has lost.
    pos = {"0,0": 0, "1,0": 0, "2,1": 0, "0,4": 0,
           "5,4": 1, "5,3": 1, "0,2": 1}
    st = make(pos, to_move=0, placed=[12, 12])
    ns = g.apply_move(st, "2,1>2,0")      # white forms three
    ok(ns.removing, "white forms a three")
    # remove a removable black piece (0,2 is isolated, definitely removable)
    rem = g.legal_moves(ns)
    target = "0,2" if "0,2" in rem else rem[0]
    ns = g.apply_move(ns, target)
    ok(g._on_board(ns, 1) == 2, "black reduced to two pieces")
    ok(g.is_terminal(ns), "position with a 2-piece player is terminal")
    ok(ns.winner == 0, "white wins when black drops below three pieces")
    ok(g.returns(ns) == [1.0, -1.0], "returns reflect white's win")

    # ---- serialize round-trip ---------------------------------------------
    st = g.initial_state()
    st = g.apply_move(st, g.legal_moves(st)[0])
    d = g.serialize(st)
    st2 = g.deserialize(d)
    ok(g.serialize(st2) == d, "serialize round-trips")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
