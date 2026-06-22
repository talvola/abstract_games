"""Lasca correctness anchor (pure stdlib). Exercises the tower mechanics that make
Lasca distinct: capture tucks the enemy's TOP piece under your column (the rest of
the jumped column stays), control follows the top piece, capturing a top can
LIBERATE a friendly piece beneath, multi-jumps are forced, soldiers promote to
officers on the last rank, and capture is mandatory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.lasca.game import (  # noqa: E402
    Lasca, LState, WHITE, BLACK, _controller, _top, _on,
)

G = Lasca()


def cols(st):
    return {f"{c},{r}": G._col_str(v) for (c, r), v in st.board.items()}


def main():
    # --- initial setup ----------------------------------------------------
    s0 = G.initial_state()
    assert all(_on(c, r) for (c, r) in s0.board), "pieces only on dark squares"
    w = sum(1 for col in s0.board.values() if col == ((WHITE, False),))
    b = sum(1 for col in s0.board.values() if col == ((BLACK, False),))
    assert w == 11 and b == 11, (w, b)
    assert all(r <= 2 for (c, r) in s0.board if _controller(s0.board[(c, r)]) == WHITE)

    # --- a capture tucks the enemy top under (control by top) -------------
    st = LState(board={(2, 2): ((WHITE, False),), (3, 3): ((BLACK, False),)}, to_move=WHITE)
    assert G.legal_moves(st) == ["2,2>4,4"]
    st2 = G.apply_move(st, "2,2>4,4")
    assert cols(st2) == {"4,4": "bw"}, cols(st2)           # black prisoner, white on top
    assert _controller(st2.board[(4, 4)]) == WHITE

    # --- mandatory capture: a simple move is illegal when a jump exists ----
    st = LState(board={(2, 2): ((WHITE, False),), (3, 3): ((BLACK, False),),
                       (0, 0): ((WHITE, False),)}, to_move=WHITE)
    assert all("4,4" in m for m in G.legal_moves(st)), G.legal_moves(st)

    # --- forced multi-jump + promotion at the end -------------------------
    st = LState(board={(2, 2): ((WHITE, False),), (3, 3): ((BLACK, False),),
                       (5, 5): ((BLACK, False),)}, to_move=WHITE)
    assert G.legal_moves(st) == ["2,2>4,4>6,6"], "multi-jump must run to the end"
    st2 = G.apply_move(st, "2,2>4,4>6,6")
    assert cols(st2) == {"6,6": "bbW"}, cols(st2)          # two prisoners, promoted top
    assert _top(st2.board[(6, 6)]) == (WHITE, True), "soldier promoted on last rank"

    # --- liberation: taking a white top frees the black piece beneath ------
    st = LState(board={(4, 4): ((BLACK, False), (WHITE, False)),  # 'bw', white-controlled
                       (5, 5): ((BLACK, False),)}, to_move=BLACK)
    assert G.legal_moves(st) == ["5,5>3,3"]
    st2 = G.apply_move(st, "5,5>3,3")
    assert st2.board[(3, 3)] == ((WHITE, False), (BLACK, False)), cols(st2)   # 'wb'
    assert st2.board.get((4, 4)) == ((BLACK, False),), "freed black piece remains"

    # --- officer captures backward ----------------------------------------
    st = LState(board={(4, 4): ((WHITE, True),), (3, 3): ((BLACK, False),)}, to_move=WHITE)
    assert "4,4>2,2" in G.legal_moves(st), "officer should capture backward"

    # --- win by leaving the opponent with no move -------------------------
    #  White officer (2,2) jumps the lone black at (3,3); black then has nothing.
    st = LState(board={(2, 2): ((WHITE, True),), (3, 3): ((BLACK, False),)}, to_move=WHITE)
    st2 = G.apply_move(st, "2,2>4,4")
    assert st2.winner == WHITE and G.returns(st2) == [1.0, -1.0]

    # --- serialize round-trips (mixed-owner towers) -----------------------
    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)

    print("lasca selftest OK")


if __name__ == "__main__":
    main()
