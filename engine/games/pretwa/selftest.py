"""Pretwa correctness anchor (pure stdlib). No published perft, so the anchor is
a set of baked rule asserts:
  (1) the board = 3 rings x 6 spokes + centre = 19 points, with ring-arc and
      radial adjacency and the diameter-through-centre jump line;
  (2) start = 9 men each on three adjacent spokes, centre empty;
  (3) movement = step along a line to an empty point; jump-capture over an
      adjacent enemy to the empty point beyond (mandatory, chaining);
  (4) win = reduce opponent TO three (or fewer) men / annihilate; if no move can
      be made the side with MORE men wins (equal men = a draw).
Plus hand-built step, ring-arc jump, diameter (centre) jump, and chained jump.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.pretwa.game import (  # noqa: E402
    Pretwa, PState, POINTS, ADJ, JUMPS, CENTRE, WHITE, BLACK,
)

G = Pretwa()


def main():
    # (1) board topology --------------------------------------------------
    assert len(POINTS) == 19, len(POINTS)
    assert CENTRE == (0, 0) and CENTRE in POINTS
    assert sum(1 for p in POINTS if p[0] == 0) == 1            # one centre
    for r in (1, 2, 3):
        assert sum(1 for p in POINTS if p[0] == r) == 6        # 6 per ring
    # centre joins all six inner points (radial spokes)
    assert ADJ[CENTRE] == {(1, s) for s in range(6)}
    # ring arc is a 6-cycle: each ring point has its two ring neighbours
    for s in range(6):
        assert (1, (s + 1) % 6) in ADJ[(1, s)] and (1, (s - 1) % 6) in ADJ[(1, s)]
    # radial chain: inner<->middle<->outer on the same spoke
    assert (2, 0) in ADJ[(1, 0)] and (3, 0) in ADJ[(2, 0)]
    assert (3, 0) not in ADJ[(1, 0)]                            # not directly joined
    # diameter jump line exists through the centre: 1,0 - centre - 1,3
    assert (CENTRE, (1, 3)) in JUMPS[(1, 0)]
    # ring-arc jump line exists: 1,0 - 1,1 - 1,2
    assert ((1, 1), (1, 2)) in JUMPS[(1, 0)]
    # radial jump line exists: centre - 1,0 - 2,0  and  1,0 - 2,0 - 3,0
    assert ((1, 0), (2, 0)) in JUMPS[CENTRE]
    assert ((2, 0), (3, 0)) in JUMPS[(1, 0)]

    # (2) start -----------------------------------------------------------
    s = G.initial_state()
    assert sum(1 for v in s.board.values() if v == WHITE) == 9
    assert sum(1 for v in s.board.values() if v == BLACK) == 9
    assert CENTRE not in s.board                                # centre empty
    assert all(s.board[(r, sp)] == WHITE for r in (1, 2, 3) for sp in (0, 1, 2))
    assert all(s.board[(r, sp)] == BLACK for r in (1, 2, 3) for sp in (3, 4, 5))
    # opening: no capture available, so every legal move is a single step
    moves = G.legal_moves(s)
    assert moves and all(len(m.split(">")) == 2 for m in moves)
    # white can step an inner man onto the empty centre
    assert any(m.endswith(">0,0") for m in moves), moves

    # (3a) mandatory capture: a jump pre-empts any plain step ------------
    # white at inner spoke 0, black adjacent on the ring at spoke 1, landing 1,2 empty
    st = PState(board={(1, 0): WHITE, (1, 1): BLACK}, to_move=WHITE)
    assert G.legal_moves(st) == ["1,0>1,2"], G.legal_moves(st)
    st2 = G.apply_move(st, "1,0>1,2")
    assert (1, 1) not in st2.board and st2.board[(1, 2)] == WHITE

    # (3b) diameter capture through the centre: 1,0 over centre to 1,3 ---
    st = PState(board={(1, 0): WHITE, CENTRE: BLACK}, to_move=WHITE)
    # black on centre must itself capture? black to_move is WHITE here, so it's white's turn.
    assert G.legal_moves(st) == ["1,0>1,3"], G.legal_moves(st)
    st2 = G.apply_move(st, "1,0>1,3")
    assert CENTRE not in st2.board and st2.board[(1, 3)] == WHITE

    # (3c) radial step (no capture) to an adjacent empty point -----------
    st = PState(board={(1, 0): WHITE}, to_move=WHITE)
    legal = set(G.legal_moves(st))
    assert "1,0>0,0" in legal and "1,0>2,0" in legal           # radial both ways
    assert "1,0>1,1" in legal and "1,0>1,5" in legal           # ring arc both ways

    # (3d) chained multi-jump along a ring (two enemies, two landings) ---
    # white 1,0; black on 1,1 (land 1,2) then black on 1,3 (land 1,4)
    st = PState(board={(1, 0): WHITE, (1, 1): BLACK, (1, 3): BLACK}, to_move=WHITE)
    assert "1,0>1,2>1,4" in G.legal_moves(st), G.legal_moves(st)
    st2 = G.apply_move(st, "1,0>1,2>1,4")
    assert (1, 1) not in st2.board and (1, 3) not in st2.board
    assert st2.board[(1, 4)] == WHITE and len(st2.board) == 1

    # (4a) win by annihilation -------------------------------------------
    st = PState(board={(1, 0): WHITE, (1, 1): BLACK}, to_move=WHITE)
    st2 = G.apply_move(st, "1,0>1,2")
    assert st2.winner == WHITE and G.returns(st2) == [1.0, -1.0]

    # (4b) win by reducing opponent below three: black has 3, white takes one
    board = {(1, 0): WHITE, (1, 1): BLACK, (2, 1): BLACK, (3, 5): BLACK}
    st = PState(board=board, to_move=WHITE)
    st2 = G.apply_move(st, "1,0>1,2")          # captures the black at 1,1 -> black down to 2
    assert sum(1 for v in st2.board.values() if v == BLACK) == 2
    assert st2.winner == WHITE, st2.winner

    # (4c) REGRESSION (BUG 1): reducing the opponent to EXACTLY three men is a win
    # (the threshold is <=3, not <=2). White jumps 1,0 over the black at 1,1 to 1,2,
    # which is black's 4th-to-3rd man; three distant black men survive.
    board = {(1, 0): WHITE, (1, 1): BLACK,
             (3, 3): BLACK, (3, 4): BLACK, (3, 5): BLACK}
    st = PState(board=board, to_move=WHITE)
    st2 = G.apply_move(st, "1,0>1,2")
    assert sum(1 for v in st2.board.values() if v == BLACK) == 3   # exactly three left
    assert st2.winner == WHITE and st2.over and G.is_terminal(st2)
    assert G.returns(st2) == [1.0, -1.0]

    # (4d) REGRESSION (BUG 2): when the side to move has NO legal move, the result is
    # decided by piece count, NOT an automatic loss for the stuck player.
    #   (i) stuck side with FEWER men loses to the majority (White 13 > Black 5).
    board = {"0,0": 0, "1,0": 0, "1,1": 0, "1,2": 0, "1,3": 0, "1,5": 0,
             "2,0": 1, "2,1": 0, "2,2": 1, "2,3": 0, "2,4": 1, "2,5": 0,
             "3,0": 0, "3,1": 0, "3,2": 0, "3,3": 0, "3,4": 1, "3,5": 1}
    st = PState(board={tuple(int(x) for x in k.split(",")): v
                       for k, v in board.items()}, to_move=WHITE)
    st2 = G.apply_move(st, "1,3>1,4")           # a plain step; afterwards Black is stuck
    assert G.legal_moves(st2) == []             # Black (to move) has no move
    assert G.is_terminal(st2) and st2.over
    assert sum(1 for v in st2.board.values() if v == WHITE) == 13
    assert sum(1 for v in st2.board.values() if v == BLACK) == 5
    assert st2.winner == WHITE, st2.winner       # majority wins

    #   (ii) the stuck side with MORE men WINS (the heart of the fix: stuck != loss).
    board = {"0,0": 1, "1,0": 0, "1,1": 1, "1,2": 1, "1,3": 1, "1,4": 0, "1,5": 1,
             "2,1": 1, "2,2": 1, "2,3": 1, "2,4": 1, "2,5": 1,
             "3,0": 0, "3,1": 0, "3,2": 0, "3,3": 0, "3,4": 0, "3,5": 0}
    st = PState(board={tuple(int(x) for x in k.split(",")): v
                       for k, v in board.items()}, to_move=WHITE)
    st3 = G.apply_move(st, "3,0>2,0")           # White steps; afterwards Black is stuck
    assert G.legal_moves(st3) == []
    assert sum(1 for v in st3.board.values() if v == WHITE) == 8
    assert sum(1 for v in st3.board.values() if v == BLACK) == 10
    assert st3.winner == BLACK and st3.over     # stuck Black still wins on majority
    assert G.returns(st3) == [-1.0, 1.0]

    #   (iii) equal men with no move is a DRAW.
    board = {"0,0": 1, "1,0": 1, "1,1": 0, "1,2": 1, "1,3": 1, "1,4": 1, "1,5": 0,
             "2,0": 1, "2,1": 0, "2,2": 0, "2,3": 1, "2,4": 0, "2,5": 1,
             "3,0": 0, "3,1": 0, "3,3": 0, "3,4": 1, "3,5": 0}
    st = PState(board={tuple(int(x) for x in k.split(",")): v
                       for k, v in board.items()}, to_move=WHITE)
    st4 = G.apply_move(st, "3,1>3,2")           # White steps; afterwards Black is stuck
    assert G.legal_moves(st4) == []
    assert sum(1 for v in st4.board.values() if v == WHITE) == 9
    assert sum(1 for v in st4.board.values() if v == BLACK) == 9
    assert st4.over and st4.winner is None       # equal men => draw
    assert G.returns(st4) == [0.0, 0.0]

    # round-trip serialise
    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
