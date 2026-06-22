"""Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Start-position perft matches the published Shogi node counts (30 / 900 / 25470;
depth 4 = 719731 was confirmed against python-shogi in _diff_pyshogi.py but is
left out here to keep the suite fast). Plus targeted rule checks: colour-relative
sliding (the lance/rook must travel the full open file for *both* colours),
capture->hand banking with promoted-piece reversion, the nifu and mandatory-
promotion rules, and serialize round-tripping.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.shogi.game import Shogi          # noqa: E402
from agp.shogilike import SState, BLACK, WHITE  # noqa: E402

G = Shogi()


def perft(state, d):
    if d == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), d - 1) for m in G.legal_moves(state))


def dests(state, frm):
    out = set()
    for m in G.legal_moves(state):
        if ">" in m and m.split(">")[0] == frm:
            out.add(m.split(">")[1].split("=")[0])
    return out


def main():
    # 1) Published start-position perft.
    s0 = G.initial_state()
    for d, want in {1: 30, 2: 900, 3: 25470}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # 2) Colour-relative full-distance sliding (regression: a White lance/rook
    #    must travel the whole open file, not stop after one square).
    for pl in (BLACK, WHITE):
        bk, wk = (0, 0), (0, 8)
        lance_sq = (8, 0) if pl == BLACK else (8, 8)
        board = {bk: (BLACK, "K"), wk: (WHITE, "K"), lance_sq: (pl, "L")}
        st = SState(board=board, hands={BLACK: {}, WHITE: {}}, to_move=pl)
        ds = dests(st, f"{lance_sq[0]},{lance_sq[1]}")
        # the lance sweeps the entire file 8 ahead of it
        far = "8,8" if pl == BLACK else "8,0"
        assert far in ds, f"{['Black','White'][pl]} lance can't reach {far}: {sorted(ds)}"
        assert len(ds) >= 6, f"lance reach too short for player {pl}: {sorted(ds)}"

    # 3) Capture banks to hand; a promoted piece reverts to its base type.
    #    White silver promoted on (3,1); Black rook captures it -> Black gains S.
    board = {(0, 0): (BLACK, "K"), (0, 8): (WHITE, "K"),
             (3, 0): (BLACK, "R"), (3, 1): (WHITE, "S")}
    st = SState(board=board, promoted=frozenset({(3, 1)}),
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "3,0>3,1")        # Rxs (captures a promoted silver)
    assert st2.hands[BLACK] == {"S": 1}, st2.hands   # banked as a plain Silver
    assert (3, 1) not in st2.promoted

    # 4) Nifu: with an unpromoted Black pawn on file 4, no pawn may be dropped
    #    there, but a different empty file is allowed.
    board = {(0, 0): (BLACK, "K"), (0, 8): (WHITE, "K"), (4, 2): (BLACK, "P")}
    st = SState(board=board, hands={BLACK: {"P": 1}, WHITE: {}}, to_move=BLACK)
    drops = {m for m in G.legal_moves(st) if m.startswith("P@")}
    assert not any(m.split("@")[1].split(",")[0] == "4" for m in drops), "nifu violated"
    assert any(m.split("@")[1].split(",")[0] == "5" for m in drops), "pawn drop missing"
    # and no pawn drop on the last rank (row 8 for Black)
    assert not any(m.endswith(",8") for m in drops), "pawn dropped on last rank"

    # 5) Mandatory promotion: a Black pawn reaching the last rank has ONLY the
    #    promoting move.
    board = {(0, 0): (BLACK, "K"), (8, 8): (WHITE, "K"), (4, 7): (BLACK, "P")}
    st = SState(board=board, hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    pawn_moves = [m for m in G.legal_moves(st) if m.startswith("4,7>")]
    assert pawn_moves == ["4,7>4,8=+"], pawn_moves

    # 6) Serialize round-trips (board + promoted + hands).
    mid = G.apply_move(G.apply_move(s0, "2,2>2,3"), "6,6>6,5")
    assert G.serialize(G.deserialize(G.serialize(mid))) == G.serialize(mid)

    print("shogi selftest OK")


if __name__ == "__main__":
    main()
