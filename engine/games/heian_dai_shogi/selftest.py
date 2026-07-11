"""Heian Dai Shogi correctness anchor (pure stdlib -- imports only agp + this game).

No engine plays this 12th-century game, so hand-transcribed anchors from the
sources (Wikipedia "Heian dai shogi" = the Nichureki reconstruction; cross-
checked vs chessvariants.com/shogivariants.dir/heiandai.html) are primary:

  * the exact 13x13 / 34-piece-a-side starting setup (both sources' diagram);
  * the opening legal-move count (29 -- the king's pawn is blocked by the
    Go-Between) and a frozen start-position perft: 29 / 841 / 25085 at depths
    1/2/3, self-computed (d3 asserted only when SELFTEST_SLOW=1; the opening
    halves cannot interact, so d2 = 29^2 is also an independent sanity check);
  * hand-transcribed complete move sets for ALL 13 piece types at a centre
    square, plus blocking / jumping / edge behaviour and a White-side mirror;
  * promotion: optional on entering AND on leaving the far-3-rank zone,
    forced for Pawn/Lance on the last rank and Knight on the last two,
    none for King/Gold, everything -> Gold except Flying Dragon -> Dragon
    Horse (bishop + one-step orthogonal);
  * the bare-king rule reached via apply_move: outright win, the mutual-baring
    draw escape, and the both-bare draw;
  * checkmate via apply_move (with the loser NOT bare, isolating the mate path);
  * fourfold-repetition draw; serialize round-trips (incl. a bare-king result);
  * DROP-LESS: no drop moves, no reserve tray; random playouts terminate
    within the ply cap.
"""
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.heian_dai_shogi.game import HeianDaiShogi, HState   # noqa: E402
from agp.shogilike import BLACK, WHITE                          # noqa: E402

G = HeianDaiShogi()
BK, WK = (1, 0), (11, 12)          # default off-diagonal king parking spots


def perft(state, d):
    if d == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), d - 1) for m in G.legal_moves(state))

def st(board, **kw):
    kw.setdefault("hands", {BLACK: {}, WHITE: {}})
    return HState(board=board, **kw)

def dests(state, frm):
    return {m.split(">")[1].split("=")[0]
            for m in G.legal_moves(state)
            if ">" in m and m.split(">")[0] == frm}

def center(letter, promoted=False, to_move=BLACK):
    board = {(6, 6): (to_move, letter), BK: (BLACK, "K"), WK: (WHITE, "K")}
    prom = frozenset({(6, 6)}) if promoted else frozenset()
    return dests(st(board, promoted=prom, to_move=to_move), "6,6")

def cells(*pairs):
    return {f"{c},{r}" for (c, r) in pairs}


def main():
    s0 = G.initial_state()

    # 1) Board size + piece census (13 types, 34 a side).
    assert G.WIDTH == 13 and G.HEIGHT == 13 and G.ZONE == 3
    assert len(s0.board) == 68
    for pl in (BLACK, WHITE):
        cnt = {}
        for (p, t) in s0.board.values():
            if p == pl:
                cnt[t] = cnt.get(t, 0) + 1
        assert cnt == {"K": 1, "G": 2, "S": 2, "C": 2, "I": 2, "N": 2, "L": 2,
                       "T": 2, "D": 2, "F": 2, "M": 1, "B": 1, "P": 13}, cnt

    # 2) Exact setup (both sources' diagram). Black rank 1 (row 0):
    b = s0.board
    back = ["L", "N", "I", "C", "S", "G", "K", "G", "S", "C", "I", "N", "L"]
    assert [b[(c, 0)][1] for c in range(13)] == back
    # rank 2: Free Chariots / Flying Dragons / Fierce Tigers / Side Mover.
    row1 = {0: "F", 1: "D", 4: "T", 6: "M", 8: "T", 11: "D", 12: "F"}
    assert {c: b[(c, 1)][1] for c in range(13) if (c, 1) in b} == row1
    # rank 3: 13 pawns; rank 4: the Go-Between on the king's file.
    assert all(b[(c, 2)] == (BLACK, "P") for c in range(13))
    assert b[(6, 3)] == (BLACK, "B") and (5, 3) not in b and (7, 3) not in b
    # White = the 180-degree rotation.
    for (c, r), (p, t) in b.items():
        if p == BLACK:
            assert b[(12 - c, 12 - r)] == (WHITE, t)

    # 3) Opening move count + frozen perft (self-computed).
    assert len(G.legal_moves(s0)) == 29, len(G.legal_moves(s0))
    assert perft(s0, 1) == 29
    assert perft(s0, 2) == 841          # = 29^2: the camps cannot interact yet
    if os.environ.get("SELFTEST_SLOW"):
        assert perft(s0, 3) == 25085

    # 4) Complete centre move sets for all 13 types (hand-transcribed).
    assert center("K") == cells((5, 5), (6, 5), (7, 5), (5, 6), (7, 6),
                                (5, 7), (6, 7), (7, 7))
    assert center("G") == cells((6, 7), (6, 5), (5, 6), (7, 6), (5, 7), (7, 7))
    assert center("S") == cells((6, 7), (5, 7), (7, 7), (5, 5), (7, 5))
    assert center("C") == cells((6, 7), (6, 5), (5, 6), (7, 6))        # wazir
    assert center("I") == cells((6, 7), (5, 7), (7, 7), (5, 6), (7, 6))  # no rear
    assert center("T") == cells((5, 7), (7, 7), (5, 5), (7, 5))
    assert center("B") == cells((6, 7), (6, 5))
    assert center("P") == cells((6, 7))
    assert center("N") == cells((5, 8), (7, 8))
    assert center("L") == cells(*[(6, r) for r in range(7, 13)])
    assert center("M") == cells((6, 7), *[(c, 6) for c in range(13) if c != 6])
    assert center("F") == cells(*[(6, r) for r in range(13) if r != 6])
    assert center("D") == cells(*[(6 + k * dc, 6 + k * dr)
                                  for k in range(1, 7)
                                  for (dc, dr) in ((1, 1), (1, -1), (-1, 1), (-1, -1))
                                  if 0 <= 6 + k * dc <= 12 and 0 <= 6 + k * dr <= 12])
    assert len(center("D")) == 24

    # 5) White mirror: a Gote Iron General steps toward row 0.
    assert center("I", to_move=WHITE) == cells((6, 5), (5, 5), (7, 5),
                                               (5, 6), (7, 6))

    # 6) Blocking / jumping. Knight jumps over a wall of pawns:
    board = {(6, 6): (BLACK, "N"), BK: (BLACK, "K"), WK: (WHITE, "K")}
    for dc in (-1, 0, 1):
        board[(6 + dc, 7)] = (BLACK if dc else WHITE, "P")
    d = dests(st(board), "6,6")
    assert d == cells((5, 8), (7, 8)), d
    # Lance stops on the first enemy piece (capture) and cannot pass it:
    board = {(6, 2): (BLACK, "L"), (6, 8): (WHITE, "P"),
             BK: (BLACK, "K"), WK: (WHITE, "K")}
    assert dests(st(board), "6,2") == cells(*[(6, r) for r in range(3, 9)])
    # Side Mover stops short of a friendly piece, steps only 1 forward:
    board = {(6, 6): (BLACK, "M"), (3, 6): (BLACK, "P"), (6, 8): (WHITE, "P"),
             BK: (BLACK, "K"), WK: (WHITE, "K")}
    d = dests(st(board), "6,6")
    assert d == cells((4, 6), (5, 6), (7, 6), (8, 6), (9, 6), (10, 6),
                      (11, 6), (12, 6), (6, 7)), d

    # 7) Promotion: optional on ENTERING the zone (rows 10-12 for Black)...
    board = {(5, 9): (BLACK, "S"), BK: (BLACK, "K"), WK: (WHITE, "K")}
    mv = set(G.legal_moves(st(board)))
    assert "5,9>5,10" in mv and "5,9>5,10=+" in mv
    # ...and on LEAVING it (move starts in the zone, ends outside):
    board = {(5, 10): (BLACK, "S"), BK: (BLACK, "K"), WK: (WHITE, "K")}
    mv = set(G.legal_moves(st(board)))
    assert "5,10>4,9" in mv and "5,10>4,9=+" in mv
    # Forced: Pawn and Lance on the last rank...
    board = {(4, 11): (BLACK, "P"), BK: (BLACK, "K"), WK: (WHITE, "K")}
    assert [m for m in G.legal_moves(st(board)) if m.startswith("4,11>")] \
        == ["4,11>4,12=+"]
    board = {(0, 5): (BLACK, "L"), BK: (BLACK, "K"), WK: (WHITE, "K")}
    mv = set(G.legal_moves(st(board)))
    assert "0,5>0,12=+" in mv and "0,5>0,12" not in mv     # last rank: forced
    assert "0,5>0,11" in mv and "0,5>0,11=+" in mv         # rank 12: optional
    # ...and the Knight on the last two ranks:
    board = {(5, 9): (BLACK, "N"), BK: (BLACK, "K"), WK: (WHITE, "K")}
    mv = set(G.legal_moves(st(board)))
    assert mv >= {"5,9>4,11=+", "5,9>6,11=+"} and not any(
        m in mv for m in ("5,9>4,11", "5,9>6,11"))
    # The Iron General is NOT forced (it can still step sideways up there):
    board = {(5, 11): (BLACK, "I"), BK: (BLACK, "K"), WK: (WHITE, "K")}
    mv = set(G.legal_moves(st(board)))
    assert "5,11>5,12" in mv and "5,11>5,12=+" in mv
    # King and Gold never promote:
    board = {(5, 10): (BLACK, "G"), (6, 10): (BLACK, "K"), WK: (WHITE, "K")}
    assert not any(m.endswith("=+") for m in G.legal_moves(st(board)))

    # 8) Promoted moves: everything -> Gold, Flying Dragon -> Dragon Horse.
    assert center("I", promoted=True) == center("G")       # a promoted Iron = Gold
    assert center("P", promoted=True) == center("G")       # tokin
    dh = center("D", promoted=True)
    assert dh == center("D") | cells((6, 7), (6, 5), (5, 6), (7, 6))
    assert len(dh) == 28
    # ...and a promotion applied via apply_move sticks:
    board = {(4, 9): (BLACK, "P"), BK: (BLACK, "K"), WK: (WHITE, "K")}
    sp = G.apply_move(st(board), "4,9>4,10=+")
    assert (4, 10) in sp.promoted and sp.board[(4, 10)] == (BLACK, "P")

    # 9) Bare-king WIN via apply_move: Black's Free Chariot takes White's last
    # non-king piece; White's far-away King cannot bare Black back.
    board = {(0, 0): (BLACK, "K"), (5, 5): (BLACK, "G"), (3, 3): (BLACK, "F"),
             (11, 12): (WHITE, "K"), (3, 9): (WHITE, "P")}
    s = G.apply_move(st(board), "3,3>3,9")
    assert s.result == BLACK and G.is_terminal(s)
    assert G.returns(s) == [1.0, -1.0] and G.legal_moves(s) == []

    # 10) The mutual-baring DRAW escape: Black bares White, but Black's ONLY
    # piece lands where the bared King can legally recapture -> drawn at once.
    board = {(0, 12): (BLACK, "K"), (5, 3): (BLACK, "G"),
             (5, 5): (WHITE, "K"), (5, 4): (WHITE, "P")}
    s = G.apply_move(st(board), "5,3>5,4")
    assert s.result == "draw" and G.is_terminal(s) and G.returns(s) == [0.0, 0.0]

    # 11) Both kings bare -> draw.
    board = {(5, 5): (BLACK, "K"), (5, 6): (WHITE, "P"), (9, 9): (WHITE, "K")}
    s = G.apply_move(st(board), "5,5>5,6")
    assert s.result == "draw" and G.returns(s) == [0.0, 0.0]

    # 12) Checkmate via apply_move (loser NOT bare, isolating the mate path):
    # Gold slides up to the corner King, guarded by a Fierce Tiger; White's
    # spare pawn has no check-resolving move.
    board = {(0, 12): (WHITE, "K"), (12, 12): (WHITE, "P"),
             (1, 10): (BLACK, "G"), (2, 10): (BLACK, "T"), (12, 0): (BLACK, "K")}
    s = G.apply_move(st(board), "1,10>1,11")
    assert s.result is None                     # not a bare-king event
    assert G.is_terminal(s) and G.legal_moves(s) == []
    assert G.returns(s) == [1.0, -1.0]          # Black mates White

    # 13) Fourfold repetition (sennichite) -> draw.
    board = {(0, 0): (BLACK, "K"), (6, 6): (BLACK, "P"),
             (12, 12): (WHITE, "K"), (6, 8): (WHITE, "P")}
    s = st(board)
    cycle = ["0,0>0,1", "12,12>12,11", "0,1>0,0", "12,11>12,12"]
    for i in range(20):
        if G.is_terminal(s):
            break
        m = cycle[i % 4]
        assert m in G.legal_moves(s)
        s = G.apply_move(s, m)
    assert G.is_terminal(s) and s.ply <= 16, s.ply
    assert s.result is None and G.returns(s) == [0.0, 0.0]

    # 14) DROP-LESS: no drop moves ever, no reserve tray; a capture stays out.
    assert not any("@" in m for m in G.legal_moves(s0))
    assert "reserve" not in G.render(s0)
    board = {(5, 5): (BLACK, "D"), (7, 7): (WHITE, "P"),
             BK: (BLACK, "K"), WK: (WHITE, "K")}
    after = G.apply_move(st(board), "5,5>7,7")
    assert not any("@" in m for m in G.legal_moves(after))

    # 15) Serialize round-trips (start, promoted, and a bare-king result).
    for state in (s0, sp, G.apply_move(st({(0, 0): (BLACK, "K"),
                                           (5, 5): (BLACK, "G"), (3, 3): (BLACK, "F"),
                                           (11, 12): (WHITE, "K"), (3, 9): (WHITE, "P")}),
                                       "3,3>3,9")):
        assert G.serialize(G.deserialize(G.serialize(state))) == G.serialize(state)
    assert G.deserialize(G.serialize(s)).result is None

    # 16) Random playouts terminate within the ply cap.
    for seed in (20260710, 7):
        rng = random.Random(seed)
        s = s0
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            assert s.ply <= G.PLY_CAP + 1, s.ply
        assert len(G.returns(s)) == 2

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
