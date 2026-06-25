"""Goro Goro Shogi correctness anchor (pure stdlib).

The move generator is the same python-shogi-verified ShogiLike core used by full
Shogi, Mini Shogi and Judkins Shogi; here we pin the 5x6 Goro Goro setup, the
two-rank (ZONE=2) promotion zone, and the reduced army (King, two Golds, two
Silvers, three Pawns -- no rook/bishop/knight/lance).

There is no published perft for Goro Goro shogi, so we hand-count the opening
legal moves (= 7) and then anchor on this engine's self-computed perft 1/2/3.

Opening count 7, by piece (Black to move from the standard setup
S G K G S on row 0, pawns on (1,1) (2,1) (3,1)):
  S(0,0)=1 [->0,1]   G(1,0)=1 [->0,1]   K(2,0)=0 (boxed in)
  G(3,0)=1 [->4,1]   S(4,0)=1 [->4,1]   P(1,1)=1 P(2,1)=1 P(3,1)=1
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.goro_goro_shogi.game import GoroGoroShogi   # noqa: E402
from agp.shogilike import SState, BLACK, WHITE          # noqa: E402

G = GoroGoroShogi()


def perft(s, d):
    if d == 0:
        return 1
    if G.is_terminal(s):
        return 0
    return sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


def main():
    s0 = G.initial_state()

    # opening legal-move count is hand-checked = 7 (see module docstring)
    assert len(G.legal_moves(s0)) == 7, len(G.legal_moves(s0))
    # self-computed perft anchors (no published reference exists)
    for d, want in {1: 7, 2: 49, 3: 434}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # board geometry: 5 wide, 6 tall
    assert (G.WIDTH, G.HEIGHT) == (5, 6)

    # setup: kings centred on opposite ranks, 8 pieces a side, three pawns each
    b = s0.board
    assert b[(2, 0)] == (BLACK, "K") and b[(2, 5)] == (WHITE, "K")
    assert "".join(b[(c, 0)][1] for c in range(5)) == "SGKGS"
    assert "".join(b[(c, 5)][1] for c in range(5)) == "SGKGS"
    assert all(b[(c, 1)] == (BLACK, "P") for c in (1, 2, 3))
    assert all(b[(c, 4)] == (WHITE, "P") for c in (1, 2, 3))
    assert sum(1 for v in b.values() if v[0] == BLACK) == 8
    assert sum(1 for v in b.values() if v[0] == WHITE) == 8
    # exactly the Goro Goro army, no rook/bishop/knight/lance anywhere
    blk = sorted(t for (p, t) in b.values() if p == BLACK)
    assert blk == ["G", "G", "K", "P", "P", "P", "S", "S"], blk

    # ZONE = 2: the far two ranks promote (rows 4,5 for Black; rows 0,1 for White)
    assert G.in_zone(BLACK, 5) and G.in_zone(BLACK, 4) and not G.in_zone(BLACK, 3)
    assert G.in_zone(WHITE, 0) and G.in_zone(WHITE, 1) and not G.in_zone(WHITE, 2)

    # a Black pawn reaching the last rank must promote (only the +move exists)
    st = SState(board={(2, 0): (BLACK, "K"), (2, 5): (WHITE, "K"), (0, 4): (BLACK, "P")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    pm = [m for m in G.legal_moves(st) if m.startswith("0,4>")]
    assert pm == ["0,4>0,5=+"], pm

    # a Black silver moving INTO the zone (row 4) has both promote / not-promote;
    # the promoted silver then moves like a gold (its (0,1) step is forward-1)
    st = SState(board={(2, 0): (BLACK, "K"), (2, 5): (WHITE, "K"), (0, 3): (BLACK, "S")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    mv = G.legal_moves(st)
    assert "0,3>0,4" in mv and "0,3>0,4=+" in mv, mv
    st2 = G.apply_move(st, "0,3>0,4=+")
    assert (0, 4) in st2.promoted and st2.board[(0, 4)] == (BLACK, "S")
    # +S now moves as a gold: a straight-forward step exists (a Silver cannot).
    # (probe with Black to move so the +S's own moves are generated)
    probe = SState(board={(2, 0): (BLACK, "K"), (3, 5): (WHITE, "K"),
                          (0, 4): (BLACK, "S")},
                   promoted=frozenset({(0, 4)}),
                   hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert "0,4>0,5" in G.legal_moves(probe)

    # a Black silver still on row 2 (outside the zone) cannot promote
    st = SState(board={(2, 0): (BLACK, "K"), (2, 5): (WHITE, "K"), (0, 2): (BLACK, "S")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    mv = G.legal_moves(st)
    assert "0,2>0,3" in mv and "0,2>0,3=+" not in mv, mv

    # capture -> the captured piece switches side into the hand, then can be dropped
    st = SState(board={(2, 0): (BLACK, "K"), (2, 5): (WHITE, "K"),
                       (0, 2): (BLACK, "S"), (1, 3): (WHITE, "G")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "0,2>1,3")             # Sxg (silver captures gold)
    assert st2.hands[BLACK] == {"G": 1}, st2.hands
    # white replies, then black drops the gold on an empty square
    st3 = G.apply_move(st2, "2,5>3,5")            # white king steps aside
    drop = "G@4,4"
    assert drop in G.legal_moves(st3), "gold drop should be legal"
    st4 = G.apply_move(st3, drop)
    assert st4.board[(4, 4)] == (BLACK, "G") and "G" not in st4.hands[BLACK]

    # nifu: you may not drop a pawn onto a file already holding your unpromoted pawn
    st = SState(board={(2, 0): (BLACK, "K"), (2, 5): (WHITE, "K"),
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

    print("goro_goro_shogi selftest OK")


if __name__ == "__main__":
    main()
