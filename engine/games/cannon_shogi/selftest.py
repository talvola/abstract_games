"""Cannon Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Anchors:
  * the exact opening legal-move count (51) and a frozen start-position perft
    (51 / 2532 / 137275 at depths 1/2/3);
  * the four cannon move/capture mechanics, the most error-prone part:
      - a GOLD cannon (orthogonal Xiangqi) slides on empties and captures ONLY
        over exactly one screen: no-screen = no capture, one-screen = capture,
        two-screens = no capture;
      - a SILVER cannon (orthogonal Janggi) lands on the first square past a
        single screen for BOTH a move and a capture, and cannot step screenless;
  * cannon CHECK detection (a cannon checks the king only across a screen);
  * a flying (promoted) cannon's perpendicular one-step / leap;
  * a standard piece move + the Janggi-soldier promotion (to a Gold);
  * a drop from the reserve (a banked cannon) and a serialize round-trip with
    hands + a promoted cannon;
  * a checkmate REACHED via apply_move (returns / is_terminal).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.cannon_shogi.game import CannonShogi          # noqa: E402
from agp.shogilike import SState, BLACK, WHITE            # noqa: E402

G = CannonShogi()


def perft(state, d):
    if d == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), d - 1) for m in G.legal_moves(state))


def dests(state, frm):
    return {m.split(">")[1].split("=")[0]
            for m in G.legal_moves(state)
            if ">" in m and m.split(">")[0] == frm}


def st(board, **kw):
    kw.setdefault("hands", {BLACK: {}, WHITE: {}})
    return SState(board=board, **kw)


def main():
    # 1) Opening + frozen perft.
    s0 = G.initial_state()
    assert len(s0.board) == 40, len(s0.board)            # 20 pieces a side
    assert len(G.legal_moves(s0)) == 51, len(G.legal_moves(s0))
    for d, want in {1: 51, 2: 2532, 3: 137275}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # 2) Verified starting placement: bishop/rook + the four cannons on rank 2.
    assert s0.board[(1, 1)] == (BLACK, "B")
    assert s0.board[(7, 1)] == (BLACK, "R")
    assert s0.board[(2, 1)] == (BLACK, "E")   # silver cannon, left silver file
    assert s0.board[(3, 1)] == (BLACK, "C")   # gold cannon, left gold file
    assert s0.board[(5, 1)] == (BLACK, "F")   # iron cannon, right gold file
    assert s0.board[(6, 1)] == (BLACK, "D")   # copper cannon, right silver file
    # soldiers on files 0,2,4,6,8 only
    assert {c for (c, r) in s0.board if r == 2} == {0, 2, 4, 6, 8}

    # 3) GOLD cannon (orthogonal Xiangqi): slide on empties, capture over exactly
    #    ONE screen.
    base = {(0, 0): (BLACK, "C"), (4, 4): (BLACK, "K"), (0, 8): (WHITE, "K")}
    # A) no screen: slides but cannot capture the enemy up the file.
    d = dests(st({**base, (0, 5): (WHITE, "P")}), "0,0")
    assert "0,4" in d and "0,5" not in d, ("no-screen", sorted(d))
    # B) one screen at (0,2): captures (0,5), still slides up to the screen.
    d = dests(st({**base, (0, 2): (BLACK, "P"), (0, 5): (WHITE, "P")}), "0,0")
    assert "0,5" in d and "0,1" in d and "0,3" not in d, ("one-screen", sorted(d))
    # C) two screens: cannot capture.
    d = dests(st({**base, (0, 2): (BLACK, "P"), (0, 4): (BLACK, "P"),
                  (0, 5): (WHITE, "P")}), "0,0")
    assert "0,5" not in d, ("two-screen", sorted(d))

    # 4) SILVER cannon (orthogonal Janggi): jump-to-move AND jump-to-capture; it
    #    lands on the first square past a single screen and cannot step screenless.
    base = {(0, 0): (BLACK, "E"), (4, 4): (BLACK, "K"), (0, 8): (WHITE, "K")}
    d = dests(st({**base, (0, 2): (BLACK, "P")}), "0,0")        # screen, empty land
    assert "0,3" in d and "0,1" not in d, ("janggi-move", sorted(d))
    d = dests(st({**base, (0, 2): (BLACK, "P"), (0, 3): (WHITE, "P")}), "0,0")
    assert "0,3" in d, ("janggi-capture", sorted(d))            # capture past screen
    d = dests(st(base), "0,0")                                  # no screen at all
    assert d == set(), ("janggi-screenless", sorted(d))

    # 5) Cannon CHECK: a gold cannon checks the king only across a screen.
    b = {(0, 0): (BLACK, "C"), (4, 4): (BLACK, "K"), (0, 8): (WHITE, "K"),
         (0, 4): (BLACK, "P")}
    assert G.attacked(b, frozenset(), (0, 8), BLACK)
    assert not G.attacked({k: v for k, v in b.items() if k != (0, 4)},
                          frozenset(), (0, 8), BLACK)           # screen removed

    # 6) Flying (promoted) gold cannon: gains a perpendicular (diagonal) one-step,
    #    and leaps an adjacent piece in that family to land on the 2nd square.
    b = {(4, 4): (BLACK, "C"), (0, 0): (BLACK, "K"), (8, 8): (WHITE, "K"),
         (3, 3): (WHITE, "P")}
    d = dests(st(b, promoted=frozenset({(4, 4)})), "4,4")
    assert "5,5" in d and "2,2" in d, ("flying-cannon", sorted(d))

    # 7) Standard piece + Janggi-soldier promotion (optional; not mandatory, since
    #    a soldier on the last rank can still move sideways).
    b = {(4, 7): (BLACK, "P"), (0, 0): (BLACK, "K"), (8, 0): (WHITE, "K")}
    moves = set(m for m in G.legal_moves(st(b)) if m.startswith("4,7>"))
    assert "4,7>4,8=+" in moves and "4,7>4,8" in moves, moves   # forward, optional
    assert "4,7>3,7" in moves and "4,7>3,7=+" in moves, moves   # sideways, optional

    # 8) Drop a banked cannon from the reserve.
    s = st({(0, 0): (BLACK, "K"), (8, 8): (WHITE, "K")},
           hands={BLACK: {"C": 1}, WHITE: {}})
    assert any(m.startswith("C@") for m in G.legal_moves(s))
    after = G.apply_move(s, "C@4,4")
    assert after.board[(4, 4)] == (BLACK, "C")
    assert after.hands[BLACK].get("C", 0) == 0

    # 9) Capture banks a promoted cannon as its base type.
    b = {(0, 0): (BLACK, "K"), (0, 8): (WHITE, "K"),
         (3, 0): (BLACK, "R"), (3, 1): (WHITE, "C")}
    s2 = G.apply_move(st(b, promoted=frozenset({(3, 1)})), "3,0>3,1")
    assert s2.hands[BLACK] == {"C": 1}, s2.hands
    assert (3, 1) not in s2.promoted

    # 10) Serialize round-trips with hands + a promoted cannon.
    s = st({(4, 4): (BLACK, "C"), (0, 0): (BLACK, "K"), (8, 8): (WHITE, "K"),
            (1, 1): (WHITE, "D")},
           promoted=frozenset({(4, 4)}),
           hands={BLACK: {"P": 2, "E": 1}, WHITE: {"N": 1}}, to_move=WHITE, ply=7)
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    # 11) Checkmate REACHED via apply_move -> terminal + correct returns.
    b = {(0, 8): (WHITE, "K"), (8, 0): (BLACK, "K"),
         (1, 7): (BLACK, "R"), (0, 6): (BLACK, "R")}
    mate = G.apply_move(st(b), "0,6>0,7")
    assert G.is_terminal(mate) and G.legal_moves(mate) == []
    assert G.returns(mate) == [1.0, -1.0]                       # Black mates White

    print("cannon_shogi selftest OK")


if __name__ == "__main__":
    main()
