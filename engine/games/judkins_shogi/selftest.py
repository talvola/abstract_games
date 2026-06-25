"""Judkins Shogi correctness anchor (pure stdlib).

The move generator is the same python-shogi-verified ShogiLike core used by full
Shogi and Mini Shogi; here we pin the 6x6 Judkins setup, the two-rank (ZONE=2)
promotion zone, and the Knight (which Mini Shogi lacks).

There is no published perft for Judkins shogi, so we hand-count the opening legal
moves (= 20) and then anchor on this engine's self-computed perft 1/2/3.

Opening count 20, by piece (Black to move from the standard setup):
  K(0,0)=1  P(0,1)=1  G(1,0)=2  S(2,0)=3  N(3,0)=2  B(4,0)=6(incl 1 promo)  R(5,0)=5(incl 1 promo)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.judkins_shogi.game import JudkinsShogi   # noqa: E402
from agp.shogilike import SState, BLACK, WHITE       # noqa: E402

G = JudkinsShogi()


def perft(s, d):
    if d == 0:
        return 1
    if G.is_terminal(s):
        return 0
    return sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


def main():
    s0 = G.initial_state()

    # opening legal-move count is hand-checked = 20 (see module docstring)
    assert len(G.legal_moves(s0)) == 20, len(G.legal_moves(s0))
    # self-computed perft anchors (no published reference exists)
    for d, want in {1: 20, 2: 336, 3: 6183}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # setup: kings in opposite left corners, 7 pieces a side, both pawns present
    b = s0.board
    assert b[(0, 0)] == (BLACK, "K") and b[(5, 5)] == (WHITE, "K")
    assert b[(0, 1)] == (BLACK, "P") and b[(5, 4)] == (WHITE, "P")
    assert "".join(b[(c, 0)][1] for c in range(6)) == "KGSNBR"
    assert "".join(b[(c, 5)][1] for c in range(6)) == "RBNSGK"
    assert sum(1 for v in b.values() if v[0] == BLACK) == 7
    assert sum(1 for v in b.values() if v[0] == WHITE) == 7

    # ZONE = 2: the far two ranks promote (rows 4,5 for Black; rows 0,1 for White)
    assert G.in_zone(BLACK, 5) and G.in_zone(BLACK, 4) and not G.in_zone(BLACK, 3)
    assert G.in_zone(WHITE, 0) and G.in_zone(WHITE, 1) and not G.in_zone(WHITE, 2)

    # a Black pawn reaching the last rank must promote (only the +move exists)
    st = SState(board={(0, 0): (BLACK, "K"), (5, 5): (WHITE, "K"), (2, 4): (BLACK, "P")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    pm = [m for m in G.legal_moves(st) if m.startswith("2,4>")]
    assert pm == ["2,4>2,5=+"], pm

    # a Black silver moving INTO the zone (row 4) has both promote / not-promote
    st = SState(board={(0, 0): (BLACK, "K"), (5, 5): (WHITE, "K"), (2, 3): (BLACK, "S")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    mv = G.legal_moves(st)
    assert "2,3>2,4" in mv and "2,3>2,4=+" in mv, mv

    # a Black silver still on row 2 (outside the zone) cannot promote
    st = SState(board={(0, 0): (BLACK, "K"), (5, 5): (WHITE, "K"), (2, 2): (BLACK, "S")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    mv = G.legal_moves(st)
    assert "2,2>2,3" in mv and "2,2>2,3=+" not in mv, mv

    # capture -> the captured piece switches side into the hand, then can be dropped
    st = SState(board={(0, 0): (BLACK, "K"), (5, 5): (WHITE, "K"),
                       (2, 2): (BLACK, "R"), (2, 3): (WHITE, "S")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "2,2>2,3")             # Rxs
    assert st2.hands[BLACK] == {"S": 1}, st2.hands
    # white replies, then black drops the silver on an empty square
    st3 = G.apply_move(st2, "5,5>4,5")            # white king steps aside
    drop = "S@1,1"
    assert drop in G.legal_moves(st3), "silver drop should be legal"
    st4 = G.apply_move(st3, drop)
    assert st4.board[(1, 1)] == (BLACK, "S") and "S" not in st4.hands[BLACK]

    # nifu: you may not drop a pawn onto a file already holding your unpromoted pawn
    st = SState(board={(0, 0): (BLACK, "K"), (5, 5): (WHITE, "K"),
                       (3, 1): (BLACK, "P")},
                hands={BLACK: {"P": 1}, WHITE: {}}, to_move=BLACK)
    drops = [m for m in G.legal_moves(st) if m.startswith("P@")]
    assert not any(m == f"P@3,{r}" for r in range(6) for m in drops), \
        "pawn drop on the occupied file must be rejected (nifu)"
    # ...but a pawn drop on a different empty file is fine
    assert "P@2,2" in drops, drops

    # serialize round-trips
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)
    assert G.serialize(G.deserialize(G.serialize(st4))) == G.serialize(st4)

    print("judkins_shogi selftest OK")


if __name__ == "__main__":
    main()
