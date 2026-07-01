"""Standalone correctness anchor for King's Valley (pure stdlib + agp + this game).

Run: PYTHONPATH=. python3 games/kings_valley/selftest.py   -> prints SELFTEST OK, exit 0.

Anchors: setup, the maximal-slide rule (no stopping short), slide-through-centre,
the centre-access rule (Soldier can't stop on centre, King can and wins), the
opening-Soldier restriction, the trapped-King loss, the draw cap, and serialize
round-trip.
"""

from __future__ import annotations

import sys

from games.kings_valley.game import KingsValley, KVState, CENTER, PLY_CAP


def check(cond, msg):
    if not cond:
        print(f"SELFTEST FAIL: {msg}")
        sys.exit(1)


def main():
    g = KingsValley()

    # ---- setup --------------------------------------------------------------
    s0 = g.initial_state()
    check(g.uid == "kings_valley", "uid from class")
    check(g.num_players == 2, "two players")
    check(len(s0.board) == 10, "10 pieces on the board")
    # White King centred on row 0, Black King centred on row 4; 4 soldiers each.
    check(s0.board[(2, 0)] == (0, True), "White King on (2,0)")
    check(s0.board[(2, 4)] == (1, True), "Black King on (2,4)")
    white_kings = [c for c, (o, k) in s0.board.items() if o == 0 and k]
    white_soldiers = [c for c, (o, k) in s0.board.items() if o == 0 and not k]
    black_kings = [c for c, (o, k) in s0.board.items() if o == 1 and k]
    black_soldiers = [c for c, (o, k) in s0.board.items() if o == 1 and not k]
    check(len(white_kings) == 1 and len(black_kings) == 1, "one King each")
    check(len(white_soldiers) == 4 and len(black_soldiers) == 4, "four Soldiers each")
    check(g.current_player(s0) == 0, "White moves first")
    check(not g.is_terminal(s0), "opening not terminal")

    lm0 = g.legal_moves(s0)
    check(len(lm0) > 0, "opening has legal moves")

    # ---- maximal slide: must go as far as possible, no stopping short --------
    # White Soldier (0,0) sliding North is blocked by Black Soldier at (0,4):
    # last empty square is (0,3). Intermediate stops (0,1)/(0,2) are ILLEGAL.
    check("0,0>0,3" in lm0, "Soldier slides to the far square (0,3)")
    check("0,0>0,1" not in lm0, "no mid-slide stop at (0,1)")
    check("0,0>0,2" not in lm0, "no mid-slide stop at (0,2)")
    # Its NE diagonal slides THROUGH the centre to (3,3) (blocked by Black (4,4)).
    check("0,0>3,3" in lm0, "Soldier slides through the centre diagonally to (3,3)")
    check("0,0>2,2" not in lm0, "opening Soldier NE does not stop on the centre")

    # ---- opening: first move must be a Soldier (King can't move on ply 0) ----
    check(not any(m.startswith("2,0>") for m in lm0), "White King can't move on ply 0")
    # On a later ply the King may move: same board, ply=1, White to move.
    s_later = KVState(board=dict(s0.board), to_move=0, ply=1, winner=-1)
    lm_later = g.legal_moves(s_later)
    check("2,0>2,3" in lm_later, "King may move (to (2,3)) once past the opening")

    # ---- Soldier may not STOP on the centre; may slide THROUGH it -----------
    # Config A: a Soldier whose maximal slide would END on the centre -> no move.
    board_a = {
        (0, 2): (0, False),   # White Soldier under test
        (2, 0): (0, True),    # White King (mobile, so state isn't terminal)
        (3, 2): (1, False),   # Black blocker just past the centre
        (4, 4): (1, True),    # Black King
    }
    sa = KVState(board=board_a, to_move=0, ply=5, winner=-1)
    lma = g.legal_moves(sa)
    check("0,2>2,2" not in lma, "Soldier may not stop on the centre")
    check("0,2>1,2" not in lma, "Soldier may not stop short of the centre either")

    # Config B: with the path past the centre open, the Soldier slides THROUGH.
    board_b = {
        (0, 2): (0, False),
        (2, 0): (0, True),
        (4, 4): (1, True),
    }
    sb = KVState(board=board_b, to_move=0, ply=5, winner=-1)
    lmb = g.legal_moves(sb)
    check("0,2>4,2" in lmb, "Soldier slides through the empty centre to (4,2)")
    check("0,2>2,2" not in lmb, "Soldier still can't stop on the centre")

    # ---- King MAY stop on the centre, and doing so WINS ---------------------
    board_c = {
        (0, 2): (0, True),    # White King, will slide East onto the centre
        (2, 0): (0, False),   # White Soldier
        (3, 2): (1, False),   # Black blocker just past the centre
        (4, 4): (1, True),    # Black King
    }
    sc = KVState(board=board_c, to_move=0, ply=5, winner=-1)
    lmc = g.legal_moves(sc)
    check("0,2>2,2" in lmc, "King's maximal slide may end on the centre")
    before = dict(sc.board)
    sc2 = g.apply_move(sc, "0,2>2,2")
    check(sc.board == before, "apply_move did not mutate input state")
    check(sc2.winner == 0, "White wins by reaching the King's Valley")
    check(sc2.board[CENTER] == (0, True), "White King now sits on the centre")
    check(g.is_terminal(sc2), "win is terminal")
    check(g.returns(sc2) == [1.0, -1.0], "returns reflect White's win")
    check(g.legal_moves(sc2) == [], "no moves after a win")

    # ---- trapped King = loss (even with Soldiers able to move) --------------
    board_t = {
        (0, 0): (0, True),    # White King cornered...
        (1, 0): (1, False),   # ...blocked East
        (0, 1): (1, False),   # ...blocked North
        (1, 1): (1, False),   # ...blocked NE
        (4, 4): (1, True),    # Black King
        (3, 3): (0, False),   # a White Soldier that CAN still move
    }
    st = KVState(board=board_t, to_move=0, ply=8, winner=-1)
    check(not g._king_can_move(st, 0), "White King is fully trapped")
    check(g.is_terminal(st), "trapped King is terminal")
    check(g.returns(st) == [-1.0, 1.0], "trapped King loses")

    # ---- draw cap guarantees termination ------------------------------------
    s_cap = KVState(board=dict(s0.board), to_move=0, ply=PLY_CAP, winner=-1)
    check(g.is_terminal(s_cap), "ply cap terminates the game")
    check(g.returns(s_cap) == [0.0, 0.0], "ply cap scores a draw")

    # ---- serialize round-trips ---------------------------------------------
    for st_rt in (s0, sa, sc2, st):
        d = g.serialize(st_rt)
        import json
        json.dumps(d)  # must be JSON-able
        back = g.deserialize(d)
        check(g.serialize(back) == d, "serialize round-trips")

    # ---- render shape (smoke) ----------------------------------------------
    spec = g.render(s0)
    check(spec["board"]["type"] == "square", "render board type")
    check(spec["board"]["width"] == 5 and spec["board"]["height"] == 5, "render 5x5")
    check(len(spec["pieces"]) == 10, "render draws 10 pieces")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
