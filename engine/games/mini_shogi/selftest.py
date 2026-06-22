"""Mini Shogi correctness anchor (pure stdlib). Start-position perft matches the
published 5x5 minishogi counts 14 / 181 / 2512 -- and depth 1 = 14 is hand-checked
(B 4 + G 2 + K 1 + P 1 + R 3 + S 3). The move generator is the same
python-shogi-verified ShogiLike core as full Shogi; here we also pin the 5x5 setup
and the single-rank (ZONE=1) promotion behaviour."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.mini_shogi.game import MiniShogi    # noqa: E402
from agp.shogilike import SState, BLACK, WHITE  # noqa: E402

G = MiniShogi()


def perft(s, d):
    if d == 0:
        return 1
    if G.is_terminal(s):
        return 0
    return sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


def main():
    s0 = G.initial_state()
    # published minishogi perft
    for d, want in {1: 14, 2: 181, 3: 2512}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # setup: kings in opposite corners, 6 pieces a side, both pawns present
    b = s0.board
    assert b[(0, 0)] == (BLACK, "K") and b[(4, 4)] == (WHITE, "K")
    assert b[(0, 1)] == (BLACK, "P") and b[(4, 3)] == (WHITE, "P")
    assert sum(1 for v in b.values() if v[0] == BLACK) == 6
    assert sum(1 for v in b.values() if v[0] == WHITE) == 6

    # ZONE = 1: only the far rank promotes
    assert G.in_zone(BLACK, 4) and not G.in_zone(BLACK, 3)
    assert G.in_zone(WHITE, 0) and not G.in_zone(WHITE, 1)
    # a Black pawn reaching the last rank must promote (only the +move exists)
    st = SState(board={(0, 0): (BLACK, "K"), (4, 4): (WHITE, "K"), (2, 3): (BLACK, "P")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    pm = [m for m in G.legal_moves(st) if m.startswith("2,3>")]
    assert pm == ["2,3>2,4=+"], pm
    # a Black rook moving INTO row 3 (not the zone) gets no promotion option
    st = SState(board={(0, 0): (BLACK, "K"), (4, 4): (WHITE, "K"), (2, 2): (BLACK, "R")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert "2,2>2,3" in G.legal_moves(st) and "2,2>2,3=+" not in G.legal_moves(st)

    # captured piece switches side into hand and can be dropped (inherited core)
    st = SState(board={(0, 0): (BLACK, "K"), (4, 4): (WHITE, "K"),
                       (2, 2): (BLACK, "R"), (2, 3): (WHITE, "S")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "2,2>2,3")          # Rxs
    assert st2.hands[BLACK] == {"S": 1}, st2.hands

    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)
    print("mini_shogi selftest OK")


if __name__ == "__main__":
    main()
