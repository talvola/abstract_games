"""Bashni correctness anchor (pure stdlib). No published perft exists, so the
anchor is a set of baked rule assertions exercising the mechanics that make
Bashni distinct from plain draughts and from Lasca:

  (1) a man captures by jumping an adjacent enemy-TOPPED column diagonally to the
      empty square beyond, and the jumped column's TOP piece is placed at the
      BOTTOM of the moving column -- the moving column grows by exactly 1, and the
      rest of the jumped column stays (he loses only its top);
  (2) control follows the TOP piece (capturing a top can liberate a buried friend);
  (3) multi-jump chains continue as ONE move and captures are mandatory;
  (4) a man captures FORWARD or BACKWARD (Russian rule);
  (5) a man reaching the far rank becomes a flying KING (slides/captures any
      distance, Russian rules), incl. in-chain promotion;
  (6) win = the opponent controls no column / has no legal move.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.bashni.game import (  # noqa: E402
    Bashni, BState, WHITE, BLACK, _controller, _top, _on, SIZE,
)

G = Bashni()


def cols(st):
    return {f"{c},{r}": G._col_str(v) for (c, r), v in st.board.items()}


def main():
    # --- initial setup: 32 dark squares, 12 men a side, 3 rows ------------
    s0 = G.initial_state()
    assert all(_on(c, r) for (c, r) in s0.board), "pieces only on dark squares"
    assert SIZE == 8
    w = sum(1 for col in s0.board.values() if col == ((WHITE, False),))
    b = sum(1 for col in s0.board.values() if col == ((BLACK, False),))
    assert w == 12 and b == 12, (w, b)
    assert all(r <= 2 for (c, r) in s0.board if _controller(s0.board[(c, r)]) == WHITE)
    assert all(r >= 5 for (c, r) in s0.board if _controller(s0.board[(c, r)]) == BLACK)
    # opening: only simple steps, no captures
    assert all(">" in m and "x" not in G.describe_move(s0, m) for m in G.legal_moves(s0))

    # --- (1) the top-to-bottom prisoner rule ------------------------------
    st = BState(board={(2, 2): ((WHITE, False),), (3, 3): ((BLACK, False),)}, to_move=WHITE)
    assert G.legal_moves(st) == ["2,2>4,4"]
    st2 = G.apply_move(st, "2,2>4,4")
    # column grew by exactly 1; black prisoner at the BOTTOM, white on top -> "bw"
    assert cols(st2) == {"4,4": "bw"}, cols(st2)
    assert len(st2.board[(4, 4)]) == 2, "moving column grows by exactly 1"
    assert _top(st2.board[(4, 4)]) == (WHITE, False)
    # --- (2) control follows the top piece --------------------------------
    assert _controller(st2.board[(4, 4)]) == WHITE

    # the rest of the jumped column stays: jump a 2-tall enemy column, only its
    # top transfers; the remainder stays in place under new control.
    st = BState(board={(2, 2): ((WHITE, False),),
                       (3, 3): ((WHITE, False), (BLACK, False))},  # 'wb', black on top
                to_move=WHITE)
    assert G.legal_moves(st) == ["2,2>4,4"]
    st2 = G.apply_move(st, "2,2>4,4")
    assert st2.board[(4, 4)] == ((BLACK, False), (WHITE, False)), cols(st2)  # 'bw'
    assert st2.board[(3, 3)] == ((WHITE, False),), "freed white man stays in place"
    assert _controller(st2.board[(3, 3)]) == WHITE, "liberation: control flips to white"

    # --- (3) mandatory + chained multi-jump as one move -------------------
    # a simple move is illegal when a jump exists
    st = BState(board={(2, 2): ((WHITE, False),), (3, 3): ((BLACK, False),),
                       (0, 0): ((WHITE, False),)}, to_move=WHITE)
    assert all("4,4" in m for m in G.legal_moves(st)), G.legal_moves(st)
    # forced multi-jump runs to its end as a single move
    st = BState(board={(2, 2): ((WHITE, False),), (3, 3): ((BLACK, False),),
                       (5, 3): ((BLACK, False),)}, to_move=WHITE)
    # 2,2 x 4,4 (over 3,3) then x 6,2 (over 5,3)
    assert "2,2>4,4>6,2" in G.legal_moves(st)
    assert all(m.count(">") == 2 for m in G.legal_moves(st)), "chain must run to the end"
    st2 = G.apply_move(st, "2,2>4,4>6,2")
    assert cols(st2) == {"6,2": "bbw"}, cols(st2)   # two prisoners at the bottom
    assert len(st2.board[(6, 2)]) == 3

    # --- (4) a MAN captures BACKWARD (Russian rule) -----------------------
    # white man at (4,4); enemy behind it at (3,5); jump backward to (2,6)
    st = BState(board={(4, 4): ((WHITE, False),), (3, 5): ((BLACK, False),)}, to_move=WHITE)
    assert G.legal_moves(st) == ["4,4>2,6"], G.legal_moves(st)
    st2 = G.apply_move(st, "4,4>2,6")
    assert cols(st2) == {"2,6": "bw"}, cols(st2)
    # ... but a man may NOT make a *simple* backward move
    st = BState(board={(4, 4): ((WHITE, False),)}, to_move=WHITE)
    moves = G.legal_moves(st)
    assert set(moves) == {"4,4>3,5", "4,4>5,5"}, moves  # only forward steps

    # --- (5) promotion to a flying king -----------------------------------
    # simple step onto the far rank promotes
    st = BState(board={(2, 6): ((WHITE, False),)}, to_move=WHITE)
    st2 = G.apply_move(st, "2,6>3,7")
    assert _top(st2.board[(3, 7)]) == (WHITE, True), "man promotes on last rank"
    # the king is a flying king: slides any distance on a free diagonal
    st = BState(board={(0, 0): ((WHITE, True),)}, to_move=WHITE)
    km = set(G.legal_moves(st))
    assert "0,0>7,7" in km and "0,0>1,1" in km, km   # slides the whole long diagonal
    # the king captures at a distance and lands beyond
    st = BState(board={(0, 0): ((WHITE, True),), (5, 5): ((BLACK, False),)}, to_move=WHITE)
    km = set(G.legal_moves(st))
    assert "0,0>6,6" in km and "0,0>7,7" in km, km    # over 5,5, land on 6,6 or 7,7
    assert "0,0>4,4" not in km, "cannot stop before the captured piece"
    st2 = G.apply_move(st, "0,0>7,7")
    assert cols(st2) == {"7,7": "bW"}, cols(st2)      # prisoner under the king

    # in-chain promotion (Russian): a man reaching the far rank mid-capture
    # promotes and continues as a flying king.
    # white man (4,4) jumps (5,5)->lands (6,6); not last rank; then needs a king
    # jump. Build: man (1,5) jumps black (2,6) landing (3,7) [far rank -> king],
    # then as a flying king jumps black (5,5) landing on 6,4 or 7,3.
    st = BState(board={(1, 5): ((WHITE, False),),
                       (2, 6): ((BLACK, False),),
                       (5, 5): ((BLACK, False),)}, to_move=WHITE)
    chain = [m for m in G.legal_moves(st) if m.startswith("1,5>3,7>")]
    assert chain, ("expected in-chain promotion continuation", G.legal_moves(st))
    st2 = G.apply_move(st, chain[0])
    # the surviving column is a white KING with two prisoners at the bottom
    sq = [k for k, v in st2.board.items() if _controller(v) == WHITE][0]
    assert _top(st2.board[sq]) == (WHITE, True), "promoted mid-chain, still a king"
    assert len(st2.board[sq]) == 3, "two captured tops banked under the king"

    # --- (6) win: opponent left with no controlled column / no move -------
    st = BState(board={(2, 2): ((WHITE, False),), (3, 3): ((BLACK, False),)}, to_move=WHITE)
    st2 = G.apply_move(st, "2,2>4,4")
    assert st2.winner == WHITE and G.returns(st2) == [1.0, -1.0]
    assert G.is_terminal(st2)
    # opponent has a piece but it is buried (no column they control) -> they lose
    st = BState(board={(2, 2): ((WHITE, True),),
                       (3, 3): ((BLACK, False),)}, to_move=WHITE)
    st2 = G.apply_move(st, "2,2>4,4")   # king jumps, black top banked, black buried
    assert st2.board[(4, 4)] == ((BLACK, False), (WHITE, True))
    assert not any(_controller(v) == BLACK for v in st2.board.values())
    assert st2.winner == WHITE, "black controls no column -> loses"

    # --- serialize round-trips (mixed-owner / king towers) ----------------
    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
