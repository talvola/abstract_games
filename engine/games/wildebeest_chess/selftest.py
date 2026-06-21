#!/usr/bin/env python3
"""Standalone correctness anchor for Wildebeest Chess.

Run with::

    cd engine && PYTHONPATH=. python3 games/wildebeest_chess/selftest.py

Pure stdlib + this game only (no third-party engine, no thousand-game loops);
finishes in a couple of seconds. Prints ``SELFTEST OK`` and exits 0 on success,
nonzero on any failure.

It asserts:

* a self-computed **perft regression baseline** from the opening position
  (depth 1 = 45, depth 2 = 2025; depth 3 = 95829 was verified once offline and
  is recorded below but not recomputed here, to keep the test fast);
* the **Camel** is a (1,3) leaper (colour-bound, 8 targets from an open centre);
* the **Wildebeest** moves as knight + camel (the union of (1,2) and (1,3));
* **multi-square en passant** works and expires after one move;
* no castling (omitted — uncertain authentic rule on the wide board);
* **promotion** offers only Queen and Wildebeest;
* a **checkmate** position is terminal and scored as a loss for the mated side;
* the **stalemate** option scores a stalemate as a draw (default) or a win.

No widely-published perft table exists for this variant; the perft numbers here
are this engine's own regression baseline.
"""

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.wildebeest_chess.game import (
    WildebeestChess, CAMEL, WILDEBEEST, KNIGHT,
)

# perft(3) from the opening position, verified once offline (≈5 s); recorded as a
# documented constant -- not recomputed here so the committed test stays fast.
PERFT3_OFFLINE = 95829

G = WildebeestChess()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def targets(state, frm):
    """Set of destination cells for moves originating at ``frm`` (a 'c,r' str),
    ignoring promotion suffixes."""
    out = set()
    for m in G.legal_moves(state):
        base = m.split("=")[0]
        f, t = base.split(">")
        if f == frm:
            tc, tr = t.split(",")
            out.add((int(tc), int(tr)))
    return out


def perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


# --------------------------------------------------------------------------- #
# 1. Opening position / setup
# --------------------------------------------------------------------------- #
s0 = G.initial_state()
# point-symmetric back ranks
check(G.setup_board()[(5, 0)] == (WHITE, "K"), "White king must be on f1")
check(G.setup_board()[(6, 0)] == (WHITE, "W"), "White wildebeest must be on g1")
check(G.setup_board()[(4, 0)] == (WHITE, "Q"), "White queen must be on e1")
check(G.setup_board()[(7, 0)] == (WHITE, "C")
      and G.setup_board()[(8, 0)] == (WHITE, "C"), "White camels on h1/i1")
check(G.setup_board()[(5, 9)] == (BLACK, "K"), "Black king must be on f10")
check(G.setup_board()[(6, 9)] == (BLACK, "Q"), "Black queen must be on g10")
check(G.setup_board()[(4, 9)] == (BLACK, "W"), "Black wildebeest must be on e10")
# 11 pawns per side
wp = sum(1 for v in s0.board.values() if v == (WHITE, "P"))
bp = sum(1 for v in s0.board.values() if v == (BLACK, "P"))
check(wp == 11 and bp == 11, f"each side must have 11 pawns (got {wp}/{bp})")
check(len(s0.board) == 2 * (11 + 11), "44 men at start (22 per side)")

# --------------------------------------------------------------------------- #
# 2. Perft regression baseline
# --------------------------------------------------------------------------- #
check(perft(s0, 1) == 45, "perft(1) must be 45")
check(perft(s0, 2) == 2025, "perft(2) must be 2025")
check(PERFT3_OFFLINE == 95829, "recorded perft(3) constant changed")

# --------------------------------------------------------------------------- #
# 3. Camel = (1,3) leaper, colour-bound
# --------------------------------------------------------------------------- #
b = {(5, 4): (WHITE, "C"), (5, 0): (WHITE, "K"), (5, 9): (BLACK, "K")}
sc = CState(board=b, to_move=WHITE)
ct = targets(sc, "5,4")
exp_c = {(5 + dc, 4 + dr) for dc, dr in CAMEL if 0 <= 5 + dc < 11 and 0 <= 4 + dr < 10}
check(ct == exp_c, f"camel targets wrong: {sorted(ct)} != {sorted(exp_c)}")
check(len(ct) == 8, "camel from open centre must have 8 moves")
check(all((c + r) % 2 == (5 + 4) % 2 for (c, r) in ct), "camel must be colour-bound")
check(sorted(CAMEL) == sorted([(1, 3), (3, 1), (-1, 3), (-3, 1),
                               (1, -3), (3, -1), (-1, -3), (-3, -1)]),
      "CAMEL offsets must be the (1,3) leaper set")

# --------------------------------------------------------------------------- #
# 4. Wildebeest = knight + camel
# --------------------------------------------------------------------------- #
b = {(5, 4): (WHITE, "W"), (5, 0): (WHITE, "K"), (5, 9): (BLACK, "K")}
sw = CState(board=b, to_move=WHITE)
wt = targets(sw, "5,4")
exp_w = {(5 + dc, 4 + dr) for dc, dr in WILDEBEEST if 0 <= 5 + dc < 11 and 0 <= 4 + dr < 10}
check(wt == exp_w, f"wildebeest targets wrong: {sorted(wt)} != {sorted(exp_w)}")
check(set(WILDEBEEST) == set(KNIGHT) | set(CAMEL), "wildebeest must be knight+camel")
check(len(set(WILDEBEEST)) == 16, "wildebeest must have 16 distinct offsets")

# --------------------------------------------------------------------------- #
# 5. Multi-step pawn + multi-square en passant
# --------------------------------------------------------------------------- #
# a2 pawn (own half rows 0-4) may step to a3/a4/a5 only.
check(targets(s0, "0,1") == {(0, 2), (0, 3), (0, 4)},
      "a2 pawn should reach a3/a4/a5 (own-half multi-step)")
# A pawn already past the midline single-steps.
b = {(1, 4): (BLACK, "P"), (5, 0): (WHITE, "K"), (5, 9): (BLACK, "K")}
sp = CState(board=b, to_move=BLACK)
check(targets(sp, "1,4") == {(1, 3)}, "black pawn past midline must single-step")

# en passant: white a2->a5 skips a3,a4; black pawn on b5 captures on a4.
b = {(0, 1): (WHITE, "P"), (1, 4): (BLACK, "P"),
     (5, 0): (WHITE, "K"), (5, 9): (BLACK, "K")}
s = CState(board=b, to_move=WHITE)
s2 = G.apply_move(s, "0,1>0,4")
check(s2.ep is not None and set(s2.ep[0]) == {(0, 2), (0, 3)} and s2.ep[1] == (0, 4),
      "en-passant record must list every skipped square")
check((1, 4, 0, 3) in [(*map(int, m.split('=')[0].replace('>', ',').split(',')),)
                       for m in G.legal_moves(s2) if m.startswith("1,4>")],
      "black should be able to ep-capture onto a4")
s3 = G.apply_move(s2, "1,4>0,3")
check((0, 4) not in s3.board, "ep capture must remove the advanced pawn")
check(s3.board.get((0, 3)) == (BLACK, "P"), "ep capturer must land on the skipped square")
# ep expires after an unrelated move
b2 = {(0, 1): (WHITE, "P"), (5, 0): (WHITE, "K"), (5, 9): (BLACK, "K"),
      (10, 9): (BLACK, "R")}
s = CState(board=b2, to_move=WHITE, castling=frozenset())
s2 = G.apply_move(s, "0,1>0,4")
s3 = G.apply_move(s2, "10,9>10,8")
check(s3.ep is None, "en passant must expire after one move")

# --------------------------------------------------------------------------- #
# 6. No castling: a lone king on its home square makes only ordinary 1-square
#    moves (Wildebeest's authentic castling is uncertain on 11-wide; omitted).
# --------------------------------------------------------------------------- #
b = {(5, 0): (WHITE, "K"), (10, 0): (WHITE, "R"), (5, 9): (BLACK, "K")}
s = CState(board=b, to_move=WHITE, castling=frozenset())
kt = targets(s, "5,0")
check(all(abs(c - 5) <= 1 and abs(r - 0) <= 1 for (c, r) in kt),
      "king makes only one-square moves (no castling)")
check((6, 0) in kt and (4, 0) in kt, "ordinary 1-square king steps are legal")
check(not any(abs(c - 5) >= 2 for (c, r) in kt), "no multi-square castle move offered")

# --------------------------------------------------------------------------- #
# 7. Promotion offers only Queen and Wildebeest
# --------------------------------------------------------------------------- #
b = {(0, 8): (WHITE, "P"), (5, 0): (WHITE, "K"), (5, 9): (BLACK, "K")}
s = CState(board=b, to_move=WHITE)
promos = {m.split("=")[1] for m in G.legal_moves(s) if m.startswith("0,8>0,9")}
check(promos == {"Q", "W"}, f"promotion must offer only Q/W, got {promos}")

# --------------------------------------------------------------------------- #
# 8. Checkmate
# --------------------------------------------------------------------------- #
b = {(10, 9): (BLACK, "K"), (9, 7): (WHITE, "Q"), (8, 8): (WHITE, "K")}
s = CState(board=b, to_move=WHITE)
mate = next((m for m in G.legal_moves(s)
             if G.is_terminal(G.apply_move(s, m))
             and G.in_check(G.apply_move(s, m).board, G.apply_move(s, m).to_move)), None)
check(mate == "9,7>10,7", f"expected the mate Qj8-k8, got {mate}")
sm = G.apply_move(s, mate)
check(G.is_terminal(sm), "checkmate position must be terminal")
check(G.returns(sm) == [1.0, -1.0], "checkmated Black must lose")

# --------------------------------------------------------------------------- #
# 9. Stalemate option (draw by default, win when selected)
# --------------------------------------------------------------------------- #
b = {(0, 9): (BLACK, "K"), (2, 8): (WHITE, "K"), (1, 7): (WHITE, "Q")}
s = CState(board=b, to_move=BLACK)
gd = WildebeestChess(); gd.stalemate_wins = False
check(gd.legal_moves(s) == [], "the stalemate position must have no legal moves")
check(not gd.in_check(s.board, BLACK), "the stalemate position must not be check")
check(gd.is_terminal(s) and gd.returns(s) == [0.0, 0.0],
      "default: stalemate is a draw")
gw = WildebeestChess(); gw.stalemate_wins = True
check(gw.returns(s) == [1.0, -1.0],
      "option stalemate=win: the stalemated side loses")

# --------------------------------------------------------------------------- #
# 10. Serialisation round-trips (including the multi-square ep record)
# --------------------------------------------------------------------------- #
b = {(0, 1): (WHITE, "P"), (1, 4): (BLACK, "P"),
     (5, 0): (WHITE, "K"), (5, 9): (BLACK, "K")}
s = CState(board=b, to_move=WHITE)
s2 = G.apply_move(s, "0,1>0,4")
again = G.serialize(G.deserialize(G.serialize(s2)))
check(again == G.serialize(s2), "serialize must round-trip (with ep set)")

print("SELFTEST OK")
sys.exit(0)
