"""Awithlaknannai Mosona correctness anchor (pure stdlib).

There is no published perft for this game; the anchor is a set of baked rule
assertions covering the serpent-lattice board, the 12v12 start with an empty
centre, line-adjacency, a hand-built jump-capture and a multi-jump chain, and the
two win conditions (annihilation / opponent stuck)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.awithlaknannai.game import (  # noqa: E402
    Awithlaknannai, AState, ADJ, POINTS, MID, TOP, BOT, CENTRE, WHITE, BLACK,
)

G = Awithlaknannai()


def main():
    # ---- board geometry --------------------------------------------------
    assert len(POINTS) == 25, len(POINTS)
    assert len(MID) == 9 and len(TOP) == 8 and len(BOT) == 8
    assert len(set(POINTS)) == 25, "points must be distinct"
    # middle row is a straight chain; interior middle points have 2 middle nbrs
    assert ADJ[(2, 1)] >= {(0, 1), (4, 1)}
    # each outer point joins exactly the two flanking middle points (degree 2)
    for (x, y) in TOP + BOT:
        assert ADJ[(x, y)] == {(x - 1, 1), (x + 1, 1)}, (x, y, ADJ[(x, y)])
    # outer rows are NOT directly connected to each other
    assert (3, 2) not in ADJ[(1, 0)] and (1, 2) not in ADJ[(1, 0)]

    # ---- start: 12v12, only the centre empty -----------------------------
    s = G.initial_state()
    assert sum(1 for v in s.board.values() if v == WHITE) == 12
    assert sum(1 for v in s.board.values() if v == BLACK) == 12
    assert CENTRE not in s.board, "centre starts empty"
    assert len(s.board) == 24, "exactly one empty point"
    # opening: no capture available, so every legal move is a single step of
    # length 1 along a drawn line (to an adjacent point)
    for m in G.legal_moves(s):
        a, b = m.split(">")
        ax, ay = map(int, a.split(","))
        bx, by = map(int, b.split(","))
        assert (bx, by) in ADJ[(ax, ay)], m
    assert all(len(m.split(">")) == 2 for m in G.legal_moves(s))

    # ---- mandatory single jump along the middle row ----------------------
    # WHITE at (0,1), BLACK at (2,1), land (4,1) empty -> only the jump is legal.
    st = AState(board={(0, 1): WHITE, (2, 1): BLACK, (9, 0): WHITE}, to_move=WHITE)
    # (9,0) gives white another piece with a legal step, to prove the jump is
    # FORCED over the step (mandatory capture).
    assert G.legal_moves(st) == ["0,1>4,1"], G.legal_moves(st)
    st2 = G.apply_move(st, "0,1>4,1")
    assert (2, 1) not in st2.board and st2.board[(4, 1)] == WHITE

    # ---- diagonal jump ----------------------------------------------------
    # WHITE (1,0) over BLACK (2,1) lands on (3,2).
    st = AState(board={(1, 0): WHITE, (2, 1): BLACK}, to_move=WHITE)
    assert "1,0>3,2" in G.legal_moves(st), G.legal_moves(st)

    # ---- multi-jump chain changing direction ------------------------------
    # WHITE (1,0) -> over (2,1) -> (3,2) -> over (4,1) -> (5,0).
    st = AState(board={(1, 0): WHITE, (2, 1): BLACK, (4, 1): BLACK}, to_move=WHITE)
    assert "1,0>3,2>5,0" in G.legal_moves(st), G.legal_moves(st)
    st2 = G.apply_move(st, "1,0>3,2>5,0")
    assert (2, 1) not in st2.board and (4, 1) not in st2.board
    assert st2.board[(5, 0)] == WHITE and len([v for v in st2.board.values() if v == BLACK]) == 0

    # ---- win by annihilation ---------------------------------------------
    st = AState(board={(0, 1): WHITE, (2, 1): BLACK}, to_move=WHITE)
    st2 = G.apply_move(st, "0,1>4,1")
    assert st2.winner == WHITE and G.returns(st2) == [1.0, -1.0]

    # ---- win by immobilising the opponent --------------------------------
    # BLACK at (1,0): its only neighbours are (0,1) and (2,1). Fill both with
    # WHITE, and block both jump-landings (3,2) behind (2,1) so black cannot
    # jump either. (0,1) has no point beyond it from (1,0), so it cannot be
    # jumped. Black is stuck.
    board = {(1, 0): BLACK, (0, 1): WHITE, (2, 1): WHITE, (3, 2): WHITE}
    st = AState(board=board, to_move=BLACK)
    assert G.legal_moves(st) == [], G.legal_moves(st)

    # ---- serialize round-trip --------------------------------------------
    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
