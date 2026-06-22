"""Focus correctness anchor (pure stdlib). No published perft exists, so the
anchor is a set of baked rule assertions exercising every distinctive mechanic:

 (1) a stack moves up to (its height) cells orthogonally, distance == pieces
     lifted, and the lifted sub-stack lands ON TOP of any stack at the destination;
 (2) over-5: a stack taller than 5 sheds from the BOTTOM until 5 remain -- the
     mover's own shed pieces go to his reserve, enemy shed pieces are captured out;
 (3) a reserve piece may be dropped (as a full turn) onto any cell, on top;
 (4) you control a stack iff your piece is on TOP;
 (5) the elimination win reached via apply_move (a player with no legal move loses);
plus the standard opening (18/18, central 6x6, empty arms) and serialise round-trip.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.focus.game import (  # noqa: E402
    Focus, FState, RED, GREEN, CELLS, REMOVED, _controller, _on,
)

G = Focus()


def cols(st):
    return {f"{c},{r}": G._col_str(v) for (c, r), v in st.board.items()}


def main():
    # --- board geometry: 52-cell octagon -----------------------------------
    assert len(CELLS) == 52, len(CELLS)
    assert len(REMOVED) == 12
    assert all(not _on(c, r) for (c, r) in REMOVED)

    # --- standard opening: 18 each, central 6x6 filled, arms empty ---------
    s0 = G.initial_state()
    red = sum(1 for col in s0.board.values() if col == (RED,))
    green = sum(1 for col in s0.board.values() if col == (GREEN,))
    assert red == 18 and green == 18, (red, green)
    assert all(1 <= c <= 6 and 1 <= r <= 6 for (c, r) in s0.board), "core only"
    assert len(s0.board) == 36
    assert s0.reserve == {RED: 0, GREEN: 0}
    # the striped pattern: row 1 starts R R G G R R, row 2 starts G G R R G G
    assert s0.board[(1, 1)] == (RED,) and s0.board[(3, 1)] == (GREEN,)
    assert s0.board[(1, 2)] == (GREEN,) and s0.board[(3, 2)] == (RED,)

    # --- (4) control follows the TOP piece ---------------------------------
    st = FState(board={(3, 3): (GREEN, RED)}, reserve={RED: 0, GREEN: 0},
                captured={RED: 0, GREEN: 0}, to_move=RED)
    assert _controller(st.board[(3, 3)]) == RED, "top piece controls"
    assert any(m.startswith("3,3>") for m in G.legal_moves(st)), "RED may move it"
    st_g = FState(board={(3, 3): (GREEN, RED)}, reserve={RED: 0, GREEN: 0},
                  captured={RED: 0, GREEN: 0}, to_move=GREEN)
    assert not any(m.startswith("3,3>") for m in G.legal_moves(st_g)), \
        "GREEN cannot move a RED-topped stack"

    # --- (1) move up to height; distance == pieces lifted; lands ON TOP ----
    # A height-3 RED stack on (3,3); a lone GREEN on (3,5). Move all 3 -> 3 cells.
    st = FState(board={(3, 3): (RED, RED, RED), (3, 5): (GREEN,)},
                reserve={RED: 0, GREEN: 0}, captured={RED: 0, GREEN: 0}, to_move=RED)
    legal = G.legal_moves(st)
    # height 3 => k in 1,2,3 in each of 4 directions, only on-board landings
    assert "3,3>3,4=1" in legal and "3,3>3,5=2" in legal and "3,3>3,6=3" in legal
    assert "3,3>3,5=3" not in legal, "k must equal the travelled distance"
    st2 = G.apply_move(st, "3,3>3,6=3")          # whole stack travels 3 cells
    # passing over (3,5) does not disturb it; only the landing cell merges
    assert cols(st2)["3,6"] == "RRR" and cols(st2)["3,5"] == "G", cols(st2)
    assert (3, 3) not in st2.board, "source emptied"
    # partial lift: move only the top 2 of a height-3 stack two cells onto GREEN
    st = FState(board={(3, 3): (RED, RED, RED), (3, 5): (GREEN,)},
                reserve={RED: 0, GREEN: 0}, captured={RED: 0, GREEN: 0}, to_move=RED)
    st2 = G.apply_move(st, "3,3>3,5=2")
    assert cols(st2)["3,3"] == "R", "one RED left behind"
    assert cols(st2)["3,5"] == "GRR", "lifted pair landed ON TOP of the GREEN"
    assert _controller(st2.board[(3, 5)]) == RED

    # --- (2) over-5: bottom-removal split (hand-built) ---------------------
    # RED lifts its top 2 onto a 5-high stack -> height 7 -> shed bottom 2.
    # Build destination bottom->top = [G, R, G, R, G]; mover RED brings (R,R).
    # Result column before settle: G R G R G R R  (height 7); shed bottom 2 = G,R.
    #   G (enemy) -> captured by RED;  R (RED's own) -> RED reserve.
    st = FState(board={(2, 2): (RED, RED, RED),                  # source, height 3
                       (2, 4): (GREEN, RED, GREEN, RED, GREEN)},  # dest, height 5
                reserve={RED: 0, GREEN: 0}, captured={RED: 0, GREEN: 0}, to_move=RED)
    st2 = G.apply_move(st, "2,2>2,4=2")          # lift top 2 RED, travel 2 cells
    assert len(st2.board[(2, 4)]) == 5, "capped to 5"
    assert cols(st2)["2,4"] == "GRGRR", cols(st2)["2,4"]   # top 5 kept, in order
    assert st2.reserve[RED] == 1, ("own shed -> reserve", st2.reserve)
    assert st2.captured[RED] == 1, ("enemy shed -> captured", st2.captured)
    assert st2.captured[GREEN] == 0
    # the leftover at source (one RED) still there
    assert cols(st2)["2,2"] == "R"

    # --- (3) reserve drop is a full turn, lands on top; cannot drop w/o reserve
    st = FState(board={(4, 4): (GREEN,)}, reserve={RED: 1, GREEN: 0},
                captured={RED: 0, GREEN: 0}, to_move=RED)
    assert "P@4,4" in G.legal_moves(st), "RED may drop onto an enemy cell"
    assert "P@2,2" in G.legal_moves(st), "...or onto an empty cell"
    st2 = G.apply_move(st, "P@4,4")
    assert cols(st2)["4,4"] == "GR", "dropped RED on TOP of the GREEN"
    assert st2.reserve[RED] == 0, "reserve decremented"
    assert _controller(st2.board[(4, 4)]) == RED
    st_no = FState(board={(4, 4): (GREEN,)}, reserve={RED: 0, GREEN: 0},
                   captured={RED: 0, GREEN: 0}, to_move=RED)
    assert not any("@" in m for m in G.legal_moves(st_no)), "no reserve -> no drop"

    # --- a drop that overflows 5 also splits correctly ---------------------
    st = FState(board={(4, 4): (RED, GREEN, RED, GREEN, RED)},  # height 5
                reserve={GREEN: 1, RED: 0}, captured={RED: 0, GREEN: 0}, to_move=GREEN)
    st2 = G.apply_move(st, "P@4,4")              # GREEN drops -> height 6 -> shed bottom 1 (RED)
    assert len(st2.board[(4, 4)]) == 5
    assert st2.captured[GREEN] == 1, "the shed bottom RED is captured by GREEN"
    assert st2.reserve[GREEN] == 0

    # --- (5) elimination win via apply_move --------------------------------
    # RED single on (3,3); GREEN single on (3,4). RED moves onto GREEN, covering
    # the only GREEN-controlled stack. GREEN then has no stack to move and no
    # reserve -> GREEN has no legal move -> RED wins.
    st = FState(board={(3, 3): (RED,), (3, 4): (GREEN,)},
                reserve={RED: 0, GREEN: 0}, captured={RED: 0, GREEN: 0}, to_move=RED)
    st2 = G.apply_move(st, "3,3>3,4=1")
    assert cols(st2) == {"3,4": "GR"}, cols(st2)
    assert G.legal_moves(st2) == [], "GREEN is immobilised"
    assert st2.winner == RED and G.returns(st2) == [1.0, -1.0]
    assert G.is_terminal(st2)

    # --- serialise round-trips (mixed stacks + reserve + captured) ---------
    st = FState(board={(2, 4): (GREEN, RED, GREEN, RED, RED), (3, 3): (RED,)},
                reserve={RED: 2, GREEN: 1}, captured={RED: 3, GREEN: 0},
                to_move=GREEN, ply=7)
    assert G.serialize(G.deserialize(G.serialize(st))) == G.serialize(st)

    # --- sanity: a full opening turn has many legal moves, all parseable ----
    om = G.legal_moves(s0)
    assert len(om) > 0
    for m in om:
        assert ("=" in m) or ("@" in m)
    # apply each opening move once -> never raises, pieces conserved-ish
    for m in om[:30]:
        G.apply_move(s0, m)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
