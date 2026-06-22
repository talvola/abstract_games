"""Go correctness anchor (pure stdlib). Pins the parts full Go adds over the
lighter Go-family cousins: Tromp-Taylor area scoring (stones + single-colour
territory + komi), two-pass termination deciding the winner, capture, illegal
suicide, and positional superko (the ko rule). The liberty/group/capture core is
the same logic verified in Atari Go."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.go.game import Go, GoState, _score, _board_key, BLACK, WHITE  # noqa: E402

G = Go()


def main():
    # --- area scoring -----------------------------------------------------
    assert _score({}, 9, 7.5) == (0, 7.5)                       # empty board
    assert _score({(2, 2): BLACK}, 5, 0.5) == (25, 0.5)        # one stone owns all
    split = {}
    for r in range(5):
        split[(0, r)] = split[(1, r)] = BLACK
        split[(3, r)] = split[(4, r)] = WHITE
    assert _score(split, 5, 0.5) == (10, 10.5)                  # middle column = dame

    # --- capture: a surrounded stone is removed ---------------------------
    s = GoState(size=5, board={(0, 0): WHITE, (1, 0): BLACK}, to_move=BLACK)
    s.history = frozenset({_board_key(s.board, 5)})
    s2 = G.apply_move(s, "0,1")                                 # black surrounds (0,0)
    assert (0, 0) not in s2.board and s2.board.get((0, 1)) == BLACK

    # --- suicide is illegal ----------------------------------------------
    #  White stones ring the empty corner (0,0); Black may not play into it.
    board = {(1, 0): WHITE, (0, 1): WHITE}
    s = GoState(size=5, board=board, to_move=BLACK)
    s.history = frozenset({_board_key(board, 5)})
    assert "0,0" not in G.legal_moves(s), "suicide must be illegal"
    #  ...but the same move IS legal if it captures (not suicide):
    board2 = {(1, 0): WHITE, (0, 1): BLACK, (2, 0): BLACK}      # white (1,0) in atari
    s = GoState(size=5, board=board2, to_move=BLACK)
    s.history = frozenset({_board_key(board2, 5)})
    # black at (0,0) would still self-atari? (0,0) libs after: none unless capture.
    # Build a clean capture-not-suicide: white (1,1) lone, black around except (0,1).
    cap = {(1, 1): WHITE, (0, 1): BLACK, (1, 0): BLACK, (1, 2): BLACK}
    s = GoState(size=5, board=cap, to_move=BLACK)
    s.history = frozenset({_board_key(cap, 5)})
    assert "2,1" in G.legal_moves(s)                            # captures (1,1), legal

    # --- positional superko forbids recreating a prior board (the ko) -----
    base = {(1, 0): BLACK, (0, 1): BLACK, (1, 2): BLACK,
            (2, 0): WHITE, (3, 1): WHITE, (2, 2): WHITE, (1, 1): WHITE}
    s0 = GoState(size=5, board=dict(base), to_move=BLACK)
    s0.history = frozenset({_board_key(base, 5)})
    s1 = G.apply_move(s0, "2,1")                                # black takes the ko at (1,1)
    assert (1, 1) not in s1.board and (2, 1) in s1.board
    assert "1,1" not in G.legal_moves(s1), "ko recapture must be superko-illegal"

    # --- two passes end the game and the score decides --------------------
    s = G.initial_state(options={"size": 5, "komi": 0.5})
    s = G.apply_move(s, "2,2")                                  # a lone black stone
    s = G.apply_move(s, "pass")
    s = G.apply_move(s, "pass")
    assert G.is_terminal(s) and G.returns(s) == [1.0, -1.0]     # black controls all
    # 'pass' is always offered while the game is live
    assert "pass" in G.legal_moves(G.initial_state())

    # --- serialize round-trips (incl. komi, passes, history) --------------
    s = G.apply_move(G.apply_move(G.initial_state(), "4,4"), "pass")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("go selftest OK")


if __name__ == "__main__":
    main()
