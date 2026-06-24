"""Standalone correctness self-test for Anti-King Chess II (run from ``engine``):

    PYTHONPATH=. python3 games/anti_king_chess/selftest.py

Pure-stdlib (imports only ``agp`` + this game). It asserts:

  1. Opening perft (engine-derived, frozen as a regression lock). Depth 1 = 22 is
     hand-explained below.
  2. Setup: both Kings AND both Anti-Kings present on the right squares, and each
     Anti-King already attacked at the start (so the opening is legal).
  3. The INVERTED rule: a move that leaves your OWN Anti-King un-attacked is
     ILLEGAL (here, capturing the sole attacker of your own Anti-King).
  4. The Anti-King captures only FRIENDLY pieces (never enemy) and gives no check.
  5. Anti-checkmate (pure, king NOT in check) is terminal with the right winner,
     reached via apply_move.
  6. Orthodox checkmate of the normal King still works (Anti-King kept safe).
  7. serialize / deserialize round-trips with the Anti-King.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

import sys

from games.anti_king_chess.game import AntiKingChess, WHITE, BLACK
from agp.chesslike import CState


# Engine-derived opening perft (frozen regression lock).
#   depth 1 = 22  (hand-explained: the 20 orthodox opening moves -- 16 pawn pushes +
#                  4 knight moves -- PLUS the White Anti-King on d6 stepping to e6 or
#                  c6, the only two king-steps that keep it attacked by a Black pawn;
#                  every other Anti-King step would leave it un-attacked and is
#                  therefore illegal).
PERFT = {1: 22, 2: 490, 3: 11469}


def perft(game, state, depth):
    if depth == 0:
        return 1
    if game.is_terminal(state):
        return 0
    total = 0
    for mv in game.legal_moves(state):
        total += perft(game, game.apply_move(state, mv), depth - 1)
    return total


def st(pieces, to_move=WHITE, castling=""):
    return CState(board=dict(pieces), to_move=to_move,
                  castling=frozenset(castling), ep=None, reps={})


def main(deep=False):
    g = AntiKingChess()
    s0 = g.initial_state()

    # ---- 1. opening perft anchor ----------------------------------------
    depths = (1, 2, 3) if deep else (1, 2)
    for d in depths:
        got = perft(g, s0, d)
        assert got == PERFT[d], f"perft({d}) = {got}, expected {PERFT[d]}"
    assert len(g.legal_moves(s0)) == 22, "opening should have 22 legal moves"

    # ---- 2. setup: two kings + two anti-kings, anti-kings attacked -------
    b = s0.board
    assert b[(4, 0)] == (WHITE, "K") and b[(4, 7)] == (BLACK, "K"), "kings on e1/e8"
    assert b[(3, 5)] == (WHITE, "A"), "white anti-king on d6 (3,5)"
    assert b[(3, 2)] == (BLACK, "A"), "black anti-king on d3 (3,2)"
    # both anti-kings must START attacked (by enemy pawns) -> position is legal.
    assert g._attacked_by_nonking(b, 3, 5, BLACK), "white anti-king must start attacked"
    assert g._attacked_by_nonking(b, 3, 2, WHITE), "black anti-king must start attacked"
    assert not g._in_danger(b, WHITE), "white not in danger at start"
    # the Anti-King is NOT in the attack tables (it attacks nothing).
    assert "A" not in g._leap_map.get((1, 0), set()), "anti-king must not be an attacker"

    # ---- 3. INVERTED rule: leaving your own anti-king un-attacked is illegal
    # White anti-king e4 (4,3) attacked ONLY by a Black rook on the e-file (e8).
    # A White move that removes that sole attacker (capturing the rook) would leave
    # White's anti-king un-attacked -> ILLEGAL, even though it is materially a free
    # rook.  A White bishop on c6 can reach e8 diagonally? No -- but a rook can:
    inv = st({
        (4, 3): (WHITE, "A"),      # white anti-king e4
        (4, 7): (BLACK, "R"),      # black rook e8 -> sole attacker of e4
        (4, 0): (WHITE, "R"),      # white rook e1 -> can capture the e8 rook up the file
        (0, 0): (WHITE, "K"), (7, 0): (BLACK, "K"),
    }, to_move=WHITE)
    assert g._attacked_by_nonking(inv.board, 4, 3, BLACK), "anti-king is attacked here"
    legal = set(g.legal_moves(inv))
    # Re1xe8 removes the only attacker of White's own anti-king -> must be ILLEGAL.
    assert "4,0>4,7" not in legal, "capturing the sole attacker of your own anti-king must be illegal"
    # But the rook MAY move up the file to e7..e2 without removing the attack (it
    # stays between e1 and e4? no -- moving onto e5/e6/e7 would BLOCK the rook's
    # attack on e4 -> also illegal).  Re1-e5/e6/e7 interpose and un-attack e4:
    for blk in ("4,0>4,4", "4,0>4,5", "4,0>4,6"):
        assert blk not in legal, f"{blk} interposes and un-attacks the anti-king -> illegal"

    # ---- 4. anti-king captures only friendly, never enemy; gives no check
    cap = st({
        (4, 3): (WHITE, "A"),      # white anti-king e4
        (5, 3): (WHITE, "P"),      # friendly pawn f4 -> CAN be captured by the A
        (3, 3): (BLACK, "P"),      # enemy pawn d4 -> may NOT be captured
        # Black rooks on e8 AND f8 keep both e4 and f4 attacked, so the anti-king
        # stays legally attacked whether it stays on e4 or captures onto f4.
        (4, 7): (BLACK, "R"), (5, 7): (BLACK, "R"),
        (0, 0): (WHITE, "K"), (7, 0): (BLACK, "K"),
    }, to_move=WHITE)
    amoves = {m for m in g.legal_moves(cap) if m.startswith("4,3>")}
    assert "4,3>5,3" in amoves, "anti-king should be able to capture a FRIENDLY pawn (f4)"
    assert "4,3>3,3" not in amoves, "anti-king must NOT capture an ENEMY pawn (d4)"
    # a black anti-king adjacent to the white king gives NO check.
    adj = st({(4, 4): (WHITE, "K"), (4, 5): (BLACK, "A"), (0, 0): (BLACK, "K")}, to_move=WHITE)
    assert not g.in_check(adj.board, WHITE), "an anti-king adjacent to a king is not check"

    # ---- 5. PURE anti-checkmate (king NOT in check), reached via apply_move
    # Black anti-king a8 attacked ONLY by a White knight on b6.  White moves the
    # knight away; Black -- having only a (mobile) king left -- can never re-attack
    # its own anti-king (kings don't attack anti-kings) -> anti-mate, White wins.
    pre = st({
        (0, 7): (BLACK, "A"),      # black anti-king a8
        (1, 5): (WHITE, "N"),      # white knight b6 -> the sole attacker of a8
        (7, 0): (BLACK, "K"),      # black king h1 (mobile, but only a king)
        (5, 2): (WHITE, "K"),      # white king f3
    }, to_move=WHITE)
    assert g._antiking_safe(pre.board, BLACK), "black anti-king starts attacked (by the knight)"
    assert "1,5>3,4" in g.legal_moves(pre), "white knight b6->d5 should be legal"
    post = g.apply_move(pre, "1,5>3,4")        # knight abandons the attack on a8
    assert not g._antiking_safe(post.board, BLACK), "black anti-king now un-attacked"
    assert not g.in_check(post.board, BLACK), "black king is NOT in check -> a PURE anti-mate"
    assert g._in_danger(post.board, BLACK), "black is in danger (anti-check)"
    assert g.legal_moves(post) == [], "anti-checkmate: black has no legal move"
    assert g.is_terminal(post), "anti-checkmate must be terminal"
    assert g.returns(post) == [1.0, -1.0], f"White should win the anti-mate, got {g.returns(post)}"
    assert "anti-checkmate" in g.render(post)["caption"]

    # ---- 6. orthodox checkmate of the normal KING still works ------------
    # Back-rank mate of the black king, with the black anti-king kept SAFELY attacked
    # so the loss is purely the king mate.
    mate = st({
        (7, 7): (BLACK, "K"), (6, 6): (BLACK, "P"), (7, 6): (BLACK, "P"),  # boxed king h8
        (0, 7): (WHITE, "R"),      # rook a8 -> back-rank check
        (4, 4): (BLACK, "A"), (4, 0): (WHITE, "R"),  # black A e5 kept attacked by rook e1
        (0, 0): (WHITE, "K"),
    }, to_move=BLACK)
    assert g.in_check(mate.board, BLACK), "black king should be in check"
    assert g._antiking_safe(mate.board, BLACK), "black anti-king is kept safe (so this is a KING mate)"
    assert g.legal_moves(mate) == [], "checkmate: black has no legal move"
    assert g.is_terminal(mate) and g.returns(mate) == [1.0, -1.0]
    assert "checkmate" in g.render(mate)["caption"]

    # ---- 7. serialize round-trip (with the anti-king) --------------------
    s = g.initial_state()
    for _ in range(6):
        s = g.apply_move(s, g.legal_moves(s)[0])
    again = g.deserialize(g.serialize(s))
    assert again.board == s.board and again.to_move == s.to_move
    assert again.castling == s.castling and again.ep == s.ep
    assert sum(1 for (_, t) in again.board.values() if t == "A") == 2, "both anti-kings survive round-trip"

    print("SELFTEST OK")
    print(f"opening legal moves = {len(g.legal_moves(s0))}")
    shown = (1, 2, 3) if deep else (1, 2)
    print("opening perft:", {d: PERFT[d] for d in shown})


if __name__ == "__main__":
    main(deep=True)
    sys.exit(0)
