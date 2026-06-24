"""Pure-stdlib selftest for Ultima (Baroque Chess).

Anchors:
  * exact opening legal-move count (32, all pincer pawns).
  * one constructed position per capture method, reached via apply_move:
    Withdrawer, Coordinator, Long Leaper (single + multi), Pincer Pawn,
    Immobilizer freeze, Chameleon-as-leaper, King capture / win-by-king-capture.
  * serialize round-trip.

Run: PYTHONPATH=. python3 games/ultima/selftest.py
"""

from __future__ import annotations

from games.ultima.game import Ultima, UState, WHITE, BLACK


def _pos(pairs, to_move=WHITE):
    """Build a UState from {(c,r): (owner, letter)}."""
    return UState(board=dict(pairs), to_move=to_move)


def _apply(g, s, move):
    assert move in g.legal_moves(s), f"{move!r} not legal in {sorted(g.legal_moves(s))}"
    return g.apply_move(s, move)


def main():
    g = Ultima()

    # --- opening move count ------------------------------------------------
    s0 = g.initial_state()
    moves = g.legal_moves(s0)
    assert len(moves) == 32, f"opening moves {len(moves)} != 32"
    assert all(m.split('>')[0] in {f"{c},1" for c in range(8)} for m in moves), \
        "opening: non-pawn move generated"

    # --- Withdrawer: capture by fleeing -----------------------------------
    # White Withdrawer at 3,3 with a Black piece adjacent at 2,3 (to its west);
    # moving east (away) captures it.  Need kings on the board so coordinator/
    # king logic is consistent; place them out of the way.
    s = _pos({
        (3, 3): (WHITE, "W"),
        (2, 3): (BLACK, "P"),
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    s2 = _apply(g, s, "3,3>5,3")  # move east, away from the enemy at 2,3
    assert (2, 3) not in s2.board, "withdrawer did not capture the adjacent enemy"
    assert s2.board[(5, 3)] == (WHITE, "W")
    # withdrawing the WRONG way (toward / not directly away) captures nothing
    s = _pos({
        (3, 3): (WHITE, "W"),
        (2, 3): (BLACK, "P"),
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    s2 = _apply(g, s, "3,3>3,6")  # move north -> enemy is to the west, not behind
    assert (2, 3) in s2.board, "withdrawer wrongly captured (not moving away)"

    # --- Coordinator: rook-cross with own King ----------------------------
    # White King at 0,0, White Coordinator at 5,5; after moving the coordinator
    # the two cross-intersections are (col of coord, row of king) and (col of
    # king, row of coord).  Put a Black piece on one intersection.
    s = _pos({
        (0, 0): (WHITE, "K"),
        (3, 7): (WHITE, "C"),
        (3, 0): (BLACK, "P"),    # will sit on (coord_col=3, king_row=0)
        (7, 6): (BLACK, "K"),
    })
    s2 = _apply(g, s, "3,7>3,5")  # coord stays col 3 ; intersections: (3,0) & (0,5)
    assert (3, 0) not in s2.board, "coordinator did not capture the cross enemy"

    # --- Long Leaper: single leap -----------------------------------------
    s = _pos({
        (0, 4): (WHITE, "L"),
        (2, 4): (BLACK, "P"),    # enemy to leap
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    s2 = _apply(g, s, "0,4>3,4")  # leap over (2,4), land on (3,4)
    assert (2, 4) not in s2.board, "long leaper single leap failed to capture"
    assert s2.board[(3, 4)] == (WHITE, "L")

    # --- Long Leaper: multi leap ------------------------------------------
    s = _pos({
        (0, 4): (WHITE, "L"),
        (2, 4): (BLACK, "P"),
        (4, 4): (BLACK, "P"),
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    s2 = _apply(g, s, "0,4>5,4")  # leap (2,4) then (4,4), land on (5,4)
    assert (2, 4) not in s2.board and (4, 4) not in s2.board, "multi-leap failed"
    assert s2.board[(5, 4)] == (WHITE, "L")
    # two enemies back-to-back cannot be leaped (no gap) -> that landing illegal
    s = _pos({
        (0, 4): (WHITE, "L"),
        (2, 4): (BLACK, "P"),
        (3, 4): (BLACK, "P"),   # adjacent to the first -> blocks the leap path
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    assert "0,4>4,4" not in g.legal_moves(s), "leaper jumped two adjacent enemies"

    # --- Pincer Pawn: custodial capture -----------------------------------
    # White pawn moves to 3,3 flanking a Black piece at 4,3 against a White piece
    # at 5,3.
    s = _pos({
        (0, 3): (WHITE, "P"),
        (4, 3): (BLACK, "P"),
        (5, 3): (WHITE, "I"),    # friendly anchor
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    s2 = _apply(g, s, "0,3>3,3")  # now 3,3(W) 4,3(B) 5,3(W) -> 4,3 captured
    assert (4, 3) not in s2.board, "pincer pawn custodial capture failed"
    # a piece moving INTO a pincer of its own accord is NOT captured: move the
    # Black pawn between two White pieces and confirm it survives (no auto-capture
    # on the opponent's move).
    s = _pos({
        (3, 3): (WHITE, "P"),
        (5, 3): (WHITE, "P"),
        (4, 6): (BLACK, "P"),
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    }, to_move=BLACK)
    s2 = _apply(g, s, "4,6>4,3")  # Black slides between the two White pawns
    assert (4, 3) in s2.board, "piece self-flanking was wrongly captured"

    # --- Immobilizer: freezes adjacent enemy ------------------------------
    # White Immobilizer adjacent to a lone Black pawn -> that pawn has no moves.
    s = _pos({
        (3, 3): (WHITE, "I"),
        (3, 4): (BLACK, "P"),    # adjacent (north) to the immobilizer
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    }, to_move=BLACK)
    bm = g.legal_moves(s)
    assert all(m == "pass" or not m.startswith("3,4>") for m in bm), \
        "immobilized pawn still has a move"
    # the Black King (far away) is NOT frozen -> Black has real moves, no pass
    assert any(m.startswith("7,7>") for m in bm), "free king has no moves"

    # Immobilizer-vs-Chameleon mutual freeze: an enemy Chameleon adjacent to the
    # immobilizer freezes the immobilizer; the chameleon itself is also frozen.
    s = _pos({
        (3, 3): (WHITE, "I"),
        (3, 4): (BLACK, "M"),
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    }, to_move=WHITE)
    wm = g.legal_moves(s)
    assert all(not m.startswith("3,3>") for m in wm), \
        "immobilizer not frozen by adjacent enemy chameleon"
    s_b = UState(board=dict(s.board), to_move=BLACK)
    bm = g.legal_moves(s_b)
    assert all(not m.startswith("3,4>") for m in bm), \
        "chameleon not frozen by adjacent enemy immobilizer"

    # --- Chameleon captures a Long Leaper by leaping ----------------------
    s = _pos({
        (0, 4): (WHITE, "M"),
        (2, 4): (BLACK, "L"),    # the leaper it will leap
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    s2 = _apply(g, s, "0,4>3,4")  # chameleon leaps the enemy long leaper
    assert (2, 4) not in s2.board, "chameleon-as-leaper failed to capture leaper"
    # a chameleon may NOT leap over a NON-leaper (it lacks leaping power vs a
    # pawn) -> the landing square beyond a pawn is not a legal destination.
    s = _pos({
        (0, 4): (WHITE, "M"),
        (2, 4): (BLACK, "P"),    # a pawn, not a leaper
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    assert "0,4>3,4" not in g.legal_moves(s), \
        "chameleon wrongly leaped over a non-leaper"

    # Chameleon captures an enemy Withdrawer by withdrawing from it, but does
    # NOT capture a non-withdrawer it withdraws from.
    s = _pos({
        (3, 3): (WHITE, "M"),
        (2, 3): (BLACK, "W"),    # enemy withdrawer to the west
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    s2 = _apply(g, s, "3,3>5,3")  # withdraw east, away from (2,3)
    assert (2, 3) not in s2.board, "chameleon-as-withdrawer failed vs enemy withdrawer"
    s = _pos({
        (3, 3): (WHITE, "M"),
        (2, 3): (BLACK, "P"),    # a pawn, not a withdrawer
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    s2 = _apply(g, s, "3,3>5,3")
    assert (2, 3) in s2.board, "chameleon wrongly withdrew-captured a non-withdrawer"

    # Chameleon captures an enemy Pincer Pawn by pincering it (custodial).
    s = _pos({
        (0, 3): (WHITE, "M"),
        (4, 3): (BLACK, "P"),    # enemy pawn
        (5, 3): (WHITE, "P"),    # friendly anchor
        (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K"),
    })
    s2 = _apply(g, s, "0,3>3,3")  # 3,3(M) 4,3(B pawn) 5,3(W) -> pawn captured
    assert (4, 3) not in s2.board, "chameleon-as-pincer failed vs enemy pawn"

    # --- King capture = win -----------------------------------------------
    s = _pos({
        (3, 3): (WHITE, "K"),
        (3, 4): (BLACK, "K"),    # adjacent (illegal in chess, fine for the test)
        (0, 0): (WHITE, "P"),
    })
    s2 = _apply(g, s, "3,3>3,4")  # king captures king by displacement
    assert s2.winner == WHITE, "king capture did not set winner"
    assert g.is_terminal(s2) and g.returns(s2) == [1.0, -1.0]

    # Chameleon captures enemy King by stepping onto it (king's own method).
    s = _pos({
        (3, 3): (WHITE, "M"),
        (3, 4): (BLACK, "K"),
        (0, 0): (WHITE, "K"),
    })
    s2 = _apply(g, s, "3,3>3,4")
    assert s2.winner == WHITE, "chameleon did not capture the king"

    # --- serialize round-trip ---------------------------------------------
    s = g.initial_state()
    s = _apply(g, s, g.legal_moves(s)[0])
    d = g.serialize(s)
    s_rt = g.deserialize(d)
    assert g.serialize(s_rt) == d, "serialize round-trip mismatch"
    import json
    json.dumps(d)  # must be JSON-able

    print("ultima selftest: all tests passed")


if __name__ == "__main__":
    main()
