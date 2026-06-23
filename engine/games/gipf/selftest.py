"""GIPF correctness anchor (pure stdlib -- imports only agp + this game).

There is no published perft for GIPF, so the anchor is a set of baked rule
assertions on hand-built positions, verified against the official rules
(gipf.com / Rio Grande rulebook / Wikipedia):

  (1) board geometry: 37 spots (radius-3 hex), 24 entry dots (radius-4 ring),
      six corners, three line directions;
  (2) a turn INTRODUCES a piece from reserve onto an entry dot and SHOVES it one
      step inward, sliding the contiguous run of pieces ahead of it; a shove is
      illegal when the line is full to the far edge;
  (3) a line of FOUR OR MORE of your colour is removed -- your pieces return to
      your reserve, the opponent pieces in the contiguous extension are captured
      (lost);
  (4) a player who cannot introduce (empty reserve) loses, reached via apply_move.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.gipf.game import (  # noqa: E402
    Gipf, GState, SPOTS, DOTS, CORNERS, ENTRIES, ALL_LINES, _cell, _qr,
)

G = Gipf()


def main():
    # --- (1) geometry -----------------------------------------------------
    assert len(SPOTS) == 37, len(SPOTS)
    assert len(DOTS) == 24, len(DOTS)
    assert len(CORNERS) == 6, CORNERS
    # three line directions -> maximal lines (3 long diagonals of length 7)
    assert len(ALL_LINES) == 21, len(ALL_LINES)
    lengths = sorted(len(l) for l in ALL_LINES)
    assert lengths.count(7) == 3 and lengths.count(4) == 6, lengths
    # every entry's first spot is a board spot adjacent to its dot
    for (dot, first), (d, line) in ENTRIES.items():
        assert first in set(SPOTS), (dot, first)
        assert dot not in set(SPOTS), dot
        assert line[0] == first
    # the 6 corner dots have a single inward line (the long diagonals);
    # there is at least one entry from every dot.
    dots_used = {dot for (dot, first) in ENTRIES}
    assert dots_used == set(DOTS), "every dot offers an entry"

    # --- initial position: 3 + 3 pieces on the six corners ---------------
    st0 = G.initial_state()
    assert len(st0.board) == 6, st0.board
    assert sum(1 for v in st0.board.values() if v == 0) == 3
    assert sum(1 for v in st0.board.values() if v == 1) == 3
    assert st0.reserve == [12, 12], st0.reserve
    # all six occupied spots are corners
    assert all(_qr(c) in set(CORNERS) for c in st0.board)

    # --- (2) shove: pieces slide one step inward -------------------------
    # Build a clean line and push a piece in behind two pieces; they all slide.
    # pick the central horizontal line r=0: spots (-3,0)..(3,0)
    line = [(q, 0) for q in range(-3, 4)]
    assert all(c in set(SPOTS) for c in line)
    # find the entry that pushes onto (-3,0) heading +q
    entry = None
    for (dot, first), (d, ln) in ENTRIES.items():
        if first == (-3, 0) and d == (1, 0):
            entry = (dot, first)
            break
    assert entry is not None
    dot, first = entry
    # place two White pieces at (-3,0) and (-2,0); empty elsewhere on the line
    board = {_cell((-3, 0)): 0, _cell((-2, 0)): 0}
    st = GState(board=dict(board), reserve=[12, 12], to_move=0)
    mv = f"{_cell(dot)}>{_cell(first)}"
    assert mv in G.legal_moves(st), (mv, G.legal_moves(st)[:5])
    st2 = G.apply_move(st, mv)
    # new piece at (-3,0); the two that were there slid to (-2,0),(-1,0)
    assert st2.board[_cell((-3, 0))] == 0
    assert st2.board[_cell((-2, 0))] == 0
    assert st2.board[_cell((-1, 0))] == 0
    assert _cell((0, 0)) not in st2.board
    assert st2.reserve[0] == 11, st2.reserve   # one piece introduced

    # --- shove illegal when the line is full to the far edge -------------
    full = {_cell(c): 0 for c in line}          # all 7 spots on r=0 occupied
    stf = GState(board=full, reserve=[12, 12], to_move=0)
    assert mv not in G.legal_moves(stf), "full line must reject the shove"

    # --- (3) four-in-a-row removal: own pieces to reserve ----------------
    # Three White on (-2,0),(-1,0),(0,0); shove a fourth in at (-3,0) -> run of 4.
    board = {_cell((-2, 0)): 0, _cell((-1, 0)): 0, _cell((0, 0)): 0}
    st = GState(board=dict(board), reserve=[12, 12], to_move=0)
    st2 = G.apply_move(st, mv)                   # introduce White at (-3,0)
    # now White has 4 in a row -> White must remove
    assert st2.removing == 0, (st2.removing,)
    runs = G.legal_moves(st2)
    assert len(runs) == 1, runs
    st3 = G.apply_move(st2, runs[0])
    # the four White pieces returned to reserve: started 12, -1 introduced,
    # +4 returned = 15
    assert st3.reserve[0] == 15, st3.reserve
    # the line is now empty of those pieces
    assert all(_cell(c) not in st3.board for c in line[:4]), st3.board
    # turn passed to Black
    assert st3.to_move == 1 and st3.removing is None

    # --- removal extension: opponent piece in the run is captured (lost) -
    # White run of 4 plus a contiguous Black piece -> Black piece captured.
    board = {_cell((-3, 0)): 0, _cell((-2, 0)): 0, _cell((-1, 0)): 0,
             _cell((0, 0)): 0,                 # White four in a row
             _cell((1, 0)): 1}                  # contiguous Black -> extension
    st = GState(board=dict(board), reserve=[10, 10], to_move=0, removing=0)
    runs = G.legal_moves(st)
    assert len(runs) == 1, runs
    st2 = G.apply_move(st, runs[0])
    assert st2.reserve[0] == 14, st2.reserve    # 4 White returned (10+4)
    assert st2.reserve[1] == 10, st2.reserve    # Black piece captured, NOT banked
    assert _cell((1, 0)) not in st2.board        # the Black piece is gone

    # a gap stops the extension: a Black piece separated by an empty spot stays.
    board = {_cell((-3, 0)): 0, _cell((-2, 0)): 0, _cell((-1, 0)): 0,
             _cell((0, 0)): 0,                 # White four
             # (1,0) empty -> gap
             _cell((2, 0)): 1}                  # Black beyond the gap survives
    st = GState(board=dict(board), reserve=[10, 10], to_move=0, removing=0)
    st2 = G.apply_move(st, G.legal_moves(st)[0])
    assert st2.board.get(_cell((2, 0))) == 1, "piece past a gap must survive"

    # --- (4) loss on empty reserve, reached via apply_move ---------------
    # White has 1 piece in reserve and no piece on the board near a run; after
    # White introduces its last piece, on Black's settled turn nothing changes;
    # then construct: Black to move with empty reserve -> Black loses.
    # Reach it: a state where after the move it becomes Black's turn with reserve 0.
    board = {_cell((3, 3)): 1}                   # one stray Black piece
    st = GState(board=dict(board), reserve=[5, 0], to_move=1)
    # Black to move but reserve is empty -> _settle on entering Black's turn.
    # legal_moves should be empty and is_terminal via reaching it:
    # Build the predecessor: White moves, handing the turn to Black (reserve 0).
    pre = GState(board=dict(board), reserve=[5, 0], to_move=0)
    # find any legal White entry
    wmv = G.legal_moves(pre)[0]
    post = G.apply_move(pre, wmv)
    assert post.to_move == 1, post.to_move
    assert post.winner == 0, (post.winner, post.reserve)   # Black can't introduce
    assert G.is_terminal(post)
    assert G.returns(post) == [1.0, -1.0]

    # --- serialize round-trips -------------------------------------------
    s = G.apply_move(G.initial_state(), G.legal_moves(G.initial_state())[0])
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
