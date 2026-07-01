"""Wa Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Anchors:
  * the exact 11x11 / 27-piece-a-side starting setup (verified vs Wikipedia);
  * the opening legal-move count (51) and a frozen start-position perft
    (51 / 2601 at depths 1/2) -- self-computed (no published Wa perft exists);
  * the geometry of the most distinctive / error-prone pieces:
      - Cloud Eagle: unlimited straight forward/back, a BOUNDED 1-3 diagonal-
        forward slide, single-step sideways and diagonal-back;
      - Liberated Horse: unlimited straight forward, a bounded 1-2 straight-back;
      - Treacherous Fox: 6 single steps PLUS a jump to the 2nd square (over a
        friendly blocker);
      - Heavenly Horse (promoted Liberated Horse): knight jumps forward AND back;
  * mandatory promotion for the Sparrow Pawn / Oxcart on the far rank, optional
    promotion in the zone, and NO promotion for the non-promoters (K/E/X);
  * the DROP-LESS ruleset: no drop moves are ever generated and there is no
    reserve tray in render();
  * a promotion applied via apply_move, a serialize round-trip, a random game
    that terminates under the ply cap, and a checkmate reached via apply_move.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.wa_shogi.game import WaShogi                     # noqa: E402
from agp.shogilike import SState, BLACK, WHITE              # noqa: E402

G = WaShogi()


def perft(state, d):
    if d == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), d - 1) for m in G.legal_moves(state))


def st(board, **kw):
    kw.setdefault("hands", {BLACK: {}, WHITE: {}})
    return SState(board=board, **kw)


def dests(state, frm):
    return {m.split(">")[1].split("=")[0]
            for m in G.legal_moves(state)
            if ">" in m and m.split(">")[0] == frm}


def main():
    s0 = G.initial_state()

    # 1) Board size + piece count.
    assert G.WIDTH == 11 and G.HEIGHT == 11 and G.ZONE == 3
    assert len(s0.board) == 54, len(s0.board)               # 27 a side
    assert sum(1 for v in s0.board.values() if v[0] == BLACK) == 27
    assert sum(1 for v in s0.board.values() if v[0] == WHITE) == 27

    # 2) Exact Black setup (verified vs Wikipedia).
    b = s0.board
    back = ["U", "D", "Y", "G", "L", "K", "T", "C", "O", "M", "N"]
    assert "".join(b[(c, 0)][1] for c in range(11)) == "".join(back)
    assert b[(1, 1)] == (BLACK, "H")            # Flying Falcon (Blind-Dog file)
    assert b[(5, 1)] == (BLACK, "W")            # Swallow's Wings (Crane-King file)
    assert b[(9, 1)] == (BLACK, "E")            # Cloud Eagle (Climbing-Monkey file)
    assert b[(3, 2)] == (BLACK, "X")            # Treacherous Fox (Flying-Goose file)
    assert b[(7, 2)] == (BLACK, "R")            # Running Rabbit (Flying-Cock file)
    assert {c for c in range(11) if b.get((c, 2)) == (BLACK, "P")} == \
        {0, 1, 2, 4, 5, 6, 8, 9, 10}           # 9 sparrow pawns on rank 3
    assert b[(3, 3)] == (BLACK, "P") and b[(7, 3)] == (BLACK, "P")   # 2 advanced
    assert sum(1 for v in b.values() if v == (BLACK, "P")) == 11
    # White is the 180-degree rotation.
    assert b[(10, 10)] == (WHITE, "U") and b[(5, 10)] == (WHITE, "K")

    # 3) Opening + frozen perft (self-computed; d3 = 126574 but omitted for speed).
    assert len(G.legal_moves(s0)) == 51, len(G.legal_moves(s0))
    assert perft(s0, 1) == 51
    assert perft(s0, 2) == 2601

    # 4) Cloud Eagle geometry (bounded diagonal-forward slide, range 3).
    board = {(5, 5): (BLACK, "E"), (10, 10): (BLACK, "K"), (0, 0): (WHITE, "K")}
    d = dests(st(board), "5,5")
    assert {"5,6", "5,7", "5,8", "5,9", "5,10"} <= d          # unlimited forward
    assert {"5,4", "5,3", "5,2", "5,1", "5,0"} <= d           # unlimited backward
    assert {"4,6", "3,7", "2,8"} <= d and "1,9" not in d      # diag-forward 1-3 only
    assert {"6,6", "7,7", "8,8"} <= d and "9,9" not in d
    assert {"4,5", "6,5"} <= d                                # step sideways
    assert {"4,4", "6,4"} <= d                                # step diag-back
    assert len(d) == 20, sorted(d)

    # 5) Liberated Horse: unlimited forward, bounded 1-2 straight back, nothing else.
    board = {(5, 5): (BLACK, "N"), (10, 10): (BLACK, "K"), (0, 0): (WHITE, "K")}
    d = dests(st(board), "5,5")
    assert d == {"5,6", "5,7", "5,8", "5,9", "5,10", "5,4", "5,3"}, sorted(d)

    # 6) Treacherous Fox jumps to the 2nd square OVER a friendly blocker.
    board = {(5, 5): (BLACK, "X"), (5, 6): (BLACK, "P"),
             (10, 10): (BLACK, "K"), (0, 0): (WHITE, "K")}
    d = dests(st(board), "5,5")
    assert "5,6" not in d and "5,7" in d, sorted(d)           # blocked step, jump lands
    assert {"3,7", "7,7", "3,3", "7,3", "5,3"} <= d           # diagonal + back jumps

    # 7) Heavenly Horse (promoted Liberated Horse): knight jumps both ways.
    board = {(5, 5): (BLACK, "N"), (10, 10): (BLACK, "K"), (0, 0): (WHITE, "K")}
    d = dests(st(board, promoted=frozenset({(5, 5)})), "5,5")
    assert d == {"4,7", "6,7", "4,3", "6,3"}, sorted(d)

    # 8) Mandatory promotion: an Oxcart onto the last rank has only the +move.
    board = {(5, 9): (BLACK, "U"), (10, 0): (BLACK, "K"), (0, 10): (WHITE, "K")}
    assert [m for m in G.legal_moves(st(board)) if m.startswith("5,9>")] == ["5,9>5,10=+"]
    # ...a Sparrow Pawn too.
    board = {(4, 9): (BLACK, "P"), (10, 0): (BLACK, "K"), (0, 10): (WHITE, "K")}
    assert [m for m in G.legal_moves(st(board)) if m.startswith("4,9>")] == ["4,9>4,10=+"]

    # 9) Optional promotion inside the zone (a Violent Wolf entering rank 8).
    board = {(4, 7): (BLACK, "L"), (10, 0): (BLACK, "K"), (0, 10): (WHITE, "K")}
    mv = set(m for m in G.legal_moves(st(board)) if m.startswith("4,7>4,8"))
    assert "4,7>4,8" in mv and "4,7>4,8=+" in mv, mv

    # 10) Non-promoters (Crane King, Cloud Eagle, Treacherous Fox) never promote.
    board = {(3, 8): (BLACK, "E"), (4, 8): (BLACK, "X"), (5, 8): (BLACK, "K"),
             (10, 0): (BLACK, "K"), (0, 10): (WHITE, "K")}
    # (two black "K" is only to satisfy generation; use a fox/eagle-focused check)
    board = {(3, 8): (BLACK, "E"), (4, 9): (BLACK, "X"),
             (10, 0): (BLACK, "K"), (0, 10): (WHITE, "K")}
    assert [m for m in G.legal_moves(st(board)) if m.endswith("=+")] == []

    # 11) DROP-LESS: no drop move is ever generated, and no reserve tray.
    assert not any("@" in m for m in G.legal_moves(s0))
    # even after a capture banks material internally, drops stay empty:
    cap = {(5, 5): (BLACK, "H"), (7, 7): (WHITE, "P"),
           (10, 0): (BLACK, "K"), (0, 10): (WHITE, "K")}
    after = G.apply_move(st(cap), "5,5>7,7")                  # falcon captures pawn
    assert not any("@" in m for m in G.legal_moves(after))
    assert "reserve" not in G.render(s0)

    # 12) A promotion applied via apply_move actually promotes.
    board = {(4, 7): (BLACK, "P"), (10, 0): (BLACK, "K"), (0, 10): (WHITE, "K")}
    s = G.apply_move(st(board), "4,7>4,8=+")
    assert (4, 8) in s.promoted and s.board[(4, 8)] == (BLACK, "P")

    # 13) Serialize round-trips (start + a promoted-piece position).
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    # 14) A random game terminates within the ply cap.
    rng = random.Random(20260701)
    s = s0
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        assert s.ply <= G.PLY_CAP + 1, s.ply
    assert G.is_terminal(s)

    # 15) Checkmate reached via apply_move -> terminal + correct returns.
    board = {(0, 10): (WHITE, "K"), (10, 0): (BLACK, "K"),
             (5, 5): (BLACK, "W"), (7, 9): (BLACK, "W")}
    mate = G.apply_move(st(board, promoted=frozenset({(5, 5), (7, 9)})), "5,5>5,10")
    assert G.is_terminal(mate) and G.legal_moves(mate) == []
    assert G.returns(mate) == [1.0, -1.0]                    # Black mates White

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
