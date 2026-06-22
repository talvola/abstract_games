"""Quoridor correctness anchor (pure stdlib): the wall-blocks-movement rule, the
no-overlap / no-cross wall constraints, the pawn jump (straight and diagonal), the
pathfinding gate's plumbing, and the reach-the-far-row win. The full pathfinding
legality (a wall may not seal a pawn off from its goal) is checked in the
adversarial rule review, which can build separating mazes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.quoridor.game import Quoridor, QState  # noqa: E402

G = Quoridor()


def pawn_dests(s):
    return {m.split(">")[1] for m in G.legal_moves(s) if ">" in m}


def main():
    s = G.initial_state()
    assert s.pawns == [(4, 0), (4, 8)] and s.counts == [10, 10]
    lm = G.legal_moves(s)
    assert len([m for m in lm if ">" in m]) == 3          # up/left/right (not down)
    assert len([m for m in lm if m[0] in "HV"]) == 128     # 64 H + 64 V

    # a wall blocks the step it spans
    s2 = G.apply_move(s, "H4,0")                            # blocks (4,0)<->(4,1)
    st = QState(pawns=s2.pawns, walls_h=s2.walls_h, walls_v=s2.walls_v, counts=s2.counts, to_move=0)
    assert "4,1" not in pawn_dests(st) and "5,0" in pawn_dests(st)

    # no overlap / no crossing
    base = QState(pawns=[(4, 0), (4, 8)], walls_h=frozenset({(4, 0)}), counts=[9, 10], to_move=1)
    assert not G._wall_ok(base, "H", 5, 0)                  # overlaps the H wall at (4,0)
    assert not G._wall_ok(base, "H", 3, 0)
    assert G._wall_ok(base, "H", 6, 0)                      # far enough away -> ok
    assert not G._wall_ok(base, "V", 4, 0)                  # crosses at the same post
    assert G._wall_ok(base, "V", 4, 1)

    # pawn jump: straight over the opponent, and diagonal when the far side is walled
    st = QState(pawns=[(4, 4), (4, 5)], to_move=0)
    assert "4,6" in pawn_dests(st)                          # jump straight
    st = QState(pawns=[(4, 4), (4, 5)], walls_h=frozenset({(4, 5)}), to_move=0)
    d = pawn_dests(st)                                      # far side (4,6) blocked
    assert "4,6" not in d and "3,5" in d and "5,5" in d     # diagonal sidesteps

    # pathfinding plumbing: open board always has a path; a normal wall keeps it
    assert G._has_path(frozenset(), frozenset(), (4, 0), 8)
    assert G._wall_ok(G.initial_state(), "H", 0, 0)

    # win by reaching the far row
    st = QState(pawns=[(4, 7), (4, 1)], to_move=0)
    st2 = G.apply_move(st, "4,7>4,8")
    assert st2.winner == 0 and G.returns(st2) == [1.0, -1.0]

    # placing a wall passes the turn and decrements the count
    s3 = G.apply_move(G.initial_state(), "V2,3")
    assert s3.to_move == 1 and s3.counts[0] == 9 and (2, 3) in s3.walls_v

    assert G.serialize(G.deserialize(G.serialize(s3))) == G.serialize(s3)
    print("quoridor selftest OK")


if __name__ == "__main__":
    main()
