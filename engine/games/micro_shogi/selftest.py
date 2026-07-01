"""Micro Shogi correctness anchor (pure stdlib).

Micro Shogi's engine reuses the ShogiLike core's colour-relative move generation,
drop bookkeeping and check detection, but replaces zone-promotion with the
game's signature **promote-on-capture** flip (a token flips to its other face
whenever it captures; a promoted face flips back when it captures again).

There is no published perft for Micro Shogi, so we hand-count the opening legal
moves (= 9) and then anchor on this engine's self-computed perft 1/2/3, plus
direct checks of the flip-on-capture, the either-face drop and serialize.

Opening count 9, by piece (Black to move from the standard S G B K / P setup):
  S(0,0)=2  G(1,0)=3  B(2,0)=2  K(3,0)=1  P(3,1)=1
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.micro_shogi.game import MicroShogi        # noqa: E402
from agp.shogilike import SState, BLACK, WHITE        # noqa: E402

G = MicroShogi()


def perft(s, d):
    if d == 0:
        return 1
    if G.is_terminal(s):
        return 0
    return sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


def main():
    s0 = G.initial_state()

    # board shape: 4 files x 5 ranks
    rb = G.render(s0)["board"]
    assert rb == {"type": "square", "width": 4, "height": 5}, rb

    # exact setup: Black S G B K on row 0 (files 0..3), pawn in front of the King;
    # White is a 180-degree rotation (King in the opposite corner).
    b = s0.board
    assert "".join(b[(c, 0)][1] for c in range(4)) == "SGBK"
    assert b[(3, 1)] == (BLACK, "P")
    assert b[(3, 0)] == (BLACK, "K") and b[(0, 4)] == (WHITE, "K")
    assert b[(0, 3)] == (WHITE, "P")
    assert "".join(b[(c, 4)][1] for c in range(4)) == "KBGS"   # white back rank (files 0..3)
    assert sum(1 for v in b.values() if v[0] == BLACK) == 5
    assert sum(1 for v in b.values() if v[0] == WHITE) == 5

    # no promotion zone at all
    assert G.ZONE == 0

    # opening legal-move count is hand-checked = 9 (see module docstring)
    assert len(G.legal_moves(s0)) == 9, len(G.legal_moves(s0))
    # self-computed perft anchors (no published reference exists)
    for d, want in {1: 9, 2: 80, 3: 767}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # --- promote-on-capture: a capturing Silver flips to a Lance; the captured
    # Pawn banks by its pair. Kings present so the base helpers are well-defined.
    st = SState(board={(3, 0): (BLACK, "K"), (0, 4): (WHITE, "K"),
                       (1, 1): (BLACK, "S"), (1, 2): (WHITE, "P")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "1,1>1,2")
    assert st2.board[(1, 2)] == (BLACK, "L"), st2.board[(1, 2)]
    assert st2.hands[BLACK] == {"P": 1}, st2.hands[BLACK]

    # --- demote-on-capture: a promoted face (Lance) capturing flips back to Silver
    st = SState(board={(3, 0): (BLACK, "K"), (0, 4): (WHITE, "K"),
                       (1, 1): (BLACK, "L"), (1, 3): (WHITE, "G")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "1,1>1,3")            # Lance slides forward and captures
    assert st2.board[(1, 3)] == (BLACK, "S"), st2.board[(1, 3)]
    assert st2.hands[BLACK] == {"G": 1}, st2.hands[BLACK]

    # --- a quiet (non-capturing) move does NOT flip the face
    st = SState(board={(3, 0): (BLACK, "K"), (0, 4): (WHITE, "K"), (1, 1): (BLACK, "S")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert G.apply_move(st, "1,1>1,2").board[(1, 2)] == (BLACK, "S")

    # --- drop: a held token offers BOTH faces; no nifu / last-rank restriction
    st = SState(board={(3, 0): (BLACK, "K"), (0, 4): (WHITE, "K"), (1, 1): (BLACK, "P")},
                hands={BLACK: {"P": 1, "S": 1}, WHITE: {}}, to_move=BLACK)
    lm = G.legal_moves(st)
    assert "P@1,2" in lm, "second pawn on a file must be allowed (no nifu)"
    assert "N@1,2" in lm, "pawn-pair may also drop as a Knight"
    assert "S@2,2" in lm and "L@2,2" in lm, "silver-pair drops as either face"
    # a Pawn may even drop on the last rank (it is simply trapped there)
    assert "P@2,4" in lm, "last-rank pawn drop is legal in Micro Shogi"
    st2 = G.apply_move(st, "L@2,2")              # drop the silver-pair as a Lance
    assert st2.board[(2, 2)] == (BLACK, "L") and "S" not in st2.hands[BLACK]

    # serialize round-trips (initial + a capture-derived state)
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)
    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
