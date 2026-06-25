#!/usr/bin/env python3
"""Standalone correctness anchor for Grant Acedrex (Grande Acedrex).

Run from the engine root with::

    PYTHONPATH=. python3 games/grand_acedrex/selftest.py

Pure stdlib (imports only ``agp`` + this game).  Asserts:

  * the exact 12x12 opening array file-by-file (Kings on the same file g,
    Aanca on f -- a non-mirrored back rank) and the opening legal-move count;
  * a self-computed perft regression baseline (no published Grant Acedrex perft
    exists; these are reproducible node counts that must stay stable);
  * the move of every unusual piece -- Aanca (diagonal-step then orthogonal
    slide outward), Unicorn (knight-hop then diagonal slide outward), Lion
    ((3,0)+(3,1) leaper), Giraffe ((3,2) zebra), Crocodile (= modern bishop),
    Rook -- including the compound pieces' blocking/capture-on-intermediate;
  * the King's one-time first-move two-square leap (over an occupied square, no
    capture, flag cleared after moving) and that the leap respects king safety;
  * the file-based pawn promotion (g-file pawn -> Aanca);
  * compound-piece check detection and a forced checkmate;
  * a serialize / deserialize round-trip (incl. the king-leap flags).

Prints "SELFTEST OK" and exits 0 on success, nonzero on any failure.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import GrantAcedrex, BACK_RANK  # noqa: E402
from agp.chesslike import CState, WHITE, BLACK  # noqa: E402

G = GrantAcedrex()


def fail(msg: str):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def perft(state, depth: int) -> int:
    if depth == 0:
        return 1
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


def state_from(pieces: dict, to_move=WHITE, rights=frozenset()) -> CState:
    board = dict(pieces)
    return CState(board=board, to_move=to_move, castling=rights, ep=None,
                  reps={G._poskey(board, to_move, rights, None): 1})


def targets(state, src):
    """Destination cells the piece on ``src`` can legally move to (king-safety
    filtered; uses ``_legal`` so the insufficient-material gate can't suppress
    moves in these sparse test positions)."""
    out = {to for (frm, to) in G._legal(state) if frm == src}
    out |= {to for (frm, to) in G.CASTLING.moves(G, state) if frm == src}
    return out


# --------------------------------------------------------------------------- #
# 1. Board geometry & the exact opening array
# --------------------------------------------------------------------------- #
def test_setup():
    s = G.initial_state()
    if (G.WIDTH, G.HEIGHT) != (12, 12):
        fail(f"board must be 12x12, got {G.WIDTH}x{G.HEIGHT}")
    if len(s.board) != (12 + 12) * 2:
        fail(f"expected 48 pieces at start, got {len(s.board)}")
    expect = ["R", "L", "U", "G", "C", "A", "K", "C", "G", "U", "L", "R"]
    if BACK_RANK != expect:
        fail(f"back rank array wrong: {BACK_RANK}")
    # Kings face each other on the SAME file g (col 6); Aanca on f (col 5).
    if s.board.get((6, 0)) != (WHITE, "K") or s.board.get((6, 11)) != (BLACK, "K"):
        fail("both Kings must be on file g (col 6)")
    if s.board.get((5, 0)) != (WHITE, "A") or s.board.get((5, 11)) != (BLACK, "A"):
        fail("Aanca must be on file f (col 5)")
    for c in range(12):
        if s.board.get((c, 0)) != (WHITE, expect[c]):
            fail(f"White back rank wrong at col {c}")
        if s.board.get((c, 11)) != (BLACK, expect[c]):
            fail(f"Black back rank wrong at col {c}")
        if s.board.get((c, 3)) != (WHITE, "P"):
            fail(f"White pawn missing on col {c}, row 3")
        if s.board.get((c, 8)) != (BLACK, "P"):
            fail(f"Black pawn missing on col {c}, row 8")
    # both kings carry the unmoved-leap flag at the start
    if sorted(s.castling) != ["B", "W"]:
        fail(f"king-leap flags wrong at start: {sorted(s.castling)}")


# --------------------------------------------------------------------------- #
# 2. Opening legal-move count + perft regression baseline (self-computed)
# --------------------------------------------------------------------------- #
def test_opening_count():
    s = G.initial_state()
    n = len(G.legal_moves(s))
    if n != 59:
        fail(f"opening legal-move count = {n}, expected 59")


def test_perft():
    s = G.initial_state()
    # Frozen, reproducible baselines (depth 3 = 206209 was computed once; it is
    # ~18s, so it is left out of the fast suite -- depths 1 and 2 guard the same
    # move generator against regressions).
    for d, want in {1: 59, 2: 3481}.items():
        got = perft(s, d)
        if got != want:
            fail(f"perft({d}) = {got}, expected {want}")


# --------------------------------------------------------------------------- #
# 3. Rook (orthogonal slider) and Crocodile (= modern bishop)
# --------------------------------------------------------------------------- #
def test_rook_crocodile():
    # Kings placed OFF the test piece's lines (col 0 / col 11 are clear of the
    # central piece's rays).
    s = state_from({(5, 5): (WHITE, "R"), (0, 11): (WHITE, "K"), (11, 0): (BLACK, "K")})
    t = targets(s, (5, 5))
    expect = {(c, 5) for c in range(12) if c != 5} | {(5, r) for r in range(12) if r != 5}
    if t != expect:
        fail("Rook orthogonal reach wrong")

    s = state_from({(5, 5): (WHITE, "C"), (0, 11): (WHITE, "K"), (11, 0): (BLACK, "K")})
    t = targets(s, (5, 5))
    expect = set()
    for dc, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        c, r = 5 + dc, 5 + dr
        while 0 <= c < 12 and 0 <= r < 12:
            expect.add((c, r)); c += dc; r += dr
    if t != expect:
        fail("Crocodile (modern-bishop) diagonal reach wrong")
    if any(c == 5 or r == 5 for (c, r) in t):
        fail("Crocodile moved orthogonally (must be a pure diagonal slider)")


# --------------------------------------------------------------------------- #
# 4. Lion ((3,0)+(3,1) leaper) and Giraffe ((3,2) zebra)
# --------------------------------------------------------------------------- #
def test_lion():
    s = state_from({(5, 5): (WHITE, "L"), (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")})
    t = targets(s, (5, 5))
    expect = set()
    for dc, dr in [(3, 0), (-3, 0), (0, 3), (0, -3)]:        # threeleaper
        expect.add((5 + dc, 5 + dr))
    for dc, dr in [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]:
        expect.add((5 + dc, 5 + dr))                        # camel
    expect = {p for p in expect if 0 <= p[0] < 12 and 0 <= p[1] < 12}
    if t != expect:
        fail(f"Lion (3,0)+(3,1) leap wrong: {sorted(t)} != {sorted(expect)}")
    # leaps OVER an adjacent blocker (it's a jumper)
    s2 = state_from({(5, 5): (WHITE, "L"), (6, 6): (BLACK, "P"),
                     (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")})
    if (8, 6) not in targets(s2, (5, 5)) and (8, 6) in expect:
        fail("Lion failed to jump over an adjacent piece")


def test_giraffe():
    s = state_from({(5, 5): (WHITE, "G"), (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")})
    t = targets(s, (5, 5))
    expect = set()
    for dc, dr in [(3, 2), (2, 3), (-3, 2), (-2, 3), (3, -2), (2, -3), (-3, -2), (-2, -3)]:
        expect.add((5 + dc, 5 + dr))
    expect = {p for p in expect if 0 <= p[0] < 12 and 0 <= p[1] < 12}
    if t != expect:
        fail(f"Giraffe (3,2) leap wrong: {sorted(t)} != {sorted(expect)}")


# --------------------------------------------------------------------------- #
# 5. Aanca: one diagonal step then orthogonal slide outward
# --------------------------------------------------------------------------- #
def test_aanca():
    s = state_from({(5, 5): (WHITE, "A"), (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")})
    t = targets(s, (5, 5))
    # Build the expected griffon cross: four diagonal steps, then slide out along
    # the two orthogonals leading away from origin.
    expect = set()
    for sx in (1, -1):
        for sy in (1, -1):
            mc, mr = 5 + sx, 5 + sy
            expect.add((mc, mr))                            # the intermediate
            for ddc, ddr in [(sx, 0), (0, sy)]:
                cc, rr = mc + ddc, mr + ddr
                while 0 <= cc < 12 and 0 <= rr < 12:
                    expect.add((cc, rr)); cc += ddc; rr += ddr
    if t != expect:
        fail(f"Aanca reach wrong: count {len(t)} vs {len(expect)}")
    # The Aanca's vertical slides run up the columns ADJACENT to its origin
    # (cols 4 and 6, reached via the diagonal steps), NOT its own column 5.
    if (6, 11) not in t or (4, 0) not in t:
        fail("Aanca vertical slide should reach the far ranks on cols 4/6")
    if (5, 11) in t or (5, 0) in t:
        fail("Aanca must NOT slide up its own column (col 5)")

    # Blocking: own piece on the diagonal step blocks that whole leg.
    s2 = state_from({(5, 5): (WHITE, "A"), (6, 6): (WHITE, "R"),
                     (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")})
    t2 = targets(s2, (5, 5))
    if (6, 6) in t2 or (7, 6) in t2 or (6, 7) in t2:
        fail("Aanca should be blocked by an own piece on its diagonal step")
    # Capture on the intermediate, but no sliding past it.
    s3 = state_from({(5, 5): (WHITE, "A"), (6, 6): (BLACK, "P"),
                     (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")})
    t3 = targets(s3, (5, 5))
    if (6, 6) not in t3:
        fail("Aanca should capture an enemy on its diagonal step")
    if (7, 6) in t3 or (6, 7) in t3:
        fail("Aanca must not slide past a piece it stops on")


# --------------------------------------------------------------------------- #
# 6. Unicorn: knight hop then diagonal slide outward
# --------------------------------------------------------------------------- #
def test_unicorn():
    s = state_from({(5, 5): (WHITE, "U"), (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")})
    t = targets(s, (5, 5))
    knight = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
    expect = set()
    for a, b in knight:
        mc, mr = 5 + a, 5 + b
        if not (0 <= mc < 12 and 0 <= mr < 12):
            continue
        expect.add((mc, mr))                                # the knight landing
        ddc, ddr = (1 if a > 0 else -1), (1 if b > 0 else -1)
        cc, rr = mc + ddc, mr + ddr
        while 0 <= cc < 12 and 0 <= rr < 12:
            expect.add((cc, rr)); cc += ddc; rr += ddr
    if t != expect:
        fail(f"Unicorn reach wrong: count {len(t)} vs {len(expect)}")
    # The classic diagonal run from a hop: e5(5,5)->g6(7,6)->h7(8,7)->...
    for sq in [(7, 6), (8, 7), (9, 8), (10, 9), (11, 10)]:
        if sq not in t:
            fail(f"Unicorn knight-then-diagonal run missing {sq}")
    # Capture on the knight landing, no slide past it.
    s2 = state_from({(5, 5): (WHITE, "U"), (7, 6): (BLACK, "P"),
                     (0, 0): (WHITE, "K"), (11, 11): (BLACK, "K")})
    t2 = targets(s2, (5, 5))
    if (7, 6) not in t2:
        fail("Unicorn should capture an enemy on its knight landing")
    if (8, 7) in t2:
        fail("Unicorn must not slide past a piece it stops on")


# --------------------------------------------------------------------------- #
# 7. King's one-time first-move two-square leap
# --------------------------------------------------------------------------- #
def test_king_leap():
    # White king on g4 (6,3) with flag set; (6,4) occupied -> may leap over it.
    s = state_from({(6, 3): (WHITE, "K"), (6, 4): (WHITE, "R"), (11, 11): (BLACK, "K")},
                   rights=frozenset({"W"}))
    ms = [m for m in G.legal_moves(s) if m.startswith("6,3>")]
    if "6,3>6,5" not in ms:
        fail("king first-move leap over an occupied square missing (6,3>6,5)")
    # Diagonal leap available too.
    if "6,3>8,5" not in ms or "6,3>4,5" not in ms:
        fail("king diagonal two-square leaps missing")
    # After any king move the flag is cleared -> no further leap.
    s2 = G.apply_move(s, "6,3>6,2")
    if "W" in s2.castling:
        fail("king-leap flag not cleared after a king move")
    s3 = state_from({(6, 2): (WHITE, "K"), (11, 11): (BLACK, "K")}, rights=s2.castling)
    if any(m.startswith("6,2>") and (abs(int(m.split('>')[1].split(',')[0]) - 6) == 2
           or abs(int(m.split('>')[1].split(',')[1]) - 2) == 2) for m in G.legal_moves(s3)):
        fail("king should not leap after its flag is cleared")
    # The leap cannot capture: enemy on the landing square => no leap there.
    s4 = state_from({(6, 3): (WHITE, "K"), (6, 5): (BLACK, "P"), (11, 11): (BLACK, "K")},
                    rights=frozenset({"W"}))
    if "6,3>6,5" in G.legal_moves(s4):
        fail("king leap must not capture (landing on enemy should be illegal)")
    # The leap may not land the king on an attacked (empty) square: a Black rook
    # on (0,5) controls the whole 5th rank, so the leap to the empty (6,5) is
    # illegal (it would land the king in check).
    s5 = state_from({(6, 3): (WHITE, "K"), (0, 5): (BLACK, "R"), (11, 0): (BLACK, "K")},
                    rights=frozenset({"W"}))
    if "6,3>6,5" in G.legal_moves(s5):
        fail("king leap onto an attacked square should be illegal")


# --------------------------------------------------------------------------- #
# 8. File-based pawn promotion (g-file pawn -> Aanca)
# --------------------------------------------------------------------------- #
def test_promotion():
    for col, want in [(0, "R"), (1, "L"), (2, "U"), (3, "G"), (4, "C"),
                      (5, "A"), (6, "A"), (11, "R")]:
        s = state_from({(col, 10): (WHITE, "P"), (0, 0): (WHITE, "K"), (11, 0): (BLACK, "K")})
        promos = [m for m in G.legal_moves(s) if m.startswith(f"{col},10>{col},11")]
        if promos != [f"{col},10>{col},11={want}"]:
            fail(f"col {col} pawn should promote to {want}, got {promos}")
        after = G.apply_move(s, f"{col},10>{col},11={want}")
        if after.board.get((col, 11)) != (WHITE, want):
            fail(f"promoted piece on col {col} is not {want}")


# --------------------------------------------------------------------------- #
# 9. Compound-piece check detection + a forced checkmate
# --------------------------------------------------------------------------- #
def test_checks_and_mate():
    # Aanca delivers check up file g: Aanca on f5 (5,5) steps to g6 then slides
    # up file g to the king on g12... wait, the Aanca's step from f5 is to g6,
    # then it slides up file g -> attacks g-file. King on (6,11).
    s = state_from({(5, 5): (WHITE, "A"), (6, 11): (BLACK, "K"), (0, 0): (WHITE, "K")},
                   to_move=BLACK)
    if not G.in_check(s.board, BLACK):
        fail("Aanca should check a king on the file its slide runs up")
    # Unicorn check along its diagonal run.
    s = state_from({(5, 5): (WHITE, "U"), (9, 8): (BLACK, "K"), (0, 0): (WHITE, "K")},
                   to_move=BLACK)
    if not G.in_check(s.board, BLACK):
        fail("Unicorn should check a king on its knight-then-diagonal line")

    # A forced checkmate: Black king cornered at a12 (0,11); a White Rook on the
    # 12th rank checks from l12 (11,11); the king's flight squares a11 (0,10) and
    # b11 (1,10) are sealed by its own pawns, b12 (1,11) is on the rook's line.
    board = {
        (11, 11): (WHITE, "R"),
        (0, 11): (BLACK, "K"),
        (0, 10): (BLACK, "P"),
        (1, 10): (BLACK, "P"),
        (0, 0): (WHITE, "K"),
    }
    s = state_from(board, to_move=BLACK)
    if not G.in_check(s.board, BLACK):
        fail("checkmate position: Black should be in check")
    if G.legal_moves(s):
        fail(f"checkmate position has legal moves: {G.legal_moves(s)}")
    if not G.is_terminal(s):
        fail("checkmate position should be terminal")
    if G.returns(s) != [1.0, -1.0]:
        fail(f"checkmate should be a White win, got {G.returns(s)}")


# --------------------------------------------------------------------------- #
# 10. serialize / deserialize round-trip (incl. king-leap flags)
# --------------------------------------------------------------------------- #
def test_serialize():
    s = G.initial_state()
    s2 = G.apply_move(s, "6,0>6,2")          # a king leap (clears White's flag)
    d = G.serialize(s2)
    s3 = G.deserialize(d)
    if s3.board != s2.board:
        fail("serialize/deserialize board mismatch")
    if s3.castling != s2.castling:
        fail(f"serialize/deserialize castling-flag mismatch: {s3.castling} != {s2.castling}")
    if s3.to_move != s2.to_move:
        fail("serialize/deserialize to_move mismatch")


def main():
    test_setup()
    test_opening_count()
    test_perft()
    test_rook_crocodile()
    test_lion()
    test_giraffe()
    test_aanca()
    test_unicorn()
    test_king_leap()
    test_promotion()
    test_checks_and_mate()
    test_serialize()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
