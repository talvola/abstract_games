"""Camelot correctness anchor — pure stdlib, fast.

No published perft for Camelot, so the anchor is a set of baked rule assertions:
the cross/plus board (160 squares, polygons), the 14-piece (4 Knight + 10 Man)
setup, the three move types (plain / canter / jump), the Knight's Charge, the
compulsory-jump rule, and both win conditions plus the one-piece draw.

Run with:  PYTHONPATH=. python3 games/camelot/selftest.py
Prints "SELFTEST OK" and exits 0 on success; raises / nonzero on failure.
"""

from __future__ import annotations

import json

from games.camelot.game import (
    Camelot, CState, CELLS, CASTLE, TARGET_CASTLE, MAN, KNIGHT,
)


def main() -> None:
    g = Camelot()

    # ---- (1) the cross/plus board: 160 squares, polygons render ----------
    assert len(CELLS) == 160, f"expected 160 squares, got {len(CELLS)}"
    # castle squares present; cut corners absent
    assert (5, 0) in CELLS and (6, 0) in CELLS, "White castle F1/G1 missing"
    assert (5, 15) in CELLS and (6, 15) in CELLS, "Black castle F16/G16 missing"
    assert (0, 0) not in CELLS and (0, 1) not in CELLS, "corner A1/A2 should be cut"
    assert (11, 0) not in CELLS and (11, 1) not in CELLS, "corner L1/L2 should be cut"
    # rank widths of the stepped corner
    assert sum(1 for (c, r) in CELLS if r == 1) == 8, "rank 2 should have 8 squares (C..J)"
    assert sum(1 for (c, r) in CELLS if r == 2) == 10, "rank 3 should have 10 squares (B..K)"
    assert sum(1 for (c, r) in CELLS if r == 7) == 12, "interior rank should be 12 wide"
    rs = g.render(g.initial_state())
    assert rs["board"]["type"] == "polygons", "board must be a polygons board"
    assert len(rs["board"]["cells"]) == 160, "render must emit all 160 cells"

    # ---- (2) 14 pieces/side: 4 Knights + 10 Men ----------------------------
    st = g.initial_state()
    for seat in (0, 1):
        knights = sum(1 for v in st.board.values() if v == (seat, KNIGHT))
        men = sum(1 for v in st.board.values() if v == (seat, MAN))
        assert knights == 4, f"seat {seat} should have 4 knights, got {knights}"
        assert men == 10, f"seat {seat} should have 10 men, got {men}"
    # exact knight placement (WCF setup)
    assert st.board[(2, 5)] == (0, KNIGHT) and st.board[(9, 5)] == (0, KNIGHT)
    assert st.board[(3, 6)] == (0, KNIGHT) and st.board[(8, 6)] == (0, KNIGHT)
    assert st.board[(2, 10)] == (1, KNIGHT) and st.board[(9, 10)] == (1, KNIGHT)

    # ---- (3a) PLAIN move: one step to an adjoining empty square -----------
    st = CState(board={(5, 5): (0, MAN), (0, 3): (1, MAN), (1, 3): (1, MAN)}, to_move=0)
    moves = g.legal_moves(st)
    assert "5,5>5,6" in moves and "5,5>6,6" in moves, "plain orthogonal/diagonal step missing"
    assert "5,5>5,7" not in moves, "plain move is only one step"

    # ---- (3b) CANTER: leap a friendly piece, no capture, chainable --------
    st = CState(board={(5, 5): (0, MAN), (5, 6): (0, MAN),
                       (0, 3): (1, MAN), (1, 3): (1, MAN)}, to_move=0)
    moves = g.legal_moves(st)
    assert "5,5>5,7" in moves, "canter over friendly piece missing"
    ns = g.apply_move(st, "5,5>5,7")
    assert ns.board.get((5, 7)) == (0, MAN), "canter must land beyond the friend"
    assert ns.board.get((5, 6)) == (0, MAN), "canter must NOT remove the cantered-over friend"
    assert (5, 5) not in ns.board, "mover must vacate its origin"
    # chained canter: two friends in a line
    st = CState(board={(5, 5): (0, MAN), (5, 6): (0, MAN), (5, 8): (0, MAN),
                       (0, 3): (1, MAN), (1, 3): (1, MAN)}, to_move=0)
    moves = g.legal_moves(st)
    assert "5,5>5,7>5,9" in moves, "chained canter missing"

    # ---- (3c) JUMP: leap an adjacent enemy to the square beyond, capturing
    st = CState(board={(5, 5): (0, MAN), (5, 6): (1, MAN), (0, 3): (0, MAN)}, to_move=0)
    moves = g.legal_moves(st)
    # compulsory jump: with a jump available, ONLY jump moves are legal
    assert moves == ["5,5>5,7"], f"jump must be compulsory & sole, got {moves}"
    ns = g.apply_move(st, "5,5>5,7")
    assert (5, 6) not in ns.board, "jump must remove the jumped enemy"
    assert ns.board.get((5, 7)) == (0, MAN), "jump must land beyond the enemy"
    # chained jump
    st = CState(board={(4, 4): (0, MAN), (5, 5): (1, MAN), (7, 7): (1, MAN),
                       (3, 3): (0, MAN)}, to_move=0)
    moves = g.legal_moves(st)
    assert "4,4>6,6>8,8" in moves, "chained jump missing"
    ns = g.apply_move(st, "4,4>6,6>8,8")
    assert (5, 5) not in ns.board and (7, 7) not in ns.board, "both enemies must be captured"

    # ---- (3c') JUMP CONTINUATION IS COMPULSORY (no premature stop) --------
    # From (4,4), jumping the enemy at (5,5) lands on (6,6); from (6,6) the piece
    # is adjacent to enemy (7,7) with empty (8,8) beyond, so the jump MUST
    # continue. The premature-stop '4,4>6,6' is ILLEGAL; only the full chain is.
    st = CState(board={(4, 4): (0, MAN), (5, 5): (1, MAN), (7, 7): (1, MAN)}, to_move=0)
    moves = g.legal_moves(st)
    assert "4,4>6,6" not in moves, \
        f"premature-stop jump must be ABSENT (continuation compulsory), got {moves}"
    assert "4,4>6,6>8,8" in moves, \
        f"continuation-maximal jump chain must be PRESENT, got {moves}"
    assert moves == ["4,4>6,6>8,8"], \
        f"only the maximal-by-continuation chain should be legal, got {moves}"

    # ---- (3c'') BRANCHING: two distinct continuations, both full, no early stop
    # From (4,4) jump (5,5) -> land (6,6). From (6,6) two enemies invite further
    # jumps: (7,7)->(8,8) and (7,5)->(8,4). Both full chains are legal; neither
    # stops early at (6,6).
    st = CState(board={(4, 4): (0, MAN), (5, 5): (1, MAN),
                       (7, 7): (1, MAN), (7, 5): (1, MAN)}, to_move=0)
    moves = g.legal_moves(st)
    assert "4,4>6,6" not in moves, f"branch point must not be a legal stop, got {moves}"
    assert "4,4>6,6>8,8" in moves, f"first branch chain missing, got {moves}"
    assert "4,4>6,6>8,4" in moves, f"second branch chain missing, got {moves}"
    assert set(moves) == {"4,4>6,6>8,8", "4,4>6,6>8,4"}, \
        f"exactly the two full branch chains should be legal, got {moves}"

    # ---- (3d) KNIGHT'S CHARGE: canter(s) THEN jump(s), knights only -------
    st = CState(board={(4, 4): (0, KNIGHT), (5, 5): (0, MAN), (7, 7): (1, MAN),
                       (3, 3): (0, MAN)}, to_move=0)
    moves = g.legal_moves(st)
    assert "4,4>6,6>8,8" in moves, "knight's charge (canter then jump) missing"
    ns = g.apply_move(st, "4,4>6,6>8,8")
    assert ns.board.get((5, 5)) == (0, MAN), "charge must NOT remove the cantered friend"
    assert (7, 7) not in ns.board, "charge must capture the jumped enemy"
    assert ns.board.get((8, 8)) == (0, KNIGHT), "knight must finish on the landing square"
    # a MAN may not perform a charge (canter then jump)
    st = CState(board={(4, 4): (0, MAN), (5, 5): (0, MAN), (7, 7): (1, MAN),
                       (3, 3): (0, MAN)}, to_move=0)
    assert "4,4>6,6>8,8" not in g.legal_moves(st), "a Man must not be able to charge"

    # ---- (3e) own-castle restriction: no plain/canter into your own castle
    st = CState(board={(5, 1): (0, MAN), (0, 5): (1, MAN), (1, 5): (1, MAN)}, to_move=0)
    assert "5,1>5,0" not in g.legal_moves(st), "plain move into own castle must be illegal"

    # ---- (4a) WIN by castle invasion: two pieces into enemy castle --------
    st = CState(board={(5, 15): (0, MAN), (6, 14): (0, MAN),
                       (0, 5): (1, MAN), (1, 5): (1, MAN)}, to_move=0)
    ns = g.apply_move(st, "6,14>6,15")
    assert ns.winner == 0, "occupying both enemy-castle squares must win"
    assert g.is_terminal(ns) and g.returns(ns) == [1.0, -1.0]
    # both enemy-castle squares must be the target for White
    assert TARGET_CASTLE[0] == CASTLE[1] and TARGET_CASTLE[1] == CASTLE[0]

    # ---- (4b) WIN by annihilation (keep >=2, capture all enemy) -----------
    st = CState(board={(4, 4): (0, MAN), (0, 3): (0, MAN), (5, 5): (1, MAN)}, to_move=0)
    ns = g.apply_move(st, "4,4>6,6")
    assert ns.winner == 0 and not ns.draw, "capturing all enemy with >=2 survivors must win"
    assert g.returns(ns) == [1.0, -1.0]

    # ---- (4c) DRAW: both reduced to <=1 piece -----------------------------
    st = CState(board={(4, 4): (0, MAN), (5, 5): (1, MAN)}, to_move=0)
    ns = g.apply_move(st, "4,4>6,6")   # White captures Black's last; White left with 1
    assert ns.winner is None and ns.draw, "a lone survivor cannot win -> draw"
    assert g.is_terminal(ns) and g.returns(ns) == [0.0, 0.0]

    # ---- serialize round-trips, JSON-able ---------------------------------
    d = g.serialize(g.initial_state())
    assert g.serialize(g.deserialize(d)) == d
    assert json.loads(json.dumps(d)) == d

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
