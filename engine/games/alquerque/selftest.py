"""Alquerque correctness anchor (pure stdlib): the 12v12 setup with an empty
centre, mandatory jump-capture with chains, and the two win conditions
(annihilation / opponent stuck)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.alquerque.game import Alquerque, AState, WHITE, BLACK  # noqa: E402

G = Alquerque()


def main():
    s = G.initial_state()
    assert sum(1 for v in s.board.values() if v == WHITE) == 12
    assert sum(1 for v in s.board.values() if v == BLACK) == 12
    assert (2, 2) not in s.board                              # empty centre
    # opening has no capture, so all moves are single steps
    assert all(len(m.split(">")) == 2 for m in G.legal_moves(s))
    assert all(max(abs(int(m.split(">")[1].split(",")[0]) - int(m.split(">")[0].split(",")[0])),
                   abs(int(m.split(">")[1].split(",")[1]) - int(m.split(">")[0].split(",")[1]))) == 1
               for m in G.legal_moves(s))

    # mandatory capture: when a jump exists, only jumps are legal
    st = AState(board={(1, 1): WHITE, (2, 2): BLACK, (0, 0): WHITE}, to_move=WHITE)
    assert G.legal_moves(st) == ["1,1>3,3"], G.legal_moves(st)

    # chained multi-jump across two strong points
    st = AState(board={(0, 0): WHITE, (1, 1): BLACK, (3, 3): BLACK}, to_move=WHITE)
    assert "0,0>2,2>4,4" in G.legal_moves(st), G.legal_moves(st)
    st2 = G.apply_move(st, "0,0>2,2>4,4")
    assert (1, 1) not in st2.board and (3, 3) not in st2.board and st2.board[(4, 4)] == WHITE

    # win by annihilation: capture the last black piece
    st = AState(board={(1, 1): WHITE, (2, 2): BLACK}, to_move=WHITE)
    st2 = G.apply_move(st, "1,1>3,3")
    assert st2.winner == WHITE and G.returns(st2) == [1.0, -1.0]

    # win by leaving the opponent with no move: black boxed into a corner
    #  black at (0,0); whites on its only line-neighbours (1,0),(0,1),(1,1) and the
    #  jump-landings behind them, so black is stuck on its turn.
    board = {(0, 0): BLACK, (1, 0): WHITE, (0, 1): WHITE, (1, 1): WHITE,
             (2, 0): WHITE, (0, 2): WHITE, (2, 2): WHITE}
    st = AState(board=board, to_move=BLACK)
    assert G.legal_moves(st) == [], "black should be stuck"

    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)
    print("alquerque selftest OK")


if __name__ == "__main__":
    main()
