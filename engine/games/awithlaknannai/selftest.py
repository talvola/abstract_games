"""Awithlaknannai Mosona correctness anchor (pure stdlib).

There is no published perft for this game; the anchor is a set of baked rule
assertions covering the serpent-lattice board, the 12v12 start with an empty
centre, line-adjacency, a hand-built jump-capture and a multi-jump chain, and the
two win conditions (annihilation / opponent stuck). The 49-point Kolowis
Awithlaknannai size option is probed separately (Culin 1907: 17+16+16 points,
23 men each, centre + both middle-row end points empty)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.awithlaknannai.game import (  # noqa: E402
    Awithlaknannai, AState, geom, WHITE, BLACK,
)

G = Awithlaknannai()
G25 = geom(25)
ADJ, POINTS, CENTRE = G25.adj, G25.points, G25.centre
MID, TOP, BOT = G25.mid, G25.top, G25.bot


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
    assert s.size == 25
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
    # legacy payloads (no "size" key) must deserialize to the 25-point game,
    # and default-size payloads must not gain a "size" key
    d = G.serialize(st2)
    assert "size" not in d
    assert G.deserialize(d).size == 25

    # ---- Kolowis Awithlaknannai (size 49) --------------------------------
    g49 = geom(49)
    assert len(g49.points) == 49
    assert len(g49.mid) == 17 and len(g49.top) == 16 and len(g49.bot) == 16
    for (x, y) in g49.top + g49.bot:
        assert g49.adj[(x, y)] == {(x - 1, 1), (x + 1, 1)}, (x, y)
    k = G.initial_state(options={"size": 49})
    assert k.size == 49
    # Culin setup: 23 men each; centre (16,1) and the two middle-row end
    # points (0,1)/(32,1) empty; outer rows full.
    assert sum(1 for v in k.board.values() if v == WHITE) == 23
    assert sum(1 for v in k.board.values() if v == BLACK) == 23
    assert len(k.board) == 46
    for empty in [(0, 1), (16, 1), (32, 1)]:
        assert empty not in k.board, empty
    assert all(p in k.board for p in g49.top + g49.bot)
    # halves: white on the low-x middle points, black on the high-x ones
    assert all(k.board[(x, 1)] == WHITE for x in range(2, 16, 2))
    assert all(k.board[(x, 1)] == BLACK for x in range(18, 32, 2))
    # opening moves are steps along drawn lines only
    ms = G.legal_moves(k)
    assert ms and all(len(m.split(">")) == 2 for m in ms)
    for m in ms:
        a, b = m.split(">")
        pa = tuple(map(int, a.split(",")))
        pb = tuple(map(int, b.split(",")))
        assert pb in g49.adj[pa], m
    # a capture on the big board, and size survives apply_move + round-trip
    st = AState(board={(0, 1): WHITE, (2, 1): BLACK}, to_move=WHITE, size=49)
    assert G.legal_moves(st) == ["0,1>4,1"]
    st2 = G.apply_move(st, "0,1>4,1")
    assert st2.size == 49 and st2.winner == WHITE
    rt = G.deserialize(G.serialize(st2))
    assert rt.size == 49 and G.serialize(rt) == G.serialize(st2)
    # render advertises the big lattice
    spec = G.render(k)
    assert len(spec["board"]["cells"]) == 49 and len(spec["pieces"]) == 46

    # ---- random playouts terminate on both sizes -------------------------
    import random
    for size, n_games in ((25, 40), (49, 15)):
        rng = random.Random(20260717 + size)
        for _ in range(n_games):
            st = G.initial_state(options={"size": size})
            while not G.is_terminal(st):
                st = G.apply_move(st, rng.choice(G.legal_moves(st)))
            total = len(st.board)
            assert total <= (24 if size == 25 else 46)
            assert G.returns(st) in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0])

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
