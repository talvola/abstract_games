"""Quixo correctness anchor (pure stdlib). No published perft exists, so the
anchor is hand-built rule positions covering the take/slide/win mechanics:

  (1) opening legal-move count (border cubes x legal slide edges);
  (2) the slide shifts the line correctly and stamps the mover's symbol;
  (3) you may not take a cube showing the opponent's symbol;
  (4) a slide that completes YOUR line wins;
  (5) a slide that completes only the OPPONENT's line loses (opponent wins);
  (6) serialize round-trip.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.quixo.game import Quixo, QState, BLANK, N, BORDER  # noqa: E402

G = Quixo()


def board(overrides):
    b = {(c, r): BLANK for r in range(N) for c in range(N)}
    b.update(overrides)
    return b


def main():
    # (1) opening: 16 border cells, all blank/takeable. 4 corners x 2 dirs +
    #     12 edge cells x 3 dirs = 8 + 36 = 44 moves.
    s0 = G.initial_state()
    assert len(BORDER) == 16, len(BORDER)
    assert len(G.legal_moves(s0)) == 44, len(G.legal_moves(s0))

    # (2) slide shifts the line and stamps the mover. Row 0 = [X, O, _, _, _];
    #     X takes the blank at (4,0) and pushes from the LEFT -> the cube enters
    #     at col 0 and cols 0..3 shift right.
    s = QState(board=board({(0, 0): 0, (1, 0): 1}), to_move=0)
    s2 = G.apply_move(s, "4,0=L")
    row0 = {c: s2.board[(c, 0)] for c in range(N)}
    assert row0 == {0: 0, 1: 0, 2: 1, 3: BLANK, 4: BLANK}, row0
    assert s2.to_move == 1 and s2.winner is None

    # (3) cannot take the opponent's cube: (0,0) shows O, X to move -> no move
    #     touches (0,0).
    s = QState(board=board({(0, 0): 1}), to_move=0)
    assert all(not m.startswith("0,0=") for m in G.legal_moves(s)), "took opp cube"
    # ...but the owner (O) may take their own border cube.
    s_o = QState(board=board({(0, 0): 1}), to_move=1)
    assert any(m.startswith("0,0=") for m in G.legal_moves(s_o))

    # (4) mover completes their own line. Row 2 = four X then blank; X takes the
    #     blank at (4,2), pushes from the LEFT -> row 2 becomes five X.
    s = QState(board=board({(0, 2): 0, (1, 2): 0, (2, 2): 0, (3, 2): 0}), to_move=0)
    s2 = G.apply_move(s, "4,2=L")
    assert all(s2.board[(c, 2)] == 0 for c in range(N)), "row not all X"
    assert s2.winner == 0, s2.winner
    assert G.returns(s2) == [1.0, -1.0]

    # (5) X's slide completes only O's line -> O wins. Column 2 holds O at rows
    #     0,2,3,4 (row 1 empty) and an O waits at (3,1). X takes (0,1) and pushes
    #     from the RIGHT: cols 1..4 of row 1 shift left, sliding (3,1)'s O into
    #     (2,1) -> column 2 becomes five O. The stamped X lands at (4,1), off the
    #     column, so only O completes a line.
    s = QState(board=board({(2, 0): 1, (2, 2): 1, (2, 3): 1, (2, 4): 1,
                            (3, 1): 1}), to_move=0)
    s2 = G.apply_move(s, "0,1=R")
    assert all(s2.board[(2, r)] == 1 for r in range(N)), \
        {r: s2.board[(2, r)] for r in range(N)}
    assert s2.board[(4, 1)] == 0, "stamped cube should be X at (4,1)"
    assert s2.winner == 1, ("opponent-completion must hand O the win", s2.winner)
    assert G.returns(s2) == [-1.0, 1.0]

    # (6) serialize round-trips.
    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
