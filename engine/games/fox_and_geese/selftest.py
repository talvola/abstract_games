"""Fox and Geese correctness anchor (pure stdlib). Checks the 33-point cross
topology + alquerque diagonals, the opening geese move count, the no-backward
geese restriction, a fox single jump (goose removed, count decremented), a fox
chained multi-jump, the geese-win (fox trapped) and fox-win (geese reduced to 2)
conditions, and serialize round-trip. Terminals are reached via apply_move."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.fox_and_geese.game import (  # noqa: E402
    FoxAndGeese, FGState, ADJ, POINTS, GEESE, FOX, GEESE_TOTAL, GEESE_LOSE,
)

G = FoxAndGeese()


def main():
    # --- topology: 33 points, alquerque diagonals -------------------------
    assert len(POINTS) == 33, f"expected 33 points, got {len(POINTS)}"
    # centre 3,3 is a strong point -> degree 8 (full 8 neighbours)
    assert ADJ[(3, 3)] == frozenset({
        (2, 2), (2, 3), (2, 4), (3, 2), (3, 4), (4, 2), (4, 3), (4, 4)
    }), "centre should have all 8 neighbours"
    # 3,0 is a weak top point (3+0 odd): orthogonal-only, degree 3
    assert ADJ[(3, 0)] == frozenset({(2, 0), (4, 0), (3, 1)}), "weak point ortho-only"
    # 2,2 is strong -> has its diagonal to 3,3 ; 3,2 is weak -> no diagonals
    assert (3, 3) in ADJ[(2, 2)], "strong point missing diagonal"
    assert (2, 3) not in ADJ[(3, 2)] and (4, 3) not in ADJ[(3, 2)], "weak point has diagonal"
    for p in ADJ:                                  # adjacency symmetric
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"

    # --- initial position --------------------------------------------------
    s = G.initial_state()
    assert s.to_move == GEESE and s.geese_left == GEESE_TOTAL == 15
    assert s.board[(3, 3)] == FOX
    assert sum(1 for v in s.board.values() if v == GEESE) == 15
    # opening geese move count (hand-derived): 12
    assert len(G.legal_moves(s)) == 12, f"opening geese moves != 12 ({len(G.legal_moves(s))})"

    # --- geese cannot move backward ---------------------------------------
    # a lone goose at 3,5 (strong) with empty neighbours: forward/side allowed,
    # backward (row 6) forbidden.
    st = FGState(board={(3, 5): GEESE, (0, 3): FOX}, to_move=GEESE, geese_left=1)
    tos = {m.split(">")[1] for m in G.legal_moves(st)}
    assert "3,4" in tos and "2,4" in tos and "4,4" in tos, "forward/diag-forward missing"
    assert "2,5" in tos and "4,5" in tos, "sideways missing"
    assert "3,6" not in tos and "2,6" not in tos and "4,6" not in tos, "backward allowed!"

    # --- fox single jump removes a goose ----------------------------------
    st = FGState(board={(3, 3): FOX, (3, 4): GEESE}, to_move=FOX, geese_left=1 + GEESE_LOSE)
    assert "3,3>3,5" in G.legal_moves(st), "straight orthogonal jump missing"
    st2 = G.apply_move(st, "3,3>3,5")
    assert (3, 4) not in st2.board, "jumped goose not removed"
    assert st2.board[(3, 5)] == FOX and st2.geese_left == GEESE_LOSE + 0  # one captured

    # --- fox chained multi-jump -------------------------------------------
    # fox at 3,2 ; geese at 3,3 (land 3,4) then at 4,4 wait -> use a clean L:
    # fox 2,2 jumps goose 3,3 -> land 4,4, then jumps goose 4,3? set up a chain:
    # fox 2,4 jump goose 3,4 -> 4,4 ; then jump goose 4,3? Use orth chain along a row.
    # Simpler vertical+vertical chain: fox 3,1 over 3,2 ->? 3,2 weak; use 2,2 strong line.
    # Chain along column c=3: fox 3,0? 3,0 exists. geese at 3,1 and 3,3, lands 3,2 then 3,4.
    board = {(3, 0): FOX, (3, 1): GEESE, (3, 3): GEESE}
    st = FGState(board=board, to_move=FOX, geese_left=5)
    moves = G.legal_moves(st)
    assert "3,0>3,2>3,4" in moves, f"expected chained jump in {moves}"
    st2 = G.apply_move(st, "3,0>3,2>3,4")
    assert st2.board[(3, 4)] == FOX
    assert (3, 1) not in st2.board and (3, 3) not in st2.board, "both jumped geese removed"
    assert st2.geese_left == 3, "two captures should drop geese to 3"

    # --- geese win: fox fully trapped -------------------------------------
    # fox at corner-ish 3,0 (neighbours 2,0 / 4,0 / 3,1). Block all three with
    # geese AND the squares beyond (1,0 / 5,0 / 3,2) so no jump escapes.
    board = {(3, 0): FOX,
             (2, 0): GEESE, (4, 0): GEESE, (3, 1): GEESE,
             (1, 0): GEESE, (5, 0): GEESE, (3, 2): GEESE}
    st = FGState(board=board, to_move=FOX, geese_left=6)
    assert G.legal_moves(st) == [], "fox should be fully trapped (steps + jumps blocked)"
    G._settle(st)
    assert st.winner == GEESE, "trapped fox -> geese win"

    # reach the geese win via apply_move (a goose closes the trap)
    board = {(3, 0): FOX,
             (2, 0): GEESE, (4, 0): GEESE,
             (1, 0): GEESE, (5, 0): GEESE, (3, 2): GEESE,
             (4, 2): GEESE}                          # this goose steps to 3,1
    st = FGState(board=board, to_move=GEESE, geese_left=7)
    st2 = G.apply_move(st, "4,2>3,1")               # 4,2 strong -> diagonal forward
    assert st2.winner == GEESE and G.returns(st2) == [1.0, -1.0]

    # --- fox win: reduce geese to GEESE_LOSE ------------------------------
    st = FGState(board={(3, 3): FOX, (3, 4): GEESE}, to_move=FOX, geese_left=GEESE_LOSE + 1)
    st2 = G.apply_move(st, "3,3>3,5")               # capture -> geese_left == GEESE_LOSE
    assert st2.geese_left == GEESE_LOSE and st2.winner == FOX
    assert G.returns(st2) == [-1.0, 1.0]

    # --- serialize round-trips --------------------------------------------
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)
    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)

    print("fox_and_geese selftest OK")


if __name__ == "__main__":
    main()
